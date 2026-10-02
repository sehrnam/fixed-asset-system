from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Cell(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sheet_id: int = Field(foreign_key="sheet.id", index=True)
    row: int = Field(index=True)   # 1-based
    col: int = Field(index=True)   # 1-based

    raw: str = Field(default="", max_length=4096)
    computed: Optional[str] = Field(default=None, max_length=4096)
    is_formula: bool = Field(default=False)
    error: Optional[str] = Field(default=None, max_length=255)

    updated_at: datetime = Field(default_factory=_utc_now)