"""Erkennung personenbeziehbarer Angaben in deutschem Klinik-/Gutachtentext.

Zwei Schichten, die sich gegenseitig absichern:

1. Regex-Regeln für alles, was ein festes Format hat (Daten, Telefon, IBAN,
   Aktenzeichen, Anschriften). Deterministisch und sehr zuverlässig.
2. spaCy-NER (de_core_news_lg) für Namen, Orte und Organisationen im
   Fließtext, also genau das, was sich nicht in ein Muster pressen lässt.

Grundhaltung: lieber ein Fehlalarm zu viel als ein übersehener Name. Alles
Gefundene landet im Review und kann dort abgewählt werden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

import spacy

MODELL_NAME = "de_core_news_lg"
_nlp = None


def _modell():
    """Lädt das spaCy-Modell einmalig und ohne die Pipes, die wir nicht brauchen."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(
                MODELL_NAME,
                exclude=["tagger", "morphologizer", "parser", "lemmatizer",
                         "attribute_ruler", "senter"],
            )
        except Exception:
            _nlp = spacy.load(MODELL_NAME)
        # Arztbriefe sind kurz, Gutachten können lang werden.
        _nlp.max_length = 3_000_000
    return _nlp


# --------------------------------------------------------------------------
# Kategorien
# --------------------------------------------------------------------------
# prioritaet: Bei Überlappung gewinnt die höhere Zahl. Spezifische Muster
# (Geburtsdatum, Versichertennummer) müssen generische (Datum, Person)
# schlagen, sonst wird ein Geburtsdatum nur als "irgendein Datum" behandelt.
KATEGORIEN: dict[str, dict] = {
    "PATIENT":        {"label": "PATIENT",  "stil": "letter", "prioritaet": 60, "farbe": "#e5484d"},
    "ARZT":           {"label": "ARZT",     "stil": "zahl",   "prioritaet": 58, "farbe": "#d6409f"},
    "PERSON":         {"label": "PERSON",   "stil": "zahl",   "prioritaet": 55, "farbe": "#8e4ec6"},
    "GEBURTSDATUM":   {"label": "GEBDAT",   "stil": "zahl",   "prioritaet": 90, "farbe": "#0090ff"},
    "VERSICHERTENNR": {"label": "VERSNR",   "stil": "zahl",   "prioritaet": 88, "farbe": "#0090ff"},
    "IBAN":           {"label": "IBAN",     "stil": "zahl",   "prioritaet": 86, "farbe": "#0090ff"},
    "FALLNUMMER":     {"label": "FALLNR",   "stil": "zahl",   "prioritaet": 84, "farbe": "#0090ff"},
    "AKTENZEICHEN":   {"label": "AZ",       "stil": "zahl",   "prioritaet": 82, "farbe": "#0090ff"},
    "EMAIL":          {"label": "EMAIL",    "stil": "zahl",   "prioritaet": 80, "farbe": "#12a594"},
    "URL":            {"label": "URL",      "stil": "zahl",   "prioritaet": 78, "farbe": "#12a594"},
    "TELEFON":        {"label": "TELEFON",  "stil": "zahl",   "prioritaet": 76, "farbe": "#12a594"},
    "ADRESSE":        {"label": "ADRESSE",  "stil": "zahl",   "prioritaet": 70, "farbe": "#f76b15"},
    "KLINIK":         {"label": "KLINIK",   "stil": "zahl",   "prioritaet": 40, "farbe": "#ffb224"},
    "ORT":            {"label": "ORT",      "stil": "zahl",   "prioritaet": 35, "farbe": "#ffb224"},
    "DATUM":          {"label": "DATUM",    "stil": "zahl",   "prioritaet": 30, "farbe": "#46a758"},
    "ALTER":          {"label": "ALTER",    "stil": "zahl",   "prioritaet": 34, "farbe": "#46a758"},
    "ZEITSPANNE":     {"label": "ZEITRAUM", "stil": "zahl",   "prioritaet": 33, "farbe": "#46a758"},
    "JAHRESZAHL":     {"label": "JAHR",     "stil": "zahl",   "prioritaet": 20, "farbe": "#46a758"},
    "MANUELL":        {"label": "GESCHWÄRZT", "stil": "zahl", "prioritaet": 99, "farbe": "#000000"},
}

