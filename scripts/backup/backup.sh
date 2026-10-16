#!/usr/bin/env bash
# Backs up PostgreSQL and the attachments volume together (run on the Ubuntu server).
# Usage: scripts/backup/backup.sh [env-file]   -> writes backups/<timestamp>/{db.sql.gz,attachments.tar.gz}
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ENV_FILE="${1:-.env.production}"
DC=(docker compose --env-file "$ENV_FILE" -f infra/compose.production.yaml)
set -a; . "$ENV_FILE"; set +a

out="backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$out"
"${DC[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner | gzip > "$out/db.sql.gz"
"${DC[@]}" exec -T backend tar -C /data -czf - attachments > "$out/attachments.tar.gz"
chmod 600 "$out"/*
echo "Backup written to $out"
echo "Copy it off this server; a backup on the same disk is not a disaster-recovery plan."
