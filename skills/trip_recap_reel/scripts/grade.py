#!/usr/bin/env python3
"""The photographs made one set: graded once by the look's card over the whole frame, so here they keep their own color
and are only matched to each other.

USAGE (from the workspace root; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/grade.py recipe            # grade.json: the filter every photograph and clip passes through
    python3 S/scripts/grade.py photos [FILE...]  # copy photos/*.jpg (or the files named) into public/graded/
    python3 S/scripts/grade.py match NAME...     # match the graded photos named into public/matched/
    python3 S/scripts/grade.py show              # print the filter

The film has one grade, the style card's `finish.grade`, which the stage lays over the whole frame; the recipe is
ffmpeg's null filter, so a photograph and a generated clip reach the film with the same color and the card's grade
lands on each once.

The match (storyboard.py draft runs it on the film's photographs): exposure and contrast pulled together across the
set at four fifths strength, and color, the white balance and the saturation, matched in full, so the stops read as one
film. Each photograph's mean brightness moves toward the set's by a gamma and its contrast toward the set's mean; its
saturation takes the set's mean, and the cast of its near-neutral pixels the set's average neutral cast, by bounded
per-channel gains. A photograph with too few near-neutral pixels (a sunset, a desert) keeps its cast, and a night
photograph (mean brightness under half the set's) keeps its own exposure and contrast and takes the set's color.
"""
import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path("public")
GRADED = PUBLIC / "graded"


def recipe(taste):
    """The filter the photographs and clips pass through on their way to the film: none, since the card grades the frame."""
    return {"filter": "null", "why": "the photographs keep their own color; the look's card grades the whole frame once"}


def grade_file(src, dest, filt):
    """The graded copy, made under a temporary name and moved to `dest` whole: a graded file newer than grade.json is
    taken as done, so a part of one must never stand at its name."""
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
    files = [Path(f) for f in files] if files else sorted(Path("photos").glob("[!.]*.jpg"))
    todo = [f for f in files if not (GRADED / f.name).exists() or (GRADED / f.name).stat().st_mtime < Path("grade.json").stat().st_mtime]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda f: (f, *grade_file(f, GRADED / f.name, g["filter"])), todo))
    bad = [(f, e) for f, ok, e in res if not ok]
    for f, e in bad:
        print(f"could not grade {f.name}: {e}", file=sys.stderr)
    return len(todo) - len(bad), len(files)


MATCHED = PUBLIC / "matched"
STRENGTH = 0.8


def _stats(path):
    from PIL import Image, ImageStat
    im = Image.open(path).convert("RGB")
    small = im.resize((96, 96))
    m = ImageStat.Stat(small).mean
    lum = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]
    neutral = [p for p in small.getdata() if 40 < sum(p) / 3 < 225 and max(p) - min(p) < 0.18 * max(p)]
    sat = ImageStat.Stat(small.convert("HSV")).mean[1]
    spread = ImageStat.Stat(small.convert("L")).stddev[0]
    if len(neutral) < 0.06 * 96 * 96:
        return im, lum, None, sat, spread
    nm = [sum(p[c] for p in neutral) / len(neutral) for c in range(3)]
    nl = sum(nm) / 3
    return im, lum, [c / nl for c in nm], sat, spread


def match_photos(names, k=STRENGTH):
    """public/graded/NAME -> public/matched/NAME for every name, matched across the set: exposure and contrast at
    strength `k`, color in full. What each photograph took is kept in public/matched/match.json, so a clip that plays
    on a photograph takes the same match."""
    import math
    from PIL import Image
    MATCHED.mkdir(parents=True, exist_ok=True)
    S = {n: _stats(GRADED / n) for n in dict.fromkeys(names)}
    lum_t = sum(s[1] for s in S.values()) / len(S)
    casts = [s[2] for s in S.values() if s[2]]
    cast_t = [sum(c[i] for c in casts) / len(casts) for i in range(3)] if casts else None
    sat_t = sum(s[3] for s in S.values()) / len(S)
    spread_t = sum(s[4] for s in S.values()) / len(S)
    ops = {}
    for n, (im, lum, cast, sat, spread) in S.items():
        night = lum < 0.5 * lum_t
        target = lum if night else lum + (lum_t - lum) * k
        ops[n] = {"gamma": max(0.7, min(1.4, math.log(max(1, target) / 255) / math.log(max(1, min(254, lum)) / 255))),
                  "gains": [max(0.8, min(1.25, cast_t[c] / cast[c])) if cast else 1.0 for c in range(3)],
                  "color": max(0.6, min(2.2, sat_t / max(1, sat))),
                  "contrast": 1.0 if night else max(0.85, min(1.2, (spread_t / max(1, spread)) ** k))}
        apply_match(im, ops[n]).save(_env.part(MATCHED / n), quality=94)
        os.replace(_env.part(MATCHED / n), MATCHED / n)
    _env.write_json(MATCHED / "match.json", ops)
    return len(S)


def apply_match(im, op):
    """One image through one photograph's match: its channel gains and exposure curve, then contrast and saturation."""
    from PIL import Image, ImageEnhance
    bands = [b.point([round(255 * min(1.0, i / 255 * op["gains"][c]) ** op["gamma"]) for i in range(256)])
             for c, b in enumerate(im.convert("RGB").split())]
    return ImageEnhance.Color(ImageEnhance.Contrast(Image.merge("RGB", bands)).enhance(op["contrast"])).enhance(op["color"])


def match_of(image):
    """The match the photograph at public/IMAGE took, or None when it is not a matched photograph."""
    if not str(image).startswith("matched/") or not (MATCHED / "match.json").exists():
        return None
    return (_env.read_json(MATCHED / "match.json") or {}).get(Path(image).name)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["recipe", "photos", "match", "show"])
    ap.add_argument("files", nargs="*")
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
    elif a.cmd == "photos":
        n, total = grade_photos(a.files)
        print(f"graded {n} of {total} photos into public/graded/ (the rest were already graded)")
    elif a.cmd == "match":
        print(f"matched {match_photos(a.files)} photos into public/matched/")
    else:
        print(ensure_recipe()["filter"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
