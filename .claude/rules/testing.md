---
paths:
  - "backend/tests/**"
  - "frontend/src/tests/**"
  - "frontend/e2e/**"
---

# Testing rules

- Tests must never contact a real SMTP server or email real people. Backend tests use `FakeMailer`/monkeypatched
  `smtplib` or an in-process `aiosmtpd` sink on 127.0.0.1; e2e uses `scripts/test/smtp_capture.py`.
- Use reserved/test domains only (`corp.example.com`); `.test` is rejected by email-validator.
- Backend tests run on SQLite through the **real Alembic migration** (`conftest._migrate`). Tables are emptied after each
  test. Anything PostgreSQL-specific (row locks, `SKIP LOCKED` concurrency) is UNVERIFIED locally — say so.
- Bug fix → write the failing test first. New route → happy path + permission denial (viewer/editor/admin as relevant).
- Assert behaviour, not implementation: statuses, counts in DB, messages captured by the fake mailer.
- Frontend: Testing Library by role/label; mock `fetch`, not internal modules. Playwright: one critical-path spec, local only.
- Never mark flaky tests as skipped without a TASKS.md entry.
- Gate: `bash scripts/test/run.sh all`.
