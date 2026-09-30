"""Shared helpers for the dollhouse furniture collection.

Convention:
- LightBurn Y-up coordinate system.
- All dimensions in mm.
- Material settings (thickness, kerf, machine speeds) loaded from the file
  named in the LASER_CALIBRATION environment variable, else from
  ~/.laser/calibration.json. Falls back to sensible defaults if missing.
  See calibration.example.json in the repository root for the format.
- Kerf compensation: laser burns ~0.15 mm wide, so SLOT_W = THICKNESS - KERF
  for press-fit joints.
"""
import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw


# ============================================================================
# Calibration loading
# ============================================================================
def _calibration_file() -> Path:
    env = os.environ.get("LASER_CALIBRATION")
    if env:
        return Path(env)
    return Path.home() / ".laser" / "calibration.json"


CALIBRATION_FILE = _calibration_file()

_DEFAULTS = {
    "name": "Default (3mm plywood)",
    "thickness": 3.0,
    "kerf": 0.15,
    "settings": {
        "cut": {"speed_mm_s": 10, "power_pct": 85, "passes": 2},
        "engrave_score": {"speed_mm_s": 100, "power_pct": 35, "passes": 1},
        "engrave_image": {"speed_mm_s": 250, "power_pct": 30, "passes": 1, "dither": "jarvis"},
    },
}


def load_active_material() -> dict:
    """Load the currently-active material's settings from calibration JSON.
    Falls back to defaults if file missing or malformed."""
    if not CALIBRATION_FILE.exists():
        return _DEFAULTS
    try:
        cfg = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        machine = cfg.get("active_machine") or next(iter(cfg["machines"]))
        m = cfg["machines"][machine]
        material = m.get("active_material") or next(iter(m["materials"]))
        return m["materials"][material]
    except (KeyError, json.JSONDecodeError, StopIteration, OSError):
        return _DEFAULTS


_MAT = load_active_material()
THICKNESS = float(_MAT["thickness"])
KERF = float(_MAT["kerf"])
SLOT_W = THICKNESS - KERF
MATERIAL_NAME = _MAT.get("name", "unknown")
MATERIAL_SETTINGS = _MAT.get("settings", _DEFAULTS["settings"])


# ============================================================================
# Shape generators
# ============================================================================
def rect(x, y, w, h):
    """Rectangle as 4 corner points (CCW), Y-UP."""
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def rect_centered(cx, cy, w, h):
    """Rectangle centered at (cx, cy)."""
    return rect(cx - w/2, cy - h/2, w, h)


def slot_rect(cx, cy, length, width=SLOT_W, vertical=False):
    """A slot (internal hole) as a rectangle polygon.
    `length` = long dimension of the slot, `width` = perpendicular dimension.
    If vertical=True, slot is oriented vertically.
    """
    if vertical:
        return rect_centered(cx, cy, width, length)
    return rect_centered(cx, cy, length, width)


def fillet_corners(pts, r, steps=6):
    """Round all corners of a polygon (each vertex becomes a small arc)."""
    if r <= 0 or len(pts) < 3:
        return pts
    out = []
    n = len(pts)
    for i in range(n):
        p_prev = pts[(i - 1) % n]
        p = pts[i]
        p_next = pts[(i + 1) % n]
        v1 = (p_prev[0] - p[0], p_prev[1] - p[1])
        v2 = (p_next[0] - p[0], p_next[1] - p[1])
        d1 = math.hypot(*v1)
        d2 = math.hypot(*v2)
        if d1 == 0 or d2 == 0:
            out.append(p)
            continue
        # cap r at half each edge
        rr = min(r, d1 / 2, d2 / 2)
        # arc start = on edge toward p_prev, distance rr from p
        a_start = (p[0] + v1[0] * rr / d1, p[1] + v1[1] * rr / d1)
        a_end = (p[0] + v2[0] * rr / d2, p[1] + v2[1] * rr / d2)
        # Angle interpolation around p (approximate fillet)
        # For simplicity use linear interpolation between a_start and a_end
        # through a point pulled toward p (creates a rounded look)
        for s in range(steps + 1):
            t = s / steps
            # quadratic bezier with control point at p
            u = 1 - t
            x = u * u * a_start[0] + 2 * u * t * p[0] + t * t * a_end[0]
            y = u * u * a_start[1] + 2 * u * t * p[1] + t * t * a_end[1]
            out.append((x, y))
    return out


