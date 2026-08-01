#!/usr/bin/env python3
"""Misst Laufzeit und Speicherbedarf über wachsende Dokumentgrössen.

Gesucht wird nicht ein Bestwert, sondern die Form der Kurve: Wächst die
Laufzeit linear mit der Seitenzahl oder überproportional? Bleibt der
Speicher nach der Verarbeitung stehen?

    .venv/bin/python tools/leistungsmessung.py [--gross]

Ohne Schalter bis 100 Seiten, mit --gross bis 500.
"""

from __future__ import annotations

import gc
import io
import resource
import sys
import time
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, extract, stufen

ABSATZ = (
    "Wir berichten über unsere gemeinsame Patientin Frau Elisabeth Hartmann, "
    "geboren am 22.07.1958, wohnhaft Rosenweg 12 in 94469 Deggendorf, "
    "Versichertennummer M123456789. Die Patientin befand sich vom 03.03.2026 "
    "bis zum 12.03.2026 in unserer stationären Behandlung. Die Aufnahme "
    "erfolgte über die Notaufnahme nach einem erstmaligen generalisierten "
    "tonisch-klonischen Anfall. Laborchemisch ergaben sich unauffällige Werte "
    "für Vitamin B12, Folsäure und TSH. Der Babinski-Reflex war negativ, das "
    "Lasegue-Zeichen beidseits unauffällig. Rückfragen an Prof. Dr. med. "
    "Konrad Weißbach, Telefon 0851 4409-233."
)


def speicher_mb() -> float:
    """Höchststand des belegten Speichers seit Prozessstart."""
    roh = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS meldet Bytes, Linux Kilobytes.
    return roh / (1024 * 1024) if sys.platform == "darwin" else roh / 1024


def pdf_bauen(seiten: int) -> bytes:
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=25 * mm,
                            rightMargin=20 * mm, topMargin=20 * mm)
    stil = ParagraphStyle("K", fontName="Helvetica", fontSize=10.5, leading=15)
    fluss = []
    for _ in range(seiten):
        fluss.extend(Paragraph(ABSATZ, stil) for _ in range(4))
    doc.build(fluss)
    return puffer.getvalue()


def durchlauf(seiten: int) -> dict:
    daten = pdf_bauen(seiten)
    gc.collect()
    vorher = speicher_mb()

    t0 = time.perf_counter()
    auszug = extract.aus_pdf(daten)
    t_extrakt = time.perf_counter() - t0

    t0 = time.perf_counter()
    gruppen = detect.analysiere(auszug.text)
    t_erkennung = time.perf_counter() - t0

    t0 = time.perf_counter()
    stufen.formen_berechnen(gruppen)
    matrix = stufen.STUFEN["standard"]
    ersetzungen = [
        {"start": f.start, "ende": f.end, "label": g.label}
        for g in gruppen for f in g.funde
        if matrix.get(g.typ, "ersetzen") != "behalten"
    ]
    ergebnis = export.ersetze(auszug.text, ersetzungen)
    pdf = export.als_pdf(ergebnis)
    t_export = time.perf_counter() - t0

    gc.collect()
    return {
        "seiten": seiten,
        "zeichen": len(auszug.text),
        "gruppen": len(gruppen),
        "extraktion": t_extrakt,
        "erkennung": t_erkennung,
        "export": t_export,
        "gesamt": t_extrakt + t_erkennung + t_export,
        "speicher": speicher_mb(),
        "zuwachs": speicher_mb() - vorher,
        "ausgabe_kb": len(pdf) / 1024,
    }


def main() -> None:
    stufenfolge = [1, 5, 20, 50, 100]
    if "--gross" in sys.argv:
        stufenfolge += [250, 500]

    # Modell vorab laden, damit die erste Messung nicht die Ladezeit trägt.
    print("Sprachmodell wird geladen …")
    t0 = time.perf_counter()
    detect._modell()
    print(f"  bereit nach {time.perf_counter() - t0:.1f} s, "
          f"Grundlast {speicher_mb():.0f} MB\n")

    kopf = (f"{'Seiten':>7} {'Zeichen':>9} {'Treffer':>8} "
            f"{'Extrakt':>9} {'Erkennung':>10} {'Export':>8} {'Gesamt':>9} "
            f"{'RAM':>8} {'ms/Seite':>10}")
    print(kopf)
    print("─" * len(kopf))

    messungen = []
    for seiten in stufenfolge:
        m = durchlauf(seiten)
        messungen.append(m)
        print(f"{m['seiten']:7d} {m['zeichen']:9d} {m['gruppen']:8d} "
              f"{m['extraktion']:8.2f}s {m['erkennung']:9.2f}s "
              f"{m['export']:7.2f}s {m['gesamt']:8.2f}s "
              f"{m['speicher']:7.0f}M {m['gesamt'] / m['seiten'] * 1000:9.0f}")

    print("\n── Beurteilung " + "─" * 60)

    # Linearität: Verdoppelt sich die Seitenzahl, sollte sich die Laufzeit
    # ungefähr verdoppeln. Deutlich mehr deutet auf quadratisches Verhalten.
    erste, letzte = messungen[0], messungen[-1]
    faktor_seiten = letzte["seiten"] / erste["seiten"]
    faktor_zeit = letzte["gesamt"] / max(erste["gesamt"], 1e-6)
    verhaeltnis = faktor_zeit / faktor_seiten
    print(f"  {faktor_seiten:.0f}× mehr Seiten → {faktor_zeit:.1f}× mehr Zeit "
          f"(Verhältnis {verhaeltnis:.2f})")
    if verhaeltnis > 1.6:
        print("  ⚠ überproportionaler Anstieg — auf quadratisches Verhalten prüfen")
    else:
        print("  ✓ näherungsweise linear")

    ms_pro_seite = [m["gesamt"] / m["seiten"] * 1000 for m in messungen]
    print(f"  Zeit je Seite: {min(ms_pro_seite):.0f}–{max(ms_pro_seite):.0f} ms")

    # Speicherleck: nach dem Einschwingen sollte der Höchststand nicht mehr
    # mit jeder Runde weiter klettern.
    print(f"  Speicher: {erste['speicher']:.0f} MB → {letzte['speicher']:.0f} MB "
          f"bei {letzte['seiten']} Seiten")

    print("\n── Wiederholungslauf auf Speicherleck " + "─" * 37)
    vor_schleife = speicher_mb()
    for runde in range(5):
        durchlauf(20)
        print(f"  Runde {runde + 1}: {speicher_mb():7.0f} MB")
    zuwachs = speicher_mb() - vor_schleife
    print(f"  Zuwachs über fünf gleiche Läufe: {zuwachs:+.0f} MB")
    if zuwachs > 150:
        print("  ⚠ Speicher wächst weiter — auf Leck prüfen")
    else:
        print("  ✓ stabil")


if __name__ == "__main__":
    main()
