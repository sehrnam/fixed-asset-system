from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.journal import JournalRead, PrepareJournalRequest
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import journal_service

router = APIRouter(prefix="/api/journals", tags=["journals"])


@router.get("", response_model=list[JournalRead])
def list_journals(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return journal_service.list_journals(db)


@router.post("/depreciation", response_model=JournalRead, status_code=201)
def prepare_depreciation_journal(
    payload: PrepareJournalRequest,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.PREPARE_JOURNAL)),
):
    return journal_service.prepare_depreciation_journal(db, payload, user)


@router.get("/{journal_id}", response_model=JournalRead)
def get_journal(
    journal_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return journal_service.get_journal(db, journal_id)


@router.post("/{journal_id}/approve", response_model=JournalRead)
def approve_journal(
    journal_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.APPROVE_JOURNAL)),
):
    return journal_service.approve_journal(db, journal_id, user)