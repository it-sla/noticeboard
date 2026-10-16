from datetime import timedelta

import pytest

from app.core.db import SessionLocal, utcnow
from app.models import EmailAttempt, EmailJob, JobStatus, Notice, NoticeStatus
from app.services import delivery
from app.services.mailer import (
    AmbiguousSMTPError,
    DryRunMailer,
    PermanentSMTPError,
    TransientSMTPError,
)

from .test_notices import make_notice, publish


class FakeMailer:
    dry_run = False

    def __init__(self, behaviour=None):
        self.sent, self.behaviour = [], behaviour or {}

    def send(self, msg):
        to = msg["To"]
        for email, exc in self.behaviour.items():
            if email in to and exc:
                raise exc
        self.sent.append(msg)


@pytest.fixture
def queued(admin, staff, broadcast_on):
    n = make_notice(admin)
    publish(admin, n["id"], 3)
    return n["id"]


def cycle(mailer, now=None):
    with SessionLocal() as s:
        return delivery.run_once(s, mailer, now)


def jobs(db):
    db.expire_all()
    return {j.recipient.email: j for j in db.query(EmailJob)}


def test_success_marks_accepted_and_publishes(queued, db):
    m = FakeMailer()
    stats = cycle(m)
    assert stats["sent"] == 3 and stats["finalized"] == 1
    assert {j.status for j in jobs(db).values()} == {JobStatus.ACCEPTED}
    assert db.get(Notice, queued).status == NoticeStatus.PUBLISHED
    msg = m.sent[0]
    assert "कार्यालय" in msg.get_body(("plain",)).get_content()
    assert msg["From"].endswith("<it@gohimalaya.travel>")
    assert msg["To"].count("@") == 1  # individual messages, never a shared list


def test_each_recipient_gets_one_message_and_rerun_sends_nothing(queued):
    m = FakeMailer()
    cycle(m)
    cycle(m)
    assert len(m.sent) == 3


def test_dry_run_sends_nothing(queued, db):
    cycle(DryRunMailer())
    assert {j.status for j in jobs(db).values()} == {JobStatus.DRY_RUN}


def test_transient_failure_backoff_then_gives_up(queued, db):
    m = FakeMailer({"asha@": TransientSMTPError("421 try later", 421)})
    now = utcnow()
    cycle(m, now)
    asha = jobs(db)["asha@corp.example.com"]
    assert asha.status == JobStatus.PENDING and asha.attempt_count == 1
    assert asha.next_attempt_at > now + timedelta(seconds=50)
    cycle(m, now + timedelta(seconds=5))  # backoff not elapsed: untouched
    assert jobs(db)["asha@corp.example.com"].attempt_count == 1
    for i in range(1, 6):
        cycle(m, utcnow() + timedelta(days=i))
    asha = jobs(db)["asha@corp.example.com"]
    assert asha.status == JobStatus.FAILED and asha.attempt_count == asha.max_attempts
    assert db.get(Notice, queued).status == NoticeStatus.PUBLISHED
    outcomes = [a.outcome for a in db.query(EmailAttempt).filter_by(job_id=asha.id)]
    assert outcomes == ["transient_failure"] * asha.max_attempts


def test_permanent_failure_not_retried(queued, db):
    cycle(FakeMailer({"sita@": PermanentSMTPError("550 no such user", 550)}))
    sita = jobs(db)["sita@corp.example.com"]
    assert sita.status == JobStatus.FAILED and sita.attempt_count == 1
    assert "550" in sita.error


def test_auth_failure_is_permanent_and_redacted(queued, db, _settings, monkeypatch):
    monkeypatch.setattr(_settings, "smtp_password", "s3cret-pass")
    cycle(
        FakeMailer(
            {
                "": PermanentSMTPError(
                    "auth failed for s3cret-pass".replace("s3cret-pass", "***"), 535
                )
            }
        )
    )
    assert all("s3cret-pass" not in (j.error or "") for j in jobs(db).values())


def test_ambiguous_outcome_is_flagged_not_retried(queued, db):
    m = FakeMailer({"bikash@": AmbiguousSMTPError("connection dropped during DATA")})
    cycle(m)
    cycle(m, utcnow() + timedelta(days=1))
    j = jobs(db)["bikash@corp.example.com"]
    assert j.status == JobStatus.UNKNOWN and j.attempt_count == 1


def test_worker_restart_recovers_stale_sending_as_unknown(queued, db, _settings):
    # simulate a worker that claimed jobs and died
    with SessionLocal() as s:
        ids = delivery.claim_jobs(s, utcnow(), 10)
    assert len(ids) == 3
    m = FakeMailer()
    stats = cycle(m, utcnow() + timedelta(hours=1))
    assert stats["recovered"] == 3 and m.sent == []  # nothing is resent blindly
    assert {j.status for j in jobs(db).values()} == {JobStatus.UNKNOWN}
    assert {a.outcome for a in db.query(EmailAttempt)} == {"unknown"}


