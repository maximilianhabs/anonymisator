"""Prüft Dokumente ausserhalb der Medizin: Rechnung und Unfallgutachten.

Der Schwerpunkt des Werkzeugs liegt auf Arztbriefen, aber Rechnungsnummern,
Kontoverbindungen, Steuernummern und Kfz-Kennzeichen sind ebenso direkte
Identifikatoren und müssen auf jeder Stufe verschwinden.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, stufen

RECHNUNG = """Grubmüller Metallbau GmbH
Industriestraße 8, 94032 Passau
USt-IdNr.: DE123456789
Steuernummer: 153/815/47110
Handelsregister: HRB 12345

Rechnung

Kundennummer: KD-2026-4711
Rechnungsnummer: RE-2026-00842
Rechnungsdatum: 14.03.2026

Sehr geehrter Herr Baumgartner,

für die Reparatur Ihres Fahrzeugs mit dem amtlichen Kennzeichen PA-XY 1234
berechnen wir Ihnen wie folgt:

Ersatzteile                     1.284,50 €
Arbeitslohn (6,5 Std.)            487,50 €
Zwischensumme                   1.772,00 €
Umsatzsteuer 19 %                 336,68 €
Gesamtbetrag                    2.108,68 €

Bitte überweisen Sie den Betrag auf folgendes Konto:
IBAN: DE89 3704 0044 0532 0130 00
BIC: COBADEFFXXX
Kontonummer: 0532013000

Mit freundlichen Grüßen
Josef Grubmüller"""

GUTACHTEN = """Sachverständigenbüro Dr. Ing. Reinhard Kellermann
Bahnhofstraße 22, 94469 Deggendorf

Amtsgericht Passau
Aktenzeichen: 3 C 412/26

Unfallgutachten

Geschädigter: Herr Thomas Baumgartner, geb. 04.11.1979
Personalausweisnummer: L01X00T47
Sozialversicherungsnummer: 12 190367 K 123
Fahrzeug: amtliches Kennzeichen PA-XY 1234
Versicherung: Allianz Versicherungs-AG, Policennummer: POL-99887766

Der Sachschaden beläuft sich auf 8.450,00 €. Die Wertminderung beträgt
1.200,00 €. Der Geschädigte war vom 15.02.2026 bis 28.02.2026
arbeitsunfähig.

Deggendorf, 05.03.2026
Dr. Ing. Reinhard Kellermann"""

# Was in keiner Stufe stehen bleiben darf.
IMMER_WEG = [
    "DE123456789", "153/815/47110", "HRB 12345", "KD-2026-4711",
    "RE-2026-00842", "DE89 3704 0044 0532 0130 00", "COBADEFFXXX",
    "0532013000", "PA-XY 1234", "L01X00T47", "12 190367 K 123",
    "3 C 412/26", "POL-99887766",
]

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def anonymisieren(text: str, stufe: str) -> str:
    gruppen = detect.analysiere(text)
    stufen.formen_berechnen(gruppen)
    matrix = stufen.STUFEN[stufe]
    ersetzungen = []
    for gruppe in gruppen:
        art = matrix.get(gruppe.typ, "ersetzen")
        if art == "behalten":
            continue
        for fund in gruppe.funde:
            if art == "initialen":
                ersatz = gruppe.initialen or gruppe.label
            elif art == "ersetzen":
                ersatz = gruppe.label
            else:
                ersatz = fund.formen.get(art, gruppe.label)
            ersetzungen.append({"start": fund.start, "ende": fund.end, "label": ersatz})
    return export.ersetze(text, ersetzungen)


for name, dokument in (("Rechnung", RECHNUNG), ("Unfallgutachten", GUTACHTEN)):
    print(f"\n=== {name} ===")
    for stufe in stufen.STUFEN_REIHENFOLGE:
        ergebnis = anonymisieren(dokument, stufe)
        uebrig = [w for w in IMMER_WEG if w in dokument and w in ergebnis]
        pruefe(not uebrig,
               f"Stufe {stufe}: keine Kennnummer übrig"
               + (f" — GEFUNDEN: {uebrig}" if uebrig else ""))

print("\n=== Geldbeträge ===")
leicht = anonymisieren(RECHNUNG, "leicht")
standard = anonymisieren(RECHNUNG, "standard")
streng = anonymisieren(RECHNUNG, "streng")

pruefe("2.108,68 €" in leicht, "Leicht: Betrag bleibt centgenau stehen")
pruefe("2.108,68 €" not in standard and "rund 2.100 €" in standard,
       "Standard: Betrag ist auf 'rund 2.100 €' gerundet")
pruefe("2.108,68" not in streng and "[BETRAG_" in streng,
       "Streng: Betrag ist vollständig ersetzt")

print("\n=== Rundung einzeln ===")
for roh, erwartet in [("1.284,50 €", "rund 1.300 €"), ("487,50 €", "rund 490 €"),
                      ("8.450,00 €", "rund 8.400 €"), ("336,68 €", "rund 340 €")]:
    wert = stufen.betrag_lesen(roh)
    ergebnis = stufen._runden(wert, "€")
    pruefe(ergebnis == erwartet, f"{roh} → {ergebnis} (erwartet {erwartet})")

print("\n=== Firmen und Behörden als Organisation ===")
gruppen = detect.analysiere(RECHNUNG)
namen = {g.anzeige for g in gruppen if g.typ == "ORGANISATION"}
pruefe(any("Grubmüller Metallbau" in n for n in namen),
       f"Firma mit Rechtsform erkannt: {sorted(namen)}")

gruppen = detect.analysiere(GUTACHTEN)
namen = {g.anzeige for g in gruppen if g.typ == "ORGANISATION"}
pruefe(any("Amtsgericht" in n for n in namen), f"Gericht erkannt: {sorted(namen)}")
pruefe(any("Versicherung" in n for n in namen), f"Versicherung erkannt: {sorted(namen)}")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
