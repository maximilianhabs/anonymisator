"""Erkennung personenbeziehbarer Angaben in deutschem Klinik-/Gutachtentext.

Zwei Schichten, die sich gegenseitig absichern:

1. Regex-Regeln für alles, was ein festes Format hat (Daten, Telefon, IBAN,
   Aktenzeichen, Anschriften). Deterministisch und sehr zuverlässig.
2. spaCy-NER (de_core_news_lg) für Namen, Orte und Organisationen im
   Fließtext, also genau das, was sich nicht in ein Muster pressen lässt.

Grundhaltung: lieber ein Fehlalarm zu viel als ein übersehener Name. Alles
Gefundene landet im Review und kann dort abgewählt werden.

--------------------------------------------------------------------------
Muster oder Wortliste? Die Entscheidung bei jedem neuen Fund
--------------------------------------------------------------------------
spaCy erzeugt regelmässig Fehlalarme (Fachbegriffe, Medikamente,
Formularfelder, die wie Namen aussehen). Jeder Fund wirft dieselbe Frage
auf, bevor irgendetwas geändert wird:

    Folgt der Fehler einem MUSTER, oder ist er ein EINZELFALL aus einer
    kleinen, geschlossenen Menge?

Folgt er einem Muster — eine Regelmässigkeit in Form, Endung oder
Umgebung, die sich auf viele künftige Fälle überträgt —, gehört die Lösung
in eine der bestehenden Mustergruppen, nicht in eine Wortliste:

  - Wortendung/-baustein: `_MED_ENDUNGEN`, `_MED_GRUNDWOERTER` (Suffixe wie
    "-itis", "-blut" — ein Eintrag deckt tausende mögliche Komposita ab)
  - Umgebung/Position im Satz: `_DOSIS_FOLGT` (ein Name unmittelbar vor
    einer Dosierung ist ein Medikament, gleich welches — "Ebrantil 25 mg"
    und "Novalgin 500 mg" fielen beide durch dieselbe eine Regel, ohne dass
    ein Markenname eingetragen wurde)
  - Grossschreibung, Wortgrenzen, Titel-Anker: siehe `_NAMENSTEIL`,
    `_NAME_GROSS`, `_TITELKETTE`

Ein Muster deckt eine ganze *Klasse* künftiger Fälle ab, ohne dass jeder
Einzelfall eingetragen werden muss — deshalb hier immer die erste Wahl.

Ist der Fehler dagegen ein Einzelfall aus einer kleinen, tatsächlich
begrenzten Menge — deutsche Klinik-Fachrichtungen, Formularfeld-Namen wie
"Aufnahmegrund", gängige Abkürzungen —, ist eine Wortliste
(`_STOPP_ANATOMIE`, `_STOPP_MEDIZIN`, `_STOPP_ALLGEMEIN`) die richtige,
ehrliche Lösung. Diese Mengen sind endlich und wachsen langsam gegen eine
Grenze; das unterscheidet sie von unbegrenzten Mengen wie Medikamenten-
Markennamen oder Nachnamen, für die eine Liste nie vollständig würde.

Die Probe für "unbegrenzt": Könnte in den nächsten fünf Jahren ein
komplett neues Wort aus dieser Kategorie auftauchen, das mit den
bisherigen nichts zu tun hat (ein neues Medikament, ein neuer Nachname)?
Wenn ja, ist es eine unbegrenzte Menge — Muster suchen, nicht eintragen.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

import spacy

from . import config

MODELL_NAME = config.SPACY_MODELL
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
    "SOZIALVERSNR":   {"label": "SVNR",     "stil": "zahl",   "prioritaet": 89, "farbe": "#0090ff"},
    "VERSICHERTENNR": {"label": "VERSNR",   "stil": "zahl",   "prioritaet": 88, "farbe": "#0090ff"},
    "KONTONR":        {"label": "KONTO",    "stil": "zahl",   "prioritaet": 87, "farbe": "#0090ff"},
    "IBAN":           {"label": "IBAN",     "stil": "zahl",   "prioritaet": 86, "farbe": "#0090ff"},
    "STEUERNR":       {"label": "STEUERNR", "stil": "zahl",   "prioritaet": 85, "farbe": "#0090ff"},
    "FALLNUMMER":     {"label": "FALLNR",   "stil": "zahl",   "prioritaet": 84, "farbe": "#0090ff"},
    "RECHNUNGSNR":    {"label": "RECHNR",   "stil": "zahl",   "prioritaet": 83, "farbe": "#0090ff"},
    "AKTENZEICHEN":   {"label": "AZ",       "stil": "zahl",   "prioritaet": 82, "farbe": "#0090ff"},
    "KUNDENNR":       {"label": "KUNDENNR", "stil": "zahl",   "prioritaet": 81, "farbe": "#0090ff"},
    "AUSWEISNR":      {"label": "AUSWEIS",  "stil": "zahl",   "prioritaet": 79, "farbe": "#0090ff"},
    "KFZ":            {"label": "KFZ",      "stil": "zahl",   "prioritaet": 77, "farbe": "#0090ff"},
    "HANDELSREGISTER": {"label": "HR",      "stil": "zahl",   "prioritaet": 75, "farbe": "#0090ff"},
    "EMAIL":          {"label": "EMAIL",    "stil": "zahl",   "prioritaet": 80, "farbe": "#12a594"},
    "URL":            {"label": "URL",      "stil": "zahl",   "prioritaet": 78, "farbe": "#12a594"},
    "TELEFON":        {"label": "TELEFON",  "stil": "zahl",   "prioritaet": 76, "farbe": "#12a594"},
    "ADRESSE":        {"label": "ADRESSE",  "stil": "zahl",   "prioritaet": 70, "farbe": "#f76b15"},
    "DIAGNOSECODE":   {"label": "DIAGCODE", "stil": "zahl",   "prioritaet": 72, "farbe": "#ad7f58"},
    "ORGANISATION":   {"label": "ORG",      "stil": "zahl",   "prioritaet": 40, "farbe": "#ffb224"},
    # ORT trug bis 2026-08-13 dieselbe Farbe wie ORGANISATION — beim Testen
    # als Ursache für "ist das jetzt ein Ort oder eine Zahl?" identifiziert.
    # Jetzt eine eigene Farbe, unabhängig von der zugrunde liegenden Frage,
    # ob Orte in der Standardstufe stehen bleiben oder nicht.
    "ORT":            {"label": "ORT",      "stil": "zahl",   "prioritaet": 35, "farbe": "#00a2c7"},
    "DATUM":          {"label": "DATUM",    "stil": "zahl",   "prioritaet": 30, "farbe": "#46a758"},
    "BETRAG":         {"label": "BETRAG",   "stil": "zahl",   "prioritaet": 25, "farbe": "#46a758"},
    "ALTER":          {"label": "ALTER",    "stil": "zahl",   "prioritaet": 34, "farbe": "#46a758"},
    "GESCHLECHT":     {"label": "GESCHL",   "stil": "zahl",   "prioritaet": 45, "farbe": "#3e63dd"},
    "ZEITSPANNE":     {"label": "ZEITRAUM", "stil": "zahl",   "prioritaet": 33, "farbe": "#46a758"},
    "JAHRESZAHL":     {"label": "JAHR",     "stil": "zahl",   "prioritaet": 20, "farbe": "#46a758"},
    # Niedrigste Priorität überhaupt: jede spezifischere Regel geht vor.
    "ZAHL":           {"label": "ZAHL",     "stil": "zahl",   "prioritaet": 10, "farbe": "#8e8e8e"},
    "MANUELL":        {"label": "GESCHWÄRZT", "stil": "zahl", "prioritaet": 99, "farbe": "#000000"},
}

KATEGORIE_TITEL = {
    "PATIENT": "Patient/in", "ARZT": "Behandler/in", "PERSON": "Weitere Person",
    "GEBURTSDATUM": "Geburtsdatum", "VERSICHERTENNR": "Versichertennummer",
    "SOZIALVERSNR": "Sozialversicherungsnummer", "IBAN": "IBAN",
    "KONTONR": "Kontoverbindung", "STEUERNR": "Steuernummer",
    "FALLNUMMER": "Fall-/Patientennummer", "RECHNUNGSNR": "Rechnungs-/Belegnummer",
    "KUNDENNR": "Kunden-/Vertragsnummer", "AUSWEISNR": "Ausweisnummer",
    "KFZ": "Kfz-Kennzeichen", "HANDELSREGISTER": "Handelsregisternummer",
    "AKTENZEICHEN": "Aktenzeichen", "EMAIL": "E-Mail", "URL": "Web-Adresse",
    "TELEFON": "Telefon/Fax", "ADRESSE": "Anschrift",
    "DIAGNOSECODE": "Diagnosecode (ICD/OPS/DRG)",
    "ORGANISATION": "Einrichtung / Firma",
    "ORT": "Ort", "DATUM": "Datum", "BETRAG": "Geldbetrag",
    "ZAHL": "Zahl ohne Einheit", "GESCHLECHT": "Geschlecht",
    "ALTER": "Altersangabe", "ZEITSPANNE": "Zeitraum", "JAHRESZAHL": "Jahreszahl",
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

# Nach einem akademischen Titel darf der Name auch durchgehend gross
# geschrieben sein: "PROF. DR. MED. WEISSBACH" ist in Briefköpfen und
# Unterschriftenzeilen die Regel. Diese Form nur hier zuzulassen und nicht
# überall ist Absicht — freistehend würde sie jede Abkürzung fangen, von
# EEG bis MRT. Der vorangehende Titel ist der Beleg, der sie rechtfertigt.
_NAME_GROSS = _KEIN_NAME + r"(?:[A-ZÄÖÜ][a-zäöüß]{2,}|[A-ZÄÖÜ]{3,})"
_NAMENSTEIL_NACH_TITEL = (
    _NAME_GROSS + r"(?:-(?:[A-ZÄÖÜ][a-zäöüß]{2,}|[A-ZÄÖÜ]{2,}))?")

# Akademische Zusätze, die zwischen Titel und Namen stehen können, ohne
# selbst ein Name zu sein. Gross- und Kleinschreibung gemischt, weil
# Briefköpfe "MED." und Fliesstext "med." schreibt.
_TITELKETTE = (
    r"(?:(?i:dr|prof|priv|pd|med|dent|vet|habil|h\.\s?c|rer|nat|phil|"
    r"dipl|ing|psych|univ)\.?[ \t]*)*")

# Titel und Anreden, die zwischen Anrede und Namen stehen dürfen und
# mitkonsumiert, aber nicht als Name gewertet werden.
_TITEL = (r"(?:(?:Dr|Prof|PD|med|habil|Dipl\.-?\s?(?:Med|Psych)|Kolleg(?:e|in)|"
          r"Doktor|Professor)\.?\s+)*")

# --------------------------------------------------------------------------
# Physikalische Einheiten
# --------------------------------------------------------------------------
# Sie entscheiden, ob eine Zahl ein Messwert ist. Steht eine davon hinter der
# Zahl, trägt sie medizinische Aussage und bleibt unangetastet — auch in der
# strengen Stufe. Ohne Einheit gilt die Zahl als mögliche Kennung.
#
# Die Reihenfolge ist bedeutsam: längere Einheiten müssen vor ihren kürzeren
# Anfängen stehen, sonst greift "m" bereits bei "mmHg".
_EINHEITEN = (
    # Zusammengesetzte zuerst
    r"mg/dl|mg/l|mg/kg|µg/l|ug/l|µg/dl|ng/ml|ng/l|pg/ml|pmol/l|nmol/l|"
    r"mmol/l|µmol/l|umol/l|mval/l|mU/l|µU/ml|mIE/l|"
    r"g/dl|g/l|IE/l|U/l|E/l|U/ml|ml/min|l/min|mmHg|cmH2O|kg/m²|kg/m2|"
    # Masse und Volumen
    r"mg|µg|ug|mcg|ng|pg|kg|g\b|ml|dl|cl|µl|ul|l\b|"
    # Länge
    r"mm|cm|dm|km|m\b|µm|um|nm|"
    # Elektrisch
    r"mV|µV|uV|kV|V\b|mA|µA|uA|A\b|Ohm|Ω|"
    # Zeit und Frequenz
    r"ms|µs|us|ns|sec|s\b|min|h\b|Hz|kHz|MHz|/min|/s|"
    # Stoffmenge, Aktivität, Sonstiges
    r"mmol|µmol|umol|mol|mval|IE|IU|E\b|U\b|Bq|Gy|Sv|"
    r"°C|°|%|‰|dpt|dB|kcal|kJ|J\b|W\b|bar|Pa|hPa"
)
# Erkennt einen Messwert irgendwo im Text — für die Prüfung von
# Treffern des Sprachmodells.
_MESSWERT_ENTHALTEN = re.compile(
    rf"\d(?:[.,]\d+)?[ \t]?(?:{_EINHEITEN})(?![A-Za-zÄÖÜäöü0-9])")

# Direkt gefolgt von einer Dosierung ("Ebrantil 25 mg") ist ein Treffer ein
# Medikamentenname, keine Person — Markennamen wie "Ebrantil" sind für das
# Sprachmodell namensförmig und werden regelmässig als Person getaggt, oft
# sogar als Behandler (der nächstgelegene Rollenmarker entscheidet). Eine
# vollständige Liste aller Markennamen wäre unbegrenzt und ohnehin nie
# abschliessend; die Dosierung direkt danach ist dagegen ein verlässliches,
# strukturelles Merkmal, unabhängig vom konkreten Namen.
_DOSIS_FOLGT = re.compile(
    rf"^[ \t]+\d+(?:[.,]\d+)?[ \t]*(?:{_EINHEITEN})(?![A-Za-zÄÖÜäöü0-9])")

# Lookahead: optionales Leerzeichen, dann eine Einheit, danach kein
# Wortzeichen mehr (sonst würde "mg" auch in "mgxyz" passen).
#
# Der Teil "/\d+" davor fängt Bruchschreibweisen ab, bei denen die Einheit
# nur hinter der zweiten Zahl steht: bei "140/90 mmHg" sind beide Werte
# Messwerte, nicht nur die 90. Ohne das würde der Blutdruck zerschnitten.
#
# Der Abstand ist "[ \t]*" statt eines einzelnen Leerzeichens: In
# Laborbefunden stehen Wert und Einheit in Spalten und damit weit
# auseinander — "Natrium      139     mmol/l". Mit nur einem Leerzeichen
# gälte der Messwert dort als Kennung und verschwände in der strengen Stufe.
_EINHEIT_FOLGT = (
    rf"(?:[ \t]*/[ \t]*\d+(?:[.,]\d+)?)?[ \t]*(?:{_EINHEITEN})"
    r"(?![A-Za-zÄÖÜäöü0-9])")

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

# Briefköpfe stehen häufig durchgehend in Versalien, und dort ist keine der
# bisherigen Regeln zuständig: die Muster oben verlangen Binnenkleinschreibung
# ("Bezirksklinik", Nachsatz "[A-ZÄÖÜ][a-zäöüß]{2,}"), und das Sprachmodell
# ist bei Grossschreibung unzuverlässig — "BEZIRKSKLINIKUM AUWALD" in der
# Unterschriftszeile hat es gar nicht erst getaggt. Genau dort steht der
# Absender: ein Briefkopf ohne erkannte Einrichtung ist der Fehler, der am
# meisten kostet.
_EINR_KOPF_VERSAL = (
    r"(?:UNIVERSITÄTSKLINIK(?:UM)?|BEZIRKSKLINIK(?:UM)?|FACHKLINIK|TAGESKLINIK|"
    r"REHAKLINIK|POLIKLINIK|KLINIK(?:UM|EN)?|KRANKENHAUS|KRANKENANSTALT|"
    r"HOSPITAL|SPITAL|HOSPIZ|ZENTRUM|AMBULANZ|ÄRZTEHAUS|SANATORIUM|"
    r"GEMEINSCHAFTSPRAXIS|PRAXIS|INSTITUT|PFLEGEHEIM|SENIORENHEIM|MVZ)")
# Vor- und Nachsilben gehören zum Wort: BEZIRKS|KLINIKUM, KLINIK|EN.
_EINRICHTUNG_VERSAL = (
    r"(?<![\wÄÖÜäöüß])"
    rf"[A-ZÄÖÜ][A-ZÄÖÜß\-]*?{_EINR_KOPF_VERSAL}[A-ZÄÖÜß]*"
    # Der Ortsname dahinter, ebenfalls in Versalien. Nur [ \t]: an der
    # Zeilengrenze ist Schluss, sonst verschluckt der Treffer den Umbruch.
    r"(?:[ \t]+(?!GMBH|GGMBH|AG|KG|E\.[ \t]?V)[A-ZÄÖÜ][A-ZÄÖÜß\-]{2,}){0,2}"
    r"(?![\wÄÖÜäöüß])")

# Nummernbezeichnungen kommen in jeder erdenklichen Schreibweise vor:
# "Fallnummer", "Fall-Nr.", "Fall Nr.", "FallNr". Ein gemeinsames Fragment
# deckt alle ab — ohne es fehlte ausgerechnet die Bindestrichform, die in
# Labor- und Klinikbefunden die häufigste ist.
_NR = r"(?:[-\s]?(?:[Nn]ummer|NUMMER|[Nn]r\.?|NR\.?))"

# (typ, pattern, gruppe) — gruppe 0 = ganzer Treffer, sonst nur die Fundstelle
REGELN: list[tuple[str, str, int]] = [
    # --- eindeutige Formate -------------------------------------------------
    # Der Auslöser gehört mit in den Fund: nur so lässt sich "geb. 22.07.1958"
    # in den schwächeren Stufen zu "Jahrgang 1958" oder "60–69 J." machen,
    # ohne dass "geb. Jahrgang 1958" oder "geb. 60–69 J." dabei herauskommt.
    ("GEBURTSDATUM",
     rf"(?:geb\.|geboren\s+am|Geburtsdatum|Geb\.[-\s]?Dat(?:um)?\.?|GebDat|\*)\s*:?\s*{_DATUM}", 0),
    # "geb." leitet nicht nur ein Datum ein, sondern ebenso häufig den
    # Geburtsnamen ("Frau Müller, geb. Schuster") — bisher unabgedeckt, weil
    # die Regel darüber ausschliesslich auf ein Datum prüfte. Beide Formen
    # schliessen sich an derselben Stelle gegenseitig aus (ein Datum ist nie
    # gleichzeitig ein Name), eine Überschneidung der beiden Regeln entsteht
    # deshalb nicht.
    ("PERSON", rf"(?:geb\.|geborene?)[ \t]+({_NAMENSTEIL})", 1),
    ("VERSICHERTENNR",
     rf"(?:Versicherten{_NR}|KVNR|Vers\.-?Nr\.?|Krankenversicherten-?nummer)"
     r"\s*:?\s*([A-Z]\s?\d[\d\s]{7,12}\d)", 1),
    ("VERSICHERTENNR", r"\b[A-Z]\d{9}\b", 0),
    ("IBAN", r"\b[A-Z]{2}\d{2}(?:[ \t]?[A-Z0-9]{4}){3,7}(?:[ \t]?[A-Z0-9]{1,3})?\b", 0),
    ("FALLNUMMER",
     rf"(?:Fall{_NR}|Aufnahme{_NR}|Auftrags{_NR}|Labor{_NR}"
     rf"|Patienten{_NR}|Pat\.-?\s?Nr\.?|PID|Vorgangs{_NR}|Befund{_NR})"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-.]{2,20})", 1),
    ("AKTENZEICHEN",
     r"(?:Aktenzeichen|Az\.|Gesch\.-?\s?Z\.|Geschäftszeichen|Unser\s+Zeichen|Ihr\s+Zeichen)"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9 /\-.]{3,30})", 1),

    # Diagnosecodes (ICD-10-GM, OPS, DRG) — nur der Code, nicht der
    # Diagnosetext selbst. Der Text ("Depressive Episode") bleibt medizinisch
    # wertvoll und wird nicht angetastet; der Code allein, kombiniert mit
    # Alter/Ort/Zeitpunkt, kann bei seltenen Diagnosen re-identifizierend
    # wirken — dieselbe Überlegung wie bei blossen Ortsnamen. Deshalb nur in
    # Standard und Streng aktiv (siehe stufen.py), nicht in Leicht.
    # Jeweils an ein Auslösewort gebunden, nicht frei im Text gesucht: ein
    # freistehendes "[A-Z]\d{2}" träfe auch "Vitamin B12".
    ("DIAGNOSECODE",
     r"(?:ICD-?10?(?:-GM)?|Haupt-?diagnose(?:n)?|Neben-?diagnose(?:n)?|Diagnose(?:n)?)"
     r"[ \t]*:?[ \t]*([A-Z]\d{2}(?:\.\d{1,2})?!?)\b", 1),
    ("DIAGNOSECODE",
     r"OPS(?:-20\d{2})?[ \t]*:?[ \t]*(\d{1,2}-\d{2,3}(?:\.\d{1,2})?)\b", 1),
    ("DIAGNOSECODE", r"DRG[ \t]*:?[ \t]*([A-Z]\d{2}[A-Z])\b", 1),

    # --- Geschäftsverkehr: Rechnungen, Verträge, Behörden -------------------
    # Der Anonymisator wird nicht nur auf Arztbriefe angewandt, sondern auch
    # auf Gutachten, Rechnungen und Schriftverkehr. Diese Nummern sind
    # durchweg direkte Identifikatoren und werden auf jeder Stufe ersetzt.
    ("RECHNUNGSNR",
     rf"(?:Rechnungs{_NR}|Rechnung{_NR}|Beleg{_NR}"
     rf"|Abrechnungs{_NR}|Bestell{_NR}"
     rf"|Quittungs{_NR}|Gutschrift{_NR}"
     rf"|Lieferschein{_NR}|Invoice[ \\t]*(?:No\.?|Number))"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-.]{2,25})", 1),
    ("KUNDENNR",
     rf"(?:Kunden{_NR}|Kd\.-?[ \\t]?Nr\.?|Mitglieds{_NR}"
     r"|Vertrags(?:nummer|nr\.?)|Mandanten(?:nummer|nr\.?)|Debitoren(?:nummer|nr\.?)"
     r"|Kreditoren(?:nummer|nr\.?)|Lieferanten(?:nummer|nr\.?)|Personal(?:nummer|nr\.?)"
     r"|Mitarbeiter(?:nummer|nr\.?)|Policen(?:nummer|nr\.?)|Schaden(?:s?nummer|s?nr\.?))"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9/\-.]{2,25})", 1),
    ("KONTONR",
     r"(?:Konto(?:nummer|nr\.?)|Kto\.?-?[ \t]?Nr\.?|Bankleitzahl|BLZ|BIC|SWIFT(?:-Code)?)"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9 /\-.]{3,25})", 1),
    ("STEUERNR",
     r"(?:Steuer(?:nummer|nr\.?)|St\.-?[ \t]?Nr\.?|USt\.?-?[ \t]?IdNr\.?"
     r"|Umsatzsteuer-?Identifikationsnummer|Steuer-?ID|Steueridentifikationsnummer)"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9 /\-.]{4,25})", 1),
    # Deutsche USt-IdNr auch ohne Beschriftung
    ("STEUERNR", r"\bDE[ \t]?\d{9}\b", 0),
    ("SOZIALVERSNR",
     r"(?:Sozialversicherungs(?:nummer|nr\.?)|SV-?[ \t]?Nr\.?|Renten(?:versicherungs)?"
     r"(?:nummer|nr\.?)|RV-?[ \t]?Nr\.?)\s*:?\s*([0-9][0-9 ]{6,}[A-Z][0-9 ]{2,4})", 1),
    # Format der deutschen Versicherungsnummer: 12 190367 K 123
    ("SOZIALVERSNR", r"\b\d{2}[ ]?\d{6}[ ]?[A-Z][ ]?\d{3}\b", 0),
    ("AUSWEISNR",
     r"(?:Personalausweis(?:nummer|nr\.?)?|Ausweis(?:nummer|nr\.?)"
     r"|Reisepass(?:nummer|nr\.?)?|Pass(?:nummer|nr\.?)"
     r"|Führerschein(?:nummer|nr\.?)?)\s*:?\s*([A-Z0-9][A-Z0-9\-]{5,15})", 1),
    ("HANDELSREGISTER",
     r"(?:HRB|HRA|Handelsregister(?:nummer|nr\.?)?|Registernummer)"
     r"\s*:?\s*([A-Za-z0-9][A-Za-z0-9 /\-.]{2,20})", 1),
    # Deutsches Kfz-Kennzeichen — in Unfallgutachten ein direkter Identifikator
    ("KFZ", r"\b[A-ZÄÖÜ]{1,3}[-–][ ]?[A-Z]{1,2}[ ]?\d{1,4}[ ]?[EH]?\b", 0),
    # Das @ ist der Anker, nicht der Zusammenhang. In Briefköpfen bricht die
    # Adresse regelmässig um — "t.schmidt-wilcke\n@auwald.de" —, weil der
    # Satz sie am Spaltenrand trennt. Eine Regel, die Zusammenhang verlangt,
    # sieht dort nichts, und übrig bleibt der Klarname im Ortsteil.
    #
    # Hier ist das Verschlucken des Umbruchs ausnahmsweise richtig: er liegt
    # *innerhalb* der Adresse, nicht zwischen zwei Angaben. Höchstens ein
    # Umbruch je Seite des @, damit das Muster nicht über einen Absatz
    # greift und den halben Briefkopf mitnimmt.
    ("EMAIL",
     r"[\w.+-]+[ \t]*\n?[ \t]*@[ \t]*\n?[ \t]*[\w-]+\.[\w.-]*[a-zA-Z]{2,}", 0),
    ("URL", r"(?:https?://|www\.)[^\s<>\"')\]]+", 0),
    ("TELEFON",
     r"(?:Tel\.?|Telefon|Fon|Fax|Telefax|Mobil|Handy|Mobiltelefon|Durchwahl|Piep(?:er)?)"
     r"\s*:?\s*([+(]?[\d][\d\s/()\-]{5,25}\d)", 1),
    # Durchgehend [ \t] statt \s: eine Telefonnummer endet an der Zeilengrenze.
    # Mit \s greift das Muster über den Umbruch und verschluckt ihn beim
    # Ersetzen — im Ergebnis kleben dann zwei Platzhalter aneinander.
    ("TELEFON", r"\+49[ \t\-/]?\(?\d{1,5}\)?[ \t\-/]?\d[\d \t\-/]{4,}\d", 0),
    ("TELEFON", r"\b0\d{2,4}[ \t\-/]\d{2,}[\d \t\-/]{2,}\d\b", 0),

    # --- Anschriften --------------------------------------------------------
    # Zusammengeschrieben ("Ludwigstraße 47", "Kirchweg 4") — das
    # Gattungswort klebt am Namen, deshalb Kleinschreibung im Wortinnern.
    ("ADRESSE",
     r"\b[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ.\-]*(?:straße|strasse|str\.|weg|allee|platz|gasse"
     r"|ring|damm|ufer|chaussee|steig|hof|berg|feld)[ \t]+\d{1,4}[ \t]*[a-zA-Z]?\b", 0),
    # Getrennt geschrieben ("Königsberger Straße 1", "Am Alten Weg 3",
    # "Berliner Str. 5") — mindestens so häufig wie die zusammengeschriebene
    # Form, bisher aber nicht erfasst: das Sprachmodell rettete zwar meist
    # den Ortsnamen, liess dabei aber die Hausnummer unbeachtet. Diese Regel
    # hat höhere Priorität als ORT (siehe KATEGORIEN) und gewinnt deshalb
    # bei Überlappung — aus einer NER-vermuteten "Königsberger Straße"
    # (Ort) wird "Königsberger Straße 1" (Adresse). Bis zu zwei
    # grossgeschriebene Vorworte erlaubt, damit auch "Am Alten Weg" komplett
    # erfasst wird, nicht nur "Alten Weg".
    ("ADRESSE",
     r"\b(?:[A-ZÄÖÜ][a-zäöüß]+[ \t]+){0,2}(?:Straße|Strasse|Str\.|Weg|Allee|Platz"
     r"|Gasse|Ring|Damm|Ufer|Chaussee|Steig|Hof|Berg|Feld)[ \t]+\d{1,4}"
     r"[ \t]*[a-zA-Z]?\b", 0),
    # Der Ortsname nach der PLZ verlangte bisher Binnenkleinschreibung und
    # überging deshalb Briefköpfe in Versalien ("94469 DEGGENDORF") — ohne
    # PLZ davor fängt das Sprachmodell einen Versal-Ortsnamen meist noch ab,
    # mit PLZ griff bisher gar keine Regel.
    ("ADRESSE",
     r"\b\d{5}[ \t]+[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ]+(?:[ \-][A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ]+)*", 0),
    ("ADRESSE", r"(?:Postfach)[ \t]*:?[ \t]*\d[\d \t]{2,12}", 0),

    # --- Einrichtungen ------------------------------------------------------
    # Die NER erkennt Klinik- und Praxisnamen unzuverlässig; ein Briefkopf
    # ohne erkannten Absender wäre der peinlichste denkbare Fehler.
    ("ORGANISATION", rf"{_EINR_VORSATZ}{{1,3}}{_EINRICHTUNG}(?:{_EINR_NACHSATZ})?", 0),
    ("ORGANISATION", rf"{_EINRICHTUNG}{_EINR_NACHSATZ}", 0),
    ("ORGANISATION", _EINRICHTUNG_VERSAL, 0),
    # Firmen erkennt man an der Rechtsform, die hinter dem Namen steht.
    ("ORGANISATION",
     r"(?:[A-ZÄÖÜ][\wäöüß&.\-]*[ \t]+){1,4}"
     r"(?:GmbH(?:[ \t]?&[ \t]?Co\.?[ \t]?KGa?A?)?|AGa?|KGaA|KG|OHG|GbR|mbH|SE|"
     r"UG(?:[ \t]?\(haftungsbeschränkt\))?|e\.[ \t]?[VvKk]\.|gGmbH|Ltd\.?|Inc\.?)"
     r"(?![\wäöüß])", 0),
    # Gerichte, Behörden und Kanzleien
    ("ORGANISATION",
     r"(?:Amts|Land|Oberlandes|Sozial|Arbeits|Verwaltungs|Finanz|Bundes|Verfassungs)"
     r"gericht(?:[ \t]+[A-ZÄÖÜ][\wäöüß.\-]+)?", 0),
    ("ORGANISATION",
     rf"{_EINR_VORSATZ}{{0,3}}(?:Rechtsanwälte|Rechtsanwaltskanzlei|Kanzlei|"
     r"Steuerberat(?:er|ung)|Notariat|Versicherung(?:s-?AG)?|Krankenkasse|"
     r"Berufsgenossenschaft|Sparkasse|Volksbank|Raiffeisenbank|Bank)"
     r"(?![\wäöüß])", 0),

    # --- Personen über Anrede/Titel (fängt, was die NER verpasst) -----------
    # "Hartmann, Elisabeth" — in Labor- und Kliniksystemen die Regel, weil
    # dort nach Nachnamen sortiert wird. Ohne diese Regel findet das
    # Sprachmodell nur den Vornamen und der Nachname bleibt im Dokument.
    # Der Feldname davor ist Pflicht, sonst träfe das Muster jede Aufzählung
    # zweier grossgeschriebener Wörter.
    ("PERSON",
     rf"(?:Patient(?:in)?|Pat\.|Name|Nachname|Versicherte[rn]?|Geschädigte[rn]?|"
     rf"Proband(?:in)?|Einsender(?:in)?|Freigabe|Befunder(?:in)?)"
     rf"[ \t]*:[ \t]*({_NAMENSTEIL},[ \t]*{_NAMENSTEIL})", 1),

    ("PERSON",
     rf"(?:Herr|Herrn|Frau|Hr\.|Fr\.)\s+{_TITEL}((?:{_NAMENSTEIL}\s+)?{_NAMENSTEIL})", 1),
    # Der akademische Titel ist einer der stärksten Belege überhaupt: was
    # danach steht und wie ein Name aussieht, ist einer. Deshalb wird die
    # ganze Titelkette übersprungen — "Prof. Dr. med. habil." — und der
    # Name danach auch in Grossschreibung genommen.
    ("ARZT",
     rf"(?i:dr|prof|oa|oä|ca|cha|chefarzt|chefärztin|oberarzt|oberärztin)\.?[ \t]+"
     rf"{_TITELKETTE}"
     rf"((?:{_NAMENSTEIL_NACH_TITEL}[ \t]+)?{_NAMENSTEIL_NACH_TITEL})", 1),

    # Initialen statt ausgeschriebenem Vornamen: "Dr. med. K. Weißbach".
    ("ARZT",
     rf"(?i:dr|prof|oa|oä|ca|cha)\.?[ \t]+{_TITELKETTE}"
     rf"((?:[A-ZÄÖÜ]\.[ \t]*){{1,3}}{_NAMENSTEIL_NACH_TITEL})", 1),

    # --- Freistehende Zahlen ------------------------------------------------
    # Der Grundsatz: Eine Zahl mit physikalischer Einheit ist ein Messwert und
    # trägt medizinische Aussage — sie bleibt. Eine Zahl ohne Einheit ist eine
    # mögliche Kennung: Durchwahl, Piepser, Zimmer, Bett, Fallnummer ohne
    # Beschriftung. In der strengen Stufe wird sie ersetzt.
    #
    # Das ersetzt ein Dutzend Einzelregeln durch ein Prinzip. Die Priorität
    # ist die niedrigste von allen, damit Datum, Telefon, IBAN und alles
    # andere Spezifische zuerst greifen.
    # Der possessive Quantifier "?+" ist wesentlich: ohne ihn fällt die
    # Maschine hinter den Dezimalteil zurück und prüft bei "36,5 °C" nur
    # noch ",5 °C" — der Treffer wäre dann "36", die Einheit übersehen.
    # Der Rückblick "(?<![\d.,])" verhindert, dass die Regel mitten in eine
    # Dezimalzahl greift: bei "1,84 mU/l" wäre "84" sonst ein eigener
    # Treffer, obwohl die ganze Zahl einen Messwert bildet.
    # Im Rückblick steht auch der Buchstabe: klebt die Zahl unmittelbar an
    # einem Wort, gehört sie zum Fachbegriff und ist keine Kennung —
    # Vitamin B12, T3, T4, O2, CO2, C3, IgG4, HbA1c.
    ("ZAHL",
     rf"(?<![\d.,A-Za-zÄÖÜäöüß])\d{{2,}}(?:[.,]\d+)?+\b(?!{_EINHEIT_FOLGT})", 0),

    # --- Zeitangaben --------------------------------------------------------
    # Nur für die strenge Stufe relevant, dort aber unverzichtbar: ein
    # ersetztes Datum nützt wenig, wenn zwei Zeilen später "67-jährig" oder
    # "seit 1994" steht und sich daraus alles zurückrechnen lässt.
    ("ALTER",
     r"\b\d{1,3}(?:\s?[-–]\s?|\s+)?(?:jährig\w*|jaehrig\w*)"
     r"|\b\d{1,3}\s*(?:Jahre|J\.)\s*alt"
     r"|(?<=Alter[:\s])\s*\d{1,3}\s*(?:Jahre|J\.?)?", 0),
    # Geschlecht: allein genommen ein schwaches Merkmal (trifft auf die
    # halbe Bevölkerung zu), zusammen mit Alter, Ort und Diagnose aber ein
    # weiterer Baustein der Re-Identifizierung. Nur in Standard und Streng
    # aktiv (siehe stufen.py), nicht in Leicht. Die ausgeschriebenen Wörter
    # sind im klinischen Text eindeutig genug, um frei im Fliesstext gesucht
    # zu werden; die einbuchstabige Kurzform ("m"/"w"/"d") dagegen nur, wenn
    # ein Feldname wie "Geschlecht:" sie ausdrücklich einleitet — sonst
    # träfe sie jedes einzelne "m" im Text.
    # Als Adjektiv vor einem Substantiv dekliniert Deutsch die Endung
    # ("männlicher Patient", "weibliches Kind") — die blosse Grundform
    # allein hätte "45-jähriger männlicher Patient" nicht gefangen.
    ("GESCHLECHT",
     r"\b(?:männlich|weiblich|divers|intergeschlechtlich)(?:e[rns]?)?\b", 0),
    ("GESCHLECHT", r"(?:Geschlecht|Sex)[ \t]*:?[ \t]*([mwd])\b", 1),
    ("ZEITSPANNE",
     r"(?:seit|vor|über|innerhalb\s+von|nach)\s+(?:etwa\s+|ca\.\s+|rund\s+)?"
     r"\d{1,3}\s*(?:Jahren|Jahre|Monaten|Monate|Wochen|Tagen|Tage)"
     r"|(?:seit|im|ab)\s+(?:dem\s+)?(?:Frühjahr|Frühling|Sommer|Herbst|Winter)"
     r"\s+(?:19|20)\d{2}", 0),

    # --- Geldbeträge --------------------------------------------------------
    # Kein Identifikator für sich, aber in Rechnungen und Gutachten der
    # eigentliche Inhalt — und eine exakte Summe zu einem exakten Datum ist
    # sehr wohl wiedererkennbar.
    # Kein \b hinter dem Währungszeichen: "€" ist kein Wortzeichen, dort kann
    # eine Wortgrenze nie greifen — das Muster hätte nur bei "EUR" gezogen.
    ("BETRAG",
     r"(?:€|EUR|CHF|USD|\$)\s?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?(?![\d,.])"
     r"|\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})?\s?(?:€|EUR|Euro|CHF|USD)"
     r"(?![A-Za-zÄÖÜäöüß])", 0),

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
    # Die lateinischen Gattungswörter in ihrer Kurzform. Das Sprachmodell
    # trennt "Lig. collaterale" gern am Punkt, sodass der Rumpf allein
    # ankommt und die Regel für die volle Kurzform nicht mehr greift.
    "lig", "proc", "ncl", "fasc", "tuberc", "artic", "musc", "nerv", "vas",
    "temporallappen", "frontallappen", "parietallappen", "okzipitallappen",
    "schläfenlappen", "stirnlappen", "scheitellappen", "hinterhauptslappen",
    "hippocampus", "hippokampus", "amygdala", "thalamus", "hypothalamus",
    "kleinhirn", "cerebellum", "großhirn", "hirnstamm", "pons", "medulla",
    "cortex", "kortex", "gyrus", "sulcus", "insula", "operculum", "precuneus",
    "cuneus", "uncus", "claustrum", "capsula", "striatum", "putamen",
    "pallidum", "basalganglien", "nucleus", "corpus", "callosum", "ventrikel",
    "liquor", "dura", "arachnoidea", "hypophyse", "epiphyse", "stammganglien",
    # Wirkstoffe und Präparate. Ohne diese Sperre wird aus der Zeile
    # "Ramipril 5 mg 1-0-0" eines Medikationsplans eine Organisation.
    # Die Liste ist bewusst nicht vollständig — sie deckt ab, was in
    # neurologischen und internistischen Briefen regelmässig vorkommt.
    "ramipril", "enalapril", "lisinopril", "candesartan", "valsartan",
    "metoprolol", "bisoprolol", "amlodipin", "torasemid", "furosemid",
    "hydrochlorothiazid", "spironolacton", "simvastatin", "atorvastatin",
    "rosuvastatin", "metformin", "insulin", "pantoprazol", "omeprazol",
    "levothyroxin", "thyroxin", "ibuprofen", "paracetamol", "metamizol",
    "novaminsulfon", "tilidin", "tramadol", "morphin", "oxycodon",
    "levetiracetam", "lamotrigin", "carbamazepin", "oxcarbazepin",
    "valproat", "valproinsäure", "lacosamid", "brivaracetam", "topiramat",
    "zonisamid", "perampanel", "phenytoin", "phenobarbital", "primidon",
    "gabapentin", "pregabalin", "clobazam", "clonazepam", "lorazepam",
    "diazepam", "midazolam", "levodopa", "carbidopa", "benserazid",
    "pramipexol", "ropinirol", "rotigotin", "amantadin", "rasagilin",
    "selegilin", "entacapon", "riluzol", "donepezil", "rivastigmin",
    "memantin", "galantamin", "quetiapin", "risperidon", "olanzapin",
    "aripiprazol", "haloperidol", "melperon", "pipamperon", "mirtazapin",
    "sertralin", "citalopram", "escitalopram", "fluoxetin", "venlafaxin",
    "duloxetin", "amitriptylin", "doxepin", "lithium", "clopidogrel",
    "apixaban", "rivaroxaban", "edoxaban", "dabigatran", "phenprocoumon",
    "marcumar", "heparin", "enoxaparin", "prednisolon", "dexamethason",
    "methylprednisolon", "cortison", "azathioprin", "methotrexat",
    "sumatriptan", "zolmitriptan", "flunarizin", "baclofen",
    "tizanidin", "tolperison", "botulinumtoxin", "immunglobulin",
    # Einheiten und Darreichungsformen — sie stehen in Medikationsplänen
    # neben dem Wirkstoff und müssen mit als unverfänglich gelten.
    "mg", "ml", "mmol", "mval", "mol", "kg", "µg", "mcg", "ie", "iu",
    "tbl", "tabl", "tablette", "tabletten", "kps", "kaps", "kapsel",
    "amp", "supp", "ret", "retard", "tropfen", "hub", "stk", "dosis",
    "neurocranium", "neurocraniums", "neurokranium", "neurokraniums",
    "viscerocranium", "cranium", "craniums", "kranium", "schädelbasis",
    "hirnschädel", "sella", "cochlea", "vestibulum", "labyrinth", "orbita",
    "sinus", "mastoid", "felsenbein", "keilbein", "siebbein",
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
    # Stehende Wendungen, die das Sprachmodell für Eigennamen hält. Sie
    # erreichen die Prüfung bereits um den Schlusspunkt gekürzt, stehen
    # deshalb ohne ihn in der Liste.
    "z.n", "z. n", "zn", "st.p", "st. p", "d.d", "v.a", "i.v", "p.o",
    "s.c", "i.m", "a.e", "ggf", "bds", "re", "li",
    "patient", "patientin", "patienten", "diagnose", "diagnosen", "befund",
    "befunde", "vorbefund", "vorbefunde", "therapie", "anamnese", "epikrise",
    "medikation", "medikamente", "station", "klinik", "klinikum", "abteilung",
    "ambulanz", "notaufnahme", "arzt", "ärztin", "aufnahme", "entlassung",
    "verlauf", "beurteilung", "procedere", "prozedere", "labor", "röntgen",
    "radiologie", "neurologie", "psychiatrie", "chirurgie", "innere",
    "kardiologie", "onkologie", "orthopädie", "urologie", "gynäkologie",
    "mrt", "ct", "eeg", "ekg", "emg", "nlg", "ssep", "meg", "pet", "spect",
    # Modalitäten mit Ortsangabe ("cMRT" = kraniell, "cCT") -- eine kleine,
    # feste Menge in der deutschen Radiologie, keine, die mitwachsen würde.
    "cmrt", "cct", "mra", "cta",
    "gutachten", "sachverständiger", "epilepsie", "hypertonie", "diabetes",
    "demenz", "migräne", "apoplex", "insult", "schwindel",
    # Körperregionen, wie sie hinter einer Modalität stehen ("CT
    # Hals/Thorax", "MRT Kopf") -- ergänzt "kopf"/"hals" u. a. in
    # _MED_GRUNDWOERTER, die dort nur Kompositum-Enden abdecken, nicht das
    # freistehende Wort.
    "hals", "thorax", "abdomen", "nativ",
    "kontrolle", "kontrollen", "visite",
    # Feldbezeichner aus dem Dokumentkopf, als Ganzes: "aufnahme" allein war
    # schon Stoppwort, das zusammengesetzte "Aufnahmegrund" traf die Liste
    # aber nicht — beim Praxistest als eigenständiger Fund aufgefallen.
    "aufnahmegrund", "diagnosegrund", "entlassungsgrund",
    "behandlungsgrund", "einweisungsgrund",
}
_STOPP_ALLGEMEIN = {
    # Bezeichner aus Briefköpfen. Sie stehen unmittelbar vor der Angabe, die
    # sie benennt, und werden vom Sprachmodell für Eigennamen gehalten --
    # "Tel" kam als Ortsname an. Die Angabe selbst fasst ohnehin eine eigene
    # Regel, der Bezeichner davor ist nur Beiwerk.
    "tel", "fon", "fax", "telefax", "mobil", "mail", "email", "e-mail",
    "web", "internet", "zentrale", "kontakt", "ansprechpartner",
    "ansprechpartnerin",
    "sehr", "mit", "freundlichen", "grüßen", "herr", "frau", "herrn",
    # Akademische Titel und Anreden. Sie stehen neben Namen und werden vom
    # Sprachmodell regelmässig mit hineingezogen — besonders in
    # Grossschreibung, wie sie in Briefköpfen üblich ist.
    "dr", "drs", "prof", "professor", "doktor", "med", "dent", "vet",
    "habil", "pd", "priv", "dipl", "psych", "phil", "rer", "nat", "hc",
    "mba", "msc", "bsc", "ma", "ba",
    # Partizipien in Rollenbezeichnungen. Generisch über die Endung "-ender"
    # zu filtern verbietet sich: "Bender" ist ein Familienname.
    "behandelnder", "behandelnde", "behandelnden", "zuweisender",
    "zuweisende", "überweisender", "untersuchender", "diensthabender",
    "aufnehmender", "entlassender", "unterzeichnender", "vertretender",
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


# --------------------------------------------------------------------------
# Fachbegriffe strukturell erkennen
# --------------------------------------------------------------------------
# Eine Wortliste kann Fachsprache nie einholen — es entstehen laufend neue
# Komposita. Die folgenden Regeln greifen deshalb an der Wortbildung an und
# decken damit Tausende Begriffe ab, die nie einzeln aufgeführt werden müssen.

# Endungen, auf die im Deutschen kein Familienname endet. Die Mindestlänge
# schützt kurze Namen: "Rose" endet auf "ose", ist aber ein Nachname.
_MED_ENDUNGEN = (
    "itis", "itiden", "ose", "osen", "osis", "iasis", "ismus",
    "pathie", "pathien", "opathie", "algie", "algien", "algesie",
    "ektomie", "tomie", "stomie", "skopie", "graphie", "grafie",
    "therapie", "plegie", "parese", "paresen", "plasie", "plasie",
    "trophie", "atrophie", "penie", "zytose", "philie", "ämie", "ämien",
    "urie", "logie", "sklerose", "stenose", "fraktur",
    "insuffizienz", "syndrom", "syndroms", "syndrome",
    # Adjektive und Adverbien der Fachsprache. Sie stehen oft am Satzanfang
    # ("Laborchemisch ergaben sich …") und werden dort grossgeschrieben, was
    # das Sprachmodell regelmässig für einen Eigennamen hält. Die Endungen
    # sind lang genug, dass kurze Familiennamen auf -isch nicht betroffen
    # sind: "Kubisch" und "Bartisch" bleiben Namen.
    "logisch", "chemisch", "physisch", "metrisch", "graphisch", "grafisch",
    "skopisch", "gnostisch", "peutisch", "matisch", "tomisch", "morphisch",
    "statisch", "zentrisch", "sektionell", "ational",
    # Partizipien auf -iert beschreiben den Zustand, nie eine Person:
    # "orientiert", "kompensiert", "dokumentiert". In Versalien geschrieben
    # ("WACH UND ORIENTIERT") hält das Sprachmodell sie für Firmennamen.
    "iert", "ierte", "ierten", "iertem", "ierter",
    # Fachadjektive. Am Satzanfang grossgeschrieben ("Multisegmentale
    # Veränderungen …") liest das Sprachmodell sie als Ortsnamen.
    "entale", "entaler", "entalen", "mentale", "mentaler",
    "matös", "matöse", "matöser", "matösen", "kulös", "kulöse", "kulöser",
    "ulös", "ulöse", "ulöser", "ulösen", "konvex", "konvexe", "konvexer",
    "konkav", "konkave", "konkaver", "segmental", "segmentale",
    # Wirkstoffstämme der INN-Nomenklatur. Sie sind international
    # vergeben und bilden im Deutschen keinen Familiennamen -- anders als
    # ein blosses "-ib", das in "Habib" steckte.
    "statin", "sartan", "pril", "olol", "azol", "tidin", "profen",
    "cillin", "mycin", "floxacin", "gliptin", "glitazon", "parin",
    "xaban", "timib", "tinib", "zumab", "ximab", "mumab", "zepam",
    # Antikonvulsiva: Racetame ("Levetiracetam", "Piracetam") und
    # Succinimide ("Ethosuximid") — beide kamen als Person/Behandler an.
    "acetam", "uximid",
)

# Grundwörter am Ende eines Kompositums. Deutsche Zusammensetzungen tragen
# ihre Bedeutung hinten, deshalb genügt die Prüfung des Wortendes — eine
# Suche im ganzen Wort würde "Werther" über den Bestandteil "wert" treffen.
_MED_GRUNDWOERTER = (
    # Anatomie
    "arterie", "arterien", "vene", "venen", "nerv", "nerven", "muskel",
    "muskeln", "knochen", "gelenk", "gelenke", "sehne", "sehnen", "band",
    "fuß", "füße", "fuss", "füsse", "hand", "hände", "arm", "arme",
    "bein", "beine", "finger", "zehe", "zehen", "kopf", "hals", "rumpf",
    "haut", "schleimhaut", "lappen", "kern", "kerne", "rinde", "mark",
    "nase", "ohr", "auge", "mund", "knie", "hacke", "ferse", "schulter",
    "hüfte", "rücken", "brust", "bauch", "becken", "wirbel", "schädel",
    # Befund und Diagnostik
    "antikörper", "antigen", "serologie", "sonographie", "sonografie",
    "mikroskopie", "szintigraphie", "phänomen", "erkrankung", "krankheit",
    "befund", "befunde", "diagnostik", "diagnose", "diagnosen", "therapie",
    "latenz", "latenzen", "potential", "potentiale", "potenzial", "reflex",
    "reflexe", "agglutinin", "globulin", "globuline", "faktor", "faktoren",
    "spiegel", "index", "quotient", "geschwindigkeit", "amplitude",
    # Klinik
    "stellung", "exposition", "belastung", "verfärbung", "verfärbungen",
    "schwellung", "schwellungen", "störung", "störungen", "empfindung",
    "empfindungen", "veränderung", "veränderungen", "symptomatik",
    "ätiologie", "genese", "anamnese", "medikation", "dosierung",
    "beschwerde", "beschwerden", "schmerz", "schmerzen", "defizit",
    "defizite", "ausfall", "ausfälle", "karenz", "schutz", "verlauf",
    "trauma", "traumata", "verletzung", "verletzungen",
    # Glued statt getrennt geschrieben ("Verlaufslabor", "Chefarztvisite")
    # -- dieselben Wörter, die als eigenständiges Wort oder mit Bindestrich
    # bereits als Stoppwort gelten (siehe _STOPP_MEDIZIN), fängt hier auch
    # ihre Kompositum-Form am Wortende.
    "labor", "visite",
    # Eponyme: Zeichen, Tests und Skalen tragen den Namen ihres
    # Erstbeschreibers. "Lasègue-Zeichen" oder "Schellong-Test" enthalten
    # damit formal einen Personennamen, sind aber Fachbegriffe und keine
    # Angabe über die untersuchte Person.
    "zeichen", "test", "tests", "versuch", "stehversuch", "probe",
    "manöver", "handgriff", "griff", "skala", "score", "schema",
    "kriterium", "kriterien", "klassifikation", "einteilung", "regel",
    "stadium", "stadien", "grad", "grade", "methode", "formel",
    "operation", "plastik", "prothese", "naht", "zugang", "punktion",
    # Feldbezeichnungen aus Formularköpfen. "Auftrags-Nr." oder
    # "Fall-Nummer" sind die Beschriftung neben dem Wert, nicht der Wert —
    # die Nummer selbst fangen die eigenen Regeln ab.
    "nr", "nummer", "nummern", "datum", "name", "vorname", "nachname",
    "anschrift", "eingang", "ausgang", "einsender", "empfänger", "absender",
    # Grundwörter aus der Verwaltungs- und Messsprache des Arztbriefs.
    # Sie stehen am Ende deutscher Zusammensetzungen, die das Sprachmodell
    # für Eigennamen hält: "Kassensitz", "Laborbudget", "Lageempfinden",
    # "Schilddrüsenparameter". Am Wortende bilden sie im Deutschen keinen
    # Familiennamen -- die Prüfung greift nur auf das letzte Glied zu.
    "sitz", "budget", "empfinden", "parameter", "wert", "werte", "bereich",
    "grenze", "grenzen", "spanne", "dauer", "frequenz", "intervall",
    "abstand", "abstände", "breite", "höhe", "tiefe", "länge", "gewicht",
    "umfang", "volumen", "menge", "anteil", "verhältnis", "summe",
    "schwung", "beweglichkeit", "tonus", "trophik", "koordination",
    # "kraft" steht bewusst NICHT hier: Kraft ist ein verbreiteter
    # Familienname und wäre unter der Sechs-Zeichen-Schranke sofort
    # unterdrückt worden. Zusammensetzungen darauf ("Muskelkraft") fängt
    # ohnehin schon der Baustein "muskel".
)

# Lateinische Anatomie: das Gattungswort steht vorn.
_LATEIN_ANATOMIE = re.compile(
    r"^(?:Nervus|Nervi|Arteria|Arteriae|Vena|Venae|Musculus|Musculi|Os|Ossa|"
    r"Ligamentum|Ligamenta|Ramus|Rami|Plexus|Ganglion|Truncus|Fascia|"
    r"Bursa|Tendo|Vertebra|Costa|Foramen|Sinus|Sulcus|Gyrus|Nucleus|"
    r"Cortex|Medulla|Corpus|Capsula|Membrana)\b", re.I)

# Dieselben Gattungswörter in der Kurzform, wie sie im Befund steht:
# "N. tibialis", "M. biceps", "A. carotis", "Lig. collaterale". Dazu die
# stehenden Wendungen "Z. n." (Zustand nach) und "St. p." (Status post).
_ANATOMIE_KURZ = re.compile(
    r"^(?:[NMAVR]|Lig|Proc|Art|Gl|Ncl|Tr|Fasc|Vv|Aa|Nn|Mm|Z\.\s?n|St\.\s?p)\.\s*"
    r"[a-zäöüß]", re.I)

# Bausteine, die ein Wort als medizinischen Fachbegriff ausweisen. Sie werden
# im ganzen Wort gesucht, nicht nur am Ende — "Differentialblutbild" trägt
# "blut" in der Mitte.
#
# Die Mindestlänge von elf Zeichen ist der Schutz: Familiennamen wie "Herzog"
# (herz), "Bluthardt" (blut) oder "Ohrmann" (ohr) bleiben darunter und
# gelten weiter als Namen. Lange deutsche Komposita mit medizinischem
# Baustein sind dagegen praktisch nie Nachnamen.
_MED_BAUSTEINE = (
    "blut", "nerv", "atem", "bewusstsein", "eiweiss", "eiweiß", "muskel",
    "knochen", "gelenk", "gefäss", "gefäß", "herz", "lunge", "leber",
    "niere", "magen", "darm", "haut", "auge", "ohr", "hirn", "wirbel",
    "rücken", "schädel", "becken", "schulter", "gewebe", "zelle", "serum",
    "plasma", "liquor", "urin", "stuhl", "harn", "galle", "lymph",
    "status", "befund", "infekt", "entzündung", "erkrankung", "syndrom",
    "therapie", "diagnos", "anamnes", "untersuchung", "behandlung",
    "versuch", "reflex", "sensib", "motor", "vegetat", "kognitiv",
)
_MIN_BAUSTEINLAENGE = 11

# Lateinische Endungen, die im Deutschen keinen Familiennamen bilden.
# "iones" ist die Pluralform ("Perniones"); die kürzere Variante "ones"
# steht bewusst nicht dabei, weil sie "Jones" träfe.
_LATEIN_ENDUNGEN = ("ulus", "olus", "culus", "icus", "inus", "osus", "atum",
                    "ismus", "itis", "oma", "osis", "iasis", "algia",
                    "iones", "ationes", "itides", "omata")

# Segmentbezeichnungen der Wirbelsäule: C1-C7, Th1-Th12, L1-L5, S1-S5,
# dazu die deutschen Kürzel HWK/BWK/LWK/SWK. Sie stehen im Befund überall
# und kamen als Ort ("S1") oder Firma ("HWK7") an.
_WIRBELSEGMENT = re.compile(
    r"^(?:HWK|BWK|LWK|SWK|WK|Th|[CTLS])[ \t]?\d{1,2}"
    r"(?:[/-](?:HWK|BWK|LWK|SWK|Th|[CTLS])?\d{1,2})?$", re.I)

# Krankenkassen und Verbände, die als Abkürzung auftreten und trotz
# Grossschreibung echte Organisationen sind.
_ECHTE_ABKUERZUNGEN = {
    "aok", "tk", "dak", "bkk", "ikk", "kkh", "kvb", "kbv", "mdk", "mds",
    "bg", "dgb", "vdk", "sbk", "hek", "gkv", "pkv",
}


def _ist_abkuerzung(wert: str) -> bool:
    """Reine Grossbuchstabenfolge — im Befund fast immer ein Fachkürzel.

    ANA, ANCA, TSH, MAG, CRP, EEG. Krankenkassen sind die Ausnahme und
    stehen deshalb in einer eigenen Liste.
    """
    kern = re.sub(r"[-.\s]", "", wert)
    if not (2 <= len(kern) <= 6) or not kern.isalpha():
        return False
    return kern.isupper() and kern.lower() not in _ECHTE_ABKUERZUNGEN


def _ist_fachbegriff(wert: str) -> bool:
    """Erkennt medizinische Fachsprache an ihrer Wortbildung."""
    bereinigt = wert.strip(" .,;:-")
    if (_LATEIN_ANATOMIE.match(bereinigt) or _ANATOMIE_KURZ.match(bereinigt)
            or _WIRBELSEGMENT.match(bereinigt)):
        return True

    klein = bereinigt.lower()

    # Ein langes Wort mit medizinischem Baustein: "Differentialblutbild",
    # "Hirnnervenstatus", "Atemwegsinfekt". Kurze Wörter bleiben aussen vor,
    # damit "Herzog" und "Bluthardt" weiter als Namen gelten.
    for wortteil in re.split(r"[-\s]+", klein):
        if len(wortteil) >= _MIN_BAUSTEINLAENGE and any(
                b in wortteil for b in _MED_BAUSTEINE):
            return True

    # Lateinische Endung ohne deutsches Namensvorbild: "Nodulus", "Neuritis".
    if len(klein) >= 6 and klein.endswith(_LATEIN_ENDUNGEN):
        return True

    # Bei Bindestrichwörtern trägt der letzte Teil die Bedeutung:
    # "Anti-MAG-Antikörper" ist ein Antikörper.
    teile = [t for t in re.split(r"[-\s]+", bereinigt.lower()) if t]
    if not teile:
        return False

    for teil in teile:
        if len(teil) >= 8 and teil.endswith(_MED_ENDUNGEN):
            return True
        # Ein Segmentkürzel irgendwo im Treffer macht die ganze Angabe zur
        # Ortsbezeichnung am Körper: "Wurzelkompression S1" ist ein Befund,
        # kein Eigenname.
        if _WIRBELSEGMENT.match(teil):
            return True

    # Angehängte Zahlen zählen nicht: "Rankin-Skala 2" ist eine Skala.
    woerter = [t for t in teile if any(z.isalpha() for z in t)]
    if not woerter:
        return False

    letzter = woerter[-1]
    if len(letzter) >= 6 and letzter.endswith(_MED_GRUNDWOERTER):
        return True
    # Auch alleinstehend: "Zehen", "Vorfüße", "Nerven"
    return letzter in _MED_GRUNDWOERTER


def _ist_stoppwort(wert: str) -> bool:
    """Wahr, wenn der Treffer ausschliesslich aus unverfänglichen Wörtern besteht.

    Zahlenanteile bleiben ausser Betracht. Das Sprachmodell zieht in einem
    Medikationsplan gern die Dosis mit in den Namen — "Ramipril 5" statt
    "Ramipril" — und ohne diese Bereinigung hätte die Stoppliste dort nie
    gegriffen.
    """
    bereinigt = wert.strip(" .,;:-").lower()
    if _stoppwort_einzeln(bereinigt):
        return True
    # Auch die einzelnen Bestandteile von Satzzeichen und Schrägstrich
    # befreien: "Dr." trägt seinen Punkt mit, "CT Hals/Thorax" trennt seine
    # beiden Körperregionen nur durch "/" — beides würde die Liste sonst
    # nie erreichen.
    teile = [t.strip(".,;:-") for t in re.split(r"[\s\-/]+", bereinigt)]
    teile = [t for t in teile if t and not any(z.isdigit() for z in t)]
    return bool(teile) and all(_stoppwort_einzeln(t) for t in teile)


def _stoppwort_einzeln(wort: str) -> bool:
    """Ein Wort, direkt oder als Mehrzahl mit angehängtem 's'.

    Abkürzungen wie "EEG"/"MRT" werden im Deutschen wie englische Lehnwörter
    pluralisiert ("die EEGs", "mehrere MRTs") — ohne diese Ausnahme träfe
    die Stoppliste die Einzahl, aber nie die im Befund häufigere Mehrzahl.
    """
    if wort in _STOPP:
        return True
    return len(wort) > 1 and wort.endswith("s") and wort[:-1] in _STOPP


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
            # Die Mindestlänge fängt entartete Treffer ab — ausser bei der
            # einbuchstabigen Geschlechtsabkürzung ("Geschlecht: w"), die
            # genau deshalb an ein Auslösewort gebunden ist (siehe REGELN):
            # nicht die Kürze macht sie riskant, das Auslösewort macht sie
            # sicher.
            if ende - start < 2 and typ != "GESCHLECHT":
                continue
            yield Fund(start, ende, text[start:ende], typ, f"regex:{typ.lower()}")


def _ner_funde(text: str) -> Iterable[Fund]:
    nlp = _modell()
    doc = nlp(text)
    zuordnung = {"PER": "PERSON", "LOC": "ORT", "ORG": "ORGANISATION"}
    for ent in doc.ents:
        typ = zuordnung.get(ent.label_)
        if not typ:
            continue
        # Das Sprachmodell zieht gelegentlich über einen Zeilen- oder
        # Absatzumbruch hinweg. Weder Person noch Ort noch Einrichtung
        # erstrecken sich über einen Absatz — am Umbruch wird abgeschnitten.
        wert = ent.text.split("\n", 1)[0].strip()
        if len(wert) < 2 or wert.isdigit():
            continue
        # Enthält der Treffer einen Messwert, ist er keine Person und kein
        # Ort. "Temperatur 36,5 °C" oder "Amplitude 45 mV" hat das
        # Sprachmodell wiederholt für Ortsnamen gehalten — eine physikalische
        # Einheit im Treffer schliesst das aus.
        if _MESSWERT_ENTHALTEN.search(wert):
            continue
        if _DOSIS_FOLGT.match(text[ent.end_char:ent.end_char + 20]):
            continue
        # Ohne einen einzigen Grossbuchstaben ist es kein Eigenname. Im
        # Deutschen trägt jeder Name, Ort und Firmenname eine Majuskel;
        # "seitengleich", "grössenkonstant" und "collaterale mediale" haben
        # keine. Das Sprachmodell greift bei solchen Wörtern regelmässig
        # daneben, weil sie an der Satzstelle eines Namens stehen.
        if not any(z.isupper() for z in wert):
            continue
        if _ist_stoppwort(wert) or _ist_fachbegriff(wert) or _ist_abkuerzung(wert):
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


# Kategorien, deren Treffer allein aus dem Sprachmodell stammen können und
# deshalb einer Plausibilitätsangabe bedürfen. Ein Telefonmuster oder eine
# IBAN ist dagegen aus sich heraus eindeutig.
_UNSICHER_MOEGLICH = {"PERSON", "PATIENT", "ARZT", "ORT", "ORGANISATION"}


def _ist_belegt(text: str, fund: Fund) -> bool:
    """Steht neben dem Treffer etwas, das ihn als Eigennamen bestätigt?

    Eine Anrede, ein akademischer Titel oder eine Rollenbezeichnung sind
    harte Belege. Ein Vorschlag des Sprachmodells ohne jeden solchen Beleg
    ist die häufigste Quelle von Fehlalarmen — gerade in Befundtext, der
    voller grossgeschriebener Fachbegriffe steckt.
    """
    if fund.typ not in _UNSICHER_MOEGLICH:
        return True
    if not fund.quelle.startswith("ner"):
        return True  # über Anrede oder Titel gefunden
    links = text[max(0, fund.start - 70):fund.start]
    rechts = text[fund.end:fund.end + 45]
    return bool(
        _ARZT_MARKER.search(links) or _ARZT_MARKER.search(rechts)
        or _PATIENT_MARKER.search(links) or _PATIENT_MARKER.search(rechts)
    )


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
    # Falsch heisst: allein vom Sprachmodell vorgeschlagen, ohne Anrede,
    # Titel oder anderen Kontextmarker. Solche Treffer werden trotzdem
    # ersetzt — sie sind aber die, bei denen sich das Nachsehen lohnt.
    sicher: bool = True

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


_NACHLAUF_TYPEN = {"PERSON", "PATIENT", "ARZT", "ORT", "ORGANISATION"}

# Gattungswörter aus Einrichtungsnamen. Sie benennen die Art des Hauses, nicht
# das einzelne Haus, und dürfen deshalb nicht als Einzelbegriff im Dokument
# nachgeschlagen werden — sonst wäre jedes "die Klinik" im Fliesstext ein
# Treffer.
# Gattungswörter, die einen Treffer als Haus ausweisen. Sie werden im ganzen
# Wort gesucht, weil sie im Deutschen meist angewachsen sind: "Neurozentrum"
# trägt "zentrum", "Rehaklinik" trägt "klinik".
_EINRICHTUNG_KERN = (
    "klinik", "krankenhaus", "spital", "hospital", "praxis", "zentrum",
    "institut", "ambulanz", "sanatorium", "poliklinik", "ärztehaus",
    "arztpraxis", "pflegeheim", "seniorenheim", "hospiz", "labor",
)

_EINRICHTUNGSWORT = {
    "klinik", "kliniken", "klinikum", "krankenhaus", "spital", "praxis",
    "zentrum", "institut", "abteilung", "ambulanz", "station", "haus",
    "gmbh", "ggmbh", "ag", "kg", "ohg", "mbh", "ev", "e.v", "kdör",
    "universität", "universitäts", "hochschule", "fakultät", "med",
    "neurologie", "neurologische", "neurologisches", "chirurgie", "innere",
    "medizin", "medizinische", "medizinisches", "rehaklinik", "reha",
    "fachklinik", "facharzt", "fachärztin", "gemeinschaftspraxis", "mvz",
    "der", "die", "das", "für", "und", "am", "an", "im", "in", "zu", "zum",
}


_EMAIL_TRENNER = re.compile(r"[._\-]+")


def _namen_aus_emails(text: str, gruppen: list[Gruppe]) -> list[str]:
    """Gewinnt Personennamen aus dem Ortsteil einer E-Mail-Adresse.

    Dienstliche Adressen sind fast immer nach Vorname.Nachname gebaut:
    konrad.weissbach@klinik.de, k.weissbach@…, weissbach.k@…. Die Adresse
    selbst wird ohnehin ersetzt — der Name darin verrät aber zusätzlich,
    wonach im übrigen Text zu suchen ist. Genau dort steht er oft ohne
    Titel und entgeht deshalb den anderen Regeln.

    Zurückgegeben werden nur Bestandteile, die tatsächlich wie ein Name
    aussehen: mindestens drei Buchstaben, kein Funktionswort wie "info",
    "praxis" oder "sekretariat".
    """
    unbrauchbar = {
        "info", "kontakt", "mail", "email", "post", "praxis", "kanzlei",
        "sekretariat", "empfang", "anmeldung", "verwaltung", "buchhaltung",
        "service", "support", "noreply", "no", "reply", "team", "office",
        "zentrale", "ambulanz", "station", "klinik", "klinikum", "labor",
        "abrechnung", "personal", "datenschutz", "webmaster", "admin",
    }

    kandidaten: list[str] = []
    for gruppe in gruppen:
        if gruppe.typ != "EMAIL":
            continue
        for fund in gruppe.funde:
            ortsteil = fund.text.split("@", 1)[0]
            for stueck in _EMAIL_TRENNER.split(ortsteil):
                stueck = stueck.strip()
                if len(stueck) < 3 or not stueck.isalpha():
                    continue
                if stueck.lower() in unbrauchbar:
                    continue
                # Im Text steht der Name gross geschrieben, in der Adresse
                # klein. Gesucht wird deshalb mit grossem Anfangsbuchstaben.
                name = stueck.capitalize()
                if re.search(rf"\b{re.escape(name)}\b", text):
                    kandidaten.append(name)
    return kandidaten


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

    # 2. Jede Variante — und zusätzlich ihre Bestandteile — im ganzen Text
    #    nachschlagen.
    #
    #    Bei Personen zählt jeder Namensteil, nicht nur der Nachname. Wer
    #    einmal als "Herr Peter Tisch" eingeführt wurde, ist auch dort
    #    gemeint, wo später bloss "Tisch" steht — selbst wenn das Wort für
    #    sich genommen ein Möbelstück ist. Der Beleg aus der Anrede wiegt
    #    schwerer als die Alltagsbedeutung. Trifft es einmal daneben, kann
    #    der Nutzer die Stelle einzeln wieder freigeben; die umgekehrte
    #    Reihenfolge — Name bleibt stehen, niemand merkt es — ist die
    #    gefährlichere.
    #
    #    Bei Einrichtungen ist es der Ortsteil: aus "Bezirksklinikum
    #    Stuttgart" wird auch das spätere blosse "Stuttgart" geschwärzt.
    for gruppe in gruppen:
        if gruppe.typ not in _NACHLAUF_TYPEN:
            continue
        begriffe = list(gruppe.varianten)
        if gruppe.typ in ("PERSON", "PATIENT", "ARZT"):
            for variante in gruppe.varianten:
                teile = variante.split()
                if len(teile) > 1:
                    begriffe.extend(
                        t for t in teile if not _ist_stoppwort(t))
        elif gruppe.typ == "ORGANISATION":
            for variante in gruppe.varianten:
                teile = [t.strip(",.") for t in variante.split()]
                # Das Gattungswort ("Klinikum", "Praxis") benennt keine
                # bestimmte Stelle und bliebe sonst überall hängen.
                begriffe.extend(
                    t for t in teile[1:]
                    if len(t) >= 4 and t[0].isupper()
                    and t.lower() not in _EINRICHTUNGSWORT
                    and not _ist_stoppwort(t))
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

    # Trägt ein Treffer ein Gattungswort für ein Haus, ist er eine
    # Einrichtung — auch wenn das Sprachmodell ihn für einen Ort oder eine
    # Person gehalten hat. "Sankt-Josef-Krankenhaus" und "Neurozentrum
    # Auwald" kamen beide als Ort an, und Orte bleiben in der
    # Standardstufe stehen. Die behandelnde Einrichtung ist aber ein
    # Hinweis auf die Person: wer sie kennt, hat das Feld erheblich
    # eingegrenzt. Deshalb wiegt das Gattungswort schwerer.
    for gruppe in liste:
        if gruppe.typ in ("ORT", "PERSON") and any(
                kern in gruppe.anzeige.lower() for kern in _EINRICHTUNG_KERN):
            gruppe.typ = "ORGANISATION"
            for fund in gruppe.funde:
                fund.typ = "ORGANISATION"

    # Namen aus E-Mail-Adressen als zusätzliche Gruppen, bevor der
    # Konsistenzlauf sie im ganzen Dokument nachschlägt.
    nach_schluessel = {g.schluessel: g for g in liste}
    vorhanden = set(nach_schluessel)
    for name in _namen_aus_emails(text, liste):
        if name.lower() in vorhanden:
            # Der Name ist schon bekannt — aber womöglich falsch einsortiert.
            # Das Sprachmodell hält Nachnamen regelmässig für Ortsnamen, und
            # Orte bleiben in der Standardstufe stehen. Wer in einer
            # dienstlichen E-Mail-Adresse steht, ist eine Person; dieser
            # Beleg wiegt schwerer als die Vermutung des Modells.
            treffer = nach_schluessel[name.lower()]
            if treffer.typ in ("ORT", "ORGANISATION"):
                treffer.typ = "PERSON"
            continue
        # Nur Stellen, die noch frei sind. `_entwirren` ist längst gelaufen,
        # diese Funde entstehen erst danach — ohne die Prüfung entstünden
        # überlappende Bereiche, und beim Ersetzen schöbe sich ein Platzhalter
        # in den anderen ("[ARZT_1]RSON_2]"). Der Nachname steckt regelmässig
        # in einem bereits erkannten vollen Namen: "Schmidt" aus
        # t.schmidt-wilcke@… liegt mitten in "T. Schmidt-Wilcke".
        vergeben = [(f.start, f.end) for g in liste for f in g.funde]
        funde = [
            Fund(t.start(), t.end(), t.group(0), "PERSON", "regex:email-ortsteil")
            for t in re.finditer(rf"\b{re.escape(name)}\b", text)
            if not any(t.start() < e and s < t.end() for s, e in vergeben)
        ]
        if not funde:
            continue
        neue_gruppe = Gruppe(
            id=f"e{len(liste)}", typ="PERSON", anzeige=name,
            schluessel=name.lower(), funde=funde,
        )
        liste.append(neue_gruppe)
        vorhanden.add(name.lower())
        # `nach_schluessel` muss mitwachsen: taucht derselbe Nachname aus
        # einer weiteren E-Mail-Adresse erneut auf (zwei verschiedene
        # Personen mit demselben Nachnamen — im 50-Seiten-Dokument keine
        # Seltenheit), griffe der Lookup oben sonst ins Leere, obwohl
        # `vorhanden` den Namen längst kennt: KeyError statt Ergebnis.
        # Die Zusammenführung selbst ist eine bekannte, akzeptierte Grenze
        # (siehe BACKLOG.md, "Gleiche Nachnamen sauber trennen") — hier geht
        # es nur darum, dass sie nicht abstürzt, sondern sich wie überall
        # sonst im Code verhält.
        nach_schluessel[name.lower()] = neue_gruppe

    liste = _konsistenz_nachlauf(text, liste)
    for gruppe in liste:
        gruppe.anzeige = max(gruppe.varianten, key=len)
        # Eine Gruppe gilt als belegt, sobald eine ihrer Fundstellen belegt
        # ist: wer einmal als "Frau Hartmann" auftaucht, ist auch dort eine
        # Person, wo der Nachname allein steht.
        gruppe.sicher = any(_ist_belegt(text, f) for f in gruppe.funde)
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
