# Anonymisator

Lokales Werkzeug, das Dokumente von personenbeziehbaren Angaben befreit.
Läuft im Browser, aber vollständig auf dem eigenen Rechner — kein Upload,
kein Cloud-Dienst, keine Netzverbindung nötig.

Der Schwerpunkt liegt auf medizinischen Unterlagen — Arztbriefe, Befunde,
Gutachten. Rechnungen, Verträge und Behördenschreiben werden ebenso
abgedeckt: Rechnungs- und Kundennummern, Kontoverbindungen, Steuernummern,
Kfz-Kennzeichen und Geldbeträge sind eigene Kategorien.

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

## Stufen

Die Stufe ändert nicht, **was** gefunden wird, sondern **was damit geschieht**.
Die Erkennung läuft immer auf voller Schärfe; der Wechsel ist deshalb sofort
sichtbar, ohne neue Analyse.

| Kategorie | Leicht | Standard | Streng |
|---|---|---|---|
| Patient/in, Behandler/in | `E. H.` | `[PATIENT_A]` | `[PATIENT_A]` |
| Einrichtung, Firma | bleibt | `[ORG_1]` | `[ORG_1]` |
| Anschrift | Ort bleibt, Strasse raus | `[ADRESSE_1]` | `[ADRESSE_1]` |
| Ort | bleibt | bleibt | `[ORT_1]` |
| Geburtsdatum | `Jahrgang 1958` | `60–69 J.` | `[GEBDAT_1]` |
| Datum | bleibt | einheitlich verschoben | `[DATUM_1]` |
| Altersangabe im Text | bleibt | `60–69-jährige` | `[ALTER_1]` |
| Jahreszahl, Zeitraum | bleibt | bleibt | `[JAHR_1]`, `[ZEITRAUM_1]` |
| Geldbetrag | `2.108,68 €` | `rund 2.100 €` | `[BETRAG_1]` |
| Alle Kennnummern | ersetzt | ersetzt | ersetzt |

Die letzte Zeile ist auf allen Stufen starr und umfasst Versicherten-,
Sozialversicherungs-, Fall-, Rechnungs-, Kunden-, Konto-, Steuer-, Ausweis-
und Handelsregisternummer sowie Aktenzeichen, IBAN, Kfz-Kennzeichen, Telefon
und E-Mail. Diese Angaben identifizieren unmittelbar und tragen keinerlei
inhaltliche Information — sie „leicht" zu anonymisieren ergäbe keinen Sinn.

Geldbeträge sind der Gegenfall: Sie identifizieren nicht für sich, sind aber
in einer Rechnung der eigentliche Inhalt. In der Standardstufe werden sie
deshalb auf zwei signifikante Stellen gerundet — die Grössenordnung bleibt
ablesbar, die centgenaue Summe als Wiedererkennungsmerkmal verschwindet.

**Leicht ist keine Anonymisierung.** Initialen, Geburtsjahr, Einrichtung und
Behandlungszeitraum lassen zusammen regelmässig einen Rückschluss auf die
Person zu. Das Ergebnis bleibt im Sinne der DSGVO ein personenbezogenes Datum.
Für die interne Fallbesprechung ist das der richtige Weg — nur muss beim
Empfänger ankommen, was er in der Hand hält. Der Exportvermerk sagt es
deshalb ausdrücklich.

### Datumsverschiebung

In der Standardstufe werden alle Datumsangaben um denselben, je Dokument neu
gewürfelten Versatz verschoben (120 bis 400 Tage, in beide Richtungen). Die
absoluten Daten verschwinden, **die Abstände bleiben exakt erhalten**: aus
einem Aufenthalt vom 03.03. bis 12.03. wird einer vom 06.11. bis 15.11. —
dieselben neun Tage. Für Verlauf, Latenz und Aufenthaltsdauer bleibt das
Dokument damit auswertbar.

Der Versatz wird bei jeder Analyse neu gezogen. Zwei Dokumente derselben
Person, getrennt anonymisiert, lassen sich deshalb nicht über die Daten
zusammenführen — was gewollt ist, aber verhindert, dass man einen Verlauf
über mehrere Briefe hinweg rekonstruiert.

## Was erkannt wird

| Kategorie | Beispiel | Pseudonym |
|---|---|---|
| Patient/in | Elisabeth Hartmann | `[PATIENT_A]` |
| Behandler/in | Prof. Dr. Weißbach | `[ARZT_1]` |
| Weitere Person | Angehörige, Betreuer | `[PERSON_1]` |
| Einrichtung / Firma | Klinik am Auwald, Metallbau GmbH, Amtsgericht Passau | `[ORG_1]` |
| Anschrift | Ludwigstraße 47, 94032 Passau | `[ADRESSE_1]` |
| Ort | Passau | `[ORT_1]` |
| Geburtsdatum | geb. 22.07.1958 | `[GEBDAT_1]` |
| Datum | 14.03.2026 | `[DATUM_1]` |
| Versichertennummer | M123456789 | `[VERSNR_1]` |
| Fall-/Patientennummer | 2026-KA-88213 | `[FALLNR_1]` |
| Altersangabe | 67-jährige Patientin | `[ALTER_1]` |
| Zeitraum | seit 3 Jahren | `[ZEITRAUM_1]` |
| Jahreszahl | seit 1994 | `[JAHR_1]` |
| Aktenzeichen, IBAN, Telefon, E-Mail, URL | | |

