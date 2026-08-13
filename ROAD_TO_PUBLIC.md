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
| **Reale Serveradresse im Repo** | ✅ **Behoben (2026-08-13).** Stand in vier Dateien, 15 Stellen (`DEPLOYMENT.md`, `deploy/vorpruefung.sh`, `deploy/dienst.sh`, sogar in diesem Dokument). Durch die Dokumentations-Platzhalteradresse `203.0.113.10` (RFC 5737, reserviert für genau diesen Zweck) ersetzt — **nicht nur im aktuellen Stand, sondern per `git filter-repo` aus der gesamten Commit-Historie und allen acht Tags entfernt**, dann mit `git push --force` auf den Server durchgesetzt. Verifiziert: `git log --all -p` findet die echte IP an keiner Stelle mehr. Bewusst *kein* Neuaufbau der Historie — nur diese eine Zeichenkette wurde ersetzt, alles andere blieb unangetastet. |
| Kliniknamen in Kommentaren | ✅ **Behoben** (Road-to-Public Phase 1, Commit `b9d2367`). „Mainkofen" in `app/detect.py` durch das bereits im Projekt etablierte fiktive „Auwald" ersetzt. |
| Font-CDN | **Kein Fund.** Bereits selbst gehostet unter `static/fonts/` (Redesign vom 2026-08-04), keine Anfrage verlässt den Rechner. |
| Telemetrie | **Kein Fund.** Der Dienst ist zustandslos per Architektur, kein Tracking-Skript im Frontend. |
| GPL/AGPL-Abhängigkeit in Apache-Projekt | **Kein Fund, bereits durchdacht.** `NOTICE` erklärt die AGPL-Lage von PyMuPDF explizit inklusive der Konsequenz bei Netzwerkbetrieb (§13). Vorbildlich, nicht nachzubessern. |

**Bleibt zu tun:** Nichts mehr aus dieser Lehre. Ehrlicher Hinweis zur
Grenze der Historienbereinigung: Ein bereits vorhandener Klon oder Fork
des Repositories (falls je einer existierte, während es privat war)
behielte die alte Historie mit der echten IP. Bei einem bislang privaten
Repo ohne bekannte Drittklone ist dieses Restrisiko gering.

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

**Stand 2026-08-13 — Phase 1 und Phase 2 vollständig abgeschlossen.**

**Bereits solide, keine Änderung nötig:**
Lizenz- und AGPL-Dokumentation, Font-Hosting, fehlende Telemetrie,
Test-Disziplin gegen Toleranz-Aufweichung, README-Ehrlichkeit über
Grenzen, SECURITY.md, Export-Hygiene auf Byte-Ebene, Auth-Fallback ist
fail-closed (nicht das befürchtete Leck).

**Erledigt:**
1. ✅ Haftungshinweis steht im exportierten Dokument selbst
2. ✅ Reale Server-IP — aus allen aktuellen Dateien **und** aus der
   gesamten Commit-Historie samt Tags entfernt
3. ✅ „Mainkofen" durch „Auwald" ersetzt
4. ✅ Sonderzeichen-Regressionstest dauerhaft in der Testsuite
5. ✅ Volle Historie auf PHI/Secrets geprüft, sauber

**Noch offen, kein Blocker für den Repo-Wechsel:**
6. `CITATION.cff` erneut veraltet (zeigt 0.14.2, aktuell 0.15.1) — driftet
   wiederholt, weil es in keiner Routine steckt; siehe Hinweis unten
7. Screenshot/GIF fürs README — bewusst dem Nutzer überlassen
8. Goldkorpus mit Ratschen-Logik (Lehre 2, 3, 11 — grösster Einzelposten,
   Konzept unten ausgearbeitet)
9. `CONTRIBUTING.md` — neu hinzugekommen, da Beiträge explizit erwünscht
10. Impressum/Datenschutzerklärung — betrifft den Serverbetrieb, nicht
    das Repository; erst relevant, wenn der Server reaktiviert wird

---

