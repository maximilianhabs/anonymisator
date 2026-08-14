"""Goldkorpus: prüft Recall und Präzision gegen einen festgeschriebenen Stand.

Anders als test_fehlalarme.py (was nicht gefunden werden darf) und
test_erkennung.py (ein Brief zum Durchlesen) trägt jedes Dokument hier eine
von Hand geprüfte Ground Truth: was gefunden werden SOLL. Ausgewertet wird
getrennt nach

  Recall     -- von dem, was gefunden werden sollte, wie viel wurde gefunden.
                Der gefährliche Fehler: ein übersehener Name bleibt lesbar.
  Präzision  -- von dem, was gefunden wurde, wie viel war korrekt.
                Der nur lästige Fehler: ein Fehlalarm nervt, gefährdet aber
                niemanden.

Bewusst kein gemeinsamer F-Wert -- der würde genau die Asymmetrie
verwischen, auf die es hier ankommt.

Ratschen-Logik: der Test schlägt nur fehl, wenn Recall oder Präzision eines
Dokuments gegenüber dem committeten Stand (goldkorpus_stand.json) SINKEN --
nicht gegen einen absoluten Schwellenwert. Eine Verbesserung wird nicht
automatisch übernommen, damit sie nicht unbemerkt vorbeirauscht: Stand mit
`python tests/test_goldkorpus.py --stand-aktualisieren` neu schreiben und
bewusst mitcommitten.

Alle Dokumente in goldkorpus/ sind frei erfunden und keinem realen Fall
nachgebildet -- Pflicht, weil dieses Korpus im öffentlichen Repository
liegt (siehe CONTRIBUTING.md).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect

KORPUS_DIR = Path(__file__).resolve().parent / "goldkorpus"
STAND_DATEI = Path(__file__).resolve().parent / "goldkorpus_stand.json"

fehler = []


def pruefe(bedingung, beschreibung):
    print(f"  {'OK  ' if bedingung else 'FEHL'}  {beschreibung}")
    if not bedingung:
        fehler.append(beschreibung)


def _auswerten(text: str, erwartet: list[dict]) -> dict:
    """Recall/Präzision eines Dokuments, auf Ebene der Gruppen.

    ZAHL bleibt aussen vor -- sie wirkt nur in der strengen Stufe und ist
    absichtlich sehr weit gefasst (jede Zahl ohne Einheit), siehe
    test_fehlalarme.py.
    """
    gruppen = [g for g in detect.analysiere(text) if g.typ != "ZAHL"]
    getroffen_ids: set[int] = set()
    uebersehen = []
    for e in erwartet:
        treffer = next(
            (g for g in gruppen if g.typ == e["typ"] and e["text"] in g.varianten),
            None,
        )
        if treffer is not None:
            getroffen_ids.add(id(treffer))
        else:
            uebersehen.append(f'{e["typ"]}: {e["text"]!r}')
    zu_viel = [f"{g.typ}: {g.anzeige!r}" for g in gruppen if id(g) not in getroffen_ids]

    recall = (len(erwartet) - len(uebersehen)) / len(erwartet) if erwartet else 1.0
    praezision = (len(gruppen) - len(zu_viel)) / len(gruppen) if gruppen else 1.0
    return {
        "recall": recall,
        "praezision": praezision,
        "uebersehen": uebersehen,
        "zu_viel": zu_viel,
        "erwartet_gesamt": len(erwartet),
        "gefunden_gesamt": len(gruppen),
    }


def _dokumente() -> list[str]:
    return sorted(p.stem for p in KORPUS_DIR.glob("*.txt"))


def _ergebnisse() -> dict[str, dict]:
    ergebnisse = {}
    for name in _dokumente():
        text = (KORPUS_DIR / f"{name}.txt").read_text(encoding="utf-8")
        erwartet = json.loads((KORPUS_DIR / f"{name}.json").read_text(encoding="utf-8"))
        ergebnisse[name] = _auswerten(text, erwartet["funde"])
    return ergebnisse


def _stand_schreiben(ergebnisse: dict[str, dict]) -> None:
    stand = {
        name: {"recall": r["recall"], "praezision": r["praezision"]}
        for name, r in ergebnisse.items()
    }
    STAND_DATEI.write_text(
        json.dumps(stand, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    dokumente = _dokumente()
    if not dokumente:
        print("Kein Dokument in tests/goldkorpus/ gefunden.")
        return 1

    ergebnisse = _ergebnisse()

    if "--stand-aktualisieren" in sys.argv:
        _stand_schreiben(ergebnisse)
        print(f"Stand geschrieben: {STAND_DATEI}")
        return 0

    stand = json.loads(STAND_DATEI.read_text(encoding="utf-8")) if STAND_DATEI.exists() else {}

    for name in dokumente:
        r = ergebnisse[name]
        print(f"\n=== {name} ===")
        print(f"  Recall {r['recall']:.0%} ({r['erwartet_gesamt'] - len(r['uebersehen'])}/"
              f"{r['erwartet_gesamt']}), Präzision {r['praezision']:.0%} "
              f"({r['gefunden_gesamt'] - len(r['zu_viel'])}/{r['gefunden_gesamt']})")
        for u in r["uebersehen"]:
            print(f"    übersehen: {u}")
        for z in r["zu_viel"]:
            print(f"    zu viel:   {z}")

        alter_stand = stand.get(name)
        if alter_stand is None:
            pruefe(False, f"{name}: kein Stand hinterlegt -- mit "
                   "--stand-aktualisieren erzeugen und committen")
            continue
        pruefe(r["recall"] >= alter_stand["recall"] - 1e-9,
               f"{name}: Recall nicht gesunken "
               f"({r['recall']:.0%}, Stand {alter_stand['recall']:.0%})")
        pruefe(r["praezision"] >= alter_stand["praezision"] - 1e-9,
               f"{name}: Präzision nicht gesunken "
               f"({r['praezision']:.0%}, Stand {alter_stand['praezision']:.0%})")

    print("\n" + "=" * 60)
    if fehler:
        print(f"{len(fehler)} FEHLER:")
        for f in fehler:
            print("  -", f)
        return 1
    print("Alle Prüfungen bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