KATEGORIE_TITEL = {
    "PATIENT": "Patient/in", "ARZT": "Behandler/in", "PERSON": "Weitere Person",
    "GEBURTSDATUM": "Geburtsdatum", "VERSICHERTENNR": "Versichertennummer",
    "IBAN": "IBAN", "FALLNUMMER": "Fall-/Patientennummer",
    "AKTENZEICHEN": "Aktenzeichen", "EMAIL": "E-Mail", "URL": "Web-Adresse",
    "TELEFON": "Telefon/Fax", "ADRESSE": "Anschrift", "KLINIK": "Einrichtung",
    "ORT": "Ort", "DATUM": "Datum", "ALTER": "Altersangabe",
    "ZEITSPANNE": "Zeitraum", "JAHRESZAHL": "Jahreszahl",
    "MANUELL": "Manuell ergänzt",
}


@dataclass
class Fund:
    start: int
    end: int
    text: str
    typ: str
    quelle: str  # "regex:<name>" | "ner" | "manuell"
    # Alternative Darstellungen für die schwächeren Stufen, gefüllt von
    # stufen.py: z. B. {"jahrgang": "Jahrgang 1958", "dekade": "60–69 J."}
    formen: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Regex-Schicht
# --------------------------------------------------------------------------

_MONATE = ("Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|"
           "Oktober|November|Dezember")
_DATUM = (r"(?:\d{1,2}\.\s?\d{1,2}\.\s?(?:\d{4}|\d{2})"
          rf"|\d{{1,2}}\.\s?(?:{_MONATE})\s+\d{{4}}"
          r"|\d{4}-\d{2}-\d{2})")

# Wörter, die formal wie ein Nachname aussehen, aber Titel, Rolle oder
# Verwandtschaftsbezeichnung sind. Ohne diese Sperre wird aus
# "Prof. Dr. med. Weißbach" eine Person namens "Dr".
_KEIN_NAME = (
    r"(?!(?:Dr|Prof|med|habil|PD|Dipl|Herrn?|Frau|Hr|Fr|Kolleg(?:e|in)|Doktor|"
    r"Professor|Patient(?:in)?|Ober(?:arzt|ärztin)|Chef(?:arzt|ärztin)|"
    r"Assistenz(?:arzt|ärztin)|Fach(?:arzt|ärztin)|Arzt|Ärztin|Pfleger(?:in)?|"
    r"Sohn|Tochter|Ehemann|Ehefrau|Mutter|Vater|Bruder|Schwester|Eltern|"
    r"Angehörige[rn]?|Betreuer(?:in)?|Rechtsanwalt|Rechtsanwältin)\b)")

# Mindestens zwei Kleinbuchstaben — schliesst "Dr" aus, lässt "Utz" zu.
_NAMENSTEIL = _KEIN_NAME + r"[A-ZÄÖÜ][a-zäöüß]{2,}(?:-[A-ZÄÖÜ][a-zäöüß]{2,})?"

# Titel und Anreden, die zwischen Anrede und Namen stehen dürfen und
# mitkonsumiert, aber nicht als Name gewertet werden.
_TITEL = (r"(?:(?:Dr|Prof|PD|med|habil|Dipl\.-?\s?(?:Med|Psych)|Kolleg(?:e|in)|"
          r"Doktor|Professor)\.?\s+)*")

# Bausteine für Einrichtungsnamen
_EINRICHTUNG = (
    r"(?:Universitätsklinik(?:um)?|Bezirksklinik(?:um)?|Klinik(?:um)?|Krankenhaus|"
    r"Hospital|Ärztehaus|Gemeinschaftspraxis|Praxisgemeinschaft|Praxis|MVZ|"
    r"Medizinisches\s+Versorgungszentrum|Institut|Sanatorium|Reha-?klinik|"
    r"Fachklinik|Tagesklinik|Pflegeheim|Seniorenheim|Pflegedienst|Hospiz)")
# Bewusst [ \t] statt \s: ein Einrichtungsname endet an der Zeilengrenze.
# Mit \s greift das Muster über den Umbruch hinweg in die nächste Zeile des
# Briefkopfs und kollidiert dort mit der Anschrift.
_EINR_VORSATZ = (
    r"(?:(?!(?:Die|Der|Das|Den|Dem|Des|Unser\w*|Ihre\w*|Eine\w*|Diese\w*|In|Im|Bei|"
    r"Von|Vom|Zur|Zum|Nach|Aus|Für|Sehr|Mit)\b)[A-ZÄÖÜ][\wäöüß.\-]*[ \t]+)")
