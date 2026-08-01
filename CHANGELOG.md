# Änderungen

Dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).
Solange die Hauptversion 0 ist, können sich Schnittstellen und Kürzel
zwischen Nebenversionen ändern.

## 0.11.0 — 2026-08-01

Einmalige Verarbeitung: sichtbar gemacht, ausführlich erklärt, nachgewiesen.

**Aufklärung des Anwenders**
- Ausklappbarer Abschnitt „Der Weg Ihrer Datei, Schritt für Schritt" auf der
  Startseite. Er benennt für jede der acht Stationen konkret, was geschieht
  und wie lange etwas verweilt: Übertragung, Entgegennahme, Lesen und
  Verwerfen, Analyse, Prüfung im Browser, Export, Protokollierung, Neustart.
  Einschliesslich der technischen Einzelheiten, die sonst niemand nachprüfen
  könnte — die 1-MB-Grenze der Auslagerung, `TMPDIR`, das `tmpfs`.
- Eigener Haftungsabschnitt: Die Standards werden benannt, zugleich steht
  ausdrücklich da, dass **keine vollständige Erkennung zugesichert werden
  kann**, dass die Verantwortung für ein weitergegebenes Dokument beim
  Anwender bleibt und dass die Software kein Medizinprodukt ist.
- Beides unterscheidet ausdrücklich zwischen Betrieb auf dem eigenen Gerät
  und Betrieb auf einem Server — nur im ersten Fall verlässt nichts den
  Rechner.

**Behoben — eine Zusicherung, die nicht mehr stimmte**
- Die Kopfzeile versprach „läuft vollständig lokal · keine Datei verlässt
  diesen Rechner". Das galt für den Betrieb auf dem eigenen Gerät; hinter
  einer Adresse wie `ano.neuro-vibe.de` ist es schlicht unwahr — dort geht
  das Dokument sehr wohl über das Netz. Eine Sicherheitszusage, die nicht
  zutrifft, ist schlimmer als keine. Jetzt: „Einmalige Verarbeitung ·
  nichts wird gespeichert", zutreffend für beide Betriebsarten. Dieselbe
  Richtigstellung im README.

**Verarbeitung endet früher**
- Die hochgeladene Datei wird unmittelbar nach dem Lesen geschlossen, nicht
  erst beim Aufräumen der Anfrage. Starlette legt Uploads über 1 MB als
  temporäre Datei ab; sie verschwindet damit schon vor der Analyse.
- Die Rohbytes werden nach der Textgewinnung ausdrücklich freigegeben,
  statt bis zum Ende der Anfrage im Speicher zu stehen.
- „Neues Dokument" räumt jetzt vollständig auf — auch die gerenderten
  Markierungen und das Eingabefeld. Vorher blieb der vorige Brief im
  Klartext im Browser stehen, während schon der nächste bearbeitet wurde.

**Sichtbar gemacht**
- Hinweis auf der Ablagefläche: gelesen, ausgewertet, sofort verworfen.
- Eigener Abschnitt auf der Startseite und im README, der für jede Stelle
  angibt, wie lange etwas verweilt — Upload, Rohbytes, Text, Browser,
  Protokoll, Neustart.

**Nachgewiesen**
- `tests/test_keine_persistenz.py` prüft mit einer eindeutigen Kennung, dass
  weder ein kleiner noch ein 1,4 MB grosser Upload eine Datei hinterlässt,
  dass die Kennung anschliessend nirgends im Dateisystem auffindbar ist und
  dass die nächste Anfrage keinen Rest der vorigen enthält.

## 0.10.0 — 2026-08-01

Freigabeprüfung. Zwei Sicherheitsbefunde und zwei Erkennungslücken behoben,
Messungen erstmals durchgeführt.

**Sicherheit**
- Der Datumsversatz kam aus `random`. Der Versatz ist das Geheimnis, das die
  echten Behandlungsdaten verdeckt — ein Mersenne-Twister lässt sich aus
  hinreichend vielen Ausgaben rekonstruieren. Wer mehrere anonymisierte
  Dokumente derselben Einrichtung sieht, hätte den Generatorzustand aufrollen
  und sämtliche Daten zurückrechnen können. Jetzt `secrets`.
- Bandit läuft ohne Befund, `pip-audit` meldet keine bekannten Schwachstellen
  in den Abhängigkeiten.

