import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="notice-tests-")
os.environ.update(
    ENV="test",
    DATABASE_URL=f"sqlite:///{Path(_tmp, 'test.db').as_posix()}",
    ATTACHMENT_DIR=str(Path(_tmp, "attachments")),
    EMAIL_MODE="dry_run",
    COOKIE_SECURE="false",
    # pin every SMTP setting so a developer's backend/.env can never leak into tests
    SMTP_HOST="smtp.hostinger.com",
    SMTP_PORT="465",
    SMTP_USE_SSL="true",
    SMTP_USERNAME="",
    SMTP_PASSWORD="",
    SMTP_FROM_EMAIL="it@gohimalaya.travel",
    SMTP_FROM_NAME="Shangri La Tours",
    EMAIL_RATE_PER_MINUTE="20",
    EMAIL_RATE_PER_DAY="300",
    CORS_ORIGINS="http://localhost:5173",
)

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Department, Employee, Role, User  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    # Exercises the real Alembic migration instead of metadata.create_all.
    command.upgrade(Config(str(Path(__file__).parent.parent / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def _clean():
    yield
    with engine.begin() as c:
        for t in reversed(Base.metadata.sorted_tables):
            c.execute(text(f"DELETE FROM {t.name}"))  # noqa: S608 - fixed table names


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    s = get_settings()
    for k, v in dict(email_mode="dry_run", email_rate_per_minute=1000, email_rate_per_day=10000,
                     email_backoff_base_seconds=60, attachment_mode="attach",
                     login_max_failures=5).items():  # fmt: skip
        monkeypatch.setattr(s, k, v)
    return s


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def make_user(db, role: Role, email: str | None = None) -> User:
    u = User(email=email or f"{role.value.lower()}@corp.example.com", name=role.value.title(),
             role=role, password_hash=hash_password(PASSWORD))  # fmt: skip
    db.add(u)
    db.commit()
    return u


def login(email: str, password: str = PASSWORD) -> TestClient:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


@pytest.fixture
def make_client(db):
    def _make(role: Role) -> TestClient:
        user = make_user(db, role)
        return login(user.email)

    return _make


@pytest.fixture
def admin(make_client):
    return make_client(Role.ADMIN)


@pytest.fixture
def superadmin(make_client):
    return make_client(Role.SUPER_ADMIN)


@pytest.fixture
def staff(db):
    """Three IT/Ops employees + one inactive."""
    it, ops = Department(name="IT"), Department(name="Operations")
    db.add_all([it, ops])
    db.flush()
    emps = [
        Employee(name="Asha", email="asha@corp.example.com", department_id=it.id),
        Employee(name="बिकास", email="bikash@corp.example.com", department_id=ops.id),
        Employee(name="Sita", email="sita@corp.example.com", department_id=ops.id),
        Employee(name="Gone", email="gone@corp.example.com", department_id=ops.id, is_active=False),
    ]
    db.add_all(emps)
    db.commit()
    return {"it": it, "ops": ops, "emps": emps}


@pytest.fixture
def broadcast_on(superadmin):
    assert superadmin.put("/api/settings/broadcast", json={"enabled": True}).status_code == 200
