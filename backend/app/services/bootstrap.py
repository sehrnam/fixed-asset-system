"""
Self-healing bootstrap.

Ensures the application always has working users and demo data,
even on free-tier hosts where the filesystem is wiped between
restarts. Safe to call on every startup — it only adds what is
missing and never duplicates.
"""
import logging

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.asset import Asset
from app.models.depreciation_record import DepreciationRecord
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


def bootstrap_if_empty() -> dict:
    """Ensure tables exist, users exist, and demo data exists.

    Idempotent. Returns a summary dict suitable for logging.
    """
    summary = {
        "tables_created": False,
        "users_created": 0,
        "users_skipped": 0,
        "categories_created": 0,
        "assets_created": 0,
        "depreciation_run": False,
    }

    # 1. Create tables if missing (no-op when they exist)
    init_db()
    summary["tables_created"] = True

    with Session(engine) as db:
        # 2. Users — seed any missing by username
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

        # 3. Demo categories + assets — only if NO assets exist at all
        any_asset = db.exec(select(Asset)).first()
        if any_asset is None:
            from app.services.demo_seed import seed_demo_data
            result = seed_demo_data(db)
            summary["categories_created"] = result.get("categories", 0)
            summary["assets_created"] = result.get("assets", 0)

        # 4. Depreciation — only if NO records exist
        any_record = db.exec(select(DepreciationRecord)).first()
        if any_record is None and summary["assets_created"] > 0:
            from app.services.depreciation_service import run_depreciation
            run_depreciation(db, through_period="2024", asset_ids=None)
            summary["depreciation_run"] = True

    return summary