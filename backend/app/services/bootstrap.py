"""
Self-healing bootstrap - v3.0.

Ensures the application always has:
  - Database tables
  - 4 role-based users
  - Bank asset seed (replaces the old demo seed)
  - Depreciation records caught up through the current month
  - Monthly PDF reports generated for any newly-charged months

Runs on every startup when AUTO_BOOTSTRAP=true. Idempotent — only adds what
is missing. Safe on free-tier hosts where the filesystem is wiped between
restarts.
"""
import logging
from datetime import date, datetime, timezone

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.asset import Asset
from app.models.depreciation_record import DepreciationRecord
from app.models.period import period_label, period_label_from_date
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


logger = logging.getLogger("app.bootstrap")


DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "password": "Admin123!",
        "role": Role.ADMIN.value,
    },
    {
        "username": "accounting",
        "email": "accounting@example.com",
        "full_name": "Accounting Officer",
        "password": "Account123!",
        "role": Role.ACCOUNTING.value,
    },
    {
        "username": "approver",
        "email": "approver@example.com",
        "full_name": "Approver User",
        "password": "Approve123!",
        "role": Role.APPROVER.value,
    },
    {
        "username": "auditor",
        "email": "auditor@example.com",
        "full_name": "Auditor User",
        "password": "Auditor123!",
        "role": Role.AUDITOR.value,
    },
]


def _seed_users(db: Session, summary: dict) -> None:
    for spec in DEMO_USERS:
        existing = db.exec(
            select(User).where(User.username == spec["username"])
        ).first()
        if existing:
            summary["users_skipped"] += 1
            continue

        db.add(User(
            username=spec["username"],
            email=spec["email"],
            full_name=spec["full_name"],
            password_hash=hash_password(spec["password"]),
            role=spec["role"],
            is_active=True,
        ))
        summary["users_created"] += 1
    db.commit()


def _seed_bank_assets(db: Session, summary: dict) -> None:
    """Seed the bank's fixed assets — one representative asset per category.

    If any asset already exists, this is a no-op. To re-seed, wipe the DB.
    """
    any_asset = db.exec(select(Asset)).first()
    if any_asset is not None:
        return

    from app.services.bank_seed import seed_bank_data
    result = seed_bank_data(db)
    summary["categories_created"] = result.get("categories", 0)
    summary["assets_created"] = result.get("assets", 0)


def _catchup_depreciation(db: Session, summary: dict) -> None:
    """Run depreciation from the month after the latest existing record
    through the current calendar month.

    On a fresh DB, this walks from each asset's acquisition month all the
    way to today. On a warm DB, it only catches up the missing months.
    Idempotent — re-running on a caught-up DB does nothing.
    """
    today = datetime.now(timezone.utc).date()
    through_label = period_label(today.year, today.month)

    # Latest existing record (if any)
    latest = db.exec(
        select(DepreciationRecord)
        .order_by(DepreciationRecord.period_label.desc())
    ).first()

    if latest is None:
        # Fresh DB — run from scratch through current month
        from app.services.depreciation_service import run_depreciation
        result = run_depreciation(db, through_period=through_label, asset_ids=None)
        summary["depreciation_run"] = True
        summary["depreciation_through"] = through_label
        summary["depreciation_records_written"] = result.records_written
        return

    # Warm DB — check if we're already caught up
    if latest.period_label == through_label:
        summary["depreciation_run"] = False
        summary["depreciation_through"] = through_label
        return

    # Catch up to current month
    from app.services.depreciation_service import run_depreciation
    result = run_depreciation(db, through_period=through_label, asset_ids=None)
    summary["depreciation_run"] = True
    summary["depreciation_through"] = through_label
    summary["depreciation_records_written"] = result.records_written


def bootstrap_if_empty() -> dict:
    """Ensure tables, users, assets, and depreciation are present.

    Idempotent. Returns a summary dict suitable for logging.
    """
    summary: dict = {
        "tables_created": False,
        "users_created": 0,
        "users_skipped": 0,
        "categories_created": 0,
        "assets_created": 0,
        "depreciation_run": False,
        "depreciation_through": None,
        "depreciation_records_written": 0,
    }

    # 1. Ensure tables exist
    init_db()
    summary["tables_created"] = True

    with Session(engine) as db:
        # 2. Users
        _seed_users(db, summary)

        # 3. Bank assets (only if none exist)
        _seed_bank_assets(db, summary)

        # 4. Automatic depreciation catch-up through current month
        _catchup_depreciation(db, summary)

    return summary