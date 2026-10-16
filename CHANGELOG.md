# Changelog

## [0.1.0] - 2026-10-15 (unreleased, not deployed)
Initial implementation.

### Added
- Authentication: argon2 login, server-side sessions, CSRF, lockout/throttle, four roles, audit log, CLI bootstrap of the first Super Admin.
- Directory: departments, employees (search/filter/deactivate), CSV/XLSX import with preview and error report.
- Notices: rich-text drafts, categories/priorities, attachments (allow-list), preview, duplicate, archive, search, immutable approved versions.
- Recipients: all / departments / employees with exact count, drift check and immutable snapshot at approval.
- Email: Hostinger-compatible SMTP mailer, responsive HTML + text template (Nepali-safe), database outbox + worker, bounded retries,
  ambiguous-outcome handling, rate limits, dry-run mode, broadcast kill switch, single-address test send.
- Scheduling in Asia/Kathmandu with revalidation at fire time.
- Dashboard, Email History (filters, pagination, CSV export, retries), Templates, Settings (broadcast switch, SMTP check, users).
- Docker Compose (dev/prod), Caddy HTTPS, nginx SPA, backup/restore/deploy/verify scripts, Claude Code harness (rules, agents, skills).
- Tests: 58 pytest, 10 Vitest, 1 Playwright local e2e.

- Image notices: upload a photo of the physical notice board; resized/EXIF-stripped, shown inline in the email, preview and notice page; image-only notices can be published.
- Expiry Tracker: vehicles, staff/driver documents, company licences, equipment; renewal history; bell notifications; daily admin email digest; CSV export.
- UI and email restyled to the Apple-inspired design system in `DESIGN.md` (Action Blue accent, pill buttons, parchment canvas, hairline cards, dark sidebar).
- Shangri La Tours logo in the email header, sign-in page and sidebar.

### Not yet verified
Docker image builds, PostgreSQL-specific concurrency, live Hostinger sending (see docs/01-REQUIREMENTS.md).
