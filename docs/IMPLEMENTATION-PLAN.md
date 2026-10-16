# Implementation plan

Phases map to the original master prompt. State on 2026-10-15: phases 0–8 complete locally; phase 9 files written but **Docker
parts unverified**; deployment not performed. Task-level status lives in `TASKS.md`.

| Phase | Scope | Depends | Acceptance | Status |
|---|---|---|---|---|
| 0 Harness | CLAUDE/AGENTS, rules, agents, skills, scripts, docs skeleton | – | `run.sh` usable by a fresh session | DONE (docs were finalised after the code so they match it) |
| 1 Infrastructure | backend/frontend skeletons, config, Alembic, Dockerfiles, compose | 0 | services boot locally; compose config valid | DONE locally; Docker boot UNVERIFIED |
| 2 Authentication | sessions, CSRF, roles, lockout, bootstrap | 1 | `test_auth.py` | DONE |
| 3 Directory | departments, employees, import | 2 | `test_directory.py` | DONE |
| 4 Notices | CRUD, preview, attachments, template, sanitising | 3 | `test_notices.py` | DONE |
| 5 Email automation | SMTP, outbox, worker, history | 4 | `test_mailer.py`, `test_delivery.py` | DONE |
| 6 Recipients + publish | audience, count, snapshot, confirmation, broadcast gate | 5 | publish tests | DONE |
| 7 Scheduling + reporting | scheduler, dashboard, history, export | 6 | scheduling + dashboard tests | DONE |
| 8 Testing + security | full suite, e2e, review | 7 | `run.sh all` = ALL PASSED | DONE (inline security review only) |
| 9 Deployment prep | prod compose, Caddy, backups, docs | 8 | config validates; images build | PARTIAL - build/boot UNVERIFIED |

## Design decisions
See `13-DECISIONS.md` and `ADR/`. Key ones: DB outbox + worker; frozen version/recipients at approval; dry-run + broadcast switch;
ambiguous SMTP outcomes never auto-retried.

## Risks and mitigations
| Risk | Mitigation | Residual |
|---|---|---|
| Accidental mass email | dry-run default, broadcast switch, confirm + count, single-address test, tests use sinks | operator error after enabling |
| Duplicate emails | locks + unique keys + `unknown` handling | admin retry of `unknown` |
| Hostinger limits unknown | env-driven per-minute/day caps, backoff | must be set from the real plan before go-live |
| SQLite-tested, PostgreSQL-deployed | portable types, real migration in tests | T82 to close |
| Docker unverified | compose config validated, health checks | T83 to close |
| Single worker / single host | outbox is restart-safe; backups documented | no HA |

## Verification commands
```bash
bash scripts/test/run.sh all
docker compose -f infra/compose.yaml config -q                                   # dev
POSTGRES_PASSWORD=x APP_DB_PASSWORD=y docker compose --env-file .env.example -f infra/compose.production.yaml config -q
python scripts/deploy/validate_config.py .env.production                         # on the server
```

## Next steps (in order)
1. T83: start Docker, build images, `compose up` (dev) with `EMAIL_MODE=dry_run`, repeat the e2e flow by hand.
2. T82: run `TEST_DATABASE_URL`-style test pass against PostgreSQL 16 (set `DATABASE_URL` to a scratch PG; run pytest + a two-worker run).
3. T42: owner enters the Hostinger password on the server → SMTP check → single test email.
4. T91: deployment (needs owner approval) → enable broadcasting for a pilot department.
