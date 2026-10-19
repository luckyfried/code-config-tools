#!/usr/bin/env python3
"""Movement 1, research: the posts the film carries, in date order. Reads build/subject.json (timeline.py),
writes build/picks.json. Also the photo helpers the other scripts share (prepare, poster, analyse).

USAGE (from the workspace root):
    python3 S/scripts/picks.py [--beats 12]

The sequence is the subject's first post, every milestone, the latest post, and between them posts spread evenly
by date (their own reels first where two candidates sit close, since a reel is footage of the change) until the
sequence holds --beats posts. Every photo is a 1600 px JPEG copy in build/photos/ (HEIC converted, EXIF rotation
applied); a reel stands in by its poster frame (ffmpeg, 40% of the way in) and stays available as footage.
picks.json carries the sequence oldest first (each post's id, date, photo, library source, reel, caption,
milestone flag, visible change and focal point), the first and the latest, and the photos' focal points.
To swap a post, edit the beat's "post", "at" and "photos" in build/storyboards/N/storyboard.json (run
`grade.py photos FILE` for a photo that is not graded yet); storyboard.py check keeps the dates in order.
"""
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
    # the calmer of the photo's upper and lower bands (edge energy once grain is blurred away): where a card of type
    # can sit over the photo without covering what it shows
    soft = small.convert("L").filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    band = lambda a, b: ImageStat.Stat(soft.crop((2, int(sh * a), sw - 2, max(int(sh * a) + 1, int(sh * b))))).mean[0]
    calm = "top" if band(0.08, 0.45) < band(0.55, 0.92) else "bottom"
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "calm": calm, "colors": dom}


def sequence(posts, firsts, n):
    """first, milestones, latest, then the post nearest each gap's middle by date, until n posts."""
    keep = {posts[0]["id"], posts[-1]["id"]} | set(firsts)
    while len(keep) < min(n, len(posts)):
        chosen = sorted((p for p in posts if p["id"] in keep), key=lambda p: p["ts"])
        a, b = max(zip(chosen, chosen[1:]), key=lambda ab: ab[1]["ts"] - ab[0]["ts"])
        mid = (a["ts"] + b["ts"]) / 2
        between = [p for p in posts if a["ts"] < p["ts"] < b["ts"]]
        if not between:
            break
        span = b["ts"] - a["ts"]
        best = min(between, key=lambda p: abs(p["ts"] - mid) - (0.2 * span if p.get("video") else 0))
        keep.add(best["id"])
    return [p for p in posts if p["id"] in keep]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--beats", type=int, default=12, help="how many posts the film carries (first and latest included)")
    a = ap.parse_args()
    sub = _env.read_json("build/subject.json")
    if not sub:
        sys.exit("build/subject.json is missing: run timeline.py first (research.py runs it)")
    posts = sub["posts"]
    seq = sequence(posts, [m["id"] for m in sub["milestones"]], max(2, a.beats))
    keys = ("id", "date", "ts", "kind", "photo", "src", "video", "caption", "milestone", "change", "step", "focal", "calm", "bright")
    out = {"subject": sub["subject"], "span": sub["span"], "first": posts[0]["id"], "latest": posts[-1]["id"],
           "sequence": [{k: p.get(k) for k in keys} for p in seq], "focal": {}, "source_of": {}}
    for p in seq:
        out["focal"][p["photo"]] = f"{p['focal'][0] * 100:.0f}% {p['focal'][1] * 100:.0f}%"
        out["source_of"][p["photo"]] = p["src"]
    _env.write_json("build/picks.json", out)
    print(f"the film carries {len(seq)} of {len(posts)} posts, {seq[0]['date']} to {seq[-1]['date']}:")
    for p in seq:
        print(f"  {p['id']} {p['date']} {p['kind']:<4} change {p['change']:.2f}{'  milestone' if p['milestone'] else ''}")
    print("wrote build/picks.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
