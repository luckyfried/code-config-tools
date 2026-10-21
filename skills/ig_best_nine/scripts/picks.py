#!/usr/bin/env python3
"""Movement 1, research: the nine's photographs, each with the point the storyboard frames it around.

USAGE (from the workspace root):
    python3 S/scripts/picks.py --run build/<stamp>

Indexes every photo of the year (color, contrast, exposure) into photo_index.json. For each of the nine (rank
order, from stats.json) it writes the photograph the film draws, public/photos/r<rank>-<name>.jpg (HEIC
converted, EXIF rotation applied, at most 2400 px on a side, its mean light moved halfway to the nine's common
exposure by a curve that keeps its color; a reel stands in by its poster frame, 40% of the way in), and decides
where the storyboard looks:

  focus  the subject, as [u, v] fractions of the photograph: each cell of a small copy is weighted by its detail
         (edge strength), by how far its color stands from the photograph's mean color, by skin tones, and by a
         soft center prior; the focus is the weighted center of the strongest tenth of the cells, kept 0.2-0.8.
  crop   the wall's square, [x, y, w] fractions (w of the width): the largest square inside the photograph,
         centered on the focus as far as the edges allow.
  line   the photograph's own strongest straight line, [u0, v0, u1, v1] fractions (a rail, a board's edge, a hem):
         written by the person reading the photographs, never guessed here. drive lays its cut along it; a
         photograph without one is cut level. Running picks.py again keeps each photograph's line.

picks.json carries the nine in rank order (file relative to public/, aspect as height over width, focus, crop,
score, brightness, colors, source). The storyboard records the same focus and crop on every layer that draws the
photograph, so a person can move a focus in picks.json and draft again.
"""
import datetime as dt
import math
import subprocess
import sys
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

PUBLIC = Path("public")
PHOTOS = PUBLIC / "photos"
VIDEO = {".mp4", ".mov", ".m4v"}
LONG = 2400


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def poster(video, dest):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    try:
        at = float(r.stdout.strip()) * 0.4
    except ValueError:
        at = 0.5
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale='min({LONG},iw)':-2", "-q:v", "2", str(dest)], capture_output=True)
    return dest.exists() and dest.stat().st_size > 0


def place(rank, src, video=None):
    """The photograph the film draws, in public/photos/. Returns its path, or None when it cannot be opened."""
    PHOTOS.mkdir(parents=True, exist_ok=True)
    dest = PHOTOS / f"r{rank}-{Path(src).stem}.jpg"
    if video:
        return dest if poster(src, dest) else None
    try:
        im = open_image(src)
    except Exception as e:
        print(f"skip {Path(src).name}: cannot open ({e})", file=sys.stderr)
        return None
    im.thumbnail((LONG, LONG), Image.LANCZOS)
    matched(im.convert("RGB")).save(dest, "JPEG", quality=90)
    return dest


# the nine's common exposure (mean luma, 0-255) and how far toward it each photograph moves
EXPOSURE = 128
MATCH = 0.5


def matched(im):
    """The photograph with its mean light moved MATCH of the way to EXPOSURE by one gamma curve on every channel, so
    the nine sit in one grade and each keeps its own color."""
    m = ImageStat.Stat(im.convert("L")).mean[0]
    if not 8 < m < 247:
        return im
    want = m + (EXPOSURE - m) * MATCH
    g = math.log(want / 255) / math.log(m / 255)
    lut = [round(255 * (i / 255) ** g) for i in range(256)]
    return im.point(lut * 3)


def skin(r, g, b):
    return r > 95 and g > 40 and b > 20 and r > g and r > b and r - min(g, b) > 15 and abs(r - g) > 15


def focus_of(im, cells=48):
    """The subject's point, [u, v]: detail x color distinctness (skin counts double) x a soft center prior, averaged
    over the strongest tenth of the cells."""
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
            wgt = (0.5 + ed[x, y] / 255) * (0.25 + far) * (2.0 if skin(r, g, b) else 1.0) * prior
            weights.append((wgt, u, v))
    weights.sort(reverse=True)
    top = weights[:max(1, len(weights) // 10)]
    tot = sum(wt for wt, _, _ in top) or 1
    fu = sum(wt * u for wt, u, _ in top) / tot
    fv = sum(wt * v for wt, _, v in top) / tot
    return [round(min(0.8, max(0.2, fu)), 2), round(min(0.8, max(0.2, fv)), 2)]


def square_crop(aspect, focus):
    """The largest square window, [x, y, w] fractions, centered on the focus as far as the edges allow."""
    w = min(1.0, aspect)
    hh = w / aspect
    x = min(max(0.0, focus[0] - w / 2), 1 - w)
    y = min(max(0.0, focus[1] - hh / 2), 1 - hh)
    return [round(x, 3), round(y, 3), round(w, 3)]


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
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3), "colors": dom}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _env.run_arg(ap)
    _env.enter_run(ap.parse_args().run)
    d = _env.read_json("library.json")
    s = _env.read_json("stats.json")
    if not d or not s:
        sys.exit("run gather.py and stats.py first")
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
                index.append({"src": m, "kind": kind, "ts": r["ts"], "month": month, "likes": r.get("likes"), **a})
    _env.write_json("photo_index.json", index)
    lines = {n["src"]: n["line"] for n in (_env.read_json("picks.json") or {}).get("nine", []) if n.get("line")}
    nine = []
    for t in s["top_nine"]:
        out = place(t["rank"], t["media"], t.get("video"))
        if not out:
            print(f"skip rank {t['rank']}: its media cannot be opened ({Path(t['media']).name})", file=sys.stderr)
            continue
        im = open_image(out)
        aspect = round(im.size[1] / im.size[0], 4)
        focus = focus_of(im)
        nine.append({"rank": t["rank"], "kind": t["kind"], "file": str(out.relative_to(PUBLIC)), "src": t["media"],
                     "video": t.get("video"), "aspect": aspect, "focus": focus, "crop": square_crop(aspect, focus), **analyse(out)})
        if t["media"] in lines:
            nine[-1]["line"] = lines[t["media"]]
    _env.write_json("picks.json", {"nine": nine})
    print(f"indexed {len(index)} photos ({skipped} could not be opened); the nine's photographs in {PHOTOS}/")
    for n in nine:
        print(f"  {n['rank']}. {n['kind']:<5} {Path(n['src']).name}  focus {n['focus']}  crop {n['crop']}")
    print("wrote picks.json and photo_index.json")
    return 0 if nine else 1


if __name__ == "__main__":
    sys.exit(main())
