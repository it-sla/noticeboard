# Requirements and status

Legend: **DONE** implemented + automated test; **PARTIAL** implemented with a stated gap; **UNVERIFIED** implemented but a
needed check could not run here (reason given); **NOT DONE** not implemented. Verified on 2026-10-15 with
`bash scripts/test/run.sh all` (see `PROGRESS.md`).

| Area | Requirement | Status | Notes / tests |
|---|---|---|---|
| A Auth | Secure login, argon2, HttpOnly cookie sessions, logout, protected routes | DONE | `test_auth.py` |
| A | Roles SUPER_ADMIN/ADMIN/NOTICE_EDITOR/VIEWER enforced server-side | DONE | `test_role_matrix`, `test_every_route_requires_authentication` |
| A | Login rate limiting / lockout, session expiry, CSRF, audit of sensitive actions | DONE | lockout + per-IP throttle tested; idle/absolute expiry implemented, expiry itself not unit-tested |
| A | Initial admin bootstrap without default credentials | DONE | `python -m app.cli create-admin` (password from env/prompt) |
| A | Self-service password change / reset email | NOT DONE | Super Admin can reset via Settings → Users |
| B Employees | CRUD, deactivate (history kept), search, department filter | DONE | `test_directory.py` |
| B | CSV/Excel import: preview, duplicates, validation, error report | DONE | CSV + XLSX tested; existing emails skipped, never overwritten |
| C Departments | create/edit/deactivate, counts | DONE | assignment through the employee form/import |
| D Notices | draft/edit/preview/duplicate/archive/search/filter/history | DONE | `test_notices.py` |
| D | Statuses draft/scheduled/queued/published/cancelled; delivery tracked separately | DONE | `email_jobs` vs `notices.status` |
| D | Immutable approved version | DONE | `notice_versions`, edit of published notice → 409 |
| D | Attachments (allow-list, size, safe names, authorised download) | DONE | `test_attachment_validation` |
| E Recipients | all / departments / employees, exact count, stable snapshot | DONE | `test_publish_snapshot_jobs_and_no_double_publish` |
| F Templates | responsive HTML + text fallback, Nepali, sanitised | DONE | branding fields editable (name, subject prefix, footer); layout fixed |
| G SMTP | Hostinger SMTP (configurable), individual sends, bounded backoff, ambiguous → unknown | DONE | real SMTP exchange vs local aiosmtpd; `test_mailer.py` |
| G | Live send through Hostinger | UNVERIFIED | needs the real password; not attempted by design |
| H Queue | DB outbox, restart-safe, no duplicate claims, rate limits, requeue | DONE | `test_delivery.py`; concurrent PostgreSQL claim UNVERIFIED (SQLite has no row locks) |
| I Dashboard | cards, recent notices/sending, upcoming, failure warnings from DB | DONE | `test_dashboard_numbers_come_from_database` |
| J History | filters, pagination, CSV export, retry | DONE | export neutralises formula injection |
| D | Image-only notices (photo of the physical board) - inline in email/preview/detail | DONE | `test_image_only_notice_is_resized_and_emailed_inline` |
| K Attachments | link or attach mode, lifecycle, cleanup | DONE | `cleanup-attachments` CLI; no automatic purge of cancelled notices' files |
| L Scheduling | Asia/Kathmandu input, UTC storage, resume after restart, cancel, revalidate | DONE | `test_schedule_cancel_and_fire`, `test_scheduled_revalidated_at_fire_time` |
| Security | headers, CORS, CSRF, sanitisation, secret redaction, dry-run, disabled-by-default broadcast | DONE | see `07-SECURITY.md` |
| Security | Database least privilege | UNVERIFIED | init script + two URLs implemented; never run (no Docker daemon locally) |
| Infra | Dev/prod compose, health checks, restart policies, Caddy HTTPS, non-root containers | UNVERIFIED | `docker compose config` validated; images **not built** (daemon unavailable) |
| Infra | Backup/restore scripts + docs | UNVERIFIED | not executed |
| Expiry | Expiry Tracker: vehicles, staff/driver, company, equipment; renewals + history; bell; daily admin email digest; CSV export | DONE | `test_expiry.py` (22), bell/date Vitest, e2e #2; import from Excel NOT DONE; BS (Nepali) dates NOT DONE |
| Testing | pytest, Vitest, local Playwright e2e | DONE | 83 + 14 + 2 passing |
| Departments | Per-department "head"/ownership, templates CRUD beyond default | NOT DONE | see roadmap |

Acceptance criteria 1–16, 18 (SQLite), 19, 20 are met; 17 (Docker build) and PostgreSQL-specific checks are UNVERIFIED.
