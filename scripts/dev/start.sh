#!/usr/bin/env bash
# Runs API (:8000), email worker (dry-run) and Vite (:5173) locally. Ctrl+C stops all.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/backend"
PY=".venv/Scripts/python.exe"; [ -x "$PY" ] || PY=".venv/bin/python"
trap 'kill 0' EXIT
"$PY" -m uvicorn app.main:app --reload --port 8000 &
"$PY" -m app.workers.email_worker &
(cd "$ROOT/frontend" && npm run dev) &
wait