# ============================================================================
# Part = polygon outline + list of interior holes (slots/cutouts)
# Optional: AssemblyPosition for 3D placement (used by simulator)
# ============================================================================
class Part:
    def __init__(self, name, outline, holes=None, assembly=None):
        self.name = name
        self.outline = outline             # list of (x, y) points (CCW), 2D local
        self.holes = list(holes or [])     # list of polygons (interior cuts)
        self.assembly = assembly           # Optional[AssemblyPosition] for 3D sim

    def bbox(self):
        xs = [p[0] for p in self.outline]
        ys = [p[1] for p in self.outline]
        return (min(xs), min(ys), max(xs), max(ys))

    def translate(self, dx, dy):
        self.outline = [(x + dx, y + dy) for x, y in self.outline]
        self.holes = [[(x + dx, y + dy) for x, y in h] for h in self.holes]
        return self


# ============================================================================
# 3D Assembly model, input for the simulator
# ============================================================================
@dataclass
class AssemblyPosition:
    """3D placement of a Part in the assembled object.

    The Part's 2D outline is mapped to 3D based on `plane`:
      - "XY":  horizontal plate. 2D (lx,ly) → 3D (pos.x+lx, pos.y+ly, pos.z).
               Part thickness extends in +Z direction.
      - "XZ":  vertical wall facing ±Y. 2D (lx,ly) → 3D (pos.x+lx, pos.y, pos.z+ly).
               Part thickness extends in +Y direction.
      - "YZ":  vertical wall facing ±X. 2D (lx,ly) → 3D (pos.x, pos.y+lx, pos.z+ly).
               Part thickness extends in +X direction.
    """
    pos: Tuple[float, float, float]  # 3D origin of part's local (0,0)
    plane: str = "XY"                # one of "XY", "XZ", "YZ"
    rotation_deg: float = 0.0        # rotation within the plane (around plane normal)


@dataclass
class Joint:
    """Explicit record of a tab-slot connection between two parts.

    Used by simulate_assembly() to whitelist expected overlaps.
    """
    part_a: str                       # name of first part (typically tab-owner)
    part_b: str                       # name of second part (typically slot-owner)
    joint_type: str = "tab-slot"      # "tab-slot" | "finger-joint" | "cross-lap" | "through-tenon"
    tab_w: float = 0.0                # tab width along the joint axis
    tab_l: float = 0.0                # tab length (penetration depth, usually = material thickness)
    note: str = ""                    # optional human description


@dataclass
class Issue:
    """A simulator finding, error or warning."""
    severity: str                     # "ERROR" or "WARNING"
    code: str                         # short identifier (COLLISION, NO_POSITION, ...)
    message: str
    parts: List[str] = field(default_factory=list)


