---
name: laser-mech
description: Erzeugt Laser-Cut-Vorlagen für mechanische Teile (Zahnräder, Getriebe, Planetensysteme, Riemenscheiben, einfache Uhrwerke, Kurbeln) auf Basis von boxes.py. Ausgabe standardmäßig als LightBurn .lbrn2, alternativ SVG. Auslöser z. B. "Zahnrad lasern", "Getriebe entwerfen", "boxes.py Generator", "Planetengetriebe", "Riemenscheibe".
---

# laser-mech: mechanische Laser-Cut-Vorlagen

## Wann einsetzen
Für Zahnräder, Getriebe, Planetensysteme, Riemenscheiben, Uhrgehäuse, Kurbeln und Hebel.

## Werkzeuge

- `run_boxes.py`: Wrapper um die boxes.py-CLI (Florian Festi, GPL-3.0, externe Abhängigkeit, nicht Teil dieses Repos). Findet die CLI über `BOXES_EXE`, `PATH` oder das Scripts-Verzeichnis des aktiven Python.
- `crank.py`: eigene Handkurbel (Arm plus Griffscheiben) mit shapely, schreibt `.lbrn2` direkt.

## Kommandos

```bash
python skills/laser-mech/run_boxes.py list-mech          # kuratierte Mechanik-Generatoren
python skills/laser-mech/run_boxes.py list               # alle Generatoren
python skills/laser-mech/run_boxes.py params Gears       # Parameter eines Generators
python skills/laser-mech/run_boxes.py run Gears \
       --teeth1=12 --teeth2=32 --modulus=3 --shaft1=6 \
       --thickness=4 --burn=0.15 --output=gears.lbrn2
python skills/laser-mech/crank.py --shaft 6 --arm-length 60 --output crank.lbrn2
```

## Kuratierte Generatoren

| Generator | Zweck |
|---|---|
| `Gears` | Stirnradpaar (Ritzel und großes Rad) |
| `Pulley` | Riemenscheibe (u. a. GT2-Profil) |
| `GearBox` | Geschlossenes Getriebegehäuse |
| `Planetary` | Planetengetriebe (Sonne, Planeten, Hohlrad) |
| `Planetary2` | Alternative Planetenkonfiguration |
| `Clock` | Uhrgesicht / Gehäuse |
| `SevenSegmentClock` | Uhr im 7-Segment-Stil |

## Ablauf

1. Ziel klären; bei Unklarheit `list-mech` zeigen.
2. Parameter klären: Zähnezahl, Modul, Wellendurchmesser, Materialstärke.
3. Bei Bedarf `params <Generator>`.
4. `run <Generator>` mit den finalen Werten.
5. Datei in LightBurn öffnen und die Schnitt-Layer mit den Materialwerten belegen.

## Häufige Parameter

- `--thickness=4`: Materialstärke in mm
- `--burn=0.15`: Kerf-Kompensation in mm (Startwert, unkalibriert)
- `--format=svg`: statt `.lbrn2`
- `--reference=0`, `--labels=False`: vom Wrapper standardmäßig gesetzt

Für `Gears`: `--teeth1`, `--teeth2`, `--modulus` (Teilkreisdurchmesser / Zähnezahl), `--shaft1`, `--shaft2`, `--pressure_angle=20`. Übersetzung i = teeth2 / teeth1, z. B. 12 zu 32 ergibt 1 : 2,67.

## Ausgabe und Attribution

- Standardformat `.lbrn2`, mit `--format=svg` SVG. Kein DXF (kann boxes.py nicht direkt).
- boxes.py schreibt einen Attributionsblock (`<Notes>`) in `.lbrn2`, den LightBurn beim Öffnen anzeigt. Er bleibt standardmäßig erhalten; `run --strip-notes <Generator> ...` entfernt ihn bei Bedarf. Die Herkunft bleibt dann über die boxes.py-Metadaten und diese Dokumentation nachvollziehbar.
- Die Layer-Namen von boxes.py lauten "Outer Cut", "Inner Cut", "Etch"; Geschwindigkeit und Leistung werden in LightBurn gesetzt.

## Grenzen

- Mehrstufige Präzisionsgetriebe und Hemmungen deckt boxes.py nicht vollständig ab.
- Bei beweglichen Teilen zuerst Probestücke schneiden, Toleranzen schwanken je Materialcharge.
