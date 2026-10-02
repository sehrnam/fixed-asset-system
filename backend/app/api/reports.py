from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.reports import AssetMovementReport, TableReport
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/asset-register", response_model=TableReport)
def asset_register(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return report_service.asset_register(db)


@router.get("/depreciation-schedule", response_model=TableReport)
def depreciation_schedule(
    period_label: str | None = None,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return report_service.depreciation_schedule(db, period_label)


@router.get("/asset-movement", response_model=AssetMovementReport)
def asset_movement(
    period_label: str,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return report_service.asset_movement(db, period_label)


@router.get("/disposal-register", response_model=TableReport)
def disposal_register(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return report_service.disposal_register(db)