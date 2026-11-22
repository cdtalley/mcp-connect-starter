# Security FAQ

_Last updated: 2023-11-15_

Sample knowledge-base article bundled with the MCP Connect starter.

## Where is customer data stored?

Production data is stored in region-pinned managed databases. Backups are
encrypted at rest and retained for 35 days.

## Do you support SSO?

Yes. SAML 2.0 and OIDC are supported on the Enterprise plan. See the SSO
setup guide for configuration steps with Okta, Azure AD, and Google
Workspace.

## What is your incident response process?

All production incidents follow a documented runbook with a defined
severity scale (P1-P4), a named incident commander, and a post-incident
review within 5 business days for P1/P2 incidents. See
`incident-runbook.md` in this same knowledge base.

## How do you handle PII?

Personally identifiable information is scoped to the minimum needed for
the product to function, access is role-gated, and all access is logged.
Any AI assistant or automated tool reading from internal systems should
redact PII (emails, phone numbers, SSNs, card numbers) before returning it
in a response -- which is exactly what this server's redaction layer does
by default on every tool call.

## Can support agents see billing details?

Support agents can see redacted billing summaries (plan, status, last 4
digits of card) but not full card numbers, which are tokenized by the
payment processor and never stored in plaintext.
