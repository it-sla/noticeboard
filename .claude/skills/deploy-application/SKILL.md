---
name: deploy-application
description: Prepare and (only with explicit user permission) perform a production deployment to the Ubuntu Docker server. Never runs automatically.
disable-model-invocation: true
---

# deploy-application

**Hard rule: do not deploy, SSH, or touch the server unless the user explicitly asks for this deployment in the current conversation.** Preparing and validating is always allowed; executing is not.

## Prerequisites
- `bash scripts/test/run.sh all` is green (or gaps recorded as UNVERIFIED and accepted by the user).
- `.env.production` exists on the server, created by a human (never by you), with strong DB passwords, `SITE_ADDRESS`,
  `EMAIL_MODE` (keep `dry_run` for the first deploy). The SMTP password is entered by the user on the server only.
- Docker + compose plugin on the server; ports 80/443 reachable; DNS for `SITE_ADDRESS` points to the server.

## Procedure (prepare)
1. `python scripts/deploy/validate_config.py .env.production` (on the server) - must print `OK`.
2. `docker compose --env-file .env.production -f infra/compose.production.yaml config -q`.
3. Review `docs/09-DEPLOYMENT.md` with the user; confirm backup location and rollback plan.

## Procedure (execute - only after explicit permission)
1. On the server: `CONFIRM_DEPLOY=yes bash scripts/deploy/deploy.sh` (validates, backs up, builds, migrates, starts).
2. First run only: `docker compose ... run --rm backend python -m app.cli create-admin --email <admin>` (password from prompt/env).
3. Verify: `curl -fsS https://<SITE_ADDRESS>/api/health`; sign in; Settings shows mode `dry_run`, broadcasting disabled.

## Evidence of success
`docker compose ps` all healthy, `/api/health` OK, admin login works, worker log shows "worker started".

## Failure handling
Roll back per `docs/10-OPERATIONS-RUNBOOK.md` (previous image + `scripts/backup/restore.sh`). Never enable
`EMAIL_MODE=smtp` or broadcasting as part of deployment; that is a separate, explicit approval.
