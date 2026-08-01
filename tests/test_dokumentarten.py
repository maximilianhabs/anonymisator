"""Regressionslauf über die Dokumentarten, die im Alltag vorkommen.

Jede Art bringt ihre eigene Bauform mit: der Laborbericht schreibt Namen als
"Nachname, Vorname" und mischt sie unter Messwerte, das Gutachten führt viele
Beteiligte, der Mehrspalter setzt zwei Blöcke nebeneinander. Was in einer Art
funktioniert, muss in den anderen nicht funktionieren.

Alle Angaben sind frei erfunden.
"""
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, extract, stufen

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def treffer(text: str) -> list[str]:
    return [f.text for g in detect.analysiere(text) for f in g.funde]


def erwarte(text: str, muss: list[str], darf_nicht: list[str], was: str) -> None:
    gefunden = treffer(text)
    fehlend = [w for w in muss if not any(w in t for t in gefunden)]
    falsch = [w for w in darf_nicht if any(w in t for t in gefunden)]
    pruefe(not fehlend, f"{was}: alles Schützenswerte gefunden"
           + (f" — FEHLT: {fehlend}" if fehlend else ""))
    pruefe(not falsch, f"{was}: keine Fachbegriffe markiert"
           + (f" — FEHLALARM: {falsch}" if falsch else ""))


print("\n=== Laborbericht ===")
# "Nachname, Vorname" ist in Laborsystemen die Regel, weil dort nach
# Nachnamen sortiert wird. Ohne eigene Regel fände das Sprachmodell nur den
# Vornamen — der Nachname bliebe im Dokument stehen.
LABOR = """Laborzentrum Passau MVZ GmbH
Nibelungenstraße 12, 94032 Passau

Befundbericht

Patient:      Hartmann, Elisabeth
Geb.-Datum:   22.07.1958
Auftrags-Nr.: L-2026-0033891
Einsender:    Dr. med. I. Brandner, Bahnhofstraße 3, 94032 Passau
Eingang:      14.03.2026

Parameter              Ergebnis    Einheit    Referenz
Natrium                    139     mmol/l     135-145
Kalium                     4,2     mmol/l     3,5-5,1
Kreatinin                  0,9     mg/dl      0,5-1,0
CRP                        3,1     mg/l       < 5,0
TSH basal                 1,84     mU/l       0,27-4,20
Vitamin B12                412     pg/ml      197-771
HbA1c                      5,4     %          < 5,7
Anti-MAG-AK           negativ                 negativ

Beurteilung: Alle Parameter im Referenzbereich.

Freigabe: Dr. rer. nat. M. Kolbeck, Fachärztin für Laboratoriumsmedizin"""

erwarte(LABOR,
        muss=["Hartmann", "Elisabeth", "22.07.1958", "L-2026-0033891",
              "Brandner", "Bahnhofstraße 3", "94032 Passau", "Kolbeck",
              "Laborzentrum"],
        darf_nicht=["Natrium", "Kalium", "Kreatinin", "CRP", "TSH", "HbA1c",
                    "Anti-MAG", "mmol/l", "Referenz", "Beurteilung",
                    "Parameter", "Einheit", "Ergebnis"],
        was="Laborbericht")

print("\n=== Nummernbezeichnungen in allen Schreibweisen ===")
# "Fallnummer", "Fall-Nr.", "Fall Nr." — alle drei kommen vor, und die
# Bindestrichform ist in Klinikbefunden die häufigste.
for schreibweise in ["Fallnummer: 2026-KA-88213", "Fall-Nr.: 2026-KA-88213",
                     "Fall Nr. 2026-KA-88213", "Auftrags-Nr.: 2026-KA-88213",
                     "Patienten-Nr.: 2026-KA-88213", "Aufnahme-Nr: 2026-KA-88213"]:
    gefunden = treffer(schreibweise)
    pruefe(any("2026-KA-88213" in t for t in gefunden),
           f"{schreibweise.split(':')[0].split(' 2026')[0]!r} erkannt")

print("\n=== Worst Case: viele Beteiligte, viele Orte ===")
VIELE = """Verlegungsbericht

Patientin Frau Elisabeth Hartmann wurde von Herrn Dr. Ostermeier aus
Deggendorf zugewiesen. Die Voruntersuchung erfolgte durch Frau Dr. Sailer
im Klinikum Landshut. Mitbehandelnd waren Herr Prof. Dr. Weißbach und Frau
Dr. Kolbeck. Der Ehemann, Herr Gerhard Hartmann, war anwesend. Die
Betreuerin, Frau Miriam Brandner, wurde informiert. Die Weiterbehandlung
übernimmt Herr Dr. Grubmüller in Regensburg. Rehabilitation ist in Bad
Kötzting vorgesehen, Nachsorge im MVZ Passau."""

