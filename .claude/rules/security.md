# Security rules

- Secrets (SMTP password, DB passwords, bootstrap password) live only in server env files. Never ask for them in chat,
  never write them to code, docs, tests, logs, commits or screenshots. Tests use throwaway values.
- Email safety: `EMAIL_MODE=dry_run` by default; `broadcast_enabled` OFF by default; test-send = one address; production
  broadcasts require (1) `EMAIL_MODE=smtp` set on the server and (2) a SUPER_ADMIN enabling broadcasting.
- Auth: argon2 hashes, server-side sessions in DB (cookie holds a random token, only its SHA-256 is stored), HttpOnly +
  SameSite=Lax + Secure (prod), CSRF header on unsafe methods, Origin check, lockout + per-IP failure throttle.
- Authorisation on the server for every route; add a test in `tests/test_auth.py::test_role_matrix` style for new routes.
- Input: Pydantic validation at the boundary; HTML sanitised with nh3 allow-list; CSV export neutralises formula cells;
  uploads limited by extension allow-list + magic bytes + size.
- Logging: no message bodies, no full recipient lists, no tokens. SMTP errors pass through `redact()`.
- Never configure Claude Code hooks that deploy, send email, or print secrets.
- Do not touch production systems (server, DNS, live mailbox, production DB) without explicit user permission.
- Run the `security-reviewer` subagent or `/review-security` skill for changes to auth, sessions, sending, uploads, config.
