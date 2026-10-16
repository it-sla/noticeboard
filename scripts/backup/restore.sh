#!/usr/bin/env bash
# Restores a backup made by backup.sh. DESTRUCTIVE: replaces the current database contents.
# Usage: CONFIRM_RESTORE=yes scripts/backup/restore.sh backups/<timestamp> [env-file]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
dir="${1:?usage: restore.sh backups/<timestamp> [env-file]}"
ENV_FILE="${2:-.env.production}"
[ "${CONFIRM_RESTORE:-}" = "yes" ] || { echo "Refusing: set CONFIRM_RESTORE=yes to overwrite the database."; exit 1; }
DC=(docker compose --env-file "$ENV_FILE" -f infra/compose.production.yaml)
set -a; . "$ENV_FILE"; set +a

"${DC[@]}" stop worker backend
"${DC[@]}" exec -T db psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS ${POSTGRES_DB} WITH (FORCE)" -c "CREATE DATABASE ${POSTGRES_DB}"
gunzip -c "$dir/db.sql.gz" | "${DC[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q
# default privileges for the runtime role were defined in the old database; re-grant explicitly
"${DC[@]}" exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -q \
  -c "GRANT USAGE ON SCHEMA public TO ${APP_DB_USER}" \
  -c "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO ${APP_DB_USER}" \
  -c "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO ${APP_DB_USER}"
"${DC[@]}" run --rm --no-deps -T -v "$PWD/$dir:/restore:ro" backend sh -c "tar -C /data -xzf /restore/attachments.tar.gz"
"${DC[@]}" up -d backend worker
echo "Restore complete. Check: docker compose ... logs --tail=50 backend worker"
