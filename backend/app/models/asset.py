from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AssetStatus:
    ACTIVE = "ACTIVE"
    DISPOSED = "DISPOSED"
    RETIRED = "RETIRED"
    ALL = (ACTIVE, DISPOSED, RETIRED)


class DepreciationMethod:
    STRAIGHT_LINE = "straight_line"
    REDUCING_BALANCE = "reducing_balance"
    ALL = (STRAIGHT_LINE, REDUCING_BALANCE)


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_code: str = Field(index=True, unique=True, max_length=32)
    name: str = Field(max_length=255)
    category_id: int = Field(foreign_key="assetcategory.id", index=True)

    cost: float
    acquisition_date: datetime
    useful_life_years: int
    depreciation_method: str = Field(max_length=32)
    residual_value: float = 0.0
    rate: Optional[float] = None  # percent; required for reducing_balance

    description: Optional[str] = Field(default=None, max_length=512)
    location: Optional[str] = Field(default=None, max_length=128)
    status: str = Field(default=AssetStatus.ACTIVE, max_length=16, index=True)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)