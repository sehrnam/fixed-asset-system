from pydantic import BaseModel, Field


class SheetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class SheetRename(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class SheetReorderRequest(BaseModel):
    # Full ordered list of sheet IDs for the workbook.
    sheet_ids: list[int]


class SheetRead(BaseModel):
    id: int
    workbook_id: int
    name: str
    order_index: int
    kind: str
    system_view: str | None
    is_dirty: bool


class DuplicateRequest(BaseModel):
    new_name: str | None = Field(default=None, max_length=64)