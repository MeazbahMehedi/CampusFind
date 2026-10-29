"""Administrator-only report summaries; private claim evidence is never exported."""

import csv
from io import BytesIO, StringIO
from pathlib import Path
from xml.sax.saxutils import escape

from flask import current_app, make_response


def report_export(data, format):
    headers = [
        "Report ID",
        "Title",
        "Type",
        "Category",
        "Location",
        "Publication review",
        "Lifecycle",
        "Visibility",
        "Submitted (UTC)",
        "Event date",
    ]
    rows = [
        [
            item.id,
            item.title,
            item.kind,
            item.category,
            item.location,
            item.review_status,
            item.status,
            "Hidden"
            if item.is_hidden
            else "Public"
            if item.review_status == "approved"
            else "Not public",
            item.created_at.strftime("%Y-%m-%d %H:%M"),
            item.event_date.isoformat(),
        ]
        for item in data["items"]
    ]
    if format == "csv":
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(headers)

        # Prevent user-controlled text being evaluated as spreadsheet formulas.
        def cell(value):
            text = str(value)
            return (
                "'" + text
                if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r"))
                else text
            )

        writer.writerows([[cell(value) for value in row] for row in rows])
        response = make_response("\ufeff" + stream.getvalue())
        response.mimetype = "text/csv"
    else:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        if "CampusSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont("CampusSans", str(Path(current_app.static_folder) / "fonts/DejaVuSans.ttf"))
            )
        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=30,
            rightMargin=30,
            topMargin=32,
            bottomMargin=35,
        )
        normal = ParagraphStyle(
            "body",
            fontName="CampusSans",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#263d46"),
            alignment=TA_LEFT,
        )
        heading = ParagraphStyle(
            "heading",
            parent=normal,
            fontSize=20,
            leading=27,
            spaceAfter=10,
            textColor=colors.HexColor("#087f70"),
        )
        small = ParagraphStyle("small", parent=normal, fontSize=7, leading=10)
        brand = current_app.config["PROJECT_BRAND"]["project_name"]
        story = [
            Paragraph(escape(brand) + " — Management report summary", heading),
            Paragraph(
                f"Matching reports: {data['total']} · Confirmed returns: {data['returned']} · Closed without confirmed return: {data['closed']} · Pending publication: {data['pending']}",
                normal,
            ),
            Spacer(1, 8),
            Paragraph(
                "Based on the filters selected in Analytics. Report dates are UTC. Closing a report is not confirmation of return. Private claim evidence is excluded.",
                small,
            ),
            Spacer(1, 18),
        ]
        columns = [
            "ID / type",
            "Item / category",
            "Campus location",
            "Publication / lifecycle",
            "Visibility / submitted",
        ]
        cells = [[Paragraph(escape(h), normal) for h in columns]]
        for row in rows:
            values = [
                f"#{row[0]} / {row[2]}",
                f"{row[1]}\n{row[3]}",
                row[4],
                f"{row[5]} / {row[6]}",
                f"{row[7]}\n{row[8]}",
            ]
            cells.append(
                [Paragraph(escape(str(value)).replace("\n", "<br/>"), normal) for value in values]
            )
        if not rows:
            cells.append(
                [Paragraph("No reports match the selected filters.", normal), "", "", "", ""]
            )
        table = Table(cells, colWidths=[65, 240, 150, 160, 166], repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f5f0")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f7f9fa")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#cfe4dc")),
                ]
            )
        )
        story.append(table)

        def footer(canvas, doc):
            canvas.setFont("CampusSans", 7)
            canvas.setFillColor(colors.HexColor("#718087"))
            canvas.drawString(30, 19, "Campus management · Internal report summary")
            canvas.drawRightString(811, 19, f"Page {doc.page}")

        document.build(story, onFirstPage=footer, onLaterPages=footer)
        response = make_response(buffer.getvalue())
        response.mimetype = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="campusfind-report-summary.{format}"'
    )
    response.headers["Cache-Control"] = "private, no-store"
    return response
