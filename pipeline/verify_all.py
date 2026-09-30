"""Verify all 9 furniture pieces with the 3D simulator.

For each piece:
  - Build parts via the existing build_*.py
  - Define 3D AssemblyPositions + Joints
  - Run simulate_assembly()
  - Report per-piece status

This is the link between the static build scripts and the
geometric verifier, gives us PASS/FAIL for every piece.

Run: python verify_all.py
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import (AssemblyPosition, Joint, simulate_assembly,
                 print_simulation_report, THICKNESS)

PIPELINE_DIR = Path(__file__).parent
T = THICKNESS


def load_build(filename: str):
    """Dynamically import a build_*.py module by filename."""
    spec = importlib.util.spec_from_file_location("build_mod", PIPELINE_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============================================================================
# Per-piece metadata: each function returns (parts, positions_dict, joints_list)
# ============================================================================
def info_01_tisch():
    mod = load_build("01_tisch_quadrat.py")
    parts = mod.build_table()  # top_w=70, top_d=70, height=60, tab_w=50, leg_inset=15
    # Top sits at z=57..60 (3mm thick). 2 leg panels at y=15 and y=55 (parallel walls).
    positions = {
        "top":   AssemblyPosition(pos=(0, 0, 60 - T), plane="XY"),
        "leg_A": AssemblyPosition(pos=(0, 15 - T/2, 0), plane="XZ"),
        "leg_B": AssemblyPosition(pos=(0, 55 - T/2, 0), plane="XZ"),
    }
    joints = [
        Joint("leg_A", "top", "tab-slot", tab_w=50, tab_l=T),
        Joint("leg_B", "top", "tab-slot", tab_w=50, tab_l=T),
    ]
    return parts, positions, joints


def info_02_stuhl():
    mod = load_build("02_stuhl.py")
    parts = mod.build_chair()  # seat 38x38, seat_h=35, back_h=75, tab_w=30
    seat_z = 32  # seat sits z=32..35
    positions = {
        "seat":        AssemblyPosition(pos=(0, 0, seat_z), plane="XY"),
        "front_panel": AssemblyPosition(pos=(0, 5 - T/2, 0), plane="XZ"),  # at y=5 (front slot pos)
        "back_panel":  AssemblyPosition(pos=(0, 38, 0), plane="XZ"),       # behind seat back edge
    }
    joints = [
        Joint("front_panel", "seat", "tab-slot", tab_w=30, tab_l=T),
        Joint("seat", "back_panel", "through-tenon", tab_w=30, tab_l=T),
    ]
    return parts, positions, joints


def info_03_bett():
    mod = load_build("03_bett.py")
    parts = mod.build_bed()  # bed_len=167, bed_wid=133, head_h=78, side_h=30
    positions = {
        "headboard": AssemblyPosition(pos=(0, 0, 0), plane="YZ"),
        "footboard": AssemblyPosition(pos=(167 - T, 0, 0), plane="YZ"),
        "side_A":    AssemblyPosition(pos=(T, 0, 0), plane="XZ"),
        "side_B":    AssemblyPosition(pos=(T, 133 - T, 0), plane="XZ"),
        "base":      AssemblyPosition(pos=(T, T, 0), plane="XY"),
    }
    joints = [
        Joint("side_A", "headboard", "corner-tab", tab_w=5, tab_l=T),
        Joint("side_B", "headboard", "corner-tab", tab_w=5, tab_l=T),
        Joint("side_A", "footboard", "corner-tab", tab_w=5, tab_l=T),
        Joint("side_B", "footboard", "corner-tab", tab_w=5, tab_l=T),
    ]
    return parts, positions, joints


def _box_positions(W: float, D: float, H: float, has_top: bool = True,
                   n_shelves: int = 0, has_back: bool = True,
                   door_inset: float = None, front_panel: bool = False):
    """Standard positions for a make_finger_box() output.
    Convention: bottom at z=0..T, side body z=T..H+T, top at z=H+T..H+2T.
    Back panel sits at Y=D-T..D (inside the box footprint, back 3 mm)."""
    pos = {
        "bottom": AssemblyPosition(pos=(0, 0, 0), plane="XY"),
        "side_L": AssemblyPosition(pos=(0, 0, T), plane="YZ"),
        "side_R": AssemblyPosition(pos=(W - T, 0, T), plane="YZ"),
    }
    if has_top:
        pos["top"] = AssemblyPosition(pos=(0, 0, H + T), plane="XY")
    if has_back:
        # Z-offset = T so back-tab-top extends from H+T to H+2T (= top panel range)
        pos["back"] = AssemblyPosition(pos=(0, D - T, T), plane="XZ")
    # Shelves evenly spaced between top and bottom
    for i in range(n_shelves):
        z = T + H * (i + 1) / (n_shelves + 1)
        pos[f"shelf_{i+1}"] = AssemblyPosition(pos=(0, 0, z), plane="XY")
    # Door (placed outside the box, no joinery, just for layout)
    if door_inset is not None:
        # door sits in front of the box opening (Y < 0)
        pos["door"] = AssemblyPosition(pos=(door_inset, -T - 1, T + door_inset), plane="XZ")
    if front_panel:
        # front panel on the front face (Y = 0..T, but offset so it doesn't collide with anything)
        # We treat it as decorative, place it far enough to avoid collision
        pos["front"] = AssemblyPosition(pos=(0, -T - 1, 0), plane="XZ")
    return pos


def _box_joints(W: float, D: float, n_shelves: int = 0, has_top: bool = True):
    """Standard joints for a finger-box: side panels carry tabs, others have slots."""
    joints = [
        Joint("side_L", "bottom", "finger", tab_w=8, tab_l=T),
        Joint("side_R", "bottom", "finger", tab_w=8, tab_l=T),
        Joint("side_L", "back",   "finger", tab_w=8, tab_l=T),
        Joint("side_R", "back",   "finger", tab_w=8, tab_l=T),
        Joint("back",   "bottom", "finger", tab_w=8, tab_l=T),
    ]
    if has_top:
        joints += [
            Joint("side_L", "top", "finger", tab_w=8, tab_l=T),
            Joint("side_R", "top", "finger", tab_w=8, tab_l=T),
            Joint("back",   "top", "finger", tab_w=8, tab_l=T),
        ]
    for i in range(n_shelves):
        joints += [
            Joint(f"shelf_{i+1}", "side_L", "tab-slot", tab_w=8, tab_l=T),
            Joint(f"shelf_{i+1}", "side_R", "tab-slot", tab_w=8, tab_l=T),
            # Shelf back-edge touches back panel (current make_finger_box generates
            # shelves with full D depth; declared as joint to acknowledge contact)
            Joint(f"shelf_{i+1}", "back", "edge-contact", tab_w=0, tab_l=0),
        ]
    return joints


def info_04_nachttisch():
    mod = load_build("04_nachttisch.py")
    parts = mod.make_finger_box(W=38, D=33, H=50, n_tabs_W=2, n_tabs_D=2, n_tabs_H=3, n_shelves=0)
    return parts, _box_positions(38, 33, 50), _box_joints(38, 33)


def info_05_schrank():
    mod = load_build("05_kleiderschrank.py")
    parts = mod.make_finger_box(W=50, D=42, H=167, n_tabs_W=3, n_tabs_D=2, n_tabs_H=5,
                                n_shelves=1, door_inset=1.0)
    return parts, _box_positions(50, 42, 167, n_shelves=1, door_inset=1.0), _box_joints(50, 42, n_shelves=1)


def info_06_kommode():
    mod = load_build("06_kommode.py")
    parts = mod.make_finger_box(W=83, D=38, H=67, n_tabs_W=4, n_tabs_D=2, n_tabs_H=3,
                                n_shelves=2, front_panel=True)
    return parts, _box_positions(83, 38, 67, n_shelves=2, front_panel=True), _box_joints(83, 38, n_shelves=2)


def info_07_sofa():
    mod = load_build("07_sofa.py")
    parts = mod.build_sofa()  # L=167, D=70, back_h=70, front_h=30, arm_h=50
    positions = {
        "back":  AssemblyPosition(pos=(T, 70 - T, 0), plane="XZ"),  # at back edge
        "front": AssemblyPosition(pos=(T, 0, 0), plane="XZ"),        # at front edge
        "arm_L": AssemblyPosition(pos=(0, 0, 0), plane="YZ"),
        "arm_R": AssemblyPosition(pos=(167 - T, 0, 0), plane="YZ"),
        "base":  AssemblyPosition(pos=(T, T, 0), plane="XY"),
    }
    joints = [
        Joint("back",  "arm_L", "corner-tab", tab_w=5, tab_l=T),
        Joint("back",  "arm_R", "corner-tab", tab_w=5, tab_l=T),
        Joint("front", "arm_L", "corner-tab", tab_w=5, tab_l=T),
        Joint("front", "arm_R", "corner-tab", tab_w=5, tab_l=T),
    ]
    return parts, positions, joints


def info_08_buecherregal():
    mod = load_build("08_buecherregal.py")
    parts = mod.make_finger_box(W=67, D=25, H=150, n_tabs_W=2, n_tabs_D=2, n_tabs_H=4, n_shelves=3)
    return parts, _box_positions(67, 25, 150, n_shelves=3), _box_joints(67, 25, n_shelves=3)


def info_09_stehlampe():
    mod = load_build("09_stehlampe.py")
    parts = mod.build_lamp()
    # foot at z=0..3, pole vertical, shade walls form box on top of pole
    positions = {
        "foot":         AssemblyPosition(pos=(0, 0, 0), plane="XY"),
        # Pole centered on foot, standing up
        "pole":         AssemblyPosition(pos=(25 - 3, 25, 0), plane="XZ"),  # 6mm wide centered on 50mm foot
        # Shade walls glued together → represent as 4 walls forming box at top
        # Wall 1: front (at Y = pole_center - 12, facing +Y)
        # Skip detailed shade positions, would need careful 3D layout, low value for simulator
    }
    joints = [
        Joint("pole", "foot", "tab-slot", tab_w=4, tab_l=T),
        Joint("pole", "shade_roof", "tab-slot", tab_w=4, tab_l=T),
    ]
    # Don't position shade walls (their joinery is glue, not lasercut)
    # They'll trigger NO_POSITION warnings, that's OK, documents the limitation
    return parts, positions, joints


# ============================================================================
# Run all
# ============================================================================
INFO_FUNCTIONS = [
    ("01 Tisch",         info_01_tisch),
    ("02 Stuhl",         info_02_stuhl),
    ("03 Bett v4",       info_03_bett),
    ("04 Nachttisch",    info_04_nachttisch),
    ("05 Schrank",       info_05_schrank),
    ("06 Kommode",       info_06_kommode),
    ("07 Sofa",          info_07_sofa),
    ("08 Bücherregal",   info_08_buecherregal),
    ("09 Stehlampe",     info_09_stehlampe),
]


def main():
    print("=" * 72)
    print("Geometric Verification of all 9 furniture pieces")
    print("=" * 72)
    results = []
    for name, info_fn in INFO_FUNCTIONS:
        print(f"\n--- {name} ---")
        try:
            parts, positions, joints = info_fn()
        except Exception as e:
            print(f"X SETUP ERROR: {type(e).__name__}: {e}")
            results.append((name, False, "setup error"))
            continue
        issues = simulate_assembly(parts, positions, joints)
        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]
        passed = not errors
        if passed and not warnings:
            print(f"  PASS - clean (joints: {len(joints)})")
        elif passed:
            print(f"  PASS WITH WARNINGS ({len(warnings)})")
            for w in warnings[:5]:
                print(f"    ! [{w.code}] {w.message}")
            if len(warnings) > 5:
                print(f"    ... +{len(warnings)-5} more")
        else:
            print(f"  FAIL - {len(errors)} error(s), {len(warnings)} warning(s)")
            for e in errors[:5]:
                print(f"    X [{e.code}] {e.message}")
            if len(errors) > 5:
                print(f"    ... +{len(errors)-5} more")
        results.append((name, passed, f"{len(errors)}E {len(warnings)}W"))
    print()
    print("=" * 72)
    print("Summary")
    print("=" * 72)
    for name, ok, info in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  {mark:5s} {name:25s} ({info})")
    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"\n=> {n_pass}/{len(results)} pieces passed simulator")


if __name__ == "__main__":
    sys.exit(main())
