from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import period_service

router = APIRouter(prefix="/api/periods", tags=["periods"])


@router.get("")
def list_periods(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return [
        {"id": p.id, "label": p.label, "start_date": p.start_date, "end_date": p.end_date, "status": p.status}
        for p in period_service.list_periods(db)
    ]


@router.post("/{label}/lock")
def lock_period(
    label: str,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.APPROVE_JOURNAL)),
):
    p = period_service.lock_period(db, label, user)
    return {"label": p.label, "status": p.status}


@router.post("/{label}/unlock")
def unlock_period(
    label: str,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.APPROVE_JOURNAL)),
):
    p = period_service.unlock_period(db, label, user)
    return {"label": p.label, "status": p.status}