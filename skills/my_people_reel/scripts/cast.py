#!/usr/bin/env python3
"""Movement 1, the cast: which photographs carry each person, where in each the person is, and all of them matched
to one light before anything is placed.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/cast.py draft              # R/cast.json from picks.json and people.json, for you to correct
    python3 S/scripts/cast.py match [--cast F]   # R/public/: every cast photograph matched, the fonts and the grain

cast.json, one entry per person in rank order and the one photograph of them together:
    {"group": {"file": ..., "point": [u, v], "heads": {"handle": [u, v], ...}, "month": 4, "keep_light": false, "shot": "..."},
     "people": {"handle": [{"file": ..., "point": [u, v], "tip": [u, v], "face": [u0, v0, u1, v1],
                            "close": 1.0 | {"frame": 1.25, "bar": 2.2, "slice": 1.0}, "keep_light": false, "shot": "...",
                            "trim": [u0, v0, u1, v1]}, ...]}}
Points are fractions of the photograph's width and height. `point` is what a crop keeps in view (the face, or the
person when no face shows); `tip` is where their tag points (default: point), and the tag stands under it, so on a
figure small in its photograph (a surfer on the shoreline, a walker on a hill) the tip goes at their feet and the tag
stands on the ground below them, never over them; `face` a box that a crop at rest
must show whole, brow to chin and ear to ear (never the hair or a hat above it); `close` how much closer than the widest fill a small frame sits (a film frame, a chart bar, a
slice); `keep_light` keeps a photograph's own lightness (a sunset silhouette, a night lit by a fire) and moves
only its color; `trim` is the part of a photograph the film keeps, its corners as fractions of the whole, to leave
out someone else's mark at its edge (a photographer's watermark) when no other photograph of the person shows them, and
every point stays a place on the whole photograph. A person's first photograph is the one they are named on; up to three per person for three people
or more, four each for two, nine for one (a film about fewer people shows more of each).
`heads` are the people's heads in the group photograph, for their tags; a person not in it has none.
`shot` is the clip the photograph would become, in one sentence of your own from looking at it: who or what moves
in it and how (hair lifting in the wind off the water, the crowd's hands rising as the stage light sweeps the
haze); the clip request adds the lens, the height and the light measured from the photograph, the camera's own
small move, the beat's length and the loop. The group and each person's first photograph carry one.

draft starts each person from their best photograph (picks.json) and more of them, alone first, and the group
from the photograph with the most of them in it, its heads spread evenly: look at each photograph and correct the
points, heads and faces before match. A file name resolves against R; with PEOPLE_PHOTOS set, against that folder.
match writes public/matched/<handle>-<n>.jpg and group.jpg (each moved most of the way to the set's black and white
points and its colorfulness, its color cast most of the way to the warmth of the year palette, so every photograph
reads as one set; the style's own grade is laid over the whole film as it renders), aspects.json, and
copies the fonts and the grain tile into public/ (the folder the renderer serves). A photograph as wide as it is tall
or wider, and the photograph of them together whatever its shape short of 9:16, is framed: laid whole across a 9:16
picture over a blurred, darkened copy of itself that fills the rest, so no frame crops its sides and every head in the
group is in every format's frame; its aspects.json entry is {"aspect": 16/9, "band": [v0, v1]}, the band the photograph
spans as fractions of the picture's height, and the boards place its points, tips, faces and heads inside that band.
The film shows only the band: the style mounts the photograph on its own ground (board_drive.Look.mount), and the
blurred copy is what an image-to-video model sees around it. Every other entry is the photograph's height over its
width. aspects.json is the index of public/matched/: match
removes it before the first photograph changes and writes it after the last.
"""
import argparse
import datetime as dt
import math
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

LONG = 2400
# a framed photograph's picture: 9:16, no wider than this; its blurred copy, darkened to this share of its light
TALL = 16 / 9
FRAMED_W = 1350
BLUR = 0.04
DIM = 0.5
# how far each photograph moves to the set: its black and white points to the set's, its color cast to the palette's
# warmth, its colorfulness to the set's (scaled by no less and no more than CHROMA, and never past CHROMA_MOST)
STRENGTH = 0.9
CHROMA = (0.6, 1.8)
CHROMA_MOST = 18.0
NEUTRAL = 128.0
TOWARD = 0.8   # the palette's warmth, a fifth of the way back to neutral, so the film never reads as one tint


