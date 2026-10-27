"""Anonymisierungsstufen: was mit einem Fund geschieht, nicht ob er gefunden wird.

Die Erkennung läuft immer auf voller Schärfe. Erst hier entscheidet sich pro
Kategorie und Stufe, welche Behandlung ein Fund erfährt — behalten, auf
Initialen kürzen, vergröbern, verschieben oder ersetzen.

Weil alle Darstellungen vorab berechnet und mitgeliefert werden, kostet ein
Stufenwechsel in der Oberfläche keine neue Analyse: es wird nur eine andere
Spalte gelesen.
"""

from __future__ import annotations

import re
import secrets
from datetime import date, timedelta

from .detect import Gruppe

# --------------------------------------------------------------------------
# Behandlungen
# --------------------------------------------------------------------------
# behalten   — Fund bleibt unverändert im Text
# initialen  — "Elisabeth Hartmann" wird zu "E. H."
# jahrgang   — Datum wird zu "Jahrgang 1958"
# dekade     — Datum/Alter wird zur Lebensdekade "60–69 J."
# verschoben — Datum um einen dokumentweit einheitlichen Versatz verschoben
# nur_ort    — Anschrift behält Ort und Postleitzahl, verliert die Strasse
# gerundet   — Geldbetrag auf zwei signifikante Stellen, "rund 1.200 €"
# ersetzen   — Fund wird durch das Pseudonym ersetzt

STUFEN_REIHENFOLGE = ["leicht", "standard", "streng"]

# "erlaeuterung" beschreibt den Mechanismus, nicht das Ergebnis. Bewusst
# keine Formulierung wie "gilt als anonymisiert nach DSGVO" — das wäre eine
# Rechtsaussage, die eine automatische Erkennung nicht zusichern kann (siehe
# Haftungsabschnitt im README). Beschrieben wird, was mit welcher Kategorie
# geschieht; die Einordnung bleibt der lesenden Person überlassen.
STUFEN_INFO = {
    "leicht": {
        "titel": "Leicht",
        "untertitel": "Pseudonymisiert",
        "zweck": "Interne Fallbesprechung, Übergabe im Haus.",
        "erlaeuterung": (
            "Namen werden zu Initialen, das Geburtsdatum zum Jahrgang. "
            "Einrichtung, Ort und alle übrigen Daten bleiben unverändert "
            "stehen."
        ),
        "warnung": (
            "Dies ist keine Anonymisierung. Initialen, Geburtsjahr, "
            "Einrichtung und Behandlungszeitraum lassen zusammen regelmässig "
            "einen Rückschluss auf die Person zu. Das Ergebnis bleibt ein "
            "personenbezogenes Datum und ist entsprechend zu behandeln."
        ),
    },
    "standard": {
        "titel": "Standard",
        "untertitel": "Anonymisiert",
        "zweck": "Lehre, Fallvorstellung, Weitergabe ausser Haus.",
        "erlaeuterung": (
            "Namen, Einrichtungen und Anschriften werden ersetzt. Geburtsdatum "
            "und Alter werden auf die Dekade vergröbert, alle übrigen Daten um "
            "denselben zufälligen Zeitraum verschoben — der Abstand zwischen "
            "zwei Terminen bleibt dadurch ablesbar. Geschlecht und "
            "Diagnosecodes (ICD-10, OPS, DRG) werden ebenfalls ersetzt, der "
            "Diagnosetext selbst bleibt stehen. Ein blosser Ortsname ohne "
            "Adresse bleibt stehen."
        ),
        "warnung": None,
    },
    "streng": {
        "titel": "Streng",
        "untertitel": "Anonymisiert, ohne Zeitbezug",
        "zweck": "Publikation, öffentliche Beispiele.",
        "erlaeuterung": (
            "Zusätzlich zur Standardstufe: auch blosse Ortsnamen, das "
            "Geburtsdatum selbst und Zahlen ohne physikalische Einheit "
            "(Durchwahl, Zimmer, Kennung) werden ersetzt. Daten verlieren "
            "den gemeinsamen Zeitversatz — auch der Abstand zwischen zwei "
            "Terminen lässt sich nicht mehr ablesen."
        ),
        "warnung": None,
    },
}

# Direkte Identifikatoren. Sie tragen keine inhaltliche Information und werden
# auf jeder Stufe ersetzt — eine "leicht anonymisierte" Versicherten- oder
# Kontonummer ergibt keinen Sinn. Gilt für Arztbriefe wie für Rechnungen,
# Verträge und Gutachten gleichermassen.
_DIREKT = [
    "VERSICHERTENNR", "SOZIALVERSNR", "FALLNUMMER", "AKTENZEICHEN",
    "IBAN", "KONTONR", "STEUERNR", "RECHNUNGSNR", "KUNDENNR",
    "AUSWEISNR", "KFZ", "HANDELSREGISTER",
    "TELEFON", "EMAIL", "MANUELL",
]

STUFEN: dict[str, dict[str, str]] = {
    "leicht": {
        "PATIENT": "initialen", "ARZT": "initialen", "PERSON": "initialen",
        "ORGANISATION": "behalten", "ADRESSE": "nur_ort", "ORT": "behalten",
        "GEBURTSDATUM": "jahrgang", "DATUM": "behalten",
        "ALTER": "behalten", "ZEITSPANNE": "behalten", "JAHRESZAHL": "behalten",
        "BETRAG": "behalten", "URL": "behalten", "ZAHL": "behalten",
        # Für die interne Übergabe im Haus ("Leicht") bleiben Geschlecht und
        # Diagnosecode stehen — beides ist dort gewollter Fachinhalt, kein
        # Merkmal, das für sich genommen die Anonymität gefährdet. Erst ab
        # Standard, wo das Dokument das Haus verlässt, greift die
        # Kombinationsüberlegung: Geschlecht + Alter + Diagnose + Zeitpunkt
        # kann eine seltene Konstellation eindeutig machen.
        "GESCHLECHT": "behalten", "DIAGNOSECODE": "behalten",
    },
    "standard": {
        "PATIENT": "ersetzen", "ARZT": "ersetzen", "PERSON": "ersetzen",
        "ORGANISATION": "ersetzen", "ADRESSE": "ersetzen", "ORT": "behalten",
        "GEBURTSDATUM": "dekade", "DATUM": "verschoben",
        "GESCHLECHT": "ersetzen", "DIAGNOSECODE": "ersetzen",
        # Bewusst ebenfalls vergröbert: eine ausgeschriebene Altersangabe im
        # Text würde das zur Dekade vergröberte Geburtsdatum sonst aushebeln.
        "ALTER": "dekade",
        # Relative Zeitspannen ("seit 3 Jahren") bleiben. Eine nackte
        # Jahreszahl wird dagegen mit demselben Versatz verschoben wie die
        # vollen Daten: "seit 2019" neben einem verschobenen Datum 2024
        # liesse sonst den Abstand und damit den Versatz erkennen.
        "ZEITSPANNE": "behalten", "JAHRESZAHL": "verschoben",
        # Gerundet statt ersetzt: eine Rechnung ohne jede Grössenordnung ist
        # wertlos, eine centgenaue Summe zu einem Datum dagegen wiedererkennbar.
        "BETRAG": "gerundet",
        # Zahlen ohne Einheit bleiben hier noch stehen — erst die strenge
        # Stufe räumt sie weg. In der Standardstufe wäre der Verlust an
        # Lesbarkeit grösser als der Gewinn an Schutz.
        "ZAHL": "behalten",
        "URL": "ersetzen",
    },
    "streng": {
        "PATIENT": "ersetzen", "ARZT": "ersetzen", "PERSON": "ersetzen",
        "ORGANISATION": "ersetzen", "ADRESSE": "ersetzen", "ORT": "ersetzen",
        "GEBURTSDATUM": "ersetzen", "DATUM": "ersetzen",
        "ALTER": "ersetzen", "ZEITSPANNE": "ersetzen", "JAHRESZAHL": "ersetzen",
        "BETRAG": "ersetzen", "URL": "ersetzen",
        "GESCHLECHT": "ersetzen", "DIAGNOSECODE": "ersetzen",
        # Jede Zahl ohne physikalische Einheit: Durchwahl, Piepser, Zimmer,
        # Bett, Kennungen ohne Beschriftung. Messwerte bleiben, weil dort
        # eine Einheit folgt.
        "ZAHL": "ersetzen",
    },
}

