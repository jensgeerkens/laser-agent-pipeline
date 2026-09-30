"""Demo: boxes_bridge in action.
Generates a simple BasicBox via boxes.py, returns our Parts, lays out and renders.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib import layout_grid, write_lbrn2, render_preview
from boxes_bridge import make_from_boxes, list_boxes_generators

OUT = Path(__file__).parent
LBRN2 = OUT / "output" / "demo_boxes_basicbox.lbrn2"
PREVIEW = OUT / "previews" / "demo_boxes_basicbox.png"


def main():
    # 1. Discovery, what's available?
    box_gens = list_boxes_generators("box")
    print(f"=== boxes.py 'box' generators: {len(box_gens)} ===")
    for n in box_gens[:10]:
        print(f"  {n}")
    print()

    # 2. Generate a simple closed box: ClosedBox 80×50×40 mm
    print("=== Generating ClosedBox 80×50×40 mm ===")
    parts = make_from_boxes("ClosedBox", x=80, y=50, h=40, thickness=3.0)
    print(f"-> {len(parts)} Parts erzeugt:")
    for p in parts:
        x0, y0, x1, y1 = p.bbox()
        print(f"   {p.name:18s} bbox={x1-x0:.1f}×{y1-y0:.1f} mm  ({len(p.outline)} pts, {len(p.holes)} holes)")
    print()

    # 3. Through our normal pipeline (layout + lbrn2 + preview)
    sheet_w, sheet_h = layout_grid(parts, margin=5, gap=4)
    size = write_lbrn2(parts, LBRN2)
    render_preview(parts, PREVIEW, sheet_w, sheet_h, dpi=8)
    print(f"-> Sheet: {sheet_w:.0f}×{sheet_h:.0f} mm")
    print(f"-> {LBRN2.name}: {size/1024:.1f} KB")
    print(f"-> Preview: {PREVIEW.name}")


if __name__ == "__main__":
    main()
