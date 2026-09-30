"""07: Sofa (couch, 1:12), v2, FIXED.

Real: ~200×85×85 cm → 1:12 → 167×70×85 mm.
Same architecture as Bett v4: 4 walls form a rectangular frame, base sits
inside. Different wall heights give the sofa-look:
- Back wall = full backrest (70 mm tall)
- Front wall = low (30 mm)
- 2 Armrests = side walls (50 mm tall)
- Base = seat surface inside the frame, with engraved cushion details

Corner joints: tabs on the long walls (back+front), notches on the short walls
(armrests). Same pattern as Bett v4.

Parts (5 total):
- 1× Back wall (161×70)       , Tabs on both ends at bottom 30 mm zone
- 1× Front wall (161×30)      , Tabs on both ends
- 2× Armrest (70×50)          , Notches on left+right edges at bottom 30 mm
- 1× Base (161×64)            , Lose Sitzfläche im Rahmen, mit Engrave-Polster-Linien
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (Part, SLOT_W, THICKNESS, rect, slot_rect, layout_grid,
                 write_lbrn2, render_preview)

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "07_sofa.lbrn2"
PREVIEW = OUT_DIR / "previews" / "07_sofa.png"


def build_sofa(L=167.0, D=70.0,
               back_h=70.0, front_h=30.0, arm_h=50.0,
               corner_tab_h=5.0, corner_tab_y1=8.0, corner_tab_y2=20.0):
    """Same corner-joint design as Bett v4, alle Wände bis Boden, Base liegt drin."""
    parts = []

    inner_len = L - 2 * THICKNESS    # 161 mm
    inner_dep = D - 2 * THICKNESS    # 64 mm

    tab1_lo = corner_tab_y1 - corner_tab_h / 2
    tab1_hi = corner_tab_y1 + corner_tab_h / 2
    tab2_lo = corner_tab_y2 - corner_tab_h / 2
    tab2_hi = corner_tab_y2 + corner_tab_h / 2

    # Long-wall: tabs on both ENDS (left + right) at bottom 30 mm zone
    def long_wall_outline(width, height):
        pts = []
        pts.append((0, 0))
        # left edge with 2 tabs going LEFT
        pts.append((0, tab1_lo))
        pts.append((-THICKNESS, tab1_lo)); pts.append((-THICKNESS, tab1_hi))
        pts.append((0, tab1_hi))
        pts.append((0, tab2_lo))
        pts.append((-THICKNESS, tab2_lo)); pts.append((-THICKNESS, tab2_hi))
        pts.append((0, tab2_hi))
        pts.append((0, height))
        pts.append((width, height))
        # right edge with 2 tabs going RIGHT
        pts.append((width, tab2_hi))
        pts.append((width + THICKNESS, tab2_hi)); pts.append((width + THICKNESS, tab2_lo))
        pts.append((width, tab2_lo))
        pts.append((width, tab1_hi))
        pts.append((width + THICKNESS, tab1_hi)); pts.append((width + THICKNESS, tab1_lo))
        pts.append((width, tab1_lo))
        pts.append((width, 0))
        pts.append((0, 0))
        return pts

    # Short-wall: notches on left + right edges at bottom 30 mm
    def short_wall_outline(width, height, with_chamfer=False):
        pts = [(0, 0), (width, 0)]
        # right edge bottom-up with notches IN
        pts.append((width, tab1_lo))
        pts.append((width - THICKNESS, tab1_lo)); pts.append((width - THICKNESS, tab1_hi))
        pts.append((width, tab1_hi))
        pts.append((width, tab2_lo))
        pts.append((width - THICKNESS, tab2_lo)); pts.append((width - THICKNESS, tab2_hi))
        pts.append((width, tab2_hi))
        if with_chamfer:
            pts.append((width, height - 4))
            pts.append((width - 4, height))
            pts.append((4, height))
            pts.append((0, height - 4))
        else:
            pts.append((width, height))
            pts.append((0, height))
        # left edge top-down with notches IN
        pts.append((0, tab2_hi))
        pts.append((THICKNESS, tab2_hi)); pts.append((THICKNESS, tab2_lo))
        pts.append((0, tab2_lo))
        pts.append((0, tab1_hi))
        pts.append((THICKNESS, tab1_hi)); pts.append((THICKNESS, tab1_lo))
        pts.append((0, tab1_lo))
        pts.append((0, 0))
        return pts

    parts.append(Part("back",  long_wall_outline(inner_len, back_h), []))
    parts.append(Part("front", long_wall_outline(inner_len, front_h), []))
    parts.append(Part("arm_L", short_wall_outline(D, arm_h, with_chamfer=True), []))
    parts.append(Part("arm_R", short_wall_outline(D, arm_h, with_chamfer=True), []))
    parts.append(Part("base",  rect(0, 0, inner_len, inner_dep), []))

    return parts


def main():
    parts = build_sofa()
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)

    # Engrave: Polster-Trennlinien auf der base (3-Sitzer) + auf der back-Wand
    base = next(p for p in parts if p.name == "base")
    back = next(p for p in parts if p.name == "back")
    engraves = []
    bx0, by0, bx1, by1 = base.bbox()
    bw = bx1 - bx0
    # 2 vertikale Linien teilen base in 3 Sitze
    for frac in [1/3, 2/3]:
        x = bx0 + bw * frac
        engraves.append([(x - 0.3, by0 + 4), (x + 0.3, by0 + 4),
                         (x + 0.3, by1 - 4), (x - 0.3, by1 - 4)])
    # Same auf back-Wand (oberhalb der Tab-Zone, also y > 30)
    bbx0, bby0, bbx1, bby1 = back.bbox()
    bbw = bbx1 - bbx0
    for frac in [1/3, 2/3]:
        x = bbx0 + bbw * frac
        engraves.append([(x - 0.3, bby0 + 35), (x + 0.3, bby0 + 35),
                         (x + 0.3, bby1 - 5), (x - 0.3, bby1 - 5)])

    size = write_lbrn2(parts, LBRN2, engrave_shapes=engraves)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=6, engrave_shapes=engraves)
    print(f"[sofa v2] {len(parts)} parts + {len(engraves)} engrave on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
