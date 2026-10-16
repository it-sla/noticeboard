from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.errors import ApiError
from app.core.security import safe_equal, token_id
from app.models import ROLE_RANK, Role, User, UserSession

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class Auth:
    user: User
    session: UserSession


def client_ip(request: Request) -> str | None:
    # Behind our own reverse proxy the first X-Forwarded-For hop is the client.
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def current_auth(request: Request, db: Session = Depends(get_db)) -> Auth:
    s = get_settings()
    token = request.cookies.get(SESSION_COOKIE)
    row = db.get(UserSession, token_id(token)) if token else None
    now = utcnow()
    if (
        row is None
        or row.expires_at <= now
        or row.last_seen_at + timedelta(minutes=s.session_idle_minutes) <= now
        or not row.user.is_active
    ):
        raise ApiError(401, "not_authenticated", "Authentication required")
    if request.method in UNSAFE:
        origin = request.headers.get("origin")
        if origin and origin not in s.cors_origin_list:
            raise ApiError(403, "bad_origin", "Cross-origin request rejected")
        sent = request.headers.get("x-csrf-token", "")
        if not sent or not safe_equal(sent, row.csrf_token):
            raise ApiError(403, "csrf_failed", "Missing or invalid CSRF token")
    if (now - row.last_seen_at) > timedelta(minutes=1):
        row.last_seen_at = now
        db.commit()
    return Auth(user=row.user, session=row)


def require_role(minimum: Role):
    def dep(auth: Auth = Depends(current_auth)) -> Auth:
        if ROLE_RANK[Role(auth.user.role)] < ROLE_RANK[minimum]:
            raise ApiError(403, "forbidden", "You do not have permission for this action")
        return auth

    return dep
