#!/usr/bin/env bash
# Deterministic verification. Usage: scripts/test/run.sh <step|all>
# Steps: backend-lint backend-test migrations frontend-lint frontend-typecheck frontend-test
#        frontend-build prod-config e2e all
# Works from Git Bash (Windows) and Ubuntu. Never contacts real SMTP.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [ -x "$ROOT/backend/.venv/Scripts/python.exe" ]; then PY="$ROOT/backend/.venv/Scripts/python.exe"
elif [ -x "$ROOT/backend/.venv/bin/python" ]; then PY="$ROOT/backend/.venv/bin/python"
else PY="${PYTHON:-python3}"; fi

backend-lint()      { (cd "$ROOT/backend" && "$PY" -m ruff check . && "$PY" -m ruff format --check .); }
backend-test()      { (cd "$ROOT/backend" && "$PY" -m pytest -q); }   # includes API/worker integration tests
migrations() {
  # upgrade to head on a scratch DB, then verify models == migrations (no drift) and downgrade works
  (cd "$ROOT/backend" && rm -f _migrate_check.db && export DATABASE_URL="sqlite:///./_migrate_check.db"     && "$PY" -m alembic upgrade head && "$PY" -m alembic check     && "$PY" -m alembic downgrade base && "$PY" -m alembic upgrade head; rc=$?; rm -f _migrate_check.db; exit $rc)
}
frontend-lint()      { (cd "$ROOT/frontend" && npm run --silent lint); }
frontend-typecheck() { (cd "$ROOT/frontend" && npm run --silent typecheck); }
frontend-test()      { (cd "$ROOT/frontend" && npm run --silent test); }
frontend-build()     { (cd "$ROOT/frontend" && npm run --silent build); }
prod-config() {
  "$PY" "$ROOT/scripts/deploy/validate_config.py" "${ENV_FILE:-$ROOT/.env.example}" --template
}
e2e()                { (cd "$ROOT/frontend" && npx playwright test); }

ALL=(backend-lint backend-test migrations frontend-lint frontend-typecheck frontend-test frontend-build prod-config e2e)
step="${1:-all}"
if [ "$step" = "all" ]; then
  failed=()
  for s in "${ALL[@]}"; do
    echo "=== $s"; if "$s"; then echo "PASS $s"; else echo "FAIL $s"; failed+=("$s"); fi
  done
  [ ${#failed[@]} -eq 0 ] && echo "ALL PASSED" || { echo "FAILED: ${failed[*]}"; exit 1; }
else
  "$step"
fi
