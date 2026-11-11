"""Prüft den Ordner-Modus (app/ordner.py): Ablage, Endkontrolle, Startprüfung.

Läuft ohne Server, nur in temporären Verzeichnissen und mit frei erfundenen
Briefen. Der Kern ist die Zusage, dass nichts Ungeprüftes im Ausgang landet
und dass Protokoll und Konsole keinen Namen verraten — weder aus dem Text noch
aus dem Dateinamen.
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export, ordner, stufen

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


BRIEF = """Neurologische Klinik am Auwald
Ludwigstraße 47, 94032 Passau
Tel.: 0851 / 4409-233

Passau, 14.03.2026

Sehr geehrte Frau Kollegin Brandner,

wir berichten über Ihre Patientin Frau Elisabeth Hartmann, geb. 22.07.1958,
wohnhaft Rosenweg 12, 94469 Deggendorf, Versichertennummer M123456789.
Die 67-jährige Patientin befand sich vom 03.03.2026 bis 12.03.2026 in
unserer stationären Behandlung. Fallnummer: 2026-KA-88213

Die Beschwerden bestehen seit 3 Jahren. Die Patientin arbeitet seit 1994
bei der Firma Grubmüller Metallbau. Das MRT zeigte eine Läsion im linken
Temporallappen.

Mit freundlichen Grüßen
Prof. Dr. med. Konrad Weißbach"""

KLARTEXT = ["Hartmann", "Elisabeth", "Brandner", "Weißbach", "22.07.1958",
            "Rosenweg", "Deggendorf", "0851", "4409", "M123456789", "88213",
            "Grubmüller"]

BRIEF2 = (Path(__file__).parent / "goldkorpus" / "diagnose_hirntumor.txt").read_text(
    encoding="utf-8")

OHNE_PATIENT = (
    "Die Magnetresonanztomographie des Schädels ohne und mit Kontrastmittel "
    "zeigt eine umschriebene Läsion im linken Temporallappen mit geringem "
    "perifokalem Ödem. Eine Mittellinienverlagerung besteht nicht. Die "
    "Liquorräume sind symmetrisch weit, die Hirnstammstrukturen unauffällig. "
    "Eine Kontrolle wird in drei Monaten empfohlen."
)


def lauf(eingang, ausgang, *extra):
    """Ruft main() auf und fängt die Konsole ab. Gibt (Code, stdout, stderr)."""
    aus, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(aus), contextlib.redirect_stderr(err):
        code = ordner.main(["--eingang", str(eingang), "--ausgang", str(ausgang),
                            "--einmal", *extra])
    return code, aus.getvalue(), err.getvalue()


def protokoll(eingang):
    pfad = Path(eingang) / "protokoll.csv"
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


def namen(verzeichnis):
    return sorted(p.name for p in Path(verzeichnis).iterdir())


with tempfile.TemporaryDirectory() as wurzel:
    wurzel = Path(wurzel)
    ein, aus = wurzel / "eingang", wurzel / "ausgang"
    ein.mkdir()

    print("\n=== 1. Guter Brief, Ablage und Verschwiegenheit ===")
    (ein / "Hartmann_Elisabeth_Brief.txt").write_text(BRIEF, encoding="utf-8")
    code, stdout, stderr = lauf(ein, aus)
    pruefe(code == 0, f"Lauf endet mit 0 (war {code}; {stderr.strip()[:80]})")
    pruefe(namen(aus) == ["dokument_0001.txt"], f"Ausgang: {namen(aus)}")
    ergebnis = (aus / "dokument_0001.txt").read_text(encoding="utf-8")
    uebrig = [w for w in KLARTEXT if w.lower() in ergebnis.lower()]
    pruefe(not uebrig, f"Kein Klartext im Ergebnis (gefunden: {uebrig})")
    pruefe("Anonymisiert (Stufe streng" in ergebnis, "Kopfzeile mit Stufe vorhanden")
    pruefe(namen(ein / "Erledigt") == ["Hartmann_Elisabeth_Brief.txt"],
           "Original in Erledigt")
    pruefe("Hartmann_Elisabeth_Brief.txt" not in namen(ein), "Original nicht mehr im Eingang")
    prot = protokoll(ein)
    zeilen = prot.strip().splitlines()
    pruefe(len(zeilen) == 2 and ",frei," in zeilen[1] and "dokument_0001.txt" in zeilen[1],
           f"Protokoll: Kopf plus eine Zeile 'frei' ({len(zeilen)} Zeilen)")
    pruefe(zeilen[1].split(",")[3] == "paste", "Protokoll nennt die Quelle")
    pruefe(zeilen[0].startswith("zeitstempel,ergebnis,ausgabedatei"), "Protokoll mit Kopfzeile")
    sensibel = ["Hartmann", "Elisabeth", "Brief.txt", "Weißbach", "1958"]
    pruefe(not [w for w in sensibel if w in prot],
           "Protokoll ohne Dateiname und Klarnamen")
    pruefe(not [w for w in sensibel if w in stdout + stderr],
           "Konsole ohne Dateiname und Klarnamen")

    print("\n=== 2. Zweite Datei, laufende Nummer ===")
    (ein / "zweiter_fall.txt").write_text(BRIEF2, encoding="utf-8")
    code, stdout, stderr = lauf(ein, aus)
    pruefe(namen(aus) == ["dokument_0001.txt", "dokument_0002.txt"],
           f"Ausgang: {namen(aus)} (Konsole: {stdout.strip()[:160]})")
    pruefe("Lindqvist" not in (aus / "dokument_0002.txt").read_text(encoding="utf-8")
           if (aus / "dokument_0002.txt").exists() else False,
           "Zweites Ergebnis ohne Klarnamen")

    print("\n=== 3. Namenskollision in Erledigt ===")
    (ein / "zweiter_fall.txt").write_text(BRIEF2, encoding="utf-8")
    lauf(ein, aus)
    pruefe("zweiter_fall_2.txt" in namen(ein / "Erledigt"),
           f"Suffix _2 bei gleichem Namen: {namen(ein / 'Erledigt')}")

    print("\n=== 4. Ohne erkennbaren Patienten: zurückgehalten ===")
    vor = namen(aus)
    (ein / "befund.txt").write_text(OHNE_PATIENT, encoding="utf-8")
    lauf(ein, aus)
    pruefe(namen(aus) == vor, "Nichts Neues im Ausgang")
    pruefe("befund.txt" in namen(ein / "Zurueckgehalten"), "Original zurückgehalten")
    letzte = protokoll(ein).strip().splitlines()[-1]
    pruefe("zurueckgehalten" in letzte and "kein_patient" in letzte,
           f"Protokoll mit kein_patient: {letzte}")

    print("\n=== 5. Kurzer Text, kaputte PDF ===")
    vor = namen(aus)
    (ein / "kurz.txt").write_text("Kurzer Text.", encoding="utf-8")
    (ein / "kaputt.pdf").write_bytes(os.urandom(600))
    (ein / "kaputt2.pdf").write_bytes(b"%PDF-1.4\n" + os.urandom(600))
    code, stdout, _ = lauf(ein, aus)
    pruefe(code == 0, "Lauf bricht trotz kaputter Datei nicht ab")
    prot = protokoll(ein)
    pruefe("kein_text" in prot, "kein_text gemeldet")
    pruefe(prot.count("lesefehler") == 2, f"lesefehler gemeldet ({prot.count('lesefehler')}x)")
    pruefe(namen(aus) == vor, "Nichts im Ausgang")
    pruefe({"kurz.txt", "kaputt.pdf", "kaputt2.pdf"} <= set(namen(ein / "Zurueckgehalten")),
           "Alle drei zurückgehalten")

    print("\n=== 6. Unbekannte Endung, Unterordner, Verstecktes bleiben liegen ===")
    (ein / "bild.png").write_bytes(b"\x89PNG")
    (ein / ".versteckt.txt").write_text(BRIEF, encoding="utf-8")
    (ein / "unterordner").mkdir()
    (ein / "unterordner" / "tief.txt").write_text(BRIEF, encoding="utf-8")
    vor = namen(aus)
    code, stdout, _ = lauf(ein, aus)
    pruefe(namen(aus) == vor, "Nichts verarbeitet")
    pruefe({"bild.png", ".versteckt.txt", "unterordner"} <= set(namen(ein)),
           "Alle drei liegen noch im Eingang")
    pruefe("1 Datei(en) mit unbekannter Endung" in stdout,
           f"Anzahl unbekannter Endungen gemeldet: {stdout.strip()[:100]}")
    pruefe("bild" not in stdout, "Konsole nennt den Namen nicht")

    print("\n=== 7. Stabilitätsprüfung: erst bei gleicher Messung ===")
    ein2, aus2 = wurzel / "ein2", wurzel / "aus2"
    ein2.mkdir()
    (ein2 / "neu.txt").write_text(BRIEF, encoding="utf-8")
    einst = ordner.Einstellungen(ein2, aus2)
    aus2.mkdir()
    still = io.StringIO()
    with contextlib.redirect_stdout(still):
        messung, n1, _, nr = ordner.durchlauf(einst, {}, 0)
    pruefe(n1 == 0 and (ein2 / "neu.txt").exists(), "Erste Messung fasst nichts an")
    (ein2 / "neu.txt").write_text(BRIEF + "\nNachtrag.", encoding="utf-8")
    os.utime(ein2 / "neu.txt", ns=(1, 2))
    with contextlib.redirect_stdout(still):
        messung, n2, _, nr = ordner.durchlauf(einst, messung, nr)
    pruefe(n2 == 0, "Geänderte Datei wird nicht gelesen")
    with contextlib.redirect_stdout(still):
        messung, n3, _, nr = ordner.durchlauf(einst, messung, nr)
    pruefe(n3 == 1 and namen(aus2) == ["dokument_0001.txt"],
           "Unveränderte Datei wird verarbeitet")

    print("\n=== 8. Endkontrolle rest_klartext ===")
    for stufe in ("leicht", "standard", "streng"):
        gruppen = detect.analysiere(BRIEF)
        stufen.formen_berechnen(gruppen)
        sauber = ordner.verarbeite("x.txt", BRIEF.encode(), stufe).text
        pruefe(sauber and not ordner.rest_klartext(gruppen, sauber, stufe),
               f"{stufe}: sauberer Text besteht")
        pruefe(ordner.rest_klartext(gruppen, sauber + "\nFrau Hartmann", stufe),
               f"{stufe}: stehen gebliebener Nachname wird gemeldet")
    gruppen = detect.analysiere(BRIEF)
    stufen.formen_berechnen(gruppen)
    pruefe(ordner.rest_klartext(gruppen, "Patientin [PATIENT_A] in Passau.", "streng"),
           "Ort im Klartext wird gemeldet (streng)")
    pruefe(not ordner.rest_klartext(gruppen, "Patientin E. H. in Passau.", "standard"),
           "Behaltener Ort (standard, Behandlung behalten) ist kein Rest")
    pruefe(not ordner.rest_klartext(gruppen, "Prof. Dr. med. [ARZT_2], Frau [PATIENT_A]",
                                    "streng"),
           "Titel und Anrede allein zählen nicht")
    # Der Name im Klartext fällt auch der erneuten Erkennung auf: beide Codes.
    pruefe("rest_klartext" in ordner.endkontrolle(
        gruppen, "[PATIENT_A] ist da, wohnt in Hartmanns Haus. Hartmann.", "streng"),
           "endkontrolle liefert den Code rest_klartext")

    print("\n=== 9. Endkontrolle rest_erkennung ===")
    gut = ordner.verarbeite("x.txt", BRIEF.encode(), "streng").text
    pruefe(not ordner.rest_erkennung(gut, "streng"),
           "Platzhalter lösen keinen Fehlalarm aus (streng)")
    pruefe(ordner.rest_erkennung(gut + "\nTelefon: 0851 / 998877", "streng"),
           "Übrig gebliebene Telefonnummer wird erkannt")
    pruefe(ordner.rest_erkennung(gut + "\nBitte antworten an max.mustermann@example.org",
                                 "streng"),
           "Übrig gebliebene E-Mail wird erkannt")
    gut_leicht = ordner.verarbeite("x.txt", BRIEF.encode(), "leicht").text
    pruefe(not ordner.rest_erkennung(gut_leicht, "leicht"),
           "Initialen und Jahrgang lösen auf Stufe leicht keinen Fehlalarm aus")

    print("\n=== 10. Startprüfungen ===")
    a, b = wurzel / "a", wurzel / "b"
    a.mkdir()
    f, _ = ordner.pruefe_start(a, a)
    pruefe(bool(f), "Eingang == Ausgang: Fehler")
    (a / "innen").mkdir()
    f, _ = ordner.pruefe_start(a, a / "innen")
    pruefe(bool(f), "Ausgang im Eingang: Fehler")
    f, _ = ordner.pruefe_start(a / "innen", a)
    pruefe(bool(f), "Eingang im Ausgang: Fehler")
    f, _ = ordner.pruefe_start(wurzel / "gibtsnicht", b)
    pruefe(bool(f), "Eingang existiert nicht: Fehler")
    f, _ = ordner.pruefe_start(a, b)
    pruefe(not f and not b.exists(), "Gültig; Ausgang wird nicht angelegt")
    f, _ = ordner.pruefe_start(ordner.REPO / "tests", b)
    pruefe(bool(f), "Eingang im Repo: Fehler")
    f, _ = ordner.pruefe_start(a, ordner.REPO / "neuer_ausgang")
    pruefe(bool(f) and not (ordner.REPO / "neuer_ausgang").exists(),
           "Ausgang im Repo: Fehler, nichts angelegt")
    code, _, stderr = lauf(a, a)
    pruefe(code == 2 and "Abbruch" in stderr, "main() bricht mit Code 2 ab")
    fehlt = io.StringIO()
    with contextlib.redirect_stderr(fehlt):
        code = ordner.main(["--einmal"]) if not (
            os.environ.get("ANON_EINGANG") or os.environ.get("ANON_AUSGANG")) else 2
    pruefe(code == 2, "Ohne Eingang und Ausgang: Abbruch")

    heim = wurzel / "heim"
    (heim / "Desktop" / "post").mkdir(parents=True)
    alt = os.environ.get("HOME")
    os.environ["HOME"] = str(heim)
    try:
        _, w = ordner.pruefe_start(heim / "Desktop" / "post", b)
    finally:
        os.environ["HOME"] = alt
    pruefe(bool(w), "Eingang unter ~/Desktop: Warnung, kein Fehler")

print("\n=== Namens-Nachlauf und Titel-Fehlalarm der Endkontrolle ===")
# Aus dem ersten echten Lauf (nur Formen bekannt): ein Wort war an einer Stelle
# als Person erkannt, stand woanders aber noch im Text; und "PROF. DR. MED.
# [ARZT_1]" liess die Arzt-Regel auf "MED" ausweichen.
_brief = ("Sehr geehrte Kollegen,\n\nwir berichten über Frau Elisabeth Hartmann, "
          "geb. 22.07.1958, wohnhaft Ludwigstraße 47, 94469 Deggendorf.\n\n"
          "Die Patientin wurde stationär behandelt. Der Verlauf war unauffällig, "
          "die Entlassung erfolgte in gutem Allgemeinzustand nach Hause.\n\n"
          "PROF. DR. MED. KONRAD WEISSBACH\nChefarzt\n")
_g = detect.analysiere(_brief)
stufen.formen_berechnen(_g)
_ers = stufen.ersetzungen_fuer(_g, "streng", nur_aktive=False)
_roh = export.ersetze(_brief, _ers) + "\nNachtrag: HARTMANN wünscht einen Termin."
pruefe(ordner.rest_klartext(_g, _roh, "streng"),
       "Vor dem Nachlauf: stehen gebliebener Name wird als Rest gemeldet")
_neu, _n = ordner.namens_nachlauf(_g, _ers, _roh)
pruefe(_n == 1 and "HARTMANN" not in _neu.upper().replace("[", " ").split()
       and "hartmann" not in _neu.lower(),
       f"Nachlauf ersetzt das verbliebene Vorkommen ({_n} Ersetzung)")
pruefe(not ordner.rest_klartext(_g, _neu, "streng"),
       "Nach dem Nachlauf: kein Rest mehr")
pruefe(ordner.namens_nachlauf(_g, _ers, export.ersetze(_brief, _ers))[1] == 0,
       "Sauberer Text: Nachlauf ändert nichts")
pruefe(not ordner.rest_erkennung("PROF. DR. MED. [ARZT_1]\nChefarzt der Klinik\n",
                                 "streng"),
       "Titelzeile vor Platzhalter ist kein Rest ('MED' ist kein Arzt)")
pruefe(ordner.rest_erkennung("PROF. DR. MED. KONRAD WEISSBACH\nChefarzt\n", "streng"),
       "Gegenprobe: echter Name nach Titel bleibt ein Rest")

if fehler:
    print(f"\n{len(fehler)} Fehler:")
    for f in fehler:
        print(f"  - {f}")
    sys.exit(1)
print("\nAlles in Ordnung.")
