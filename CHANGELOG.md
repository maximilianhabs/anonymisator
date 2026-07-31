# Änderungen

## 0.4.0 — 2026-07-31

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
