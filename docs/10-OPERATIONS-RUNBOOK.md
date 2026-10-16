# Operations runbook

`DC="docker compose --env-file .env.production -f infra/compose.production.yaml"`

## Health
```bash
$DC ps                                  # all services "healthy"/running (migrate: exited 0)
curl -fsS https://<SITE_ADDRESS>/api/health
$DC logs --tail=100 backend
```

## Email worker
```bash
$DC logs -f worker                      # "worker started (email_mode=...)", per-cycle stats when something was sent
$DC restart worker                      # safe: claimed jobs left in `sending` become `unknown` after the stale window
$DC stop worker                         # pauses delivery without losing queued jobs
```
Pause sending instantly without touching containers: Settings → Disable broadcasting (worker claims nothing; scheduled notices revert to draft).

## Common situations
| Symptom | Check | Action |
|---|---|---|
| Dashboard "Pending emails" not decreasing | `$DC logs worker`; Settings: broadcasting enabled? mode? | enable broadcasting; fix SMTP; rate limit may be pacing sends (`EMAIL_RATE_PER_MINUTE`) |
| Many `failed` with "authentication failed" | SMTP username/password in `.env.production` | fix env, `$DC up -d backend worker`, Email History → Retry failed |
| `failed` with 4xx/"gave up" | provider throttling/outage | wait, then Retry failed; lower rate limits |
| `unknown` rows | worker restarted or connection dropped mid-send | check the mailbox Sent folder / ask recipient; "Retry…" only if sure it was not delivered |
| Notice stuck `queued` | any job still `pending`/`sending` | wait for completion or inspect jobs; it becomes `published` automatically |
| Login locked | 5 wrong passwords → 15 min | wait, or Super Admin resets password in Settings → Users |
| Disk filling | `docker system df`, attachments volume | `python -m app.cli cleanup-attachments` removes orphan files; prune images |

## Maintenance commands
```bash
$DC run --rm backend python -m app.cli cleanup-attachments
$DC exec db psql -U $POSTGRES_USER -d $POSTGRES_DB -c "select status,count(*) from email_jobs group by 1"
```

## Rollback
1. `git log --oneline` → pick the previous good commit; `git checkout <commit>`.
2. If the failed release applied a migration that must be undone: `$DC run --rm migrate alembic downgrade -1`
   (only if the downgrade is safe) **or** restore the pre-deploy backup:
   `CONFIRM_RESTORE=yes bash scripts/backup/restore.sh backups/<pre-deploy-ts> .env.production`.
3. `CONFIRM_DEPLOY=yes bash scripts/deploy/deploy.sh .env.production` to rebuild the old version.
4. Verify health, login, and the Email History page. Record the incident in `docs/PROGRESS.md`.
Emails already sent cannot be recalled; after a restore, compare `email_jobs` against the mailbox Sent folder before retrying anything.

## Periodic tasks
Daily backup + off-server copy; weekly look at `failed`/`unknown` jobs; monthly image updates (`$DC build --pull && $DC up -d`) and a restore test on a scratch machine.
