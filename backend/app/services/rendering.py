"""Sanitising and rendering notices to subject / HTML / plain-text email parts."""

import base64
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import nh3
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "ul", "ol", "li", "h1", "h2", "h3",
    "blockquote", "a", "hr", "table", "thead", "tbody", "tr", "th", "td", "span",
}  # fmt: skip
_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates"),
    autoescape=select_autoescape(["html"]),
)


LOGO_PATH = Path(__file__).resolve().parent.parent / "templates" / "logo.jpg"


def logo_bytes() -> bytes:
    return LOGO_PATH.read_bytes()


def logo_data_uri() -> str:
    return "data:image/jpeg;base64," + base64.b64encode(logo_bytes()).decode()


def sanitize_html(html: str) -> str:
    return nh3.clean(
        html or "",
        tags=ALLOWED_TAGS,
        attributes={"a": {"href"}},
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
    )


class _Text(HTMLParser):
    BLOCK = {"p", "br", "li", "h1", "h2", "h3", "blockquote", "tr", "hr", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.out.append("\n- ")
        elif tag in self.BLOCK:
            self.out.append("\n")
        elif tag == "a":
            self.href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in {"p", "h1", "h2", "h3", "blockquote"}:
            self.out.append("\n")
        elif tag == "a" and self.href:
            self.out.append(f" ({self.href})")
            self.href = None

    def handle_data(self, data):
        self.out.append(data)


def html_to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    text = "".join(p.out)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def clean_header(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).strip()


def build_subject(title: str, prefix: str = "") -> str:
    return clean_header(f"{prefix}{title}")[:300]


def local_date(dt: datetime | None) -> str:
    dt = dt or datetime.now(ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(get_settings().timezone)).strftime("%d %B %Y")


def render_email(
    *,
    title: str,
    body_html: str,
    category: str,
    priority: str,
    published_at: datetime | None,
    header_text: str,
    footer_text: str,
    attachment_links: list[tuple[str, str]],
    logo_src: str = "cid:logo",
    images: list[str] | None = None,
) -> tuple[str, str]:
    """Returns (html, text). body_html must already be sanitised."""
    ctx = dict(
        title=title,
        body_html=body_html,
        category=category,
        priority=priority,
        date=local_date(published_at),
        header_text=header_text,
        footer_text=footer_text,
        attachments=attachment_links,
        logo_src=logo_src,
        images=images or [],
    )
    html = _env.get_template("notice_email.html").render(**ctx)
    lines = [header_text, "=" * len(header_text), f"{category} | {ctx['date']}", "", title, ""]
    lines.append(html_to_text(body_html))
    if images:
        lines += ["", f"[{len(images)} image(s) - open the HTML version of this email to view]"]
    if attachment_links:
        lines += ["", "Attachments:"] + [f"- {n}: {u}" for n, u in attachment_links]
    if footer_text:
        lines += ["", "--", footer_text]
    return html, "\n".join(lines)
