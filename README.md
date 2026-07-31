# Anonymisator

Lokales Werkzeug, das Arztbriefe, Gutachten und Befunde von personenbeziehbaren
Angaben befreit. Läuft im Browser, aber vollständig auf dem eigenen Rechner —
kein Upload, kein Cloud-Dienst, keine Netzverbindung nötig.

```bash
./start.sh
```

Öffnet <http://127.0.0.1:5302>. Der Server bindet ausschliesslich an
`127.0.0.1` und ist im Netzwerk nicht erreichbar.

## Ablauf

1. **Einlesen** — PDF hineinziehen, Word-`.docx` hineinziehen oder Text einfügen.
   Bei PDFs ohne Textlayer wird automatisch per OCR gelesen (Tesseract, deutsch).
2. **Prüfen** — alle Fundstellen sind farbig markiert. In der Seitenleiste steht
   jede Gruppe mit Pseudonym; per Klick auf eine Markierung oder die Checkbox
   wird sie ab- oder wieder angewählt. Die Kategorie lässt sich korrigieren.
3. **Exportieren** — als PDF, Word oder Text. Immer ohne Metadaten.

## Was erkannt wird

| Kategorie | Beispiel | Pseudonym |
|---|---|---|
| Patient/in | Elisabeth Hartmann | `[PATIENT_A]` |
| Behandler/in | Prof. Dr. Weißbach | `[ARZT_1]` |
| Weitere Person | Angehörige, Betreuer | `[PERSON_1]` |
| Einrichtung | Neurologische Klinik am Auwald | `[KLINIK_1]` |
| Anschrift | Ludwigstraße 47, 94032 Passau | `[ADRESSE_1]` |
| Ort | Passau | `[ORT_1]` |
| Geburtsdatum | geb. 22.07.1958 | `[GEBDAT_1]` |
| Datum | 14.03.2026 | `[DATUM_1]` |
| Versichertennummer | M123456789 | `[VERSNR_1]` |
| Fall-/Patientennummer | 2026-KA-88213 | `[FALLNR_1]` |
| Aktenzeichen, IBAN, Telefon, E-Mail, URL | | |

Pseudonyme sind über das ganze Dokument konsistent: derselbe Name bekommt
überall dasselbe Kürzel, auch in Schreibvarianten. „Hartmann", „Elisabeth
Hartmann" und „E. Hartmann" landen in einer Gruppe.

Medizinische Fachbegriffe bleiben stehen. „Temporallappen" ist ein Ort im
Gehirn, kein Wohnort — ein Befund, in dem die Anatomie geschwärzt wurde, wäre
wertlos.

## Grenzen — bitte lesen

**Das Werkzeug garantiert keine Vollständigkeit.** Es kombiniert feste
Regeln mit einem statistischen Sprachmodell; beide können Stellen übersehen:

- Namen ohne Anrede und ohne Titel mitten im Fließtext
- OCR-Lesefehler in schlechten Scans (aus „Hartmann" wird „Hartrnann")
- ungewöhnliche Schreibweisen, Bindestrichnamen, fremdsprachige Namen
- indirekte Identifikatoren: eine sehr seltene Diagnose, ein ungewöhnlicher
  Beruf, eine markante Zeitangabe können eine Person auch ohne Namen
  erkennbar machen — dagegen hilft nur der eigene Kopf

Der Prüfschritt vor dem Export ist deshalb kein optionaler Komfort, sondern
der eigentliche Kern. Was dort niemand kontrolliert, geht ungeprüft hinaus.

Zwei bekannte Ungenauigkeiten:

- **Gleiche Nachnamen.** Steht „Hartmann" allein im Text und es gibt zwei
  Personen dieses Namens, wird die Stelle ersetzt, aber möglicherweise dem
  falschen Pseudonym zugeordnet. Datenschutz bleibt gewahrt, die Zuordnung
  kann kippen.
- **Spitznamen.** „Lisbeth" wird als eigene Person geführt, nicht als
  Variante von „Elisabeth Hartmann". Beide werden ersetzt, bekommen aber
  verschiedene Kürzel.

## Zuordnungstabelle

Über die Seitenleiste lässt sich eine CSV mit der Zuordnung Pseudonym →
Klarname herunterladen. Sie wird **nur auf ausdrücklichen Klick** erzeugt und
nirgends automatisch gespeichert.

Wer diese Datei neben dem anonymisierten Dokument ablegt, hebt die
Anonymisierung faktisch auf. Getrennt und geschützt aufbewahren — oder
gar nicht erst erzeugen.

## Datenfluss

Der Server ist zustandslos. Es gibt kein Upload-Verzeichnis, keine Session und
keine Datenbank. Jede Anfrage bringt ihren Text mit, die Antwort geht zurück,
danach bleibt nichts liegen. Dokumentinhalte werden nicht protokolliert.

Beim Export werden Metadaten aktiv geleert — Autor, Titel, Betreff,
Stichwörter. Ein anonymisiertes Dokument, in dessen Autorfeld noch der
Klarname steht, ist nicht anonymisiert.

## Einrichtung

Einmalig:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m spacy download de_core_news_lg
```

Für OCR gescannter PDFs zusätzlich Tesseract mit deutschem Sprachpaket:

```bash
brew install tesseract tesseract-lang
```

Ohne Tesseract funktioniert alles ausser gescannten PDFs.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `app/extract.py` | Text aus PDF, DOCX, OCR |
| `app/detect.py` | Erkennung: Regex-Regeln + spaCy-NER, Gruppierung, Pseudonyme |
| `app/export.py` | Ersetzung anwenden, TXT/DOCX/PDF schreiben |
| `app/main.py` | HTTP-Endpunkte |
| `static/` | Oberfläche (eine Seite, kein Framework) |

## Tests

```bash
.venv/bin/python tests/test_erkennung.py
```

Zeigt an einem erfundenen Arztbrief, was erkannt wird und wie das Ergebnis
aussieht. Nach jeder Änderung an den Erkennungsregeln durchsehen.

```bash
.venv/bin/python tests/test_e2e.py
```

Läuft gegen den gestarteten Server: PDF mit Textlayer, DOCX mit Kopfzeile,
gescanntes PDF über OCR, dann alle drei Exportformate. Der entscheidende
Test steht am Ende — er öffnet die fertigen Exportdateien inklusive
Metadaten und prüft, ob irgendwo noch ein Klarname steht.
