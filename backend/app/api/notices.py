import base64

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.util import PageParams, like, paginate
from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import Auth, client_ip, current_auth, require_role
from app.core.errors import ApiError
from app.models import (
    ROLE_RANK,
    EmailJob,
    JobStatus,
    Notice,
    NoticeAttachment,
    NoticeStatus,
    NoticeVersion,
    Role,
)
from app.schemas.common import (
    AttachmentOut,
    NoticeIn,
    NoticeListItem,
    NoticeOut,
    NoticeUpdate,
    Page,
    PreviewOut,
    PublishIn,
    ScheduleIn,
    VersionOut,
)
from app.services import attachments as att_svc
from app.services import notices as svc
from app.services.app_settings import broadcast_enabled
from app.services.audit import audit
from app.services.delivery import attachment_links, notice_images
from app.services.mailer import formataddr
from app.services.rendering import build_subject, logo_data_uri, render_email, sanitize_html

router = APIRouter(tags=["notices"])


def _out(n: Notice) -> NoticeOut:
    out = NoticeOut.model_validate(n)
    out.created_by_name = n.creator.name if n.creator else None
    return out


def _is_viewer_only(auth: Auth) -> bool:
    return ROLE_RANK[Role(auth.user.role)] < ROLE_RANK[Role.NOTICE_EDITOR]


def _get(db: Session, nid: int) -> Notice:
    n = db.get(Notice, nid)
    if not n:
        raise ApiError(404, "not_found", "Notice not found")
    return n


def _readable(auth: Auth, n: Notice) -> None:
    # Viewers only see notices that have been published.
    if _is_viewer_only(auth) and n.status not in (NoticeStatus.QUEUED, NoticeStatus.PUBLISHED):
        raise ApiError(404, "not_found", "Notice not found")


def _editable(auth: Auth, n: Notice) -> None:
    if n.status != NoticeStatus.DRAFT:
        raise ApiError(
            409, "not_editable", "Only drafts can be edited. Cancel a scheduled notice first."
        )
    is_admin = ROLE_RANK[Role(auth.user.role)] >= ROLE_RANK[Role.ADMIN]
    if not is_admin and n.created_by != auth.user.id:
        raise ApiError(403, "forbidden", "Editors can only change their own drafts")


@router.get("/notices", response_model=Page[NoticeListItem])
def list_notices(
    search: str | None = None, status: str | None = None, category: str | None = None,
    archived: bool = False, p: PageParams = Depends(), auth: Auth = Depends(current_auth),
    db: Session = Depends(get_db),
):  # fmt: skip
    q = (
        select(Notice)
        .options(joinedload(Notice.creator))
        .order_by(Notice.created_at.desc(), Notice.id.desc())
    )
    q = q.where(Notice.archived_at.is_not(None) if archived else Notice.archived_at.is_(None))
    if _is_viewer_only(auth):
        q = q.where(Notice.status.in_((NoticeStatus.QUEUED, NoticeStatus.PUBLISHED)))
    elif status:
        q = q.where(Notice.status == status)
    if category:
        q = q.where(Notice.category == category)
    if search:
        q = q.where(Notice.title.ilike(like(search.strip()), escape="\\"))
    total, rows = paginate(db, q, p)
    items = []
    for n in rows.scalars().unique():
        item = NoticeListItem.model_validate(n)
        item.created_by_name = n.creator.name if n.creator else None
        items.append(item)
    return Page(items=items, total=total, page=p.page, page_size=p.page_size)


@router.post("/notices", response_model=NoticeOut, status_code=201)
def create_notice(
    body: NoticeIn, request: Request, auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)),
    db: Session = Depends(get_db),
):  # fmt: skip
    svc.validate_selection(db, body.recipient_mode, body.department_ids, body.employee_ids)
    data = body.model_dump()
    data["body_html"] = sanitize_html(data["body_html"])
    n = Notice(**data, created_by=auth.user.id)
    db.add(n)
    db.flush()
    audit(db, "notice.create", auth.user.id, "notice", n.id, ip=client_ip(request))
    db.commit()
    return _out(n)


