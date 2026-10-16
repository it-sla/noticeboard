# API contract

Base path `/api`. JSON in/out. OpenAPI/Swagger at `/api/docs` and `/api/openapi.json` **only when `DOCS_ENABLED=true`** (default
in development; production config rejects it). Auth: session cookie (`session`, HttpOnly) + `X-CSRF-Token` header on
POST/PUT/PATCH/DELETE (token from `POST /auth/login` or `GET /auth/me`). Minimum role in brackets.

## Conventions
- Errors: `{"error": {"code": "snake_case", "message": "...", "details": ...}}`. Status: 401 not authenticated, 403 forbidden /
  csrf_failed / bad_origin, 404, 409 conflict/state, 422 validation (`details` = `[{field, message}]`), 429 rate-limited.
- Pagination: query `page` (≥1), `page_size` (1–200, default 25) → `{items, total, page, page_size}`.
- Timestamps: ISO-8601 UTC. Schedule input must include an offset (e.g. `2026-12-01T09:00:00+05:45`).

## Auth
`POST /auth/login {email,password}` (public) → `{user, csrf_token}` · `POST /auth/logout` (any) · `GET /auth/me` (any)
`GET /users`, `POST /users`, `PATCH /users/{id}` [SUPER_ADMIN] (create/role/active/password reset; cannot demote or deactivate self)

## Directory
`GET /departments` [EDITOR] (`include_inactive`) · `POST /departments`, `PATCH /departments/{id}` [ADMIN]
`GET /employees` [EDITOR] (`search`, `department_id`, `active`, paging) · `POST /employees`, `PATCH /employees/{id}`,
`DELETE /employees/{id}` (= deactivate) [ADMIN]
`POST /employees/import?commit=false|true` multipart `file` (.csv UTF-8 or .xlsx; columns Name, Email, Department, Job Title) [ADMIN]
→ `{committed,total,ok,skipped,errors,rows[{row,status,message,new_department}]}`

## Notices
`GET /notices` (`search,status,category,archived`, paging; viewers see only queued/published) [VIEWER]
`POST /notices` [EDITOR] · `GET /notices/{id}` [VIEWER, published only] · `PATCH /notices/{id}` [EDITOR own draft / ADMIN any draft]
`GET /notices/{id}/preview` [EDITOR] → `{subject,html,text,sender,recipient_count,attachments,broadcast_enabled,email_mode}`
`POST /notices/{id}/publish {confirm:true, expected_recipient_count}` [ADMIN] → `{status:"queued", recipient_count}`
  409 codes: `already_published`, `broadcast_disabled`, `recipient_count_changed` (details.recipient_count); 422: `no_recipients`, `incomplete_notice`
`POST /notices/{id}/schedule {scheduled_at}` · `POST /notices/{id}/cancel` · `POST /notices/{id}/archive?undo=` [ADMIN]
`POST /notices/{id}/duplicate` [EDITOR] (copies content + audience, not attachments)
`GET /notices/{id}/versions` [VIEWER] · `GET /notices/{id}/sending` [EDITOR] → `{notice_status,total,counts,complete}`
`GET /notices/{id}/recipients` [ADMIN] (per-recipient delivery log, paging)
`POST /notices/{id}/attachments` (multipart `file`; PNG/JPG are re-encoded to JPEG ≤1600 px and shown inline in emails; a notice can be published with an image and no text) · `DELETE /notices/{id}/attachments/{aid}` [EDITOR, drafts only]
`GET /attachments/{aid}/download` [VIEWER, published only]

## Email
`GET /email/jobs` (`status,search,notice_id,date_from,date_to`, paging) · `GET /email/jobs/export` (CSV) ·
`GET /email/jobs/{id}/attempts` · `POST /email/jobs/{id}/retry {include_unknown}` ·
`POST /email/notices/{id}/retry-failed {include_unknown}` · `POST /email/test {to,title,body_html,category,priority}` [ADMIN]
  `to` is one address; limit `TEST_SEND_PER_HOUR` per user; response `{mode,sent,message}` (`sent:false` in dry-run).

## Expiry tracker [ADMIN]
`GET /expiry/presets` · `GET /expiry/summary` (counts overdue/due7/due30/due60/ok) · `GET /expiry/alerts` (bell: overdue + within 7 days)
`GET /expiry/items` (`category,status,search,archived`, paging; soonest first) · `POST /expiry/items` · `PATCH /expiry/items/{id}` ·
`DELETE /expiry/items/{id}` (= archive) · `POST /expiry/items/{id}/renew {new_expires_on,cost?,note?}` (must be after current expiry) ·
`GET /expiry/items/{id}/history` · `GET /expiry/export` (CSV) · `PUT /settings/expiry {enabled, extra_recipients[]}`

## Dashboard / settings / templates
`GET /dashboard/summary`, `GET /dashboard/activity` [ADMIN] · `GET /settings` [ADMIN] · `PUT /settings/broadcast {enabled}` [SUPER_ADMIN]
`POST /settings/smtp-check` [SUPER_ADMIN] (connect+auth only) · `GET /templates`, `PATCH /templates/{id}` [ADMIN] ·
`GET /audit?limit=` [SUPER_ADMIN] · `GET /health` (public)