def part_3d_bbox(part: Part, pos: AssemblyPosition,
                 thickness: float = None) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Compute axis-aligned 3D bounding box of a part in its assembled position."""
    t = thickness if thickness is not None else THICKNESS
    xs = [p[0] for p in part.outline]
    ys = [p[1] for p in part.outline]
    lo_x, hi_x = min(xs), max(xs)
    lo_y, hi_y = min(ys), max(ys)
    px, py, pz = pos.pos
    if pos.plane == "XY":
        return ((px + lo_x, py + lo_y, pz), (px + hi_x, py + hi_y, pz + t))
    elif pos.plane == "XZ":
        return ((px + lo_x, py, pz + lo_y), (px + hi_x, py + t, pz + hi_y))
    elif pos.plane == "YZ":
        return ((px, py + lo_x, pz + lo_y), (px + t, py + hi_x, pz + hi_y))
    else:
        raise ValueError(f"Unknown plane: {pos.plane}")


def _aabb_overlap_volume(bb1, bb2) -> float:
    """Volume of intersection of two 3D AABBs. 0 if disjoint."""
    vol = 1.0
    for axis in range(3):
        lo = max(bb1[0][axis], bb2[0][axis])
        hi = min(bb1[1][axis], bb2[1][axis])
        if hi <= lo:
            return 0.0
        vol *= (hi - lo)
    return vol


def _aabb_volume(bb) -> float:
    return ((bb[1][0] - bb[0][0]) * (bb[1][1] - bb[0][1]) * (bb[1][2] - bb[0][2]))


# ============================================================================
# Assembly simulator (implemented checks: AABB collision, joint contact,
# joint overlap ratio). Assembly order and pass-through checks: see README roadmap.
# ============================================================================
def simulate_assembly(parts: List[Part],
                      positions: Optional[dict] = None,
                      joints: Optional[List[Joint]] = None,
                      thickness: float = None,
                      verbose: bool = False) -> List[Issue]:
    """Verify physical assembleability of a parts list.

    Args:
        parts:     list of Part objects
        positions: dict mapping part_name → AssemblyPosition. If None, uses each
                   Part's `.assembly` field if set.
        joints:    list of Joint records declaring expected connections.
                   Overlaps between joined parts are expected (tab in slot).
                   Overlaps between un-joined parts are reported as COLLISION.
        thickness: material thickness (default: module THICKNESS)
        verbose:   if True, print progress

    Returns:
        list of Issue objects. Empty list = PASS.
    """
    t = thickness if thickness is not None else THICKNESS
    joints = joints or []
    issues: List[Issue] = []

    # Resolve positions: prefer explicit positions dict, fall back to part.assembly
    pos_map = dict(positions or {})
    for p in parts:
        if p.name not in pos_map and p.assembly is not None:
            pos_map[p.name] = p.assembly

    # Build whitelist of expected overlap pairs from joints
    joint_pairs = set()
    for j in joints:
        joint_pairs.add(tuple(sorted([j.part_a, j.part_b])))

    # Compute 3D bbox per part
    bboxes = {}
    for p in parts:
        if p.name not in pos_map:
            issues.append(Issue(
                "WARNING", "NO_POSITION",
                f"Part '{p.name}' has no AssemblyPosition, cannot 3D-verify.",
                [p.name]))
            continue
        try:
            bboxes[p.name] = part_3d_bbox(p, pos_map[p.name], t)
        except ValueError as e:
            issues.append(Issue(
                "ERROR", "BAD_POSITION",
                f"Part '{p.name}': {e}", [p.name]))
            continue

    # Pairwise overlap check
    names = list(bboxes.keys())
    for i in range(len(names)):
        for k in range(i + 1, len(names)):
            a, b = names[i], names[k]
            vol = _aabb_overlap_volume(bboxes[a], bboxes[b])
            if vol <= 0.001:
                continue
            pair = tuple(sorted([a, b]))
            if pair in joint_pairs:
                # Expected overlap (tab-in-slot). Warn if implausibly large.
                a_vol = _aabb_volume(bboxes[a])
                b_vol = _aabb_volume(bboxes[b])
                ratio = vol / min(a_vol, b_vol)
                if ratio > 0.25:
                    issues.append(Issue(
                        "WARNING", "EXCESSIVE_JOINT_OVERLAP",
                        f"Joint {a}<->{b}: overlap {vol:.0f} mm³ is {ratio*100:.0f}% of smaller part; "
                        f"check that joint dims are correct.",
                        [a, b]))
                elif verbose:
                    issues.append(Issue(
                        "WARNING", "JOINT_OK",
                        f"Joint {a}<->{b}: {vol:.1f} mm³ overlap as expected.",
                        [a, b]))
            else:
                # Unexpected overlap = collision
                issues.append(Issue(
                    "ERROR", "COLLISION",
                    f"Parts '{a}' and '{b}' overlap by {vol:.1f} mm³ "
                    f"but no Joint declared between them.",
                    [a, b]))

    # Verify each declared joint actually shows up as overlap (else joint is wrong)
    for j in joints:
        if j.part_a not in bboxes or j.part_b not in bboxes:
            continue
        if _aabb_overlap_volume(bboxes[j.part_a], bboxes[j.part_b]) <= 0.001:
            issues.append(Issue(
                "ERROR", "JOINT_NO_CONTACT",
                f"Joint declared between '{j.part_a}' and '{j.part_b}' but their 3D bboxes "
                f"don't actually overlap. Check positions.",
                [j.part_a, j.part_b]))

    return issues


def print_simulation_report(issues: List[Issue]) -> bool:
    """Pretty-print issues. Returns True if PASS (no ERRORs)."""
    errors = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING" and i.code != "JOINT_OK"]
    notes = [i for i in issues if i.code == "JOINT_OK"]
    if not errors and not warnings:
        print(f"PASS - All checks succeeded ({len(notes)} joints verified)")
        for i in notes:
            print(f"  ok [{i.code}] {i.message}")
        return True
    if errors:
        print(f"FAIL - {len(errors)} error(s), {len(warnings)} warning(s)")
    else:
        print(f"PASS WITH WARNINGS - {len(warnings)} warning(s)")
    for i in errors:
        print(f"  X [{i.code}] {i.message}")
    for i in warnings:
        print(f"  ! [{i.code}] {i.message}")
    return len(errors) == 0


# ============================================================================
# Finger-jointed box generator: single source of truth for box furniture
# ============================================================================
# Joinery convention (avoids the tab-vs-tab collision bug):
#   - SIDE panels carry ALL the tabs (on top, bottom, back edges)
#   - TOP / BOTTOM panels carry only SLOTS (left, right, back)
#   - BACK panel carries tabs on top+bottom (mating top/bottom back-slots)
#                  and INTERIOR slots on left+right (mating side back-tabs)
#   - SHELVES carry tabs on left+right, mating INTERIOR slots in the sides
# Result: every joint has exactly one tab-bearing piece and one slot-bearing
# piece, no two tabs ever try to occupy the same volume.
# ============================================================================
def make_finger_box(W, D, H,
                    n_tabs_W=3, n_tabs_D=2, n_tabs_H=4,
                    n_shelves=0,
                    has_back=True,
                    has_top=True,
                    door_inset=None,
                    front_panel=False,
                    tab_l=10.0,
                    thickness=THICKNESS):
    """Generate the parts list for a finger-jointed rectangular box.

    Args:
      W, D, H: outer width, depth, height (mm)
      n_tabs_W/D/H: number of finger-tabs along each axis
      n_shelves: internal horizontal shelves (with slot-mates cut in sides)
      has_back: include closed back panel
      has_top: include closed top panel (False for some shelves with open top)
      door_inset: if set, generate a flat door panel inset by this margin
      front_panel: if True, generate a flat front panel (no joinery, for
                   decorative engraving like drawer fronts on a dresser)

    Returns:
      list[Part], ready to layout & write
    """
    parts = []

    def edge_tabs(length, n):
        gap = (length - n * tab_l) / (n + 1)
        return [(gap + i * (tab_l + gap), gap + i * (tab_l + gap) + tab_l)
                for i in range(n)]

    tabs_W = edge_tabs(W, n_tabs_W)
    tabs_D = edge_tabs(D, n_tabs_D)
    tabs_H = edge_tabs(H, n_tabs_H) if has_back else []

    # Side panel (D × H): tabs on top (up), bottom (down), back (right)
    def side_panel_outline():
        pts = [(0, 0)]
        for s, e in tabs_D:
            pts += [(s, 0), (s, -thickness), (e, -thickness), (e, 0)]
        pts.append((D, 0))
        for s, e in tabs_H:
            pts += [(D, s), (D + thickness, s), (D + thickness, e), (D, e)]
        pts.append((D, H))
        if has_top:
            for s, e in reversed(tabs_D):
                pts += [(e, H), (e, H + thickness), (s, H + thickness), (s, H)]
        pts.append((0, H))
        pts.append((0, 0))
        return pts

    # Interior slots in sides for shelf tabs
    shelf_zs = [H * (i + 1) / (n_shelves + 1) for i in range(n_shelves)]
    side_shelf_slots = []
    for z in shelf_zs:
        for s, e in tabs_D:
            side_shelf_slots.append(slot_rect((s + e) / 2, z, e - s, vertical=False))

    side_outline = side_panel_outline()
    parts.append(Part("side_L", list(side_outline), [list(h) for h in side_shelf_slots]))
    parts.append(Part("side_R", list(side_outline), [list(h) for h in side_shelf_slots]))

    # Top/bottom panel (W × D): slots on L, R, back
    def horiz_panel(name):
        holes = []
        for s, e in tabs_D:
            holes.append(slot_rect(thickness / 2,     (s + e) / 2, e - s, vertical=True))
            holes.append(slot_rect(W - thickness / 2, (s + e) / 2, e - s, vertical=True))
        if has_back:
            for s, e in tabs_W:
                holes.append(slot_rect((s + e) / 2, D - thickness / 2, e - s, vertical=False))
        return Part(name, rect(0, 0, W, D), holes)

    if has_top:
        parts.append(horiz_panel("top"))
    parts.append(horiz_panel("bottom"))

    # Internal shelves (W × D): tabs on L (left) + R (right); NO back tabs.
    def shelf_panel(name):
        pts = [(0, 0), (W, 0)]
        for s, e in tabs_D:
            pts += [(W, s), (W + thickness, s), (W + thickness, e), (W, e)]
        pts.append((W, D))
        pts.append((0, D))
        for s, e in reversed(tabs_D):
            pts += [(0, e), (-thickness, e), (-thickness, s), (0, s)]
        pts.append((0, 0))
        return Part(name, pts, [])

    for i in range(n_shelves):
        parts.append(shelf_panel(f"shelf_{i+1}"))

    # Back panel (W × H): tabs on top + bottom; INTERIOR slots on L + R sides
    if has_back:
        def back_panel_outline():
            pts = [(0, 0)]
            for s, e in tabs_W:
                pts += [(s, 0), (s, -thickness), (e, -thickness), (e, 0)]
            pts.append((W, 0))
            pts.append((W, H))
            if has_top:
                for s, e in reversed(tabs_W):
                    pts += [(e, H), (e, H + thickness), (s, H + thickness), (s, H)]
            pts.append((0, H))
            return pts

        back_holes = []
        for s, e in tabs_H:
            back_holes.append(slot_rect(thickness / 2,     (s + e) / 2, e - s, vertical=True))
            back_holes.append(slot_rect(W - thickness / 2, (s + e) / 2, e - s, vertical=True))
        parts.append(Part("back", back_panel_outline(), back_holes))

    if door_inset is not None:
        dw = W - 2 * door_inset
        dh = H - 2 * door_inset
        parts.append(Part("door", rect(0, 0, dw, dh), []))

    if front_panel:
        parts.append(Part("front", rect(0, 0, W, H), []))

    return parts


# ============================================================================
# Sheet layout: pack parts onto a sheet with spacing
# ============================================================================
def layout_grid(parts, margin=5, gap=4):
    """Lay out parts left-to-right, wrapping rows as needed.
    Returns total (sheet_w, sheet_h) after layout.
    All parts mutated in place (translated to their grid position).
    """
    # Sort parts by height descending so taller parts share rows efficiently
    parts_sorted = sorted(parts, key=lambda p: -(p.bbox()[3] - p.bbox()[1]))
    cur_x = margin
    cur_y = margin
    row_h = 0
    max_x = margin
    # Use a simple shelf-packing approach with a generous max width
    MAX_W = 400  # plenty wide; will wrap when needed
    for p in parts_sorted:
        x0, y0, x1, y1 = p.bbox()
        w = x1 - x0; h = y1 - y0
        if cur_x + w + margin > MAX_W and cur_x > margin:
            # wrap to next row
            cur_y += row_h + gap
            cur_x = margin
            row_h = 0
        # translate part so its bbox lower-left lands at (cur_x, cur_y)
        p.translate(cur_x - x0, cur_y - y0)
        cur_x += w + gap
        if cur_x > max_x:
            max_x = cur_x
        if h > row_h:
            row_h = h
    sheet_w = max_x + margin - gap
    sheet_h = cur_y + row_h + margin
    return sheet_w, sheet_h


# ============================================================================
# LightBurn .lbrn2 output
# ============================================================================
def _cut_layer(index, name, speed, power, passes, priority):
    return f"""    <CutSetting type="Cut">
        <index Value="{index}"/>
        <name Value="{name}"/>
        <minPower Value="{power}"/>
        <maxPower Value="{power}"/>
        <minPower2 Value="{power}"/>
        <maxPower2 Value="{power}"/>
        <speed Value="{speed}"/>
        <numPasses Value="{passes}"/>
        <doOutput Value="1"/>
        <priority Value="{priority}"/>
    </CutSetting>
