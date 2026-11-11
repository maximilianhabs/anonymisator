"""Ordner-Modus (opt-in): Datei in den Eingang legen, anonymisiertes Ergebnis im Ausgang.

    .venv/bin/python -m app.ordner --eingang <Ordner> --ausgang <Ordner>

Das Web-Werkzeug bleibt unverändert und ist weiterhin der Weg mit Review. Dieser
Modus arbeitet bewusst OHNE Review und ersetzt ihn nicht: Weil niemand
mitliest, werden alle erkannten Gruppen ersetzt (auch unbelegte) und jedes
Ergebnis durchläuft eine Endkontrolle. Was sie nicht sicher besteht, wird nicht
ausgegeben, sondern mitsamt dem Original zurückgehalten — dann bearbeitet der
Nutzer es von Hand im Web-Werkzeug.

Zustand ist der Ordner, nicht eine Datenbank:

    <eingang>/Erledigt/        Originale, deren Ergebnis im Ausgang liegt
    <eingang>/Zurueckgehalten/ Originale, die die Endkontrolle nicht bestanden
    <eingang>/protokoll.csv    eine Zeile je Datei, ohne Namen und ohne Inhalt
    <ausgang>/dokument_NNNN.txt

Das Protokoll und die Konsole nennen nie den Originaldateinamen, Klartext,
Fundtexte oder Ausnahmemeldungen. Der Dateiname enthält bei Arztbriefen oft den
Patientennamen; eine Zuordnung Original zu Ausgabe wäre selbst ein Schlüssel
zur Person. Es gibt keine Netzwerkzugriffe und nichts wird ausserhalb von
Eingang und Ausgang geschrieben. Gelöscht wird nie etwas.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import os
import re
import signal
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from . import config, detect, export, extract, stufen

REPO = Path(__file__).resolve().parent.parent

ENDUNGEN = (".pdf", ".docx", ".txt")
ERLEDIGT = "Erledigt"
ZURUECKGEHALTEN = "Zurueckgehalten"
PROTOKOLL = "protokoll.csv"

PROTOKOLL_KOPF = [
    "zeitstempel", "ergebnis", "ausgabedatei", "quelle", "seiten", "zeichen",
    "gruppen", "fundstellen", "unbelegt", "stufe", "gruende", "version",
]

# Ordner, in denen macOS Dateien gern in die iCloud spiegelt. Ein Original,
# das dort liegt, verlässt womöglich den Rechner, bevor es verarbeitet ist.
_SYNC_ORDNER = ("Library/Mobile Documents", "Desktop", "Documents")


# --------------------------------------------------------------------------
# Startprüfung
# --------------------------------------------------------------------------

def _liegt_in(pfad: Path, ordner: Path) -> bool:
    return pfad == ordner or ordner in pfad.parents


def pruefe_start(eingang: Path, ausgang: Path) -> tuple[list[str], list[str]]:
    """Gibt (Fehler, Warnungen) zurück. Legt nichts an.

    Echte Dokumente dürfen das öffentliche Repository nie erreichen, deshalb
    ist jeder Pfad im Repo-Verzeichnis ein Abbruchgrund — auch der Ausgang,
    denn auch anonymisierte Ausgaben sind dort fehl am Platz.
    """
    fehler: list[str] = []
    warnungen: list[str] = []
    ein = eingang.expanduser().resolve()
    aus = ausgang.expanduser().resolve()

    if not ein.is_dir():
        fehler.append("Der Eingangsordner existiert nicht (oder ist kein Ordner).")
    if aus.exists() and not aus.is_dir():
        fehler.append("Der Ausgang existiert, ist aber kein Ordner.")
    if ein == aus:
        fehler.append("Eingang und Ausgang sind derselbe Ordner.")
    elif _liegt_in(ein, aus) or _liegt_in(aus, ein):
        fehler.append("Eingang und Ausgang dürfen nicht ineinander liegen.")
    if _liegt_in(ein, REPO) or _liegt_in(aus, REPO):
        fehler.append(
            "Ein Pfad liegt im Repo-Verzeichnis. Echte Dokumente dürfen nie "
            "ins Repo (öffentlich, die Historie behält jede Datei).")

    heim = Path.home().resolve()
    for teil in _SYNC_ORDNER:
        if _liegt_in(ein, heim / teil):
            warnungen.append(
                f"Der Eingang liegt unter ~/{teil}. Dort kann die iCloud die "
                "Originale synchronisieren. Besser ein Ordner ausserhalb.")
            break
    return fehler, warnungen


# --------------------------------------------------------------------------
# Endkontrolle
# --------------------------------------------------------------------------

# Platzhalter wie [PATIENT_A], [ADRESSE_3], [GESCHWÄRZT_1].
_PLATZHALTER = re.compile(r"\[[A-ZÄÖÜ]{2,}_[A-Z0-9]{1,3}\]")

# Titel und Anreden: Namenswörter, die in jedem Brief vorkommen und für sich
# keine Person verraten.
_TITEL = {
    "dr", "prof", "med", "habil", "pd", "dipl", "ing", "rer", "nat", "phil",
    "univ", "apl", "herr", "herrn", "frau", "hr", "fr", "doktor",
    "kollege", "kollegin",
}

_PERSONEN = ("PATIENT", "ARZT", "PERSON")

# Typen, deren Originaltext nach dem Ersetzen nirgends mehr stehen darf. Es
# sind die Kategorien, die eine Person oder einen Ort bezeichnen. Bewusst NICHT
# geprüft: ZAHL, ALTER, ZEITSPANNE, JAHRESZAHL, BETRAG, GESCHLECHT und
# DIAGNOSECODE. Ihr Fundtext ("120", "Patientin", "G40.1") taucht in
# legitimem Fachtext an Stellen auf, die die Erkennung zu Recht nicht anfasst
# (Messwert mit Einheit, Dosis, Wort im Kompositum); der Nutzen wäre ein Strom
# von Fehlalarmen, die jeden Lauf zurückhielten. Für DATUM gilt das nicht:
# ein vollständiges Datum ist selbst ein Merkmal und wird geprüft.
_KLARTEXT_TYPEN = {
    "ORGANISATION", "ADRESSE", "ORT", "GEBURTSDATUM", "DATUM", "URL",
    *stufen._DIREKT,
}

# Typen, bei denen eine erneute Erkennung im Ergebnis Alarm schlägt. Nur dort,
# wo die Stufe den Typ vollständig ersetzt: bei "initialen", "jahrgang",
# "dekade" oder "nur_ort" findet die Erkennung die bewusst stehen gebliebene
# Form ("E. H.", "Jahrgang 1958", "94032 Passau") wieder — das wäre ein
# Fehlalarm in jedem Lauf. DATUM fehlt ganz: auf der Standardstufe bleibt ein
# verschobenes Datum ein Datum, die Erkennung schlüge strukturell immer an.
# ZAHL, ORT und ORGANISATION fehlen, weil die Erkennung dort auch in sauberem
# Text unbelegt anschlägt; sie sind über rest_klartext abgedeckt.
_ERKENNUNG_TYPEN = {
    "PATIENT", "ARZT", "GEBURTSDATUM", "TELEFON", "EMAIL", "ADRESSE",
    *stufen._DIREKT,
}


def _platzhalter_maske(text: str) -> list[bool]:
    maske = [False] * len(text)
    for treffer in _PLATZHALTER.finditer(text):
        for i in range(treffer.start(), treffer.end()):
            maske[i] = True
    return maske


def _namenswoerter(name: str) -> list[str]:
    """Grossgeschriebene Wörter ab drei Buchstaben, ohne Titel und Anreden."""
    return [w for w in re.findall(r"[^\W\d_]+", name)
            if len(w) >= 3 and w[0].isupper() and w.lower() not in _TITEL]


def _muster(begriff: str) -> re.Pattern:
    """Wortgrenzen, Gross/Klein egal, Leerraum im Begriff beliebig lang."""
    teile = [re.escape(t) for t in begriff.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(teile) + r"(?!\w)", re.IGNORECASE)


def rest_klartext(gruppen: list[detect.Gruppe], ergebnis: str, stufe: str) -> bool:
    """Wahr, wenn ein ersetzter Originaltext im Ergebnis noch vorkommt.

    Fundtexte nur für Behandlung "ersetzen": bei initialen, jahrgang, dekade,
    nur_ort, verschoben und gerundet bleibt ein Teil des Originals gewollt
    stehen und dürfte sonst nicht als Rest zählen. Personen werden zusätzlich
    (und auch bei "initialen") wortweise geprüft — von "Elisabeth Hartmann"
    darf weder Vor- noch Nachname bleiben, "E. H." enthält aber kein Wort ab
    drei Buchstaben und löst nichts aus. Platzhalter werden vor der Suche
    unkenntlich gemacht, damit ein Fundtext wie "ORT" nicht im Platzhalter
    "[ORT_1]" gefunden wird.
    """
    sichtbar = list(ergebnis)
    for i, versteckt in enumerate(_platzhalter_maske(ergebnis)):
        if versteckt:
            sichtbar[i] = "\x00"
    text = "".join(sichtbar)

    begriffe: set[str] = set()
    for gruppe in gruppen:
        art = stufen.behandlung_von(stufe, gruppe.typ)
        if gruppe.typ in _PERSONEN:
            if art in ("ersetzen", "initialen"):
                for fund in gruppe.funde:
                    begriffe.update(_namenswoerter(fund.text))
        elif art == "ersetzen" and gruppe.typ in _KLARTEXT_TYPEN:
            begriffe.update(f.text.strip() for f in gruppe.funde
                            if len(f.text.strip()) >= 3)
    return any(_muster(b).search(text) for b in begriffe)


def rest_erkennung(ergebnis: str, stufe: str) -> bool:
    """Wahr, wenn die Erkennung im fertigen Text noch direkte Identifikatoren findet.

    Läuft auf dem Ergebnistext ohne Kopfzeile (die erzeugt export.als_txt
    selbst, sie enthält nur das Tagesdatum). Funde, die in einem Platzhalter
    liegen, zählen nicht: das Sprachmodell liest "ADRESSE_3" gern als Namen.
    Von einem Fund, der einen Platzhalter nur streift ("ARZT_1 Müller"), zählt
    der Teil ausserhalb.
    """
    maske = _platzhalter_maske(ergebnis)
    for gruppe in detect.analysiere(ergebnis):
        if (gruppe.typ not in _ERKENNUNG_TYPEN or not gruppe.sicher
                or stufen.behandlung_von(stufe, gruppe.typ) != "ersetzen"):
            continue
        for fund in gruppe.funde:
            rest = "".join(c for i, c in enumerate(ergebnis[fund.start:fund.end],
                                                   fund.start) if not maske[i])
            # Steht der Name nicht mehr da, weicht die Arzt-Regel auf den
            # letzten Titel aus: aus "PROF. DR. MED. [ARZT_1]" wird ein Arzt
            # namens "MED". Was nur aus Titeln besteht, ist kein Rest.
            if any(w.lower() not in _TITEL for w in re.findall(r"\w{3,}", rest)):
                return True
    return False


def namens_nachlauf(gruppen: list[detect.Gruppe], ersetzungen: list[dict],
                    ergebnis: str) -> tuple[str, int]:
    """Ersetzt stehen gebliebene Vorkommen erkannter Namenswörter.

    Die Erkennung markiert ein Wort mitunter nur an einer Stelle als Person
    und lässt dasselbe Wort woanders stehen. Im Web-Werkzeug sieht das der
    Prüfende; hier prüft niemand, also gilt: einmal Person, überall Person.
    Das trifft auch Fehlalarme (ein Fachwort, das das Sprachmodell für einen
    Namen hielt) und kostet dann Lesbarkeit — der sichere Fehler. Gibt den
    neuen Text und die Zahl der nachträglichen Ersetzungen zurück.
    """
    label_von = {e["start"]: e["label"] for e in ersetzungen}
    anzahl = 0
    for gruppe in gruppen:
        if gruppe.typ not in _PERSONEN or not gruppe.funde:
            continue
        label = label_von.get(gruppe.funde[0].start)
        if not label or not _PLATZHALTER.fullmatch(label):
            continue  # Initialen o. Ä.: kein Platzhalter zum Einsetzen
        for wort in {w for f in gruppe.funde for w in _namenswoerter(f.text)}:
            maske = _platzhalter_maske(ergebnis)
            teile, ende = [], 0
            for treffer in _muster(wort).finditer(ergebnis):
                if any(maske[treffer.start():treffer.end()]):
                    continue
                teile += [ergebnis[ende:treffer.start()], label]
                ende = treffer.end()
                anzahl += 1
            ergebnis = "".join(teile) + ergebnis[ende:]
    return ergebnis, anzahl


def endkontrolle(gruppen: list[detect.Gruppe], ergebnis: str, stufe: str) -> list[str]:
    """Gründe als kurze Codes; leer heisst bestanden (Prüfungen a bis c)."""
    gruende = []
    if rest_klartext(gruppen, ergebnis, stufe):
        gruende.append("rest_klartext")
    if rest_erkennung(ergebnis, stufe):
        gruende.append("rest_erkennung")
    if not any(g.typ == "PATIENT" for g in gruppen):
        gruende.append("kein_patient")
    return gruende


# --------------------------------------------------------------------------
# Verarbeitung einer Datei (im Arbeitsspeicher)
# --------------------------------------------------------------------------

@dataclass
class Ergebnis:
    gruende: list[str] = field(default_factory=list)
    text: str = ""
    quelle: str = ""
    seiten: int = 0
    zeichen: int = 0
    gruppen: int = 0
    fundstellen: int = 0
    unbelegt: int = 0
    nachlauf: int = 0  # nachträglich ersetzte Vorkommen erkannter Namenswörter
    fehlertyp: str = ""  # nur der Typname einer Ausnahme, nie ihre Meldung

    @property
    def frei(self) -> bool:
        return not self.gruende


def verarbeite(dateiname: str, daten: bytes, stufe: str,
               ocr_freigeben: bool = False) -> Ergebnis:
    erg = Ergebnis()
    if len(daten) > config.MAX_UPLOAD_MB * 1024 * 1024:
        erg.gruende.append("lesefehler")
        return erg
    try:
        auszug = extract.aus_upload(dateiname, daten)
    except Exception as fehler:
        # Die Meldung kann Inhalt enthalten; nur der Typ wird gemerkt.
        erg.gruende.append("lesefehler")
        erg.fehlertyp = type(fehler).__name__
        return erg

    erg.quelle, erg.seiten, erg.zeichen = auszug.quelle, auszug.seiten, len(auszug.text)
    if auszug.quelle in ("pdf-ocr", "pdf-gemischt") and not ocr_freigeben:
        erg.gruende.append("ocr")
    if any("kein Text gewonnen" in h for h in auszug.hinweise):
        erg.gruende.append("seite_ohne_text")
    if len(auszug.text.strip()) < config.ORDNER_MIN_ZEICHEN:
        erg.gruende.append("kein_text")
        return erg

    try:
        gruppen = detect.analysiere(auszug.text)
        stufen.formen_berechnen(gruppen)
        # Kein Review, also im Zweifel ersetzen: auch unbelegte Gruppen.
        ersetzungen = stufen.ersetzungen_fuer(gruppen, stufe, nur_aktive=False)
        ergebnis = export.ersetze(auszug.text, ersetzungen)
        ergebnis, erg.nachlauf = namens_nachlauf(gruppen, ersetzungen, ergebnis)
        erg.gruppen = len(gruppen)
        erg.fundstellen = sum(len(g.funde) for g in gruppen)
        erg.unbelegt = sum(1 for g in gruppen if not g.sicher)
        erg.gruende += endkontrolle(gruppen, ergebnis, stufe)
    except Exception as fehler:
        erg.gruende.append("analysefehler")
        erg.fehlertyp = type(fehler).__name__
        return erg

    erg.text = ergebnis
    return erg


# --------------------------------------------------------------------------
# Ablage
# --------------------------------------------------------------------------

def _programmversion() -> str:
    """Version aus CITATION.cff (pyproject.toml führt sie nicht nach)."""
    try:
        quelle = (REPO / "CITATION.cff").read_text(encoding="utf-8")
        treffer = re.search(r'^version:\s*"?([\w.\-+]+)"?\s*$', quelle, re.MULTILINE)
        return treffer.group(1) if treffer else "unbekannt"
    except OSError:
        return "unbekannt"


def _naechste_nummer(ausgang: Path) -> int:
    nummern = [int(m.group(1)) for p in ausgang.iterdir()
               if (m := re.fullmatch(r"dokument_(\d{4,})\.txt", p.name))]
    return max(nummern, default=0) + 1


def _atomar_schreiben(ziel: Path, inhalt: bytes) -> None:
    """Temporäre Datei im Ausgang, dann os.replace: nie eine halbe Ausgabe."""
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=ziel.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(inhalt)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ziel)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _verschieben(quelle: Path, zielordner: Path) -> None:
    """Verschiebt ohne Überschreiben; bei Namensgleichheit _2, _3 …"""
    zielordner.mkdir(exist_ok=True)
    ziel = zielordner / quelle.name
    n = 2
    while ziel.exists():
        ziel = zielordner / f"{quelle.stem}_{n}{quelle.suffix}"
        n += 1
    os.replace(quelle, ziel)


def _protokollieren(eingang: Path, zeile: list) -> None:
    pfad = eingang / PROTOKOLL
    neu = not pfad.exists()
    with pfad.open("a", newline="", encoding="utf-8") as f:
        schreiber = csv.writer(f)
        if neu:
            schreiber.writerow(PROTOKOLL_KOPF)
        schreiber.writerow(zeile)


@dataclass
class Einstellungen:
    eingang: Path
    ausgang: Path
    stufe: str = "streng"
    ocr_freigeben: bool = False


def erledige(datei: Path, einst: Einstellungen, laufnummer: int) -> Ergebnis:
    """Verarbeitet eine Datei und legt sie ab. Wirft nur bei Ablagefehlern."""
    erg = verarbeite(datei.name, datei.read_bytes(), einst.stufe, einst.ocr_freigeben)
    ausgabe = ""
    if erg.frei:
        einst.ausgang.mkdir(parents=True, exist_ok=True)
        ausgabe = f"dokument_{_naechste_nummer(einst.ausgang):04d}.txt"
        _atomar_schreiben(
            einst.ausgang / ausgabe,
            export.als_txt(erg.text, mit_kopfzeile=True, stufe=einst.stufe))
        _verschieben(datei, einst.eingang / ERLEDIGT)
    else:
        _verschieben(datei, einst.eingang / ZURUECKGEHALTEN)

    _protokollieren(einst.eingang, [
        datetime.now(tz=UTC).astimezone().isoformat(timespec="seconds"),
        "frei" if erg.frei else "zurueckgehalten", ausgabe, erg.quelle,
        erg.seiten, erg.zeichen, erg.gruppen, erg.fundstellen, erg.unbelegt,
        einst.stufe, ";".join(erg.gruende), _programmversion(),
    ])
    # Konsole: nur Laufnummer, Ergebnis, Codes und Zahlen.
    zusatz = f" ({erg.fehlertyp})" if erg.fehlertyp else ""
    print(f"[{laufnummer}] {'frei' if erg.frei else 'zurückgehalten'}"
          f"{' ' + ausgabe if ausgabe else ''} | quelle={erg.quelle or '-'} "
          f"seiten={erg.seiten} zeichen={erg.zeichen} gruppen={erg.gruppen} "
          f"fundstellen={erg.fundstellen} unbelegt={erg.unbelegt} "
          f"nachlauf={erg.nachlauf} "
          f"gründe={';'.join(erg.gruende) or '-'}{zusatz}", flush=True)
    return erg


# --------------------------------------------------------------------------
# Abfrage des Eingangs
# --------------------------------------------------------------------------

def _messen(eingang: Path) -> tuple[dict[Path, tuple[int, int]], int]:
    """Grösse und mtime aller regulären, sichtbaren Dateien direkt im Eingang.

    Zweiter Wert: Zahl der Dateien mit unbekannter Endung (bleiben liegen).
    Unterordner, Verknüpfungen und versteckte Dateien zählen nicht.
    """
    bekannt: dict[Path, tuple[int, int]] = {}
    unbekannt = 0
    for p in eingang.iterdir():
        if p.name.startswith(".") or p.is_symlink() or not p.is_file():
            continue
        if p.name == PROTOKOLL:
            continue
        if p.suffix.lower() not in ENDUNGEN:
            unbekannt += 1
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        bekannt[p] = (st.st_size, st.st_mtime_ns)
    return bekannt, unbekannt


def durchlauf(einst: Einstellungen, vorher: dict[Path, tuple[int, int]],
              laufnummer: int, halt: threading.Event | None = None,
              ) -> tuple[dict[Path, tuple[int, int]], int, int, int]:
    """Eine Abfrage. Gibt (Messung, verarbeitet, unbekannt, laufnummer) zurück.

    Eine Datei wird erst angefasst, wenn Grösse und mtime gegenüber der
    vorherigen Messung gleich geblieben sind — sonst läse man eine halb
    kopierte Datei.
    """
    jetzt, unbekannt = _messen(einst.eingang)
    verarbeitet = 0
    for datei, signatur in sorted(jetzt.items()):
        if halt is not None and halt.is_set():
            break
        if vorher.get(datei) != signatur:
            continue
        laufnummer += 1
        try:
            erledige(datei, einst, laufnummer)
            verarbeitet += 1
        except OSError as fehler:
            # Ablage gescheitert: nur der Typ, nie Pfad oder Meldung. Die
            # Messung bleibt unverändert, der nächste Lauf versucht es erneut.
            print(f"[{laufnummer}] Ablagefehler ({type(fehler).__name__}); "
                  "Datei bleibt liegen.", flush=True)
    return jetzt, verarbeitet, unbekannt, laufnummer


# --------------------------------------------------------------------------
# Kommandozeile
# --------------------------------------------------------------------------

def _argumente(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m app.ordner",
        description="Ordner-Modus: anonymisiert Dateien aus dem Eingang ohne "
                    "Rückfrage. Ersetzt NICHT den Review im Web-Werkzeug.")
    p.add_argument("--eingang", default=config.ORDNER_EINGANG,
                   help="Eingangsordner (oder ANON_EINGANG), Pflicht")
    p.add_argument("--ausgang", default=config.ORDNER_AUSGANG,
                   help="Ausgangsordner (oder ANON_AUSGANG), Pflicht")
    p.add_argument("--stufe", default=config.ORDNER_STUFE,
                   help="leicht | standard | streng (oder ANON_ORDNER_STUFE), "
                        "Standard streng")
    p.add_argument("--einmal", action="store_true",
                   help="einmal durchlaufen und beenden")
    p.add_argument("--ocr-freigeben", action="store_true",
                   help="auch per OCR gelesene Dokumente ausgeben (Standard: "
                        "zurückhalten, OCR-Fehler sind häufigste Lücke)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _argumente(argv)
    if not args.eingang or not args.ausgang:
        print("Eingang und Ausgang sind Pflicht (--eingang/--ausgang oder "
              "ANON_EINGANG/ANON_AUSGANG).", file=sys.stderr)
        return 2
    stufe = args.stufe.strip().lower()
    if stufe not in stufen.STUFEN:
        print(f"Unbekannte Stufe. Erlaubt: {', '.join(stufen.STUFEN_REIHENFOLGE)}.",
              file=sys.stderr)
        return 2

    fehler, warnungen = pruefe_start(Path(args.eingang), Path(args.ausgang))
    for w in warnungen:
        print(f"Warnung: {w}", file=sys.stderr)
    if fehler:
        for f in fehler:
            print(f"Abbruch: {f}", file=sys.stderr)
        return 2

    einst = Einstellungen(
        eingang=Path(args.eingang).expanduser().resolve(),
        ausgang=Path(args.ausgang).expanduser().resolve(),
        stufe=stufe, ocr_freigeben=args.ocr_freigeben)
    einst.ausgang.mkdir(parents=True, exist_ok=True)

    laufnummer = 0
    if args.einmal:
        # Zwei Messungen im Abstand von einer Sekunde: was dazwischen noch
        # wächst, wird in diesem Lauf nicht angefasst.
        erste, _ = _messen(einst.eingang)
        time.sleep(1)
        _, verarbeitet, unbekannt, laufnummer = durchlauf(einst, erste, laufnummer)
        if unbekannt:
            print(f"{unbekannt} Datei(en) mit unbekannter Endung bleiben liegen.")
        print(f"Fertig: {verarbeitet} Datei(en) verarbeitet.")
        return 0

    halt = threading.Event()

    def _beenden(_signum, _frame):
        # Die laufende Datei wird noch abgelegt; ein zweites Strg-C bricht hart ab.
        halt.set()
        signal.signal(signal.SIGINT, signal.default_int_handler)

    signal.signal(signal.SIGINT, _beenden)
    print(f"Ordner-Modus, Stufe {stufe}. Beenden mit Strg-C. "
          "Ohne Review: Ausgaben vor Weitergabe stichprobenartig lesen.")
    messung: dict[Path, tuple[int, int]] = {}
    gemeldet = 0
    while not halt.is_set():
        messung, _, unbekannt, laufnummer = durchlauf(einst, messung, laufnummer, halt)
        if unbekannt != gemeldet:
            gemeldet = unbekannt
            if unbekannt:
                print(f"{unbekannt} Datei(en) mit unbekannter Endung bleiben liegen.")
        halt.wait(config.ORDNER_ABFRAGE_SEKUNDEN)
    print("Beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
