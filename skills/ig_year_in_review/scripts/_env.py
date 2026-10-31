"""Shared helpers for the year-in-review scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under
  the python3 setup.py found with Pillow.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- pil_font(size, kind): the style in use's display or text face for Pillow text (contact sheets).
- read_json(path, default), write_json(path, obj), write_text(path, text): build/ files; a write lands whole, by
  os.replace from a temp name beside it, so a command stopped partway leaves the file as it was.
- stamp(): a name unique to this command's run (the UTC second and the process id), for the files an index names: a
  command writes its new set under it, publishes the index, then removes the old set.
- WORKSPACE: the folder the script was started in (the workspace root); enter_build(): moves into its build/ folder,
  where the storyboard, the music, the renders and the film's working files live under the names the studio reads
  (public/, storyboards/, music/, render/, film.json); the deliverables are ../out from there.
- enter_run(path): work inside the run folder a path names, relative to WORKSPACE, as render.py --run passes it.
"""
import json
import os
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


def enter_build():
    """Work inside the workspace's build/ folder from here on."""
    b = WORKSPACE / "build"
    b.mkdir(parents=True, exist_ok=True)
    os.chdir(b)
    return b


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
    # only a script run by its path is run again; a caller in the same process (a test runner, python -c) gets the error
    if not Path(sys.argv[0]).is_file():
        raise ModuleNotFoundError(f"python modules {missing} are missing here; scripts/setup.py's python has them")
    if os.environ.get("YIR_REEXEC") == "1":
        sys.exit(f"python modules {missing} are still missing. Run: python3 {SKILL}/scripts/setup.py")
    py = tools().get("python")
    if not py or not Path(py).exists() or os.path.abspath(py) == os.path.abspath(sys.executable):
        sys.exit(f"Missing python modules {missing}. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, YIR_REEXEC="1")
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


def font_file(kind="text", weight=None):
    """The font file a line is set in, as the film sets it: the display or text face of the style card in use
    (style.use names it)."""
    import style
    return SKILL / style.in_use()["faces"]["display" if kind == "display" else "text"]["file"]


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
    import style
    from PIL import ImageFont
    path = font_file(kind, weight)
    w = weight or style.in_use()["faces"]["display" if kind == "display" else "text"]["weight"]
    return at_weight(ImageFont.truetype(str(path), size), path, w)


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


def stamp():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + f"-{os.getpid()}"


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print(__doc__)
