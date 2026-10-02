from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.audit.writer import write_audit
from app.models.period import AccountingPeriod, AccountingPeriodStatus
from app.models.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_period_by_label(db: Session, label: str) -> AccountingPeriod:
    """Fetch an existing period by label. Raises 404 if not found.

    Use this for paths that require the period to exist (reports, locking).
    """
    period = db.exec(
        select(AccountingPeriod).where(AccountingPeriod.label == label)
    ).first()
    if period is None:
        raise HTTPException(status_code=404, detail=f"Period {label} not found")
    return period


def get_or_create_period(db: Session, label: str) -> AccountingPeriod:
    """Fetch the period by label, creating it as OPEN if it doesn't exist.

    Used by write paths (disposal, journal, depreciation) that need a period
    to exist but should not require it to have been pre-provisioned.
    """
    existing = db.exec(
        select(AccountingPeriod).where(AccountingPeriod.label == label)
    ).first()
    if existing is not None:
        return existing

    try:
        year = int(label)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid period label: {label!r}")

    period = AccountingPeriod(
        label=label,
        start_date=datetime(year, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        status=AccountingPeriodStatus.OPEN,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


def assert_period_open(db: Session, label: str) -> AccountingPeriod:
    """Ensure a period exists AND is OPEN. Auto-creates if missing.

    Raises 409 if the period is LOCKED — the only condition that must block
    write paths.
    """
    period = get_or_create_period(db, label)
    if period.status == AccountingPeriodStatus.LOCKED:
        raise HTTPException(
            status_code=409,
            detail=f"Period {label} is LOCKED and cannot be modified",
        )
    return period


def lock_period(db: Session, label: str, actor: User) -> AccountingPeriod:
    period = get_period_by_label(db, label)
    if period.status == AccountingPeriodStatus.LOCKED:
        return period
    period.status = AccountingPeriodStatus.LOCKED
    db.add(period)
    write_audit(
        db,
        action="PERIOD_LOCKED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="AccountingPeriod",
        target_id=label,
    )
    db.commit()
    db.refresh(period)
    return period


def unlock_period(db: Session, label: str, actor: User) -> AccountingPeriod:
    period = get_period_by_label(db, label)
    if period.status == AccountingPeriodStatus.OPEN:
        return period
    period.status = AccountingPeriodStatus.OPEN
    db.add(period)
    write_audit(
        db,
        action="PERIOD_UNLOCKED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="AccountingPeriod",
        target_id=label,
    )
    db.commit()
    db.refresh(period)
    return period


def list_periods(db: Session) -> list[AccountingPeriod]:
    return list(db.exec(select(AccountingPeriod).order_by(AccountingPeriod.label)).all())