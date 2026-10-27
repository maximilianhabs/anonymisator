"""Prüft, dass die Datumsverschiebung der Standardstufe lückenlos ist.

Ein verschobenes Datum nützt nichts, wenn daneben ein unverschobenes steht:
"vom 03.03. bis 12.03.2026" mit nur dem zweiten Datum verschoben verrät den
Versatz — der Abstand beider Angaben ist bekannt. Dieser Test setzt den
Versatz fest und prüft, dass jede Datumsangabe eines Beispieltexts
(vollständig, nur Tag+Monat, Monat+Jahr, Jahreszeit+Jahr, Jahr allein,
Jahrgang) mit demselben Versatz behandelt wird.

Alle Texte sind frei erfunden.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, stufen

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def standardtext(text: str, versatz_tage: int) -> str:
    """Wendet die Standardstufe mit festem Versatz an, wie die Oberfläche es tut."""
    stufen.secrets.choice = lambda _: 1 if versatz_tage >= 0 else -1
    stufen.secrets.randbelow = lambda _: abs(versatz_tage) - 120
    gruppen = detect.analysiere(text)
    info = stufen.formen_berechnen(gruppen)
    assert info["versatz_tage"] == versatz_tage
    ersetzungen = []
    for gruppe in gruppen:
        art = stufen.STUFEN["standard"].get(gruppe.typ, "ersetzen")
        if art == "behalten":
            continue
        for fund in gruppe.funde:
            if art == "ersetzen":
                neu = gruppe.label
            elif art == "initialen":
                neu = gruppe.initialen
            else:
                neu = fund.formen.get(art, gruppe.label)
            ersetzungen.append((fund.start, fund.end, neu))
    for start, ende, neu in sorted(ersetzungen, reverse=True):
        text = text[:start] + neu + text[ende:]
    return text


print("=== 1. Tag und Monat ohne Jahr werden mitverschoben ===")
text = "Aufenthalt vom 03.03. bis 12.03.2026 mit Entlassung am 12.03.2026."
ergebnis = standardtext(text, 200)
erwartet_von = (date(2026, 3, 3) + timedelta(days=200)).strftime("%d.%m")
erwartet_bis = (date(2026, 3, 12) + timedelta(days=200)).strftime("%d.%m.%Y")
pruefe("03.03" not in ergebnis and "12.03" not in ergebnis,
       f"Kein Rest der echten Angaben im Text ({ergebnis!r})")
pruefe(f"vom {erwartet_von}. bis {erwartet_bis}" in ergebnis,
       f"Beide Daten mit demselben Versatz, Abstand erhalten ({ergebnis!r})")

print("\n=== 2. Jahreswechsel: das Jahr kommt vom nächsten vollen Datum ===")
text = "Aufnahme am 28.12. und Entlassung am 05.01.2026."
ergebnis = standardtext(text, 100)
erwartet_auf = (date(2025, 12, 28) + timedelta(days=100)).strftime("%d.%m")
pruefe(f"am {erwartet_auf}." in ergebnis,
       f"28.12. gehört zu 2025, nicht zu 2026 ({ergebnis!r})")

print("\n=== 3. Jahr, Monat+Jahr, Jahreszeit und Jahrgang ===")
text = ("Seit 2019 bekannt, Jahrgang 1971. Im März 2024 und 03/2024 MRT, "
        "Frühjahr 2019 erste Beschwerden. Entlassung am 14.05.2024.")
ergebnis = standardtext(text, 300)
pruefe("1971" not in ergebnis, f"Jahrgang bleibt nicht stehen ({ergebnis!r})")
pruefe("März 2024" not in ergebnis and "03/2024" not in ergebnis,
       f"Monat+Jahr verschoben ({ergebnis!r})")
pruefe("Frühjahr 2019" not in ergebnis and "seit 2019" not in ergebnis.lower(),
       f"Jahreszeit und Jahr verschoben ({ergebnis!r})")
pruefe(str((date(2019, 7, 1) + timedelta(days=300)).year) in ergebnis,
       f"Jahreszahl um denselben Versatz verschoben ({ergebnis!r})")

print("\n=== 4. Gegenprobe: Gliederung und Relativangaben bleiben ===")
text = "Gliederung 3.2. Befund. Seit 3 Jahren bekannt, vor 6 Monaten Beginn."
ergebnis = standardtext(text, 200)
pruefe("3.2." in ergebnis and "Seit 3 Jahren" in ergebnis and "vor 6 Monaten" in ergebnis,
       f"Nichts davon wird als Datum verschoben ({ergebnis!r})")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
