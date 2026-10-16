# Progress log


## 2026-10-16 (later) - Apple-style design system + Expiry Tracker
Applied `DESIGN.md` across UI and emails. Added the Expiry Tracker (migration 0002, `services/expiry.py`, `api/expiry.py`, worker digest,
bell, panel, settings). Bug found by tests and fixed: overdue transition tried to re-insert already-recorded reminder thresholds.
`bash scripts/test/run.sh all` -> ALL PASSED: 83 pytest, 14 Vitest, 2 Playwright. Migration 0002 applied to the local dev.db. No real digest
email has been sent yet (first one should go only to the owner's address).

## 2026-10-16 - image notices, logo, Gmail test
Added Pillow (pinned 12.3.0), image upload re-encoding, inline email images, image-only publish, logo in email/UI. Gmail SMTP (shangrilatoursextra@gmail.com) used for one real test to it@gohimalaya.travel: accepted by SMTP; inbox receipt confirmed by the owner ("mail is working"). Tests: 61 pytest. Per-file upload limit raised to 20 MB (nginx 25 MB).

## 2026-10-15 - initial implementation (single Claude Code session)

### Completed
Everything marked DONE in `TASKS.md`. Highlights: auth/RBAC, directory + import, notices with frozen versions and recipient
snapshots, SMTP mailer + DB outbox + worker + scheduler, dashboard/history/export/templates/settings, full React UI, Docker/Caddy
config, verification and ops scripts, Claude Code harness.

### Files (high level)
`backend/app/**` (api, core, models, schemas, services, workers, templates), `backend/alembic/versions/0001_initial_schema.py`,
`backend/tests/**` (58 tests), `frontend/src/**`, `frontend/e2e/**`, `infra/**`, `scripts/**`, `docs/**`, `.claude/**`, `CLAUDE.md`,
`AGENTS.md`, `README.md`, `CHANGELOG.md`, `.env.example`.

### Deviations from the master prompt (deliberate)
- Harness *documents* were written after the code (they needed to describe real behaviour); the executable scripts and rules existed
  before feature work was finished.
- No Claude Code hooks were added (optional; nothing safe and useful to automate). `.claude/settings.json` only denies reading
  `.env*`/backups and asks before `git push`/deploy/ssh.
- `repositories/` is empty on purpose; `roles` is a column rather than a table (see `13-DECISIONS.md`).
- Subagent reviewers are defined but **were not run**: the session had only the built-in agent types. The security review was done
  inline by the implementing agent (below).

### Commands executed and results (real)
| Command | Result |
|---|---|
| `python -m venv backend/.venv`; `pip install …` | OK (first attempt timed out on network, retry OK) |
| `cd backend && pytest -q` | **58 passed** |
| `ruff check . && ruff format --check .` | passed |
| `alembic upgrade head`, `alembic check`, downgrade/upgrade (SQLite) | passed (expression index not comparable on SQLite - warning) |
| `cd frontend && npm run lint / typecheck / test / build` | passed; 10 Vitest tests; build warns bundle 865 kB |
| `npx playwright test` (Chromium, local SQLite + aiosmtpd sink) | **1 passed** (login → enable broadcast → import 3 → notice → preview → test send → publish → 3 delivered → history) |
| `bash scripts/test/run.sh all` | **ALL PASSED** (9 steps) |
| `docker compose -f infra/compose.yaml config -q`; prod with `.env.example` + dummy passwords | valid |
| `docker build`/`compose up` | **NOT RUN - Docker daemon not running** |
| PostgreSQL anything | **NOT RUN - no PostgreSQL available** |
| Live Hostinger SMTP | **NOT RUN - no credentials, by design** |

### Inline security review findings (implementing agent, not independent)
Checked: route auth coverage (new test walks OpenAPI), CSRF/Origin, session handling, lockout, XSS (sanitiser + sandbox + CSP),
CSV injection, upload validation, header injection, secret handling/redaction, prod config guards, email gates.
Found and fixed during build: editor remount lost state (functional); auth coverage not asserted → added
`test_every_route_requires_authentication`. Accepted risks are listed in `07-SECURITY.md`.
Not reviewed: container hardening in practice, TLS config at runtime, PostgreSQL role grants, dependency CVEs (no `pip-audit`/`npm audit` run).

### Blockers
- Docker daemon unavailable on this machine → T83, parts of T03/T90.
- No PostgreSQL → T82.
- Hostinger password intentionally not available → T42.
- Hostinger plan limits unknown → `EMAIL_RATE_PER_MINUTE/DAY` are placeholders (20/300).

### Next action
Owner: start Docker Desktop (or use the Ubuntu server), then run T83: `docker compose --env-file .env -f infra/compose.yaml up --build`
in dry-run, create the admin with `docker compose … exec backend python -m app.cli create-admin`, and repeat the notice flow.
Then T82 (PostgreSQL pass), then T42 (enter the Hostinger password on the server; Settings → Test SMTP connection → Send test to yourself).
