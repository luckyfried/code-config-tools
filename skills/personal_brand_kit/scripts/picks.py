#!/usr/bin/env python3
"""Movement 1, research: read every photo. Writes build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Reads every photo of the person's posts and stories and every liked image (color, contrast, exposure, focal
point, and the five colors each covers with their shares), converting HEIC and rotating by EXIF. Each index row
carries its kind (post, story, liked) and, for a post, "row", its place in library.json's posts, so the research
joins a photo to its caption and its time. picks.json names the opener, the feed's most striking photo, as a
1600 px JPEG copy in build/photos/. To grade a photo for the film, run `grade.py photos FILE` and put
"graded/<name>.jpg" in the beat's "photos" in build/storyboards/N/storyboard.json.
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


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    if not d:
        sys.exit("run gather.py first")
    index, skipped = [], 0
    for kind, rows in (("post", d["posts"]), ("story", d["stories"]), ("liked", d.get("liked_media") or [])):
        for n, r in enumerate(rows):
            for m in r["media"]:
                if Path(m).suffix.lower() in VIDEO:
                    continue
                try:
                    a = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                row = {"src": m, "kind": kind, "ts": r.get("ts"), "likes": r.get("likes"), **a}
                if kind == "post":
                    row["row"] = n
                if kind == "liked":
                    row["account"] = r.get("account") or ""
                index.append(row)
    if not any(e["kind"] != "liked" for e in index):
        sys.exit("no photos of their own could be opened; the kit reads their photos")
    _env.write_json("build/photo_index.json", index)
    feed = [e for e in index if e["kind"] == "post"] or [e for e in index if e["kind"] != "liked"]
    opener = max((e for e in feed if e["bright"] > 0.25), key=lambda e: e["score"], default=max(feed, key=lambda e: e["score"]))
    out = {"chapters": {}, "focal": {}, "source_of": {}}
    op = prepare(opener["src"])
    out["chapters"]["opener"] = [op] if op else []
    if op:
        out["focal"][op] = f"{opener['focal'][0] * 100:.0f}% {opener['focal'][1] * 100:.0f}%"
        out["source_of"][op] = opener["src"]
    _env.write_json("build/picks.json", out)
    kinds = {k: sum(1 for e in index if e["kind"] == k) for k in ("post", "story", "liked")}
    print(f"indexed {len(index)} photos ({kinds['post']} post, {kinds['story']} story, {kinds['liked']} liked; "
          f"{skipped} could not be opened)")
    print("wrote build/picks.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
