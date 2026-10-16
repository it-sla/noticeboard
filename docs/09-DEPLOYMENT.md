# Deployment (Ubuntu + Docker)

> Status: **prepared, not executed.** Compose files pass `docker compose config`, but no image has been built or started
> (no Docker daemon was available during development). Do the first deployment with `EMAIL_MODE=dry_run`.
> Deploying requires the owner's explicit go-ahead.

## Requirements
Ubuntu 22.04/24.04, Docker Engine + compose plugin, a DNS name pointing to the server (or use `TLS_MODE=internal` on a LAN),
ports 80/443 open. PostgreSQL is **not** published.

## 1. Get the code and configure
```bash
git clone <your-repo-url> employee-notice-board && cd employee-notice-board
cp .env.example .env.production && chmod 600 .env.production
nano .env.production        # fill the REQUIRED values; keep EMAIL_MODE=dry_run for now
python3 scripts/deploy/validate_config.py .env.production
```
### Environment variables
| Variable | Purpose |
|---|---|
| `POSTGRES_USER/PASSWORD/DB` | database owner (used only by migrations and backups). Password ≥ 16 chars |
| `APP_DB_USER/PASSWORD` | restricted runtime role created on first DB init (must differ from owner) |
| `SITE_ADDRESS`, `TLS_MODE` | public host name; `internal` (private CA) or an ACME email for a real certificate |
| `EMAIL_MODE` | `dry_run` (default) or `smtp` |
| `SMTP_HOST/PORT/USE_SSL/USERNAME/PASSWORD/FROM_EMAIL` | Hostinger mailbox; password entered by a human on the server only |
| `EMAIL_RATE_PER_MINUTE/DAY` | set from the verified Hostinger plan limits |
| `ATTACHMENT_MODE` | `attach` (default) or `link` |
| `BOOTSTRAP_ADMIN_PASSWORD` | only for the first-admin command; remove afterwards |
Optional tuning (defaults in `backend/app/core/config.py`): session lifetimes, login lock, retry/backoff, attachment limits.

## 2. Build and start
```bash
CONFIRM_DEPLOY=yes bash scripts/deploy/deploy.sh .env.production   # validate → (backup if db running) → build → up -d
docker compose --env-file .env.production -f infra/compose.production.yaml ps
```
Migrations run automatically in the one-shot `migrate` service (as the DB owner) before `backend` starts.

## 3. First administrator
```bash
docker compose --env-file .env.production -f infra/compose.production.yaml run --rm backend \
  python -m app.cli create-admin --email you@company.com --name "Your Name"      # prompts for the password
```
Sign in at `https://<SITE_ADDRESS>`; add Departments/Employees; check Settings: mode `dry_run`, broadcasting disabled.

## 4. Stop / start / update
```bash
docker compose --env-file .env.production -f infra/compose.production.yaml down            # keeps volumes (never add -v)
docker compose --env-file .env.production -f infra/compose.production.yaml up -d
git pull && CONFIRM_DEPLOY=yes bash scripts/deploy/deploy.sh .env.production                # update (takes a backup first)
```

## 5. Backup and restore
```bash
bash scripts/backup/backup.sh .env.production            # backups/<ts>/db.sql.gz + attachments.tar.gz (copy off-server!)
CONFIRM_RESTORE=yes bash scripts/backup/restore.sh backups/<ts> .env.production   # DESTRUCTIVE
```
Back up the database and the attachments together; schedule `backup.sh` with cron (e.g. daily 02:00) and ship the files elsewhere.

## 6. Rollback
See `10-OPERATIONS-RUNBOOK.md` → Rollback.

## 7. Enabling live email (separate approval, after the dry-run deployment works)
1. Confirm the Hostinger plan's send limits; set `EMAIL_RATE_PER_MINUTE/DAY` below them.
2. Edit `.env.production`: `EMAIL_MODE=smtp`, `SMTP_PASSWORD=<typed by you>`; `docker compose ... up -d backend worker`.
3. Settings → **Test SMTP connection** (sends nothing). Then publish-page → **Send test** to your own address.
4. Only then a Super Admin enables broadcasting; start with a notice to a small department.

## Server hardening checklist
Firewall (allow 22/80/443 only), unattended security upgrades, SSH keys only, `chmod 600 .env.production`, regular off-server backups,
monitor disk space of `pgdata`/`attachments`, `docker image prune` periodically.
