from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    SQLModel 0.0.47+ rejects naive datetimes for persisted DateTime fields,
    so we consistently produce timezone-aware UTC values here.
    """
    return datetime.now(timezone.utc)


class AuthSession(SQLModel, table=True):
    """Server-side session record. The token is the primary key; cookies carry it."""

    id: str = Field(primary_key=True, max_length=128)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime
    revoked: bool = Field(default=False)
    
