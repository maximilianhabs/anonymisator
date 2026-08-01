"""Webserver für den Anonymisator.

Der Dienst hält keinerlei Dokumentinhalte: jede Anfrage bringt ihren Text
mit, die Antwort geht zurück, danach bleibt nichts liegen. Es gibt keine
Session, kein Upload-Verzeichnis, keine Datenbank und kein Protokoll der
Inhalte.

Beim Betrieb hinter einem Reverse Proxy bindet der Dienst an 0.0.0.0 und ist
damit im Containernetz erreichbar. Die Zugangskontrolle liegt dann beim
Proxy — ohne sie kann jeder, der die Adresse kennt, Dokumente hochladen.
"""

from __future__ import annotations

import re
import time
import uuid

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, detect, export, extract, logging_setup, stufen

STATIC = config.STATIC_DIR
_log = logging_setup.einrichten()

app = FastAPI(title="Anonymisator", docs_url=None, redoc_url=None)


@app.on_event("startup")
async def beim_start() -> None:
    _log.info("Dienst startet", extra={
        "modell": config.SPACY_MODELL,
        "ocr_sprache": config.OCR_SPRACHE,
        "max_upload_mb": config.MAX_UPLOAD_MB,
        "log_json": config.LOG_JSON,
    })
    if config.MODELL_VORLADEN:
        # Ohne Vorladen träfe der erste Anwender die Ladezeit des Modells,
        # und der Healthcheck meldete den Dienst als bereit, bevor er es ist.
        beginn = time.perf_counter()
        try:
            detect._modell()
            _log.info("Sprachmodell geladen", extra={
                "dauer_ms": round((time.perf_counter() - beginn) * 1000, 1)})
        except Exception as fehler:
            _log.error("Sprachmodell konnte nicht geladen werden",
                       extra={"grund": str(fehler)})


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class TextEingabe(BaseModel):
    text: str


class BegriffEingabe(BaseModel):
    text: str
    begriff: str
    naechste_id: str


class Ersetzung(BaseModel):
    start: int
    ende: int
    label: str


class ExportEingabe(BaseModel):
    text: str
    ersetzungen: list[Ersetzung]
    format: str
    dateiname: str = "dokument"
    mit_kopfzeile: bool = True
    stufe: str = "standard"


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------

def _gruppe_als_dict(gruppe: detect.Gruppe) -> dict:
    return {
        "id": gruppe.id,
        "typ": gruppe.typ,
        "anzeige": gruppe.anzeige,
        "label": gruppe.label,
        "initialen": gruppe.initialen,
        "aktiv": gruppe.aktiv,
        "sicher": gruppe.sicher,
        "varianten": gruppe.varianten,
        "funde": [{"start": f.start, "ende": f.end, "text": f.text,
                   "quelle": f.quelle, "formen": f.formen}
                  for f in gruppe.funde],
    }


def _antwort(auszug: extract.Extraktion) -> dict:
    if not auszug.text.strip():
        raise HTTPException(
            422,
            "Aus der Datei liess sich kein Text gewinnen. Bei einem Scan ohne "
            "Textlayer kann das an sehr schlechter Bildqualität liegen.",
        )
    gruppen = detect.analysiere(auszug.text)
    zeitbezug = stufen.formen_berechnen(gruppen)
    return {
        "stufen": stufen.STUFEN,
        "stufen_info": stufen.STUFEN_INFO,
        "stufen_reihenfolge": stufen.STUFEN_REIHENFOLGE,
        "zeitbezug": zeitbezug,
        "text": auszug.text,
        "quelle": auszug.quelle,
        "seiten": auszug.seiten,
        "hinweise": auszug.hinweise,
        "gruppen": [_gruppe_als_dict(g) for g in gruppen],
        "kategorien": {
            name: {
                "titel": detect.KATEGORIE_TITEL[name],
                "farbe": eigenschaften["farbe"],
                "label": eigenschaften["label"],
                "stil": eigenschaften["stil"],
            }
            for name, eigenschaften in detect.KATEGORIEN.items()
        },
    }


# --------------------------------------------------------------------------
# Endpunkte
# --------------------------------------------------------------------------

@app.post("/api/analysieren/datei")
async def analysieren_datei(datei: UploadFile = File(...)):
    """Liest die Datei, wertet sie aus und vergisst sie.

    Zum Umgang mit der hochgeladenen Datei: Starlette hält Uploads bis 1 MB
    im Arbeitsspeicher und legt alles darüber in einer temporären Datei unter
    TMPDIR ab. Im Behälter ist TMPDIR ein tmpfs — die Datei erreicht also
    keine Platte, sondern bleibt im Arbeitsspeicher und ist beim Neustart in
    jedem Fall fort.

    Geschlossen wird sie hier ausdrücklich, unmittelbar nach dem Lesen, statt
    erst beim Aufräumen der Anfrage. Damit verschwindet die temporäre Datei
    schon vor der Analyse, nicht erst nach dem Absenden der Antwort.
    """
    name = datei.filename or ""
    try:
        daten = await datei.read()
    finally:
        # Löscht die temporäre Datei, sofern Starlette eine angelegt hat.
        await datei.close()

    if not daten:
        raise HTTPException(422, "Die Datei ist leer.")
    if len(daten) > config.MAX_UPLOAD_MB * 1024 * 1024:
        del daten
        raise HTTPException(
            413, f"Die Datei ist grösser als {config.MAX_UPLOAD_MB} MB.")

    try:
        auszug = extract.aus_upload(name, daten)
    except ValueError as fehler:
        raise HTTPException(422, str(fehler)) from fehler
    except Exception as fehler:  # defekte PDFs, unlesbare DOCX
        raise HTTPException(
            422, f"Die Datei konnte nicht gelesen werden: {fehler}") from fehler
    finally:
        # Der Dateiinhalt wird ab hier nicht mehr gebraucht: gearbeitet wird
        # mit dem gewonnenen Text. Die Referenz fällt sofort weg, damit die
        # Rohbytes nicht bis zum Ende der Anfrage im Speicher stehen.
        del daten

    return _antwort(auszug)


