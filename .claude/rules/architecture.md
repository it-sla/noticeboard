# Architecture rules

- Modular monolith: one FastAPI app + one worker process sharing `app/`. No microservices, no Redis/Celery, no n8n yet.
- Layering: `api/` (HTTP, validation, permission) → `services/` (business rules, transactions) → `models/` (tables).
  `repositories/` is unused by design; do not add a repository layer without a documented need.
- Integration boundary for future automation (e.g. n8n): outbound email goes only through `services/mailer.py`
  (`get_mailer()`) and the `email_jobs` outbox. New senders implement the same `send(msg)`/`dry_run` interface.
- State machines (keep in sync with `models/entities.py`):
  - notice: draft → scheduled → queued → published; draft/scheduled → cancelled; archive is a flag (`archived_at`).
  - job: pending → sending → accepted | failed | unknown | dry_run; failed/unknown → pending only via explicit retry.
- Publishing is one DB transaction (lock notice row, freeze version, snapshot recipients, insert jobs, flip status).
- Time: store UTC, `UTCDateTime` type, never naive datetimes. Display zone is `Asia/Kathmandu`.
- Config only through `core/config.py` (env vars). No hardcoded hosts, credentials or limits.
- Mirror API shape changes in `frontend/src/types/index.ts` and `docs/04-API-CONTRACT.md` in the same task.
