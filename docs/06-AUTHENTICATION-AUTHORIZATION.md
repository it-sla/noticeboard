# Authentication and authorization

## Sessions
- `POST /auth/login` verifies the password with **argon2id** (`argon2-cffi` defaults). Unknown users still run a dummy verify to
  keep timing similar; the error is always `invalid_credentials`.
- On success a random 256-bit token is set as cookie `session` (HttpOnly, SameSite=Lax, `Secure` when `COOKIE_SECURE=true`,
  max-age = absolute lifetime). Only `SHA-256(token)` is stored in `sessions`.
- Expiry: absolute `SESSION_ABSOLUTE_HOURS` (12) and idle `SESSION_IDLE_MINUTES` (120; `last_seen_at` updated at most once a minute).
  Logout deletes the row; deactivating a user deletes all their sessions.
- Throttling: after `LOGIN_MAX_FAILURES` (5) wrong passwords the account is locked `LOGIN_LOCK_MINUTES` (15) (returns 429);
  per source IP, `LOGIN_IP_MAX_FAILURES` (20) failures in the window return 429. Known trade-off: lockout can be used to annoy a
  known account; Super Admin can see attempts in `audit_logs`.
- CSRF: every unsafe request needs `X-CSRF-Token` equal to the session's token (readable from `/auth/me` and the `csrf_token`
  cookie), and a present `Origin` header must be in `CORS_ORIGINS`.
- Client IP is read from `X-Forwarded-For` (first hop) because the app only runs behind Caddy/nginx; do not publish port 8000.

## Roles and permissions
| Capability | VIEWER | NOTICE_EDITOR | ADMIN | SUPER_ADMIN |
|---|:-:|:-:|:-:|:-:|
| Read published notices, download their attachments | ✓ | ✓ | ✓ | ✓ |
| See drafts/scheduled/cancelled, preview, list departments & employees | | ✓ | ✓ | ✓ |
| Create drafts, edit **own** drafts, upload attachments, duplicate | | ✓ | ✓ | ✓ |
| Edit any draft | | | ✓ | ✓ |
| Publish, schedule, cancel, archive, send test, retry failed | | | ✓ | ✓ |
| Employees, departments, import, templates, email history, dashboard, settings (read) | | | ✓ | ✓ |
| Enable/disable broadcasting, SMTP check, manage users, view audit log | | | | ✓ |

Implemented as a rank comparison in `core/deps.require_role`. Every route is checked; `test_every_route_requires_authentication`
fails if a new route is reachable without a session, and `test_role_matrix` covers the privilege boundaries.

## Bootstrap
No default accounts exist. Create the first Super Admin on the server:
```bash
docker compose --env-file .env.production -f infra/compose.production.yaml run --rm \
  -e BOOTSTRAP_ADMIN_PASSWORD='<12+ chars>' backend python -m app.cli create-admin --email you@company.com --name "Your Name"
```
(or omit the env var to be prompted; use `-it`). It refuses if a Super Admin already exists. Passwords: minimum 12 characters.

## Audit log
Written in the same transaction as the action: login success/failure, logout, user create/update, employee/department changes,
import, notice create/update/publish/schedule/cancel/archive/duplicate, attachments, retries, exports, test sends, broadcast
switch, SMTP check, template edits. Contains ids and field names, not message bodies or passwords.

## Not implemented
Self-service password change, MFA, SSO. Planned in `12-FUTURE-ROADMAP.md`.
