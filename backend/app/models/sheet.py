from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SheetKind:
    SYSTEM = "SYSTEM"
    USER = "USER"
    ALL = (SYSTEM, USER)


class SystemView:
    ASSET_REGISTER = "asset_register"
    DEPRECIATION = "depreciation"
    DISPOSAL = "disposal"
    ALL = (ASSET_REGISTER, DEPRECIATION, DISPOSAL)


class Sheet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workbook_id: int = Field(foreign_key="workbook.id", index=True)
    name: str = Field(max_length=64)

    # Trimmed + lowercased for case-insensitive, whitespace-insensitive uniqueness.
    name_normalized: str = Field(max_length=64, index=True)

    order_index: int = Field(index=True)
    kind: str = Field(default=SheetKind.USER, max_length=16)
    system_view: Optional[str] = Field(default=None, max_length=32)
    is_dirty: bool = Field(default=False)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)