def cmd_draft(a):
    picks = _env.read_json("picks.json") or {}
    stats = _env.read_json("people.json") or {}
    if not picks or not stats:
        sys.exit("picks.json or people.json is missing: run research.py first")
    best = {p["handle"]: p for p in picks.get("people", [])}
    cap = _env.per_person(len(stats.get("people", [])))
    people = {}
    for p in stats.get("people", []):
        h = p["handle"]
        rows = []
        if h in best:
            rows.append({"file": best[h]["src"], "point": best[h].get("focal") or [0.5, 0.45], "shot": ""})
        alone = [ph for ph in p.get("photos", []) if ph.get("with") == [h]]
        for ph in alone + [ph for ph in p.get("photos", []) if ph not in alone]:
            if len(rows) >= cap:
                break
            if ph["src"] not in {r["file"] for r in rows}:
                rows.append({"file": ph["src"], "point": [0.5, 0.45]})
        people[h] = rows
    wall = {w["photo"]: w for w in picks.get("wall", [])}
    opener = (picks.get("chapters", {}).get("opener") or [None])[0]
    w = wall.get(opener) or (picks.get("wall") or [{}])[0]
    inside = [h for h in people if h in (w.get("people") or [])]
    heads = {h: [round(0.2 + 0.6 * (i + 0.5) / max(1, len(inside)), 3), 0.35] for i, h in enumerate(inside)}
    month = dt.datetime.fromtimestamp(w["ts"], dt.timezone.utc).month if w.get("ts") else None
    cast = {"group": {"file": w.get("src") or w.get("photo"), "point": [0.5, 0.4], "heads": heads, "month": month, "shot": ""}, "people": people}
    _env.write_json("cast.json", cast)
    print(f"cast.json: {sum(len(v) for v in people.values())} photographs of {len(people)} people, the group of {len(heads)}; "
          "look at each and correct the points, tips, heads and faces, write each shot, then run cast.py match")
    return 0


def resolve(name):
    p = Path(name)
    if p.is_absolute():
        return p
    base = os.environ.get("PEOPLE_PHOTOS")
    return Path(base) / p if base else p   # the run folder is the working directory


def target_ab():
    """The year palette's mean a*/b* in 8-bit Lab, a fifth of the way back to neutral."""
    from PIL import Image, ImageCms
    pal = ((_env.read_json("taste.json") or {}).get("palette") or {}).get("year") or (_env.read_json("palette.json") or {}).get("year") or []
    tr = ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB"), "RGB", "LAB")
    A = B = W = 0.0
    for c in pal:
        h = c["hex"].lstrip("#")
        _, la, lb = ImageCms.applyTransform(Image.new("RGB", (1, 1), tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))), tr).getpixel((0, 0))
        A, B, W = A + la * c.get("share", 1), B + lb * c.get("share", 1), W + c.get("share", 1)
    if not W:
        return NEUTRAL, NEUTRAL
    return NEUTRAL + (A / W - NEUTRAL) * TOWARD, NEUTRAL + (B / W - NEUTRAL) * TOWARD


