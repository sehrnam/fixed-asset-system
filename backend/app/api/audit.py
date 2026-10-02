from fastapi import APIRouter, Depends, Query
from sqlmodel import Session as DBSession, select

from app.database import get_session
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventRead
from app.security.deps import require_permission
from app.security.permissions import Permission

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    limit: int = Query(default=200, ge=1, le=1000),
    action: str | None = None,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_AUDIT)),
):
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    stmt = stmt.order_by(AuditEvent.timestamp.desc()).limit(limit)
    rows = db.exec(stmt).all()
    return [
        AuditEventRead(
            id=r.id,
            timestamp=r.timestamp,
            actor_id=r.actor_id,
            actor_username=r.actor_username,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            result=r.result,
            source_context=r.source_context,
        )
        for r in rows
    ]