"""Tests für Skills und Repo-Konfiguration."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
PREP = REPO / "skills" / "laser-prep" / "prep.py"
TEMPLATE = REPO / "skills" / "laser-prep" / "template.lbrn2"


def _env():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def test_calibration_example_is_loadable_and_uncalibrated():
    cfg = json.loads((REPO / "calibration.example.json").read_text(encoding="utf-8"))
    machine = cfg["machines"][cfg["active_machine"]]
    active = machine["materials"][machine["active_material"]]
    assert active["thickness"] == 3.0
    assert active["kerf"] == 0.15
    # Startwerte: nichts ist als gemessen markiert
    assert all(m["calibrated_at"] is None for m in machine["materials"].values())


def test_lib_reads_calibration_from_env():
    import lib
    assert lib.CALIBRATION_FILE == Path(os.environ["LASER_CALIBRATION"])
    assert abs(lib.SLOT_W - 2.85) < 1e-9


def test_prep_template_contains_no_file_reference():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert 'File=""' in text
    assert len(text) < 10_000, "Template soll nur einen kleinen Platzhalter enthalten"
    for needle in ('W="1333.334"', 'H="2000.0011"', "150 120</XForm>"):
        assert needle in text, f"prep.py erwartet {needle} im Template"


def test_prep_writes_lbrn2_without_local_paths(tmp_path):
    src = tmp_path / "motiv.png"
    im = Image.new("L", (300, 450), 0)
    for y in range(100, 350):
        for x in range(50, 250):
            im.putpixel((x, y), 60 + (x + y) % 150)
    im.save(src)
    r = subprocess.run([sys.executable, str(PREP), str(src), "10x10", "round10",
                        "--no-bgremove", "--name", "t", "--out-dir", str(tmp_path / "out")],
                       capture_output=True, text=True, encoding="utf-8", env=_env())
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("t-10x10.lbrn2", "t-rund10.lbrn2"):
        text = (tmp_path / "out" / name).read_text(encoding="utf-8")
        assert 'File="t_slate.png"' in text
        assert str(tmp_path) not in text and ":/" not in text and ":\\" not in text
    rund = (tmp_path / "out" / "t-rund10.lbrn2").read_text(encoding="utf-8")
    assert 'Type="Ellipse"' in rund and 'W="555.0"' in rund


def test_mesh_slice_on_synthetic_body(tmp_path):
    trimesh = pytest.importorskip("trimesh")
    body = trimesh.creation.icosphere(subdivisions=3)
    body.apply_scale([100.0, 10.0, 25.0])
    stl = tmp_path / "body.stl"
    body.export(stl)
    r = subprocess.run([sys.executable, str(REPO / "skills" / "mesh-slice" / "slice.py"),
                        str(stl), "--slices", "8", "--no-fins",
                        "--out-dir", str(tmp_path), "--name", "b"],
                       capture_output=True, text=True, encoding="utf-8", env=_env())
    assert r.returncode == 0, r.stdout + r.stderr
    m = re.search(r"pieces: 1 spine \+ (\d+) ribs", r.stdout)
    assert m and int(m.group(1)) >= 6
    for suffix in ("_slice.svg", "_slice.lbrn2", "_slice_preview.png"):
        assert (tmp_path / f"b{suffix}").exists()
