"""
Month and proration helpers for the v3.0 monthly accounting model.

v3.0 rules (from REVISED ACCOUNTING REQUIREMENTS - AUTHORITATIVE, 2026-10-09):
  - Periods are monthly. Calculation date = last calendar day of the month.
  - Depreciation commences on the acquisition date.
  - First-month proration: exclude the acquisition date itself.
        eligible_days = days_in_month - acquisition_day
        first_month_dep = monthly_base * (eligible_days / days_in_month)
  - Subsequent months: full monthly amount.

This module is pure: no DB access, no side effects.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime

from app.models.asset import Asset
from app.models.period import AccountingPeriod


def _to_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def days_in_month(year: int, month: int) -> int:
    """Return the number of calendar days in the given month (28/29/30/31)."""
    return calendar.monthrange(year, month)[1]


@dataclass(frozen=True)
class Proration:
    """Result of proration analysis for one (asset, period) pair."""
    is_eligible: bool      # True if the asset should be charged in this period
    is_first_month: bool   # True if this period is the acquisition month
    days_in_month: int     # 28/29/30/31 - always populated
    eligible_days: int     # days charged this period (0 if not eligible)


def proration_for_period(asset: Asset, period: AccountingPeriod) -> Proration:
    """Compute the proration for `asset` in `period` under v3.0 rules.

    Cases handled:
      1. Period ends before acquisition month -> not eligible, 0 days.
      2. Period is before acquisition month (same month check) -> see (3).
      3. Period is the acquisition month -> first month, prorated by days.
      4. Period is after the acquisition month -> full month (all days).
      5. Same month but acquisition day = last day -> eligible_days = 0.
    """
    acquisition = _to_date(asset.acquisition_date)
    period_start = _to_date(period.start_date)
    period_end = _to_date(period.end_date)

    # Which month/year does this period represent?
    # We assume monthly periods: start_date = first of month, end_date = last.
    period_year = period_start.year
    period_month = period_start.month
    dim = days_in_month(period_year, period_month)

    # The acquisition month as a (year, month) tuple
    acq_ym = (acquisition.year, acquisition.month)
    period_ym = (period_year, period_month)

    # Case 1 — period is entirely before acquisition month
    if period_ym < acq_ym:
        return Proration(
            is_eligible=False,
            is_first_month=False,
            days_in_month=dim,
            eligible_days=0,
        )

    # Case 3 — the acquisition month
    if period_ym == acq_ym:
        eligible_days = dim - acquisition.day
        if eligible_days < 0:
            eligible_days = 0
        return Proration(
            is_eligible=eligible_days > 0,
            is_first_month=True,
            days_in_month=dim,
            eligible_days=eligible_days,
        )

    # Case 4 — a subsequent month (full month)
    return Proration(
        is_eligible=True,
        is_first_month=False,
        days_in_month=dim,
        eligible_days=dim,
    )


def month_end_date(year: int, month: int) -> date:
    """Return the last calendar day of the given month."""
    return date(year, month, days_in_month(year, month))