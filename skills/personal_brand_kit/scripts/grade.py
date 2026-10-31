#!/usr/bin/env python3
"""The film's color grade, derived from the person's palette and applied to every photograph.

USAGE (from the workspace root):
    python3 S/scripts/grade.py recipe            # taste.json -> grade.json (the ffmpeg filter and why)
    python3 S/scripts/grade.py photos [FILE...]  # grade photos/*.jpg (or the files named) into public/graded/
    python3 S/scripts/grade.py show              # print the filter

The recipe:
  each photograph is first matched to the film: its own color cast taken out, and its saturation and
  exposure brought toward one level (`match`), so a cyan beach, a sepia library and a neutral room start alike;
  then shadows lean toward the hue of their darkest color, highlights toward their lightest, midtones toward the
  feed's average hue, and saturation follows how saturated their palette is (`filter`, one ffmpeg filter string,
  so every photograph gets the identical grade). The look the film wears over every frame (grain, grade,
  bloom) is the style card's finish, never this file's.
"""
import argparse
import colorsys
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path("public")
GRADED = PUBLIC / "graded"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lean(rgb, k):
    """How far a color sits from gray on each channel, scaled to a colorbalance amount."""
    m = sum(rgb) / 3
    return [max(-0.2, min(0.2, round((c - m) / 255 * k, 3))) for c in rgb]


def recipe(taste):
    sw = [s for s in (taste.get("palette", {}).get("feed") or []) if s.get("hex")]
    if not sw:
        sw = [{"hex": "#8a7560", "share": 1}]
    rgbs = [hex_rgb(s["hex"]) for s in sw]
    lum = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    dark, light = min(rgbs, key=lum), max(rgbs, key=lum)
    w = [s.get("share", 1) or 1 for s in sw]
    mean = tuple(sum(c[i] * wi for c, wi in zip(rgbs, w)) / sum(w) for i in range(3))
    sats = [colorsys.rgb_to_hsv(*(x / 255 for x in c))[1] for c in rgbs]
    sat = sum(sats) / len(sats)
    rs, gs, bs = lean(dark, 0.9)
    rm, gm, bm = lean(mean, 0.45)
    rh, gh, bh = lean(light, 0.6)
    saturation = round(max(0.78, min(1.18, 0.82 + sat * 0.55)), 3)
    f = (f"eq=contrast=1.06:saturation={saturation},"
         f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rm={rm}:gm={gm}:bm={bm}:rh={rh}:gh={gh}:bh={bh}")
    why = (f"each photograph's own cast taken out first, then shadows toward {sw[[hex_rgb(s['hex']) for s in sw].index(dark)]['hex']}, "
           f"highlights toward {sw[[hex_rgb(s['hex']) for s in sw].index(light)]['hex']}, saturation x{saturation} from a palette "
           f"saturation of {sat:.2f}")
    return {"filter": f, "why": why}


# how much of a photograph's own color cast the match takes out, and how far its saturation and exposure move toward
# the film's level: all of the cast, and nearly all the way to the level, so every photograph stands in one light
# before the shared grade tints them together
CAST, LEVEL = 1.0, 0.9
# the film's level: a photograph's mean saturation and its mean brightness, both 0-1
SATURATION, BRIGHTNESS = 0.26, 0.47


def match(img):
    """The ffmpeg filter that matches one photograph (a PIL image) to the film before the shared grade: each channel
    scaled so CAST of the cast between the channels' means goes, then the saturation and the brightness moved LEVEL
    of the way (as ratios) toward SATURATION and BRIGHTNESS."""
    import math
    small = img.convert("RGB").resize((48, 48))
    raw = small.tobytes()
    px = [(raw[i] / 255, raw[i + 1] / 255, raw[i + 2] / 255) for i in range(0, len(raw), 3)]
    mean = [sum(c[i] for c in px) / len(px) for i in range(3)]
    gray = sum(mean) / 3
    gains = [max(0.6, min(1.6, (gray / max(m, 1e-3)) ** CAST)) for m in mean]
    sat = sum(max(c) - min(c) for c in px) / len(px)
    s = max(0.55, min(1.6, (SATURATION / max(sat, 1e-3)) ** LEVEL))
    luma = sum(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in px) / len(px)
    g = max(0.7, min(1.4, (math.log(max(luma, 1e-3)) / math.log(BRIGHTNESS)) ** LEVEL))
    return (f"colorchannelmixer=rr={gains[0]:.4f}:gg={gains[1]:.4f}:bb={gains[2]:.4f},"
            f"eq=saturation={s:.4f}:gamma={g:.4f}")


def grade_file(src, dest, filt):
    """The graded copy, made under another name and moved in whole: a copy newer than grade.json is kept."""
    tmp = _env.part(dest)
    r = subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", filt, "-q:v", "2", str(tmp)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        os.replace(tmp, dest)
    return r.returncode == 0, r.stderr[-300:]


def ensure_recipe():
    g = _env.read_json("grade.json")
    if g:
        return g
    taste = _env.read_json("taste.json")
    if not taste:
        sys.exit("taste.json is missing: run research.py first")
    g = recipe(taste)
    _env.write_json("grade.json", g)
    return g


def graded_name(p):
    """The graded copy of a photos file, as a path relative to public/, the folder the renderer serves."""
    return f"graded/{Path(p).name}"


def grade_photos(files=None):
    _env.need("PIL")
    g = ensure_recipe()
    GRADED.mkdir(parents=True, exist_ok=True)
    # a photo stopped before its move is a hidden temp name beside it, never a photo
    files = [Path(f) for f in files] if files else sorted(p for p in Path("photos").glob("*.jpg") if not p.name.startswith("."))
    todo = [f for f in files if not (GRADED / f.name).exists() or (GRADED / f.name).stat().st_mtime < Path("grade.json").stat().st_mtime]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda f: (f, *grade_file(f, GRADED / f.name, g["filter"])), todo))
    bad = [(f, e) for f, ok, e in res if not ok]
    for f, e in bad:
        print(f"could not grade {f.name}: {e}", file=sys.stderr)
    return len(todo) - len(bad), len(files)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["recipe", "photos", "show"])
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()
    _env.enter()
    if a.cmd == "recipe":
        taste = _env.read_json("taste.json")
        if not taste:
            sys.exit("taste.json is missing: run research.py first")
        g = recipe(taste)
        _env.write_json("grade.json", g)
        print(g["why"])
        print("wrote grade.json")
    elif a.cmd == "photos":
        n, total = grade_photos(a.files)
        print(f"graded {n} of {total} photos into public/graded/ (the rest were already graded)")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
