#!/usr/bin/env python3
"""
USAGE:
    python3 scripts/setup.py          # check that this machine can make a film, and print what it found as JSON

Checks for the four things a film needs and installs nothing:
    {"python": ".../python3", "pillow": "12.1.1", "ffmpeg": ".../ffmpeg", "ffprobe": ".../ffprobe" | null,
     "chromium": ".../chrome", "dist": ".../motion/dist", "cache": "~/.cache/code-config/video_studio", "ok": true}

python is the first python3 that imports Pillow: this one, else python3 on PATH. ffmpeg is the one on PATH, else the
one the imageio_ffmpeg package carries when that package is importable. chromium is the browser render.py starts
(its docstring gives the order it looks in). dist is the built composition, motion/dist/. ok is
true only when all of them are found; otherwise each missing one gets a plain sentence on stderr and the exit status
is 1. The render keeps its frames and the browser's profile under the cache folder, never in this one.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

PILLOW = "import PIL; print(PIL.__version__)"


def python():
    """(python3, Pillow's version) for the first python3 that imports Pillow, or (None, None)."""
    for py in dict.fromkeys(p for p in (sys.executable, shutil.which("python3")) if p):
        r = subprocess.run([py, "-c", PILLOW], capture_output=True, text=True)
        if r.returncode == 0:
            return py, r.stdout.strip()
    return None, None


def ffmpeg(py):
    """(ffmpeg, ffprobe): the system's, else imageio_ffmpeg's ffmpeg (it carries no ffprobe)."""
    if shutil.which("ffmpeg"):
        return shutil.which("ffmpeg"), shutil.which("ffprobe")
    for p in dict.fromkeys(x for x in (sys.executable, py) if x):
        r = subprocess.run([p, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                           capture_output=True, text=True)
        exe = r.stdout.strip()
        if r.returncode == 0 and exe and Path(exe).exists():
            return exe, None
    return None, None


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    py, pillow = python()
    ff, fp = ffmpeg(py)
    chrome = render.chromium()
    dist = render.DIST if (render.DIST / "index.html").is_file() else None
    missing = []
    if not py:
        missing.append("No python3 here can load Pillow, which draws the contact sheets and measures the type: "
                       "install Pillow for python3.")
    if not ff:
        missing.append("No ffmpeg was found, which encodes the film and its music: install ffmpeg so it is on PATH.")
    if not chrome:
        missing.append("No Chromium was found, which draws every frame of the film: install Chromium or Google Chrome, "
                       "or set CHROME_PATH to one.")
    if not dist:
        missing.append(f"The built composition is missing from {render.DIST}: this copy of the kit is incomplete, so "
                       "copy the kit folder again.")
    out = {"python": py, "pillow": pillow, "ffmpeg": ff, "ffprobe": fp, "chromium": chrome,
           "dist": str(dist) if dist else None, "cache": str(render.cache()), "ok": not missing}
    print(json.dumps(out, indent=2))
    for line in missing:
        print(line, file=sys.stderr)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
