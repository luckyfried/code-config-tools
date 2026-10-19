#!/usr/bin/env python3
"""Movement 1, research: each place's photos. Reads build/library.json and build/places.json; writes
build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py [--per-place 6]

Scores every photo of the year (color, contrast, exposure), finds each one's focal point (where the detail is,
so a cover crop keeps it), converts HEIC and rotates by EXIF, and saves a 1600 px JPEG copy in build/photos/.
Every photo carries the place places.py gave its post or story. picks.json carries, per place, its best photos
(the hero first, one from each visit of a place visited twice, then by score and likes), its own reels with a
poster frame each (ffmpeg, 40% of the way in), and the "opener" chapter: the year's most striking photo taken
away from home. To swap a photo, run `grade.py photos FILE` and put "graded/<name>.jpg" in the beat's "photos" in
build/storyboards/N/storyboard.json.
"""
import collections
import datetime as dt
import hashlib
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
    ap.add_argument("--per-place", type=int, default=6)
    a = ap.parse_args()
    d = _env.read_json("build/library.json")
    pl = _env.read_json("build/places.json")
    if not d or not pl:
        sys.exit("run gather.py and places.py first")
    rowmap = pl.get("rows") or {}
    index, skipped = [], 0
    for kind in ("posts", "stories", "facebook"):
        for i, r in enumerate(d.get(kind) or []):
            for m in r.get("media") or []:
                if Path(m).suffix.lower() in VIDEO:
                    continue
                try:
                    an = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                month = dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month
                index.append({"src": m, "kind": kind.rstrip("s") if kind != "facebook" else "facebook", "ts": r["ts"], "month": month,
                              "likes": r.get("likes"), "place": rowmap.get(f"{kind}:{i}"), **an})
    if not index:
        sys.exit("no photos could be opened; the film needs at least one photo")
    _env.write_json("build/photo_index.json", index)
    visits = collections.defaultdict(list)
    for v in pl.get("visits") or []:
        visits[v["place"]].append(v)
    likes = sorted(e["likes"] for e in index if e.get("likes") is not None)
    usual = likes[len(likes) // 2] if likes else 0
    out = {"places": {}, "chapters": {}, "focal": {}, "source_of": {}}

    def keep(e):
        ph = prepare(e["src"])
        if ph:
            out["focal"][ph] = f"{e['focal'][0] * 100:.0f}% {e['focal'][1] * 100:.0f}%"
            out["source_of"][ph] = e["src"]
        return ph

    def worth(e):
        bonus = 0.15 * min(2.0, (e["likes"] or 0) / usual) if usual and e.get("likes") is not None else 0
        return e["score"] + bonus + (0.05 if e["kind"] == "post" else 0) - (0.3 if e["bright"] < 0.18 else 0)

    for p in pl["places"]:
        mine = sorted((e for e in index if e.get("place") == p["id"]), key=lambda e: -worth(e))
        chosen = []
        for v in visits.get(p["id"], []) if p["visits"] > 1 and not p["home"] else []:
            lo, hi = v["from"], v["to"]
            first = next((e for e in mine if lo <= dt.datetime.fromtimestamp(int(e["ts"]), dt.timezone.utc).date().isoformat() <= hi
                          and e not in chosen), None)
            if first:
                chosen.append(first)
        for e in mine:
            if len(chosen) >= a.per_place:
                break
            if e not in chosen:
                chosen.append(e)
        chosen.sort(key=lambda e: -worth(e))
        photos = [ph for ph in (keep(e) for e in chosen) if ph]
        clips = []
        for c in p.get("clips") or []:
            still = poster(c)
            if still:
                clips.append({"video": c, "poster": still})
                out["source_of"][still] = c
        out["places"][p["id"]] = {"photos": photos, "clips": clips,
                                  "bright": [e["bright"] for e in chosen], "colors": [e["colors"] for e in chosen[:3]]}
    away = [e for e in index if e.get("place") and e["place"] != pl.get("home") and e["bright"] > 0.25] or index
    opener = max(away, key=worth)
    op = keep(opener)
    out["chapters"]["opener"] = [op] if op else []
    _env.write_json("build/picks.json", out)
    empty = [p["name"] for p in pl["places"] if not out["places"][p["id"]]["photos"]]
    print(f"indexed {len(index)} photos ({skipped} could not be opened); prepared {len(list(PHOTOS.glob('*.jpg')))} in build/photos/")
    for p in pl["places"]:
        got = out["places"][p["id"]]
        print(f"  {p['name']:<14} {len(got['photos'])} photos, {len(got['clips'])} of their reels")
    if empty:
        print("no photo at: " + ", ".join(empty) + " (their beat uses the map alone)")
    print("wrote build/picks.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
