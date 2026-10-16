# ADR-004: Database outbox + dedicated worker (no Redis/Celery/n8n)

Status: accepted (2026-10-15)

## Decision
- `email_jobs` is the durable outbox. Publishing inserts all jobs in the same transaction that freezes the content and recipients.
- A single worker process loops every `WORKER_POLL_SECONDS`: recover stale `sending`, fire due scheduled notices, claim jobs with
  `FOR UPDATE SKIP LOCKED`, send, record each attempt, finalise notices. Safe to run more than one worker.
- Retry: bounded exponential backoff for transient errors; permanent → failed; ambiguous → unknown. Idempotency keys + unique
  constraints prevent duplicate jobs. Rate limits are computed from `email_attempts`.
- Scheduling lives in the same loop (no cron container).
- Integration boundary for n8n or another system: everything that sends goes through `mailer.get_mailer()`; external
  tools may enqueue via the REST API (service account) or read `email_jobs`; no code path sends outside the outbox except the single-address test send.

## Consequences
+ Survives restarts and crashes with no extra infrastructure; every state is queryable in SQL.
− Polling latency of a few seconds; throughput bounded by SMTP and configured limits (fine for the expected volume).
− Exactly-once is impossible with SMTP; the design minimises duplicates and surfaces ambiguity instead of hiding it.

## Alternatives
Redis + Celery/RQ (extra services, less transparent state), in-memory queue (loses jobs — rejected), n8n (deferred by requirement).
