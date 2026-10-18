#!/usr/bin/env python3
"""
USAGE:
    python3 scripts/setup.py
    python3 scripts/setup.py --json   # (default) print resolved paths as JSON

Idempotent dependency bootstrap for the social toolkit renderer. Resolves (installing
only what's missing) and prints:
    {
      "python": "/path/to/venv/bin/python3",
      "venv": "/path/to/.venv",
      "chromium": "/path/to/chromium-or-None",
      "chromium_kind": "system" | "playwright" | "none",
      "ffmpeg": "/path/to/ffmpeg-binary-or-None",
      "ok": true
    }

No machine-specific paths: everything is resolved relative to this skill directory,
or to a venv cached inside it (`.venv/`). Safe to call every time render.py runs;
re-running when everything is already present does no network work and returns fast.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_DIR = SKILL_DIR / ".venv"


def venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python3"


def ensure_venv():
    py = venv_python()
    if py.exists():
        return py
    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    return py


def pip_install(py, *pkgs):
    subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pkgs], check=True)


def ensure_packages(py):
    # Cheap check: try importing; only pip install if missing.
    check = subprocess.run([str(py), "-c", "import playwright, imageio_ffmpeg, PIL"], capture_output=True)
    if check.returncode != 0:
        pip_install(py, "playwright", "imageio_ffmpeg", "Pillow")


def find_system_chromium():
    # SOCIAL_CHROMIUM=/path/to/chrome forces a browser; SOCIAL_CHROMIUM=playwright skips system browsers
    # (e.g. a broken snap chromium on Linux) and uses playwright's own download.
    forced = os.environ.get("SOCIAL_CHROMIUM", "").strip()
    if forced == "playwright":
        return None
    if forced and Path(forced).exists():
        return forced
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium"):
        if Path(p).exists():
            return p
    return None


def ensure_chromium(py):
    sysc = find_system_chromium()
    if sysc:
        return sysc, "system"
    # Try playwright's own bundled chromium; install if not already cached.
    probe = subprocess.run(
        [str(py), "-c", "from playwright.sync_api import sync_playwright\n"
         "with sync_playwright() as p:\n"
         "    print(p.chromium.executable_path)"],
        capture_output=True, text=True,
    )
    exe = probe.stdout.strip()
    if probe.returncode == 0 and exe and Path(exe).exists():
        return exe, "playwright"
    subprocess.run([str(py), "-m", "playwright", "install", "chromium"], check=True)
    probe = subprocess.run(
        [str(py), "-c", "from playwright.sync_api import sync_playwright\n"
         "with sync_playwright() as p:\n"
         "    print(p.chromium.executable_path)"],
        capture_output=True, text=True,
    )
    exe = probe.stdout.strip()
    if probe.returncode == 0 and exe and Path(exe).exists():
        return exe, "playwright"
    return None, "none"


def ensure_ffmpeg(py):
    probe = subprocess.run([str(py), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        exe = probe.stdout.strip()
        if exe and Path(exe).exists():
            return exe
    sysff = shutil.which("ffmpeg")
    return sysff


def main():
    py = ensure_venv()
    ensure_packages(py)
    chromium, kind = ensure_chromium(py)
    ffmpeg = ensure_ffmpeg(py)
    out = {
        "python": str(py),
        "venv": str(VENV_DIR),
        "chromium": chromium,
        "chromium_kind": kind,
        "ffmpeg": ffmpeg,
        "ok": bool(chromium),
    }
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
