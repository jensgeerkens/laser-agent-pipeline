"""02: Stuhl (chair, 1:12).

Real: ~45×45×90 cm → scale 1:12 → 38×38×75 mm
Construction: through-seat tenon design (back panel passes through the seat).

Parts (3 different shapes, 3 pieces total):
- 1× Seat (38×38 mm) with 1 front slot + tab on back edge
- 1× Front panel (38×35 mm) with 30×3 tab on top
- 1× Back panel + backrest combined (38×75 mm) with horizontal slot at seat-line
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import (Part, SLOT_W, THICKNESS, rect, slot_rect, layout_grid,
                 write_lbrn2, render_preview)

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "02_stuhl.lbrn2"
PREVIEW = OUT_DIR / "previews" / "02_stuhl.png"


def build_chair(seat_w=38.0, seat_d=38.0,
                seat_height=35.0, back_height=75.0,
                tab_w=30.0, foot_cut_h=8.0):
    """Through-seat chair. Seat has a back-tab passing through a slot in the back panel."""
    parts = []

    # === Seat: rectangle + back tab ===
    # Layout: front edge at y=0, back edge at y=seat_d (=38). Back tab sticks
    # out further at y > seat_d. Front slot for front-panel tab at y=4.
    seat_outline = [
        (0, 0),
        (seat_w, 0),
        (seat_w, seat_d),
        ((seat_w + tab_w) / 2, seat_d),
        ((seat_w + tab_w) / 2, seat_d + THICKNESS),
        ((seat_w - tab_w) / 2, seat_d + THICKNESS),
        ((seat_w - tab_w) / 2, seat_d),
        (0, seat_d),
    ]
    seat_holes = [slot_rect(seat_w / 2, 5, tab_w, vertical=False)]
    parts.append(Part("seat", seat_outline, seat_holes))

    # === Front panel ===
    front_body_h = seat_height - THICKNESS    # leg body height = 32 mm
    foot_w = (seat_w - tab_w) / 2 + 4         # foot width on each side
    cut_w = seat_w - 2 * foot_w               # decorative foot cutout width
    front_outline = [
        (0, 0),
        (foot_w, 0),
        (foot_w, foot_cut_h),
        (foot_w + cut_w, foot_cut_h),
        (foot_w + cut_w, 0),
        (seat_w, 0),
        (seat_w, front_body_h),
        ((seat_w + tab_w) / 2, front_body_h),
        ((seat_w + tab_w) / 2, front_body_h + THICKNESS),
        ((seat_w - tab_w) / 2, front_body_h + THICKNESS),
        ((seat_w - tab_w) / 2, front_body_h),
        (0, front_body_h),
    ]
    parts.append(Part("front_panel", front_outline, []))

    # === Back panel + backrest (single piece, 75 mm tall) ===
    back_outline = [
        (0, 0),
        (foot_w, 0),
        (foot_w, foot_cut_h),
        (foot_w + cut_w, foot_cut_h),
        (foot_w + cut_w, 0),
        (seat_w, 0),
        (seat_w, back_height),
        # Slightly rounded-feeling top corner: chamfer
        (seat_w - 4, back_height + 2),
        (4, back_height + 2),
        (0, back_height),
    ]
    # Horizontal slot for seat back-tab: positioned at z=32..35 (seat-line)
    seat_z = front_body_h           # 32 mm
    back_slot = slot_rect(seat_w / 2, seat_z + THICKNESS / 2, tab_w, vertical=False)
    parts.append(Part("back_panel", back_outline, [back_slot]))

    return parts


def main():
    parts = build_chair()
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=10)
    print(f"[stuhl] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm sheet, "
          f".lbrn2 {size/1024:.1f} KB, preview {px[0]}×{px[1]}")


if __name__ == "__main__":
    main()
