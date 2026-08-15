# Backlog

Offene Punkte, nach Nutzen sortiert. Erledigtes wandert ins `CHANGELOG.md`.

## Naheliegend

- **OCR-Auslöser: Lesbarkeit statt nur Zeichenzahl.** Heute entscheidet
  allein `len(text)/Seiten < 100`, ob auf OCR umgeschaltet wird. Ein PDF mit
  defekter `ToUnicode`-Tabelle oder kaputtem CID-Mapping liefert aber
  *reichlich* Text — nur besteht der aus Zeichensalat. Der Schwellenwert
  greift dann nicht, und der Müll geht ungeprüft in die Erkennung, wo weder
  Regex noch NER etwas finden. Ein leeres Ergebnis sieht dabei aus wie ein
  sauberes.

  Umsetzung: zusätzlich zum Zeichenzähler den Anteil plausibler Zeichen
  messen — Buchstaben, Ziffern, Satzzeichen, Leerraum gegen die Gesamtzahl.
  Liegt er unter etwa 0,85, oder liegt der Anteil von Zeichen ausserhalb
  Latin-1/Latin-Extended-A auffällig hoch, gilt der Textlayer als
  unbrauchbar und OCR übernimmt. Beides zusammen in einer Funktion
  `_textlayer_brauchbar(text) -> bool` in `extract.py`, damit die
  Entscheidung an einer Stelle steht und testbar ist. Der bestehende
  Hinweistext an den Nutzer ist um den Grund zu ergänzen: „Textlayer
  vorhanden, aber nicht lesbar" ist etwas anderes als „kein Textlayer".
- **Konfidenz-Ampel im Review.** Die Oberfläche unterscheidet heute nur
  belegt und unbelegt. Die Daten für eine feinere Abstufung liegen bereits
  vor: `Fund.quelle` sagt, ob der Treffer aus einer Regex oder aus dem
  Sprachmodell stammt, `Gruppe.sicher` sagt, ob ein Marker in der Nähe
  stand.

  Umsetzung: drei Stufen statt zwei — Regex (strukturell eindeutig),
  Sprachmodell mit Kontextbeleg, Sprachmodell ohne Beleg. Nur die dritte
  Stufe wird farblich hervorgehoben; die ersten beiden bleiben ruhig. Der
  Zweck ist, den Blick des Prüfenden dorthin zu lenken, wo das System am
  ehesten danebenliegt — eine Ampel, die überall Farbe zeigt, erreicht das
  Gegenteil. Die Sortierung der Seitenleiste sollte optional nach
  Konfidenz statt nach Textposition möglich sein.

  Ergänzung aus externem Feedback (2026-08-04): Ein Tastaturkürzel, das
  gezielt zur nächsten unbelegten Fundstelle springt, statt die Liste
  durchscrollen zu müssen — genau dort, wohin die Ampel den Blick lenken
  soll. Dazu Bestätigen/Verwerfen einer Fundstelle per Taste (Vorschlag:
  Leertaste bestätigt, Entf verwirft — beide bereits durch bestehende
  Aktionen belegt, siehe `kategorienInAuswahl`/`auswahlUebernehmen` in
  `app.js`, vor Umsetzung auf Kollisionen prüfen). Manuelles Zuweisen der
  Rolle Arzt/Patient pro Taste (`U`/`P`) ist ebenfalls sinnvoll, sofern es
  ausschliesslich greift, wenn eine Fundstelle fokussiert ist und kein
  Eingabefeld — sonst kollidiert es mit normalem Tippen im Freitextfeld
  „Zusätzlich ersetzen". Review-Arbeit an einem langen Dokument ist
  Akkordarbeit; das rechtfertigt den Aufwand einer durchdachten
  Tastaturbedienung, aber genau deshalb muss die Fokus-Logik zuerst stehen,
  nicht die Tastenbelegung.
