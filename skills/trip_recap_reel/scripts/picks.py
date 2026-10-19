#!/usr/bin/env python3
"""Movement 1, research: the trip's photos, day by day and place by place, and their everyday photos to set them
against. Writes build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/picks.py

Reads build/library.json and build/trip.json (trip.py). Scores every photo of the trip (color, contrast,
exposure), finds each one's focal point (where the detail is, so a cover crop keeps it), converts HEIC and rotates
by EXIF, and saves a 1600 px JPEG copy in build/photos/. Up to 80 of their everyday photos (posts outside any trip)
are scored too, so palette.py and research.py can say how the trip looked different from every other week.
Each clip they shot on the trip gets a poster frame (ffmpeg, 40% of the way in).
picks.json carries "days" (each date with its places and its photos, best first), "places" (each stop with its
photos, in route order), "opener" (the most striking photo of the first days), "closer" (the last day's best),
"clips" (their footage with its poster, day and place), and "focal" and "caption_of" for every prepared photo.
To swap a photo, run `grade.py photos FILE` and put "graded/<name>.jpg" in the beat's "photos" in
build/storyboards/N/storyboard.json.
"""
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


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()


def focal_css(e):
    return f"{e['focal'][0] * 100:.0f}% {e['focal'][1] * 100:.0f}%"


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    lib = _env.read_json("build/library.json")
    trip = _env.read_json("build/trip.json")
    if not lib or not trip:
        sys.exit("build/library.json and build/trip.json are needed: run gather.py and trip.py first (research.py runs trip.py)")
    lo, hi = trip["from"], trip["to"]
    spans = [(lo, hi)] + [(o["from"], o["to"]) for o in trip.get("others") or []]
    place_of = {}
    for d in trip["days"]:
        for it in d["items"]:
            place_of[(it["ts"], tuple(it["media"]))] = it.get("place") or (d["places"][0] if d["places"] else None)
    index, skipped, everyday = [], 0, []
    for kind in ("posts", "stories", "facebook"):
        for r in lib.get(kind) or []:
            if not r.get("ts"):
                continue
            day = day_of(r["ts"])
            on_trip = lo <= day <= hi
            if not on_trip:
                if kind == "posts" and not any(a <= day <= b for a, b in spans):
                    everyday.append(r)
                continue
            for m in r.get("media") or []:
                if Path(m).suffix.lower() in VIDEO:
                    continue
                try:
                    a = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                index.append({"src": m, "kind": kind[:-1] if kind != "facebook" else "facebook", "set": "trip", "ts": r["ts"], "day": day,
                              "place": place_of.get((r["ts"], tuple(r.get("media") or []))), "likes": r.get("likes"),
                              "caption": r.get("caption") or "", **a})
    for r in sorted(everyday, key=lambda r: -r["ts"])[:80]:
        m = (r.get("media") or [None])[0]
        if not m or Path(m).suffix.lower() in VIDEO:
            continue
        try:
            a = analyse(m)
        except Exception:
            skipped += 1
            continue
        index.append({"src": m, "kind": "post", "set": "everyday", "ts": r["ts"], "day": day_of(r["ts"]), "place": None,
                      "likes": r.get("likes"), "caption": r.get("caption") or "", **a})
    tripx = [e for e in index if e["set"] == "trip"]
    if not tripx:
        sys.exit("no photo of the trip could be opened; the film needs at least one")
    _env.write_json("build/photo_index.json", index)
    out = {"trip": {"name": trip["name"], "from": lo, "to": hi}, "days": [], "places": [], "clips": [], "focal": {},
           "caption_of": {}, "source_of": {}}

    def take(e):
        p = prepare(e["src"])
        if p:
            out["focal"][p] = focal_css(e)
            out["caption_of"][p] = e["caption"]
            out["source_of"][p] = e["src"]
        return p

    def rank(es):
        # their posts before their stories, then the stronger photo; a photo that is too dark to carry type goes last
        return sorted(es, key=lambda e: (e["bright"] < 0.18, e["kind"] == "story", -e["score"]))

    for d in trip["days"]:
        es = rank([e for e in tripx if e["day"] == d["date"]])
        photos = [p for p in (take(e) for e in es) if p]
        out["days"].append({"date": d["date"], "places": d["places"], "photos": photos,
                            "captions": [c for c in d.get("captions") or [] if c.strip()][:4]})
    for pl in trip["places"]:
        es = rank([e for e in tripx if e["place"] == pl["name"]])
        out["places"].append({"name": pl["name"], "days": pl["days"], "photos": [p for p in (take(e) for e in es) if p]})
    early = [e for e in tripx if e["day"] <= (trip["days"][min(1, len(trip["days"]) - 1)]["date"])] or tripx
    op = max((e for e in early if e["bright"] > 0.25 and e["kind"] != "story"), key=lambda e: e["score"], default=max(early, key=lambda e: e["score"]))
    last = [e for e in tripx if e["day"] == trip["days"][-1]["date"]] or tripx
    cl = max((e for e in last if e["src"] != op["src"]), key=lambda e: e["score"], default=op)
    out["opener"], out["closer"] = take(op), take(cl)
    for c in trip.get("clips") or []:
        pst = poster(c["file"])
        if pst:
            out["focal"][pst] = "50% 45%"
            out["caption_of"][pst] = c.get("caption") or ""
        out["clips"].append({**c, "poster": pst})
    _env.write_json("build/picks.json", out)
    n_every = sum(1 for e in index if e["set"] == "everyday")
    print(f"indexed {len(tripx)} trip photos and {n_every} everyday photos ({skipped} could not be opened); "
          f"prepared {len(list(PHOTOS.glob('*.jpg')))} in build/photos/")
    for d in out["days"]:
        print(f"  {d['date']}  {', '.join(d['places']) or '-'}: {len(d['photos'])} photos")
    print(f"clips: {len(out['clips'])}, {sum(1 for c in out['clips'] if c['poster'])} with a poster")
    print("wrote build/picks.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
