from fastapi.testclient import TestClient

from app.main import app
from app.models import Role, User

from .conftest import PASSWORD, login, make_user


def test_login_logout_and_me(db):
    u = make_user(db, Role.ADMIN)
    c = login(u.email)
    assert c.get("/api/auth/me").json()["user"]["email"] == u.email
    cookie = c.cookies.jar
    assert any(k.name == "session" and k.has_nonstandard_attr("HttpOnly") for k in cookie)
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_bad_credentials_generic_and_lockout(db):
    u = make_user(db, Role.ADMIN)
    c = TestClient(app)
    for _ in range(5):
        r = c.post("/api/auth/login", json={"email": u.email, "password": "wrong-password-1"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "invalid_credentials"
    # locked: even the right password is refused
    r = c.post("/api/auth/login", json={"email": u.email, "password": PASSWORD})
    assert r.status_code == 429
    unknown = c.post("/api/auth/login", json={"email": "nobody@corp.example.com", "password": "x"})
    assert unknown.status_code == 401


def test_inactive_user_cannot_login(db):
    u = make_user(db, Role.ADMIN)
    u.is_active = False
    db.commit()
    r = TestClient(app).post("/api/auth/login", json={"email": u.email, "password": PASSWORD})
    assert r.status_code == 401


def test_protected_routes_require_auth():
    c = TestClient(app)
    for path in ("/api/employees", "/api/notices", "/api/dashboard/summary", "/api/email/jobs"):
        assert c.get(path).status_code == 401


def test_csrf_required_on_unsafe_requests(admin):
    del admin.headers["X-CSRF-Token"]
    r = admin.post("/api/departments", json={"name": "HR"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"


def test_foreign_origin_rejected(admin):
    r = admin.post("/api/departments", json={"name": "HR"}, headers={"Origin": "https://evil.test"})
    assert r.status_code == 403


def test_role_matrix(make_client, staff):
    viewer, editor, adm, sup = (make_client(r) for r in
                                (Role.VIEWER, Role.NOTICE_EDITOR, Role.ADMIN, Role.SUPER_ADMIN))  # fmt: skip
    assert viewer.get("/api/employees").status_code == 403
    assert editor.get("/api/employees").status_code == 200
    assert (
        editor.post("/api/employees", json={"name": "X", "email": "x@corp.example.com"}).status_code
        == 403
    )
    assert (
        adm.post("/api/employees", json={"name": "X", "email": "x@corp.example.com"}).status_code
        == 201
    )
    assert adm.get("/api/users").status_code == 403
    assert sup.get("/api/users").status_code == 200
    assert adm.put("/api/settings/broadcast", json={"enabled": True}).status_code == 403
    assert editor.get("/api/dashboard/summary").status_code == 403


def test_super_admin_user_management(superadmin, db):
    r = superadmin.post("/api/users", json={"email": "New@Corp.example.com", "name": "N",
                                            "role": "VIEWER", "password": "long-enough-pass"})  # fmt: skip
    assert r.status_code == 201 and r.json()["email"] == "new@corp.example.com"
    assert superadmin.post("/api/users", json={"email": "new@corp.example.com", "name": "N", "role": "VIEWER",
                                                "password": "long-enough-pass"}).status_code == 409  # fmt: skip
    short = superadmin.post("/api/users", json={"email": "s@corp.example.com", "name": "S", "role": "VIEWER",
                                                "password": "short"})  # fmt: skip
    assert short.status_code == 422
    me = db.query(User).filter_by(role="SUPER_ADMIN").one()
    assert superadmin.patch(f"/api/users/{me.id}", json={"is_active": False}).status_code == 409


PUBLIC = {("POST", "/api/auth/login"), ("GET", "/api/health")}


def test_every_route_requires_authentication():
    """Walks the OpenAPI schema so a newly added route cannot silently ship unauthenticated."""
    c = TestClient(app)
    schema = c.get("/api/openapi.json").json()
    checked = 0
    for path, ops in schema["paths"].items():
        for method in ops:
            if (method.upper(), path) in PUBLIC:
                continue
            url = path.replace("{nid}", "1").replace("{job_id}", "1").replace("{notice_id}", "1")
            for name in ("emp_id", "dept_id", "user_id", "aid", "tid", "item_id", "id"):
                url = url.replace("{" + name + "}", "1")
            r = c.request(method.upper(), url)
            assert r.status_code == 401, f"{method.upper()} {path} -> {r.status_code}"
            checked += 1
    assert checked > 30
