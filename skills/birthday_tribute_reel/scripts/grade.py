#!/usr/bin/env python3
"""The film's color grade, derived from the person's palette and applied to every photo and clip.

USAGE (from the workspace root; B = the run's folder, build/<run stamp>/):
    python3 S/scripts/grade.py recipe            # B/taste.json -> B/grade.json (the ffmpeg filter and why)
    python3 S/scripts/grade.py photos [FILE...]  # grade B/photos/*.jpg (or the files named) into B/public/graded/
    python3 S/scripts/grade.py show              # print the filter

Before the grade, every photo is matched to one light, so photos from different cameras and days sit together: its
white balance is pulled part of the way to grey (WB; the scene keeps some of its own color), less and less toward
white, so a sun or a lamp stays white instead of turning a color, and less and less as the cast grows strong (CAST), so
a sunset or a lamp-lit room keeps the light it was taken in and only a camera's tint is taken out; its exposure part of the way to one target (EXPOSE,
the gamma bounded so a white beach stays bright and a night stays dark; a photo that measures darker than NIGHT is
pulled toward the night target instead, so it stays a night); and its saturation part of the way to one target (SAT,
bounded by SAT_RANGE, so a stock-blue sky calms and a photo already quieter than SAT keeps its own color). A
black-and-white photograph (its mean chroma under MONO) is toned in the hue of the palette the two share, its mids
the chroma of the film's quiet photographs (TONE) and its blacks and whites left neutral, so it sits in the year
as a toned print beside its colored neighbors.

The recipe (design/grade.md has the reasoning):
  shadows lean toward the hue of their darkest color, highlights toward their lightest, midtones toward the
  average hue of the photos the two share; saturation follows how saturated their palette is and never rises past the photos' own; a film taste lifts the blacks and
  rolls off the whites. One ffmpeg filter string carries all of it, so a photo and a generated clip get the
  identical grade. Also writes B/public/fx/grain.png, the grain tile the renderer overlays when taste asks.
"""
import argparse
import colorsys
import math
import random
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path(f"{_env.B}/public")
GRADED = PUBLIC / "graded"
WB, EXPOSE = 0.45, 0.6  # how far toward grey, and how far toward the target exposure, each photo is pulled
CAST = 0.5  # the chroma of a photo's mean color at which its cast is the scene's light and the white balance lets it be
DAY, NIGHT = 0.47, 0.30  # the target luma of a day photo, and of one that measures darker than NIGHT
GAMMA = (0.78, 1.35)
SAT, SAT_RANGE = 0.4, (0.5, 1.0)  # the mean saturation a louder photo is pulled toward, and the bound on the pull
MONO = 4 / 255  # a photo whose mean chroma (max - min of its channels) is under this is black and white
TONE = 30  # the chroma, of 255, a black-and-white photograph's mid gray is toned to
LUMA = (0.299, 0.587, 0.114)  # each channel's share of a color's lightness, which saturation turns about


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lean(rgb, k):
    """How far a color sits from gray on each channel, scaled to a colorbalance amount."""
    m = sum(rgb) / 3
    return [max(-0.2, min(0.2, round((c - m) / 255 * k, 3))) for c in rgb]


def recipe(taste):
    sw = [s for s in (taste.get("palette", {}).get("together") or []) if s.get("hex")]
    if not sw:
        sw = [{"hex": "#8a7560", "share": 1}]
    rgbs = [hex_rgb(s["hex"]) for s in sw]
    lum = lambda c: sum(w * x for w, x in zip(LUMA, c))
    dark, light = min(rgbs, key=lum), max(rgbs, key=lum)
    w = [s.get("share", 1) or 1 for s in sw]
    mean = tuple(sum(c[i] * wi for c, wi in zip(rgbs, w)) / sum(w) for i in range(3))
    sats = [colorsys.rgb_to_hsv(*(x / 255 for x in c))[1] for c in rgbs]
    sat = sum(sats) / len(sats)
    film = bool(taste.get("texture", {}).get("film"))
    rs, gs, bs = lean(dark, 0.9)
    rm, gm, bm = lean(mean, 0.45)
    rh, gh, bh = lean(light, 0.6)
    saturation = round(max(0.78, min(1.0, 0.72 + sat * 0.5)), 3)
    off = [c - sum(mean) / 3 for c in mean]
    span = max(off) - min(off)
    tone = [round(c / span * TONE, 1) for c in off] if span > 1 else [TONE / 2, 0.0, -TONE / 2]
    contrast = 1.04 if film else 1.08
    lift, roll = (0.05, 0.95) if film else (0.015, 0.985)
    # contrast and saturation in RGB: a YUV saturation tints a gray green and a clipped yellow lime
    mix = ":".join(f"{o}{i}={round(w * (1 - saturation) + (saturation if o == i else 0), 4)}"
                   for o in "rgb" for i, w in zip("rgb", LUMA))
    f = (f"lutrgb=r=(val-128)*{contrast}+128:g=(val-128)*{contrast}+128:b=(val-128)*{contrast}+128,"
         f"colorchannelmixer={mix},"
         f"colorbalance=rs={rs}:gs={gs}:bs={bs}:rm={rm}:gm={gm}:bm={bm}:rh={rh}:gh={gh}:bh={bh},"
         f"curves=all='0/{lift} 0.5/0.5 1/{roll}'")
    why = (f"shadows toward {sw[[hex_rgb(s['hex']) for s in sw].index(dark)]['hex']}, highlights toward "
           f"{sw[[hex_rgb(s['hex']) for s in sw].index(light)]['hex']}, saturation x{saturation} from a palette "
           f"saturation of {sat:.2f}, " + ("lifted blacks and soft whites for their film look" if film else "clean blacks"))
    return {"filter": f, "why": why, "film": film, "tone": tone}


