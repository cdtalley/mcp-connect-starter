"""Adapter interface for ticketing/CRM-style connectors.

This starter ships `mock_adapter.MockCRMAdapter`, backed by a bundled JSON
fixture, so the server runs with zero external accounts. To connect a real
system -- HubSpot, Salesforce, Jira, Zendesk, a Google Sheet, ... -- write a
new class that implements `CRMAdapter` against that system's API and
construct it in `server.py` instead of `MockCRMAdapter`. Nothing else in the
server needs to change, because every tool talks to the adapter only
through this interface.

A real adapter should:
  - Read its credentials from environment variables only (e.g.
    `HUBSPOT_API_KEY`), never from a committed file.
  - Raise `LookupError` for an unknown ticket/contact id, matching the
    contract `get_ticket` / `add_ticket_comment` already follow here.
  - Return the same `Ticket` / `Contact` models (or add fields with
    defaults) so the server's tool schemas don't change underneath callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class Contact(BaseModel):
    id: str
    name: str
    email: str
    phone: str | None = None
    company: str
    role: str | None = None


class TicketComment(BaseModel):
    author: str
    created_at: str
    body: str


class Ticket(BaseModel):
    id: str
    subject: str
    status: str
    priority: str
    requester_email: str
    assignee: str | None = None
    created_at: str
    updated_at: str
    description: str
    comments: list[TicketComment] = []


class CRMAdapter(ABC):
    """Minimal surface a ticketing/CRM connector needs to expose as MCP tools."""

    @abstractmethod
    def list_tickets(self, status: str | None = None, limit: int = 20) -> list[Ticket]:
        """Return tickets, newest first, optionally filtered by status."""

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Ticket:
        """Return one ticket including its comment thread. Raises LookupError if unknown."""

    @abstractmethod
    def search_contacts(self, query: str, limit: int = 10) -> list[Contact]:
        """Return contacts matching `query` against name, email, or company."""

    @abstractmethod
    def add_ticket_comment(self, ticket_id: str, author: str, body: str) -> Ticket:
        """Append a comment to a ticket and return the updated ticket.

        This is the one *write* operation in the starter, and it is wired
        up behind the `crm:write` scope, disabled by default in
        `config/scopes.yaml`. A real adapter should treat this the same
        way: writes are exactly the operations that most need least-
        privilege gating.
        """
