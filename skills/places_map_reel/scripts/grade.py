#!/usr/bin/env python3
"""The film's light: every photograph of the cast brought into one grade, and the grain tile the renderer lays over it.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/grade.py photos     # cast.json -> public/photos/<place>-<n>-<k>.jpg and public/photos.json

cast.json (picks.py) lists the visits in route order, each with the photographs it shows. The first is the visit's own
print: the photograph of its moment in taste.json (the one the curation pairs with it, else its post's own), set
before whatever cast.json put first, so their words stand on the photograph they were written under.

Every photograph goes through the same steps, toward the same three middles taken from the cast itself: the median
temperature of its color photographs (the mean red less blue of the mid-tones), the median of their lightness (the
median luminance after the levels, kept inside LIGHT) and the median saturation (kept inside SAT). The steps:
  levels       one curve on the luminance, the same for all three channels, white set at WHITE, so nothing the source
               holds is pushed into clipping
  saturation   scaled toward the cast's middle by a factor inside GAIN, so a vivid photograph keeps most of its color
               and a muted one is not forced loud
  white        a per-photograph white balance moving its temperature WB of the way toward the cast's middle, red and
               blue gains of the same size in opposite directions, scaled so no gain is over 1: a warm source stays
               warmer than a cool one, and the spread of temperature across the stops narrows
  exposure     a gamma under WHITE moving its median luminance toward the cast's middle with strength EXPOSE
  print        one warm print balance, BALANCE, the same for every color photograph
  tone         one wash from their year's colors (taste.json palette.year), TONE of the way toward the photograph's own
               lightness mapped from their year's darkest color through its most shared one to the paper, so every
               photograph of the film, of any light, sits in the one color family; none without a palette
A black-and-white source takes the levels, the exposure and the tone, with no white balance, saturation or print
balance. Each keeps its whole frame, never enlarged: a source over LONG px on its
long side comes down to LONG, or to COVER on its short side when that is larger, so it still covers any format's frame
without the film enlarging it.
public/photos.json carries, per photograph, {place, n, k, file, w, h, aspect, color, focus, subject, line, about, camera,
texture, look, gray, home, source}: `color` is the most saturated mid-tone of its lower two thirds; `subject` the box that holds the central
half of the photograph's detail as [u0, v0, u1, v1] fractions (the edge strength of a small blurred copy) and `focus`
that box's center, where the film centers the photograph in the frame; `gray` whether the source is black and white;
`line` the photograph's own strongest straight line as [u0, v0, u1, v1] fractions when the person reading the
photographs wrote one into cast.json (a shot given as {"file", "line"}), else null, and the drive film's cut takes its
slope; `about` (what the photograph shows and its light), `camera` (its lens feel and the camera's height) and
`texture` (the place's material close up, with no subject and no landmark) as that person wrote them for the shot, else
null, which the stop's clip request is written from; `look` the photograph in a grid of LOOK cells, rows top to bottom: `light`, each cell's mean lightness 0-1, and
`busy`, its mean edge strength 0-1, from which the drive film holds a busier photograph and a bigger change from the
stop before longer. The source files are read, never changed.
"""
import argparse
import colorsys
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUBLIC = Path("public")
LONG = 2560
COVER = 1920
# the one print balance every color photograph takes: red, green and blue gains
BALANCE = (1.025, 1.0, 0.965)
# the levels' white, under 255 by the balance's red gain, and the share of the darkest and brightest pixels the levels
# set at black and white
WHITE = 248
CUT = 0.002
# the cast's middle lightness is kept inside LIGHT; the exposure moves a photograph's median toward it with strength
# EXPOSE: gamma = (log middle / log median) ** EXPOSE, on the scale up to WHITE
LIGHT = (0.4, 0.6)
EXPOSE = 0.7
# the white balance moves a photograph's temperature this share of the way toward the cast's middle, its red and blue
# gains at most WB_MOST from 1
WB, WB_MOST = 0.75, 0.3
# the saturation every color photograph is scaled toward: the cast's median, kept inside SAT; one photograph's factor
# is kept inside GAIN, so a vivid photograph (a sunset, a field of tulips) keeps at least 0.7 of its saturation and a
# muted photograph is not forced loud
SAT = (0.22, 0.4)
GAIN = (0.7, 1.35)
# the share of the way every photograph moves toward their year's colors (tone), and the paper the wash ends in
TONE = 0.24
PAPER = "#f4eee3"
# a source whose channels differ by less than this on average is black and white
GRAY = 3.0
# the look grid's columns and rows
LOOK = (6, 6)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(img):
    hist = img.convert("L").resize((64, 64)).histogram()
    return sum(i * n for i, n in enumerate(hist)) / (255 * sum(hist))


