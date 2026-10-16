"""Validate a production env file before deploying.

Usage: python validate_config.py <env-file> [--template]
  --template  validate structure only (for .env.example: secrets may be blank)

Exits non-zero on any error. Never prints secret values.
"""

import re
import sys
from pathlib import Path

REQUIRED = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "APP_DB_USER",
            "APP_DB_PASSWORD", "SITE_ADDRESS", "EMAIL_MODE"]  # fmt: skip
SECRETS = ["POSTGRES_PASSWORD", "APP_DB_PASSWORD"]
PLACEHOLDER = re.compile(r"(change.?me|example\.com|password|secret|^x+$)", re.I)


def parse(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def main() -> int:
    path, template = Path(sys.argv[1]), "--template" in sys.argv
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1
    env, errors = parse(path), []
    for k in REQUIRED:
        if k not in env:
            errors.append(f"{k} is missing")
    if template:
        print("OK: template structure valid" if not errors else "\n".join(f"ERROR: {e}" for e in errors))
        return 1 if errors else 0
    for k in SECRETS:
        if not env.get(k):
            errors.append(f"{k} must be set")
        elif len(env[k]) < 16:
            errors.append(f"{k} must be at least 16 characters")
    if env.get("POSTGRES_USER") == env.get("APP_DB_USER"):
        errors.append("APP_DB_USER must differ from POSTGRES_USER (least privilege)")
    if PLACEHOLDER.search(env.get("SITE_ADDRESS", "")) or not env.get("SITE_ADDRESS"):
        errors.append("SITE_ADDRESS looks like a placeholder")
    mode = env.get("EMAIL_MODE", "")
    if mode not in ("dry_run", "smtp"):
        errors.append("EMAIL_MODE must be dry_run or smtp")
    if mode == "smtp":
        for k in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL"):
            if not env.get(k):
                errors.append(f"{k} is required when EMAIL_MODE=smtp")
    if env.get("BOOTSTRAP_ADMIN_PASSWORD"):
        print("WARN: BOOTSTRAP_ADMIN_PASSWORD is set; remove it after creating the admin")
    if mode == "dry_run":
        print("NOTE: EMAIL_MODE=dry_run - no real email will be sent")
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: production config valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
