from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.disposal import DisposalCreate, DisposalRead
from app.security.deps import get_current_user, require_permission
from app.security.permissions import Permission
from app.services import disposal_service

router = APIRouter(prefix="/api/disposals", tags=["disposals"])


@router.get("", response_model=list[DisposalRead])
def list_disposals(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return disposal_service.list_disposals(db, status_filter)


@router.post("", response_model=DisposalRead, status_code=201)
def create_disposal(
    payload: DisposalCreate,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.CREATE_DISPOSAL)),
):
    return disposal_service.create_disposal(db, payload, user)


@router.get("/{disposal_id}", response_model=DisposalRead)
def get_disposal(
    disposal_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return disposal_service.get_disposal(db, disposal_id)


@router.post("/{disposal_id}/approve", response_model=DisposalRead)
def approve_disposal(
    disposal_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.APPROVE_DISPOSAL)),
):
    return disposal_service.approve_disposal(db, disposal_id, user)


@router.post("/{disposal_id}/reject", response_model=DisposalRead)
def reject_disposal(
    disposal_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.APPROVE_DISPOSAL)),
):
    return disposal_service.reject_disposal(db, disposal_id, user)