_EINR_NACHSATZ = (
    r"(?:[ \t]+(?:am|an[ \t]der|für|im|in|zu|St\.)[ \t]+[A-ZÄÖÜ][\wäöüß.\-]+"
    r"(?:[ \t]+[A-ZÄÖÜ][\wäöüß.\-]+)?"
    r"|[ \t]+(?!(?:Dr|Prof|med|habil|PD|Herrn?|Frau|Hr|Fr)\b)[A-ZÄÖÜ][a-zäöüß]{2,})")

# (typ, pattern, gruppe) — gruppe 0 = ganzer Treffer, sonst nur die Fundstelle
REGELN: list[tuple[str, str, int]] = [
    # --- eindeutige Formate -------------------------------------------------
    # Der Auslöser gehört mit in den Fund: nur so lässt sich "geb. 22.07.1958"
    # in den schwächeren Stufen zu "Jahrgang 1958" oder "60–69 J." machen,
    # ohne dass "geb. Jahrgang 1958" oder "geb. 60–69 J." dabei herauskommt.
    ("GEBURTSDATUM",
     rf"(?:geb\.|geboren\s+am|Geburtsdatum|Geb\.[-\s]?Dat(?:um)?\.?|GebDat|\*)\s*:?\s*{_DATUM}", 0),
    ("VERSICHERTENNR",
     r"(?:Versicherten(?:nummer|nr\.?)|KVNR|Vers\.-?Nr\.?|Krankenversicherten-?nummer)"
     r"\s*:?\s*([A-Z]\s?\d[\d\s]{7,12}\d)", 1),
    ("VERSICHERTENNR", r"\b[A-Z]\d{9}\b", 0),
    ("IBAN", r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b", 0),
    ("FALLNUMMER",
     r"(?:Fall(?:nummer|nr\.?)|Fall-\s?Nr\.?|Aufnahme(?:nummer|nr\.?)|Aufnahme-\s?Nr\.?"
     r"|Patienten(?:nummer|nr\.?)|Pat\.-?\s?Nr\.?|PID|Vorgangs(?:nummer|nr\.?))"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-.]{2,20})", 1),
    ("AKTENZEICHEN",
     r"(?:Aktenzeichen|Az\.|Gesch\.-?\s?Z\.|Geschäftszeichen|Unser\s+Zeichen|Ihr\s+Zeichen)"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9 /\-.]{3,30})", 1),
    ("EMAIL", r"[\w.+-]+@[\w-]+\.[\w.-]*[a-zA-Z]{2,}", 0),
    ("URL", r"(?:https?://|www\.)[^\s<>\"')\]]+", 0),
    ("TELEFON",
     r"(?:Tel\.?|Telefon|Fon|Fax|Telefax|Mobil|Handy|Mobiltelefon|Durchwahl|Piep(?:er)?)"
     r"\s*:?\s*([+(]?[\d][\d\s/()\-]{5,25}\d)", 1),
    ("TELEFON", r"\+49[\s\-/]?\(?\d{1,5}\)?[\s\-/]?\d[\d\s\-/]{4,}\d", 0),
    ("TELEFON", r"\b0\d{2,4}[\s\-/]\d{2,}[\d\s\-/]{2,}\d\b", 0),

    # --- Anschriften --------------------------------------------------------
    ("ADRESSE",
     r"\b[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ.\-]*(?:straße|strasse|str\.|weg|allee|platz|gasse"
     r"|ring|damm|ufer|chaussee|steig|hof|berg|feld)\s+\d{1,4}\s*[a-zA-Z]?\b", 0),
    ("ADRESSE", r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:[ \-][A-ZÄÖÜ][a-zäöüß]+)*", 0),
    ("ADRESSE", r"(?:Postfach)\s*:?\s*\d[\d\s]{2,12}", 0),

    # --- Einrichtungen ------------------------------------------------------
    # Die NER erkennt Klinik- und Praxisnamen unzuverlässig; ein Briefkopf
    # ohne erkannten Absender wäre der peinlichste denkbare Fehler.
    ("KLINIK", rf"{_EINR_VORSATZ}{{1,3}}{_EINRICHTUNG}(?:{_EINR_NACHSATZ})?", 0),
    ("KLINIK", rf"{_EINRICHTUNG}{_EINR_NACHSATZ}", 0),

    # --- Personen über Anrede/Titel (fängt, was die NER verpasst) -----------
    ("PERSON",
     rf"(?:Herr|Herrn|Frau|Hr\.|Fr\.)\s+{_TITEL}((?:{_NAMENSTEIL}\s+)?{_NAMENSTEIL})", 1),
    ("ARZT",
     rf"(?:Dr\.|Prof\.|OA|OÄ|CA|ChA)\s*{_TITEL}((?:{_NAMENSTEIL}\s+)?{_NAMENSTEIL})", 1),

    # --- Zeitangaben --------------------------------------------------------
    # Nur für die strenge Stufe relevant, dort aber unverzichtbar: ein
    # ersetztes Datum nützt wenig, wenn zwei Zeilen später "67-jährig" oder
    # "seit 1994" steht und sich daraus alles zurückrechnen lässt.
    ("ALTER",
     r"\b\d{1,3}(?:\s?[-–]\s?|\s+)?(?:jährig\w*|jaehrig\w*)"
     r"|\b\d{1,3}\s*(?:Jahre|J\.)\s*alt"
     r"|(?<=Alter[:\s])\s*\d{1,3}\s*(?:Jahre|J\.?)?", 0),
    ("ZEITSPANNE",
     r"(?:seit|vor|über|innerhalb\s+von|nach)\s+(?:etwa\s+|ca\.\s+|rund\s+)?"
     r"\d{1,3}\s*(?:Jahren|Jahre|Monaten|Monate|Wochen|Tagen|Tage)"
     r"|(?:seit|im|ab)\s+(?:dem\s+)?(?:Frühjahr|Frühling|Sommer|Herbst|Winter)"
     r"\s+(?:19|20)\d{2}", 0),

    # --- Datum zuletzt: generischer als Geburtsdatum ------------------------
    ("DATUM", _DATUM, 0),
    # Nackte Jahreszahl ganz zum Schluss und mit der niedrigsten Priorität:
    # sie darf niemals einem vollständigen Datum vorgehen.
    ("JAHRESZAHL", r"\b(?:19|20)\d{2}\b", 0),
]

