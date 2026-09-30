"""
Photo prep for slate engraving with a CO2 laser (target: 65 W, LightBurn).

Pipeline:
  source image -> EXIF transpose -> [optional bg removal via rembg]
                -> place on black bg -> portrait/round crop
                -> grayscale -> autocontrast -> sharpen -> PNG
                -> embed into .lbrn2 templates (one per target format)

Slate logic: bright pixels => laser fires => white burn,
             dark pixels => no burn => slate stays dark.
Backgrounds must be BLACK so the slate shows through there.

Formats are 2:3 portrait at 254 DPI inside slate stones:
  10x10        => 10x10 cm slate, image 66.67 x 100.00 mm
  round10      => Ø10 cm slate, image 55.50 x 83.20 mm (with reference circle)
  15x20        => 15x20 cm slate, image 133.33 x 200.00 mm

Usage:
  python prep.py <source-image> <format> [<format> ...]
                 [--model birefnet-portrait|u2net_human_seg]
                 [--no-bgremove]
                 [--name <basename>]
                 [--out-dir <dir>]
"""
import argparse
import base64
import re
import sys
import time
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE = SCRIPT_DIR / "template.lbrn2"
DEFAULT_OUT = Path.cwd() / "laser-prep-out"

FORMATS = {
    "10x10":   {"w_mm": 66.67,  "h_mm": 100.00, "circle": False},
    "round10": {"w_mm": 55.50,  "h_mm":  83.20, "circle": True},
    "15x20":   {"w_mm": 133.33, "h_mm": 200.00, "circle": False},
}

TARGET_DPI = 254  # 0.1 mm line interval, matches template <interval Value="0.1"/>


def check_resolution(cropped_size_px, fmt_name, fmt_spec):
    """Compare cropped image pixels to what's needed at TARGET_DPI for fmt.
    Prints OK / WARN. Returns True if sufficient."""
    px_per_mm = TARGET_DPI / 25.4   # ≈ 10 px/mm at 254 DPI
    need_h_px = fmt_spec["h_mm"] * px_per_mm
    have_h_px = cropped_size_px[1]
    effective_dpi = have_h_px / fmt_spec["h_mm"] * 25.4
    if have_h_px >= need_h_px:
        print(f"[res] {fmt_name}: OK - {have_h_px}px for {fmt_spec['h_mm']:.0f}mm "
              f"= {effective_dpi:.0f} DPI (target {TARGET_DPI})")
        return True
    deficit_pct = (1 - have_h_px / need_h_px) * 100
    print(f"[res] {fmt_name}: WARN - {have_h_px}px for {fmt_spec['h_mm']:.0f}mm "
          f"= {effective_dpi:.0f} DPI ({deficit_pct:.0f}% under target {TARGET_DPI}). "
          f"LightBurn upscales, Detail leidet.")
    return False


def cut_background(im: Image.Image, model: str) -> Image.Image:
    """Run rembg on a PIL image; return RGBA with alpha = foreground mask."""
    import rembg
    print(f"[rembg] model={model}")
    t0 = time.time()
    session = rembg.new_session(model)
    out = rembg.remove(im, session=session)
    print(f"[rembg] done in {time.time()-t0:.1f}s")
    return out


def on_black(rgba: Image.Image) -> Image.Image:
    """Flatten an RGBA image onto a black background -> RGB."""
    bg = Image.new("RGB", rgba.size, (0, 0, 0))
    if rgba.mode == "RGBA":
        bg.paste(rgba, mask=rgba.split()[-1])
    else:
        bg.paste(rgba.convert("RGB"))
    return bg


def auto_portrait_crop(im: Image.Image, target_ratio: float = 2/3) -> Image.Image:
    """Find the subject bbox (anything non-black with margin) and crop to target_ratio
    (width/height) portrait centered on the subject, hugging the bbox as tightly as
    the image bounds allow."""
    W, H = im.size
    # Find bbox of non-black pixels (treat <8 in all channels as background)
    px = im.load()
    xs_min, xs_max, ys_min, ys_max = W, 0, H, 0
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y][:3]
            if r > 8 or g > 8 or b > 8:
                if x < xs_min: xs_min = x
                if x > xs_max: xs_max = x
                if y < ys_min: ys_min = y
                if y > ys_max: ys_max = y
    if xs_max < xs_min:  # nothing found
        return im
    # Add ~5% margin around subject
    bw = xs_max - xs_min
    bh = ys_max - ys_min
    mx = int(bw * 0.05)
    my = int(bh * 0.05)
    sx_min = max(0, xs_min - mx)
    sx_max = min(W, xs_max + mx)
    sy_min = max(0, ys_min - my)
    sy_max = min(H, ys_max + my)
    sw = sx_max - sx_min
    sh = sy_max - sy_min
    cx = (sx_min + sx_max) / 2
    cy = (sy_min + sy_max) / 2
    # Determine crop window that contains the subject and has target ratio
    if sw / sh > target_ratio:
        # subject wider than target -> width drives, height = w/ratio
        crop_w = sw
        crop_h = crop_w / target_ratio
    else:
        crop_h = sh
        crop_w = crop_h * target_ratio
    # If crop_h exceeds image bounds, scale down so it fits and grow width
    if crop_h > H:
        crop_h = H
        crop_w = crop_h * target_ratio
    if crop_w > W:
        crop_w = W
        crop_h = crop_w / target_ratio
    # Center on subject, clamp to image
    left   = cx - crop_w / 2
    top    = cy - crop_h / 2
    right  = left + crop_w
    bottom = top + crop_h
    if left < 0:
        right -= left; left = 0
    if top < 0:
        bottom -= top; top = 0
    if right > W:
        left -= (right - W); right = W
    if bottom > H:
        top -= (bottom - H); bottom = H
    left, top, right, bottom = max(0, int(left)), max(0, int(top)), int(right), int(bottom)
    return im.crop((left, top, right, bottom))


