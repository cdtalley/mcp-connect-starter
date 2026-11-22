from __future__ import annotations

import pytest

from mcp_connect_starter.security import SQLSecurityError, ensure_read_only_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM customers",
        "select id, name from customers where id = ?",
        "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent",
        "SELECT * FROM customers;",
        "SELECT * FROM customers -- trailing line comment is fine\n",
        "SELECT * FROM customers -- ; this is not a real second statement\n",
    ],
)
def test_allows_read_only_statements(sql: str) -> None:
    ensure_read_only_sql(sql)  # should not raise


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "   ",
        "DROP TABLE customers",
        "DELETE FROM customers",
        "UPDATE customers SET name = 'x'",
        "INSERT INTO customers (id) VALUES (1)",
        "REPLACE INTO customers (id) VALUES (1)",
        "ATTACH DATABASE '/tmp/evil.db' AS evil",
        "PRAGMA writable_schema = 1",
        "VACUUM",
        "SELECT * FROM customers; DROP TABLE customers;",
        "SELECT 1; SELECT 2",
        "-- a comment that is not a statement at all",
        "EXPLAIN SELECT * FROM customers",
    ],
)
def test_rejects_unsafe_statements(sql: str) -> None:
    with pytest.raises(SQLSecurityError):
        ensure_read_only_sql(sql)
