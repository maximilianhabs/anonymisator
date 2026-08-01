# Anonymisator

[![Lizenz: Apache 2.0](https://img.shields.io/badge/Lizenz-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.7.0-informational.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](#einrichtung)

Lokales Werkzeug, das deutschsprachige Dokumente von personenbeziehbaren
Angaben befreit. Läuft im Browser, aber vollständig auf dem eigenen Rechner —
kein Upload, kein Cloud-Dienst, keine Netzverbindung nötig.

Der Schwerpunkt liegt auf medizinischen Unterlagen — Arztbriefe, Befunde,
Gutachten. Rechnungen, Verträge und Behördenschreiben werden ebenso
abgedeckt: Rechnungs- und Kundennummern, Kontoverbindungen, Steuernummern,
Kfz-Kennzeichen und Geldbeträge sind eigene Kategorien.

## Für wen

Für Ärztinnen und Ärzte, Gutachterinnen und Gutachter sowie Forschende, die
einzelne Dokumente für **Lehre, Fallvorstellung, Supervision oder eine
Publikation** von Personenbezug befreien müssen und dabei nichts aus der Hand
geben wollen. Der typische Fall ist ein einzelner Arztbrief, der morgen in
einer Fortbildung gezeigt werden soll.

Ausdrücklich **nicht** gedacht als:

- Verfahren zur Freigabe grosser Datenbestände für die Sekundärforschung —
  dafür fehlt jede statistische Absicherung gegen Re-Identifikation
- unbeaufsichtigte Stapelverarbeitung; der manuelle Prüfschritt ist
  Bestandteil des Verfahrens, nicht optionaler Komfort
- Medizinprodukt oder zertifiziertes Werkzeug im Sinne der MDR

## Schnellstart

```bash
git clone https://github.com/maximilianhabs/anonymisator.git
cd anonymisator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./start.sh
```

Öffnet <http://127.0.0.1:5302>. Der Server bindet ausschliesslich an
`127.0.0.1` und ist im Netzwerk nicht erreichbar.

## Beispiel

Eingang — ein frei erfundener Arztbrief:

```
Neurologische Klinik am Auwald
Ludwigstraße 47, 94032 Passau

Sehr geehrte Frau Kollegin Brandner,

wir berichten über Ihre Patientin Frau Elisabeth Hartmann,
geb. 22.07.1958, wohnhaft Rosenweg 12, 94469 Deggendorf,
Versichertennummer M123456789. Die 67-jährige Patientin befand
sich vom 03.03.2026 bis 12.03.2026 in unserer stationären
Behandlung. Das MRT zeigte eine Läsion im linken Temporallappen.

Mit freundlichen Grüßen
Prof. Dr. med. Konrad Weißbach
```

Ausgang, Stufe **Standard** (Datumsversatz in diesem Lauf +187 Tage):

```
[ORG_1]
[ADRESSE_1], [ADRESSE_2]

Sehr geehrte Frau Kollegin [ARZT_1],

wir berichten über Ihre Patientin Frau [PATIENT_A], 60–69 J., wohnhaft
[ADRESSE_3], [ADRESSE_4], Versichertennummer [VERSNR_1]. Die 60–69-jährige
Patientin befand sich vom 06.09.2026 bis 15.09.2026 in unserer stationären
Behandlung. Das MRT zeigte eine Läsion im linken Temporallappen.

Mit freundlichen Grüßen
Prof. Dr. med. [ARZT_2]
```

Drei Dinge sind hier wesentlich. Die Behandlungsdaten sind verschoben, aber
die **neun Tage Aufenthaltsdauer bleiben erhalten**. Der medizinische Inhalt —
„Läsion im linken Temporallappen" — steht unangetastet da; ein Befund mit
geschwärzter Anatomie wäre wertlos. Und die harten Zeilenumbrüche der Vorlage
sind zu durchgehenden Absätzen zusammengefügt, damit sich das Ergebnis ohne
Nacharbeit weiterverwenden lässt (siehe [Satzspiegel](#satzspiegel)).

Der Versatz wird bei jedem Durchlauf neu gezogen; dieselbe Datei zweimal
anonymisiert ergibt verschiedene Datumsangaben.

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

Der Text wird deshalb aus der **Geometrie der Seite** neu gesetzt, nicht aus
den ausgelesenen Zeichen geraten:

1. **Absatzgrenze** — der senkrechte Abstand zur Vorzeile. Ist er deutlich
   grösser als der übliche Zeilenabstand, beginnt ein neuer Absatz.
2. **Weicher Umbruch** — hätte das erste Wort der Folgezeile am Ende der
   aktuellen Zeile noch aufs Papier gepasst? Wenn nein, wurde hier
   umbrochen und beide Zeilen gehören zusammen. Wenn ja, endete der Absatz.

Der zweite Test ist der entscheidende, und er kommt bewusst ohne Zeichen­zählen
aus. Ein Arztbrief besteht überwiegend aus **kurzen** Zeilen — Briefkopf,
Anschrift, Datenblock, Diagnosenliste, Medikationsplan, Unterschrift. Ein
Verfahren, das aus der Häufigkeit langer Zeilen auf harten Umbruch schliesst,
versagt dort und lässt den Brief zerhackt. Die Geometrie kennt die Antwort
dagegen für jede Zeile einzeln.

Davor steht allerdings noch ein Schritt, ohne den alles Weitere ins Leere
läuft: **Bruchstücke derselben Textzeile müssen wieder vereint werden.** Im
Blocksatz setzt die erzeugende Software jedes Wort an eine eigene berechnete
Position, um die Wortabstände zu strecken. PyMuPDF meldet diese Wörter als
eigene Zeilen — allesamt auf derselben Höhe. Hält man das für Zeilenumbrüche,
zerfällt ein Absatz zu einer Kette von Einzelwörtern untereinander. In einem
typischen Brief werden so aus 92 gemeldeten Zeilen zwölf echte.

Dabei darf Blocksatz nicht mit Spaltensatz verwechselt werden — beide erzeugen
grosse waagerechte Lücken. Unterscheidbar sind sie an deren Verteilung:
Blocksatz streckt **alle** Wortabstände einer Zeile gleichmässig, eine Tabelle
hat einen einzelnen Ausreisser.

Drei weitere Eigenheiten echter Arztbriefe sind entscheidend:

**Gelesen wird blockweise**, nicht seitenweit nach Höhe. Steht neben dem
Anschriftenfeld ein zweiter Block mit Ansprechpartner, Durchwahl und Datum,
würde eine Sortierung nach Höhe beide Spalten Zeile für Zeile ineinander
verschränken.

**Der Satzrand wird aus der Hauptspalte bestimmt** und gilt auch nur dort.
Eine breite Fusszeile mit Bankverbindung reicht weiter nach rechts als der
Fliesstext — zählt man sie mit, liegt der Rand zu weit rechts und es wird
überhaupt nichts mehr zusammengefügt. Umgekehrt darf der Rand der Hauptspalte
nicht auf Nebenblöcke angewandt werden, sonst zieht es dort alles zusammen.

Tabellarisch gesetzte Zeilen erkennt das Verfahren an den waagerechten Lücken
zwischen den Textspannen und lässt sie in Ruhe — ein Medikationsplan bleibt
zeilenweise stehen. Ebenso Anschriftenblöcke, Aufzählungen und
Unterschriftenzeilen.

### Wenn ein Brief trotzdem zerrissen ankommt

```bash
.venv/bin/python tools/layout_diagnose.py brief.pdf
```

Zeigt Spaltenzahl, Zeilenschritt, geschätzten Satzrand und für jede Zeile die
getroffene Entscheidung — als Balken, deren Länge der Zeilenbreite entspricht.
Die Ausgabe enthält **keinen Buchstaben** des Dokuments und lässt sich deshalb
gefahrlos weitergeben, um einem Fehler nachzugehen.

Für OCR-Ergebnisse und eingefügten Text gibt es keine Geometrie. Dort greift
ersatzweise eine Zusammenführung nach Zeilenlänge, die nur anspringt, wenn
der Text tatsächlich hart umbrochen aussieht.

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
```

Das deutsche Sprachmodell ist in `requirements.txt` mit fester Version
verzeichnet und wird dabei mitinstalliert — ein getrennter
`spacy download`-Aufruf ist nicht nötig und liesse die Version offen.

Für OCR gescannter PDFs zusätzlich Tesseract mit deutschem Sprachpaket:

```bash
brew install tesseract tesseract-lang
```

Ohne Tesseract funktioniert alles ausser gescannten PDFs.

### Getestete Umgebung

Die Erkennungsleistung hängt unmittelbar an der Version des Sprachmodells.
Alle Angaben im README beziehen sich auf diesen Stand:

| Komponente | Version |
|---|---|
| Python | 3.13.3 |
| spaCy | 3.8.14 |
| Sprachmodell `de_core_news_lg` | 3.8.0 |
| Tesseract OCR | 5.5.2, Sprachpaket `deu` |
| Betriebssystem | macOS 26.5, Apple Silicon |

Andere Plattformen sind nicht geprüft. Linux sollte unverändert
funktionieren, sofern Tesseract mit deutschem Sprachpaket vorliegt.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `app/extract.py` | Text aus PDF, DOCX, OCR; Absatzerkennung und Reflow |
| `app/detect.py` | Erkennung: Regex-Regeln + spaCy-NER, Gruppierung, Pseudonyme |
| `app/stufen.py` | Stufenmatrix, Datumsverschiebung, Initialen, Altersdekaden |
| `app/export.py` | Ersetzung anwenden, TXT/DOCX/PDF schreiben |
| `app/main.py` | HTTP-Endpunkte |
| `static/` | Oberfläche (eine Seite, kein Framework) |
| `tools/layout_diagnose.py` | zeigt den Satzspiegel eines PDFs, ohne Inhalt |

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

Alle in Quelltext und Tests verwendeten Namen, Anschriften, Geburtsdaten,
Aktenzeichen sowie Rechnungs-, Konto- und Versicherungsnummern sind **frei
erfunden**. Es wurden zu keinem Zeitpunkt echte Personen-, Patienten- oder
Geschäftsdaten verarbeitet oder in dieses Repository aufgenommen.

## Wie belastbar ist die Erkennung?

Ehrlich gesagt: nicht beziffert. Es gibt bislang **keine Messung von
Trefferquote und Fehlalarmrate** an einem annotierten Prüfsatz. Die Beurteilung
beruht darauf, dass die Testdokumente nach jeder Änderung durchgelesen werden.

Was das heisst: Die Aussage „findet Namen, Anschriften und Kennnummern" ist
belegt in dem Sinne, dass es an den mitgelieferten Beispielen nachweislich
funktioniert. Eine Aussage wie „findet 98 Prozent aller Personennamen" wird
hier bewusst **nicht** getroffen, weil sie nicht gemessen wurde. Eine solche
Messung steht im [Backlog](BACKLOG.md).

Wer das Werkzeug in einem Zusammenhang einsetzt, in dem eine belastbare Zahl
gebraucht wird — etwa als Verfahrensschritt in einem Datenschutzkonzept —,
muss diese Messung für den eigenen Dokumentenbestand selbst durchführen.

## Haftung

Das Werkzeug wird ohne Gewähr bereitgestellt (siehe [LICENSE](LICENSE),
Abschnitte 7 und 8). Es ist **kein Medizinprodukt** und nicht nach MDR
zertifiziert.

Die Verantwortung dafür, dass ein Dokument tatsächlich frei von
Personenbezug ist, bleibt bei der Person, die es weitergibt. Der Prüfschritt
vor dem Export unterstützt diese Prüfung, er ersetzt sie nicht.

## Zitieren

Falls diese Software in einer Veröffentlichung verwendet wird, liegt eine
maschinenlesbare Zitationsangabe als [CITATION.cff](CITATION.cff) bei.
GitHub zeigt daraus rechts auf der Projektseite ein fertiges Zitat an.

## Lizenz

Apache License 2.0, siehe [LICENSE](LICENSE). Die Lizenzen der verwendeten
Fremdbibliotheken sind in [NOTICE](NOTICE) aufgeführt — beachtenswert ist
dort der Hinweis zu PyMuPDF, das unter der AGPL-3.0 steht.

## Mitwirkung und Kontakt

Betreut von [@maximilianhabs](https://github.com/maximilianhabs). Fragen,
Fehlermeldungen und Vorschläge bitte über die
[Issues](https://github.com/maximilianhabs/anonymisator/issues) des
Projekts.

**Bitte niemals echte Dokumente, Textausschnitte oder Bildschirmfotos mit
Personenbezug an ein Issue anhängen.** Zur Beschreibung eines Fehlers genügt
ein nachgebautes Beispiel mit erfundenen Daten.

Offene Punkte und bewusst abgelehnte Vorschläge stehen im
[Backlog](BACKLOG.md).

## Entstehung

Entwickelt mit Unterstützung von Claude (Anthropic); die Beiträge sind in
der Commit-Historie als solche gekennzeichnet. Konzept, fachliche
Entscheidungen und Prüfung liegen beim Autor.