def test_pending_jobs_resume_after_restart(queued, db):
    cycle(FakeMailer({"asha@": TransientSMTPError("421", 421)}))
    fresh = FakeMailer()  # "new process"
    cycle(fresh, utcnow() + timedelta(days=1))
    assert [m["To"] for m in fresh.sent][0].endswith("<asha@corp.example.com>")


def test_no_duplicate_claims(queued):
    with SessionLocal() as a, SessionLocal() as b:
        first = delivery.claim_jobs(a, utcnow(), 10)
        second = delivery.claim_jobs(b, utcnow(), 10)
    assert len(first) == 3 and second == []


def test_rate_limit_caps_batch(queued, db, _settings, monkeypatch):
    monkeypatch.setattr(_settings, "email_rate_per_minute", 2)
    m = FakeMailer()
    assert cycle(m)["sent"] == 2
    assert cycle(m)["sent"] == 0  # minute budget used
    assert cycle(m, utcnow() + timedelta(minutes=2))["sent"] == 1


def test_broadcast_disabled_pauses_worker(queued, superadmin):
    superadmin.put("/api/settings/broadcast", json={"enabled": False})
    m = FakeMailer()
    assert cycle(m)["sent"] == 0 and m.sent == []


# ------------------------------------------------------------- API surface
def test_retry_failed_and_unknown_opt_in(queued, admin, db):
    cycle(FakeMailer({"sita@": PermanentSMTPError("550", 550),
                      "bikash@": AmbiguousSMTPError("dropped")}))  # fmt: skip
    j = jobs(db)
    r = admin.post(f"/api/email/jobs/{j['bikash@corp.example.com'].id}/retry", json={})
    assert r.status_code == 409  # unknown requires explicit opt-in
    assert admin.post(f"/api/email/notices/{queued}/retry-failed", json={}).json() == {
        "requeued": 1
    }
    assert db.get(Notice, queued).status == NoticeStatus.QUEUED  # reopened
    m = FakeMailer()
    cycle(m)
    assert len(m.sent) == 1 and jobs(db)["sita@corp.example.com"].status == JobStatus.ACCEPTED
    ok = admin.post(f"/api/email/jobs/{j['bikash@corp.example.com'].id}/retry",
                    json={"include_unknown": True})  # fmt: skip
    assert ok.status_code == 200
    assert (
        admin.post(f"/api/email/jobs/{j['asha@corp.example.com'].id}/retry", json={}).status_code
        == 409
    )


def test_history_filters_pagination_and_export(queued, admin):
    cycle(FakeMailer({"sita@": PermanentSMTPError("=cmd|' /C calc'!A0", 550)}))
    all_ = admin.get("/api/email/jobs", params={"page_size": 2}).json()
    assert all_["total"] == 3 and len(all_["items"]) == 2
    failed = admin.get("/api/email/jobs", params={"status": "failed"}).json()
    assert failed["total"] == 1 and failed["items"][0]["recipient_email"] == "sita@corp.example.com"
    assert admin.get("/api/email/jobs", params={"search": "asha"}).json()["total"] == 1
    assert admin.get("/api/email/jobs", params={"date_from": "2999-01-01"}).json()["total"] == 0
    csv_text = admin.get("/api/email/jobs/export").text
    assert csv_text.splitlines()[0].startswith("notice,recipient,email,status")
    assert "'=cmd" in csv_text and ",=cmd" not in csv_text  # formula injection neutralised
    attempts = admin.get(f"/api/email/jobs/{failed['items'][0]['id']}/attempts").json()
    assert attempts[0]["outcome"] == "permanent_failure"


def test_sending_status_and_recipient_log(queued, admin):
    s = admin.get(f"/api/notices/{queued}/sending").json()
    assert s["total"] == 3 and s["counts"] == {"pending": 3} and s["complete"] is False
    cycle(FakeMailer())
    s = admin.get(f"/api/notices/{queued}/sending").json()
    assert s["complete"] and s["notice_status"] == "published"
    assert admin.get(f"/api/notices/{queued}/recipients").json()["total"] == 3


def test_dashboard_numbers_come_from_database(queued, admin, staff):
    s = admin.get("/api/dashboard/summary").json()
    assert (s["active_employees"], s["pending_emails"], s["published_notices"]) == (3, 3, 1)
    cycle(FakeMailer({"sita@": PermanentSMTPError("550", 550)}))
    s = admin.get("/api/dashboard/summary").json()
    assert (s["smtp_accepted_emails"], s["failed_emails"], s["pending_emails"]) == (2, 1, 0)
    a = admin.get("/api/dashboard/activity").json()
    assert a["recent_notices"][0]["id"] == queued
    assert a["failed_warnings"][0]["recipient_email"] == "sita@corp.example.com"
    assert len(a["recent_sending"]) == 3


