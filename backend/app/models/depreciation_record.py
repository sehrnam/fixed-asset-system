"""
DepreciationRecord model - v3.0 (monthly).

v3.0 changes:
  - Monthly periods ("YYYY-MM" labels)
  - First-month proration fields (days_in_month, eligible_days, is_first_month)
  - Cap flag (capped) for final-month / cumulative-cap records
  - Removed months_charged_* fields (replaced by day-based tracking)
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DepreciationRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    period_id: int = Field(foreign_key="accountingperiod.id", index=True)

    # Denormalized for ordering without a join.
    # v3.0 format: "YYYY-MM" e.g. "2026-08"
    period_label: str = Field(index=True, max_length=16)
    period_end_date: datetime  # last calendar day of the month, 23:59:59

    method: str = Field(max_length=32, default="straight_line")

    # Money values (2 dp)
    opening_nbv: float
    depreciation: float
    accumulated_depreciation: float
    closing_nbv: float

    # v3.0 proration tracking
    # days_in_month: 28/29/30/31 for the period (0 if a full month applied)
    # eligible_days: days actually charged in the period
    #                - first month: days_in_month - acquisition_day
    #                - subsequent months: days_in_month
    #                - ineligible: 0
    # is_first_month: True only if this period is the acquisition month
    days_in_month: int = Field(default=0)
    eligible_days: int = Field(default=0)
    is_first_month: bool = Field(default=False)

    # v3.0 cap tracking
    # capped: True if the period charge was limited by the cumulative cap
    #         (cost - residual) or by the residual floor.
    capped: bool = Field(default=False)

    policy_source: str = Field(default="DEMO_v3.0", max_length=16)
    created_at: datetime = Field(default_factory=_utc_now)