@router.get("/notices/{nid}", response_model=NoticeOut)
def get_notice(nid: int, auth: Auth = Depends(current_auth), db: Session = Depends(get_db)):
    n = _get(db, nid)
    _readable(auth, n)
    return _out(n)


@router.patch("/notices/{nid}", response_model=NoticeOut)
def update_notice(
    nid: int, body: NoticeUpdate, request: Request,
    auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)), db: Session = Depends(get_db),
):  # fmt: skip
    n = _get(db, nid)
    _editable(auth, n)
    data = body.model_dump(exclude_unset=True)
    mode = data.get("recipient_mode", n.recipient_mode)
    svc.validate_selection(db, mode, data.get("department_ids", n.department_ids),
                           data.get("employee_ids", n.employee_ids))  # fmt: skip
    if "body_html" in data:
        data["body_html"] = sanitize_html(data["body_html"])
    for k, v in data.items():
        setattr(n, k, v)
    audit(db, "notice.update", auth.user.id, "notice", n.id, {"fields": sorted(data)},
          client_ip(request))  # fmt: skip
    db.commit()
    return _out(n)


@router.get("/notices/{nid}/preview", response_model=PreviewOut)
def preview(
    nid: int, auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)), db: Session = Depends(get_db)
):  # fmt: skip
    n = _get(db, nid)
    s = get_settings()
    tpl = svc.default_template(db)
    html, text = render_email(
        title=n.title, body_html=n.body_html, category=n.category, priority=n.priority,
        published_at=n.published_at, header_text=tpl.header_text, footer_text=tpl.footer_text,
        attachment_links=attachment_links(n),
        logo_src=logo_data_uri(),
        images=[
            "data:image/jpeg;base64," + base64.b64encode(d).decode() for _, d in notice_images(n)
        ],
    )  # fmt: skip
    return PreviewOut(
        subject=build_subject(n.title, tpl.subject_prefix), html=html, text=text,
        sender=formataddr((s.smtp_from_name, s.smtp_from_email)),
        recipient_count=len(svc.resolve_recipients(db, n)),
        attachments=[AttachmentOut.model_validate(a) for a in n.attachments],
        broadcast_enabled=broadcast_enabled(db), email_mode=s.email_mode,
    )  # fmt: skip


@router.post("/notices/{nid}/publish")
def publish(
    nid: int, body: PublishIn, request: Request,
    auth: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    if not body.confirm:
        raise ApiError(422, "confirmation_required", "Explicit confirmation is required")
    count = svc.publish_now(
        db, nid, auth.user.id, body.expected_recipient_count, client_ip(request)
    )
    return {"status": "queued", "recipient_count": count}


@router.post("/notices/{nid}/schedule", response_model=NoticeOut)
def schedule(
    nid: int, body: ScheduleIn, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    if body.scheduled_at.tzinfo is None:
        raise ApiError(422, "invalid_schedule", "scheduled_at must include a UTC offset")
    return _out(svc.schedule(db, nid, auth.user.id, body.scheduled_at))


@router.post("/notices/{nid}/cancel", response_model=NoticeOut)
def cancel(nid: int, auth: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db)):
    return _out(svc.cancel(db, nid, auth.user.id))


@router.post("/notices/{nid}/duplicate", response_model=NoticeOut, status_code=201)
def duplicate(
    nid: int, auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)), db: Session = Depends(get_db)
):  # fmt: skip
    return _out(svc.duplicate(db, _get(db, nid), auth.user.id))