def pixels(img):
    """The image's pixels in order (get_flattened_data from Pillow 12 on, getdata before it)."""
    return list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())


def is_gray(img):
    """The source is black and white: its channels differ by less than GRAY on average."""
    px = pixels(img.resize((64, 64)))
    return sum(max(p) - min(p) for p in px) / len(px) < GRAY


def levels(img):
    """One curve for all three channels: levels on the luminance, the CUT darkest at black and the CUT brightest at
    WHITE."""
    hist = img.convert("L").histogram()
    total = sum(hist)
    run, lo, hi = 0, 0, 255
    for v, n in enumerate(hist):
        run += n
        if run >= CUT * total:
            lo = v
            break
    run = 0
    for v in range(255, -1, -1):
        run += hist[v]
        if run >= CUT * total:
            hi = v
            break
    hi = max(hi, lo + 16)
    return img.point([round(max(0.0, min(1.0, (i - lo) / (hi - lo))) * WHITE) for i in range(256)] * len(img.getbands()))


def lightness(img):
    """The photograph's median luminance on the scale up to WHITE, 0 to 1."""
    hist = img.convert("L").resize((96, 96)).histogram()
    run, total = 0, sum(hist)
    for v, n in enumerate(hist):
        run += n
        if run >= total / 2:
            return min(1.0, v / WHITE)
    return 0.5


def expose(img, middle):
    """A gamma under WHITE moving the photograph's median luminance toward `middle` with strength EXPOSE: black and
    WHITE stay where they are, so nothing clips."""
    m = max(0.02, min(0.98, lightness(img)))
    gamma = (math.log(middle) / math.log(m)) ** EXPOSE
    return img.point([round(WHITE * min(1.0, i / WHITE) ** gamma) for i in range(256)] * len(img.getbands()))


def mids(img):
    """The photograph's mid-tone pixels (luminance 30 to 243) on a small copy."""
    px = pixels(img.convert("RGB").resize((96, 96)))
    return [p for p in px if 30 < 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] < 243] or px


def temperature(img):
    """How warm the photograph is: the mean red less blue of its mid-tones, over 255."""
    m = mids(img)
    return sum(r - b for r, g, b in m) / len(m) / 255


def white(img, toward):
    """The photograph's temperature moved WB of the way toward `toward`: red and blue gains 1 + a and 1 - a, all three
    gains scaled so none is over 1, `a` found in three measured steps and kept within WB_MOST."""
    from PIL import Image
    now = temperature(img)
    want = now + WB * (toward - now)
    m = mids(img)
    slope = max(0.05, sum(r + b for r, g, b in m) / len(m) / 255)
    gains = lambda a: [k / (1 + abs(a)) for k in (1 + a, 1.0, 1 - a)]
    shift = lambda a: Image.merge("RGB", [ch.point(lambda v, k=k: round(v * k)) for ch, k in zip(img.split(), gains(a))])
    a, out = 0.0, img
    for _ in range(3):
        a = max(-WB_MOST, min(WB_MOST, a + (want - now) / slope))
        out = shift(a)
        now = temperature(out)
    return out


def saturation(img):
    """The mean saturation of the photograph's mid-tones, 0 to 1."""
    small = img.resize((96, 96))
    got = [h[1] for h in pixels(small.convert("HSV")) if 30 < h[2] < 243]
    return sum(got) / len(got) / 255 if got else 0.0


def saturate(img, target):
    """The photograph's saturation scaled toward `target`, the factor kept inside GAIN, measured again once because the
    enhancer is not exactly proportional."""
    from PIL import ImageEnhance
    k = 1.0
    for _ in range(2):
        now = saturation(ImageEnhance.Color(img).enhance(k))
        if now < 1e-3:
            return img
        k = max(GAIN[0], min(GAIN[1], k * target / now))
    return ImageEnhance.Color(img).enhance(k)


def balance(img):
    from PIL import Image
    return Image.merge("RGB", [ch.point(lambda v, k=k: min(255, round(v * k))) for ch, k in zip(img.split(), BALANCE)])


