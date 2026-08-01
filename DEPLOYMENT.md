# Deployment auf neuro-vibe.de

Zielzustand: `ano.neuro-vibe.de` → HTTPS → bestehender Caddy → Container
`anonymisator` → lokale De-Identifikation ohne Datenpersistenz.

Diese Anleitung gilt für **einen Server, auf dem bereits vier Anwendungen
laufen**. Das prägt fast jede Entscheidung darin.

---

## Vor dem ersten Deployment: drei Punkte müssen geklärt sein

### 1 · Arbeitsspeicher — der enge Punkt

Stand der Messung auf dem Server:

| | |
|---|---|
| Gesamt | 3,7 GB |
| Belegt | 1,5 GB (vier Anwendungen) |
| Verfügbar | 2,2 GB |
| Auslagerungsdatei | **keine** |

Der Anonymisator hält das Sprachmodell im Speicher: rund 600 MB **je
Arbeitsprozess**. Dazu kommt die Verarbeitung — gemessen 1,0 GB bei 100
Seiten, 2,1 GB bei 300.

Ohne Auslagerungsdatei bedeutet eine Überschreitung nicht etwa eine
Fehlermeldung, sondern den OOM-Killer. Der trifft nicht zwingend den
Verursacher, sondern den Prozess mit dem grössten Speicherbedarf — das kann
die Datenbank des Dienstwerks sein.

**Deshalb ist `docker-compose.server.yml` bewusst sparsam eingestellt:**

| Einstellung | Wert | Grund |
|---|---|---|
| `ANON_WORKERS` | 1 | spart 600 MB gegenüber der Voreinstellung |
| `ANON_MAX_SEITEN` | 80 | darüber reicht der Speicher nicht |
| `ANON_MAX_OCR_SEITEN` | 25 | Rastern ist der teuerste Schritt |
| `ANON_MEM_LIMIT` | 1600m | harte Grenze — schützt die anderen Dienste |

Empfehlung, unabhängig von diesem Projekt: **eine Auslagerungsdatei
anlegen.** Ein Server ohne Swap hat keinerlei Puffer.

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2 · Plattenplatz — reicht knapp nicht

| | |
|---|---|
| Gesamt | 38 GB |
| Belegt | 30 GB (82 %) |
| Frei | 6,6 GB |
| Docker-Baucache | 25,8 GB |

Gemessen an den beiden Stufen des Abbilds: Bauschicht 2,39 GB,
Laufzeitschicht 2,32 GB. Beide bestehen während des Baus gleichzeitig, die
Spitze liegt also bei etwa **4,7 GB** — konservativ gerechnet, weil geteilte
Basisebenen doppelt gezählt sind.

**Vor dem Bau aufräumen:**

```bash
docker builder prune -f          # gibt mehrere GB frei
df -h /                          # danach prüfen: mindestens 7 GB frei
```

*Erledigt am 2026-08-01: 3,5 GB freigegeben, 6,6 GB → 9,5 GB. Alle sechs
Container liefen unverändert weiter.*

### 3 · Gebaut wird auf dem Server

Der Server ist `x86_64`, ein Entwicklungsrechner mit Apple Silicon ist
`arm64`. Ein lokal gebautes Abbild lässt sich **nicht** übertragen. Der Bau
läuft auf dem Server; er dauert dort mehrere Minuten und belastet den
Rechner spürbar — nicht zur Sprechstundenzeit ausführen.

---

## Abweichungen von der ursprünglichen Vorgabe

| Vorgabe | Umsetzung | Grund |
|---|---|---|
| `/opt/apps/ano-deidentifier` | `~/anonymisator` | `/opt` gehört root, `deploy` hat kein Schreibrecht. Alle drei bestehenden Anwendungen liegen unter `~`. |
| eigener Reverse Proxy | bestehender Caddy | Ports 80/443 sind belegt; ein zweiter Proxy könnte nicht starten. |
| Ubuntu 24.04 | Ubuntu 26.04 LTS | Server ist bereits neuer. |

---

## Ablauf

### Schritt 1 — DNS (im Hetzner-Dashboard)

| Feld | Wert |
|---|---|
| Name | `ano` |
| Typ | `A` |
| Ziel | `203.0.113.10` |

Prüfen, bevor es weitergeht — Caddy fordert sonst vergeblich ein Zertifikat
an und läuft in die Sperre von Let's Encrypt:

```bash
dig +short ano.neuro-vibe.de     # muss 203.0.113.10 liefern
```

### Schritt 2 — Repository auf den Server

```bash
ssh deploy@203.0.113.10
git clone https://github.com/maximilianhabs/anonymisator.git ~/anonymisator
cd ~/anonymisator
cp .env.example .env
```

In `.env` anpassen — die Werte aus `docker-compose.server.yml` gelten als
Vorgabe, `.env` überschreibt sie nur bei Bedarf:

```
ANON_WORKERS=1
ANON_MAX_SEITEN=80
ANON_MEM_LIMIT=1600m
```