_KOMPILIERT = [(typ, re.compile(muster), gruppe) for typ, muster, gruppe in REGELN]

# Begriffe, die spaCy im Deutschen regelmäßig als Eigennamen taggt, die aber
# nie eine Person identifizieren. Anatomie ist hier der wichtigste Block:
# ein Befund, in dem "Temporallappen" geschwärzt wurde, ist unbrauchbar.
_STOPP_ANATOMIE = {
    "temporallappen", "frontallappen", "parietallappen", "okzipitallappen",
    "schläfenlappen", "stirnlappen", "scheitellappen", "hinterhauptslappen",
    "hippocampus", "hippokampus", "amygdala", "thalamus", "hypothalamus",
    "kleinhirn", "cerebellum", "großhirn", "hirnstamm", "pons", "medulla",
    "cortex", "kortex", "gyrus", "sulcus", "insula", "operculum", "precuneus",
    "cuneus", "uncus", "claustrum", "capsula", "striatum", "putamen",
    "pallidum", "basalganglien", "nucleus", "corpus", "callosum", "ventrikel",
    "liquor", "dura", "arachnoidea", "hypophyse", "epiphyse", "stammganglien",
    "herz", "lunge", "leber", "niere", "nieren", "milz", "magen", "darm",
    "pankreas", "schilddrüse", "prostata", "uterus", "ovar", "blase", "galle",
    "gallenblase", "ösophagus", "duodenum", "kolon", "rektum", "aorta",
    "karotis", "carotis", "femur", "tibia", "fibula", "humerus", "radius",
    "ulna", "skapula", "klavikula", "sternum", "patella", "kalkaneus",
    "wirbelsäule", "halswirbelsäule", "brustwirbelsäule", "lendenwirbelsäule",
    "hws", "bws", "lws", "iliosakralgelenk", "plexus", "nervus", "arteria",
    "vena", "musculus", "ramus", "truncus",
}
_STOPP_MEDIZIN = {
    "patient", "patientin", "patienten", "diagnose", "diagnosen", "befund",
    "befunde", "vorbefund", "vorbefunde", "therapie", "anamnese", "epikrise",
    "medikation", "medikamente", "station", "klinik", "klinikum", "abteilung",
    "ambulanz", "notaufnahme", "arzt", "ärztin", "aufnahme", "entlassung",
    "verlauf", "beurteilung", "procedere", "prozedere", "labor", "röntgen",
    "radiologie", "neurologie", "psychiatrie", "chirurgie", "innere",
    "kardiologie", "onkologie", "orthopädie", "urologie", "gynäkologie",
    "mrt", "ct", "eeg", "ekg", "emg", "nlg", "ssep", "meg", "pet", "spect",
    "gutachten", "sachverständiger", "epilepsie", "hypertonie", "diabetes",
    "demenz", "migräne", "apoplex", "insult",
}
_STOPP_ALLGEMEIN = {
    "sehr", "mit", "freundlichen", "grüßen", "herr", "frau", "herrn",
    "kollege", "kollegin", "fallnummer", "aktenzeichen", "versichertennummer",
    "geburtsdatum", "anschrift", "telefon", "durchwahl", "sekretariat",
    "chefarzt", "chefärztin", "oberarzt", "oberärztin", "assistenzarzt",
    "assistenzärztin", "januar", "februar", "märz", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "dezember",
    "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag",
    "sonntag", "links", "rechts", "beidseits", "temporal", "frontal",
    "parietal", "okzipital", "zentral", "medial", "lateral", "distal",
    "proximal", "kranial", "kaudal", "ventral", "dorsal",
}
_STOPP = _STOPP_ANATOMIE | _STOPP_MEDIZIN | _STOPP_ALLGEMEIN


