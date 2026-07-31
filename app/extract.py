"""Textextraktion aus PDF, DOCX und Klartext.

Alles läuft lokal. Kein Aufruf verlässt den Rechner.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Unter diesem Schnitt an Zeichen pro Seite gehen wir davon aus, dass das PDF
# keinen brauchbaren Textlayer hat und gescannt wurde.
MIN_ZEICHEN_PRO_SEITE = 100

# 300 dpi ist der übliche Kompromiss: darunter leidet die OCR-Qualität bei
# kleinen Serifenschriften spürbar, darüber wird es nur noch langsamer.
OCR_DPI = 300


@dataclass
class Extraktion:
    text: str
    quelle: str  # "pdf-textlayer" | "pdf-ocr" | "docx" | "paste"
    seiten: int = 0
    hinweise: list[str] = field(default_factory=list)


def _normalisiere(text: str) -> str:
    """Vereinheitlicht Zeilenenden und Sonderzeichen.

    Muss vor der Erkennung passieren, damit alle Offsets auf denselben
    Textstand zeigen.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Weiche Trennstriche und geschützte Leerzeichen aus PDFs
    text = text.replace("­", "").replace(" ", " ")
    # Typografische Anführungszeichen und Bindestriche vereinheitlichen,
    # sonst greifen die Regex-Regeln an manchen Stellen nicht.
    for alt, neu in [("‘", "'"), ("’", "'"), ("“", '"'),
                     ("”", '"'), ("„", '"'), ("–", "-"),
                     ("—", "-"), ("−", "-")]:
        text = text.replace(alt, neu)
    # Trennung am Zeilenende zusammenziehen ("Kopf-\nschmerz" -> "Kopfschmerz")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Mehr als zwei Leerzeilen bringen nichts
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def aus_pdf(daten: bytes) -> Extraktion:
    hinweise: list[str] = []
    with fitz.open(stream=daten, filetype="pdf") as doc:
        seiten = doc.page_count
        teile = [seite.get_text("text") for seite in doc]
        text = "\n\n".join(teile)

        zeichen_pro_seite = len(text.strip()) / max(seiten, 1)
        if zeichen_pro_seite >= MIN_ZEICHEN_PRO_SEITE:
            meta_treffer = _pdf_metadaten_pruefen(doc)
            if meta_treffer:
                hinweise.append(
                    "PDF-Metadaten enthalten Angaben (" + ", ".join(meta_treffer)
                    + "). Sie werden beim Export nicht übernommen."
                )
            return Extraktion(_normalisiere(text), "pdf-textlayer", seiten, hinweise)

        # Kein oder zu wenig Textlayer -> gescanntes Dokument, OCR nötig.
        hinweise.append(
            f"Kein verwertbarer Textlayer ({zeichen_pro_seite:.0f} Zeichen/Seite). "
            f"{seiten} Seite(n) wurden per OCR gelesen — Lesefehler sind möglich, "
            "bitte den Text im Review gegenlesen."
        )
        ocr_teile = []
        for seite in doc:
            pix = seite.get_pixmap(dpi=OCR_DPI)
            bild = Image.open(io.BytesIO(pix.tobytes("png")))
            ocr_teile.append(pytesseract.image_to_string(bild, lang="deu"))
        return Extraktion(_normalisiere("\n\n".join(ocr_teile)), "pdf-ocr", seiten, hinweise)


def _pdf_metadaten_pruefen(doc) -> list[str]:
    """Meldet befüllte Metadatenfelder, die Klarnamen enthalten können."""
    treffer = []
    for feld in ("author", "title", "subject", "creator", "producer", "keywords"):
        wert = (doc.metadata or {}).get(feld) or ""
        if wert.strip() and feld in ("author", "title", "subject", "keywords"):
            treffer.append(f"{feld}: {wert.strip()[:40]}")
    return treffer


def aus_docx(daten: bytes) -> Extraktion:
    import docx  # python-docx

    dokument = docx.Document(io.BytesIO(daten))
    teile: list[str] = []

    # Kopf- und Fußzeilen zuerst: dort stehen bei Arztbriefen fast immer
    # Klinikname, Anschrift und Telefonnummern. Wer nur document.paragraphs
    # liest, übersieht genau diesen Block.
    for abschnitt in dokument.sections:
        for bereich in (abschnitt.header, abschnitt.footer):
            for absatz in bereich.paragraphs:
                if absatz.text.strip():
                    teile.append(absatz.text)

    for absatz in dokument.paragraphs:
        teile.append(absatz.text)

    for tabelle in dokument.tables:
        for zeile in tabelle.rows:
            zellen = [z.text.strip() for z in zeile.cells]
            # Verbundene Zellen liefert python-docx mehrfach zurück
            entdoppelt = [z for i, z in enumerate(zellen) if i == 0 or z != zellen[i - 1]]
            if any(entdoppelt):
                teile.append("\t".join(entdoppelt))

    hinweise = []
    kern = dokument.core_properties
    meta = [f for f in ("author", "last_modified_by", "title", "subject")
            if (getattr(kern, f, None) or "")]
    if meta:
        hinweise.append(
            "DOCX-Metadaten enthalten Angaben (" + ", ".join(meta)
            + "). Sie werden beim Export nicht übernommen."
        )

    return Extraktion(_normalisiere("\n".join(teile)), "docx", 0, hinweise)


def aus_upload(dateiname: str, daten: bytes) -> Extraktion:
    name = dateiname.lower()
    if name.endswith(".pdf"):
        return aus_pdf(daten)
    if name.endswith(".docx"):
        return aus_docx(daten)
    if name.endswith(".doc"):
        raise ValueError(
            "Das alte .doc-Format wird nicht unterstützt. "
            "Bitte in Word als .docx speichern oder den Text direkt einfügen."
        )
    if name.endswith(".txt"):
        return Extraktion(_normalisiere(daten.decode("utf-8", errors="replace")), "paste")
    raise ValueError(f"Dateityp nicht unterstützt: {dateiname}")


def aus_text(text: str) -> Extraktion:
    return Extraktion(_normalisiere(text), "paste")
