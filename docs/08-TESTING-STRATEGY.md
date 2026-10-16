# Testing strategy

Gate: `bash scripts/test/run.sh all` → backend-lint, backend-test, migrations, frontend-lint, frontend-typecheck, frontend-test,
frontend-build, prod-config, e2e. Individual steps can be run by name.

## Layers
| Layer | Tool | Location | Notes |
|---|---|---|---|
| API + services + worker (integration) | pytest, FastAPI TestClient | `backend/tests/` | SQLite DB created by the real Alembic migration; tables emptied per test |
| SMTP behaviour | pytest + `aiosmtpd` sink / monkeypatched `smtplib` | `test_mailer.py` | real SMTP protocol exchange on 127.0.0.1; failure classification |
| Worker | pytest with `FakeMailer` | `test_delivery.py` | restart recovery, backoff, rate limit, duplicate claim, ambiguity |
| Frontend units | Vitest + Testing Library | `frontend/src/tests/` | api client, format helpers, PublishDialog, LoginPage |
| End-to-end (local only) | Playwright (Chromium) | `frontend/e2e/` | starts SMTP sink, API+worker on SQLite, Vite; never real SMTP/UPS |
| Migrations | alembic | `run.sh migrations` | upgrade, `alembic check` (no model drift), downgrade, upgrade |
| Config | `scripts/deploy/validate_config.py` | `run.sh prod-config` | validates `.env.example` structure; use on `.env.production` before deploy |

## Coverage map (requirements → tests)
Employee create/validation/duplicates, import (CSV/XLSX, preview, errors), department filter/counts, inactive exclusion →
`test_directory.py`, `test_notices.py`. Draft edit, sanitising, recipient modes, snapshot stability, double-publish prevention,
confirmation + count drift, broadcast gate, scheduling/cancel/fire/revalidate, duplicate/archive, attachments → `test_notices.py`.
Authorization (role matrix, viewer visibility, editor own drafts, CSRF, origin, every-route auth, lockout) → `test_auth.py`.
Template rendering + Nepali Unicode → `test_notices.py::test_preview_counts_and_nepali`, `test_delivery.py`, `test_mailer.py`.
SMTP auth/connection failure, throttling (4xx), permanent rejection, dropped connection → `test_mailer.py` (classification) and
`test_delivery.py` (resulting job states). Worker restart/stale recovery, duplicate job prevention, retries, status reporting,
dashboard data, history filters/export (formula guard), test-send safety → `test_delivery.py`.

## Not covered / UNVERIFIED
- PostgreSQL-specific behaviour: real `FOR UPDATE SKIP LOCKED` contention between two workers, the `lower(name)` functional index
  semantics. SQLite ignores row locks; sequential tests still prove the status logic.
- Docker image builds, compose startup, Caddy TLS, the DB role init script.
- Live Hostinger SMTP (credentials intentionally unavailable).
- Session idle/absolute expiry timing and browser cross-compatibility (only Chromium).
- Bundle-size and accessibility tooling (axe) are not automated; accessibility is reviewed by rule only.

## Writing tests
Follow `.claude/rules/testing.md`: reserved domains (`corp.example.com`), no real SMTP, assert persisted state, add a denial test for every new route.
