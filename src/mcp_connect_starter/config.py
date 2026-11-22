"""Central, env-driven configuration.

Every secret or deployment-specific value in this project comes from an
environment variable -- nothing is ever hard-coded or read from a committed
file. This module only defines *defaults* that make the starter runnable
with zero external accounts; override any of them in your own deployment.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repository root when running from a source checkout (editable install or
# `git clone` + run). The bundled demo data lives here. In a real deployment
# you would point MCP_CONNECT_DB_PATH / MCP_CONNECT_DOCS_DIR at your own data
# instead of relying on this default.
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent
DEFAULT_DATA_DIR = _REPO_ROOT / "data"


def _env_path(var: str, default: Path) -> Path:
    raw = os.environ.get(var)
    return Path(raw).expanduser().resolve() if raw else default


def _env_int(var: str, default: int) -> int:
    raw = os.environ.get(var)
    return int(raw) if raw else default


def _env_float(var: str, default: float) -> float:
    raw = os.environ.get(var)
    return float(raw) if raw else default


def _env_bool(var: str, default: bool) -> bool:
    raw = os.environ.get(var)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- Server identity -------------------------------------------------------

SERVER_NAME = os.environ.get("MCP_CONNECT_SERVER_NAME", "mcp-connect-starter")

# --- Data sources (zero external accounts out of the box) ------------------

SQLITE_DB_PATH = _env_path("MCP_CONNECT_DB_PATH", DEFAULT_DATA_DIR / "demo.sqlite3")
DOCS_DIR = _env_path("MCP_CONNECT_DOCS_DIR", DEFAULT_DATA_DIR / "docs")
CRM_FIXTURE_PATH = _env_path("MCP_CONNECT_CRM_FIXTURE", DEFAULT_DATA_DIR / "crm_mock.json")

# --- Read-only SQL guard rails ---------------------------------------------

SQL_MAX_ROWS = _env_int("MCP_CONNECT_SQL_MAX_ROWS", 200)
SQL_TIMEOUT_SECONDS = _env_float("MCP_CONNECT_SQL_TIMEOUT_S", 5.0)

# --- Least-privilege scopes / allowlist -------------------------------------
#
# A tool only runs if every scope it declares is present in the server's
# *granted* scope set. This lets an operator ship the same code to different
# deployments and simply narrow MCP_CONNECT_GRANTED_SCOPES, e.g. a
# read-only analyst deployment never grants "crm:write".
_DEFAULT_GRANTED_SCOPES = "data:read,docs:read,crm:read"


def granted_scopes() -> frozenset[str]:
    raw = os.environ.get("MCP_CONNECT_GRANTED_SCOPES", _DEFAULT_GRANTED_SCOPES)
    return frozenset(s.strip() for s in raw.split(",") if s.strip())


SCOPES_FILE = _env_path("MCP_CONNECT_SCOPES_FILE", _REPO_ROOT / "config" / "scopes.yaml")


def tool_allowlist() -> frozenset[str] | None:
    """Optional hard allowlist of tool *names*, independent of scopes.

    None means "no additional restriction beyond scopes" -- the usual case.
    Set MCP_CONNECT_ALLOWED_TOOLS="sql_query,search_docs" to expose only a
    specific subset of tools regardless of what scopes are granted.
    """
    raw = os.environ.get("MCP_CONNECT_ALLOWED_TOOLS")
    if raw is None:
        return None
    return frozenset(t.strip() for t in raw.split(",") if t.strip())


# --- Audit logging -----------------------------------------------------------

# Audit records are always emitted as structured JSON to stderr (never
# stdout -- stdout is the MCP stdio transport's wire format). Optionally also
# append them to a file for shipping to a SIEM.
AUDIT_LOG_FILE = os.environ.get("MCP_CONNECT_AUDIT_LOG_FILE")

# --- HTTP transport ----------------------------------------------------------

HTTP_HOST = os.environ.get("MCP_CONNECT_HTTP_HOST", "127.0.0.1")
HTTP_PORT = _env_int("MCP_CONNECT_HTTP_PORT", 8080)
HTTP_STATELESS = _env_bool("MCP_CONNECT_HTTP_STATELESS", False)