**Erkennung**
- „Hartmann, Elisabeth" wurde nicht erkannt — nur der Vorname. Das Format
  *Nachname, Vorname* ist in Labor- und Kliniksystemen die Regel, weil dort
  nach Nachnamen sortiert wird; der Nachname wäre im Dokument stehen
  geblieben.
- Nummernbezeichnungen mit Bindestrich wurden übersehen: „Fall-Nr.",
  „Auftrags-Nr.", „Patienten-Nr.". Ausgerechnet diese Form ist in Befunden
  die häufigste. Alle Nummernregeln nutzen jetzt ein gemeinsames Fragment,
  das jede Schreibweise abdeckt.
- Feldbezeichnungen aus Formularköpfen („Auftrags-Nr", „Eingang") galten als
  Einrichtungsnamen.

**Grenzen**
- Seitenzahl insgesamt begrenzt, nicht nur bei Texterkennung. Gemessen: 500
  Seiten belegen 2,8 GB. Ohne Grenze wäre der Behälter abgeräumt worden,
  statt eine verständliche Meldung zu geben. Voreinstellung 300 Seiten,
  Speichergrenze entsprechend auf 4 GB angehoben.
- Defekte Dateien liefern verständliche Meldungen statt englischem
  Bibliothekstext („Failed to open stream", „File is not a zip file").

**Prüfschritt**
- Vor dem ersten Export wird ausdrücklich bestätigt, dass der markierte Text
  durchgesehen wurde. Einmal je Dokument, nicht bei jedem Export — sonst
  wird die Rückfrage zur Gewohnheit und damit wirkungslos.

**Neue Prüfungen**
- `tests/test_export_hygiene.py` untersucht die erzeugten Dateien im
  Rohinhalt: DOCX-Metadaten, Kommentare, Änderungsverfolgung, versteckter
  Text, eingebettete Dateien; PDF-Metadaten, XMP, Anmerkungen, Textlayer.
  Mit Gegenprobe, dass die Suche überhaupt anschlägt.
- `tests/test_dokumentarten.py` prüft Laborbericht, Nummernschreibweisen,
  Dokumente mit vielen Beteiligten, OCR-typische Lesefehler und
  mehrspaltige Briefe.
- `tools/leistungsmessung.py` misst Laufzeit und Speicher über 1 bis 500
  Seiten. Ergebnis: näherungsweise linear, 82–139 ms je Seite, kein
  Speicherzuwachs über wiederholte Läufe.
- `pyproject.toml` mit Ruff, Black, MyPy und Bandit. CI prüft Linter,
  Sicherheitsbefunde und bekannte Schwachstellen bei jedem Commit.

## 0.9.0 — 2026-08-01

Auslieferung als Container. Ein frischer Ubuntu-24.04-Server mit Docker
genügt; nach dem Klonen sind keine manuellen Schritte mehr nötig.

**Neu**
- Zweistufiges `Dockerfile`. Das Basisabbild ist über seinen Digest
  festgelegt, nicht über ein bewegliches Etikett — nur so liefert derselbe
  Bauauftrag auf jedem Server dasselbe Ergebnis. Sprachmodell und Tesseract
  mit deutschem Sprachpaket stecken im Abbild; der Behälter startet
  nachweislich auch mit `--network none`.
- `docker compose up -d` startet Anwendung und Caddy als Reverse Proxy.
  Nur der Proxy veröffentlicht Ports, die Anwendung bleibt im internen Netz.
- Automatisches HTTPS über Let's Encrypt, sobald `ANON_DOMAIN` auf eine
  erreichbare Domain zeigt. Ohne Domain bleibt es bei HTTP im lokalen Netz.
- **Zugangsschutz über Basic Auth im Proxy.** Bisher band der Dienst an
  127.0.0.1 und war per Konstruktion unerreichbar. Unter fester Adresse
  könnte sonst jeder, der sie kennt, Arztbriefe hochladen. `/health` bleibt
  frei, damit die Bereitschaftsprüfung funktioniert.
- Sicherheitskopf im Proxy: CSP, X-Frame-Options, X-Content-Type-Options,
  Referrer-Policy, Permissions-Policy, HSTS, Cross-Origin-Regeln.
- Endpunkt `/health`, der erst dann gesund meldet, wenn das Sprachmodell
  tatsächlich geladen ist. Docker-Healthchecks für beide Dienste; der Proxy
  startet erst, nachdem die Anwendung bereit ist.
