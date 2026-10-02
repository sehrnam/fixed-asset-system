import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from app.config import settings
from app.models.auth_session import AuthSession


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    SQLModel 0.0.47+ rejects naive datetimes for persisted DateTime fields,
    and comparisons between naive and aware datetimes raise TypeError.
    Using aware UTC values everywhere keeps storage and comparisons consistent.
    """
    return datetime.now(timezone.utc)


def create_session(db: Session, user_id: int) -> AuthSession:
    token = secrets.token_urlsafe(32)
    now = _utc_now()
    sess = AuthSession(
        id=token,
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_lifetime_hours),
        revoked=False,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def get_valid_session(db: Session, token: str) -> Optional[AuthSession]:
    if not token:
        return None

    sess = db.exec(select(AuthSession).where(AuthSession.id == token)).first()
    if sess is None:
        return None
    if sess.revoked:
        return None

    # Defensive: coerce a naive stored value to UTC in case the row was
    # written before the timezone-aware fix. Prevents TypeError when
    # comparing naive vs aware datetimes.
    expires_at = sess.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < _utc_now():
        return None

    return sess


def revoke_session(db: Session, token: str) -> None:
    sess = get_valid_session(db, token)
    if sess is None:
        return
    sess.revoked = True
    db.add(sess)
    db.commit()