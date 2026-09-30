"""Helpers for snapshot tests: image diff, baseline management."""
import shutil
from pathlib import Path
import numpy as np
from PIL import Image


def image_diff_pct(path_a: Path, path_b: Path, pixel_threshold: int = 10) -> float:
    """Return percentage of pixels that differ between two PNG images.

    A pixel counts as 'different' if any RGB channel differs by more than
    `pixel_threshold` (default 10, robust against tiny rendering noise).

    Returns:
        Float in [0, 100]. 0 = identical, 100 = all pixels differ.
        Returns 100.0 if images have different sizes (counts as full mismatch).
    """
    if not path_a.exists() or not path_b.exists():
        return 100.0
    a = Image.open(path_a).convert("RGB")
    b = Image.open(path_b).convert("RGB")
    if a.size != b.size:
        return 100.0
    arr_a = np.array(a, dtype=np.int16)
    arr_b = np.array(b, dtype=np.int16)
    diff = np.abs(arr_a - arr_b)
    diff_mask = (diff > pixel_threshold).any(axis=2)
    return 100.0 * diff_mask.sum() / diff_mask.size


def snapshot_baseline_dir() -> Path:
    return Path(__file__).parent / "baselines"


def update_baseline(name: str, source: Path):
    """Copy a preview file to the baselines directory.
    Used initially to set baselines, or with --update-baselines flag.
    """
    target = snapshot_baseline_dir() / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
