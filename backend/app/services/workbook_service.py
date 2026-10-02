from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.sheet import Sheet, SheetKind, SystemView
from app.models.user import User
from app.models.workbook import Workbook
from app.audit.writer import write_audit
from app.schemas.workbook import SheetSummary, WorkbookRead


DEFAULT_SYSTEM_SHEETS = [
    ("Asset Register", SystemView.ASSET_REGISTER),
    ("Depreciation", SystemView.DEPRECIATION),
    ("Disposal", SystemView.DISPOSAL),
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_sheet_name(name: str) -> str:
    return name.strip().lower()


def get_or_create_default_workbook(db: Session, actor: User) -> Workbook:
    wb = db.exec(select(Workbook).order_by(Workbook.id)).first()
    if wb is not None:
        return wb

    wb = Workbook(name="Default Workbook", owner_id=actor.id, revision=1)
    db.add(wb)
    db.flush()

    for idx, (name, view) in enumerate(DEFAULT_SYSTEM_SHEETS):
        db.add(
            Sheet(
                workbook_id=wb.id,
                name=name,
                name_normalized=normalize_sheet_name(name),
                order_index=idx,
                kind=SheetKind.SYSTEM,
                system_view=view,
            )
        )

    # Starter user sheet
    db.add(
        Sheet(
            workbook_id=wb.id,
            name="Sheet 4",
            name_normalized=normalize_sheet_name("Sheet 4"),
            order_index=len(DEFAULT_SYSTEM_SHEETS),
            kind=SheetKind.USER,
        )
    )

    db.commit()
    db.refresh(wb)

    write_audit(
        db,
        action="WORKBOOK_CREATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Workbook",
        target_id=str(wb.id),
    )
    return wb


def workbook_to_read(db: Session, wb: Workbook) -> WorkbookRead:
    sheets = list(
        db.exec(
            select(Sheet)
            .where(Sheet.workbook_id == wb.id)
            .order_by(Sheet.order_index, Sheet.id)
        ).all()
    )
    return WorkbookRead(
        id=wb.id,
        name=wb.name,
        active_sheet_id=wb.active_sheet_id,
        revision=wb.revision,
        sheets=[
            SheetSummary(
                id=s.id,
                name=s.name,
                order_index=s.order_index,
                kind=s.kind,
                system_view=s.system_view,
                is_dirty=s.is_dirty,
            )
            for s in sheets
        ],
        created_at=wb.created_at,
        updated_at=wb.updated_at,
    )


def get_workbook(db: Session, workbook_id: int) -> Workbook:
    wb = db.get(Workbook, workbook_id)
    if wb is None:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return wb


def set_active_sheet(db: Session, workbook_id: int, sheet_id: int) -> Workbook:
    wb = get_workbook(db, workbook_id)
    sheet = db.get(Sheet, sheet_id)
    if sheet is None or sheet.workbook_id != wb.id:
        raise HTTPException(status_code=400, detail="Sheet does not belong to this workbook")
    wb.active_sheet_id = sheet.id
    wb.updated_at = _now()
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return wb