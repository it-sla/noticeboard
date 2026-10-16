# Email automation

## Modes and gates (all must allow before a real email leaves the server)
1. `EMAIL_MODE=smtp` in the server environment (default `dry_run`: the worker records `dry_run` and never opens a socket).
2. A SUPER_ADMIN enabled broadcasting in Settings (`app_settings.broadcast_enabled`, default **off**). While off, publish returns
   409 `broadcast_disabled`, scheduled notices revert to draft at fire time, and the worker claims nothing (acts as a pause switch).
3. An ADMIN published a notice with explicit confirmation and the matching recipient count.
Test sends (`POST /email/test`) obey gate 1 only, go to **one** address, bypass the outbox, and are limited per user per hour.

## Hostinger SMTP configuration (all overridable; verify against your plan)
```
SMTP_HOST=smtp.hostinger.com   SMTP_PORT=465   SMTP_USE_SSL=true
SMTP_USERNAME=it@gohimalaya.travel   SMTP_PASSWORD=<set on the server only>   SMTP_FROM_EMAIL=it@gohimalaya.travel
SMTP_STARTTLS=false   (set true with SMTP_USE_SSL=false and port 587 if your plan requires STARTTLS)
EMAIL_RATE_PER_MINUTE=20   EMAIL_RATE_PER_DAY=300   # placeholders - set from the verified plan limits
```
The password is never shown by the API or UI (`smtp_password_configured` only). Use Settings → "Test SMTP connection" (connect +
authenticate, sends nothing) before the first live test email.

## Message construction
One `EmailMessage` per recipient (`To` contains exactly that employee; no CC/BCC, no shared list), multipart/alternative
(plain text + responsive HTML from `templates/notice_email.html`), UTF-8 (Nepali verified), unique `Message-ID`. Subject/title
CR/LF stripped; header injection raises and fails only that recipient. Attachments: `ATTACHMENT_MODE=attach` (files attached,
total ≤ `ATTACHMENT_MAX_TOTAL_MB`) or `link` (login-protected `/api/attachments/{id}/download`; no public URLs are created).

## Job states
| Status | Meaning | Next |
|---|---|---|
| `pending` | queued or waiting for backoff | worker claims it |
| `sending` | claimed by a worker | → outcome, or `unknown` if the worker dies |
| `accepted` | SMTP server accepted the message (**not** proof of inbox delivery, bounce or read) | terminal |
| `failed` | permanent error or retries exhausted | admin may retry |
| `unknown` | connection lost after the message may have been handed over / worker died | admin reconciles; retry needs explicit opt-in |
| `dry_run` | processed in dry-run mode | terminal |

## Failure classification (`services/mailer.py`)
| Situation | Class | Action |
|---|---|---|
| connect/TLS/timeout **before** sending, 4xx replies | transient | retry with backoff `60s·2^(n-1)` (cap 1h), max `EMAIL_MAX_ATTEMPTS` (4) |
| authentication failure, 5xx replies, recipients refused (5xx) | permanent | `failed`, no retry |
| drop/timeout during `send_message` | ambiguous | `unknown`, **no automatic retry** |
| missing attachment file, rendering error | permanent | `failed` |

## Idempotency and duplicates
Publishing is one transaction guarded by a row lock and status check; unique keys on `email_jobs` make a second job impossible.
Retrying a `failed` job reuses the same row (attempt history kept, `max_attempts` extended). A message may still be duplicated only
in the `unknown` case when an admin chooses to retry; the UI warns before that.

## Expiry digest (admins only)
The worker sends one internal email per day (after 08:00 Asia/Kathmandu) to all active ADMIN/SUPER_ADMIN users plus the extra addresses in
Settings. It lists items that crossed a reminder threshold (default 60/30/14/7/1 days) for the first time, items that just became overdue,
and all still-overdue items on Mondays. A threshold is recorded in `expiry_reminders` only after the SMTP server accepts the mail; a failed
send is retried after an hour. Dry-run mode records nothing. It does not use the notice outbox or the broadcast switch (it never goes to
employees) but needs `EMAIL_MODE=smtp` and "Send expiry reminder emails" enabled.

## Rate limits
Per cycle the worker computes `min(per_minute − accepted-or-sending in last 60s, per_day − same in last 24h, 50)` and claims that many.
Counts come from `email_attempts`, so they survive restarts. Verify the real Hostinger limits and set the env vars before going live.

## Reconciliation
Failed/unknown rows appear on the Dashboard and Email History (`status=failed|unknown`). For `unknown`, check the Sent folder / recipient
before choosing "Retry…". Bounce handling (parsing NDRs in the mailbox) is not implemented.
