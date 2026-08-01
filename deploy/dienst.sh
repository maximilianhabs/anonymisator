#!/usr/bin/env bash
#
# dienst.sh — Anonymisator anhalten und wieder starten.
#
# Gedacht für Zeiten, in denen der Arbeitsspeicher des Servers anderweitig
# gebraucht wird. Der Anonymisator hält das Sprachmodell dauerhaft im
# Speicher — rund 1 GB von 3,7 GB. Wer intensiv am Dienstwerk arbeitet,
# gewinnt durch ein Anhalten spürbar Luft.
#
#     bash deploy/dienst.sh pause     # anhalten, Speicher freigeben
#     bash deploy/dienst.sh weiter    # wieder starten
#     bash deploy/dienst.sh status    # Zustand und Speicherlage
#
# Läuft auf dem Server oder von aussen über SSH:
#     ssh deploy@203.0.113.10 'bash ~/anonymisator/deploy/dienst.sh pause'
#
# Was beim Anhalten passiert — und was nicht:
#
#   • Der Behälter wird gestoppt, nicht entfernt. Das Abbild bleibt, ein
#     erneuter Bau ist nicht nötig; der Start dauert rund 25 Sekunden.
#   • Docker merkt sich das Anhalten als ausdrücklich gewollt. Trotz
#     "restart: unless-stopped" startet der Dienst deshalb auch nach einem
#     Neustart des Servers NICHT von selbst wieder.
#   • Es geht nichts verloren: der Dienst ist zustandslos und hat keine
#     Daten, die überdauern könnten.
#   • Die Caddy-Route bleibt bestehen. Wer die Adresse aufruft, erhält
#     einen Fehler des Reverse Proxy statt der Oberfläche — das ist der
#     einzige sichtbare Unterschied.
#
set -uo pipefail

VERZEICHNIS="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="docker compose -f $VERZEICHNIS/docker-compose.server.yml"
BEHAELTER="anonymisator"

gruen() { printf '\033[32m%s\033[0m\n' "$*"; }
gelb()  { printf '\033[33m%s\033[0m\n' "$*"; }
rot()   { printf '\033[31m%s\033[0m\n' "$*"; }

zustand() {
    docker inspect "$BEHAELTER" --format '{{.State.Status}}' 2>/dev/null || echo "fehlt"
}

speicherlage() {
    echo
    free -h | head -2 | sed 's/^/  /'
    echo
    printf '  %-28s %s\n' "Dienst" "Speicher"
    docker stats --no-stream --format '  {{.Name}}|{{.MemUsage}}' 2>/dev/null \
        | awk -F'|' '{printf "  %-28s %s\n", $1, $2}' | sed 's/^  //' | sed 's/^/  /'
}

case "${1:-status}" in

  pause|stop|anhalten)
      if [ "$(zustand)" != "running" ]; then
          gelb "Der Anonymisator läuft nicht (Zustand: $(zustand))."
          exit 0
      fi
      vorher=$(free -m | awk '/^Mem:/ {print $7}')
      echo "Halte den Anonymisator an …"
      $COMPOSE stop
      sleep 3
      nachher=$(free -m | awk '/^Mem:/ {print $7}')
      gruen "Angehalten. Verfügbarer Speicher: ${vorher} MB → ${nachher} MB (+$((nachher - vorher)) MB)"
      echo
      echo "  Wieder starten:  bash deploy/dienst.sh weiter"
      echo "  Der Dienst bleibt auch nach einem Server-Neustart aus."
      ;;

  weiter|start|starten)
      if [ "$(zustand)" = "running" ]; then
          gelb "Der Anonymisator läuft bereits."
          exit 0
      fi
      if [ "$(zustand)" = "fehlt" ]; then
          rot "Kein Behälter vorhanden — zuerst aufsetzen:"
          echo "  $COMPOSE up -d --build"
          exit 1
      fi
      echo "Starte den Anonymisator …"
      $COMPOSE start
      echo -n "  Warte auf Bereitschaft "
      for i in $(seq 1 40); do
          if [ "$(docker inspect "$BEHAELTER" --format '{{.State.Health.Status}}' 2>/dev/null)" = "healthy" ]; then
              echo
              gruen "Dienst bereit nach etwa $((i * 3)) Sekunden."
              # Das Sprachmodell wird beim Start geladen; vorher meldet der
              # Dienst bewusst "nicht bereit", damit Caddy keinen Verkehr
              # schickt, den er noch nicht bedienen kann.
              docker exec nz-dienstplan-caddy-1 \
                  wget -qO- --timeout=5 http://anonymisator:8000/health 2>/dev/null \
                  | sed 's/^/  /' || true
              echo

              # Caddy prüft seine Gegenstellen nur alle 30 Sekunden. Bis zur
              # nächsten Prüfung antwortet die Adresse noch mit 503 — das ist
              # kein Fehler, sondern der Takt des Reverse Proxy. Ohne diesen
              # Hinweis sähe es nach einem misslungenen Start aus.
              echo -n "  Warte, bis der Reverse Proxy wieder durchlässt "
              for k in $(seq 1 14); do
                  if docker exec nz-dienstplan-caddy-1 \
                       wget -qO- --timeout=3 http://127.0.0.1/health >/dev/null 2>&1; then
                      echo; gruen "  Über die Adresse erreichbar (nach $((k * 5)) s)."
                      exit 0
                  fi
                  printf '.'
                  sleep 5
              done
              echo
              gelb "  Caddy meldet die Gegenstelle noch nicht als gesund."
              echo "  Er prüft alle 30 Sekunden — in aller Regel genügt kurzes Warten."
              exit 0
          fi
          printf '.'
          sleep 3
      done
      echo
      rot "Nicht bereit geworden. Protokoll:"
      docker logs --tail 15 "$BEHAELTER"
      exit 1
      ;;

  status|zustand)
      z=$(zustand)
      case "$z" in
          running) gruen "Anonymisator: läuft ($(docker inspect "$BEHAELTER" --format '{{.State.Health.Status}}' 2>/dev/null))" ;;
          exited)  gelb  "Anonymisator: angehalten — startet auch nach Server-Neustart nicht" ;;
          fehlt)   rot   "Anonymisator: kein Behälter vorhanden" ;;
          *)       gelb  "Anonymisator: $z" ;;
      esac
      speicherlage
      ;;

  *)
      echo "Aufruf: $0 {pause|weiter|status}"
      exit 1
      ;;
esac
