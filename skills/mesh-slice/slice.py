"""
mesh-slice: 3D mesh (STL/OBJ) to a slot-together plywood figure.

Pipeline:
- Load mesh, orient longest axis to X, scale to --length
- N cross-sections (ribs) + one longitudinal silhouette (spine)
- Morphological opening + mirror symmetry to clean each section
- Drop ribs that do not cross Z=0 or are too small
- Optional lateral fins: section at Y=+fin_y, left and right copy
- Half-lap slots: spine slotted from below, ribs slotted from above,
  slot width = material thickness + clearance
- Shelf layout, export as SVG, LightBurn .lbrn2 and preview PNG
"""
import argparse
from pathlib import Path
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, box
from shapely import affinity
import svgwrite


# =============================================================================
# Mesh loading + slicing
# =============================================================================

def load_and_orient(stl_path: Path, target_length_mm: float = 250.0) -> trimesh.Trimesh:
    mesh = trimesh.load(stl_path)
    if not isinstance(mesh, trimesh.Trimesh):
        mesh = trimesh.util.concatenate(tuple(g for g in mesh.geometry.values()))
    longest_axis = int(np.argmax(mesh.extents))
    if longest_axis == 1:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 0, 1]))
    elif longest_axis == 2:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
    mesh.apply_translation(-mesh.centroid)
    mesh.apply_scale(target_length_mm / mesh.extents[0])
    return mesh


def _section_polygons_anatomical(mesh, plane_origin, plane_normal, drop_axis: int):
    sec = mesh.section(plane_origin=plane_origin, plane_normal=plane_normal)
    if sec is None:
        return []
    keep_axes = [a for a in (0, 1, 2) if a != drop_axis]
    verts_2d = sec.vertices[:, keep_axes]
    path2d = trimesh.path.Path2D(entities=sec.entities, vertices=verts_2d, process=True)
    return list(path2d.polygons_full)


def clean_section(poly, opening_radius: float = 2.5):
    if poly is None or poly.is_empty:
        return None
    cleaned = poly.buffer(-opening_radius).buffer(opening_radius)
    if cleaned.is_empty or not cleaned.is_valid:
        cleaned = poly
    if isinstance(cleaned, MultiPolygon):
        cleaned = max(cleaned.geoms, key=lambda g: g.area)
    mirrored = affinity.scale(cleaned, xfact=-1, origin=(0, 0))
    sym = cleaned.union(mirrored).buffer(0.3).buffer(-0.3)
    if isinstance(sym, MultiPolygon):
        sym = max(sym.geoms, key=lambda g: g.area)
    return sym


def cross_sections(mesh, n_slices, margin_pct=10.0, opening_radius=2.5):
    x_min, x_max = mesh.bounds[0][0], mesh.bounds[1][0]
    margin = (x_max - x_min) * margin_pct / 100.0
    xs = np.linspace(x_min + margin, x_max - margin, n_slices)
    out = []
    for x in xs:
        polys = _section_polygons_anatomical(mesh, [x, 0, 0], [1, 0, 0], drop_axis=0)
        if not polys:
            continue
        largest = max(polys, key=lambda p: p.area)
        clean = clean_section(largest, opening_radius)
        if clean is None or clean.is_empty:
            continue
        out.append((float(x), clean))
    return out


def longitudinal_silhouette(mesh):
    polys = _section_polygons_anatomical(mesh, [0, 0, 0], [0, 1, 0], drop_axis=1)
    if not polys:
        return None
    sil = max(polys, key=lambda p: p.area).buffer(0.5).buffer(-0.5)
    if isinstance(sil, MultiPolygon):
        sil = max(sil.geoms, key=lambda g: g.area)
    return sil


def extract_lateral_fins(mesh, y_offset: float, min_area: float = 50,
                         opening_radius: float = 0.6):
    """Section the mesh at Y=+y_offset, project to XZ.
    Anything that lives there is by definition outside the body's half-width at that point.
    Returns a list of cleaned Polygons in XZ space."""
    polys = _section_polygons_anatomical(mesh, [0, y_offset, 0], [0, 1, 0], drop_axis=1)
    print(f"  [fins] Y={y_offset:+.1f} mm  raw polys: {len(polys)}, "
          f"largest area: {max((p.area for p in polys), default=0):.1f}")
    cleaned = []
    for p in polys:
        c = p.buffer(-opening_radius).buffer(opening_radius)
        if c.is_empty:
            continue
        geoms = c.geoms if isinstance(c, MultiPolygon) else [c]
        for g in geoms:
            if g.area >= min_area:
                cleaned.append(g.buffer(0.2).buffer(-0.2))  # light smoothing
    return cleaned


# =============================================================================
# Filtering bad ribs
# =============================================================================

def filter_ribs(ribs, min_area=100, min_width=5):
    kept = []
    dropped = []
    for x_pos, rib in ribs:
        minx, miny, maxx, maxy = rib.bounds
        reasons = []
        if miny >= -0.5: reasons.append("ventral-clear-of-z0")
        if maxy <= 0.5:  reasons.append("dorsal-clear-of-z0")
        if rib.area < min_area: reasons.append(f"area<{min_area}")
        if maxx - minx < min_width: reasons.append(f"width<{min_width}mm")
        if reasons:
            dropped.append((x_pos, reasons))
        else:
            kept.append((x_pos, rib))
    return kept, dropped


# =============================================================================
# Slot generation
# =============================================================================

def add_spine_slots(silhouette, x_positions, slot_width, extra=1.0):
    sil = silhouette
    for x in x_positions:
        strip = box(x - slot_width/2, -1000, x + slot_width/2, 1000)
        inter = sil.intersection(strip)
        if inter.is_empty: continue
        top_z = inter.bounds[3]
        slot_rect = box(x - slot_width/2, 0.0, x + slot_width/2, top_z + extra)
        sil = sil.difference(slot_rect)
        if isinstance(sil, MultiPolygon):
            sil = max(sil.geoms, key=lambda g: g.area)
    return sil


def add_rib_slot(rib, slot_width, extra=1.0):
    bottom_z = rib.bounds[1]
    slot_rect = box(-slot_width/2, bottom_z - extra, slot_width/2, 0.0)
    out = rib.difference(slot_rect)
    if isinstance(out, MultiPolygon):
        out = max(out.geoms, key=lambda g: g.area)
    return out


# =============================================================================
# Layout
# =============================================================================

def layout_pieces(spine, ribs, fins, padding_mm=8.0, max_row_width=350.0):
    placed = []
    cur_y = padding_mm

    # Spine
    sx_min, sy_min, sx_max, sy_max = spine.bounds
    sp = affinity.translate(spine, -sx_min + padding_mm, -sy_min + padding_mm)
    placed.append((sp, "SPINE", (sp.centroid.x, sp.centroid.y)))
    cur_y = padding_mm + (sy_max - sy_min) + padding_mm

    # Ribs row(s)
    cur_x = padding_mm
    row_h = 0.0
    for i, (x_pos, rib) in enumerate(ribs):
        rb = rib.bounds
        rw = rb[2] - rb[0]
        rh = rb[3] - rb[1]
        if cur_x + rw > max_row_width:
            cur_y += row_h + padding_mm
            cur_x = padding_mm
            row_h = 0.0
        r = affinity.translate(rib, -rb[0] + cur_x, -rb[1] + cur_y)
        placed.append((r, f"#{i+1:02d}", (r.centroid.x, r.bounds[1] + 5)))
        cur_x += rw + padding_mm
        row_h = max(row_h, rh)
    cur_y += row_h + padding_mm

    # Fins row(s)
    cur_x = padding_mm
    row_h = 0.0
    for i, fin in enumerate(fins):
        fb = fin.bounds
        fw = fb[2] - fb[0]
        fh = fb[3] - fb[1]
        if cur_x + fw > max_row_width:
            cur_y += row_h + padding_mm
            cur_x = padding_mm
            row_h = 0.0
        f = affinity.translate(fin, -fb[0] + cur_x, -fb[1] + cur_y)
        placed.append((f, f"FIN_{i+1}", (f.centroid.x, f.centroid.y)))
        cur_x += fw + padding_mm
        row_h = max(row_h, fh)

    total_h = cur_y + row_h + padding_mm
    return placed, (max_row_width, total_h)


