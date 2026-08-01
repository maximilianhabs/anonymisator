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
