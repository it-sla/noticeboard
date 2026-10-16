import csv
import io
from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.api.util import PageParams, like, paginate
from app.core.config import get_settings
from app.core.db import get_db, utcnow
from app.core.deps import Auth, client_ip, require_role
from app.core.errors import ApiError
from app.models import (
    AuditLog,
    EmailAttempt,
    EmailJob,
    JobStatus,
    Notice,
    NoticeRecipient,
    NoticeStatus,
    Role,
)
from app.schemas.common import JobOut, Page, RetryIn, TestSendIn
from app.services import notices as svc
from app.services.audit import audit
from app.services.mailer import (
    SMTPFailure,
    build_message,
    get_mailer,
    redact,
)
from app.services.rendering import build_subject, logo_bytes, render_email, sanitize_html

router = APIRouter(prefix="/email", tags=["email"])


def job_query(*, status=None, search=None, notice_id=None, date_from: date | None = None,
              date_to: date | None = None):  # fmt: skip
    q = (
        select(EmailJob)
        .join(EmailJob.recipient)
        .options(joinedload(EmailJob.recipient), joinedload(EmailJob.notice))
        .order_by(EmailJob.id.desc())
    )
    if status:
        q = q.where(EmailJob.status == status)
    if notice_id:
        q = q.where(EmailJob.notice_id == notice_id)
    if search:
        t = like(search.strip())
        q = q.where(
            or_(
                NoticeRecipient.email.ilike(t, escape="\\"),
                NoticeRecipient.name.ilike(t, escape="\\"),
            )
        )
    if date_from:
        q = q.where(EmailJob.created_at >= datetime.combine(date_from, time.min, UTC))
    if date_to:
        q = q.where(
            EmailJob.created_at < datetime.combine(date_to + timedelta(days=1), time.min, UTC)
        )
    return q


def to_job_out(j: EmailJob) -> JobOut:
    return JobOut(
        id=j.id, notice_id=j.notice_id, notice_title=j.notice.title,
        recipient_name=j.recipient.name, recipient_email=j.recipient.email, status=j.status,
        attempt_count=j.attempt_count, last_attempt_at=j.last_attempt_at,
        accepted_at=j.accepted_at, error=j.error,
    )  # fmt: skip