- Strukturierte Protokollierung als JSON-Zeilen nach stdout. Festgehalten
  werden Methode, Pfad, Statuscode und Dauer — **keine Dokumentinhalte,
  keine Dateinamen, keine erkannten Namen**. Uvicorns Zugriffsprotokoll ist
  abgeschaltet, weil es zusätzlich die Adresse des Aufrufers mitführte.
- `app/config.py`: sämtliche Einstellungen aus Umgebungsvariablen, keine
  Pfade und keine Grenzwerte mehr im Quelltext. Vollständig dokumentiert in
  `.env.example`.
- Obergrenze für die Seitenzahl bei Texterkennung. Ein Scan mit 200 Seiten
  blockierte einen Arbeitsprozess sonst über viele Minuten.
- CI baut das Abbild, startet den Gesamtaufbau und prüft: Nicht-Root-Konto,
  Start ohne Netz, Sprachmodell und Tesseract im Abbild, Erreichbarkeit über
  den Proxy, Sicherheitskopf, schreibgeschütztes Wurzeldateisystem sowie
  dass im Protokoll kein Dokumentinhalt landet.

**Härtung**
- Anwendungsbehälter läuft als UID 10001 mit schreibgeschütztem
  Wurzeldateisystem, ohne jede Linux-Berechtigung und mit
  `no-new-privileges`.
- Temporäre Dateien der Texterkennung liegen in einem `tmpfs` und erreichen
  nie eine Platte.
- Speichergrenze für den Anwendungsbehälter; Rastern grosser Scans belegte
  sonst unbegrenzt Arbeitsspeicher.
- Der Quelltext im Abbild gehört root und ist für den Dienstbenutzer nur
  lesbar.

## 0.8.0 — 2026-07-31

Deutlich weniger Fehlalarme in Befundtext.

**Behoben**
Befundtext steckt voller grossgeschriebener Fachbegriffe, die das
Sprachmodell für Eigennamen hielt. Statt einer Wortliste, die Fachsprache
nie einholt, greifen jetzt Regeln an der Wortbildung an:

- **Medizinische Endungen** — kein Familienname endet auf `-itis`,
  `-pathie`, `-ektomie`, `-sklerose`. Die Mindestlänge schützt kurze Namen:
  „Rose" endet auf `-ose` und bleibt eine Person.
- **Grundwörter am Wortende** — deutsche Komposita tragen ihre Bedeutung
  hinten, deshalb genügt die Prüfung des Endes. Eine Suche im ganzen Wort
  würde „Werther" über den Bestandteil „wert" treffen.
- **Eponyme** — „Lasègue-Zeichen", „Schellong-Test", „Barthel-Index" tragen
  formal einen Personennamen, sind aber Fachbegriffe. Erkannt am Grundwort
  (Zeichen, Test, Skala, Schema, Klassifikation, …). Ein Brief von einem
  echten Herrn Dr. Schellong wird davon nicht berührt: dort entscheidet die
  Anrede.
- **Lateinische Anatomie** — „Nervus suralis", „Arteria carotis" wurden als
  Ortsangaben geführt.
- **Grossbuchstaben-Kürzel** — ANA, ANCA, TSH, CRP galten als Einrichtungen.
  Krankenkassen wie AOK oder TK sind ausgenommen.
- **Akademische Titel** — „Dr.", „med.", „Prof." wurden mitsamt Punkt
  geführt und passten deshalb nie zur Stoppliste. Betraf besonders
  Briefköpfe in Grossschreibung.
- **Fachadverbien am Satzanfang** — „Laborchemisch ergaben sich …" wurde als
  Person gelesen.
- Treffer des Sprachmodells greifen nicht mehr über einen Zeilen- oder
  Absatzumbruch hinweg.

Gemessen an 216 Wörtern reinem Befundtext: von sechs Fehlalarmen auf null,
ohne einen einzigen echten Namen zu verlieren.