def _ist_stoppwort(wert: str) -> bool:
    """Wahr, wenn der Treffer ausschliesslich aus unverfänglichen Wörtern besteht."""
    bereinigt = wert.strip(" .,;:-").lower()
    if bereinigt in _STOPP:
        return True
    teile = [t for t in re.split(r"[\s\-]+", bereinigt) if t]
    return bool(teile) and all(t in _STOPP for t in teile)


def _regex_funde(text: str) -> Iterable[Fund]:
    for typ, muster, gruppe in _KOMPILIERT:
        for treffer in muster.finditer(text):
            if gruppe and treffer.group(gruppe) is None:
                continue
            start, ende = treffer.span(gruppe)
            roh = text[start:ende]
            # Nachlaufende Satzzeichen/Leerzeichen nicht mitschwärzen
            gekuerzt = roh.rstrip(" \t.,;:)")
            ende -= len(roh) - len(gekuerzt)
            if ende - start < 2:
                continue
            yield Fund(start, ende, text[start:ende], typ, f"regex:{typ.lower()}")


def _ner_funde(text: str) -> Iterable[Fund]:
    nlp = _modell()
    doc = nlp(text)
    zuordnung = {"PER": "PERSON", "LOC": "ORT", "ORG": "KLINIK"}
    for ent in doc.ents:
        typ = zuordnung.get(ent.label_)
        if not typ:
            continue
        wert = ent.text.strip()
        if len(wert) < 2 or wert.isdigit():
            continue
        if _ist_stoppwort(wert):
            continue
        start = ent.start_char + (len(ent.text) - len(ent.text.lstrip()))
        yield Fund(start, start + len(wert), wert, typ, "ner")


# --------------------------------------------------------------------------
# Rollen-Heuristik
# --------------------------------------------------------------------------

_ARZT_MARKER = re.compile(
    r"(?:Dr\.|Prof\.|OA|OÄ|CA|ChA|Oberarzt|Oberärztin|Chefarzt|Chefärztin|"
    r"Assistenzarzt|Assistenzärztin|Facharzt|Fachärztin|Arzt|Ärztin|Kolleg(?:e|in)|"
    r"Unterschrift|i\.\s?V\.|i\.\s?A\.|Gutachter|Sachverständige|Behandler)", re.I)
_PATIENT_MARKER = re.compile(
    r"(?:Patient(?:in|en)?|Pat\.|Betr(?:\.|ifft|eff)|Ihres?\s+Patient|"
    r"unsere[nr]?\s+Patient|geb\.|geboren|Versicherte[rn]?|Proband(?:in)?|"
    r"Kläger(?:in)?|Antragsteller(?:in)?|Beschwerdeführer(?:in)?)", re.I)


