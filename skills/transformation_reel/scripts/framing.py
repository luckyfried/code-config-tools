#!/usr/bin/env python3
"""Frame the subject's photographs for the studio compositions: each photograph stands whole on one table line.

USAGE (from the workspace root; S = this skill's folder; storyboard.py draft runs it):
    python3 S/scripts/framing.py

Reads RUN/subject.json (timeline.py) and writes RUN/public/: matched/<post id>.jpg, one plate per dated post,
matched/measure.json, photos/<post id>.jpg (the photograph alone, upright, at the size that fills the film's frame at
a station: it covers STATION px, never enlarged past the original), tiles/<post id>.jpg (the same at TILE px on its
long side, which the wall shows), and the fonts and grain the compositions load.

Every photograph, day one included, takes the one grade of the set before any copy is made: its exposure moves
GRADE of the way toward the set's median lightness (a gamma on all three channels, never past GAMMA), its white balance
BALANCE of the way toward the set's median color (a gain per channel inside GAIN that leaves its lightness where the
exposure put it), and its saturation SATURATE of the way toward the set's median chroma (inside CHROMA), so a dark
first post, a cool white studio shot and a warm kitchen one sit in one film, and the change between them stays theirs.

The photographs share no table (different rooms, phones and distances), so each is framed, never registered or
cropped: the photograph stands whole, at its own aspect however wide or tall, inside a box FRAME_W wide and FRAME_H
tall, centered, its bottom on the table line. The plate around it, PLATE_W by PLATE_H with the table line at
PLATE_TABLE, is the same photograph enlarged, blurred and darkened, so the frame has no hard edge at any scale and
type reads over it.

measure.json per post: id, date, day (day one is 1), kind, file, photo, tile, aspect (width over height), focal (the
point of interest as fractions of the photograph, from research), src (the photograph's own path, by which
taste.json's moments name it), caption (hashtags off), line and next (their curated words on it, storyboard.told),
milestone (timeline.py's flag), words, look (the photograph in a grid of LOOK cells, rows top to bottom: `light`,
each cell's mean lightness 0-1, and `busy`, its mean edge strength 0-1, which decide where their words stand on it and
how far the photograph darkens under them), table (FRAME_H), extent (the photograph's box [x0, y0, x1, y1] in the FRAME_W x FRAME_H box, its
bottom on the table), tallest_px, sharp (the 99.5th percentile of its edge contrast at the size it is shown: of two
posts, the higher one is the one to hold), wall and wood (the plate's color just above and just below the box).
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

W = 1080
FRAME_W, FRAME_H = 1080, 840
STATION = (1240, 2200)  # the reel frame at a station with its overfill and its push in, the largest a photograph is shown
TILE = 800
LOOK = (12, 20)  # the look grid's columns and rows
PLATE_H, PLATE_TABLE = 5200, 2600
GRADE = 0.6        # how far each photograph's lightness moves toward the set's median
GAMMA = (0.5, 1.8)  # the least and the most gamma the grade applies
BALANCE = 0.7      # how far each photograph's color moves toward the set's median color
GAIN = (0.8, 1.25)  # the least and the most gain the balance gives one channel
SATURATE = 0.6     # how far each photograph's chroma moves toward the set's median chroma
CHROMA = (0.7, 1.2)  # the least and the most the saturation is scaled
LUMA = (0.299, 0.587, 0.114)  # the lightness the balance keeps, weighted as a grayscale copy weighs it
STILLS = {".jpg", ".jpeg", ".png", ".webp"}


def edge_contrast(im):
    from PIL import ImageChops
    g = im.convert("L")
    e = sorted(ImageChops.lighter(ImageChops.difference(g, ImageChops.offset(g, 1, 0)), ImageChops.difference(g, ImageChops.offset(g, 0, 1))).tobytes())
    return e[int(len(e) * 0.995)]


def framed_plate(im):
    """The photograph whole on the table line inside the frame's box, on its own enlarged, blurred and darkened copy.
    Returns the plate, the photograph as shown, and its box in the frame's coordinates."""
    from PIL import Image, ImageFilter
    k = min(FRAME_W / im.width, FRAME_H / im.height)
    pw, ph = round(im.width * k), round(im.height * k)
    shown = im.resize((pw, ph), Image.LANCZOS)
    c = max(W / 4 / im.width, PLATE_H / 4 / im.height)
    fill = im.resize((max(1, round(im.width * c)), max(1, round(im.height * c))), Image.BOX)
    fill = fill.crop(((fill.width - W // 4) // 2, (fill.height - PLATE_H // 4) // 2, (fill.width - W // 4) // 2 + W // 4, (fill.height - PLATE_H // 4) // 2 + PLATE_H // 4))
    fill = fill.filter(ImageFilter.GaussianBlur(14)).resize((W, PLATE_H), Image.BICUBIC).point(lambda v: round(v * 0.38))
    x0 = (W - pw) // 2
    fill.paste(shown, (x0, PLATE_TABLE - ph))
    return fill, shown, [x0, FRAME_H - ph, x0 + pw, FRAME_H]


def still_of(p, work):
    """The post's picture: the original still when it is one Pillow reads, else the prepared copy; a reel's middle frame."""
    from PIL import Image
    if p.get("video"):
        dest = work / f"{p['id']}-frame.jpg"
        r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p["video"])], capture_output=True, text=True)
        mid = max(0.0, float(r.stdout.strip() or 0) / 2)
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-ss", f"{mid:.2f}", "-i", str(p["video"]), "-frames:v", "1", "-q:v", "2", str(dest)], check=True)
        return Image.open(dest)
    for f in (p.get("src"), p.get("photo")):
        if f and Path(f).suffix.lower() in STILLS and Path(f).exists():
            return Image.open(f)
    return Image.open(p["photo"])


