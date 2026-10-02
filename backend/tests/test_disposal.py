from datetime import datetime, timezone

from sqlmodel import select

from app.models.asset import Asset, AssetStatus
from app.models.category import AssetCategory
from app.models.disposal import Disposal
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


def _login(client, username="admin", password="Passw0rd!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def _seed_asset(db, code="FA-D1", status=AssetStatus.ACTIVE):
    cat = AssetCategory(name=f"Cat-{code}")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    a = Asset(
        asset_code=code,
        name=f"Asset {code}",
        category_id=cat.id,
        cost=100_000.0,
        acquisition_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        useful_life_years=5,
        depreciation_method="straight_line",
        residual_value=10_000.0,
        status=status,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_create_disposal_computes_gain_loss(client, seeded_user, db):
    _login(client)
    asset = _seed_asset(db)
    r = client.post(
        "/api/disposals",
        json={
            "asset_id": asset.id,
            "disposal_date": "2025-06-30T00:00:00Z",
            "proceeds": 80000.0,
            "reason": "Sold",
        },
    )
    assert r.status_code == 201
    body = r.json()
    # NBV: no depreciation records → cost = 100,000 → gain = 80,000 - 100,000 = -20,000
    assert body["nbv_at_disposal"] == 100_000.0
    assert body["gain_loss"] == -20_000.0
    assert body["status"] == "PENDING"


def test_cannot_dispose_non_active(client, seeded_user, db):
    _login(client)
    asset = _seed_asset(db, code="FA-D2", status=AssetStatus.DISPOSED)
    r = client.post(
        "/api/disposals",
        json={"asset_id": asset.id, "disposal_date": "2025-01-01T00:00:00Z", "proceeds": 0.0},
    )
    assert r.status_code == 400


def test_future_disposal_rejected(client, seeded_user, db):
    _login(client)
    asset = _seed_asset(db, code="FA-D3")
    r = client.post(
        "/api/disposals",
        json={"asset_id": asset.id, "disposal_date": "2099-01-01T00:00:00Z", "proceeds": 0.0},
    )
    assert r.status_code == 400


def test_approver_must_differ_from_requester(client, seeded_user, db):
    """Maker-checker: same user cannot create and approve."""
    _login(client)
    asset = _seed_asset(db, code="FA-D4")
    created = client.post(
        "/api/disposals",
        json={"asset_id": asset.id, "disposal_date": "2025-01-15T00:00:00Z", "proceeds": 50000.0},
    ).json()

    # Admin is both CREATE and APPROVE capable; maker-checker blocks self-approval.
    r = client.post(f"/api/disposals/{created['id']}/approve")
    assert r.status_code == 403


def test_approver_can_approve(client, seeded_user, db):
    """Create a separate approver user, request as admin, approve as approver."""
    _login(client)
    asset = _seed_asset(db, code="FA-D5")

    approver = User(
        username="app1",
        email="app1@example.com",
        full_name="Approver One",
        password_hash=hash_password("Passw0rd!"),
        role=Role.APPROVER.value,
        is_active=True,
    )
    db.add(approver)
    db.commit()

    created = client.post(
        "/api/disposals",
        json={"asset_id": asset.id, "disposal_date": "2025-01-15T00:00:00Z", "proceeds": 50000.0},
    ).json()

    client.post("/api/auth/logout")
    _login(client, username="app1")

    r = client.post(f"/api/disposals/{created['id']}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"

    # Asset should now be DISPOSED
    db.refresh(asset)
    assert asset.status == AssetStatus.DISPOSED