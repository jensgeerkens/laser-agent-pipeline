"""boxes.py bridge: make boxes.py's generators usable in our pipeline.

Public API:
    make_from_boxes(generator, **params) -> list[Part]
    list_boxes_generators(filter=None) -> list[str]

Why this exists:
    boxes.py is excellent at finger-jointed boxes, hinges, drawers, gears.
    Its output is SVG, while this pipeline works on Part objects.
    This bridge runs the generator headless, parses the SVG, returns Parts that
    plug right into lib.py (layout_grid, write_lbrn2, simulate_assembly).
"""
import os
import re
import shutil
import subprocess
import sysconfig
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from svgpathtools import svg2paths

from lib import Part

SVG_NS = "{http://www.w3.org/2000/svg}"


def find_boxes_executable() -> Optional[Path]:
    """Locate the boxes.py CLI without hard-coded user paths.

    Order: BOXES_EXE environment variable, PATH, the scripts directories of
    the running interpreter (system and user scheme)."""
    env = os.environ.get("BOXES_EXE")
    if env and Path(env).exists():
        return Path(env)
    found = shutil.which("boxes")
    if found:
        return Path(found)
    names = ("boxes.exe", "boxes") if os.name == "nt" else ("boxes",)
    schemes = [None, f"{os.name}_user"]
    for scheme in schemes:
        try:
            scripts = sysconfig.get_path("scripts", scheme) if scheme else sysconfig.get_path("scripts")
        except KeyError:
            continue
        for n in names:
            cand = Path(scripts) / n
            if cand.exists():
                return cand
    return None


# ============================================================================
# Public API
# ============================================================================
def make_from_boxes(generator: str, output_dir: Optional[Path] = None,
                    bezier_segments: int = 8, **params) -> List[Part]:
    """Run a boxes.py generator and return its output as our Part objects.

    Args:
        generator: e.g. "ABox", "BasicBox", "Drawer", "Hinge", "Gears"
        output_dir: where to keep the SVG (default: temp dir, cleaned up)
        bezier_segments: how many line-segments to approximate a Bezier curve with
        **params: generator-specific (e.g. width=100, height=80, depth=50)

    Returns:
        list[Part], each <path> in the SVG becomes one Part.
        SVG is Y-DOWN so we flip to Y-UP for lib.py compatibility.
    """
    exe = find_boxes_executable()
    if exe is None:
        raise RuntimeError("boxes.py CLI not found. Install boxes.py or set BOXES_EXE.")
    keep = output_dir is not None
    svg_path = (output_dir / f"{generator}.svg") if keep else Path(
        tempfile.NamedTemporaryFile(suffix=".svg", delete=False).name)
    try:
        cmd = [str(exe), generator,
               "--format=svg", "--labels=False", "--reference=0",
               f"--output={svg_path}"]
        for k, v in params.items():
            cmd.append(f"--{k}={v}")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"boxes.py exit {r.returncode}: {r.stderr.strip()}")
        if not svg_path.exists():
            raise RuntimeError(f"boxes.py produced no output at {svg_path}")
        return _parse_svg(svg_path, generator, bezier_segments)
    finally:
        if not keep and svg_path.exists():
            svg_path.unlink()


def list_boxes_generators(filter_substring: str = None) -> List[str]:
    """List all available boxes.py generators (optionally filtered by substring)."""
    import boxes.generators as G
    import pkgutil
    names = sorted(m.name for m in pkgutil.iter_modules(G.__path__)
                   if not m.name.startswith("_"))
    # Capitalize first letter to match class names
    names = [n[0].upper() + n[1:] for n in names]
    if filter_substring:
        s = filter_substring.lower()
        names = [n for n in names if s in n.lower()]
    return names


def boxes_help(generator: str) -> str:
    """Print parameter list for a boxes.py generator (for discovering options)."""
    exe = find_boxes_executable()
    if exe is None:
        raise RuntimeError("boxes.py CLI not found. Install boxes.py or set BOXES_EXE.")
    r = subprocess.run([str(exe), generator, "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout


# ============================================================================
# SVG → Part parsing
# ============================================================================
def _parse_svg(svg_path: Path, name_prefix: str, bezier_segments: int) -> List[Part]:
    """Extract polygons from an SVG file as Part objects.

    Strategy:
    - svgpathtools handles all M/L/C/Z and gives us segments
    - Sample bezier curves to polyline points
    - Each <path> in the SVG becomes one Part (boxes.py convention)
    - Coordinate system: SVG Y-DOWN → flip to Y-UP for our lib
    - Holes detection: paths fully contained inside another path become holes
    """
    # Need viewBox/height for Y-flip
    tree = ET.parse(svg_path)
    root = tree.getroot()
    height_attr = root.get("height", "1000")
    height = float(re.match(r"[-+]?\d*\.?\d+", height_attr).group(0))

    paths, attributes = svg2paths(str(svg_path))
    outlines = []
    for path in paths:
        if len(path) == 0:
            continue
        pts = _sample_path(path, bezier_segments)
        if len(pts) < 3:
            continue
        # Y-flip (SVG Y-DOWN → lib Y-UP)
        pts = [(x, height - y) for x, y in pts]
        # De-dup consecutive identical points
        clean = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - clean[-1][0]) > 0.001 or abs(p[1] - clean[-1][1]) > 0.001:
                clean.append(p)
        if len(clean) < 3:
            continue
        outlines.append(clean)

    # Determine which outlines are HOLES (fully inside another outline)
    parts = []
    used_as_hole = set()
    for i, outer in enumerate(outlines):
        if i in used_as_hole:
            continue
        holes = []
        for j, inner in enumerate(outlines):
            if i == j or j in used_as_hole:
                continue
            if _polygon_contains(outer, inner):
                holes.append(inner)
                used_as_hole.add(j)
        parts.append(Part(f"{name_prefix}_{len(parts)+1}", outer, holes))
    return parts


def _sample_path(path, bezier_segments: int) -> List[tuple]:
    """Approximate an svgpathtools Path as a list of (x, y) points."""
    pts = []
    for seg in path:
        # Always start with the start point
        if not pts or pts[-1] != (seg.start.real, seg.start.imag):
            pts.append((seg.start.real, seg.start.imag))
        # If it's a curve, sample intermediate points
        seg_class = type(seg).__name__
        if seg_class in ("CubicBezier", "QuadraticBezier", "Arc"):
            for k in range(1, bezier_segments):
                t = k / bezier_segments
                p = seg.point(t)
                pts.append((p.real, p.imag))
        pts.append((seg.end.real, seg.end.imag))
    return pts


def _polygon_contains(outer: List[tuple], inner: List[tuple]) -> bool:
    """Check if `inner` is fully inside `outer` (simple bbox + 1-point-in-polygon test)."""
    ox = [p[0] for p in outer]
    oy = [p[1] for p in outer]
    ix = [p[0] for p in inner]
    iy = [p[1] for p in inner]
    if min(ix) < min(ox) or max(ix) > max(ox):
        return False
    if min(iy) < min(oy) or max(iy) > max(oy):
        return False
    # Point-in-polygon test for the centroid of inner
    cx = sum(ix) / len(ix)
    cy = sum(iy) / len(iy)
    return _point_in_polygon(cx, cy, outer)


def _point_in_polygon(x, y, poly) -> bool:
    """Ray-casting test: returns True if (x,y) is inside `poly`."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside
