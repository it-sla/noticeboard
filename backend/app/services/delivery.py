"""Outbox processing: claim -> send -> record. All state lives in the database so a crashed
worker loses nothing; jobs stuck in `sending` are flagged `unknown`, never silently resent."""

import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import utcnow
from app.models import (
    EmailAttempt,
    EmailJob,
    JobStatus,
    Notice,
    NoticeStatus,
    NoticeVersion,
)
from app.services.app_settings import broadcast_enabled
from app.services.attachments import is_image
from app.services.expiry import send_digest_if_due
from app.services.mailer import (
    AmbiguousSMTPError,
    Attach,
    PermanentSMTPError,
    SMTPFailure,
    build_message,
    redact,
)
from app.services.notices import default_template, fire_due_scheduled
from app.services.rendering import logo_bytes, render_email

TERMINAL = (JobStatus.ACCEPTED, JobStatus.FAILED, JobStatus.UNKNOWN, JobStatus.DRY_RUN)


def attachment_links(notice: Notice) -> list[tuple[str, str]]:
    s = get_settings()
    files = [a for a in notice.attachments if not is_image(a)]  # images are shown inline
    if s.attachment_mode == "attach":
        return [(a.original_filename, "") for a in files]
    return [
        (a.original_filename, f"{s.public_base_url}/api/attachments/{a.id}/download") for a in files
    ]


def notice_images(notice: Notice) -> list[tuple[int, bytes]]:
    base = Path(get_settings().attachment_dir)
    return [(a.id, (base / a.stored_name).read_bytes()) for a in notice.attachments if is_image(a)]


def compose(db: Session, job: EmailJob, *, test_prefix: str = ""):
    """Build the EmailMessage for a job from its frozen version + recipient snapshot."""
    s = get_settings()
    version: NoticeVersion = db.get(NoticeVersion, job.version_id)
    notice = job.notice
    template = default_template(db)
    images = notice_images(notice)
    html, text = render_email(
        title=version.title, body_html=version.body_html, category=version.category,
        priority=version.priority, published_at=notice.published_at,
        header_text=template.header_text, footer_text=template.footer_text,
        attachment_links=attachment_links(notice),
        images=[f"cid:img{i}" for i, _ in images],
    )  # fmt: skip
    files = []
    if s.attachment_mode == "attach":
        base = Path(s.attachment_dir)
        files = [
            Attach(a.original_filename, a.content_type, (base / a.stored_name).read_bytes())
            for a in notice.attachments
            if not is_image(a)
        ]
    return build_message(
        to_email=job.recipient.email, to_name=job.recipient.name,
        subject=f"{test_prefix}{version.subject}", html=html, text=text, attachments=files,
        inline_logo=logo_bytes(),
        inline_images=[(f"img{i}", data) for i, data in images],
    )  # fmt: skip


def recover_stale(db: Session, now: datetime) -> int:
    cutoff = now - timedelta(minutes=get_settings().email_sending_stale_minutes)
    jobs = list(
        db.scalars(
            select(EmailJob)
            .where(EmailJob.status == JobStatus.SENDING, EmailJob.locked_at < cutoff)
            .with_for_update(skip_locked=True)
        )
    )
    for job in jobs:
        job.status, job.locked_at = JobStatus.UNKNOWN, None
        job.error = "Worker stopped while sending; the message may have been accepted. Reconcile."
        db.execute(
            update(EmailAttempt)
            .where(EmailAttempt.job_id == job.id, EmailAttempt.outcome == "sending")
            .values(outcome="unknown", error=job.error)
        )
    db.commit()
    return len(jobs)


def _allowance(db: Session, now: datetime) -> int:
    s = get_settings()

    def sent_since(delta):
        return db.scalar(
            select(func.count(EmailAttempt.id)).where(
                EmailAttempt.outcome.in_(("accepted", "unknown", "sending")),
                EmailAttempt.attempted_at > now - delta,
            )
        )

    return max(0, min(s.email_rate_per_minute - sent_since(timedelta(minutes=1)),
                      s.email_rate_per_day - sent_since(timedelta(days=1))))  # fmt: skip


