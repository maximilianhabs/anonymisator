# Road to Public

Konzept und Schritt-für-Schritt-Plan für den Wechsel von privat zu
öffentlich auf GitHub. Repo bleibt bis zum bewussten Umschalten privat —
dieses Dokument bereitet vor, es schaltet nichts um.

Die Struktur folgt elf übertragbaren Lehren aus einer anderen
Review-Serie (EDF-Analyzer, drei externe Durchsichten). Jede Lehre wird
hier nicht abstrakt zitiert, sondern gegen den tatsächlichen Stand des
Anonymisators geprüft — mit Datum und Befund, nicht mit Vermutung. Wo
nichts zu tun ist, steht das auch so da.

---

## Der Massstab

> Ein öffentliches Repository wird nicht danach beurteilt, wie gut der
> Code ist, sondern daran, ob man seinen Aussagen trauen kann.

Für den Anonymisator heisst das konkret: Jede Zusicherung im README
("nichts wird gespeichert", "keine Vollständigkeit garantiert", "läuft
lokal") muss an der Stelle stimmen, wo sie gelesen wird — nicht nur im
README, sondern im laufenden Programm und im exportierten Dokument.

---

## Die elf Lehren, geprüft gegen den Anonymisator (Stand 2026-08-12)

### 1. Der Sprung ist nicht „funktioniert es", sondern „kann man es glauben"

**Geprüft:** `grep` nach "validiert", "zertifiziert", "garantiert" in
README, `app/`, `static/`. Ergebnis: **kein Fehlklassifikations-Risiko wie
beim EDF-Analyzer.** Der Anonymisator behauptet an keiner Stelle
Vollständigkeit — im Gegenteil, README §„Grenzen" und die
Export-Bestätigung sagen ausdrücklich das Gegenteil ("Die Erkennung kann
Namen übersehen — Vollständigkeit ist nicht garantiert").

Der Grund: Der Anonymisator hat kein Äquivalent zur
Methoden-Registry-Behauptung, weil er keine einzelne Kennzahl als
"validiert" ausgibt, sondern einen Text zur Prüfung durch einen Menschen
vorlegt. Das strukturelle Risiko aus Lehre 1 entfällt also nicht durch
Vorsicht, sondern durch die Architektur selbst — der Prüfschritt ist so
oder so Pflicht.

**Bleibt zu tun:** Nichts Neues. Bei jeder künftigen README-Änderung
weiter so präzise bleiben.

### 2. Die gefährlichen Fehler stürzen nicht ab

**Geprüft:** Die Fehlerklasse "plausibel aussehendes falsches Ergebnis
ohne Fehlermeldung" trifft auf den Anonymisator in abgeschwächter Form
zu — nicht als Berechnungsfehler, sondern als **übersehene Fundstelle**.
Ein Name, der nicht erkannt wird, erzeugt keine Fehlermeldung; er sieht
im Ergebnis wie ein bereits geprüfter, sauberer Text aus.

Das ist der Grund, warum „Erkennungsgüte messen" (BACKLOG.md, Abschnitt
„Nützlich") als **wichtigste offene Lücke** markiert ist — dort auch
schon so benannt. Diese Lehre bestätigt nur, mit fremdem Vokabular, was
im eigenen Backlog bereits richtig priorisiert war.

**Bleibt zu tun:** Das Goldkorpus bauen (siehe Schritt 6 unten) — vor
Punkt 4 im Zeitplan, weil genau das hier beschriebene Risiko sonst nach
der Veröffentlichung unbemerkt bleibt.

### 3. Behauptungen, die nichts prüft, driften weg

**Geprüft:** Der Anonymisator hat bereits neun Testdateien, die genau
diesem Prinzip folgen — `test_fehlalarme.py` prüft nicht nur, was
erkannt wird, sondern was **nicht** erkannt werden darf, mit
benannten Beispielen. `test_export_hygiene.py` prüft die Zusicherung
"keine Metadaten" auf Byte-Ebene, nicht durch Lesen des Codes.

**Kein Ratschen-Mechanismus vorhanden.** Der EDF-Analyzer hat einen
Layering-Prüfer, der bestehende Altlasten namentlich duldet und neue
verbietet. Der Anonymisator hat kein Äquivalent — nicht, weil es
gebraucht würde (es gibt keine bekannte, geduldete Architekturschulden-
Liste), sondern weil das natürliche Analogon woanders liegt: **das
Goldkorpus selbst wird die Ratsche**, sobald es existiert — ein Test,
der eine Verschlechterung gegenüber einem festgeschriebenen Stand meldet
(so bereits in BACKLOG.md konzipiert), ist strukturell dieselbe Idee.

**Bleibt zu tun:** Beim Bau des Goldkorpus (Schritt 6) den
Ratschen-Gedanken explizit übernehmen: der Test schlägt fehl, wenn der
Recall gegenüber dem letzten commiteten Stand sinkt, nicht erst, wenn er
unter einen absoluten Schwellenwert fällt.

### 4. Reviews sind unterschiedlich gut — jede Behauptung einzeln prüfen

**Bereits gelebte Praxis in diesem Projekt.** Die externe Durchsicht vom
2026-08-04 wurde in dieser Konversation bereits Punkt für Punkt gegen
den Code geprüft — zwei der drei vorgeschlagenen Sofortmassnahmen liefen
schon, die Lizenzempfehlung (AGPL statt Apache-2.0) erwies sich beim
Nachlesen von `NOTICE` als bereits gelöst, nur anders als vorgeschlagen.

**Beim Schreiben dieses Konzepts genauso verfahren:** Der Verdacht, ein
Passwort-Hash läge fest im Repository (`docker-compose.yml:97`), wurde
per SSH gegen den Server geprüft, bevor er als Befund gemeldet wird. Er
hat sich **nicht bestätigt** — siehe Lehre 5 unten. Das ist die Methode,
nicht die Ausnahme.

**Bleibt zu tun:** Falls vor der Veröffentlichung eine weitere externe
Durchsicht eingeholt wird, jeden Punkt einzeln gegen den Code prüfen,
nicht pauschal übernehmen oder verwerfen.

### 5. Öffentlich zu gehen ändert das Bedrohungsmodell, nicht den Code

**Das ist der Abschnitt mit den echten Funden.** Geprüft wurden:
Default-Passwörter, interne Adressen, Kliniknamen in Kommentaren,
Font-CDN, Telemetrie — jeweils einzeln, mit Ergebnis:

| Punkt | Befund |
|---|---|
| Default-Passwort im Quelltext | **Kein Fund, aber verwechslungsgefährlich.** `docker-compose.yml:97` enthält einen bcrypt-Hash als Ersatzwert. Per SSH gegen den Server geprüft: es ist der dokumentierte Platzhalter für "ein zufälliges Passwort, das niemand kennt" (Kommentar direkt daneben) — Caddy sperrt damit zu, nicht auf. Kein Leck. Bleibt so. |
| **Reale Serveradresse im Repo** | **Echter Fund.** `DEPLOYMENT.md` nennt `203.0.113.10` neunmal — die tatsächliche, aktive IP eines Servers, auf dem **auch andere private Projekte** liegen (Dienstwerk, EEG-Navigator). Öffentlich einsehbar würde das den Server als Angriffsziel identifizierbar machen, unabhängig vom Anonymisator selbst. |
| Kliniknamen in Kommentaren | **Echter, kleiner Fund.** `app/detect.py` nennt „Mainkofen" zweimal als Beispiel in Erklärkommentaren zur Regex-Logik. Eine echte, existierende psychiatrische Einrichtung als wiederkehrendes Beispiel widerspricht der eigenen, in `NOTICE` erklärten Regel „alle verwendeten Namen sind frei erfunden". Für die Regex-Erklärung ist der Name beliebig — ein erfundener funktioniert genauso gut. |
| Font-CDN | **Kein Fund.** Bereits selbst gehostet unter `static/fonts/` (Redesign vom 2026-08-04), keine Anfrage verlässt den Rechner. |
| Telemetrie | **Kein Fund.** Der Dienst ist zustandslos per Architektur, kein Tracking-Skript im Frontend. |
| GPL/AGPL-Abhängigkeit in Apache-Projekt | **Kein Fund, bereits durchdacht.** `NOTICE` erklärt die AGPL-Lage von PyMuPDF explizit inklusive der Konsequenz bei Netzwerkbetrieb (§13). Vorbildlich, nicht nachzubessern. |

**Bleibt zu tun:**
- `DEPLOYMENT.md` vor der Veröffentlichung entweder aus dem öffentlichen
  Repo ausschliessen (z. B. in eine private Zweitablage verschieben, nur
  eine generische Kurzanleitung ohne IP im öffentlichen Teil belassen)
  oder die IP durchgehend durch einen Platzhalter ersetzen
  (`<server-ip>` oder `dein-server.example`). Die zweite Option ist
  vorzuziehen — die Anleitung bleibt dann für andere nachvollziehbar.
- `app/detect.py`: „Mainkofen" durch einen erfundenen Einrichtungsnamen
  ersetzen (z. B. „Waldheim", bereits an anderer Stelle im Projekt als
  fiktives Beispiel verwendet). Zwei Zeilen, keine Verhaltensänderung.

### 6. Das Billigste ist oft das Wichtigste

**Echter Fund, direkte Parallele.** Der Haftungshinweis existiert im
Anonymisator — aber nur als einmaliger `window.confirm()`-Dialog beim
Export (`static/app.js`, Funktion um Zeile 790). Wer die exportierte
Datei später weitergibt, ausdruckt oder archiviert, hat diesen Text nie
wieder vor Augen. Der `_VERMERK` in `app/export.py` trägt nur Stufe und
Datum ("Anonymisiert am … — automatisch erkannt und manuell geprüft"),
keinen Haftungshinweis.

Das ist exakt der Befund aus der anderen Review-Serie, nur an einer
anderen Stelle der Kette: dort war es das README, das niemand liest, der
die App benutzt; hier ist es der Bestätigungsdialog, den niemand mehr
sieht, sobald das Dokument die App verlassen hat.

**Bleibt zu tun:** `_VERMERK` in `app/export.py` um einen kurzen
Zusatz erweitern, z. B. „— Vollständigkeit nicht garantiert, Verantwortung
für die Weitergabe bleibt beim Absender." Aufwand: eine Codezeile pro
Stufentext, keine Logikänderung. Genau die Art Fund, die diese Lehre
meint.

Zweiter Punkt aus derselben Lehre: **kein Screenshot, kein GIF im
README.** Bestätigt (`find . -iname "*.png" -o -iname "*.gif"` liefert
nichts ausser den beiden neuen Schriftdateien). Bereits einmal versucht
(2026-08-04) und am fehlenden Speicherweg für Browser-Screenshots
gescheitert — siehe Schritt 3 unten für einen Weg, der diesmal
funktioniert.

### 7. Bewusste Nicht-Entscheidungen gehören dokumentiert

**Bereits vorhanden.** `BACKLOG.md` hat einen Abschnitt „Bewusst nicht
vorgesehen" mit drei begründeten Ablehnungen (Cloud-Anbindung,
automatischer Export ohne Review, automatisch gespeicherte
Zuordnungstabelle). Das entspricht der Lehre strukturell.

**Kleine Lücke:** Die Einträge tragen keinen ausdrücklichen Vermerk
„nicht erneut aufwerfen" — bei drei Einträgen noch kein praktisches
Problem, aber ab der öffentlichen Phase kommen wahrscheinlich neue
Vorschläge von aussen (genau diese drei Punkte fragen externe Prüfer
erfahrungsgemäss zuerst).

**Bleibt zu tun:** Beim nächsten Backlog-Update diesen Abschnitt um den
Vermerk ergänzen, dass die Punkte geprüft und bewusst abgelehnt sind —
kein Sofortbedarf, aber vor dem ersten öffentlichen Issue dazu hilfreich.

### 8. Ursache untersuchen statt Toleranz aufweichen

**Bereits gelebte Praxis, mit Beleg.** Bei jeder in dieser Konversation
behobenen Fehlalarm-Runde wurde die Wortbildungsregel verschärft
(Mindestlängen, Wortgrenzen, Fachbegriff-Endungen), nie eine bestehende
Prüfung gelockert, um einen Test grün zu bekommen. `tests/test_erkennung.py`
prüft explizit die Gegenrichtung: dass eine neue Filterregel keine echten
Nachnamen verschluckt (Kollisionsliste `Kraft`, `Nase`, `Ohr`, `Wert` …).

**Bleibt zu tun:** Nichts. Diese Disziplin in `feedback_anonymisator_erkennung.md`
(lokales Gedächtnis) bereits als Punkt 12 festgehalten — weiter danach
arbeiten.

### 9. Das Erzeugnis ansehen, nicht nur erzeugen

**Geprüft, mit echtem Test statt Vermutung.** Deutsche Sonderzeichen
(ä ö ü ß Ä Ö Ü) wurden gerade durch den tatsächlichen PDF-Export
geschickt und aus der erzeugten Datei zurückgelesen (PyMuPDF-Extraktion).
Ergebnis: **sauber, kein Zeichen verändert oder verloren.** Das war die
konkrete Sorge aus der anderen Review-Serie (dort: „Gąsior" wurde zu
„G■sior") — beim Anonymisator nicht eingetreten, weil ReportLabs
Helvetica-Basisschrift den benötigten Zeichensatz (WinAnsi/Latin-1)
abdeckt.

**Aber:** Dieser Test lief eben manuell, einmalig, nicht dauerhaft.
`test_export_hygiene.py` prüft PDF-Metadaten und Klarnamen-Abwesenheit
auf Byte-Ebene, aber nicht Sonderzeichen-Korrektheit.

**Bleibt zu tun:** Den eben durchgeführten Test dauerhaft in
`tests/test_export_hygiene.py` aufnehmen — sonst gilt die Prüfung nur für
heute, nicht für jede künftige Änderung an Schrift oder Exportcode.

### 10. Automatische Korrekturen brauchen Urteilsvermögen

**Kein aktueller Fund, aber eine Regel für den weiteren Weg.** `ruff
check` läuft in der CI, `ruff --fix` (automatische Korrektur) wird nicht
automatisch ausgeführt — richtig so. Der Anonymisator hat mehrere
Stellen, an denen Reihenfolge und Kommentarplatzierung Bedeutung tragen
(z. B. die Regelliste in `detect.py`, wo Priorität von der Position
abhängt).

**Bleibt zu tun:** Vor der Veröffentlichung nicht `ruff --fix` blind über
den ganzen Baum laufen lassen. Jede vorgeschlagene automatische Korrektur
einzeln lesen, insbesondere Importreihenfolge und alles, was
`app/detect.py` betrifft.

### 11. Fremde Daten finden, was eigene nie zeigen

**Echte Spannung, kein Widerspruch — aber ungelöst.** Die andere
Review-Serie profitierte von echten PhysioNet-Aufnahmen. Der
Anonymisator hat die entgegengesetzte, bewusste Regel: **niemals ein
echtes Dokument**, auch nicht zum Testen (siehe `.gitignore`,
`NOTICE`). Diese Regel bleibt richtig — sie ist der Kern der
Vertrauenswürdigkeit des Projekts und wird nicht aufgeweicht.

Die Lehre lässt sich trotzdem übertragen, nur anders: nicht „echte
Patientendaten besorgen", sondern **öffentlich verfügbare, echte
Formulierungs- und Layout-Muster** verwenden, die selbst keine
Personendaten tragen — Vorlagen-Arztbriefe, wie sie Kliniken auf ihren
eigenen Webseiten als Muster veröffentlichen, oder real gescannte,
schlecht erkannte OCR-Artefakte aus selbst erzeugten Testscans. Das
deckt genau die Klasse Fehler ab, die synthetischer Text nie zeigt:
echte Briefkopf-Layouts, echte Scanner-Bildfehler, echte
Zeilenumbruch-Muster von echter Software (Word, Diktiersystemen).

**Bleibt zu tun:** Beim Bau des Goldkorpus (Schritt 6) diese Quelle
ausdrücklich mit einplanen — Layout-Vorlagen ja, Personendaten nie.

---

## Zusammenfassung: was neu ist, was schon stimmt

**Bereits solide, keine Änderung nötig:**
Lizenz- und AGPL-Dokumentation, Font-Hosting, fehlende Telemetrie,
Test-Disziplin gegen Toleranz-Aufweichung, README-Ehrlichkeit über
Grenzen, SECURITY.md, Export-Hygiene auf Byte-Ebene, Auth-Fallback ist
fail-closed (nicht das befürchtete Leck).

**Echte, verifizierte Funde — in Prioritätsreihenfolge nach Aufwand:**
1. Haftungshinweis fehlt im exportierten Dokument selbst (eine Zeile,
   grösste Wirkung — Lehre 6)
2. Reale Server-IP in `DEPLOYMENT.md` (Textersatz, vor Veröffentlichung
   zwingend — Lehre 5)
3. „Mainkofen" in Code-Kommentaren durch fiktiven Namen ersetzen (zwei
   Zeilen — Lehre 5)
4. `CITATION.cff` zeigt Version 0.11.0, aktuell ist 0.14.1 (ein Feld)
5. Sonderzeichen-Regressionstest dauerhaft in die Testsuite aufnehmen
   (Lehre 9)
6. Screenshot/GIF fürs README (Lehre 6, aufwändiger — eigener Schritt)
7. Goldkorpus mit Ratschen-Logik (Lehre 2, 3, 11 — grösster Einzelposten,
   aber bereits konzipiert in BACKLOG.md)
8. Impressum/Datenschutzerklärung (bereits in BACKLOG.md als Pflicht vor
   öffentlichem Betrieb vermerkt, unabhängig vom Repo-Status)

---

## Schritt-für-Schritt-Plan

Die Reihenfolge trennt bewusst **Repo-Sichtbarkeit** von
**Server-Sichtbarkeit** — der Server bleibt so oder so pausiert und
unabhängig entschieden. „Öffentlich" heisst hier: das GitHub-Repository.

### Phase 1 — Sofort erledigbar, geringes Risiko (vor jeder weiteren Prüfung)

1. `app/export.py`: `_VERMERK`-Texte um den Haftungssatz erweitern.
   Danach `test_export_hygiene.py` erweitern, um zu prüfen, dass der
   Zusatz in jeder Exportform (TXT/DOCX/PDF) tatsächlich ankommt.
2. `app/detect.py`: „Mainkofen" in den zwei Kommentarzeilen durch einen
   erfundenen Namen ersetzen.
3. `CITATION.cff`: Version und Datum auf den aktuellen Stand heben.
4. Den eben durchgeführten Sonderzeichen-Test als festen Fall in
   `tests/test_export_hygiene.py` aufnehmen.
5. `BACKLOG.md`, Abschnitt „Bewusst nicht vorgesehen": Vermerk ergänzen,
   dass die Punkte geprüft und bewusst abgelehnt sind.

Jeder dieser fünf Punkte ist unabhängig, risikolos, und verändert kein
Verhalten der Erkennung. Lässt sich in einer Sitzung erledigen und
committen.

### Phase 2 — Vor jeder Veröffentlichung zwingend

6. `DEPLOYMENT.md` bereinigen: Server-IP durch Platzhalter ersetzen, im
   ganzen Dokument. Die konkrete IP für den eigenen Gebrauch bleibt in
   diesem Memory-System hinterlegt, nicht im Repo — dort ist sie ja
   schon (`reference_server_uebersicht.md` u. ä.).
7. Einmal `git log --all --diff-filter=A --name-only` über das ganze
   Repo laufen lassen (nicht nur den aktuellen Stand) und nach PDFs,
   DOCX, TXT, Screenshots mit Personenbezug suchen — auch wenn
   `.gitignore` das seit Beginn verhindert haben sollte, ist das der
   Punkt, an dem man es nachweist statt annimmt (Lehre 1).
8. `git grep` über die volle Historie nach IPs, internen Hostnamen,
   E-Mail-Adressen ausserhalb der bereits geprüften Fälle.

### Phase 3 — Vertrauenswürdigkeit sichtbar machen

9. Screenshot oder kurzes GIF der Prüfansicht fürs README erzeugen. Der
   Weg vom 2026-08-04 scheiterte daran, dass ein im Werkzeug erzeugter
   Screenshot nicht auf die Platte geschrieben werden konnte — Weg über
   `mcp__Claude_Code_iOS_Simulator` entfällt (kein iOS-Projekt), aber ein
   Screenshot lässt sich auch über die Bash-Kommandozeile mit einem
   Werkzeug wie `screencapture` (macOS, systemeigen) vom offenen
   Browserfenster ziehen, dateibasiert, ohne das Browser-Werkzeug selbst
   zu bitten, etwas zu speichern, was es nicht speichern kann.
10. Goldkorpus bauen (siehe BACKLOG.md, Abschnitt „Erkennungsgüte
    messen" — dort bereits vollständig konzipiert: 20–30 Briefe,
    Randfallklassen, getrennte Recall-/Präzisionsauswertung). Mit
    Ratschen-Logik: `tests/test_goldkorpus.py` schlägt fehl, sobald der
    Recall gegenüber dem letzten commiteten Stand sinkt.
11. Impressum und Datenschutzerklärung (bereits in BACKLOG.md
    konzipiert, Vorlagen aus anderen eigenen Projekten vorhanden) — wird
    erst wirksam, wenn der Server wieder läuft, aber kann unabhängig vom
    Repo-Status vorbereitet werden.

### Phase 4 — Der Umschalter

12. Repo bleibt bis hierhin **privat**. Erst wenn Phase 1 und 2
    vollständig sind und Phase 3 mindestens den Goldkorpus enthält, ist
    der Zeitpunkt für den Wechsel gekommen.
13. Vor dem Umschalten: eine letzte, externe Durchsicht einholen (Lehre
    4) — und jeden Punkt einzeln gegen den dann aktuellen Code prüfen,
    nicht pauschal übernehmen.
14. Repo auf öffentlich stellen. Server-Reaktivierung ist eine separate
    Entscheidung, unabhängig davon.

---

## Was dieses Konzept bewusst nicht tut

Es implementiert nichts. Phase 1 besteht aus fünf kleinen, unabhängigen
Änderungen — auf Wunsch als Nächstes einzeln umsetzbar. Phase 2 und 3
sind grösser und verdienen eine eigene Rücksprache, bevor sie beginnen,
insbesondere der Goldkorpus (Aufwand: mehrere Sitzungen) und die
Screenshot-Frage (Werkzeugfrage, noch ungelöst).
