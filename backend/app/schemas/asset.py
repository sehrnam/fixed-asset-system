from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AssetCreate(BaseModel):
    asset_code: Optional[str] = Field(default=None, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    category_id: int

    cost: float
    acquisition_date: datetime
    useful_life_years: int
    depreciation_method: str
    residual_value: float = 0.0
    rate: Optional[float] = None

    description: Optional[str] = Field(default=None, max_length=512)
    location: Optional[str] = Field(default=None, max_length=128)

    @field_validator("cost")
    @classmethod
    def _cost_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Cost must be greater than zero.")
        return v

    @field_validator("useful_life_years")
    @classmethod
    def _life_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Useful life must be greater than zero.")
        return v

    @field_validator("residual_value")
    @classmethod
    def _residual_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Residual value cannot be negative.")
        return v


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category_id: Optional[int] = None
    cost: Optional[float] = None
    acquisition_date: Optional[datetime] = None
    useful_life_years: Optional[int] = None
    depreciation_method: Optional[str] = None
    residual_value: Optional[float] = None
    rate: Optional[float] = None
    description: Optional[str] = Field(default=None, max_length=512)
    location: Optional[str] = Field(default=None, max_length=128)

    @field_validator("cost")
    @classmethod
    def _cost_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Cost must be greater than zero.")
        return v

    @field_validator("useful_life_years")
    @classmethod
    def _life_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Useful life must be greater than zero.")
        return v

    @field_validator("residual_value")
    @classmethod
    def _residual_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("Residual value cannot be negative.")
        return v


class AssetRead(BaseModel):
    id: int
    asset_code: str
    name: str
    category_id: int
    category_name: Optional[str] = None
    cost: float
    acquisition_date: datetime
    useful_life_years: int
    depreciation_method: str
    residual_value: float
    rate: Optional[float]
    description: Optional[str]
    location: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime