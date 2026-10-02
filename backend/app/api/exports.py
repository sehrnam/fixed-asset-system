from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlmodel import Session as DBSession

from app.audit.writer import write_audit
from app.database import get_session
from app.models.user import User
from app.reports.pdf import render_table_report_pdf
from app.security.deps import require_permission
from app.security.permissions import Permission
from app.services import cell_service, report_service, sheet_service
from app.workbook.io_xlsx import export_report, export_sheet

router = APIRouter(prefix="/api/exports", tags=["exports"])


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:64]


@router.get("/sheets/{sheet_id}/xlsx")
def export_sheet_xlsx(
    sheet_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    sheet = sheet_service.get_sheet(db, sheet_id)
    if sheet.system_view:
        raise HTTPException(status_code=400, detail="System sheets are exported via reports, not direct sheet export")

    render = cell_service.render_sheet(db, sheet)
    if render.grid is None:
        raise HTTPException(status_code=400, detail="Sheet has no grid to export")

    data = export_sheet(
        sheet_name=sheet.name,
        rows=render.grid.rows,
        cols=render.grid.cols,
        cells=[
            {"row": c.row, "col": c.col, "raw": c.raw, "computed": c.computed}
            for c in render.grid.cells
        ],
    )
    write_audit(
        db,
        action="EXPORT_SHEET_XLSX",
        actor_id=user.id,
        actor_username=user.username,
        target_type="Sheet",
        target_id=str(sheet.id),
    )
    filename = f"{_slug(sheet.name)}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _report_payload(db, kind: str, period_label: str | None):
    if kind == "asset-register":
        r = report_service.asset_register(db)
        return r.title, None, r.columns, r.rows, r.totals
    if kind == "depreciation-schedule":
        r = report_service.depreciation_schedule(db, period_label)
        return r.title, period_label, r.columns, r.rows, r.totals
    if kind == "disposal-register":
        r = report_service.disposal_register(db)
        return r.title, None, r.columns, r.rows, r.totals
    raise HTTPException(status_code=404, detail="Unknown report")


@router.get("/reports/{kind}/xlsx")
def export_report_xlsx(
    kind: str,
    period_label: str | None = None,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    title, sub, columns, rows, totals = _report_payload(db, kind, period_label)
    data = export_report(title=title, columns=columns, rows=rows, totals=totals)
    write_audit(
        db,
        action="EXPORT_REPORT_XLSX",
        actor_id=user.id,
        actor_username=user.username,
        target_type="Report",
        target_id=kind,
    )
    filename = f"{_slug(title)}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{kind}/pdf")
def export_report_pdf(
    kind: str,
    period_label: str | None = None,
    db: DBSession = Depends(get_session),
    user: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    title, sub, columns, rows, totals = _report_payload(db, kind, period_label)
    data = render_table_report_pdf(
        title=title,
        subtitle=sub,
        columns=columns,
        rows=rows,
        totals=totals,
    )
    write_audit(
        db,
        action="EXPORT_REPORT_PDF",
        actor_id=user.id,
        actor_username=user.username,
        target_type="Report",
        target_id=kind,
    )
    filename = f"{_slug(title)}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )