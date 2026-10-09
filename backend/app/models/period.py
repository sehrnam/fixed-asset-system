"""
AccountingPeriod model - v3.0 (monthly).

v3.0 change: periods are now monthly.
Label format: "YYYY-MM" (e.g. "2026-08").
start_date = first calendar day of the month
end_date   = last calendar day of the month
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccountingPeriodStatus:
    OPEN = "OPEN"
    LOCKED = "LOCKED"
    ALL = (OPEN, LOCKED)


class AccountingPeriod(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    # "YYYY-MM" e.g. "2026-08"
    label: str = Field(index=True, unique=True, max_length=16)

    start_date: datetime   # first day of month, 00:00:00
    end_date: datetime     # last day of month, 23:59:59
    status: str = Field(default=AccountingPeriodStatus.OPEN, max_length=16)

    created_at: datetime = Field(default_factory=_utc_now)


# ---------------------------------------------------------------------------
# Period label helpers (pure, no DB)
# ---------------------------------------------------------------------------

def period_label(year: int, month: int) -> str:
    """Return the canonical monthly label, e.g. period_label(2026, 8) -> '2026-08'."""
    if not (1 <= month <= 12):
        raise ValueError(f"month must be 1..12, got {month}")
    return f"{year:04d}-{month:02d}"


def parse_period_label(label: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' into (year, month). Raises ValueError on bad input."""
    parts = label.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid period label {label!r}; expected 'YYYY-MM'")
    year, month = int(parts[0]), int(parts[1])
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month in {label!r}")
    return year, month


def next_month(year: int, month: int) -> tuple[int, int]:
    """Return the (year, month) tuple for the month after the given one."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def previous_month(year: int, month: int) -> tuple[int, int]:
    """Return the (year, month) tuple for the month before the given one."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def list_months_between(
    start_year: int, start_month: int, end_year: int, end_month: int
) -> list[tuple[int, int]]:
    """Inclusive list of (year, month) tuples from start to end."""
    out: list[tuple[int, int]] = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        out.append((y, m))
        y, m = next_month(y, m)
    return out


def period_label_from_date(d: date | datetime) -> str:
    """Return the period label that contains the given date."""
    if isinstance(d, datetime):
        d = d.date()
    return period_label(d.year, d.month)