"""Zero-account mock CRM/ticketing adapter backed by a bundled JSON fixture.

All data here is synthetic and fictional. Writes via `add_ticket_comment`
are applied in-memory only and do not persist across restarts -- this is a
demo adapter, not a database.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from threading import Lock

from mcp_connect_starter.connectors.crm.base import Contact, CRMAdapter, Ticket, TicketComment


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MockCRMAdapter(CRMAdapter):
    def __init__(self, fixture_path: Path):
        self._fixture_path = Path(fixture_path)
        self._lock = Lock()
        self._contacts: list[Contact] = []
        self._tickets: dict[str, Ticket] = {}
        self._load()

    def _load(self) -> None:
        raw = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        self._contacts = [Contact.model_validate(c) for c in raw.get("contacts", [])]
        self._tickets = {t["id"]: Ticket.model_validate(t) for t in raw.get("tickets", [])}

    def list_tickets(self, status: str | None = None, limit: int = 20) -> list[Ticket]:
        with self._lock:
            tickets = list(self._tickets.values())
        if status:
            tickets = [t for t in tickets if t.status == status]
        tickets.sort(key=lambda t: t.created_at, reverse=True)
        return tickets[: max(0, limit)]

    def get_ticket(self, ticket_id: str) -> Ticket:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise LookupError(f"No such ticket: '{ticket_id}'.")
        return ticket

    def search_contacts(self, query: str, limit: int = 10) -> list[Contact]:
        q = query.lower().strip()
        with self._lock:
            contacts = list(self._contacts)
        if not q:
            return contacts[: max(0, limit)]
        matches = [
            c
            for c in contacts
            if q in c.name.lower() or q in c.email.lower() or q in c.company.lower()
        ]
        return matches[: max(0, limit)]

    def add_ticket_comment(self, ticket_id: str, author: str, body: str) -> Ticket:
        with self._lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                raise LookupError(f"No such ticket: '{ticket_id}'.")
            updated = ticket.model_copy(
                update={
                    "comments": [
                        *ticket.comments,
                        TicketComment(author=author, created_at=_utc_now_iso(), body=body),
                    ],
                    "updated_at": _utc_now_iso(),
                }
            )
            self._tickets[ticket_id] = updated
            return updated
