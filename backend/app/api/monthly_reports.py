"""
Monthly reports API - v3.0.

Endpoints:
  GET  /api/reports/monthly                     list available reports
  GET  /api/reports/monthly/{period}/pdf        download PDF
  GET  /api/reports/monthly/{period}/pdf?inline=1  open for print
  POST /api/admin/run-monthly                    run + generate (admin)
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session as DBSession, select

from app.audit.writer import write_audit
from app.database import get_session
from app.models.monthly_report_pdf import MonthlyReportPDF
from app.models.period import period_label, parse_period_label
from app.models.user import User
from app.reports.monthly_schedule import build_monthly_schedule_pdf
from app.schemas.monthly_report import (
    MonthlyReportGenerateResult,
    MonthlyReportList,
    MonthlyReportSummary,
)
from app.security.deps import require_permission
from app.security.permissions import Permission


router = APIRouter(tags=["monthly-reports"])


# ---------------------------------------------------------------------------
# Helper — generate + persist one PDF
# ---------------------------------------------------------------------------

def generate_and_store(db: DBSession, target_period: str, trigger: str) -> MonthlyReportPDF:
    """Build the PDF for `target_period` and persist it (overwriting any prior)."""
    try:
        y, m = parse_period_label(target_period)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period label {target_period!r}; expected 'YYYY-MM'",
        )

    pdf_bytes = build_monthly_schedule_pdf(db, target_period)
    filename = f"fixed_assets_{target_period}.pdf"

    existing = db.exec(
        select(MonthlyReportPDF).where(MonthlyReportPDF.period_label == target_period)
    ).first()

    if existing is None:
        row = MonthlyReportPDF(
            period_label=target_period,
            filename=filename,
            content=pdf_bytes,
            size_bytes=len(pdf_bytes),
            trigger=trigger,
        )
        db.add(row)
    else:
        existing.filename = filename
        existing.content = pdf_bytes
        existing.size_bytes = len(pdf_bytes)
        existing.generated_at = datetime.now(timezone.utc)
        existing.trigger = trigger
        db.add(existing)
        row = existing

    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/reports/monthly", response_model=MonthlyReportList)
def list_monthly_reports(
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    rows = list(
        db.exec(
            select(MonthlyReportPDF).order_by(MonthlyReportPDF.period_label.desc())
        ).all()
    )
    return MonthlyReportList(
        reports=[
            MonthlyReportSummary(
                period_label=r.period_label,
                filename=r.filename,
                size_bytes=r.size_bytes,
                generated_at=r.generated_at,
                trigger=r.trigger,
            )
            for r in rows
        ]
    )


@router.get("/api/reports/monthly/{target_period}/pdf")
def download_monthly_report(
    target_period: str,
    inline: bool = Query(default=False),
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    """Download (default) or open inline (inline=true) the PDF for the month.

    If the PDF hasn't been generated yet, it is generated on demand.
    """
    try:
        parse_period_label(target_period)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid period label")

    row = db.exec(
        select(MonthlyReportPDF).where(MonthlyReportPDF.period_label == target_period)
    ).first()

    if row is None:
        # Generate on demand
        row = generate_and_store(db, target_period, trigger="on_demand")

    disposition = "inline" if inline else "attachment"
    return Response(
        content=row.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{row.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/api/admin/run-monthly", response_model=MonthlyReportGenerateResult)
def admin_run_monthly(
    target_period: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.CALC_DEPRECIATION)),
):
    """Force a monthly run for `target_period` (default: current month).

    Runs depreciation, then generates the PDF. Admin-only.
    """
    if target_period is None:
        today = datetime.now(timezone.utc).date()
        target_period = period_label(today.year, today.month)

    try:
        parse_period_label(target_period)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid period label")

    # Run depreciation up to this month
    from app.services.depreciation_service import run_depreciation
    run_depreciation(db, through_period=target_period, asset_ids=None)

    # Generate + store PDF
    row = generate_and_store(db, target_period, trigger="manual")

    write_audit(
        db,
        action="MONTHLY_REPORT_GENERATED",
        actor_id=user.id,
        actor_username=user.username,
        target_type="MonthlyReport",
        target_id=target_period,
    )

    return MonthlyReportGenerateResult(
        period_label=target_period,
        created=True,
        size_bytes=row.size_bytes,
    )