for _stufe in STUFEN.values():
    for _kategorie in _DIREKT:
        _stufe[_kategorie] = "ersetzen"


# --------------------------------------------------------------------------
# Datum lesen und schreiben
# --------------------------------------------------------------------------

_MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}


def datum_lesen(text: str) -> date | None:
    """Liest die im deutschen Schriftverkehr üblichen Datumsformate.

    Sucht im Text statt ihn vollständig abzugleichen, weil ein Geburtsdatum
    als "geb. 22.07.1958" gefunden wird — mitsamt Auslöser.
    """
    wert = text.strip()

    treffer = re.search(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{2,4})\b", wert)
    if treffer:
        tag, monat, jahr = (int(g) for g in treffer.groups())
        if jahr < 100:
            # Zweistellige Jahre: 30 als Grenze, damit Geburtsjahre wie 58
            # ins letzte Jahrhundert fallen und nicht in die Zukunft.
            jahr += 2000 if jahr <= 30 else 1900
        return _sicher(jahr, monat, tag)

    treffer = re.search(r"(\d{1,2})\.\s?([A-Za-zÄÖÜäöüß]+)\s+(\d{4})\b", wert)
    if treffer and treffer.group(2).lower() in _MONATE:
        return _sicher(int(treffer.group(3)), _MONATE[treffer.group(2).lower()],
                       int(treffer.group(1)))

    treffer = re.search(r"(\d{4})-(\d{2})-(\d{2})\b", wert)
    if treffer:
        return _sicher(*(int(g) for g in treffer.groups()))

    return None


def _sicher(jahr: int, monat: int, tag: int) -> date | None:
    try:
        return date(jahr, monat, tag)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Unvollständige Daten verschieben
# --------------------------------------------------------------------------

_MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                "August", "September", "Oktober", "November", "Dezember"]
_JAHRESZEIT_MONAT = {"frühjahr": 4, "frühling": 4, "sommer": 7, "herbst": 10,
                     "winter": 1}


def _jahreszeit(monat: int) -> str:
    if 3 <= monat <= 5:
        return "Frühjahr"
    if 6 <= monat <= 8:
        return "Sommer"
    if 9 <= monat <= 11:
        return "Herbst"
    return "Winter"


def _kontextdatum(start: int, tag: int, monat: int, voll: list[tuple[int, date]],
                  stichtag: date | None) -> date | None:
    """Ergänzt Tag und Monat ohne Jahr um das Jahr aus der Nachbarschaft.

    Aus "vom 03.03. bis 12.03.2026" wird für das erste Datum das Jahr des
    folgenden vollen Datums genommen — und eines abgezogen, falls das
    ergänzte Datum sonst hinter dem Bezug läge. Nie das aktuelle Jahr:
    ein Brief von 2019 würde sonst um sieben Jahre danebenliegen.
    """
    spaeter = [d for s, d in voll if s > start and s - start <= 80]
    if spaeter:
        bezug = spaeter[0]
        kandidat = _sicher(bezug.year, monat, tag)
        if kandidat and kandidat > bezug:
            kandidat = _sicher(bezug.year - 1, monat, tag)
        return kandidat
    frueher = [d for s, d in voll if s < start and start - s <= 200]
    if frueher:
        bezug = frueher[-1]
        kandidat = _sicher(bezug.year, monat, tag)
        if kandidat and kandidat < bezug:
            kandidat = _sicher(bezug.year + 1, monat, tag)
        return kandidat
    if stichtag is not None:
        kandidat = _sicher(stichtag.year, monat, tag)
        if kandidat and kandidat > stichtag:
            kandidat = _sicher(stichtag.year - 1, monat, tag)
        return kandidat
    return None


