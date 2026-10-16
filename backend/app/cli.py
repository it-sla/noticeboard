"""Operational commands: python -m app.cli <create-admin|cleanup-attachments|seed-dev>."""

import argparse
import getpass
import os
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password, validate_password_strength
from app.models import Department, Employee, Notice, Role, User
from app.services.attachments import cleanup_orphans
from app.services.audit import audit
from app.services.notices import default_template


def create_admin(email: str, name: str) -> int:
    """Password comes from BOOTSTRAP_ADMIN_PASSWORD or an interactive prompt - never argv."""
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    except ValidationError:
        print("Invalid email address", file=sys.stderr)
        return 2
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or getpass.getpass("Password: ")
    try:
        validate_password_strength(password)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    with SessionLocal() as db:
        if db.scalars(select(User).where(User.role == Role.SUPER_ADMIN)).first():
            print("A SUPER_ADMIN already exists; use the Settings page to manage users.",
                  file=sys.stderr)  # fmt: skip
            return 1
        user = User(
            email=email, name=name, role=Role.SUPER_ADMIN, password_hash=hash_password(password)
        )
        db.add(user)
        db.flush()
        default_template(db)
        audit(db, "user.bootstrap", user.id, "user", user.id)
        db.commit()
    print(f"Created SUPER_ADMIN {email}")
    return 0


def seed_dev() -> int:
    if get_settings().env != "development":
        print("seed-dev only runs with ENV=development", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        if db.scalars(select(Employee)).first():
            print("Employees already exist; nothing seeded.")
            return 0
        depts = {n: Department(name=n) for n in ("Administration", "IT", "Operations", "Finance")}
        db.add_all(depts.values())
        db.flush()
        # example.com addresses are reserved and can never receive mail.
        for i, (n, d) in enumerate([("Asha Gurung", "IT"), ("Bikash Thapa", "Operations"),
                                    ("Sita Sharma", "Finance"), ("Ram Karki", "Administration")]):  # fmt: skip
            db.add(Employee(name=n, email=f"dev{i}@example.com", department_id=depts[d].id,
                            job_title="Staff"))  # fmt: skip
        admin = db.scalars(select(User).where(User.role == Role.SUPER_ADMIN)).first()
        if admin:
            db.add(Notice(title="Welcome to the Notice Board",
                          body_html="<p>नमस्ते! This is a sample draft notice.</p>",
                          created_by=admin.id))  # fmt: skip
        db.commit()
    print("Seeded development data (no emails sent).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-admin")
    c.add_argument("--email", required=True)
    c.add_argument("--name", default="Administrator")
    sub.add_parser("cleanup-attachments")
    sub.add_parser("seed-dev")
    a = ap.parse_args(argv)
    if a.cmd == "create-admin":
        return create_admin(a.email, a.name)
    if a.cmd == "seed-dev":
        return seed_dev()
    with SessionLocal() as db:
        print(f"Removed {cleanup_orphans(db)} orphaned file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
