#!/usr/bin/env python3
"""Movement 1, research: every month's photograph, each with its subject and its own line.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Indexes every photo of the year (color, contrast, exposure, focal point) into build/photo_index.json, the input of
palette.py. For every month of the year's posts it takes the month's own photograph: the one build/taste.json's
`moments` names for that month (the moment the person's year is told by), else the photograph of the month's post
with the most to say (its longest caption), and writes the file the film draws, build/public/photos/<stamp>/mNN-<name>.jpg (HEIC converted,
EXIF rotation applied, at most 2400 px on a side, its mean light moved halfway to the year's common exposure by one
curve that keeps its color, so the twelve sit in one grade), and decides how the film reads it:

  focus  the subject, [u, v] fractions of the photograph: each cell of a small copy weighted by its detail, by how
         far its color stands from the photograph's mean color, by skin tones and by a soft center prior; the
         weighted center of the strongest tenth of the cells, kept 0.2-0.8, with "focus_from": "found". The film's crop
         keeps it in the frame and the month's words stand clear of the box around it. A focus that misses the subject
         (faces above a busy stall, a person at the edge of a wide view) is rewritten in build/picks.json with
         "focus_from": "read". Running picks.py again keeps every focus marked read.
  line   the photograph's own line, [u0, v0, u1, v1] fractions: the horizon, a rail, a sill, a pier, a road's edge,
         along which the accent line opens the month and the photograph splits. picks.py finds the straight edge
         with the most consistent light or color step across it (within 24 degrees of level) among the lines that lie
         inside the type area's height in the film's frame, and records it with "line_from": "found". The month's
         words stand where the board's style card sets them, never on the line. Read build/picks-sheet.jpg, where
         every found line is drawn: a line that misses the photograph's own edge is rewritten in build/picks.json
         with "line_from": "read". A close-up's line is its subject's own edge or a visible alignment in it (a cup's
         lip, a bowl's rim, a row of flower heads, the eyes), never the frame's edge or open texture. Running
         picks.py again keeps every line marked read.
  scene  what the photograph shows, in a few plain words ("the graffiti tram climbing the steep street"), written in
         build/picks.json by the person reading each photograph at full size (the sheet's copies hide the detail). The storyboard names each photograph by it and the clip
         prompt starts from it; a caption says what the person felt, often not what the photograph shows, so the
         storyboard refuses a month without a scene. Running picks.py again keeps every scene.

build/picks.json carries the months in calendar order (file relative to build/public/, size, focus, line, caption,
said, people, place, date, scene). `said` is the caption's first sentence with its hashtags and mentions taken off, the
line the month says on screen unless the moment gives its own; `people` are the accounts it tags; `place` the place it
names. A month with no post with a photograph is left out of the film.
"""
import calendar
import datetime as dt
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat  # noqa: E402
import year  # noqa: E402

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None


PUBLIC = Path("build/public")
PHOTOS = PUBLIC / "photos"
VIDEO = {".mp4", ".mov", ".m4v"}
LONG = 2400
# the year's common exposure (mean luma, 0-255) and how far toward it each photograph moves
EXPOSURE = 124
MATCH = 0.5
TILT = 24


MENTION = re.compile(r"@([A-Za-z0-9._]{2,30}[A-Za-z0-9_])")


def first_line(caption):
    """The caption's first sentence, as they wrote it, without its hashtags and mentions."""
    text = MENTION.sub("", re.sub(r"#\w+", "", caption or ""))
    text = " ".join(text.split())
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    return (m.group(1) if m else text).strip()


def place_in(caption):
    """The place a caption names, from the places research knows, else None."""
    import research
    low = (caption or "").lower()
    return next((p for p in research.PLACES if p != "home" and re.search(rf"\b{re.escape(p)}\b", low)), None)


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def matched(im):
    """The photograph with its mean light moved MATCH of the way to EXPOSURE by one gamma curve on every channel."""
    m = ImageStat.Stat(im.convert("L")).mean[0]
    if not 8 < m < 247:
        return im
    want = m + (EXPOSURE - m) * MATCH
    g = math.log(want / 255) / math.log(m / 255)
    lut = [round(255 * (i / 255) ** g) for i in range(256)]
    return im.point(lut * 3)


def place(month, src, into):
    """The photograph the film draws, in the run's folder `into` under build/public/photos/. Returns its path, or None
    when it cannot be opened."""
    into.mkdir(parents=True, exist_ok=True)
    dest = into / f"m{month:02d}-{Path(src).stem}.jpg"
    try:
        im = open_image(src)
    except Exception as e:
        print(f"skip {Path(src).name}: cannot open ({e})", file=sys.stderr)
        return None
    im.thumbnail((LONG, LONG), Image.LANCZOS)
    tmp = dest.with_name(f".{dest.name}.part")
    matched(im).save(tmp, "JPEG", quality=90)
    os.replace(tmp, dest)
    return dest


