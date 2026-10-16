from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.db import SessionLocal
from app.models import ExpiryReminder, Role
from app.services import expiry as svc
from app.services.mailer import PermanentSMTPError, TransientSMTPError

TODAY = svc.today_local()
NPT = ZoneInfo("Asia/Kathmandu")


def item(c, days, **kw):
    body = {
        "category": "vehicle",
        "item_type": "Insurance",
        "subject": "Ba 1 Cha 1234",
        "expires_on": (TODAY + timedelta(days=days)).isoformat(),
        **kw,
    }
    r = c.post("/api/expiry/items", json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize(
    "days,status",
    [
        (-1, "overdue"),
        (0, "due7"),
        (7, "due7"),
        (8, "due30"),
        (30, "due30"),
        (31, "due60"),
        (60, "due60"),
        (61, "ok"),
    ],
)
def test_status_boundaries(days, status):
    assert svc.status_of(days) == status


def test_create_list_filter_and_summary(admin):
    item(admin, -3, subject="Overdue van")
    item(admin, 5, subject="Soon van")
    item(admin, 45, category="staff", item_type="Driving licence", subject="Ram")
    item(admin, 200, category="company", item_type="Trade licence", subject="Company")
    rows = admin.get("/api/expiry/items").json()
    assert [i["subject"] for i in rows["items"]] == ["Overdue van", "Soon van", "Ram", "Company"]
    assert [i["status"] for i in rows["items"]] == ["overdue", "due7", "due60", "ok"]
    assert rows["items"][0]["days_left"] == -3
    assert admin.get("/api/expiry/items", params={"status": "overdue"}).json()["total"] == 1
    assert admin.get("/api/expiry/items", params={"status": "due60"}).json()["total"] == 1
    assert admin.get("/api/expiry/items", params={"category": "staff"}).json()["total"] == 1
    assert admin.get("/api/expiry/items", params={"search": "licence"}).json()["total"] == 2
    s = admin.get("/api/expiry/summary").json()
    assert (s["overdue"], s["due7"], s["due60"], s["ok"], s["total"]) == (1, 1, 1, 1, 4)


def test_bell_alerts_overdue_and_within_7_days(admin):
    item(admin, -2, subject="A")
    item(admin, 7, subject="B")
    item(admin, 8, subject="C")
    a = admin.get("/api/expiry/alerts").json()
    assert a["count"] == 2 and [i["subject"] for i in a["items"]] == ["A", "B"]


def test_renew_updates_date_keeps_history_and_clears_alert(admin):
    it = item(admin, 3)
    new = (TODAY + timedelta(days=368)).isoformat()
    r = admin.post(
        f"/api/expiry/items/{it['id']}/renew",
        json={"new_expires_on": new, "cost": "12500.50", "note": "Paid at office"},
    )
    assert r.status_code == 200 and r.json()["expires_on"] == new and r.json()["status"] == "ok"
    h = admin.get(f"/api/expiry/items/{it['id']}/history").json()
    assert len(h) == 1 and h[0]["new_expires_on"] == new and float(h[0]["cost"]) == 12500.5
    assert admin.get("/api/expiry/alerts").json()["count"] == 0
    back = admin.post(
        f"/api/expiry/items/{it['id']}/renew", json={"new_expires_on": TODAY.isoformat()}
    )
    assert back.status_code == 422  # must move forward


def test_archive_keeps_record_and_hides_from_active(admin):
    it = item(admin, 2)
    assert admin.delete(f"/api/expiry/items/{it['id']}").json()["is_archived"] is True
    assert admin.get("/api/expiry/items").json()["total"] == 0
    assert admin.get("/api/expiry/items", params={"archived": "true"}).json()["total"] == 1
    assert admin.get("/api/expiry/alerts").json()["count"] == 0


def test_validation(admin, staff):
    base = {"item_type": "x", "subject": "x", "expires_on": "2030-01-01"}
    assert admin.post("/api/expiry/items", json={"category": "boat", **base}).status_code == 422
    assert (
        admin.post(
            "/api/expiry/items", json={"category": "staff", "employee_id": 9999, **base}
        ).status_code
        == 422
    )
    ok = item(
        admin,
        10,
        category="staff",
        subject="Asha",
        employee_id=staff["emps"][0].id,
        reminder_days=[7, 30, 30],
    )
    assert ok["employee_name"] == "Asha" and ok["reminder_days"] == [30, 7]


def test_permissions(make_client):
    body = {"category": "vehicle", "item_type": "x", "subject": "x", "expires_on": "2030-01-01"}
    for role in (Role.NOTICE_EDITOR, Role.VIEWER):
        c = make_client(role)
        assert c.get("/api/expiry/items").status_code == 403
        assert c.get("/api/expiry/alerts").status_code == 403
        assert c.post("/api/expiry/items", json=body).status_code == 403


def test_export_csv_guards_formulas(admin):
    item(admin, 5, subject='=HYPERLINK("http://evil")')
    csv_text = admin.get("/api/expiry/export").text
    assert csv_text.splitlines()[0].startswith("category,type,subject")
    assert "'=HYPERLINK" in csv_text


# ------------------------------------------------------------------ digest
class FakeMailer:
    dry_run = False

    def __init__(self, exc=None):
        self.sent, self.exc = [], exc

    def send(self, msg):
        if self.exc:
            raise self.exc
        self.sent.append(msg)


class DryMailer(FakeMailer):
    dry_run = True


def local(days=0, hour=9):
    d = TODAY + timedelta(days=days)
    return datetime(d.year, d.month, d.day, hour, 0, tzinfo=NPT).astimezone(UTC)


def digest(mailer, now):
    with SessionLocal() as db:
        return svc.send_digest_if_due(db, mailer, now)


def text(msg):
    return msg.get_body(("plain",)).get_content()


def test_digest_goes_to_admins_once_and_each_threshold_only_once(admin, db):
    it = item(admin, 29, subject="Digest van")
    m = FakeMailer()
    assert digest(m, local(0)) == "sent"
    msg = m.sent[0]
    assert "admin@corp.example.com" in msg["To"] and "Digest van" in text(msg)
    assert msg["Subject"] == "Expiry reminders: 0 overdue, 1 due soon"
    assert digest(m, local(0)) == "wait"  # once per day
    assert digest(m, local(1)) == "nothing"  # 28 days left: no new threshold crossed
    sent = {r.threshold_days for r in db.query(ExpiryReminder).filter_by(item_id=it["id"])}
    assert sent == {60, 30}


def test_new_threshold_fires_later_and_overdue_reported_once_then_mondays(admin):
    item(admin, 8, subject="Slow van")
    m = FakeMailer()
    assert digest(m, local(0)) == "sent"  # crossed 60 and 30
    assert digest(m, local(1)) == "sent"  # 7 days left -> crossed 14 and 7
    assert "7 day(s) left" in text(m.sent[1])
    assert digest(m, local(9)) == "sent"  # now overdue: reported once
    assert "OVERDUE" in text(m.sent[2])
    count = len(m.sent)
    days = range(10, 17)
    non_monday = next(local(k) for k in days if local(k).astimezone(NPT).weekday() != 0)
    assert digest(m, non_monday) == "nothing" and len(m.sent) == count
    monday = next(local(k) for k in days if local(k).astimezone(NPT).weekday() == 0)
    assert digest(m, monday) == "sent"  # weekly reminder for what is still overdue


def test_digest_waits_before_8am_and_when_disabled(admin):
    item(admin, 3)
    m = FakeMailer()
    assert digest(m, local(0, hour=6)) == "wait"
    assert (
        admin.put(
            "/api/settings/expiry", json={"enabled": False, "extra_recipients": []}
        ).status_code
        == 200
    )
    assert digest(m, local(0)) == "wait" and m.sent == []


def test_failed_send_records_nothing_and_retries_after_an_hour(admin, db):
    it = item(admin, 3)
    now = local(0)
    assert digest(FakeMailer(TransientSMTPError("421", 421)), now) == "failed"
    assert db.query(ExpiryReminder).filter_by(item_id=it["id"]).count() == 0
    assert digest(FakeMailer(), now + timedelta(minutes=5)) == "wait"
    ok = FakeMailer()
    assert digest(ok, now + timedelta(hours=1, minutes=1)) == "sent" and len(ok.sent) == 1
    assert (
        digest(FakeMailer(PermanentSMTPError("550", 550)), now + timedelta(hours=3)) == "wait"
    )  # done today


def test_extra_recipients_validated_and_included(admin):
    item(admin, 3)
    bad = admin.put("/api/settings/expiry", json={"enabled": True, "extra_recipients": ["nope"]})
    assert bad.status_code == 422
    ok = admin.put(
        "/api/settings/expiry",
        json={"enabled": True, "extra_recipients": ["Boss@Corp.example.com"]},
    )
    assert ok.status_code == 200
    m = FakeMailer()
    assert digest(m, local(0)) == "sent"
    assert "boss@corp.example.com" in m.sent[0]["To"]
    assert admin.get("/api/settings").json()["expiry_extra_recipients"] == ["boss@corp.example.com"]


def test_dry_run_sends_nothing_and_keeps_reminders_unrecorded(admin, db):
    it = item(admin, 3)
    d = DryMailer()
    assert digest(d, local(0)) == "dry_run" and d.sent == []
    assert db.query(ExpiryReminder).filter_by(item_id=it["id"]).count() == 0


def test_worker_cycle_runs_digest(admin):
    from app.services import delivery

    item(admin, 3)
    m = FakeMailer()
    with SessionLocal() as db:
        stats = delivery.run_once(db, m, local(0))
    assert stats["expiry_digest"] == 1 and len(m.sent) == 1
