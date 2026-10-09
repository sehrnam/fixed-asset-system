"""
Depreciation schemas - v3.0 (monthly).

v3.0 changes:
  - DepreciationRunRequest.through_period is now "YYYY-MM" (length 7)
  - DepreciationRecordRead replaces months_charged_* with day-based fields
"""
from typing import Optional

from pydantic import BaseModel, Field


class DepreciationRunRequest(BaseModel):
    # v3.0: monthly label "YYYY-MM"
    through_period: str = Field(min_length=7, max_length=7)
    asset_ids: Optional[list[int]] = None


class DepreciationRecordRead(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    period_label: str          # "YYYY-MM"
    period_end_date: str
    method: str

    # Money
    opening_nbv: float
    depreciation: float
    accumulated_depreciation: float
    closing_nbv: float

    # v3.0 proration tracking
    days_in_month: int         # 28/29/30/31 for the period, 0 if full month
    eligible_days: int         # days actually charged this period
    is_first_month: bool       # True if this is the acquisition month
    capped: bool               # True if the charge was limited by cap/floor

    policy_source: str


class DepreciationRunResult(BaseModel):
    through_period: str
    assets_processed: int
    records_written: int


class DepreciationPeriodSummary(BaseModel):
    period_label: str
    total_depreciation: float
    record_count: int