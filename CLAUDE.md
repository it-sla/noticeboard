# Employee Notice Board — Claude Code entry point

Internal notice board + email broadcast system for **Shangri La Tours / UPS Nepal**. Admins write a
notice, choose recipients, preview, and **Publish & Email**; a database-backed worker sends one
individual email per employee through the existing Hostinger mailbox `it@gohimalaya.travel`.
This is a real business app, not a demo.

## Before you change anything
1. Read `docs/TASKS.md` and `docs/PROGRESS.md` (current state, blockers, next action).
2. Read the rule files in `.claude/rules/` that match the files you touch.
3. Prove your work with `bash scripts/test/run.sh all` (or the single step you need).

## Stack
- Backend: Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2.1, Alembic, PostgreSQL 16 (psycopg 3), argon2, nh3, Jinja2, openpyxl.
- Worker: same image, `python -m app.workers.email_worker` (DB outbox, no Redis/Celery, no n8n).
- Frontend: React 19, TypeScript, Vite, Tailwind 4, React Router 8, TanStack Query, React Hook Form + Zod, TipTap.
- Tests: pytest, Vitest + Testing Library, Playwright (LOCAL app only). Lint: ruff, ESLint.
- Infra: Docker Compose (dev + production), Caddy (HTTPS), nginx (SPA), Ubuntu server.
- Exact versions: `backend/requirements.lock.txt`, `frontend/package.json`.

## Repository map
```
backend/app/{api,core,models,schemas,services,repositories,workers,templates}  FastAPI modular monolith
backend/alembic/            migrations (0001 initial schema, 0002 expiry tracker)
backend/tests/              pytest (SQLite via the real Alembic migration)
frontend/src/{app,components,pages,lib,types,tests}   SPA; frontend/e2e = Playwright
infra/                      compose.yaml (dev), compose.production.yaml, caddy/, postgres/
scripts/{dev,test,backup,deploy}   executable helpers (run.sh = verification entry point)
docs/                       numbered design docs, TASKS, PROGRESS, ADR/
.claude/{rules,agents,skills}      project memory for Claude Code
```
`repositories/` is intentionally empty: the ORM is used directly in services/API (see docs/13-DECISIONS.md).

## Commands
```bash
bash scripts/dev/setup.sh              # venv + npm + SQLite dev DB + seed (no email sent)
bash scripts/dev/start.sh              # API :8000, worker (dry-run), Vite :5173
bash scripts/test/run.sh all           # lint, pytest, migrations, vitest, tsc, build, config, e2e
bash scripts/test/run.sh backend-test  # single step (see header of run.sh)
cd backend && .venv/Scripts/python -m pytest -q          # (Linux: .venv/bin/python)
cd frontend && npm run typecheck && npm test && npm run build
cd frontend && npx playwright test     # starts its own SQLite backend + local SMTP sink
docker compose --env-file .env -f infra/compose.yaml up --build           # dev stack
```
Production deploy: see `docs/09-DEPLOYMENT.md`. **Never deploy without explicit user permission.**

## Critical architecture rules
- Modular monolith. Routes in `api/`, business rules in `services/`, tables in `models/entities.py`.
- Schema changes only through Alembic (`backend/alembic/versions`); never `create_all` in app code.
- Publication status (`notices.status`) and delivery status (`email_jobs.status`) are separate concepts.
- Publish freezes content (`notice_versions`) and recipients (`notice_recipients`) and creates one
  `email_jobs` row per recipient in the same transaction. Unique keys make duplicates impossible.
- Authorization is enforced server-side via `require_role(...)`; UI guards are cosmetic.
- All timestamps are UTC (`UTCDateTime`); display in `Asia/Kathmandu` in the UI only.
- SMTP "accepted" ≠ inbox delivery. Ambiguous outcomes become `unknown` and are never auto-retried.

## Security and email-sending restrictions (non-negotiable)
- **Never send real email** from tests, seeds, scripts or dev runs. Default `EMAIL_MODE=dry_run`; tests use
  fakes or the local aiosmtpd sink. `broadcast_enabled` is OFF by default (SUPER_ADMIN switch).
- Never request, print, log or commit the SMTP password or any secret. `.env*` (except `.env.example`) is gitignored and
  denied in `.claude/settings.json`.
- Test sends go to exactly one address and never touch the outbox.
- No UPS API, UPS website automation or scraping. Playwright is for the local app only.
- Do not deploy, touch DNS, live mail settings or production databases without explicit permission.
- No default/public admin credentials; the first admin comes from `python -m app.cli create-admin`.

## Detailed docs
`DESIGN.md` (UI/email visual system) · `docs/00-PROJECT-OVERVIEW.md` · `01-REQUIREMENTS` (status matrix) · `02-ARCHITECTURE` · `03-DATABASE-SCHEMA` ·
`04-API-CONTRACT` · `05-EMAIL-AUTOMATION` · `06-AUTHENTICATION-AUTHORIZATION` · `07-SECURITY` · `08-TESTING-STRATEGY` ·
`09-DEPLOYMENT` · `10-OPERATIONS-RUNBOOK` · `11-ADMIN-USER-GUIDE` · `12-FUTURE-ROADMAP` · `13-DECISIONS` ·
`14-TROUBLESHOOTING` · `ADR/` · `AGENTS.md` (agent roles, handoff).

## Definition of done
A task is done only when: acceptance criteria in `docs/TASKS.md` are met; `bash scripts/test/run.sh all` passes (or
skipped steps are recorded as UNVERIFIED with the reason); new behaviour has tests; security/error handling reviewed;
affected docs updated; `docs/PROGRESS.md` and `docs/TASKS.md` updated with real command results. Never claim a test,
review or deployment happened if it did not.
