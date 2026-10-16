from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.db import UTCDateTime, utcnow


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    NOTICE_EDITOR = "NOTICE_EDITOR"
    VIEWER = "VIEWER"


ROLE_RANK = {Role.VIEWER: 0, Role.NOTICE_EDITOR: 1, Role.ADMIN: 2, Role.SUPER_ADMIN: 3}


class NoticeStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    PUBLISHED = "published"
    CANCELLED = "cancelled"


class Category(StrEnum):
    HOLIDAY = "Holiday Notice"
    GENERAL = "General Announcement"
    HR = "HR Notice"
    MEETING = "Meeting"
    URGENT = "Urgent Notice"
    POLICY = "Policy Update"
    OTHER = "Other"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class RecipientMode(StrEnum):
    ALL = "all"
    DEPARTMENTS = "departments"
    EMPLOYEES = "employees"


class JobStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    ACCEPTED = "accepted"  # accepted by SMTP server; NOT confirmed inbox delivery
    FAILED = "failed"
    UNKNOWN = "unknown"  # ambiguous outcome; needs manual reconciliation
    DRY_RUN = "dry_run"  # processed in dry-run mode; nothing was sent


class _Stamps:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class User(_Stamps, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of cookie token
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    user: Mapped[User] = relationship()


class Department(_Stamps, Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (Index("uq_departments_name_lower", func.lower(name), unique=True),)


class Employee(_Stamps, Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored lower-case
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), index=True)
    job_title: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    department: Mapped[Department | None] = relationship()


class Notice(_Stamps, Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    body_html: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default=Category.GENERAL)
    priority: Mapped[str] = mapped_column(String(10), default=Priority.NORMAL)
    status: Mapped[str] = mapped_column(String(12), default=NoticeStatus.DRAFT, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    scheduled_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    archived_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    recipient_mode: Mapped[str] = mapped_column(String(12), default=RecipientMode.ALL)
    department_ids: Mapped[list] = mapped_column(JSON, default=list)
    employee_ids: Mapped[list] = mapped_column(JSON, default=list)
    attachments: Mapped[list["NoticeAttachment"]] = relationship(
        back_populates="notice", order_by="NoticeAttachment.id"
    )
    creator: Mapped[User] = relationship(foreign_keys=[created_by])


class NoticeVersion(Base):
    """Immutable copy of the content as approved for publication."""

    __tablename__ = "notice_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"))
    version_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(400))
    body_html: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(10))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("notice_id", "version_no"),)


class NoticeRecipient(Base):
    """Recipient snapshot taken at approval; never changes with the directory."""

    __tablename__ = "notice_recipients"
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"))
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320))
    department_name: Mapped[str | None] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("notice_id", "email"),)


class EmailJob(_Stamps, Base):
    __tablename__ = "email_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id"), index=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("notice_versions.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("notice_recipients.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    status: Mapped[str] = mapped_column(String(10), default=JobStatus.PENDING)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=4)
    next_attempt_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    locked_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    error: Mapped[str | None] = mapped_column(Text)
    recipient: Mapped[NoticeRecipient] = relationship()
    notice: Mapped[Notice] = relationship()
    __table_args__ = (Index("ix_email_jobs_claim", "status", "next_attempt_at"),)


class EmailAttempt(Base):
    __tablename__ = "email_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("email_jobs.id", ondelete="CASCADE"), index=True)
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    # sending | accepted | dry_run | transient_failure | permanent_failure | unknown
    outcome: Mapped[str] = mapped_column(String(20))
    smtp_code: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class NoticeAttachment(Base):
    __tablename__ = "notice_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    notice_id: Mapped[int] = mapped_column(ForeignKey("notices.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    notice: Mapped[Notice] = relationship(back_populates="attachments")


class NoticeTemplate(Base):
    __tablename__ = "notice_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    subject_prefix: Mapped[str] = mapped_column(String(100), default="")
    header_text: Mapped[str] = mapped_column(String(200), default="Shangri La Tours")
    footer_text: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(64), index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class ExpiryCategory(StrEnum):
    VEHICLE = "vehicle"
    STAFF = "staff"
    COMPANY = "company"
    EQUIPMENT = "equipment"


class ExpiryItem(_Stamps, Base):
    """Anything with a renewal date: vehicle papers, licences, contracts, refills..."""

    __tablename__ = "expiry_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(12), index=True)
    item_type: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(200), index=True)  # plate number, person, asset...
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    reference_no: Mapped[str | None] = mapped_column(String(100))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date] = mapped_column(Date, index=True)
    reminder_days: Mapped[list] = mapped_column(JSON, default=lambda: [60, 30, 14, 7, 1])
    notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    employee: Mapped[Employee | None] = relationship()


class ExpiryRenewal(Base):
    __tablename__ = "expiry_renewals"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("expiry_items.id", ondelete="CASCADE"), index=True
    )
    old_expires_on: Mapped[date] = mapped_column(Date)
    new_expires_on: Mapped[date] = mapped_column(Date)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    note: Mapped[str | None] = mapped_column(Text)
    renewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    renewed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ExpiryReminder(Base):
    """A reminder threshold already emailed for one expiry date (-1 = 'overdue' alert)."""

    __tablename__ = "expiry_reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("expiry_items.id", ondelete="CASCADE"))
    expires_on: Mapped[date] = mapped_column(Date)
    threshold_days: Mapped[int] = mapped_column(Integer)
    sent_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("item_id", "expires_on", "threshold_days"),)
