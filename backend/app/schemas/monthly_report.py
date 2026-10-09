from datetime import datetime

from pydantic import BaseModel


class MonthlyReportSummary(BaseModel):
    period_label: str
    filename: str
    size_bytes: int
    generated_at: datetime
    trigger: str


class MonthlyReportList(BaseModel):
    reports: list[MonthlyReportSummary]


class MonthlyReportGenerateResult(BaseModel):
    period_label: str
    created: bool
    size_bytes: int