gefunden = treffer(VIELE)
for name in ["Hartmann", "Ostermeier", "Sailer", "Weißbach", "Kolbeck",
             "Brandner", "Grubmüller"]:
    pruefe(any(name in t for t in gefunden), f"Worst Case: {name} erkannt")

personen = [g for g in detect.analysiere(VIELE)
            if g.typ in ("PATIENT", "ARZT", "PERSON")]
pruefe(len(personen) >= 7,
       f"Worst Case: {len(personen)} Personen erkannt, keine gekappt")

print("\n=== Worst Case: OCR-typische Lesefehler ===")
# Tesseract verwechselt regelmässig l/I/1 und O/0 und verliert Umlaute.
OCR = """Sehr geehrte Frau Kollegin Brandner,
wir berichten uber unsere Patientin Frau Elisabeth Hartrnann,
geb. 22.07.l958, wohnhaft Rosenweg l2, 94469 Deggendorf.
Die Behandlung erfolgte vom 03.03.2026 bis 12.03.2026."""

gefunden = treffer(OCR)
pruefe(any("Brandner" in t for t in gefunden), "OCR: Name trotz Lesefehler erkannt")
pruefe(any("Hartrnann" in t for t in gefunden),
       "OCR: verstümmelter Nachname (rn statt m) erkannt")
pruefe(any("Deggendorf" in t for t in gefunden), "OCR: Ort erkannt")
pruefe(any("03.03.2026" in t for t in gefunden), "OCR: unversehrtes Datum erkannt")

print("\n=== Mehrspaltiges Dokument ===")


def zweispalter() -> bytes:
    schrift = fitz.open()
    blatt = schrift.new_page(width=595, height=842)
    hoehe = 70
    for zeile in ["Neurologische Klinik am Auwald", "", "Frau",
                  "Dr. med. Ingrid Brandner", "Bahnhofstraße 3", "94032 Passau"]:
        if zeile:
            blatt.insert_text((70, hoehe), zeile, fontname="helv", fontsize=10)
        hoehe += 14.5
    hoehe = 70
    for zeile in ["Ansprechpartner:", "Prof. Dr. Weißbach",
                  "Durchwahl: 0851 4409-233", "", "Passau, 14.03.2026"]:
        if zeile:
            blatt.insert_text((360, hoehe), zeile, fontname="helv", fontsize=9)
        hoehe += 13
    hoehe = 190
    for zeile in ["Sehr geehrte Frau Kollegin Brandner,", "",
                  "wir berichten über unsere gemeinsame Patientin Frau Elisabeth",
                  "Hartmann, geboren am 22.07.1958, die sich in unserer",
                  "stationären Behandlung befand."]:
        if zeile:
            blatt.insert_text((70, hoehe), zeile, fontname="helv", fontsize=10)
        hoehe += 14.5
    roh = schrift.tobytes()
    schrift.close()
    return roh


text = extract.aus_pdf(zweispalter()).text
gefunden = treffer(text)
for name in ["Brandner", "Weißbach", "Hartmann"]:
    pruefe(any(name in t for t in gefunden), f"Mehrspalter: {name} erkannt")
pruefe(any("0851 4409-233" in t.replace(" ", " ") for t in gefunden)
       or any("4409-233" in t for t in gefunden),
       "Mehrspalter: Durchwahl aus der Nebenspalte erkannt")
pruefe("Brandner\nAnsprechpartner" not in text,
       "Mehrspalter: Spalten nicht ineinander verschränkt")

print("\n=== Vollständiger Durchlauf bis zum PDF ===")
gruppen = detect.analysiere(LABOR)
stufen.formen_berechnen(gruppen)
matrix = stufen.STUFEN["streng"]
ersetzungen = [
    {"start": f.start, "ende": f.end, "label": g.label}
    for g in gruppen for f in g.funde
    if matrix.get(g.typ, "ersetzen") != "behalten"
]
anonym = export.ersetze(LABOR, ersetzungen)
pdf = export.als_pdf(anonym)
with fitz.open(stream=pdf, filetype="pdf") as doc:
    textlayer = "\n".join(s.get_text() for s in doc)

for name in ["Hartmann", "Elisabeth", "Brandner", "Kolbeck", "L-2026-0033891"]:
    pruefe(name not in textlayer, f"Laborbefund als PDF: {name!r} entfernt")
# Die Messwerte müssen erhalten bleiben, sonst ist der Befund wertlos.
for wert in ["Natrium", "139", "Kalium", "CRP", "HbA1c"]:
    pruefe(wert in textlayer, f"Laborbefund als PDF: {wert!r} erhalten")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
