#!/usr/bin/env bash
# One-time local setup without Docker: venv, dependencies, SQLite database, dev seed.
# Then: scripts/dev/start.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/backend"
[ -d .venv ] || python -m venv .venv
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
"$PY" -m pip install -q -r requirements.txt pytest httpx ruff aiosmtpd
cat > .env <<'EOF'
ENV=development
DATABASE_URL=sqlite:///./dev.db
EMAIL_MODE=dry_run
EOF
"$PY" -m alembic upgrade head
echo "Create the first admin (password prompt; min 12 chars):"
"$PY" -m app.cli create-admin --email "${ADMIN_EMAIL:-admin@localhost.example.com}" --name "Administrator" || true
"$PY" -m app.cli seed-dev
(cd "$ROOT/frontend" && npm install --no-fund --no-audit)
echo "Setup done. Start with: scripts/dev/start.sh"
