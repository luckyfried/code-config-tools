"""Shared helpers for the personal brand kit scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the python setup.py found with them.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- pil_font(size, kind, style, weight): the face a style card sets a line in, at the weight the film draws it, for
  Pillow (measuring type, contact sheets).
- read_json(path, default), write_json(path, obj): the run's files.
- enter(new=False): every script works inside one run folder, build/<run stamp>/ under the workspace, with out/ in it
  holding the deliverables. gather.py starts a run (new=True: a fresh stamp, named in build/run); every other script
  enters the run build/run names. A rerun of gather never touches a prior run's folder.
- ROOT: the workspace root (the directory the script was started in); at_root(p) resolves a path the person or the
  agent gave against it.
- WORKSPACE: the folder the command ran from. enter_run(path): work inside the run folder a path names, relative to
  it, as render.py --run passes it.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
WORKSPACE = Path.cwd()
# A script a script started (research.py runs picks.py and palette.py) inherits the run through BRAND_RUN.
ROOT = Path(os.environ["BRAND_RUN"]).parent.parent if os.environ.get("BRAND_RUN") else Path.cwd()
_TOOLS = None


def enter_run(path):
    """Work inside the run folder `path` (relative to the workspace): every path a script names is relative to it."""
    run = (WORKSPACE / path).resolve()
    if not run.is_dir():
        sys.exit(f"no run at {path}: gather.py makes one and prints its folder")
    os.chdir(run)
    return run


def at_root(p):
    """A path given on the command line or in a setting, resolved against the workspace root."""
    p = Path(p).expanduser()
    return p if p.is_absolute() else (ROOT / p)


def enter(new=False):
    """Work inside the run folder: a new one (gather) or the one build/run names. Returns it."""
    import datetime as dt
    build = ROOT / "build"
    if new:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run, k = build / stamp, 1
        while run.exists():
            k += 1
            run = build / f"{stamp}-{k}"
        run.mkdir(parents=True)
        (build / "run").write_text(run.name + "\n")
    elif os.environ.get("BRAND_RUN"):
        run = Path(os.environ["BRAND_RUN"])
    else:
        named = build / "run"
        if not named.exists():
            sys.exit(f"no run in {build}: gather.py starts one (python3 {SKILL}/scripts/gather.py)")
        run = build / named.read_text().strip()
    (run / "out").mkdir(parents=True, exist_ok=True)
    os.environ["BRAND_RUN"] = str(run)
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
    """Resolved tool paths from setup.py, once per process. Never raises; missing keys are None. A command that takes
    the render lock resolves them before it (studio.lock), so setup.py never runs under the lock."""
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
    if os.environ.get("PB_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if (not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable)
            or not Path(sys.argv[0]).is_file()):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, PB_REEXEC="1")
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


def font_file(kind="text", style=None):
    """The font file of a style card's display or text face: the card `style` names, else the one in use
    (compose.in_use)."""
    import compose
    card = compose.card(style) if style else compose.in_use()
    return SKILL / card["faces"]["display" if kind == "display" else "text"]["file"]


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


def pil_font(size, kind="text", style=None, weight=None):
    """The face a style card sets a line in (the card `style` names, else the one in use), at `size`, for Pillow, at
    the weight the film draws it: the line's weight, else its face's, on a variable file's weight axis (a static file
    is as it is)."""
    import compose
    from PIL import ImageFont
    path = font_file(kind, style)
    card = compose.card(style) if style else compose.in_use()
    w = weight or card["faces"]["display" if kind == "display" else "text"]["weight"]
    return at_weight(ImageFont.truetype(str(path), size), path, w)


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def part(path):
    """The name a file is made under before os.replace moves it in: beside it, named from it, its suffix kept for the
    tool that writes it."""
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
