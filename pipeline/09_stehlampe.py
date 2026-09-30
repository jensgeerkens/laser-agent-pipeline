"""09: Stehlampe (floor lamp, 1:12), v2, FIXED.

Real: ~Ø30×180 cm → 1:12 → 50×50 Fuß × 130 mm Pol × 27×27×25 Schirm.

Konstruktion v2 (jeder Joint hat passende Tab/Slot-Paare):
- 1× Foot-Base (50×50 quadrat) mit zentralem Slot (4×3 mm) für Pol-Zapfen
- 1× Pole (6 mm breit × 130 mm hoch + 3 mm Zapfen oben + 3 mm Zapfen unten,
   Zapfen 4 mm breit zentriert mit Schultern)
- 4× Schirm-Wand (24×25 mm Rechteck, wird zusammengeklebt)
- 1× Schirm-Deckel (27×27 mm) mit zentralem Slot für oberen Pol-Zapfen

Assembly:
  1. Pol mit unterem Zapfen in Foot-Slot stecken → Pol steht vertikal
  2. 4 Schirm-Wände an den Kanten zu einer quadratischen Röhre verleimen (24×24 innen)
  3. Schirm-Deckel oben aufkleben (1.5 mm Überstand auf jeder Seite)
  4. Komplettierte Schirm-Einheit von oben auf den Pol stecken
     (oberer Pol-Zapfen in Deckel-Slot)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (Part, SLOT_W, THICKNESS, rect, slot_rect, layout_grid,
                 write_lbrn2, render_preview)

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "09_stehlampe.lbrn2"
PREVIEW = OUT_DIR / "previews" / "09_stehlampe.png"


def build_lamp(foot_size=50.0, pole_h=130.0, pole_w=6.0,
               shade_wall_w=24.0, shade_wall_h=25.0, shade_roof=27.0,
               tab_w=4.0):
    parts = []

    # 1. Foot base: square plate with center slot
    foot_holes = [slot_rect(foot_size / 2, foot_size / 2, tab_w, vertical=False)]
    parts.append(Part("foot", rect(0, 0, foot_size, foot_size), foot_holes))

    # 2. Pole: 6 mm wide × 130 mm body, with 4×3 tabs (centered) on top + bottom
    tab_off = (pole_w - tab_w) / 2     # = 1 mm shoulder each side
    pole_outline = [
        (tab_off, 0),                                       # bottom tab L
        (tab_off + tab_w, 0),                               # bottom tab R
        (tab_off + tab_w, THICKNESS),                       # shoulder R in
        (pole_w, THICKNESS),                                # shoulder R out
        (pole_w, THICKNESS + pole_h),                       # right edge up to top body
        (tab_off + tab_w, THICKNESS + pole_h),              # shoulder R top in
        (tab_off + tab_w, 2 * THICKNESS + pole_h),          # top tab R
        (tab_off, 2 * THICKNESS + pole_h),                  # top tab L
        (tab_off, THICKNESS + pole_h),                      # shoulder L top in
        (0, THICKNESS + pole_h),                            # shoulder L top out
        (0, THICKNESS),                                     # left edge down to bottom body
        (tab_off, THICKNESS),                               # shoulder L bottom out
    ]
    parts.append(Part("pole", pole_outline, []))

    # 3. 4 Schirm-Wände, einfache Rechtecke (Verkleben)
    for i in range(4):
        parts.append(Part(f"shade_wall_{i+1}",
                          rect(0, 0, shade_wall_w, shade_wall_h), []))

    # 4. Schirm-Deckel mit zentralem Slot für oberen Pol-Zapfen
    roof_holes = [slot_rect(shade_roof / 2, shade_roof / 2, tab_w, vertical=False)]
    parts.append(Part("shade_roof", rect(0, 0, shade_roof, shade_roof), roof_holes))

    return parts


def main():
    parts = build_lamp()
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=10)
    print(f"[lampe v2] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
