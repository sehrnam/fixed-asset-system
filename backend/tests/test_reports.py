from datetime import datetime, timezone

from app.models.asset import Asset
from app.models.category import AssetCategory


def _login(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    assert r.status_code == 200


def _seed(db):
    cat = AssetCategory(name="Cat-R")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    a = Asset(
        asset_code="FA-R1", name="Report Asset", category_id=cat.id,
        cost=100_000.0,
        acquisition_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        useful_life_years=5, depreciation_method="straight_line",
        residual_value=10_000.0,
    )
    db.add(a)
    db.commit()


def test_asset_register_report(client, seeded_user, db):
    _login(client)
    _seed(db)
    r = client.get("/api/reports/asset-register")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Asset Register"
    assert len(body["rows"]) >= 1
    assert body["totals"]["total_cost"] >= 100000.0


def test_depreciation_schedule_report(client, seeded_user, db):
    _login(client)
    _seed(db)
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    r = client.get("/api/reports/depreciation-schedule?period_label=2024")
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["total_depreciation"] > 0


def test_asset_movement_report(client, seeded_user, db):
    _login(client)
    _seed(db)
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    r = client.get("/api/reports/asset-movement?period_label=2024")
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert body["totals"]["closing_cost"] >= 0


def test_disposal_register_report(client, seeded_user, db):
    _login(client)
    r = client.get("/api/reports/disposal-register")
    assert r.status_code == 200
    assert r.json()["title"] == "Disposal Register"


def test_dashboard(client, seeded_user, db):
    _login(client)
    _seed(db)
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert "total_asset_cost" in body
    assert "total_nbv" in body
    assert "category_summary" in body