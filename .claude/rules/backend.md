---
paths:
  - "backend/app/**/*.py"
---

# Backend rules

- Every route declares its minimum role with `Depends(require_role(Role.X))` (or `current_auth` for any signed-in user).
  Writes require ADMIN unless the spec says otherwise; editors only touch their own drafts.
- Raise `ApiError(status, code, message)`; never leak stack traces, SQL or SMTP responses containing secrets.
  Run SMTP error text through `mailer.redact()` before storing/returning it.
- Pagination: `PageParams` + `paginate()` → `Page[T]`. Search uses `like()` escaping with `ilike(..., escape="\\")`.
- Write an `audit(...)` row for every sensitive mutation, in the same transaction as the change.
- Services own transactions: commit once at the end of the unit of work. Use `with_for_update` for claim/lock paths
  (`skip_locked=True` for queue claims).
- Never send mail from request handlers except `/email/test` (single address, rate-limited, admin-only).
- Sanitise rich text with `rendering.sanitize_html` on every write path that stores `body_html`.
- Uploads: validate with `services/attachments.py` (allow-list, magic bytes, size) and store under a uuid name only.
- No raw SQL with string interpolation. No `print` — use `logging`, and never log message bodies or addresses lists.
- Lint/format: `ruff check . && ruff format .` from `backend/`.