def skin(r, g, b):
    return r > 95 and g > 40 and b > 20 and r > g and r > b and r - min(g, b) > 15 and abs(r - g) > 15


def focus_of(im, cells=48):
    w, h = im.size
    sw, sh = (cells, max(1, round(cells * h / w))) if w >= h else (max(1, round(cells * w / h)), cells)
    small = im.resize((sw, sh), Image.BILINEAR)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.BoxBlur(1))
    rgb, ed = small.load(), edges.load()
    mean = ImageStat.Stat(small).mean
    weights = []
    for y in range(sh):
        for x in range(sw):
            r, g, b = rgb[x, y]
            far = math.sqrt((r - mean[0]) ** 2 + (g - mean[1]) ** 2 + (b - mean[2]) ** 2) / 255
            u, v = (x + 0.5) / sw, (y + 0.5) / sh
            prior = math.exp(-((u - 0.5) ** 2 + (v - 0.5) ** 2) / (2 * 0.22 ** 2))
            weights.append(((0.5 + ed[x, y] / 255) * (0.25 + far) * (2.0 if skin(r, g, b) else 1.0) * prior, u, v))
    weights.sort(reverse=True)
    top = weights[:max(1, len(weights) // 10)]
    tot = sum(wt for wt, _, _ in top) or 1
    fu = sum(wt * u for wt, u, _ in top) / tot
    fv = sum(wt * v for wt, _, v in top) / tot
    return [round(min(0.8, max(0.2, fu)), 2), round(min(0.8, max(0.2, fv)), 2)]


def line_of(im, ok=lambda ln: True, width=160):
    """The straight edge across the photograph with the most consistent step in light and color from one side to the
    other: for every angle within TILT of level and every height, the mean over the line of (the 4 px above minus the
    4 px below), per channel, so an edge between two regions adds up and texture cancels, among the lines `ok` takes.
    [u0, v0, u1, v1]."""
    w, h = im.size
    sw, sh = width, max(8, round(width * h / w))
    px = im.resize((sw, sh), Image.BILINEAR).filter(ImageFilter.BoxBlur(1)).load()
    best = (0.0, [0.0, 0.5, 1.0, 0.5])
    xs = range(int(sw * 0.06), int(sw * 0.94), 2)
    for deg in range(-TILT, TILT + 1, 3):
        k = math.tan(math.radians(deg))
        for y0 in range(int(sh * 0.12), int(sh * 0.9)):
            acc = [0.0, 0.0, 0.0]
            n = 0
            for x in xs:
                y = y0 + k * (x - sw / 2)
                yi = int(round(y))
                if yi - 4 < 0 or yi + 4 >= sh:
                    continue
                for o in (1, 2, 3, 4):
                    a, b = px[x, yi - o], px[x, yi + o]
                    acc[0] += a[0] - b[0]
                    acc[1] += a[1] - b[1]
                    acc[2] += a[2] - b[2]
                n += 1
            if n < len(xs) * 0.7:
                continue
            step = sum(abs(c) for c in acc) / (4 * n)
            v = y0 / sh
            score = step * (1 - 0.3 * abs(deg) / TILT) * (1 - 0.5 * max(0.0, abs(v - 0.55) - 0.2))
            ln = [0.0, round((y0 - k * sw / 2) / sh, 3), 1.0, round((y0 + k * sw / 2) / sh, 3)]
            if score > best[0] and ok(ln):
                best = (score, ln)
    return best[1]


def analyse(path):
    im = open_image(path, draft=(160, 200))
    w, h = im.size
    small = im.resize((64, max(1, round(64 * h / w))))
    hsv = small.convert("HSV")
    sat = ImageStat.Stat(hsv.getchannel("S")).mean[0] / 255
    light = ImageStat.Stat(small.convert("L"))
    bright, contrast = light.mean[0] / 255, light.stddev[0] / 128
    expo = 1 - min(1, abs(bright - 0.52) * 2.2)
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    cols = sorted(q.getcolors(), reverse=True)
    dom = [{"rgb": pal[3 * i:3 * i + 3], "share": round(n / (small.size[0] * small.size[1]), 3)} for n, i in cols]
    score = round(0.45 * sat + 0.35 * min(1, contrast) + 0.2 * expo, 3)
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3), "focal": focus_of(small), "colors": dom}


