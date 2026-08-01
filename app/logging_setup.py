"""Strukturierte Protokollierung nach stdout und stderr.

Wichtigste Eigenschaft: **Dokumentinhalte werden nie protokolliert.** Weder
hochgeladene Dateien noch erkannte Entitäten oder erzeugte Pseudonyme
erscheinen im Log. Festgehalten werden ausschliesslich Kennzahlen — Dauer,
Zeichenanzahl, Anzahl Treffer, Statuscode.

Diese Zurückhaltung ist keine Höflichkeit gegenüber dem Betreiber, sondern
Voraussetzung dafür, dass Logs eines De-Identifiers überhaupt aufbewahrt
werden dürfen. Ein Log, das Klarnamen enthält, hebt den Zweck der Anwendung
auf.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone

from . import config

# Felder, die der LogRecord immer mitbringt und die nicht in die
# strukturierte Ausgabe gehören.
_STANDARDFELDER = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        eintrag = {
            "zeit": datetime.fromtimestamp(
                record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "stufe": record.levelname,
            "quelle": record.name,
            "text": record.getMessage(),
        }
        for schluessel, wert in record.__dict__.items():
            if schluessel not in _STANDARDFELDER and not schluessel.startswith("_"):
                eintrag[schluessel] = wert
        if record.exc_info:
            eintrag["ausnahme"] = self.formatException(record.exc_info)
        return json.dumps(eintrag, ensure_ascii=False)


def einrichten() -> logging.Logger:
    formatierer: logging.Formatter = (
        JsonFormatter() if config.LOG_JSON
        else logging.Formatter("%(asctime)s %(levelname)-7s %(name)s  %(message)s")
    )

    ausgabe = logging.StreamHandler(sys.stdout)
    ausgabe.setFormatter(formatierer)

    wurzel = logging.getLogger()
    wurzel.handlers.clear()
    wurzel.addHandler(ausgabe)
    wurzel.setLevel(config.LOG_LEVEL)

    # Uvicorns eigene Handler entfernen, sonst erscheint jede Zeile doppelt
    # und einmal davon unstrukturiert.
    for name in ("uvicorn", "uvicorn.error"):
        protokoll = logging.getLogger(name)
        protokoll.handlers.clear()
        protokoll.propagate = True

    # Das Zugriffsprotokoll bleibt stumm. Die Anwendung protokolliert jede
    # Anfrage selbst und strukturiert; uvicorns Fassung wäre eine Dublette
    # und führte zusätzlich die Adresse des Aufrufers mit. Ein Werkzeug für
    # Patientendaten sollte nicht nebenbei festhalten, wer wann welche
    # Unterlage bearbeitet hat.
    zugriff = logging.getLogger("uvicorn.access")
    zugriff.handlers.clear()
    zugriff.propagate = False
    zugriff.disabled = True

    return logging.getLogger("anonymisator")


class Zeitmesser:
    """Misst die Dauer eines Abschnitts in Millisekunden."""

    def __enter__(self) -> "Zeitmesser":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self.ms = round((time.perf_counter() - self._start) * 1000, 1)
