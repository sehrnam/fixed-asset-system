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
    period_label: str = Field(index=True, max_length=16)   # e.g. "2024"
    period_end_date: datetime

    method: str = Field(max_length=32)

    opening_nbv: float
    depreciation: float
    accumulated_depreciation: float
    closing_nbv: float

    months_charged_this_period: int
    months_charged_cumulative: int

    policy_source: str = Field(default="DEMO", max_length=16)
    created_at: datetime = Field(default_factory=_utc_now)