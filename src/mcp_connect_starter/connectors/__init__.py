"""Example connectors bundled with MCP Connect Starter.

- `sql_connector`: read-only SQL over a bundled SQLite demo database.
- `docs_connector`: search/read over a bundled folder of markdown docs.
- `crm`: a ticketing/CRM-style connector with a clear adapter interface
  (`crm.base.CRMAdapter`) so a real system (HubSpot, Salesforce, Jira, ...)
  can be swapped in without touching the server wiring.
"""