`ANON_DOMAIN`, `ANON_HTTP_PORT` und die Zugangsdaten werden **nicht**
gebraucht: In dieser Fassung gibt es keinen eigenen Caddy, die
Zugangskontrolle liegt im zentralen Caddyfile.

### Schritt 3 — Zugangspasswort

```bash
docker run --rm caddy:2.10-alpine caddy hash-password
```

Den Hash notieren. Er kommt in Schritt 4 ins Caddyfile — dort **ohne**
Verdopplung der Dollarzeichen (das ist nur in Compose-Dateien nötig).

### Schritt 4 — Caddy-Route eintragen

Der Block steht vorbereitet in `deploy/Caddyfile.block`. Er wird an
`~/nz-dienstplan/Caddyfile` angehängt — **dort und nirgends sonst**, weil
der Caddy des Dienstwerk-Stacks genau diese eine Datei liest.

```bash
cat ~/anonymisator/deploy/Caddyfile.block >> ~/nz-dienstplan/Caddyfile
nano ~/nz-dienstplan/Caddyfile      # HIER_DEN_BCRYPT_HASH_EINTRAGEN ersetzen
```

Änderung im Dienstwerk-Repository festhalten, sonst geht sie beim nächsten
`git pull` dort verloren:

```bash
cd ~/nz-dienstplan
git add Caddyfile && git commit -m "Caddy-Route für ano.neuro-vibe.de"
git push
```

### Schritt 5 — Container starten

```bash
cd ~/anonymisator
docker compose -f docker-compose.server.yml up -d --build
```

Der erste Bau dauert mehrere Minuten. Warten, bis der Dienst gesund meldet —
das Sprachmodell braucht beim Start etwa 15 Sekunden:

```bash
docker compose -f docker-compose.server.yml ps
docker logs -f anonymisator
```

### Schritt 6 — Caddy neu laden

Erst **nachdem** der Container gesund ist, sonst holt Caddy ein Zertifikat
für einen Dienst, der nicht antwortet:

```bash
docker exec nz-dienstplan-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

Der Reload läuft ohne Unterbrechung für die anderen Anwendungen.

---

## Abnahme

```bash
# 1 · Container gesund und im richtigen Netz
docker inspect anonymisator --format '{{.State.Health.Status}}'
docker inspect anonymisator --format '{{range $n,$v := .NetworkSettings.Networks}}{{$n}} {{end}}'
#   → muss nz-dienstplan_app enthalten

# 2 · Kein Port nach aussen
docker port anonymisator
#   → muss leer sein

# 3 · Zugangsschutz greift
curl -s -o /dev/null -w '%{http_code}\n' https://ano.neuro-vibe.de/
#   → 401
curl -s -o /dev/null -w '%{http_code}\n' -u anonymisator:PASSWORT https://ano.neuro-vibe.de/
#   → 200
curl -s https://ano.neuro-vibe.de/health
#   → {"status":"bereit",...}

# 4 · Anonymisierung funktioniert
curl -s -u anonymisator:PASSWORT -X POST https://ano.neuro-vibe.de/api/analysieren/text \
  -H 'Content-Type: application/json' \
  -d '{"text":"Frau Elisabeth Hartmann, geb. 22.07.1958."}' | grep -q PATIENT_A && echo OK

# 5 · Protokoll ohne Dokumentinhalte
docker logs anonymisator 2>&1 | grep -c -E 'Hartmann|22\.07\.1958'
#   → 0

# 6 · Keine Persistenz
docker inspect anonymisator --format '{{range .Mounts}}{{.Type}} {{.Destination}} {{end}}'
#   → nur tmpfs /tmp

# 7 · Neustartfest
docker inspect anonymisator --format '{{.HostConfig.RestartPolicy.Name}}'
#   → unless-stopped

# 8 · Die anderen Anwendungen laufen unverändert
for url in https://neuro-vibe.de https://eeg.neuro-vibe.de https://edf.neuro-vibe.de; do
  printf '%-32s %s\n' "$url" "$(curl -s -o /dev/null -w '%{http_code}' "$url")"
