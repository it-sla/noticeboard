"""Expiry tracker: status maths, renewals and the daily admin digest."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import ApiError
from app.models import ExpiryItem, ExpiryReminder, ExpiryRenewal, Role, User
from app.services.app_settings import get_setting, set_setting
from app.services.audit import audit
from app.services.mailer import SMTPFailure, build_message, redact
from app.services.rendering import _env, logo_bytes

log = logging.getLogger("expiry")

PRESETS = {
    "vehicle": ["Registration (Bluebook)", "Pollution test", "Insurance", "Route permit", "Annual vehicle tax"],
    "staff": ["Driving licence", "Passport", "Visa / Work permit", "Contract"],
    "company": ["PAN / VAT renewal", "Trade licence", "Agency / airline licence", "Lease agreement"],
    "equipment": ["Fire extinguisher refill", "Domain / SSL / software", "AMC contract", "Warranty"],
}  # fmt: skip
DIGEST_HOUR = 8  # local (Asia/Kathmandu) hour after which the daily digest may go out
OVERDUE = -1  # pseudo-threshold recorded once an item has been reported as overdue


def today_local(now: datetime | None = None) -> date:
    return (now or utcnow()).astimezone(ZoneInfo(get_settings().timezone)).date()


def status_of(days_left: int) -> str:
    if days_left < 0:
        return "overdue"
    if days_left <= 7:
        return "due7"
    if days_left <= 30:
        return "due30"
    if days_left <= 60:
        return "due60"
    return "ok"


def active_items(db: Session) -> list[ExpiryItem]:
    return list(
        db.scalars(
            select(ExpiryItem)
            .options(joinedload(ExpiryItem.employee))
            .where(ExpiryItem.is_archived.is_(False))
            .order_by(ExpiryItem.expires_on, ExpiryItem.id)
        )
    )


def summary(db: Session, today: date) -> dict:
    counts = {"overdue": 0, "due7": 0, "due30": 0, "due60": 0, "ok": 0}
    by_cat: dict[str, int] = {}
    for it in active_items(db):
        counts[status_of((it.expires_on - today).days)] += 1
        by_cat[it.category] = by_cat.get(it.category, 0) + 1
    return {**counts, "total": sum(counts.values()), "by_category": by_cat}


def alerts(db: Session, today: date, limit: int = 8) -> dict:
    """Bell icon: overdue + due within 7 days, most urgent first."""
    urgent = [it for it in active_items(db) if (it.expires_on - today).days <= 7]
    return {
        "count": len(urgent),
        "items": [
            {"id": it.id, "subject": it.subject, "item_type": it.item_type,
             "expires_on": it.expires_on, "days_left": (it.expires_on - today).days}
            for it in urgent[:limit]
        ],
    }  # fmt: skip


def renew(db: Session, item: ExpiryItem, new_expires_on: date, cost, note, user_id: int) -> None:
    if new_expires_on <= item.expires_on:
        raise ApiError(422, "invalid_renewal", "The new expiry date must be after the current one")
    db.add(
        ExpiryRenewal(
            item_id=item.id, old_expires_on=item.expires_on, new_expires_on=new_expires_on,
            cost=cost, note=note, renewed_by=user_id,
        )
    )  # fmt: skip
    audit(db, "expiry.renew", user_id, "expiry_item", item.id,
          {"from": item.expires_on.isoformat(), "to": new_expires_on.isoformat()})  # fmt: skip
    item.expires_on = new_expires_on


# ------------------------------------------------------------------ digest
def _sent_map(db: Session) -> dict[tuple[int, date], set[int]]:
    out: dict[tuple[int, date], set[int]] = {}
    for r in db.scalars(select(ExpiryReminder)):
        out.setdefault((r.item_id, r.expires_on), set()).add(r.threshold_days)
    return out


def collect(db: Session, today: date, monday: bool):
    """Returns (due_soon, overdue, records) where records are (item, thresholds) to persist once sent."""
    sent = _sent_map(db)
    due_soon, overdue, records = [], [], []
    for it in active_items(db):
        left = (it.expires_on - today).days
        done = sent.get((it.id, it.expires_on), set())
        if left < 0:
            new = OVERDUE not in done
            if new or monday:
                overdue.append((it, left))
            if new:
                records.append((it, {OVERDUE, *(it.reminder_days or [])} - done))
            continue
        crossed = {t for t in (it.reminder_days or []) if left <= t and t not in done}
        if crossed:
            due_soon.append((it, left))
            records.append((it, crossed))
    return due_soon, overdue, records


def recipients(db: Session) -> list[str]:
    admins = db.scalars(
        select(User.email).where(
            User.is_active.is_(True), User.role.in_((Role.ADMIN, Role.SUPER_ADMIN))
        )
    )
    extra = get_setting(db, "expiry_extra_recipients", [])
    seen: dict[str, None] = {}
    for e in [*admins, *extra]:
        seen.setdefault(e.strip().lower(), None)
    return list(seen)


def send_digest_if_due(db: Session, mailer, now: datetime | None = None) -> str:
    """Daily admin digest. Returns: sent | dry_run | nothing | wait | failed."""
    now = now or utcnow()
    local = now.astimezone(ZoneInfo(get_settings().timezone))
    today = local.date()
    if local.hour < DIGEST_HOUR or not get_setting(db, "expiry_alerts_enabled", True):
        return "wait"
    if get_setting(db, "expiry_last_digest", "") == today.isoformat():
        return "wait"
    last_try = get_setting(db, "expiry_last_attempt", "")
    if last_try and now - datetime.fromisoformat(last_try) < timedelta(hours=1):
        return "wait"

    due_soon, overdue, records = collect(db, today, monday=today.weekday() == 0)
    to = recipients(db)
    if not (due_soon or overdue) or not to:
        set_setting(db, "expiry_last_digest", today.isoformat(), None)
        db.commit()
        return "nothing"

    html = _env.get_template("expiry_digest.html").render(
        logo_src="cid:logo", today=today.strftime("%d %B %Y"),
        due_soon=[(i, d) for i, d in due_soon], overdue=[(i, abs(d)) for i, d in overdue],
        base_url=get_settings().public_base_url,
    )  # fmt: skip
    lines = [f"Expiry reminders - {today.isoformat()}", ""]
    lines += ["OVERDUE:"] + [
        f"- {i.subject} / {i.item_type}: expired {abs(d)} day(s) ago ({i.expires_on})"
        for i, d in overdue
    ]
    lines += ["", "DUE SOON:"] + [f"- {i.subject} / {i.item_type}: {d} day(s) left ({i.expires_on})" for i, d in due_soon]  # fmt: skip
    subject = f"Expiry reminders: {len(overdue)} overdue, {len(due_soon)} due soon"
    msg = build_message(to_email=to[0], to_name=None, subject=subject, html=html,
                        text="\n".join(lines), inline_logo=logo_bytes())  # fmt: skip
    msg.replace_header("To", ", ".join(to))

    if getattr(mailer, "dry_run", False):
        set_setting(db, "expiry_last_digest", today.isoformat(), None)
        db.commit()
        return "dry_run"
    set_setting(db, "expiry_last_attempt", now.isoformat(), None)
    db.commit()
    try:
        mailer.send(msg)
    except SMTPFailure as e:
        log.warning("expiry digest failed: %s", redact(str(e)))
        return "failed"  # nothing recorded -> tried again after an hour
    for item, thresholds in records:
        for t in thresholds:
            db.add(ExpiryReminder(item_id=item.id, expires_on=item.expires_on, threshold_days=t))
    set_setting(db, "expiry_last_digest", today.isoformat(), None)
    db.commit()
    return "sent"