def framed(im):
    """A photograph shorter than 9:16, whole across a 9:16 picture at most FRAMED_W wide, over a copy of
    itself scaled to fill the picture, blurred and darkened; the band [v0, v1] it spans, as fractions of the
    picture's height; and the blurred copy alone."""
    from PIL import Image, ImageEnhance, ImageFilter
    W = min(im.size[0], FRAMED_W)
    H = round(W * TALL)
    h = round(W * im.size[1] / im.size[0])
    k = max(W / im.size[0], H / im.size[1])
    back = im.resize((round(im.size[0] * k), round(im.size[1] * k)), Image.LANCZOS)
    back = back.crop(((back.size[0] - W) // 2, (back.size[1] - H) // 2, (back.size[0] - W) // 2 + W, (back.size[1] - H) // 2 + H))
    back = ImageEnhance.Brightness(back.filter(ImageFilter.GaussianBlur(W * BLUR))).enhance(DIM)
    top = (H - h) // 2
    whole = back.copy()
    whole.paste(im.resize((W, h), Image.LANCZOS), (0, top))
    return whole, [round(top / H, 4), round((top + h) / H, 4)], back


def cmd_match(a):
    _env.need("PIL")
    from PIL import Image, ImageCms, ImageFilter, ImageStat
    cast = _env.read_json(_env.ws(a.cast) if a.cast else "cast.json")
    if not cast:
        sys.exit("cast.json is missing: run cast.py draft (or pass --cast FILE)")
    if a.cast:
        _env.write_json("cast.json", cast)
    roles = {"group": cast["group"]} if cast.get("group", {}).get("file") else {}
    for h, rows in cast["people"].items():
        for i, r in enumerate(rows[:_env.per_person(len(cast["people"]))]):
            roles[f"{h}-{i}"] = r
    out = Path("public/matched")
    out.mkdir(parents=True, exist_ok=True)
    to_lab = ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB"), "RGB", "LAB")
    to_rgb = ImageCms.buildTransformFromOpenProfiles(ImageCms.createProfile("LAB"), ImageCms.createProfile("sRGB"), "LAB", "RGB")

    def stats(ch):
        s = ImageStat.Stat(ch)
        return s.mean[0], s.stddev[0]

    def ends(ch):
        """The channel's 2nd and 98th percentiles: its black and white points."""
        h, acc, out = ch.histogram(), 0, []
        for v, c in enumerate(h):
            acc += c
            while len(out) < 2 and acc >= sum(h) * (0.02, 0.98)[len(out)]:
                out.append(v)
        return out

    def lin(x0, x1, y0, y1):
        """The line through (x0, y0) and (x1, y1), clipped to a byte."""
        g = (y1 - y0) / max(1, x1 - x0)
        return lambda v: max(0, min(255, int(round((v - x0) * g + y0))))

    def toward(v, t):
        return v + (t - v) * STRENGTH

    labs = {}
    for role, r in roles.items():
        f = resolve(r["file"])
        if not f.exists():
            sys.exit(f"{role}: {f} is not there; fix cast.json")
        im = Image.open(f)
        im.draft("RGB", (LONG, LONG))
        im = im.convert("RGB")
        if r.get("trim"):
            u0, v0, u1, v1 = r["trim"]
            im = im.crop((round(u0 * im.size[0]), round(v0 * im.size[1]), round(u1 * im.size[0]), round(v1 * im.size[1])))
        im.thumbnail((LONG, LONG), Image.LANCZOS)
        labs[role] = ImageCms.applyTransform(im, to_lab)
    ls = [ends(im.getchannel(0)) for n, im in labs.items() if not roles[n].get("keep_light")] or [ends(im.getchannel(0)) for im in labs.values()]
    black, white = sum(e[0] for e in ls) / len(ls), sum(e[1] for e in ls) / len(ls)
    spread = {n: math.hypot(stats(im.getchannel(1))[1], stats(im.getchannel(2))[1]) for n, im in labs.items()}
    colorful = min(CHROMA_MOST, sum(spread.values()) / len(spread))
    ta, tb = target_ab()
    # aspects.json is the index of public/matched/, so it goes before the first photograph changes and comes back after
    # the last: a match stopped on the way leaves none, and the boards refuse to lay out
    (out / "aspects.json").unlink(missing_ok=True)
    aspects = {}
    for n, im in labs.items():
        L, la, lb = im.split()
        if not roles[n].get("keep_light"):
            b0, w0 = ends(L)
            L = L.point(lin(b0, w0, toward(b0, black), toward(w0, white)))
        g = 1 + (min(CHROMA[1], max(CHROMA[0], colorful / max(1e-3, spread[n]))) - 1) * STRENGTH
        for ch, t in ((la, ta), (lb, tb)):
            mu = stats(ch)[0]
            ch.paste(ch.point(lin(mu, mu + 1, toward(mu, t), toward(mu, t) + g)))
        rgb = ImageCms.applyTransform(Image.merge("LAB", (L, la, lb)), to_rgb)
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=2))
        aspects[n] = round(rgb.size[1] / rgb.size[0], 4)
        if aspects[n] <= 1 or (n == "group" and aspects[n] < TALL):
            rgb, band, _ = framed(rgb)
            aspects[n] = {"aspect": round(rgb.size[1] / rgb.size[0], 4), "band": band}
        rgb.save(_env.part(out / f"{n}.jpg"), "JPEG", quality=94)
        os.replace(_env.part(out / f"{n}.jpg"), out / f"{n}.jpg")
    _env.write_json(out / "aspects.json", aspects)
    pub = Path("public")
    for name in ("fonts", "fx"):
        src = (_env.SKILL / "fonts") if name == "fonts" else (_env.SKILL / "motion" / "public" / "fx")
        if not (pub / name).exists():
            shutil.copytree(src, pub / name, ignore=shutil.ignore_patterns("*.md"))
    print(f"matched {len(aspects)} photographs into public/matched/ (target a* {ta:.0f}, b* {tb:.0f}; black {black:.0f}, white {white:.0f})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "match"])
    ap.add_argument("--cast", help="match: a cast file to use (copied to R/cast.json)")
    a = ap.parse_args()
    _env.enter_run()
    return {"draft": cmd_draft, "match": cmd_match}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
