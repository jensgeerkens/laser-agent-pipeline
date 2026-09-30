"""06: Kommode (chest of drawers, 1:12).

Real: ~100×45×80 cm → 1:12 → 83×38×67 mm.
Box mit 2 internen Trennwänden (= 3 Schubladen-Fächer) und einem flachen
Front-Panel mit gravierten Schubladen-Linien + Knöpfen.
"""
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import make_finger_box, layout_grid, write_lbrn2, render_preview

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "06_kommode.lbrn2"
PREVIEW = OUT_DIR / "previews" / "06_kommode.png"

W, D, H = 83.0, 38.0, 67.0


def main():
    parts = make_finger_box(W=W, D=D, H=H,
                            n_tabs_W=4, n_tabs_D=2, n_tabs_H=3,
                            n_shelves=2,            # 2 Trennwände = 3 Schubladen
                            front_panel=True)
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)

    # Engraves auf dem Front-Panel, nach Layout, weil Position erst dann bekannt ist
    front = next(p for p in parts if p.name == "front")
    x0, y0, x1, y1 = front.bbox()
    fw = x1 - x0; fh = y1 - y0
    engraves = []
    for frac in [1/3, 2/3]:
        y = y0 + fh * frac
        engraves.append([(x0 + 2, y - 0.3), (x1 - 2, y - 0.3),
                         (x1 - 2, y + 0.3), (x0 + 2, y + 0.3)])
    for i in range(3):
        cy = y0 + fh * (i + 0.5) / 3
        cx = x0 + fw / 2
        r = 1.5
        engraves.append([(cx + r * math.cos(2 * math.pi * k / 12),
                          cy + r * math.sin(2 * math.pi * k / 12)) for k in range(12)])

    size = write_lbrn2(parts, LBRN2, engrave_shapes=engraves)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=6, engrave_shapes=engraves)
    print(f"[kommode] {len(parts)} parts + {len(engraves)} engrave on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
