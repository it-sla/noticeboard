# ADR-002: Email delivery via Hostinger SMTP, one message per recipient

Status: accepted (2026-10-15)

## Decision
- Send through the existing mailbox `it@gohimalaya.travel` with `smtplib` (stdlib; SSL on 465 by default, STARTTLS optional). All
  connection parameters and rate limits come from environment variables; nothing is assumed about Hostinger plan limits.
- One SMTP transaction per recipient; `To` holds only that employee (no CC/BCC leakage, per-recipient status).
- Each message has a plain-text part and a responsive HTML part; attachments are attached by default.
- Outcomes are classified transient / permanent / ambiguous. Ambiguous ones are stored as `unknown` and never retried automatically.
- "Accepted by SMTP" is the strongest claim the system makes; it is never described as delivered.
- Safety gates: `EMAIL_MODE=dry_run` default, `broadcast_enabled` off by default, single-address test send, confirmation with
  matching recipient count.
- No UPS API/website automation; no n8n in v1.

## Consequences
+ Exact per-recipient audit trail; simple retry semantics; no provider SDK.
− Many short SMTP connections (a connection per message). Acceptable for the volume; a persistent connection per batch is a
  later optimisation if the provider throttles connection rates.
− No bounce/read tracking until mailbox parsing is added (roadmap).

## Alternatives
Transactional email API (SES/SendGrid): better deliverability and webhooks but new vendor/cost, contradicts "use the existing Hostinger mailbox".
BCC batches: leaks nothing but loses per-recipient status and breaks on one bad address.