def grain_tile(path, seed=7):
    from PIL import Image
    rnd = random.Random(seed)
    n = 512
    data = bytes(max(0, min(255, int(rnd.gauss(128, 46)))) for _ in range(n * n))
    tmp = Path(path).with_name(f".{Path(path).name}.part")
    Image.frombytes("L", (n, n), data).convert("RGB").save(tmp, "PNG")
    os.replace(tmp, path)


def match_light(src, dest, tone=None):
    """The photo matched to one light (white balance, exposure and saturation, see the top of this file), a
    black-and-white one toned by `tone` (the recipe's offset of each channel at mid gray), saved losslessly at dest."""
    from PIL import Image, ImageEnhance, ImageStat
    im = Image.open(src).convert("RGB")
    small = im.copy()
    small.thumbnail((256, 256))
    r, g, b = ImageStat.Stat(small).mean
    s = ImageStat.Stat(small.convert("HSV")).mean[1] / 255
    grey = (r + g + b) / 3
    wb = WB * max(0.0, 1 - (max(r, g, b) - min(r, g, b)) / max(r, g, b, 1) / CAST)
    gains = [(grey / max(c, 1)) ** wb for c in (r, g, b)]
    lum = (0.2126 * r * gains[0] + 0.7152 * g * gains[1] + 0.0722 * b * gains[2]) / 255
    target = NIGHT if lum < NIGHT else DAY
    gamma = min(GAMMA[1], max(GAMMA[0], 1 + (math.log(target) / math.log(max(min(lum, 0.98), 0.02)) - 1) * EXPOSE))
    lut = []
    for k in gains:
        lut += [min(255, round(255 * (min(1.0, v * (1 + (k - 1) * (1 - (v / 255) ** 2)) / 255) ** gamma))) for v in range(256)]
    pull = min(SAT_RANGE[1], max(SAT_RANGE[0], (SAT / max(s, 0.01)) ** EXPOSE))
    im = im.point(lut)
    if tone and chroma(small) < MONO:
        bell = [4 * (v / 255) * (1 - v / 255) for v in range(256)]
        im = im.point([min(255, max(0, round(v + k * bell[v]))) for k in tone for v in range(256)])
    ImageEnhance.Color(im).enhance(pull).save(dest)


def chroma(im):
    """The mean chroma of a photo, max - min of its channels, as a share of 255."""
    px = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
    return sum(max(p) - min(p) for p in px) / max(1, im.width * im.height) / 255


def grade_file(src, dest, filt, tone=None):
    """The graded photograph, moved in under dest whole once it is written. ffmpeg grades into a lossless png and PIL
    encodes the jpeg: ffmpeg's own jpeg rounds a clipped yellow's red down and its green up, a lime sun."""
    from PIL import Image
    tmp = Path(dest).with_suffix(".match.png")
    png = Path(dest).with_name(f".{Path(dest).name}.part.png")
    part = Path(dest).with_name(f".{Path(dest).name}.part.jpg")
    try:
        match_light(src, tmp, tone)
        r = subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(tmp), "-vf", filt, str(png)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            Image.open(png).convert("RGB").save(part, "JPEG", quality=95, subsampling=0)
            os.replace(part, dest)
        return r.returncode == 0, r.stderr[-300:]
    except Exception as e:
        return False, str(e)[-300:]
    finally:
        for f in (tmp, png, part):
            f.unlink(missing_ok=True)


def ensure_recipe():
    g = _env.read_json(f"{_env.B}/grade.json")
    if g:
        return g
    taste = _env.read_json(f"{_env.B}/taste.json")
    if not taste:
        sys.exit(f"{_env.B}/taste.json is missing: run research.py first")
    g = recipe(taste)
    _env.write_json(f"{_env.B}/grade.json", g)
    return g


def graded_name(p):
    """The graded copy of a B/photos file, as a path relative to B/public/, the folder the renderer serves."""
    return f"graded/{Path(p).name}"


def grade_photos(files=None):
    _env.need("PIL")
    g = ensure_recipe()
    GRADED.mkdir(parents=True, exist_ok=True)
    fx = PUBLIC / "fx"
    fx.mkdir(parents=True, exist_ok=True)
    if not (fx / "grain.png").exists():
        grain_tile(fx / "grain.png")
    files = [Path(f) for f in files] if files else sorted(Path(f"{_env.B}/photos").glob("*.jpg"))
    todo = [f for f in files if not (GRADED / f.name).exists() or (GRADED / f.name).stat().st_mtime < Path(f"{_env.B}/grade.json").stat().st_mtime]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda f: (f, *grade_file(f, GRADED / f.name, g["filter"], g.get("tone"))), todo))
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
        taste = _env.read_json(f"{_env.B}/taste.json")
        if not taste:
            sys.exit(f"{_env.B}/taste.json is missing: run research.py first")
        g = recipe(taste)
        _env.write_json(f"{_env.B}/grade.json", g)
        print(g["why"])
        print(f"wrote {_env.B}/grade.json")
    elif a.cmd == "photos":
        n, total = grade_photos(a.files)
        print(f"graded {n} of {total} photos into {GRADED}/ (the rest were already graded)")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