def _markerabstand(muster: re.Pattern, links: str, rechts: str) -> int | None:
    """Abstand des nächstgelegenen Markers zum Fund; None, wenn keiner da ist."""
    abstaende = []
    treffer = list(muster.finditer(links))
    if treffer:
        abstaende.append(len(links) - treffer[-1].end())
    rechter = muster.search(rechts)
    if rechter:
        # Ein Marker hinter dem Namen wiegt weniger: die übliche Reihenfolge
        # ist "Patientin Frau Meier", nicht "Meier, unsere Patientin".
        abstaende.append(rechter.start() + 10)
    return min(abstaende) if abstaende else None


def _rolle_bestimmen(text: str, fund: Fund) -> str:
    """Ordnet einer erkannten Person Patient/Behandler/sonstige Person zu.

    Entscheidend ist der *nächstgelegene* Marker, nicht der zuerst geprüfte.
    In "Frau Kollegin Brandner, wir berichten über Ihre Patientin Frau
    Hartmann" stehen beide Marker im selben Fenster — nur die Distanz sagt,
    welcher zu welchem Namen gehört.

    Bleibt eine Heuristik; deshalb lässt sich der Typ im Review umstellen.
    """
    if fund.typ != "PERSON":
        return fund.typ

    # Der Kontext endet am Absatz: was hinter der Leerzeile steht, gehört zu
    # einem anderen Gedanken.
    links = text[max(0, fund.start - 80):fund.start].rsplit("\n\n", 1)[-1]
    rechts = text[fund.end:fund.end + 50].split("\n\n", 1)[0]

    arzt = _markerabstand(_ARZT_MARKER, links, rechts)
    patient = _markerabstand(_PATIENT_MARKER, links, rechts)

    if arzt is None and patient is None:
        return "PERSON"
    if patient is None:
        return "ARZT"
    if arzt is None:
        return "PATIENT"
    return "ARZT" if arzt < patient else "PATIENT"


# --------------------------------------------------------------------------
# Überlappungen auflösen
# --------------------------------------------------------------------------

def _entwirren(funde: list[Fund]) -> list[Fund]:
    """Behält bei Überlappung den Fund mit höherer Priorität, dann den längeren."""
    def rang(f: Fund):
        return (KATEGORIEN[f.typ]["prioritaet"], f.end - f.start)

    behalten: list[Fund] = []
    for fund in sorted(funde, key=rang, reverse=True):
        if any(fund.start < b.end and b.start < fund.end for b in behalten):
            continue
        behalten.append(fund)
    return sorted(behalten, key=lambda f: f.start)


# --------------------------------------------------------------------------
# Gruppierung & Pseudonyme
# --------------------------------------------------------------------------

_ANREDE = re.compile(
    r"^(?:Herrn?|Frau|Hr\.|Fr\.|Dr\.|Prof\.|med\.|Dipl\.-?\s?\w+\.?|PD|habil\.)\s+",
    re.I)


def _gruppenschluessel(fund: Fund) -> str:
    wert = fund.text.strip()
    if fund.typ in ("PERSON", "PATIENT", "ARZT"):
        vorher = None
        while vorher != wert:
            vorher = wert
            wert = _ANREDE.sub("", wert).strip()
    # Zahlenformate ohne Trennzeichen vergleichen, damit "0851 / 123"
    # und "0851/123" dieselbe Gruppe bilden.
    if fund.typ in ("TELEFON", "IBAN", "VERSICHERTENNR"):
        return re.sub(r"[\s/()\-.]", "", wert).upper()
    return re.sub(r"\s+", " ", wert).lower()


@dataclass
class Gruppe:
    id: str
    typ: str
    anzeige: str
    schluessel: str
    funde: list[Fund] = field(default_factory=list)
    label: str = ""
    initialen: str = ""
    aktiv: bool = True

    @property
    def varianten(self) -> list[str]:
        return sorted({f.text for f in self.funde})


def _ist_initiale(teil: str) -> bool:
    return len(teil.rstrip(".")) == 1


