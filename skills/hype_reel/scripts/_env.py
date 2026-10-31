"""Shared helpers for the hype reel scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under the
  python3 setup.py found with them.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- font_file(kind), pil_font(size, kind, weight): the display or text face of the style in use (compose.in_use), for
  Pillow text, at the weight the film draws it.
- read_json(path, default), write_json(path, obj): the run's files.
- enter_run(path=None, new=False): every script works inside one run folder, build/<run stamp>/ under the workspace
  root, with out/ in it holding the deliverables. gather.py starts a new run (enter_run(new=True)); every later step
  works in the run that build/current names (LH_RUN, a stamp or a path, names another), and a `path` (render.py --run)
  names the run itself and never starts one. ROOT is the workspace root; WORKSPACE is the folder the command was run
  from (LH_ROOT in a step's child).
- fork_run(drop): a new run folder that starts as a copy of this one without the files named in `drop`, so a second
  film (a recut) never overwrites the first.
- engine(): the tools a render needs, resolved before a command takes the run's lock (chunks.lock).
- render(run, jobs, report): the jobs (videos and stills of the built composition, motion/dist) rendered by
  scripts/render.py from the run's public/ folder through scripts/chunks.py under the lock `run` holds; returns the
  render report (failed
  jobs and the FONT_ERROR, IMAGE_ERROR and RENDER_ERROR findings, a graphics context lost or a shader that failed to
  validate among the last). A video job carries its length in `frames` and renders in chunks kept in render/chunks/,
  so the same command run again after an interruption renders only the chunks still missing.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import chunks

SKILL = Path(__file__).resolve().parent.parent
ROOT = None
WORKSPACE = Path(os.environ.get("LH_ROOT") or Path.cwd()).resolve()
_TOOLS = None


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
    if os.environ.get("LH_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if (not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable)
            or not Path(sys.argv[0]).is_file()):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, LH_REEXEC="1")
    os.execve(py, [py, sys.argv[0], *sys.argv[1:]], env)


def ffmpeg():
    f = tools().get("ffmpeg")
    if not f:
        sys.exit("No ffmpeg found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


def ffprobe():
    f = tools().get("ffprobe")
    if not f:
        f = shutil.which("ffprobe")
    if not f:
        sys.exit("No ffprobe found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return f


def font_file(kind="text"):
    """The display or text face file of the style in use."""
    import compose
    return SKILL / compose.in_use()["faces"]["display" if kind == "display" else "text"]["file"]


def weight_axis(path):
    """The place of the weight axis (tag `wght`) among a font file's variation axes, read from its fvar table, or None
    for a file with no weight axis. Pillow lists the axes in this order and names them, but never by tag."""
    import struct
    b = Path(path).read_bytes()
    tables = {b[12 + 16 * i:16 + 16 * i]: struct.unpack(">I", b[20 + 16 * i:24 + 16 * i])[0]
              for i in range(struct.unpack(">H", b[4:6])[0])}
    if b"fvar" not in tables:
        return None
    o = tables[b"fvar"]
    first, _, count, size = struct.unpack(">HHHH", b[o + 4:o + 12])
    tags = [b[o + first + i * size:o + first + i * size + 4] for i in range(count)]
    return tags.index(b"wght") if b"wght" in tags else None


def at_weight(f, path, weight):
    """Pillow font `f`, opened from `path`, set to `weight` on its weight axis (clamped to the axis); a file with no
    weight axis is as it is."""
    axis = weight_axis(path)
    if axis is None:
        return f
    axes = f.get_variation_axes()
    f.set_variation_by_axes([min(a["maximum"], max(a["minimum"], weight)) if i == axis else a["default"]
                             for i, a in enumerate(axes)])
    return f


def pil_font(size, kind="text", weight=None):
    """The face a line is set in, at `size`, for Pillow, at the weight the film draws it: the line's weight, else its
    face's, on a variable file's weight axis (a static file is as it is)."""
    import compose
    from PIL import ImageFont
    path = font_file(kind)
    w = weight or compose.in_use()["faces"]["display" if kind == "display" else "text"]["weight"]
    return at_weight(ImageFont.truetype(str(path), size), path, w)


def _stamp(build):
    import datetime as dt
    base = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name, n = base, 1
    while (build / name).exists():
        n += 1
        name = f"{base}-{n}"
    return name


def _point(build, name):
    """build/current names the run in use: a link to its folder, or a file holding its name where links are refused."""
    cur = build / "current"
    if cur.is_symlink() or cur.is_file():
        cur.unlink()
    try:
        cur.symlink_to(name, target_is_directory=True)
    except OSError:
        cur.write_text(name)


def current_run(root=None):
    """The folder of the run in use under `root`, or None."""
    root = Path(root or ROOT or Path.cwd())
    want = os.environ.get("LH_RUN")
    if want:
        p = Path(want)
        p = p if p.is_absolute() else (root / "build" / want if (root / "build" / want).is_dir() else root / want)
        return p.resolve() if p.is_dir() else None
    cur = root / "build" / "current"
    if cur.is_symlink():
        return cur.resolve() if cur.resolve().is_dir() else None
    if cur.is_file():
        p = root / "build" / cur.read_text().strip()
        return p if p.is_dir() else None
    return None


def enter_run(path=None, new=False):
    """Moves into the run folder and returns it: the run `path` names when given (a folder under the workspace, or a
    run's stamp under build/), else a new build/<run stamp>/ when `new`, else the one build/current names."""
    global ROOT
    if ROOT is None:
        ROOT = Path(os.environ.get("LH_ROOT") or Path.cwd()).resolve()
    build = ROOT / "build"
    if path:
        p = Path(path)
        p = p if p.is_absolute() else (ROOT / p if (ROOT / p).is_dir() else build / p)
        if not p.is_dir():
            sys.exit(f"no run at {path}: gather.py starts one under build/")
        return _enter(p.resolve())
    if new:
        build.mkdir(parents=True, exist_ok=True)
        name = _stamp(build)
        (build / name).mkdir()
        _point(build, name)
        run = build / name
    else:
        run = current_run(ROOT)
        if run is None:
            sys.exit("no run in this workspace: start one with python3 " + str(SKILL / "scripts" / "gather.py"))
    return _enter(run)


def _enter(run):
    """The scripts a step starts (research runs stats, picks and palette) inherit the run through LH_ROOT and LH_RUN."""
    os.environ["LH_ROOT"] = str(ROOT)
    os.environ["LH_RUN"] = str(run)
    os.chdir(run)
    return run


def fork_run(drop):
    """A new run beside the current one holding a copy of everything in it except the names in `drop` (top-level files
    or folders; links stay links). Moves into it and returns it."""
    here = Path.cwd().resolve()
    build = here.parent
    name = _stamp(build)
    dst = build / name
    shutil.copytree(here, dst, symlinks=True, ignore=lambda d, names: [n for n in names if Path(d) == here and n in drop])
    _point(build, name)
    return _enter(dst)


RENDERER = SKILL / "scripts" / "render.py"
DIST = SKILL / "motion" / "dist"


def engine():
    """The resolved tools of a render, or exit naming what is missing. A command calls it before it takes the run's
    lock, so setup.py never runs as a child the lock does not reach."""
    t = tools()
    if not t.get("chromium") or not t.get("dist"):
        sys.exit(f"the film cannot render here: python3 {SKILL}/scripts/setup.py says what is missing")
    return t


def render(run, jobs, report):
    """Renders `jobs` (videos and stills of the built composition) from the run's public/ folder through
    scripts/chunks.py inside the `run` a command holds (chunks.lock), writes the report to `report` and returns it.
    render/<run name>.log carries the renderer's progress and render/<run name>.renderer.json its own report, with its
    per-job seconds."""
    t = engine()

    def invoke(pending, spawn):
        own = run.render_dir / f"{run.name}.renderer.json"
        own.unlink(missing_ok=True)
        jf = run.render_dir / f"{run.name}.jobs.json"
        write_json(jf, {"publicDir": str(Path("public").resolve()), "report": str(own), "jobs": pending,
                        "ffmpeg": ffmpeg(), "chromium": t["chromium"]})
        line = f"render {run.name}: {len(pending)} jobs to render"
        print(f"{line}; progress in {run.render_dir / (run.name + '.log')}", flush=True)
        with open(run.render_dir / f"{run.name}.log", "w") as log:
            log.write(line + "\n")
            log.flush()
            code = spawn([sys.executable, str(RENDERER), "--jobs", str(jf.resolve())], stdout=log,
                         stderr=subprocess.STDOUT, env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1")).returncode
        return read_json(own) or chunks.unreported(pending, code, run.render_dir / f"{run.name}.log")

    rep = chunks.render(run, jobs, "public", [DIST], ffmpeg(), ffprobe(), invoke)
    write_json(report, rep)
    return rep


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


def staged(path):
    """The name a file is made under beside `path`, unique to that destination and keeping its suffix (ffmpeg picks
    the format from it). The made file reaches `path` by os.replace, so a command killed partway leaves no half file
    where the next command reads."""
    p = Path(path)
    return p.with_name(f".{p.stem}.part{p.suffix}")


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = staged(p)
    tmp.write_text(text)
    os.replace(tmp, p)


if __name__ == "__main__":
    print(__doc__)