**Neu**
- Treffer werden als **belegt** oder **unbelegt** ausgewiesen. Belegt heisst:
  Anrede, akademischer Titel oder Rollenbezeichnung stand daneben. Unbelegt
  heisst: allein vom Sprachmodell vorgeschlagen. Unbelegte Treffer stehen in
  der Seitenleiste unten, sind gestrichelt unterstrichen und lassen sich
  gesammelt abwählen.

  Bewusst **kein** automatisches Kappen ab einer Anzahl: Welche der erkannten
  Personen die echten sind, lässt sich nicht an ihrer Zahl ablesen. Ein Brief
  kann Patient, Angehörige, Zuweiser sowie Haus- und Fachärzte nennen und
  damit zu Recht über jedem Grenzwert liegen. Wer dort automatisch kappt,
  lässt Klarnamen stehen — der teuerste Fehler, den dieses Werkzeug machen
  kann. Alles bleibt ersetzt, gelenkt wird nur der Blick.

- `tests/test_fehlalarme.py` misst, was **nicht** gefunden werden darf. Die
  übrigen Testdateien prüfen nur, was gefunden wird — eine Erkennung, die
  alles markiert, besteht jeden davon und ist im Alltag trotzdem unbrauchbar.

## 0.7.0 — 2026-07-31

Blocksatz zerlegte den Text in einzelne Wörter.

**Behoben**
- Um die Wortabstände zu strecken, setzt die erzeugende Software im Blocksatz
  jedes Wort an eine eigene berechnete Position. PyMuPDF meldet diese Wörter
  als eigene Zeilen — allesamt auf **derselben Höhe**. Sie wurden für echte
  Zeilenumbrüche gehalten, wodurch ein Absatz zu einer Kette von Einzelwörtern
  untereinander zerfiel. Zeilenbruchstücke gleicher Höhe werden jetzt zuerst
  wieder zu einer Textzeile vereint, bevor Absätze bestimmt werden.
  An einem nachgebildeten Brief: 92 Roh-Zeilen ergaben 92 Ausgabezeilen,
  jetzt zwei durchgehende Absätze.
- Die Erkennung tabellarischer Zeilen musste dafür schärfer werden. Blocksatz
  und Spaltensatz erzeugen beide grosse waagerechte Lücken; unterscheidbar
  sind sie nur an deren Verteilung. Blocksatz streckt **alle** Wortabstände
  einer Zeile gleichmässig, eine Tabelle hat einen einzelnen Ausreisser. Der
  bisherige Test auf die blosse Lückenbreite hätte gestreckten Fliesstext für
  eine Tabelle gehalten und ihn dann nicht mehr zusammengefügt.

**Verbessert**
- `tools/layout_diagnose.py` meldet, wie viele Roh-Zeilen zu wie vielen
  Textzeilen vereint wurden. Ein grosses Verhältnis weist unmittelbar auf
  Blocksatz hin.

## 0.6.0 — 2026-07-31

Der Brieftext wird bereits beim Einlesen richtig zusammengesetzt.

**Behoben — die Fragmentierung entstand vor dem Export**
- Zeilen wurden seitenweit nach Höhe sortiert. Steht neben dem
  Anschriftenfeld ein zweiter Block — Ansprechpartner, Durchwahl, Datum, im
  Klinikalltag die Regel —, verschränkte diese Sortierung beide Spalten Zeile
  für Zeile ineinander. Gelesen wird jetzt blockweise in Lesereihenfolge.
- Der rechte Satzrand wurde aus allen Zeilen der Seite geschätzt. Eine breite
  Fusszeile mit Bankverbindung oder eine Tabelle reicht weiter nach rechts als
  der Fliesstext; der Rand lag dadurch zu weit rechts, jede Textzeile galt als
  freiwillig beendet und **nichts** wurde mehr zusammengefügt. Für die
  Schätzung zählen nun ausschliesslich Zeilen der Hauptspalte, die nicht
  tabellarisch gesetzt sind.
- Der so ermittelte Rand galt anschliessend für alle Spalten. In einem
  Nebenblock, der weiter rechts steht, wurde damit umgekehrt jede Zeile für
  umbrochen gehalten und alles zusammengezogen. Zeilen ausserhalb der
  Hauptspalte behalten ihre Umbrüche jetzt unverändert.

Nachgemessen an vier Bauarten: schlicht, mit zweispaltigem Kopf, mit breiter
Fusszeile, mit beidem. Die vorherige Fassung zerriss den Fliesstext in allen
drei realistischen Fällen und blieb nur beim schlichten Brief heil.

