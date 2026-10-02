from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccountingPeriodStatus:
    OPEN = "OPEN"
    LOCKED = "LOCKED"
    ALL = (OPEN, LOCKED)


class AccountingPeriod(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(index=True, unique=True, max_length=16)  # e.g. "2024"
    start_date: datetime
    end_date: datetime
    status: str = Field(default=AccountingPeriodStatus.OPEN, max_length=16)
    created_at: datetime = Field(default_factory=_utc_now)