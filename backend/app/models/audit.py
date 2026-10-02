from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    SQLModel 0.0.47+ rejects naive datetimes for persisted DateTime fields,
    so we consistently produce timezone-aware UTC values here.
    """
    return datetime.now(timezone.utc)


class AuditEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=_utc_now, index=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id")
    actor_username: Optional[str] = Field(default=None, max_length=64)
    action: str = Field(max_length=64, index=True)
    target_type: Optional[str] = Field(default=None, max_length=64)
    target_id: Optional[str] = Field(default=None, max_length=64)
    result: str = Field(default="SUCCESS", max_length=16)
    metadata_json: Optional[str] = Field(default=None)
    source_context: Optional[str] = Field(default=None, max_length=255)