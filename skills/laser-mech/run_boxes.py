"""
Thin wrapper around boxes.py CLI for laser-cut mechanical parts.

Why this wrapper exists:
  - the boxes CLI often sits in a Python Scripts dir that is not on PATH
  - We want a single command-line interface that:
      * Lists generators by category
      * Prints parameters for a given generator
      * Runs a generator with parameters and writes the result to a chosen output path

Usage:
  python run_boxes.py list                          # list all generators
  python run_boxes.py list-mech                     # only mechanic / gear / clock
  python run_boxes.py params <Generator>            # show parameters for a generator
  python run_boxes.py run <Generator> [--param=val] # run generator -> .lbrn2 (default)

boxes.py (Florian Festi, GPL-3.0) is an external dependency and is called as a
separate program; it is not part of this repository.
"""
import argparse
import os
import shutil
import subprocess
import sysconfig
import sys
from pathlib import Path

OUT_DIR = Path.cwd()

# Curated subset of generators relevant for mechanical / kinetic projects
# (Verified to exist in boxes.py)
MECH_GENERATORS = {
    "Gears":             "Two spur gears (a small pinion + a larger gear)",
    "Pulley":            "Belt pulley wheel",
    "GearBox":           "Closed gearbox housing with internal gear train",
    "Planetary":         "Planetary gear system (sun + planets + ring)",
    "Planetary2":        "Alternate planetary gear configuration",
    "Clock":             "Decorative clock face / mechanism housing",
    "SevenSegmentClock": "7-segment display style clock",
}


def find_boxes_executable():
    """BOXES_EXE environment variable, PATH, then the interpreter's scripts dirs."""
    env = os.environ.get("BOXES_EXE")
    if env and Path(env).exists():
        return Path(env)
    found = shutil.which("boxes")
    if found:
        return Path(found)
    names = ("boxes.exe", "boxes") if os.name == "nt" else ("boxes",)
    for scheme in (None, f"{os.name}_user"):
        try:
            scripts = sysconfig.get_path("scripts", scheme) if scheme else sysconfig.get_path("scripts")
        except KeyError:
            continue
        for n in names:
            cand = Path(scripts) / n
            if cand.exists():
                return cand
    return None


def env_utf8():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run_boxes(args, capture=False):
    exe = find_boxes_executable()
    if exe is None:
        sys.exit("boxes.py CLI not found. Install boxes.py or set BOXES_EXE.")
    cmd = [str(exe)] + args
    if capture:
        r = subprocess.run(cmd, env=env_utf8(), text=True, encoding="utf-8",
                           capture_output=True)
        return r.stdout, r.stderr, r.returncode
    return subprocess.call(cmd, env=env_utf8())


def cmd_list(only_mech: bool):
    if only_mech:
        print(f"=== Mechanic-related generators ({len(MECH_GENERATORS)}) ===")
        for name, desc in MECH_GENERATORS.items():
            print(f"  {name:14s} - {desc}")
        return
    # Full list via boxes itself (uses --help? we just import)
    import boxes.generators as G
    import pkgutil
    names = sorted([m.name for m in pkgutil.iter_modules(G.__path__) if not m.name.startswith("_")])
    print(f"=== All {len(names)} generators ===")
    for n in names:
        print(f"  {n}")


def cmd_params(generator: str):
    """Print parameter list for a generator by importing and inspecting its argparser."""
    try:
        mod_name = generator.lower()
        mod = __import__(f"boxes.generators.{mod_name}", fromlist=[generator])
    except ImportError:
        sys.exit(f"Generator module 'boxes.generators.{generator.lower()}' not found.")
    # Find the class (case-insensitive)
    candidates = [n for n in dir(mod) if n.lower() == generator.lower()]
    if not candidates:
        # Search for capitalized class in module
        from boxes import Boxes
        candidates = [n for n in dir(mod)
                      if isinstance(getattr(mod, n), type)
                      and issubclass(getattr(mod, n), Boxes)
                      and n != "Boxes"]
    if not candidates:
        sys.exit(f"Could not find generator class in module.")
    cls = getattr(mod, candidates[0])
    g = cls()
    print(f"=== {candidates[0]} parameters ===")
    for arg in g.argparser._actions:
        if arg.dest == "help":
            continue
        default = arg.default
        help_text = (arg.help or "").replace("\U0001f6c8", "").split("[")[0].strip()[:80]
        print(f"  --{arg.dest:25s} default={default!s:18s} {help_text}")


