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

from app import detect, export, extract, stufen  # noqa: E402

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

pruefe(any(b.strip().startswith("Neurologische Klinik") and "\n" in b.strip()
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

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
