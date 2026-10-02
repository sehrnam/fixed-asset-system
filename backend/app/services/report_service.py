from datetime import datetime

from sqlmodel import Session, select

from app.accounting.rounding import round_money
from app.models.asset import Asset
from app.models.category import AssetCategory
from app.models.depreciation_record import DepreciationRecord
from app.models.disposal import Disposal, DisposalStatus
from app.schemas.reports import (
    AssetMovementReport,
    AssetMovementRow,
    TableReport,
)
from app.services import period_service


def asset_register(db: Session) -> TableReport:
    rows: list[list[str]] = []
    total_cost = 0.0
    total_nbv = 0.0

    assets = db.exec(select(Asset).order_by(Asset.asset_code)).all()
    for a in assets:
        cat = db.get(AssetCategory, a.category_id)
        # Compute NBV from the latest record, if any.
        records = db.exec(
            select(DepreciationRecord)
            .where(DepreciationRecord.asset_id == a.id)
            .order_by(DepreciationRecord.period_label.desc())
        ).first()
        nbv = records.closing_nbv if records else a.cost
        total_cost += a.cost
        total_nbv += nbv
        rows.append([
            a.asset_code,
            a.name,
            cat.name if cat else "",
            f"{a.cost:.2f}",
            a.acquisition_date.date().isoformat(),
            str(a.useful_life_years),
            a.depreciation_method,
            f"{a.residual_value:.2f}",
            f"{nbv:.2f}",
            a.status,
        ])

    return TableReport(
        title="Asset Register",
        columns=[
            "Code", "Name", "Category", "Cost", "Acquired",
            "Life (y)", "Method", "Residual", "NBV", "Status",
        ],
        rows=rows,
        totals={
            "total_cost": round_money(total_cost),
            "total_nbv": round_money(total_nbv),
        },
    )


def depreciation_schedule(db: Session, period_label: str | None = None) -> TableReport:
    stmt = select(DepreciationRecord)
    if period_label:
        stmt = stmt.where(DepreciationRecord.period_label == period_label)
    stmt = stmt.order_by(DepreciationRecord.period_label, DepreciationRecord.asset_id)

    rows: list[list[str]] = []
    total_dep = 0.0
    for r in db.exec(stmt).all():
        asset = db.get(Asset, r.asset_id)
        total_dep += r.depreciation
        rows.append([
            r.period_label,
            asset.asset_code if asset else str(r.asset_id),
            asset.name if asset else "",
            r.method,
            str(r.months_charged_this_period),
            f"{r.opening_nbv:.2f}",
            f"{r.depreciation:.2f}",
            f"{r.accumulated_depreciation:.2f}",
            f"{r.closing_nbv:.2f}",
        ])

    return TableReport(
        title=f"Depreciation Schedule {period_label or '(all periods)'}",
        columns=[
            "Period", "Code", "Name", "Method", "Months",
            "Opening NBV", "Depreciation", "Accumulated", "Closing NBV",
        ],
        rows=rows,
        totals={"total_depreciation": round_money(total_dep)},
    )


def asset_movement(db: Session, period_label: str) -> AssetMovementReport:
    """Opening + Additions - Disposals = Closing, per category.

    Simplified MVP: cost movements only; depreciation charge is period-only.
    """
    period = period_service.get_period_by_label(db, period_label)
    year = period.end_date.year

    categories = db.exec(select(AssetCategory).order_by(AssetCategory.name)).all()
    rows: list[AssetMovementRow] = []

    totals = AssetMovementRow(
        category_id=None, category_name="TOTAL",
        opening_cost=0.0, additions=0.0, disposals=0.0, closing_cost=0.0,
        opening_accum=0.0, dep_charge=0.0, disposals_accum=0.0, closing_accum=0.0,
        closing_nbv=0.0,
    )

    for cat in categories:
        assets = db.exec(select(Asset).where(Asset.category_id == cat.id)).all()

        opening_cost = 0.0
        additions = 0.0
        disposals = 0.0
        opening_accum = 0.0
        dep_charge = 0.0
        disposals_accum = 0.0

        for a in assets:
            acquisition_year = a.acquisition_date.year
            if acquisition_year < year:
                opening_cost += a.cost
            else:
                additions += a.cost

            # Prior accumulated as of end of (year - 1)
            prior = db.exec(
                select(DepreciationRecord)
                .where(DepreciationRecord.asset_id == a.id)
                .where(DepreciationRecord.period_label < period_label)
                .order_by(DepreciationRecord.period_label.desc())
            ).first()
            if prior:
                opening_accum += prior.accumulated_depreciation

            # Period charge
            this_period = db.exec(
                select(DepreciationRecord)
                .where(DepreciationRecord.asset_id == a.id)
                .where(DepreciationRecord.period_label == period_label)
            ).first()
            if this_period:
                dep_charge += this_period.depreciation

            # Disposal in this period
            dis = db.exec(
                select(Disposal)
                .where(Disposal.asset_id == a.id)
                .where(Disposal.status == DisposalStatus.APPROVED)
                .where(Disposal.period_label_used == period_label)
            ).first()
            if dis:
                disposals += a.cost
                disposals_accum += dis.nbv_at_disposal

        closing_cost = opening_cost + additions - disposals
        closing_accum = opening_accum + dep_charge - disposals_accum
        closing_nbv = closing_cost - closing_accum

        row = AssetMovementRow(
            category_id=cat.id,
            category_name=cat.name,
            opening_cost=round_money(opening_cost),
            additions=round_money(additions),
            disposals=round_money(disposals),
            closing_cost=round_money(closing_cost),
            opening_accum=round_money(opening_accum),
            dep_charge=round_money(dep_charge),
            disposals_accum=round_money(disposals_accum),
            closing_accum=round_money(closing_accum),
            closing_nbv=round_money(closing_nbv),
        )
        rows.append(row)

        totals.opening_cost += row.opening_cost
        totals.additions += row.additions
        totals.disposals += row.disposals
        totals.closing_cost += row.closing_cost
        totals.opening_accum += row.opening_accum
        totals.dep_charge += row.dep_charge
        totals.disposals_accum += row.disposals_accum
        totals.closing_accum += row.closing_accum
        totals.closing_nbv += row.closing_nbv

    # Round totals
    for field in (
        "opening_cost", "additions", "disposals", "closing_cost",
        "opening_accum", "dep_charge", "disposals_accum",
        "closing_accum", "closing_nbv",
    ):
        setattr(totals, field, round_money(getattr(totals, field)))

    return AssetMovementReport(period_label=period_label, rows=rows, totals=totals)


def disposal_register(db: Session) -> TableReport:
    rows: list[list[str]] = []
    total_proceeds = 0.0
    total_gain = 0.0
    for d in db.exec(select(Disposal).order_by(Disposal.disposal_date)).all():
        asset = db.get(Asset, d.asset_id)
        total_proceeds += d.proceeds
        total_gain += d.gain_loss
        rows.append([
            asset.asset_code if asset else str(d.asset_id),
            asset.name if asset else "",
            d.disposal_date.date().isoformat(),
            f"{d.proceeds:.2f}",
            f"{d.nbv_at_disposal:.2f}",
            f"{d.gain_loss:.2f}",
            d.status,
        ])

    return TableReport(
        title="Disposal Register",
        columns=["Code", "Name", "Disposal Date", "Proceeds", "NBV", "Gain/Loss", "Status"],
        rows=rows,
        totals={
            "total_proceeds": round_money(total_proceeds),
            "total_gain_loss": round_money(total_gain),
        },
    )