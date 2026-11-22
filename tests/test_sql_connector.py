from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from mcp_connect_starter.connectors import sql_connector
from mcp_connect_starter.security import SQLSecurityError


def test_list_sql_tables_includes_demo_tables(demo_db_path: Path) -> None:
    tables = sql_connector.list_sql_tables(demo_db_path)
    names = {t.name for t in tables}
    assert {"customers", "orders", "deals"} <= names

    customers = next(t for t in tables if t.name == "customers")
    assert {"id", "name", "email", "phone", "company"} <= set(customers.columns)


def test_sql_query_returns_rows_and_columns(demo_db_path: Path) -> None:
    result = sql_connector.sql_query(
        "SELECT id, name, email FROM customers ORDER BY id LIMIT 3", db_path=demo_db_path
    )
    assert result.columns == ["id", "name", "email"]
    assert result.row_count == 3
    assert not result.truncated


def test_sql_query_redacts_pii_at_the_source(demo_db_path: Path) -> None:
    result = sql_connector.sql_query("SELECT email, phone FROM customers LIMIT 1", db_path=demo_db_path)
    row = result.rows[0]
    assert row["email"] == "[REDACTED_EMAIL]"
    assert row["phone"] == "[REDACTED_PHONE]"


def test_sql_query_enforces_row_limit(demo_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_connect_starter.config.SQL_MAX_ROWS", 2)
    result = sql_connector.sql_query("SELECT * FROM orders", db_path=demo_db_path)
    assert result.row_count == 2
    assert result.truncated is True


def test_sql_query_uses_bound_parameters(demo_db_path: Path) -> None:
    result = sql_connector.sql_query(
        "SELECT name FROM customers WHERE id = ?", params=[1], db_path=demo_db_path
    )
    assert result.row_count == 1


def test_sql_query_rejects_write_statements(demo_db_path: Path) -> None:
    for statement in ("DELETE FROM customers", "DROP TABLE customers", "UPDATE customers SET name='x'"):
        with pytest.raises(SQLSecurityError):
            sql_connector.sql_query(statement, db_path=demo_db_path)


def test_connection_is_read_only_even_if_the_text_guard_were_bypassed(demo_db_path: Path) -> None:
    # Defense in depth: the connection is opened via a read-only SQLite URI
    # with PRAGMA query_only = ON, so a write fails independently of
    # `ensure_read_only_sql`.
    conn = sql_connector._connect(demo_db_path)
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM customers")
    finally:
        conn.close()
