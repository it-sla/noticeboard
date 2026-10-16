# Database schema

PostgreSQL 16 in production; tests use SQLite through the same Alembic migration (`backend/alembic/versions/0001_initial_schema.py`).
All timestamps are timezone-aware UTC. Source of truth: `backend/app/models/entities.py`.

| Table | Purpose | Key constraints / indexes |
|---|---|---|
| `users` | admin users; `role` ∈ SUPER_ADMIN, ADMIN, NOTICE_EDITOR, VIEWER (single role per user) | unique `email` (lower-case); `failed_logins`, `locked_until` |
| `sessions` | server-side sessions; `id` = SHA-256 of cookie token; `csrf_token`, `expires_at`, `last_seen_at` | FK users (cascade), idx `user_id` |
| `departments` | groups of employees | unique index on `lower(name)` |
| `employees` | directory; `email` stored lower-case; deactivated rows are kept | unique `email`; idx `department_id`, `is_active` |
| `notices` | draft/scheduled/queued/published/cancelled; `archived_at` flag; recipient rule (`recipient_mode`, `department_ids`, `employee_ids` JSON) | idx `status`, `scheduled_at` |
| `notice_versions` | immutable approved content (title, subject, body, category, priority) | unique (`notice_id`,`version_no`) |
| `notice_recipients` | recipient snapshot at approval (name, email, department name) | unique (`notice_id`,`email`) |
| `email_jobs` | one outbox row per recipient | unique `recipient_id`, unique `idempotency_key`; idx (`status`,`next_attempt_at`), `notice_id` |
| `email_attempts` | every send attempt: outcome, SMTP code, redacted error, duration | idx `job_id`, `attempted_at` |
| `notice_attachments` | metadata; file stored as uuid under `ATTACHMENT_DIR` | unique `stored_name`; idx `notice_id` |
| `notice_templates` | branding for emails (header text, subject prefix, footer); one default row created on demand | unique `name` |
| `audit_logs` | who did what (action, entity, detail JSON, ip) | idx `at`, `action`, `ip` |
| `expiry_items` | things that expire: category (vehicle/staff/company/equipment), type, subject, optional employee, reference, issued/expires (DATE, AD), reminder days (JSON), archived flag | idx `category`, `expires_on`, `subject`, `is_archived` |
| `expiry_renewals` | history: old/new expiry, optional cost, note, who/when | idx `item_id` |
| `expiry_reminders` | thresholds already emailed per (item, expiry date); `-1` = overdue alert | unique (`item_id`,`expires_on`,`threshold_days`) |
| `app_settings` | key/value (currently `broadcast_enabled`, default off) | PK `key` |

Enums are stored as strings (see `models/entities.py`): job status `pending, sending, accepted, failed, unknown, dry_run`.

## Why these invariants
- `UNIQUE(email_jobs.recipient_id)` + `UNIQUE(idempotency_key)`: a recipient can never get two jobs for one notice, even if the
  publish code path runs twice.
- `UNIQUE(notice_recipients.notice_id, email)`: duplicates in the audience collapse.
- Recipients/versions are copied, not referenced, so later edits to employees or the draft cannot change a sent notice.
- `employees` are never deleted; `notice_recipients.employee_id` keeps history.

## Migrations
`alembic upgrade head` (dev), production uses the `migrate` service with `MIGRATE_DATABASE_URL` (owner role). The runtime role
`APP_DB_USER` is created by `infra/postgres/10-app-role.sh` on first DB initialisation with DML-only default privileges.
PostgreSQL-specific behaviour (row locking, the `lower(name)` index) is **UNVERIFIED** locally (no PostgreSQL available).
