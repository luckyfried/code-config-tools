"""Shared helpers for the social toolkit scripts (stdlib only).

- skill_dir(): the social/ folder, resolved from this file (no machine paths).
- tools(): runs scripts/setup.py once and returns its JSON (python, chromium, ffmpeg).
- need(*modules): make sure the current interpreter can import the modules; if not,
  re-exec this script under the toolkit venv python (installing Pillow etc. if missing).
- formats(): formats.json as a list of dicts with w, h, safe_zone, key.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
_TOOLS = None

PIP_NAMES = {"PIL": "Pillow", "imageio_ffmpeg": "imageio-ffmpeg", "playwright": "playwright"}


def skill_dir():
    return SKILL


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
    setup = SKILL / "scripts" / "setup.py"
    if setup.exists():
        try:
            p = subprocess.run([sys.executable if Path(sys.executable).exists() else "python3", str(setup)],
                               capture_output=True, text=True, timeout=900)
            out = _parse_last_json(p.stdout)
            if not out:
                sys.stderr.write("setup.py gave no JSON:\n" + p.stdout[-800:] + p.stderr[-800:] + "\n")
        except Exception as e:  # keep going with fallbacks
            sys.stderr.write(f"setup.py failed: {e}\n")
    out.setdefault("python", None)
    if not out.get("python"):
        for cand in (SKILL / ".venv" / "bin" / "python3", SKILL / ".venv" / "Scripts" / "python.exe"):
            if cand.exists():
                out["python"] = str(cand)
    if not out.get("chromium"):
        out["chromium"] = find_chromium()
    if not out.get("ffmpeg"):
        out["ffmpeg"] = shutil.which("ffmpeg")
    _TOOLS = out
    return out


def find_chromium():
    for n in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium"):
        if Path(p).exists():
            return p
    return None


def need(*modules):
    """Ensure modules import. Re-exec under the venv python if they don't."""
    missing = []
    for m in modules:
        try:
            __import__(m)
        except Exception:
            missing.append(m)
    if not missing:
        return
    if os.environ.get("SOCIAL_REEXEC") == "1":
        # Already in the venv python: install what's missing, then retry once.
        pkgs = [PIP_NAMES.get(m, m) for m in missing]
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", *pkgs],
                       check=False)
        for m in missing:
            __import__(m)  # raise a real ImportError if still missing
        return
    py = tools().get("python")
    if not py or not Path(py).exists():
        sys.exit(f"Missing python modules {missing} and no toolkit venv. Run: python3 {SKILL}/scripts/setup.py")
    env = dict(os.environ, SOCIAL_REEXEC="1")
    os.execve(py, [py, sys.argv[0], *sys.argv[1:]], env)


