from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.audit.writer import write_audit
from app.models.cell import Cell
from app.models.sheet import Sheet, SheetKind
from app.models.user import User
from app.services.workbook_service import normalize_sheet_name


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_sheet(db: Session, sheet_id: int) -> Sheet:
    sheet = db.get(Sheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return sheet


def _check_name_unique(db: Session, workbook_id: int, normalized: str, exclude_id: int | None = None):
    q = select(Sheet).where(Sheet.workbook_id == workbook_id).where(Sheet.name_normalized == normalized)
    if exclude_id is not None:
        q = q.where(Sheet.id != exclude_id)
    if db.exec(q).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sheet with that name already exists in this workbook",
        )


def _next_order_index(db: Session, workbook_id: int) -> int:
    rows = db.exec(select(Sheet).where(Sheet.workbook_id == workbook_id)).all()
    return (max((r.order_index for r in rows), default=-1)) + 1


def create_user_sheet(db: Session, workbook_id: int, name: str, actor: User) -> Sheet:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Sheet name is required")
    normalized = normalize_sheet_name(name)
    _check_name_unique(db, workbook_id, normalized)

    sheet = Sheet(
        workbook_id=workbook_id,
        name=name,
        name_normalized=normalized,
        order_index=_next_order_index(db, workbook_id),
        kind=SheetKind.USER,
    )
    db.add(sheet)
    db.flush()
    write_audit(
        db,
        action="SHEET_CREATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Sheet",
        target_id=str(sheet.id),
    )
    db.commit()
    db.refresh(sheet)
    return sheet


def rename_sheet(db: Session, sheet_id: int, new_name: str, actor: User) -> Sheet:
    sheet = get_sheet(db, sheet_id)
    if sheet.kind == SheetKind.SYSTEM:
        raise HTTPException(status_code=400, detail="System sheets cannot be renamed")

    new_name = new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Sheet name is required")

    normalized = normalize_sheet_name(new_name)
    _check_name_unique(db, sheet.workbook_id, normalized, exclude_id=sheet.id)

    sheet.name = new_name
    sheet.name_normalized = normalized
    sheet.updated_at = _now()
    db.add(sheet)
    write_audit(
        db,
        action="SHEET_RENAMED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Sheet",
        target_id=str(sheet.id),
    )
    db.commit()
    db.refresh(sheet)
    return sheet


def delete_sheet(db: Session, sheet_id: int, actor: User) -> None:
    sheet = get_sheet(db, sheet_id)
    if sheet.kind == SheetKind.SYSTEM:
        raise HTTPException(status_code=400, detail="System sheets cannot be deleted")

    # Delete cells first (no cascade in SQLModel)
    cells = db.exec(select(Cell).where(Cell.sheet_id == sheet.id)).all()
    for c in cells:
        db.delete(c)

    db.delete(sheet)
    write_audit(
        db,
        action="SHEET_DELETED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Sheet",
        target_id=str(sheet_id),
    )
    db.commit()


def duplicate_sheet(db: Session, sheet_id: int, new_name: str | None, actor: User) -> Sheet:
    source = get_sheet(db, sheet_id)
    if source.kind == SheetKind.SYSTEM:
        raise HTTPException(status_code=400, detail="System sheets cannot be duplicated")

    if not new_name:
        # Generate a unique "Copy of X" / "Copy of X (2)" style name.
        base = f"{source.name} copy"
        candidate = base
        n = 2
        while db.exec(
            select(Sheet)
            .where(Sheet.workbook_id == source.workbook_id)
            .where(Sheet.name_normalized == normalize_sheet_name(candidate))
        ).first() is not None:
            candidate = f"{base} ({n})"
            n += 1
        new_name = candidate

    new_name = new_name.strip()
    normalized = normalize_sheet_name(new_name)
    _check_name_unique(db, source.workbook_id, normalized)

    copy = Sheet(
        workbook_id=source.workbook_id,
        name=new_name,
        name_normalized=normalized,
        order_index=_next_order_index(db, source.workbook_id),
        kind=SheetKind.USER,
        is_dirty=False,
    )
    db.add(copy)
    db.flush()

    # Copy cells
    cells = db.exec(select(Cell).where(Cell.sheet_id == source.id)).all()
    for c in cells:
        db.add(
            Cell(
                sheet_id=copy.id,
                row=c.row,
                col=c.col,
                raw=c.raw,
                computed=c.computed,
                is_formula=c.is_formula,
                error=c.error,
            )
        )

    write_audit(
        db,
        action="SHEET_DUPLICATED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Sheet",
        target_id=str(copy.id),
    )
    db.commit()
    db.refresh(copy)
    return copy


def reorder_sheets(db: Session, workbook_id: int, ordered_ids: list[int], actor: User) -> list[Sheet]:
    sheets = list(
        db.exec(select(Sheet).where(Sheet.workbook_id == workbook_id)).all()
    )
    by_id = {s.id: s for s in sheets}

    if set(ordered_ids) != set(by_id.keys()):
        raise HTTPException(
            status_code=400,
            detail="The provided order must include exactly the workbook's sheets",
        )

    for idx, sid in enumerate(ordered_ids):
        sheet = by_id[sid]
        sheet.order_index = idx
        db.add(sheet)

    write_audit(
        db,
        action="SHEETS_REORDERED",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Workbook",
        target_id=str(workbook_id),
    )
    db.commit()
    return list(
        db.exec(
            select(Sheet)
            .where(Sheet.workbook_id == workbook_id)
            .order_by(Sheet.order_index)
        ).all()
    )