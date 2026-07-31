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


# Zeilenanfänge, die immer einen neuen Absatz beginnen und deshalb nie an die
# vorherige Zeile angehängt werden dürfen.
_AUFZAEHLUNG = re.compile(r"^\s*(?:[-–—•*·>]|\(?\d{1,2}[.)]|[a-z][.)])\s+")


def _volle_breite(zeilen: list[str]) -> float:
    """Typische Satzbreite des Dokuments, robust gegen einzelne Ausreisser."""
    laengen = sorted(len(z) for z in zeilen if z.strip())
    if len(laengen) < 3:
        return 0.0
    return laengen[int(len(laengen) * 0.9)] if len(laengen) > 9 else laengen[-1]


def _reflow(text: str, mindestanteil: float = 0.15) -> str:
    """Fügt weich umbrochene Zeilen wieder zu durchgehenden Absätzen zusammen.

    Nur für Quellen ohne Geometrie: OCR-Ergebnisse und eingefügten Text. Bei
    PDFs mit Textlayer übernimmt `_pdf_absaetze` diese Aufgabe anhand der
    tatsächlichen Zeilenkoordinaten und damit erheblich zuverlässiger.

    Ein PDF kennt keine Absätze, nur Zeilen. Wer diese Zeilenenden als feste
    Umbrüche übernimmt, bekommt sie beim Export erneut aufgezwungen — bei
    anderer Satzbreite entstehen daraus Flatterzeilen und einzelne Wörter auf
    eigener Zeile. Beim Anonymisieren verschärft sich das noch, weil ein
    Pseudonym selten genauso lang ist wie der ersetzte Klarname.

    Erkennungsmerkmal ist die Zeilenlänge: eine Zeile, die bis an den Rand
    reicht, wurde vom Satz umbrochen und gehört mit der nächsten zusammen.
    Eine kürzere Zeile beendet den Absatz. Anschriftenblöcke, Unterschriften
    und Aufzählungen bestehen aus kurzen Zeilen und bleiben damit von allein
    unangetastet.
    """
    zeilen = text.split("\n")
    breite = _volle_breite(zeilen)
    if breite < 45:
        return text

    schwelle = breite * 0.8
    inhalt = [z for z in zeilen if z.strip()]
    if not inhalt:
        return text

    anteil = sum(1 for z in inhalt if len(z) >= schwelle) / len(inhalt)
    if anteil < mindestanteil:
        # Sieht nicht nach hartem Umbruch aus, sondern nach Text, in dem jede
        # Zeile bereits ein eigener Absatz ist. Dann nichts anfassen.
        return text

    ergebnis: list[str] = []
    vorherige_voll = False
    for zeile in zeilen:
        gefuellt = bool(zeile.strip()) and len(zeile) >= schwelle
        if (ergebnis and vorherige_voll and zeile.strip()
                and not _AUFZAEHLUNG.match(zeile)):
            ergebnis[-1] = f"{ergebnis[-1].rstrip()} {zeile.lstrip()}"
        else:
            ergebnis.append(zeile)
        vorherige_voll = gefuellt

    return "\n".join(ergebnis)


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


def _blockzeilen(block) -> list[dict]:
    """Alle Textzeilen einer Seite mit ihrer Lage auf dem Papier.

    Aus den Spannen einer Zeile wird zusätzlich abgeleitet, ob sie tabellarisch
    gesetzt ist: liegen zwischen den Spannen grosse waagerechte Lücken, handelt
    es sich um Spalten (Medikationsplan, Laborwerte) und nicht um Fliesstext.
    """
    zeilen: list[dict] = []
    for zeile in block.get("lines", []):
        spannen = [s for s in zeile.get("spans", []) if s["text"].strip()]
        if not spannen:
            continue
        text = "".join(s["text"] for s in zeile["spans"]).rstrip()
        if not text.strip():
            continue
        x0, y0, x1, y1 = zeile["bbox"]

        hoehe = max((s["bbox"][3] - s["bbox"][1]) for s in spannen)
        luecke = max(
            (b["bbox"][0] - a["bbox"][2] for a, b in zip(spannen, spannen[1:])),
            default=0.0,
        )
        zeilen.append({
            "text": text, "x0": x0, "x1": x1, "y0": y0, "y1": y1,
            "hoehe": hoehe, "spaltig": luecke > hoehe * 1.5,
        })
    zeilen.sort(key=lambda z: (round(z["y0"], 1), z["x0"]))
    return zeilen


