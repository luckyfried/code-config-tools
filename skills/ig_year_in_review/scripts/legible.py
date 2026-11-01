"""Type a phone shows legibly over what stands behind it (motion/system/standards.md, R3): the contrast a line needs at
its size, the light of a photograph behind a line under the scrim a film lays there, and the scrim a line needs to read.
Every kit lays its captions out and reads them in its storyboard check through these, so a caption is measured against
the pixels under it before the film renders.

A line's contrast is the WCAG 2 ratio of its color against the quarter of what is behind it nearest its own light: the
brightest quarter under light type, the darkest under dark type, so a few bright patches under paper count, and the
median alone never passes a busy photograph."""
from pathlib import Path

PHONE = 390 / 1080  # points a phone 390 points wide shows each px of a 1080 px wide frame in
LARGE = 24          # points: type at this size or larger reads at 3:1; smaller type needs 4.5:1 (WCAG 2, level AA)
LEAST = 32          # px on a 1080 px wide frame: the smallest type a phone shows legibly, about 11.5 points
SCRIM_MOST = 0.9    # the deepest scrim a line may ask for: past it the photograph under the words is gone


def lum(c):
    """Relative luminance of a hex color or of a 0-1 gray."""
    v = [int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)] if isinstance(c, str) else [c] * 3
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def ratio(a, b):
    """The contrast of two luminances, 1 to 21."""
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def need(size, width=1080):
    """The contrast a line `size` px tall on a frame `width` px wide needs on a phone."""
    return 3.0 if size * 1080 / width * PHONE >= LARGE else 4.5


def quarters(file, crop):
    """The gray (0-1) of the darkest quarter's top, the median and the brightest quarter's foot of an image file
    (absolute, or under the run's public/) inside `crop`, [x0, y0, x1, y1] in its own px; None when the crop is empty."""
    from PIL import Image
    path = Path(file) if Path(file).is_absolute() else Path("public") / file
    im = Image.open(path).convert("L")
    x0, y0, x1, y1 = (max(0, min(n, round(v))) for v, n in zip(crop, (im.width, im.height) * 2))
    if x1 <= x0 or y1 <= y0:
        return None
    h = im.crop((x0, y0, x1, y1)).histogram()
    n, seen, q = sum(h), 0, {}
    for v, c in enumerate(h):
        seen += c
        for k in (0.25, 0.5, 0.75):
            if k not in q and seen >= k * n:
                q[k] = v / 255
    return q[0.25], q[0.5], q[0.75]


def under(file, place, box):
    """quarters() of a photograph laid over a frame at `place` ([x, y, width, height] frame px) under `box`, frame px."""
    x, y, w, h = place
    from PIL import Image
    path = Path(file) if Path(file).is_absolute() else Path("public") / file
    with Image.open(path) as im:
        sx, sy = im.width / w, im.height / h
    return quarters(file, [(box[0] - x) * sx, (box[1] - y) * sy, (box[2] - x) * sx, (box[3] - y) * sy])


def behind(gray, scrim=0.0, linear=True):
    """The luminance of a 0-1 gray under a black scrim of opacity `scrim`: a 3D film blends it in linear light, a page
    drawn with CSS blends the encoded value."""
    return lum(gray) * (1 - scrim) if linear else lum(gray * (1 - scrim))


def contrast(color, q, scrim=0.0, linear=True):
    """A line of `color` over quarters `q` under the scrim: its contrast against the quarter nearest its own light."""
    c = lum(color)
    worst = q[2] if c > behind(q[1], scrim, linear) else q[0]
    return ratio(c, behind(worst, scrim, linear))


def scrim_for(color, q, wanted, least=0.0, linear=True):
    """The shallowest scrim, `least` or deeper, under which a line of `color` reads at `wanted` over quarters `q`, in
    steps of 0.01; None when even SCRIM_MOST does not."""
    s = least
    while s <= SCRIM_MOST + 1e-9:
        if contrast(color, q, s, linear) >= wanted:
            return round(s, 2)
        s += 0.01
    return None
