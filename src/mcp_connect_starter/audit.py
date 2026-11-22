"""Structured audit logging for every tool call.

Audit records are JSON lines so they can be shipped straight to a log
pipeline (Datadog, Splunk, CloudWatch, ...). They are always written to
stderr -- never stdout, since stdout carries the MCP JSON-RPC wire format
when running over the stdio transport and must stay uncontaminated.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from mcp_connect_starter import config

_LOGGER_NAME = "mcp_connect_starter.audit"


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "audit_payload", None)
        if payload is None:
            payload = {"message": record.getMessage()}
        payload.setdefault("logger", record.name)
        payload.setdefault("level", record.levelname)
        return json.dumps(payload, default=str, sort_keys=True)


def _build_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger  # already configured (e.g. re-imported in tests)

    logger.setLevel(logging.INFO)
    logger.propagate = False

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(_JsonLineFormatter())
    logger.addHandler(stderr_handler)

    if config.AUDIT_LOG_FILE:
        file_handler = logging.FileHandler(config.AUDIT_LOG_FILE)
        file_handler.setFormatter(_JsonLineFormatter())
        logger.addHandler(file_handler)

    return logger


_audit_logger = _build_logger()


@dataclass
class AuditRecord:
    """One audit log entry for a single tool invocation."""

    request_id: str
    tool: str
    status: str  # "success" | "error" | "denied"
    duration_ms: float
    required_scopes: list[str] = field(default_factory=list)
    granted_scopes: list[str] = field(default_factory=list)
    arg_keys: list[str] = field(default_factory=list)
    error: str | None = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def emit(record: AuditRecord) -> None:
    """Write one audit record as a JSON line to stderr (and optionally a file)."""
    payload: dict[str, Any] = asdict(record)
    _audit_logger.info("tool_call", extra={"audit_payload": payload})


def get_audit_logger() -> logging.Logger:
    """Expose the underlying logger, mainly so tests can attach a capture handler."""
    return _audit_logger