**Neu**
- `tools/layout_diagnose.py` zeigt, wie ein PDF gesetzt ist — Spaltenzahl,
  Zeilenschritt, geschätzter Satzrand und je Zeile die getroffene
  Entscheidung, dargestellt als Balken. Die Ausgabe enthält **keinen
  Buchstaben** des Dokuments und lässt sich deshalb weitergeben, um einem
  Fehler nachzugehen.
- `tests/test_formatierung.py` prüft die vier Bauarten und stellt sicher,
  dass die Kopfspalten nicht ineinandergeraten.

## 0.5.0 — 2026-07-31

Der Text wird jetzt aus der Seitengeometrie neu gesetzt.

**Behoben — die eigentliche Ursache der zerhackten Ausgabe**
- Die Zusammenführung weich umbrochener Zeilen beruhte auf Zeichenlängen und
  lief nur an, wenn mindestens ein Viertel aller Zeilen nahezu voll war. In
  einem echten Arztbrief überwiegen aber die kurzen Zeilen — Briefkopf,
  Anschrift, Datenblock, Diagnosen, Medikationsplan, Unterschrift. Damit
  griff die Zusammenführung **überhaupt nicht**, und sämtliche harten
  Umbrüche blieben stehen. Genau das erzeugte die stark fragmentierte,
  auseinandergezogene Ausgabe.
- Ersetzt durch ein geometrisches Verfahren: Absatzgrenzen aus dem
  senkrechten Zeilenabstand, weiche Umbrüche aus der Frage, ob das erste
  Wort der Folgezeile am Zeilenende noch gepasst hätte. Beides wird je Zeile
  entschieden und ist damit unabhängig davon, wie viele kurze Zeilen das
  Dokument sonst enthält.
- Tabellarisch gesetzte Zeilen werden an den waagerechten Lücken zwischen den
  Textspannen erkannt und bleiben unangetastet.

**Behoben — dabei aufgefallen**
- Anschriften verschluckten den Zeilenumbruch: die Regel endete auf `\s*`,
  und `\s` schliesst `\n` ein. Im Ergebnis klebten zwei Platzhalter ohne
  Trennung aneinander (`[ADRESSE_3][ADRESSE_2]`). Dieselbe Falle bestand bei
  Telefonnummern, IBAN und Postfach; alle vier verwenden jetzt `[ \t]`.
- Wirkstoffnamen galten als Organisation — aus „Ramipril 5 mg 1-0-0" wurde
  „[ORG_2] mg 1-0-0". Die Stoppliste umfasst nun die gängigen Wirkstoffe
  sowie Einheiten und Darreichungsformen. Zusätzlich bleiben Zahlenanteile
  bei der Prüfung ausser Betracht: das Sprachmodell zieht die Dosis mit in
  den Namen, weshalb die Liste bei „Ramipril 5" zuvor nicht ansprach.

**Neu**
- `tests/test_formatierung.py` prüft zusätzlich die Bauart, an der die
  frühere Fassung scheiterte: einen zeilenweise gesetzten Arztbrief mit
  Medikationsplan und Diagnosenliste.

## 0.4.0 — 2026-07-31

Erster getaggter Release.

Über die Medizin hinaus: Rechnungen, Verträge, Behördenschreiben.

**Neue Kategorien**
- Rechnungs- und Belegnummer (auch Abrechnungs-, Auftrags-, Bestell-,
  Quittungs-, Gutschrift- und Lieferscheinnummer)
- Kunden- und Vertragsnummer (auch Mitglieds-, Mandanten-, Debitoren-,
  Kreditoren-, Lieferanten-, Personal-, Policen- und Schadensnummer)
- Kontoverbindung: Kontonummer, Bankleitzahl, BIC
- Steuernummer, USt-IdNr. und Steuer-ID, letztere auch ohne Beschriftung
- Sozial- und Rentenversicherungsnummer, auch im blossen Zahlenformat
- Ausweisnummer: Personalausweis, Reisepass, Führerschein
- Kfz-Kennzeichen — in Unfallgutachten ein direkter Identifikator
- Handelsregisternummer
- Geldbeträge in Euro, Franken und Dollar

