"""03: Doppelbett (double bed, 1:12), v4, Wände bis Boden.

Real: ~200×160×50 cm mit 90 cm Kopfteil → 1:12 → 167×133×30 mm + Kopfteil 78 mm.

Konstruktion v4: Alle 4 Wände stehen DIREKT auf dem Boden (z=0). Die Wände
interlocken an den Ecken miteinander (je 2 Zapfen pro Ecke). Das Bodenpanel
sitzt INNERHALB des Wandrahmens, auf dem Fußboden, einfach reingelegt.

Vorteil: Kopfteil reicht jetzt bis zum Boden (kein "schwebendes" Aussehen mehr).

Assembly:
  1. Kopfteil aufstellen
  2. Beide Side Rails mit ihren linken End-Zapfen in die Kopfteil-Notches stecken
  3. Footboard mit Notches auf die rechten Side-Rail-Enden stecken
  4. Bodenpanel von oben in den entstandenen 4-seitigen Rahmen einlegen

Parts (5 total):
- 1× Kopfteil (133×78)        , Notches auf beiden Seiten unten für Side Rails
- 1× Footboard (133×30)       , gleiche Notches
- 2× Side Rail (161×30)       , Zapfen auf beiden Enden für Kopf/Foot
- 1× Bodenpanel (161×127)     , sitzt einfach im Rahmen, keine Joinery
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (Part, SLOT_W, THICKNESS, rect, slot_rect, layout_grid,
                 write_lbrn2, render_preview)

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "03_bett.lbrn2"
PREVIEW = OUT_DIR / "previews" / "03_bett.png"


def build_bed(bed_len=167.0, bed_wid=133.0,
              head_h=78.0, side_h=30.0,
              corner_tab_h=5.0, corner_tab_y1=8.0, corner_tab_y2=20.0):
    """
    bed_len, bed_wid: Bett-Außenmaße (= Boden + Wände im Rahmen)
    head_h: Gesamt-Höhe des Kopfteils (vom Fußboden bis Oberkante)
    side_h: Höhe der Side Rails + Footboard
    corner_tab_h: Höhe jedes Zapfens (5 mm)
    corner_tab_y1/y2: Z-Positionen der unteren/oberen Zapfen-Mitte
    """
    parts = []

    # Innere Bett-Maße (Bodenpanel-Größe)
    inner_len = bed_len - 2 * THICKNESS   # 161 mm
    inner_wid = bed_wid - 2 * THICKNESS   # 127 mm

    # Zapfen-Y-Bereiche (in 3D Z-Richtung) für Side-Rail-zu-Wand-Eckverbindung
    tab1_lo = corner_tab_y1 - corner_tab_h / 2
    tab1_hi = corner_tab_y1 + corner_tab_h / 2
    tab2_lo = corner_tab_y2 - corner_tab_h / 2
    tab2_hi = corner_tab_y2 + corner_tab_h / 2

    # === Side Rail: inner_len lang, side_h hoch, mit 2 Zapfen an JEDEM Ende ===
    def side_rail_outline():
        # Outline CCW startend bei (0, 0). Zapfen ragen LINKS (negative x) und RECHTS (positive x über inner_len)
        pts = []
        # Linke Kante (von unten nach oben), mit 2 Zapfen nach links
        pts.append((0, 0))
        pts.append((0, tab1_lo))
        pts.append((-THICKNESS, tab1_lo))
        pts.append((-THICKNESS, tab1_hi))
        pts.append((0, tab1_hi))
        pts.append((0, tab2_lo))
        pts.append((-THICKNESS, tab2_lo))
        pts.append((-THICKNESS, tab2_hi))
        pts.append((0, tab2_hi))
        pts.append((0, side_h))
        # Top edge nach rechts
        pts.append((inner_len, side_h))
        # Rechte Kante (von oben nach unten), mit 2 Zapfen nach rechts
        pts.append((inner_len, tab2_hi))
        pts.append((inner_len + THICKNESS, tab2_hi))
        pts.append((inner_len + THICKNESS, tab2_lo))
        pts.append((inner_len, tab2_lo))
        pts.append((inner_len, tab1_hi))
        pts.append((inner_len + THICKNESS, tab1_hi))
        pts.append((inner_len + THICKNESS, tab1_lo))
        pts.append((inner_len, tab1_lo))
        pts.append((inner_len, 0))
        # Bottom edge nach links zurück
        pts.append((0, 0))
        return pts

    side_outline = side_rail_outline()
    parts.append(Part("side_A", list(side_outline), []))
    parts.append(Part("side_B", list(side_outline), []))

    # === Kopfteil/Footboard mit Notches (Slots in den Seiten-Edges) für Side-Rail-Zapfen ===
    def end_wall_outline(width, height, with_chamfer=False):
        """End wall: full rectangle width × height (von z=0 bis z=height),
        mit Notches in linker und rechter Edge bei tab1 und tab2 Höhen."""
        pts = [(0, 0), (width, 0)]
        # Rechte Edge von unten nach oben, mit 2 Notches REIN (nach links)
        pts.append((width, tab1_lo))
        pts.append((width - THICKNESS, tab1_lo))
        pts.append((width - THICKNESS, tab1_hi))
        pts.append((width, tab1_hi))
        pts.append((width, tab2_lo))
        pts.append((width - THICKNESS, tab2_lo))
        pts.append((width - THICKNESS, tab2_hi))
        pts.append((width, tab2_hi))
        if with_chamfer:
            pts.append((width, height - 5))
            pts.append((width - 5, height))
            pts.append((5, height))
            pts.append((0, height - 5))
        else:
            pts.append((width, height))
            pts.append((0, height))
        # Linke Edge von oben nach unten, mit 2 Notches REIN (nach rechts)
        pts.append((0, tab2_hi))
        pts.append((THICKNESS, tab2_hi))
        pts.append((THICKNESS, tab2_lo))
        pts.append((0, tab2_lo))
        pts.append((0, tab1_hi))
        pts.append((THICKNESS, tab1_hi))
        pts.append((THICKNESS, tab1_lo))
        pts.append((0, tab1_lo))
        pts.append((0, 0))
        return pts

    parts.append(Part("headboard", end_wall_outline(bed_wid, head_h, with_chamfer=True), []))
    parts.append(Part("footboard", end_wall_outline(bed_wid, side_h, with_chamfer=False), []))

    # === Bodenpanel: einfaches Rechteck, sitzt im Rahmen ===
    parts.append(Part("base", rect(0, 0, inner_len, inner_wid), []))

    return parts


def main():
    parts = build_bed()
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=6)
    print(f"[bett v4] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
