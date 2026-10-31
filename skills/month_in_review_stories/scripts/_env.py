"""Shared helpers for the month-in-review scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the python3 setup.py found with Pillow.
- ffmpeg(), ffprobe(): the binaries on PATH, else setup.py's, or exit with the setup command to run.
- read_json(path, default), write_json(path, obj): JSON files, written atomically.
- start_run(), run(), writable_run(): the run's own build folder, build/<run stamp>/. gather.py starts a run; every
  later step reads and writes inside it. A step that would write into a run that has already delivered starts a new
  run from a copy of it, so a delivered build is never overwritten.
- WORKSPACE: the folder the command ran from. enter_run(path): work inside the run folder a path names, relative to
  it, as render.py --run passes it.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORKSPACE = Path.cwd()
_TOOLS = None


def enter_run(path):
    """Work inside the run folder `path` (relative to the workspace): every path a script names is relative to it."""
    run = (WORKSPACE / path).resolve()
    if not run.is_dir():
        sys.exit(f"no run at {path}: gather.py makes one and prints its folder")
    os.chdir(run)
    return run


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
        p = subprocess.run([sys.executable, str(SKILL / "scripts" / "setup.py")], capture_output=True, text=True, timeout=120)
        out = _parse_last_json(p.stdout)
        if not out:
            sys.stderr.write("setup.py gave no JSON:\n" + p.stdout[-800:] + p.stderr[-800:] + "\n")
    except Exception as e:
        sys.stderr.write(f"setup.py failed: {e}\n")
    for k in ("python", "ffmpeg", "ffprobe", "chromium", "dist"):
        out.setdefault(k, None)
    _TOOLS = out
    return out


def need(*modules):
    """Ensure modules import. Re-exec the calling script under the python3 setup.py found with them if they don't; a
    caller that is not a script file (python3 -m, an interactive session) exits naming what is missing."""
    missing = []
    for m in modules:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return
    if os.environ.get("MR_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if (not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable)
            or not Path(sys.argv[0]).is_file()):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, MR_REEXEC="1")
    os.execve(py, [py, sys.argv[0], *sys.argv[1:]], env)


def ffmpeg():
    f = shutil.which("ffmpeg") or tools().get("ffmpeg")
    if not f:
        sys.exit("No ffmpeg found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


def ffprobe():
    f = shutil.which("ffprobe") or tools().get("ffprobe")
    if not f:
        sys.exit("No ffprobe found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_text(path, text):
    """Writes `text` beside `path` and renames it into place, so a reader sees the old file or the new one, whole."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.part")
    tmp.write_text(text)
    tmp.replace(p)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


BUILD = Path("build")
LATEST = BUILD / "latest"


def _new_stamp():
    base = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stamp, n = base, 2
    while (BUILD / stamp).exists():
        stamp, n = f"{base}-{n}", n + 1
    (BUILD / stamp).mkdir(parents=True)
    write_text(LATEST, stamp + "\n")
    return BUILD / stamp


def start_run():
    """A new build folder for this run, build/<UTC stamp>/, named in build/latest."""
    return _new_stamp()


def run():
    """The current run's build folder."""
    stamp = LATEST.read_text().strip() if LATEST.exists() else ""
    if not stamp or not (BUILD / stamp).is_dir():
        sys.exit("no run in build/: run gather.py first")
    return BUILD / stamp


def delivered(r):
    """A run whose gate passed and whose out/ was handed over (deliver.py writes delivered.json)."""
    return (r / "delivered.json").exists()


def writable_run():
    """The current run's folder, or, when that run has delivered, a new run copied from it without its out/, and without
    film.json, which vouches for that out/."""
    r = run()
    if not delivered(r):
        return r
    new = _new_stamp()
    for k in r.iterdir():
        if k.name in ("out", "delivered.json", "film.json"):
            continue
        dst = new / k.name
        if k.is_dir():
            shutil.copytree(k, dst, symlinks=True)
        else:
            shutil.copy2(k, dst)
    print(f"{r} has delivered and stays as it is; this step continues in {new}", file=sys.stderr)
    return new



if __name__ == "__main__":
    print(__doc__)
