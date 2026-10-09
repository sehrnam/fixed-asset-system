"""
Depreciation service - v3.0 (monthly).

v3.0 changes:
  - Periods are monthly ("YYYY-MM"), created/derived via period helpers
  - run_depreciation walks months, not years
  - Reads/writes the new proration + cap fields on DepreciationRecord
  - No reducing-balance path
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.accounting.engine import net_book_value_at, run_for_asset
from app.accounting.rounding import round_money
from app.models.asset import Asset, AssetStatus
from app.models.depreciation_record import DepreciationRecord
from app.models.period import (
    AccountingPeriod,
    list_months_between,
    parse_period_label,
    period_label,
    period_label_from_date,
)
from app.schemas.depreciation import (
    DepreciationPeriodSummary,
    DepreciationRecordRead,
    DepreciationRunResult,
)


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

def get_or_create_period(db: Session, label: str) -> AccountingPeriod:
    """Fetch the monthly period for 'YYYY-MM', creating it if missing."""
    existing = db.exec(
        select(AccountingPeriod).where(AccountingPeriod.label == label)
    ).first()
    if existing is not None:
        return existing

    try:
        year, month = parse_period_label(label)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period label {label!r}; expected 'YYYY-MM'",
        )

    # First day of month 00:00:00
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Last instant of month (23:59:59) = first of next month minus 1 second
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        next_month_start = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = (next_month_start - timedelta(seconds=1)).replace(microsecond=0)

    period = AccountingPeriod(
        label=label,
        start_date=start,
        end_date=end,
        status="OPEN",
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _record_to_read(db: Session, record: DepreciationRecord) -> DepreciationRecordRead:
    asset = db.get(Asset, record.asset_id)
    return DepreciationRecordRead(
        id=record.id,
        asset_id=record.asset_id,
        asset_code=asset.asset_code if asset else "",
        asset_name=asset.name if asset else "",
        period_label=record.period_label,
        period_end_date=record.period_end_date.isoformat(),
        method=record.method,
        opening_nbv=record.opening_nbv,
        depreciation=record.depreciation,
        accumulated_depreciation=record.accumulated_depreciation,
        closing_nbv=record.closing_nbv,
        days_in_month=record.days_in_month,
        eligible_days=record.eligible_days,
        is_first_month=record.is_first_month,
        capped=record.capped,
        policy_source=record.policy_source,
    )


# ---------------------------------------------------------------------------
# Depreciation run
# ---------------------------------------------------------------------------

def run_depreciation(
    db: Session,
    *,
    through_period: str,
    asset_ids: list[int] | None = None,
) -> DepreciationRunResult:
    """Compute and persist depreciation for all active assets.

    Walks from each asset's acquisition month through `through_period`,
    month by month. Idempotent: re-running recomputes and overwrites
    existing records for the same period.

    Returns a summary: number of assets processed, number of records written.
    """
    try:
        through_year, through_month = parse_period_label(through_period)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period label {through_period!r}; expected 'YYYY-MM'",
        )

    # Ensure the target period exists before we start
    get_or_create_period(db, through_period)

    stmt = select(Asset).where(Asset.status != AssetStatus.DISPOSED)
    if asset_ids:
        stmt = stmt.where(Asset.id.in_(asset_ids))
    assets = list(db.exec(stmt).all())

    written = 0
    for asset in assets:
        commencement_label = period_label_from_date(asset.acquisition_date)
        try:
            start_year, start_month = parse_period_label(commencement_label)
        except ValueError:
            # Bad acquisition date - skip asset rather than crash the run
            continue

        # Every month from acquisition through the target month
        months = list_months_between(
            start_year, start_month, through_year, through_month
        )
        for (y, m) in months:
            label = period_label(y, m)
            period = get_or_create_period(db, label)
            rec = run_for_asset(db, asset, period)
            if rec is not None:
                written += 1

    return DepreciationRunResult(
        through_period=through_period,
        assets_processed=len(assets),
        records_written=written,
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_schedule_for_asset(db: Session, asset_id: int) -> list[DepreciationRecordRead]:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    records = list(
        db.exec(
            select(DepreciationRecord)
            .where(DepreciationRecord.asset_id == asset_id)
            .order_by(DepreciationRecord.period_label)
        ).all()
    )
    return [_record_to_read(db, r) for r in records]


def get_period_summary(db: Session, label: str) -> DepreciationPeriodSummary:
    try:
        parse_period_label(label)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period label {label!r}; expected 'YYYY-MM'",
        )

    records = list(
        db.exec(
            select(DepreciationRecord).where(
                DepreciationRecord.period_label == label
            )
        ).all()
    )
    total = round_money(sum(r.depreciation for r in records))
    return DepreciationPeriodSummary(
        period_label=label,
        total_depreciation=total,
        record_count=len(records),
    )


def list_period_summaries(db: Session) -> list[DepreciationPeriodSummary]:
    """Return every month that has depreciation records, newest first.

    Used by the frontend month picker and the Monthly Reports page.
    """
    labels = list(
        db.exec(
            select(DepreciationRecord.period_label)
            .distinct()
            .order_by(DepreciationRecord.period_label.desc())
        ).all()
    )
    return [get_period_summary(db, label) for label in labels]


def get_nbv_at(db: Session, asset_id: int, label: str) -> float:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    records = list(
        db.exec(
            select(DepreciationRecord).where(DepreciationRecord.asset_id == asset_id)
        ).all()
    )
    return net_book_value_at(asset, records, label)