def lightness(im):
    """The photograph's mean lightness, 0-1."""
    from PIL import Image
    return sum(im.convert("L").resize((64, 64), Image.BOX).tobytes()) / (64 * 64 * 255)


def graded(im, mean, target):
    """The photograph with the set's grade: its mean lightness `mean` moved GRADE of the way toward `target`."""
    import math
    goal = mean ** (1 - GRADE) * target ** GRADE
    e = min(GAMMA[1], max(GAMMA[0], math.log(goal) / math.log(mean))) if 0 < mean < 1 and 0 < goal < 1 else 1.0
    return im.point([round(255 * (v / 255) ** e) for v in range(256)] * 3)


def color_of(im):
    """The photograph's mean color, each channel 0-1, and its mean chroma (HSV saturation) 0-1."""
    from PIL import Image
    small = im.resize((64, 64), Image.BOX)
    rgb = [v / 255 for v in small.resize((1, 1), Image.BOX).getpixel((0, 0))]
    sat = small.convert("HSV").getchannel("S")
    return rgb, sum(sat.tobytes()) / (64 * 64 * 255)


def balanced(im, rgb, chroma, target_rgb, target_chroma):
    """The photograph with the set's balance: its mean color `rgb` moved BALANCE of the way toward `target_rgb` by a
    gain per channel, its lightness kept, and its chroma moved SATURATE of the way toward `target_chroma`."""
    gain = [min(GAIN[1], max(GAIN[0], (t / max(m, 1e-3)) ** BALANCE)) for m, t in zip(rgb, target_rgb)]
    keep = sum(w * m for w, m in zip(LUMA, rgb)) / max(1e-3, sum(w * m * g for w, m, g in zip(LUMA, rgb, gain)))
    gain = [g * keep for g in gain]
    k = min(CHROMA[1], max(CHROMA[0], (target_chroma / max(chroma, 1e-3)) ** SATURATE))
    # one matrix: the gain on each channel, then each pixel's chroma scaled by k about its own lightness
    rows = [[(LUMA[j] * (1 - k) + (k if i == j else 0)) * gain[j] for j in range(3)] + [0] for i in range(3)]
    return im.convert("RGB", [v for r in rows for v in r])


def look_of(im):
    """The photograph's lightness and edge strength per cell of a LOOK grid, rows top to bottom."""
    from PIL import Image, ImageFilter
    cols, rows = LOOK
    small = im.convert("L").resize((cols * 16, rows * 16), Image.BOX)
    edges = small.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    grid = lambda g: [[round(v / 255, 3) for v in list(g.resize((cols, rows), Image.BOX).getdata())[r * cols:(r + 1) * cols]] for r in range(rows)]
    return {"light": grid(small), "busy": grid(edges)}


def hex_of(im):
    from PIL import Image
    return "#%02x%02x%02x" % im.resize((1, 1), Image.BOX).getpixel((0, 0))


