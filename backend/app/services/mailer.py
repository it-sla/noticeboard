"""SMTP delivery. Classifies failures so callers know whether a retry is safe.

- TransientSMTPError: nothing was accepted; safe to retry later.
- PermanentSMTPError: server rejected the message/credentials; retrying will not help.
- AmbiguousSMTPError: connection broke after the message may have been handed over; NEVER
  auto-retry (could duplicate) - flag for reconciliation.
"""

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import get_settings


class SMTPFailure(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class TransientSMTPError(SMTPFailure): ...


class PermanentSMTPError(SMTPFailure): ...


class AmbiguousSMTPError(SMTPFailure): ...


@dataclass
class Attach:
    filename: str
    content_type: str
    data: bytes


def redact(text: str) -> str:
    pw = get_settings().smtp_password
    if pw:
        text = text.replace(pw, "***")
    return text[:500]


def build_message(
    *, to_email: str, to_name: str | None, subject: str, html: str, text: str,
    attachments: list[Attach] | None = None,
    inline_logo: bytes | None = None,
    inline_images: list[tuple[str, bytes]] | None = None,
) -> EmailMessage:  # fmt: skip
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = formataddr((s.smtp_from_name, s.smtp_from_email))
    msg["To"] = formataddr((to_name or "", to_email))
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=s.smtp_from_email.split("@")[-1])
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    if inline_logo:
        msg.get_payload()[1].add_related(inline_logo, "image", "jpeg", cid="<logo>")
    for cid, data in inline_images or []:
        msg.get_payload()[1].add_related(data, "image", "jpeg", cid=f"<{cid}>")
    for a in attachments or []:
        maintype, _, subtype = a.content_type.partition("/")
        msg.add_attachment(a.data, maintype=maintype, subtype=subtype, filename=a.filename)
    return msg


class DryRunMailer:
    dry_run = True

    def send(self, msg: EmailMessage) -> None:
        return None

    def check(self) -> str:
        return "dry-run mode: no SMTP connection attempted"


class SmtpMailer:
    dry_run = False

    def _connect(self) -> smtplib.SMTP:
        s = get_settings()
        try:
            if s.smtp_use_ssl:
                smtp = smtplib.SMTP_SSL(
                    s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds,
                    context=ssl.create_default_context(),
                )  # fmt: skip
            else:
                smtp = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_seconds)
                if s.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password)
            return smtp
        except smtplib.SMTPAuthenticationError as e:
            raise PermanentSMTPError(
                f"SMTP authentication failed: {redact(str(e))}", e.smtp_code
            ) from e
        except smtplib.SMTPResponseException as e:
            raise _classify(e) from e
        except (TimeoutError, smtplib.SMTPException, OSError, ssl.SSLError) as e:
            # Failure before any message data was sent: safe to retry.
            raise TransientSMTPError(f"SMTP connection failed: {redact(str(e))}") from e

    def check(self) -> str:
        smtp = self._connect()
        try:
            smtp.noop()
        finally:
            _quit(smtp)
        return "SMTP connection and authentication succeeded"

    def send(self, msg: EmailMessage) -> None:
        smtp = self._connect()
        try:
            smtp.send_message(msg)
        except smtplib.SMTPRecipientsRefused as e:
            codes = [c for c, _ in e.recipients.values()]
            cls = (
                TransientSMTPError
                if codes and all(400 <= c < 500 for c in codes)
                else (PermanentSMTPError)
            )
            raise cls(f"Recipient refused: {redact(str(e))}", codes[0] if codes else None) from e
        except smtplib.SMTPResponseException as e:
            raise _classify(e) from e
        except (TimeoutError, smtplib.SMTPException, OSError) as e:
            raise AmbiguousSMTPError(f"Connection lost during send: {redact(str(e))}") from e
        finally:
            _quit(smtp)


def _classify(e: smtplib.SMTPResponseException) -> SMTPFailure:
    msg = redact(f"{e.smtp_code} {e.smtp_error!r}")
    return (TransientSMTPError if 400 <= e.smtp_code < 500 else PermanentSMTPError)(
        msg, e.smtp_code
    )


def _quit(smtp: smtplib.SMTP) -> None:
    try:
        smtp.quit()
    except Exception:  # noqa: BLE001, S110 - best-effort close
        pass


def get_mailer():
    return DryRunMailer() if get_settings().email_mode == "dry_run" else SmtpMailer()
