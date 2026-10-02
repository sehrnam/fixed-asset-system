from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SheetSummary(BaseModel):
    id: int
    name: str
    order_index: int
    kind: str
    system_view: Optional[str]
    is_dirty: bool


class WorkbookRead(BaseModel):
    id: int
    name: str
    active_sheet_id: Optional[int]
    revision: int
    sheets: list[SheetSummary]
    created_at: datetime
    updated_at: datetime