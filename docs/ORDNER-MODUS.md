# Ordner-Modus

Opt-in-Weg des Anonymisators: Datei in einen Eingangsordner legen, das
anonymisierte Ergebnis erscheint als Textdatei in einem Ausgangsordner. Ohne
Rückfrage, ohne Review. Umgesetzt in `app/ordner.py`, gestartet mit
`pipeline.sh`.

Inhalt: [1 Wozu](#1-wozu-und-für-wen-nicht) ·
[2 Schnellstart](#2-schnellstart) · [3 Ablauf](#3-ablauf-schritt-für-schritt) ·
[4 Ordner und Startprüfungen](#4-ordnerstruktur-und-startprüfungen) ·
[5 Endkontrolle](#5-endkontrolle-im-detail) · [6 Protokoll](#6-protokoll) ·
[7 Grenzen](#7-grenzen-und-restrisiko) ·
[8 Weiterverarbeitung](#8-weiterverarbeitung) · [9 Praxisbefund](#9-praxisbefund) ·
[10 Tests](#10-tests)

## 1. Wozu und für wen nicht

**Wozu.** Wer regelmässig Briefe oder Gutachten anonymisiert für eine
nachgelagerte Auswertung, will nicht jede Datei einzeln im Browser öffnen,
prüfen und exportieren. Im Ordner-Modus genügt es, die Datei abzulegen. Der
Anonymisator liest sie, erkennt, ersetzt, kontrolliert das Ergebnis und legt
es im Ausgang ab. Was die Kontrolle nicht sicher besteht, wird nicht
ausgegeben, sondern mit dem Original zurückgehalten.

**Das ist eine Ausnahme vom Grundsatz „kein Export ohne Review“.** Der
Review vor dem Export ist der Kern des Werkzeugs (siehe README, „Für wen“,
und BACKLOG, „Bewusst nicht vorgesehen“). Der Ordner-Modus ersetzt ihn nicht
und gleicht ihn nicht aus; er begrenzt das Risiko durch strengere
Voreinstellungen und eine Endkontrolle, schliesst es aber nicht. Das
Web-Werkzeug bleibt unverändert: Dort gibt es weiterhin keinen Export ohne
Prüfschritt, und der Ordner-Modus startet nie von selbst.

**Für wen nicht.** Nicht geeignet, wenn

- ein einziger übersehener Name nicht vertretbar ist und niemand die
  Ausgaben liest,
- das Ergebnis ohne weitere Prüfung das Haus oder den Rechner verlassen soll,
- Scans (OCR) ohne Nachsicht durchlaufen sollen: Sie werden standardmässig
  zurückgehalten.

Für diese Fälle ist das Web-Werkzeug mit Review der richtige Weg.

## 2. Schnellstart

Zwei Ordner anlegen, am besten ausserhalb von iCloud-Ordnern und ausserhalb
des Repos (siehe Abschnitt 4):

```bash
mkdir -p ~/"Inbox Anonymize" ~/"Outbox Anonymize"
./pipeline.sh --eingang ~/"Inbox Anonymize" --ausgang ~/"Outbox Anonymize"
```

Das Skript prüft, ob `.venv` existiert, und reicht alle Argumente an
`.venv/bin/python -m app.ordner` weiter. Dateien (`.pdf`, `.docx`, `.txt`) in
den Eingang legen; im Dauerbetrieb wird alle 5 Sekunden nachgesehen. Beenden
mit Strg-C: Die gerade laufende Datei wird noch abgelegt, ein zweites Strg-C
bricht hart ab.

| Angabe | Umgebungsvariable | Bedeutung |
|---|---|---|
| `--eingang <Ordner>` | `ANON_EINGANG` | Pflicht, kein Standardpfad |
| `--ausgang <Ordner>` | `ANON_AUSGANG` | Pflicht, kein Standardpfad |
| `--stufe leicht\|standard\|streng` | `ANON_ORDNER_STUFE` | Standard `streng`, weil niemand mitliest |
| `--einmal` | – | einmal durchlaufen und beenden |
| `--ocr-freigeben` | – | auch per OCR gelesene Dokumente ausgeben |
| – | `ANON_ORDNER_ABFRAGE_SEKUNDEN` | Abstand der Abfragen, Standard 5 |
| – | `ANON_ORDNER_MIN_ZEICHEN` | Mindestlänge des Textes, Standard 200 |

Eingang und Ausgang haben bewusst keinen Standardpfad: Ein vorgegebener
Ordner würde dazu einladen, ihn anzulegen, ohne über Synchronisierung und
Ablageort nachzudenken. Die Kommandozeile überschreibt die Umgebung.

`--einmal` misst den Eingang zweimal im Abstand von einer Sekunde und
verarbeitet nur Dateien, die sich dazwischen nicht verändert haben.

## 3. Ablauf Schritt für Schritt

```
Datei im Eingang
   |
   v
[1] Stabilitätsprüfung   Grösse und mtime gleich wie bei der Abfrage davor?
   |  nein -> liegen lassen, nächste Abfrage
   v
[2] Extraktion           PDF (je Seite Textlayer oder OCR), DOCX, TXT
   |  Lesefehler / zu gross -> zurückhalten
   v
[3] Erkennung            wie im Web-Werkzeug (detect.analysiere)
   |
   v
[4] Ersetzung            ALLE Gruppen der gewählten Stufe, auch unbelegte
   |
   v
[5] Namens-Nachlauf      einmal Person, überall Person
   |
   v
[6] Endkontrolle         rest_klartext, rest_erkennung, kein_patient
   |            |
 bestanden   nicht bestanden / OCR / kurzer Text / Seite ohne Text
   |            |
   v            v
Ausgang      Eingang/Zurueckgehalten/   (Original, keine Ausgabe)
dokument_NNNN.txt
Original -> Eingang/Erledigt/
   |
   v
[7] Protokollzeile       Zahlen und Kürzel, keine Namen
```

1. **Stabilitätsprüfung.** Eine Datei wird erst gelesen, wenn Grösse und
   Änderungszeit bei zwei aufeinanderfolgenden Abfragen gleich sind. So wird
   keine halb kopierte Datei verarbeitet. Unterordner, Verknüpfungen,
   versteckte Dateien (Name beginnt mit Punkt) und `protokoll.csv` werden
   ignoriert; Dateien mit anderer Endung bleiben liegen, die Konsole nennt nur
   ihre Anzahl.
2. **Extraktion.** Dieselbe Extraktion wie im Web-Werkzeug. Bei PDFs
   entscheidet sie je Seite, ob der Textlayer lesbar ist (genug Zeichen,
   Anteil plausibler Zeichen, wenig Fremdschrift) oder OCR nötig ist. Ist die
   Datei grösser als das Upload-Limit oder nicht lesbar, wird sie mit
   `lesefehler` zurückgehalten.
3. **Erkennung.** Dieselbe Erkennung wie im Web-Werkzeug. Die Stufe ändert
   nur die Behandlung, nie die Erkennung.
4. **Ersetzung.** `stufen.ersetzungen_fuer(..., nur_aktive=False)` baut die
   Ersetzungsliste wie der Browser, nimmt aber auch unbelegte Gruppen
   (Treffer ohne Anrede, Titel oder Rollenwort) mit. Im Web-Werkzeug wählt der
   Prüfende solche Gruppen ab; hier prüft niemand, also wird im Zweifel
   ersetzt.
5. **Namens-Nachlauf.** Die Erkennung markiert ein Wort mitunter nur an einer
   Stelle als Person und lässt dasselbe Wort woanders stehen. Jedes
   Namenswort (grossgeschrieben, ab drei Buchstaben, kein Titel) einer
   erkannten Person wird deshalb an allen übrigen Stellen mit dem Platzhalter
   der Gruppe ersetzt. Das trifft auch Fehlalarme (ein Fachwort, das für einen
   Namen gehalten wurde) und kostet dann Lesbarkeit; das ist der sichere
   Fehler. Bei der Behandlung „initialen“ (Stufe leicht) gibt es keinen
   Platzhalter zum Einsetzen, dort entfällt der Nachlauf.
6. **Endkontrolle.** Drei Prüfungen auf dem fertigen Text (Abschnitt 5).
7. **Ablage.** Bestanden: Ausgabe als `dokument_NNNN.txt` (laufende Nummer,
   vierstellig, fortgesetzt nach der höchsten vorhandenen), Original nach
   `Erledigt/`. Nicht bestanden: Original nach `Zurueckgehalten/`, keine
   Ausgabe. Die Ausgabe wird zuerst in eine temporäre Datei im Ausgang
   geschrieben und dann umbenannt, damit nie eine halbe Datei sichtbar ist.
   Beim Verschieben wird nichts überschrieben; bei Namensgleichheit entsteht
   `name_2.ext`, `name_3.ext` und so weiter. Zuletzt folgt die Protokollzeile.

Die Ausgabe trägt die Kopfzeile des Text-Exports (Stufe, Tagesdatum) und
sonst nur den ersetzten Text. Metadaten des Originals werden nicht
übernommen.

## 4. Ordnerstruktur und Startprüfungen

| Ort | Inhalt |
|---|---|
| `~/Inbox Anonymize/` (Eingang) | abgelegte Originale, die noch warten |
| `~/Inbox Anonymize/Erledigt/` | Originale, deren Ergebnis im Ausgang liegt |
| `~/Inbox Anonymize/Zurueckgehalten/` | Originale, die die Kontrolle nicht bestanden haben |
| `~/Inbox Anonymize/protokoll.csv` | eine Zeile je verarbeiteter Datei |
| `~/Outbox Anonymize/dokument_NNNN.txt` (Ausgang) | anonymisierte Texte |

Der Zustand ist der Ordner, nicht eine Datenbank: Was im Eingang liegt, ist
offen; was in `Erledigt/` oder `Zurueckgehalten/` liegt, ist abgeschlossen.
Es wird nichts gelöscht und ausserhalb von Eingang und Ausgang nichts
geschrieben. Netzwerkzugriffe gibt es nicht.

**Startprüfungen.** Vor dem ersten Lauf wird `pruefe_start` ausgeführt. Es
legt nichts an.

| Befund | Folge | Begründung |
|---|---|---|
| Eingang fehlt oder ist kein Ordner | Abbruch | nichts zu lesen |
| Ausgang existiert, ist aber eine Datei | Abbruch | nichts zu schreiben |
| Eingang und Ausgang gleich | Abbruch | die Ausgabe würde als Eingabe erneut gelesen |
| ineinander verschachtelt | Abbruch | gleicher Grund; zudem Verwechslung von Original und Ausgabe |
| ein Pfad im Repo-Verzeichnis | Abbruch | das Repo ist öffentlich, jede Datei bliebe für immer in der Historie; auch anonymisierte Ausgaben gehören nicht dorthin |
| Eingang unter `~/Library/Mobile Documents`, `~/Desktop` oder `~/Documents` | Warnung, Lauf geht weiter | dort kann macOS die Dateien in die iCloud spiegeln; die **Originale** würden den Rechner verlassen, bevor sie verarbeitet sind |

Abbruch endet mit Rückgabewert 2. Die Warnung zur Synchronisierung betrifft
nur den Eingang, weil dort die Klardaten liegen. Der Ausgang wird beim Start
angelegt, falls er fehlt.

## 5. Endkontrolle im Detail

Die Endkontrolle läuft auf dem fertigen Ergebnistext. Bestanden heisst: kein
Grund wird gemeldet. Platzhalter wie `[PATIENT_A]`, `[ADRESSE_3]` oder
`[GESCHWÄRZT_1]` werden bei allen Suchen unkenntlich gemacht, damit ein
Fundtext wie „ORT“ nicht im Platzhalter `[ORT_1]` gefunden wird.

**`rest_klartext`.** Steht ein ersetzter Originaltext noch im Ergebnis?
Geprüft wird, was die gewählte Stufe tatsächlich ersetzt (Behandlung
„ersetzen“):

- Bei Personen (Patient, Arzt, Person) wortweise: Von „Elisabeth Hartmann“
  darf weder „Elisabeth“ noch „Hartmann“ stehen bleiben. Das gilt auch bei
  Initialen (Stufe leicht); „E. H.“ enthält kein Wort ab drei Buchstaben und
  löst nichts aus. Titel und Anreden („Dr.“, „Prof.“, „Frau“, „Kollegin“ und
  ähnliche) zählen nicht, sie stehen in jedem Brief.
- Bei Organisation, Adresse, Ort, Geburtsdatum, Datum, URL und den direkten
  Kennungen (Versicherten-, Fall-, Konto-, Telefonnummer und so weiter) mit
  dem vollständigen Fundtext, ab drei Zeichen.
- Suche an Wortgrenzen, Gross- und Kleinschreibung egal, Leerraum im Begriff
  beliebig lang (ein Umbruch mitten im Namen entgeht der Kontrolle nicht).

Bewusst **nicht** geprüft werden Zahl, Alter, Zeitspanne, Jahreszahl, Betrag,
Geschlecht und Diagnosecode. Ihr Fundtext („120“, „Patientin“, „G40.1“)
taucht in legitimem Fachtext an Stellen auf, die die Erkennung zu Recht nicht
anfasst (Messwert mit Einheit, Dosis, Wort im Kompositum). Der Nutzen wäre
ein Strom von Fehlalarmen, die jeden Lauf zurückhielten. Für Datum gilt das
nicht: Ein vollständiges Datum ist selbst ein Merkmal und wird geprüft. Bei
Behandlungen, die einen Teil des Originals gewollt stehen lassen („jahrgang“,
„dekade“, „nur_ort“, „verschoben“, „gerundet“, „behalten“), wird der
Fundtext nicht gesucht, sonst wäre jeder Lauf ein Fehlalarm.

**`rest_erkennung`.** Findet die Erkennung im fertigen Text noch direkte
Identifikatoren? Sie läuft ein zweites Mal über das Ergebnis, zählt aber nur
sichere Funde der Typen Patient, Arzt, Geburtsdatum, Telefon, E-Mail,
Adresse und der direkten Kennungen, und nur dort, wo die Stufe den Typ
vollständig ersetzt. Sonst fände sie die bewusst stehen gebliebene Form
(„E. H.“, „Jahrgang 1958“, „94032 Passau“) in jedem Lauf wieder. Ausgelassen
sind ausserdem:

- Datum: Auf der Standardstufe bleibt ein verschobenes Datum ein Datum, die
  Erkennung schlüge strukturell immer an.
- Zahl, Ort und Organisation: Die Erkennung schlägt dort auch in sauberem Text
  unbelegt an; sie sind über `rest_klartext` abgedeckt.

Funde, die in einem Platzhalter liegen, zählen nicht (das Sprachmodell liest
„ADRESSE_3“ gern als Namen). Streift ein Fund einen Platzhalter („ARZT_1
Müller“), zählt nur der Teil ausserhalb. Besteht ein Fund nur aus Titeln
(„PROF. DR. MED. [ARZT_1]“, wo die Arzt-Regel auf „MED“ ausweicht), ist er
kein Rest.

**`kein_patient`.** Wurde im Dokument überhaupt ein Patient erkannt? Ein Text
ohne erkannten Patienten ist entweder kein Arztbrief oder die Erkennung hat
versagt; in beiden Fällen soll ein Mensch hinsehen.

**Weitere Gründe, die vor oder neben der Endkontrolle entstehen.** Mehrere
Gründe können zusammen auftreten, sie stehen dann mit Semikolon getrennt im
Protokoll.

| Code | Bedeutung | Was tun |
|---|---|---|
| `rest_klartext` | Ein ersetzter Name, Ort, Datum oder eine Kennung steht noch im Ergebnis. | Original aus `Zurueckgehalten/` im Web-Werkzeug öffnen und prüfen. |
| `rest_erkennung` | Die Erkennung findet im Ergebnis noch einen direkten Identifikator. | Wie oben. |
| `kein_patient` | Kein Patient erkannt. | Prüfen, ob es überhaupt ein Patientendokument ist; sonst im Web-Werkzeug von Hand markieren. |
| `kein_text` | Weniger als 200 Zeichen Text (Einstellung `ANON_ORDNER_MIN_ZEICHEN`); meist ein leerer Scan oder ein Lesefehler. Keine weitere Analyse. | Original ansehen; ggf. neu scannen. |
| `seite_ohne_text` | Eine per OCR gelesene Seite hat keinen Text ergeben. Das Dokument wäre unvollständig. | Original mit dem Ergebnis vergleichen, Seite besser einscannen. |
| `ocr` | Mindestens eine Seite wurde per OCR gelesen (Quelle `pdf-ocr` oder `pdf-gemischt`). OCR-Fehler verstecken Namen („Hartmann“ wird zu „Hartrnann“) und sind die häufigste Lücke. | Im Web-Werkzeug bearbeiten, oder mit `--ocr-freigeben` bewusst durchlassen und die Ausgabe lesen. |
| `lesefehler` | Datei nicht lesbar (etwa beschädigt oder falsches Format) oder grösser als das Upload-Limit. | Datei prüfen, ggf. als `.txt` oder anderes PDF neu erzeugen. |
| `analysefehler` | In Erkennung oder Ersetzung ist eine Ausnahme aufgetreten. Nur der Typname der Ausnahme erscheint auf der Konsole, nie ihre Meldung (sie könnte Inhalt enthalten). | Im Web-Werkzeug versuchen; tritt es wiederholt auf, mit einem erfundenen Beispieltext als Fehler melden. |

## 6. Protokoll

`protokoll.csv` liegt im Eingang und bekommt je verarbeiteter Datei eine
Zeile; die Kopfzeile wird beim ersten Eintrag geschrieben.

| Spalte | Inhalt |
|---|---|
| `zeitstempel` | Zeitpunkt der Ablage (lokale Zeit, ISO 8601, auf die Sekunde) |
| `ergebnis` | `frei` oder `zurueckgehalten` |
| `ausgabedatei` | `dokument_NNNN.txt`, bei Zurückgehaltenem leer |
| `quelle` | Art der Extraktion (etwa `pdf-textlayer`, `pdf-ocr`, `pdf-gemischt`, `docx`, `paste` für Textdateien) |
| `seiten` | Seitenzahl |
| `zeichen` | Länge des gelesenen Textes |
| `gruppen` | Zahl der erkannten Gruppen (je eine Person, Adresse und so weiter) |
| `fundstellen` | Zahl aller Fundstellen |
| `unbelegt` | Zahl der Gruppen ohne Beleg (Anrede, Titel, Rolle daneben) |
| `stufe` | angewandte Stufe |
| `gruende` | Codes aus Abschnitt 5, mit Semikolon getrennt, leer bei `frei` |
| `version` | Programmversion (aus `CITATION.cff`) |

**Was bewusst nicht drinsteht:** der Originaldateiname, Klartext oder
Fundtexte und Fehlermeldungen. Der Dateiname enthält bei Arztbriefen oft den
Patientennamen. Eine Zeile, die Original und Ausgabe einander zuordnet,
wäre selbst ein Schlüssel zur Person: Wer das Protokoll hat und das Original
kennt, wüsste, welche anonymisierte Datei zu welcher Person gehört. Die
Konsole hält dieselbe Linie: Sie zeigt Laufnummer, Ergebnis, Ausgabedatei,
Zahlen und Codes, im Fehlerfall nur den Typnamen der Ausnahme.

Die Reihenfolge der Zeilen folgt der Verarbeitung. Wer wissen will, welches
Original hinter einer Zeile steckt, muss das Original selbst öffnen; das ist
gewollt.

## 7. Grenzen und Restrisiko

- **Die Endkontrolle findet nur Reste von Erkanntem.** Sie vergleicht das
  Ergebnis mit dem, was die Erkennung selbst gefunden hat. Ein Name, den die
  Erkennung nie als Name erkannt hat, geht durch, und keine Prüfung kann das
  bemerken. Das ist das Restrisiko des Modus; im Web-Werkzeug fängt es der
  Prüfende auf.
- **Scans werden standardmässig zurückgehalten.** OCR-Fehler verstecken
  Namen vor der Erkennung. Wer `--ocr-freigeben` setzt, nimmt dieses Risiko
  bewusst in Kauf.
- **Pseudonymisiert ist nicht anonymisiert.** Auf der Stufe `leicht` bleiben
  Initialen, Geburtsjahr, Einrichtung und Behandlungszeitraum; das Ergebnis
  bleibt ein personenbezogenes Datum. Der Ordner-Modus startet bewusst mit
  `streng`.
- **Anonymisiert heisst nicht verschlüsselt.** Der Ausgang enthält Klartext
  mit Platzhaltern. Wer Zugriff auf den Ordner hat, liest ihn.
- **Über-Ersetzung ist gewollt.** Hält das Sprachmodell ein Fachwort für einen
  Namen, wird es überall ersetzt, auch an unbelegten Stellen. Das kostet
  Lesbarkeit, ist aber der sichere Fehler.
- **Originale bleiben Klardaten.** `Erledigt/` und `Zurueckgehalten/` enthalten
  die unveränderten Originale, auf der Platte und in jedem Backup des
  Rechners. Das Programm löscht nie etwas; Aufbewahrung und Löschung sind
  Sache des Nutzers.
- **Dateinamen** bleiben am Original (auch bei der Verschiebung). Sie
  gelangen nie in Ausgabe, Protokoll oder Konsole.
- **Empfehlung.** Die ersten Ausgaben vollständig lesen, danach regelmässig
  Stichproben, besonders nach Änderungen am Dokumenttyp oder an der
  Erkennung. Zurückgehaltenes im Web-Werkzeug bearbeiten. Die Zahl der
  Zurückgehaltenen im Protokoll ansehen, bevor jemand Schwellen ändert (siehe
  BACKLOG).

## 8. Weiterverarbeitung

Der Ausgang ist die einzige Stelle, von der aus weiter ausgewertet werden
soll. Nie dort ablegen: Originale, Zuordnungstabellen (CSV mit Pseudonym und
Klarname) oder Schlüsseldateien; sie würden die Anonymisierung aufheben.

Eine Übergabe der Ausgaben an externe Dienste (Sprachmodelle, Cloud,
Auftragsverarbeiter) braucht eine eigene rechtliche Prüfung, etwa zu
Schweigepflicht und Auftragsverarbeitung, und ist nicht Teil dieses
Projekts. Der Anonymisator endet am lokalen Ausgangsordner und ruft
selbst keinen Dienst auf (siehe BACKLOG, „Bewusst nicht vorgesehen“).

## 9. Praxisbefund

Beim ersten Lauf an einem realen, fünfseitigen Brief (74 Gruppen, 123
Fundstellen) enthielt die automatische Ausgabe kein Wort, das eine
manuelle Prüfung desselben Briefs entfernt hatte. Das ist **eine**
Beobachtung an einem Dokument, keine Gütezusage; aus ihr folgt weder eine
Trefferquote noch eine Eignung für andere Dokumenttypen. Das Dokument selbst
und seine Inhalte sind nicht Teil des Repos. Ein Goldkorpus und Messungen
stehen im Etappenplan (BACKLOG, „Pipeline-Ausbau“).

## 10. Tests

`tests/test_ordner.py` läuft ohne Server in temporären Verzeichnissen und mit
frei erfundenen Briefen:

```bash
.venv/bin/python tests/test_ordner.py
```

Abgedeckt sind:

- Ablage und Protokoll: Ausgabe, laufende Nummern, Original nach `Erledigt/`,
  Protokoll mit Kopfzeile und Quelle, Namenskollision (`_2`).
- Verschwiegenheit: weder Protokoll noch Konsole enthalten Klarnamen oder
  Dateinamen, auch nicht die des Originals.
- Zurückhalten bei fehlendem Patienten, kurzem Text, kaputten PDFs
  (`lesefehler`).
- Unbekannte Endungen, Unterordner und versteckte Dateien bleiben liegen.
- Stabilitätsprüfung: Erste Messung fasst nichts an, geänderte Datei wird
  nicht gelesen.
- Endkontrolle: `rest_klartext` je Stufe (stehen gebliebener Nachname,
  Ort, behaltene Form bei Initialen, Titel), `rest_erkennung` (Telefon,
  E-Mail, behaltene Form auf Stufe leicht).
- Startprüfungen: gleicher, verschachtelter, fehlender Ordner, Pfad im
  Repo, fehlende Pflichtangaben, Warnung unter `~/Desktop`.
- Namens-Nachlauf und der Titel-Fehlalarm der Endkontrolle („PROF. DR. MED.
  [ARZT_1]“), aus dem ersten echten Lauf übernommen.

Nicht abgedeckt: ein Lauf mit einem echten gescannten PDF und die
Verdrahtung „Textlayer vorhanden, aber unlesbar“ (siehe BACKLOG).
