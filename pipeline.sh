#!/usr/bin/env bash
# Startet den Ordner-Modus (opt-in): Dateien aus dem Eingang werden ohne
# Rückfrage anonymisiert. Ersetzt NICHT den Review im Web-Werkzeug.
#
#   ./pipeline.sh --eingang <Ordner> --ausgang <Ordner> [--stufe streng] [--einmal]
#
# Alle Argumente gehen unverändert an `python -m app.ordner` (siehe README,
# Abschnitt "Ordner-Modus"). Eingang und Ausgang haben keinen Standardpfad.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "Kein .venv gefunden. Einmalig einrichten mit:"
  echo "  ./einrichten.sh"
  exit 1
fi

# Nichts davon öffnet einen Port oder verbindet nach aussen.
exec .venv/bin/python -m app.ordner "$@"