def sheet(months, out):
    """Every month's photograph with its line drawn, for reading the lines."""
    T = 360
    cols = 4
    rows = (len(months) + cols - 1) // cols
    S = Image.new("RGB", (cols * T, rows * (T + 28)), (20, 22, 28))
    d = ImageDraw.Draw(S)
    for i, m in enumerate(months):
        im = open_image(PUBLIC / m["file"])
        im.thumbnail((T, T))
        g = ImageDraw.Draw(im)
        u0, v0, u1, v1 = m["line"]
        g.line([(u0 * im.width, v0 * im.height), (u1 * im.width, v1 * im.height)], fill=(255, 201, 60), width=3)
        fx, fy = m["focus"][0] * im.width, m["focus"][1] * im.height
        g.ellipse([fx - 5, fy - 5, fx + 5, fy + 5], outline=(255, 255, 255), width=2)
        x0, y0 = (i % cols) * T, (i // cols) * (T + 28)
        S.paste(im, (x0, y0))
        d.text((x0 + 4, y0 + T + 6), f"{m['month']:02d} {m['line_from']} {m['line']}", fill=(240, 236, 228))
    S.save(out, quality=88)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    if not d:
        sys.exit("run gather.py first")
    index, skipped = [], 0
    for kind, rows in (("post", d["posts"]), ("story", d["stories"])):
        for r in rows:
            for m in r["media"]:
                if Path(m).suffix.lower() in VIDEO:
                    continue
                try:
                    a = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                month = dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month
                index.append({"src": m, "kind": kind, "ts": r["ts"], "month": month, **a})
    if not index:
        sys.exit("no photos could be opened; the film needs at least one photograph")
    _env.write_json("build/photo_index.json", index)
    old = (_env.read_json("build/picks.json") or {}).get("months", [])
    read = {m["src"]: m["line"] for m in old if m.get("line_from") == "read"}
    seen = {m["src"]: m["focus"] for m in old if m.get("focus_from") == "read"}
    scenes = {m["src"]: m["scene"] for m in old if m.get("scene")}
    # the photographs go into a folder of this run's own and picks.json names them, so it always names photographs that
    # are whole and are the ones its focus and line were read from; earlier runs' folders stay, since a cut board names them
    into = PHOTOS / _env.stamp()
    named = {}
    for mo in (_env.read_json("build/taste.json") or {}).get("moments") or []:
        n = mo.get("month")
        n = n if isinstance(n, int) else next((i for i in range(1, 13) if calendar.month_name[i].lower() == str(n).lower()), None)
        if n and mo.get("photo"):
            named[n] = mo["photo"]
    by_month = {}
    for r in d["posts"]:
        photos = [m for m in r["media"] if Path(m).suffix.lower() not in VIDEO]
        if photos:
            by_month.setdefault(dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month, []).append((r, photos))
    months = []
    for n in sorted(by_month):
        posts = by_month[n]
        hit = [(r, [m for m in ph if m == named.get(n)]) for r, ph in posts]
        hit = [(r, ph) for r, ph in hit if ph]
        post, photos = hit[0] if hit else max(posts, key=lambda rp: (len(rp[0].get("caption") or ""), -rp[0]["ts"]))
        src = photos[0]
        out = place(n, src, into)
        if not out:
            continue
        im = open_image(out)
        focus = seen.get(src) or focus_of(im)
        cap = post.get("caption") or ""
        rec = {"month": n, "name": calendar.month_name[n], "file": str(out.relative_to(PUBLIC)), "src": src,
               "size": list(im.size), "focus": focus, "focus_from": "read" if src in seen else "found",
               "caption": cap, "said": first_line(cap),
               "people": MENTION.findall(cap), "place": post.get("place") or place_in(cap),
               "date": dt.datetime.fromtimestamp(int(post["ts"]), dt.timezone.utc).date().isoformat()}
        if src in read:
            rec.update(line=read[src], line_from="read")
        else:
            rec.update(line=line_of(im, lambda ln: year.shown(im.size, focus, ln)), line_from="found")
        if src in scenes:
            rec["scene"] = scenes[src]
        months.append(rec)
    _env.write_json("build/picks.json", {"year": d.get("year"), "months": months})
    if months:
        sheet(months, "build/picks-sheet.jpg")
    print(f"indexed {len(index)} photos ({skipped} could not be opened); {len(months)} months' photographs in {PHOTOS}/")
    for m in months:
        print(f"  {m['month']:02d} {Path(m['src']).name}  focus {m['focus']}  line {m['line']} ({m['line_from']})")
    print("wrote build/picks.json, build/photo_index.json and build/picks-sheet.jpg (read the lines)")
    return 0 if months else 1


if __name__ == "__main__":
    sys.exit(main())
