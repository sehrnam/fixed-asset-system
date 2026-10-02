"""Tests for the M3 accounting engine.

Covers the frozen demo policy cases from Doc 09:
  A. Straight-line full year
  B. Straight-line partial year
  C. Reducing balance full year
  D. Reducing-balance residual floor
  E. NBV computation for disposal (helper only in M3)
  F. Rounding to 2 dp
  G. Reconciliation identities
"""
from datetime import datetime, timezone

import pytest

from app.accounting.engine import (
    compute_period,
    months_life_total,
    net_book_value_at,
)
from app.accounting.months import chargeable_months
from app.accounting.rounding import round_money
from app.models.asset import Asset, AssetStatus, DepreciationMethod
from app.models.period import AccountingPeriod


def _period(year: int) -> AccountingPeriod:
    return AccountingPeriod(
        id=year,  # not persisted; just a namespace for pure tests
        label=str(year),
        start_date=datetime(year, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        status="OPEN",
    )


def _asset(
    *,
    cost: float,
    residual: float,
    life: int,
    method: str,
    rate: float | None = None,
    acquisition_year: int = 2024,
    acquisition_month: int = 1,
    acquisition_day: int = 1,
) -> Asset:
    return Asset(
        id=1,
        asset_code="FA-TEST",
        name="Test Asset",
        category_id=1,
        cost=cost,
        acquisition_date=datetime(
            acquisition_year,
            acquisition_month,
            acquisition_day,
            tzinfo=timezone.utc,
        ),
        useful_life_years=life,
        depreciation_method=method,
        residual_value=residual,
        rate=rate,
        status=AssetStatus.ACTIVE,
    )


# ---------- Case A — straight-line full year ----------

def test_straight_line_full_year():
    """Doc 09 case: 100,000 / 10,000 / 5y → 18,000 per full year."""
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=1,
    )
    out = compute_period(
        asset,
        _period(2024),
        opening_nbv=100_000.0,
        accumulated_prior=0.0,
        months_already_charged=0,
    )
    assert out.months_charged == 12
    assert out.depreciation == 18_000.0
    assert out.closing_nbv == 82_000.0
    assert out.accumulated_depreciation == 18_000.0


# ---------- Case B — straight-line partial year ----------

def test_straight_line_partial_year_acquisition_march():
    """Acquired March 2024 → March-Dec = 10 months → 18,000 x 10/12 = 15,000."""
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=3,
        acquisition_day=17,
    )
    out = compute_period(
        asset,
        _period(2024),
        opening_nbv=100_000.0,
        accumulated_prior=0.0,
        months_already_charged=0,
    )
    assert out.months_charged == 10
    assert out.depreciation == 15_000.0
    assert out.closing_nbv == 85_000.0


def test_straight_line_partial_year_final_period():
    """Asset acquired March 2024, 5y life ends Feb 2029.

    2029 is the last period: Jan-Feb = 2 months → 18,000 x 2/12 = 3,000.
    """
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=3,
    )
    # By the start of 2029 we've already charged 58 of 60 months.
    out = compute_period(
        asset,
        _period(2029),
        opening_nbv=13_000.0,
        accumulated_prior=87_000.0,
        months_already_charged=58,
    )
    assert out.months_charged == 2
    assert out.depreciation == 3_000.0
    assert out.closing_nbv == 10_000.0
    assert out.accumulated_depreciation == 90_000.0


def test_straight_line_stops_at_useful_life_end():
    """Once all life months are consumed, no further depreciation is charged."""
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=1,
    )
    out = compute_period(
        asset,
        _period(2030),
        opening_nbv=10_000.0,
        accumulated_prior=90_000.0,
        months_already_charged=60,
    )
    assert out.months_charged == 0
    assert out.depreciation == 0.0
    assert out.closing_nbv == 10_000.0


# ---------- Case C — reducing balance full year ----------

def test_reducing_balance_full_year():
    """Doc 09 case: opening NBV 100,000 x 20% → 20,000; closing NBV 80,000."""
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=10,
        method=DepreciationMethod.REDUCING_BALANCE,
        rate=20.0,
        acquisition_year=2024,
        acquisition_month=1,
    )
    out = compute_period(
        asset,
        _period(2024),
        opening_nbv=100_000.0,
        accumulated_prior=0.0,
        months_already_charged=0,
    )
    assert out.months_charged == 12
    assert out.depreciation == 20_000.0
    assert out.closing_nbv == 80_000.0


