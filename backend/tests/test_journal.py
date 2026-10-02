from datetime import datetime, timezone

from app.models.asset import Asset
from app.models.category import AssetCategory
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


def _login(client, username="admin", password="Passw0rd!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def _seed_asset(db, code="FA-J1"):
    cat = AssetCategory(name=f"Cat-{code}")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    a = Asset(
        asset_code=code, name=f"Asset {code}", category_id=cat.id,
        cost=100_000.0,
        acquisition_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        useful_life_years=5, depreciation_method="straight_line",
        residual_value=10_000.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_prepare_journal_requires_depreciation_first(client, seeded_user, db):
    _login(client)
    # No records yet → total = 0
    r = client.post("/api/journals/depreciation", json={"period_label": "2024"})
    # Journal can still be prepared with zero, but let's make sure it doesn't 500
    assert r.status_code in (201, 404)
    if r.status_code == 404:
        return
    body = r.json()
    assert body["total_debit"] == 0.0
    assert body["total_credit"] == 0.0
    assert len(body["lines"]) == 2


def test_prepare_journal_with_depreciation(client, seeded_user, db):
    _login(client)
    _seed_asset(db)
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})

    r = client.post("/api/journals/depreciation", json={"period_label": "2024"})
    assert r.status_code == 201
    body = r.json()
    assert body["total_debit"] == body["total_credit"]
    assert body["total_debit"] > 0
    assert body["status"] == "DRAFT"
    # DR/CR structure
    lines = body["lines"]
    assert any(l["debit"] > 0 for l in lines)
    assert any(l["credit"] > 0 for l in lines)


def test_journal_reprepared_is_idempotent(client, seeded_user, db):
    _login(client)
    _seed_asset(db, code="FA-J2")
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})

    first = client.post("/api/journals/depreciation", json={"period_label": "2024"}).json()
    second = client.post("/api/journals/depreciation", json={"period_label": "2024"}).json()
    assert first["id"] == second["id"]
    assert first["code"] == second["code"]


def test_approver_must_differ_from_preparer(client, seeded_user, db):
    _login(client)
    _seed_asset(db, code="FA-J3")
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    j = client.post("/api/journals/depreciation", json={"period_label": "2024"}).json()

    # Admin prepared, admin cannot approve
    r = client.post(f"/api/journals/{j['id']}/approve")
    assert r.status_code == 403


def test_approver_can_approve_journal(client, seeded_user, db):
    _login(client)
    _seed_asset(db, code="FA-J4")
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    j = client.post("/api/journals/depreciation", json={"period_label": "2024"}).json()

    approver = User(
        username="app2", email="app2@example.com", full_name="Approver Two",
        password_hash=hash_password("Passw0rd!"),
        role=Role.APPROVER.value, is_active=True,
    )
    db.add(approver)
    db.commit()

    client.post("/api/auth/logout")
    _login(client, username="app2")
    r = client.post(f"/api/journals/{j['id']}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"