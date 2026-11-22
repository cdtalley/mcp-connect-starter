"""Builds the bundled SQLite demo database.

Everything here is synthetic, deterministic, and fictional -- no real
customer data, no network calls, no external accounts. The seed is
idempotent: `ensure_demo_database()` is a no-op if the file already exists,
so importing the server repeatedly (tests, reloads) never re-seeds.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    company TEXT NOT NULL,
    segment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    amount_usd REAL NOT NULL
);

CREATE TABLE deals (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    value_usd REAL NOT NULL,
    close_date TEXT,
    owner TEXT NOT NULL
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_deals_customer ON deals(customer_id);
"""

# (id, name, email, phone, company, segment, created_at)
_CUSTOMERS = [
    (1, "Priya Nakamura", "priya.nakamura@brightloop.io", "415-555-0132", "BrightLoop", "mid-market", "2023-02-14"),
    (2, "Marcus Oduya", "marcus.oduya@fernhollow.com", "312-555-0198", "Fernhollow Foods", "enterprise", "2022-11-03"),
    (3, "Elena Vasquez", "elena.vasquez@triskeleworks.com", "646-555-0111", "Triskele Works", "smb", "2023-06-21"),
    (4, "Tomás Reyes", "tomas.reyes@brightloop.io", "415-555-0177", "BrightLoop", "mid-market", "2023-02-15"),
    (5, "Hannah Lindqvist", "hannah.lindqvist@northfjord.se", "212-555-0144", "Northfjord Analytics", "enterprise", "2021-09-30"),
    (6, "Dae-Jung Park", "dae-jung.park@quietharbor.com", "503-555-0166", "Quiet Harbor Logistics", "smb", "2023-08-09"),
    (7, "Sofia Moretti", "sofia.moretti@fernhollow.com", "312-555-0120", "Fernhollow Foods", "enterprise", "2022-11-04"),
    (8, "Liam O'Connell", "liam.oconnell@cobaltreef.com", "617-555-0155", "Cobalt Reef Robotics", "mid-market", "2023-04-18"),
    (9, "Aditi Rao", "aditi.rao@northfjord.se", "212-555-0188", "Northfjord Analytics", "enterprise", "2021-10-02"),
    (10, "Benedikt Weiss", "benedikt.weiss@triskeleworks.com", "646-555-0133", "Triskele Works", "smb", "2023-06-22"),
    (11, "Nadia Ferreira", "nadia.ferreira@quietharbor.com", "503-555-0171", "Quiet Harbor Logistics", "smb", "2023-08-10"),
    (12, "Owen Fitzgerald", "owen.fitzgerald@cobaltreef.com", "617-555-0199", "Cobalt Reef Robotics", "mid-market", "2023-04-19"),
]

# (id, customer_id, order_date, status, amount_usd)
_ORDERS = [
    (1, 1, "2023-03-01", "fulfilled", 4200.00),
    (2, 1, "2023-05-12", "fulfilled", 1899.50),
    (3, 2, "2022-12-01", "fulfilled", 18200.00),
    (4, 2, "2023-04-15", "fulfilled", 22650.00),
    (5, 2, "2023-09-02", "pending", 9800.00),
    (6, 3, "2023-07-04", "fulfilled", 760.00),
    (7, 3, "2023-10-19", "refunded", 760.00),
    (8, 4, "2023-03-02", "fulfilled", 3100.00),
    (9, 5, "2021-10-15", "fulfilled", 41500.00),
    (10, 5, "2022-06-01", "fulfilled", 38950.00),
    (11, 5, "2023-07-30", "fulfilled", 52300.00),
    (12, 6, "2023-08-20", "fulfilled", 540.00),
    (13, 7, "2022-12-05", "fulfilled", 15400.00),
    (14, 7, "2023-06-11", "fulfilled", 19875.00),
    (15, 8, "2023-05-01", "fulfilled", 6750.00),
    (16, 8, "2023-11-02", "pending", 7200.00),
    (17, 9, "2021-11-01", "fulfilled", 29800.00),
    (18, 9, "2023-02-14", "fulfilled", 33150.00),
    (19, 10, "2023-07-01", "fulfilled", 890.00),
    (20, 11, "2023-08-15", "fulfilled", 620.00),
    (21, 12, "2023-05-05", "fulfilled", 5100.00),
    (22, 12, "2023-09-18", "cancelled", 4800.00),
]

# (id, customer_id, name, stage, value_usd, close_date, owner)
_DEALS = [
    (1, 1, "BrightLoop - Q3 expansion", "negotiation", 24000.00, "2024-01-15", "Jess Kim"),
    (2, 2, "Fernhollow - annual renewal", "closed_won", 95000.00, "2023-12-01", "Jess Kim"),
    (3, 3, "Triskele - starter plan", "prospecting", 3600.00, None, "Marco Diaz"),
    (4, 5, "Northfjord - enterprise upgrade", "closed_won", 180000.00, "2023-11-20", "Jess Kim"),
    (5, 6, "Quiet Harbor - pilot", "qualification", 7200.00, None, "Marco Diaz"),
    (6, 7, "Fernhollow - new region rollout", "negotiation", 62000.00, "2024-02-01", "Jess Kim"),
    (7, 8, "Cobalt Reef - robotics add-on", "closed_lost", 15000.00, "2023-10-05", "Marco Diaz"),
    (8, 9, "Northfjord - data warehouse", "closed_won", 210000.00, "2023-09-14", "Jess Kim"),
    (9, 10, "Triskele - upsell", "qualification", 5400.00, None, "Marco Diaz"),
    (10, 11, "Quiet Harbor - fleet module", "negotiation", 18500.00, "2024-01-30", "Marco Diaz"),
    (11, 12, "Cobalt Reef - support contract", "closed_won", 9600.00, "2023-08-22", "Marco Diaz"),
    (12, 4, "BrightLoop - analytics add-on", "prospecting", 12000.00, None, "Jess Kim"),
]


def ensure_demo_database(path: Path, *, force: bool = False) -> None:
    """Create and seed the demo SQLite database at `path` if it doesn't exist."""
    path = Path(path)
    if path.exists() and not force:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    if force and path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT INTO customers (id, name, email, phone, company, segment, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            _CUSTOMERS,
        )
        conn.executemany(
            "INSERT INTO orders (id, customer_id, order_date, status, amount_usd) VALUES (?, ?, ?, ?, ?)",
            _ORDERS,
        )
        conn.executemany(
            "INSERT INTO deals (id, customer_id, name, stage, value_usd, close_date, owner) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            _DEALS,
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    """CLI entry point: `python -m mcp_connect_starter.seed_data [--force] [path]`."""
    import argparse

    from mcp_connect_starter import config

    parser = argparse.ArgumentParser(description="Seed the bundled MCP Connect demo database.")
    parser.add_argument("path", nargs="?", default=str(config.SQLITE_DB_PATH))
    parser.add_argument("--force", action="store_true", help="Overwrite an existing database file.")
    args = parser.parse_args()

    ensure_demo_database(Path(args.path), force=args.force)
    print(f"Seeded demo database at {args.path}")  # noqa: T201


if __name__ == "__main__":
    main()
