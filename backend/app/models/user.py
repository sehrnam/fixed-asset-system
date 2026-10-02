from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    SQLModel 0.0.47+ rejects naive datetimes for persisted DateTime fields.
    Using timezone-aware values here keeps the model compatible and matches
    the recommended practice of storing UTC.
    """
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=64)
    email: str = Field(index=True, unique=True, max_length=255)
    full_name: str = Field(max_length=255)
    password_hash: str
    role: str = Field(max_length=32, index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)