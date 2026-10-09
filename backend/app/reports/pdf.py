"""
PDF report generation using ReportLab.

Controlled server-side generation. Inputs are authoritative stored data,
never arbitrary client-supplied totals.

v3.0 adds render_monthly_schedule_pdf() — the bank-style three-section
schedule with dynamic category columns.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# Shared style helpers
# ============================================================

def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportSub",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=10,
    ))
    return styles


# ============================================================
# Generic table report
# ============================================================

def render_table_report_pdf(
    *,
    title: str,
    subtitle: str | None,
    columns: list[str],
    rows: list[list[str]],
    totals: dict | None = None,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
    )

    styles = _styles()
    story = [Paragraph(title, styles["ReportTitle"])]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sub = subtitle or ""
    story.append(Paragraph(f"{sub} - Generated {generated}", styles["ReportSub"]))
    story.append(Spacer(1, 4))

    table_data = [columns] + rows
    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    if totals:
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Totals</b>", styles["Normal"]))
        totals_rows = [[k.replace("_", " ").title(), f"{v:,.2f}"] for k, v in totals.items()]
        t2 = Table(totals_rows, colWidths=[80 * mm, 40 * mm])
        t2.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(t2)

    doc.build(story)
    return buf.getvalue()


# ============================================================
# Bank-style monthly schedule
# ============================================================

def render_monthly_schedule_pdf(
    *,
    title: str,
    headers: list[str],
    sections: list[tuple[str, list[list[str]]]],
    bold_rows: set[tuple[int, int]] | None = None,
    section_divider_rows: set[tuple[int, int]] | None = None,
) -> bytes:
    """Render the bank-style monthly schedule.

    Args:
        title:  e.g. "FIXED ASSETS AS AT 31ST AUGUST 2026"
        headers: the header row (e.g. ["DATE", "PARTICULARS", "Computers", ..., "TOTAL"])
        sections: list of (section_label_or_empty, rows)
            Each row is a list of already-formatted strings (right-align handled
            by column position). Use "" for blank cells and "-" for zero cells.
        bold_rows: optional set of (row_idx_in_flat_table, col_idx) to bold
        section_divider_rows: optional set of (row_idx_in_flat_table, 0) that
            should draw a thicker top border

    Column alignment: column 0 and 1 are left-aligned (DATE, PARTICULARS).
    All other columns are right-aligned (numbers, rate, total).
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=title,
    )

    styles = _styles()
    story = [Paragraph(title, styles["ReportTitle"])]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated {generated}", styles["ReportSub"]))
    story.append(Spacer(1, 3))

    # Flatten sections into one data grid
    flat_rows: list[list[str]] = [headers]
    flat_row_indices: dict[int, tuple[int, str]] = {}  # flat_idx -> (section_idx, section_label)

    for s_idx, (label, rows) in enumerate(sections):
        for r in rows:
            # If a section label is provided and this is the first row of the
            # section, we prepend it into the first cell.
            row_copy = list(r)
            if label and not row_copy[0]:
                row_copy[0] = label
            flat_rows.append(row_copy)
            flat_row_indices[len(flat_rows) - 1] = (s_idx, label)

    # Column widths: 25mm for DATE, 40mm for PARTICULARS, then equal shares
    n_cols = len(headers)
    date_w = 18 * mm
    part_w = 42 * mm
    remaining = 277 * mm - date_w - part_w  # A4 landscape usable width minus margins
    per_cat = remaining / max(n_cols - 2, 1)
    col_widths = [date_w, part_w] + [per_cat] * (n_cols - 2)

    t = Table(flat_rows, colWidths=col_widths, repeatRows=1)

    style = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("FONTSIZE", (0, 1), (-1, -1), 6.5),
        # Alignment: first two columns left, rest right
        ("ALIGN", (0, 0), (1, -1), "LEFT"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#94a3b8")),
        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]

    # Bold specific rows (e.g. Total, Balance B/F, NET BOOK VALUE, VALUE)
    if bold_rows:
        for (r_idx, c_idx) in bold_rows:
            style.append(("FONTNAME", (c_idx, r_idx), (c_idx, r_idx), "Helvetica-Bold"))

    # Thicker top border for section dividers
    if section_divider_rows:
        for (r_idx, _) in section_divider_rows:
            style.append((
                "LINEABOVE",
                (0, r_idx), (-1, r_idx),
                0.8, colors.HexColor("#1e293b"),
            ))

    t.setStyle(TableStyle(style))
    story.append(t)

    doc.build(story)
    return buf.getvalue()