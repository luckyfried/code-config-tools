"""Shared helpers for the my-people-reel scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the python3 setup.py found with Pillow.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- enter_run(new=False): every run of the pipeline writes under its own folder, build/<run stamp>/ in the
  workspace, with out/ inside it holding the deliverables; build/current names the latest. gather.py starts a run
  (new=True); every other script enters the current one, so its paths are relative to the run folder. The commands
  that start a film (storyboard.py draft and snap) on a run that already delivered one (again=True) start a new
  run carrying everything but what a film makes, so a second film never overwrites the first. WORKSPACE is
  the folder the scripts were started from; ws(path) resolves a path given on the command line against it.
  enter_run(path) works inside the run folder a path names, relative to WORKSPACE, as render.py --run passes it.
- read_json(path, default), write_json(path, obj), write_text(path, text): files of the run. A file is written
  under part(path) beside it and put in place by os.replace, so a stopped command leaves the file before or the
  file after, never half of one.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
_TOOLS = None
WORKSPACE = Path(os.environ.get("MPR_WORKSPACE") or os.getcwd())


def ws(path):
    """A path given on the command line, resolved against the workspace."""
    return str(Path(WORKSPACE, path)) if path else path


def per_person(n):
    """How many photographs carry each person in cast.json: three each for three people or more, more for fewer
    (nine for one)."""
    return max(3, 9 // max(1, min(n, 5)))


# what a film makes in its run: the cut, the renders, the checks, the critics' rounds and the deliverables
MADE = {"out", "render", "frames", "qa", "critic", "film.json", "engine.json", "render-report.json", "render-report-final.json"}


def _new_run(build, carry=None):
    """A new build/<UTC stamp>/, named in build/current; with `carry`, a copy of that run but for what a film makes."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run, n = build / stamp, 1
    while run.exists():
        n += 1
        run = build / f"{stamp}-{n}"
    if carry:
        shutil.copytree(carry, run, symlinks=True, ignore=lambda d, names: MADE & set(names) if Path(d) == carry else set())
        sys.stderr.write(f"{carry.name} delivered its film; this one starts {run.name}, carrying its people, boards and vote\n")
    else:
        run.mkdir(parents=True)
    write_text(build / "current", run.name + "\n")
    return run


def enter_run(new=False, again=False):
    """Change into this run's folder and return it: a new build/<UTC stamp>/ when `new`, else the one build/current
    names (or the one a parent script already entered, MPR_RUN); with `again`, a run that holds out/ is carried into
    a new one first. Child scripts inherit the run. A path (relative to the folder the command ran from, as
    render.py --run passes it) names the run."""
    global WORKSPACE
    if isinstance(new, (str, Path)):
        here = (Path(WORKSPACE) / new).resolve()
        if not here.is_dir():
            sys.exit(f"no run at {new}")
        os.chdir(here)
        return here
    build = Path(WORKSPACE) / "build"
    if new:
        run = _new_run(build)
    elif os.environ.get("MPR_RUN"):
        run = Path(WORKSPACE, os.environ["MPR_RUN"])
    else:
        cur = build / "current"
        if not cur.exists():
            sys.exit("no run yet: start with gather.py (it makes build/<run stamp>/ and names it in build/current)")
        run = build / cur.read_text().strip()
    run = run.resolve()
    # a run has delivered a film once out/ holds one; the sheets' out/boards.png alone is still this film's run
    if again and (run / "out" / "film.mp4").exists():
        run = _new_run(run.parent, carry=run).resolve()
    os.environ.update(MPR_RUN=str(run), MPR_WORKSPACE=str(WORKSPACE))
    os.chdir(run)
    sys.stderr.write(f"run folder: {os.path.relpath(run, WORKSPACE)}\n")
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
    """Ensure modules import. Re-exec under the toolkit python if they don't."""
    missing = []
    for m in modules:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return
    if os.environ.get("MPR_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, MPR_REEXEC="1")
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


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def part(path):
    """The name a file is made under before os.replace puts it at `path`: beside it, hidden, named from it, and ending
    in its suffix, so a tool that reads the format from the name still writes it."""
    p = Path(path)
    return p.with_name(f".{p.stem}.part{p.suffix}")


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = part(p)
    tmp.write_text(text)
    os.replace(tmp, p)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print(__doc__)
