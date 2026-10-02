from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.audit.writer import write_audit
from app.database import get_session
from app.models.user import User
from app.schemas.depreciation import (
    DepreciationPeriodSummary,
    DepreciationRecordRead,
    DepreciationRunRequest,
    DepreciationRunResult,
)
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import depreciation_service

router = APIRouter(prefix="/api/depreciation", tags=["depreciation"])


@router.post("/run", response_model=DepreciationRunResult)
def run_depreciation(
    payload: DepreciationRunRequest,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.CALC_DEPRECIATION)),
):
    result = depreciation_service.run_depreciation(
        db,
        through_period=payload.through_period,
        asset_ids=payload.asset_ids,
    )
    write_audit(
        db,
        action="DEPRECIATION_RUN",
        actor_id=user.id,
        actor_username=user.username,
        target_type="AccountingPeriod",
        target_id=payload.through_period,
    )
    return result


@router.get(
    "/assets/{asset_id}",
    response_model=list[DepreciationRecordRead],
)
def get_asset_schedule(
    asset_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return depreciation_service.get_schedule_for_asset(db, asset_id)


@router.get("/periods/{period_label}", response_model=DepreciationPeriodSummary)
def get_period_summary(
    period_label: str,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    return depreciation_service.get_period_summary(db, period_label)