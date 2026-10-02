from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session

from app.models.audit import AuditEvent


def write_audit(
    db: Session,
    *,
    action: str,
    result: str = "SUCCESS",
    actor_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    metadata_json: Optional[str] = None,
    source_context: Optional[str] = None,
) -> AuditEvent:
    ev = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        actor_id=actor_id,
        actor_username=actor_username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        metadata_json=metadata_json,
        source_context=source_context,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev