#!/usr/bin/env python3
"""Movement 1, research: read the grid and the library photo by photo. Writes build/grid.json,
build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Measures every photo (its mean color in Lab, chroma, warmth, brightness, detail, how much of it is flat near-white,
its focal point and five dominant colors), converts HEIC, rotates by EXIF and saves a 1600 px JPEG copy of every
grid cover and every library photo in build/photos/. A reel's cover is its poster frame (ffmpeg, 40% of the way in).

build/grid.json: the last 30 posts and reels in grid order (position 0 is the top left), each with its cover, its
likes, comments and saves, and the flags the audit reads:
  clash  its color sits far from the grid's own (Lab distance over 2.2x the grid's median distance and over 18, or
         chroma over 1.8x the grid's median chroma and over 30);
  text   a screenshot or a text card (more than half of it flat near-white or near-black, almost no color);
  busy   much more detail than the grid median (over 1.6x);
  square posted square, so the 4:5 profile grid crops its sides.
A close crop among wide ones is a judgment of scale no measurement makes reliably: the eye pass in
pipeline/1-research.md adds "tight" by looking at build/grid-sheet.png, the grid drawn with each cell's position.
build/photo_index.json: every photo measured, with its kind (grid, post, carousel, story, facebook, photo), likes
and saves when it is a post's cover. build/picks.json: "pool", the photos the next nine are drawn from (everything
not on the grid and not posted before: carousel slides, stories, Facebook photos, the photo folder; older posts
only when that pool is under 18), ranked by how well they read as a post (exposure, detail, not text).
To swap a photo, run `grade.py photos FILE` and name the build/photos file in build/plan.json.
"""
import datetime as dt
import hashlib
import math
import statistics
import subprocess
import sys
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageFilter, ImageOps, ImageStat  # noqa: E402

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

PHOTOS = Path("build/photos")
VIDEO = {".mp4", ".mov", ".m4v"}


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def prepare(path):
    """A 1600 px JPEG copy in build/photos/ (HEIC converted, EXIF rotation applied). Returns its path or None."""
    src = Path(path)
    dest = PHOTOS / (hashlib.sha1(str(src.resolve()).encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    try:
        im = open_image(src)
    except Exception as e:
        print(f"skip {src.name}: cannot open ({e}){' ; HEIC needs pillow-heif' if src.suffix.lower() in ('.heic', '.heif') else ''}",
              file=sys.stderr)
        return None
    im.thumbnail((1600, 1600), Image.LANCZOS)
    PHOTOS.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=90)
    return str(dest.resolve())


def poster(video):
    """A reel's poster frame as a 1600 px JPEG in build/photos/, 40% of the way in. Returns its path or None."""
    src = Path(video)
    dest = PHOTOS / (hashlib.sha1((str(src.resolve()) + "#poster").encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    PHOTOS.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    try:
        at = float(r.stdout.strip()) * 0.4
    except ValueError:
        at = 0.5
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                    "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", str(dest)], capture_output=True)
    return str(dest.resolve()) if dest.exists() and dest.stat().st_size > 0 else None


def to_lab(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return (116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z)))


def analyse(path):
    im = open_image(path, draft=(160, 200))
    w, h = im.size
    small = im.resize((64, max(1, round(64 * h / w))))
    hsv = small.convert("HSV")
    sat = ImageStat.Stat(hsv.getchannel("S")).mean[0] / 255
    light = ImageStat.Stat(small.convert("L"))
    bright, contrast = light.mean[0] / 255, light.stddev[0] / 128
    expo = 1 - min(1, abs(bright - 0.52) * 2.2)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES)
    px = edges.load()
    sw, sh = edges.size
    tot = sx = sy = 0
    for y in range(1, sh - 1):
        for x in range(1, sw - 1):
            v = px[x, y]
            tot += v
            sx += v * x
            sy += v * y
    fx, fy = (sx / tot / sw, sy / tot / sh) if tot else (0.5, 0.5)
    detail = tot / max(1, (sw - 2) * (sh - 2)) / 255
    pix = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    labs = [to_lab(c) for c in pix[::3]]
    L = sum(l[0] for l in labs) / len(labs)
    A = sum(l[1] for l in labs) / len(labs)
    B = sum(l[2] for l in labs) / len(labs)
    chroma = sum(math.hypot(l[1], l[2]) for l in labs) / len(labs)
    flat = sum(1 for l in labs if math.hypot(l[1], l[2]) < 6 and (l[0] > 88 or l[0] < 12)) / len(labs)
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    cols = sorted(q.getcolors(), reverse=True)
    dom = [{"rgb": pal[3 * i:3 * i + 3], "share": round(n / (sw * sh), 3)} for n, i in cols]
    score = round(0.45 * sat + 0.35 * min(1, contrast) + 0.2 * expo, 3)
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3), "expo": round(expo, 3),
            "lab": [round(L, 1), round(A, 1), round(B, 1)], "chroma": round(chroma, 1), "warmth": round(A * 0.4 + B, 1),
            "detail": round(detail, 4), "flat": round(flat, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "colors": dom}


def lab_dist(a, b):
    return math.dist(a, b)


def flag_grid(cells):
    """Marks clash, tight, text, busy and square on the grid's cells, each against the grid's own medians."""
    photos = [c for c in cells if c.get("a")]
    if not photos:
        return {}
    for c in photos:
        c["a"]["text"] = c["a"]["flat"] > 0.5 and c["a"]["chroma"] < 12
    base = [c for c in photos if not c["a"]["text"]] or photos
    med = [statistics.median(c["a"]["lab"][i] for c in base) for i in range(3)]
    dists = [lab_dist(c["a"]["lab"], med) for c in base]
    md = statistics.median(dists) or 1
    mc = statistics.median(c["a"]["chroma"] for c in base) or 1
    det = statistics.median(c["a"]["detail"] for c in base) or 1e-6
    for c in cells:
        a = c.get("a")
        f = []
        if a:
            d = lab_dist(a["lab"], med)
            if a["text"]:
                f.append("text")
            else:
                if d > max(18, 2.2 * md) or a["chroma"] > max(30, 1.8 * mc):
                    f.append("clash")
                if a["detail"] > 1.6 * det:
                    f.append("busy")
            if c["kind"] == "post" and abs(a["w"] - a["h"]) < 0.04 * a["w"]:
                f.append("square")
            c["distance"] = round(d, 1)
        c["flags"] = f
    return {"median_lab": [round(v, 1) for v in med], "median_distance": round(md, 1), "median_chroma": round(mc, 1),
            "median_detail": round(det, 4)}


def grid_sheet(cells, path, cell=240):
    """The grid as their profile shows it, 3 wide in 4:5 cells, each numbered with its position (eye pass input)."""
    from PIL import ImageDraw, ImageFont
    rows = math.ceil(len(cells) / 3)
    ch = int(cell * 1.25)
    sheet = Image.new("RGB", (3 * cell + 4, rows * (ch + 2) + 2), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    for c in cells:
        x, y = (c["pos"] % 3) * (cell + 2), (c["pos"] // 3) * (ch + 2)
        if c.get("cover"):
            im = ImageOps.fit(open_image(c["cover"]), (cell, ch), Image.LANCZOS)
            sheet.paste(im, (x, y))
        d.rectangle([x + 6, y + 6, x + 46, y + 34], fill=(0, 0, 0))
        d.text((x + 12, y + 8), str(c["pos"]), font=font, fill=(255, 255, 255))
        if c["kind"] == "reel":
            d.text((x + cell - 60, y + 8), "reel", font=font, fill=(255, 255, 255))
    sheet.save(path)


def measure(job):
    m, kind, r, pos = job
    try:
        path = m if kind == "post" else (poster(m) if Path(m).suffix.lower() in VIDEO else prepare(m))
        if not path:
            return None
        a = analyse(path)
    except Exception as e:
        print(f"skip {Path(m).name}: {e}", file=sys.stderr)
        return None
    own = kind in ("grid", "post")
    return {"src": m, "photo": None if kind == "post" else path, "kind": kind, "pos": pos, "ts": r.get("ts"),
            "likes": r.get("likes") if own else None, "saves": r.get("saves") if own else None,
            "comments": r.get("comments") if own else None, **a}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    if not d or "grid" not in d:
        sys.exit("run gather.py first")
    grid_src = {r["media"][0] for r in d["grid"] if r.get("media")}
    jobs = []  # (src, kind, row, pos)
    for r in d["grid"]:
        if r.get("media"):
            jobs.append((r["media"][0], "grid", r, r["pos"]))
    for r in d["posts"]:
        for i, m in enumerate(r.get("media") or []):
            if m in grid_src or Path(m).suffix.lower() in VIDEO:
                continue
            jobs.append((m, "post" if i == 0 else "carousel", r, None))
    for kind, rows in (("story", d["stories"]), ("facebook", d["facebook"])):
        for r in rows:
            for m in r.get("media") or []:
                if Path(m).suffix.lower() not in VIDEO:
                    jobs.append((m, kind, r, None))
    if d.get("source") == "photos":
        jobs = [(m, "grid" if m in grid_src else "photo", r, p) for m, _, r, p in jobs]
    jobs = [(m, k, {x: r.get(x) for x in ("ts", "likes", "saves", "comments")}, p) for m, k, r, p in jobs]

    with ProcessPoolExecutor(min(8, os.cpu_count() or 2)) as ex:
        index = [e for e in ex.map(measure, jobs, chunksize=4) if e]
    if not index:
        sys.exit("no photos could be opened; the grid read needs at least one photo")
    by_pos = {e["pos"]: e for e in index if e["kind"] == "grid"}
    cells = []
    for r in d["grid"]:
        e = by_pos.get(r["pos"])
        cells.append({"pos": r["pos"], "kind": r["kind"], "ts": r["ts"], "caption": r.get("caption") or "",
                      "src": r["media"][0] if r.get("media") else None, "cover": e["photo"] if e else None,
                      "likes": r.get("likes"), "comments": r.get("comments"), "saves": r.get("saves"),
                      "carousel": len(r.get("media") or []) > 1, "a": {k: v for k, v in e.items()
                                                                     if k not in ("src", "photo", "kind", "pos", "ts", "likes", "saves", "comments")} if e else None})
    medians = flag_grid(cells)
    for c in cells:
        if c["pos"] in by_pos:
            by_pos[c["pos"]]["flags"] = c["flags"]
    _env.write_json("build/grid.json", {"cells": cells, **medians})
    grid_sheet(cells, "build/grid-sheet.png")
    _env.write_json("build/photo_index.json", index)
    fresh = [e for e in index if e["kind"] in ("carousel", "story", "facebook", "photo")]
    if len(fresh) < 18:
        fresh += [e for e in index if e["kind"] == "post"]
    pool = []
    for e in fresh:
        if e["flat"] > 0.5 and e["chroma"] < 12:
            continue
        e = dict(e, photo=e["photo"] or prepare(e["src"]))
        if not e["photo"]:
            continue
        e["fit"] = round(0.5 * e["expo"] + 0.3 * min(1, e["detail"] / (medians["median_detail"] or 1)) + 0.2 * min(1, e["score"]), 3)
        pool.append(e)
    pool.sort(key=lambda e: -e["fit"])
    focal = {e["photo"]: f"{e['focal'][0] * 100:.0f}% {e['focal'][1] * 100:.0f}%" for e in pool}
    focal.update({c["cover"]: f"{c['a']['focal'][0] * 100:.0f}% {c['a']['focal'][1] * 100:.0f}%" for c in cells if c.get("cover")})
    out = {"pool": [{k: e[k] for k in ("photo", "src", "kind", "ts", "fit", "lab", "chroma", "warmth", "bright", "detail",
                                       "focal", "w", "h", "colors")} for e in pool],
           "chapters": {"grid": [c["cover"] for c in cells if c.get("cover")], "pool": [e["photo"] for e in pool]},
           "focal": focal, "source_of": {e["photo"]: e["src"] for e in pool}}
    _env.write_json("build/picks.json", out)
    flagged = {f: [c["pos"] for c in cells if f in c["flags"]] for f in ("clash", "text", "busy", "square")}
    print(f"measured {len(index)} photos; grid {len(cells)} cells; pool {len(pool)} photos for the next nine")
    for f, ps in flagged.items():
        print(f"  {f:<6} at grid positions {ps}")
    print("wrote build/grid.json, build/grid-sheet.png, build/photo_index.json and build/picks.json")
    return 0 if len(cells) >= 9 else 1


if __name__ == "__main__":
    sys.exit(main())
