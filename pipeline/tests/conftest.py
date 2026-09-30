"""pytest fixtures for snapshot testing the furniture pipeline."""
import os
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent.parent
REPO_ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))

# Deterministic material values for all tests, independent of the local machine.
os.environ.setdefault("LASER_CALIBRATION", str(REPO_ROOT / "calibration.example.json"))


def pytest_addoption(parser):
    parser.addoption("--update-baselines", action="store_true",
                     help="Replace baselines with current preview output (no diff check)")
