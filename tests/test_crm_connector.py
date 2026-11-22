from __future__ import annotations

from pathlib import Path

import pytest

from mcp_connect_starter.connectors.crm.mock_adapter import MockCRMAdapter


def test_list_tickets_filters_by_status(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    open_tickets = adapter.list_tickets(status="open")
    assert all(t.status == "open" for t in open_tickets)
    assert any(t.id == "TCK-1" for t in open_tickets)


def test_list_tickets_respects_limit(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    assert len(adapter.list_tickets(limit=1)) == 1


def test_get_ticket_returns_match(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    ticket = adapter.get_ticket("TCK-1")
    assert ticket.subject == "Login broken"


def test_get_ticket_unknown_id_raises(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    with pytest.raises(LookupError):
        adapter.get_ticket("TCK-does-not-exist")


def test_search_contacts_matches_company_case_insensitively(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    hits = adapter.search_contacts("ACME")
    assert len(hits) == 1
    assert hits[0].id == "CON-1"


def test_search_contacts_no_match_returns_empty(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    assert adapter.search_contacts("nonexistent-co") == []


def test_add_ticket_comment_appends_and_persists_in_memory(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    updated = adapter.add_ticket_comment("TCK-1", author="Agent Smith", body="Looking into it.")

    assert len(updated.comments) == 1
    assert updated.comments[0].body == "Looking into it."
    assert adapter.get_ticket("TCK-1").comments[0].author == "Agent Smith"


def test_add_ticket_comment_unknown_id_raises(crm_fixture_path: Path) -> None:
    adapter = MockCRMAdapter(crm_fixture_path)
    with pytest.raises(LookupError):
        adapter.add_ticket_comment("TCK-does-not-exist", author="x", body="y")
