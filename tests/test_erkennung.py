"""Prüft die Erkennung an einem frei erfundenen Arztbrief."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import detect, export

BRIEF = """Neurologische Klinik am Auwald
Ludwigstraße 47, 94032 Passau
Tel.: 0851 / 4409-233, Fax 0851/4409-299
E-Mail: sekretariat@klinik-auwald.de

Chefarzt: Prof. Dr. med. Konrad Weißbach

Passau, 14.03.2026

Sehr geehrte Frau Kollegin Brandner,

wir berichten über Ihre Patientin Frau Elisabeth Hartmann, geb. 22.07.1958,
wohnhaft Rosenweg 12, 94469 Deggendorf, Versichertennummer M123456789,
die sich vom 03.03.2026 bis 12.03.2026 in unserer stationären Behandlung befand.
Fallnummer: 2026-KA-88213

Diagnosen:
1. Fokale Epilepsie mit Ursprung im linken Temporallappen
2. Arterielle Hypertonie

Anamnese:
Frau Hartmann wurde von ihrem Ehemann, Herrn Gerhard Hartmann, in der
Notaufnahme vorgestellt. Die Patientin berichtet über wiederholte Episoden
seit etwa Januar 2026. Die Vorbefunde von Dr. Sailer aus Vilshofen lagen vor.

Befunde:
Das EEG vom 05.03.2026 zeigte intermittierende Verlangsamungen temporal links.
Das MRT wurde in der Radiologie Dr. Ostermeier durchgeführt.

Wir bitten um Wiedervorstellung. Bei Rückfragen erreichen Sie mich unter
der Durchwahl 0851 4409-241 oder mobil unter +49 171 2233445.

Mit freundlichen Grüßen

Prof. Dr. med. K. Weißbach          Dr. Miriam Kolbeck
Chefarzt                            Assistenzärztin
"""

gruppen = detect.analysiere(BRIEF)

print(f"{len(gruppen)} Gruppen, "
      f"{sum(len(g.funde) for g in gruppen)} Fundstellen\n")

nach_typ = {}
for g in gruppen:
    nach_typ.setdefault(g.typ, []).append(g)

for typ in detect.KATEGORIEN:
    if typ not in nach_typ:
        continue
    print(f"── {detect.KATEGORIE_TITEL[typ]}")
    for g in nach_typ[typ]:
        weitere = [v for v in g.varianten if v != g.anzeige]
        extra = f"   (auch: {', '.join(weitere)})" if weitere else ""
        print(f"   {g.label:<14} {g.anzeige!r} ×{len(g.funde)}{extra}")
    print()

ers = [{"start": f.start, "ende": f.end, "label": g.label}
       for g in gruppen for f in g.funde]
print("=" * 72)
print(export.ersetze(BRIEF, ers))
