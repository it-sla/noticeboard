import smtplib
import socket
from email import message_from_bytes, policy

import pytest
from aiosmtpd.controller import Controller

from app.services import mailer as m


def _msg():
    return m.build_message(
        to_email="a@corp.example.com",
        to_name="Asha",
        subject="Hi\r\nBcc: x@y.z" if False else "Hi",
        html="<p>नमस्ते</p>",
        text="नमस्ते",
    )


@pytest.fixture
def smtp_settings(_settings, monkeypatch):
    for k, v in dict(email_mode="smtp", smtp_use_ssl=False, smtp_starttls=False, smtp_username="",
                     smtp_host="127.0.0.1").items():  # fmt: skip
        monkeypatch.setattr(_settings, k, v)
    return _settings


class Capture:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope)
        return "250 OK"


def test_real_smtp_roundtrip_with_unicode(smtp_settings, monkeypatch):
    handler = Capture()
    port = _free_port()
    ctl = Controller(handler, hostname="127.0.0.1", port=port)
    ctl.start()
    try:
        monkeypatch.setattr(smtp_settings, "smtp_port", port)
        mailer = m.SmtpMailer()
        assert "succeeded" in mailer.check()
        mailer.send(_msg())
    finally:
        ctl.stop()
    env = handler.messages[0]
    assert env.rcpt_tos == ["a@corp.example.com"] and env.mail_from == "it@gohimalaya.travel"
    parsed = message_from_bytes(env.content, policy=policy.default)
    assert "नमस्ते" in parsed.get_body(("plain",)).get_content()
    assert "नमस्ते" in parsed.get_body(("html",)).get_content()


def test_header_injection_blocked():
    with pytest.raises(ValueError):
        m.build_message(
            to_email="a@corp.example.com",
            to_name=None,
            subject="Hi\r\nBcc: x@y.z",
            html="<p>x</p>",
            text="x",
        )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_connection_refused_is_transient(smtp_settings, monkeypatch):
    monkeypatch.setattr(smtp_settings, "smtp_port", _free_port())
    with pytest.raises(m.TransientSMTPError):
        m.SmtpMailer().send(_msg())


class FakeSMTP:
    mode = ""

    def __init__(self, *a, **k):
        pass

    def login(self, u, p):
        if self.mode == "auth":
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 bad credentials hunter2")

    def send_message(self, msg):
        if self.mode == "drop":
            raise smtplib.SMTPServerDisconnected("dropped after DATA")
        if self.mode == "reject":
            raise smtplib.SMTPRecipientsRefused({"a@corp.example.com": (550, b"no such user")})
        if self.mode == "throttle":
            raise smtplib.SMTPDataError(451, b"rate limit")
        if self.mode == "spam":
            raise smtplib.SMTPDataError(554, b"rejected as spam")

    def quit(self):
        pass


@pytest.mark.parametrize(
    "mode,exc",
    [("auth", m.PermanentSMTPError), ("drop", m.AmbiguousSMTPError),
     ("reject", m.PermanentSMTPError), ("throttle", m.TransientSMTPError),
     ("spam", m.PermanentSMTPError)],
)  # fmt: skip
def test_failure_classification(smtp_settings, monkeypatch, mode, exc):
    FakeSMTP.mode = mode
    monkeypatch.setattr(smtp_settings, "smtp_use_ssl", True)
    monkeypatch.setattr(smtp_settings, "smtp_username", "it@gohimalaya.travel")
    monkeypatch.setattr(smtp_settings, "smtp_password", "hunter2")
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    with pytest.raises(exc) as ei:
        m.SmtpMailer().send(_msg())
    assert "hunter2" not in str(ei.value)  # password never leaks into stored errors


def test_dry_run_mailer_selected_by_default(_settings):
    assert isinstance(m.get_mailer(), m.DryRunMailer)
