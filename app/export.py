"""Ersetzung anwenden und Ergebnis als TXT, DOCX oder PDF ausgeben.

Alle Exporte werden ohne Metadaten geschrieben. Ein anonymisiertes Dokument,
in dessen Autorfeld noch der Klarname steht, ist nicht anonymisiert.
"""

from __future__ import annotations

import html
import io
from datetime import datetime

from docx import Document
from docx.shared import Pt
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def ersetze(text: str, ersetzungen: list[dict]) -> str:
    """Wendet Span-Ersetzungen an. Rein mechanisch, keine eigene Logik.

    Von hinten nach vorn, damit frühere Offsets gültig bleiben.
    """
    gueltig = [e for e in ersetzungen
               if 0 <= e["start"] < e["ende"] <= len(text)]
    for eintrag in sorted(gueltig, key=lambda e: e["start"], reverse=True):
        text = text[:eintrag["start"]] + eintrag["label"] + text[eintrag["ende"]:]
    return text


def _kopfzeile() -> str:
    return (f"Anonymisiert am {datetime.now():%d.%m.%Y} "
            "— automatisch erkannt und manuell geprüft.")


def als_txt(text: str, mit_kopfzeile: bool = True) -> bytes:
    inhalt = f"{_kopfzeile()}\n{'-' * 70}\n\n{text}\n" if mit_kopfzeile else text
    return inhalt.encode("utf-8")


def als_docx(text: str, mit_kopfzeile: bool = True) -> bytes:
    dokument = Document()

    stil = dokument.styles["Normal"]
    stil.font.name = "Calibri"
    stil.font.size = Pt(11)

    if mit_kopfzeile:
        kopf = dokument.add_paragraph(_kopfzeile())
        kopf.runs[0].font.size = Pt(8)
        kopf.runs[0].font.italic = True

    for block in text.split("\n\n"):
        absatz = dokument.add_paragraph()
        for i, zeile in enumerate(block.split("\n")):
            lauf = absatz.add_run(zeile)
            if i < len(block.split("\n")) - 1:
                lauf.add_break()

    kern = dokument.core_properties
    for feld in ("author", "last_modified_by", "title", "subject",
                 "comments", "category", "keywords", "identifier"):
        try:
            setattr(kern, feld, "")
        except (AttributeError, ValueError):
            pass

    puffer = io.BytesIO()
    dokument.save(puffer)
    return puffer.getvalue()


def als_pdf(text: str, mit_kopfzeile: bool = True) -> bytes:
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(
        puffer, pagesize=A4,
        leftMargin=25 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="", author="", subject="", creator="",
    )

    koerper = ParagraphStyle(
        "Koerper", fontName="Helvetica", fontSize=10.5, leading=15,
        alignment=TA_LEFT, spaceAfter=6,
    )
    notiz = ParagraphStyle(
        "Notiz", fontName="Helvetica-Oblique", fontSize=7.5,
        leading=11, textColor="#666666", spaceAfter=10,
    )

    fluss = []
    if mit_kopfzeile:
        fluss.append(Paragraph(html.escape(_kopfzeile()), notiz))

    for block in text.split("\n\n"):
        if not block.strip():
            fluss.append(Spacer(1, 6))
            continue
        fluss.append(Paragraph(html.escape(block).replace("\n", "<br/>"), koerper))

    doc.build(fluss)
    return puffer.getvalue()


FORMATE = {
    "txt": (als_txt, "text/plain; charset=utf-8", "txt"),
    "docx": (als_docx,
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             "docx"),
    "pdf": (als_pdf, "application/pdf", "pdf"),
}
