"""
Depreciation API - v3.0 (monthly).

v3.0 changes:
  - Period labels are "YYYY-MM"
  - Added list_periods() and current_period() for the frontend month picker
  - Added catchup() endpoint for admin manual trigger
  - run() now accepts a monthly target
"""
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


# ---------------------------------------------------------------------------
# Manual / admin triggers
# ---------------------------------------------------------------------------

@router.post("/run", response_model=DepreciationRunResult)
def run_depreciation(
    payload: DepreciationRunRequest,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.CALC_DEPRECIATION)),
):
    """Compute and persist depreciation for all active assets up to and
    including `through_period` (format: 'YYYY-MM').

    In normal operation this runs automatically on every app startup
    (see AUTO_BOOTSTRAP in bootstrap.py). This endpoint exists for
    admin manual triggers and testing.
    """
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


@router.post("/catchup", response_model=DepreciationRunResult)
def catchup_depreciation(
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.CALC_DEPRECIATION)),
):
    """Run depreciation from the latest existing record through the current
    calendar month. Idempotent.

    This is the same routine that runs on startup when AUTO_BOOTSTRAP=true.
    Exposed here so an admin can force a catch-up without restarting.
    """
    from datetime import datetime, timezone
    from app.models.period import period_label as make_label

    today = datetime.now(timezone.utc).date()
    through = make_label(today.year, today.month)

    result = depreciation_service.run_depreciation(
        db,
        through_period=through,
        asset_ids=None,
    )
    write_audit(
        db,
        action="DEPRECIATION_CATCHUP",
        actor_id=user.id,
        actor_username=user.username,
        target_type="AccountingPeriod",
        target_id=through,
    )
    return result


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/assets/{asset_id}",
    response_model=list[DepreciationRecordRead],
)
def get_asset_schedule(
    asset_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    """Return the full monthly schedule for one asset, sorted by period."""
    return depreciation_service.get_schedule_for_asset(db, asset_id)


@router.get("/periods", response_model=list[DepreciationPeriodSummary])
def list_periods(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    """List every period that has depreciation records, newest first.

    Used by the frontend month picker and the Monthly Reports page.
    """
    return depreciation_service.list_period_summaries(db)


@router.get("/periods/current", response_model=DepreciationPeriodSummary)
def current_period(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    """Return the current calendar month's summary (may be empty if not
    yet run)."""
    from datetime import datetime, timezone
    from app.models.period import period_label as make_label

    today = datetime.now(timezone.utc).date()
    label = make_label(today.year, today.month)
    return depreciation_service.get_period_summary(db, label)


@router.get("/periods/{period_label}", response_model=DepreciationPeriodSummary)
def get_period_summary(
    period_label: str,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    """Return the summary for one monthly period. Format: 'YYYY-MM'."""
    return depreciation_service.get_period_summary(db, period_label)