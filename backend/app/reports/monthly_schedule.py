"""
Builder for the bank-style monthly schedule PDF.

Reads authoritative data, produces the section structure that pdf.py
renders. Returns bytes.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.accounting.rounding import round_money
from app.models.asset import Asset, AssetStatus
from app.models.category import AssetCategory
from app.models.depreciation_record import DepreciationRecord
from app.models.disposal import Disposal, DisposalStatus
from app.models.period import parse_period_label, period_label, previous_month
from app.reports.pdf import render_monthly_schedule_pdf


def _fmt_money(v: float) -> str:
    return f"{v:,.2f}"


def _fmt_cell(v: float) -> str:
    return "-" if abs(v) < 0.005 else _fmt_money(v)


def _rate_display(rate: Optional[float], life: int) -> str:
    """Match the sheet's convention: '25%' for rate, '10YRS' for life."""
    if rate is None or rate <= 0:
        return ""
    if life >= 10:
        return f"{life}YRS"
    return f"{rate:g}%"


def build_monthly_schedule_pdf(
    db: Session, target_period: str
) -> bytes:
    """Build the PDF for one monthly period ('YYYY-MM')."""
    try:
        y, m = parse_period_label(target_period)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid period label {target_period!r}; expected 'YYYY-MM'")

    prior_y, prior_m = previous_month(y, m)
    prior_label = period_label(prior_y, prior_m)

    categories = list(
        db.exec(select(AssetCategory).order_by(AssetCategory.id)).all()
    )

    # Column headers: DATE, PARTICULARS, <categories...>, TOTAL
    headers = ["DATE", "PARTICULARS"] + [c.name for c in categories] + ["TOTAL"]

    n_cat = len(categories)

    def blank_row() -> list[str]:
        return [""] * (2 + n_cat + 1)

    # ------- SECTION A: COST -------
    bfwd_row = blank_row()
    bfwd_row[0] = f"BFWD"

    total_row = blank_row()
    total_row[0] = "Total"

    # Track additions for row items
    additions: list[dict] = []

    for idx, cat in enumerate(categories):
        col = 2 + idx

        # Opening cost: assets acquired before the target period
        assets = db.exec(select(Asset).where(Asset.category_id == cat.id)).all()
        opening = 0.0
        for a in assets:
            acq_label = f"{a.acquisition_date.year:04d}-{a.acquisition_date.month:02d}"
            if acq_label <= prior_label:
                opening += a.cost
            elif acq_label == target_period:
                additions.append({
                    "date": a.acquisition_date,
                    "desc": a.description or a.name,
                    "cat_idx": idx,
                    "amount": a.cost,
                })

        bfwd_row[col] = _fmt_cell(opening)
        total_row[col] = _fmt_cell(opening + sum(
            add["amount"] for add in additions if add["cat_idx"] == idx
        ))

    # Totals
    bfwd_row[-1] = _fmt_cell(sum(
        float(bfwd_row[2 + i]) if bfwd_row[2 + i] != "-" else 0.0
        for i in range(n_cat)
    ))
    total_row[-1] = _fmt_cell(sum(
        float(total_row[2 + i]) if total_row[2 + i] != "-" else 0.0
        for i in range(n_cat)
    ))

    cost_rows: list[list[str]] = [bfwd_row]
    for add in sorted(additions, key=lambda x: x["date"]):
        r = blank_row()
        r[0] = add["date"].strftime("%d/%m/%y")
        r[1] = add["desc"][:40]
        r[2 + add["cat_idx"]] = _fmt_money(add["amount"])
        r[-1] = _fmt_money(add["amount"])
        cost_rows.append(r)
    cost_rows.append(total_row)

    # ------- SECTION B: DEPRECIATION -------
    bf_row = blank_row()
    bf_row[0] = "Balance B/F"

    charges_row = blank_row()
    charges_row[0] = f"Charges for"
    charges_row[1] = target_period

    rate_row = blank_row()
    rate_row[0] = "RATE"

    acc_row = blank_row()
    acc_row[0] = "NET BOOK VALUE"

    for idx, cat in enumerate(categories):
        col = 2 + idx

        assets = db.exec(select(Asset).where(Asset.category_id == cat.id)).all()

        opening_accum = 0.0
        charge = 0.0
        rate_display = ""
        life_display = 0

        for a in assets:
            # Prior accumulated
            prior_rec = db.exec(
                select(DepreciationRecord)
                .where(DepreciationRecord.asset_id == a.id)
                .where(DepreciationRecord.period_label <= prior_label)
                .order_by(DepreciationRecord.period_label.desc())
            ).first()
            if prior_rec:
                opening_accum += prior_rec.accumulated_depreciation

            # Current month charge
            curr = db.exec(
                select(DepreciationRecord)
                .where(DepreciationRecord.asset_id == a.id)
                .where(DepreciationRecord.period_label == target_period)
            ).first()
            if curr:
                charge += curr.depreciation

            if rate_display == "":
                life_display = a.useful_life_years
                rate_display = _rate_display(a.rate, a.useful_life_years)

        bf_row[col] = _fmt_cell(opening_accum)
        charges_row[col] = _fmt_cell(charge)
        rate_row[col] = rate_display
        acc_row[col] = _fmt_cell(opening_accum + charge)

    # Totals
    for row in (bf_row, charges_row, acc_row):
        row[-1] = _fmt_cell(sum(
            float(row[2 + i]) if row[2 + i] not in ("", "-") else 0.0
            for i in range(n_cat)
        ))

    dep_rows = [bf_row, charges_row, rate_row, acc_row]

    # ------- SECTION C: VALUE -------
    value_row = blank_row()
    value_row[0] = "VALUE"

    for idx in range(n_cat):
        cost_col = 2 + idx
        closing_cost = float(total_row[cost_col]) if total_row[cost_col] not in ("", "-") else 0.0
        closing_accum = float(acc_row[cost_col]) if acc_row[cost_col] not in ("", "-") else 0.0
        value_row[cost_col] = _fmt_cell(closing_cost - closing_accum)

    value_row[-1] = _fmt_cell(sum(
        float(value_row[2 + i]) if value_row[2 + i] not in ("", "-") else 0.0
        for i in range(n_cat)
    ))

    # Prepare title: "FIXED ASSETS AS AT 31ST AUGUST 2026"
    from calendar import monthrange
    day = monthrange(y, m)[1]
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    month_name = [
        "", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
    ][m]
    title = f"FIXED ASSETS AS AT {day}{suffix} {month_name} {y}"

    sections = [
        ("", cost_rows),
        ("DEPRECIATION", dep_rows),
        ("", [value_row]),
    ]

    # Row indices for bolding (row 0 is headers, so +1)
    bold_rows = set()
    cost_total_idx = 1 + len(cost_rows) - 1
    for c in range(len(headers)):
        bold_rows.add((cost_total_idx, c))
    bf_idx = cost_total_idx + 1
    for c in range(len(headers)):
        bold_rows.add((bf_idx, c))
    acc_idx = bf_idx + 3
    for c in range(len(headers)):
        bold_rows.add((acc_idx, c))
    val_idx = acc_idx + 1
    for c in range(len(headers)):
        bold_rows.add((val_idx, c))

    # Section dividers: first row of DEPRECIATION and VALUE sections
    section_dividers = {(bf_idx, 0), (val_idx, 0)}

    return render_monthly_schedule_pdf(
        title=title,
        headers=headers,
        sections=sections,
        bold_rows=bold_rows,
        section_divider_rows=section_dividers,
    )