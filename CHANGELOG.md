# Änderungen

Dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).
Solange die Hauptversion 0 ist, können sich Schnittstellen und Kürzel
zwischen Nebenversionen ändern.

## 0.20.0 — 2026-08-15

Zwei Funde aus einem echten Testlauf mit einem DRG-Entgeltnachweis, vom
Nutzer per Screenshot gemeldet.

- **Vierstellige Geldbeträge ohne Tausendertrennzeichen verloren die erste
  Ziffer.** "2050,75 €" (in Entgeltnachweisen üblich, kein "2.050,75 €")
  kam nur als "050,75 €" an. Ursache: die führende Zifferngruppe war auf
  höchstens drei Stellen begrenzt (`\d{1,3}`) — ohne folgendes
  Tausendertrennzeichen rutschte der Regex-Motor einfach eine Stelle
  weiter, bis irgendwo ein kürzeres Fenster passte. Grenze jetzt offen
  (`\d+`); bei echt gruppierten Zahlen ("2.050,75 €") ändert sich nichts,
  vor dem Punkt steht ohnehin nur die kurze erste Gruppe.
- **"Gültiges"/"Gültige" als Feldkommentar kam unbelegt als Person an.**
  DRG-Entgeltnachweise beginnen Feldkommentare regelmässig so ("Gültiges
  Geschlecht. Nicht für Grouping verwendet") — grossgeschrieben durch die
  Satzanfangsposition, nicht durch einen Eigennamen. Alle Deklinations-
  formen als Stoppwort ergänzt.

3 neue Fälle in `test_fehlalarme.py`, mit Gegenprobe gegen eine echt
gruppierte Zahl.

## 0.19.0 — 2026-08-15

Mobile-Optimierung: Bedienung auf Smartphone und kleinem Tablet. Die
Darstellung stapelte dank bestehender Breakpoints (640/780/1000px) schon
vorher brauchbar — das eigentliche Problem war die Bedienung. Sechs
konkrete Funde, jeder einzeln im Browser (Chrome-Emulation, 375/393/768px,
hell und dunkel) geprüft:

- **Touch-Ziele waren real zu klein.** Die Fund-Checkbox in der Prüfliste
  war gemessen nur 13×13px gross — das meistgenutzte Bedienelement der
  ganzen Anwendung. Mehrere Buttons lagen bei 26–32px. Neue Regel über
  `@media (pointer: coarse)`, nicht über Bildschirmbreite: reagiert auf
  Fingerbedienung unabhängig von der Displaygrösse, ein schmales
  Desktop-Fenster mit Maus bleibt unverändert dicht. Checkbox jetzt 22px,
  alle Buttons/Tabs mindestens 44px (Apple HIG / Material Design).
- **Tooltip-only-Information ohne Touch-Äquivalent.** Die Begründung, warum
  ein Fund "unbelegt" ist, und die Erklärung je Stufenmatrix-Zelle steckten
  ausschliesslich im `title`-Attribut — kein Hover auf dem Finger. Neues,
  wiederverwendbares Info-Popover (nach Vorbild des bestehenden
  Auswahl-Menüs), per Tap auf das "?"-Zeichen bzw. eine Stufenmatrix-Zelle.
  Das "?" ist jetzt ein echtes Element mit eigenem Tap-Ziel statt eines
  `::after`-Pseudoelements.
- **"Zusätzlich markieren" war durchgehend mausorientiert.** Die
  Positionierung des Auswahl-Menüs hatte keine Kollisionsprüfung gegen den
  rechten/unteren Bildschirmrand, und das Schliessen hing an einem reinen
  `mousedown`-Listener. Neuer gemeinsamer Helfer `positionGeklemmt()` (auch
  vom neuen Info-Popover genutzt): klemmt an den Viewport, klappt bei
  fehlendem Platz nach oben statt unten. Schliessen zusätzlich an
  `touchstart` gebunden.
- **iOS-Zoom-Falle.** Das Eingabefeld für Text und das Feld „Zusätzlich
  ersetzen" hatten 13px Schrift — unter Safaris 16px-Schwelle zoomt iOS
  beim Fokussieren automatisch hinein. Auf 16px angehoben.
- **Verschachteltes Scrollen.** Fundliste und Dokumentansicht hatten auf
  schmalen Bildschirmen eine eigene, begrenzte Scroll-Höhe — auf einem
  Touch-Gerät die klassische Scroll-Falle, ein Wisch bewegt nur die
  kleine Box statt der ganzen Seite. Diese Begrenzung gilt jetzt nur noch
  mit Maus/Trackpad (`pointer: fine`); auf Touch-Geräten scrollt die ganze
  Seite als Ganzes.

Kein Python/Backend betroffen, bestehende Testsuite unverändert grün.

## 0.18.0 — 2026-08-14

Zwei Quick Wins aus einer externen Durchsicht der Oberfläche — die übrigen
Vorschläge dieser Runde beschrieben grösstenteils bereits Vorhandenes
(FastAPI, Docker, Regex-Precompile) oder widersprachen bewussten
Design-Entscheidungen (siehe `BACKLOG.md`, „Bewusst nicht vorgesehen").

- **Fundquelle im Tooltip.** Beim Überfahren einer markierten Stelle zeigt
  der Tooltip jetzt zusätzlich, wie der Fund zustande kam — regelbasiert,
  Sprachmodell (ggf. „unbelegt"), Konsistenz-Nachlauf oder manuell markiert.
  Die Information gab es serverseitig schon vorher (`Fund.quelle`), nur die
  Oberfläche zeigte sie nirgends an.
- **„Alle Stufen im Vergleich".** Neue ausklappbare Übersicht in der
  Seitenleiste, direkt neben der Stufenwahl: eine Tabelle, was jede der drei
  Stufen mit jeder Kategorie tut — bisher stand das nur im README. Aus
  denselben Daten aufgebaut, die auch die Stufenwahl selbst speist, bleibt
  dadurch automatisch mit `stufen.py` in Sync.

## 0.17.0 — 2026-08-14

Goldkorpus von 3 auf 10 Briefe erweitert — alle in `BACKLOG.md` genannten
Randfallklassen jetzt abgedeckt (OCR-Verstümmelung, zitierter Fremdbefund,
Medikationstabelle, Versalsatz mit mehrspaltigem Kopf), dazu drei weitere
Diagnosegruppen und ein Nicht-Arztbrief-Dokument (Kfz-Unfallgutachten).
Jeder neue Brief einzeln gegen die Erkennung geprüft, bevor er aufgenommen
wurde — dabei acht echte Funde:

- **Verwandtschaftswörter fehlten in der NER-Stoppliste.** "Vaters" (Genitiv)
  kam unbelegt als Person an — `_KEIN_NAME` kannte Vater/Mutter/Bruder/
  Schwester/Sohn/Tochter/Ehemann/Ehefrau/Eltern/Angehörige/Betreuer nur für
  die Regex-Schicht, nicht für die NER-Schicht.
- **PLZ + Grosseinheiten-Kürzel wurde zur Adresse.** "20000 IE" (Vitamin D3)
  erfüllte die PLZ+Ort-Regel aus 0.15.2 (Versalien) ungewollt — "IE" ist
  zwei Grossbuchstaben und damit ein gültiger, nur zu kurzer Versal-Ortsname.
  Mindestlänge auf drei Zeichen angehoben.
- **Versal-Einrichtungen ohne zusammengesetztes Präfix wurden nie erkannt.**
  "KLINIK AM AUWALD" oder "KLINIKUM MUSTERSTADT" fielen durch — nur
  zusammengesetzte Präfixformen wie "BEZIRKSKLINIKUM" funktionierten, weil
  der bisher verpflichtende erste Buchstabe stets den Anfang des Kopfworts
  selbst mit auffraß. Der häufigere, einfache Fall war seit Einführung der
  Regel (0.12.0) unentdeckt.
- **Kurze Bindewörter ("AM", "IM" …) rissen Versal-Einrichtungsnamen ab**,
  und ohne Schranke bei der Lückenbreite zog ein zu grosszügiges Muster
  danach die zweite Spalte eines kopierten, mehrspaltigen Briefkopfs mit
  hinein. Beides in derselben Regel behoben.
- **Zusammengeschriebene Strassennamen in Versalien** ("LUDWIGSTRASSE 47")
  wurden von keiner Adressregel erfasst, weil das Suffix nur kleingeschrieben
  geprüft wurde — sie fielen stattdessen der Einrichtungserkennung zu.
- **Virustyp mit angehängter Zahl** ("HSV-1", "HHV-6") kam unbelegt als
  Organisation an: `_ist_abkuerzung()` entfernte Bindestriche, aber keine
  Ziffern, bevor sie auf reine Buchstaben prüfte.
- **Zwei weitere INN-Wirkstoffstämme ergänzt:** "-clovir" (Aciclovir und
  verwandte Virostatika) und "zolomid" (Temozolomid) — beide kamen unbelegt
  als Person an.

Details und Fallstricke in `feedback_anonymisator_erkennung.md` (Memory)
sowie als Kommentar direkt an der jeweiligen Regel in `app/detect.py`.
Zwei Funde bewusst nicht behoben, weil nicht reproduzierbar bzw. ohne
Privatsphäre-Risiko: siehe `tests/goldkorpus/diagnose_hirntumor.json` und
`kfz_unfallgutachten.json`.

## 0.16.0 — 2026-08-14

Erster Schritt beim Goldkorpus (`tests/goldkorpus/`, `tests/test_goldkorpus.py`):
ein kleiner Satz frei erfundener Briefe mit von Hand geprüfter Ground Truth,
ausgewertet getrennt nach Recall und Präzision, mit Ratsche gegen einen
committeten Stand. Details und offene Randfallklassen in `BACKLOG.md`.

Beim Bau des ersten Briefs (Doppelname mit Präfix) ein echter Fund:

- **Arztnamen mit „van der"/„van den" wurden nur bis zum Vornamen erkannt**
  („Petra van der Berg-Ostermann" → nur „Petra"). Die Namenskette riss an
  jedem kleingeschriebenen Wort ab. Behoben über eine kleine, geschlossene
  Partikelliste (`_NAMENSPARTIKEL`) — bewusst ohne „von"/„der"/„den" als
  freistehende Partikel, das sind die häufigsten Wörter der deutschen
  Sprache und stehen in Arztbriefen ständig vor einer Einrichtung, nicht
  vor einem Namensteil („Dr. Schmidt von der Uniklinik Regensburg" darf
  die Klinik nicht in den Namen ziehen). Nur als feste Verbindung nach
  „van" zugelassen. Regressionstest in `test_fehlalarme.py`, Abschnitt 18,
  mit Positiv- und Gegenprobe.

## 0.15.3 — 2026-08-14

Bildgebende Modalitäten (EEG, MRT, CT u. a.) wurden je nach Schreibweise
weiterhin fälschlich markiert — die Grundform war als Stoppwort erfasst,
ihre Abwandlungen nicht.

- **Mehrzahl mit angehängtem „s"** („EEGs", „MRTs") — Abkürzungen werden
  im Deutschen wie Lehnwörter pluralisiert, das galt bisher nicht als
  dieselbe Angabe wie die Einzahl.
- **Zusammengesetzt statt getrennt** („Verlaufslabor", „Chefarztvisite") —
  dieselben Wörter, die einzeln oder mit Bindestrich schon erkannt wurden,
  fielen als Kompositum-Ende durch.
- **Modalität mit Ortskürzel** („cMRT" für kraniell) — als eigene, kleine
  und tatsächlich abgeschlossene Menge ergänzt.
- **Schrägstrich als Worttrenner** — „CT Hals/Thorax" scheiterte daran,
  dass „/" bisher keine erkannte Trennstelle war.

5 neue Fälle in `test_fehlalarme.py`, mit Gegenprobe gegen echte Namen.

## 0.15.2 — 2026-08-13

Drei weitere bestätigte Funde aus derselben Praxistest-Runde.

- **Zwei weitere Wirkstoffstämme ergänzt:** Ethosuximid (Succinimid) und
  die Levetiracetam-Familie (Racetam) kamen als Person bzw. Behandler an.
  Wie schon bei Ebrantil und den zuvor ergänzten Stämmen: der Wirkstoff-
  stamm wird erkannt, nicht der einzelne Markenname.
- **„Sturztraumata" als eigenständiger Fund** — Kompositum aus „Sturz"
  und der Pluralform von „Trauma", bisher nicht als Fachbegriff erkannt.
- **Postleitzahl mit Ort in Versalien** — „94469 DEGGENDORF" wurde nicht
  erfasst, obwohl derselbe Ortsname ohne PLZ meist noch vom Sprachmodell
  gefangen wurde. Die PLZ+Ort-Regel verlangte bislang Binnenkleinschreibung.

Zwei weitere gemeldete Fälle (zwei Vornamen bzw. Nachnamen, ein
Medikament in Kombination mit "i.v.") liessen sich trotz zahlreicher
Kontextvarianten nicht nachstellen und bleiben offen.

## 0.15.1 — 2026-08-13

Aus einer weiteren Praxistest-Runde: eine hochprioritäre Erkennungslücke
geschlossen, ein Medikamenten-Fehlalarm strukturell behoben.

- **„geb." leitet jetzt auch einen Geburtsnamen ein, nicht nur ein Datum.**
  „Frau Müller, geb. Schuster" wurde bisher gar nicht erfasst — die
  einzige Regel über „geb." verlangte zwingend ein folgendes Datum. Beide
  Formen schliessen sich an derselben Stelle gegenseitig aus.
- **Medikamente mit Dosierung gelten nicht mehr als Person.** Markennamen
  wie „Ebrantil" sind für das Sprachmodell namensförmig und wurden
  teils sogar als Behandler eingestuft. Eine Liste aller Markennamen wäre
  unbegrenzt; stattdessen ein strukturelles Merkmal: eine unmittelbar
  folgende Dosierung („Ebrantil 25 mg") macht den Fund zum Medikament,
  unabhängig vom konkreten Namen.
- Zwei beiläufig gefundene Fehlalarme behoben: „Aufnahmegrund" (der
  Feldbezeichner selbst) als Person, „Schwindel" (ein Symptom) als Ort.

Mehrere gemeldete Fälle liessen sich trotz zahlreicher Kontextvarianten
nicht nachstellen und bleiben offen, bis der genaue Originaltext vorliegt.

## 0.15.0 — 2026-08-13

Aus dem Praxistest mit mehreren Dokumenten: eine Adresslücke geschlossen,
zwei neue Kategorien, eine Legende für die Farbcodierung.

**Getrennt geschriebene Strassennamen.** „Königsberger Straße 1" wurde
bisher nicht als Adresse erkannt — die Regel verlangte, dass Strassenname
und Hausnummer als ein Wort zusammenkleben („Ludwigstraße 47"). Getrennt
geschriebene Formen („Königsberger Straße 1", „Am Alten Weg 3", „Berliner
Str. 5") sind im Deutschen mindestens so häufig und liessen bisher die
Hausnummer unbeachtet zurück. Betrifft alle drei Stufen, am stärksten
Standard: dort wird eine korrekt erkannte Adresse ersetzt, ein bloss
vermuteter Ortsname nicht.

**Zwei neue Kategorien, beide erst ab Standard aktiv (in Leicht bleiben
sie stehen):**
- **Geschlecht** — „männlich", „weiblich", „divers", auch dekliniert
  („männlicher Patient"), sowie die Kurzform „m"/"w"/"d", aber nur direkt
  nach einem Feldnamen wie „Geschlecht:". Allein ein schwaches Merkmal,
  zusammen mit Alter, Ort und Diagnose aber ein weiterer Baustein der
  Re-Identifizierung.
- **Diagnosecode** — ICD-10(-GM), OPS und DRG, jeweils nur der Code
  selbst, an ein Auslösewort gebunden („Diagnose:", „ICD-10:", „OPS:",
  „DRG:"). Der Diagnosetext bleibt unangetastet, er ist medizinisch
  wertvoll und für sich genommen kein Identifikator. Bewusst an ein
  Auslösewort gebunden, nicht frei im Text gesucht — ein freistehendes
  Muster wie `[A-Z]\d{2}` träfe auch „Vitamin B12".

**Farbcodierung überarbeitet.** Ort und Einrichtung teilten sich bisher
dieselbe Farbe — eine wiederkehrende Quelle für „ist das jetzt ein Ort
oder eine Zahl?" beim Testen. Ort hat jetzt eine eigene Farbe. Dazu eine
Legende oberhalb des Dokuments (nur im Tab „Erkannt", wo die
Unterscheidung Sinn ergibt): kräftig hinterlegt heisst „wird ersetzt",
gedämpft und gepunktet heisst „bleibt auf dieser Stufe stehen" — bildet
exakt nach, was im Dokument selbst zu sehen ist, damit die Zuordnung ohne
Nachdenken gelingt.

## 0.14.2 — 2026-08-13

Road-to-Public, Phase 1: fünf kleine, unabhängige Korrekturen aus
`ROAD_TO_PUBLIC.md`.

- **Haftungshinweis steht jetzt im exportierten Dokument selbst**, nicht
  mehr nur im einmaligen Bestätigungsdialog vor dem Export. Wer eine Datei
  Monate später weitergibt, ausdruckt oder archiviert, sieht den Hinweis
  weiterhin — bisher stand er ausschliesslich im Browser-Dialog, den
  niemand mehr sieht, sobald das Dokument die Anwendung verlassen hat.
  Gilt für alle drei Formate (TXT/DOCX/PDF), da sie sich denselben Vermerk
  teilen.
- Ein real existierender Einrichtungsname („Mainkofen") in
  Erklärkommentaren zu Regex-Regeln durch die im Projekt bereits
  etablierte fiktive „Klinik am Auwald" ersetzt — passend zur eigenen, in
  `NOTICE` erklärten Regel, dass alle verwendeten Namen frei erfunden
  sind.
- `CITATION.cff` zeigte noch Version 0.11.0 vom 2026-07-31, aktualisiert
  auf den tatsächlichen Stand.
- Sonderzeichen-Rundlauf (ä ö ü ß Ä Ö Ü) durch alle drei Exportformate
  jetzt fester Bestandteil von `test_export_hygiene.py`, nicht mehr nur
  einmalig von Hand geprüft.
- `BACKLOG.md`: Der Abschnitt „Bewusst nicht vorgesehen" trägt jetzt den
  Vermerk, dass die dortigen Punkte geprüft und bewusst abgelehnt sind —
  damit sie nach der Veröffentlichung nicht bei jedem externen Vorschlag
  neu verhandelt werden müssen.

## 0.14.1 — 2026-08-10

Absturz bei grossen Dokumenten mit mehreren gleichnamigen Personen behoben.

- Beim Testen mit einem rund 50-seitigen, eingefügten Text kam es zu einem
  `500 Internal Server Error`, sobald zwei verschiedene Personen denselben
  Nachnamen trugen und beide ausschliesslich über ihre E-Mail-Adresse
  bekannt waren (keine Anrede, kein Titel). Ursache: Beim Anlegen einer
  neuen, aus dem E-Mail-Ortsteil gewonnenen Person wuchs die Menge der
  bekannten Namen mit, das parallel geführte Nachschlagewörterbuch aber
  nicht — traf ein zweiter Name auf denselben Nachnamen, schlug der
  Lookup mit `KeyError` fehl statt ein Ergebnis zu liefern. Wer von zwei
  gleichnamigen Personen den Nachnamen "gewinnt", bleibt eine bekannte,
  hingenommene Grenze (siehe Backlog, „Gleiche Nachnamen sauber trennen") —
  behoben wurde ausschliesslich der Absturz, nicht diese Zuordnungsfrage.
- Gegengeprüft mit einem eingefügten, vollständig erfundenen Text von
  rund 155.000 Zeichen (≈ 50 Seiten): Analyse läuft in unter zehn Sekunden
  durch, keine Zeichen- oder Seitengrenze für eingefügten Text.

## 0.14.0 — 2026-08-04

Gestaltung überarbeitet: eine Anmutung, die zum Gegenstand passt — ein
Werkzeug für vertrauliche Akten, nicht ein Tech-Produkt.

- Gedecktes Papierweiss statt reinem Weiss, ein Tintengrün als einzige
  Markenfarbe. Die Stufenfarben aus 0.13.0 verfeinert auf Salbei/Messing/
  Ochsenblut statt reiner Ampelfarben.
- Zwei Schriften, selbst gehostet unter `static/fonts/` — IBM Plex Sans für
  Bedienelemente, Newsreader für Überschriften und grosse Zahlen. Beide als
  Variable Fonts, zusammen unter 100 KB, keine Schriftart-CDN — folgt aus
  der bestehenden Content-Security-Policy und der Regel, dass die Anwendung
  nichts nachlädt. Lizenzen (SIL OFL 1.1) in `NOTICE` ergänzt.
- Jeder Seitenleisten-Abschnitt jetzt eine eigene Karte statt einer
  durchlaufenden Spalte mit Trennlinien.
- Wortmarke in zwei Schriftschnitten ("Anonym" leicht, "isator" kräftig).
- Dabei ein Layoutfehler gefunden und behoben: Mit allen Karten zusammen
  übersteigt der Inhalt oft die verfügbare Höhe der Seitenleiste. Ohne
  Gegenmassnahme drückt Flexbox die grösste Karte (die Statistik) zusammen —
  mit `overflow: hidden` für die runden Ecken wurde daraus ein unsichtbares
  Verschwinden statt eines sichtbaren Fehlers. Jede Karte behält jetzt ihre
  natürliche Höhe, die Seitenleiste scrollt bei Bedarf als Ganzes.

## 0.13.0 — 2026-08-04

Aus dem Praxistest: Konsistenz für von Hand markierte Stellen, eine
Statistik, farblich erklärte Stufen.

- **Manuelle Markierung gilt jetzt für das ganze Dokument.** Bisher wirkte
  eine per Auswahl markierte Stelle nur an genau dieser einen Stelle. Wird
  z. B. "Deggendorf" von Hand als Ort markiert, gilt das jetzt für jedes
  weitere Vorkommen exakt derselben Zeichenfolge — Gross-/Kleinschreibung
  eingeschlossen, an Wortgrenzen, ohne bereits vergebene Stellen zu
  überschreiben. Spiegelt serverseitig, was der Konsistenz-Nachlauf für
  automatisch erkannte Treffer schon leistet.
- **Statistik.** Eine aufklappbare Übersicht in der Seitenleiste: Anzahl
  je Kategorie (erkannt vs. tatsächlich ersetzt), Summe der Angaben und
  Fundstellen, dazu Zeichenzahl, Seiten und bei Uploads die Dateigrösse.
- **Stufen farblich gekennzeichnet und erklärt.** Leicht/Standard/Streng
  tragen jetzt eine eigene Farbe. Standard und Streng erhalten dieselbe
  erklärende Box, die bisher nur "Leicht" hatte — nicht als Warnung (sie
  sind keine), sondern als Beschreibung des Mechanismus: was genau ersetzt,
  vergröbert oder verschoben wird. Bewusst keine Rechtsaussage ("gilt als
  anonymisiert nach DSGVO"), das kann eine automatische Erkennung nicht
  zusichern.
- **Fehlalarm behoben:** "Kontakt" vor einer E-Mail- oder Telefonangabe
  wurde zur Rolle Patient/in, weil "geboren" der nächstgelegene
  Rollenmarker war. Der Bezeichner fehlte schlicht in der Stoppliste,
  dieselbe Fehlerklasse wie zuvor "Tel". Mit "Ansprechpartner(in)" gleich
  mit behoben.
- `SECURITY.md` ergänzt (fehlte vollständig) — grenzt eine Sicherheitslücke
  ausdrücklich von einer Erkennungsschwäche ab, Letztere ist ein
  Qualitätsmangel, kein Sicherheitsproblem.
- Versionsbadge im README korrigiert (zeigte noch 0.11.0).

## 0.12.0 — 2026-08-01

Erkennungsschärfe aus dem Praxistest an echten Arztbriefen: zwei Runden
gemeldeter Fehlalarme behoben, dazu ein Ausfall bei Briefkopf-Einrichtungen
und ein Fehler in der CI-Prüfung.

**Fachsprache, die nicht mehr für Namen gehalten wird**
- Anatomie in der Kurzform (`N. tibialis`, `Z.n.`, `Lig. collaterale`) —
  bisher war nur die Langform abgedeckt, im Befund steht fast immer die
  Kurzform.
- Lange Komposita mit medizinischem Baustein (`Differentialblutbild`,
  `Hirnnervenstatus`, `Atemwegsinfekt`), ab elf Zeichen Wortlänge — die
  Schranke schützt kurze Nachnamen wie `Herzog` und `Bluthardt`.
- Fachadjektive (`multisegmentale`, `rechtskonvexer`, `granulomatöser`) und
  Partizipien auf `-iert` (`WACH und ORIENTIERT`).
- Verwaltungs- und Messkomposita (`Kassensitz`, `Laborbudget`,
  `Lageempfinden`, `Schilddrüsenparameter`, `Finger-Nase`).
- Wirkstoffstämme der internationalen INN-Nomenklatur (`Ezetimib` u. a. auf
  `-statin`, `-sartan`, `-pril`, `-timib`, `-mumab`).
- Wirbelsäulensegmente (`S1`, `HWK7`, `Th12`), auch als Bestandteil eines
  längeren Treffers.
- Durchgehend kleingeschriebene Modelltreffer (`seitengleich`,
  `bewusstseinsklar`) — im Deutschen trägt jeder Eigenname eine Majuskel.

**Einrichtungen**
- Briefköpfe in Versalien (`BEZIRKSKLINIKUM MAINKOFEN`) wurden vom
  Sprachmodell unzuverlässig erkannt, in der Unterschriftszeile gar nicht.
  Eigenes, vom Sprachmodell unabhängiges Muster für die Versalform.
- Ein Gattungswort im Namen (`klinik`, `krankenhaus`, `zentrum` …) stuft
  einen als Ort erkannten Treffer zur Einrichtung hoch — Orte bleiben in
  der Standardstufe stehen, die behandelnde Einrichtung nicht.

**Konsistenz über das Dokument**
- Der Nachlauf sucht jetzt auch einzelne Namensbestandteile und den
  Ortsteil einer Einrichtung im ganzen Text: aus „Herr Peter Tisch" wird
  auch das spätere blosse „Tisch" geschwärzt, aus „Bezirksklinikum
  Stuttgart" auch das spätere „Stuttgart".

**E-Mail-Adressen**
- Am `@` verankert statt am Zusammenhang: Adressen, die im Briefkopf am
  Spaltenrand umbrechen (`t.schmidt-wilcke` / `@mainkofen.de`), wurden
  bisher übersehen und der Klarname blieb im Ortsteil sichtbar.
- Dabei ein Fehler behoben, der unabhängig vom Umbruch bestand: aus einer
  E-Mail-Adresse gewonnene Namen prüften nicht, ob die Textstelle bereits
  einem anderen Fund gehörte. Lag der Ortsteil in einem bereits erkannten
  vollen Namen, schob sich beim Ersetzen ein Platzhalter in den anderen.

**Betrieb**
- Vier Sicherheitskopfzeilen (`X-Frame-Options`,
  `X-Content-Type-Options`, `Content-Security-Policy`,
  `Referrer-Policy`) wurden nie gesetzt — die CI-Prüfung dafür scheiterte
  seit ihrem Bestehen an einer eigenen, vorgelagerten Ursache (`HEAD`
  statt `GET`) und verbarg damit den eigentlichen Mangel. Beides behoben.

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
