"""Prüft die seitenweise OCR-Entscheidung und den neutralen Exportnamen.

Läuft ohne Server: `app.extract` und `app.main.exportieren` werden direkt
aufgerufen. Alle Texte sind frei erfunden.

Der Kern ist die Frage, ob eine Seite still verloren geht. Ein PDF aus
Textseite plus eingescannter Anlage darf nicht als "Textlayer" durchgehen,
und ein Textlayer aus Zeichensalat darf nicht ungeprüft in die Erkennung.
"""
import asyncio
import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import extract, main

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


BRIEF = (
    "Sehr geehrte Frau Kollegin, wir berichten über die stationäre "
    "Behandlung unserer Patientin vom 03.03. bis 17.03. Die Aufnahme erfolgte "
    "bei zunehmenden Kopfschmerzen und Übelkeit. Im MRT zeigte sich eine "
    "Läsion im linken Temporallappen. Laborwerte: CRP 4,2 mg/l, Kalium 3,9 "
    "mmol/l, Hämoglobin 13,1 g/dl. Wir empfehlen eine Kontrolle in drei Monaten."
)
SCAN = (
    "Befundbericht Radiologie. Untersuchung des Schädels ohne und mit "
    "Kontrastmittel. Beurteilung: kein Hinweis auf eine frische Blutung, "
    "stabile Läsion temporal links, keine Raumforderung mit Mittellinienshift."
)


def textseite(doc, text, fontsize=11):
    seite = doc.new_page()
    seite.insert_textbox(fitz.Rect(50, 60, 545, 780), text, fontsize=fontsize)
    return seite


def bildseite(doc, text):
    """Seite, deren Inhalt nur als Pixelbild vorliegt (Scan)."""
    with fitz.open() as quelle:
        textseite(quelle, text, fontsize=14)
        pix = quelle[0].get_pixmap(dpi=200)
    seite = doc.new_page()
    seite.insert_image(seite.rect, stream=pix.tobytes("png"))
    return seite


def leere_bildseite(doc):
    with fitz.open() as quelle:
        quelle.new_page()
        pix = quelle[0].get_pixmap(dpi=100)
    seite = doc.new_page()
    seite.insert_image(seite.rect, stream=pix.tobytes("png"))


print("a) Gemischtes PDF: Textseite + Scanseite")
with fitz.open() as doc:
    textseite(doc, BRIEF)
    bildseite(doc, SCAN)
    erg = extract.aus_pdf(doc.tobytes())
pruefe(erg.quelle == "pdf-gemischt", f"Quelle gemischt (war: {erg.quelle})")
pruefe("Temporallappen" in erg.text and "CRP" in erg.text, "Text von Seite 1 enthalten")
pruefe("Radiologie" in erg.text and "Kontrastmittel" in erg.text,
       "Text von Seite 2 (OCR) enthalten")
pruefe("Temporallappen" in erg.text and "Radiologie" in erg.text
       and erg.text.index("Temporallappen") < erg.text.index("Radiologie"),
       "Reihenfolge der Seiten erhalten")
pruefe(any("Seite 2" in h and "kein Textlayer" in h for h in erg.hinweise),
       f"Hinweis nennt Seite 2 und den Grund (Hinweise: {erg.hinweise})")
pruefe(not any("Seite 1" in h for h in erg.hinweise), "Seite 1 wird nicht beanstandet")

print("b) Textlayer-PDF mit kurzer letzter Seite ohne Bild")
with fitz.open() as doc:
    textseite(doc, BRIEF)
    textseite(doc, BRIEF)
    textseite(doc, "Mit freundlichen Grüssen")
    erg = extract.aus_pdf(doc.tobytes())
pruefe(erg.quelle == "pdf-textlayer", f"Quelle Textlayer (war: {erg.quelle})")
pruefe("Grüssen" in erg.text, "Grussformel der letzten Seite enthalten")
pruefe(not any("OCR" in h for h in erg.hinweise), "kein OCR-Hinweis")

print("c) Reiner Scan")
with fitz.open() as doc:
    bildseite(doc, SCAN)
    bildseite(doc, SCAN)
    erg = extract.aus_pdf(doc.tobytes())
pruefe(erg.quelle == "pdf-ocr", f"Quelle OCR (war: {erg.quelle})")
pruefe("Radiologie" in erg.text, "OCR-Text enthalten")
pruefe(any("per OCR gelesen" in h for h in erg.hinweise), "Hinweis auf OCR vorhanden")

print("d) _textlayer_brauchbar")
brauchbar = extract._textlayer_brauchbar
pruefe(brauchbar(BRIEF), "deutscher Brieftext mit Umlauten und Laborwerten")
MEDI = (
    "Medikation bei Entlassung:\n"
    "Nr. | Präparat | Dosis | Zeit\n"
    "1) Ramipril 5 mg 1-0-0 (p.o.)\n"
    "2) Metformin 850 mg 1-0-1 (p.o.)\n"
    "3) ASS 100 mg 0-1-0 – nach dem Essen\n"
    "4) Pantoprazol 40 mg 1-0-0 • 30 min vor dem Essen\n"
    "5) Vitamin D 20.000 I.E. 1x/Woche; Kalium 3,9–4,8 mmol/l; GFR ≥ 60 ml/min\n"
    "Temperatur 36,8 °C, RR 130/80 mmHg ± 5, Gewicht 82 kg, Preis 12,50 €, § 31 SGB V"
)
pruefe(brauchbar(MEDI), "Medikationstabelle mit Ziffern und Sonderzeichen (kein Fehlalarm)")
pruefe(not brauchbar("�" * 60 + " abc " + "�" * 60), "Zeichensalat aus U+FFFD")
pruefe(not brauchbar("".join(chr(0xE000 + i % 200) for i in range(250))),
       "Zeichensalat aus Private-Use-Zeichen")
pruefe(not brauchbar("Жзиф世界你好ΩΨλ " * 20), "Mischung aus Kyrillisch, CJK und Griechisch")
pruefe(not brauchbar("Kurzer Text."), "zu kurzer Text")
pruefe(not brauchbar("   \n  " * 50), "nur Leerraum")

print("e) Bildseite ohne erkennbaren Text")
with fitz.open() as doc:
    textseite(doc, BRIEF)
    textseite(doc, BRIEF)
    leere_bildseite(doc)
    erg = extract.aus_pdf(doc.tobytes())
pruefe(any("Seite 3" in h and "kein Text gewonnen" in h for h in erg.hinweise),
       f"Hinweis 'kein Text gewonnen' für Seite 3 (Hinweise: {erg.hinweise})")
pruefe("Temporallappen" in erg.text, "Text der übrigen Seiten bleibt erhalten")
with fitz.open() as doc:
    leere_bildseite(doc)
    erg = extract.aus_pdf(doc.tobytes())
pruefe(any("kein Text gewonnen" in h for h in erg.hinweise),
       "Hinweis auch im reinen OCR-Pfad")

print("f) Exportdateiname neutral")
ein = main.ExportEingabe(
    text="Frau [PATIENT_A]", ersetzungen=[], format="txt",
    dateiname="Musterfrau_Erika_Brief",
)
antwort = asyncio.run(main.exportieren(ein))
kopf = antwort.headers["content-disposition"]
pruefe("Musterfrau" not in kopf and "Erika" not in kopf,
       f"Originalname nicht im Header ({kopf})")
pruefe(kopf == 'attachment; filename="dokument_anonymisiert.txt"',
       "fester neutraler Name")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
