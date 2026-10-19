#!/usr/bin/env python3
"""Movement 1, research: prepare the photos the two share and the photos around them. Reads build/library.json
and build/shared.json; writes build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Scores every photo (color, contrast, exposure): the person's own (set "mine"), the named one's saved feed
("theirs"), and marks the ones the two share. Finds each one's focal point (where the detail is, so a cover crop
keeps it), converts HEIC and rotates by EXIF, and saves a 1600 px JPEG copy of every shared photo in build/photos/.
A shared video gets a poster frame (ffmpeg, 40% of the way in); the video itself stays available as footage.

picks.json carries "shared" (every prepared photo of the two, the only photos a beat may use; qa.py checks it),
"items" (each shared photo with its date, caption, era, focal point and colors), "videos", and the chapters:
"opener" (the most striking shared photo), "first" (the first photo together), "latest" (the latest), "eras" (each
era's photos in date order) and "best" (the twelve strongest shared photos, spread across the eras). To use
another of their photos, run `grade.py photos FILE` and put "graded/<name>.jpg" in a beat's "photos"; the file
has to be one of picks.json "shared".
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


def focal(a):
    return f"{a['focal'][0] * 100:.0f}% {a['focal'][1] * 100:.0f}%"


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    sh = _env.read_json("build/shared.json")
    if not d or not sh:
        sys.exit("run gather.py and shared.py first (research.py runs shared.py)")
    together = {m for x in sh["items"] for m in x["media"]}
    feed = (d.get("feeds") or {}).get(sh["who"]["handle"]) or {}
    index, skipped = [], 0
    rows = [("mine", r) for k in ("posts", "stories") for r in d[k]] + [("theirs", r) for r in feed.get("posts", [])]
    for side, r in rows:
        for m in r["media"]:
            if Path(m).suffix.lower() in VIDEO:
                continue
            try:
                a = analyse(m)
            except Exception:
                skipped += 1
                continue
            index.append({"src": m, "set": side, "shared": m in together, "ts": r["ts"],
                          "month": dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month, **a})
    if not index:
        sys.exit("no photos could be opened; the video needs at least one photo")
    _env.write_json("build/photo_index.json", index)
    era_of = {i: e["label"] for e in sh["eras"] for i in e["items"]}
    out = {"for": sh["who"]["handle"], "shared": [], "items": [], "videos": [], "focal": {}, "source_of": {},
           "chapters": {"opener": [], "first": [], "latest": [], "eras": {}, "best": []}}
    for x in sh["items"]:
        for n, m in enumerate(x["media"]):
            video = Path(m).suffix.lower() in VIDEO
            still = poster(m) if video else prepare(m)
            if not still:
                print(f"skip {Path(m).name}: cannot be opened", file=sys.stderr)
                continue
            a = analyse(still)
            row = {"id": x["id"], "photo": still, "src": m, "date": x["date"], "ts": x["ts"], "caption": x["caption"],
                   "from": x["from"], "era": era_of.get(x["id"]), "video": m if video else None, "group": len(x["tagged"]) >= 3, **a}
            out["shared"].append(still)
            out["focal"][still] = focal(a)
            out["source_of"][still] = m
            (out["videos"] if video else out["items"]).append(row)
    items = out["items"]
    if not items:
        sys.exit(f"no photo of you and @{sh['who']['handle']} could be opened")
    ch = out["chapters"]
    lit = [r for r in items if r["bright"] > 0.25] or items
    ch["opener"] = [max(lit, key=lambda r: r["score"])["photo"]]
    ch["first"] = [items[0]["photo"]]
    ch["latest"] = [items[-1]["photo"]]
    for e in sh["eras"]:
        ch["eras"][e["label"]] = [r["photo"] for r in items if r["era"] == e["label"]]
    per = max(1, 12 // max(1, len(sh["eras"])))
    best = [p for e in sh["eras"] for p in sorted((r for r in items if r["era"] == e["label"]), key=lambda r: -r["score"])[:per]]
    ch["best"] = [r["photo"] for r in sorted((r for r in items if r["photo"] in best), key=lambda r: r["ts"])][:12]
    _env.write_json("build/picks.json", out)
    print(f"indexed {len(index)} photos ({sum(1 for e in index if e['set'] == 'theirs')} from their feed, {skipped} could not be opened); "
          f"prepared {len(out['shared'])} shared ({len(items)} photos, {len(out['videos'])} video posters) in build/photos/")
    print(f"first {items[0]['date']} ({Path(items[0]['src']).name}), latest {items[-1]['date']} ({Path(items[-1]['src']).name})")
    for e, ps in ch["eras"].items():
        print(f"  {e}: {len(ps)} photos")
    print("wrote build/picks.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
