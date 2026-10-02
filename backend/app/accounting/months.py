from datetime import date, datetime

from app.models.asset import Asset
from app.models.period import AccountingPeriod


def _to_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def chargeable_months(asset: Asset, period: AccountingPeriod) -> int:
    """Count depreciation months in `period` for `asset`.

    Frozen demo policy (Doc 09 #2):
      - Depreciation commences on the acquisition date.
      - The acquisition month counts as one full month.
      - No day-level proration.
    """
    acquisition = _to_date(asset.acquisition_date)
    period_start = _to_date(period.start_date)
    period_end = _to_date(period.end_date)

    if period_end < acquisition:
        return 0

    # Acquisition month = full month → effective start is the 1st of that month.
    commencement_month_start = date(acquisition.year, acquisition.month, 1)

    effective_start = max(period_start, commencement_month_start)
    effective_end = period_end

    if effective_start > effective_end:
        return 0

    months = (
        (effective_end.year - effective_start.year) * 12
        + (effective_end.month - effective_start.month)
        + 1
    )
    return max(months, 0)