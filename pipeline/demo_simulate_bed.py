"""Demo: Use lib.simulate_assembly() to verify Bett v4 is geometrically sound.

Loads the bed v4 design, attaches AssemblyPosition + Joint metadata,
runs the simulator, prints a verification report.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Dynamically import 03_bett.py (numeric prefix makes normal import awkward)
import importlib.util
spec = importlib.util.spec_from_file_location("bett_module", Path(__file__).parent / "03_bett.py")
bett_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bett_module)

from lib import (AssemblyPosition, Joint, simulate_assembly,
                 print_simulation_report, THICKNESS, KERF, MATERIAL_NAME)


def main():
    print(f"=== Bett v4, Assembly-Verifikation ===")
    print(f"Material: {MATERIAL_NAME}, THICKNESS={THICKNESS}, KERF={KERF}, SLOT_W={THICKNESS - KERF}")
    print()

    parts = bett_module.build_bed()
    print(f"Parts geladen: {[p.name for p in parts]}")
    print()

    # ==== 3D-Positionierung jeder Part im assembled Bett ====
    # Bed dimensions (from build_bed defaults): 167 long × 133 wide × 78 high (with headboard)
    bed_len, bed_wid = 167.0, 133.0
    positions = {
        # Headboard: vertical wall at the HEAD end (X=0..3), facing +X direction
        "headboard": AssemblyPosition(pos=(0.0, 0.0, 0.0), plane="YZ"),
        # Footboard: vertical wall at FOOT end (X=164..167), facing -X
        "footboard": AssemblyPosition(pos=(bed_len - THICKNESS, 0.0, 0.0), plane="YZ"),
        # Side rail A: vertical wall along FRONT side (Y=0..3)
        # In bed v4 the side rail's outline extends from x=-3 to x=inner_len+3
        # So we offset by THICKNESS to get tabs into the headboard area
        "side_A":    AssemblyPosition(pos=(THICKNESS, 0.0, 0.0), plane="XZ"),
        # Side rail B: BACK side (Y=130..133)
        "side_B":    AssemblyPosition(pos=(THICKNESS, bed_wid - THICKNESS, 0.0), plane="XZ"),
        # Base: horizontal platform INSIDE the wall frame (X=3..164, Y=3..130, Z=0..3)
        "base":      AssemblyPosition(pos=(THICKNESS, THICKNESS, 0.0), plane="XY"),
    }

    # ==== Joints: 4 corners, each with 2 tabs ====
    joints = [
        Joint("side_A", "headboard", "corner-tab", tab_w=5.0, tab_l=THICKNESS, note="2 tabs at z=5..10, z=17..22"),
        Joint("side_B", "headboard", "corner-tab", tab_w=5.0, tab_l=THICKNESS),
        Joint("side_A", "footboard", "corner-tab", tab_w=5.0, tab_l=THICKNESS),
        Joint("side_B", "footboard", "corner-tab", tab_w=5.0, tab_l=THICKNESS),
    ]
    print(f"Joints deklariert: {len(joints)} corner-tab joints")
    print()

    # ==== Simulator laufen lassen ====
    issues = simulate_assembly(parts, positions, joints, verbose=True)
    print(f"--- Simulator Report ---")
    passed = print_simulation_report(issues)
    print()
    print(f"=> {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
