#!/usr/bin/env bash
# Startet den Anonymisator lokal und öffnet den Browser.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "Kein .venv gefunden. Einmalig einrichten:"
  echo "  python3 -m venv .venv"
  echo "  .venv/bin/pip install -r requirements.txt"
  echo "(Das Sprachmodell steht mit fester Version in requirements.txt —"
  echo " ein separater 'spacy download'-Aufruf ist nicht nötig und würde"
  echo " die Version offenlassen.)"
  exit 1
fi

PORT="${PORT:-5302}"

# --host 127.0.0.1 ist Absicht: der Dienst darf im Netz nicht erreichbar sein.
(sleep 2 && open "http://127.0.0.1:${PORT}") &
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
