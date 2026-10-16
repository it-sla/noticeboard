from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import ApiError
from app.models import (
    Department,
    EmailJob,
    Employee,
    JobStatus,
    Notice,
    NoticeRecipient,
    NoticeStatus,
    NoticeTemplate,
    NoticeVersion,
    RecipientMode,
)
from app.services.app_settings import broadcast_enabled
from app.services.audit import audit
from app.services.rendering import build_subject

DEFAULT_FOOTER = "Shangri La Tours / UPS Nepal - Internal communication."


def default_template(db: Session) -> NoticeTemplate:
    t = db.scalars(select(NoticeTemplate).where(NoticeTemplate.is_default.is_(True))).first()
    if t is None:
        t = NoticeTemplate(
            name="Default", subject_prefix="", header_text="Shangri La Tours",
            footer_text=DEFAULT_FOOTER, is_default=True,
        )  # fmt: skip
        db.add(t)
        db.flush()
    return t


def validate_selection(db: Session, mode: str, department_ids: list[int], employee_ids: list[int]):
    if mode == RecipientMode.DEPARTMENTS:
        found = set(
            db.scalars(
                select(Department.id).where(
                    Department.id.in_(department_ids), Department.is_active.is_(True)
                )
            )
        )
        if not department_ids or found != set(department_ids):
            raise ApiError(422, "invalid_recipients", "Select existing, active departments")
    elif mode == RecipientMode.EMPLOYEES:
        found = set(db.scalars(select(Employee.id).where(Employee.id.in_(employee_ids))))
        if not employee_ids or found != set(employee_ids):
            raise ApiError(422, "invalid_recipients", "Select existing employees")


def resolve_recipients(db: Session, notice: Notice) -> list[Employee]:
    """Active employees matching the notice's current selection (inactive are never included)."""
    q = (
        select(Employee)
        .where(Employee.is_active.is_(True))
        .options(joinedload(Employee.department))
        .order_by(Employee.id)
    )
    if notice.recipient_mode == RecipientMode.DEPARTMENTS:
        q = q.join(Department).where(
            Employee.department_id.in_(notice.department_ids or []),
            Department.is_active.is_(True),
        )
    elif notice.recipient_mode == RecipientMode.EMPLOYEES:
        q = q.where(Employee.id.in_(notice.employee_ids or []))
    return list(db.scalars(q).unique())


def _check_publishable(db: Session, notice: Notice) -> list[Employee]:
    if not broadcast_enabled(db):
        raise ApiError(
            409, "broadcast_disabled",
            "Email broadcasting is disabled. A Super Admin must enable it in Settings.",
        )  # fmt: skip
    has_image = any(a.content_type.startswith("image/") for a in notice.attachments)
    if not notice.title.strip() or not (notice.body_html.strip() or has_image):
        raise ApiError(422, "incomplete_notice", "A title and either text or an image are required")
    s = get_settings()
    total = sum(a.size_bytes for a in notice.attachments)
    if total > s.attachment_max_total_mb * 1024 * 1024:
        raise ApiError(422, "attachments_too_large", "Attachments exceed the total size limit")
    recipients = resolve_recipients(db, notice)
    if not recipients:
        raise ApiError(422, "no_recipients", "The selection contains no active employees")
    return recipients


def _lock(db: Session, notice_id: int) -> Notice:
    notice = db.scalars(select(Notice).where(Notice.id == notice_id).with_for_update()).first()
    if notice is None:
        raise ApiError(404, "not_found", "Notice not found")
    return notice


def _approve(db: Session, notice: Notice, user_id: int | None) -> int:
    """Freeze content + recipients and enqueue one durable job per recipient."""
    recipients = _check_publishable(db, notice)
    now = utcnow()
    s = get_settings()
    version_no = (
        db.scalar(
            select(func.max(NoticeVersion.version_no)).where(NoticeVersion.notice_id == notice.id)
        )
        or 0
    ) + 1
    template = default_template(db)
    version = NoticeVersion(
        notice_id=notice.id, version_no=version_no, title=notice.title,
        subject=build_subject(notice.title, template.subject_prefix),
        body_html=notice.body_html, category=notice.category, priority=notice.priority,
        created_by=notice.created_by,
    )  # fmt: skip
    db.add(version)
    db.flush()
    for emp in recipients:
        rec = NoticeRecipient(
            notice_id=notice.id, employee_id=emp.id, name=emp.name, email=emp.email,
            department_name=emp.department.name if emp.department else None,
        )  # fmt: skip
        db.add(rec)
        db.flush()
        db.add(
            EmailJob(
                notice_id=notice.id,
                version_id=version.id,
                recipient_id=rec.id,
                idempotency_key=f"notice:{notice.id}:recipient:{rec.id}",
                status=JobStatus.PENDING,
                max_attempts=s.email_max_attempts,
                next_attempt_at=now,
            )  # fmt: skip
        )
    notice.status = NoticeStatus.QUEUED
    notice.published_at = now
    notice.scheduled_at = None
    audit(db, "notice.publish", user_id, "notice", notice.id,
          {"recipients": len(recipients), "version": version_no})  # fmt: skip
    return len(recipients)


