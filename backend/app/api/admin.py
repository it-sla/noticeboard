"""Dashboard, settings and templates."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import Auth, client_ip, require_role
from app.core.errors import ApiError
from app.models import (
    AuditLog,
    EmailAttempt,
    EmailJob,
    Employee,
    JobStatus,
    Notice,
    NoticeStatus,
    NoticeTemplate,
    Role,
)
from app.schemas.common import BroadcastIn, TemplateOut, TemplateUpdate
from app.schemas.expiry import ExpirySettingsIn
from app.services import notices as svc
from app.services.app_settings import broadcast_enabled, get_setting, set_setting
from app.services.audit import audit
from app.services.mailer import SMTPFailure, SmtpMailer, redact

router = APIRouter(tags=["admin"])


@router.get("/dashboard/summary")
def summary(_: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)):
    def n_notices(*st):
        return db.scalar(select(func.count(Notice.id)).where(Notice.status.in_(st)))

    jobs = dict(db.execute(select(EmailJob.status, func.count(EmailJob.id))
                           .group_by(EmailJob.status)).all())  # fmt: skip
    return {
        "active_employees": db.scalar(
            select(func.count(Employee.id)).where(Employee.is_active.is_(True))
        ),
        "published_notices": n_notices(NoticeStatus.PUBLISHED, NoticeStatus.QUEUED),
        "scheduled_notices": n_notices(NoticeStatus.SCHEDULED),
        "pending_emails": jobs.get(JobStatus.PENDING, 0) + jobs.get(JobStatus.SENDING, 0),
        "smtp_accepted_emails": jobs.get(JobStatus.ACCEPTED, 0),
        "failed_emails": jobs.get(JobStatus.FAILED, 0),
        "unknown_emails": jobs.get(JobStatus.UNKNOWN, 0),
        "dry_run_emails": jobs.get(JobStatus.DRY_RUN, 0),
        "broadcast_enabled": broadcast_enabled(db),
        "email_mode": get_settings().email_mode,
    }


@router.get("/dashboard/activity")
def activity(_: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)):
    def brief(n: Notice):
        return {"id": n.id, "title": n.title, "status": n.status, "category": n.category,
                "published_at": n.published_at, "scheduled_at": n.scheduled_at,
                "created_at": n.created_at}  # fmt: skip

    recent = db.scalars(
        select(Notice).order_by(Notice.created_at.desc(), Notice.id.desc()).limit(5)
    )
    upcoming = db.scalars(select(Notice).where(Notice.status == NoticeStatus.SCHEDULED)
                          .order_by(Notice.scheduled_at).limit(5))  # fmt: skip
    attempts = db.execute(
        select(EmailAttempt, EmailJob)
        .join(EmailJob, EmailJob.id == EmailAttempt.job_id)
        .options(joinedload(EmailJob.recipient), joinedload(EmailJob.notice))
        .where(EmailAttempt.outcome != "sending")
        .order_by(EmailAttempt.id.desc())
        .limit(10)
    ).unique()
    failed = db.scalars(
        select(EmailJob)
        .options(joinedload(EmailJob.recipient), joinedload(EmailJob.notice))
        .where(EmailJob.status.in_((JobStatus.FAILED, JobStatus.UNKNOWN)))
        .order_by(EmailJob.id.desc())
        .limit(5)
    ).unique()
    return {
        "recent_notices": [brief(n) for n in recent],
        "upcoming_scheduled": [brief(n) for n in upcoming],
        "recent_sending": [
            {
                "at": a.attempted_at,
                "outcome": a.outcome,
                "notice": j.notice.title,
                "recipient_email": j.recipient.email,
            }
            for a, j in attempts  # fmt: skip
        ],
        "failed_warnings": [
            {
                "job_id": j.id,
                "notice": j.notice.title,
                "recipient_email": j.recipient.email,
                "status": j.status,
                "error": j.error,
            }
            for j in failed  # fmt: skip
        ],
    }


# ------------------------------------------------------------------ settings
@router.get("/settings")
def get_app_settings(_: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)):
    s = get_settings()
    return {
        "broadcast_enabled": broadcast_enabled(db),
        "email_mode": s.email_mode,
        "smtp_host": s.smtp_host, "smtp_port": s.smtp_port, "smtp_use_ssl": s.smtp_use_ssl,
        "smtp_from_email": s.smtp_from_email, "smtp_password_configured": bool(s.smtp_password),
        "rate_per_minute": s.email_rate_per_minute, "rate_per_day": s.email_rate_per_day,
        "attachment_mode": s.attachment_mode, "timezone": s.timezone,
        "expiry_alerts_enabled": get_setting(db, "expiry_alerts_enabled", True),
        "expiry_extra_recipients": get_setting(db, "expiry_extra_recipients", []),
    }  # fmt: skip


@router.put("/settings/broadcast")
def set_broadcast(
    body: BroadcastIn, request: Request, auth: Auth = Depends(require_role(Role.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    set_setting(db, "broadcast_enabled", body.enabled, auth.user.id)
    audit(
        db,
        "settings.broadcast",
        auth.user.id,
        detail={"enabled": body.enabled},
        ip=client_ip(request),
    )
    db.commit()
    return {"broadcast_enabled": body.enabled}


@router.put("/settings/expiry")
def set_expiry_settings(
    body: ExpirySettingsIn, request: Request, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    from pydantic import EmailStr, TypeAdapter, ValidationError

    ta = TypeAdapter(EmailStr)
    try:
        extra = [
            str(ta.validate_python(e.strip())).lower() for e in body.extra_recipients if e.strip()
        ]
    except ValidationError:
        raise ApiError(
            422, "invalid_email", "One of the extra recipients is not a valid email"
        ) from None
    set_setting(db, "expiry_alerts_enabled", body.enabled, auth.user.id)
    set_setting(db, "expiry_extra_recipients", extra, auth.user.id)
    audit(db, "settings.expiry", auth.user.id, detail={"enabled": body.enabled, "extra": len(extra)},
          ip=client_ip(request))  # fmt: skip
    db.commit()
    return {"expiry_alerts_enabled": body.enabled, "expiry_extra_recipients": extra}


@router.post("/settings/smtp-check")
def smtp_check(request: Request, auth: Auth = Depends(require_role(Role.SUPER_ADMIN)),
               db: Session = Depends(get_db)):  # fmt: skip
    """Connects and authenticates only; sends no message."""
    s = get_settings()
    if s.email_mode == "dry_run":
        return {"ok": True, "message": "EMAIL_MODE is dry_run: no connection attempted"}
    audit(db, "settings.smtp_check", auth.user.id, ip=client_ip(request))
    db.commit()
    try:
        return {"ok": True, "message": SmtpMailer().check()}
    except SMTPFailure as e:
        return {"ok": False, "message": redact(str(e))}


# ----------------------------------------------------------------- templates
@router.get("/templates", response_model=list[TemplateOut])
def list_templates(_: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)):
    svc.default_template(db)
    db.commit()
    return list(db.scalars(select(NoticeTemplate).order_by(NoticeTemplate.id)))


@router.patch("/templates/{tid}", response_model=TemplateOut)
def update_template(
    tid: int, body: TemplateUpdate, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    t = db.get(NoticeTemplate, tid)
    if not t:
        raise ApiError(404, "not_found", "Template not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    audit(db, "template.update", auth.user.id, "template", t.id)
    db.commit()
    return t


@router.get("/audit")
def audit_log(limit: int = 100, _: Auth = Depends(require_role(Role.SUPER_ADMIN)),
              db: Session = Depends(get_db)):  # fmt: skip
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)))
    return [{"at": r.at, "user_id": r.user_id, "action": r.action, "entity_type": r.entity_type,
             "entity_id": r.entity_id, "detail": r.detail} for r in rows]  # fmt: skip
