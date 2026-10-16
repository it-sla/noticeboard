from sqlalchemy.orm import Session

from app.models import AuditLog


def audit(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: object = None,
    detail: dict | None = None,
    ip: str | None = None,
) -> None:
    """Adds an audit row to the caller's transaction (commits with the action itself)."""
    db.add(
        AuditLog(
            action=action,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=None if entity_id is None else str(entity_id),
            detail=detail,
            ip=ip,
        )
    )