def _nachnamen_zusammenfuehren(gruppen: list[Gruppe]) -> list[Gruppe]:
    """Führt Schreibvarianten derselben Person zu einer Gruppe zusammen.

    Zwei Fälle: 'Müller' geht in 'Peter Müller' auf, und 'P. Müller' geht in
    'Peter Müller' auf. Beides nur bei exakt gleichem letzten Namensteil —
    sonst verschmelzen 'Müller' und 'Müller-Schmidt'. Verschiedene Vornamen
    bleiben getrennt, sonst würden Ehepaare zu einer Person.
    """
    personen = [g for g in gruppen if g.typ in ("PERSON", "PATIENT", "ARZT")]
    nach_laenge = sorted(personen, key=lambda g: len(g.schluessel), reverse=True)
    ziel_von: dict[str, Gruppe] = {}

    # a) Bloßer Nachname geht im vollen Namen auf.
    for kurz in personen:
        if " " in kurz.schluessel:
            continue
        for lang in nach_laenge:
            if lang is kurz or " " not in lang.schluessel:
                continue
            if lang.schluessel.split()[-1] == kurz.schluessel:
                ziel_von[kurz.id] = lang
                break

    # b) Abgekürzter Vorname geht im ausgeschriebenen auf.
    for kurz in personen:
        if kurz.id in ziel_von:
            continue
        teile_kurz = kurz.schluessel.split()
        if len(teile_kurz) < 2 or not _ist_initiale(teile_kurz[0]):
            continue
        for lang in nach_laenge:
            if lang is kurz or lang.id in ziel_von:
                continue
            teile_lang = lang.schluessel.split()
            if len(teile_lang) < 2 or _ist_initiale(teile_lang[0]):
                continue
            if (teile_lang[-1] == teile_kurz[-1]
                    and teile_lang[0][0] == teile_kurz[0][0]):
                ziel_von[kurz.id] = lang
                break

    def endziel(gruppe: Gruppe) -> Gruppe:
        gesehen = {gruppe.id}
        while gruppe.id in ziel_von and ziel_von[gruppe.id].id not in gesehen:
            gruppe = ziel_von[gruppe.id]
            gesehen.add(gruppe.id)
        return gruppe

    for kurz_id in list(ziel_von):
        quelle = next(g for g in gruppen if g.id == kurz_id)
        ziel = endziel(quelle)
        if ziel.id == quelle.id:
            continue
        ziel.funde.extend(quelle.funde)
        # Der spezifischere Typ gewinnt: eine als PATIENT erkannte Nennung
        # macht die ganze Gruppe zum Patienten.
        if ziel.typ == "PERSON" and quelle.typ != "PERSON":
            ziel.typ = quelle.typ

    uebrig = [g for g in gruppen if g.id not in ziel_von]
    for g in uebrig:
        g.funde.sort(key=lambda f: f.start)
    return uebrig


_NACHLAUF_TYPEN = {"PERSON", "PATIENT", "ARZT", "ORT", "KLINIK"}


def _konsistenz_nachlauf(text: str, gruppen: list[Gruppe]) -> list[Gruppe]:
    """Sucht jede bereits erkannte Bezeichnung im gesamten Dokument erneut.

    Die NER erkennt denselben Namen nicht an jeder Stelle — mal fehlt der
    Kontext, mal steht er in einer Aufzählung oder Unterschriftszeile. Wer
    einmal als Name erkannt wurde, ist im ganzen Dokument einer. Genau hier
    entstehen sonst die gefährlichen Lücken: ein Name, der neunmal ersetzt
    wird und beim zehnten Mal stehen bleibt.
    """
    belegt: list[tuple[int, int]] = [(f.start, f.end) for g in gruppen for f in g.funde]

    def ist_frei(a: int, b: int) -> bool:
        return not any(a < ende and start < b for start, ende in belegt)

    def stellen(begriff: str) -> list[tuple[int, int]]:
        muster = re.compile(rf"(?<![\wÄÖÜäöüß]){re.escape(begriff)}(?![\wÄÖÜäöüß])")
        return [(t.start(), t.end()) for t in muster.finditer(text)]

    # 1. Aus "94032 Passau" wird zusätzlich der blosse Ortsname — der taucht
    #    in Briefen oft nochmal allein in der Datumszeile auf.
    zusatz: list[Gruppe] = []
    for gruppe in gruppen:
        if gruppe.typ != "ADRESSE":
            continue
        for variante in gruppe.varianten:
            treffer = re.fullmatch(r"\d{5}\s+(.+)", variante)
            if not treffer:
                continue
            ort = treffer.group(1).strip()
            frei = [(a, b) for a, b in stellen(ort) if ist_frei(a, b)]
            if not frei:
                continue
            zusatz.append(Gruppe(
                id=f"n{len(zusatz)}", typ="ORT", anzeige=ort, schluessel=ort.lower(),
                funde=[Fund(a, b, text[a:b], "ORT", "nachlauf") for a, b in frei],
            ))
            belegt.extend(frei)

    gruppen = gruppen + zusatz

    # 2. Jede Variante — und bei Personen zusätzlich der blosse Nachname —
    #    im ganzen Text nachschlagen.
    for gruppe in gruppen:
        if gruppe.typ not in _NACHLAUF_TYPEN:
            continue
        begriffe = list(gruppe.varianten)
        if gruppe.typ in ("PERSON", "PATIENT", "ARZT"):
            for variante in gruppe.varianten:
                teile = variante.split()
                if len(teile) > 1:
                    begriffe.append(teile[-1])
        for begriff in dict.fromkeys(begriffe):
            if len(begriff) < 4:
                continue
            for a, b in stellen(begriff):
                if ist_frei(a, b):
                    gruppe.funde.append(Fund(a, b, text[a:b], gruppe.typ, "nachlauf"))
                    belegt.append((a, b))
        gruppe.funde.sort(key=lambda f: f.start)
    return gruppen


