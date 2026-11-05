"""PDF institucional gerado exclusivamente de texto escapado e snapshot da versão."""

from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_fonts = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Acervo", str(_fonts / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("AcervoBold", str(_fonts / "VeraBd.ttf")))


def render_publication_pdf(*, title, abstract, content, snapshot, version):
    buffer = BytesIO()
    normal = ParagraphStyle("body", fontName="Acervo", fontSize=11, leading=16, spaceAfter=8)
    heading = ParagraphStyle("heading", parent=normal, fontName="AcervoBold", fontSize=15)

    def paragraph(text, style=normal):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)

    story = [
        paragraph("Plataforma Extensionista — Acervo", heading),
        paragraph(f"Documento versão {version}"),
        paragraph(title, heading),
    ]
    for label, value in [
        ("Projeto", snapshot["project_name"]),
        ("Ano", snapshot["year"]),
        ("Orientador(es)", ", ".join(snapshot["advisors"])),
    ]:
        story.append(paragraph(f"{label}: {value}"))
    story.append(paragraph("Integrantes", heading))
    for member in snapshot["members"]:
        story.append(paragraph(f"{member['name']} — {member['course']}"))
    story.extend(
        [
            Spacer(1, 0.4 * cm),
            paragraph("Resumo", heading),
            paragraph(abstract),
            paragraph("Descrição do projeto", heading),
        ]
    )
    # Paragraphs split over pages; no HTML/images/URLs from the user are interpreted.
    story.extend(paragraph(text) for text in content.split("\n\n") if text.strip())

    def footer(canvas, document):
        canvas.setFont("Acervo", 8)
        canvas.drawRightString(A4[0] - 2 * cm, cm, f"Versão {version} · Página {document.page}")

    SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        author="Plataforma Extensionista",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
