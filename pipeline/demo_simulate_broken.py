"""Demo: Zeige dass der Simulator echte Bugs fängt.

3 absichtlich kaputte Designs:
  CASE 1: 2 Parts in derselben Position OHNE Joint -> COLLISION
  CASE 2: Joint deklariert, aber Parts berühren sich gar nicht -> JOINT_NO_CONTACT
  CASE 3: Part ohne AssemblyPosition -> NO_POSITION
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from lib import (Part, AssemblyPosition, Joint, simulate_assembly,
                 print_simulation_report, rect, THICKNESS)


def case_1_collision():
    print("\n=== CASE 1: Collision (2 Parts gleiche Position, kein Joint) ===")
    parts = [
        Part("plate_A", rect(0, 0, 50, 50), assembly=AssemblyPosition(pos=(0, 0, 0), plane="XY")),
        Part("plate_B", rect(0, 0, 50, 50), assembly=AssemblyPosition(pos=(10, 10, 0), plane="XY")),
    ]
    issues = simulate_assembly(parts)
    print_simulation_report(issues)


def case_2_no_contact():
    print("\n=== CASE 2: Joint deklariert aber Parts berühren sich nicht ===")
    parts = [
        Part("part_A", rect(0, 0, 20, 20), assembly=AssemblyPosition(pos=(0, 0, 0), plane="XY")),
        Part("part_B", rect(0, 0, 20, 20), assembly=AssemblyPosition(pos=(100, 100, 0), plane="XY")),
    ]
    joints = [Joint("part_A", "part_B", "tab-slot", tab_w=5, tab_l=THICKNESS)]
    issues = simulate_assembly(parts, joints=joints)
    print_simulation_report(issues)


def case_3_no_position():
    print("\n=== CASE 3: Part ohne AssemblyPosition (unverifizierbar) ===")
    parts = [
        Part("positioned", rect(0, 0, 30, 30), assembly=AssemblyPosition(pos=(0, 0, 0), plane="XY")),
        Part("loose",      rect(0, 0, 30, 30)),  # kein assembly
    ]
    issues = simulate_assembly(parts)
    print_simulation_report(issues)


def case_4_excessive_overlap():
    print("\n=== CASE 4: Joint deklariert, aber Overlap zu groß (falsche Maße?) ===")
    parts = [
        Part("box_A", rect(0, 0, 40, 40), assembly=AssemblyPosition(pos=(0, 0, 0), plane="XY")),
        Part("box_B", rect(0, 0, 40, 40), assembly=AssemblyPosition(pos=(5, 5, 0), plane="XY")),
    ]
    joints = [Joint("box_A", "box_B", "tab-slot", tab_w=5, tab_l=THICKNESS)]
    issues = simulate_assembly(parts, joints=joints)
    print_simulation_report(issues)


if __name__ == "__main__":
    case_1_collision()
    case_2_no_contact()
    case_3_no_position()
    case_4_excessive_overlap()
