"""Shared helpers for the best-nine scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, node, motion, engine).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the toolkit's python (setup.py makes it and installs Pillow on first run).
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- pil_font(size, kind): a bundled font for Pillow text (video captions, contact sheets).
- read_json(path, default), write_json(path, obj): a run's files, written atomically.
- new_run(), enter_run(path): a run is one folder, build/<UTC stamp>/, holding everything the run writes, with the
  deliverables in its out/. gather.py makes it; every later script takes --run and works inside it, so a rerun never
  overwrites a prior build. WORKSPACE is the folder the command was run from.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORKSPACE = Path.cwd()
_TOOLS = None


def new_run():
    """A new run folder under the workspace's build/, named for the UTC second it starts."""
    import datetime as dt
    import time
    while True:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run = WORKSPACE / "build" / stamp
        try:
            run.mkdir(parents=True)
            return run
        except FileExistsError:
            time.sleep(1)


def enter_run(path):
    """Work inside the run folder `path` (relative to the workspace): every path a script names is relative to it."""
    run = (WORKSPACE / path).resolve()
    if not (run / "library.json").exists() and not run.is_dir():
        sys.exit(f"no run at {path}: gather.py makes one and prints its folder")
    os.chdir(run)
    return run


def run_arg(ap):
    ap.add_argument("--run", required=True, help="the run folder gather.py printed, for example build/20261020T120000Z")


def _parse_last_json(text):
    i = text.rfind("\n{")
    i = 0 if (i < 0 and text.lstrip().startswith("{")) else i + 1
    try:
        return json.loads(text[i:])
    except Exception:
        return {}


def tools():
    """Resolved tool paths from setup.py. Never raises; missing keys are None."""
    global _TOOLS
    if _TOOLS is not None:
        return _TOOLS
    out = {}
    try:
        p = subprocess.run([sys.executable, str(SKILL / "scripts" / "setup.py")], capture_output=True, text=True, timeout=1200)
        out = _parse_last_json(p.stdout)
        if not out:
            sys.stderr.write("setup.py gave no JSON:\n" + p.stdout[-800:] + p.stderr[-800:] + "\n")
    except Exception as e:
        sys.stderr.write(f"setup.py failed: {e}\n")
    for k in ("python", "ffmpeg", "ffprobe", "node", "motion", "engine"):
        out.setdefault(k, None)
    _TOOLS = out
    return out


def need(*modules):
    """Ensure modules import. Re-exec under the toolkit python if they don't."""
    missing = []
    for m in modules:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return
    if os.environ.get("BN_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, BN_REEXEC="1")
    os.execve(py, [py, sys.argv[0], *sys.argv[1:]], env)


def ffmpeg():
    f = tools().get("ffmpeg")
    if not f:
        sys.exit("No ffmpeg found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


def ffprobe():
    f = tools().get("ffprobe")
    if not f:
        import shutil
        f = shutil.which("ffprobe")
    if not f:
        sys.exit("No ffprobe found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


FONT_FILES = {
    "display": SKILL / "fonts" / "ArchivoBlack" / "ArchivoBlack-Regular.ttf",
    "label": SKILL / "fonts" / "Archivo" / "Archivo[wdth,wght].ttf",
    "text": SKILL / "fonts" / "Inter" / "Inter[opsz,wght].ttf",
}


def pil_font(size, kind="text", weight=None):
    from PIL import ImageFont
    f = ImageFont.truetype(str(FONT_FILES[kind]), size)
    if weight:
        try:
            axes = f.get_variation_axes()
            f.set_variation_by_axes([weight if a.get("name") in (b"Weight", "Weight") else a["default"] for a in axes])
        except Exception:
            pass
    return f


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.part")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    tmp.replace(p)


if __name__ == "__main__":
    print(__doc__)
