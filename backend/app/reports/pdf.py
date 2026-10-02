"""
PDF report generation using ReportLab.

Controlled server-side generation. Inputs are authoritative stored data,
never arbitrary client-supplied totals.
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
    story.append(Paragraph(f"{sub} · Generated {generated}", styles["ReportSub"]))
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