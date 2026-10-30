#!/usr/bin/env python3
"""The photo helpers the research scripts share: a 1600 px JPEG copy of a photograph in RUN/photos/ (HEIC
converted, EXIF rotation applied), a reel's poster frame (ffmpeg, 40% of the way in), and a photograph's read (its
size, score, brightness, focal point, calm band and dominant colors). A library module; it is not run on its own.
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

PHOTOS = _env.b("photos")
VIDEO = {".mp4", ".mov", ".m4v"}


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def prepare(path):
    """A 1600 px JPEG copy in RUN/photos/ (HEIC converted, EXIF rotation applied). Returns its path or None."""
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
    with _env.whole(dest) as tmp:
        im.save(tmp, "JPEG", quality=90)
    return str(dest.resolve())


def poster(video):
    """A reel's poster frame as a 1600 px JPEG in RUN/photos/, 40% of the way in. Returns its path or None."""
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
    try:
        with _env.whole(dest) as tmp:
            subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                            "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", str(tmp)], capture_output=True)
            if not (tmp.exists() and tmp.stat().st_size > 0):
                raise OSError("ffmpeg made no poster frame")
    except OSError:
        return None
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
    # the calmer of the photo's upper and lower bands (edge energy once grain is blurred away): where a card of type
    # can sit over the photo without covering what it shows
    soft = small.convert("L").filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    band = lambda a, b: ImageStat.Stat(soft.crop((2, int(sh * a), sw - 2, max(int(sh * a) + 1, int(sh * b))))).mean[0]
    calm = "top" if band(0.08, 0.45) < band(0.55, 0.92) else "bottom"
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "calm": calm, "colors": dom}
