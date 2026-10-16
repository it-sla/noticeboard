---
name: verify-project
description: Run the full deterministic verification suite (lint, tests, migrations, typecheck, build, prod-config validation, local e2e) and report real results. Use before declaring work done or at the start of a session to learn the baseline.
---

# verify-project

## Prerequisites
- Backend venv at `backend/.venv` with dev deps; `frontend/node_modules`; Playwright Chromium (`npx playwright install chromium`) for e2e.
- Ports 1025, 8000, 5173 free (e2e starts its own SMTP sink, API+worker on SQLite, and Vite).

## Procedure
1. `bash scripts/test/run.sh all` (or per step; see header of the script). It prints PASS/FAIL per step and a summary.
2. If Docker is available also run: `docker compose --env-file .env.example -f infra/compose.production.yaml config -q`
   (needs POSTGRES_PASSWORD/APP_DB_PASSWORD exported) and `docker compose -f infra/compose.yaml config -q`.
3. Optionally `docker compose ... build` for the three images (needs a running Docker daemon).

## Commands
```bash
bash scripts/test/run.sh all
bash scripts/test/run.sh backend-test      # one step
```

## Evidence of success
Final line `ALL PASSED`; per-step counts (pytest passed, vitest passed, e2e passed). Copy actual numbers into `docs/PROGRESS.md`.

## Failure handling
- Read the failing step's output; fix the cause (code or test, whichever is wrong) and rerun that step, then `all`.
- A step that cannot run (no Docker daemon, no browser) is reported **UNVERIFIED**, never PASS.
- Port conflicts: stop stale `uvicorn`/`vite`/`aiosmtpd` processes and rerun.
