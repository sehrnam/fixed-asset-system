"""
Excel I/O for the workbook engine.

Export: internal Workbook/Sheet/Cell -> XLSX bytes.
Import: XLSX bytes -> internal model, returned as a **new user sheet**.
        Imported data is NEVER written directly into authoritative accounting
        records (Doc 03 §7). The client must explicitly create the sheet.

No macros. No formula execution on import — formulas are stored as raw text and
evaluated by our own parser on next render.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable

from openpyxl import Workbook as XlWorkbook, load_workbook
from openpyxl.cell.cell import Cell as XlCell
from openpyxl.utils import get_column_letter


MAX_IMPORT_ROWS = 500
MAX_IMPORT_COLS = 100
MAX_CELL_LEN = 4096


class XlsxImportError(Exception):
    """Raised for any problem parsing an uploaded workbook."""


def _col_letter(col: int) -> str:
    return get_column_letter(col)


def export_sheet(
    *,
    sheet_name: str,
    rows: int,
    cols: int,
    cells: Iterable[dict],
) -> bytes:
    """Export a single sheet as .xlsx bytes.

    `cells` is an iterable of dicts with keys: row, col, raw, computed.
    """
    wb = XlWorkbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Sheet"

    for c in cells:
        r = int(c["row"])
        col = int(c["col"])
        raw = c.get("raw") or ""
        # Store the raw text (including any leading '='). Excel will treat a
        # leading '=' as a formula; that's fine because we only export our own
        # vetted data. Imported data is stored separately and never executed.
        ws.cell(row=r, column=col, value=raw)

    # Column widths — nice-to-have, cheap.
    for col in range(1, cols + 1):
        ws.column_dimensions[_col_letter(col)].width = 14

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_report(
    *,
    title: str,
    columns: list[str],
    rows: list[list[str]],
    totals: dict | None = None,
) -> bytes:
    """Export a table report as .xlsx bytes."""
    wb = XlWorkbook()
    ws = wb.active
    ws.title = (title[:31] or "Report")

    # Title row
    ws.cell(row=1, column=1, value=title).font = ws.cell(row=1, column=1).font.copy(bold=True)

    # Header row at row 3
    for j, col_name in enumerate(columns, start=1):
        cell = ws.cell(row=3, column=j, value=col_name)
        cell.font = cell.font.copy(bold=True)

    # Body
    r = 4
    for row in rows:
        for j, value in enumerate(row, start=1):
            ws.cell(row=r, column=j, value=value)
        r += 1

    # Totals row
    if totals:
        r += 1
        for k, v in totals.items():
            ws.cell(row=r, column=1, value=k)
            ws.cell(row=r, column=2, value=v)
            r += 1

    for col in range(1, len(columns) + 1):
        ws.column_dimensions[_col_letter(col)].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def parse_xlsx(data: bytes) -> dict:
    """Parse an uploaded XLSX file into a normalized internal structure.

    Returns:
        {
            "sheets": [
                {"name": str, "cells": [{"row", "col", "raw"}, ...]},
                ...
            ]
        }

    Raises XlsxImportError for structural problems, oversized files, or
    unsupported content. Does NOT execute formulas.
    """
    try:
        wb = load_workbook(io.BytesIO(data), data_only=False, read_only=True)
    except Exception as e:
        raise XlsxImportError(f"Cannot read XLSX file: {e}")

    result_sheets = []
    try:
        for ws in wb.worksheets:
            cells = []
            for row in ws.iter_rows(
                min_row=1,
                max_row=min(ws.max_row or 1, MAX_IMPORT_ROWS),
                min_col=1,
                max_col=min(ws.max_column or 1, MAX_IMPORT_COLS),
            ):
                for xl_cell in row:
                    if xl_cell.value is None or xl_cell.value == "":
                        continue
                    raw = _cell_to_raw(xl_cell)
                    if raw is None:
                        continue
                    cells.append({
                        "row": xl_cell.row,
                        "col": xl_cell.column,
                        "raw": raw[:MAX_CELL_LEN],
                    })

            result_sheets.append({"name": (ws.title or "Sheet")[:64], "cells": cells})
    finally:
        wb.close()

    if not result_sheets:
        raise XlsxImportError("Workbook contains no sheets")

    return {"sheets": result_sheets}


def _cell_to_raw(xl_cell: XlCell) -> str | None:
    v = xl_cell.value
    if v is None:
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, datetime):
        return v.date().isoformat()
    # Strings, formulas (stored as "=..." by openpyxl when data_only=False)
    return str(v)