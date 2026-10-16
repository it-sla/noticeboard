# Architecture

Modular monolith: one codebase, two processes (API, worker) sharing the `app` package and one PostgreSQL database.

```
Browser ──HTTPS──> Caddy ──> nginx (SPA + /api proxy) ──> FastAPI (api/ → services/ → models/) ──> PostgreSQL
                                                                         ▲
                                              email worker (services/delivery.py) ── SMTP ──> Hostinger
```

## Layers (backend/app)
- `api/` HTTP routes, request validation, `require_role` permission, audit calls. Files: `auth.py` (+users), `directory.py`
  (departments, employees, import), `notices.py` (+attachments), `email.py` (history, retry, test), `admin.py` (dashboard,
  settings, templates, audit).
- `services/` business rules and transactions: `notices.py` (recipients, publish, schedule, cancel, duplicate),
  `delivery.py` (outbox claim/send/record, stale recovery, finalise), `mailer.py` (SMTP + failure classification),
  `rendering.py` (sanitise, HTML/text email), `attachments.py`, `audit.py`, `app_settings.py`.
- `models/entities.py` all tables + enums. `schemas/common.py` Pydantic I/O. `core/` config, db, security, deps, errors.
- `workers/email_worker.py` loop: recover stale → fire due scheduled → claim → send → finalise.
- `repositories/` intentionally empty (ORM used directly; revisit if query logic starts to be duplicated).

## Publish flow (one transaction)
`POST /notices/{id}/publish {confirm, expected_recipient_count}` → lock notice row → verify status draft/scheduled →
verify broadcasting enabled → resolve active recipients → compare count (409 `recipient_count_changed` on drift) →
insert `notice_versions` (frozen subject/body) → insert `notice_recipients` snapshot → insert `email_jobs`
(`idempotency_key = notice:{id}:recipient:{rid}`, unique) → `notices.status = queued`. A second request sees `queued` → 409.

## Delivery flow
1. `claim_jobs`: `SELECT … WHERE status='pending' AND next_attempt_at<=now FOR UPDATE SKIP LOCKED LIMIT n`
   (n = min(per-minute, per-day allowance, 50)); set `sending`, bump `attempt_count`, insert an `email_attempts` row `sending`.
2. `send_job`: build the message from the frozen version + recipient snapshot; `mailer.send`.
3. Outcome: accepted → `accepted`; transient → `pending` with backoff `base·2^(n-1)` (capped) until `max_attempts` → `failed`;
   permanent → `failed`; ambiguous (connection lost after DATA began) → `unknown`; dry-run → `dry_run`.
4. `recover_stale`: `sending` older than `EMAIL_SENDING_STALE_MINUTES` → `unknown` (never resent automatically).
5. `finalize_notices`: `queued` notice with no pending/sending jobs → `published`.

## Scheduling
`notices.scheduled_at` (UTC). Worker `fire_due_scheduled` claims due notices with `SKIP LOCKED`, revalidates eligibility
(broadcast enabled, non-empty audience) and runs the same approval code as manual publish. Ineligible → back to `draft` + audit.
Recipients for scheduled notices are resolved **at fire time** (the audience is a rule until approval).

## Frontend
React SPA; `lib/api.ts` is the only HTTP client (cookie + CSRF header). TanStack Query for server state. The editor page
(`/notices/:id/edit`, `/notices/new/edit`) saves drafts before preview/publish; location state carries "show preview" across the
post-create redirect.

## Failure modes
| Failure | Behaviour |
|---|---|
| Worker killed mid-send | job stays `sending` → `unknown` after the stale window; admin decides on retry |
| SMTP down/auth wrong | transient → backoff; auth error → permanent `failed` (inspect, fix env, retry from History) |
| DB unavailable | API 500; worker logs and retries next cycle |
| Two workers | `SKIP LOCKED` claims are disjoint (PostgreSQL); run one worker unless needed |
