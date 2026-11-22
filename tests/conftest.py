from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_connect_starter.seed_data import ensure_demo_database


@pytest.fixture
def demo_db_path(tmp_path: Path) -> Path:
    path = tmp_path / "demo.sqlite3"
    ensure_demo_database(path)
    return path


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "refund-policy.md").write_text(
        "# Refund Policy\n\n"
        "Customers get a full refund within 30 days of purchase. Refund "
        "requests after that window are prorated. Contact billing at "
        "refunds@example.com for help with a refund.\n"
    )
    (docs / "security.md").write_text(
        "# Security\n\n"
        "We redact PII such as emails and phone numbers like 415-555-0132 "
        "before returning tool output.\n"
    )
    nested = docs / "nested"
    nested.mkdir()
    (nested / "onboarding.md").write_text("# Onboarding\n\nJust a nested doc about getting started.\n")
    return docs


_CRM_FIXTURE = {
    "contacts": [
        {
            "id": "CON-1",
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "212-555-0100",
            "company": "Acme",
            "role": "Engineer",
        },
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
        },
        {
            "id": "TCK-2",
            "subject": "Billing question",
            "status": "closed",
            "priority": "P3",
            "requester_email": "ada@example.com",
            "assignee": "Support: Bo",
            "created_at": "2023-12-01T00:00:00Z",
            "updated_at": "2023-12-02T00:00:00Z",
            "description": "Question about an invoice.",
            "comments": [],
        },
    ],
}


@pytest.fixture
def crm_fixture_path(tmp_path: Path) -> Path:
    path = tmp_path / "crm_mock.json"
    path.write_text(json.dumps(_CRM_FIXTURE))
    return path