def teildatum_verschieben(fund_text: str, start: int, versatz: timedelta,
                          voll: list[tuple[int, date]],
                          stichtag: date | None) -> str | None:
    """Verschiebt Jahr, Monat+Jahr, Jahreszeit+Jahr und Tag+Monat.

    Bei grober Angabe zählt die Mitte des Zeitraums (15. des Monats, 1. Juli
    für ein ganzes Jahr). Das ist eine Näherung: bei einem Versatz von
    weniger als einem Jahr kann eine reine Jahreszahl um ein Jahr von dem
    abweichen, was die vollen Daten im selben Dokument nahelegen. Die
    Reihenfolge bleibt in aller Regel erhalten, der Abstand auf den Tag
    genau nur bei vollständigen Daten.
    """
    text = fund_text.strip()

    treffer = re.fullmatch(r"([A-Za-zÄÖÜäöüß]+)\s+((?:19|20)\d{2})", text)
    if treffer:
        name, jahr = treffer.group(1).lower(), int(treffer.group(2))
        if name in _MONATE:
            mitte = _sicher(jahr, _MONATE[name], 15)
            if mitte is None:
                return None
            neu = mitte + versatz
            return f"{_MONATSNAMEN[neu.month - 1]} {neu.year}"
        if name in _JAHRESZEIT_MONAT:
            mitte = _sicher(jahr, _JAHRESZEIT_MONAT[name], 15)
            if mitte is None:
                return None
            neu = mitte + versatz
            return f"{_jahreszeit(neu.month)} {neu.year}"
        return None

    treffer = re.fullmatch(r"(0[1-9]|1[0-2])([/.])((?:19|20)\d{2})", text)
    if treffer:
        mitte = _sicher(int(treffer.group(3)), int(treffer.group(1)), 15)
        if mitte is None:
            return None
        neu = mitte + versatz
        return f"{neu.month:02d}{treffer.group(2)}{neu.year}"

    treffer = re.fullmatch(r"(?:19|20)\d{2}", text)
    if treffer:
        return str((date(int(text), 7, 1) + versatz).year)

    treffer = re.fullmatch(r"(\d{1,2})\.\s?(\d{1,2})\.?", text)
    if treffer:
        tag_text, monat_text = treffer.group(1), treffer.group(2)
        gesamt = _kontextdatum(start, int(tag_text), int(monat_text), voll, stichtag)
        if gesamt is None:
            return None
        neu = gesamt + versatz
        tag = f"{neu.day:02d}" if len(tag_text) == 2 else str(neu.day)
        monat = f"{neu.month:02d}" if len(monat_text) == 2 else str(neu.month)
        return f"{tag}.{monat}"

    return None



