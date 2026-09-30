"""01: Quadratischer Tisch (dining/coffee table, 1:12).

Real dimensions: ~84×84×72 cm → scale 1:12 → 70×70×60 mm
Construction: top + 2 parallel leg panels (slot-together, no glue needed).

Parts (3 total, all from 3 mm plywood):
- 1× Top (70×70 mm) with 2 parallel slots for the leg tabs
- 2× Leg panel (70×60 mm) with 50 mm × 3 mm tab on top edge
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (Part, SLOT_W, THICKNESS, rect, slot_rect, layout_grid,
                 write_lbrn2, render_preview)

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "01_tisch_quadrat.lbrn2"
PREVIEW = OUT_DIR / "previews" / "01_tisch_quadrat.png"


def build_table(top_w=70.0, top_d=70.0, height=60.0, tab_w=50.0,
                leg_inset=15.0, foot_cut_h=12.0):
    """
    top_w, top_d: top dimensions (width × depth)
    height: total table height (= leg panel height incl. tab)
    tab_w: width of the tab on each leg-panel (must be ≤ top_w)
    leg_inset: distance of each leg panel from the top edges (front/back)
    foot_cut_h: height of the decorative cutout at the bottom of each leg
                (creates 2 visible feet per panel)
    """
    parts = []

    # === Top piece ===
    top_outline = rect(0, 0, top_w, top_d)
    slot_y_front = leg_inset
    slot_y_back  = top_d - leg_inset
    top_holes = [
        slot_rect(top_w / 2, slot_y_front, tab_w, vertical=False),
        slot_rect(top_w / 2, slot_y_back,  tab_w, vertical=False),
    ]
    parts.append(Part("top", top_outline, top_holes))

    # === Leg panels (2 identical) ===
    leg_w = top_w               # full width to match top edges
    leg_h_body = height - THICKNESS  # body height (tab adds THICKNESS on top)
    foot_w = (leg_w - tab_w) / 2 + 4  # foot width on each side (under the shoulder)
    cut_w = leg_w - 2 * foot_w        # decorative cutout width

    # Outline CCW starting at bottom-left, with foot cutout at bottom and tab at top
    leg_outline = [
        (0, 0),
        (foot_w, 0),
        (foot_w, foot_cut_h),
        (foot_w + cut_w, foot_cut_h),
        (foot_w + cut_w, 0),
        (leg_w, 0),
        (leg_w, leg_h_body),
        ((leg_w + tab_w) / 2, leg_h_body),
        ((leg_w + tab_w) / 2, leg_h_body + THICKNESS),
        ((leg_w - tab_w) / 2, leg_h_body + THICKNESS),
        ((leg_w - tab_w) / 2, leg_h_body),
        (0, leg_h_body),
    ]
    parts.append(Part("leg_A", leg_outline, []))
    # Second leg panel: separate copy at origin (lib.layout_grid will place it)
    leg_outline_b = list(leg_outline)
    parts.append(Part("leg_B", leg_outline_b, []))

    return parts


def main():
    parts = build_table()
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2, name="01_tisch_quadrat")
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=10)
    print(f"[tisch] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm sheet")
    print(f"        .lbrn2: {LBRN2.name} ({size/1024:.1f} KB)")
    print(f"        preview: {PREVIEW.name} ({px[0]}×{px[1]} px)")


if __name__ == "__main__":
    main()
