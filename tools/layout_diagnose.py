#!/usr/bin/env python3
"""Zeigt, wie ein PDF gesetzt ist — ohne seinen Inhalt preiszugeben.

Wenn ein Brief nach dem Einlesen zerrissen aussieht, liegt das an seiner
Bauart: mehrspaltiger Kopf, ungewöhnlicher Zeilenabstand, breite Fusszeile,
Tabellen. Dieses Werkzeug gibt genau diese Kennzahlen aus und **keinen
einzigen Buchstaben** des Dokuments. Die Ausgabe lässt sich deshalb
gefahrlos weitergeben, um einem Fehler nachzugehen.

    .venv/bin/python tools/layout_diagnose.py brief.pdf

Textzeilen erscheinen als Balken, deren Länge der Zeilenbreite entspricht.
Rechts steht, wie die Zeile eingeordnet wurde:

    ┃ verbunden   weicher Umbruch, wird an die Vorzeile angehängt
    ┆ Zeile       gewollter Umbruch, bleibt eigene Zeile
    ▌ Absatz      neuer Absatz
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz  # noqa: E402

from app import extract  # noqa: E402


def diagnose(pfad: Path) -> None:
    with fitz.open(pfad) as doc:
        print(f"Datei      {pfad.name}")
        print(f"Seiten     {doc.page_count}")

        for nummer, seite in enumerate(doc, start=1):
            bloecke = [b for b in seite.get_text("dict")["blocks"]
                       if b.get("type", 0) == 0 and b.get("lines")]
            if not bloecke:
                print(f"\nSeite {nummer}: kein Text (vermutlich Scan → OCR)")
                continue

            bloecke.sort(key=lambda b: (round(b["bbox"][1], 1), b["bbox"][0]))
            alle = [z for b in bloecke for z in extract._blockzeilen(b)]
            if not alle:
                continue

            roh = sum(len(b["lines"]) for b in bloecke)

            zeichenbreite = extract._mittlere_zeichenbreite(alle)
            haupt_x0 = extract._hauptspalte(alle, zeichenbreite)
            rand = extract._rechter_rand(alle, zeichenbreite, haupt_x0)
            abstaende = sorted(
                b["y0"] - a["y0"] for a, b in zip(alle, alle[1:])
                if 0 < b["y0"] - a["y0"] < 200
            )
            schritt = abstaende[len(abstaende) // 2] if abstaende else 14.0

            linke = sorted({round(z["x0"]) for z in alle})
            spalten = _spalten(linke, zeichenbreite)

            print(f"\n{'─' * 66}")
            print(f"Seite {nummer}: {len(bloecke)} Blöcke, {len(alle)} Zeilen")
            if roh > len(alle):
                print(f"  Blocksatz       {roh} Roh-Zeilen zu {len(alle)} "
                      f"vereint (Wörter waren einzeln gesetzt)")
            print(f"  Zeichenbreite   {zeichenbreite:5.2f} pt")
            print(f"  rechter Rand    {rand:5.1f} pt")
            print(f"  Zeilenschritt   {schritt:5.1f} pt "
                  f"(Absatz ab {schritt * 1.45:.1f} pt)")
            print(f"  linke Kanten    {len(spalten)} Spalte(n) bei "
                  f"{', '.join(f'{s:.0f}' for s in spalten)} pt")
            tabellarisch = sum(1 for z in alle if z["spaltig"])
            if tabellarisch:
                print(f"  tabellarisch    {tabellarisch} Zeile(n)")

            _zeilenbild(bloecke, rand, zeichenbreite, schritt, haupt_x0)

    text = extract.aus_pdf(pfad.read_bytes()).text
    absaetze = [a for a in text.split("\n\n") if a.strip()]
    zeilen = sum(a.count("\n") + 1 for a in absaetze)
    laengen = sorted(len(a) for a in absaetze)

    print(f"\n{'═' * 66}")
    print(f"ERGEBNIS   {len(absaetze)} Absätze, {zeilen} Zeilen")
    if laengen:
        print(f"           längster Absatz {laengen[-1]} Zeichen, "
              f"Mittelwert {sum(laengen) // len(laengen)}")
    lang = sum(1 for a in absaetze if len(a) > 200 and "\n" not in a)
    print(f"           {lang} durchgehende Fliesstextabsätze (>200 Zeichen)")
    if zeilen > len(absaetze) * 3 and lang == 0:
        print("\n  ⚠ Viele Zeilen, aber kein durchgehender Fliesstext — der "
              "Brief\n    wurde vermutlich nicht richtig zusammengefügt. "
              "Bitte diese\n    Ausgabe weitergeben, sie enthält keinen "
              "Dokumentinhalt.")


def _spalten(kanten: list[int], zeichenbreite: float) -> list[float]:
    """Fasst dicht beieinanderliegende linke Kanten zu Spalten zusammen."""
    gruppen: list[list[int]] = []
    for kante in kanten:
        if gruppen and kante - gruppen[-1][-1] <= zeichenbreite * 3:
            gruppen[-1].append(kante)
        else:
            gruppen.append([kante])
    return [sum(g) / len(g) for g in gruppen]


def _zeilenbild(bloecke, rand: float, zeichenbreite: float, schritt: float,
                haupt_x0: float) -> None:
    """Stellt jede Zeile als Balken dar — Länge statt Inhalt."""
    print("\n  Zeilenbild (Balkenlänge = Zeilenbreite, kein Text):")
    gezeigt = 0
    for block in bloecke:
        zeilen = extract._blockzeilen(block)
        for i, zeile in enumerate(zeilen):
            if gezeigt >= 45:
                print("    … weitere Zeilen ausgelassen")
                return
            breite = int((zeile["x1"] - zeile["x0"]) / max(rand / 46, 1))
            balken = "█" * max(1, min(breite, 46))

            if i == 0:
                zeichen, wie = "▌", "Absatz"
            else:
                vorige = zeilen[i - 1]
                abstand = zeile["y0"] - vorige["y0"]
                wort = zeile["text"].strip().split(" ", 1)[0]
                passte = (rand - vorige["x1"]) >= (len(wort) + 1) * zeichenbreite
                if abstand > schritt * 1.45:
                    zeichen, wie = "▌", "Absatz"
                elif (passte or vorige["spaltig"] or zeile["spaltig"]
                      or abs(vorige["x0"] - haupt_x0) > zeichenbreite * 4):
                    zeichen, wie = "┆", "Zeile"
                else:
                    zeichen, wie = "┃", "verbunden"
            print(f"    {zeichen} {balken:<46} {wie}")
            gezeigt += 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    ziel = Path(sys.argv[1]).expanduser()
    if not ziel.exists():
        print(f"Nicht gefunden: {ziel}")
        sys.exit(1)
    diagnose(ziel)
