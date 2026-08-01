# syntax=docker/dockerfile:1.7
#
# Zweistufiger Aufbau. Die Bauphase zieht Übersetzer und Entwicklungsdateien
# heran, die Laufzeitschicht bekommt davon nichts zu sehen — sie erhält nur
# das fertige virtuelle Umfeld.
#
# Das Basisabbild ist über seinen Digest festgelegt, nicht über ein
# bewegliches Etikett. Nur so liefert derselbe Bauauftrag auf jedem Server
# dasselbe Ergebnis; "python:3.13-slim" zeigt je nach Tag auf verschiedene
# Abbilder.

ARG BASIS=python:3.13.3-slim-bookworm@sha256:56a11364ffe0fee3bd60af6d6d5209eba8a99c2c16dc4c7c5861dc06261503cc

# ==========================================================================
# Bauphase
# ==========================================================================
FROM ${BASIS} AS bau

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential nur hier: PyMuPDF und die spaCy-Abhängigkeiten bringen
# Erweiterungen mit, die übersetzt werden müssen, falls kein passendes Rad
# vorliegt. Die Laufzeitschicht braucht davon nichts.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Erst die Abhängigkeiten, dann der Quelltext: so bleibt diese Schicht im
# Zwischenspeicher, solange sich requirements.txt nicht ändert.
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Das Sprachmodell steckt bereits als Rad-Adresse mit fester Version in
# requirements.txt und liegt damit im Abbild. Zur Laufzeit wird nichts
# nachgeladen — der Behälter hat keinen Netzzugang.
RUN python -c "import spacy; spacy.load('de_core_news_lg')" \
    && python -c "import fitz, docx, reportlab, pytesseract; print('Abhängigkeiten geladen')"

# ==========================================================================
# Laufzeitschicht
# ==========================================================================
FROM ${BASIS} AS laufzeit

LABEL org.opencontainers.image.title="Anonymisator" \
      org.opencontainers.image.description="Lokale De-Identifikation deutschsprachiger Dokumente" \
      org.opencontainers.image.source="https://github.com/maximilianhabs/anonymisator" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    ANON_STATIC_DIR=/app/static \
    TMPDIR=/tmp

# Tesseract mit deutschem Sprachpaket, dazu die Systembibliotheken, die
# Pillow und PyMuPDF zur Laufzeit benötigen. Bewusst ohne Empfehlungen, um
# die Angriffsfläche klein zu halten.
#
# Zu den Paketversionen: Debian pflegt innerhalb einer stabilen
# Veröffentlichung dieselben Hauptversionen und liefert nur Sicherheits-
# korrekturen nach. Eine harte Festlegung auf Patch-Stände würde den Bau
# brechen, sobald ein Stand aus dem Spiegel verschwindet — und sie würde
# genau die Sicherheitskorrekturen aussperren, die man haben will. Die
# Reproduzierbarkeit kommt deshalb vom Digest des Basisabbilds, das den
# Paketstand mitbringt.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-deu \
        libgl1 \
        libglib2.0-0 \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Unprivilegiertes Konto ohne Anmeldeschale und ohne eigenes Heimatverzeichnis
# auf beschreibbarem Grund.
RUN groupadd --gid 10001 anon \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin anon

COPY --from=bau /opt/venv /opt/venv

WORKDIR /app
COPY --chown=root:root app/ /app/app/
COPY --chown=root:root static/ /app/static/

# Der Quelltext gehört root und ist für den Dienstbenutzer nur lesbar. Zusammen
# mit dem schreibgeschützten Wurzeldateisystem kann ein übernommener Prozess
# den eigenen Code nicht verändern.
RUN chmod -R a-w /app

USER anon:anon

EXPOSE 8000

# Der Healthcheck fragt denselben Endpunkt ab, den auch der Reverse Proxy
# nutzt. start-period ist grosszügig: das Sprachmodell braucht beim ersten
# Laden einige Sekunden.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${ANON_PORT:-8000}/health" || exit 1

# 0.0.0.0 ist hier richtig: erreichbar sein soll der Dienst nur im
# Behälternetz, nach aussen führt allein der Reverse Proxy.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${ANON_PORT:-8000} --workers ${ANON_WORKERS:-2} --no-access-log --proxy-headers --forwarded-allow-ips '*'"]
