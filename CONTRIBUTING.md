# Mitwirken

Danke für das Interesse. Dieses Dokument beschreibt, wie ein Beitrag
zustande kommt — von der Meldung eines Fehlers bis zum fertigen Pull
Request. Der Umgang miteinander dabei steht in
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Die eine Regel, die vor allen anderen steht

**Niemals ein echtes Dokument, einen echten Namen oder eine echte
Textstelle mit Personenbezug einreichen — auch nicht in einem Issue,
auch nicht als Screenshot, auch nicht ausschnittweise.**

Dieses Werkzeug entfernt personenbeziehbare Angaben aus Arztbriefen und
Gutachten. Ein Issue, das zur Veranschaulichung eine echte Textstelle
zitiert, unterläuft genau das, was das Projekt leisten soll — und der
Text bliebe für immer in der GitHub-Historie stehen, selbst wenn er
später gelöscht wird.

Ein frei erfundenes Beispiel zeigt jeden bisher bekannten Fehler genauso
gut wie ein echtes. Etwa so:

> „Königsberger Straße 1" wird nicht als Adresse erkannt, nur als loser
> Ortsname. Die Hausnummer bleibt unmarkiert.

Reicht als Meldung vollständig aus. Kein Auszug aus einem echten Brief
nötig oder gewünscht.

## Einen Fehler melden

Über die [Issues](https://github.com/maximilianhabs/anonymisator/issues)
des Projekts. Am hilfreichsten sind:

- ein **erfundener** Beispielsatz, der den Fehler zeigt
- was erkannt wurde (oder fälschlich nicht erkannt wurde)
- was stattdessen richtig wäre
- die verwendete Stufe (Leicht/Standard/Streng), falls relevant

Eine **Sicherheitslücke** — ein Weg, wie eine geschützte Angabe den
Export erreicht, obwohl sie es nicht sollte, oder ein Weg, wie Daten
entgegen der Zusicherung gespeichert werden — gehört nicht in ein
öffentliches Issue, sondern in eine private Meldung nach
[SECURITY.md](SECURITY.md). Eine Erkennungsschwäche (ein übersehener
Name) ist dagegen ein normaler, öffentlicher Bugreport — beides ist in
`SECURITY.md` gegeneinander abgegrenzt.

## Bevor eine neue Erkennungsregel entsteht

**Muster oder Wortliste?** Diese Frage steht ausführlich im
Modul-Docstring von [`app/detect.py`](app/detect.py) — dort lesen, bevor
eine Änderung beginnt. Kurz zusammengefasst:

Folgt ein Fehlalarm oder ein übersehener Fall einer *Regelmässigkeit*
(einer Endung, einer Umgebung, einer Position im Satz), gehört die Lösung
in eine der bestehenden Mustergruppen — ein Eintrag deckt dann viele
künftige Fälle ab. Ist er dagegen ein *Einzelfall aus einer kleinen,
tatsächlich begrenzten Menge* (eine deutsche Fachrichtung, ein
Formularfeld-Name), ist eine Wortliste die ehrliche, richtige Lösung.

Die Probe: Könnte in den nächsten fünf Jahren ein komplett neues Wort aus
dieser Kategorie auftauchen, das mit den bisherigen nichts zu tun hat
(ein neues Medikament, ein neuer Nachname)? Dann ist es eine unbegrenzte
Menge — ein Muster suchen, kein Wort eintragen.

## Bevor ein Vorschlag zum wiederholten Mal kommt

`BACKLOG.md`, Abschnitt „Bewusst nicht vorgesehen", listet Punkte, die
bereits geprüft und mit Begründung abgelehnt wurden — etwa eine
Cloud-Anbindung oder automatischer Export ohne Prüfschritt. Dort zuerst
nachsehen, bevor ein bereits verhandelter Punkt neu aufgemacht wird. Wer
anderer Meinung ist als die dort stehende Begründung, ist eingeladen, das
im entsprechenden Issue zu benennen — die Begründung gilt, bis sich die
zugrunde liegende Voraussetzung ändert, nicht bis jemand widerspricht.

## Lokal einrichten

Ausführlich in [README.md](README.md#einrichtung) und
[README.md](README.md#lokal-entwickeln) beschrieben. Kurzfassung:

```bash
./einrichten.sh
./start.sh
```

`einrichten.sh` installiert in zwei angekündigten Schritten — zuerst das
kleine Grundgerüst, dann das 542 MB grosse Sprachmodell — statt beides
still in einem `pip install -r requirements.txt` verschwinden zu lassen.

## Vor jedem Pull Request

Alle zehn Testdateien müssen ohne Fehler durchlaufen:

```bash
for t in tests/test_*.py; do
  echo "=== $t ==="
  .venv/bin/python "$t" || exit 1
done
```

`test_erkennung.py` und `test_stufen.py` geben keinen Fehlercode zurück,
sondern zeigen einen erfundenen Arztbrief in allen Varianten — die
gehören nach jeder Änderung an den Erkennungsregeln oder der Stufenmatrix
**gelesen**, nicht nur ausgeführt. Ein Zähler, der stimmt, sagt nichts
darüber, ob der Text noch seinen Zweck erfüllt.

Dazu:

```bash
.venv/bin/ruff check .
```

**Eine neue Erkennungsregel ohne einen neuen Testfall in
`tests/test_fehlalarme.py` ist unvollständig.** Das gilt in beide
Richtungen: ein Testfall für das, was jetzt korrekt gefunden wird, *und*
eine Gegenprobe für das, was weiterhin nicht fälschlich gefunden werden
darf. Die Datei ist voller Beispiele für dieses Muster — eine neue
Sektion im selben Stil anhängen.

## Lizenz

Beiträge fallen unter die Apache License 2.0 dieses Projekts (siehe
[LICENSE](LICENSE)).