# =============================================================================
# SVG + preview + .lbrn2
# =============================================================================

def write_svg(placed, total_size, out_path: Path):
    w, h = total_size
    dwg = svgwrite.Drawing(str(out_path), size=(f"{w}mm", f"{h}mm"),
                           viewBox=f"0 0 {w} {h}")
    cuts = dwg.g(id="cut", stroke="red", fill="none", stroke_width=0.1,
                 transform=f"translate(0,{h}) scale(1,-1)")
    for poly, _, _ in placed:
        ext_pts = [(round(x, 3), round(y, 3)) for x, y in poly.exterior.coords]
        cuts.add(dwg.polygon(points=ext_pts))
        for interior in poly.interiors:
            int_pts = [(round(x, 3), round(y, 3)) for x, y in interior.coords]
            cuts.add(dwg.polygon(points=int_pts))
    dwg.add(cuts)
    engrave = dwg.g(id="engrave", fill="black", stroke="none",
                    font_family="Arial", font_size="4", text_anchor="middle")
    for _, name, (ax, ay) in placed:
        engrave.add(dwg.text(name, insert=(ax, h - ay)))
    dwg.add(engrave)
    dwg.save()
    print(f"[svg] {out_path}")


def write_preview_png(placed, total_size, out_path: Path, px_per_mm=4):
    from PIL import Image, ImageDraw
    w, h = total_size
    img = Image.new("RGB", (int(w * px_per_mm), int(h * px_per_mm)), "white")
    draw = ImageDraw.Draw(img)
    def to_px(x, y):
        return (int(x * px_per_mm), int((h - y) * px_per_mm))
    for poly, name, (ax, ay) in placed:
        ext_px = [to_px(x, y) for x, y in poly.exterior.coords]
        draw.polygon(ext_px, outline="red", width=2)
        for interior in poly.interiors:
            int_px = [to_px(x, y) for x, y in interior.coords]
            draw.polygon(int_px, outline="red", width=2)
        lx, ly = to_px(ax, ay)
        draw.text((lx - 12, ly - 6), name, fill="black")
    img.save(out_path, "PNG")
    print(f"[preview] {out_path}")


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
    <CutSetting type="Cut">
        <index Value="1"/>
        <name Value="C01 Engrave"/>
        <minPower Value="25"/>
        <maxPower Value="25"/>
        <minPower2 Value="25"/>
        <maxPower2 Value="25"/>
        <speed Value="200"/>
        <numPasses Value="1"/>
        <doOutput Value="1"/>
        <priority Value="1"/>
    </CutSetting>
