"""Builds the MCP Connect Starter server: registers every tool behind
`security.secure_tool` (scopes, allowlist, audit log, output redaction).

Transports:
  - stdio, for Claude Desktop / Cursor (`mcp.run(transport="stdio")`).
  - streamable HTTP, for remote use (`mcp.run(transport="streamable-http")`).

See `cli.py` for the command-line entry point that picks a transport.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_connect_starter import config
from mcp_connect_starter.connectors import docs_connector, sql_connector
from mcp_connect_starter.connectors.crm.base import Contact, CRMAdapter, Ticket
from mcp_connect_starter.connectors.crm.mock_adapter import MockCRMAdapter
from mcp_connect_starter.security import secure_tool
from mcp_connect_starter.seed_data import ensure_demo_database

INSTRUCTIONS = (
    "MCP Connect Starter exposes three connectors, all read-only unless the "
    "deployment explicitly grants a write scope: sql_query / list_sql_tables "
    "over a sample customers/orders/deals SQLite database, search_docs / "
    "read_doc over a markdown knowledge base, and list_tickets / get_ticket / "
    "search_contacts over a mock CRM. Call list_sql_tables before writing ad "
    "hoc SQL, and search_docs before read_doc. Every tool call is audit "
    "logged and PII (emails, phone numbers, SSNs, card numbers) is redacted "
    "from tool output."
)


def _build_crm_adapter() -> CRMAdapter:
    """Swap this for a real adapter (HubSpot/Salesforce/Jira/...) in production.

    See connectors/crm/base.py for the interface every adapter implements.
    """
    return MockCRMAdapter(config.CRM_FIXTURE_PATH)


def build_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    """Construct a fresh, fully-wired FastMCP server instance."""
    ensure_demo_database(config.SQLITE_DB_PATH)

    mcp = FastMCP(
        config.SERVER_NAME,
        instructions=INSTRUCTIONS,
        host=host or config.HTTP_HOST,
        port=port or config.HTTP_PORT,
        stateless_http=config.HTTP_STATELESS,
    )

    crm = _build_crm_adapter()

    # --- SQL connector (read-only) ----------------------------------------

    @mcp.tool()
    @secure_tool("list_sql_tables", scopes=["data:read"])
    def list_sql_tables() -> list[sql_connector.SqlTableInfo]:
        """List the tables and columns available in the demo SQL database."""
        return sql_connector.list_sql_tables()

    @mcp.tool()
    @secure_tool("sql_query", scopes=["data:read"])
    def sql_query(sql: str, params: list[Any] | None = None) -> sql_connector.SqlQueryResult:
        """Run a read-only SQL query against the demo database.

        Only a single SELECT or WITH...SELECT statement is allowed; writes,
        DDL, and multi-statement payloads are rejected before they reach
        SQLite. Use `?` placeholders in `sql` and pass values via `params`
        rather than formatting them into the query text. Results are capped
        at MCP_CONNECT_SQL_MAX_ROWS rows (see `truncated` in the response).
        """
        return sql_connector.sql_query(sql, params)

    # --- Docs / knowledge-base connector -----------------------------------

    @mcp.tool()
    @secure_tool("search_docs", scopes=["docs:read"])
    def search_docs(query: str, limit: int = 5) -> list[docs_connector.DocHit]:
        """Search the bundled markdown knowledge base and return the best-matching documents."""
        return docs_connector.search_docs(query, limit=limit)

    @mcp.tool()
    @secure_tool("read_doc", scopes=["docs:read"])
    def read_doc(path: str) -> docs_connector.DocContent:
        """Read one markdown document by the `path` returned from `search_docs`."""
        return docs_connector.read_doc(path)

    # --- CRM / ticketing connector (mock; swap in a real adapter) ---------

    @mcp.tool()
    @secure_tool("list_tickets", scopes=["crm:read"])
    def list_tickets(status: str | None = None, limit: int = 20) -> list[Ticket]:
        """List support tickets, newest first, optionally filtered by status (open/pending/closed)."""
        return crm.list_tickets(status=status, limit=limit)

    @mcp.tool()
    @secure_tool("get_ticket", scopes=["crm:read"])
    def get_ticket(ticket_id: str) -> Ticket:
        """Get one support ticket by id, including its comment thread."""
        return crm.get_ticket(ticket_id)

    @mcp.tool()
    @secure_tool("search_contacts", scopes=["crm:read"])
    def search_contacts(query: str, limit: int = 10) -> list[Contact]:
        """Search CRM contacts by name, email, or company."""
        return crm.search_contacts(query, limit=limit)

    @mcp.tool()
    @secure_tool("add_ticket_comment", scopes=["crm:write"])
    def add_ticket_comment(ticket_id: str, author: str, body: str) -> Ticket:
        """Add a comment to a ticket and return it updated.

        Disabled by default (see config/scopes.yaml) -- this is the one
        write-capable tool in the starter, gated behind the `crm:write`
        scope to demonstrate least-privilege-by-default.
        """
        return crm.add_ticket_comment(ticket_id, author=author, body=body)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": config.SERVER_NAME})

    return mcp
