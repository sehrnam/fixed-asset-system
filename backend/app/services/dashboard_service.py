from sqlmodel import Session, select

from app.accounting.rounding import round_money
from app.models.asset import Asset, AssetStatus
from app.models.category import AssetCategory
from app.models.depreciation_record import DepreciationRecord
from app.schemas.dashboard import CategorySummary, DashboardRead


def _current_period_label() -> str:
    from datetime import datetime, timezone
    return str(datetime.now(timezone.utc).year)


def dashboard(db: Session) -> DashboardRead:
    label = _current_period_label()
    assets = db.exec(select(Asset)).all()

    total_cost = 0.0
    total_accum = 0.0

    by_cat: dict[int, CategorySummary] = {}

    for a in assets:
        latest = db.exec(
            select(DepreciationRecord)
            .where(DepreciationRecord.asset_id == a.id)
            .order_by(DepreciationRecord.period_label.desc())
        ).first()

        accum = latest.accumulated_depreciation if latest else 0.0
        nbv = latest.closing_nbv if latest else a.cost

        total_cost += a.cost
        total_accum += accum

        cs = by_cat.get(a.category_id)
        if cs is None:
            cat = db.get(AssetCategory, a.category_id)
            cs = CategorySummary(
                category_id=a.category_id,
                category_name=cat.name if cat else "",
                asset_count=0,
                total_cost=0.0,
                total_nbv=0.0,
            )
            by_cat[a.category_id] = cs
        cs.asset_count += 1
        cs.total_cost += a.cost
        cs.total_nbv += nbv

    period_dep = db.exec(
        select(DepreciationRecord).where(DepreciationRecord.period_label == label)
    ).all()
    current_period_dep = round_money(sum(r.depreciation for r in period_dep))

    return DashboardRead(
        total_asset_cost=round_money(total_cost),
        total_accumulated_depreciation=round_money(total_accum),
        total_nbv=round_money(total_cost - total_accum),
        current_period_label=label,
        current_period_depreciation=current_period_dep,
        category_summary=[
            CategorySummary(
                category_id=c.category_id,
                category_name=c.category_name,
                asset_count=c.asset_count,
                total_cost=round_money(c.total_cost),
                total_nbv=round_money(c.total_nbv),
            )
            for c in sorted(by_cat.values(), key=lambda x: x.category_name)
        ],
    )