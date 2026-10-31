"""Shared helpers for the trip recap scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the first python3 setup.py found with them.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- pil_font(size, kind): a bundled font for Pillow text (video captions, contact sheets).
- enter_run(new): every command works inside one run's folder, build/<run stamp>/ under the workspace root, and
  every path a script names (trip.json, public/, out/film.mp4) is inside it. gather.py starts a run (a new stamp,
  written to build/RUN); every later command enters the run that TR_RUN names, else the one build/RUN names. A
  rerun starts a new folder, so no run ever overwrites another's build.
  enter_run(path) works inside the run folder a path names, relative to WORKSPACE (the folder the command ran
  from), as render.py --run passes it.
- home_path(p): a path the person or the agent named, read against the workspace root.
- read_json(path, default), write_json(path, obj), write_text(path, text): the run's files; a write moves the whole
  file in by rename, so a killed command leaves the earlier file or the new one, never part of one.
- part(path): the temporary name a file is made under beside its destination, unique to that destination, its
  extension kept so ffmpeg and Pillow read the format from it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORKSPACE = Path.cwd()
HOME = Path(os.environ.get("TR_HOME") or Path.cwd()).resolve()
_TOOLS = None


def enter_run(new=False):
    """Change into the run's folder (build/<stamp>/ under HOME) and return it; `new` starts a fresh run. A path (relative
    to the folder the command ran from, as render.py --run passes it) names the run."""
    if isinstance(new, (str, Path)):
        here = (Path(WORKSPACE) / new).resolve()
        if not here.is_dir():
            sys.exit(f"no run at {new}")
        os.chdir(here)
        return here
    import datetime as dt
    runs = HOME / "build"
    pointer = runs / "RUN"
    if new:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        base, n = stamp, 1
        while (runs / stamp).exists():
            n += 1
            stamp = f"{base}-{n}"
        (runs / stamp).mkdir(parents=True)
        pointer.write_text(stamp + "\n")
    else:
        stamp = os.environ.get("TR_RUN") or (pointer.read_text().strip() if pointer.exists() else "")
        if not stamp or not (runs / stamp).is_dir():
            sys.exit(f"no run in {runs}: start one with python3 {SKILL}/scripts/gather.py")
    here = runs / stamp
    if Path.cwd().resolve() != here.resolve():
        os.chdir(here)
        sys.stderr.write(f"run {here}\n")
    os.environ.update(TR_RUN=stamp, TR_HOME=str(HOME))
    return here


def home_path(p):
    """A path the person or the agent named: absolute as given, else from the workspace root."""
    p = Path(p).expanduser()
    return p if p.is_absolute() else HOME / p


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
    if os.environ.get("TR_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if (not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable)
            or not Path(sys.argv[0]).is_file()):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, TR_REEXEC="1")
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


def pil_font(size, kind="text", look=None):
    """A face of a look's card at `size` px for a still the kit draws itself: its display face (`kind` "display") or its
    text face, of the look named, else of the first of the trio, at the face's weight on a variable file's weight axis
    (a static file is as it is)."""
    from PIL import ImageFont
    import style
    face = style.card(look or style.TRIO[0])["faces"]["display" if kind == "display" else "text"]
    path = SKILL / face["file"]
    return at_weight(ImageFont.truetype(str(path), size), path, face["weight"])


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def part(path):
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
