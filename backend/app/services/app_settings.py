from sqlalchemy.orm import Session

from app.models import AppSetting


def get_setting(db: Session, key: str, default):
    row = db.get(AppSetting, key)
    return row.value["v"] if row else default


def set_setting(db: Session, key: str, value, user_id: int | None) -> None:
    row = db.get(AppSetting, key)
    if row:
        row.value, row.updated_by = {"v": value}, user_id
    else:
        db.add(AppSetting(key=key, value={"v": value}, updated_by=user_id))


def broadcast_enabled(db: Session) -> bool:
    """Kill switch. Off by default: nothing is queued or sent until a SUPER_ADMIN enables it."""
    return bool(get_setting(db, "broadcast_enabled", False))
