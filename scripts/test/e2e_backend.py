"""Starts an isolated backend + worker for Playwright (SQLite, SMTP -> local capture sink).

Never touches real SMTP: SMTP_HOST is forced to 127.0.0.1.
"""

import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
backend = root / "backend"
tmp = root / "frontend" / "e2e" / ".tmp"
tmp.mkdir(parents=True, exist_ok=True)
db = tmp / "e2e.db"
for f in tmp.glob("e2e.db*"):
    f.unlink()

env = {
    **os.environ,
    "ENV": "development",
    "DATABASE_URL": f"sqlite:///{db.as_posix()}",
    "ATTACHMENT_DIR": str(tmp / "attachments"),
    "EMAIL_MODE": "smtp",
    "SMTP_HOST": "127.0.0.1",
    "SMTP_PORT": "1025",
    "SMTP_USE_SSL": "false",
    "SMTP_USERNAME": "",
    "SMTP_PASSWORD": "",
    "SMTP_FROM_EMAIL": "it@gohimalaya.travel",
    "SMTP_FROM_NAME": "Shangri La Tours",
    "EMAIL_RATE_PER_MINUTE": "60",
    "EMAIL_RATE_PER_DAY": "1000",
    "CORS_ORIGINS": "http://localhost:5173",
    "WORKER_POLL_SECONDS": "1",
    "BOOTSTRAP_ADMIN_PASSWORD": "e2e-password-123",
}
py = sys.executable


def run(*args: str) -> None:
    subprocess.run([py, *args], cwd=backend, env=env, check=True)


run("-m", "alembic", "upgrade", "head")
run("-m", "app.cli", "create-admin", "--email", "admin@corp.example.com", "--name", "E2E Admin")
worker = subprocess.Popen([py, "-m", "app.workers.email_worker"], cwd=backend, env=env)
try:
    subprocess.run(
        [py, "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=backend,
        env=env,
        check=False,
    )
finally:
    worker.terminate()
