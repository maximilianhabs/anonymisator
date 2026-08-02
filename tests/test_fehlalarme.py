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

print("\n=== 8. Belegte und unbelegte Treffer ===")
belegt = detect.analysiere("Wir danken Frau Dr. Ostermeier für die Zuweisung.")
pruefe(belegt and all(g.sicher for g in belegt if g.typ == "ARZT"),
       "Treffer mit Anrede und Titel gilt als belegt")

unbelegt = detect.analysiere(
    "Die Untersuchung fand in Regensburg statt und wurde dort ausgewertet.")
orte = [g for g in unbelegt if g.typ == "ORT"]
pruefe(orte and not orte[0].sicher,
       "Ortsname ohne Kontextmarker gilt als unbelegt")

print("\n" + "=" * 60)
if fehler:
    print(f"{len(fehler)} FEHLER:")
    for f in fehler:
        print("  -", f)
    sys.exit(1)
print("Alle Prüfungen bestanden.")
