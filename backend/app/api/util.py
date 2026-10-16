from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=200),
    ):
        self.page, self.page_size = page, page_size


def paginate(db: Session, stmt, p: PageParams):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.execute(stmt.limit(p.page_size).offset((p.page - 1) * p.page_size))
    return total, rows


def like(term: str) -> str:
    esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"
