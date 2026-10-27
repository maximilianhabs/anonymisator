"""Misst Fehlalarme in Befundtext, der keine schützenswerte Angabe enthält.

Die übrigen Testdateien prüfen, was gefunden **wird**. Diese prüft, was nicht
gefunden werden darf. Beides ist nötig: eine Erkennung, die alles markiert,
besteht jeden Recall-Test und ist im Alltag trotzdem unbrauchbar, weil im
Rauschen die echten Treffer untergehen.

Alle Texte sind frei erfunden und enthalten weder Namen noch Orte noch
Einrichtungen. Jeder Treffer ist damit ein Fehlalarm.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def ohne_treffer(text: str, was: str) -> None:
    """Prüft, dass in diesem Text nichts Schützenswertes gefunden wird.

    Die Kategorie ZAHL bleibt dabei aussen vor. Sie erfasst absichtlich jede
    Zahl ohne physikalische Einheit — „85 Punkte", „Grad 2" — und wirkt
    ausschliesslich in der strengen Stufe. Dort ist genau das gewollt: eine
    Zahl ohne Einheit kann eine Durchwahl, ein Zimmer oder eine Kennung
    sein. In den beiden anderen Stufen bleibt sie unangetastet, ist hier
    also kein Fehlalarm.
    """
    gruppen = [g for g in detect.analysiere(text) if g.typ != "ZAHL"]
    treffer = [f"{g.anzeige} ({g.typ})" for g in gruppen]
    pruefe(not treffer, f"{was}{f' — gefunden: {treffer}' if treffer else ''}")


print("\n=== 1. Anamnese und Verlauf ===")
ohne_treffer(
    "Weiterhin berichtete der Patient über episodisch auftretende, vorwiegend "
    "kälteinduzierte schmerzhafte Missempfindungen im Bereich der Zehen und "
    "Vorfüße beidseits mit begleitenden Schwellungen, lividen Verfärbungen "
    "sowie zeitweiligen Hautveränderungen. Die Beschwerden traten insbesondere "
    "während der kalten Jahreszeit auf und wurden durch Kälteexposition sowie "
    "mechanische Belastung provoziert. Neu aufgetretene Paresen, Gangstörungen "
    "oder vegetative Beschwerden wurden verneint.",
    "Anamnesetext ohne Fehlalarm")

print("\n=== 2. Neurologischer Befund ===")
ohne_treffer(
    "Klinisch-neurologisch zeigte sich ein distal betontes, symmetrisches "
    "sensomotorisches polyneuropathisches Syndrom ohne Nachweis relevanter "
    "motorischer Defizite mit leichter Hohlfußstellung beidseits. Aufgrund der "
    "ungeklärten Ätiologie der Polyneuropathie sowie der unklaren Genese der "
    "kälteinduzierten Akrosymptomatik erfolgte die weiterführende Diagnostik.",
    "Befundtext ohne Fehlalarm")

print("\n=== 3. Anatomie, deutsch und lateinisch ===")
ohne_treffer(
    "Die Nervenleitgeschwindigkeit des Nervus peroneus communis war beidseits "
    "vermindert. Der Nervus suralis zeigte keine reproduzierbaren sensiblen "
    "Nervenaktionspotentiale. Das Elektromyogramm des Musculus tibialis "
    "anterior zeigte Denervierungszeichen. Die Duplexsonographie der "
    "Extremitätenarterien und der Arteria carotis interna war unauffällig.",
    "Anatomische Bezeichnungen sind keine Orte")

print("\n=== 3b. Anatomie in der Kurzform des Befunds ===")
ohne_treffer(
    "Z.n. Dekompression bei Kompression des N. medianus. Der N. tibialis "
    "posterior war seitengleich, der M. extensor digitorum brevis atroph. "
    "Die A. carotis interna und die V. jugularis waren frei. St. p. "
    "Implantation. Lig. collaterale mediale intakt.",
    "Abgekürzte Gattungswörter sind keine Orte")

print("\n=== 3c. Komposita mit medizinischem Baustein ===")
ohne_treffer(
    "Das Differentialblutbild war unauffällig. Der Hirnnervenstatus zeigte "
    "keine Auffälligkeiten. Patient wach und bewusstseinsklar. Kein Hinweis "
    "auf einen Atemwegsinfekt. Gesamteiweiß im Normbereich. Der Nodulus "
    "war grössenkonstant. Die Sensibilitätsprüfung war regelrecht.",
    "Lange Fachkomposita sind keine Personen")

print("\n=== 3d0. Weitere Komposita, Adjektive, Wirkstoffe, Segmente ===")
ohne_treffer(
    "Multisegmentale degenerative Veränderungen. Rechtskonvexer "
    "Gelenkschwung lumbosakral. Granulomatöser Prozess nachgewiesen. "
    "Finger-Nase beidseits sicher. Der Kassensitz wurde übernommen. Das "
    "Laborbudget ist ausgeschöpft. Lageempfinden ungestört. "
    "Schilddrüsenparameter im Normbereich. Perniones an beiden Zehen. "
    "Medikation: Ezetimib 10 mg, Atorvastatin, Ramipril täglich. "
    "Bandscheibenvorfall L5/S1 mit Wurzelkompression S1. Osteochondrose "
    "HWK7 und Th12.",
    "Adjektive, Komposita, Wirkstoffe und Wirbelsegmente sind keine Namen")

print("\n=== 3e. Gegenprobe: Nachnamen, die den neuen Filtern ähneln ===")
# Genau die Wörter, auf denen die Filter oben aufbauen, kommen als
# Nachname vor. Ohne Anrede waeren sie unter der Laengenschranke frei --
# mit Anrede muss der Regex-Anker durchgreifen, unabhaengig vom Filter.
NAMENSRISIKO = [
    ("Herr Kraft wurde aufgenommen.", "Kraft"),
    ("Frau Nase stellte sich vor.", "Nase"),
    ("Wir danken Herrn Dr. Ohr.", "Ohr"),
    ("Herr Wert berichtete über Schwindel.", "Wert"),
    ("Frau Menge wurde entlassen.", "Menge"),
    ("Herr Berg stellte sich vor.", "Berg"),
    ("Frau Habib wurde untersucht.", "Habib"),
    ("Herr Jones berichtete über Schmerzen.", "Jones"),
]
for text, muss in NAMENSRISIKO:
    gefunden = [f.text for g in detect.analysiere(text) for f in g.funde]
    pruefe(any(muss in t for t in gefunden),
           f"{muss!r} bleibt trotz Aehnlichkeit zum Fachbegriff erkannt"
           f"{'' if any(muss in t for t in gefunden) else f' — {gefunden}'}")

print("\n=== 3d. Fachsprache in Versalien ===")
ohne_treffer(
    "Der Patient war WACH und ORIENTIERT. Die Herzinsuffizienz zeigte sich "
    "KOMPENSIERT. Der Verlauf wurde fortlaufend DOKUMENTIERT.",
    "Partizipien in Grossschreibung sind keine Firmennamen")

print("\n=== 3f. Briefkopf-Bezeichner vor Kontaktdaten ===")
# "Kontakt" fehlte in der Stoppliste und wurde zur Rolle PATIENT, weil
# "geboren" — der nächstgelegene Rollenmarker — zufällig in Reichweite lag.
# Der Bezeichner selbst trägt keine Angabe; das Beispiel enthält bewusst
# legitime Treffer (Name, Geburtsdatum, Adresse, E-Mail, Telefon), darum
# reicht "ohne_treffer" hier nicht — geprüft wird gezielt, dass der
# Bezeichner selbst nirgends als eigene Fundstelle auftaucht.
_bezeichner_text = (
    "Herr Peter Beispiel, geboren am 03.11.1958, wohnhaft in 12345 "
    "Musterstadt. Kontakt: p.beispiel@musterklinikum.de. Tel: 05551 123456.")
_bezeichner_treffer = [
    f.text for g in detect.analysiere(_bezeichner_text) for f in g.funde
    if f.text.strip(": ") in ("Kontakt", "Tel")]
pruefe(not _bezeichner_treffer,
       f"Kontakt und Tel sind keine eigenen Fundstellen"
       f"{f' — gefunden: {_bezeichner_treffer}' if _bezeichner_treffer else ''}")

_ansprech_treffer = [
    f.text for g in detect.analysiere("Ansprechpartnerin: Frau Dr. Sailer.")
    for f in g.funde if f.text.strip(": ") == "Ansprechpartnerin"]
pruefe(not _ansprech_treffer,
       f"Ansprechpartnerin ist kein eigener Name"
       f"{f' — gefunden: {_ansprech_treffer}' if _ansprech_treffer else ''}")

print("\n=== 4. Eponyme: Zeichen, Tests und Skalen ===")
ohne_treffer(
    "Der Babinski-Reflex war negativ, das Lasegue-Zeichen beidseits "
    "unauffällig. Im Romberg-Stehversuch bestand eine Fallneigung. Der "
    "Barthel-Index betrug 85 Punkte, die Rankin-Skala 2. Im Schellong-Test "
    "kein Hinweis auf orthostatische Dysregulation. Der Phalen-Test war "
    "positiv, das Hoffmann-Tinel-Zeichen ebenfalls. Die McDonald-Kriterien "
    "waren nicht erfüllt. Einteilung nach Hunt-Hess-Klassifikation Grad 2.",
    "Eponyme sind keine Personen")

print("\n=== 5. Laborwerte und Abkürzungen ===")
ohne_treffer(
    "Laborchemisch ergaben sich unauffällige Werte für Vitamin B12, Folsäure, "
    "TSH und HbA1c. Die Immunfixation im Serum war unauffällig. "
    "Anti-MAG-Antikörper waren negativ. Eine Vaskulitis-Serologie "
    "einschließlich ANA, ANCA und Rheumafaktor blieb ohne pathologischen "
    "Befund. CRP und BSG im Normbereich, CK leicht erhöht.",
    "Fachabkürzungen sind keine Einrichtungen")

print("\n=== 6. Über den Absatz hinweg ===")
ohne_treffer(
    "Der Barthel-Index betrug 85, die Rankin-Skala 2.\n\n"
    "Laborchemisch unauffällige Werte für Vitamin B12 und TSH.",
    "Kein Treffer greift über einen Absatzumbruch")

print("\n=== 7. Gegenprobe: echte Angaben bleiben erhalten ===")
ECHTE = [
    ("Frau Elisabeth Hartmann stellte sich vor.", "Hartmann"),
    ("Wir danken Herrn Dr. med. Konrad Weißbach.", "Weißbach"),
    ("Sehr geehrte Frau Kollegin Brandner,", "Brandner"),
    ("Die Patientin wohnt in Deggendorf.", "Deggendorf"),
    ("Verlegung in die Neurologische Klinik am Auwald.", "Auwald"),
    # Nachname, der auf eine medizinische Endung passt
    ("Der Ehemann, Herr Gerhard Rose, war anwesend.", "Rose"),
    # Nachnamen, die auch als Eponym vorkommen
    ("Wir danken Herrn Dr. Schellong für die Zuweisung.", "Schellong"),
    ("Frau Romberg wurde stationär aufgenommen.", "Romberg"),
    # Titel in Grossschreibung
    ("PROF. DR. MED. K. WEISSBACH", "WEISSBACH"),
    ("Dipl.-Psych. Anna Sailer", "Sailer"),
    # Krankenkasse als Abkürzung
    ("Die AOK Bayern übernimmt die Kosten.", "AOK"),
    # Nachnamen, die einen medizinischen Baustein tragen. Sie bleiben unter
    # der Mindestlänge und dürfen deshalb nicht der Kompositaregel zum
    # Opfer fallen.
    ("Herr Herzog wurde aufgenommen.", "Herzog"),
    ("Frau Bluthardt stellte sich vor.", "Bluthardt"),
    ("Wir danken Herrn Dr. Ohrmann.", "Ohrmann"),
]
for text, muss in ECHTE:
    gruppen = detect.analysiere(text)
    gefunden = [f.text for g in gruppen for f in g.funde]
    pruefe(any(muss in t for t in gefunden),
           f"{muss!r} wird weiterhin erkannt{'' if any(muss in t for t in gefunden) else f' — {gefunden}'}")

print("\n=== 7a. Briefköpfe in Versalien ===")
# Der Absender steht oft durchgehend gross. Das Sprachmodell erkennt ihn
# dort unzuverlässig — in der Unterschriftszeile hatte es "BEZIRKSKLINIKUM
# MAINKOFEN" gar nicht getaggt. Ein Briefkopf ohne erkannte Einrichtung ist
# der Fehler, der am meisten kostet, deshalb steht er hier fest.
VERSAL = [
    ("Mit freundlichen Grüßen\n\nBEZIRKSKLINIKUM MAINKOFEN\n"
     "Prof. Dr. med. Weissbach", "BEZIRKSKLINIKUM MAINKOFEN"),
    ("UNIVERSITÄTSKLINIKUM REGENSBURG", "UNIVERSITÄTSKLINIKUM REGENSBURG"),
    ("Die Aufnahme erfolgte im KLINIKUM PASSAU am 3. Mai.", "KLINIKUM PASSAU"),
    ("SANKT-JOSEF-KRANKENHAUS", "SANKT-JOSEF-KRANKENHAUS"),
    ("NEUROZENTRUM MAINKOFEN", "NEUROZENTRUM MAINKOFEN"),
]
for text, muss in VERSAL:
    treffer = [g.anzeige for g in detect.analysiere(text)
               if g.typ == "ORGANISATION"]
    pruefe(muss in treffer,
           f"{muss!r} wird als Einrichtung erkannt"
           f"{'' if muss in treffer else f' — gefunden: {treffer}'}")

print("\n=== 7c. E-Mail-Adressen, am @ verankert ===")
# In Briefköpfen bricht die Adresse am Spaltenrand um. Eine Regel, die
# Zusammenhang verlangt, sieht dort nichts -- und übrig bleibt der Klarname
# im Ortsteil, also genau das, was geschützt werden soll.
EMAILS = [
    ("Kontakt:\nt.schmidt-wilcke\n@mainkofen.de", "umbrochen vor dem @"),
    ("Kontakt: t.schmidt-wilcke@\nmainkofen.de", "umbrochen nach dem @"),
    ("Kontakt: t.schmidt-wilcke @mainkofen.de", "Leerzeichen vor dem @"),
    ("Rückfragen an ingrid.brandner@klinik.de", "zusammenhängend"),
]
for text, was in EMAILS:
    typen = [g.typ for g in detect.analysiere(text)]
    pruefe("EMAIL" in typen, f"E-Mail erkannt, {was}")

# Ein Absatzumbruch trennt zwei Angaben und darf nicht überbrückt werden.
pruefe("EMAIL" not in [g.typ for g in detect.analysiere(
           "Sehr geehrte Frau Kollegin\n\n@mainkofen.de")],
       "Das Muster greift nicht über einen Absatz")

# Überlappende Bereiche schieben beim Ersetzen einen Platzhalter in den
# anderen. Der Nachname aus dem Ortsteil steckt regelmässig in einem
# bereits erkannten vollen Namen.
_t = ("Prof. Dr. med. T. Schmidt-Wilcke\nKontakt:\n"
      "t.schmidt-wilcke\n@mainkofen.de")
_spannen = sorted((f.start, f.end) for g in detect.analysiere(_t)
                  for f in g.funde)
pruefe(all(_spannen[i][1] <= _spannen[i + 1][0]
           for i in range(len(_spannen) - 1)),
       f"Keine überlappenden Fundstellen — {_spannen}")

print("\n=== 7b. Der Beleg gilt für das ganze Dokument ===")
# Die Gegenrichtung zu allem darüber: hier ist ein Treffer erwünscht, auch
# wenn das Wort für sich genommen harmlos aussieht. Wer einmal mit Anrede
# eingeführt wurde, ist im ganzen Dokument dieselbe Person.
KONSISTENZ = [
    ("Herr Peter Tisch stellte sich vor. Später berichtete Tisch über "
     "Schmerzen.", "Tisch", 2),
    ("Frau Anna Sommer wurde aufgenommen. Sommer klagte über Schwindel.",
     "Sommer", 2),
    ("Aufnahme im Bezirksklinikum Stuttgart. Verlegung nach Stuttgart.",
     "Stuttgart", 2),
]
for text, teil, mindestens in KONSISTENZ:
    treffer = sum(
        1 for g in detect.analysiere(text) for f in g.funde if teil in f.text)
    pruefe(treffer >= mindestens,
           f"{teil!r} wird an allen {mindestens} Stellen erfasst "
           f"(gefunden: {treffer})")

print("\n=== 7d. Zwei Personen, derselbe Nachname, nur per E-Mail bekannt ===")
# Fand sich beim Testen mit einem ~50-seitigen Dokument: teilen sich zwei
# Personen einen Nachnamen und sind beide nur über die E-Mail-Adresse
# eingeführt (keine Anrede, kein Titel), stürzte die Analyse mit einem
# KeyError ab. Der Grund: die Menge der bekannten Namen ("vorhanden") wuchs
# bei jeder neuen Gruppe mit, das Nachschlagewörterbuch ("nach_schluessel")
# aber nicht -- die zweite Person mit demselben Nachnamen traf auf einen
# Eintrag, der laut Menge existiert, im Wörterbuch aber fehlte. Wer den
# Nachnamen als Erster bekommt, ist eine bekannte, hingenommene Grenze
# (siehe BACKLOG.md); hier zaehlt nur, dass die Analyse nicht abstuerzt.
try:
    ergebnis = detect.analysiere(
        "Rückfragen bitte an e.beispiel@musterklinikum.de oder "
        "k.beispiel@musterklinikum.de richten. Beispiel war zuständig.")
    pruefe(True, "Zwei E-Mail-Namen mit gleichem Nachnamen stürzen nicht ab")
except KeyError as exc:
    pruefe(False, f"Absturz mit KeyError: {exc}")

print("\n=== 8. Belegte und unbelegte Treffer ===")
belegt = detect.analysiere("Wir danken Frau Dr. Ostermeier für die Zuweisung.")
pruefe(belegt and all(g.sicher for g in belegt if g.typ == "ARZT"),
       "Treffer mit Anrede und Titel gilt als belegt")

unbelegt = detect.analysiere(
    "Die Untersuchung fand in Regensburg statt und wurde dort ausgewertet.")
orte = [g for g in unbelegt if g.typ == "ORT"]
pruefe(orte and not orte[0].sicher,
       "Ortsname ohne Kontextmarker gilt als unbelegt")

print("\n=== 9. Getrennt geschriebene Strassennamen ===")
# "Königsberger Straße 1" — beim Testen mit echten Dokumenten aufgefallen.
# Die alte Regel verlangte, dass Strassensuffix und Name als ein Wort
# zusammenklebten ("Ludwigstraße"); getrennt geschriebene Formen sind im
# Deutschen mindestens so häufig und liessen zuvor die Hausnummer komplett
# unbeachtet.
STRASSEN = [
    ("Königsberger Straße 1", "Königsberger Straße 1"),
    ("Berliner Str. 5", "Berliner Str. 5"),
    ("Am Alten Weg 3", "Am Alten Weg 3"),
]
for text, muss_ganz in STRASSEN:
    gruppen = detect.analysiere(text)
    adressen = [g.anzeige for g in gruppen if g.typ == "ADRESSE"]
    pruefe(muss_ganz in adressen,
           f"{muss_ganz!r} vollständig als Adresse erfasst, samt Hausnummer "
           f"(gefunden: {adressen})")

# Gegenprobe: das Auslösewort allein, ohne folgende Hausnummer, darf nicht
# reichen — sonst würde jeder Nachname "Berg" oder "Weg" anschlagen.
for text in ["Herr Berg wurde untersucht.", "Frau Weg stellte sich vor.",
             "Gesichtsfeld eingeschränkt."]:
    treffer = [g.anzeige for g in detect.analysiere(text) if g.typ == "ADRESSE"]
    pruefe(not treffer, f"{text!r} bleibt ohne Adress-Fehlalarm ({treffer})")

print("\n=== 10. Geschlecht — nur mit Beleg, auch dekliniert ===")
GESCHLECHT_FAELLE = [
    ("Geschlecht: männlich", "männlich"),
    ("Geschlecht: w", "w"),
    ("Die Patientin ist weiblich.", "weiblich"),
    ("45-jähriger männlicher Patient", "männlicher"),
    ("ein weibliches Kind", "weibliches"),
]
for text, muss in GESCHLECHT_FAELLE:
    treffer = [g.anzeige for g in detect.analysiere(text) if g.typ == "GESCHLECHT"]
    pruefe(muss in treffer, f"{muss!r} als Geschlecht erfasst (gefunden: {treffer})")

# Die einbuchstabige Form darf nur mit dem Auslösewort "Geschlecht"/"Sex"
# greifen — sonst träfe sie jedes einzelne "m" oder "w" im Fliesstext.
for text in ["m Punkt Meier", "w wie Woche", "Der Wert war m."]:
    treffer = [g.anzeige for g in detect.analysiere(text) if g.typ == "GESCHLECHT"]
    pruefe(not treffer, f"{text!r} bleibt ohne Geschlecht-Fehlalarm ({treffer})")

print("\n=== 11. Diagnosecodes — nur der Code, an ein Auslösewort gebunden ===")
DIAGNOSE_FAELLE = [
    ("Diagnose: F32.1 Depressive Episode", "F32.1"),
    ("ICD-10: I63.9", "I63.9"),
    ("ICD-10-GM: E11.90", "E11.90"),
    ("OPS: 5-470.0", "5-470.0"),
    ("DRG: F62B", "F62B"),
    ("Hauptdiagnose: C34.90", "C34.90"),
]
for text, muss in DIAGNOSE_FAELLE:
    treffer = [g.anzeige for g in detect.analysiere(text) if g.typ == "DIAGNOSECODE"]
    pruefe(muss in treffer, f"{muss!r} als Diagnosecode erfasst (gefunden: {treffer})")

# Ein freistehendes "[A-Z]\d{2}"-Muster ohne Auslösewort träfe auch
# "Vitamin B12" — deshalb ausschliesslich an ICD/OPS/DRG/Diagnose gebunden.
for text in ["Vitamin B12 im Normbereich.",
             "Diagnose: Depression, kein Code notiert.",
             "Laborwert D3 erniedrigt."]:
    treffer = [g.anzeige for g in detect.analysiere(text) if g.typ == "DIAGNOSECODE"]
    pruefe(not treffer, f"{text!r} bleibt ohne Diagnosecode-Fehlalarm ({treffer})")

print("\n=== 12. 'geb.' leitet auch einen Geburtsnamen ein, nicht nur ein Datum ===")
# "Frau Müller, geb. Schuster" -- bisher unabgedeckt, weil die einzige
# Regel über "geb." zwingend ein Datum verlangte. Geburtsname und
# Geburtsdatum schliessen sich an derselben Stelle gegenseitig aus.
for text, muss in [
    ("Herr Müller, geb. Schuster, wurde aufgenommen.", "Schuster"),
    ("Die Patientin, geb. Schuster, wohnhaft in Musterstadt.", "Schuster"),
]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde]
    pruefe(muss in treffer, f"{muss!r} als Geburtsname erfasst (gefunden: {treffer})")

# Ein echtes Geburtsdatum an derselben Stelle darf weiterhin als Datum
# gelten, nicht als vermeintlicher Name.
datum = detect.analysiere("Geburtsdatum: 22.07.1958")
pruefe(any(g.typ == "GEBURTSDATUM" for g in datum),
       "'geb.'-Familie erkennt weiterhin echte Geburtsdaten")

print("\n=== 13. Medikamentennamen mit Dosierung sind keine Person ===")
# "Ebrantil 25 mg" -- Markennamen sind für das Sprachmodell namensförmig,
# oft sogar als Behandler eingestuft. Eine Liste aller Markennamen wäre
# unbegrenzt; die direkt folgende Dosierung ist ein verlässliches
# strukturelles Merkmal.
for text in ["Ebrantil 25 mg i.v. verabreicht.", "Novalgin 500 mg gegeben.",
             "Unter Ebrantil 25mg Blutdrucksenkung erreicht."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde
               if g.typ in ("PERSON", "ARZT", "PATIENT")]
    pruefe(not treffer, f"{text!r} bleibt ohne Medikamenten-Fehlalarm ({treffer})")

# Ohne Dosierung bleibt die Heuristik naturgemäss wirkungslos -- das ist
# hier keine Prüfung, sondern nur die Abgrenzung dokumentiert.

# Ein echter Name mit einer Altersangabe daneben darf nicht verschwinden:
# "Jahre" steht nicht auf der Einheitenliste, die Heuristik darf hier
# nicht greifen.
alter = detect.analysiere("Herr Weissbach, 25 Jahre alt, wurde aufgenommen.")
pruefe(any("Weissbach" in f.text for g in alter for f in g.funde),
       "Ein echter Name bleibt trotz folgender Altersangabe erkannt")

print("\n=== 14. Feldbezeichner und Symptome, beiläufig beim Testen gefunden ===")
# "Aufnahmegrund" (das Wort selbst) als Person, "Schwindel" als Ort --
# unabhängig von den oben gemeldeten Fällen aufgefallen.
for text in ["Aufnahmegrund: Sturz.", "Diagnosegrund: Schwindel.",
             "Sie berichtet über Schwindel und Übelkeit."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

# Ein echter Nachname, der zufällig gleich "Grund" lautet, muss mit Anrede
# weiterhin erkannt werden -- die neuen Stoppwörter sind Komposita
# ("Aufnahmegrund"), kein allgemeiner Filter auf "Grund".
grund = detect.analysiere("Herr Grund wurde aufgenommen.")
pruefe(any("Grund" in f.text for g in grund for f in g.funde),
       "Der Nachname 'Grund' bleibt mit Anrede weiterhin erkannt")

print("\n=== 15. Weitere Medikamente und ein Trauma-Fachbegriff ===")
# Ethosuximid (Succinimid) und Levetiracetam-Familie (Racetam) kamen als
# Person bzw. Behandler an -- INN-Wirkstoffstamm ergaenzt, analog zu den
# bereits abgedeckten Stämmen. "Sturztraumata" (Kompositum, Pluralform von
# Trauma) als eigenständiger Fund.
for text in ["Ethosuximid wurde angesetzt.", "Unter Ethosuximid gute Anfallskontrolle.",
             "Zustand nach Sturztraumata im Kindesalter."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

print("\n=== 16. Postleitzahl mit Ort in Versalien ===")
# "94469 DEGGENDORF" -- die PLZ+Ort-Regel verlangte bisher
# Binnenkleinschreibung und uebersah Briefkoepfe in Versalien, obwohl
# derselbe Ortsname ohne PLZ meist noch vom Sprachmodell gefangen wurde.
for text, muss in [("94469 DEGGENDORF", "94469 DEGGENDORF"),
                    ("94469 Deggendorf", "94469 Deggendorf")]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde
               if g.typ == "ADRESSE"]
    pruefe(muss in treffer, f"{muss!r} als Adresse erfasst (gefunden: {treffer})")

print("\n=== 17. Modalitäten, gleich wie geschrieben ===")
# EEG/MRT/CT u. a. waren als einzelnes Wort schon Stoppwort, nicht aber als
# Mehrzahl ("EEGs"), Kompositum ("Verlaufslabor", "Chefarztvisite") oder
# mit Bindestrich-Zusatz ("EEG-Kontrollen"). "CT Hals/Thorax" scheiterte
# am Schrägstrich, der bisher kein Worttrenner war.
for text in ["Die EEGs zeigten unauffällige Befunde.",
             "cMRT ohne pathologischen Befund.",
             "EEG-Kontrollen wurden durchgeführt.",
             "Verlaufslabor unauffällig.",
             "Procedere: CT Hals/Thorax, Verlaufslabor.",
             "MRTs im Verlauf unauffällig.",
             "Chefarztvisite am Montag."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

# Gegenprobe: ein echter Name bleibt erkannt, auch wenn er zufällig auf
# ein Wort aus der neuen Mehrzahl-/Schrägstrich-Logik trifft.
kraft = detect.analysiere("Herr Kraft wurde untersucht.")
pruefe(any("Kraft" in f.text for g in kraft for f in g.funde),
       "Ein echter Nachname bleibt trotz der neuen Regeln erkannt")

print("\n=== 18. Namenspartikel \"van der\"/\"van den\" in Arztnamen ===")
# "Dr. med. Petra van der Berg-Ostermann" wurde bisher nur bis zum
# Vornamen erkannt ("Petra") -- die Namenskette riss an "van" ab, weil
# das Muster nur grossgeschriebene Namensteile verkettete. Gefunden beim
# Bau des Goldkorpus (tests/goldkorpus/doppelname_praefix.txt).
brief = ("Mit freundlichen Grüßen\n\nDr. med. Petra van der Berg-Ostermann\n"
         "Fachärztin für Neurologie")
arzt = [f.text for g in detect.analysiere(brief) for f in g.funde if g.typ == "ARZT"]
pruefe("Petra van der Berg-Ostermann" in arzt,
       f"Arztname mit 'van der' vollständig erfasst (gefunden: {arzt})")

brief2 = "Dr. med. Habib van den Berg berichtet."
arzt2 = [f.text for g in detect.analysiere(brief2) for f in g.funde if g.typ == "ARZT"]
pruefe("Habib van den Berg" in arzt2,
       f"Arztname mit 'van den' vollständig erfasst (gefunden: {arzt2})")

# Gegenprobe: "von der"/"von"/"der" bleiben bewusst KEINE freistehenden
# Partikel -- das sind die häufigsten Wörter der deutschen Sprache und
# stehen in Arztbriefen ständig vor einer Einrichtung, nicht vor einem
# weiteren Namensteil. Ohne diese Schranke würde "Dr. Schmidt von der
# Uniklinik Regensburg" die Klinik in den Arztnamen hineinziehen.
for text, darf_nicht_enthalten in [
    ("Dr. Schmidt von der Uniklinik Regensburg überwiesen.", "Uniklinik"),
    ("Dr. med. Habib von der Nachfolgerin übernommen.", "Nachfolgerin"),
    ("Prof. Dr. med. Weißbach vom Klinikum Deggendorf überwiesen.", "Klinikum"),
]:
    arzt3 = [f.text for g in detect.analysiere(text) for f in g.funde if g.typ == "ARZT"]
    pruefe(not any(darf_nicht_enthalten in a for a in arzt3),
           f"{text!r} -- Einrichtung bleibt ausserhalb des Arztnamens (gefunden: {arzt3})")

print("\n=== 19. Verwandtschaftswörter, auch im Genitiv ===")
# "dem Vater des Patienten" kam unbelegt als Person an -- die NER-
# Stoppliste hatte Verwandtschaftswörter nie, nur die Regex-Schicht kannte
# sie ueber _KEIN_NAME. Gefunden im Goldkorpus (fremdbefund_zitat.txt).
for text in ["Anamnestisch berichtet die Mutter des Patienten.",
             "Laut Angaben des Vaters bestand die Symptomatik bereits Wochen.",
             "Die Schwester begleitete die Patientin zur Aufnahme.",
             "Der Ehemann war während der gesamten Behandlung anwesend."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

print("\n=== 20. PLZ + Grosseinheiten-Kürzel wird nicht zur Adresse ===")
# "20000 IE" (Internationale Einheiten, z. B. Vitamin D3) erfuellte die
# PLZ+Ort-Regel aus 0.15.2 (Versalien) ungewollt mit -- "IE" ist zwei
# Grossbuchstaben und damit ein gueltiger, wenn auch zu kurzer Versal-
# Ortsname. Gefunden im Goldkorpus (tabelle_medikation.txt).
for text in ["Vitamin D3           20000 IE      1x/Woche",
             "Gegeben wurden 20000 IE Vitamin D3."]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde if g.typ == "ADRESSE"]
    pruefe(not treffer, f"{text!r} bleibt ohne Adress-Fehlalarm (gefunden: {treffer})")

# Gegenprobe: ein kurzer, aber echter Versal-Ortsname mit PLZ bleibt erkannt.
passau = [f.text for g in detect.analysiere("94032 PASSAU") for f in g.funde
          if g.typ == "ADRESSE"]
pruefe("94032 PASSAU" in passau,
       f"Ein echter Versal-Ortsname mit PLZ bleibt erkannt (gefunden: {passau})")

print("\n=== 21. Versal-Einrichtung ohne zusammengesetztes Präfix ===")
# _EINRICHTUNG_VERSAL verlangte bisher immer mindestens einen Buchstaben
# vor dem Kopfwort -- der frass dabei den Anfang des Kopfworts selbst auf,
# wenn keine Zusammensetzung vorlag ("KLINIK" wurde zu "K" + "LINIK",
# Letzteres passt zu keinem Muster). Nur zusammengesetzte Präfixformen wie
# "BEZIRKSKLINIKUM" funktionierten -- die häufigere, einfache Form nie.
# Gefunden im Goldkorpus (versalsatz_mehrspaltig.txt).
for text, muss in [
    ("KLINIK AM AUWALD", "KLINIK AM AUWALD"),
    ("KLINIKUM MUSTERSTADT", "KLINIKUM MUSTERSTADT"),
    ("KRANKENHAUS DEGGENDORF", "KRANKENHAUS DEGGENDORF"),
]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde
               if g.typ == "ORGANISATION"]
    pruefe(muss in treffer, f"{text!r} vollständig als Einrichtung erfasst "
           f"(gefunden: {treffer})")

# Gegenprobe: zwei durch eine grosse Lücke getrennte Spalten (kopiert aus
# einem zweispaltigen PDF-Kopf) dürfen nicht zu einem Einrichtungsnamen
# verschmelzen.
zweispaltig = [f.text for g in detect.analysiere(
    "KLINIK AM AUWALD                              ANSPRECHPARTNERIN: FRAU HUBER"
) for f in g.funde if g.typ == "ORGANISATION"]
pruefe(zweispaltig == ["KLINIK AM AUWALD"],
       f"Rechte Spalte bleibt ausserhalb des Einrichtungsnamens (gefunden: {zweispaltig})")

# Auch der zusammengeschriebene Strassenname in Versalien wird jetzt als
# Adresse erkannt, nicht mehr fälschlich als Einrichtung.
strasse = [(g.typ, f.text) for g in detect.analysiere("LUDWIGSTRASSE 47, 94032 PASSAU")
           for f in g.funde]
pruefe(("ADRESSE", "LUDWIGSTRASSE 47") in strasse,
       f"Versal-Strassenname als Adresse erfasst (gefunden: {strasse})")

print("\n=== 22. Virustyp mit angehängter Zahl, ein weiterer Wirkstoffstamm ===")
# "HSV-1" kam unbelegt als Organisation an -- _ist_abkuerzung() entfernte
# Bindestriche, aber keine Ziffern, bevor sie auf reine Buchstaben prüfte;
# die angehängte "1" liess die Prüfung scheitern. "Aciclovir" (und
# Verwandte auf -clovir) kamen unbelegt als Person an, INN-Endung fehlte.
# Gefunden im Goldkorpus (diagnose_entzuendlich.txt).
for text in ["PCR auf HSV-1 fiel positiv aus.", "HHV-6 wurde nachgewiesen.",
             "Unter Aciclovir intravenös zeigte sich Besserung.",
             "Valaciclovir wurde angesetzt."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

print("\n=== 23. Vierstellige Geldbeträge ohne Tausendertrennzeichen ===")
# "2050,75 €" (in DRG-Entgeltnachweisen ueblich, kein "2.050,75 €") verlor
# die erste Ziffer -- die alte Regel begrenzte die fuehrende Zifferngruppe
# auf hoechstens drei Stellen, der Regex-Motor rutschte deshalb eine
# Stelle weiter, bis "050,75 €" irgendwo passte. Gefunden vom Nutzer beim
# Testen eines echten DRG-Entgeltnachweises.
for text, muss in [
    ("2050,75 €", "2050,75 €"),
    ("12345,00 €", "12345,00 €"),
    ("2.050,75 €", "2.050,75 €"),  # Gegenprobe: echt gruppierte Zahl unveraendert
]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde if g.typ == "BETRAG"]
    pruefe(muss in treffer, f"{text!r} vollständig als Betrag erfasst (gefunden: {treffer})")

print("\n=== 24. 'Gültig(es/e/er/en)' als Feldkommentar ===")
# "Gültiges Geschlecht. Nicht für Grouping verwendet" -- Satzanfang in
# einem DRG-Entgeltnachweis, "Gültiges" kam unbelegt als Person an.
for text in ["Gültiges Geschlecht. Nicht für Grouping verwendet.",
             "Gültiges Alter. Nicht für Grouping verwendet.",
             "Gültige ICD-Angabe."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

print("\n=== 25. Freistehende Initialen in Unterschriftenzeilen ===")
# Mehrere Mitzeichnende unter einem Brief, von denen nur die erste Person
# den vollen Titel trägt -- die restlichen Zeilen sind reine
# "Initiale(n) + Nachname"-Muster ohne jedes Auslösewort in derselben
# Zeile. Zuvor blieben sie unerkannt: Nutzer-Fund in einem echten
# Testdatensatz (anonymisiertes Nachstellen unten), Unterschrift eines
# Chefarztes gefolgt von zwei weiteren Unterzeichnenden.
unterschriftenblock = (
    "Mit freundlichen kollegialen Grüßen\n\n"
    "Prof. Dr. med. T. S.\nM. Richter\nT. Egerter\n\n"
    "Chefarzt\nLeitender Oberarzt\nStationsärztin"
)
gefunden = {f.text for g in detect.analysiere(unterschriftenblock) for f in g.funde}
for name in ("T. S.", "M. Richter", "T. Egerter"):
    pruefe(name in gefunden,
           f"{name!r} im Unterschriftenblock erkannt (gefunden: {gefunden})")

# Gegenprobe: gängige deutsche Abkürzungen mit kleinem Anfangsbuchstaben
# sehen dem Initialen-Muster ähnlich, sind aber keine Namen.
ohne_treffer("Der Patient berichtet, z. B. beim Treppensteigen, "
             "u. a. über Schwindel, d. h. keine Synkope.",
             "gängige Abkürzungen (z. B., u. a., d. h.)")

print("\n=== 26. Rollenwörter und Artikel im Wortinneren ===")
# "Stationsärztin" kam im echten Unterschriftenblock oben als ORT an --
# "chefarzt"/"oberarzt"/"assistenzarzt" standen schon in der Stoppliste,
# "facharzt"/"stationsarzt" fehlten. Eigener Testfall, unabhängig vom
# Unterschriftenblock, damit die Lücke gezielt geprüft wird.
ohne_treffer("Stationsärztin\nStationsarzt\nFacharzt für Neurologie",
             "Rollenbezeichnungen ohne Titel bleiben unerkannt")

# "MRT DES SCHÄDELS" und "Zentrum der Läsion" kamen als Einrichtung an --
# ein radiologischer/anatomischer Begriff mit einem Artikel im
# Wortinneren. Echte Einrichtungsnamen haben diesen Aufbau zufällig auch
# ("Universität der Bundeswehr") -- die Gegenprobe muss stehen bleiben.
for text in ["Das MRT DES SCHÄDELS zeigte eine Läsion.",
             "Im Zentrum der Läsion zeigte sich eine Nekrose."]:
    treffer = [(g.typ, f.text) for g in detect.analysiere(text) for f in g.funde]
    pruefe(not treffer, f"{text!r} bleibt ohne Fehlalarm ({treffer})")

gegenprobe = [(g.typ, f.text) for g in detect.analysiere(
    "Die Universität der Bundeswehr München wurde vergleichend genannt."
) for f in g.funde]
pruefe(("ORGANISATION", "Universität der Bundeswehr München") in gegenprobe,
       f"Echte Einrichtung mit Artikel im Namen bleibt erkannt (gefunden: {gegenprobe})")

print("\n=== 27. Regel-Ergänzungen aus der Gutachtenpraxis (Issue-Feedback) ===")
# Ein Kollege hat die Regelschicht einzeln, ohne Sprachmodell, geprüft und
# sechs Sätze gefunden, die sie nicht fing. Das Sprachmodell fängt vieles
# davon im Normalbetrieb ohnehin — die Regelschicht soll es aber auch allein
# können (Absicherung, und für jeden, der ohne Modell arbeitet). Deshalb
# wird hier bewusst `_regex_funde` geprüft, nicht `analysiere`.
for text, muss in [
    ("Herrn Rechtsanwalt Jens Probst", "Jens Probst"),
    ("Sachverständigenbüro Dipl.-Ing. Cornelia Wenzel", "Cornelia Wenzel"),
    ("Kläger: Thomas Weidinger", "Thomas Weidinger"),
    ("unseren Patienten Elias Vogt, geboren am 03.03.1971", "Elias Vogt"),
    ("ANSPRECHPARTNERIN: FRAU HUBER", "HUBER"),
    ("Dr. med. IIse Brandt", "IIse Brandt"),
]:
    treffer = [f.text for f in detect._regex_funde(text)]
    pruefe(muss in treffer, f"{muss!r} schon von der Regelschicht allein erfasst "
           f"(gefunden: {treffer})")

# Name hinter der Grussformel, auch mit OCR-Schreibweise ohne Umlaute.
for text in ["Mit freundlichen Grüßen\nIlse Brandt", "Mit freundlichen Grussen\n\nIlse Brandt",
             "gez. Hans Peter Weissbach\n"]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde]
    pruefe(any("Brandt" in t or "Weissbach" in t for t in treffer),
           f"Unterzeichnende hinter {text.splitlines()[0]!r} erfasst (gefunden: {treffer})")

# Gegenproben: dieselben Muster dürfen keine Einrichtung, kein Feldwert und
# keine Krankheitsabkürzung als Person nehmen.
for text, was in [
    ("RA Faktor positiv.", "'RA' ist die rheumatoide Arthritis, kein Rechtsanwalt"),
    ("Patient: Verlauf unauffällig.", "Feldwert nach 'Patient:' ist kein Name"),
    ("SEHR GEEHRTE FRAU KOLLEGIN", "Versal-Anrede ohne Namen"),
    ("Gliederung 3.2. Befund.", "Gliederungspunkt ist kein Datum"),
]:
    treffer = [(g.typ, g.anzeige) for g in detect.analysiere(text) if g.typ != "ZAHL"]
    pruefe(not treffer, f"{was} — ohne Fehlalarm ({treffer})")

treffer = [(g.typ, g.anzeige) for g in detect.analysiere("Mit freundlichen Grüßen\nKlinikum Passau")
           if g.typ in ("PERSON", "ARZT", "PATIENT")]
pruefe(not treffer, f"Einrichtung hinter der Grussformel wird keine Person ({treffer})")

print("\n=== 28. Unvollständige Datumsangaben werden als Datum erkannt ===")
# Bis 0.24.0 blieben sie als nackte Jahreszahl oder Ziffernfolge unverschoben
# stehen — siehe tests/test_datumsverschiebung.py für die Verschiebung selbst.
for text, typ, muss in [
    ("Im März 2024 erfolgte die Aufnahme.", "DATUM", "März 2024"),
    ("MRT 03/2024 ohne Befund.", "DATUM", "03/2024"),
    ("Seit Frühjahr 2019 Beschwerden.", "DATUM", "Frühjahr 2019"),
    ("Aufenthalt vom 03.03. bis 12.03.2026.", "DATUM", "03.03"),
    ("Jahrgang 1971, Migräne.", "GEBURTSDATUM", "Jahrgang 1971"),
]:
    treffer = [f.text for g in detect.analysiere(text) for f in g.funde if g.typ == typ]
    pruefe(muss in treffer, f"{muss!r} als {typ} erfasst (gefunden: {treffer})")

# Ein volles Datum bleibt ein Fund, es zerfällt nicht in Teilangaben.
treffer = [f.text for g in detect.analysiere("Entlassung am 03.03.2024.")
           for f in g.funde if g.typ == "DATUM"]
pruefe(treffer == ["03.03.2024"], f"Volles Datum bleibt ungeteilt (gefunden: {treffer})")

print("\n=== 29. Restprüfung mit Fehlertoleranz (OCR) ===")
# "Hartrnann" (rn statt m) war als Grenze im README genannt. Die Prüfung
# vergleicht noch nicht abgedeckte, grossgeschriebene Wörter mit den
# Namensteilen erkannter Personen -- mit einer Gewichtung, die typische
# OCR-Verwechslungen billig und beliebige Ersetzungen teuer macht.
ocr_text = ("Frau Dr. Elisabeth Hartmann berichtet. Im Scan steht Hartrnann und "
            "Eiisabeth.")
ocr_gruppen = detect.analysiere(ocr_text)
ocr_funde = {f.text: f.quelle for g in ocr_gruppen for f in g.funde}
for wort in ("Hartrnann", "Eiisabeth"):
    pruefe(ocr_funde.get(wort, "").startswith("ocr-aehnlich:"),
           f"{wort!r} als mögliche Lesefehler-Variante erfasst ({ocr_funde})")
pruefe(all(not g.sicher for g in ocr_gruppen
           if any(f.quelle.startswith("ocr-aehnlich") for f in g.funde)),
       "Solche Treffer gelten nie als belegt (sie sollen im Review auffallen)")

# Gegenproben: ein beliebiges Wort mit einem Buchstaben Unterschied ist kein
# Lesefehler, und zwei verschiedene, ähnliche Personen bleiben getrennt.
gegen = detect.analysiere("Herr Peter Mayer kam. Die Mauer ist alt.")
pruefe(not any(f.text == "Mauer" for g in gegen for f in g.funde),
       "'Mauer' wird nicht zu 'Mayer' (y/u ist keine OCR-Verwechslung)")
zwei = {g.anzeige for g in detect.analysiere(
    "Herr Hans Meier und Herr Karl Meyer kamen zusammen.")}
pruefe("Hans Meier" in zwei and "Karl Meyer" in zwei,
       f"Meier und Meyer bleiben zwei Personen ({zwei})")

print("\n=== 30. Bekannte Personen: alle Schreibweisen ===")
varianten = detect.namensvarianten("Thomas", "Weidinger")
for v in ("Weidinger", "Weidinger, Thomas", "Thomas Weidinger", "T. Weidinger",
          "Weidinger, T.", "WEIDINGER", "Weidingers"):
    pruefe(v in varianten, f"Variante {v!r} wird erzeugt")
umlaut = detect.namensvarianten("Anna", "Müller")
pruefe("Mueller" in umlaut and "Anna Mueller" in umlaut,
       "Schreibweise ohne Umlaute wird miterzeugt")

gruppe = detect.bekannte_person_gruppe(
    "Weidinger, Thomas kam. T. Weidinger klagte. Thomasine Weidinger kam nicht. "
    "Die Annahme blieb.", "Thomas", "Weidinger", "", "PATIENT", "b0")
texte = [f.text for f in gruppe.funde] if gruppe else []
pruefe("Weidinger, Thomas" in texte and "T. Weidinger" in texte,
       f"Schreibweisen im Text gefunden ({texte})")
pruefe(not any(t.startswith("Thomas") and t != "Thomas" and "Weidinger" not in t
               for t in texte),
       "Ein Vorname trifft nicht den Anfang eines anderen Worts ('Thomasine')")
pruefe(gruppe is not None and gruppe.sicher and gruppe.typ == "PATIENT",
       "Eingabe des Nutzers gilt als Beleg (sicher), Rolle bleibt erhalten")
pruefe(detect.bekannte_person_gruppe("Nichts davon steht hier.", "Anna", "Meier",
                                      "", "PATIENT", "b1") is None,
       "Name, der nicht vorkommt, ergibt keine Gruppe")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