def color_of(img):
    """The most saturated mid-tone among the dominant colors of the photograph's lower two thirds, as #rrggbb."""
    from PIL import Image
    img = img.crop((0, img.height // 3, img.width, img.height))
    q = img.resize((96, 96)).quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    best, score = None, -1.0
    for count, idx in sorted(q.getcolors(), reverse=True):
        r, g, b = pal[idx * 3: idx * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l < 0.18 or l > 0.86:
            continue
        sc = (count ** 0.5) * (0.25 + s) * (1 - abs(l - 0.5))
        if sc > score:
            best, score = (r, g, b), sc
    return "#%02x%02x%02x" % (best or (128, 110, 90))


def subject_of(img):
    """The box holding the central half of the photograph's detail, as [u0, v0, u1, v1] fractions: the edge strength of
    a small blurred copy, its columns' and rows' totals cut at their quarter and three-quarter marks. The kit has no
    subject detector; the detail stands in for one."""
    from PIL import ImageFilter
    w = 96
    h = max(1, round(w * img.height / img.width))
    e = img.convert("L").resize((w, h)).filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(2))
    px = e.load()
    cols, rows = [0.0] * w, [0.0] * h
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            v = px[x, y]
            cols[x] += v
            rows[y] += v

    def span(totals):
        all_ = sum(totals)
        if not all_:
            return 0.25, 0.75
        run, a, b = 0.0, None, None
        for i, v in enumerate(totals):
            run += v
            if a is None and run >= 0.25 * all_:
                a = i
            if b is None and run >= 0.75 * all_:
                b = i + 1
        return a / len(totals), b / len(totals)

    (u0, u1), (v0, v1) = span(cols), span(rows)
    return [round(u0, 3), round(v0, 3), round(u1, 3), round(v1, 3)]


def focus_of(subject):
    """The subject's center as [u, v] fractions."""
    u0, v0, u1, v1 = subject
    return [round((u0 + u1) / 2, 3), round((v0 + v1) / 2, 3)]


def look_of(img):
    """The photograph's lightness and edge strength per cell of a LOOK grid, rows top to bottom, each 0 to 1."""
    from PIL import Image, ImageFilter
    cols, rows = LOOK
    small = img.convert("L").resize((cols * 16, rows * 16), Image.BOX)
    edges = small.filter(ImageFilter.GaussianBlur(1)).filter(ImageFilter.FIND_EDGES)
    grid = lambda g: [[round(v / 255, 3) for v in pixels(g.resize((cols, rows), Image.BOX))[r * cols:(r + 1) * cols]] for r in range(rows)]
    return {"light": grid(small), "busy": grid(edges)}


def toned(src):
    """The source read upright, never enlarged (brought down to LONG on its long side, or COVER on its short side when
    that is larger), through the levels; and whether it is black and white."""
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    f = min(1.0, max(LONG / max(img.size), COVER / min(img.size)))
    if f < 1:
        img = img.resize((round(img.width * f), round(img.height * f)), Image.LANCZOS)
    gray = is_gray(img)
    if gray:
        return levels(img.convert("L")).convert("RGB"), True
    return levels(img), False


def wash_of(taste):
    """The tone's three colors from their taste: their year's darkest color brought down to a shadow, its most shared one,
    and the paper; None when their taste names no year palette."""
    year = ((taste or {}).get("palette") or {}).get("year") or []
    if not year:
        return None
    rgb = lambda c: tuple(int(c["hex"][i:i + 2], 16) for i in (1, 3, 5))
    dark = min(year, key=lambda c: sum(rgb(c)))
    most = max(year, key=lambda c: c.get("share", 0))
    return tuple(round(v * 0.4) for v in rgb(dark)), rgb(most), tuple(int(PAPER[i:i + 2], 16) for i in (1, 3, 5))


def tone(img, wash):
    """The photograph TONE of the way toward its own lightness mapped through `wash` (wash_of)."""
    from PIL import Image, ImageOps
    if not wash:
        return img
    dark, mid, paper = wash
    return Image.blend(img, ImageOps.colorize(img.convert("L"), black=dark, white=paper, mid=mid), TONE)


def finish(img, gray, target, wash=None):
    """A leveled photograph through the rest of the grade toward the cast's middles `target` (target_of): its
    saturation, its white balance, its exposure, the print balance and the tone (`wash`, wash_of); a black-and-white one
    takes the exposure and the tone."""
    if gray:
        return tone(expose(img, target["light"]), wash)
    return tone(balance(expose(white(saturate(img, target["sat"]), target["temp"]), target["light"])), wash)


def target_of(imgs):
    """The cast's middles from its leveled photographs [(img, gray)]: {light: the median of every photograph's
    lightness, kept inside LIGHT, sat: the median saturation of its color photographs, kept inside SAT, temp: the median
    temperature of its color photographs once each is saturated toward that, the step before the white balance}."""
    import statistics
    color = [img for img, gray in imgs if not gray]
    light = max(LIGHT[0], min(LIGHT[1], statistics.median(lightness(img) for img, _ in imgs))) if imgs else sum(LIGHT) / 2
    sat = max(SAT[0], min(SAT[1], statistics.median(saturation(img) for img in color))) if color else sum(SAT) / 2
    small = lambda img: img.resize((192, max(1, round(192 * img.height / img.width))))
    temp = statistics.median(temperature(saturate(small(img), sat)) for img in color) if color else 0.0
    return {"light": light, "sat": sat, "temp": temp}


def grade(src, target=None):
    """One photograph through the whole grade, toward the cast's middles `target` (its own when None)."""
    img, gray = toned(src)
    return finish(img, gray, target_of([(img, gray)]) if target is None else target)


def grain_tile(path, seed=7):
    from PIL import Image
    rnd = random.Random(seed)
    n = 512
    data = bytes(max(0, min(255, int(rnd.gauss(128, 46)))) for _ in range(n * n))
    part = path.with_name(f".{path.name}.part")
    Image.frombytes("L", (n, n), data).convert("RGB").save(part, "PNG")
    os.replace(part, path)


def own_prints():
    """{(place, n): the photograph of each visit's moment in taste.json, None where its post has none}."""
    import picks
    lib = _env.read_json("library.json") or {}
    return {(m["place"], m.get("n", 1)): picks.own_print(lib, m)
            for m in (_env.read_json("taste.json") or {}).get("moments") or [] if m.get("place")}


def own_first(shots, own):
    """A visit's shots as {file, line?}, its moment's own print first: moved to the front with the line read on it
    when the cast already shows it, set before the rest when it does not."""
    shots = [s if isinstance(s, dict) else {"file": s} for s in shots]
    if not own:
        return shots
    key = lambda s: str(_env.home_path(s["file"]).resolve())
    lead = next((s for s in shots if key(s) == key({"file": own})), {"file": own})
    return [lead] + [s for s in shots if key(s) != key(lead)]


def grade_cast(own=None):
    """Grade every photograph cast.json names into public/photos/, each visit's moment's own print (`own`, from
    own_prints) first, and write public/photos.json; returns its rows."""
    own = own_prints() if own is None else own
    cast = _env.read_json("cast.json")
    if not cast:
        sys.exit("cast.json is missing: run research.py (picks.py writes it), look at cast.png and correct it first")
    home = (_env.read_json("places.json") or {}).get("home")
    (PUBLIC / "photos").mkdir(parents=True, exist_ok=True)
    # photos.json names the graded set, so it goes before the first photograph changes and comes back after the last
    (PUBLIC / "photos.json").unlink(missing_ok=True)
    # the levels first, for every photograph, so the middles they are all moved toward are the cast's own
    shots = [(v, k, shot, *toned(_env.home_path(shot["file"])))
             for v in cast["visits"] for k, shot in enumerate(own_first(v.get("shots") or [], own.get((v["place"], v["n"]))), 1)]
    target = target_of([(img, gray) for *_, img, gray in shots])
    wash = wash_of(_env.read_json("taste.json"))
    rows = []
    for v, k, shot, img, gray in shots:
        name = f"{v['place']}-{v['n']}-{k}.jpg"
        img = finish(img, gray, target, wash)
        img.save(PUBLIC / "photos" / f".{name}.part", "JPEG", quality=92)
        os.replace(PUBLIC / "photos" / f".{name}.part", PUBLIC / "photos" / name)
        subject = subject_of(img)
        rows.append({"place": v["place"], "n": v["n"], "k": k, "file": f"photos/{name}", "w": img.width, "h": img.height,
                     "aspect": round(img.height / img.width, 4), "color": color_of(img), "focus": focus_of(subject),
                     "subject": subject, "line": shot.get("line"), "about": shot.get("about"), "camera": shot.get("camera"),
                     "texture": shot.get("texture"), "look": look_of(img), "gray": gray,
                     "home": v["place"] == home, "source": str(shot["file"])})
    _env.write_json(PUBLIC / "photos.json", {"photos": rows})
    fx = PUBLIC / "fx" / "grain.png"
    if not fx.exists():
        fx.parent.mkdir(parents=True, exist_ok=True)
        grain_tile(fx)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["photos"])
    ap.parse_args()
    _env.enter_run()
    _env.need("PIL")
    rows = grade_cast()
    print(f"graded {len(rows)} photographs of {len({(r['place'], r['n']) for r in rows})} visits -> public/photos/, public/photos.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
