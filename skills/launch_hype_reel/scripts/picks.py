#!/usr/bin/env python3
"""Movement 1, research: prepare the product's assets, the posts that drew the most response, and the photos around
them. Writes build/photo_index.json, build/picks.json and build/photos/*.jpg.

USAGE (from the workspace root):
    python3 S/scripts/picks.py

Scores every photo of the person's window (color, contrast, exposure), finds each one's focal point (where the
detail is, so a cover crop keeps it), converts HEIC and rotates by EXIF, and saves a 1600 px JPEG copy in
build/photos/. picks.json carries:
  product   the product's own stills (build/library/product/stills, from the asset folder or link), each prepared
            and scored, best first; when there are none, the person's posts that mention the product stand in
  footage   the product's own clips, each with a poster frame (40% of the way in)
  top       the nine posts that drew the most comments and saves, in rank order, each with its photo (a reel's poster frame)
  chapters  "product" (the stills, best first), "top" (those posts' photos), "feed" (the person's most striking
            photos outside both, for teases and the world around the product)
source_of maps every prepared photo back to its library file, which qa.py gate reads to prove a product beat uses
the product's own asset. To swap a photo, run `grade.py photos FILE` and put "graded/<name>.jpg" in the beat's
"photos" in build/storyboards/N/storyboard.json.
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


def still_of(path):
    return poster(path) if Path(path).suffix.lower() in VIDEO else prepare(path)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    s = _env.read_json("build/stats.json")
    if not d or not s:
        sys.exit("run gather.py and stats.py first")
    launch = d.get("launch") or {}
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
    out = {"product": [], "footage": [], "top": [], "chapters": {}, "focal": {}, "source_of": {}}

    def keep(photo, src, a):
        out["focal"][photo] = f"{a['focal'][0] * 100:.0f}% {a['focal'][1] * 100:.0f}%"
        out["source_of"][photo] = src

    for src in launch.get("stills") or []:
        ph = prepare(src)
        if ph:
            a = analyse(ph)
            out["product"].append({"photo": ph, "src": src, "own": True, **a})
            keep(ph, src, a)
    for src in launch.get("footage") or []:
        ph = poster(src)
        if ph:
            a = analyse(ph)
            out["footage"].append({"file": src, "poster": ph, **a})
            keep(ph, src, a)
    if not out["product"]:
        for p in s.get("product_posts") or []:
            ph = still_of(p["media"])
            if ph:
                a = analyse(ph)
                out["product"].append({"photo": ph, "src": p["media"], "own": False, **a})
                keep(ph, p["media"], a)
    out["product"].sort(key=lambda e: -e["score"])
    for t in s.get("top") or []:
        ph = still_of(t["media"])
        if not ph:
            print(f"skip rank {t['rank']}: its media cannot be opened ({Path(t['media']).name})", file=sys.stderr)
            continue
        a = analyse(ph)
        out["top"].append({"rank": t["rank"], "kind": t["kind"], "photo": ph, "src": t["media"], "video": t.get("video"), **a})
        keep(ph, t["media"], a)
    if not index and not out["product"]:
        sys.exit("no photos could be opened; the film needs at least one photo of theirs or of the product")
    _env.write_json("build/photo_index.json", index)
    taken = {e["src"] for e in out["top"]} | {e["src"] for e in out["product"]}
    feed = sorted((e for e in index if e["kind"] == "post" and e["src"] not in taken and e["bright"] > 0.22), key=lambda e: -e["score"])
    chosen = []
    for e in feed[:12]:
        ph = prepare(e["src"])
        if ph:
            chosen.append(ph)
            keep(ph, e["src"], e)
    out["chapters"] = {"product": [e["photo"] for e in out["product"]], "top": [e["photo"] for e in out["top"]], "feed": chosen}
    _env.write_json("build/picks.json", out)
    print(f"indexed {len(index)} photos ({skipped} could not be opened); prepared {len(list(PHOTOS.glob('*.jpg')))} in build/photos/")
    print(f"product: {len(out['product'])} stills ({'their own asset folder' if any(e['own'] for e in out['product']) else 'posts that mention it'}), "
          f"{len(out['footage'])} clips")
    for e in out["product"]:
        print(f"  {Path(e['src']).name}  score {e['score']}  bright {e['bright']}")
    for n in out["top"]:
        print(f"  top {n['rank']}. {n['kind']:<5} {Path(n['src']).name}  score {n['score']}")
    print("wrote build/picks.json and build/photo_index.json")
    return 0 if out["product"] or out["top"] else 1


if __name__ == "__main__":
    sys.exit(main())
