from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DisposalStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ALL = (PENDING, APPROVED, REJECTED)


class Disposal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    disposal_date: datetime
    proceeds: float
    reason: Optional[str] = Field(default=None, max_length=512)

    # Snapshot of accounting state at the moment of request.
    # Frozen demo policy: gain/loss = proceeds - NBV at disposal date.
    nbv_at_disposal: float
    gain_loss: float
    method_used: str = Field(max_length=32)
    period_label_used: str = Field(max_length=16)

    status: str = Field(default=DisposalStatus.PENDING, max_length=16, index=True)
    requested_by: int = Field(foreign_key="user.id")
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)