"""Weist nach, dass ein hochgeladenes Dokument nichts hinterlässt.

Die Oberfläche sagt zu: gelesen, ausgewertet, sofort verworfen. Diese
Zusicherung darf nicht auf gutem Willen beruhen — sie wird hier geprüft.

Läuft gegen den gestarteten Dienst:
    .venv/bin/python -m uvicorn app.main:app --port 5302 &
    .venv/bin/python tests/test_keine_persistenz.py
"""
import io
import os
import sys
import tempfile
from pathlib import Path

import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASIS = os.environ.get("ANON_TEST_URL", "http://127.0.0.1:5302")

# Eine Kennung, die sonst nirgends vorkommt — danach lässt sich das gesamte
# Dateisystem absuchen.
MARKE = "ZWX7QKPV4NRB"

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def brief_pdf(gross: bool) -> bytes:
    """Erzeugt ein PDF; über 1 MB legt Starlette eine temporäre Datei an."""
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=25 * mm,
                            rightMargin=20 * mm, topMargin=20 * mm)
    stil = ParagraphStyle("K", fontName="Helvetica", fontSize=10.5, leading=15)
    absatz = (f"Patientin Frau Elisabeth {MARKE}, geboren am 22.07.1958, "
              "befand sich in unserer Behandlung. ")
    fluss = [Paragraph(absatz * 3, stil)]
    if gross:
        # Auf über 1 MB aufblähen, damit der Auslagerungspfad greift.
        fuellung = "Unauffälliger Verlauf ohne Besonderheiten. " * 40
        fluss.extend(Paragraph(fuellung, stil) for _ in range(700))
    doc.build(fluss)
    return puffer.getvalue()


def dateien_in(verzeichnis: str) -> set:
    pfad = Path(verzeichnis)
    if not pfad.exists():
        return set()
    return {p for p in pfad.rglob("*") if p.is_file()}


print("\n=== 1. Kleiner Upload (unter 1 MB, rein im Arbeitsspeicher) ===")
klein = brief_pdf(gross=False)
print(f"  Grösse: {len(klein) / 1024:.0f} KB")

vorher = dateien_in(tempfile.gettempdir())
antwort = requests.post(f"{BASIS}/api/analysieren/datei",
                        files={"datei": ("brief.pdf", klein, "application/pdf")},
                        timeout=180)
pruefe(antwort.status_code == 200, f"Analyse erfolgreich (HTTP {antwort.status_code})")
pruefe(MARKE in antwort.json()["text"], "Text wurde gewonnen")
nachher = dateien_in(tempfile.gettempdir())
neue = nachher - vorher
pruefe(not neue, f"Keine neue Datei in {tempfile.gettempdir()}"
       + (f" — {[p.name for p in neue][:3]}" if neue else ""))

print("\n=== 2. Grosser Upload (über 1 MB, Auslagerung greift) ===")
# Bewusst eine Textdatei statt eines PDFs: PDF komprimiert so gut, dass die
# Auslagerungsgrenze erst bei einer Seitenzahl fiele, die der Dienst zu Recht
# ablehnt. Für den geprüften Punkt — legt Starlette eine temporäre Datei an
# und verschwindet sie wieder — ist das Format ohne Belang.
zeile = f"Patientin Frau Elisabeth {MARKE}, geboren am 22.07.1958.\n"
gross = (zeile * 24000).encode("utf-8")
print(f"  Grösse: {len(gross) / 1024 / 1024:.1f} MB")
pruefe(len(gross) > 1024 * 1024,
       "Vorbedingung: über der Auslagerungsgrenze von 1 MB")

vorher = dateien_in(tempfile.gettempdir())
antwort = requests.post(f"{BASIS}/api/analysieren/datei",
                        files={"datei": ("gross.txt", gross, "text/plain")},
                        timeout=300)
pruefe(antwort.status_code == 200, f"Analyse erfolgreich (HTTP {antwort.status_code})")
nachher = dateien_in(tempfile.gettempdir())
neue = nachher - vorher
pruefe(not neue, "Auch die temporäre Datei ist wieder fort"
       + (f" — GEFUNDEN: {[p.name for p in neue][:3]}" if neue else ""))

print("\n=== 3. Kennung nirgends im Dateisystem ===")
# Sucht die Kennung in allen Orten, an denen eine Ablage entstehen könnte.
verdaechtig = []
for ort in (tempfile.gettempdir(), "/tmp", "/var/tmp",  # noqa: S108
            str(Path(__file__).resolve().parent.parent)):
    for datei in dateien_in(ort):
        if datei.suffix in (".py", ".md", ".yml", ".json", ".js", ".css"):
            continue
        try:
            if MARKE.encode() in datei.read_bytes()[:2_000_000]:
                verdaechtig.append(str(datei))
        except (OSError, PermissionError):
            continue
pruefe(not verdaechtig,
       "Kennung in keiner Datei auffindbar"
       + (f" — GEFUNDEN in {verdaechtig[:3]}" if verdaechtig else ""))

print("\n=== 4. Der Dienst erinnert sich nicht ===")
# Zweite Anfrage ohne Text: würde etwas zwischengespeichert, käme der alte
# Inhalt zurück.
leer = requests.post(f"{BASIS}/api/analysieren/text",
                     json={"text": "Ein unbeteiligter Satz ohne Namen."},
                     timeout=120)
pruefe(leer.status_code == 200, "Zweite Anfrage erfolgreich")
pruefe(MARKE not in leer.text, "Kein Rest der vorigen Anfrage in der Antwort")

print("\n=== 5. Protokoll ohne Dokumentinhalt ===")
# Der Dienst schreibt nach stdout; hier wird geprüft, dass die Kennung nicht
# in der Antwort steckt, die ein Protokollsammler abgreifen könnte.
pruefe("dateiname" not in antwort.text.lower(),
       "Antwort führt keinen Dateinamen mit")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
