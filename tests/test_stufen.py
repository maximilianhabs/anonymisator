"""Zeigt denselben Brief in allen drei Stufen nebeneinander.

Nach jeder Änderung an der Stufenmatrix durchlesen: die Frage ist nicht, ob
Zahlen stimmen, sondern ob das Ergebnis für seinen Zweck taugt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, stufen  # noqa: E402

BRIEF = """Neurologische Klinik am Auwald
Ludwigstraße 47, 94032 Passau
Tel.: 0851 / 4409-233

Passau, 14.03.2026

Sehr geehrte Frau Kollegin Brandner,

wir berichten über Ihre Patientin Frau Elisabeth Hartmann, geb. 22.07.1958,
wohnhaft Rosenweg 12, 94469 Deggendorf, Versichertennummer M123456789.
Die 67-jährige Patientin befand sich vom 03.03.2026 bis 12.03.2026 in
unserer stationären Behandlung. Fallnummer: 2026-KA-88213

Die Beschwerden bestehen seit 3 Jahren. Die Patientin arbeitet seit 1994
bei der Firma Grubmüller Metallbau. Das MRT zeigte eine Läsion im linken
Temporallappen.

Mit freundlichen Grüßen
Prof. Dr. med. Konrad Weißbach"""

gruppen = detect.analysiere(BRIEF)
zeitbezug = stufen.formen_berechnen(gruppen)

print(f"Datumsversatz: {zeitbezug['versatz_tage']:+d} Tage · "
      f"Bezugsdatum: {zeitbezug['bezugsdatum']}\n")

for stufe in stufen.STUFEN_REIHENFOLGE:
    info = stufen.STUFEN_INFO[stufe]
    matrix = stufen.STUFEN[stufe]

    ersetzungen = []
    zaehler = {}
    for gruppe in sorted(gruppen, key=lambda g: g.funde[0].start):
        art = matrix.get(gruppe.typ, "ersetzen")
        if art == "behalten":
            continue
        # Pseudonyme in Reihenfolge des Auftretens, wie im Browser
        kat = detect.KATEGORIEN[gruppe.typ]
        n = zaehler.get(gruppe.typ, 0)
        zaehler[gruppe.typ] = n + 1
        suffix = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[n] if kat["stil"] == "letter" else str(n + 1)
        label = f"[{kat['label']}_{suffix}]"

        for fund in gruppe.funde:
            if art == "initialen":
                ersatz = gruppe.initialen or label
            elif art == "ersetzen":
                ersatz = label
            else:
                ersatz = fund.formen.get(art, label)
            ersetzungen.append({"start": fund.start, "ende": fund.end, "label": ersatz})

    trenner = "=" * 74
    print(f"{trenner}\n  {info['titel'].upper()} — {info['untertitel']}\n"
          f"  {info['zweck']}\n{trenner}")
    print(export.ersetze(BRIEF, ersetzungen))
    print()