def enhance_for_slate(im: Image.Image) -> Image.Image:
    gray  = ImageOps.grayscale(im)
    ac    = ImageOps.autocontrast(gray, cutoff=1)
    c     = ImageEnhance.Contrast(ac).enhance(1.20)
    sharp = c.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
    return sharp


def build_lbrn2(template_text: str, png_path: Path, out_path: Path,
                w_mm: float, h_mm: float, with_circle: bool) -> None:
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    # Only the file name goes into the project file, never a local absolute path.
    forward = png_path.name
    data = template_text
    start = data.find('Data="')
    end   = data.find('"', start + 6)
    data  = data[:start] + f'Data="{b64}"' + data[end+1:]
    data  = re.sub(r'File="[^"]*"', f'File="{forward}"', data)
    w_attr = round(w_mm * 10, 4)
    h_attr = round(h_mm * 10, 4)
    data = re.sub(r'W="1333\.334"',  f'W="{w_attr}"',  data)
    data = re.sub(r'H="2000\.0011"', f'H="{h_attr}"',  data)
    data = data.replace('150 120</XForm>', '100 100</XForm>')
    if with_circle:
        tool_layer = (
            '    <CutSetting type="Cut">\n'
            '        <index Value="30"/>\n'
            '        <name Value="T1"/>\n'
            '        <maxPower Value="20"/>\n'
            '        <maxPower2 Value="20"/>\n'
            '        <speed Value="20"/>\n'
            '        <priority Value="0"/>\n'
            '        <doOutput Value="0"/>\n'
            '    </CutSetting>\n'
        )
        circle_shape = (
            '    <Shape Type="Ellipse" CutIndex="30" Rx="500" Ry="500" Sx="0" Sy="0">\n'
            '        <XForm>0.1 0 0 0.1 100 100</XForm>\n'
            '    </Shape>\n'
        )
        data = data.replace(
            '    <CutSetting_Img type="Image">',
            tool_layer + '    <CutSetting_Img type="Image">'
        )
        data = data.replace(
            '</LightBurnProject>',
            circle_shape + '</LightBurnProject>'
        )
    out_path.write_text(data, encoding="utf-8")
    print(f"[lbrn2] wrote {out_path.name} ({out_path.stat().st_size/1024:.0f} KB, "
          f"{w_mm}x{h_mm} mm)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, help="Source image (any common format)")
    p.add_argument("formats", nargs="+", choices=list(FORMATS.keys()),
                   help="One or more target formats: 10x10 round10 15x20")
    p.add_argument("--model", default="birefnet-portrait",
                   choices=["birefnet-portrait", "u2net_human_seg"],
                   help="rembg model (default birefnet-portrait, fallback u2net_human_seg)")
    p.add_argument("--no-bgremove", action="store_true",
                   help="Skip background removal (image is already cut out on white/transparent)")
    p.add_argument("--name", default=None,
                   help="Output basename (defaults to source filename stem)")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT,
                   help="Output directory (default ./laser-prep-out); PNG and preview go to <out-dir>/png")
    args = p.parse_args()

    if not args.source.exists():
        sys.exit(f"Source not found: {args.source}")
    if not TEMPLATE.exists():
        sys.exit(f"Template not found: {TEMPLATE}")
    png_dir = args.out_dir / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    basename = args.name or args.source.stem

    print(f"=== Source: {args.source} ===")
    im = ImageOps.exif_transpose(Image.open(args.source))
    print(f"size={im.size}, mode={im.mode}")

    if args.no_bgremove:
        # Convert near-white to black so slate shows through
        if im.mode != "RGB":
            im = im.convert("RGB")
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                r, g, b = px[x, y]
                if r >= 240 and g >= 240 and b >= 240:
                    px[x, y] = (0, 0, 0)
        flattened = im
    else:
        cut = cut_background(im, args.model)
        flattened = on_black(cut)

    cropped = auto_portrait_crop(flattened, target_ratio=2/3)
    print(f"[crop] {cropped.size}")

    print(f"[res] target = {TARGET_DPI} DPI (0,1 mm line interval)")
    for fmt in args.formats:
        check_resolution(cropped.size, fmt, FORMATS[fmt])

    enhanced = enhance_for_slate(cropped)

    png_path = png_dir / f"{basename}_slate.png"
    enhanced.save(png_path, "PNG", dpi=(300, 300))
    print(f"[png] {png_path}")

    template_text = TEMPLATE.read_text(encoding="utf-8")
    suffix_map = {"10x10": "10x10", "round10": "rund10", "15x20": "15x20"}
    for fmt in args.formats:
        spec = FORMATS[fmt]
        out = args.out_dir / f"{basename}-{suffix_map[fmt]}.lbrn2"
        build_lbrn2(template_text, png_path, out,
                    spec["w_mm"], spec["h_mm"], spec["circle"])

    # Tiny preview JPG: cropped on black + enhanced grayscale, side by side
    pw = 500
    ratio = pw / cropped.width
    ph = int(cropped.height * ratio)
    panels = [cropped.resize((pw, ph)), enhanced.resize((pw, ph)).convert("RGB")]
    combo = Image.new("RGB", (pw * 2 + 20, ph), "white")
    combo.paste(panels[0], (0, 0))
    combo.paste(panels[1], (pw + 20, 0))
    preview = png_dir / f"{basename}_preview.jpg"
    combo.save(preview, "JPEG", quality=88)
    print(f"[preview] {preview}")

    print("\nDone.")


if __name__ == "__main__":
    main()