def frame(posts, public):
    """Plates and measure.json for dated `posts` (oldest first) under `public`/matched; returns the measure."""
    from PIL import Image, ImageOps
    out = Path(public) / "matched"
    out.mkdir(parents=True, exist_ok=True)
    # measure.json names these photographs, so it goes before the first one changes (the caller removes the boards
    # laid out from it first)
    (out / "measure.json").unlink(missing_ok=True)
    first = date.fromisoformat(posts[0]["date"])
    # each photograph at the largest size any copy shows it, and the set's median lightness the grade moves them toward
    ims = []
    for p in posts:
        im = ImageOps.exif_transpose(still_of(p, out)).convert("RGB")
        k = min(1.0, max(STATION[0] / im.width, STATION[1] / im.height))
        ims.append(im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS) if k < 1 else im)
    means = [lightness(im) for im in ims]
    target = sorted(means)[len(means) // 2]
    ims = [graded(im, mean, target) for im, mean in zip(ims, means)]
    colors = [color_of(im) for im in ims]
    mid = lambda xs: sorted(xs)[len(xs) // 2]
    to_rgb, to_chroma = [mid([c[0][i] for c in colors]) for i in range(3)], mid([c[1] for c in colors])
    rows = []
    for p, im, (rgb, chroma) in zip(posts, ims, colors):
        im = balanced(im, rgb, chroma, to_rgb, to_chroma)
        pl, shown, extent = framed_plate(im)
        name = f"{p['id']}.jpg"
        with _env.whole(out / name) as tmp:
            pl.save(tmp, quality=92)
        for folder, k in (("photos", 1.0), ("tiles", min(1.0, TILE / max(im.size)))):
            (Path(public) / folder).mkdir(exist_ok=True)
            with _env.whole(Path(public) / folder / name) as tmp:
                (im if k == 1.0 else im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)).save(tmp, quality=92)
        caption = re.sub(r"\s*#\w+", "", p.get("caption") or "").strip()
        rows.append({
            "id": p["id"], "date": p["date"], "day": (date.fromisoformat(p["date"]) - first).days + 1, "kind": p.get("kind", "post"),
            "file": f"matched/{name}", "photo": f"photos/{name}", "tile": f"tiles/{name}", "aspect": round(im.width / im.height, 5), "focal": p.get("focal") or [0.5, 0.5], "src": p.get("src"), "caption": caption,
            "line": p.get("line") or "", "next": p.get("next") or "", "milestone": bool(p.get("milestone")), "words": len(caption.split()), "look": look_of(im),
            "table": FRAME_H, "extent": extent, "tallest_px": extent[3] - extent[1], "sharp": edge_contrast(shown),
            "wall": hex_of(pl.crop((0, PLATE_TABLE - FRAME_H - 24, W, PLATE_TABLE - FRAME_H))),
            "wood": hex_of(pl.crop((0, PLATE_TABLE + 24, W, PLATE_TABLE + 48))),
        })
    m = {"fit": "frame", "table": FRAME_H, "width": FRAME_W, "height": FRAME_H, "plate": {"width": W, "height": PLATE_H, "table": PLATE_TABLE}, "posts": rows}
    _env.write_json(out / "measure.json", m)
    return m


def furnish(public):
    """The fonts and the grain tile the compositions load from the public folder, copied over on every staging so a
    run never keeps an older copy."""
    public = Path(public)
    shutil.copytree(_env.SKILL / "fonts", public / "fonts", dirs_exist_ok=True)
    shutil.copytree(_env.SKILL / "motion" / "public" / "fx", public / "fx", dirs_exist_ok=True)


def main():
    _env.open_run()
    _env.need("PIL")
    sub = _env.read_json(_env.b("subject.json"))
    if not sub:
        sys.exit("RUN/subject.json is missing: run research.py first")
    posts = [p for p in sub["posts"] if p.get("date")]
    for board in _env.b("storyboards").glob("*/storyboard.json"):
        board.unlink()
    m = frame(posts, _env.b("public"))
    furnish(_env.b("public"))
    for r in m["posts"]:
        print(r["id"], r["date"], "day", r["day"], "box", r["extent"], "sharp", r["sharp"], r["caption"][:50])
    return 0


if __name__ == "__main__":
    sys.exit(main())
