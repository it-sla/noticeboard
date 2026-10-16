from datetime import timedelta

from app.core.db import utcnow
from app.models import EmailJob, Employee, Notice, NoticeRecipient, NoticeStatus, Role
from app.services.notices import fire_due_scheduled

BODY = "<p>कार्यालय बन्द रहनेछ।</p><script>alert(1)</script><a href='javascript:x'>bad</a>"


def make_notice(c, **kw):
    payload = {"title": "Dashain holiday", "body_html": BODY, "category": "Holiday Notice",
               "recipient_mode": "all", **kw}  # fmt: skip
    r = c.post("/api/notices", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_draft_sanitizes_and_edits(admin):
    n = make_notice(admin)
    assert "<script" not in n["body_html"] and "javascript:" not in n["body_html"]
    assert "कार्यालय बन्द" in n["body_html"] and n["status"] == "draft"
    r = admin.patch(f"/api/notices/{n['id']}", json={"title": "Updated"}).json()
    assert r["title"] == "Updated"
    assert admin.post("/api/notices", json={"title": "", "body_html": "x"}).status_code == 422
    assert admin.post("/api/notices", json={"title": "t", "category": "Nope"}).status_code == 422


def test_preview_counts_and_nepali(admin, staff):
    n = make_notice(admin)
    p = admin.get(f"/api/notices/{n['id']}/preview").json()
    assert p["recipient_count"] == 3  # inactive excluded
    assert "कार्यालय बन्द रहनेछ" in p["html"] and "कार्यालय बन्द रहनेछ" in p["text"]
    assert p["sender"].endswith("<it@gohimalaya.travel>") and p["subject"] == "Dashain holiday"
    assert "Holiday Notice" in p["html"]


def test_recipient_modes(admin, staff):
    d = make_notice(admin, recipient_mode="departments", department_ids=[staff["ops"].id])
    assert admin.get(f"/api/notices/{d['id']}/preview").json()["recipient_count"] == 2
    ids = [staff["emps"][0].id, staff["emps"][3].id]  # one active, one inactive
    e = make_notice(admin, recipient_mode="employees", employee_ids=ids)
    assert admin.get(f"/api/notices/{e['id']}/preview").json()["recipient_count"] == 1
    bad = admin.post("/api/notices", json={"title": "t", "recipient_mode": "departments",
                                           "department_ids": [999]})  # fmt: skip
    assert bad.status_code == 422


def publish(c, nid, count, confirm=True):
    return c.post(f"/api/notices/{nid}/publish", json={"confirm": confirm,
                                                       "expected_recipient_count": count})  # fmt: skip


def test_publish_blocked_until_broadcast_enabled(admin, staff):
    n = make_notice(admin)
    r = publish(admin, n["id"], 3)
    assert r.status_code == 409 and r.json()["error"]["code"] == "broadcast_disabled"


def test_publish_requires_confirmation_and_matching_count(admin, staff, broadcast_on):
    n = make_notice(admin)
    assert publish(admin, n["id"], 3, confirm=False).status_code == 422
    r = publish(admin, n["id"], 2)
    assert r.status_code == 409 and r.json()["error"]["details"]["recipient_count"] == 3


def test_publish_snapshot_jobs_and_no_double_publish(admin, staff, broadcast_on, db):
    n = make_notice(admin)
    assert publish(admin, n["id"], 3).json() == {"status": "queued", "recipient_count": 3}
    assert db.query(EmailJob).count() == 3
    # directory changes after approval must not alter the snapshot
    db.add(Employee(name="Late Joiner", email="late@corp.example.com"))
    db.query(Employee).filter_by(email="asha@corp.example.com").update({"is_active": False})
    db.commit()
    assert db.query(NoticeRecipient).filter_by(notice_id=n["id"]).count() == 3
    again = publish(admin, n["id"], 3)
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_published"
    assert db.query(EmailJob).count() == 3
    versions = admin.get(f"/api/notices/{n['id']}/versions").json()
    assert len(versions) == 1 and versions[0]["title"] == "Dashain holiday"
    # content is frozen: published notices cannot be edited
    assert admin.patch(f"/api/notices/{n['id']}", json={"title": "Changed"}).status_code == 409


def test_publish_empty_audience_rejected(admin, broadcast_on):
    n = make_notice(admin)
    assert publish(admin, n["id"], 1).status_code == 422


def test_editor_cannot_publish_or_edit_others(make_client, staff, broadcast_on, db):
    editor = make_client(Role.NOTICE_EDITOR)
    other = make_client(Role.ADMIN)
    n = make_notice(editor)
    assert publish(editor, n["id"], 3).status_code == 403
    assert (
        editor.post(
            f"/api/notices/{n['id']}/schedule", json={"scheduled_at": "2030-01-01T00:00:00+00:00"}
        ).status_code
        == 403
    )  # noqa: E501
    assert db.query(EmailJob).count() == 0
    theirs = make_notice(other)
    assert editor.patch(f"/api/notices/{theirs['id']}", json={"title": "hijack"}).status_code == 403


def test_viewer_sees_only_published(make_client, admin, staff, broadcast_on):
    viewer = make_client(Role.VIEWER)
    draft = make_notice(admin)
    sent = make_notice(admin, title="Sent one")
    publish(admin, sent["id"], 3)
    ids = [i["id"] for i in viewer.get("/api/notices").json()["items"]]
    assert ids == [sent["id"]]
    assert viewer.get(f"/api/notices/{draft['id']}").status_code == 404
    assert viewer.post("/api/notices", json={"title": "x"}).status_code == 403


def test_schedule_cancel_and_fire(admin, staff, broadcast_on, db):
    n = make_notice(admin)
    soon = (utcnow() + timedelta(hours=1)).isoformat()
    assert (
        admin.post(f"/api/notices/{n['id']}/schedule", json={"scheduled_at": soon}).json()["status"]
        == "scheduled"
    )
    assert (
        admin.post(
            f"/api/notices/{n['id']}/schedule", json={"scheduled_at": "2020-01-01T00:00:00+00:00"}
        ).status_code
        == 422
    )  # noqa: E501
    assert (
        admin.post(
            f"/api/notices/{n['id']}/schedule", json={"scheduled_at": "2030-01-01T00:00:00"}
        ).status_code
        == 422
    )  # noqa: E501
    assert admin.post(f"/api/notices/{n['id']}/cancel").json()["status"] == "cancelled"
    assert fire_due_scheduled(db, utcnow() + timedelta(days=1)) == 0

    m = make_notice(admin, title="Later")
    admin.post(f"/api/notices/{m['id']}/schedule", json={"scheduled_at": soon})
    assert fire_due_scheduled(db, utcnow()) == 0  # not due yet
    later = utcnow() + timedelta(hours=2)
    assert fire_due_scheduled(db, later) == 1
    assert fire_due_scheduled(db, later) == 0  # no duplicate processing
    assert db.get(Notice, m["id"]).status == NoticeStatus.QUEUED
    assert db.query(EmailJob).filter_by(notice_id=m["id"]).count() == 3


def test_scheduled_revalidated_at_fire_time(admin, superadmin, staff, broadcast_on, db):
    n = make_notice(admin)
    admin.post(f"/api/notices/{n['id']}/schedule",
               json={"scheduled_at": (utcnow() + timedelta(hours=1)).isoformat()})  # fmt: skip
    superadmin.put("/api/settings/broadcast", json={"enabled": False})
    assert fire_due_scheduled(db, utcnow() + timedelta(hours=2)) == 0
    assert db.get(Notice, n["id"]).status == NoticeStatus.DRAFT
    assert db.query(EmailJob).count() == 0


def test_duplicate_and_archive(admin, staff):
    n = make_notice(admin, recipient_mode="departments", department_ids=[staff["it"].id])
    d = admin.post(f"/api/notices/{n['id']}/duplicate").json()
    assert d["title"].startswith("Copy of") and d["status"] == "draft"
    assert d["department_ids"] == [staff["it"].id]
    assert admin.post(f"/api/notices/{d['id']}/archive").json()["archived_at"]
    assert d["id"] not in [i["id"] for i in admin.get("/api/notices").json()["items"]]
    assert d["id"] in [
        i["id"] for i in admin.get("/api/notices", params={"archived": "true"}).json()["items"]
    ]


def test_search_and_filter(admin):
    make_notice(admin, title="Holiday A")
    make_notice(admin, title="Meeting B", category="Meeting")
    assert admin.get("/api/notices", params={"search": "meeting"}).json()["total"] == 1
    assert admin.get("/api/notices", params={"category": "Holiday Notice"}).json()["total"] == 1


def test_attachment_validation(admin, monkeypatch, _settings):
    n = make_notice(admin)
    url = f"/api/notices/{n['id']}/attachments"
    pdf = b"%PDF-1.4 test"
    ok = admin.post(url, files={"file": ("../../evil name.pdf", pdf, "application/pdf")})
    assert ok.status_code == 201 and "/" not in ok.json()["original_filename"]
    assert (
        admin.post(url, files={"file": ("a.exe", b"MZ", "application/octet-stream")}).status_code
        == 422
    )
    assert (
        admin.post(url, files={"file": ("fake.pdf", b"not a pdf", "application/pdf")}).status_code
        == 422
    )
    big = b"%PDF" + b"0" * (11 * 1024 * 1024)
    monkeypatch.setattr(_settings, "attachment_max_mb", 10)
    assert admin.post(url, files={"file": ("big.pdf", big, "application/pdf")}).status_code == 413
    dl = admin.get(f"/api/attachments/{ok.json()['id']}/download")
    assert dl.status_code == 200 and dl.content == pdf
    assert admin.delete(f"{url}/{ok.json()['id']}").status_code == 204
    assert admin.get(f"/api/attachments/{ok.json()['id']}/download").status_code == 404
