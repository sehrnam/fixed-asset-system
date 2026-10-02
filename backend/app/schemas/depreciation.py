from typing import Optional

from pydantic import BaseModel, Field


class DepreciationRunRequest(BaseModel):
    through_period: str = Field(min_length=4, max_length=16)
    asset_ids: Optional[list[int]] = None


class DepreciationRecordRead(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    period_label: str
    period_end_date: str
    method: str
    opening_nbv: float
    depreciation: float
    accumulated_depreciation: float
    closing_nbv: float
    months_charged_this_period: int
    months_charged_cumulative: int
    policy_source: str


class DepreciationRunResult(BaseModel):
    through_period: str
    assets_processed: int
    records_written: int


class DepreciationPeriodSummary(BaseModel):
    period_label: str
    total_depreciation: float
    record_count: int