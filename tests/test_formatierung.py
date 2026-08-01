"""Prüft, dass der Satzspiegel den Weg durch das Programm überlebt.

Ein PDF kennt keine Absätze, nur Zeilen. Werden diese Zeilenenden als feste
Umbrüche mitgeschleppt, kommt beim Export zerrissener Flattersatz heraus —
und zwar besonders dann, wenn ein Pseudonym eine andere Länge hat als der
ersetzte Klarname.
"""
import io
import sys
from pathlib import Path

import fitz
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, extract, stufen

ANREDE = "Sehr geehrte Frau Kollegin Brandner,"
FLIESSTEXT = [
    "wir berichten über unsere gemeinsame Patientin Frau Elisabeth Hartmann, "
    "geb. 22.07.1958, die sich vom 03.03.2026 bis zum 12.03.2026 in unserer "
    "stationären Behandlung befand. Die Aufnahme erfolgte über die Notaufnahme "
    "nach einem erstmaligen generalisierten tonisch-klonischen Anfall, den der "
    "Ehemann beobachtet hatte und der etwa zwei Minuten angedauert haben soll.",

    "In der Vorgeschichte findet sich eine seit mehreren Jahren bestehende "
    "arterielle Hypertonie, die mit einem ACE-Hemmer behandelt wird. Eine "
    "vergleichbare Episode war bislang nicht aufgetreten. Die Familienanamnese "
    "bezüglich epileptischer Anfälle ist unauffällig.",

    "Das EEG vom 05.03.2026 zeigte intermittierende rhythmische Verlangsamungen "
    "über den linken temporalen Ableitungen ohne Nachweis epilepsietypischer "
    "Potentiale. Die MRT des Neurocraniums ergab eine umschriebene Läsion im "
    "linken Hippocampus, vereinbar mit einer Hippocampussklerose.",
]
BLOECKE = ["Neurologische Klinik am Auwald", "Ludwigstraße 47, 94032 Passau", "",
           ANREDE, "", FLIESSTEXT[0], "", FLIESSTEXT[1], "",
           "Diagnosen:", "1. Fokale Epilepsie", "2. Arterielle Hypertonie", "",
           FLIESSTEXT[2], "", "Mit freundlichen Grüßen",
           "Prof. Dr. med. Konrad Weißbach"]

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def quell_pdf() -> bytes:
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4, leftMargin=25 * mm,
                            rightMargin=20 * mm, topMargin=20 * mm)
    stil = ParagraphStyle("K", fontName="Helvetica", fontSize=10.5, leading=15)
    doc.build([Paragraph(b, stil) if b else Spacer(1, 8) for b in BLOECKE])
    return puffer.getvalue()


def zeilen_von(text: str) -> list[str]:
    return [z for z in text.split("\n") if z.strip()]


print("\n=== 1. Extraktion: Absätze statt Zeilen ===")
auszug = extract.aus_pdf(quell_pdf())
text = auszug.text

pruefe("\n\n" in text, "Absatzgrenzen sind erhalten")

for i, absatz in enumerate(FLIESSTEXT, start=1):
    anfang = absatz[:40]
    passende = [b for b in text.split("\n\n") if anfang in b]
    pruefe(len(passende) == 1, f"Fliesstext-Absatz {i} liegt in genau einem Block")
    if passende:
        pruefe("\n" not in passende[0].strip(),
               f"Absatz {i} ist durchgehend, ohne harte Umbrüche")

pruefe(any((b.strip().startswith("Neurologische Klinik") and "\n" in b.strip())
           or b.strip() == "Neurologische Klinik am Auwald"
           for b in text.split("\n\n")),
       "Briefkopf wurde nicht in den Fliesstext gezogen")
pruefe("1. Fokale Epilepsie" in text and "2. Arterielle Hypertonie" in text,
       "Aufzählungspunkte stehen weiterhin einzeln")
zeile_mit_aufzaehlung = [z for z in zeilen_von(text) if z.startswith("1. Fokale")]
pruefe(zeile_mit_aufzaehlung and zeile_mit_aufzaehlung[0].strip() == "1. Fokale Epilepsie",
       "Aufzählungspunkt wurde nicht an die Überschrift angehängt")

