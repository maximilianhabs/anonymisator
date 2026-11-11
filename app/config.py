"""Laufzeiteinstellungen, ausschliesslich aus Umgebungsvariablen.

Keine Pfade und keine Grenzwerte stehen im Quelltext. Was der Container
braucht, kommt aus der Umgebung; die Standardwerte sind so gewählt, dass die
Anwendung auch ohne gesetzte Variablen sinnvoll startet.
"""

from __future__ import annotations

import os
from pathlib import Path


def _zahl(name: str, standard: int) -> int:
    roh = os.environ.get(name, "").strip()
    try:
        return int(roh) if roh else standard
    except ValueError:
        return standard


def _schalter(name: str, standard: bool = False) -> bool:
    roh = os.environ.get(name, "").strip().lower()
    if not roh:
        return standard
    return roh in ("1", "true", "yes", "on", "ja")


# Verzeichnis der statischen Oberfläche. Über die Umgebung überschreibbar,
# damit das Image die Dateien an einen anderen Ort legen kann.
STATIC_DIR = Path(
    os.environ.get("ANON_STATIC_DIR")
    or Path(__file__).resolve().parent.parent / "static"
)

# Obergrenze für Uploads. Grosse Scans erzeugen beim Rastern erheblichen
# Speicherbedarf; der Wert begrenzt zugleich die Angriffsfläche.
MAX_UPLOAD_MB = _zahl("ANON_MAX_UPLOAD_MB", 60)

# Seitenzahl, ab der OCR abgelehnt wird. Ohne Grenze kann ein einzelnes
# Dokument den Container über Minuten blockieren.
MAX_OCR_SEITEN = _zahl("ANON_MAX_OCR_SEITEN", 50)

# Seitenzahl, ab der ein Dokument insgesamt abgelehnt wird — auch mit
# Textlayer. Gemessen: 500 Seiten belegen rund 2,8 GB Arbeitsspeicher.
# Zusammen mit dem Sprachmodell je Arbeitsprozess sprengt das die übliche
# Speichergrenze; der Behälter würde abgeräumt statt eine Meldung zu geben.
MAX_SEITEN = _zahl("ANON_MAX_SEITEN", 300)

# Auflösung beim Rastern gescannter Seiten.
OCR_DPI = _zahl("ANON_OCR_DPI", 300)

# Tesseract-Sprachpaket. Mehrere mit "+" verketten, etwa "deu+eng".
OCR_SPRACHE = os.environ.get("ANON_OCR_SPRACHE", "deu").strip() or "deu"

# spaCy-Modell. Muss im Image vorhanden sein — es wird zur Laufzeit nicht
# nachgeladen, der Container hat keinen Netzzugang.
SPACY_MODELL = os.environ.get("ANON_SPACY_MODELL", "de_core_news_lg").strip()

# Protokolltiefe. Inhalte verarbeiteter Dokumente werden auf keiner Stufe
# protokolliert.
LOG_LEVEL = os.environ.get("ANON_LOG_LEVEL", "INFO").strip().upper()

# JSON-Zeilen statt Klartext — für Log-Sammler wie Loki oder journald.
LOG_JSON = _schalter("ANON_LOG_JSON", True)

# Modell beim Start laden statt beim ersten Aufruf. Der Healthcheck meldet
# den Dienst damit erst als bereit, wenn er tatsächlich antworten kann.
MODELL_VORLADEN = _schalter("ANON_MODELL_VORLADEN", True)

# --------------------------------------------------------------------------
# Ordner-Modus (opt-in, app/ordner.py)
# --------------------------------------------------------------------------
# Der Server liest nichts davon. Eingang und Ausgang haben bewusst keinen
# Standardpfad im Quelltext: ein vorgegebener Ordner würde dazu einladen, ihn
# anzulegen, ohne über Synchronisierung oder Ablageort nachzudenken. Leer
# heisst "nicht gesetzt"; die Kommandozeile überschreibt die Umgebung.
ORDNER_EINGANG = os.environ.get("ANON_EINGANG", "").strip()
ORDNER_AUSGANG = os.environ.get("ANON_AUSGANG", "").strip()

# Stufe für unbeaufsichtigte Läufe. Streng als Standard, weil ohne Review
# nichts Übersehenes durch das Auge des Nutzers aufgefangen wird.
ORDNER_STUFE = os.environ.get("ANON_ORDNER_STUFE", "streng").strip().lower() or "streng"

# Abstand der Abfragen im Dauerbetrieb. Zugleich der Mindestabstand, über den
# eine Datei unverändert bleiben muss, bevor sie gelesen wird.
ORDNER_ABFRAGE_SEKUNDEN = _zahl("ANON_ORDNER_ABFRAGE_SEKUNDEN", 5)

# Unter dieser Textlänge gilt ein Dokument als nicht gelesen. Ein Arztbrief ist
# länger; ein kürzerer Text ist meist ein leerer Scan oder ein Lesefehler.
ORDNER_MIN_ZEICHEN = _zahl("ANON_ORDNER_MIN_ZEICHEN", 200)
