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
    gruppen = detect.analysiere(text)
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
]
for text, muss in ECHTE:
    gruppen = detect.analysiere(text)
    gefunden = [f.text for g in gruppen for f in g.funde]
    pruefe(any(muss in t for t in gefunden),
           f"{muss!r} wird weiterhin erkannt{'' if any(muss in t for t in gefunden) else f' — {gefunden}'}")

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