print("\n=== 2. Gegenprobe: sauberer Text bleibt unangetastet ===")
sauber = "\n\n".join(FLIESSTEXT)
pruefe(extract.aus_text(sauber).text.count("\n\n") == 2,
       "Bereits gesetzter Text wird nicht umgebaut")

kurz = "Praxis Dr. Ostermeier\nBahnhofstraße 3\n94032 Passau\nTel. 0851 12345"
pruefe(extract.aus_text(kurz).text.count("\n") == 3,
       "Anschriftenblock behält seine Zeilen")

print("\n=== 3. Nach der Anonymisierung: kein Flattersatz ===")
gruppen = detect.analysiere(text)
stufen.formen_berechnen(gruppen)
matrix = stufen.STUFEN["streng"]
ersetzungen = [
    {"start": f.start, "ende": f.end, "label": g.label}
    for g in gruppen for f in g.funde
    if matrix.get(g.typ, "ersetzen") != "behalten"
]
anonym = export.ersetze(text, ersetzungen)

vorher = [b for b in text.split("\n\n") if b.strip()]
absaetze = [b for b in anonym.split("\n\n") if b.strip()]
pruefe(len(absaetze) >= 6, f"{len(absaetze)} Absätze erhalten")

# Der eigentliche Prüfpunkt: das Ersetzen darf den Satzspiegel nicht
# verändern. Ein kurzer Briefkopf bleibt kurz, ein Fliesstextabsatz bleibt
# eine durchgehende Zeile — unabhängig davon, wie lang das Pseudonym ist.
pruefe(len(vorher) == len(absaetze),
       f"Absatzzahl unverändert ({len(vorher)} → {len(absaetze)})")

abweichend = [
    i for i, (alt, neu) in enumerate(zip(vorher, absaetze), start=1)
    if alt.count("\n") != neu.count("\n")
]
pruefe(not abweichend,
       f"Zeilenstruktur je Absatz unverändert{f' — abweichend: {abweichend}' if abweichend else ''}")

fliesstext = [b for b in absaetze if len(b) > 150]
pruefe(all("\n" not in b.strip() for b in fliesstext),
       f"Die {len(fliesstext)} Fliesstextabsätze bleiben durchgehend")

print("\n=== 4. Export: Satzspiegel im Zieldokument ===")
pdf_daten = export.als_pdf(anonym, mit_kopfzeile=False)
with fitz.open(stream=pdf_daten, filetype="pdf") as doc:
    bloecke = [b[4].strip() for seite in doc
               for b in seite.get_text("blocks", sort=True)
               if len(b) < 7 or b[6] == 0]
    bloecke = [b for b in bloecke if b]

pruefe(abs(len(bloecke) - len(absaetze)) <= 1,
       f"PDF hat {len(bloecke)} Blöcke bei {len(absaetze)} Absätzen")

# Nur die Fliesstextblöcke prüfen: Briefkopf, Überschrift und Aufzählung
# bestehen zu Recht aus kurzen Zeilen.
flatter = []
for block in bloecke:
    zeilen = [z for z in block.split("\n") if z.strip()]
    if len(zeilen) < 3 or len(block) < 150:
        continue
    breite = max(len(z) for z in zeilen)
    # Jede Zeile ausser der letzten muss den Satzspiegel ausnutzen. Eine
    # kurze Zeile mittendrin heisst, dass ein Umbruch erzwungen wurde.
    flatter += [z for z in zeilen[:-1] if len(z) < breite * 0.7]
pruefe(not flatter,
       f"Fliesstext im PDF läuft bis an den Rand{f' — gerissen: {flatter}' if flatter else ''}")

txt = export.als_txt(anonym, mit_kopfzeile=False).decode()
lange = [z for z in zeilen_von(txt) if len(z) > 150]
pruefe(len(lange) >= 3,
       f"TXT liefert durchgehende Absätze zum Kopieren ({len(lange)} lange Zeilen)")

print("\n=== 5. Kliniksoftware-Bauart: Zeile für Zeile gesetzt ===")

