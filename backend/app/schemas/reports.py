from typing import Optional

from pydantic import BaseModel


class TableReport(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[str]]
    totals: Optional[dict[str, float]] = None


class AssetMovementRow(BaseModel):
    category_id: Optional[int]
    category_name: str
    opening_cost: float
    additions: float
    disposals: float
    closing_cost: float
    opening_accum: float
    dep_charge: float
    disposals_accum: float
    closing_accum: float
    closing_nbv: float


class AssetMovementReport(BaseModel):
    period_label: str
    rows: list[AssetMovementRow]
    totals: AssetMovementRow