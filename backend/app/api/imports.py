from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session as DBSession

from app.audit.writer import write_audit
from app.config import settings
from app.database import get_session
from app.models.sheet import Sheet, SheetKind
from app.models.user import User
from app.schemas.sheet import SheetRead
from app.security.deps import get_current_user
from app.services import sheet_service, workbook_service
from app.workbook.io_xlsx import XlsxImportError, parse_xlsx

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/xlsx-to-sheet", response_model=SheetRead, status_code=201)
async def import_xlsx_as_sheet(
    workbook_id: int = Form(...),
    sheet_name: str = Form(...),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Import an XLSX file as a NEW user sheet.

    The first sheet in the uploaded workbook becomes the target sheet's content.
    No existing sheet is modified. No authoritative accounting records change.
    """
    # MIME check
    if file.content_type and file.content_type not in settings.allowed_xlsx_mime_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Size check
    raw = await file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_bytes // 1_000_000} MB)",
        )
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        parsed = parse_xlsx(raw)
    except XlsxImportError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create the new sheet first (name uniqueness enforced by service)
    sheet = sheet_service.create_user_sheet(db, workbook_id, sheet_name, user)

    # Import only the first parsed sheet's cells
    target = parsed["sheets"][0]
    from app.schemas.cell import CellWrite
    writes = [
        CellWrite(row=c["row"], col=c["col"], raw=c["raw"])
        for c in target["cells"]
    ]

    # Only store; do not use write_cells (which audits as CELLS_WRITTEN).
    # We still want a separate audit marker for the import itself.
    if writes:
        from app.services import cell_service
        cell_service.write_cells(db, sheet.id, writes, user)

    write_audit(
        db,
        action="XLSX_IMPORTED",
        actor_id=user.id,
        actor_username=user.username,
        target_type="Sheet",
        target_id=str(sheet.id),
        metadata_json=f'{{"cells": {len(writes)}, "source_sheets": {len(parsed["sheets"])}}}',
    )

    return sheet