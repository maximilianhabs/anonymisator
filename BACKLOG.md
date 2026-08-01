# Backlog

Offene Punkte, nach Nutzen sortiert. Erledigtes wandert ins `CHANGELOG.md`.

## Naheliegend

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
  lassen. Heute beruht die Beurteilung auf Durchlesen.

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