"""
LBRN_FOOTER = "</LightBurnProject>\n"


def polygon_to_lbrn_shape(poly, cut_index):
    out = []
    rings = [poly.exterior] + list(poly.interiors)
    for ring in rings:
        pts = list(ring.coords)
        if len(pts) < 3: continue
        if pts[-1] == pts[0]: pts = pts[:-1]
        n = len(pts)
        verts = "".join(f"V{x:.3f} {y:.3f}c0x1L" for x, y in pts)
        prims = "".join(f"LineL{i} {(i + 1) % n}" for i in range(n))
        out.append(
            f'    <Shape Type="Path" CutIndex="{cut_index}">\n'
            f'        <XForm>1 0 0 1 0 0</XForm>\n'
            f'        <VertList>{verts}</VertList>\n'
            f'        <PrimList>{prims}</PrimList>\n'
            f'    </Shape>\n')
    return out


def text_to_lbrn_shape(text, x, y, height_mm, cut_index):
    return (
        f'    <Shape Type="Text" CutIndex="{cut_index}" Font="Arial,400,0" '
        f'Str="{text}" H="{height_mm}" Spacing="0" UpperCase="false" '
        f'HOffset="0" VOffset="0" Weld="false" HasBackupPath="false">\n'
        f'        <XForm>1 0 0 1 {x:.3f} {y:.3f}</XForm>\n'
        f'    </Shape>\n')


def write_lbrn2(placed, out_path: Path):
    parts = [LBRN_HEADER]
    for poly, _, _ in placed:
        parts.extend(polygon_to_lbrn_shape(poly, cut_index=0))
    for _, label, (ax, ay) in placed:
        parts.append(text_to_lbrn_shape(label, ax, ay, 4.0, cut_index=1))
    parts.append(LBRN_FOOTER)
    out_path.write_text("".join(parts), encoding="utf-8")
    print(f"[lbrn2] {out_path}  ({out_path.stat().st_size/1024:.0f} KB)")


# =============================================================================
# Main
# =============================================================================

def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--length", type=float, default=250.0)
    p.add_argument("--slices", type=int, default=16, help="Cross-sections (default 16)")
    p.add_argument("--margin", type=float, default=10.0)
    p.add_argument("--opening", type=float, default=2.5)
    p.add_argument("--thickness", type=float, default=4.0)
    p.add_argument("--clearance", type=float, default=0.15)
    p.add_argument("--fin-y", type=float, default=15.0,
                   help="Y plane (mm) for lateral fin extraction (default 15 mm)")
    p.add_argument("--no-fins", action="store_true", help="Skip lateral fin extraction")
    p.add_argument("--out-dir", type=Path, default=Path.cwd(),
                   help="Output directory (default: current directory)")
    p.add_argument("--name", default=None,
                   help="Output basename (default: source file name)")
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    base = args.name or args.source.stem
    out_svg = args.out_dir / f"{base}_slice.svg"
    out_lbrn = args.out_dir / f"{base}_slice.lbrn2"
    out_png = args.out_dir / f"{base}_slice_preview.png"

    slot_width = args.thickness + args.clearance

    print("=== Load + orient ===")
    mesh = load_and_orient(args.source, args.length)
    print(f"  extents: {[round(v, 2) for v in mesh.extents]}")

    print(f"\n=== {args.slices} cross-sections ===")
    raw_ribs = cross_sections(mesh, args.slices, args.margin, args.opening)
    ribs, dropped = filter_ribs(raw_ribs)
    for x, reasons in dropped:
        print(f"  drop rib at x={x:7.2f}  reasons={','.join(reasons)}")
    print(f"  kept {len(ribs)} ribs (#01..#{len(ribs):02d})")

    print(f"\n=== Side silhouette ===")
    silhouette = longitudinal_silhouette(mesh)

    fins = []
    if not args.no_fins:
        print(f"\n=== Lateral fins (Y = ±{args.fin_y:.1f} mm) ===")
        side = extract_lateral_fins(mesh, args.fin_y)
        print(f"  extracted {len(side)} lateral piece(s)")
        # Build left+right: mirror each XZ shape to also cut a mirror copy
        for shp in side:
            fins.append(shp)            # right side
            fins.append(affinity.scale(shp, xfact=-1, origin="centroid"))  # left

    print(f"\n=== Slots (width = {slot_width:.2f} mm) ===")
    x_positions = [x for x, _ in ribs]
    spine = add_spine_slots(silhouette, x_positions, slot_width)
    ribs_slotted = [(x, add_rib_slot(rib, slot_width)) for x, rib in ribs]

    print(f"\n=== Layout ===")
    placed, total_size = layout_pieces(spine, ribs_slotted, fins)
    print(f"  total size: {total_size[0]:.1f} x {total_size[1]:.1f} mm")
    print(f"  pieces: 1 spine + {len(ribs)} ribs + {len(fins)} fins = {1 + len(ribs) + len(fins)} total")

    print(f"\n=== Export ===")
    write_preview_png(placed, total_size, out_png)
    write_svg(placed, total_size, out_svg)
    write_lbrn2(placed, out_lbrn)

    print("\nSettings reminder (4mm plywood @ 65W CO2):")
    print("  Cut layer:     8 mm/s, 90 % power, 2 passes, air assist ON")
    print("  Engrave layer: 200 mm/s, 25 % power, 1 pass")
    print("\nDone.")


if __name__ == "__main__":
    main()