@app.post("/api/analysieren/text")
async def analysieren_text(eingabe: TextEingabe):
    if not eingabe.text.strip():
        raise HTTPException(422, "Kein Text übergeben.")
    return _antwort(extract.aus_text(eingabe.text))


@app.post("/api/begriff")
async def begriff_suchen(eingabe: BegriffEingabe):
    gruppe = detect.manuelle_gruppe(eingabe.text, eingabe.begriff, eingabe.naechste_id)
    if gruppe is None:
        return JSONResponse({"gefunden": False, "gruppe": None})
    return {"gefunden": True, "gruppe": _gruppe_als_dict(gruppe)}


@app.post("/api/export")
async def exportieren(eingabe: ExportEingabe):
    if eingabe.format not in export.FORMATE:
        raise HTTPException(400, f"Unbekanntes Format: {eingabe.format}")

    ergebnis = export.ersetze(
        eingabe.text,
        [{"start": e.start, "ende": e.ende, "label": e.label}
         for e in eingabe.ersetzungen],
    )

    erzeuger, mimetyp, endung = export.FORMATE[eingabe.format]
    daten = erzeuger(ergebnis, eingabe.mit_kopfzeile, eingabe.stufe)

    # Der übergebene Dateiname landet im Content-Disposition-Header und wird
    # deshalb auf harmlose Zeichen reduziert.
    basis = re.sub(r"[^\w\-. ]", "_", eingabe.dateiname).strip() or "dokument"
    name = f"{basis}_anonymisiert.{endung}"

    return Response(
        content=daten,
        media_type=mimetyp,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.get("/api/status")
async def status():
    try:
        detect._modell()
        modell_bereit = True
        fehler = None
    except Exception as e:
        modell_bereit = False
        fehler = str(e)
    return {"modell": detect.MODELL_NAME, "bereit": modell_bereit, "fehler": fehler}


@app.get("/health")
async def health():
    """Bereitschaftsprüfung für Docker und Reverse Proxy.

    Meldet erst dann gesund, wenn das Sprachmodell tatsächlich geladen ist —
    ein Dienst, der zwar antwortet, aber keine Erkennung leisten kann, würde
    sonst Verkehr bekommen, den er nicht bedienen kann.
    """
    try:
        detect._modell()
    except Exception as fehler:
        return JSONResponse(
            status_code=503,
            content={"status": "nicht bereit", "grund": str(fehler)},
        )
    return {"status": "bereit", "modell": detect.MODELL_NAME}


@app.middleware("http")
async def protokoll_und_kopfzeilen(anfrage: Request, weiter):
    """Protokolliert jede Anfrage — ohne eine Spur ihres Inhalts.

    Festgehalten werden Methode, Pfad, Statuscode und Dauer. Nicht der
    Dokumenttext, nicht der Dateiname, nicht die erkannten Entitäten. Ein
    Protokoll, das Klarnamen enthielte, höbe den Zweck der Anwendung auf.
    """
    kennung = uuid.uuid4().hex[:12]
    beginn = time.perf_counter()
    try:
        antwort = await weiter(anfrage)
    except Exception:
        _log.exception("Anfrage fehlgeschlagen", extra={
            "anfrage": kennung,
            "methode": anfrage.method,
            "pfad": anfrage.url.path,
            "dauer_ms": round((time.perf_counter() - beginn) * 1000, 1),
        })
        raise

    dauer = round((time.perf_counter() - beginn) * 1000, 1)
    if anfrage.url.path != "/health":  # sonst flutet der Healthcheck das Log
        _log.info("Anfrage", extra={
            "anfrage": kennung,
            "methode": anfrage.method,
            "pfad": anfrage.url.path,
            "status": antwort.status_code,
            "dauer_ms": dauer,
        })

    # Kein Zwischenspeichern: nach einem Update sonst stundenlang die alte
    # Oberfläche. Bei einem Werkzeug für Patientendaten kommt hinzu, dass
    # Antworten nicht in Proxy- oder Browsercaches liegen bleiben sollen.
    antwort.headers["Cache-Control"] = "no-store, must-revalidate"
    antwort.headers["X-Anfrage-Kennung"] = kennung

    # Die Anwendung lädt nichts aus dem Netz und soll auch nichts laden
    # können. Das ist hier kein Selbstzweck: Wer eine eingeschleuste Quelle
    # nachladen könnte, könnte den Dokumenttext aus dem Browser
    # heraustragen -- an der zustandslosen Verarbeitung im Rücken vorbei.
    #
    # 'unsafe-inline' steht bewusst nur bei style-src: die Oberfläche setzt
    # die Farbcodierung der Fundstellen über style-Attribute. Ohne die
    # Ausnahme bliebe die Prüfansicht farblos, was die Erkennungsarbeit
    # unbrauchbar machte. Für Skripte gilt sie nicht -- inline-Skripte gibt
    # es in der Oberfläche keine, und genau dort läge auch das Risiko.
    antwort.headers["X-Frame-Options"] = "DENY"
    antwort.headers["X-Content-Type-Options"] = "nosniff"
    antwort.headers["Referrer-Policy"] = "no-referrer"
    antwort.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'; "
        "object-src 'none'"
    )
    return antwort


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
