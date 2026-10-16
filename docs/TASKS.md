# Tasks

Status: TODO · IN_PROGRESS · DONE · BLOCKED · UNVERIFIED (implemented, a required check could not run). Updated 2026-10-15.
Priority: P0 must-have for first deployment, P1 important, P2 later.

| ID | Description | Pri | Status | Depends | Acceptance criteria |
|---|---|---|---|---|---|
| T00 | Repo inspection + harness (CLAUDE/AGENTS, rules, agents, skills, settings, scripts) | P0 | DONE | – | Files exist with project-specific content; `run.sh all` works; no hooks configured (by design) |
| T01 | Backend skeleton, config, DB, Alembic baseline | P0 | DONE | T00 | `alembic upgrade head` + `alembic check` pass; app boots; `/api/health` |
| T02 | Frontend skeleton (Vite/TS/Tailwind/Router/Query) | P0 | DONE | T00 | typecheck, lint, build pass |
| T03 | Docker/Compose dev + prod, Caddy, nginx, health checks | P0 | UNVERIFIED | T01,T02 | `docker compose config` OK (done). Images build and stack boots (**not done: no Docker daemon**) |
| T10 | Auth: login/logout/me, sessions, CSRF, lockout, roles, audit, bootstrap CLI | P0 | DONE | T01 | `test_auth.py` (9 tests) |
| T11 | User management (Super Admin) | P1 | DONE | T10 | create/role/deactivate/password reset; self-lockout guard tested |
| T20 | Departments + employees CRUD, search/filter, deactivate | P0 | DONE | T10 | `test_directory.py` |
| T21 | Employee CSV/XLSX import with preview and error report | P0 | DONE | T20 | preview does not write; commit writes; duplicates/invalid reported |
| T30 | Notice CRUD, sanitising, preview, versions, duplicate, archive, search | P0 | DONE | T20 | `test_notices.py` |
| T31 | Attachments: allow-list, limits, authorised download, orphan cleanup CLI | P0 | DONE | T30 | `test_attachment_validation`; purge of old notices' files not automated |
| T33 | Image notices (upload photo, inline in email, image-only publish) | P0 | DONE | T31 | tests in `test_delivery.py`; resize to 1600 px, EXIF stripped |
| T34 | Expiry Tracker (items, renew + history, bell, dashboard card, daily digest, settings, CSV export) | P0 | DONE | T41 | `test_expiry.py`, Vitest, e2e #2 |
| T35 | Expiry: Excel/CSV import, Nepali (BS) date entry/display, per-item owner reminders | P1 | TODO | T34 | roadmap |
| T32 | Email templates (HTML+text, Nepali, branding fields) | P0 | DONE | T30 | preview/test cover Unicode; template page edits branding |
| T40 | SMTP mailer (Hostinger config), classification, redaction, dry-run | P0 | DONE | T01 | `test_mailer.py` incl. real SMTP exchange vs local sink |
| T41 | DB outbox + worker: claim, retry/backoff, unknown handling, stale recovery, rate limits, finalise | P0 | DONE | T40 | `test_delivery.py` |
| T42 | Live Hostinger test email | P0 | BLOCKED | T40,T03 | Needs real mailbox password entered by owner on the server; run SMTP check then Send test |
| T50 | Recipient selection, count drift check, snapshot, confirm & publish, broadcast gate | P0 | DONE | T30,T41 | publish tests in `test_notices.py` |
| T60 | Scheduling + revalidation + cancel | P0 | DONE | T50 | scheduled tests |
| T61 | Dashboard, Email History (filters/export/retry), Settings | P0 | DONE | T41 | delivery/API tests; UI covered by e2e path only |
| T70 | Frontend pages: login, dashboard, board, editor, detail, employees, departments, history, templates, settings | P0 | DONE | T10.. | typecheck/lint/build; 10 Vitest; 1 Playwright e2e |
| T71 | Local e2e: login → import → notice → preview → test → publish → history | P0 | DONE | T70 | `npx playwright test` passes (Chromium) |
| T80 | Backend/frontend lint + migrations + prod-config validation scripts | P0 | DONE | T00 | `run.sh all` → ALL PASSED |
| T81 | Security review | P0 | DONE* | all | *Inline review by the implementing agent only; no independent reviewer ran. Findings in PROGRESS.md |
| T82 | PostgreSQL verification (migration, SKIP LOCKED concurrency, role init script) | P0 | TODO | T03 | Run backend tests and a two-worker soak against PostgreSQL 16 |
| T83 | Docker image builds + compose smoke test (dev and prod, dry-run) | P0 | TODO | T03 | `docker compose build` and `up` healthy; first-admin command works |
| T90 | Deployment docs, runbook, backup/restore scripts | P0 | UNVERIFIED | T03 | Docs written; scripts never executed |
| T91 | Server deployment | P0 | BLOCKED | T82,T83,T90 | Requires explicit owner permission; start with `EMAIL_MODE=dry_run` |
| T100 | Self-service password change / MFA | P1 | TODO | T10 | roadmap |
| T101 | Bounce parsing / delivery feedback | P2 | TODO | T42 | roadmap |
| T102 | Emergency "cancel pending jobs" for a queued notice | P1 | TODO | T41 | roadmap |
| T103 | Code-split TipTap/editor chunk | P2 | TODO | T70 | bundle < 500 kB per chunk |
