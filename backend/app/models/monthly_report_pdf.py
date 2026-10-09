"""
Stores generated monthly PDF reports.

Each row is one month's "FIXED ASSETS AS AT ..." schedule, stored as
a BLOB so it survives warm restarts of the SQLite file.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MonthlyReportPDF(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # "YYYY-MM"
    period_label: str = Field(index=True, unique=True, max_length=16)

    filename: str = Field(max_length=128)
    content: bytes = Field(default=b"")
    size_bytes: int = Field(default=0)

    generated_at: datetime = Field(default_factory=_utc_now)
    trigger: str = Field(default="startup_catchup", max_length=32)
    policy_source: str = Field(default="DEMO_v3.0", max_length=16)