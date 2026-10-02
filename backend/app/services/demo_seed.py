"""
Deterministic demo dataset (per blueprint Q7).

Fictional data only. Safe to re-run; will no-op if the demo marker exists.
"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.asset import Asset, AssetStatus, DepreciationMethod
from app.models.category import AssetCategory


DEMO_CATEGORIES = [
    {"name": "Motor Vehicles", "description": "Company-owned vehicles"},
    {"name": "Office Equipment", "description": "Computers, printers, furniture"},
    {"name": "Machinery", "description": "Plant and machinery"},
]


def _iso(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


def seed_demo_data(db: Session) -> dict:
    created = {"categories": 0, "assets": 0}

    # 1. Categories
    cat_by_name: dict[str, AssetCategory] = {}
    for spec in DEMO_CATEGORIES:
        existing = db.exec(select(AssetCategory).where(AssetCategory.name == spec["name"])).first()
        if existing is None:
            cat = AssetCategory(name=spec["name"], description=spec["description"])
            db.add(cat)
            db.flush()
            cat_by_name[spec["name"]] = cat
            created["categories"] += 1
        else:
            cat_by_name[spec["name"]] = existing

    # 2. Assets (SKIP if any exist with a "FA-9000x" demo code)
    demo_codes = {"FA-90001", "FA-90002", "FA-90003", "FA-90004"}
    existing_demo = db.exec(select(Asset).where(Asset.asset_code.in_(demo_codes))).all()
    if existing_demo:
        return created

    assets = [
        Asset(
            asset_code="FA-90001",
            name="Toyota Hilux Pickup",
            category_id=cat_by_name["Motor Vehicles"].id,
            cost=250000.00,
            acquisition_date=_iso(2024, 1, 15),
            useful_life_years=5,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            residual_value=25000.00,
            rate=None,
            description="Field operations vehicle (DEMO)",
            location="Head Office",
            status=AssetStatus.ACTIVE,
        ),
        Asset(
            asset_code="FA-90002",
            name="HP LaserJet Printer",
            category_id=cat_by_name["Office Equipment"].id,
            cost=3500.00,
            acquisition_date=_iso(2023, 6, 10),
            useful_life_years=4,
            depreciation_method=DepreciationMethod.REDUCING_BALANCE,
            residual_value=200.00,
            rate=25.0,
            description="Accounts department printer (DEMO)",
            location="Head Office",
            status=AssetStatus.ACTIVE,
        ),
        Asset(
            asset_code="FA-90003",
            name="Standby Generator 20kVA",
            category_id=cat_by_name["Machinery"].id,
            cost=85000.00,
            acquisition_date=_iso(2025, 3, 1),
            useful_life_years=10,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            residual_value=5000.00,
            rate=None,
            description="Backup power generator (DEMO)",
            location="Head Office",
            status=AssetStatus.ACTIVE,
        ),
        Asset(
            asset_code="FA-90004",
            name="Old Desktop Computer",
            category_id=cat_by_name["Office Equipment"].id,
            cost=6000.00,
            acquisition_date=_iso(2020, 4, 20),
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            residual_value=0.0,
            rate=None,
            description="Retired desktop (DEMO)",
            location="Head Office",
            status=AssetStatus.DISPOSED,
        ),
    ]

    for a in assets:
        db.add(a)
        created["assets"] += 1

    db.commit()
    return created