@router.get("/jobs", response_model=Page[JobOut])
def list_jobs(
    status: str | None = None, search: str | None = None, notice_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None, p: PageParams = Depends(),
    _: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    total, rows = paginate(db, job_query(status=status, search=search, notice_id=notice_id,
                                         date_from=date_from, date_to=date_to), p)  # fmt: skip
    return Page(items=[to_job_out(j) for j in rows.scalars().unique()], total=total,
                page=p.page, page_size=p.page_size)  # fmt: skip


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # spreadsheet formula guard


@router.get("/jobs/export")
def export_jobs(
    status: str | None = None, search: str | None = None, notice_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None, request: Request = None,
    auth: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    q = job_query(status=status, search=search, notice_id=notice_id, date_from=date_from,
                  date_to=date_to).limit(50_000)  # fmt: skip
    rows = list(db.scalars(q).unique())
    audit(db, "email.export", auth.user.id, detail={"rows": len(rows)}, ip=client_ip(request))
    db.commit()

    def gen():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["notice", "recipient", "email", "status", "attempts", "last_attempt",
                    "accepted_at", "error"])  # fmt: skip
        yield buf.getvalue()
        for j in rows:
            buf.seek(0), buf.truncate()
            w.writerow([_csv_safe(x) for x in (
                j.notice.title, j.recipient.name, j.recipient.email, j.status, j.attempt_count,
                j.last_attempt_at and j.last_attempt_at.isoformat(),
                j.accepted_at and j.accepted_at.isoformat(), j.error)])  # fmt: skip
            yield buf.getvalue()

    return StreamingResponse(
        gen(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="email-history.csv"'},
    )  # fmt: skip


@router.get("/jobs/{job_id}/attempts")
def job_attempts(job_id: int, _: Auth = Depends(require_role(Role.ADMIN)),
                 db: Session = Depends(get_db)):  # fmt: skip
    rows = db.scalars(select(EmailAttempt).where(EmailAttempt.job_id == job_id)
                      .order_by(EmailAttempt.id))  # fmt: skip
    return [{"at": a.attempted_at, "outcome": a.outcome, "smtp_code": a.smtp_code,
             "error": a.error, "duration_ms": a.duration_ms} for a in rows]  # fmt: skip


def _requeue(
    db: Session, statuses: list[str], job_ids: list[int] | None, notice_id: int | None
) -> int:
    q = update(EmailJob).where(EmailJob.status.in_(statuses))
    if job_ids is not None:
        q = q.where(EmailJob.id.in_(job_ids))
    if notice_id:
        q = q.where(EmailJob.notice_id == notice_id)
    res = db.execute(
        q.values(
            status=JobStatus.PENDING,
            next_attempt_at=utcnow(),
            error=None,
            locked_at=None,
            max_attempts=EmailJob.attempt_count + get_settings().email_max_attempts,
        )  # fmt: skip
    )
    # A requeued job reopens its notice so it is finalised again once the retries finish.
    db.execute(
        update(Notice)
        .where(
            Notice.status == NoticeStatus.PUBLISHED,
            Notice.id.in_(select(EmailJob.notice_id).where(EmailJob.status == JobStatus.PENDING)),
        )
        .values(status=NoticeStatus.QUEUED)
    )
    return res.rowcount


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: int, body: RetryIn, request: Request, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    statuses = [JobStatus.FAILED] + ([JobStatus.UNKNOWN] if body.include_unknown else [])
    n = _requeue(db, statuses, [job_id], None)
    if n == 0:
        raise ApiError(
            409, "not_retryable", "Only failed jobs (or unknown, when confirmed) can be retried"
        )
    audit(db, "email.retry", auth.user.id, "email_job", job_id,
          {"include_unknown": body.include_unknown}, client_ip(request))  # fmt: skip
    db.commit()
    return {"requeued": n}


@router.post("/notices/{notice_id}/retry-failed")
def retry_failed(
    notice_id: int, body: RetryIn, request: Request,
    auth: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    statuses = [JobStatus.FAILED] + ([JobStatus.UNKNOWN] if body.include_unknown else [])
    n = _requeue(db, statuses, None, notice_id)
    audit(db, "email.retry_failed", auth.user.id, "notice", notice_id,
          {"requeued": n, "include_unknown": body.include_unknown}, client_ip(request))  # fmt: skip
    db.commit()
    return {"requeued": n}


@router.post("/test")
def send_test(
    body: TestSendIn, request: Request, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    """Sends ONE message to ONE address. Never touches the recipient list or the outbox."""
    s = get_settings()
    since = utcnow() - timedelta(hours=1)
    used = db.scalar(select(func.count(AuditLog.id)).where(
        AuditLog.action == "email.test_send", AuditLog.user_id == auth.user.id,
        AuditLog.at > since))  # fmt: skip
    if used >= s.test_send_per_hour:
        raise ApiError(429, "rate_limited", "Test-send limit reached. Try again later.")
    tpl = svc.default_template(db)
    html, text = render_email(
        title=body.title, body_html=sanitize_html(body.body_html), category=body.category,
        priority=body.priority, published_at=None, header_text=tpl.header_text,
        footer_text=tpl.footer_text, attachment_links=[],
    )  # fmt: skip
    msg = build_message(to_email=body.to, to_name=None,
                        subject="[TEST] " + build_subject(body.title, tpl.subject_prefix),
                        html=html, text=text, inline_logo=logo_bytes())  # fmt: skip
    mailer = get_mailer()
    audit(db, "email.test_send", auth.user.id, detail={"mode": s.email_mode}, ip=client_ip(request))
    db.commit()  # counts toward the hourly limit even if the send fails
    try:
        mailer.send(msg)
    except SMTPFailure as e:
        raise ApiError(502, "smtp_error", redact(str(e))) from None
    return {"mode": s.email_mode, "sent": not mailer.dry_run,
            "message": "Dry-run: nothing was sent" if mailer.dry_run else "Accepted by SMTP server"}  # fmt: skip
