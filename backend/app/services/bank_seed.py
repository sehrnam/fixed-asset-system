"""
Bank asset seed - v3.0.

Seeds one representative asset per category from the bank's August 2026
fixed-asset sheet. This is a demo seed - values come from the sheet the
bank provided.

Replace with real individual assets via the UI going forward.
"""
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.asset import Asset, AssetStatus, DepreciationMethod
from app.models.category import AssetCategory


# (category name, cost, annual rate %, useful life years)
BANK_CATEGORIES = [
    ("Computers & Accessories",         509530.18, 25.0,  4),
    ("Office Furniture & Fittings",     495137.80, 20.0,  5),
    ("Office Equipment",                722433.76, 25.0,  4),
    ("Bungalow Furniture & Fittings",    10250.00, 20.0,  5),
    ("Safe",                             26476.00, 25.0,  4),
    ("Police Booth",                     16963.36, 20.0,  5),
    ("Motor Vehicles",                 2113754.56, 33.33, 3),
    ("Armoured Bullion Van",                 0.00, 33.33, 3),
    ("Managers Bungalow",                    0.00, 20.0,  5),
    ("Bank Building",                 10976201.36,  5.0, 20),
    ("Intangible Asset",                432008.69,  5.0, 20),
    ("Right of Use Agreement",          607800.00, 10.0, 10),
    ("Land & Leasehold Property",            0.00,  0.0,  0),
    ("Capital Work in Progress",             0.00,  0.0,  0),
]


def _acq_date(years_ago: int, month: int, day: int) -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year - years_ago, month, day, tzinfo=timezone.utc)


def seed_bank_data(db: Session) -> dict:
    """Seed categories + one representative asset per category.

    Idempotent - only adds categories/assets that don't already exist.
    Returns a summary dict.
    """
    created = {"categories": 0, "assets": 0}

    for name, cost, rate, life in BANK_CATEGORIES:
        # Category
        cat = db.exec(
            select(AssetCategory).where(AssetCategory.name == name)
        ).first()
        if cat is None:
            cat = AssetCategory(name=name, description="Bank fixed-asset category")
            db.add(cat)
            db.flush()
            created["categories"] += 1

        # Skip zero-cost placeholder categories (no asset to seed)
        if cost <= 0 or life <= 0:
            continue

        # Skip if an asset for this category already exists
        existing = db.exec(
            select(Asset).where(Asset.category_id == cat.id)
        ).first()
        if existing is not None:
            continue

        # Pick a plausible acquisition date so accumulated is meaningful.
        # Ballpark: ~50% of life elapsed for most categories.
        if life >= 20:
            years_ago = 5
        elif life >= 10:
            years_ago = 5
        elif life >= 5:
            years_ago = 3
        else:
            years_ago = 2

        asset = Asset(
            asset_code=f"FA-{cat.id:05d}",
            name=f"{name} (as per Aug-2026 schedule)",
            category_id=cat.id,
            cost=cost,
            acquisition_date=_acq_date(years_ago, 1, 1),
            useful_life_years=life,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            residual_value=0.0,
            rate=rate,
            description=f"Seeded from bank schedule. Rate {rate}%.",
            status=AssetStatus.ACTIVE,
        )
        db.add(asset)
        created["assets"] += 1

    db.commit()
    return created