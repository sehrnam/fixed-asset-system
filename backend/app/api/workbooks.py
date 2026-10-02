from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from app.database import get_session
from app.models.user import User
from app.schemas.cell import CellsBatchWrite, SheetRenderResponse
from app.schemas.sheet import (
    DuplicateRequest,
    SheetCreate,
    SheetRead,
    SheetRename,
    SheetReorderRequest,
)
from app.schemas.workbook import WorkbookRead
from app.security.deps import get_current_user, require_permission
from app.security.permissions import Permission
from app.services import cell_service, sheet_service, workbook_service

router = APIRouter(prefix="/api", tags=["workbook"])


# ---------- workbooks ----------

@router.get("/workbooks/default", response_model=WorkbookRead)
def get_default_workbook(
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    wb = workbook_service.get_or_create_default_workbook(db, user)
    return workbook_service.workbook_to_read(db, wb)


@router.post("/workbooks/{workbook_id}/active-sheet/{sheet_id}", response_model=WorkbookRead)
def set_active_sheet(
    workbook_id: int,
    sheet_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    workbook_service.set_active_sheet(db, workbook_id, sheet_id)
    wb = workbook_service.get_workbook(db, workbook_id)
    return workbook_service.workbook_to_read(db, wb)


# ---------- sheets ----------

@router.post(
    "/workbooks/{workbook_id}/sheets",
    response_model=SheetRead,
    status_code=201,
)
def create_sheet(
    workbook_id: int,
    payload: SheetCreate,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return sheet_service.create_user_sheet(db, workbook_id, payload.name, user)


@router.patch("/sheets/{sheet_id}", response_model=SheetRead)
def rename_sheet(
    sheet_id: int,
    payload: SheetRename,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return sheet_service.rename_sheet(db, sheet_id, payload.name, user)


@router.delete("/sheets/{sheet_id}", status_code=204)
def delete_sheet(
    sheet_id: int,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    sheet_service.delete_sheet(db, sheet_id, user)


@router.post("/sheets/{sheet_id}/duplicate", response_model=SheetRead, status_code=201)
def duplicate_sheet(
    sheet_id: int,
    payload: DuplicateRequest,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return sheet_service.duplicate_sheet(db, sheet_id, payload.new_name, user)


@router.post("/workbooks/{workbook_id}/sheets/reorder")
def reorder_sheets(
    workbook_id: int,
    payload: SheetReorderRequest,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    sheets = sheet_service.reorder_sheets(db, workbook_id, payload.sheet_ids, user)
    return {"ok": True, "count": len(sheets)}


# ---------- cells ----------

@router.get("/sheets/{sheet_id}/render", response_model=SheetRenderResponse)
def render_sheet(
    sheet_id: int,
    db: DBSession = Depends(get_session),
    _: User = Depends(require_permission(Permission.VIEW_ASSETS)),
):
    sheet = sheet_service.get_sheet(db, sheet_id)
    return cell_service.render_sheet(db, sheet)


@router.patch("/sheets/{sheet_id}/cells", response_model=SheetRenderResponse)
def write_cells(
    sheet_id: int,
    payload: CellsBatchWrite,
    db: DBSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return cell_service.write_cells(db, sheet_id, payload.cells, user)