#!/usr/bin/env python3
"""The color grade, derived from the person's palette and applied to every photo of the plan.

USAGE (from the workspace root):
    python3 S/scripts/grade.py recipe            # taste.json -> grade.json (the ffmpeg filter and why)
    python3 S/scripts/grade.py photos [FILE...]  # grade photos/*.jpg (or the files named) into public/graded/
    python3 S/scripts/grade.py show              # print the filter

The recipe (design/grade.md has the reasoning):
  shadows lean toward the hue of their darkest color, highlights toward their lightest, midtones toward the
  year's average hue; saturation follows how saturated their palette is; a warm palette pulls the blues and cyans
  down by how warm it is; a film taste lifts the blacks and rolls off the whites. One ffmpeg filter string carries
  all of it, so every photo gets the identical grade. Before it, each photo of the set is matched to the set: its
  saturation scaled toward the set's median and its balance moved toward the set's median warmth, so one grade lands
  on photos that already agree. grade.json is the recipe and each photo's match, read from taste.json every time it
  is used, so a taste change reaches every graded copy. The film's grain is its style card's, drawn over the whole frame
  by the composition.
"""
import statistics
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
    sw = [s for s in (taste.get("palette", {}).get("year") or []) if s.get("hex")]
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
    cool = round(max(0.0, min(0.6, (mean[0] - mean[2]) / 255 * 3)), 3)
    f = (f"eq=contrast={contrast}:saturation={saturation},"
         + (f"huesaturation=saturation={-cool}:colors=c+b:strength=5," if cool else "")
         + f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rm={rm}:gm={gm}:bm={bm}:rh={rh}:gh={gh}:bh={bh},"
         f"curves=all='0/{lift} 0.5/0.5 1/{roll}'")
    why = (f"shadows toward {sw[[hex_rgb(s['hex']) for s in sw].index(dark)]['hex']}, highlights toward "
           f"{sw[[hex_rgb(s['hex']) for s in sw].index(light)]['hex']}, saturation x{saturation} from a palette "
           f"saturation of {sat:.2f}, " + (f"blues and cyans down {cool} for a warm palette, " if cool else "")
           + ("lifted blacks and soft whites for their film look" if film else "clean blacks"))
    return {"filter": f, "why": why, "film": film, "warm": mean[0] >= mean[2]}


def measure(f):
    """A photo's mean saturation and warmth (red over blue, -1 to 1), read from a 48 px copy."""
    from PIL import Image
    with Image.open(f) as im:
        px = list(im.convert("RGB").resize((48, 48)).getdata())
    sat = sum(colorsys.rgb_to_hsv(*(c / 255 for c in p))[1] for p in px) / len(px)
    return sat, sum(p[0] - p[2] for p in px) / len(px) / 255


def matched(files, g):
    """Each photo's filter: its match to the set (saturation toward the set's median; a photo colder than the set's
    median warmed toward it under a warm palette, a warmer one cooled under a cool palette), then the one grade."""
    m = {f.name: measure(f) for f in files}
    if not m:
        return {}
    ts = statistics.median(v[0] for v in m.values())
    tw = statistics.median(v[1] for v in m.values())
    out = {}
    for name, (sat, warm) in sorted(m.items()):
        k = round(max(0.7, min(1.2, ts / max(sat, 0.02))), 3)
        w = round(max(0.0, min(0.15, (tw - warm) * 0.6)) if g["warm"] else max(-0.15, min(0.0, (tw - warm) * 0.6)), 3)
        out[name] = f"eq=saturation={k},colorbalance=rm={w}:bm={-w}," + g["filter"]
    return out


def grade_file(src, dest, filt):
    """The graded copy, made under its part name and moved onto `dest` once ffmpeg finished it: grade_photos takes a
    copy that exists and is newer than grade.json as done."""
    tmp = _env.part(dest)
    r = subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", filt, "-q:v", "2", str(tmp)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        os.replace(tmp, dest)
    else:
        tmp.unlink(missing_ok=True)
    return r.returncode == 0, r.stderr[-300:]


def ensure_recipe(files=()):
    """The recipe from taste.json as it is now, with each of `files` matched to the set; grade.json is written only
    when it changed, so its time says when the graded copies went stale."""
    taste = _env.read_json("taste.json")
    if not taste:
        sys.exit("taste.json is missing: run research.py first")
    g = recipe(taste)
    g["photos"] = matched(files, g)
    if _env.read_json("grade.json") != g:
        _env.write_json("grade.json", g)
    return g


def graded_name(p):
    """The graded copy of a photos file, as a path relative to public/, the folder the renderer serves."""
    return f"graded/{Path(p).name}"


def grade_photos(files=None):
    _env.need("PIL")
    files = [Path(f) for f in files] if files else sorted(f for f in Path("photos").glob("*.jpg") if not f.name.startswith("."))
    g = ensure_recipe(files)
    GRADED.mkdir(parents=True, exist_ok=True)
    todo = [f for f in files if not (GRADED / f.name).exists() or (GRADED / f.name).stat().st_mtime < Path("grade.json").stat().st_mtime]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda f: (f, *grade_file(f, GRADED / f.name, g["photos"][f.name])), todo))
    bad = [(f, e) for f, ok, e in res if not ok]
    for f, e in bad:
        print(f"could not grade {f.name}: {e}", file=sys.stderr)
    return len(todo) - len(bad), len(files)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["recipe", "photos", "show"])
    ap.add_argument("files", nargs="*")
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "recipe":
        g = ensure_recipe()
        print(g["why"])
        print("grade.json holds it; storyboard.py draft matches the plan's photos to it")
    elif a.cmd == "photos":
        n, total = grade_photos(a.files)
        print(f"graded {n} of {total} photos into public/graded/ (the rest were already graded)")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
