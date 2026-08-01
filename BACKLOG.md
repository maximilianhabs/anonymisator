# Backlog

Offene Punkte, nach Nutzen sortiert. Erledigtes wandert ins `CHANGELOG.md`.

## Naheliegend

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
