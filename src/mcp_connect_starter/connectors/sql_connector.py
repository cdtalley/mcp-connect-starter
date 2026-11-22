"""Read-only SQL connector over the bundled SQLite demo database.

Security properties (see README "Security model" for the full write-up):

- The connection itself is opened read-only (SQLite URI `mode=ro`) with
  `PRAGMA query_only = ON` as a second, independent layer of defense.
- `security.ensure_read_only_sql` rejects anything that isn't a single
  SELECT / WITH...SELECT statement *before* it reaches SQLite.
- Callers must use `?` placeholders and pass values via `params` --
  never format values into the `sql` string.
- Results are capped at `config.SQL_MAX_ROWS`, and a progress-handler based
  timeout bounds how long a single query may run.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_connect_starter import config
from mcp_connect_starter.redaction import redact_any
from mcp_connect_starter.security import ensure_read_only_sql
from mcp_connect_starter.seed_data import ensure_demo_database


class SqlTableInfo(BaseModel):
    name: str
    columns: list[str]


class SqlQueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = Field(
        description="True if more rows matched than were returned; narrow the query or paginate."
    )


def _connect(db_path: Path) -> sqlite3.Connection:
    ensure_demo_database(db_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON;")
    return conn


def _install_timeout(conn: sqlite3.Connection, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds

    def handler() -> int:
        return 1 if time.monotonic() > deadline else 0

    # Called by SQLite every N virtual machine instructions; returning a
    # non-zero value aborts the query with sqlite3.OperationalError.
    conn.set_progress_handler(handler, 1000)


def list_sql_tables(db_path: Path | None = None) -> list[SqlTableInfo]:
    """List tables and their columns in the demo database."""
    path = db_path or config.SQLITE_DB_PATH
    conn = _connect(path)
    try:
        table_names = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        tables = []
        for name in table_names:
            # `name` comes from sqlite_master, not from caller input, so this
            # is not a SQL-injection vector despite the f-string.
            columns = [row["name"] for row in conn.execute(f"PRAGMA table_info('{name}')")]
            tables.append(SqlTableInfo(name=name, columns=columns))
        return tables
    finally:
        conn.close()


def sql_query(
    sql: str,
    params: list[Any] | None = None,
    *,
    db_path: Path | None = None,
) -> SqlQueryResult:
    """Run a read-only SELECT query against the demo database."""
    ensure_read_only_sql(sql)

    path = db_path or config.SQLITE_DB_PATH
    conn = _connect(path)
    try:
        _install_timeout(conn, config.SQL_TIMEOUT_SECONDS)
        cursor = conn.execute(sql, params or [])
        max_rows = config.SQL_MAX_ROWS
        fetched = cursor.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = [dict(row) for row in fetched[:max_rows]]
        columns = [d[0] for d in cursor.description] if cursor.description else []
        # Redact at the source as well as in the generic tool-output
        # filter -- belt and suspenders for the data most likely to carry
        # real PII (customer emails/phones).
        rows = redact_any(rows)
        return SqlQueryResult(columns=columns, rows=rows, row_count=len(rows), truncated=truncated)
    finally:
        conn.close()
