# Änderungen

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
