"""04: Nachttisch (nightstand, 1:12).

Real: ~45×40×60 cm → 1:12 → 38×33×50 mm. Open-front box (drawer cubby visible).

Verwendet lib.make_finger_box(), alle Verbindungen sind sauber.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import make_finger_box, layout_grid, write_lbrn2, render_preview

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "04_nachttisch.lbrn2"
PREVIEW = OUT_DIR / "previews" / "04_nachttisch.png"


def main():
    parts = make_finger_box(W=38.0, D=33.0, H=50.0,
                            n_tabs_W=2, n_tabs_D=2, n_tabs_H=3,
                            n_shelves=0)
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=10)
    print(f"[nachttisch] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