"""


def _shape_polygon(points, cut_index=0):
    n = len(points)
    verts = "".join(f"V{x:.3f} {y:.3f}c0x1c1x1L" for x, y in points)
    prims = "".join(f"LineL{i} {(i + 1) % n}" for i in range(n))
    return (f'    <Shape Type="Path" CutIndex="{cut_index}">\n'
            f'        <XForm>1 0 0 1 0 0</XForm>\n'
            f'        <VertList>{verts}</VertList>\n'
            f'        <PrimList>{prims}</PrimList>\n'
            f'    </Shape>\n')


def write_lbrn2(parts, out_path: Path, name="furniture",
                cut_speed=10, cut_power=85, passes=2,
                score_speed=120, score_power=35,
                engrave_shapes=None):
    """Write a .lbrn2 file with all part outlines + holes on the cut layer.
    `engrave_shapes` is optional list of (polygon, ...) for score layer.
    """
    shapes = []
    for p in parts:
        shapes.append(_shape_polygon(p.outline, cut_index=0))
        for h in p.holes:
            shapes.append(_shape_polygon(h, cut_index=0))
    if engrave_shapes:
        for poly in engrave_shapes:
            shapes.append(_shape_polygon(poly, cut_index=2))

    layers = (_cut_layer(0, "C00 Cut",   cut_speed, cut_power, passes, 0)
              + _cut_layer(2, "C02 Score", score_speed, score_power, 1, 2))

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<LightBurnProject AppVersion="2.0.05" FormatVersion="1" MaterialHeight="0" MirrorX="False" MirrorY="False">
    <Thumbnail Source=""/>
    <VariableText/>
    <UIPrefs/>
{layers}{"".join(shapes)}</LightBurnProject>
"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path.stat().st_size


# ============================================================================
# PIL preview renderer
# ============================================================================
def render_preview(parts, out_path: Path, sheet_w, sheet_h, dpi=10, bg="#f3e0b3",
                   engrave_shapes=None):
    W = int(sheet_w * dpi); H = int(sheet_h * dpi)
    pad = 20
    img = Image.new("RGB", (W + pad*2, H + pad*2), bg)
    draw = ImageDraw.Draw(img)
    def pt(x, y):
        # Y-up to PIL Y-down
        return (pad + int(x * dpi), pad + int((sheet_h - y) * dpi))
    for p in parts:
        # outline = filled tan wood color, dark border (cut line)
        draw.polygon([pt(x, y) for x, y in p.outline], fill="#dcb878",
                     outline="#3a2814", width=1)
        for h in p.holes:
            draw.polygon([pt(x, y) for x, y in h], fill=bg, outline="#3a2814", width=1)
    if engrave_shapes:
        for poly in engrave_shapes:
            draw.polygon([pt(x, y) for x, y in poly], fill="#7a5a3a", outline=None)
    img.save(out_path, "PNG")
    return img.size
