"""Security primitives shared by every tool: scopes/allowlist enforcement,
audit logging, output redaction, and the read-only SQL guard.
"""

from __future__ import annotations

import functools
import inspect
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import anyio
import yaml

from mcp_connect_starter import audit, config
from mcp_connect_starter.redaction import redact_any, redact_text

F = TypeVar("F", bound=Callable[..., Any])


class ToolAccessError(Exception):
    """Raised when a tool call is denied by the scope/allowlist policy."""


class SQLSecurityError(Exception):
    """Raised when a submitted SQL statement fails the read-only guard."""


# --------------------------------------------------------------------------
# Scope / allowlist policy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolPolicy:
    name: str
    enabled: bool
    scopes: frozenset[str]


_policy_cache: dict[str, ToolPolicy] | None = None
_policy_cache_mtime: float | None = None


def _load_policy_file(path: Path) -> dict[str, ToolPolicy]:
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text()) or {}
    tools_raw = raw.get("tools", {}) or {}
    policies: dict[str, ToolPolicy] = {}
    for name, spec in tools_raw.items():
        spec = spec or {}
        policies[name] = ToolPolicy(
            name=name,
            enabled=bool(spec.get("enabled", True)),
            scopes=frozenset(spec.get("scopes", []) or []),
        )
    return policies


def get_tool_policy(name: str, *, default_scopes: frozenset[str] = frozenset()) -> ToolPolicy:
    """Return the effective policy for `name`, reloading the scopes file if it changed on disk.

    A tool with no entry in the policy file is enabled by default and
    requires `default_scopes` (the scopes declared in code), so the
    allowlist file is opt-out, not opt-in -- forgetting to list a brand-new
    tool there does not silently expose it with zero required scopes.
    """
    global _policy_cache, _policy_cache_mtime

    path = config.SCOPES_FILE
    mtime = path.stat().st_mtime if path.exists() else None

    if _policy_cache is None or mtime != _policy_cache_mtime:
        _policy_cache = _load_policy_file(path)
        _policy_cache_mtime = mtime

    return _policy_cache.get(name) or ToolPolicy(name=name, enabled=True, scopes=default_scopes)


def reset_policy_cache() -> None:
    """Force the next `get_tool_policy` call to reread the scopes file. Used by tests."""
    global _policy_cache, _policy_cache_mtime
    _policy_cache = None
    _policy_cache_mtime = None


# --------------------------------------------------------------------------
# Tool decorator: enforce policy, audit log, redact output
# --------------------------------------------------------------------------


def secure_tool(name: str, scopes: list[str] | tuple[str, ...] = ()) -> Callable[[F], F]:
    """Decorator applied to every MCP tool implementation.

    On every call it:
      1. Checks the tool is enabled and the server holds every required scope.
      2. Checks the tool against the optional hard allowlist.
      3. Runs the wrapped function.
      4. Redacts PII from the return value (defense in depth; connectors
         should also redact at the source).
      5. Emits a structured audit log record, regardless of outcome.

    Never logs raw argument *values* -- only argument *names* -- so audit
    logs can't themselves become a PII leak.
    """
    required_scopes = frozenset(scopes)

    def decorator(fn: F) -> F:
        is_async = inspect.iscoroutinefunction(fn)

        async def _run_and_handle(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
            request_id = uuid.uuid4().hex[:12]
            started = time.monotonic()
            bound_positional = dict(zip(inspect.signature(fn).parameters, args, strict=False))
            arg_keys = sorted({**bound_positional, **kwargs}.keys())
            policy = get_tool_policy(name, default_scopes=required_scopes)
            granted = config.granted_scopes()
            allowlist = config.tool_allowlist()

            def _audit(status: str, error: str | None = None) -> None:
                audit.emit(
                    audit.AuditRecord(
                        request_id=request_id,
                        tool=name,
                        status=status,
                        duration_ms=round((time.monotonic() - started) * 1000, 3),
                        required_scopes=sorted(policy.scopes),
                        granted_scopes=sorted(granted),
                        arg_keys=arg_keys,
                        error=redact_text(error) if error else None,
                    )
                )

            if not policy.enabled:
                _audit("denied", error=f"tool '{name}' is disabled by server policy")
                raise ToolAccessError(f"Tool '{name}' is disabled by server configuration.")

            if allowlist is not None and name not in allowlist:
                _audit("denied", error=f"tool '{name}' is not in MCP_CONNECT_ALLOWED_TOOLS")
                raise ToolAccessError(f"Tool '{name}' is not on this server's allowlist.")

            missing = policy.scopes - granted
            if missing:
                _audit("denied", error=f"missing scopes: {sorted(missing)}")
                raise ToolAccessError(
                    f"Tool '{name}' requires scope(s) {sorted(policy.scopes)}; "
                    f"this server was granted {sorted(granted)}."
                )

            try:
                if is_async:
                    result = await fn(*args, **kwargs)
                else:
                    # Run blocking connector code (sqlite, file I/O) off the
                    # event loop so one slow call can't stall the HTTP
                    # transport's other in-flight sessions.
                    result = await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
            except (ToolAccessError, SQLSecurityError) as exc:
                _audit("denied", error=str(exc))
                raise
            except Exception as exc:  # noqa: BLE001 - audited then re-raised
                _audit("error", error=str(exc))
                raise
            else:
                _audit("success")
                return redact_any(result)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_and_handle(args, kwargs)

        # FastMCP tool functions may be sync or async; this wrapper is
        # always async (it awaits `fn` itself when `fn` is sync), which
        # FastMCP handles transparently either way.
        return async_wrapper  # type: ignore[return-value]

    return decorator


# --------------------------------------------------------------------------
# Read-only SQL guard
# --------------------------------------------------------------------------

_DISALLOWED_KEYWORDS = re.compile(
    r"(?i)\b("
    r"insert|update|delete|drop|alter|create|replace|truncate|"
    r"attach|detach|pragma|vacuum|grant|revoke|reindex|"
    r"savepoint|release|begin|commit|rollback|into"
    r")\b"
)

_LEADING_KEYWORD = re.compile(r"(?i)^\s*(with|select)\b")


def _strip_sql_comments(sql: str) -> str:
    # Remove -- line comments and /* */ block comments so a commented-out
    # SELECT can't be used to smuggle a write statement past the keyword scan.
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def ensure_read_only_sql(sql: str) -> None:
    """Raise `SQLSecurityError` unless `sql` is a single, read-only SELECT/CTE statement.

    This is layer one of two: the connection itself is also opened read-only
    (SQLite URI `mode=ro`) with `PRAGMA query_only = ON`, so even a statement
    that slips past this check cannot mutate the database.
    """
    if not sql or not sql.strip():
        raise SQLSecurityError("Empty SQL statement.")

    cleaned = _strip_sql_comments(sql).strip()

    # Reject multiple statements (allow one optional trailing semicolon).
    body = cleaned[:-1] if cleaned.endswith(";") else cleaned
    if ";" in body:
        raise SQLSecurityError("Multiple SQL statements are not allowed.")

    if not _LEADING_KEYWORD.match(body):
        raise SQLSecurityError("Only SELECT (or WITH ... SELECT) statements are allowed.")

    match = _DISALLOWED_KEYWORDS.search(body)
    if match:
        raise SQLSecurityError(f"Disallowed keyword in read-only query: '{match.group(0)}'.")
