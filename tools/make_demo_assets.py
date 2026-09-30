"""Erzeugt die synthetischen Eingaben für die Beispiele.

- examples/laser-prep/testmotiv.png: Testmuster (Verlaufskugel, Graukeil,
  Linienraster) auf schwarzem Grund. Kein Foto.
- examples/mesh-slice/demo_body.stl: stilisierter Körper aus einem gestreckten
  Ellipsoid mit zwei dreieckigen Seitenflossen, rein prozedural erzeugt.

Aufruf:  python tools/make_demo_assets.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent


def make_testmotiv(path: Path, w: int = 800, h: int = 1200) -> None:
    im = Image.new("L", (w, h), 0)
    px = im.load()
    # Kugel mit radialem Verlauf (prüft Graustufen-Wiedergabe)
    cx, cy, r = w / 2, h * 0.36, w * 0.36
    for y in range(int(cy - r), int(cy + r)):
        for x in range(int(cx - r), int(cx + r)):
            d = ((x - cx - r * 0.3) ** 2 + (y - cy + r * 0.3) ** 2) ** 0.5
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[x, y] = max(40, int(225 - d / (1.7 * r) * 185))
    draw = ImageDraw.Draw(im)
    # Graukeil mit 11 Stufen (0 bis 100 %)
    top = int(h * 0.74)
    step = (w - 80) / 11
    for i in range(11):
        x0 = 40 + i * step
        draw.rectangle([x0, top, x0 + step - 4, top + 90], fill=int(225 * i / 10))
    # Feines Linienraster (prüft Auflösung)
    for i in range(0, 24):
        x = 40 + i * 30
        draw.line([x, h - 150, x + 15, h - 60], fill=210, width=1 + i % 3)
    im.save(path, "PNG")
    print(f"[ok] {path.relative_to(REPO)}")


def make_demo_body(path: Path) -> None:
    import trimesh

    body = trimesh.creation.icosphere(subdivisions=4)
    body.apply_scale([125.0, 11.0, 30.0])          # Länge 250, halbe Breite 11, halbe Höhe 30
    fins = []
    # Dreieckige Seitenflosse: Profil in der XZ-Ebene, seitlich (Y) als Prisma
    profile = [(10.0, -6.0), (55.0, -10.0), (18.0, -34.0)]   # (x, z)
    for side in (1, -1):
        y_in, y_out = side * 8.0, side * 34.0
        pts = [(x, y, z) for (x, z) in profile for y in (y_in, y_out)]
        fins.append(trimesh.Trimesh(vertices=pts).convex_hull)
    mesh = trimesh.util.concatenate([body] + fins)
    mesh.export(path)
    print(f"[ok] {path.relative_to(REPO)} ({len(mesh.faces)} Dreiecke)")


if __name__ == "__main__":
    make_testmotiv(REPO / "examples" / "laser-prep" / "testmotiv.png")
    make_demo_body(REPO / "examples" / "mesh-slice" / "demo_body.stl")
