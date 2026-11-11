"""Weist nach, dass ein hochgeladenes Dokument nichts hinterlässt.

Die Oberfläche sagt zu: gelesen, ausgewertet, sofort verworfen. Diese
Zusicherung darf nicht auf gutem Willen beruhen — sie wird hier geprüft.

Der Test startet den Dienst selbst als Unterprozess (freier Port auf
127.0.0.1) mit einem frisch angelegten, leeren TMPDIR und einem leeren
Arbeitsverzeichnis, lädt Testdokumente hoch und durchsucht danach genau diese
beiden Verzeichnisse und die Protokollausgabe des Dienstes nach der Kennung.
Fremde Dateien im Temp-Verzeichnis des Benutzers können so keinen Fehlalarm
auslösen. Aufruf:
    .venv/bin/python tests/test_keine_persistenz.py

Gegen einen bereits laufenden Dienst (kein eigener Unterprozess):
    ANON_TEST_URL=http://127.0.0.1:5302 \\
    ANON_TEST_TMPDIR=/pfad/zum/TMPDIR/des/Dienstes \\
    .venv/bin/python tests/test_keine_persistenz.py
Ohne ANON_TEST_TMPDIR entfallen die Dateisuche und die Protokollprüfung;
das wird ausgewiesen und gilt nicht als bestanden. Das Protokoll eines
fremd gestarteten Dienstes ist dem Test ohnehin nicht zugänglich.
"""
import io
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import fitz
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

EXTERN = os.environ.get("ANON_TEST_URL")
BASIS = EXTERN or None  # wird beim Start des Unterprozesses gesetzt

# Eine Kennung, die sonst nirgends vorkommt — danach lassen sich die vom
# Dienst beschriebenen Verzeichnisse und das Protokoll absuchen.
MARKE = "ZWX7QKPV4NRB"

fehler = []
hinweise = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def brief_pdf(gross: bool) -> bytes:
    """Erzeugt ein PDF; über 1 MB legt Starlette eine temporäre Datei an.

    Die Grösse kommt von einer eingebetteten, nicht komprimierbaren Anlage
    (Zufallsbytes), nicht von analysierbarem Text: Die Analyse bleibt kurz,
    der Auslagerungspfad wird trotzdem getroffen. Die Seite trägt kein Bild
    und mehr als 100 Zeichen Text, läuft also weder in OCR noch in die
    Seitenablehnung; die Kennung kommt aus dem Textlayer.
    """
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=25 * mm,
                            rightMargin=20 * mm, topMargin=20 * mm)
    stil = ParagraphStyle("K", fontName="Helvetica", fontSize=10.5, leading=15)
    absatz = (f"Patientin Frau Elisabeth {MARKE}, geboren am 22.07.1958, "
              "befand sich in unserer Behandlung. ")
    doc.build([Paragraph(absatz * 3, stil)])
    if not gross:
        return puffer.getvalue()
    with fitz.open(stream=puffer.getvalue(), filetype="pdf") as pdf:
        pdf.embfile_add("anlage.bin", os.urandom(1_300_000))
        return pdf.tobytes()


def dateien_in(verzeichnis) -> set:
    pfad = Path(verzeichnis)
    if not pfad.exists():
        return set()
    return {p for p in pfad.rglob("*") if p.is_file()}


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def kennung_in(verzeichnisse) -> list[str]:
    gefunden = []
    for ort in verzeichnisse:
        for datei in dateien_in(ort):
            try:
                if MARKE.encode() in datei.read_bytes():
                    gefunden.append(str(datei))
            except OSError:
                continue
    return gefunden


