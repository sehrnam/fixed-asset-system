from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JournalLineRead(BaseModel):
    id: int
    account_code: str
    account_name: str
    debit: float
    credit: float
    memo: Optional[str]


class JournalRead(BaseModel):
    id: int
    code: str
    period_label: str
    entry_date: datetime
    description: str
    kind: str
    status: str
    total_debit: float
    total_credit: float
    prepared_by: int
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    lines: list[JournalLineRead] = []


class PrepareJournalRequest(BaseModel):
    period_label: str