def publish_now(db: Session, notice_id: int, user_id: int, expected_count: int, ip=None) -> int:
    notice = _lock(db, notice_id)
    if notice.status not in (NoticeStatus.DRAFT, NoticeStatus.SCHEDULED):
        raise ApiError(409, "already_published", f"Notice is already {notice.status}")
    actual = len(_check_publishable(db, notice))
    if actual != expected_count:
        raise ApiError(
            409, "recipient_count_changed",
            f"Recipient count changed from {expected_count} to {actual}. Review and confirm again.",
            {"recipient_count": actual},
        )  # fmt: skip
    notice.published_by = user_id
    count = _approve(db, notice, user_id)
    db.commit()
    return count


def schedule(db: Session, notice_id: int, user_id: int, when: datetime) -> Notice:
    notice = _lock(db, notice_id)
    if notice.status not in (NoticeStatus.DRAFT, NoticeStatus.SCHEDULED):
        raise ApiError(409, "invalid_state", f"Cannot schedule a {notice.status} notice")
    if when <= utcnow() + timedelta(minutes=1):
        raise ApiError(422, "invalid_schedule", "Scheduled time must be in the future")
    _check_publishable(db, notice)
    notice.status, notice.scheduled_at, notice.published_by = (
        NoticeStatus.SCHEDULED, when, user_id,
    )  # fmt: skip
    audit(db, "notice.schedule", user_id, "notice", notice.id, {"at": when.isoformat()})
    db.commit()
    return notice


def cancel(db: Session, notice_id: int, user_id: int) -> Notice:
    notice = _lock(db, notice_id)
    if notice.status not in (NoticeStatus.DRAFT, NoticeStatus.SCHEDULED):
        raise ApiError(409, "invalid_state", "Only draft or scheduled notices can be cancelled")
    notice.status, notice.cancelled_at, notice.scheduled_at = (
        NoticeStatus.CANCELLED, utcnow(), None,
    )  # fmt: skip
    audit(db, "notice.cancel", user_id, "notice", notice.id)
    db.commit()
    return notice


def fire_due_scheduled(db: Session, now: datetime | None = None) -> int:
    """Publish scheduled notices that are due. Rows are claimed with SKIP LOCKED so two
    workers never publish the same notice; eligibility is revalidated at fire time."""
    now = now or utcnow()
    ids = list(
        db.scalars(
            select(Notice.id)
            .where(Notice.status == NoticeStatus.SCHEDULED, Notice.scheduled_at <= now)
            .order_by(Notice.scheduled_at)
            .with_for_update(skip_locked=True)
        )
    )
    db.rollback()  # release the claim locks; _lock() below re-checks state per notice
    fired = 0
    for nid in ids:
        notice = _lock(db, nid)
        if notice.status != NoticeStatus.SCHEDULED or notice.scheduled_at > now:
            db.rollback()
            continue
        try:
            _approve(db, notice, notice.published_by)
            fired += 1
        except ApiError as e:
            # Not eligible any more (e.g. broadcast disabled, no recipients): back to draft.
            notice.status, notice.scheduled_at = NoticeStatus.DRAFT, None
            audit(db, "notice.schedule_failed", notice.published_by, "notice", nid,
                  {"reason": e.code})  # fmt: skip
        db.commit()
    return fired


def duplicate(db: Session, notice: Notice, user_id: int) -> Notice:
    copy = Notice(
        title=f"Copy of {notice.title}"[:300], body_html=notice.body_html,
        category=notice.category, priority=notice.priority, created_by=user_id,
        recipient_mode=notice.recipient_mode, department_ids=list(notice.department_ids or []),
        employee_ids=list(notice.employee_ids or []),
    )  # fmt: skip
    db.add(copy)
    db.flush()
    audit(db, "notice.duplicate", user_id, "notice", copy.id, {"source": notice.id})
    db.commit()
    return copy
