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
- **Oberfläche modernisieren.** Die Gestaltung wirkt altbacken. Betrifft
  Typografie, Abstände, Farbwerte und die Anmutung der Bedienelemente, nicht
  den Aufbau: der Ablauf aus Hochladen, Prüfen und Ausgeben hat sich
  bewährt und soll erhalten bleiben.
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

- **Stufenmatrix im Programm sichtbar machen.** Heute steht sie nur im
  README. Eine ausklappbare Übersicht in der Seitenleiste würde zeigen, was
  eine Stufe konkret tut, bevor man sie wählt.
- **Eigene Begriffslisten.** Wiederkehrende Namen (Kolleginnen und Kollegen,
  Stationen, Zuweiser) einmal hinterlegen, statt sie in jedem Dokument über
  „Zusätzlich ersetzen" nachzutragen. Muss lokal bleiben und darf nie ins
  Repository geraten.
- **Stapelverarbeitung.** Mehrere Dateien nacheinander mit derselben Stufe
  und denselben Entscheidungen. Sinnvoll erst, wenn der Review-Schritt dabei
  erhalten bleibt — ohne ihn wäre es genau der falsche Komfort.
- **Erkennungsgüte messen.** Ein kleiner Satz von Hand annotierter, frei
  erfundener Dokumente, gegen den sich Trefferquote und Fehlalarme beziffern
  lassen. Heute beruht die Beurteilung auf Durchlesen. **Das ist die
  wichtigste offene Lücke** — jede Aussage über die Erkennungsleistung ist
  bis dahin eine Vermutung, und ein Rückschritt beim Recall bliebe
  unbemerkt, weil die vorhandenen Tests nur prüfen, was *nicht* gefunden
  werden darf.

  Umsetzung: 20 bis 30 vollständig erfundene Briefe, jeder mit einer
  Randfallklasse, die heute nicht abgedeckt ist:
  - Doppelnamen und Namen mit Präfix („van der Berg", „Di Lorenzo")
  - nichtdeutsche Namen, auch solche, die als Fachbegriff lesbar sind
  - Namen, die zugleich Ortsnamen sind („Frau Hamburg")
  - OCR-typische Verstümmelungen (`rn`→`m`, `l`↔`I`, fehlende Umlaute)
  - zitierte Fremdbefunde mit zweitem Behandler und drittem Patienten
  - Tabellen, Versalsatz, mehrspaltige Briefköpfe

  Format: Rohtext plus eine Liste erwarteter Spannen `(start, ende, typ)` je
  Datei, keine externe Bibliothek. Ausgewertet wird getrennt nach
  **Recall je Kategorie** (was fehlt) und **Präzision** (was zu viel ist) —
  ein einzelner F-Wert würde genau die Asymmetrie verwischen, auf die es
  hier ankommt: ein übersehener Name wiegt schwerer als ein Fehlalarm.
  Läuft als `tests/test_goldkorpus.py` bei jedem Durchlauf mit und meldet
  eine Verschlechterung gegenüber einem festgeschriebenen Stand.

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

- **Cloud oder externe Schnittstelle.** Das Werkzeug verarbeitet Arztbriefe
  und Gutachten; nichts davon darf den Rechner verlassen. Der Server bindet
  nur an 127.0.0.1 und bleibt zustandslos.
- **Automatischer Export ohne Review.** Keine Erkennung erreicht hundert
  Prozent Trefferquote. Der Prüfschritt ist kein Komfort, sondern der Kern.
- **Zuordnungstabelle automatisch speichern.** Sie hebt die Anonymisierung
  auf und wird deshalb nur auf ausdrückliche Bestätigung erzeugt.
