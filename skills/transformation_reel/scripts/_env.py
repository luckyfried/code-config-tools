"""Shared helpers for the transformation-reel scripts (stdlib only).

- SKILL: this skill's folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once per process and returns its JSON (python, ffmpeg, ffprobe, chromium, dist).
- need(*modules): make sure this interpreter can import the modules; if not, re-exec the calling script under the
  python3 setup.py found with them.
- ffmpeg(), ffprobe(): resolved binaries, or exit with the setup command to run.
- pil_font(size, kind, style): a style card's face for Pillow text (video captions, contact sheets).
- read_json(path, default), write_json(path, obj), write_text(path, text): files, written atomically.
- whole(path): a temp path beside `path` to write, renamed onto it once whole, so a killed write leaves the old file.
- b(*parts), cut(*parts), out(*parts): paths inside the current run, build/<run stamp>/, its cut/ (the rendered
  cut the critic scores and the gate measures) and its out/ (the deliverables, which deliver.py publishes from cut/
  only when the gate passes). build/RUN names the current run. gather.py starts a run with start_run(). Every other
  movement that writes calls open_run() first: once the current run's film is published (RUN/out/film.mp4), the next
  run starts with this one's inputs carried, so a rerun never overwrites a delivered film; until then every movement,
  the one fix's render included, writes in the same run. vote.py pick of another look is the exception: the person
  asked for that film instead, and it is made in this run.
- WORKSPACE: the folder the command ran from. enter_run(path): work inside the run folder a path names, relative to
  it, as render.py --run passes it.
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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


def pil_font(size, kind="text", weight=None, style=None):
    """The Pillow font of a style card's face (`kind` "display", else its text face) at `size` px: the card `style`,
    else the card type is being measured in (compose.use), at the weight the film draws it: `weight`, else the face's,
    on a variable file's weight axis (a static file is as it is)."""
    from PIL import ImageFont
    import compose
    c = compose.card(style) if style else compose.in_use()
    face = c["faces"]["display" if kind == "display" else "text"]
    path = SKILL / face["file"]
    return at_weight(ImageFont.truetype(str(path), size), path, weight or face["weight"])


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


@contextlib.contextmanager
def whole(path):
    """A temp path beside `path`, named from it with its suffix kept (so a tool still reads the format from it), for the
    caller to write. It is renamed onto `path` when the block ends and removed when the block raises, so `path` is only
    ever the old file or the new one whole."""
    p = Path(path)
    tmp = p.with_name(f".{p.stem}.part{p.suffix}")
    try:
        yield tmp
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, p)


def write_json(path, obj):
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def write_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with whole(p) as tmp:
        tmp.write_text(text)


RUN_FILE = Path("build") / "RUN"


def _current():
    try:
        stamp = RUN_FILE.read_text().strip()
    except OSError:
        return None
    return Path("build") / stamp if stamp and (Path("build") / stamp).is_dir() else None


B = _current()


def b(*parts):
    """A path inside the current run (relative to the workspace root)."""
    if B is None:
        sys.exit("no run in build/: movement 0 starts one (python3 " + str(SKILL / "scripts" / "gather.py") + ")")
    return B.joinpath(*parts)


def cut(*parts):
    return b("cut", *parts)


def out(*parts):
    return b("out", *parts)


# What a carried run leaves behind: the previous run's cut, its deliverables, its renders and its checks. The timing
# read and the critic's rounds carry, so a re-render after the one fix is scored as the next round.
NOT_CARRIED = ("out", "render", "qa", "cut")


def moved(old, new):
    """Every path the carried records (.json, .md) name inside the run folder `old` named inside `new` instead, as the
    absolute path and as the path from the workspace root, so the new run never reads the old one's files."""
    pairs = [(f"{old.resolve().as_posix()}/", f"{new.resolve().as_posix()}/"), (f"{old.as_posix()}/", f"{new.as_posix()}/")]
    for f in new.rglob("*"):
        if f.suffix in (".json", ".md") and f.is_file() and not f.is_symlink():
            text = was = f.read_text()
            for a, z in pairs:
                text = text.replace(a, z)
            if text != was:
                f.write_text(text)


def start_run(carry=False):
    """A new run folder build/<UTC stamp>/, named in build/RUN. With `carry`, the current run's inputs (everything but
    its deliverables and renders) are copied in, every path they name inside it moved to the new run (`moved`), so the
    next movement starts where the last run stood and reads only its own files."""
    global B
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    d, n = Path("build") / stamp, 2
    while d.exists():
        d, n = Path("build") / f"{stamp}-{n}", n + 1
    if carry and B is not None:
        shutil.copytree(B, d, symlinks=True, ignore=lambda src, names: [x for x in names if Path(src) == B and x in NOT_CARRIED])
        moved(B, d)
    d.mkdir(parents=True, exist_ok=True)
    tmp = RUN_FILE.with_name(".RUN.part")
    tmp.write_text(d.name + "\n")
    tmp.replace(RUN_FILE)
    B = d
    return d


def open_run():
    """The run a movement writes to: the current one, or the next one with the current one's inputs once the current
    run's film is published (RUN/out/film.mp4, which deliver.py writes only on a passing gate). A cut the critics sent
    back for its one fix renders again in its own run, so its second round is scored beside its first."""
    if B is not None and (B / "out" / "film.mp4").exists():
        d = start_run(carry=True)
        sys.stderr.write(f"the last run's film is delivered, so this movement writes to a new run: {d}\n")
    return B


if __name__ == "__main__":
    print(__doc__)
