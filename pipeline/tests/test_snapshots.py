"""Snapshot tests for all furniture build scripts.

Each test:
  1. Runs the build script (regenerates .lbrn2 + preview PNG)
  2. Compares the preview PNG against a frozen baseline
  3. FAILS if pixel diff > 1.0% (catches geometry regressions)

To update baselines after intentional changes:
    pytest --update-baselines

To run all snapshot tests:
    pytest tests/
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from snapshot_utils import image_diff_pct, snapshot_baseline_dir, update_baseline

PIPELINE_DIR = Path(__file__).parent.parent
PREVIEWS = PIPELINE_DIR / "previews"
BASELINES = snapshot_baseline_dir()
DIFF_THRESHOLD_PCT = 1.0  # max 1% pixel diff allowed
REPO_ROOT = PIPELINE_DIR.parent


def _env():
    """Child processes: UTF-8 console (Windows cp1252 safe) and the repo's
    example calibration, so results do not depend on the local machine."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("LASER_CALIBRATION", str(REPO_ROOT / "calibration.example.json"))
    return env


def _run(script_name: str):
    return subprocess.run([sys.executable, str(PIPELINE_DIR / script_name)],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=str(PIPELINE_DIR), env=_env())

# Build scripts → expected preview filename
BUILDS = [
    ("01_tisch_quadrat.py", "01_tisch_quadrat.png"),
    ("02_stuhl.py",         "02_stuhl.png"),
    ("03_bett.py",          "03_bett.png"),
    ("04_nachttisch.py",    "04_nachttisch.png"),
    ("05_kleiderschrank.py","05_kleiderschrank.png"),
    ("06_kommode.py",       "06_kommode.png"),
    ("07_sofa.py",          "07_sofa.png"),
    ("08_buecherregal.py",  "08_buecherregal.png"),
    ("09_stehlampe.py",     "09_stehlampe.png"),
]


@pytest.fixture
def update_baselines_flag(request):
    return request.config.getoption("--update-baselines")


def _run_build(script_name: str):
    """Execute a build script. Raises if exit code != 0."""
    r = _run(script_name)
    if r.returncode != 0:
        pytest.fail(f"Build failed for {script_name}:\n{r.stdout}\n{r.stderr}")


@pytest.mark.parametrize("script_name,preview_name", BUILDS,
                         ids=[b[0] for b in BUILDS])
def test_furniture_snapshot(script_name, preview_name, update_baselines_flag):
    """Build the piece and compare preview to baseline."""
    _run_build(script_name)
    preview = PREVIEWS / preview_name
    baseline = BASELINES / preview_name

    assert preview.exists(), f"Build did not produce expected preview: {preview}"

    if update_baselines_flag:
        update_baseline(preview_name, preview)
        return

    if not baseline.exists():
        update_baseline(preview_name, preview)
        pytest.skip(f"Baseline created (first run): {preview_name}")

    diff = image_diff_pct(preview, baseline)
    assert diff <= DIFF_THRESHOLD_PCT, (
        f"Preview for {preview_name} differs by {diff:.2f}% (threshold {DIFF_THRESHOLD_PCT}%). "
        f"If intentional, run `pytest --update-baselines` to refresh."
    )


def test_simulator_bed_v4_passes():
    """Verify the bed v4 still passes the geometric simulator."""
    r = _run("demo_simulate_bed.py")
    assert r.returncode == 0, f"Simulator returned non-zero:\n{r.stdout}\n{r.stderr}"
    assert "PASS - All checks succeeded" in r.stdout, \
        f"Simulator did not PASS:\n{r.stdout}"


def test_simulator_catches_known_bugs():
    """Verify the simulator catches the 4 known-bad designs."""
    r = _run("demo_simulate_broken.py")
    assert r.returncode == 0, f"Demo script failed:\n{r.stderr}"
    # Expect: 2 FAILs (collision + no-contact) + 2 WARNINGs (no-position + excessive-overlap)
    assert r.stdout.count("FAIL") >= 2, \
        f"Expected at least 2 FAILs in broken-demo output, got:\n{r.stdout}"
    assert "COLLISION" in r.stdout
    assert "JOINT_NO_CONTACT" in r.stdout
    assert "NO_POSITION" in r.stdout
    assert "EXCESSIVE_JOINT_OVERLAP" in r.stdout


def test_boxes_bridge_basicbox():
    """Verify the boxes.py bridge generates a valid ClosedBox."""
    from boxes_bridge import find_boxes_executable
    if find_boxes_executable() is None:
        pytest.skip("boxes.py CLI not installed")
    r = _run("demo_boxes_bridge.py")
    assert r.returncode == 0, f"boxes-bridge demo failed:\n{r.stderr}"
    assert "6 Parts erzeugt" in r.stdout, \
        f"Expected 6 parts from ClosedBox, got:\n{r.stdout}"


def test_all_pieces_pass_simulator():
    """Run verify_all.py, every furniture piece must pass the 3D simulator."""
    r = _run("verify_all.py")
    assert r.returncode == 0, f"verify_all crashed:\n{r.stderr}"
    assert "9/9 pieces passed simulator" in r.stdout, \
        f"Not all pieces passed:\n{r.stdout}"
