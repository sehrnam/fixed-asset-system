from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.category import AssetCategory
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


def _login(client, username="admin", password="Passw0rd!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def _make_category(client, name="Vehicles"):
    return client.post("/api/categories", json={"name": name}).json()


def _valid_asset_payload(category_id: int, **overrides):
    base = {
        "name": "Test Asset",
        "category_id": category_id,
        "cost": 100000.0,
        "acquisition_date": "2024-01-15T00:00:00Z",
        "useful_life_years": 5,
        "depreciation_method": "straight_line",
        "residual_value": 10000.0,
        "rate": None,
    }
    base.update(overrides)
    return base


def test_create_asset_auto_code(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    r = client.post("/api/assets", json=_valid_asset_payload(cat["id"]))
    assert r.status_code == 201
    body = r.json()
    assert body["asset_code"] == "FA-00001"
    assert body["category_name"] == cat["name"]
    assert body["status"] == "ACTIVE"


def test_create_asset_explicit_code(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], asset_code="FA-CUSTOM-001")
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 201
    assert r.json()["asset_code"] == "FA-CUSTOM-001"


def test_create_asset_duplicate_code(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], asset_code="FA-DUP")
    assert client.post("/api/assets", json=payload).status_code == 201
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 409


def test_create_asset_invalid_cost(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], cost=0)
    r = client.post("/api/assets", json=payload)
    assert r.status_code in (400, 422)


def test_create_asset_residual_not_less_than_cost(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], cost=1000.0, residual_value=1000.0)
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 400


def test_create_asset_rb_without_rate(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], depreciation_method="reducing_balance", rate=None)
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 400


def test_create_asset_rb_with_rate(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    payload = _valid_asset_payload(cat["id"], depreciation_method="reducing_balance", rate=20.0)
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 201
    assert r.json()["rate"] == 20.0


def test_create_asset_future_date(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    payload = _valid_asset_payload(cat["id"], acquisition_date=future)
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 400


def test_create_asset_invalid_category(client, seeded_user):
    _login(client)
    payload = _valid_asset_payload(99999)
    r = client.post("/api/assets", json=payload)
    assert r.status_code == 400


def test_list_assets(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    client.post("/api/assets", json=_valid_asset_payload(cat["id"], asset_code="FA-A1"))
    client.post("/api/assets", json=_valid_asset_payload(cat["id"], asset_code="FA-A2"))
    r = client.get("/api/assets")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_assets_search(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    client.post("/api/assets", json=_valid_asset_payload(cat["id"], asset_code="FA-X1", name="Ford Ranger"))
    client.post("/api/assets", json=_valid_asset_payload(cat["id"], asset_code="FA-X2", name="Toyota Hilux"))
    r = client.get("/api/assets?search=toyota")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Toyota Hilux"


def test_get_asset(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    created = client.post("/api/assets", json=_valid_asset_payload(cat["id"])).json()
    r = client.get(f"/api/assets/{created['id']}")
    assert r.status_code == 200
    assert r.json()["asset_code"] == created["asset_code"]


def test_update_asset(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    created = client.post("/api/assets", json=_valid_asset_payload(cat["id"])).json()
    r = client.patch(f"/api/assets/{created['id']}", json={"name": "Renamed Asset", "cost": 120000.0})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Asset"
    assert r.json()["cost"] == 120000.0


def test_update_asset_invalid_residual(client, seeded_user):
    _login(client)
    cat = _make_category(client)
    created = client.post("/api/assets", json=_valid_asset_payload(cat["id"])).json()
    r = client.patch(f"/api/assets/{created['id']}", json={"residual_value": 999999.0})
    assert r.status_code == 400


def test_asset_audit_events(client, seeded_user, db):
    _login(client)
    cat = _make_category(client)
    created = client.post("/api/assets", json=_valid_asset_payload(cat["id"])).json()
    client.patch(f"/api/assets/{created['id']}", json={"name": "Changed"})

    created_events = db.exec(select(AuditEvent).where(AuditEvent.action == "ASSET_CREATED")).all()
    updated_events = db.exec(select(AuditEvent).where(AuditEvent.action == "ASSET_UPDATED")).all()
    assert len(created_events) >= 1
    assert len(updated_events) >= 1


def test_auditor_cannot_create_asset(client, db):
    auditor = User(
        username="auditor2",
        email="auditor2@example.com",
        full_name="Auditor Two",
        password_hash=hash_password("Passw0rd!"),
        role=Role.AUDITOR.value,
        is_active=True,
    )
    db.add(auditor)
    db.commit()

    # Seed a category directly (no login needed)
    cat = AssetCategory(name="SeedCat")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    _login(client, username="auditor2", password="Passw0rd!")
    r = client.post("/api/assets", json=_valid_asset_payload(cat.id))
    assert r.status_code == 403


def test_auditor_can_view_assets(client, db):
    auditor = User(
        username="auditor3",
        email="auditor3@example.com",
        full_name="Auditor Three",
        password_hash=hash_password("Passw0rd!"),
        role=Role.AUDITOR.value,
        is_active=True,
    )
    db.add(auditor)
    db.commit()

    _login(client, username="auditor3", password="Passw0rd!")
    r = client.get("/api/assets")
    assert r.status_code == 200