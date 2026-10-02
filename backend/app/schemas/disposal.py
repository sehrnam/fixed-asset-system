from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DisposalCreate(BaseModel):
    asset_id: int
    disposal_date: datetime
    proceeds: float = Field(ge=0)
    reason: Optional[str] = Field(default=None, max_length=512)


class DisposalRead(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    disposal_date: datetime
    proceeds: float
    reason: Optional[str]
    nbv_at_disposal: float
    gain_loss: float
    method_used: str
    period_label_used: str
    status: str
    requested_by: int
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime