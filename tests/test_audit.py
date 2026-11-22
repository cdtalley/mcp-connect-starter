from __future__ import annotations

import json
import logging
import sys

from mcp_connect_starter import audit


def test_emit_writes_one_structured_record() -> None:
    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Capture()
    logger = audit.get_audit_logger()
    logger.addHandler(handler)
    try:
        audit.emit(
            audit.AuditRecord(
                request_id="abc123",
                tool="sql_query",
                status="success",
                duration_ms=12.3,
                required_scopes=["data:read"],
                granted_scopes=["data:read"],
                arg_keys=["sql"],
            )
        )
    finally:
        logger.removeHandler(handler)

    assert len(captured) == 1
    payload = captured[0].audit_payload  # type: ignore[attr-defined]
    assert payload["tool"] == "sql_query"
    assert payload["status"] == "success"
    assert payload["request_id"] == "abc123"
    assert payload["duration_ms"] == 12.3


def test_formatter_produces_parseable_json_line() -> None:
    formatter = audit._JsonLineFormatter()
    record = logging.LogRecord(
        name="mcp_connect_starter.audit",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="tool_call",
        args=None,
        exc_info=None,
    )
    record.audit_payload = {"tool": "demo", "status": "success"}

    line = formatter.format(record)
    parsed = json.loads(line)

    assert parsed["tool"] == "demo"
    assert parsed["level"] == "INFO"


def test_audit_logger_never_writes_to_stdout() -> None:
    # stdout carries the MCP JSON-RPC wire format over the stdio transport;
    # audit logging must never share it.
    for handler in audit.get_audit_logger().handlers:
        stream = getattr(handler, "stream", None)
        assert stream is not sys.stdout