## Schritt-für-Schritt-Plan

Die Reihenfolge trennt bewusst **Repo-Sichtbarkeit** von
**Server-Sichtbarkeit** — der Server bleibt so oder so pausiert und
unabhängig entschieden. „Öffentlich" heisst hier: das GitHub-Repository.

### Phase 1 — Sofort erledigbar, geringes Risiko (vor jeder weiteren Prüfung)

**✅ Erledigt am 2026-08-13** (0.14.2). Alle fünf Punkte umgesetzt,
gegengeprüft (Testsuite grün, Live-Probe gegen den laufenden Dienst) und
gepusht.

1. ✅ `app/export.py`: `_VERMERK`-Texte um den Haftungssatz erweitert.
   `test_export_hygiene.py` erweitert — prüft jetzt, dass der Zusatz in
   jeder Exportform (TXT/DOCX/PDF) tatsächlich ankommt.
2. ✅ `app/detect.py`: „Mainkofen" ersetzt — tatsächlich **drei**
   Fundstellen, nicht zwei wie hier ursprünglich vermutet
   (`grep -ni mainkofen` beim Umsetzen genauer geprüft als beim Planen).
   Ersetzt durch die im Projekt bereits etablierte „Klinik am Auwald".
3. ✅ `CITATION.cff`: Version und Datum auf 0.14.2 / 2026-08-13 gehoben.
4. ✅ Sonderzeichen-Rundlauf (ä ö ü ß) als fester Fall in
   `tests/test_export_hygiene.py`, für alle drei Exportformate.
5. ✅ `BACKLOG.md`, Abschnitt „Bewusst nicht vorgesehen": Vermerk ergänzt.

Jeder dieser fünf Punkte war unabhängig, risikolos, und veränderte kein
Verhalten der Erkennung. Details im CHANGELOG, Abschnitt 0.14.2.

### Phase 2 — Vor jeder Veröffentlichung zwingend — ✅ abgeschlossen (2026-08-13)

6. ✅ `DEPLOYMENT.md` und die drei weiteren betroffenen Dateien bereinigt,
   Server-IP durch die Dokumentations-Platzhalteradresse `203.0.113.10`
   ersetzt — **nicht nur im aktuellen Stand, auch in der gesamten
   Commit-Historie und allen Tags** (`git filter-repo`, siehe Lehre 5).
   Die echte IP für den eigenen Gebrauch bleibt im Memory-System
   hinterlegt, nicht im Repo.
7. ✅ `git log --all --diff-filter=A --name-only` über das ganze Repo
   geprüft — keine PDFs, DOCX, TXT oder Screenshots mit Personenbezug in
   der Historie gefunden.
8. ✅ Volle Historie nach IPs, internen Hostnamen, Passwörtern und
   API-Schlüsseln durchsucht — ausser der jetzt behobenen Server-IP kein
   weiterer Fund.

### Phase 3 — Vertrauenswürdigkeit sichtbar machen

9. **Screenshot/GIF fürs README — bewusst dem Nutzer überlassen,** zum
   Schluss vor der Veröffentlichung. Kein technisches Hindernis mehr im
   Weg (macOS `screencapture` funktioniert dateibasiert), aber die
   Bildauswahl selbst ist eine gestalterische Entscheidung.
10. Goldkorpus bauen (siehe BACKLOG.md, Abschnitt „Erkennungsgüte
    messen" — dort bereits vollständig konzipiert: 20–30 Briefe,
    Randfallklassen, getrennte Recall-/Präzisionsauswertung). Mit
    Ratschen-Logik: `tests/test_goldkorpus.py` schlägt fehl, sobald der
    Recall gegenüber dem letzten commiteten Stand sinkt.
11. `CONTRIBUTING.md` — jetzt zusätzlich sinnvoll, weil das Projekt
    explizit für Beiträge geöffnet werden soll. Die Muster-vs-Wortliste-
    Entscheidungsregel aus `app/detect.py` gehört dort verlinkt oder
    zusammengefasst.
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
