from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.accounting.engine import net_book_value_at, run_for_asset
from app.accounting.rounding import round_money
from app.models.asset import Asset, AssetStatus
from app.models.depreciation_record import DepreciationRecord
from app.models.period import AccountingPeriod
from app.schemas.depreciation import (
    DepreciationPeriodSummary,
    DepreciationRecordRead,
    DepreciationRunResult,
)


def get_or_create_period(db: Session, label: str) -> AccountingPeriod:
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
        status="OPEN",
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


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
        months_charged_this_period=record.months_charged_this_period,
        months_charged_cumulative=record.months_charged_cumulative,
        policy_source=record.policy_source,
    )


def run_depreciation(
    db: Session,
    *,
    through_period: str,
    asset_ids: list[int] | None = None,
) -> DepreciationRunResult:
    """Compute and persist depreciation for all active assets through
    `through_period`, walking the NBV chain from each asset's acquisition year.

    Idempotent: re-running recomputes and overwrites existing records.
    """
    through = get_or_create_period(db, through_period)
    through_year = through.end_date.year

    stmt = select(Asset).where(Asset.status != AssetStatus.DISPOSED)
    if asset_ids:
        stmt = stmt.where(Asset.id.in_(asset_ids))
    assets = list(db.exec(stmt).all())

    written = 0
    for asset in assets:
        commencement_year = asset.acquisition_date.year
        for year in range(commencement_year, through_year + 1):
            period = get_or_create_period(db, str(year))
            rec = run_for_asset(db, asset, period)
            if rec is not None:
                written += 1

    return DepreciationRunResult(
        through_period=through_period,
        assets_processed=len(assets),
        records_written=written,
    )


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


def get_period_summary(db: Session, period_label: str) -> DepreciationPeriodSummary:
    records = list(
        db.exec(
            select(DepreciationRecord).where(
                DepreciationRecord.period_label == period_label
            )
        ).all()
    )
    total = round_money(sum(r.depreciation for r in records))
    return DepreciationPeriodSummary(
        period_label=period_label,
        total_depreciation=total,
        record_count=len(records),
    )


def get_nbv_at(db: Session, asset_id: int, period_label: str) -> float:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    records = list(
        db.exec(
            select(DepreciationRecord).where(DepreciationRecord.asset_id == asset_id)
        ).all()
    )
    return net_book_value_at(asset, records, period_label)