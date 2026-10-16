#!/usr/bin/env bash
# Build and (re)start the production stack on the Ubuntu server. Run ON the server, in the repo.
# Refuses to run without CONFIRM_DEPLOY=yes. Does not enable EMAIL_MODE=smtp or broadcasting:
# those are explicit choices in .env.production and in the Settings page.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ENV_FILE="${1:-.env.production}"
[ "${CONFIRM_DEPLOY:-}" = "yes" ] || { echo "Refusing: set CONFIRM_DEPLOY=yes to deploy."; exit 1; }

python3 scripts/deploy/validate_config.py "$ENV_FILE"
DC=(docker compose --env-file "$ENV_FILE" -f infra/compose.production.yaml)
"${DC[@]}" config -q
[ -d backups ] || mkdir backups
if "${DC[@]}" ps --status running db 2>/dev/null | grep -q db; then
  scripts/backup/backup.sh "$ENV_FILE"      # pre-deploy backup, so rollback has data to return to
fi
"${DC[@]}" build
"${DC[@]}" up -d
"${DC[@]}" ps
echo "Deployed. Verify: curl -fsS https://\$SITE_ADDRESS/api/health   (use -k for TLS_MODE=internal)"
