from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.dashboard import DashboardRead
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def get_dashboard(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return dashboard_service.dashboard(db)