def _dekade_grenzen(alter: int) -> tuple[int, int]:
    beginn = max(0, alter // 10 * 10)
    return beginn, beginn + 9


def _dekade(alter: int) -> str:
    von, bis = _dekade_grenzen(alter)
    return f"{von}–{bis} J."


def _dekade_im_satz(alter: int, original: str) -> str:
    """Vergröbert eine Altersangabe, ohne den Satzbau zu zerstören.

    Aus "67-jährige" wird "60–69-jährige", nicht "60–69 J." — sonst steht
    "Die 60–69 J. Patientin" im Befund.
    """
    von, bis = _dekade_grenzen(alter)
    endung = re.search(r"j[äa]hrig(\w*)", original, re.I)
    if endung:
        return f"{von}–{bis}-jährig{endung.group(1)}"
    return f"{von}–{bis} J."


def _alter_am(geburt: date, stichtag: date) -> int:
    vorher = (stichtag.month, stichtag.day) < (geburt.month, geburt.day)
    return stichtag.year - geburt.year - (1 if vorher else 0)


# --------------------------------------------------------------------------
# Geldbeträge
# --------------------------------------------------------------------------

_WAEHRUNG = {"€": "€", "EUR": "€", "EURO": "€", "CHF": "CHF",
             "USD": "$", "$": "$"}


def betrag_lesen(text: str) -> float | None:
    """Liest einen Geldbetrag in deutscher Schreibweise.

    Punkt trennt Tausender, Komma trennt Nachkommastellen — genau umgekehrt
    zur englischen Schreibweise.
    """
    treffer = re.search(r"\d[\d.\s]*(?:,\d{1,2})?", text)
    if not treffer:
        return None
    roh = treffer.group().replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return float(roh)
    except ValueError:
        return None


def _waehrung_aus(text: str) -> str:
    grossbuchstaben = text.upper()
    for zeichen, anzeige in _WAEHRUNG.items():
        if zeichen in grossbuchstaben:
            return anzeige
    return "€"


def _runden(betrag: float, waehrung: str) -> str:
    """Rundet auf zwei signifikante Stellen.

    Die Grössenordnung bleibt damit ablesbar — eine Rechnung über rund 1.200 €
    ist noch als solche zu erkennen —, die exakte Summe als Wiedererkennungs-
    merkmal verschwindet aber.
    """
    if betrag <= 0:
        return f"0 {waehrung}"
    stelle = len(str(int(betrag))) - 1
    schritt = 10 ** max(0, stelle - 1)
    gerundet = round(betrag / schritt) * schritt
    return f"rund {gerundet:,.0f} {waehrung}".replace(",", ".")


# --------------------------------------------------------------------------
# Darstellungen berechnen
# --------------------------------------------------------------------------

def _initialen(name: str) -> str:
    """'Elisabeth Hartmann' wird zu 'E. H.'.

    Titel stehen nicht im Fund selbst — die Regeln erfassen nur den Namen —
    und bleiben deshalb von allein im Text stehen: aus
    "Prof. Dr. med. Konrad Weissbach" wird "Prof. Dr. med. K. W.".
    """
    teile = [t for t in re.split(r"[\s]+", name.strip()) if t]
    buchstaben = [t[0].upper() for t in teile if t[:1].isalpha()]
    return " ".join(f"{b}." for b in buchstaben) if buchstaben else ""


def _bezugsdatum(gruppen: list[Gruppe]) -> date | None:
    """Spätestes Datum im Dokument — üblicherweise das Briefdatum.

    Dient als Stichtag für die Altersberechnung. Ohne Bezug wäre 'heute' die
    Alternative, was bei alten Dokumenten das Alter systematisch überschätzt.
    """
    gefunden = [
        gelesen
        for gruppe in gruppen if gruppe.typ in ("DATUM", "GEBURTSDATUM")
        for fund in gruppe.funde
        if (gelesen := datum_lesen(fund.text)) is not None
    ]
    return max(gefunden) if gefunden else None


def formen_berechnen(gruppen: list[Gruppe]) -> dict:
    """Füllt je Fund die alternativen Darstellungen und je Gruppe die Initialen.

    Der Datumsversatz gilt dokumentweit einheitlich. Genau darin liegt der
    Wert: absolute Daten verschwinden, die Abstände zwischen ihnen bleiben
    exakt erhalten. Aufenthaltsdauer und Verlauf bleiben damit lesbar.
    """
    # secrets statt random: Der Versatz ist das Geheimnis, das die echten
    # Behandlungsdaten verdeckt. Ein Mersenne-Twister lässt sich aus
    # hinreichend vielen Ausgaben rekonstruieren — wer mehrere anonymisierte
    # Dokumente derselben Einrichtung sieht, könnte den Generatorzustand
    # aufrollen und damit sämtliche Daten zurückrechnen.
    versatz_tage = secrets.choice((-1, 1)) * (120 + secrets.randbelow(281))
    versatz = timedelta(days=versatz_tage)
    stichtag = _bezugsdatum(gruppen)
    # Volle Daten (nur Typ DATUM, nicht das Geburtsdatum) mit Fundstelle: sie
    # liefern das Jahr für Angaben wie "vom 03.03. bis 12.03.2026".
    voll = sorted(
        (fund.start, gelesen)
        for gruppe in gruppen if gruppe.typ == "DATUM"
        for fund in gruppe.funde
        if (gelesen := datum_lesen(fund.text)) is not None
    )

    for gruppe in gruppen:
        if gruppe.typ in ("PATIENT", "ARZT", "PERSON"):
            gruppe.initialen = _initialen(gruppe.anzeige)

        for fund in gruppe.funde:
            formen: dict[str, str] = {}

            gelesen = datum_lesen(fund.text)
            if gelesen is not None:
                formen["jahrgang"] = f"Jahrgang {gelesen.year}"
                formen["verschoben"] = (gelesen + versatz).strftime("%d.%m.%Y")
                if stichtag is not None:
                    alter = _alter_am(gelesen, stichtag)
                    if 0 <= alter <= 120:
                        formen["dekade"] = _dekade(alter)

            if gruppe.typ == "GEBURTSDATUM":
                kurz = re.search(r"(?:Jahrgang|Jg\.)[ \t]*((?:19|20)\d{2})", fund.text)
                if kurz:
                    formen["jahrgang"] = f"Jahrgang {kurz.group(1)}"
                    if stichtag is not None:
                        alter = stichtag.year - int(kurz.group(1))
                        if 0 <= alter <= 120:
                            formen["dekade"] = _dekade(alter)

            if gruppe.typ in ("DATUM", "JAHRESZAHL") and gelesen is None:
                teil = teildatum_verschieben(fund.text, fund.start, versatz,
                                             voll, stichtag)
                if teil is not None:
                    formen["verschoben"] = teil

            if gruppe.typ == "ALTER":
                zahl = re.search(r"\d{1,3}", fund.text)
                if zahl and int(zahl.group()) <= 120:
                    formen["dekade"] = _dekade_im_satz(int(zahl.group()), fund.text)

            if gruppe.typ == "BETRAG":
                wert = betrag_lesen(fund.text)
                if wert is not None:
                    formen["gerundet"] = _runden(wert, _waehrung_aus(fund.text))

            # Nur die Form "Postleitzahl Ort" trägt keinen Strassennamen
            # und darf in der leichten Stufe stehen bleiben.
            if (gruppe.typ == "ADRESSE"
                    and re.fullmatch(r"\d{5}\s+.+", fund.text.strip())):
                formen["nur_ort"] = fund.text.strip()

            fund.formen = formen

    _initialen_entdoppeln(gruppen)

    return {
        "versatz_tage": versatz_tage,
        "bezugsdatum": stichtag.isoformat() if stichtag else None,
    }


def _initialen_entdoppeln(gruppen: list[Gruppe]) -> None:
    """Sorgt dafür, dass zwei Personen nie dieselben Initialen tragen.

    'Hans Meier' und 'Helga Meier' würden sonst beide zu 'H. M.' — und damit
    im Text ununterscheidbar.
    """
    vergeben: dict[str, int] = {}
    for gruppe in sorted(gruppen, key=lambda g: g.funde[0].start if g.funde else 0):
        if not gruppe.initialen:
            continue
        anzahl = vergeben.get(gruppe.initialen, 0)
        vergeben[gruppe.initialen] = anzahl + 1
        if anzahl:
            gruppe.initialen = f"{gruppe.initialen} {anzahl + 1}"
