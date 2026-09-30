"""05: Kleiderschrank (wardrobe, 1:12).

Real: ~60×50×200 cm → 1:12 → 50×42×167 mm.
Box-Konstruktion mit 1 Tür (separat) und 1 Innenboden auf halber Höhe.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import make_finger_box, layout_grid, write_lbrn2, render_preview

OUT_DIR = Path(__file__).parent
LBRN2 = OUT_DIR / "output" / "05_kleiderschrank.lbrn2"
PREVIEW = OUT_DIR / "previews" / "05_kleiderschrank.png"


def main():
    parts = make_finger_box(W=50.0, D=42.0, H=167.0,
                            n_tabs_W=3, n_tabs_D=2, n_tabs_H=5,
                            n_shelves=1,            # 1 innenliegender Einlegeboden
                            door_inset=1.0)         # Tür separat, 1 mm rundum kleiner
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=5)
    size = write_lbrn2(parts, LBRN2)
    px = render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=4)
    print(f"[schrank] {len(parts)} parts on {sheet_w:.0f}×{sheet_h:.0f} mm, "
          f".lbrn2 {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