# Der Fall, an dem die frühere Fassung scheiterte. Kliniksoftware setzt
# Arztbriefe nicht als Fliesstext, sondern platziert jede Zeile einzeln.
# Zusammen mit Medikationsplan und Diagnosenliste überwiegen die kurzen
# Zeilen — eine Zusammenführung nach Zeichenlänge greift dort nicht mehr.
KLINIK_ZEILEN = [
    "Neurologische Klinik am Auwald", "Ludwigstraße 47 · 94032 Passau", "",
    "Frau", "Dr. med. Ingrid Brandner", "Bahnhofstraße 3", "94032 Passau", "",
    "Patientin: Elisabeth Hartmann, geb. 22.07.1958",
    "Fallnummer: 2026-KA-88213", "",
    "Sehr geehrte Frau Kollegin Brandner,", "",
    "wir berichten Ihnen über unsere gemeinsame Patientin Frau Elisabeth",
    "Hartmann, die sich vom 03.03.2026 bis zum 12.03.2026 in unserer",
    "stationären Behandlung befand. Die Aufnahme erfolgte über die",
    "Notaufnahme nach einem erstmaligen generalisierten Anfall.", "",
    "Diagnosen:", "1. Fokale Epilepsie", "2. Arterielle Hypertonie", "",
    "Medikation bei Entlassung:", "Ramipril 5 mg 1-0-0",
    "Levetiracetam 500 mg 1-0-1", "",
    "Mit freundlichen Grüßen", "Prof. Dr. med. Konrad Weißbach",
]

doc = fitz.open()
blatt = doc.new_page(width=595, height=842)
hoehe = 70
for zeile in KLINIK_ZEILEN:
    if zeile:
        blatt.insert_text((70, hoehe), zeile, fontname="helv", fontsize=10)
    hoehe += 14.5
klinik_pdf = doc.tobytes()
doc.close()

klinik = extract.aus_pdf(klinik_pdf).text
klinik_absaetze = [a for a in klinik.split("\n\n") if a.strip()]

fliess_absatz = [a for a in klinik_absaetze if "wir berichten" in a]
pruefe(len(fliess_absatz) == 1 and "\n" not in fliess_absatz[0].strip(),
       "Fliesstext ist eine durchgehende Zeile, trotz vieler Kurzzeilen ringsum")

kopf = [a for a in klinik_absaetze if a.startswith("Neurologische")]
pruefe(kopf and kopf[0].count("\n") == 1, "Briefkopf behält seine zwei Zeilen")

anschrift = [a for a in klinik_absaetze if a.startswith("Frau\n")]
pruefe(anschrift and anschrift[0].count("\n") == 3,
       "Empfängeranschrift behält alle vier Zeilen")

medikation = [a for a in klinik_absaetze if "Ramipril" in a]
pruefe(medikation and medikation[0].count("\n") == 2,
       "Medikationsplan bleibt zeilenweise")

pruefe("Ramipril 5 mg 1-0-0" in klinik and "Levetiracetam 500 mg 1-0-1" in klinik,
       "Wirkstoffzeilen sind unversehrt")

# Wirkstoffe sind keine Organisationen — sonst steht "[ORG_2] mg 1-0-0"
# im fertigen Brief.
klinik_gruppen = detect.analysiere(klinik)
wirkstoff_treffer = [
    f.text for g in klinik_gruppen for f in g.funde
    if "Ramipril" in f.text or "Levetiracetam" in f.text
]
pruefe(not wirkstoff_treffer,
       f"Wirkstoffnamen werden nicht als Entität erkannt{f' — {wirkstoff_treffer}' if wirkstoff_treffer else ''}")

# Anschriftenzeilen dürfen beim Ersetzen nicht verschmelzen: ein Muster mit
# \s am Ende verschluckt sonst den Zeilenumbruch gleich mit.
stufen.formen_berechnen(klinik_gruppen)
klinik_ersetzt = export.ersetze(klinik, [
    {"start": f.start, "ende": f.end, "label": g.label}
    for g in klinik_gruppen for f in g.funde
    if stufen.STUFEN["streng"].get(g.typ, "ersetzen") != "behalten"
])
pruefe("][" not in klinik_ersetzt,
       "Keine zwei Platzhalter ohne Trennung aneinander")

