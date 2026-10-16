import io

from openpyxl import Workbook


def test_department_crud_and_counts(admin, staff):
    r = admin.get("/api/departments").json()
    counts = {d["name"]: d["employee_count"] for d in r}
    assert counts == {"IT": 1, "Operations": 2}  # inactive employee not counted
    assert (
        admin.post("/api/departments", json={"name": "it"}).status_code == 409
    )  # case-insensitive
    d = admin.post("/api/departments", json={"name": "HR"}).json()
    assert (
        admin.patch(f"/api/departments/{d['id']}", json={"is_active": False}).json()["is_active"]
        is False
    )
    assert "HR" not in [x["name"] for x in admin.get("/api/departments").json()]


def test_employee_create_validation_and_duplicates(admin, staff):
    ok = admin.post("/api/employees", json={"name": "New", "email": "New@Corp.example.com",
                                            "department_id": staff["it"].id})  # fmt: skip
    assert ok.status_code == 201 and ok.json()["email"] == "new@corp.example.com"
    assert ok.json()["department_name"] == "IT"
    dup = admin.post("/api/employees", json={"name": "Again", "email": "NEW@corp.example.com"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "duplicate_email"
    assert (
        admin.post("/api/employees", json={"name": "Bad", "email": "not-an-email"}).status_code
        == 422
    )
    assert admin.post("/api/employees", json={"name": "X", "email": "x@corp.example.com",
                                              "department_id": 9999}).status_code == 422  # fmt: skip


def test_search_filter_and_deactivate_preserves_record(admin, staff):
    r = admin.get("/api/employees", params={"department_id": staff["ops"].id}).json()
    assert r["total"] == 3
    assert admin.get("/api/employees", params={"search": "sita"}).json()["total"] == 1
    assert admin.get("/api/employees", params={"search": "बिकास"}).json()["total"] == 1
    assert admin.get("/api/employees", params={"active": "true"}).json()["total"] == 3
    emp = staff["emps"][0]
    assert admin.delete(f"/api/employees/{emp.id}").json()["is_active"] is False
    assert (
        admin.get("/api/employees", params={"search": "asha"}).json()["total"] == 1
    )  # still stored


def test_search_escapes_wildcards(admin, staff):
    assert admin.get("/api/employees", params={"search": "%"}).json()["total"] == 0


CSV = (
    "Name,Email Address,Department,Job Title\n"
    "Priya Rai,priya@corp.example.com,Finance,Accountant\n"
    "Priya Again,PRIYA@corp.example.com,Finance,\n"
    "Asha,asha@corp.example.com,IT,\n"
    "No Email,bogus,IT,\n"
    ",blank@corp.example.com,IT,\n"
)


def _upload(c, content: bytes, name="people.csv", commit=False):
    return c.post(f"/api/employees/import?commit={str(commit).lower()}",
                  files={"file": (name, io.BytesIO(content), "application/octet-stream")})  # fmt: skip


def test_import_preview_does_not_write_then_commit(admin, staff):
    r = _upload(admin, CSV.encode()).json()
    assert r["committed"] is False
    assert [x["status"] for x in r["rows"]] == [
        "ok",
        "duplicate_in_file",
        "exists",
        "invalid",
        "invalid",
    ]
    assert r["rows"][0]["new_department"] is True
    assert admin.get("/api/employees", params={"search": "priya"}).json()["total"] == 0
    done = _upload(admin, CSV.encode(), commit=True).json()
    assert done["ok"] == 1 and done["skipped"] == 2 and done["errors"] == 2
    emp = admin.get("/api/employees", params={"search": "priya"}).json()["items"][0]
    assert emp["department_name"] == "Finance" and emp["job_title"] == "Accountant"


def test_import_xlsx(admin):
    wb = Workbook()
    ws = wb.active
    ws.append(["Employee Name", "Email", "Dept"])
    ws.append(["बिमला", "bimala@corp.example.com", "Sales"])
    buf = io.BytesIO()
    wb.save(buf)
    r = _upload(admin, buf.getvalue(), "people.xlsx", commit=True).json()
    assert r["ok"] == 1
    assert admin.get("/api/employees", params={"search": "बिमला"}).json()["total"] == 1


def test_import_rejects_bad_files(admin):
    assert _upload(admin, b"a,b\n1,2\n").status_code == 422  # missing columns
    assert _upload(admin, b"x", "evil.exe").status_code == 422
    assert _upload(admin, b"").status_code == 422