Aus dem Geschäfts- und Behördenverkehr zusätzlich:

| Kategorie | Beispiel | Pseudonym |
|---|---|---|
| Rechnungs-/Belegnummer | Rechnungsnr. RE-2026-00842 | `[RECHNR_1]` |
| Kunden-/Vertragsnummer | Kundennummer KD-2026-4711 | `[KUNDENNR_1]` |
| Kontoverbindung | Kontonummer, BLZ, BIC | `[KONTO_1]` |
| Steuernummer | USt-IdNr. DE123456789 | `[STEUERNR_1]` |
| Sozialversicherungsnummer | 12 190367 K 123 | `[SVNR_1]` |
| Ausweisnummer | Personalausweis, Reisepass | `[AUSWEIS_1]` |
| Kfz-Kennzeichen | PA-XY 1234 | `[KFZ_1]` |
| Handelsregisternummer | HRB 12345 | `[HR_1]` |
| Geldbetrag | 2.108,68 € | `[BETRAG_1]` |

Auch Abrechnungs-, Auftrags-, Beleg-, Policen-, Schadens-, Personal- und
Mitgliedsnummern fallen unter die entsprechenden Kategorien.

Pseudonyme sind über das ganze Dokument konsistent: derselbe Name bekommt
überall dasselbe Kürzel, auch in Schreibvarianten. „Hartmann", „Elisabeth
Hartmann" und „E. Hartmann" landen in einer Gruppe.

Medizinische Fachbegriffe bleiben stehen. „Temporallappen" ist ein Ort im
Gehirn, kein Wohnort — ein Befund, in dem die Anatomie geschwärzt wurde, wäre
wertlos.

## Satzspiegel

Ein PDF kennt keine Absätze, nur Zeilen. Absatzabstände sind dort blosser
Weissraum und erzeugen keinen Text. Wer beides naiv übernimmt, bekommt einen
Klumpen ohne Absätze, in dem zugleich jede Zeile hart umbrochen ist — und
beim Export erneut umbricht, diesmal an anderer Stelle. Das Ergebnis sind
Flatterzeilen und einzelne Wörter auf eigener Zeile.

Deshalb zwei Schritte beim Einlesen:

1. Gelesen wird über die **Layoutblöcke** des PDFs. Bei Fliesstext entspricht
   ein Block einem Absatz — damit sind die Absatzgrenzen zurück.
2. Innerhalb eines Blocks werden Zeilen, die **bis an den Satzrand reichen**,
   wieder zusammengefügt. Eine kürzere Zeile beendet den Absatz.

Anschriftenblöcke, Unterschriftenzeilen, Überschriften und Aufzählungen
bestehen aus kurzen Zeilen und bleiben dadurch von allein unangetastet. Wirkt
ein Text gar nicht hart umbrochen, greift die Zusammenführung nicht.

Das Ergebnis lässt sich direkt in andere Werkzeuge kopieren, ohne dass man
Umbrüche von Hand entfernen muss. Nebenbei erkennt das Sprachmodell besser,
weil es vollständige Sätze sieht statt Zeilenfragmente.

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
| `app/extract.py` | Text aus PDF, DOCX, OCR; Absatzerkennung und Reflow |
| `app/detect.py` | Erkennung: Regex-Regeln + spaCy-NER, Gruppierung, Pseudonyme |
| `app/stufen.py` | Stufenmatrix, Datumsverschiebung, Initialen, Altersdekaden |
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

```bash
.venv/bin/python tests/test_stufen.py
```

Stellt denselben Brief in allen drei Stufen nebeneinander. Nach jeder
Änderung an der Stufenmatrix durchlesen — die Frage ist nicht, ob Zahlen
stimmen, sondern ob der Text für seinen Zweck noch taugt und sprachlich
sauber bleibt.

```bash
.venv/bin/python tests/test_formatierung.py
```

Prüft, dass der Satzspiegel den Weg durch das Programm übersteht: Absätze
bleiben erhalten, Anschriftenblöcke und Aufzählungen behalten ihre Zeilen,
und das Ersetzen verändert die Zeilenstruktur nicht.

```bash
.venv/bin/python tests/test_dokumenttypen.py
```

Prüft eine Rechnung und ein Unfallgutachten: Kennnummern müssen auf jeder
Stufe verschwinden, Geldbeträge stufengerecht behandelt werden, Firmen und
Gerichte als Organisation erkannt sein.

```bash
.venv/bin/python tests/test_e2e.py
```

Läuft gegen den gestarteten Server: PDF mit Textlayer, DOCX mit Kopfzeile,
gescanntes PDF über OCR, dann alle drei Exportformate. Der entscheidende
Test steht am Ende — er öffnet die fertigen Exportdateien inklusive
Metadaten und prüft, ob irgendwo noch ein Klarname steht.
