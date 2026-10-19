#!/usr/bin/env python3
"""Movement 1, research: choose the photos for every chapter and prepare them. Writes build/photo_index.json,
build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Scores every photo of the year (color, contrast, exposure), finds each one's focal point (where the detail is,
so a cover crop keeps it), converts HEIC and rotates by EXIF, and saves a 1600 px JPEG copy in build/photos/.
Picks: the opener (the year's most striking photo), a mosaic for the numbers, the top three posts, the busiest
month's mosaic and the quietest month's photos, a photo for the people, one for what they loved, the closer, the
carousel cover and the share card. A photo is used once where the year has enough of them. Videos are skipped.
To swap a photo, run `grade.py photos FILE` and put "graded/<name>.jpg" in the beat's "photos" in
build/storyboards/N/storyboard.json.
"""
import datetime as dt
import hashlib
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
    for y in range(sh):
        for x in range(sw):
            v = px[x, y]
            tot += v
            sx += v * x
            sy += v * y
    fx, fy = (sx / tot / sw, sy / tot / sh) if tot else (0.5, 0.5)
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    cols = sorted(q.getcolors(), reverse=True)
    dom = [{"rgb": pal[3 * i:3 * i + 3], "share": round(n / (sw * sh), 3)} for n, i in cols]
    score = round(0.45 * sat + 0.35 * min(1, contrast) + 0.2 * expo, 3)
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "colors": dom}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    s = _env.read_json("build/stats.json")
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
    if not index:
        sys.exit("no photos could be opened; the video needs at least one photo")
    _env.write_json("build/photo_index.json", index)
    by_src = {e["src"]: e for e in index}
    used = set()
    feed = [e for e in index if e["kind"] == "post"] or index

    def take(cands, n=1, allow_reuse=True):
        cands = sorted(cands, key=lambda e: -e["score"])
        fresh = [e for e in cands if e["src"] not in used]
        pool = fresh if len(fresh) >= n or not allow_reuse else fresh + [e for e in cands if e["src"] in used]
        got = pool[:n]
        used.update(e["src"] for e in got)
        return got

    def spread(cands, n):
        """n photos spread across the year (one per slot of time), best of each slot."""
        cands = sorted((e for e in cands if e["src"] not in used), key=lambda e: e["ts"]) or sorted(cands, key=lambda e: e["ts"])
        if not cands:
            return []
        out = []
        for i in range(n):
            chunk = cands[i * len(cands) // n:(i + 1) * len(cands) // n] or cands[-1:]
            best = max(chunk, key=lambda e: e["score"])
            out.append(best)
            used.add(best["src"])
        return out

    picks = {}
    top_srcs = [t["photo"] for t in s["top_posts"]]
    used.update(top_srcs)
    picks["top"] = [by_src[p] for p in top_srcs if p in by_src]
    picks["opener"] = take([e for e in feed if e["bright"] > 0.25])
    busy = s["busiest"]["month"] if s.get("busiest") else None
    quiet = s["quietest"]["month"] if s.get("quietest") else None
    picks["busiest"] = take([e for e in feed if e["month"] == busy], 12)
    picks["quietest"] = take([e for e in feed if e["month"] == quiet], 3)
    picks["numbers"] = spread(feed, 15)
    people = s.get("people") or []
    tagged = [e for e in feed if people and any(p["account"].lower() in (next((x["caption"] for x in d["posts"] if e["src"] in x["media"]), "") or "").lower()
                                                 for p in people[:2])]
    picks["people"] = take(tagged or feed)
    picks["loved"] = take(feed)
    last = max(e["month"] for e in feed)
    picks["closer"] = take([e for e in feed if e["month"] >= last - 1] or feed)
    picks["cover"] = take(feed)
    picks["share"] = take(feed)
    out = {"chapters": {}, "focal": {}}
    for ch, rows in picks.items():
        paths = []
        for e in rows:
            p = prepare(e["src"])
            if p:
                paths.append(p)
                out["focal"][p] = f"{e['focal'][0] * 100:.0f}% {e['focal'][1] * 100:.0f}%"
                out.setdefault("source_of", {})[p] = e["src"]
        out["chapters"][ch] = paths
    _env.write_json("build/picks.json", out)
    print(f"indexed {len(index)} photos ({skipped} could not be opened); prepared {len(list(PHOTOS.glob('*.jpg')))} in build/photos/")
    for ch, paths in out["chapters"].items():
        print(f"  {ch:<9} {len(paths)} photo(s)")
    print("wrote build/picks.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
