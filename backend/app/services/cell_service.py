from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.audit.writer import write_audit
from app.models.asset import Asset
from app.models.cell import Cell
from app.models.depreciation_record import DepreciationRecord
from app.models.sheet import Sheet, SheetKind, SystemView
from app.models.user import User
from app.schemas.cell import (
    CellRead,
    CellWrite,
    SheetRenderGrid,
    SheetRenderResponse,
    SheetRenderTable,
)
from app.workbook.formula import FormulaError, evaluate, parse_formula


GRID_ROWS = 50
GRID_COLS = 26  # A..Z


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _col_letter(col: int) -> str:
    letters = ""
    while col > 0:
        col, rem = divmod(col - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _cell_key(row: int, col: int) -> tuple[int, int]:
    return (row, col)


def _load_cells(db: Session, sheet_id: int) -> dict[tuple[int, int], Cell]:
    rows = db.exec(select(Cell).where(Cell.sheet_id == sheet_id)).all()
    return {_cell_key(r.row, r.col): r for r in rows}


def _compute_all(db: Session, sheet: Sheet) -> dict[tuple[int, int], Cell]:
    """Load all cells for a sheet and recompute formula cells.

    Handles dependency chains with cycle detection. Non-formula cells are
    returned with computed = raw.
    """
    cells = _load_cells(db, sheet.id)

    # Normalize computed for literal cells.
    for (r, c), cell in cells.items():
        if not cell.is_formula:
            cell.computed = cell.raw
            cell.error = None

    # Pre-parse formulas
    parsed: dict[tuple[int, int], object] = {}
    for key, cell in cells.items():
        if cell.is_formula:
            try:
                parsed[key] = parse_formula(cell.raw.lstrip("="))
            except FormulaError as e:
                cell.error = str(e)
                cell.computed = None

    # Evaluate with memoization + cycle detection
    resolved: dict[tuple[int, int], float | str] = {}
    in_progress: set[tuple[int, int]] = set()

    def resolve(row: int, col: int) -> float:
        key = (row, col)
        if key in resolved:
            v = resolved[key]
            return float(v) if isinstance(v, (int, float)) else _to_float(v)

        if key in in_progress:
            raise FormulaError("Circular reference detected")

        cell = cells.get(key)
        if cell is None:
            return 0.0

        if not cell.is_formula:
            return _to_float(cell.raw)

        node = parsed.get(key)
        if node is None:
            raise FormulaError(cell.error or "Invalid formula")

        in_progress.add(key)
        try:
            value = evaluate(node, resolve)
        finally:
            in_progress.discard(key)

        resolved[key] = value
        cell.computed = _format_number(value)
        cell.error = None
        return value

    for key, cell in cells.items():
        if cell.is_formula:
            try:
                resolve(key[0], key[1])
            except FormulaError as e:
                cell.error = str(e)
                cell.computed = None

    return cells


def _to_float(value) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        raise FormulaError(f"Non-numeric value cannot be used in a formula: {value!r}")


def _format_number(value: float) -> str:
    # Preserve integers without decimal noise; otherwise keep up to 6 dp
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


# ---------- rendering ----------

def render_sheet(db: Session, sheet: Sheet) -> SheetRenderResponse:
    if sheet.kind == SheetKind.SYSTEM:
        return _render_system(db, sheet)

    cells = _compute_all(db, sheet)
    # Persist computed values so later reads are fast
    for c in cells.values():
        db.add(c)
    db.commit()

    reads = [
        CellRead(
            row=c.row,
            col=c.col,
            raw=c.raw,
            computed=c.computed,
            is_formula=c.is_formula,
            error=c.error,
        )
        for c in cells.values()
    ]

    return SheetRenderResponse(
        sheet_id=sheet.id,
        sheet_name=sheet.name,
        sheet_kind=sheet.kind,
        grid=SheetRenderGrid(rows=GRID_ROWS, cols=GRID_COLS, cells=reads),
        table=None,
    )


def _render_system(db: Session, sheet: Sheet) -> SheetRenderResponse:
    if sheet.system_view == SystemView.ASSET_REGISTER:
        assets = db.exec(select(Asset).order_by(Asset.asset_code)).all()
        columns = [
            "Code", "Name", "Category ID", "Cost",
            "Acquired", "Life (y)", "Method", "Residual", "Rate", "Status",
        ]
        rows = []
        for a in assets:
            rows.append([
                a.asset_code,
                a.name,
                str(a.category_id),
                f"{a.cost:.2f}",
                a.acquisition_date.date().isoformat(),
                str(a.useful_life_years),
                a.depreciation_method,
                f"{a.residual_value:.2f}",
                "" if a.rate is None else f"{a.rate:.2f}",
                a.status,
            ])
        return SheetRenderResponse(
            sheet_id=sheet.id,
            sheet_name=sheet.name,
            sheet_kind=sheet.kind,
            table=SheetRenderTable(
                title="Asset Register (system view)",
                columns=columns,
                rows=rows,
            ),
        )

    if sheet.system_view == SystemView.DEPRECIATION:
        records = db.exec(
            select(DepreciationRecord).order_by(
                DepreciationRecord.period_label, DepreciationRecord.asset_id
            )
        ).all()
        columns = [
            "Period", "Asset ID", "Method", "Months",
            "Opening NBV", "Depreciation", "Accumulated", "Closing NBV",
        ]
        rows = [
            [
                r.period_label,
                str(r.asset_id),
                r.method,
                str(r.months_charged_this_period),
                f"{r.opening_nbv:.2f}",
                f"{r.depreciation:.2f}",
                f"{r.accumulated_depreciation:.2f}",
                f"{r.closing_nbv:.2f}",
            ]
            for r in records
        ]
        return SheetRenderResponse(
            sheet_id=sheet.id,
            sheet_name=sheet.name,
            sheet_kind=sheet.kind,
            table=SheetRenderTable(
                title="Depreciation Schedule (system view)",
                columns=columns,
                rows=rows,
            ),
        )

    if sheet.system_view == SystemView.DISPOSAL:
        return SheetRenderResponse(
            sheet_id=sheet.id,
            sheet_name=sheet.name,
            sheet_kind=sheet.kind,
            table=SheetRenderTable(
                title="Disposals (system view)",
                columns=["Asset ID", "Disposal Date", "Proceeds", "Gain/Loss", "Status"],
                rows=[],  # M5 populates this
            ),
        )

    raise HTTPException(status_code=500, detail="Unknown system view")


# ---------- writes ----------

def write_cells(
    db: Session,
    sheet_id: int,
    writes: list[CellWrite],
    actor: User,
) -> SheetRenderResponse:
    sheet = db.get(Sheet, sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Sheet not found")
    if sheet.kind == SheetKind.SYSTEM:
        raise HTTPException(status_code=400, detail="System sheets are read-only")

    for w in writes:
        existing = db.exec(
            select(Cell)
            .where(Cell.sheet_id == sheet.id)
            .where(Cell.row == w.row)
            .where(Cell.col == w.col)
        ).first()

        raw = w.raw or ""
        is_formula = raw.startswith("=")

        if existing is None:
            cell = Cell(
                sheet_id=sheet.id,
                row=w.row,
                col=w.col,
                raw=raw,
                computed=raw if not is_formula else None,
                is_formula=is_formula,
            )
            db.add(cell)
        else:
            existing.raw = raw
            existing.is_formula = is_formula
            existing.computed = None if is_formula else raw
            existing.error = None
            existing.updated_at = _now()
            db.add(existing)

    sheet.is_dirty = False
    sheet.updated_at = _now()
    db.add(sheet)

    write_audit(
        db,
        action="CELLS_WRITTEN",
        actor_id=actor.id,
        actor_username=actor.username,
        target_type="Sheet",
        target_id=str(sheet.id),
        metadata_json=f'{{"count": {len(writes)}}}',
    )
    db.commit()

    # Re-render with recomputed formulas
    return render_sheet(db, sheet)