def _login(client, username="admin", password="Passw0rd!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def test_default_workbook_provisioned(client, seeded_user):
    _login(client)
    r = client.get("/api/workbooks/default")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Default Workbook"
    names = [s["name"] for s in body["sheets"]]
    assert "Asset Register" in names
    assert "Depreciation" in names
    assert "Disposal" in names
    assert any(n.startswith("Sheet") for n in names)


def test_default_workbook_idempotent(client, seeded_user):
    _login(client)
    first = client.get("/api/workbooks/default").json()
    second = client.get("/api/workbooks/default").json()
    assert first["id"] == second["id"]
    assert len(first["sheets"]) == len(second["sheets"])


def test_system_sheets_render_as_table(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    ar = next(s for s in wb["sheets"] if s["name"] == "Asset Register")
    r = client.get(f"/api/sheets/{ar['id']}/render")
    assert r.status_code == 200
    body = r.json()
    assert body["sheet_kind"] == "SYSTEM"
    assert body["table"]["title"].startswith("Asset Register")


def test_user_sheet_renders_as_grid(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    user_sheet = next(s for s in wb["sheets"] if s["kind"] == "USER")
    r = client.get(f"/api/sheets/{user_sheet['id']}/render")
    assert r.status_code == 200
    body = r.json()
    assert body["sheet_kind"] == "USER"
    assert body["grid"]["rows"] >= 10


def test_create_user_sheet(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    r = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "My Sheet"})
    assert r.status_code == 201
    assert r.json()["name"] == "My Sheet"


def test_duplicate_sheet_name_rejected(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Unique"})
    r = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Unique"})
    assert r.status_code == 409


def test_sheet_name_normalized_uniqueness(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Data"})
    # Case + whitespace difference must collide
    r = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "  data  "})
    assert r.status_code == 409


def test_system_sheet_cannot_be_renamed(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    ar = next(s for s in wb["sheets"] if s["name"] == "Asset Register")
    r = client.patch(f"/api/sheets/{ar['id']}", json={"name": "Renamed"})
    assert r.status_code == 400


def test_system_sheet_cannot_be_deleted(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    ar = next(s for s in wb["sheets"] if s["name"] == "Asset Register")
    r = client.delete(f"/api/sheets/{ar['id']}")
    assert r.status_code == 400


def test_rename_user_sheet(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    created = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Temp"}).json()
    r = client.patch(f"/api/sheets/{created['id']}", json={"name": "Permanent"})
    assert r.status_code == 200
    assert r.json()["name"] == "Permanent"


def test_delete_user_sheet(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    created = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Temp"}).json()
    r = client.delete(f"/api/sheets/{created['id']}")
    assert r.status_code == 204


def test_duplicate_user_sheet(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    created = client.post(f"/api/workbooks/{wb['id']}/sheets", json={"name": "Source"}).json()
    r = client.post(f"/api/sheets/{created['id']}/duplicate", json={"new_name": None})
    assert r.status_code == 201
    assert r.json()["name"].startswith("Source copy")


def test_write_and_read_cells(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    user_sheet = next(s for s in wb["sheets"] if s["kind"] == "USER")
    r = client.patch(
        f"/api/sheets/{user_sheet['id']}/cells",
        json={"cells": [{"row": 1, "col": 1, "raw": "42"}]},
    )
    assert r.status_code == 200
    cells = r.json()["grid"]["cells"]
    assert any(c["row"] == 1 and c["col"] == 1 and c["computed"] == "42" for c in cells)


def test_formula_cell_computed(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    user_sheet = next(s for s in wb["sheets"] if s["kind"] == "USER")
    client.patch(
        f"/api/sheets/{user_sheet['id']}/cells",
        json={"cells": [
            {"row": 1, "col": 1, "raw": "10"},
            {"row": 2, "col": 1, "raw": "20"},
            {"row": 3, "col": 1, "raw": "=SUM(A1:A2)"},
        ]},
    )
    r = client.get(f"/api/sheets/{user_sheet['id']}/render")
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    assert cells[(3, 1)]["computed"] == "30"


def test_formula_cycle_detected(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    user_sheet = next(s for s in wb["sheets"] if s["kind"] == "USER")
    r = client.patch(
        f"/api/sheets/{user_sheet['id']}/cells",
        json={"cells": [
            {"row": 1, "col": 1, "raw": "=A2"},
            {"row": 2, "col": 1, "raw": "=A1"},
        ]},
    )
    cells = {(c["row"], c["col"]): c for c in r.json()["grid"]["cells"]}
    assert any(c["error"] for c in cells.values())


def test_cannot_write_to_system_sheet(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    ar = next(s for s in wb["sheets"] if s["name"] == "Asset Register")
    r = client.patch(
        f"/api/sheets/{ar['id']}/cells",
        json={"cells": [{"row": 1, "col": 1, "raw": "hack"}]},
    )
    assert r.status_code == 400


def test_reorder_sheets(client, seeded_user):
    _login(client)
    wb = client.get("/api/workbooks/default").json()
    ids = [s["id"] for s in wb["sheets"]]
    reversed_ids = list(reversed(ids))
    r = client.post(
        f"/api/workbooks/{wb['id']}/sheets/reorder",
        json={"sheet_ids": reversed_ids},
    )
    assert r.status_code == 200
    wb2 = client.get("/api/workbooks/default").json()
    assert [s["id"] for s in wb2["sheets"]] == reversed_ids