#!/usr/bin/env python3
"""Build one invented person's year of places on Instagram and Facebook, as the two "Download your information" exports.

USAGE:
    python3 make_person.py DEST [--seed 7] [--year 2026] [--end 2026-10-18] [--set DIR]

DEST is a folder (a workspace). It receives:
    instagram-maren.okafor-2026-10-18/       the Instagram export, JSON layout:
        personal_information/personal_information/personal_information.json
        your_instagram_activity/content/posts_1.json, reels.json, stories.json
        your_instagram_activity/likes/liked_posts.json
        your_instagram_activity/saved/saved_posts.json
        your_instagram_activity/comments/post_comments_1.json
        connections/followers_and_following/followers_1.json, following.json
        logged_information/past_instagram_insights/posts.json      (likes, comments, saves per post)
        media/posts/YYYYMM/*.jpg|*.heic, media/reels/*.mp4, media/stories/YYYYMM/*.jpg
    facebook-marenokafor-2026-10-18/         a small Facebook export:
        your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json
        your_facebook_activity/posts/album/0.json, 1.json
        your_facebook_activity/posts/media/<album>/*.jpg
    photos-of-the-year/<place>/                with --set DIR: a copy of a photo set of the eleven places (a folder per
                                               place, each with its manifest.json ranking the photographs best first),
                                               the photographs the person hands over beside the exports; every post
                                               and story photograph of a place the set holds is then one of the set's
                                               own photographs of it, so no proof reads drawn placeholder art

The person lives in Lisbon (their bio says so) and traveled through eleven places in 2026, January to October:
Lisbon, Porto, Coimbra, Aveiro, Évora, Seville, Córdoba, Granada, Faro, Oaxaca and Madrid. Porto (March and
September) and Seville (May and August) were visited twice, so the count is of places, not visits. Oaxaca is the
one far trip (about 8,600 km from home); every other place is in Portugal and Spain. Coimbra and Córdoba carry no
geotags: they are named only in captions (Córdoba's name is shared with cities in Mexico and Argentina, so the
place has to be read from when it was posted). Most other posts and stories carry the geotag Instagram writes into
media_metadata.photo_metadata.exif_data, a few meters to a few kilometers from the city center. Their travel photos are
warm earth tones (terracotta, ochre, olive, sand); their Lisbon photos are cool (slate, fog, harbor blue, linen), so
the travel palette and the everyday palette differ. Three reels are short clips shot in Porto, Seville and Oaxaca,
geotagged. Each stay's first post carries what they did there in their own words (MOMENTS: a tram ride, a port tasting,
a mole cooked from scratch), with the friends who were there tagged and the place named. INTENDED below is the place list the kit
should find. Strings are written the way Meta writes them
(UTF-8 bytes escaped as latin-1). Images are drawn with Pillow; about one in ten carries a .heic name over plain
JPEG bytes. Needs Pillow and ffmpeg.
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import shutil
import subprocess
import sys
import unicodedata
from multiprocessing import Pool
from pathlib import Path

HANDLE, NAME = "maren.okafor", "Maren Okafor"
COLORS = {
    "terracotta": (196, 98, 64), "ochre": (214, 158, 72), "olive": (118, 120, 66), "cream": (238, 224, 198),
    "espresso": (62, 42, 34), "sand": (222, 190, 150), "rust": (160, 72, 44), "rosa": (214, 92, 128),
    "slate": (84, 98, 116), "fog": (186, 192, 198), "harbor": (58, 96, 128), "linen": (226, 224, 216),
    "ink": (34, 40, 52), "tile": (70, 128, 168),
}
HOME_PAL = ["fog", "slate", "harbor", "linen"]
PLACES = {  # name: (lat, lon, geotagged, four colors, scenes, how their captions name it)
    "Lisbon": (38.7223, -9.1393, True, HOME_PAL, ["coffee", "oldtown", "table", "city"], "lisbon"),
    "Porto": (41.1496, -8.6110, True, ["terracotta", "sand", "cream", "espresso"], ["oldtown", "market", "table"], "porto"),
    "Coimbra": (40.2033, -8.4103, False, ["ochre", "cream", "olive", "espresso"], ["oldtown", "coffee"], "coimbra"),
    "Aveiro": (40.6405, -8.6538, True, ["sand", "ochre", "cream", "rust"], ["beach", "oldtown"], "aveiro"),
    "Évora": (38.5714, -7.9135, True, ["ochre", "terracotta", "cream", "espresso"], ["hills", "oldtown", "table"], "évora"),
    "Seville": (37.3891, -5.9845, True, ["terracotta", "ochre", "sand", "espresso"], ["oldtown", "sunset", "table"], "seville"),
    "Córdoba": (37.8882, -4.7794, False, ["rust", "sand", "cream", "espresso"], ["oldtown", "flowers"], "córdoba"),
    "Granada": (37.1773, -3.5986, True, ["rust", "ochre", "cream", "olive"], ["hills", "oldtown", "sunset"], "granada"),
    "Faro": (37.0194, -7.9304, True, ["sand", "ochre", "cream", "rust"], ["beach", "sunset", "table"], "faro"),
    "Oaxaca": (17.0732, -96.7266, True, ["rosa", "terracotta", "ochre", "espresso"], ["market", "hills", "table", "oldtown"], "oaxaca"),
    "Madrid": (40.4168, -3.7038, True, ["terracotta", "sand", "cream", "espresso"], ["city", "oldtown", "coffee"], "madrid"),
}
STAYS = [  # (place, month, first day, last day, posts, stories): the year in the order they lived it
    ("Lisbon", 1, 2, 30, 8, 6), ("Lisbon", 2, 1, 27, 4, 3),
    ("Porto", 3, 2, 10, 6, 5), ("Coimbra", 3, 12, 16, 4, 2),
    ("Lisbon", 3, 22, 29, 2, 1),
    ("Aveiro", 4, 3, 7, 4, 3), ("Évora", 4, 18, 22, 4, 3),
    ("Seville", 5, 1, 9, 6, 5), ("Córdoba", 5, 11, 14, 4, 2),
    ("Granada", 6, 2, 8, 5, 4), ("Faro", 6, 18, 26, 5, 4),
    ("Oaxaca", 7, 4, 24, 12, 8),
    ("Seville", 8, 6, 14, 5, 4),
    ("Porto", 9, 3, 9, 4, 3), ("Madrid", 9, 15, 21, 5, 4),
    ("Lisbon", 10, 1, 17, 5, 4),
]
MOMENTS = {  # (place, month): the caption of the stay's first post, what they did there
    ("Lisbon", 1): "rode the 28 end to end in the rain with @dani.reyes, soaked and happy",
    ("Lisbon", 2): "@dani.reyes finally came to stay, we ate pastéis on the sofa all week",
    ("Porto", 3): "port tasting down by the river with @theo.makes, we stayed for sunset",
    ("Coimbra", 3): "heard fado in coimbra with @ines.walks, a student sang it in the street",
    ("Lisbon", 3): "home for a week and i walked the whole river front twice",
    ("Aveiro", 4): "rode a painted moliceiro down the canals of aveiro with @kofi.cooks",
    ("Évora", 4): "dinner out on the square in évora, the whole town was there",
    ("Seville", 5): "rowed a little boat round plaza de españa with @liv.outside, terribly",
    ("Córdoba", 5): "lost a whole morning under the arches of the mezquita in córdoba",
    ("Granada", 6): "up at six for the alhambra with @sam_and_june and worth every minute",
    ("Faro", 6): "first swim of the year in faro, the water was freezing and perfect",
    ("Oaxaca", 7): "cooked mole from scratch in oaxaca with @kofi.cooks, best day of the year",
    ("Seville", 8): "back in seville for @dani.reyes's birthday, we danced until the bars closed",
    ("Porto", 9): "ran across the dom luís bridge at sunrise, porto all gold below",
    ("Madrid", 9): "madrid rooftops at golden hour with @theo.makes, we never wanted to come down",
    ("Lisbon", 10): "home again and the river was silver the whole week long",
}
INTENDED = ["Lisbon", "Porto", "Coimbra", "Aveiro", "Évora", "Seville", "Córdoba", "Granada", "Faro", "Oaxaca", "Madrid"]
CLIPS = [("Porto", 3, 5), ("Seville", 5, 6), ("Oaxaca", 7, 7)]  # (place, month, seconds): their three reels
NAMED = [  # captions that name the place ({p})
    "golden hour in {p} again {e}", "the market in {p} is my whole personality", "took the long way through {p}",
    "back in {p} with @{f}", "everything is orange in {p} {e}", "last light over {p}", "postcards from {p}",
    "a slow morning in {p}", "lunch in {p} that lasted four hours", "{p}, you were good to me",
]
PLAIN = [  # captions that name no place
    "this light though", "slow morning, coffee and nothing else", "a very good bread day", "found this little place by accident {e}",
    "shot on film, eaten immediately", "dinner with @{f} and @{g}", "tomatoes, olive oil, sea salt. done",
    "cold hands, warm coffee", "a few from the road", "the colors here", "salt hair, sandy everything",
    "street food tour, round two", "one more espresso and then we go", "can't stop taking pictures of doorways",
]
HOME_CAPS = ["home for a bit", "grey morning at home, good coffee", "back home and the river is silver",
             "home, rain, a long walk anyway", "sunday at home {e}"]
EMOJI = ["\U0001F305", "\U0001F33F", "☀️", "\U0001F34B", "\U0001F342", "☕", "\U0001F35E", "\U0001F37D️"]
TAGS = ["#filmphotography", "#shotonfilm", "#slowtravel", "#foodtravel", "#35mm", "#earthtones", "#goldenhour"]
FRIENDS = ["dani.reyes", "theo.makes", "ines.walks", "kofi.cooks", "sam_and_june", "liv.outside"]
ACCOUNTS = FRIENDS + [
    "35mm.wanderer", "terracotta.table", "slowfood.diaries", "portra.400.club", "ochre.and.olive", "medina.light",
    "the.grain.journal", "film.kitchen", "iberia.slowly", "warmtones.travel", "bread.and.salt", "golden.hour.film",
    "lisbon.on.film", "oaxaca.eats", "kodak.gold.days", "clay.and.crumb", "espresso.stops", "postcard.paths",
    "olive.grove.notes", "andalucia.frames", "rust.and.linen", "tableforone.film", "mezze.mornings",
    "analog.atlas", "sunbaked.streets", "the.slow.plate", "film.fridays", "doorways.of.europe", "sand.and.saffron",
    "market.mornings", "grainy.getaways", "amber.afternoons", "lemon.trees.film", "harbor.on.film",
]
assert len(ACCOUNTS) == 40, len(ACCOUNTS)


def film_look(im, rng, cool=False):
    """Lifted blacks, soft vignette and grain: the person's film look; warm on the road, cool at home."""
    from PIL import Image, ImageChops
    w, h = im.size
    r, g, b = im.split()
    kr, kg, kb = (0.84, 0.9, 0.97) if cool else (0.95, 0.9, 0.78)
    r = r.point(lambda v: min(255, int(14 + v * kr)))
    g = g.point(lambda v: min(255, int(14 + v * kg)))
    b = b.point(lambda v: min(255, int(18 + v * kb)))
    im = Image.merge("RGB", (r, g, b))
    vig = Image.radial_gradient("L").resize((w, h)).point(lambda v: 255 - int(v * 0.55))
    im = ImageChops.multiply(im, Image.merge("RGB", (vig, vig, vig)))
    grain = Image.effect_noise((w // 2, h // 2), 48).resize((w, h)).convert("RGB")
    return Image.blend(im, grain, 0.09)


def ig_text(s):
    """Instagram writes UTF-8 bytes as if they were latin-1 code points."""
    return s.encode("utf-8").decode("latin-1")


def ts_for(rng, year, month, end):
    last = (dt.date(year, month % 12 + 1, 1) - dt.timedelta(days=1)).day if month < 12 else 31
    if (year, month) == (end.year, end.month):
        last = min(last, end.day)
    day = rng.randint(1, last)
    t = dt.datetime(year, month, day, rng.randint(7, 21), rng.randint(0, 59), rng.randint(0, 59), tzinfo=dt.timezone.utc)
    return int(t.timestamp())


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_scene(job):
    """job = (path, w, h, kind, palette, seed). Draws at half size and upscales (soft, photo-like)."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed, cool = job
    rng = random.Random(seed)
    sw, sh = w // 2, h // 2
    im = Image.new("RGB", (sw, sh))
    d = ImageDraw.Draw(im)
    a, b, c, e = (tuple(max(0, min(255, v + rng.randint(-18, 18))) for v in col) for col in pal)
    if kind in ("snow", "hills", "beach", "sunset", "rain", "forest"):
        top, bottom = {"sunset": (c, a), "beach": (a, c), "snow": (c, a), "rain": (c, b), "forest": (c, a)}.get(kind, (c, a))
        for y in range(sh):
            d.line([(0, y), (sw, y)], fill=mix(top, bottom, y / sh))
        if kind in ("sunset", "beach", "hills"):
            r = rng.randint(sw // 10, sw // 5)
            cx, cy = rng.randint(r, sw - r), rng.randint(sh // 5, sh // 2)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(c, (255, 250, 230), 0.6))
        horizon = int(sh * rng.uniform(0.55, 0.72))
        for layer in range(3):
            pts = [(0, sh)]
            base = horizon + layer * sh // 14
            for x in range(0, sw + 40, 40):
                pts.append((x, base - int(rng.uniform(0, sh / 9) * (1 - layer * 0.3))))
            pts.append((sw, sh))
            col = mix(b if kind != "beach" else c, e, 0.25 + layer * 0.25)
            if kind == "beach" and layer == 0:
                col = mix(b, (250, 250, 250), 0.2)
            d.polygon(pts, fill=col)
        if kind == "forest":
            for _ in range(28):
                x = rng.randint(0, sw)
                tw = rng.randint(10, 26)
                d.polygon([(x, horizon - rng.randint(60, 160)), (x - tw, sh), (x + tw, sh)], fill=mix(b, e, rng.random()))
        if kind == "rain":
            for _ in range(160):
                x, y = rng.randint(0, sw), rng.randint(0, sh)
                d.line([(x, y), (x - 4, y + 18)], fill=mix(c, (255, 255, 255), 0.5), width=1)
        if kind == "snow":
            for _ in range(220):
                x, y, r = rng.randint(0, sw), rng.randint(0, sh), rng.randint(1, 3)
                d.ellipse([x - r, y - r, x + r, y + r], fill=(250, 250, 252))
    elif kind == "city":
        for y in range(sh):
            d.line([(0, y), (sw, y)], fill=mix(c, a, y / sh))
        x = 0
        while x < sw:
            bw = rng.randint(40, 110)
            bh = rng.randint(sh // 4, int(sh * 0.8))
            col = mix(b, e, rng.random() * 0.7)
            d.rectangle([x, sh - bh, x + bw, sh], fill=col)
            for wy in range(sh - bh + 10, sh - 10, 18):
                for wx in range(x + 6, x + bw - 8, 14):
                    if rng.random() < 0.45:
                        d.rectangle([wx, wy, wx + 6, wy + 8], fill=mix(c, (255, 230, 160), 0.6))
            x += bw + rng.randint(0, 8)
    elif kind == "table":
        d.rectangle([0, 0, sw, sh], fill=mix(e, b, 0.4))
        for y in range(0, sh, 22):
            d.line([(0, y), (sw, y + rng.randint(-6, 6))], fill=mix(e, b, 0.5), width=2)
        for _ in range(rng.randint(2, 4)):
            r = rng.randint(sw // 8, sw // 4)
            cx, cy = rng.randint(r // 2, sw - r // 2), rng.randint(r // 2, sh - r // 2)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 244, 238))
            r2 = int(r * 0.7)
            d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=mix(a, c, rng.random()))
            for _ in range(6):
                ox, oy, rr = rng.randint(-r2 // 2, r2 // 2), rng.randint(-r2 // 2, r2 // 2), rng.randint(6, 18)
                d.ellipse([cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr], fill=mix(b, e, rng.random()))
    elif kind == "oldtown":
        for y in range(sh):
            d.line([(0, y), (sw, y)], fill=mix(c, a, y / sh * 0.6))
        x = -20
        while x < sw:
            bw = rng.randint(70, 150)
            top = rng.randint(sh // 6, sh // 2)
            wall = mix(a, b, rng.random() * 0.6)
            d.rectangle([x, top, x + bw, sh], fill=wall)
            d.polygon([(x - 6, top), (x + bw // 2, top - rng.randint(20, 50)), (x + bw + 6, top)], fill=mix(b, e, 0.5))
            for wy in range(top + 24, sh - 60, 56):
                for wx in range(x + 14, x + bw - 24, 38):
                    d.rectangle([wx, wy, wx + 16, wy + 30], fill=mix(e, b, 0.3))
            x += bw
        d.rectangle([0, int(sh * 0.86), sw, sh], fill=mix(c, b, 0.5))
    elif kind == "market":
        d.rectangle([0, 0, sw, sh], fill=mix(e, b, 0.5))
        for row in range(4):
            y0 = int(sh * (0.2 + row * 0.2))
            d.rectangle([0, y0, sw, y0 + sh // 7], fill=mix(e, b, 0.2))
            for _ in range(22):
                r = rng.randint(10, 22)
                cx = rng.randint(0, sw)
                cy = y0 + rng.randint(r, sh // 7 - r // 2)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(rng.choice([a, b, c]), (255, 220, 120), rng.random() * 0.3))
        d.polygon([(0, 0), (sw, 0), (sw, sh // 9), (0, sh // 6)], fill=mix(a, e, 0.2))
    elif kind == "coffee":
        d.rectangle([0, 0, sw, sh], fill=mix(c, b, 0.35))
        for y in range(0, sh, 16):
            d.line([(0, y), (sw, y + rng.randint(-4, 4))], fill=mix(c, b, 0.45), width=2)
        r = rng.randint(sw // 5, sw // 3)
        cx, cy = sw // 2 + rng.randint(-40, 40), sh // 2 + rng.randint(-60, 60)
        d.ellipse([cx - r - 30, cy - r - 30, cx + r + 30, cy + r + 30], fill=(240, 232, 218))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 240, 230))
        d.ellipse([cx - int(r * .78), cy - int(r * .78), cx + int(r * .78), cy + int(r * .78)], fill=mix(b, e, 0.55))
        d.ellipse([cx - r // 3, cy - r // 4, cx + r // 3, cy + r // 4], fill=mix(c, b, 0.3))
    else:  # flowers
        for y in range(sh):
            d.line([(0, y), (sw, y)], fill=mix(c, b, y / sh))
        for _ in range(rng.randint(14, 26)):
            cx, cy, r = rng.randint(0, sw), rng.randint(sh // 4, sh), rng.randint(14, 40)
            petal = mix(a, (255, 255, 255), rng.random() * 0.3)
            for k in range(6):
                ang = k * math.pi / 3
                px, py = cx + int(math.cos(ang) * r * 0.7), cy + int(math.sin(ang) * r * 0.7)
                d.ellipse([px - r // 2, py - r // 2, px + r // 2, py + r // 2], fill=petal)
            d.ellipse([cx - r // 4, cy - r // 4, cx + r // 4, cy + r // 4], fill=mix(c, (240, 200, 60), 0.6))
    im = im.filter(ImageFilter.GaussianBlur(1.2)).resize((w, h), Image.BICUBIC)
    im = film_look(im, rng, cool)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=84)  # a .heic name still gets JPEG bytes
    return path


def from_set(root, place_of):
    """Every post and story photograph of a place the set holds is one of the set's photographs of that place (best
    first, in turn), cropped to the post's frame and saved as JPEG under its own name, so the export shows the person's
    real photographs. Returns how many were replaced."""
    from PIL import Image, ImageOps
    fold = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().strip()
    folders = {fold(d.name): d for d in root.iterdir() if d.is_dir()}
    shown, turn = 0, {}
    for path, place in sorted(place_of.items()):
        d = folders.get(fold(place))
        if d is None:
            continue
        man = d / "manifest.json"
        items = sorted(json.loads(man.read_text()).get("items") or [], key=lambda it: it.get("rank", 1e9)) if man.exists() else []
        files = [d / Path(it["file"]).name for it in items] or sorted(f for f in d.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png"))
        files = [f for f in files if f.exists()]
        if not files:
            continue
        k = turn.get(place, 0)
        turn[place] = k + 1
        with Image.open(path) as drawn:
            size = drawn.size
        im = ImageOps.fit(Image.open(files[k % len(files)]).convert("RGB"), size, Image.LANCZOS)
        im.save(path, "JPEG", quality=90)
        shown += 1
    return shown


def make_reel(job):
    """job = (path, still, seconds): a slow push across one still, 540x960, 30 fps."""
    path, still, secs = job
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frames = int(secs * 30)
    vf = (f"scale=1080:1920,zoompan=z='1+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=540x960:fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still, "-vf", vf, "-frames:v", str(frames),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", path], check=True)
    return path



def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--end", default="2026-10-18", help="last day of data (the export date)")
    ap.add_argument("--set", help="a photo set of the eleven places to copy in as photos-of-the-year/")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    end = dt.date.fromisoformat(a.end)
    year = a.year
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest / f"instagram-{HANDLE}-{end.isoformat()}"
    fb = dest / f"facebook-{HANDLE.replace('.', '')}-{end.isoformat()}"
    for r in (root, fb):
        if r.exists():
            shutil.rmtree(r)
    jobs, counter, place_of = [], [0], {}

    def pal(place):
        return [COLORS[k] for k in PLACES[place][3]]

    def cool(place):
        return place == "Lisbon"

    def when(month, d0, d1):
        day = rng.randint(d0, d1)
        t = dt.datetime(year, month, day, rng.randint(8, 21), rng.randint(0, 59), rng.randint(0, 59), tzinfo=dt.timezone.utc)
        return int(t.timestamp())

    def geo(place, spread=0.02):
        lat, lon = PLACES[place][:2]
        return {"latitude": round(lat + rng.uniform(-spread, spread), 6), "longitude": round(lon + rng.uniform(-spread, spread), 6)}

    def media_path(kind, ts, ext):
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        counter[0] += 1
        return f"media/{kind}/{d:%Y%m}/{17840000000000000 + counter[0] * 7919}{ext}"

    def caption(place):
        geotagged = PLACES[place][2]
        if place == "Lisbon":
            pool = HOME_CAPS + PLAIN[:6]
        elif not geotagged:
            pool = NAMED + NAMED + PLAIN[:4]  # a caption-only place is named most of the time
        else:
            pool = NAMED + PLAIN
        cap = rng.choice(pool).format(e=rng.choice(EMOJI), f=rng.choice(FRIENDS), g=rng.choice(FRIENDS), p=PLACES[place][5])
        if rng.random() < 0.45:
            cap += " " + " ".join(rng.sample(TAGS, rng.randint(1, 3)))
        return cap

    posts, insights, stories = [], [], []
    for place, m, d0, d1, n_posts, n_stories in STAYS:
        tagged = PLACES[place][2]
        for k_post in range(n_posts):
            ts = when(m, d0, d1)
            cap = caption(place)
            if k_post == 0:
                cap = MOMENTS[(place, m)]
            n_media = 1 if rng.random() < 0.8 else rng.randint(2, 3)
            exif = [geo(place)] if tagged and rng.random() < 0.88 else []
            items = []
            for k in range(n_media):
                w, h = (1080, 1350) if rng.random() < 0.6 else (1080, 1080)
                ext = ".heic" if rng.random() < 0.1 else ".jpg"
                uri = media_path("posts", ts, ext)
                jobs.append((str(root / uri), w, h, rng.choice(PLACES[place][4]), pal(place), rng.random(), cool(place)))
                place_of[str(root / uri)] = place
                items.append({"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": exif}},
                              "title": ig_text(cap) if n_media == 1 else "", "cross_post_source": {"source_app": "FB"}})
            posts.append({"media": items} if n_media == 1 else {"media": items, "title": ig_text(cap), "creation_timestamp": ts})
            likes = int(rng.lognormvariate(4.0, 0.45)) + (40 if place == "Oaxaca" else 0)
            insights.append({"media_map_data": {"Media Thumbnail": {"uri": items[0]["uri"], "creation_timestamp": ts, "title": ""}},
                             "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                                 "Likes": {"value": str(likes)},
                                                 "Comments": {"value": str(max(0, int(likes / rng.uniform(9, 22))))},
                                                 "Saves": {"value": str(int(likes / 12))}}})
        for _ in range(n_stories):
            ts = when(m, d0, d1)
            uri = media_path("stories", ts, ".jpg")
            jobs.append((str(root / uri), 1080, 1920, rng.choice(PLACES[place][4]), pal(place), rng.random(), cool(place)))
            place_of[str(root / uri)] = place
            exif = [geo(place)] if tagged and rng.random() < 0.8 else []
            stories.append({"uri": uri, "creation_timestamp": ts, "title": "", "media_metadata": {"photo_metadata": {"exif_data": exif}}})
    rng.shuffle(posts)
    stories.sort(key=lambda s: s["creation_timestamp"])

    clip_jobs, reels = [], []
    for i, (place, m, secs) in enumerate(CLIPS):
        stay = next(s for s in STAYS if s[0] == place and s[1] == m)
        ts = when(m, stay[2], stay[3])
        still = str(root / f"media/reels/clip{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, PLACES[place][4][0], pal(place), rng.random(), cool(place)))
        uri = f"media/reels/{17841000000000000 + i * 104729}.mp4"
        clip_jobs.append((str(root / uri), still, secs))
        reels.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(caption(place)),
                                 "media_metadata": {"video_metadata": {"exif_data": [geo(place, 0.01)]}}}]})

    months = sorted({s[1] for s in STAYS})
    weights = [1 / (i + 1) ** 0.9 for i in range(len(ACCOUNTS))]
    order = ACCOUNTS[:]
    rng.shuffle(order)
    liked = {}
    for i in range(900):
        acct = order[i] if i < len(order) else rng.choices(order, weights)[0]
        ts = when(rng.choice(months), 1, 28)
        liked.setdefault(acct, []).append({"href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/",
                                           "value": ig_text("\U0001F44D"), "timestamp": ts})
    saved = []
    for i in range(70):
        acct = rng.choices(order, weights)[0]
        saved.append({"title": acct, "string_map_data": {"Saved on": {
            "href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/", "timestamp": when(rng.choice(months), 1, 28)}}})
    comment_lines = ["this is so good", "obsessed", "need to go here", "the colors!!", "ok this light ✨",
                     "save me a slice", "when are we going back", "\U0001F525\U0001F525", "that grain", "take me with you"]
    others = rng.sample(ACCOUNTS[6:], 18)
    comments = []
    for _ in range(200):
        acct = rng.choices(FRIENDS + others, [8, 6, 5, 3, 2, 2] + [1] * len(others))[0]
        comments.append({"media_list_data": [{"uri": ""}],
                         "string_map_data": {"Comment": {"value": ig_text(rng.choice(comment_lines))},
                                             "Media Owner": {"value": acct}, "Time": {"timestamp": when(rng.choice(months), 1, 28)}}})
    followers = []
    for i in range(412):
        acct = f"{rng.choice(['sun', 'clay', 'wild', 'little', 'amber', 'quiet', 'olive', 'moss'])}.{rng.choice(['fox', 'cafe', 'pages', 'lens', 'trails', 'kitchen', 'notes'])}{i}"
        ts = (when(rng.choice(months), 1, 28) if i < 96 else
              int(dt.datetime(rng.randint(2019, year - 1), rng.randint(1, 12), rng.randint(1, 28), tzinfo=dt.timezone.utc).timestamp()))
        followers.append({"title": "", "media_list_data": [], "string_list_data": [
            {"href": f"https://www.instagram.com/{acct}", "value": acct, "timestamp": ts}]})
    following = []
    for i, acct in enumerate(ACCOUNTS + [f"film.{w}{i}" for i, w in enumerate(["notes", "lab", "club", "days"] * 35)][:140]):
        following.append({"title": acct, "string_list_data": [
            {"href": f"https://www.instagram.com/_u/{acct}", "timestamp": when(rng.randint(1, 9), 1, 28)}]})

    def write(base, rel, obj):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2))

    write(root, "personal_information/personal_information/personal_information.json",
          {"profile_user": [{"title": "", "media_map_data": {}, "string_map_data": {
              "Username": {"value": HANDLE}, "Name": {"value": NAME},
              "Bio": {"value": ig_text("eating my way around on 35mm \U0001F35E\U0001F39E️ lisbon / wherever the bread is")}}}]})
    write(root, "your_instagram_activity/content/posts_1.json", posts)
    write(root, "your_instagram_activity/content/reels.json", {"ig_reels_media": reels})
    write(root, "your_instagram_activity/content/stories.json", {"ig_stories": stories})
    write(root, "your_instagram_activity/likes/liked_posts.json",
          {"likes_media_likes": [{"title": k, "string_list_data": v} for k, v in liked.items()]})
    write(root, "your_instagram_activity/saved/saved_posts.json", {"saved_saved_media": saved})
    write(root, "your_instagram_activity/comments/post_comments_1.json", comments)
    write(root, "connections/followers_and_following/followers_1.json", followers)
    write(root, "connections/followers_and_following/following.json", {"relationships_following": following})
    write(root, "logged_information/past_instagram_insights/posts.json", {"organic_insights_posts": insights})

    # Facebook: two albums named for places, a handful of posts
    fb_posts, albums = [], []
    for k, (title, place, m, n) in enumerate((("Oaxaca, July 2026", "Oaxaca", 7, 6), ("Seville in May", "Seville", 5, 4))):
        stay = next(s for s in STAYS if s[0] == place and s[1] == m)
        photos = []
        for j in range(n):
            ts = when(m, stay[2], stay[3])
            uri = f"your_facebook_activity/posts/media/{place}_{k}/{10160000000000000 + k * 1000 + j}.jpg"
            jobs.append((str(fb / uri), 1080, 1350, rng.choice(PLACES[place][4]), pal(place), rng.random(), cool(place)))
            photos.append({"uri": uri, "creation_timestamp": ts, "title": ig_text(title)})
        albums.append({"name": ig_text(title), "photos": photos, "cover_photo": photos[0],
                       "last_modified_timestamp": photos[-1]["creation_timestamp"], "description": ""})
        write(fb, f"your_facebook_activity/posts/album/{k}.json", albums[-1])
    for i in range(8):
        place, m, d0, d1 = rng.choice(STAYS)[:4]
        ts = when(m, d0, d1)
        post = {"timestamp": ts, "data": [{"post": ig_text(caption(place))}], "title": ig_text(f"{NAME} updated their status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, rng.choice(PLACES[place][4]), pal(place), rng.random(), cool(place)))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(make_reel, clip_jobs)
    visits = [s[0] for s in STAYS]
    if a.set:
        shutil.copytree(a.set, dest / "photos-of-the-year", dirs_exist_ok=True)
        shown = from_set(Path(a.set), place_of)
        print(f"{shown} of the export's photographs are the set's own", file=sys.stderr)
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "intended_places": INTENDED, "intended_count": len(INTENDED), "visits": visits,
                      "caption_only": [p for p in INTENDED if not PLACES[p][2]],
                      "revisited": sorted({p for p in visits if visits.count(p) > 1 and p != "Lisbon"}),
                      "far": ["Oaxaca"], "clips_in": [c[0] for c in CLIPS],
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "stories": len(stories), "likes": 900, "saved": len(saved), "comments": len(comments),
                      "followers": len(followers), "following": len(following), "facebook_posts": len(fb_posts),
                      "facebook_albums": len(albums), "images": len(jobs)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
