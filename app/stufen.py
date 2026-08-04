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
            "zwei Terminen bleibt dadurch ablesbar. Ein blosser Ortsname ohne "
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
    },
    "standard": {
        "PATIENT": "ersetzen", "ARZT": "ersetzen", "PERSON": "ersetzen",
        "ORGANISATION": "ersetzen", "ADRESSE": "ersetzen", "ORT": "behalten",
        "GEBURTSDATUM": "dekade", "DATUM": "verschoben",
        # Bewusst ebenfalls vergröbert: eine ausgeschriebene Altersangabe im
        # Text würde das zur Dekade vergröberte Geburtsdatum sonst aushebeln.
        "ALTER": "dekade",
        "ZEITSPANNE": "behalten", "JAHRESZAHL": "behalten",
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
