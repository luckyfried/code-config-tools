#!/usr/bin/env python3
"""Movement 1, research: read every photo. Writes photo_index.json, picks.json and photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Reads every photo of the person's posts and stories and every liked image (color, contrast, exposure, focal
point, and the five colors each covers with their shares), converting HEIC and rotating by EXIF. Each index row
carries its kind (post, story, liked) and, for a post, "row", its place in library.json's posts, so the research
joins a photo to its caption and its time. picks.json names the opener, the feed's most striking photo, as a
1600 px JPEG copy in photos/.
"""
import datetime as dt
import hashlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat  # noqa: E402

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

PHOTOS = Path("photos")
VIDEO = {".mp4", ".mov", ".m4v"}
# a cell of a picture holds no detail when its edge strength is under QUIET (0-255); a picture with at least FLAT of its
# cells quiet (a sky, a beach, a plain wall) is plain, and its subject is the spot that stands out from its surround
QUIET, FLAT = 12, 0.7


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def prepare(path):
    """A 1600 px JPEG copy in photos/ (HEIC converted, EXIF rotation applied). Returns its path or None."""
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
    # a photograph that is there is kept, so it is made under another name and moved in whole
    tmp = _env.part(dest)
    im.save(tmp, "JPEG", quality=90)
    os.replace(tmp, dest)
    return str(dest.resolve())


def poster(video):
    """A reel's poster frame as a 1600 px JPEG in photos/, 40% of the way in. Returns its path or None."""
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
    tmp = _env.part(dest)
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", str(tmp)], capture_output=True)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return None
    os.replace(tmp, dest)
    return str(dest.resolve())


def subject(path):
    """Where a photograph's subject sits (u, v, 0 to 1) and whether the picture is plain, mostly without detail: in a
    plain picture, as a couple on an empty beach, the spot whose colour stands out most from what surrounds it; in a
    picture whose detail runs all over it, where its detail gathers (analyse's focal point)."""
    im = open_image(path, draft=(160, 200))
    w, h = im.size
    small = im.resize((64, max(1, round(64 * h / w))))
    sw, sh = small.size
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES).get_flattened_data()
    # the outer three cells are left out: the edge filter reads the picture's own border as detail
    inner = [k for k in range(sw * sh) if 3 <= k % sw < sw - 3 and 3 <= k // sw < sh - 3]
    if sum(edges[k] < QUIET for k in inner) < FLAT * len(inner):
        return analyse(path)["focal"], False
    stands = ImageChops.difference(small, small.filter(ImageFilter.BoxBlur(8))).convert("L").filter(ImageFilter.BoxBlur(1))
    k = max(inner, key=stands.get_flattened_data().__getitem__)
    return [round((k % sw + 0.5) / sw, 2), round((k // sw + 0.5) / sh, 2)], True


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
    _env.enter()
    d = _env.read_json("library.json")
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
    _env.write_json("photo_index.json", index)
    feed = [e for e in index if e["kind"] == "post"] or [e for e in index if e["kind"] != "liked"]
    opener = max((e for e in feed if e["bright"] > 0.25), key=lambda e: e["score"], default=max(feed, key=lambda e: e["score"]))
    out = {"chapters": {}, "focal": {}, "source_of": {}}
    op = prepare(opener["src"])
    out["chapters"]["opener"] = [op] if op else []
    if op:
        out["focal"][op] = f"{opener['focal'][0] * 100:.0f}% {opener['focal'][1] * 100:.0f}%"
        out["source_of"][op] = opener["src"]
    _env.write_json("picks.json", out)
    kinds = {k: sum(1 for e in index if e["kind"] == k) for k in ("post", "story", "liked")}
    print(f"indexed {len(index)} photos ({kinds['post']} post, {kinds['story']} story, {kinds['liked']} liked; "
          f"{skipped} could not be opened)")
    print("wrote picks.json and photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
