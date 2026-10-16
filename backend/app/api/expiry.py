import csv
import io

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.email import _csv_safe
from app.api.util import PageParams, like, paginate
from app.core.db import get_db
from app.core.deps import Auth, client_ip, require_role
from app.core.errors import ApiError
from app.models import Employee, ExpiryItem, ExpiryRenewal, Role
from app.schemas.common import Page
from app.schemas.expiry import (
    ExpiryItemIn,
    ExpiryItemOut,
    ExpiryItemUpdate,
    RenewalOut,
    RenewIn,
)
from app.services import expiry as svc
from app.services.audit import audit

router = APIRouter(prefix="/expiry", tags=["expiry"])
ADMIN = Depends(require_role(Role.ADMIN))

# status filter -> (min_days, max_days) inclusive; None = unbounded
_RANGES = {
    "overdue": (None, -1),
    "due7": (0, 7),
    "due30": (8, 30),
    "due60": (31, 60),
    "ok": (61, None),
}


def _out(it: ExpiryItem, today) -> ExpiryItemOut:
    out = ExpiryItemOut.model_validate(it)
    out.days_left = (it.expires_on - today).days
    out.status = svc.status_of(out.days_left)
    out.employee_name = it.employee.name if it.employee else None
    return out


def _get(db: Session, item_id: int) -> ExpiryItem:
    it = db.get(ExpiryItem, item_id)
    if not it:
        raise ApiError(404, "not_found", "Item not found")
    return it


def _check_employee(db: Session, employee_id: int | None) -> None:
    if employee_id is not None and not db.get(Employee, employee_id):
        raise ApiError(422, "invalid_employee", "Employee does not exist")


def _query(category, status, search, archived, today):
    from datetime import timedelta

    q = (
        select(ExpiryItem)
        .options(joinedload(ExpiryItem.employee))
        .order_by(ExpiryItem.expires_on, ExpiryItem.id)
    )
    q = q.where(ExpiryItem.is_archived.is_(archived))
    if category:
        q = q.where(ExpiryItem.category == category)
    if status in _RANGES:
        lo, hi = _RANGES[status]
        if lo is not None:
            q = q.where(ExpiryItem.expires_on >= today + timedelta(days=lo))
        if hi is not None:
            q = q.where(ExpiryItem.expires_on <= today + timedelta(days=hi))
    if search:
        t = like(search.strip())
        q = q.where(or_(ExpiryItem.subject.ilike(t, escape="\\"), ExpiryItem.item_type.ilike(t, escape="\\"),
                        ExpiryItem.reference_no.ilike(t, escape="\\")))  # fmt: skip
    return q


@router.get("/presets")
def presets(_: Auth = ADMIN):
    return svc.PRESETS


@router.get("/summary")
def summary(_: Auth = ADMIN, db: Session = Depends(get_db)):
    return svc.summary(db, svc.today_local())


@router.get("/alerts")
def alerts(_: Auth = ADMIN, db: Session = Depends(get_db)):
    return svc.alerts(db, svc.today_local())


@router.get("/items", response_model=Page[ExpiryItemOut])
def list_items(
    category: str | None = None, status: str | None = None, search: str | None = None,
    archived: bool = Query(False), p: PageParams = Depends(), _: Auth = ADMIN,
    db: Session = Depends(get_db),
):  # fmt: skip
    today = svc.today_local()
    total, rows = paginate(db, _query(category, status, search, archived, today), p)
    return Page(items=[_out(i, today) for i in rows.scalars().unique()], total=total,
                page=p.page, page_size=p.page_size)  # fmt: skip


@router.post("/items", response_model=ExpiryItemOut, status_code=201)
def create_item(
    body: ExpiryItemIn, request: Request, auth: Auth = ADMIN, db: Session = Depends(get_db)
):
    _check_employee(db, body.employee_id)
    it = ExpiryItem(**body.model_dump(), created_by=auth.user.id)
    db.add(it)
    db.flush()
    audit(db, "expiry.create", auth.user.id, "expiry_item", it.id, ip=client_ip(request))
    db.commit()
    db.refresh(it)
    return _out(it, svc.today_local())


@router.patch("/items/{item_id}", response_model=ExpiryItemOut)
def update_item(item_id: int, body: ExpiryItemUpdate, request: Request, auth: Auth = ADMIN,
                db: Session = Depends(get_db)):  # fmt: skip
    it = _get(db, item_id)
    data = body.model_dump(exclude_unset=True)
    if "employee_id" in data:
        _check_employee(db, data["employee_id"])
    for k, v in data.items():
        setattr(it, k, v)
    audit(
        db,
        "expiry.update",
        auth.user.id,
        "expiry_item",
        it.id,
        {"fields": sorted(data)},
        client_ip(request),
    )
    db.commit()
    db.refresh(it)
    return _out(it, svc.today_local())


@router.delete("/items/{item_id}", response_model=ExpiryItemOut)
def archive_item(item_id: int, request: Request, auth: Auth = ADMIN, db: Session = Depends(get_db)):
    """Archive (soft delete): the item and its renewal history are kept."""
    it = _get(db, item_id)
    it.is_archived = True
    audit(db, "expiry.archive", auth.user.id, "expiry_item", it.id, ip=client_ip(request))
    db.commit()
    return _out(it, svc.today_local())


@router.post("/items/{item_id}/renew", response_model=ExpiryItemOut)
def renew_item(item_id: int, body: RenewIn, auth: Auth = ADMIN, db: Session = Depends(get_db)):
    it = _get(db, item_id)
    svc.renew(db, it, body.new_expires_on, body.cost, body.note, auth.user.id)
    db.commit()
    db.refresh(it)
    return _out(it, svc.today_local())


@router.get("/items/{item_id}/history", response_model=list[RenewalOut])
def history(item_id: int, _: Auth = ADMIN, db: Session = Depends(get_db)):
    _get(db, item_id)
    return list(db.scalars(select(ExpiryRenewal).where(ExpiryRenewal.item_id == item_id)
                           .order_by(ExpiryRenewal.id.desc())))  # fmt: skip


@router.get("/export")
def export(category: str | None = None, status: str | None = None, search: str | None = None,
           request: Request = None, auth: Auth = ADMIN, db: Session = Depends(get_db)):  # fmt: skip
    today = svc.today_local()
    rows = [
        _out(i, today) for i in db.scalars(_query(category, status, search, False, today)).unique()
    ]
    audit(db, "expiry.export", auth.user.id, detail={"rows": len(rows)}, ip=client_ip(request))
    db.commit()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "category",
            "type",
            "subject",
            "reference",
            "issued_on",
            "expires_on",
            "days_left",
            "status",
            "notes",
        ]
    )
    for r in rows:
        w.writerow([_csv_safe(x) for x in (r.category, r.item_type, r.subject, r.reference_no, r.issued_on,
                                           r.expires_on, r.days_left, r.status, r.notes)])  # fmt: skip
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": 'attachment; filename="expiry-items.csv"'})  # fmt: skip
