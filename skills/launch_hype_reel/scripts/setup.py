#!/usr/bin/env python3
"""
USAGE:
    python3 scripts/setup.py          # resolve (installing only what is missing) and print the tools as JSON

First-run setup for the best-nine toolkit. Prints:
    {"python": ".../python3", "ffmpeg": ".../ffmpeg", "ffprobe": ".../ffprobe" | null, "node": ".../node" | null,
     "motion": ".../motion" | null, "engine": "remotion" | "stills", "ok": true}

The python is the first that imports Pillow: this interpreter, else a venv inside this skill
folder (`.venv/`, or ~/.cache/ig_best_nine/venv when the skill folder is read-only). The venv is made
with `python3 -m venv`; where that has no pip it uses `uv`, else a pip-less venv plus get-pip.py. ffmpeg is the
system one, else imageio-ffmpeg's. node is the system one (18 or newer), else a portable node from nodejs.org
unpacked under the kit's data folder (`.cache/node/`). With node, `npm ci` runs in `motion/` (npm cache in
`.cache/npm/` unless npm_config_cache is set) and Remotion downloads its browser into `motion/node_modules/`;
the engine is then "remotion". Without node the engine is "stills" (film.py's fallback route) and brief.md says so.
BN_NODE=portable skips the system node; BN_NODE=none forces the stills route; BN_NODE=/path/to/node picks one.
Re-running when everything is present does no network work and returns in about a second.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
PKGS = ["Pillow"]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def venv_dir():
    d = SKILL_DIR / ".venv"
    if d.exists() or os.access(SKILL_DIR, os.W_OK):
        return d
    return Path.home() / ".cache" / "ig_best_nine" / "venv"


def venv_python(d):
    return d / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")


def imports_ok(py, mods="PIL"):
    return subprocess.run([str(py), "-c", f"import {mods}"], capture_output=True).returncode == 0


def find_uv():
    for c in (shutil.which("uv"), Path.home() / ".local/bin/uv", Path.home() / ".cargo/bin/uv"):
        if c and Path(c).exists():
            return str(c)
    return None


def make_venv(d):
    """Returns (python, installer) where installer(pkgs) installs into it."""
    py = venv_python(d)
    if py.exists() and subprocess.run([str(py), "-m", "pip", "--version"], capture_output=True).returncode == 0:
        return py, lambda pk: subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *pk], check=True)
    uv = find_uv()
    if py.exists() and uv:
        return py, lambda pk: subprocess.run([uv, "pip", "install", "-q", "--python", str(py), *pk], check=True)
    shutil.rmtree(d, ignore_errors=True)
    d.parent.mkdir(parents=True, exist_ok=True)
    log(f"setup: making a python environment in {d} (first run only)")
    if subprocess.run([sys.executable, "-m", "venv", str(d)], capture_output=True).returncode == 0:
        return make_venv(d)
    shutil.rmtree(d, ignore_errors=True)
    if uv and subprocess.run([uv, "venv", "-q", "--python", sys.executable, str(d)], capture_output=True).returncode == 0:
        return make_venv(d)
    shutil.rmtree(d, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(d)], check=True)
    getpip = d / "get-pip.py"
    with urllib.request.urlopen("https://bootstrap.pypa.io/get-pip.py", timeout=60) as r:
        getpip.write_bytes(r.read())
    subprocess.run([str(venv_python(d)), str(getpip), "-q"], check=True)
    return make_venv(d)


def ensure_python():
    if imports_ok(sys.executable):
        return Path(sys.executable)
    d = venv_dir()
    py = venv_python(d)
    if py.exists() and imports_ok(py):
        return py
    py, install = make_venv(d)
    log("setup: installing Pillow (first run only)")
    install(PKGS)
    return py


NODE_VERSION = "22.12.0"
MOTION = SKILL_DIR / "motion"


def data_dir():
    """The kit's data folder: .cache/ inside the skill, or ~/.cache/ig_best_nine when the skill is read-only."""
    d = SKILL_DIR / ".cache"
    if d.exists() or os.access(SKILL_DIR, os.W_OK):
        return d
    return Path.home() / ".cache" / "ig_best_nine"


