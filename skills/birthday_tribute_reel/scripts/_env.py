"""Shared helpers for the birthday tribute scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under the
  python3 setup.py found with them.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- read_json(path, default), write_json(path, obj), write_text(path, text): build/ files; a write lands whole, by
  os.replace from a temp name beside it, so a command stopped partway leaves the file as it was.
- digest(obj): a short hash of a JSON value, so a later step can tell whether a beat changed.
- start_run(), B: every run of the pipeline works in a folder of its own, build/<run stamp>/ (UTC, for example
  build/20261020T151200Z/), and build/latest names the current one. gather.py starts a run; every later script works
  in B, the current run's folder. A delivered run (deliver.py writes delivered.json in it) is never written again: the
  next kit command copies it to a new stamp and works there, so a rerun never overwrites a prior build. The one
  exception is `vote.py pick`, the person choosing another look: it reopens the delivered run in place, and the kit's
  sequence from the pick makes that look's film in the same folder. Importing this
  module, or reading B from anything but a kit command, copies nothing and renames nothing. out/ holds the
  deliverables of the latest delivered run, and each delivered run keeps its own in B/out/.
- WORKSPACE: the folder the command ran from. enter_run(path): work inside the run folder a path names, relative to
  it, as render.py --run passes it.
"""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORKSPACE = Path.cwd()
_TOOLS = None
BUILD = Path("build")
_RUN = None


def enter_run(path):
    """Work inside the run folder `path` (relative to the workspace): every path a script names is relative to it, and
    B is that folder."""
    global _RUN
    run = (WORKSPACE / path).resolve()
    if not run.is_dir():
        sys.exit(f"no run at {path}: gather.py makes one and prints its folder")
    os.chdir(run)
    _RUN = Path(".")
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
    if os.environ.get("BT_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if (not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable)
            or not Path(sys.argv[0]).is_file()):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, BT_REEXEC="1")
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


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.part")
    tmp.write_text(text)
    os.replace(tmp, p)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def _stamp():
    """A run folder name under build/ that no folder has yet."""
    import datetime
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d, n = BUILD / stamp, 1
    while d.exists():
        n += 1
        d = BUILD / f"{stamp}-{n}"
    return d


def _name_latest(d):
    """build/latest names d, replaced whole, once d holds everything the next script reads."""
    tmp = BUILD / f".latest.{d.name}.part"  # d's name is unique, so two commands naming runs never share a temp
    tmp.write_text(d.name + "\n")
    os.replace(tmp, BUILD / "latest")


def start_run():
    """A new run folder under build/, named in build/latest; the scripts after this one work in it."""
    global _RUN
    _RUN = _stamp()
    _RUN.mkdir(parents=True)
    _name_latest(_RUN)
    return _RUN


def _kit_command():
    """Whether this process is one of the kit's own commands (python3 S/scripts/<name>.py)."""
    return bool(sys.argv and sys.argv[0]) and Path(sys.argv[0]).resolve().parent == SKILL / "scripts"


def _picks_a_look():
    """Whether this process is `vote.py pick`, which makes another look's film in the run it was delivered from."""
    return Path(sys.argv[0]).name == "vote.py" and sys.argv[1:2] == ["pick"]


def run_dir():
    """The current run's folder. A kit command run after delivery copies the delivered run to a new stamp first and
    works in the copy; anything else that reads the run (an import, a test, a look at a delivered build) reads it where
    it is and changes nothing."""
    global _RUN
    if _RUN is not None:
        return _RUN
    latest = BUILD / "latest"
    d = BUILD / latest.read_text().strip() if latest.exists() else None
    if not d or not d.is_dir():
        sys.exit("no run in build/: run gather.py first")
    if (d / "delivered.json").exists() and _kit_command() and _picks_a_look():
        import shutil
        (d / "delivered.json").unlink()
        shutil.rmtree(d / "out", ignore_errors=True)
        sys.stderr.write(f"{d} was delivered; it is reopened for the look you picked\n")
    elif (d / "delivered.json").exists() and _kit_command():
        import shutil
        new = _stamp()
        shutil.copytree(d, new, symlinks=True, ignore=shutil.ignore_patterns("delivered.json", "out"))
        _name_latest(new)
        sys.stderr.write(f"{d} was delivered; this run continues in a copy, {new}\n")
        d = new
    _RUN = d
    return d


def __getattr__(name):
    if name == "B":
        return str(run_dir())
    raise AttributeError(name)


if __name__ == "__main__":
    print(__doc__)