_BUCHSTABEN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def labels_vergeben(gruppen: list[Gruppe]) -> None:
    """Vergibt konsistente Pseudonyme, in Reihenfolge des ersten Auftretens."""
    zaehler: dict[str, int] = {}
    for gruppe in sorted(gruppen, key=lambda g: g.funde[0].start if g.funde else 0):
        kat = KATEGORIEN[gruppe.typ]
        n = zaehler.get(gruppe.typ, 0)
        zaehler[gruppe.typ] = n + 1
        if kat["stil"] == "letter":
            if n < 26:
                suffix = _BUCHSTABEN[n]
            else:
                suffix = _BUCHSTABEN[n // 26 - 1] + _BUCHSTABEN[n % 26]
        else:
            suffix = str(n + 1)
        gruppe.label = f"[{kat['label']}_{suffix}]"


def analysiere(text: str) -> list[Gruppe]:
    """Vollständiger Durchlauf: erkennen, entwirren, gruppieren, benennen."""
    funde = list(_regex_funde(text)) + list(_ner_funde(text))
    funde = _entwirren(funde)

    for fund in funde:
        fund.typ = _rolle_bestimmen(text, fund)

    gruppen: dict[tuple[str, str], Gruppe] = {}
    for fund in funde:
        schluessel = _gruppenschluessel(fund)
        # Personen werden typunabhängig gruppiert: derselbe Name ist dieselbe
        # Person, auch wenn die Rollen-Heuristik an zwei Stellen abweicht.
        familie = "PERSON" if fund.typ in ("PERSON", "PATIENT", "ARZT") else fund.typ
        kennung = (familie, schluessel)
        if kennung not in gruppen:
            gruppen[kennung] = Gruppe(
                id=f"g{len(gruppen)}", typ=fund.typ,
                anzeige=fund.text, schluessel=schluessel,
            )
        gruppe = gruppen[kennung]
        gruppe.funde.append(fund)
        if fund.typ != "PERSON" and gruppe.typ == "PERSON":
            gruppe.typ = fund.typ

    liste = _nachnamen_zusammenfuehren(list(gruppen.values()))
    liste = _konsistenz_nachlauf(text, liste)
    for gruppe in liste:
        gruppe.anzeige = max(gruppe.varianten, key=len)
    liste.sort(key=lambda g: g.funde[0].start if g.funde else 0)
    labels_vergeben(liste)
    return liste


def manuelle_gruppe(text: str, begriff: str, gruppen_id: str) -> Gruppe | None:
    """Sucht einen frei eingegebenen Begriff im gesamten Text.

    Für alles, was die automatische Erkennung nicht findet: seltene
    Diagnosen, Berufsbezeichnungen, Spitznamen, Firmennamen.
    """
    begriff = begriff.strip()
    if len(begriff) < 2:
        return None
    muster = re.compile(re.escape(begriff), re.I)
    funde = [Fund(t.start(), t.end(), t.group(0), "MANUELL", "manuell")
             for t in muster.finditer(text)]
    if not funde:
        return None
    return Gruppe(id=gruppen_id, typ="MANUELL", anzeige=begriff,
                  schluessel=begriff.lower(), funde=funde)