def starte_dienst(basis: Path):
    """Startet uvicorn mit leerem TMPDIR; liefert (Prozess, URL, Logdatei)."""
    tmp, arbeit = basis / "tmp", basis / "arbeit"
    tmp.mkdir()
    arbeit.mkdir()
    logdatei = basis / "dienst.log"
    port = freier_port()
    umgebung = dict(os.environ, TMPDIR=str(tmp), TEMP=str(tmp), TMP=str(tmp),
                    PYTHONPATH=str(WURZEL))
    python = WURZEL / ".venv" / "bin" / "python"
    # Arbeitsverzeichnis leer und fremd: auch eine Ablage per relativem Pfad
    # würde so auffallen.
    prozess = subprocess.Popen(  # noqa: S603 - feste Argumente, kein Fremdinput
        [str(python if python.exists() else sys.executable), "-m", "uvicorn",
         "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=arbeit, env=umgebung, stdin=subprocess.DEVNULL,
        stdout=logdatei.open("wb"), stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    ende = time.time() + 300  # Laden des Sprachmodells dauert bis ~60 s
    while time.time() < ende:
        if prozess.poll() is not None:
            raise RuntimeError(
                "Dienst vorzeitig beendet:\n" + logdatei.read_text(errors="replace")[-2000:])
        try:
            if requests.get(f"{url}/health", timeout=2).status_code == 200:
                return prozess, url, logdatei
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError("Dienst wurde innerhalb von 300 s nicht bereit")


def beende_dienst(prozess):
    if prozess is None or prozess.poll() is not None:
        return
    prozess.terminate()
    try:
        prozess.wait(timeout=20)
    except subprocess.TimeoutExpired:
        prozess.kill()
        prozess.wait()


def pruefungen(suchorte, logdatei_pfad, prozess):
    """suchorte: Verzeichnisse, die der Dienst beschreiben könnte (oder leer)."""
    tmp = suchorte[0] if suchorte else None

    print("\n=== 1. Kleiner Upload (unter 1 MB, rein im Arbeitsspeicher) ===")
    klein = brief_pdf(gross=False)
    print(f"  Grösse: {len(klein) / 1024:.0f} KB")
    vorher = dateien_in(tmp) if tmp else set()
    antwort = requests.post(f"{BASIS}/api/analysieren/datei",
                            files={"datei": ("brief.pdf", klein, "application/pdf")},
                            timeout=180)
    pruefe(antwort.status_code == 200, f"Analyse erfolgreich (HTTP {antwort.status_code})")
    pruefe(MARKE in antwort.json()["text"], "Text wurde gewonnen")
    if tmp:
        neue = dateien_in(tmp) - vorher
        pruefe(not neue, "Keine neue Datei im Temp-Verzeichnis des Dienstes"
               + (f" — {[p.name for p in neue][:3]}" if neue else ""))

    print("\n=== 2. Grosser Upload (über 1 MB, Auslagerung greift) ===")
    gross = brief_pdf(gross=True)
    print(f"  Grösse: {len(gross) / 1024 / 1024:.1f} MB")
    pruefe(len(gross) > 1024 * 1024,
           "Vorbedingung: über der Auslagerungsgrenze von 1 MB")
    vorher = dateien_in(tmp) if tmp else set()
    antwort = requests.post(f"{BASIS}/api/analysieren/datei",
                            files={"datei": ("gross.pdf", gross, "application/pdf")},
                            timeout=300)
    pruefe(antwort.status_code == 200, f"Analyse erfolgreich (HTTP {antwort.status_code})")
    pruefe(antwort.status_code == 200 and MARKE in antwort.json().get("text", ""),
           "Text des grossen Dokuments wurde gewonnen (kein OCR-Umweg)")
    if tmp:
        neue = dateien_in(tmp) - vorher
        pruefe(not neue, "Auch die temporäre Datei ist wieder fort"
               + (f" — GEFUNDEN: {[p.name for p in neue][:3]}" if neue else ""))
    antwort_gross = antwort

    print("\n=== 3. Kennung nirgends in den vom Dienst beschreibbaren Orten ===")
    if suchorte:
        verdaechtig = kennung_in(suchorte)
        pruefe(not verdaechtig,
               "Kennung in keiner Datei auffindbar"
               + (f" — GEFUNDEN in {verdaechtig[:3]}" if verdaechtig else ""))
    else:
        hinweise.append("Dateisuche NICHT geprüft: ANON_TEST_TMPDIR nicht gesetzt.")
        print("  --    übersprungen (ANON_TEST_TMPDIR nicht gesetzt), zählt nicht als bestanden")

    print("\n=== 4. Der Dienst erinnert sich nicht ===")
    # Zweite Anfrage ohne Text: würde etwas zwischengespeichert, käme der alte
    # Inhalt zurück.
    leer = requests.post(f"{BASIS}/api/analysieren/text",
                         json={"text": "Ein unbeteiligter Satz ohne Namen."},
                         timeout=120)
    pruefe(leer.status_code == 200, "Zweite Anfrage erfolgreich")
    pruefe(MARKE not in leer.text, "Kein Rest der vorigen Anfrage in der Antwort")

    print("\n=== 5. Protokoll ohne Dokumentinhalt ===")
    pruefe("dateiname" not in antwort_gross.text.lower()
           and "gross.pdf" not in antwort_gross.text,
           "Antwort führt keinen Dateinamen mit")
    if logdatei_pfad:
        beende_dienst(prozess)  # Ausgabe vollständig auf der Platte
        protokoll = logdatei_pfad.read_text(errors="replace")
        pruefe(len(protokoll.strip()) > 0, "Vorbedingung: Protokoll des Dienstes nicht leer")
        pruefe(MARKE not in protokoll, "Kennung steht nicht im Protokoll")
        pruefe("brief.pdf" not in protokoll and "gross.pdf" not in protokoll,
               "Protokoll führt keinen Dateinamen")
    else:
        hinweise.append("Protokoll NICHT geprüft: Dienst wurde nicht vom Test gestartet.")
        print("  --    Protokollprüfung übersprungen (fremder Dienst), zählt nicht als bestanden")


def main():
    global BASIS
    prozess = None
    basis = None
    try:
        if EXTERN:
            BASIS = EXTERN
            tmpdir = os.environ.get("ANON_TEST_TMPDIR")
            pruefungen([tmpdir] if tmpdir else [], None, None)
        else:
            basis = Path(tempfile.mkdtemp(prefix="anon-persistenz-"))
            print(f"Starte Dienst (TMPDIR={basis / 'tmp'}) ...")
            prozess, BASIS, logdatei = starte_dienst(basis)
            pruefungen([basis / "tmp", basis / "arbeit"], logdatei, prozess)
    finally:
        beende_dienst(prozess)
        if basis:
            shutil.rmtree(basis, ignore_errors=True)


main()

print("\n" + "=" * 60)
for h in hinweise:
    print("HINWEIS:", h)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle ausgeführten Prüfungen bestanden."
      + (" (Nicht alle Prüfungen wurden ausgeführt, siehe Hinweis.)" if hinweise else ""))