@router.post("/notices/{nid}/archive", response_model=NoticeOut)
def archive(
    nid: int, undo: bool = False, auth: Auth = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):  # fmt: skip
    from app.core.db import utcnow

    n = _get(db, nid)
    if n.status in (NoticeStatus.QUEUED, NoticeStatus.SCHEDULED):
        raise ApiError(409, "invalid_state", "Cannot archive a queued or scheduled notice")
    n.archived_at = None if undo else utcnow()
    audit(db, "notice.unarchive" if undo else "notice.archive", auth.user.id, "notice", n.id)
    db.commit()
    return _out(n)


@router.get("/notices/{nid}/versions", response_model=list[VersionOut])
def versions(nid: int, auth: Auth = Depends(current_auth), db: Session = Depends(get_db)):
    _readable(auth, _get(db, nid))
    return list(db.scalars(select(NoticeVersion).where(NoticeVersion.notice_id == nid)))


@router.get("/notices/{nid}/sending")
def sending_status(
    nid: int, _: Auth = Depends(require_role(Role.NOTICE_EDITOR)), db: Session = Depends(get_db)
):  # fmt: skip
    n = _get(db, nid)
    counts = dict(
        db.execute(
            select(EmailJob.status, func.count(EmailJob.id))
            .where(EmailJob.notice_id == nid)
            .group_by(EmailJob.status)
        ).all()
    )
    total = sum(counts.values())
    open_ = counts.get(JobStatus.PENDING, 0) + counts.get(JobStatus.SENDING, 0)
    return {"notice_status": n.status, "total": total, "counts": counts,
            "complete": total > 0 and open_ == 0}  # fmt: skip


@router.get("/notices/{nid}/recipients")
def recipient_log(
    nid: int, status: str | None = None, search: str | None = None, p: PageParams = Depends(),
    _: Auth = Depends(require_role(Role.ADMIN)), db: Session = Depends(get_db),
):  # fmt: skip
    from app.api.email import job_query, to_job_out

    q = job_query(status=status, search=search, notice_id=nid)
    total, rows = paginate(db, q, p)
    return Page(items=[to_job_out(j) for j in rows.scalars().unique()], total=total,
                page=p.page, page_size=p.page_size)  # fmt: skip


# ---------------------------------------------------------------- attachments
@router.post("/notices/{nid}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    nid: int, request: Request, file: UploadFile = File(...),
    auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)), db: Session = Depends(get_db),
):  # fmt: skip
    n = _get(db, nid)
    _editable(auth, n)
    limit = get_settings().attachment_max_mb * 1024 * 1024
    data = await file.read(limit + 1)
    a = att_svc.add_attachment(db, n, file.filename or "file", data)
    audit(
        db, "attachment.add", auth.user.id, "notice", n.id, {"attachment": a.id}, client_ip(request)
    )
    db.commit()
    return a


@router.delete("/notices/{nid}/attachments/{aid}", status_code=204)
def delete_attachment(
    nid: int, aid: int, auth: Auth = Depends(require_role(Role.NOTICE_EDITOR)),
    db: Session = Depends(get_db),
):  # fmt: skip
    a = db.get(NoticeAttachment, aid)
    if not a or a.notice_id != nid:
        raise ApiError(404, "not_found", "Attachment not found")
    _editable(auth, a.notice)
    att_svc.remove_attachment(db, a)
    audit(db, "attachment.remove", auth.user.id, "notice", nid, {"attachment": aid})
    db.commit()
    return Response(status_code=204)


@router.get("/attachments/{aid}/download")
def download_attachment(
    aid: int, auth: Auth = Depends(current_auth), db: Session = Depends(get_db)
):
    a = db.get(NoticeAttachment, aid)
    if not a:
        raise ApiError(404, "not_found", "Attachment not found")
    _readable(auth, a.notice)
    path = att_svc.storage_dir() / a.stored_name
    if not path.is_file():
        raise ApiError(404, "not_found", "Attachment file is missing")
    return FileResponse(
        path, media_type=a.content_type, filename=a.original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )  # fmt: skip
