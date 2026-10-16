# Future roadmap (not implemented)

Ordered by value/risk. None of these is required for the first deployment.

1. **Delivery feedback** - parse bounce (NDR) messages from the `it@` mailbox (IMAP) to turn `accepted` into `bounced` where known; optional tracking-free "read" is out of scope.
2. **Self-service account security** - password change, forced reset on first login, MFA (TOTP), optional SSO.
3. **Employee-facing portal** - employees sign in to read notices and download linked attachments (enables `ATTACHMENT_MODE=link` as the default).
4. **Worker hardening** - heartbeat table + health endpoint, graceful drain, multi-worker soak test on PostgreSQL, metrics (Prometheus) and alert on `failed/unknown`.
5. **Templates** - multiple templates per category, per-template preview, logo upload (only approved assets; no UPS branding).
6. **Emergency stop** - cancel all `pending` jobs of a queued notice (today: disable broadcasting to pause, then retry/leave).
7. **Attachments lifecycle** - purge files of cancelled/old notices, antivirus scan (ClamAV container).
8. **n8n or other automation** - consume the same `email_jobs` outbox or call the REST API with a service account; keep `mailer.get_mailer()` as the only send path (ADR-004).
9. **Redis/Celery** - only if volume exceeds what the DB outbox sustains (currently a few hundred mails/day).
10. **Directory sync** - scheduled import from HR source; department heads and per-department editors.
11. **Localisation** - Nepali UI strings and Nepali (BS) calendar display.
12. **Retention** - archive/purge policy for `email_attempts` and `audit_logs`.
