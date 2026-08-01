"""Prüft die Exportdateien auf verbliebene Spuren — Byte für Byte.

Ein anonymisiertes Dokument ist erst dann anonym, wenn auch das steckt, was
man beim Öffnen nicht sieht: Metadaten, XMP-Pakete, Kommentare, verworfene
Textstände aus der Änderungsverfolgung, versteckter Text, eingebettete
Dateien, Anmerkungen.

Deshalb wird hier nicht der sichtbare Text geprüft, sondern der Rohinhalt
der erzeugten Dateien.
"""
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import export

# Klarnamen, die in keiner erzeugten Datei mehr vorkommen dürfen — weder im
# Text noch in einem Metadatenfeld.
KLARNAMEN = ["Elisabeth", "Hartmann", "Weißbach", "Weissbach", "Brandner",
             "M123456789", "22.07.1958", "Ludwigstraße", "Deggendorf"]

ANONYM = """[ORG_1]
[ADRESSE_1], [ADRESSE_2]

Sehr geehrte Frau Kollegin [ARZT_1],

wir berichten über unsere Patientin Frau [PATIENT_A], 60–69 J., wohnhaft
[ADRESSE_3]. Versichertennummer [VERSNR_1]. Das MRT zeigte eine Läsion im
linken Temporallappen.

Mit freundlichen Grüßen
Prof. Dr. med. [ARZT_2]"""

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def ohne_klarnamen(rohdaten: bytes, was: str) -> None:
    """Sucht Klarnamen im Rohinhalt, auch in UTF-16 — Word speichert so."""
    treffer = []
    for name in KLARNAMEN:
        for kodierung in ("utf-8", "utf-16-le", "latin-1"):
            try:
                if name.encode(kodierung) in rohdaten:
                    treffer.append(f"{name} ({kodierung})")
                    break
            except UnicodeEncodeError:
                continue
    pruefe(not treffer, f"{was}{f' — GEFUNDEN: {treffer}' if treffer else ''}")


print("\n=== TXT ===")
txt = export.als_txt(ANONYM, mit_kopfzeile=True, stufe="standard")
ohne_klarnamen(txt, "Keine Kennung in der Textdatei")
pruefe(b"[PATIENT_A]" in txt, "Pseudonyme sind enthalten")

print("\n=== DOCX ===")
docx_daten = export.als_docx(ANONYM, mit_kopfzeile=True, stufe="standard")
ohne_klarnamen(docx_daten, "Keine Kennung im gesamten DOCX-Archiv")

with zipfile.ZipFile(BytesIO(docx_daten)) as archiv:
    eintraege = archiv.namelist()
    kern = archiv.read("docProps/core.xml").decode("utf-8", "replace")
    dokument = archiv.read("word/document.xml").decode("utf-8", "replace")

# Autor und Bearbeiter müssen leer sein, nicht bloss unauffällig.
for feld in ("creator", "lastModifiedBy", "title", "subject", "keywords",
             "description", "category"):
    gefuellt = re.search(rf"<(?:\w+:)?{feld}[^>]*>([^<]+)<", kern)
    pruefe(not gefuellt,
           f"core.xml: {feld} ist leer"
           + (f" — enthält {gefuellt.group(1)!r}" if gefuellt else ""))

# Kommentare, Änderungsverfolgung und versteckter Text sind eigene
# Dateien beziehungsweise eigene Auszeichnungen im Dokumentteil.
for teil in ("word/comments.xml", "word/commentsExtended.xml",
             "word/people.xml", "word/embeddings/"):
    pruefe(not any(e.startswith(teil) for e in eintraege),
           f"DOCX enthält kein {teil}")

for auszeichnung, was in [
    ("w:ins", "Einfügungen aus der Änderungsverfolgung"),
    ("w:del", "Löschungen aus der Änderungsverfolgung"),
    ("w:commentReference", "Kommentarverweise"),
    ("w:vanish", "versteckter Text"),
    ("w:hidden", "ausgeblendete Abschnitte"),
]:
    pruefe(f"<{auszeichnung}" not in dokument, f"DOCX ohne {was}")

pruefe("[PATIENT_A]" in dokument, "Pseudonyme stehen im Dokumentteil")

print("\n=== PDF ===")
pdf_daten = export.als_pdf(ANONYM, mit_kopfzeile=True, stufe="standard")
ohne_klarnamen(pdf_daten, "Keine Kennung im PDF-Rohinhalt")

with fitz.open(stream=pdf_daten, filetype="pdf") as doc:
    metadaten = doc.metadata or {}
    xmp = doc.xref_xml_metadata() if hasattr(doc, "xref_xml_metadata") else ""
    eingebettet = doc.embfile_count()
    anmerkungen = sum(1 for seite in doc for _ in seite.annots())
    textlayer = "\n".join(seite.get_text() for seite in doc)
    seitenzahl = doc.page_count

for feld in ("author", "title", "subject", "keywords"):
    wert = (metadaten.get(feld) or "").strip()
    pruefe(not wert, f"PDF-Metadaten: {feld} ist leer"
           + (f" — enthält {wert!r}" if wert else ""))

pruefe(not (xmp or "").strip(), "Kein XMP-Paket im PDF")
pruefe(eingebettet == 0, f"Keine eingebetteten Dateien ({eingebettet})")
pruefe(anmerkungen == 0, f"Keine Anmerkungen ({anmerkungen})")
pruefe(seitenzahl >= 1, f"PDF hat {seitenzahl} Seite(n)")

# Der Textlayer ist das, was ein Kopieren aus dem PDF liefert. Genau dort
# steckt bei falsch gemachter Schwärzung der Klarname weiter drin.
for name in KLARNAMEN:
    pruefe(name not in textlayer, f"Textlayer ohne {name!r}")
pruefe("[PATIENT_A]" in textlayer, "Pseudonyme stehen im Textlayer")

print("\n=== Gegenprobe: der Prüfaufbau greift überhaupt ===")
# Ohne diese Probe wäre nicht gesagt, dass die Suche funktioniert und nicht
# jede Datei blind für sauber erklärt.
verseucht = export.als_pdf("Frau Elisabeth Hartmann", mit_kopfzeile=False)
with fitz.open(stream=verseucht, filetype="pdf") as doc:
    gefunden = "Hartmann" in "\n".join(s.get_text() for s in doc)
pruefe(gefunden, "Ein Klarname im Text würde erkannt werden")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
