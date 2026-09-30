"""08: Bücherregal (bookshelf, 1:12).

Real: ~80×30×180 cm → 1:12 → 67×25×150 mm.
Geschlossene Box mit Rückwand + 3 internen Einlegeböden. Front offen.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import make_finger_box, layout_grid, write_lbrn2, render_preview

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "08_buecherregal.lbrn2"
PREVIEW = OUT_DIR / "previews" / "08_buecherregal.png"


def main():
    parts = make_finger_box(W=67.0, D=25.0, H=150.0,
                            n_tabs_W=2, n_tabs_D=2, n_tabs_H=4,
                            n_shelves=3)
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=5)
    print(f"[regal] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
