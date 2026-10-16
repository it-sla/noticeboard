from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ExpiryCategory


class ExpiryItemIn(BaseModel):
    category: ExpiryCategory
    item_type: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    employee_id: int | None = None
    reference_no: str | None = Field(default=None, max_length=100)
    issued_on: date | None = None
    expires_on: date
    reminder_days: list[int] = [60, 30, 14, 7, 1]
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("reminder_days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 730 for d in v):
            raise ValueError("reminder days must be between 0 and 730")
        return sorted(set(v), reverse=True)


class ExpiryItemUpdate(BaseModel):
    category: ExpiryCategory | None = None
    item_type: str | None = Field(default=None, min_length=1, max_length=100)
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    employee_id: int | None = None
    reference_no: str | None = Field(default=None, max_length=100)
    issued_on: date | None = None
    expires_on: date | None = None
    reminder_days: list[int] | None = None
    notes: str | None = Field(default=None, max_length=2000)
    is_archived: bool | None = None

    @field_validator("reminder_days")
    @classmethod
    def _days(cls, v):
        if v is not None and any(d < 0 or d > 730 for d in v):
            raise ValueError("reminder days must be between 0 and 730")
        return sorted(set(v), reverse=True) if v is not None else v


class ExpiryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    item_type: str
    subject: str
    employee_id: int | None
    employee_name: str | None = None
    reference_no: str | None
    issued_on: date | None
    expires_on: date
    reminder_days: list[int]
    notes: str | None
    is_archived: bool
    days_left: int = 0
    status: str = "ok"  # overdue | due7 | due30 | due60 | ok


class RenewIn(BaseModel):
    new_expires_on: date
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    note: str | None = Field(default=None, max_length=1000)


class RenewalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    old_expires_on: date
    new_expires_on: date
    cost: Decimal | None
    note: str | None
    renewed_at: datetime


class ExpirySettingsIn(BaseModel):
    enabled: bool
    extra_recipients: list[str] = []