def chromium():
    c = tools().get("chromium")
    if not c:
        sys.exit("No Chromium found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))
    return c


def ffmpeg():
    f = tools().get("ffmpeg")
    if f:
        return f
    try:
        import imageio_ffmpeg  # noqa
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("No ffmpeg found. Run: python3 " + str(SKILL / "scripts" / "setup.py"))


# ---------------------------------------------------------------- formats
# Fallback table if formats.json is missing or has a different shape.
_FALLBACK = [
    {"key": "ig_feed_portrait", "w": 1080, "h": 1350, "safe_zone": None},
    {"key": "ig_feed_square", "w": 1080, "h": 1080, "safe_zone": None},
    {"key": "ig_story", "w": 1080, "h": 1920, "safe_zone": {"top": 250, "bottom": 320, "left": 60, "right": 60}},
    {"key": "tiktok_cover", "w": 1080, "h": 1920, "safe_zone": {"top": 220, "bottom": 400, "left": 60, "right": 220}},
    {"key": "pinterest_pin", "w": 1000, "h": 1500, "safe_zone": {"top": 40, "bottom": 180, "left": 40, "right": 40}},
    {"key": "x_post", "w": 1600, "h": 900, "safe_zone": None},
    {"key": "x_post_675", "w": 1200, "h": 675, "safe_zone": None},
    {"key": "x_header", "w": 1500, "h": 500, "safe_zone": {"top": 60, "bottom": 60, "left": 40, "right": 40}},
    {"key": "link_card", "w": 1200, "h": 630, "safe_zone": None},
    {"key": "li_post", "w": 1200, "h": 1200, "safe_zone": None},
    {"key": "li_link", "w": 1200, "h": 627, "safe_zone": None},
    {"key": "fb_cover", "w": 1640, "h": 924, "safe_zone": {"top": 40, "bottom": 300, "left": 90, "right": 90}},
    {"key": "fb_cover_2x", "w": 1640, "h": 624, "safe_zone": {"top": 0, "bottom": 0, "left": 180, "right": 180}},
    {"key": "li_banner", "w": 1584, "h": 396, "safe_zone": None},
]


def formats():
    f = SKILL / "formats.json"
    rows = []
    try:
        data = json.loads(f.read_text())
        items = data.items() if isinstance(data, dict) else ((d.get("key") or d.get("id"), d) for d in data)
        for k, d in items:
            if not isinstance(d, dict):
                continue
            w, h = d.get("w") or d.get("width"), d.get("h") or d.get("height")
            if not (w and h) and isinstance(d.get("size"), str) and "x" in d["size"]:
                w, h = map(int, d["size"].lower().split("x"))
            if w and h:
                rows.append(dict(d, key=k, w=int(w), h=int(h), safe_zone=d.get("safe_zone")))
    except Exception:
        pass
    keys = {r["key"] for r in rows}
    sizes = {(r["w"], r["h"]) for r in rows}
    for r in _FALLBACK:
        if r["key"] not in keys and (r["w"], r["h"]) not in sizes:
            rows.append(dict(r))
    return rows


def match_format(name, w, h):
    """Best formats.json row for an image name + size (filename hints pick story vs reel etc.)."""
    cands = [r for r in formats() if (r["w"], r["h"]) == (w, h)]
    if not cands:
        return None
    # "carousel-cover" is a carousel slide, not a TikTok/FB cover; don't let it trip the "cover" hint.
    n = name.lower().replace("carousel-cover", "carousel")
    hints = [("reel", "tiktok"), ("tiktok", "tiktok"), ("story", "story"), ("pin", "pinterest"),
             ("li-", "li_"), ("linkedin", "li_"), ("fb", "fb_"), ("x-", "x_"), ("twitter", "x_"), ("cover", "cover")]
    for hint, keypart in hints:
        if hint in n:
            for r in cands:
                if keypart in r["key"]:
                    return r
    return cands[0]


def out_dir(arg=None):
    return Path(arg or "out")


def build_dir():
    d = Path("build")
    d.mkdir(exist_ok=True)
    return d


def font_path(kind="bold"):
    """A bundled font file for Pillow text (captions, sheet labels). kind: bold | text."""
    fdir = SKILL / "fonts"
    prefs = {"bold": ["ArchivoBlack*.ttf", "Archivo*.ttf", "Inter*.ttf", "*.ttf"],
             "text": ["Inter*.ttf", "WorkSans*.ttf", "Manrope*.ttf", "*.ttf"]}[kind]
    for pat in prefs:
        hits = sorted(p for p in fdir.rglob(pat) if "Italic" not in p.name) if fdir.exists() else []
        if hits:
            return str(hits[0])
    return None


def pil_font(size, kind="bold", weight=None):
    from PIL import ImageFont
    p = font_path(kind)
    if p:
        try:
            f = ImageFont.truetype(p, size)
            if weight:
                try:
                    axes = f.get_variation_axes()
                    f.set_variation_by_axes([weight if a.get("name", b"") in (b"Weight", "Weight") else a["default"]
                                             for a in axes])
                except Exception:
                    pass
            return f
        except Exception:
            pass
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()