Alle Kennnummern werden wie die übrigen direkten Identifikatoren auf jeder
Stufe ersetzt. Geldbeträge folgen dagegen dem Stufenprinzip: centgenau in
der leichten Stufe, auf zwei signifikante Stellen gerundet in der
Standardstufe („rund 2.100 €"), vollständig ersetzt in der strengen.

**Geändert**
- Die Kategorie `KLINIK` heisst jetzt `ORGANISATION` und trägt das Kürzel
  `[ORG_1]` statt `[KLINIK_1]`. Eine „Musterfirma GmbH" oder ein Amtsgericht
  als Klinik auszuweisen war schlicht falsch.
- Firmen werden an ihrer Rechtsform erkannt (GmbH, AG, KG, OHG, GbR, UG,
  e. V., Ltd.), dazu Gerichte, Kanzleien, Steuerberatungen, Versicherungen,
  Krankenkassen, Berufsgenossenschaften und Banken.

**Behoben**
- Beträge mit Eurozeichen wurden nicht erkannt. Hinter `€` stand eine
  Wortgrenze `\b`, die dort nie greifen kann, weil `€` kein Wortzeichen ist —
  das Muster zog nur bei ausgeschriebenem „EUR".

**Neu**
- `tests/test_dokumenttypen.py` prüft eine Rechnung und ein Unfallgutachten
  über alle drei Stufen.

**Projektunterlagen**
- Lizenz Apache-2.0 (`LICENSE`), Fremdlizenzen in `NOTICE`. Bemerkenswert:
  PyMuPDF steht unter der AGPL-3.0 — für den lokalen Einsatz entsteht daraus
  keine Pflicht, für einen veränderten Netzwerkdienst schon.
- `CITATION.cff` für die maschinenlesbare Zitation; ORCID nachtragbar.
- README um Zielgruppe, Schnellstart, durchgerechnetes Beispiel,
  Haftungsausschluss, Kontakt und Entstehungshinweis ergänzt.
- Neuer Abschnitt „Wie belastbar ist die Erkennung?": Trefferquote und
  Fehlalarmrate sind **nicht gemessen**. Das steht jetzt ausdrücklich da,
  statt es offenzulassen.
- Reproduzierbarkeit: getestete Umgebung dokumentiert (Python 3.13.3,
  spaCy 3.8.14, Modell 3.8.0, Tesseract 5.5.2). Das Sprachmodell ist in
  `requirements.txt` mit fester Version verzeichnet und wird mitinstalliert —
  der bisherige separate `spacy download` liess die Version offen.
- `pydantic` und `requests` waren vorausgesetzt, aber nicht aufgeführt.

## 0.3.0 — 2026-07-31

Der Satzspiegel überlebt jetzt den Weg durch das Programm.

**Behoben**
- Absatzgrenzen gingen beim Einlesen von PDFs vollständig verloren. Absätze
  sind im PDF blosser Weissraum und erzeugen keinen Text; der einfache
  Textmodus lieferte deshalb einen einzigen Klumpen. Gelesen wird nun über
  die Layoutblöcke des PDFs, die bei Fliesstext den Absätzen entsprechen.
- Weiche Zeilenumbrüche wurden als feste übernommen und beim Export erneut
  erzwungen. Bei anderer Satzbreite entstand daraus Flattersatz mit
  einzelnen Wörtern auf eigener Zeile — verstärkt dadurch, dass ein
  Pseudonym selten so lang ist wie der ersetzte Klarname. Zeilen, die bis an
  den Rand reichen, werden jetzt wieder zu durchgehenden Absätzen
  zusammengefügt. Anschriftenblöcke, Überschriften und Aufzählungen bestehen
  aus kurzen Zeilen und bleiben unangetastet.
- Die Zusammenführung greift nur, wenn der Text tatsächlich hart umbrochen
  aussieht. Bereits sauber gesetzter Text wird nicht angefasst.
- Anatomie-Stoppliste um Schädel- und Felsenbeinbegriffe erweitert
  („Neurocranium" galt als Ortsname).

**Nebenwirkung**
- Die Erkennung wird durch den Reflow genauer: das Sprachmodell sieht
  vollständige Sätze statt Zeilenfragmente. „Hippocampussklerose" wurde
  vorher, weil allein auf einer Zeile stehend, als Personenname erkannt.

**Verbessert**
- PDF-Export mit grösserem Zeilenabstand und echtem Absatzabstand.
- DOCX-Export mit Absatzabstand und Zeilenabstand 1,15.
- Neuer Regressionstest `tests/test_formatierung.py`: prüft Absatzerhalt,
  Schutz von Anschriftenblöcken und Aufzählungen, unveränderte
  Zeilenstruktur nach dem Ersetzen und den Satzspiegel im Ziel-PDF.

## 0.2.0 — 2026-07-31

Drei wählbare Anonymisierungsstufen.

**Neu**
- Stufen `leicht`, `standard` und `streng`, umschaltbar ohne neue Analyse.
  Die Stufe bestimmt je Kategorie die Behandlung: behalten, auf Initialen
  kürzen, vergröbern, verschieben oder ersetzen.
- Initialen statt Namen in der leichten Stufe („Elisabeth Hartmann" wird
  „E. H."). Titel bleiben stehen, weil sie die Rolle im Dokument tragen.
  Gleiche Initialen werden durchnummeriert.
- Einheitliche Datumsverschiebung in der Standardstufe: absolute Daten
  verschwinden, die Abstände zwischen ihnen bleiben exakt erhalten.
- Altersdekaden statt Geburtsdatum in der Standardstufe, berechnet gegen das
  späteste Datum im Dokument als Stichtag.
- Neue Kategorien für die strenge Stufe: Altersangabe („67-jährige"),
  Zeitraum („seit 3 Jahren"), Jahreszahl („seit 1994"). In den schwächeren
  Stufen stehen sie auf „behalten".
- Der Exportvermerk nennt die verwendete Stufe und weist bei „leicht"
  ausdrücklich auf den fortbestehenden Personenbezug hin.
- Warnhinweis in der Oberfläche, solange die leichte Stufe aktiv ist.

**Behoben**
- Das Geburtsdatum wird samt Auslöser erfasst, sonst entstand „geb. Jahrgang
  1958" beziehungsweise „geb. 60–69 J.".
- Vergröberte Altersangaben behalten ihre Wortform: „60–69-jährige" statt
  „60–69 J." mitten im Satz.
- Die Stufenknöpfe tragen ein `aria-label`; ihr sichtbarer Text steckt in
  Kindelementen und blieb für Vorlesesoftware sonst unlesbar.

## 0.1.0 — 2026-07-31

Erste lauffähige Fassung.

**Einlesen**
- PDF mit Textlayer über PyMuPDF
- Gescanntes PDF automatisch über Tesseract-OCR (deutsch); erkannt an
  weniger als 100 Zeichen pro Seite. PyMuPDF rastert die Seiten selbst,
  dadurch keine Abhängigkeit auf ocrmypdf, Ghostscript oder poppler.
- Word `.docx` inklusive Kopf-/Fusszeilen und Tabellen
- Direkte Texteingabe
- Warnung, wenn die Quelldatei Klarnamen in den Metadaten trägt

**Erkennung**
- Regex-Regeln für Datum, Geburtsdatum, Telefon, Fax, E-Mail, URL, IBAN,
  Versichertennummer, Fall-/Patientennummer, Aktenzeichen, Anschrift,
  Einrichtungsnamen sowie Personen über Anrede und Titel
- spaCy `de_core_news_lg` für Namen, Orte und Organisationen im Fliesstext
- Stoppliste für Anatomie und medizinische Fachbegriffe, damit Befundtext
  lesbar bleibt
- Rollenzuordnung Patient/Behandler über den nächstgelegenen Kontextmarker
- Zusammenführung von Schreibvarianten: „Hartmann", „Elisabeth Hartmann"
  und „E. Hartmann" bilden eine Gruppe
- Konsistenz-Nachlauf: jede erkannte Bezeichnung wird abschliessend im
  gesamten Dokument nachgeschlagen

**Prüfen**
- Farbige Markierung im Volltext, umschaltbar auf die Ergebnisansicht
- Gruppen einzeln oder kategorieweise ab- und anwählbar
- Kategorie pro Gruppe korrigierbar
- Freitextfeld für Begriffe, die keine Regel findet
- Warnung, wenn in einem längeren Dokument kein einziger Personenname
  gefunden wurde

**Ausgabe**
- TXT, DOCX und PDF, Metadaten jeweils aktiv geleert
- Zuordnungstabelle als CSV, nur auf ausdrückliche Bestätigung

**Betrieb**
- FastAPI, gebunden ausschliesslich an 127.0.0.1
- Zustandslos: kein Upload-Verzeichnis, keine Session, keine Datenbank
- Regressionstests für Erkennung und für den vollständigen Durchlauf
  inklusive Prüfung der fertigen Exportdateien auf verbliebene Klarnamen