def test_send_test_goes_to_one_address_only(admin, staff, db, monkeypatch):
    sent = []

    class Capture(FakeMailer):
        def send(self, msg):
            sent.append(msg)

    monkeypatch.setattr("app.api.email.get_mailer", lambda: Capture())
    r = admin.post("/api/email/test", json={"to": "me@corp.example.com", "title": "Hello",
                                            "body_html": "<p>नमस्ते</p>"})  # fmt: skip
    assert r.status_code == 200 and r.json()["sent"] is True
    assert len(sent) == 1 and sent[0]["To"] == "me@corp.example.com"
    assert sent[0]["Subject"].startswith("[TEST]")
    assert db.query(EmailJob).count() == 0  # outbox untouched
    # a list of addresses is not accepted
    assert admin.post("/api/email/test", json={"to": ["a@corp.example.com", "b@corp.example.com"],
                                               "title": "x"}).status_code == 422  # fmt: skip


def test_send_test_dry_run_and_smtp_failure(admin, monkeypatch, _settings):
    r = admin.post("/api/email/test", json={"to": "me@corp.example.com", "title": "Hello"})
    assert r.json() == {"mode": "dry_run", "sent": False, "message": "Dry-run: nothing was sent"}

    class Boom(FakeMailer):
        def send(self, msg):
            raise PermanentSMTPError("SMTP authentication failed", 535)

    monkeypatch.setattr("app.api.email.get_mailer", lambda: Boom())
    r = admin.post("/api/email/test", json={"to": "me@corp.example.com", "title": "Hello"})
    assert r.status_code == 502 and "authentication failed" in r.json()["error"]["message"]


def test_send_test_rate_limited(admin, monkeypatch, _settings):
    monkeypatch.setattr(_settings, "test_send_per_hour", 2)
    body = {"to": "me@corp.example.com", "title": "Hello"}
    assert admin.post("/api/email/test", json=body).status_code == 200
    assert admin.post("/api/email/test", json=body).status_code == 200
    assert admin.post("/api/email/test", json=body).status_code == 429


# ------------------------------------------------------------- image notices
def _photo(size=(3000, 2000), fmt="PNG") -> bytes:
    import io
    import random

    from PIL import Image

    im = Image.new("RGB", size)
    px = im.load()
    for x in range(0, size[0], 50):
        for y in range(0, size[1], 50):
            px[x, y] = (random.randrange(256), random.randrange(256), 0)
    buf = io.BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def test_image_only_notice_is_resized_and_emailed_inline(admin, staff, broadcast_on, db):
    import io

    from PIL import Image

    n = admin.post("/api/notices", json={"title": "Physical board photo", "body_html": ""}).json()
    up = admin.post(f"/api/notices/{n['id']}/attachments",
                    files={"file": ("board.png", _photo(), "image/png")})  # fmt: skip
    assert up.status_code == 201
    att = up.json()
    assert att["content_type"] == "image/jpeg" and att["original_filename"] == "board.jpg"
    stored = admin.get(f"/api/attachments/{att['id']}/download").content
    assert max(Image.open(io.BytesIO(stored)).size) <= 1600
    prev = admin.get(f"/api/notices/{n['id']}/preview").json()
    assert "data:image/jpeg;base64," in prev["html"]
    assert publish(admin, n["id"], 3).status_code == 200  # no text needed when an image exists

    m = FakeMailer()
    cycle(m)
    msg = m.sent[0]
    html_part = msg.get_body(("html",))
    assert 'src="cid:img' in html_part.get_content()
    related = [p for p in msg.walk() if p.get_content_type() == "image/jpeg"]
    assert len(related) == 2  # logo + notice image, inline (not a separate attachment)
    assert not list(msg.iter_attachments()) or all(
        p.get_content_disposition() != "attachment" for p in msg.walk()
    )


def test_notice_without_text_or_image_cannot_publish(admin, staff, broadcast_on):
    n = admin.post("/api/notices", json={"title": "Empty", "body_html": ""}).json()
    r = publish(admin, n["id"], 3)
    assert r.status_code == 422 and r.json()["error"]["code"] == "incomplete_notice"


def test_corrupt_image_rejected(admin):
    n = admin.post("/api/notices", json={"title": "x", "body_html": "t"}).json()
    r = admin.post(f"/api/notices/{n['id']}/attachments",
                   files={"file": ("bad.png", b"\x89PNG\r\n\x1a\nnot really", "image/png")})  # fmt: skip
    assert r.status_code == 422
