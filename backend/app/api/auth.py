from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import CSRF_COOKIE, SESSION_COOKIE, Auth, client_ip, current_auth, require_role
from app.core.errors import ApiError
from app.core.security import hash_password, new_token, token_id, verify_password
from app.models import AuditLog, Role, User, UserSession
from app.schemas.common import LoginIn, SessionOut, UserCreate, UserOut, UserUpdate
from app.services.audit import audit

router = APIRouter(tags=["auth"])


def _set_cookies(resp: Response, token: str, csrf: str) -> None:
    s = get_settings()
    age = s.session_absolute_hours * 3600
    common = dict(max_age=age, secure=s.cookie_secure, samesite="lax", path="/")
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, **common)
    resp.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)


@router.post("/auth/login", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    s, now, ip = get_settings(), utcnow(), client_ip(request)
    recent_ip_failures = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "auth.login_failed",
            AuditLog.ip == ip,
            AuditLog.at > now - timedelta(minutes=s.login_lock_minutes),
        )
    )
    if recent_ip_failures >= s.login_ip_max_failures:
        raise ApiError(429, "rate_limited", "Too many failed attempts. Try again later.")
    email = body.email.strip().lower()
    user = db.scalars(select(User).where(User.email == email)).first()
    if user and user.locked_until and user.locked_until > now:
        raise ApiError(429, "account_locked", "Account temporarily locked. Try again later.")
    ok = verify_password(body.password, user.password_hash if user else None)
    if not (ok and user and user.is_active):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= s.login_max_failures:
                user.locked_until = now + timedelta(minutes=s.login_lock_minutes)
                user.failed_logins = 0
        audit(db, "auth.login_failed", user.id if user else None, ip=ip, detail={"email": email})
        db.commit()
        raise ApiError(401, "invalid_credentials", "Invalid email or password")
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, now
    token, csrf = new_token(), new_token()
    db.add(
        UserSession(
            id=token_id(token),
            user_id=user.id,
            csrf_token=csrf,
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=s.session_absolute_hours),
        )  # fmt: skip
    )
    audit(db, "auth.login", user.id, "user", user.id, ip=ip)
    db.commit()
    _set_cookies(response, token, csrf)
    return SessionOut(user=UserOut.model_validate(user), csrf_token=csrf)


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request, response: Response, auth: Auth = Depends(current_auth),
    db: Session = Depends(get_db),
):  # fmt: skip
    db.delete(auth.session)
    audit(db, "auth.logout", auth.user.id, "user", auth.user.id, ip=client_ip(request))
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/auth/me", response_model=SessionOut)
def me(auth: Auth = Depends(current_auth)):
    return SessionOut(user=UserOut.model_validate(auth.user), csrf_token=auth.session.csrf_token)


# ---- user administration (SUPER_ADMIN)
@router.get("/users", response_model=list[UserOut])
def list_users(_: Auth = Depends(require_role(Role.SUPER_ADMIN)), db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate, request: Request, auth: Auth = Depends(require_role(Role.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    email = body.email.lower()
    if db.scalars(select(User).where(User.email == email)).first():
        raise ApiError(409, "duplicate", "A user with this email already exists")
    user = User(
        email=email, name=body.name, role=body.role, password_hash=hash_password(body.password)
    )
    db.add(user)
    db.flush()
    audit(db, "user.create", auth.user.id, "user", user.id, {"role": body.role}, client_ip(request))
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, body: UserUpdate, request: Request,
    auth: Auth = Depends(require_role(Role.SUPER_ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    user = db.get(User, user_id)
    if not user:
        raise ApiError(404, "not_found", "User not found")
    if user.id == auth.user.id and (
        body.is_active is False or (body.role and body.role != user.role)
    ):
        raise ApiError(409, "self_change", "You cannot deactivate or demote yourself")
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for k, v in data.items():
        setattr(user, k, v)
    if body.is_active is False:
        for sess in db.scalars(select(UserSession).where(UserSession.user_id == user.id)):
            db.delete(sess)
    audit(db, "user.update", auth.user.id, "user", user.id,
          {"fields": sorted(body.model_dump(exclude_unset=True))}, client_ip(request))  # fmt: skip
    db.commit()
    return user
