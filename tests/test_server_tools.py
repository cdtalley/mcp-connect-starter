"""End-to-end tests that exercise tools through the real FastMCP server,
the same way an MCP client would call them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_connect_starter import config, security
from mcp_connect_starter.server import build_server


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "hello.md").write_text(
        "# Hello\n\nThis is a sample doc about onboarding new engineers.\n"
    )

    crm_path = tmp_path / "crm_mock.json"
    crm_path.write_text(
        json.dumps(
            {
                "contacts": [
                    {
                        "id": "CON-1",
                        "name": "Ada Lovelace",
                        "email": "ada@example.com",
                        "phone": "212-555-0100",
                        "company": "Acme",
                        "role": "Engineer",
                    }
                ],
                "tickets": [
                    {
                        "id": "TCK-1",
                        "subject": "Login broken",
                        "status": "open",
                        "priority": "P1",
                        "requester_email": "ada@example.com",
                        "assignee": "Support: Bo",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "description": "Can't log in.",
                        "comments": [],
                    }
                ],
            }
        )
    )

    monkeypatch.setattr(config, "SQLITE_DB_PATH", tmp_path / "demo.sqlite3")
    monkeypatch.setattr(config, "DOCS_DIR", docs_dir)
    monkeypatch.setattr(config, "CRM_FIXTURE_PATH", crm_path)
    monkeypatch.setattr(config, "SCOPES_FILE", Path("/nonexistent/scopes.yaml"))
    monkeypatch.setattr(config, "granted_scopes", lambda: frozenset({"data:read", "docs:read", "crm:read"}))
    monkeypatch.setattr(config, "tool_allowlist", lambda: None)
    security.reset_policy_cache()

    return build_server()


def _unwrap(result):
    """`FastMCP.call_tool(convert_result=True)` returns a
    `(content_blocks, structured_result)` tuple for a structured tool.
    `structured_result` is either the tool's dict directly, or
    `{"result": [...]}` when the tool returns a bare list. Normalize both
    to "just the data" for assertions.
    """
    if isinstance(result, tuple) and len(result) == 2:
        _content, structured = result
        if structured is not None:
            if set(structured.keys()) == {"result"}:
                return structured["result"]
            return structured
    if isinstance(result, dict):
        return result
    # Fallback: plain content blocks, concatenate text and try JSON.
    text = "".join(getattr(block, "text", "") for block in result)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


async def test_list_sql_tables_tool(server) -> None:
    result = await server.call_tool("list_sql_tables", {})
    data = _unwrap(result)
    names = {t["name"] for t in data} if isinstance(data, list) else set()
    assert {"customers", "orders", "deals"} <= names


async def test_sql_query_tool_redacts_pii(server) -> None:
    result = await server.call_tool(
        "sql_query", {"sql": "SELECT email FROM customers WHERE id = 1"}
    )
    data = _unwrap(result)
    rows = data["rows"] if isinstance(data, dict) else data
    assert rows[0]["email"] == "[REDACTED_EMAIL]"


async def test_sql_query_tool_rejects_write(server) -> None:
    with pytest.raises(Exception, match="(?i)select|read-only|disallowed"):
        await server.call_tool("sql_query", {"sql": "DELETE FROM customers"})


async def test_search_docs_tool_finds_sample_doc(server) -> None:
    result = await server.call_tool("search_docs", {"query": "onboarding"})
    data = _unwrap(result)
    paths = {hit["path"] for hit in data} if isinstance(data, list) else set()
    assert "hello.md" in paths


async def test_read_doc_tool_returns_content(server) -> None:
    result = await server.call_tool("read_doc", {"path": "hello.md"})
    data = _unwrap(result)
    content = data["content"] if isinstance(data, dict) else data
    assert "onboarding" in content.lower()


async def test_list_tickets_tool(server) -> None:
    result = await server.call_tool("list_tickets", {})
    data = _unwrap(result)
    ticket_ids = {t["id"] for t in data} if isinstance(data, list) else set()
    assert "TCK-1" in ticket_ids


async def test_get_ticket_tool(server) -> None:
    result = await server.call_tool("get_ticket", {"ticket_id": "TCK-1"})
    data = _unwrap(result)
    assert data["subject"] == "Login broken"


async def test_add_ticket_comment_is_denied_by_default(server) -> None:
    # crm:write is not in the granted scope set, so this must be denied
    # even though the ticket itself exists. FastMCP wraps the underlying
    # ToolAccessError in a ToolError, preserving its message.
    with pytest.raises(ToolError, match="crm:write"):
        await server.call_tool(
            "add_ticket_comment",
            {"ticket_id": "TCK-1", "author": "someone", "body": "hi"},
        )