def test_reducing_balance_chained_year():
    """Year 2 opening = 80,000 → 80,000 x 20% = 16,000; closing = 64,000."""
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=10,
        method=DepreciationMethod.REDUCING_BALANCE,
        rate=20.0,
    )
    out = compute_period(
        asset,
        _period(2025),
        opening_nbv=80_000.0,
        accumulated_prior=20_000.0,
        months_already_charged=12,
    )
    assert out.depreciation == 16_000.0
    assert out.closing_nbv == 64_000.0


# ---------- Case D — reducing-balance residual floor ----------

def test_reducing_balance_residual_floor():
    """Would-be 20,000 capped at opening - residual = 10,000."""
    asset = _asset(
        cost=100_000.0,
        residual=90_000.0,
        life=10,
        method=DepreciationMethod.REDUCING_BALANCE,
        rate=20.0,
    )
    out = compute_period(
        asset,
        _period(2024),
        opening_nbv=100_000.0,
        accumulated_prior=0.0,
        months_already_charged=0,
    )
    assert out.depreciation == 10_000.0
    assert out.closing_nbv == 90_000.0


def test_reducing_balance_never_negative_when_at_floor():
    """If opening NBV already equals residual, depreciation is zero."""
    asset = _asset(
        cost=100_000.0,
        residual=90_000.0,
        life=10,
        method=DepreciationMethod.REDUCING_BALANCE,
        rate=20.0,
    )
    out = compute_period(
        asset,
        _period(2030),
        opening_nbv=90_000.0,
        accumulated_prior=10_000.0,
        months_already_charged=72,
    )
    assert out.depreciation == 0.0
    assert out.closing_nbv == 90_000.0


# ---------- Case E — NBV helper for disposal (M5 will use this) ----------

def test_net_book_value_at_picks_latest_record():
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
    )

    class _R:
        def __init__(self, label: str, closing: float) -> None:
            self.period_label = label
            self.closing_nbv = closing

    records = [_R("2024", 82_000.0), _R("2025", 64_000.0), _R("2026", 46_000.0)]
    assert net_book_value_at(asset, records, "2024") == 82_000.0
    assert net_book_value_at(asset, records, "2025") == 64_000.0
    assert net_book_value_at(asset, records, "2026") == 46_000.0
    assert net_book_value_at(asset, records, "2029") == 46_000.0


def test_net_book_value_at_before_any_records_returns_cost():
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    assert net_book_value_at(asset, [], "2024") == 100_000.0


# ---------- Case F — rounding ----------

def test_rounding_two_decimal_places():
    assert round_money(1.005) in (1.0, 1.01)  # Decimal path: ROUND_HALF_UP → 1.01
    assert round_money(1.015) == 1.02
    assert round_money(1.025) == 1.03
    assert round_money(33.333333) == 33.33
    assert round_money(33.335) == 33.34
    assert round_money(100.0) == 100.0


def test_rounding_applied_in_engine():
    """SL with repeating result: (100,000 - 0) / 3 = 33,333.333... → 33,333.33."""
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=3,
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    out = compute_period(
        asset,
        _period(2024),
        opening_nbv=100_000.0,
        accumulated_prior=0.0,
        months_already_charged=0,
    )
    assert out.depreciation == 33_333.33
    assert out.closing_nbv == 66_666.67


# ---------- Case G — reconciliation identities ----------

def test_reconciliation_cost_minus_closing_equals_accumulated():
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    out = compute_period(
        asset,
        _period(2025),
        opening_nbv=82_000.0,
        accumulated_prior=18_000.0,
        months_already_charged=12,
    )
    assert round_money(asset.cost - out.closing_nbv) == out.accumulated_depreciation


def test_reconciliation_opening_minus_dep_equals_closing():
    asset = _asset(
        cost=100_000.0,
        residual=10_000.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    out = compute_period(
        asset,
        _period(2025),
        opening_nbv=82_000.0,
        accumulated_prior=18_000.0,
        months_already_charged=12,
    )
    assert out.opening_nbv - out.depreciation == out.closing_nbv


# ---------- months.py focused tests ----------

def test_chargeable_months_before_commencement():
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2025,
    )
    assert chargeable_months(asset, _period(2024)) == 0


def test_chargeable_months_full_calendar_year():
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=1,
    )
    assert chargeable_months(asset, _period(2024)) == 12


def test_chargeable_months_acquisition_month_counts_full():
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=5,
        method=DepreciationMethod.STRAIGHT_LINE,
        acquisition_year=2024,
        acquisition_month=12,
        acquisition_day=31,
    )
    # Even acquired on the last day of December, December counts as full.
    assert chargeable_months(asset, _period(2024)) == 1


def test_months_life_total():
    asset = _asset(
        cost=100_000.0,
        residual=0.0,
        life=7,
        method=DepreciationMethod.STRAIGHT_LINE,
    )
    assert months_life_total(asset) == 84