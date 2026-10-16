# Troubleshooting

## Development
| Problem | Fix |
|---|---|
| `pytest` can't import `app` | run from `backend/` with the venv: `.venv/Scripts/python -m pytest` (Linux `.venv/bin/python`) |
| 422 "special-use or reserved name" for an email | `.test`, `.invalid`, `.local` domains are rejected; use `example.com` subdomains in tests |
| Playwright: port 1025/8000/5173 busy | stop stale `uvicorn`/`vite`/`python smtp_capture.py` processes |
| Playwright can't find Chromium | `cd frontend && npx playwright install chromium` |
| Editor loses preview after saving a new draft | the post-create redirect remounts the page; preview is restored via `location.state` (see `NoticeEditorPage`) |
| Vite proxy `ECONNREFUSED` | backend not running on 127.0.0.1:8000, or set `VITE_API_PROXY` |
| `alembic check` reports drift | create a new migration (`.claude/rules/migrations.md`) |
| `bash` heredoc/quoting trouble on Windows | use Git Bash for `scripts/*.sh`; PowerShell for ad-hoc commands |

## Email
| Symptom | Likely cause / action |
|---|---|
| Jobs end as `dry_run` | `EMAIL_MODE=dry_run` - intended default. Set `smtp` only after approval |
| 409 `broadcast_disabled` | a Super Admin must enable broadcasting (Settings) |
| `SMTP authentication failed` | wrong mailbox password/username; Hostinger may require the full address as username; fix env and restart worker |
| `SMTP connection failed` / timeouts | wrong host/port/SSL combination (465 + SSL, or 587 + `SMTP_USE_SSL=false` + `SMTP_STARTTLS=true`); outbound firewall |
| 421/450/451 replies | provider throttling; lower `EMAIL_RATE_PER_MINUTE/DAY` |
| Job `unknown` | connection dropped mid-send or worker restarted; verify in the Sent folder before retrying |
| Nothing sends but jobs `pending` | worker not running, broadcasting disabled, rate allowance 0, or `next_attempt_at` in the future (backoff) |
| Test send says "sent: false" | dry-run mode |

## Deployment
| Symptom | Fix |
|---|---|
| `migrate` exits non-zero | `$DC logs migrate`; DB not healthy or wrong `POSTGRES_*`; fix and `up -d` again |
| Backend `unhealthy`, "COOKIE_SECURE must be true" | production guards: set `COOKIE_SECURE=true`/`DOCS_ENABLED=false` (compose sets both) |
| Permission denied for table | DB init script did not run (volume existed before). Grant manually: see `scripts/backup/restore.sh` GRANT block |
| Caddy cannot get a certificate | DNS not pointing here / ports closed; use `TLS_MODE=internal` for LAN |
| Browser shows CORS/CSRF errors | `SITE_ADDRESS` must match the URL users open (origin is derived from it) |
| 413 on upload | nginx `client_max_body_size` is 16 MB; attachments are limited to 10 MB each |