def _mittlere_zeichenbreite(zeilen: list[dict]) -> float:
    breite = sum(z["x1"] - z["x0"] for z in zeilen)
    zeichen = sum(len(z["text"].strip()) for z in zeilen)
    return breite / zeichen if zeichen else 5.0


def _hauptspalte(zeilen: list[dict], zeichenbreite: float) -> float:
    """Linke Kante der Spalte, in der der eigentliche Brieftext steht."""
    raster = max(zeichenbreite, 1.0)
    linke = [round(z["x0"] / raster) for z in zeilen]
    return max(set(linke), key=linke.count) * raster


def _rechter_rand(zeilen: list[dict], zeichenbreite: float,
                  haupt_x0: float) -> float:
    """Rechte Kante der Hauptspalte.

    Entscheidend ist, welche Zeilen man dafür heranzieht. Eine breite Fusszeile
    mit Bankverbindung oder eine Tabelle reicht weiter nach rechts als der
    Fliesstext. Nimmt man sie mit, liegt der geschätzte Rand zu weit rechts —
    dann sieht jede Textzeile so aus, als wäre sie freiwillig zu Ende gegangen,
    und es wird überhaupt nichts mehr zusammengefügt.

    Deshalb zählen nur Zeilen, die am linken Hauptrand beginnen und nicht
    tabellarisch gesetzt sind.
    """
    kandidaten = [
        z["x1"] for z in zeilen
        if not z["spaltig"] and abs(z["x0"] - haupt_x0) <= zeichenbreite * 2
    ]
    if not kandidaten:
        kandidaten = [z["x1"] for z in zeilen]

    kanten = sorted(kandidaten)
    return kanten[int(len(kanten) * 0.95)] if len(kanten) > 8 else kanten[-1]


