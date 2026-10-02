from pydantic import BaseModel


class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    asset_count: int
    total_cost: float
    total_nbv: float


class DashboardRead(BaseModel):
    total_asset_cost: float
    total_accumulated_depreciation: float
    total_nbv: float
    current_period_label: str
    current_period_depreciation: float
    category_summary: list[CategorySummary]