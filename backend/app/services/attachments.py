import hashlib
import io
import os
import re
import uuid
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import Notice, NoticeAttachment, NoticeStatus

# extension -> (content type, accepted magic prefixes; None = must be valid UTF-8 text)
ALLOWED = {
    ".pdf": ("application/pdf", (b"%PDF",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (b"PK\x03\x04",)),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (b"PK\x03\x04",)),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", (b"PK\x03\x04",)),
    ".doc": ("application/msword", (b"\xd0\xcf\x11\xe0",)),
    ".xls": ("application/vnd.ms-excel", (b"\xd0\xcf\x11\xe0",)),
    ".ppt": ("application/vnd.ms-powerpoint", (b"\xd0\xcf\x11\xe0",)),
    ".txt": ("text/plain", None),
    ".csv": ("text/csv", None),
}  # fmt: skip


IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
MAX_IMAGE_SIDE = 1600
Image.MAX_IMAGE_PIXELS = 50_000_000  # reject decompression bombs


def is_image(att: NoticeAttachment) -> bool:
    return att.content_type.startswith("image/")


def normalize_image(data: bytes) -> bytes:
    """Re-encode as a web-sized JPEG: strips EXIF/GPS, applies rotation, keeps emails small."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:  # noqa: BLE001 - any decoder failure means "not a usable image"
        raise ApiError(422, "attachment_content", "Could not read the image file") from None
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, "white")
        flat.paste(im, mask=im.getchannel("A"))
        im = flat
    im = im.convert("RGB")
    im.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=82, optimize=True)
    return out.getvalue()


def storage_dir() -> Path:
    p = Path(get_settings().attachment_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_display_name(name: str) -> str:
    base = os.path.basename(name.replace("\\", "/"))
    return re.sub(r"[^\w.\- ()]", "_", base)[:200] or "file"


def validate(filename: str, data: bytes) -> str:
    s = get_settings()
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ApiError(422, "attachment_type", f"File type '{ext or 'none'}' is not allowed")
    if not data:
        raise ApiError(422, "attachment_empty", "File is empty")
    if len(data) > s.attachment_max_mb * 1024 * 1024:
        raise ApiError(413, "attachment_too_large", f"File exceeds {s.attachment_max_mb} MB")
    ctype, magics = ALLOWED[ext]
    if magics is None:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise ApiError(422, "attachment_content", "Text file must be UTF-8") from None
    elif not data.startswith(magics):
        raise ApiError(422, "attachment_content", "File content does not match its extension")
    return ctype


def add_attachment(db: Session, notice: Notice, filename: str, data: bytes) -> NoticeAttachment:
    if notice.status != NoticeStatus.DRAFT:
        raise ApiError(409, "invalid_state", "Attachments can only change on draft notices")
    ctype = validate(filename, data)
    if Path(filename).suffix.lower() in IMAGE_EXTS:
        data, ctype = normalize_image(data), "image/jpeg"
        filename = Path(filename).stem + ".jpg"
    total = sum(a.size_bytes for a in notice.attachments) + len(data)
    if total > get_settings().attachment_max_total_mb * 1024 * 1024:
        raise ApiError(413, "attachments_too_large", "Total attachment size limit exceeded")
    stored = uuid.uuid4().hex
    (storage_dir() / stored).write_bytes(data)
    att = NoticeAttachment(
        notice_id=notice.id, original_filename=safe_display_name(filename), stored_name=stored,
        content_type=ctype, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
    )  # fmt: skip
    db.add(att)
    db.flush()
    return att


def remove_attachment(db: Session, att: NoticeAttachment) -> None:
    if att.notice.status != NoticeStatus.DRAFT:
        raise ApiError(409, "invalid_state", "Attachments can only change on draft notices")
    path = storage_dir() / att.stored_name
    db.delete(att)
    db.flush()
    path.unlink(missing_ok=True)


def cleanup_orphans(db: Session) -> int:
    """Delete stored files that have no database row (e.g. after a failed upload)."""
    known = set(db.scalars(select(NoticeAttachment.stored_name)))
    removed = 0
    for f in storage_dir().iterdir():
        if f.is_file() and f.name not in known:
            f.unlink()
            removed += 1
    return removed