def node_major(node):
    try:
        v = subprocess.run([str(node), "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        return int(v.lstrip("v").split(".")[0])
    except Exception:
        return 0


def portable_node():
    """A node from nodejs.org unpacked under the kit's data folder. Returns the node binary or None."""
    sysname = {"linux": "linux", "darwin": "darwin", "win32": "win"}.get(sys.platform)
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    if not sysname or not arch:
        return None
    name = f"node-v{NODE_VERSION}-{sysname}-{arch}"
    root = data_dir() / "node"
    exe = root / name / ("node.exe" if sysname == "win" else "bin/node")
    if exe.exists():
        return exe
    ext = "zip" if sysname == "win" else "tar.gz"
    url = f"https://nodejs.org/dist/v{NODE_VERSION}/{name}.{ext}"
    root.mkdir(parents=True, exist_ok=True)
    arc = root / f"{name}.{ext}"
    log(f"setup: downloading node {NODE_VERSION} into {root} (first run only)")
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            arc.write_bytes(r.read())
        if ext == "zip":
            import zipfile
            zipfile.ZipFile(arc).extractall(root)
        else:
            import tarfile
            with tarfile.open(arc) as t:
                t.extractall(root, filter="tar") if hasattr(tarfile, "data_filter") else t.extractall(root)
        arc.unlink(missing_ok=True)
    except Exception as e:
        log(f"setup: could not install node ({e})")
        return None
    return exe if exe.exists() else None


def ensure_node():
    """node 18 or newer: the system one, else a portable one. BN_NODE=portable skips the system node; BN_NODE=none
    pretends there is no node (the stills route)."""
    forced = os.environ.get("BN_NODE", "").strip()
    if forced == "none":
        return None
    if forced not in ("", "portable") and Path(forced).exists():
        return Path(forced)
    if forced != "portable":
        n = shutil.which("node")
        if n and node_major(n) >= 18:
            return Path(n)
    return portable_node()


def npm_for(node):
    d = Path(node).parent
    for c in (d / "npm", d / "npm.cmd", d / "node_modules" / "npm" / "bin" / "npm-cli.js"):
        if c.exists():
            return [str(node), str(c)] if c.suffix == ".js" else [str(c)]
    n = shutil.which("npm")
    return [n] if n else None


def ensure_motion(node):
    """npm ci in motion/ when its modules are missing or older than the lockfile, then Remotion's browser."""
    lock = MOTION / "package-lock.json"
    stamp = MOTION / "node_modules" / ".package-lock.json"
    env = dict(os.environ, PATH=f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}")
    env.setdefault("npm_config_cache", str(data_dir() / "npm"))
    env["npm_config_update_notifier"] = "false"
    if not stamp.exists() or stamp.stat().st_mtime < lock.stat().st_mtime:
        npm = npm_for(node)
        if not npm:
            log("setup: node has no npm next to it")
            return False
        log("setup: installing the motion project (npm ci in motion/, first run only)")
        r = subprocess.run([*npm, "ci", "--no-audit", "--no-fund", "--loglevel=error"], cwd=MOTION, env=env)
        if r.returncode != 0 or not stamp.exists():
            return False
    browser = MOTION / "node_modules" / ".remotion"
    if not browser.exists():
        log("setup: downloading the browser Remotion renders with (first run only)")
        cli = MOTION / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        r = subprocess.run([str(node), str(cli), "browser", "ensure"], cwd=MOTION, env=env)
        if r.returncode != 0:
            return False
    return True


def ensure_ffmpeg(py):
    ff = shutil.which("ffmpeg")
    if ff:
        return ff, shutil.which("ffprobe")
    if not imports_ok(py, "imageio_ffmpeg"):
        subprocess.run([str(py), "-m", "pip", "install", "-q", "imageio-ffmpeg"], check=False)
    r = subprocess.run([str(py), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                       capture_output=True, text=True)
    exe = r.stdout.strip()
    return (exe if r.returncode == 0 and exe and Path(exe).exists() else None), None


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    py = ensure_python()
    ffmpeg, ffprobe = ensure_ffmpeg(py)
    node = ensure_node()
    motion = bool(node) and ensure_motion(node)
    out = {"python": str(py), "ffmpeg": ffmpeg, "ffprobe": ffprobe, "node": str(node) if node else None,
           "motion": str(MOTION) if motion else None, "engine": "remotion" if motion else "stills",
           "ok": bool(ffmpeg)}
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