done
free -h
```

Zusätzlich von Hand im Browser: Datei hochladen, Fundstellen prüfen, in allen
drei Formaten exportieren, die Exportdateien öffnen und auf verbliebene
Klarnamen durchsehen.

---

## Wenn etwas nicht stimmt

| Beobachtung | Ursache | Abhilfe |
|---|---|---|
| `ano.neuro-vibe.de` nicht erreichbar | Container nicht im Netz `nz-dienstplan_app` | `docker network connect nz-dienstplan_app anonymisator` |
| Caddy meldet 502 | Container noch nicht bereit | `docker logs anonymisator`; Modell braucht ~15 s |
| Caddyfile-Änderung wirkt nicht | Proxy nicht neu geladen | `docker exec nz-dienstplan-caddy-1 caddy reload --config /etc/caddy/Caddyfile` |
| Container dauerhaft „unhealthy" | Healthcheck auf `localhost` statt `127.0.0.1` | in dieser Fassung bereits vermieden |
| Bau bricht mit „no space left" ab | Plattenplatz | `docker builder prune -f` |
| Anderer Dienst plötzlich beendet | OOM-Killer, kein Swap | `ANON_WORKERS=1`, `ANON_MAX_SEITEN` senken, Swap anlegen |
| SSH landet auf der Storage Box | AAAA-Record im DNS | immer `ssh deploy@203.0.113.10` |
| Caddyfile-Änderung wirkt auch nach Reload nicht | **toter Bind-Mount**: Docker bindet bei einer einzelnen Datei die Inode, ein `git pull` ersetzt sie. Der Container arbeitet dann mit einem eingefrorenen Stand. | Prüfsummen vergleichen (`docker exec … md5sum /etc/caddy/Caddyfile` gegen `md5sum ~/nz-dienstplan/Caddyfile`). Bei Abweichung Container neu starten. |
| `docker compose restart caddy` meldet „no such service" | Der Caddy steht in `docker-compose.prod.yml`, nicht in der Standarddatei | `docker compose -f docker-compose.prod.yml restart caddy` |

## Durchgeführt am 2026-08-01

Alle acht Abnahmeprüfungen bestanden:

| Prüfung | Ergebnis |
|---|---|
| Container | `healthy`, Netz `nz-dienstplan_app`, kein Port nach aussen |
| Benutzer | UID 10001, Wurzeldateisystem schreibgeschützt |
| Persistenz | keine Einhängung ausser `tmpfs /tmp` |
| Neustartverhalten | `unless-stopped` |
| Zugangsschutz | ohne Zugangsdaten HTTP 401, `/health` frei |
| Zertifikat | Let's Encrypt, gültig bis 30.10.2026 |
| Erkennung | Patientin, Behandlerin, Geburtsdatum, Fallnummer korrekt |
| Protokoll | fünf Suchbegriffe geprüft, kein Dokumentinhalt |
| Bestehende Dienste | unverändert (307 / 307 / 200) |

Speicher nach dem Start: Container 1008 MB von 1562 MB Grenze, Server
1,3 GB verfügbar.

**Zwei Funde, die nichts mit dem Anonymisator zu tun hatten:**

Der Bind-Mount des Caddyfiles war seit dem 22.06. tot — jede Änderung
seitdem lief ins Leere. Behoben durch Neustart (1 Sekunde Unterbrechung).

Der laufende Caddy-Stand enthielt zwei Zeilen, die nie im Git standen:
`header_up X-Forwarded-Proto` und `-Host` im edf-Block. Ohne sie erkennt
Streamlit hinter dem Proxy kein HTTPS. Sie sind jetzt versioniert.

## Anhalten, wenn der Speicher anderweitig gebraucht wird

Der Anonymisator hält das Sprachmodell dauerhaft im Arbeitsspeicher — rund
**950 MB von 3,7 GB**. Wer eine Weile intensiv an einer der anderen
Anwendungen arbeitet, gewinnt durch ein Anhalten spürbar Luft.

```bash
ssh deploy@203.0.113.10 'bash ~/anonymisator/deploy/dienst.sh pause'
ssh deploy@203.0.113.10 'bash ~/anonymisator/deploy/dienst.sh weiter'
ssh deploy@203.0.113.10 'bash ~/anonymisator/deploy/dienst.sh status'
```

Gemessen am 2026-08-01: verfügbarer Speicher **1257 MB → 2209 MB**, also
**+952 MB**. Die drei anderen Anwendungen liefen dabei unverändert weiter.

Was dabei geschieht — und was nicht:

- Der Behälter wird angehalten, **nicht entfernt**. Das Abbild bleibt, ein
  erneuter Bau entfällt. Der Wiederanlauf dauert rund 21 Sekunden.
- Docker merkt sich das Anhalten als ausdrücklich gewollt. Trotz
  `restart: unless-stopped` startet der Dienst deshalb **auch nach einem
  Neustart des Servers nicht** von selbst wieder.
- Es geht nichts verloren — der Dienst ist zustandslos und hat keine Daten,
  die überdauern könnten.
- Die Caddy-Route bleibt bestehen. Wer die Adresse aufruft, erhält für die
  Dauer der Pause einen Fehler 503.
- Nach dem Wiederanlauf dauert es **bis zu 30 Sekunden**, bis Caddy die
  Gegenstelle erneut prüft und wieder durchlässt. Das Skript wartet darauf
  und meldet es.

## Zurückrollen

```bash
docker compose -f docker-compose.server.yml down
# Caddy-Block aus ~/nz-dienstplan/Caddyfile entfernen, dann:
docker exec nz-dienstplan-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

Es bleibt nichts zurück: keine Datenbank, kein Volume, keine hochgeladene
Datei. Das ist die Kehrseite der Zustandslosigkeit — und hier die
erwünschte.