def claim_jobs(db: Session, now: datetime, limit: int) -> list[int]:
    if limit <= 0 or not broadcast_enabled(db):
        return []
    jobs = list(
        db.scalars(
            select(EmailJob)
            .where(EmailJob.status == JobStatus.PENDING, EmailJob.next_attempt_at <= now)
            .order_by(EmailJob.next_attempt_at, EmailJob.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    for job in jobs:
        job.status, job.locked_at = JobStatus.SENDING, now
        job.attempt_count += 1
        job.last_attempt_at = now
        db.add(EmailAttempt(job_id=job.id, attempted_at=now, outcome="sending"))
    db.commit()
    return [j.id for j in jobs]


def _finish(db: Session, job: EmailJob, outcome: str, status: str, *, code=None, error=None,
            ms=None, retry_at: datetime | None = None):  # fmt: skip
    attempt = db.scalars(
        select(EmailAttempt)
        .where(EmailAttempt.job_id == job.id, EmailAttempt.outcome == "sending")
        .order_by(EmailAttempt.id.desc())
    ).first()
    attempt.outcome, attempt.smtp_code, attempt.error, attempt.duration_ms = (
        outcome,
        code,
        error,
        ms,
    )
    job.status, job.locked_at, job.error = status, None, error
    if retry_at:
        job.next_attempt_at = retry_at
    if status in (JobStatus.ACCEPTED,):
        job.accepted_at = utcnow()
    db.commit()


def send_job(db: Session, job_id: int, mailer) -> str:
    job = db.get(EmailJob, job_id)
    s = get_settings()
    started = time.monotonic()
    ms = lambda: int((time.monotonic() - started) * 1000)  # noqa: E731
    try:
        msg = compose(db, job)
        mailer.send(msg)
    except AmbiguousSMTPError as e:
        _finish(db, job, "unknown", JobStatus.UNKNOWN, error=redact(str(e)), ms=ms())
    except PermanentSMTPError as e:
        _finish(db, job, "permanent_failure", JobStatus.FAILED, code=e.code,
                error=redact(str(e)), ms=ms())  # fmt: skip
    except SMTPFailure as e:  # transient
        if job.attempt_count >= job.max_attempts:
            _finish(db, job, "transient_failure", JobStatus.FAILED, code=e.code,
                    error=f"Gave up after {job.attempt_count} attempts: {redact(str(e))}", ms=ms())  # fmt: skip
        else:
            delay = min(s.email_backoff_base_seconds * 2 ** (job.attempt_count - 1),
                        s.email_backoff_max_seconds)  # fmt: skip
            _finish(db, job, "transient_failure", JobStatus.PENDING, code=e.code,
                    error=redact(str(e)), ms=ms(), retry_at=utcnow() + timedelta(seconds=delay))  # fmt: skip
    except Exception as e:  # noqa: BLE001 - e.g. attachment file missing; never retry blindly
        _finish(db, job, "permanent_failure", JobStatus.FAILED,
                error=redact(f"{type(e).__name__}: {e}"), ms=ms())  # fmt: skip
    else:
        if getattr(mailer, "dry_run", False):
            _finish(
                db, job, "dry_run", JobStatus.DRY_RUN, error="dry-run: nothing was sent", ms=ms()
            )
        else:
            _finish(db, job, "accepted", JobStatus.ACCEPTED, ms=ms())
    return job.status


def finalize_notices(db: Session) -> int:
    """queued -> published once every job has left pending/sending."""
    open_notice_ids = select(EmailJob.notice_id).where(
        EmailJob.status.in_((JobStatus.PENDING, JobStatus.SENDING))
    )
    res = db.execute(
        update(Notice)
        .where(Notice.status == NoticeStatus.QUEUED, Notice.id.not_in(open_notice_ids))
        .values(status=NoticeStatus.PUBLISHED)
    )
    db.commit()
    return res.rowcount


def run_once(db: Session, mailer, now: datetime | None = None) -> dict:
    now = now or utcnow()
    stats = {"recovered": recover_stale(db, now), "scheduled": fire_due_scheduled(db, now)}
    ids = claim_jobs(db, now, min(_allowance(db, now), 50))
    for jid in ids:
        send_job(db, jid, mailer)
    stats["sent"] = len(ids)
    stats["finalized"] = finalize_notices(db)
    stats["expiry_digest"] = 1 if send_digest_if_due(db, mailer, now) == "sent" else 0
    return stats
