"""
Server-side depreciation engine - v3.0.

Authoritative. Never trusts client-supplied amounts.
Pure-computation functions are separated from persistence so they can be
tested in isolation.

v3.0 changes:
  - Straight-line only (reducing-balance removed from active workflow)
  - Monthly periods (calculation date = last calendar day of the month)
  - First-month proration excludes the acquisition date itself
  - Cumulative cap at (cost - residual)
  - Continue until cap is hit, then cap the final month

All decisions are read from AccountingPolicy (policy.py). This module does
not hard-code any policy value.
"""
from dataclasses import dataclass

from sqlmodel import Session, select

from app.accounting.months import proration_for_period
from app.accounting.rounding import round_money
from app.models.asset import Asset, DepreciationMethod
from app.models.depreciation_record import DepreciationRecord
from app.models.period import AccountingPeriod


@dataclass
class EngineOutput:
    # First-month proration info
    days_in_month: int            # 0 if not first month
    eligible_days: int            # 0 if not first month
    is_first_month: bool          # True if this is the acquisition month

    # Whether this period received a full-month charge
    full_month_charged: bool

    # Money
    monthly_base: float           # (cost - residual) / (life * 12), rounded
    depreciation: float           # this period's charge
    opening_nbv: float
    closing_nbv: float
    accumulated_depreciation: float

    # Metadata
    method: str
    capped: bool                  # True if this period was capped


def monthly_straight_line_base(asset: Asset) -> float:
    """(Cost - Residual Value) / (Useful Life in Years x 12).

    Not rounded here. The caller rounds the final period charge.
    """
    life_months = int(asset.useful_life_years) * 12
    if life_months <= 0:
        return 0.0
    return (asset.cost - asset.residual_value) / life_months


def total_depreciable_amount(asset: Asset) -> float:
    """Maximum cumulative depreciation allowed for this asset."""
    return round_money(asset.cost - asset.residual_value)


def compute_period(
    asset: Asset,
    period: AccountingPeriod,
    opening_nbv: float,
    accumulated_prior: float,
) -> EngineOutput:
    """Pure calculation for one (asset, period). No DB access, no side effects.

    Applies the v3.0 accounting policy exactly:
      - Straight-line only
      - Monthly periods
      - First month = prorated by eligible days (acquisition date excluded)
      - Subsequent months = full monthly amount
      - Cumulative capped at (cost - residual)
      - Closing NBV never below residual
      - 2 dp rounding, after calc, before persistence
    """
    monthly_base_raw = monthly_straight_line_base(asset)
    cumulative_cap = total_depreciable_amount(asset)
    max_remaining = round_money(cumulative_cap - accumulated_prior)

    # Nothing left to depreciate - return a zero-charge output.
    if max_remaining <= 0:
        return EngineOutput(
            days_in_month=0,
            eligible_days=0,
            is_first_month=False,
            full_month_charged=False,
            monthly_base=round_money(monthly_base_raw),
            depreciation=0.0,
            opening_nbv=opening_nbv,
            closing_nbv=opening_nbv,
            accumulated_depreciation=accumulated_prior,
            method=DepreciationMethod.STRAIGHT_LINE,
            capped=True,
        )

    # Determine proration for this period.
    proration = proration_for_period(asset, period)

    if not proration.is_eligible:
        # Before acquisition, or no eligible days.
        return EngineOutput(
            days_in_month=0,
            eligible_days=0,
            is_first_month=False,
            full_month_charged=False,
            monthly_base=round_money(monthly_base_raw),
            depreciation=0.0,
            opening_nbv=opening_nbv,
            closing_nbv=opening_nbv,
            accumulated_depreciation=accumulated_prior,
            method=DepreciationMethod.STRAIGHT_LINE,
            capped=False,
        )

    # Compute raw charge for this period.
    if proration.is_first_month:
        raw = monthly_base_raw * (
            proration.eligible_days / proration.days_in_month
        )
    else:
        raw = monthly_base_raw

    depreciation = round_money(raw)

    # Apply cumulative cap.
    capped = False
    if depreciation > max_remaining:
        depreciation = max_remaining
        capped = True

    if depreciation < 0:
        depreciation = 0.0

    closing_nbv = round_money(opening_nbv - depreciation)
    accumulated = round_money(accumulated_prior + depreciation)

    # Safety: closing NBV must never fall below residual.
    if closing_nbv < asset.residual_value:
        depreciation = round_money(opening_nbv - asset.residual_value)
        if depreciation < 0:
            depreciation = 0.0
        closing_nbv = round_money(opening_nbv - depreciation)
        accumulated = round_money(accumulated_prior + depreciation)
        capped = True

    return EngineOutput(
        days_in_month=proration.days_in_month if proration.is_first_month else 0,
        eligible_days=proration.eligible_days if proration.is_first_month else 0,
        is_first_month=proration.is_first_month,
        full_month_charged=not proration.is_first_month,
        monthly_base=round_money(monthly_base_raw),
        depreciation=depreciation,
        opening_nbv=opening_nbv,
        closing_nbv=closing_nbv,
        accumulated_depreciation=accumulated,
        method=DepreciationMethod.STRAIGHT_LINE,
        capped=capped,
    )


def run_for_asset(
    db: Session, asset: Asset, period: AccountingPeriod
) -> DepreciationRecord:
    """Compute and persist one month's depreciation for one asset.

    Reads prior records to chain NBV and accumulated depreciation.
    Idempotent: if a record exists for (asset, period), it is overwritten.
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
    else:
        opening_nbv = prior.closing_nbv
        accumulated_prior = prior.accumulated_depreciation

    out = compute_period(
        asset,
        period,
        opening_nbv=opening_nbv,
        accumulated_prior=accumulated_prior,
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
            days_in_month=out.days_in_month,
            eligible_days=out.eligible_days,
            is_first_month=out.is_first_month,
            capped=out.capped,
            policy_source="DEMO_v3.0",
        )
        db.add(rec)
    else:
        existing.method = out.method
        existing.opening_nbv = out.opening_nbv
        existing.depreciation = out.depreciation
        existing.accumulated_depreciation = out.accumulated_depreciation
        existing.closing_nbv = out.closing_nbv
        existing.days_in_month = out.days_in_month
        existing.eligible_days = out.eligible_days
        existing.is_first_month = out.is_first_month
        existing.capped = out.capped
        db.add(existing)
        rec = existing

    db.commit()
    db.refresh(rec)
    return rec


def net_book_value_at(
    asset: Asset, records: list[DepreciationRecord], period_label: str
) -> float:
    """Return the NBV at the end of `period_label` using stored records.

    Used by disposal logic. Pure function so it can be tested in isolation.
    """
    relevant = [r for r in records if r.period_label <= period_label]
    if not relevant:
        return asset.cost
    latest = max(relevant, key=lambda r: r.period_label)
    return latest.closing_nbv