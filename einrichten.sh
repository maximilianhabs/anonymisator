#!/usr/bin/env bash
# Richtet den Anonymisator einmalig ein — in zwei angekündigten Schritten,
# statt alles in einem stillen "pip install" verschwinden zu lassen.
#
# Schritt 1 (Grundgerüst: FastAPI, PDF/DOCX-Verarbeitung u. a.) ist klein
# und schnell. Schritt 2 (das deutsche Sprachmodell) ist mit 542 MB der
# eigentliche, oft lange dauernde Download — siehe README, Abschnitt
# "Einrichtung", für eine Zeittabelle nach Verbindungsgeschwindigkeit.
# Beide Schritte zusammen entsprechen exakt "pip install -r requirements.txt".
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "→ Lege virtuelle Umgebung an (.venv) …"
  python3 -m venv .venv
fi

echo
echo "[1/2] Grundgerüst wird installiert (FastAPI, PDF/DOCX-Verarbeitung, spaCy selbst) …"
.venv/bin/pip install -r requirements-core.txt
echo "✓ Grundgerüst fertig."

echo
echo "[2/2] Jetzt kommt das deutsche Sprachmodell (542 MB) — der grösste und"
echo "      letzte Schritt. Geschätzte Dauer je nach Verbindung: siehe README,"
echo "      Abschnitt 'Einrichtung'. Bricht die Verbindung ab, dieses Skript"
echo "      einfach erneut ausführen: das Grundgerüst ist dann schon fertig"
echo "      und wird übersprungen, nur der Modell-Download beginnt (pip"
echo "      setzt ihn nicht fort) noch einmal von vorn."
.venv/bin/pip install -r requirements-model.txt
echo "✓ Sprachmodell fertig."

echo
echo "Einrichtung abgeschlossen. Start mit: ./start.sh"
