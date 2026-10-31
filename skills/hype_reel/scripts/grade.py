#!/usr/bin/env python3
"""The film's color grade, derived from the person's palette: a filter on every photograph of theirs the film casts.

USAGE (in a run; S = this skill's folder):
    python3 S/scripts/grade.py recipe            # taste.json -> grade.json (the ffmpeg filter and why)
    python3 S/scripts/grade.py show              # print the filter

The recipe (design/grade.md has the reasoning) reads both palettes in taste.json, theirs and the subject's, at
equal weight, so the film sits where the two meet and the subject keeps its own color:
  shadows lean toward the hue of the darkest color, highlights toward the lightest, midtones toward the
  average hue; saturation follows how saturated the palettes are; a film taste lifts the blacks and
  rolls off the whites. One ffmpeg filter string carries all of it, so every cast photograph gets the identical grade
  (storyboard.py draft applies it after cast.py's white balance and light); the subject's own stills and footage
  never take it. The finish over the whole frame (its grade, grain and vignette) is the style card's.
"""
import argparse
import colorsys
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path("public")


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lean(rgb, k):
    """How far a color sits from gray on each channel, scaled to a colorbalance amount."""
    m = sum(rgb) / 3
    return [max(-0.2, min(0.2, round((c - m) / 255 * k, 3))) for c in rgb]


def recipe(taste):
    pal = taste.get("palette", {})
    year = [s for s in (pal.get("year") or []) if s.get("hex")]
    prod = [s for s in (pal.get("subject") or []) if s.get("hex")]
    sw = year + prod
    if year and prod:
        ky, kp = sum(s.get("share", 1) or 1 for s in year), sum(s.get("share", 1) or 1 for s in prod)
        sw = [dict(s, share=(s.get("share", 1) or 1) / ky) for s in year] + [dict(s, share=(s.get("share", 1) or 1) / kp) for s in prod]
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["recipe", "show"])
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "recipe":
        taste = _env.read_json("taste.json")
        if not taste:
            sys.exit("taste.json is missing: run research.py first")
        g = recipe(taste)
        _env.write_json("grade.json", g)
        print(g["why"])
        print("wrote grade.json")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
