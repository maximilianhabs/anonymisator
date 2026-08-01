#!/usr/bin/env bash
#
# vorpruefung.sh — prüft, ob der Server das Deployment trägt.
#
# Ändert nichts. Läuft vom Entwicklungsrechner aus über SSH und beantwortet
# die Fragen, die vor dem ersten Start geklärt sein müssen: reicht der
# Arbeitsspeicher, reicht die Platte, ist die Subdomain aufgelöst, steht das
# gemeinsame Netz.
#
#     bash deploy/vorpruefung.sh
#
set -uo pipefail

SERVER="deploy@203.0.113.10"
DOMAIN="ano.neuro-vibe.de"

# Bedarf laut Messung: Sprachmodell 600 MB je Arbeitsprozess, dazu
# Verarbeitungsspielraum. Darunter wird es unzuverlässig.
MIN_RAM_MB=1400

# Gemessen an den beiden Stufen des Abbilds: Bauschicht 2,39 GB,
# Laufzeitschicht 2,32 GB. Beide bestehen während des Baus gleichzeitig, die
# Spitze liegt also bei etwa 4,7 GB — konservativ gerechnet, weil geteilte
# Basisebenen doppelt gezählt sind. 7 GB lassen darüber hinaus Luft für den
# Zwischenspeicher des Bauwerkzeugs.
MIN_PLATTE_GB=7

rot()   { printf '\033[31m✗ %s\033[0m\n' "$*"; }
gruen() { printf '\033[32m✓ %s\033[0m\n' "$*"; }
gelb()  { printf '\033[33m! %s\033[0m\n' "$*"; }
kopf()  { printf '\n\033[1m%s\033[0m\n' "$*"; }

probleme=0
warnungen=0

kopf "1 · Namensauflösung"
# Gefragt werden öffentliche Auflöser, nicht der des Entwicklungsrechners.
# Der hat womöglich noch die Fehlantwort von vor dem Anlegen des Eintrags
# zwischengespeichert — und ist für Let's Encrypt ohnehin nicht massgeblich.
treffer=0
for aufloeser in 8.8.8.8 1.1.1.1 9.9.9.9; do
    ziel=$(dig +short +time=3 +tries=1 "@$aufloeser" "$DOMAIN" A 2>/dev/null | tail -1)
    if [ "$ziel" = "203.0.113.10" ]; then
        treffer=$((treffer + 1))
    elif [ -n "$ziel" ]; then
        rot "$aufloeser meldet $ziel statt 203.0.113.10"
    fi
done
if [ "$treffer" -eq 3 ]; then
    gruen "$DOMAIN → 203.0.113.10 (bei allen drei Auflösern)"
elif [ "$treffer" -gt 0 ]; then
    gelb "erst $treffer von 3 Auflösern kennen den Eintrag — noch in Verbreitung"
    warnungen=$((warnungen + 1))
else
    rot "$DOMAIN löst nirgends auf — A-Record im Hetzner-Dashboard fehlt"
    probleme=$((probleme + 1))
fi

# Ein AAAA-Eintrag auf dieser Subdomain wäre ein Fehler: der Dienst hört nur
# auf IPv4, und ein solcher Eintrag hat beim SSH-Zugang schon einmal auf die
# Storage Box geleitet.
if [ -n "$(dig +short @1.1.1.1 "$DOMAIN" AAAA 2>/dev/null)" ]; then
    gelb "AAAA-Eintrag vorhanden — sollte für diese Subdomain nicht gesetzt sein"
    warnungen=$((warnungen + 1))
fi

kopf "2 · Erreichbarkeit des Servers"
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER" true 2>/dev/null; then
    rot "SSH zu $SERVER nicht möglich — Abbruch"
    exit 1
fi
gruen "SSH steht"

kopf "3 · Arbeitsspeicher"
frei=$(ssh "$SERVER" "free -m | awk '/^Mem:/ {print \$7}'")
swap=$(ssh "$SERVER" "free -m | awk '/^Swap:/ {print \$2}'")
echo "   verfügbar: ${frei} MB, Auslagerungsdatei: ${swap} MB"
if [ "$frei" -lt "$MIN_RAM_MB" ]; then
    rot "unter ${MIN_RAM_MB} MB verfügbar — Deployment nicht zu verantworten"
    probleme=$((probleme + 1))
else
    gruen "reicht für einen Arbeitsprozess"
fi
if [ "$swap" -eq 0 ]; then
    gelb "keine Auslagerungsdatei: bei Überschreitung greift der OOM-Killer,"
    echo "     und der trifft womöglich einen der anderen Dienste."
    warnungen=$((warnungen + 1))
fi

kopf "4 · Plattenplatz"
frei_gb=$(ssh "$SERVER" "df --output=avail -BG / | tail -1 | tr -d 'G '")
echo "   frei: ${frei_gb} GB"
if [ "$frei_gb" -lt "$MIN_PLATTE_GB" ]; then
    rot "unter ${MIN_PLATTE_GB} GB — der Bau des Abbilds (2,3 GB) scheitert"
    echo "     Abhilfe:  docker builder prune -f && docker image prune -f"
    ssh "$SERVER" "docker system df" | sed 's/^/     /'
    probleme=$((probleme + 1))
else
    gruen "reicht für den Bau"
fi

kopf "5 · Gemeinsames Docker-Netz"
if ssh "$SERVER" "docker network inspect nz-dienstplan_app >/dev/null 2>&1"; then
    gruen "nz-dienstplan_app vorhanden"
else
    rot "Netz nz-dienstplan_app fehlt — läuft der Dienstwerk-Stack?"
    probleme=$((probleme + 1))
fi

kopf "6 · Ports 80/443"
belegt=$(ssh "$SERVER" "docker ps --format '{{.Names}} {{.Ports}}' | grep -c ':443' || true")
if [ "$belegt" -gt 0 ]; then
    gruen "bereits durch den bestehenden Caddy belegt — richtig so"
    echo "   → docker-compose.server.yml verwenden, nicht docker-compose.yml"
else
    gelb "kein Dienst auf 443 — läuft der Caddy des Dienstwerks?"
    warnungen=$((warnungen + 1))
fi

kopf "7 · Namenskonflikte"
for name in anonymisator; do
    if ssh "$SERVER" "docker ps -a --format '{{.Names}}' | grep -qx $name"; then
        gelb "Container '$name' existiert bereits — wird beim Deploy ersetzt"
        warnungen=$((warnungen + 1))
    else
        gruen "Containername '$name' ist frei"
    fi
done
if ssh "$SERVER" "test -e ~/anonymisator"; then
    gelb "~/anonymisator existiert bereits"
    warnungen=$((warnungen + 1))
else
    gruen "~/anonymisator ist frei"
fi

kopf "8 · Bestehende Anwendungen"
for url in https://neuro-vibe.de https://eeg.neuro-vibe.de https://edf.neuro-vibe.de; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" || echo 000)
    printf '   %-30s HTTP %s\n' "$url" "$code"
done
echo "   (Ausgangswert — nach dem Deployment muss dasselbe herauskommen)"

kopf "Ergebnis"
if [ "$probleme" -gt 0 ]; then
    rot "$probleme Punkt(e) blockieren das Deployment"
    [ "$warnungen" -gt 0 ] && gelb "$warnungen Warnung(en)"
    exit 1
fi
if [ "$warnungen" -gt 0 ]; then
    gelb "$warnungen Warnung(en) — Deployment möglich, siehe oben"
    exit 0
fi
gruen "Server ist bereit"
