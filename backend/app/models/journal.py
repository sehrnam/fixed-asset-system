from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JournalStatus:
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    EXPORTED = "EXPORTED"
    ALL = (DRAFT, APPROVED, EXPORTED)


class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True, max_length=32)
    period_id: int = Field(foreign_key="accountingperiod.id", index=True)
    period_label: str = Field(index=True, max_length=16)
    entry_date: datetime
    description: str = Field(max_length=255)
    kind: str = Field(default="DEPRECIATION", max_length=32)

    status: str = Field(default=JournalStatus.DRAFT, max_length=16, index=True)

    total_debit: float = 0.0
    total_credit: float = 0.0

    prepared_by: int = Field(foreign_key="user.id")
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class JournalLine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    journal_entry_id: int = Field(foreign_key="journalentry.id", index=True)
    account_code: str = Field(max_length=32)
    account_name: str = Field(max_length=128)
    debit: float = 0.0
    credit: float = 0.0
    memo: Optional[str] = Field(default=None, max_length=255)