def _pdf_absaetze(doc) -> str:
    """Baut aus den Zeilen einer Seite wieder Absätze.

    Ein PDF speichert keine Absätze, sondern Zeichen an Koordinaten. Die
    Absatzgrenze steckt allein im senkrechten Abstand, der weiche Zeilenumbruch
    allein in der Zeilenlänge — beides geht verloren, wenn man nur den Text
    ausliest.

    Der entscheidende Test ist, ob das erste Wort der Folgezeile am Ende der
    aktuellen Zeile noch gepasst hätte. Passte es nicht, wurde hier umbrochen
    und beide Zeilen gehören zusammen. Passte es, endete der Absatz. Dieser
    Test kommt ohne Zeichenzählen aus und funktioniert deshalb auch in Briefen,
    die überwiegend aus kurzen Zeilen bestehen — Medikationsplan, Laborwerte,
    Diagnosenliste.
    """
    absaetze: list[str] = []

    for seite in doc:
        bloecke = [b for b in seite.get_text("dict")["blocks"]
                   if b.get("type", 0) == 0 and b.get("lines")]
        if not bloecke:
            continue
        # Lesereihenfolge: erst von oben nach unten, bei gleicher Höhe von
        # links nach rechts. Blockweise vorzugehen ist der Kern — steht neben
        # dem Anschriftenfeld ein zweiter Block mit Durchwahl und Datum, würde
        # eine seitenweite Sortierung nach Höhe beide Spalten Zeile für Zeile
        # ineinander verschränken und den Text zerreissen.
        bloecke.sort(key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))

        alle = [z for b in bloecke for z in _blockzeilen(b)]
        if not alle:
            continue

        zeichenbreite = _mittlere_zeichenbreite(alle)
        haupt_x0 = _hauptspalte(alle, zeichenbreite)
        rand = _rechter_rand(alle, zeichenbreite, haupt_x0)

        abstaende = sorted(
            b["y0"] - a["y0"] for a, b in zip(alle, alle[1:])
            if 0 < b["y0"] - a["y0"] < 200
        )
        schritt = abstaende[len(abstaende) // 2] if abstaende else 14.0

        for block in bloecke:
            zeilen = _blockzeilen(block)
            if not zeilen:
                continue

            laufend = zeilen[0]["text"].strip()
            vorige = zeilen[0]

            for zeile in zeilen[1:]:
                text = zeile["text"].strip()
                abstand = zeile["y0"] - vorige["y0"]
                erstes_wort = text.split(" ", 1)[0]

                # Der Satzrand gilt nur für die Hauptspalte. Ein Nebenblock —
                # Ansprechpartner und Durchwahl neben dem Anschriftenfeld,
                # eine Fusszeile — steht ausserhalb und reicht oft weiter nach
                # rechts. Dort jede Zeile am fremden Rand zu messen, hiesse sie
                # ausnahmslos für umbrochen zu halten und zusammenzuziehen.
                in_hauptspalte = (
                    abs(vorige["x0"] - haupt_x0) <= zeichenbreite * 4
                    and abs(zeile["x0"] - haupt_x0) <= zeichenbreite * 4
                )

                # Passte das erste Wort der Folgezeile hier noch aufs Papier?
                platz_frei = rand - vorige["x1"]
                passte_noch = platz_frei >= (len(erstes_wort) + 1) * zeichenbreite

                neuer_absatz = abstand > schritt * 1.45
                einzug_wechsel = abs(zeile["x0"] - vorige["x0"]) > zeichenbreite * 2.5

                if neuer_absatz:
                    absaetze.append(laufend)
                    laufend = text
                elif (not in_hauptspalte or passte_noch
                        or vorige["spaltig"] or zeile["spaltig"]
                        or einzug_wechsel or _AUFZAEHLUNG.match(zeile["text"])):
                    # Umbruch war gewollt: Anschrift, Liste, Tabelle, Unterschrift
                    laufend += "\n" + text
                else:
                    laufend += " " + text

                vorige = zeile

            absaetze.append(laufend)

    return "\n\n".join(a for a in absaetze if a.strip())


def aus_pdf(daten: bytes) -> Extraktion:
    hinweise: list[str] = []
    with fitz.open(stream=daten, filetype="pdf") as doc:
        seiten = doc.page_count
        text = _pdf_absaetze(doc)

        zeichen_pro_seite = len(text.strip()) / max(seiten, 1)
        if zeichen_pro_seite >= MIN_ZEICHEN_PRO_SEITE:
            meta_treffer = _pdf_metadaten_pruefen(doc)
            if meta_treffer:
                hinweise.append(
                    "PDF-Metadaten enthalten Angaben (" + ", ".join(meta_treffer)
                    + "). Sie werden beim Export nicht übernommen."
                )
            # Kein _reflow: die Absätze stehen bereits, sie wurden aus der
            # Seitengeometrie gewonnen statt aus Zeichenlängen geraten.
            return Extraktion(_normalisiere(text),
                              "pdf-textlayer", seiten, hinweise)

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
        return Extraktion(_reflow(_normalisiere("\n\n".join(ocr_teile))),
                          "pdf-ocr", seiten, hinweise)


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
    # Eingefügter Text stammt oft aus einem PDF-Betrachter und trägt dessen
    # harte Zeilenumbrüche mit. _reflow greift nur, wenn der Text tatsächlich
    # so aussieht, und lässt sauber gesetzten Text unangetastet.
    return Extraktion(_reflow(_normalisiere(text)), "paste")
