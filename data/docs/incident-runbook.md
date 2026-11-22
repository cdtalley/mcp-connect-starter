# Incident Response Runbook

_Last updated: 2023-09-30_

Sample knowledge-base article bundled with the MCP Connect starter.

## Severity levels

- **P1** - full outage or data loss risk. Page immediately, incident
  commander assigned within 5 minutes.
- **P2** - significant degradation affecting many customers. Page during
  business hours, escalate after hours if customer-visible for >30 minutes.
- **P3** - partial degradation, workaround available.
- **P4** - cosmetic or low-impact issue.

## First 15 minutes (P1/P2)

1. Acknowledge the page and open an incident channel.
2. Assign an incident commander (IC) and a scribe.
3. Post an initial status update to the status page within 15 minutes,
   even if it just says "investigating."
4. Identify whether the cause is a recent deploy; if so, prepare a
   rollback.

## Communication cadence

- P1: status update every 30 minutes until resolved.
- P2: status update every hour until resolved.
- All-clear message posted once the fix is verified in production for at
  least 15 minutes.

## Post-incident

- P1/P2 incidents require a written post-incident review within 5 business
  days: timeline, root cause, customer impact, and follow-up action items
  with owners and due dates.
