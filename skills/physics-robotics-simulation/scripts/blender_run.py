#!/usr/bin/env python3
"""Find Blender, check its release, and run one of this kit's bpy scripts headless and bounded.

USAGE:
  python scripts/blender_run.py SCRIPT.py [--blender PATH] [--max-wall-s 600] -- [script args]

Blender is found from --blender, then $BLENDER, then `blender` on PATH. The run is
`blender -b --factory-startup --python-exit-code 1 -P SCRIPT -- ARGS`: no user startup file,
no user add-ons (so no MCP add-on), and a Python exception is a non-zero exit.
Exit 2 when Blender is missing or is not the tested release line; exit 124 on the wall-time bound.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

TESTED = "5.2.3"
LINE = "5.2"


def find_blender(explicit):
    for cand in (explicit, os.environ.get("BLENDER"), shutil.which("blender")):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    return None


def main():
    argv = sys.argv[1:]
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    own = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("--blender")
    ap.add_argument("--max-wall-s", type=float, default=600.0)
    ap.add_argument("--any-version", action="store_true", help="run on a Blender outside the tested line")
    a = ap.parse_args(own)
    exe = find_blender(a.blender)
    if not exe:
        print("error: Blender was not found. Install Blender 5.2 LTS (tested: 5.2.3) from "
              "https://www.blender.org/download/lts/ (the Linux build is a folder you unpack anywhere), "
              "then pass --blender /path/to/blender or set BLENDER=/path/to/blender. "
              "Physics runs do not need Blender; only asset preparation and replay rendering do.",
              file=sys.stderr)
        return 2
    ver = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout.split("\n")[0]
    found = ver.replace("Blender", "").split()[0] if ver.startswith("Blender") else "unknown"
    if not found.startswith(LINE + ".") and not a.any_version:
        print(f"error: {exe} is Blender {found}; this kit is tested on {TESTED} ({LINE} LTS). "
              f"Install {LINE} LTS, or pass --any-version to run anyway and treat the result as untested.",
              file=sys.stderr)
        return 2
    cmd = [exe, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(a.script), "--", *rest]
    print(f"blender {found}: {' '.join(cmd[1:])}", file=sys.stderr)
    try:
        return subprocess.run(cmd, timeout=a.max_wall_s).returncode
    except subprocess.TimeoutExpired:
        print(f"error: the Blender run passed its {a.max_wall_s:.0f} s bound and was stopped", file=sys.stderr)
        return 124


if __name__ == "__main__":
    sys.exit(main())
