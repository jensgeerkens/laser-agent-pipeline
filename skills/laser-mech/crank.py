"""
Generate a laser-cuttable hand crank for shaft-driven projects (e.g. a boxes.py GearBox).

Output is a single .lbrn2 with:
- 1 main arm (stadium shape with hole at each end)
- N grip discs (stacked on a dowel to form the finger-roll knob)
- Optionally a flat end cap to retain the disc stack

The user supplies:
- a wooden dowel (same diameter as --shaft) to act as the gear shaft
- a shorter dowel (same diameter as --pin) for the grip stack
"""
import argparse
import math
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon, MultiPolygon
from shapely import affinity


LBRN_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<LightBurnProject AppVersion="2.0.05" FormatVersion="1" MaterialHeight="0" MirrorX="False" MirrorY="False">
    <Thumbnail Source=""/>
    <VariableText/>
    <UIPrefs/>
    <CutSetting type="Cut">
        <index Value="0"/>
        <name Value="C00 Cut"/>
        <minPower Value="90"/>
        <maxPower Value="90"/>
        <minPower2 Value="90"/>
        <maxPower2 Value="90"/>
        <speed Value="8"/>
        <numPasses Value="2"/>
        <doOutput Value="1"/>
        <priority Value="0"/>
    </CutSetting>
"""
LBRN_FOOTER = "</LightBurnProject>\n"


def polygon_to_lbrn_paths(poly):
    """Convert a shapely Polygon (exterior + interiors) into LightBurn <Shape Type="Path">
    XML strings, one per ring."""
    out = []
    rings = [poly.exterior] + list(poly.interiors)
    for ring in rings:
        pts = list(ring.coords)
        if len(pts) < 3:
            continue
        if pts[-1] == pts[0]:
            pts = pts[:-1]
        n = len(pts)
        verts = "".join(f"V{x:.3f} {y:.3f}c0x1L" for x, y in pts)
        prims = "".join(f"LineL{i} {(i + 1) % n}" for i in range(n))
        out.append(
            f'    <Shape Type="Path" CutIndex="0">\n'
            f'        <XForm>1 0 0 1 0 0</XForm>\n'
            f'        <VertList>{verts}</VertList>\n'
            f'        <PrimList>{prims}</PrimList>\n'
            f'    </Shape>\n')
    return out


def build_arm(arm_length, arm_width, drive_hole_r, pin_hole_r, resolution=48):
    """Stadium-shape arm with a hole at each end. Center of drive hole at (0, 0),
    center of pin hole at (arm_length, 0)."""
    arm = LineString([(0, 0), (arm_length, 0)]).buffer(
        arm_width / 2, cap_style=1, resolution=resolution)
    h1 = Point(0, 0).buffer(drive_hole_r, resolution=resolution)
    h2 = Point(arm_length, 0).buffer(pin_hole_r, resolution=resolution)
    arm = arm.difference(h1).difference(h2)
    if isinstance(arm, MultiPolygon):
        arm = max(arm.geoms, key=lambda g: g.area)
    return arm


def build_disc(radius, hole_r, center=(0, 0), resolution=48):
    cx, cy = center
    disc = Point(cx, cy).buffer(radius, resolution=resolution)
    hole = Point(cx, cy).buffer(hole_r, resolution=resolution)
    out = disc.difference(hole)
    if isinstance(out, MultiPolygon):
        out = max(out.geoms, key=lambda g: g.area)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shaft", type=float, default=6.0,
                   help="Gear-shaft diameter (mm). Drive hole = shaft + slack.")
    p.add_argument("--pin", type=float, default=None,
                   help="Grip-pin diameter (mm). Default = same as shaft.")
    p.add_argument("--arm-length", type=float, default=60.0,
                   help="Distance from drive-hole center to pin-hole center (mm).")
    p.add_argument("--arm-width", type=float, default=18.0,
                   help="Arm width (mm), also determines end-cap radius.")
    p.add_argument("--grip-diam", type=float, default=25.0,
                   help="Grip-disc outer diameter (mm).")
    p.add_argument("--grip-count", type=int, default=4,
                   help="Number of grip discs to stack (default 4 = ~16mm thick grip).")
    p.add_argument("--slack", type=float, default=0.15,
                   help="Extra clearance for shaft/pin holes (mm). Adjust for fit.")
    p.add_argument("--thickness", type=float, default=4.0,
                   help="Material thickness (info only, for layout sizing).")
    p.add_argument("--output", type=Path,
                   default=Path("crank.lbrn2"))
    args = p.parse_args()

    pin = args.pin if args.pin is not None else args.shaft
    drive_hole_r = (args.shaft + args.slack) / 2
    pin_hole_r = (pin + args.slack) / 2

    print(f"Shaft hole: dia {args.shaft + args.slack:.2f} mm (radius {drive_hole_r:.2f})")
    print(f"Pin hole:   dia {pin + args.slack:.2f} mm (radius {pin_hole_r:.2f})")
    print(f"Arm: {args.arm_length} mm center-to-center, {args.arm_width} mm wide")
    print(f"Grip discs: {args.grip_count} × {args.grip_diam} mm  "
          f"(stacked thickness ~{args.grip_count * args.thickness:.0f} mm)")

    # Build pieces
    arm = build_arm(args.arm_length, args.arm_width, drive_hole_r, pin_hole_r)

    # Layout: arm at top, discs in a row below
    padding = 8.0
    arm_minx, arm_miny, arm_maxx, arm_maxy = arm.bounds
    arm = affinity.translate(arm, -arm_minx + padding, -arm_miny + padding)
    arm_height = arm_maxy - arm_miny
    arm_width_total = arm_maxx - arm_minx

    pieces = [arm]
    disc_y = padding + arm_height + padding
    cur_x = padding
    for i in range(args.grip_count):
        disc = build_disc(args.grip_diam / 2, pin_hole_r,
                          center=(cur_x + args.grip_diam / 2, disc_y + args.grip_diam / 2))
        pieces.append(disc)
        cur_x += args.grip_diam + padding

    # Compute overall layout size for sanity
    total_w = max(arm_width_total, cur_x)
    total_h = disc_y + args.grip_diam + padding
    print(f"\nLayout: {total_w + 2*padding:.0f} x {total_h:.0f} mm")

    # Write .lbrn2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    parts = [LBRN_HEADER]
    for piece in pieces:
        parts.extend(polygon_to_lbrn_paths(piece))
    parts.append(LBRN_FOOTER)
    args.output.write_text("".join(parts), encoding="utf-8")
    print(f"\nWrote {args.output} ({args.output.stat().st_size/1024:.1f} KB)")
    print("\nAssembly:")
    print(f"  - Cut all pieces from {args.thickness} mm plywood.")
    print(f"  - Slip arm onto gear shaft (drive hole, hole-diameter {args.shaft + args.slack:.2f} mm).")
    print(f"  - Stack {args.grip_count} discs on a {pin:.0f} mm dowel, press into the arm's pin hole.")
    print(f"  - Friction-fit or glue both ends. Add a small end-cap if discs slip off.")


if __name__ == "__main__":
    main()
