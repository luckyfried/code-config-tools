"""The month's photographs as the reel reads them: opened upright, measured, and the point of each one's subject.

One grade runs across the set: every photograph's mean lightness moves GRADE of the way toward the set's median
lightness by one gamma on all three channels (never past GAMMA), and its color cast (each channel's mean over the
three's) moves GRADE of the way toward the set's median cast (each channel's gain within CAST), before any copy of it
is staged, cropped or measured for the look, so a dark photograph and a bright one, a cool one and a warm one, sit in
one film."""
import colorsys
import functools
import math
import os

from PIL import Image, ImageFilter, ImageOps, ImageStat

GRADE = 0.6        # how far each photograph's lightness moves toward the set's median
GAMMA = (0.5, 1.8)  # the least and the most gamma the grade applies
CAST = (0.85, 1.18)  # the least and the most gain the grade applies to one channel
LONG = 2048
HUES = 24           # bins of the hue histogram the look's accent is read from
SAMPLE = 96         # the long side, px, a photograph is measured at
SWATCHES = 4        # the dominant colors read from each photograph


def open_image(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def size_of(path):
    with Image.open(path) as im:
        w, h = im.size
        o = (im.getexif() or {}).get(0x0112, 1)
    return (h, w) if o in (5, 6, 7, 8) else (w, h)


def skin(r, g, b):
    return r > 95 and g > 40 and b > 20 and r > g and r > b and r - min(g, b) > 15 and abs(r - g) > 15


def focus_of(im, cells=48):
    """The subject's point, [u, v]: detail x color distinctness (skin counts double) x a soft center prior, averaged
    over the strongest tenth of the cells."""
    w, h = im.size
    sw, sh = (cells, max(1, round(cells * h / w))) if w >= h else (max(1, round(cells * w / h)), cells)
    small = im.resize((sw, sh), Image.BILINEAR)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.BoxBlur(1))
    rgb, ed = small.load(), edges.load()
    mean = ImageStat.Stat(small).mean
    weights = []
    for y in range(sh):
        for x in range(sw):
            r, g, b = rgb[x, y]
            far = math.sqrt((r - mean[0]) ** 2 + (g - mean[1]) ** 2 + (b - mean[2]) ** 2) / 255
            u, v = (x + 0.5) / sw, (y + 0.5) / sh
            prior = math.exp(-((u - 0.5) ** 2 + (v - 0.5) ** 2) / (2 * 0.22 ** 2))
            wgt = (0.5 + ed[x, y] / 255) * (0.25 + far) * (2.0 if skin(r, g, b) else 1.0) * prior
            weights.append((wgt, u, v))
    weights.sort(reverse=True)
    top = weights[:max(1, len(weights) // 10)]
    tot = sum(wt for wt, _, _ in top) or 1
    fu = sum(wt * u for wt, u, _ in top) / tot
    fv = sum(wt * v for wt, _, v in top) / tot
    return [round(min(0.8, max(0.2, fu)), 2), round(min(0.8, max(0.2, fv)), 2)]


def lightness(im):
    """The photograph's mean lightness, 0-1."""
    return sum(im.convert("L").resize((64, 64), Image.BOX).tobytes()) / (64 * 64 * 255)


def cast_of(im):
    """The photograph's color cast: each channel's mean over the three channels' mean."""
    ch = ImageStat.Stat(im.convert("RGB").resize((64, 64), Image.BOX)).mean
    m = sum(ch) / 3 or 1.0
    return [c / m for c in ch]


def graded(im, mean, target, cast=None):
    """The photograph with the set's grade: its mean lightness `mean` moved GRADE of the way toward `target`, and its
    color cast GRADE of the way toward the set's `cast`."""
    if target is None:
        return im
    goal = mean ** (1 - GRADE) * target ** GRADE
    e = min(GAMMA[1], max(GAMMA[0], math.log(goal) / math.log(mean))) if 0 < mean < 1 and 0 < goal < 1 else 1.0
    own = cast_of(im) if cast else None
    gain = [min(CAST[1], max(CAST[0], (cast[c] / own[c]) ** GRADE)) if own[c] else 1.0 for c in range(3)] if cast else [1.0] * 3
    return im.point([min(255, round(255 * (v / 255) ** e * gain[c])) for c in range(3) for v in range(256)])


@functools.lru_cache(maxsize=256)
def _sample(path, stamp):
    im = Image.open(path)
    im.draft("RGB", (SAMPLE * 4, SAMPLE * 4))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((SAMPLE, SAMPLE), Image.BOX)
    return im


def sample(path):
    """The photograph upright at SAMPLE px on its long side, for measuring."""
    return _sample(str(path), os.stat(path).st_mtime_ns)


def median_lightness(paths):
    """The set's grade target: the median of its photographs' mean lightness (the upper of the two middle ones)."""
    means = sorted(lightness(sample(p)) for p in paths)
    return means[len(means) // 2] if means else None


def median_cast(paths):
    """The set's cast: each channel's median over its photographs' casts (the upper of the two middle ones)."""
    casts = [cast_of(sample(p)) for p in paths]
    return [round(sorted(c[i] for c in casts)[len(casts) // 2], 4) for i in range(3)] if casts else None


def measure(path, target, cast=None):
    """The photograph in the set's grade, measured: `light` its mean lightness 0-1, `busy` its mean edge strength 0-1,
    `color` its mean saturation 0-1, `hues` its saturated pixels' hue histogram (HUES bins, each pixel weighted by its
    saturation, over the pixel count), and `swatches` its SWATCHES dominant colors with the share of it each covers."""
    im = sample(path)
    im = graded(im, lightness(im), target, cast)
    edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
    raw = im.tobytes()
    px = list(zip(raw[0::3], raw[1::3], raw[2::3]))
    bins, sat = [0.0] * HUES, 0.0
    for r, g, b in px:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        sat += s
        if s > 0.25 and v > 0.18:
            bins[min(HUES - 1, int(h * HUES))] += s
    n = len(px) or 1
    return {"light": round(lightness(im), 3), "busy": round(ImageStat.Stat(edges).mean[0] / 255, 4),
            "color": round(sat / n, 4), "hues": [round(x / n, 5) for x in bins], "swatches": swatches_of(im)}


def swatches_of(im):
    """The photograph's SWATCHES dominant colors as [hex, share], the largest first."""
    q = im.quantize(SWATCHES, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:3 * SWATCHES]
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    return [["#%02x%02x%02x" % tuple(pal[3 * i:3 * i + 3]), round(c / total, 4)] for c, i in counts]


def stage(src, dest, target=None, cast=None):
    """The photograph as the film draws it: upright, at most LONG px on its long side, in the set's grade toward
    `target` (the set's median lightness) and `cast` (its median cast)."""
    im = open_image(src)
    im.thumbnail((LONG, LONG), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(f".{dest.name}.part")
    graded(im, lightness(im), target, cast).save(part, "JPEG", quality=90)
    os.replace(part, dest)
    return dest
