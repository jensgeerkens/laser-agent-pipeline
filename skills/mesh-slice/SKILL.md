---
name: mesh-slice
description: Zerlegt ein 3D-Mesh (STL/OBJ) in eine steckbare Holzfigur aus Querspanten und einem Längsrücken mit Halbüberblattungs-Slots. Ausgabe als SVG, LightBurn .lbrn2 und Vorschau-PNG. Auslöser z. B. "3D-Modell in Steckfigur", "Mesh slicen für Laser".
---

# mesh-slice: 3D-Mesh zur Steckfigur

## Pipeline

1. Mesh laden, längste Achse auf X drehen, zentrieren, auf `--length` skalieren
2. `--slices` Querschnitte (Spanten) zwischen den Rändern (`--margin` in %)
3. Längsschnitt bei Y = 0 als Rücken
4. Jeder Schnitt: morphologisches Öffnen (`--opening`), Spiegelsymmetrie, größte Fläche
5. Spanten verwerfen, die Z = 0 nicht kreuzen oder zu klein sind (Grund wird ausgegeben)
6. Optional Seitenflossen: Schnitt bei Y = `--fin-y`, linke und rechte Kopie (ohne Steckverbindung)
7. Slots: Rücken von oben, Spanten von unten geschlitzt, Breite = `--thickness` + `--clearance`
8. Regal-Layout, Export als SVG (Y-DOWN mit Transformation), `.lbrn2` (Y-UP) und Vorschau

## Aufruf

```bash
python skills/mesh-slice/slice.py <mesh.stl> [--length 250] [--slices 16] \
       [--thickness 4] [--clearance 0.15] [--fin-y 15] [--no-fins] \
       [--out-dir <ordner>] [--name <basis>]
```

Beispiel mit dem synthetischen Demokörper:

```bash
python tools/make_demo_assets.py
python skills/mesh-slice/slice.py examples/mesh-slice/demo_body.stl \
       --out-dir examples/mesh-slice --name demo_body
```

## Abhängigkeiten

`trimesh`, `shapely`, `svgwrite`, `numpy`, `rtree`, `Pillow`

## Grenzen

- Die Figur wird nicht physikalisch simuliert; Slot-Tiefen folgen aus der Geometrie.
- Seitenflossen haben keine Steckverbindung und werden angeklebt.
- `--fin-y` muss außerhalb der halben Körperbreite liegen, sonst wird der Körper selbst als Flosse erfasst.
- Clearance 0,15 mm ist ein Startwert, keine Messung.
