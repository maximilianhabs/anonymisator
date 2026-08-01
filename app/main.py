"""Lokaler Webserver für den Anonymisator.

Bindet bewusst nur an 127.0.0.1. Der Server hält keinerlei Dokumentinhalte:
jede Anfrage bringt ihren Text mit, die Antwort geht zurück, danach bleibt
nichts liegen. Es gibt keine Session, kein Upload-Verzeichnis, kein Log der
Inhalte.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import detect, export, extract, stufen

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Anonymisator", docs_url=None, redoc_url=None)


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
    daten = await datei.read()
    if not daten:
        raise HTTPException(422, "Die Datei ist leer.")
    if len(daten) > 60 * 1024 * 1024:
        raise HTTPException(413, "Die Datei ist grösser als 60 MB.")
    try:
        auszug = extract.aus_upload(datei.filename or "", daten)
    except ValueError as fehler:
        raise HTTPException(422, str(fehler))
    except Exception as fehler:  # defekte PDFs, unlesbare DOCX
        raise HTTPException(422, f"Die Datei konnte nicht gelesen werden: {fehler}")
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


@app.middleware("http")
async def nicht_zwischenspeichern(anfrage, weiter):
    """Verhindert, dass der Browser eine alte Programmversion ausliefert.

    Bei einem lokalen Werkzeug bringt Caching nichts und kostet nur Nerven —
    nach einem Update sonst stundenlang die alte Oberfläche.
    """
    antwort = await weiter(anfrage)
    antwort.headers["Cache-Control"] = "no-store, must-revalidate"
    return antwort


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