print("\n=== 6. Zweispaltiger Kopf und breite Fusszeile ===")

# Beides ist im Klinikalltag die Regel und brachte die frühere Fassung zu
# Fall: der zweispaltige Kopf, weil eine seitenweite Sortierung nach Höhe
# beide Spalten ineinander verschränkt; die Fusszeile, weil sie weiter nach
# rechts reicht als der Fliesstext und damit den geschätzten Satzrand
# verschiebt — dann gilt jede Zeile als freiwillig beendet.
KOPF_LINKS = ["Neurologische Klinik am Auwald", "", "Frau",
              "Dr. med. Ingrid Brandner", "Bahnhofstraße 3", "94032 Passau"]
KOPF_RECHTS = ["Ansprechpartner:", "Prof. Dr. Weißbach",
               "Durchwahl: 0851 4409-233", "", "Passau, 14.03.2026"]
KOERPER = ["Sehr geehrte Frau Kollegin Brandner,", "", "wir berichten Ihnen über unsere gemeinsame Patientin Frau Elisabeth", "Hartmann, die sich vom 03.03.2026 bis zum 12.03.2026 in unserer", "stationären Behandlung befand. Die Aufnahme erfolgte über die", "Notaufnahme nach einem erstmaligen generalisierten Anfall."]
FUSS = [
    "Neurologische Klinik am Auwald · Ludwigstraße 47 · 94032 Passau · "
    "Tel. 0851 4409-233 · Fax 0851 4409-234 · info@klinik-auwald.de",
    "Bankverbindung: Sparkasse Passau · IBAN DE89 3704 0044 0532 0130 00 · "
    "BIC COBADEFFXXX · Steuernummer 153/815/47110",
]


def brief_mit(zweite_spalte: bool, fusszeile: bool) -> bytes:
    schrift = fitz.open()
    blatt = schrift.new_page(width=595, height=842)
    hoehe = 70
    for zeile in KOPF_LINKS:
        if zeile:
            blatt.insert_text((70, hoehe), zeile, fontname="helv", fontsize=10)
        hoehe += 14.5
    if zweite_spalte:
        hoehe = 70
        for zeile in KOPF_RECHTS:
            if zeile:
                blatt.insert_text((360, hoehe), zeile, fontname="helv", fontsize=9)
            hoehe += 13
    hoehe = 190
    for zeile in KOERPER:
        if zeile:
            blatt.insert_text((70, hoehe), zeile, fontname="helv", fontsize=10)
        hoehe += 14.5
    if fusszeile:
        for i, zeile in enumerate(FUSS):
            blatt.insert_text((40, 780 + i * 12), zeile, fontname="helv", fontsize=7)
    roh = schrift.tobytes()
    schrift.close()
    return roh


for beschreibung, zweite, fuss in [
    ("schlicht", False, False),
    ("zweispaltiger Kopf", True, False),
    ("breite Fusszeile", False, True),
    ("beides zusammen", True, True),
]:
    ergebnis = extract.aus_pdf(brief_mit(zweite, fuss)).text
    koerper = [a for a in ergebnis.split("\n\n") if "wir berichten" in a]
    pruefe(len(koerper) == 1 and "\n" not in koerper[0].strip(),
           f"Fliesstext bleibt zusammenhängend — {beschreibung}")

# Die beiden Kopfspalten dürfen nicht ineinandergeraten.
zweispaltig = extract.aus_pdf(brief_mit(True, False)).text
pruefe("Brandner\nAnsprechpartner" not in zweispaltig
       and "Auwald\nAnsprechpartner" not in zweispaltig,
       "Kopfspalten wurden nicht zeilenweise verschränkt")

print("\n=== 7. Blocksatz: jedes Wort einzeln gesetzt ===")

