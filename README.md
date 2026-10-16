# Employee Notice Board

Internal notice board and email broadcasting for Shangri La Tours / UPS Nepal. Write a notice, pick recipients, preview, **Publish & Email**;
a database-backed worker sends individual emails through the existing Hostinger mailbox and records every outcome.

**Safe by default:** `EMAIL_MODE=dry_run` and broadcasting disabled until a Super Admin turns it on. Tests and dev never send real email.

## Quick start (Windows or Linux, no Docker)
```bash
bash scripts/dev/setup.sh      # venv, deps, SQLite DB, first admin (prompts for a password), dev seed
bash scripts/dev/start.sh      # API :8000 · worker (dry-run) · web http://localhost:5173
```
Sign in with the admin you created (default email `admin@localhost.example.com`; override with `ADMIN_EMAIL=...`).

## Verify
```bash
bash scripts/test/run.sh all   # lint, pytest, migrations, vitest, typecheck, build, config check, Playwright e2e
```

## Documentation
| Start here | |
|---|---|
| [CLAUDE.md](CLAUDE.md) | entry point for coding sessions (commands, rules) |
| [docs/01-REQUIREMENTS.md](docs/01-REQUIREMENTS.md) | what is done / unverified / not done |
| [docs/09-DEPLOYMENT.md](docs/09-DEPLOYMENT.md) | Ubuntu + Docker deployment, backup/restore, enabling live email |
| [docs/11-ADMIN-USER-GUIDE.md](docs/11-ADMIN-USER-GUIDE.md) | using the app |
| [docs/PROGRESS.md](docs/PROGRESS.md), [docs/TASKS.md](docs/TASKS.md) | current state and next action |

Architecture: [02](docs/02-ARCHITECTURE.md) · DB: [03](docs/03-DATABASE-SCHEMA.md) · API: [04](docs/04-API-CONTRACT.md) · Email: [05](docs/05-EMAIL-AUTOMATION.md) · Security: [06](docs/06-AUTHENTICATION-AUTHORIZATION.md), [07](docs/07-SECURITY.md) · Ops: [10](docs/10-OPERATIONS-RUNBOOK.md), [14](docs/14-TROUBLESHOOTING.md)

## Stack
FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 · React 19 · TypeScript · Vite · Tailwind 4 · TanStack Query · Docker Compose · Caddy.
Tested versions: `backend/requirements.lock.txt`, `frontend/package-lock.json`.