- **Sichtbare Rückmeldung beim Stufenwechsel.** Der Wechsel zwischen
  Leicht/Standard/Streng läuft rein clientseitig (siehe §9 der
  Funktionsbeschreibung — alle Formen sind vorberechnet). Das ist der
  Punkt, nicht sichtbar zu sein: keine Netzwerkanfrage, keine Wartezeit.
  Genau das kann aber wie ein Ausbleiben der Reaktion wirken. Ein kurzer,
  weicher Übergang auf den Markierungen beim Neuzeichnen (CSS-Transition
  auf Hintergrundfarbe/Text, ~150 ms, wie an anderen Stellen der
  Oberfläche bereits verwendet) würde die Änderung spürbar machen, ohne
  eine Ladeanimation vorzutäuschen, die es nicht gibt.
- **Einrichtungsname über den Zeilenumbruch.** Steht der Absender umbrochen
  im Briefkopf („BEZIRKSKLINIKUM\nMAINKOFEN"), wird nur die erste Zeile
  erfasst; der Ortsname bleibt stehen. Kein Muster greift absichtlich über
  einen Umbruch — das hatte früher dazu geführt, dass der Umbruch beim
  Ersetzen verschluckt wurde und zwei Platzhalter aneinanderklebten. Ein
  Nachlauf, der die Folgezeile prüft, ohne den Umbruch in den Treffer zu
  ziehen, wäre der Weg.
- **Zwei Fehlalarme des Sprachmodells.** „MRT DES SCHÄDELS" und „Zentrum
  der Läsion" kommen als Einrichtung an. Beide bestehen seit Langem und
  sind unabhängig von der Versalregel. Gemeinsames Merkmal ist ein
  Artikel im Wortinneren („DES", „der") — bei echten Namen steht dort
  „am", „an der" oder „für". Eine Regel darauf ist denkbar, muss aber
  gegen „Universität der Bundeswehr" geprüft werden.
- **Impressum und Datenschutzerklärung.** Fehlen bisher vollständig. Sobald
  der Dienst wieder öffentlich erreichbar ist, sind beide Pflicht — das
  Impressum nach § 5 DDG, die Datenschutzerklärung nach Art. 13 DSGVO.
  Vorlagen liegen bereits im eigenen Bestand: `neuro-praxis/app/impressum`
  und `neuro-praxis/app/datenschutz` (elf Abschnitte), dazu
  `eeg-navigator/app/impressum`. Die Struktur lässt sich übernehmen, die
  Inhalte müssen vom Betreiber selbst kommen.

  Drei Punkte sind hier anders als bei einer gewöhnlichen Website:

  - **Die Datenschutzerklärung ist ungewöhnlich kurz** — und das ist die
    eigentliche Aussage. Es gibt keine Speicherung, keine Konten, keine
    Auswertung, keine Weitergabe. Der bereits ausformulierte Abschnitt „Der
    Weg Ihrer Datei" auf der Startseite beschreibt das schon präzise und
    kann die Grundlage bilden.
  - **Es werden Gesundheitsdaten verarbeitet**, auch wenn nur flüchtig.
    Damit greift Art. 9 DSGVO, nicht nur Art. 6. Das gehört benannt.
  - **Offen und vorab zu klären:** Wenn Kolleginnen und Kollegen den Dienst
    mit echten Patientendokumenten nutzen, stellt sich die Frage nach einem
    Auftragsverarbeitungsvertrag. Das ist eine juristische Einschätzung, die
    nicht aus dem Code folgt — vor einer Öffnung über den eigenen Gebrauch
    hinaus zu klären.
- **Anmeldung ohne Benutzernamen.** Der Zugang läuft heute über Basic Auth in
  Caddy. Auf mobilen Geräten macht das wiederholt Probleme — der Dialog
  erscheint unzuverlässig, gespeicherte Zugangsdaten greifen nicht, und die
  Abfrage nach einem Benutzernamen ist bei einem Dienst mit genau einem
  Zugang ohnehin überflüssig. Gewünscht ist stattdessen eine eigene
  Startseite, die nur nach dem Passwort fragt und dann in die Anwendung
  führt. Beim Umbau bleibt zu beachten, dass `/health` weiterhin ohne
  Anmeldung erreichbar sein muss und der Dienst zustandslos bleibt — eine
  Sitzung darf nichts über den Upload festhalten.
- **Mobile Nutzung.** ✅ Grösstenteils erledigt (2026-08-15). Die Darstellung
  stapelte dank bestehender Breakpoints (640/780/1000px) schon vorher
  brauchbar auf schmalen Bildschirmen — das eigentliche Problem war die
  Bedienung: Touch-Ziele wie die Fund-Checkbox waren real nur 13×13px
  gross, mehrere Erklärungen (warum ein Fund "unbelegt" ist, was eine
  Stufenmatrix-Zelle bedeutet) steckten ausschliesslich in title-Tooltips
  ohne Touch-Äquivalent, das "Zusätzlich markieren"-Menü hatte keine
  Kollisionsprüfung gegen den Bildschirmrand und schloss sich nur über
  `mousedown`, zwei Eingabefelder lösten Safaris automatischen Zoom aus,
  und Fundliste/Dokument hatten auf Touch ein verschachteltes
  Scroll-Verhalten. Alles behoben, per `@media (pointer: coarse)` gezielt
  auf Fingerbedienung statt nur auf Bildschirmbreite reagierend — ein
  schmales Desktop-Fenster mit Maus bleibt unverändert dicht. Details in
  CHANGELOG. **Offen, bewusst separat:** Anmeldung über Basic Auth bleibt
  auf mobilen Browsern unzuverlässig (siehe „Anmeldung ohne Benutzernamen"
  oben) — betrifft den Serverbetrieb, nicht die lokale Nutzung, und ist
  ein eigenständiges Problem.
- **Schreibvarianten zusammenführen.** „Lisbeth" läuft als eigene Person,
  nicht als Variante von „Elisabeth Hartmann". Beide werden ersetzt, bekommen
  aber verschiedene Kürzel. Ein Knopf „mit anderer Gruppe zusammenführen" in
  der Seitenleiste würde das lösen.
- **Gleiche Nachnamen sauber trennen.** Steht „Hartmann" allein im Text und
  es gibt zwei Personen dieses Namens, wird die Stelle ersetzt, aber
  möglicherweise dem falschen Pseudonym zugeordnet. Heute nicht auflösbar;
  denkbar wäre eine Rückfrage im Review statt einer stillen Entscheidung.
- **Ort in der Standardstufe.** Aktuell bleibt „Passau" stehen, während
  „94032 Passau" ersetzt wird. Das folgt der Stufenmatrix, sieht im Text aber
  uneinheitlich aus. Offen, ob `ORT` in der Standardstufe auf „ersetzen"
  gehört.
- **Mehrspaltige PDFs und Tabellen.** Die Absatzerkennung liest die
  Layoutblöcke in Lesereihenfolge. Bei zweispaltigem Satz oder breiten
  Tabellen kann diese Reihenfolge kippen. Bisher nicht an echten Beispielen
  geprüft.

  Umsetzung: Vorhanden sind bereits `_spaltig()` und `_hauptspalte()`, aber
  beide arbeiten *innerhalb* eines Blocks. Was fehlt, ist die Ebene darüber
  — die **Reihenfolge der Blöcke**. Vorschlag: je Seite die `x0`-Werte aller
  Blöcke sammeln und auf zwei Häufungen prüfen (eindimensionales Clustering
  genügt, etwa grösste Lücke in der sortierten Folge gegen die Seitenbreite
  gewichtet). Fallen die Blöcke in zwei klar getrennte Bänder, primär nach
  Band, sekundär nach `y` sortieren; sonst wie bisher rein nach `y`.

  Das ist mehr als ein Layoutproblem: Kippt die Reihenfolge, wandern
  Textstellen in falsche Nachbarschaft, und damit greifen die
  Kontextfenster der Rollenzuweisung (80/50 Zeichen) ins Leere. Ein
  Absender aus Spalte eins kann dann neben einem Patientennamen aus Spalte
  zwei landen. Der Fehler ist also nicht bloss unschön, er verfälscht
  Zuordnungen.

## Nützlich

- **Fundquelle im Tooltip anzeigen.** ✅ Erledigt (2026-08-14). Der Tooltip
  über einer Fundstelle zeigt jetzt Kategorie, Quelle ("Regelbasiert" /
  "Sprachmodell" / "Sprachmodell, unbelegt" / "Konsistenz-Nachlauf" /
  "Manuell markiert") und Ersatz in einer Zeile (`quelleKurz()` in
  `static/app.js`). Keine Backend-Änderung nötig, `Fund.quelle` wurde
  schon vorher mitgeschickt. Grenze bleibt: unterscheidet nur "regelbasiert"
  von "Sprachmodell", nicht die einzelne Regel unter den z. B. vier
  ADRESSE-Mustern — dafür bräuchte jede der rund 80 REGELN-Zeilen einen
  eigenen Namen, das ist bewusst nicht vorgesehen (siehe unten).

- **Stufenmatrix im Programm sichtbar machen.** ✅ Erledigt (2026-08-14).
  Ausklappbare Übersicht "Alle Stufen im Vergleich" in der Seitenleiste
  (`zeichneStufenmatrix()` in `static/app.js`), direkt aus `Z.stufen`/
  `Z.kategorien` aufgebaut statt als Textkopie der README-Tabelle gepflegt
  — bleibt dadurch automatisch in Sync mit `stufen.py`. Kategorien, die auf
  allen drei Stufen ohnehin immer ersetzt werden (Kennnummern, Telefon,
  E-Mail), fasst eine Sammelzeile zusammen, aus den Daten selbst
  abgelesen statt `_DIREKT` in JS zu duplizieren. Die Spalte der gerade
  gewählten Stufe ist hervorgehoben. In Chrome (hell/dunkel) geprüft.
- **Eigene Begriffslisten.** Wiederkehrende Namen (Kolleginnen und Kollegen,
  Stationen, Zuweiser) einmal hinterlegen, statt sie in jedem Dokument über
  „Zusätzlich ersetzen" nachzutragen — heute wirkt das nur für das eine
  offene Dokument, nicht dauerhaft. Muss lokal bleiben und darf nie ins
  Repository geraten.

  Mit der geplanten Veröffentlichung wird das wichtiger, nicht unwichtiger:
  Sobald andere das Werkzeug selbst installieren, braucht jede Praxis, jede
  Klinik ihre eigene, private Liste — Kolleginnen, Stationen und Zuweiser
  unterscheiden sich von Standort zu Standort. Eine Voraussetzung dafür,
  falls umgesetzt: die Datei darf niemals eine Vorlage im Repository sein,
  auch keine leere mit Beispieleinträgen — sonst landet beim ersten
  unbedachten `git add -A` einer dritten Person echte Information darin.
  Ein `.gitignore`-Eintrag reicht dafür allein nicht — eine ungewollte
  Änderung an dieser einen Zeile hebt den Schutz sofort auf. Sicherer: die
  Datei ausserhalb des Repository-Verzeichnisses ablegen (z. B. im
  Nutzerverzeichnis), damit ein Commit sie strukturell gar nicht erreichen
  kann, unabhängig von `.gitignore`.
- **Stapelverarbeitung.** Mehrere Dateien nacheinander mit derselben Stufe
  und denselben Entscheidungen. Sinnvoll erst, wenn der Review-Schritt dabei
  erhalten bleibt — ohne ihn wäre es genau der falsche Komfort.
- **Erkennungsgüte messen.** 🚧 Läuft (2026-08-14), `tests/test_goldkorpus.py`
  läuft mit zehn Briefen in CI. Ein kleiner Satz von Hand annotierter,
  frei erfundener Dokumente, gegen den sich Trefferquote und Fehlalarme
  beziffern lassen — vorher beruhte die Beurteilung nur auf Durchlesen.

  Umsetzung: **Ziel 20 bis 30** vollständig erfundene Briefe (Stand: 10),
  jeder mit einer Randfallklasse. Alle ursprünglich genannten Randfallklassen
  sind jetzt abgedeckt:
  - ✅ Doppelnamen und Namen mit Präfix („van der Berg") —
    `doppelname_praefix` — deckte dabei einen echten Fund auf: die
    Namenskette riss bei „van der" ab, Arztnamen wie „Petra van der
    Berg-Ostermann" wurden nur bis zum Vornamen erkannt. Behoben in
    `app/detect.py` (`_NAMENSPARTIKEL`), siehe CHANGELOG.
  - ✅ nichtdeutsche Namen, die zugleich Fachbegriff lesbar sind —
    `nichtdeutscher_name_fachbegriff` (Nachname „Kolik" neben dem
    Diagnosewort „Nierenkolik" im selben Brief)
  - ✅ Namen, die zugleich Ortsnamen sind — `ortsname_als_name`
    („Frau Hamburg" neben einer echten Ortsangabe „Klinikum Bremen")
  - ✅ OCR-typische Verstümmelungen — `ocr_verstuemmelt` (`rn`→`m`, `l`→`I`,
    fehlende Umlaute in Name/Adresse/Arztname; alle blieben trotzdem
    vollständig erkannt)
  - ✅ zitierter Fremdbefund mit zweitem Behandler und drittem Patienten —
    `fremdbefund_zitat`; deckte auf, dass Verwandtschaftswörter
    ("Vaters") in der NER-Stoppliste fehlten
  - ✅ Medikationstabelle — `tabelle_medikation`; deckte auf, dass eine
    fünfstellige Dosierung mit Einheitenkürzel ("20000 IE") fälschlich
    als PLZ+Ort-Adresse gelesen wurde
  - ✅ Versalsatz mit mehrspaltigem Briefkopf — `versalsatz_mehrspaltig`;
    deckte gleich drei Funde auf: Versal-Einrichtungen ohne
    zusammengesetztes Präfix ("KLINIK AM AUWALD") wurden nie erkannt,
    kurze Bindewörter rissen die Namenskette ab, und ohne Lückenbreiten-
    Schranke zog der Treffer die zweite Spalte eines kopierten,
    mehrspaltigen PDF-Kopfs mit hinein; zusammengeschriebene Versal-
    Strassennamen ("LUDWIGSTRASSE 47") fielen zusätzlich durch
  - ✅ drei weitere Diagnosegruppen — `diagnose_entzuendlich` (Enzephalitis;
    deckte auf, dass Virustypen mit angehängter Zahl wie "HSV-1" in
    `_ist_abkuerzung()` an der Ziffer scheiterten), `diagnose_hirntumor`
    (Glioblastom; INN-Endung „zolomid" ergänzt), `kfz_unfallgutachten`
    (ein Nicht-Arztbrief-Dokument: Aktenzeichen, Kfz-Kennzeichen,
    Versicherungspolice, Geldbeträge)

  Zwei gefundene Fehlalarme bewusst **nicht** behoben, dokumentiert statt
  versteckt (kein Privatsphäre-Risiko, beide werden trotzdem ersetzt):
  „perifokalem Ödem" als ORT (isoliert nicht reproduzierbar, klassische
  NER-Kontext-Sensitivität) und eine doppelte, leicht inkonsistente
  Erfassung der Sachverständigen in `kfz_unfallgutachten` (Titel
  „Dipl.-Ing." wird von keiner ARZT-Regel erkannt) — Details in den
  jeweiligen `.json`-Dateien im Korpus.

  Noch offen für weiteren Ausbau in Richtung 20–30: mehr Diagnosevielfalt
  über die jetzt vertretenen zehn Fälle hinaus.

  Format je Dokument: `<slug>.txt` (Brief) + `<slug>.json`
  (`{"beschreibung": ..., "funde": [{"typ": ..., "text": ...}, ...]}`) —
  bewusst **ohne Positions-Spannen**, nur Text+Typ-Paare je erwarteter
  Fundstelle. Robuster gegenüber kleinen Textänderungen, keine externe
  Bibliothek nötig. Ausgewertet wird getrennt nach **Recall** (was fehlt)
  und **Präzision** (was zu viel ist) — ein einzelner F-Wert würde genau
  die Asymmetrie verwischen, auf die es hier ankommt: ein übersehener Name
  wiegt schwerer als ein Fehlalarm.

  Ratsche: der Stand liegt in `tests/goldkorpus_stand.json` (Recall/
  Präzision je Dokument), `tests/test_goldkorpus.py` schlägt fehl, sobald
  einer der beiden Werte gegenüber diesem Stand sinkt. Eine Verbesserung
  wird nicht automatisch übernommen — `--stand-aktualisieren` schreibt den
  neuen Stand, der dann bewusst mitcommittet wird.

  Orientierung für Aufbau und Stil kam aus *Arztbriefe in der Neurologie*
  (Schmidt-Wilcke/Sturm, Springer 2023) — nur zur Struktur, kein Satz
  daraus übernommen: das Buch ist urheberrechtlich geschützt, alle Briefe
  hier sind komplette Neuschöpfungen.

  Alle Inhalte müssen erfunden sein und dürfen keinem realen Fall
  nachgebildet werden — das Korpus liegt im öffentlichen Repository.
- **Zitierte Fremdbefunde.** Arztbriefe zitieren andere Briefe: „In dem
  Bericht von Herrn Dr. Müller über Frau Schmidt heisst es …". Die
  Rollenzuweisung arbeitet über die Distanz zum nächsten Marker; in solchen
  Schachtelungen stehen mehrere Marker im selben Fenster, und die Zuordnung
  wird zum Münzwurf.

  Umsetzung: Zitatbereiche über Marker erkennen (Anführungszeichen über
  mehrere Sätze, „Vorbefund:", „Fremdbefund:", „Auszug aus", „Im Bericht
  vom") und Funde darin ein Merkmal `im_zitat` geben.

  Wichtig, damit daraus kein Sicherheitsrückschritt wird: Das Merkmal darf
  **nichts daran ändern, dass ersetzt wird**. Namen in einem Fremdbefund
  sind genauso schützenswert, eher mehr — es sind womöglich weitere
  Betroffene. Es geht ausschliesslich um zwei Dinge: die Rollenzuweisung
  soll in solchen Bereichen keine Sicherheit vortäuschen (Typ bleibt
  `PERSON`, statt zu raten), und der Review soll die Stellen gebündelt
  anzeigen, weil dort die Zuordnung erfahrungsgemäss geprüft gehört.

- **Kurze englische Projektbeschreibung.** ✅ Erledigt (2026-08-14). Repo-
  Oberfläche, Regeln und README bleiben bewusst Deutsch — das Werkzeug ist
  für deutschsprachige Dokumente gebaut — aber ein kurzer englischer Absatz
  direkt unter dem Titel im README erklärt jetzt, was das Werkzeug tut und
  dass die Erkennungslogik (Muster-vs-Wortliste-Prinzip in `app/detect.py`)
  auf andere Sprachen übertragbar wäre. GitHub-„About"-Feld ebenfalls auf
  Englisch gesetzt. Kein Umbau auf eine zweisprachige README-Struktur —
  nur eine kurze Einstiegsbrücke für internationale Leser.

## Später

- **Geschwärztes Original-PDF.** Layout bleibt erhalten, sensible Stellen
  werden geschwärzt und der darunterliegende Text wirklich entfernt. Deutlich
  aufwändiger und nur bei PDFs mit Textlayer sinnvoll; bewusst zugunsten des
  neu gesetzten Fliesstextes zurückgestellt.
- **Weitere Sprachen.** Heute ausschliesslich Deutsch — Regeln, Stoppliste
  und Sprachmodell. Englische Arztbriefe oder Rechnungen laufen ins Leere.
- **Tabellen im DOCX als Tabellen ausgeben.** Sie werden derzeit zu
  tabulatorgetrenntem Text und verlieren ihre Struktur.

## Bewusst nicht vorgesehen

Jeder Punkt hier wurde geprüft und mit Begründung abgelehnt — nicht
übersehen oder aufgeschoben. Wer einen dieser Punkte erneut vorschlägt
(intern oder als Issue nach der Veröffentlichung), findet die Begründung
hier; sie gilt, bis sich die zugrunde liegende Voraussetzung ändert, nicht
bis jemand sie zum ersten Mal wieder aufwirft.

- **Cloud oder externe Schnittstelle.** Das Werkzeug verarbeitet Arztbriefe
  und Gutachten; nichts davon darf den Rechner verlassen. Der Server bindet
  nur an 127.0.0.1 und bleibt zustandslos.
- **Automatischer Export ohne Review.** Keine Erkennung erreicht hundert
  Prozent Trefferquote. Der Prüfschritt ist kein Komfort, sondern der Kern.
- **Zuordnungstabelle automatisch speichern.** Sie hebt die Anonymisierung
  auf und wird deshalb nur auf ausdrückliche Bestätigung erzeugt.
- **Multi-Core-Batchverarbeitung für grosse Dokumentmengen** (2026-08-14,
  externes Feedback). Widerspricht dem Kernprinzip: der manuelle
  Prüfschritt vor jedem Export ist kein Komfort, sondern der
  Sicherheitsmechanismus selbst (siehe „Für wen" im README, „Ausdrücklich
  nicht gedacht als … unbeaufsichtigte Stapelverarbeitung"). Eine
  Batch-Engine, die diesen Schritt umgeht, wäre kein Performance-Feature,
  sondern ein Sicherheitsrückschritt.
- **Reversible Pseudonymisierung über HMAC/Secret-Key-Vault** (2026-08-14,
  externes Feedback). Die konsistenten Platzhalter (`[PATIENT_A]`,
  `[ARZT_1]`) gibt es schon, ohne einen Schlüssel speichern zu müssen. Ein
  Secret Key, der eine Rückführung auf die echte Identität erlaubt, wäre
  ein gespeichertes Geheimnis — widerspricht der zustandslosen
  „nichts wird gespeichert"-Zusicherung, auf der das gesamte
  Vertrauensmodell des Werkzeugs beruht.
- **Erkennungsregeln nach YAML/JSON auslagern** (2026-08-14, externes
  Feedback). Jede Regel in `app/detect.py` trägt einen Kommentar, der
  erklärt, warum sie existiert und welchen realen Fehlalarm sie behebt —
  diese Begründung ist der eigentliche Audit-Trail des Projekts. Eine
  Auslagerung in eine Konfigurationsdatei würde Muster von ihrer
  Begründung trennen und Fachfremden erlauben, Regeln zu ändern, ohne die
  in `CONTRIBUTING.md` vorgeschriebene Pflicht zu einem Positiv- und
  Negativtest je neuer Regel einzuhalten.
- **Formale Pipeline-/Protocol-Architektur** (2026-08-14, externes
  Feedback). Für ein Solo-gepflegtes Projekt dieser Grösse (vier
  Verarbeitungsschritte: Extraktion, Erkennung, Stufen, Export) wäre eine
  generische Plugin-Architektur eine Abstraktion ohne aktuellen Bedarf.
