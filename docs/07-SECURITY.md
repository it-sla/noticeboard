# Security

## Controls implemented
| Risk | Control | Where |
|---|---|---|
| Credential theft | argon2id hashes; secrets only in server env; `.env*` ignored and denied to Claude; SMTP password never returned/logged | `core/security.py`, `.gitignore`, `.claude/settings.json`, `mailer.redact` |
| Session theft/fixation | random token, only hash stored, HttpOnly+SameSite+Secure, idle+absolute expiry, new session per login | `api/auth.py`, `core/deps.py` |
| CSRF | header token + Origin allow-list; CORS limited to configured origins, credentials only for them | `core/deps.py`, `main.py` |
| Brute force | per-account lock + per-IP failure throttle | `api/auth.py` |
| Broken access control | `require_role` on every route; route-coverage test; own-draft rule for editors; viewers limited to published | `api/*`, `test_auth.py` |
| XSS | nh3 allow-list sanitiser on every write of `body_html`; sandboxed iframe preview; CSP `script-src 'self'`; React escaping | `rendering.py`, `frontend/infra-nginx.conf` |
| Injection | ORM only; `ilike` wildcard escaping; CSV export neutralises `= + - @`; email header CR/LF stripped | `api/util.py`, `api/email.py` |
| Upload abuse | extension allow-list + magic-byte check + size limits, uuid storage names, no execution, `nosniff` download | `services/attachments.py` |
| Mass-mail accident | dry-run default; broadcast off by default; explicit confirm + count match; single-address test send; per-user test limit | `services/notices.py`, `api/email.py` |
| Duplicate sends | row lock + status check, unique keys, ambiguous → `unknown` without auto-retry | `services/delivery.py` |
| Data exposure | individual sends (no shared To/CC); logs avoid bodies/lists | `mailer.py`, `workers/` |
| Network | Postgres unpublished in production; only Caddy exposes 80/443; HSTS; security headers on API and nginx | `infra/` |
| Privilege | containers non-root (backend uid 10001, nginx-unprivileged); runtime DB role DML-only | Dockerfiles, `10-app-role.sh` |
| Misconfiguration | production refuses to start with `COOKIE_SECURE=false` or docs enabled; `validate_config.py` pre-deploy check | `core/config.py`, `scripts/deploy` |

## Known limitations / residual risk
- Account lockout can be abused to lock a known account for 15 minutes.
- Import of `.xlsx` relies on openpyxl read-only mode with a 5 MB limit; decompression bombs are not specifically mitigated.
- No MFA/SSO and no self-service password change yet.
- Attachments are not virus-scanned. Link mode requires employees to have accounts; attach mode (default) does not.
- `unsafe-inline` styles are allowed in CSP (TipTap/Tailwind and the preview iframe need it); scripts are not.
- The least-privilege DB role, Docker hardening and TLS settings are implemented but **UNVERIFIED** (no Docker daemon was available).
- A formal third-party security review/penetration test has not been performed. An inline review by the implementing agent
  was done (see `PROGRESS.md`); no independent subagent review is claimed.

## Operational guidance
Rotate DB and SMTP passwords on staff changes; back up `pgdata` and `attachments` together; keep Docker images updated; review
`audit_logs` for repeated `auth.login_failed`; remove `BOOTSTRAP_ADMIN_PASSWORD` from env files after bootstrap.
