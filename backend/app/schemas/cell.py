from typing import Optional

from pydantic import BaseModel, Field


class CellRead(BaseModel):
    row: int
    col: int
    raw: str
    computed: Optional[str]
    is_formula: bool
    error: Optional[str]


class CellWrite(BaseModel):
    row: int = Field(ge=1, le=500)
    col: int = Field(ge=1, le=100)
    raw: str = Field(default="", max_length=4096)


class CellsBatchWrite(BaseModel):
    cells: list[CellWrite]


class SheetRenderGrid(BaseModel):
    kind: str = "grid"
    rows: int
    cols: int
    cells: list[CellRead]


class SheetRenderTable(BaseModel):
    kind: str = "table"
    title: str
    columns: list[str]
    rows: list[list[str]]


class SheetRenderResponse(BaseModel):
    sheet_id: int
    sheet_name: str
    sheet_kind: str
    grid: Optional[SheetRenderGrid] = None
    table: Optional[SheetRenderTable] = None