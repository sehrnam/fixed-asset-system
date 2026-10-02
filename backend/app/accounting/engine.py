"""
Server-side depreciation engine.

Authoritative. Never trusts client-supplied amounts (Doc 04 §10).
Pure-computation functions are separated from persistence so they can be
tested in isolation.
"""
from dataclasses import dataclass

from sqlmodel import Session, select

from app.accounting.methods import reducing_balance, straight_line
from app.accounting.months import chargeable_months
from app.accounting.rounding import round_money
from app.models.asset import Asset, DepreciationMethod
from app.models.depreciation_record import DepreciationRecord
from app.models.period import AccountingPeriod


@dataclass
class EngineOutput:
    months_charged: int
    depreciation: float
    closing_nbv: float
    accumulated_depreciation: float
    opening_nbv: float
    method: str


def months_life_total(asset: Asset) -> int:
    return int(asset.useful_life_years) * 12


def compute_period(
    asset: Asset,
    period: AccountingPeriod,
    opening_nbv: float,
    accumulated_prior: float,
    months_already_charged: int,
) -> EngineOutput:
    """Pure calculation for one (asset, period). No DB access, no side effects.

    Applies the frozen demo accounting policy exactly:
      - commencement = acquisition date
      - partial year = monthly pro-rating; acquisition month = full month
      - rounding = 2 dp after method calc, before persistence
      - reducing balance = opening NBV x rate, floored at residual
      - no negative depreciation
    """
    months_in_period = chargeable_months(asset, period)
    months_remaining = max(months_life_total(asset) - months_already_charged, 0)
    months_charged = min(months_in_period, months_remaining)

    if months_charged <= 0:
        return EngineOutput(
            months_charged=0,
            depreciation=0.0,
            closing_nbv=opening_nbv,
            accumulated_depreciation=accumulated_prior,
            opening_nbv=opening_nbv,
            method=asset.depreciation_method,
        )

    if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
        raw = straight_line.period_depreciation(asset, months_charged)
    elif asset.depreciation_method == DepreciationMethod.REDUCING_BALANCE:
        raw = reducing_balance.period_depreciation_before_floor(
            asset, opening_nbv, months_charged
        )
        raw = reducing_balance.apply_residual_floor(
            raw, opening_nbv, asset.residual_value
        )
    else:
        raise ValueError(f"Unsupported depreciation method: {asset.depreciation_method}")

    depreciation = round_money(raw)

    # Safety: no negative depreciation, ever.
    if depreciation < 0:
        depreciation = 0.0

    closing_nbv = round_money(opening_nbv - depreciation)
    accumulated = round_money(accumulated_prior + depreciation)

    return EngineOutput(
        months_charged=months_charged,
        depreciation=depreciation,
        closing_nbv=closing_nbv,
        accumulated_depreciation=accumulated,
        opening_nbv=opening_nbv,
        method=asset.depreciation_method,
    )


def run_for_asset(
    db: Session, asset: Asset, period: AccountingPeriod
) -> DepreciationRecord:
    """Compute and persist one period's depreciation for one asset.

    Reads prior records to chain NBV and cumulative months. Idempotent:
    if a record already exists for (asset, period), it is overwritten.
    """
    prior = db.exec(
        select(DepreciationRecord)
        .where(DepreciationRecord.asset_id == asset.id)
        .where(DepreciationRecord.period_label < period.label)
        .order_by(DepreciationRecord.period_label.desc())
    ).first()

    if prior is None:
        opening_nbv = asset.cost
        accumulated_prior = 0.0
        months_already = 0
    else:
        opening_nbv = prior.closing_nbv
        accumulated_prior = prior.accumulated_depreciation
        months_already = prior.months_charged_cumulative

    out = compute_period(
        asset,
        period,
        opening_nbv=opening_nbv,
        accumulated_prior=accumulated_prior,
        months_already_charged=months_already,
    )

    existing = db.exec(
        select(DepreciationRecord)
        .where(DepreciationRecord.asset_id == asset.id)
        .where(DepreciationRecord.period_id == period.id)
    ).first()

    if existing is None:
        rec = DepreciationRecord(
            asset_id=asset.id,
            period_id=period.id,
            period_label=period.label,
            period_end_date=period.end_date,
            method=out.method,
            opening_nbv=out.opening_nbv,
            depreciation=out.depreciation,
            accumulated_depreciation=out.accumulated_depreciation,
            closing_nbv=out.closing_nbv,
            months_charged_this_period=out.months_charged,
            months_charged_cumulative=months_already + out.months_charged,
            policy_source="DEMO",
        )
        db.add(rec)
    else:
        existing.method = out.method
        existing.opening_nbv = out.opening_nbv
        existing.depreciation = out.depreciation
        existing.accumulated_depreciation = out.accumulated_depreciation
        existing.closing_nbv = out.closing_nbv
        existing.months_charged_this_period = out.months_charged
        existing.months_charged_cumulative = months_already + out.months_charged
        db.add(existing)
        rec = existing

    db.commit()
    db.refresh(rec)
    return rec


def net_book_value_at(
    asset: Asset, records: list[DepreciationRecord], period_label: str
) -> float:
    """Return the NBV at the end of `period_label` using stored records.

    Used by disposal logic in M5; exposed now as a pure function so it can be
    tested without the disposal workflow existing yet.
    """
    relevant = [r for r in records if r.period_label <= period_label]
    if not relevant:
        return asset.cost
    latest = max(relevant, key=lambda r: r.period_label)
    return latest.closing_nbv