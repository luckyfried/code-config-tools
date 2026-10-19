#!/usr/bin/env python3
"""The film's color grade, derived from the person's palette and applied to every photo and clip.

USAGE (from the workspace root):
    python3 S/scripts/grade.py recipe            # build/taste.json -> build/grade.json (the ffmpeg filter and why)
    python3 S/scripts/grade.py photos [FILE...]  # grade build/photos/*.jpg (or the files named) into build/public/graded/
    python3 S/scripts/grade.py show              # print the filter

The recipe (design/grade.md has the reasoning):
  shadows lean toward the hue of their darkest color, highlights toward their lightest, midtones toward the
  feed's average hue; saturation follows how saturated their palette is; a film taste lifts the blacks and
  rolls off the whites. One ffmpeg filter string carries all of it, so a photo and a generated clip get the
  identical grade. Also writes build/public/fx/grain.png, the grain tile the renderer overlays when taste asks.
"""
import argparse
import colorsys
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path("build/public")
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
    film = bool(taste.get("texture", {}).get("grain"))
    rs, gs, bs = lean(dark, 0.9)
    rm, gm, bm = lean(mean, 0.45)
    rh, gh, bh = lean(light, 0.6)
    saturation = round(max(0.78, min(1.18, 0.82 + sat * 0.55)), 3)
    contrast = 1.04 if film else 1.08
    lift, roll = (0.05, 0.95) if film else (0.015, 0.985)
    f = (f"eq=contrast={contrast}:saturation={saturation},"
         f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rm={rm}:gm={gm}:bm={bm}:rh={rh}:gh={gh}:bh={bh},"
         f"curves=all='0/{lift} 0.5/0.5 1/{roll}'")
    why = (f"shadows toward {sw[[hex_rgb(s['hex']) for s in sw].index(dark)]['hex']}, highlights toward "
           f"{sw[[hex_rgb(s['hex']) for s in sw].index(light)]['hex']}, saturation x{saturation} from a palette "
           f"saturation of {sat:.2f}, " + ("lifted blacks and soft whites for their film look" if film else "clean blacks"))
    return {"filter": f, "why": why, "film": film}


def grain_tile(path, seed=7):
    from PIL import Image
    rnd = random.Random(seed)
    n = 512
    data = bytes(max(0, min(255, int(rnd.gauss(128, 46)))) for _ in range(n * n))
    Image.frombytes("L", (n, n), data).convert("RGB").save(path)


def grade_file(src, dest, filt):
    r = subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", filt, "-q:v", "2", str(dest)],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stderr[-300:]


def ensure_recipe():
    g = _env.read_json("build/grade.json")
    if g:
        return g
    taste = _env.read_json("build/taste.json")
    if not taste:
        sys.exit("build/taste.json is missing: run research.py first")
    g = recipe(taste)
    _env.write_json("build/grade.json", g)
    return g


def graded_name(p):
    """The graded copy of a build/photos file, as a path relative to build/public/, the folder the renderer serves."""
    return f"graded/{Path(p).name}"


def grade_photos(files=None):
    _env.need("PIL")
    g = ensure_recipe()
    GRADED.mkdir(parents=True, exist_ok=True)
    fx = PUBLIC / "fx"
    fx.mkdir(parents=True, exist_ok=True)
    if not (fx / "grain.png").exists():
        grain_tile(fx / "grain.png")
    files = [Path(f) for f in files] if files else sorted(Path("build/photos").glob("*.jpg"))
    todo = [f for f in files if not (GRADED / f.name).exists() or (GRADED / f.name).stat().st_mtime < Path("build/grade.json").stat().st_mtime]
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
    if a.cmd == "recipe":
        taste = _env.read_json("build/taste.json")
        if not taste:
            sys.exit("build/taste.json is missing: run research.py first")
        g = recipe(taste)
        _env.write_json("build/grade.json", g)
        print(g["why"])
        print("wrote build/grade.json")
    elif a.cmd == "photos":
        n, total = grade_photos(a.files)
        print(f"graded {n} of {total} photos into build/public/graded/ (the rest were already graded)")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
