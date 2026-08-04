# Sicherheitsrichtlinie

## Was als Sicherheitslücke gilt

Dieses Werkzeug verarbeitet medizinische Dokumente. Als Sicherheitslücke
gilt insbesondere:

- ein Weg, wie eine als geschützt geltende Angabe (Name, Adresse,
  Geburtsdatum, Kennnummer …) unbemerkt den Export erreicht, obwohl die
  gewählte Stufe sie ersetzen sollte
- ein Weg, wie ein Dokument oder Bruchstücke davon entgegen der
  Zusicherung auf der Platte, im Protokoll oder über eine ausgehende
  Verbindung landen
- eine Lücke in der Content-Security-Policy oder den übrigen
  Sicherheitskopfzeilen, die eingeschleusten Code ausführbar machte
- eine Schwachstelle in einer der eingebundenen Bibliotheken, die über den
  Anonymisator erreichbar ist

Eine **verbesserungswürdige Erkennung** — ein Name, der nicht erkannt
wird, ein Fachbegriff, der fälschlich markiert wird — ist ein
Qualitätsmangel, kein Sicherheitsproblem. Dafür bitte ein normales
[Issue](https://github.com/maximilianhabs/anonymisator/issues) eröffnen,
mit einem frei erfundenen Beispiel (siehe unten).

## Wie melden

Über die private Sicherheitsmeldung von GitHub:
[Security Advisory eröffnen](https://github.com/maximilianhabs/anonymisator/security/advisories/new).
Damit bleibt die Meldung unsichtbar, bis eine Korrektur vorliegt.

Ist dieser Weg nicht erreichbar, ersatzweise über das GitHub-Profil
[@maximilianhabs](https://github.com/maximilianhabs) Kontakt aufnehmen.

**Bitte niemals echte Dokumente, Textausschnitte oder Bildschirmfotos mit
Personenbezug einer Meldung beifügen** — auch nicht, um einen Fund zu
belegen. Ein nachgebautes Beispiel mit erfundenen Daten genügt, um jeden
bisher bekannten Fehler zu zeigen.

## Was zu erwarten ist

Eine Rückmeldung, ob die Meldung angenommen wird, innerhalb einer Woche.
Eine feste Frist für die Behebung kann nicht zugesagt werden — dies ist
ein einzeln betreutes Projekt ohne Sicherheitsteam.

## Umfang

Geprüft und behoben werden Lücken im eigenen Quelltext dieses
Repositories. Für Schwachstellen in einer eingebundenen Bibliothek
(spaCy, PyMuPDF, FastAPI, Tesseract …) bitte zusätzlich das jeweilige
Projekt benachrichtigen — hier hilft in der Regel eine aktualisierte
Version in `requirements.txt`.