def _extract_output_path(extra_args: list, default: Path):
    """If --output / --output=path appears in extra_args, parse it and remove from args.
    Returns (clean_args, output_path)."""
    out = default
    cleaned = []
    i = 0
    while i < len(extra_args):
        a = extra_args[i]
        if a.startswith("--output="):
            out = Path(a.split("=", 1)[1])
            i += 1
        elif a == "--output":
            if i + 1 < len(extra_args):
                out = Path(extra_args[i + 1])
                i += 2
            else:
                i += 1
        else:
            cleaned.append(a)
            i += 1
    return cleaned, out


def _strip_notes_lbrn2(path: Path) -> int:
    """Remove the <Notes ShowOnLoad="1" ... /> element that boxes.py adds to .lbrn2
    files. That element causes LightBurn to pop up an attribution dialog on open."""
    import re
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(r'<Notes\b[^/>]*?/>\s*', "", text)
    if n:
        path.write_text(new_text, encoding="utf-8")
    return n


def cmd_run(generator: str, extra_args: list, default_output: Path,
            strip_notes: bool = False):
    extra_args, output = _extract_output_path(extra_args, default_output)

    # Default to .lbrn2 format unless the user explicitly passed --format=
    has_format = any(a.startswith("--format") for a in extra_args)
    if not has_format:
        extra_args = extra_args + ["--format=lbrn2"]
        # Adjust output extension if it's still the default .svg
        if output.suffix == ".svg":
            output = output.with_suffix(".lbrn2")

    # Sensible laser-cut defaults: no part labels, no reference rectangle.
    if not any(a.startswith("--labels") for a in extra_args):
        extra_args = extra_args + ["--labels=False"]
    if not any(a.startswith("--reference") for a in extra_args):
        extra_args = extra_args + ["--reference=0"]

    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [generator] + extra_args + ["--output", str(output)]
    rc = run_boxes(cmd)
    if rc != 0:
        sys.exit(f"boxes returned exit code {rc}")
    if not output.exists():
        sys.exit(f"Expected output not created: {output}")

    # boxes.py embeds a <Notes ShowOnLoad="1"> block with author credits that
    # opens a dialog in LightBurn on every load. Kept by default (attribution);
    # --strip-notes removes it on request.
    if strip_notes and output.suffix == ".lbrn2":
        n = _strip_notes_lbrn2(output)
        if n:
            print(f"[strip] removed {n} attribution Notes block")

    size_kb = output.stat().st_size / 1024
    print(f"[ok] {output}  ({size_kb:.1f} KB)")
    print()
    if output.suffix == ".lbrn2":
        print("Next steps:")
        print(f"  1. Open {output.name} directly in LightBurn (double-click or File > Open)")
        print(f"  2. Verify Cut Layer settings for 4mm plywood @ 65W CO2:")
        print(f"     - Speed: 8 mm/s,  Power: 90 %,  Passes: 2,  Air Assist: ON")
        print(f"  3. Frame-test before cutting")
    else:
        print("Next steps:")
        print(f"  1. Open {output.name} in browser to inspect")
        print(f"  2. LightBurn: File > Import > select the file")
        print(f"  3. Assign Cut Layer (4mm plywood @ 65W CO2):")
        print(f"     - Speed: 8 mm/s,  Power: 90 %,  Passes: 2,  Air Assist: ON")
        print(f"  4. Frame-test before cutting")


def main():
    p = argparse.ArgumentParser(description="Wrapper around boxes.py for laser-cut mechanics")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List all generators")
    sub.add_parser("list-mech", help="List only mechanic/gear related generators")
    pp = sub.add_parser("params", help="Show parameters for a generator")
    pp.add_argument("generator")
    pr = sub.add_parser("run", help="Run a generator with parameters")
    pr.add_argument("generator")
    pr.add_argument("--strip-notes", action="store_true",
                    help="Remove the boxes.py attribution Notes block from .lbrn2 output")
    pr.add_argument("rest", nargs=argparse.REMAINDER,
                    help="Generator-specific parameters (--teeth1=12 etc.). "
                         "Pass --output=path inside these to set output file.")
    args = p.parse_args()

    if args.cmd == "list":
        cmd_list(only_mech=False)
    elif args.cmd == "list-mech":
        cmd_list(only_mech=True)
    elif args.cmd == "params":
        cmd_params(args.generator)
    elif args.cmd == "run":
        default_out = OUT_DIR / f"{args.generator}.svg"
        cmd_run(args.generator, args.rest, default_out, strip_notes=args.strip_notes)


if __name__ == "__main__":
    main()