# Der schwerste Fall. Um die Wortabstände zu strecken, setzt die erzeugende
# Software im Blocksatz jedes Wort an eine eigene berechnete Position.
# PyMuPDF meldet diese Wörter als eigene Zeilen — allesamt auf derselben
# Höhe. Wer das für Zeilenumbrüche hält, zerlegt den Absatz in einzelne
# Wörter untereinander.
BLOCKSATZ_1 = [
    "Weiterhin berichtete der Patient über episodisch auftretende, vorwiegend kälteinduzierte",
    "schmerzhafte Missempfindungen im Bereich der Zehen und Vorfüße beidseits mit begleitenden",
    "Schwellungen, lividen Verfärbungen sowie zeitweiligen Hautveränderungen. Die Beschwerden",
    "traten insbesondere während der kalten Jahreszeit auf und wurden durch Kälteexposition",
    "Beschwerden wurden verneint.",
]
BLOCKSATZ_2 = [
    "Klinisch-neurologisch zeigte sich weiterhin ein distal betontes, symmetrisches",
    "sensomotorisches polyneuropathisches Syndrom ohne Nachweis relevanter motorischer",
    "Defizite mit leichter Hohlfußstellung bds. Aufgrund der bislang ungeklärten Ätiologie",
    "erfolgte die stationäre weiterführende neurologische Diagnostik.",
]


def blocksatz_pdf() -> tuple[bytes, int]:
    schrift = fitz.open()
    blatt = schrift.new_page(width=595, height=842)
    links, rechts, groesse = 70, 525, 9
    hoehe = 80
    for absatz in (BLOCKSATZ_1, BLOCKSATZ_2):
        for i, zeile in enumerate(absatz):
            woerter = zeile.split()
            breiten = [fitz.get_text_length(w, "helv", groesse) for w in woerter]
            if i == len(absatz) - 1 or len(woerter) < 2:
                blatt.insert_text((links, hoehe), zeile,
                                  fontname="helv", fontsize=groesse)
            else:
                luecke = (rechts - links - sum(breiten)) / (len(woerter) - 1)
                x = links
                for wort, breite in zip(woerter, breiten):
                    blatt.insert_text((x, hoehe), wort,
                                      fontname="helv", fontsize=groesse)
                    x += breite + luecke
            hoehe += 13
        hoehe += 13
    roh = schrift.tobytes()
    schrift.close()
    with fitz.open(stream=roh, filetype="pdf") as auf:
        zeilenzahl = sum(len(b["lines"]) for b in auf[0].get_text("dict")["blocks"]
                         if b.get("type", 0) == 0)
    return roh, zeilenzahl


daten, rohzeilen = blocksatz_pdf()
echte_zeilen = len(BLOCKSATZ_1) + len(BLOCKSATZ_2)
pruefe(rohzeilen > echte_zeilen * 3,
       f"Vorbedingung: PyMuPDF meldet {rohzeilen} Roh-Zeilen für "
       f"{echte_zeilen} echte — der Blocksatz ist nachgebildet")

blocksatz = extract.aus_pdf(daten).text
bs_absaetze = [a for a in blocksatz.split("\n\n") if a.strip()]

pruefe(len(bs_absaetze) == 2, f"Zwei Absätze erkannt (waren: {len(bs_absaetze)})")
pruefe(all("\n" not in a.strip() for a in bs_absaetze),
       "Jeder Absatz ist eine durchgehende Zeile")
pruefe(blocksatz.startswith("Weiterhin berichtete der Patient über"),
       "Erste Zeile ist nicht in Einzelwörter zerfallen")
pruefe("kälteinduzierte schmerzhafte" in blocksatz,
       "Zeilenübergang wurde mit Leerzeichen verbunden")
pruefe("Weiterhinberichtete" not in blocksatz and "  " not in blocksatz,
       "Wörter sind weder verklebt noch doppelt getrennt")

# Blocksatz darf nicht mit Spaltensatz verwechselt werden: seine Lücken sind
# gleichmässig, die einer Tabelle haben einen Ausreisser.
pruefe(not extract._spaltig([16.0, 16.4, 15.8, 16.2], 11.0),
       "Gleichmässig gestreckte Lücken gelten nicht als Tabelle")
pruefe(extract._spaltig([2.5, 3.0, 61.0, 2.8], 11.0),
       "Ein einzelner Lückenausreisser gilt als Tabelle")
pruefe(extract._spaltig([58.0], 11.0),
       "Eine einzelne sehr weite Lücke gilt als Tabelle")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
