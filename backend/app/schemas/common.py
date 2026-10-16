from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Category, Priority, RecipientMode, Role

T = TypeVar("T")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---- auth / users
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None = None


class SessionOut(BaseModel):
    user: UserOut
    csrf_token: str


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    role: Role
    password: str = Field(min_length=12, max_length=200)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=200)


# ---- departments / employees
class DepartmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def _strip(cls, v):
        return v.strip()


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class DepartmentOut(ORM):
    id: int
    name: str
    is_active: bool
    employee_count: int = 0


class EmployeeIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    department_id: int | None = None
    job_title: str | None = Field(default=None, max_length=200)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    department_id: int | None = None
    job_title: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class EmployeeOut(ORM):
    id: int
    name: str
    email: str
    department_id: int | None
    department_name: str | None = None
    job_title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ImportRow(BaseModel):
    row: int
    name: str
    email: str
    department: str | None
    job_title: str | None
    status: str  # ok | duplicate_in_file | exists | invalid
    message: str | None = None
    new_department: bool = False


class ImportResult(BaseModel):
    committed: bool
    total: int
    ok: int
    skipped: int
    errors: int
    rows: list[ImportRow]


# ---- notices
class NoticeBase(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body_html: str = Field(default="", max_length=200_000)
    category: Category = Category.GENERAL
    priority: Priority = Priority.NORMAL
    recipient_mode: RecipientMode = RecipientMode.ALL
    department_ids: list[int] = []
    employee_ids: list[int] = []


class NoticeIn(NoticeBase):
    pass


class NoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    body_html: str | None = Field(default=None, max_length=200_000)
    category: Category | None = None
    priority: Priority | None = None
    recipient_mode: RecipientMode | None = None
    department_ids: list[int] | None = None
    employee_ids: list[int] | None = None


class AttachmentOut(ORM):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int


class NoticeOut(ORM):
    id: int
    title: str
    body_html: str
    category: str
    priority: str
    status: str
    created_by: int
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    scheduled_at: datetime | None
    archived_at: datetime | None
    recipient_mode: str
    department_ids: list[int]
    employee_ids: list[int]
    attachments: list[AttachmentOut] = []


class NoticeListItem(ORM):
    id: int
    title: str
    category: str
    priority: str
    status: str
    created_by_name: str | None = None
    created_at: datetime
    published_at: datetime | None
    scheduled_at: datetime | None
    archived_at: datetime | None


class PreviewOut(BaseModel):
    subject: str
    html: str
    text: str
    sender: str
    recipient_count: int
    attachments: list[AttachmentOut]
    broadcast_enabled: bool
    email_mode: str


class PublishIn(BaseModel):
    confirm: bool
    expected_recipient_count: int = Field(ge=1)


class ScheduleIn(BaseModel):
    scheduled_at: datetime  # must carry an offset, e.g. 2026-12-01T09:00:00+05:45


class VersionOut(ORM):
    id: int
    version_no: int
    title: str
    subject: str
    body_html: str
    created_at: datetime


# ---- email
class TestSendIn(BaseModel):
    to: EmailStr  # exactly one address by design
    title: str = Field(min_length=1, max_length=300)
    body_html: str = Field(default="", max_length=200_000)
    category: Category = Category.GENERAL
    priority: Priority = Priority.NORMAL


class JobOut(BaseModel):
    id: int
    notice_id: int
    notice_title: str
    recipient_name: str
    recipient_email: str
    status: str
    attempt_count: int
    last_attempt_at: datetime | None
    accepted_at: datetime | None
    error: str | None


class RetryIn(BaseModel):
    include_unknown: bool = False  # unknown = may already have been accepted; opt-in only


class TemplateOut(ORM):
    id: int
    name: str
    subject_prefix: str
    header_text: str
    footer_text: str
    is_default: bool


class TemplateUpdate(BaseModel):
    subject_prefix: str | None = Field(default=None, max_length=100)
    header_text: str | None = Field(default=None, min_length=1, max_length=200)
    footer_text: str | None = Field(default=None, max_length=2000)


class BroadcastIn(BaseModel):
    enabled: bool
