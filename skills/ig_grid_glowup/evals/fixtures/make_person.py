#!/usr/bin/env python3
"""Build one invented person's 2026 on Instagram and Facebook, as the two "Download your information" exports.

USAGE:
    python3 make_person.py DEST [--grid DIR] [--seed 7] [--year 2026] [--end 2026-10-18]
    python3 make_person.py --photos DIR

--grid DIR draws every post, reel cover and story from the photographs under DIR (searched recursively, matched to
the scene each post shows by the words in the file name), so the before grid is a photo feed a person would post and
the next nine have to fit it. Without --grid the scenes are drawn as flat illustrations.

--photos DIR writes, beside each of the person's next photographs in DIR (the bakery set, by file name), the note they
put with it: <name>.txt, one line in their voice on what happened, who was there and where. The photographs are not
touched.

DEST is a folder (a workspace). It receives:
    instagram-maren.okafor-2026-10-18/       the Instagram export, JSON layout:
        personal_information/personal_information/personal_information.json
        your_instagram_activity/content/posts_1.json, reels.json, stories.json
        your_instagram_activity/likes/liked_posts.json
        your_instagram_activity/saved/saved_posts.json
        your_instagram_activity/comments/post_comments_1.json
        connections/followers_and_following/followers_1.json, following.json
        logged_information/past_instagram_insights/posts.json      (likes, comments, saves per post)
        logged_information/past_instagram_insights/reels.json      (likes, comments, saves per reel)
        media/posts/YYYYMM/*.jpg|*.heic, media/reels/*.mp4, media/stories/YYYYMM/*.jpg
    facebook-marenokafor-2026-10-18/         a small Facebook export:
        your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json
        your_facebook_activity/posts/album/0.json, 1.json
        your_facebook_activity/posts/media/<album>/*.jpg

The person has a clear taste: film-grain travel and food in warm earth tones (terracotta, ochre, olive, cream,
espresso). About 120 posts (some carousels), 27 reels, 60 stories, 900 likes across 40 accounts whose names share
that taste, 70 saves, 200 comments, 412 followers (96 new this year), 180 following. July (two weeks in Sicily) is
clearly the busiest month and February the quietest.

Their nine most-liked of the year are unambiguous: seven posts and two reels, one in each of nine months from January
to October, between 291 and 486 likes, while nothing else reaches 225 (the tenth sits at least 66 below the
ninth). Each of the nine carries a caption that says why it landed (the light, the sound, the color, the table).

Their last 30 posts and reels (the grid, newest first) carry plain problems for the grid glow-up to find: a run of five
posts in a clashing palette (cold teal, magenta, cobalt and lime from a filter they tried), three tight close-up crops
among wide scenes, and two text screenshots that break the rhythm. Their own numbers point the other way: on that grid
the quiet, warm, wide posts get about three times the likes and eight times the saves of the problem posts, and their
likes and saves also go to quiet, tonal feeds (quiet.tones.journal, tonal.grid.club, muted.mornings and others).
Unposted photos (stories, carousel slides, the Facebook albums) are the library the next nine come from. Strings are written the way
Meta writes them (UTF-8 bytes escaped as latin-1). Images are drawn with Pillow; about one in ten carries a .heic
name over plain JPEG bytes. Needs Pillow and ffmpeg.
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
from multiprocessing import Pool
from pathlib import Path

HANDLE, NAME = "maren.okafor", "Maren Okafor"
CLASH = [(32, 150, 160), (205, 40, 120), (40, 70, 190), (170, 210, 40)]  # the filter phase: teal, magenta, cobalt, lime
TONAL = ["quiet.tones.journal", "tonal.grid.club", "muted.mornings", "soft.neutral.days", "the.still.table",
         "linen.and.light", "calm.film.notes", "warm.minimal.feed"]
CLASH_CAPTIONS = ["trying a new preset on everything this week", "new filter, who dis", "city lights, but make it loud",
                  "testing colors, tell me honestly", "the neon phase continues"]
SHOT_TEXT = [["reminder:", "the bread is always", "worth the queue"],
             ["sunday sauce", "6 tomatoes", "olive oil, a lot", "sea salt", "nothing else"]]
SHOT_CAPTIONS = ["saving this for later", "the recipe you all asked for"]
EARTH = {
    "terracotta": (196, 98, 64), "ochre": (214, 158, 72), "olive": (118, 120, 66), "cream": (238, 224, 198),
    "espresso": (62, 42, 34), "sand": (222, 190, 150), "rust": (160, 72, 44), "sage": (150, 158, 120),
}
SEASON = {  # month -> (post weight, scenes, four earth colors, the place)
    1: (10, ["coffee", "oldtown", "table"], ["cream", "espresso", "sand", "rust"], "lisbon"),
    2: (3, ["coffee", "table"], ["sand", "espresso", "cream", "rust"], "home"),
    3: (9, ["market", "table", "hills"], ["olive", "ochre", "cream", "espresso"], "porto"),
    4: (10, ["oldtown", "coffee", "market"], ["terracotta", "sand", "cream", "espresso"], "porto"),
    5: (12, ["market", "hills", "table"], ["ochre", "olive", "cream", "rust"], "oaxaca"),
    6: (14, ["oldtown", "table", "beach"], ["terracotta", "ochre", "cream", "espresso"], "oaxaca"),
    7: (26, ["beach", "sunset", "oldtown", "market", "table"], ["terracotta", "ochre", "sand", "espresso"], "sicily"),
    8: (15, ["sunset", "hills", "table"], ["rust", "ochre", "cream", "espresso"], "sicily"),
    9: (11, ["oldtown", "coffee", "market"], ["sand", "terracotta", "cream", "espresso"], "marrakech"),
    10: (10, ["hills", "table", "coffee"], ["rust", "olive", "sand", "espresso"], "home"),
    11: (8, ["coffee", "oldtown"], ["espresso", "rust", "cream", "sand"], "home"),
    12: (9, ["table", "coffee", "oldtown"], ["rust", "olive", "cream", "espresso"], "home"),
}
CAPTIONS = [
    "golden hour in {p} again {e}", "this light though", "slow morning, coffee and nothing else",
    "the market in {p} is my whole personality", "a very good bread day", "lunch that lasted four hours",
    "took the long way through {p}", "found this little place by accident {e}", "shot on film, eaten immediately",
    "back in {p} with @{f}", "dinner with @{f} and @{g}", "terracotta everything", "tomatoes, olive oil, sea salt. done",
    "cold hands, warm coffee", "a few from the road", "everything is orange in {p} {e}", "the colors here",
    "salt hair, sandy everything", "last light over {p}", "street food tour, round two", "home for a bit",
    "one more espresso and then we go", "can't stop taking pictures of doorways", "postcards from {p}",
]
EMOJI = ["\U0001F305", "\U0001F33F", "☀️", "\U0001F34B", "\U0001F342", "☕", "\U0001F35E", "\U0001F37D️"]
TAGS = ["#filmphotography", "#shotonfilm", "#slowtravel", "#foodtravel", "#35mm", "#earthtones", "#goldenhour"]
FRIENDS = ["dani.reyes", "theo.makes", "ines.walks", "kofi.cooks", "sam_and_june", "liv.outside"]
ACCOUNTS = FRIENDS + [
    "35mm.wanderer", "terracotta.table", "slowfood.diaries", "portra.400.club", "ochre.and.olive", "medina.light",
    "the.grain.journal", "film.kitchen", "sicily.slowly", "warmtones.travel", "bread.and.salt", "golden.hour.film",
    "lisbon.on.film", "oaxaca.eats", "kodak.gold.days", "clay.and.crumb", "espresso.stops", "postcard.paths",
    "olive.grove.notes", "marrakech.frames", "rust.and.linen", "tableforone.film", "mezze.mornings",
    "analog.atlas", "sunbaked.streets", "the.slow.plate", "film.fridays", "doorways.of.europe", "sand.and.saffron",
    "market.mornings", "grainy.getaways", "amber.afternoons", "lemon.trees.film", "harbor.on.film",
]
assert len(ACCOUNTS) == 40, len(ACCOUNTS)


NOTES = {  # the bakery set named for the next posts: the line written beside each photograph
    "01-scored-boule-wood-plate.jpg": "first loaf from the new oven, wrapped in sunday's paper for @theo.makes",
    "02-shop-window-buns-rack.jpg": "noses on the window at the padaria in lisbon, 7am, with @ines.walks",
    "03-scored-boule-cutting-board.jpg": "my starter turned one this week and she made this",
    "04-sourdough-crumb-cross-section.jpg": "cut it open at @kofi.cooks' table and everyone went quiet",
    "05-rolls-on-oven-racks.jpg": "rosa let me work the 4am shift at her bakery in palermo",
    "06-cinnamon-bun-cortado-sunlit.jpg": "one bun each with @ines.walks, then we split a third",
    "07-bakery-interior-bread-racks.jpg": "the back room where @dani.reyes learned to bake",
    "08-loaf-cooling-rack.jpg": "burned two before this one, kept this one",
    "09-croissant-pile-close.jpg": "sixty croissants for @sam_and_june's wedding breakfast",
    "10-dough-balls-rolling-pin.jpg": "pizza night at @liv.outside's, i brought the dough",
    "11-baguettes-on-rack.jpg": "baguettes in lyon, ate one on the walk home",
    "12-paris-boulangerie-facade.jpg": "beaumarchais, paris, where i had my first real croissant in 2014",
    "13-seeded-loaves-shop-tray.jpg": "the seeded rye @theo.makes keeps asking me for",
    "14-cinnamon-rolls-glazed-close.jpg": "mum's cinnamon rolls, off her recipe card from 1998",
    "15-pasteis-de-nata-trays-baker.jpg": "watched him fill a hundred tins of nata in lisbon",
    "16-torn-bread-crumb-close.jpg": "tore it open in the car, couldn't wait",
    "17-cardamom-knot-plate.jpg": "cardamom knots in stockholm, our third bakery of the day",
    "18-line-at-bakery-door.jpg": "forty minutes in the queue in taipei with @dani.reyes",
    "19-rye-slices-butter.jpg": "rye and salted butter on the boat to stromboli",
    "20-pastry-counter-warm-wood.jpg": "opening day at @kofi.cooks' counter",
    "21-dough-under-floured-towel.jpg": "dough resting overnight while the storm came in",
    "22-focaccia-counter-labels.jpg": "focaccia in genoa, @kofi.cooks ordered one of each",
    "23-pain-aux-raisins-rack.jpg": "pain aux raisins for the train to marseille",
    "24-boule-in-dutch-oven.jpg": "first bake in grandma's dutch oven",
    "25-croissants-heap-white.jpg": "my first laminated dough, all fourteen of them",
    "26-croissant-latte-red-cup.jpg": "breakfast in porto with @ines.walks before the rain",
    "27-pastry-knots-tray.jpg": "morning knots at the market stall in ortigia",
    "28-sliced-loaf-bread-knife.jpg": "sliced thin for @sam_and_june's picnic",
}


def write_notes(folder):
    """Writes the person's note beside each of their photographs in folder; returns how many it wrote."""
    wrote = 0
    for name, line in NOTES.items():
        photo = Path(folder) / name
        if photo.is_file():
            photo.with_suffix(".txt").write_text(line + "\n")
            wrote += 1
    return wrote


NINE = [  # (month, kind, scene, likes, comments, caption): their nine most-liked, planted clear of everything else
    (7, "post", "sunset", 486, 41, "the light did all the work here. sicily at 8pm, no edit, just the sun going down over the harbor"),
    (5, "reel", "market", 451, 52, "forty seconds of the oaxaca market at opening time. you asked for the sound of it \U0001F33F"),
    (1, "post", "coffee", 418, 33, "first coffee of the year in lisbon, one cup by one window, all cream and espresso brown"),
    (9, "post", "oldtown", 392, 29, "every door in marrakech is terracotta and i will not be taking questions"),
    (3, "post", "table", 371, 38, "the porto lunch that lasted four hours. olive, ochre, bread, then more bread"),
    (8, "reel", "beach", 349, 44, "a slow walk into the sea at golden hour, the reel you all sent to each other"),
    (6, "post", "hills", 328, 24, "6am on the ridge above oaxaca. worth the alarm, worth the climb, worth that orange sky"),
    (10, "post", "table", 309, 27, "back home and still cooking like it's sicily: tomatoes, olive oil, sea salt and nothing else"),
    (4, "post", "market", 291, 22, "the porto market in april, every crate orange and ochre at once #shotonfilm"),
]
OTHER_CAP = 225  # no other post or reel reaches this many likes


SCENE_WORDS = {  # the words in a photograph's file name that place it in a scene
    "coffee": ["coffee", "cappuccino", "latte", "cafe", "cup", "tea", "chai"],
    "market": ["market", "stall", "spice", "mango", "cart", "fruit", "vegetable", "tomatoes", "shrimp"],
    "table": ["table", "breakfast", "brunch", "toast", "sandwich", "platter", "plates", "oats", "pomegranate", "loaf"],
    "oldtown": ["street", "alley", "tram", "facade", "door", "stair", "church", "houses", "wall", "bicycle", "chairs", "azulejo", "square"],
    "beach": ["beach", "river", "quay", "waves", "douro", "pool"],
    "sunset": ["sunset", "evening", "dusk", "night", "viewpoint"],
    "hills": ["hill", "hillside", "cactus", "garden", "agave", "tree", "convent", "mountain"],
}


def grid_photos(folder):
    """Every photograph under folder, by the scene its file name places it in, and all of them under "" for a scene
    no file name names."""
    files = sorted(p for p in Path(folder).rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    by = {k: [p for p in files if any(w in p.stem.lower() for w in ws)] for k, ws in SCENE_WORDS.items()}
    by[""] = files
    return by


def photo_for(by, scene, seed, used):
    """The least used photograph of the scene (any photograph when the scene has none), the seed breaking ties."""
    pool = by.get(scene.split("-")[-1]) or by[""]
    rng = random.Random(seed)
    best = min(pool, key=lambda p: (used.get(p, 0), rng.random()))
    used[best] = used.get(best, 0) + 1
    return str(best)


def film_look(im, rng):
    """Warm grade, lifted blacks, soft vignette and grain: the person's film look."""
    from PIL import Image, ImageChops
    w, h = im.size
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(18 + v * 0.95)))
    g = g.point(lambda v: min(255, int(12 + v * 0.9)))
    b = b.point(lambda v: min(255, int(10 + v * 0.78)))
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


def clash_look(im):
    """The filter phase: punchy, cold, oversaturated, no grain and no vignette."""
    from PIL import Image, ImageEnhance
    r, g, b = im.split()
    b = b.point(lambda v: min(255, int(20 + v * 1.05)))
    r = r.point(lambda v: int(v * 0.86))
    im = Image.merge("RGB", (r, g, b))
    return ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.6)).enhance(1.25)


def draw_screenshot(path, w, h, lines, seed):
    """A phone notes screenshot: a status bar, a title and a few lines of text on near-white."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (w, h), (247, 246, 242))
    d = ImageDraw.Draw(im)
    try:
        big, small = ImageFont.load_default(size=86), ImageFont.load_default(size=34)
    except TypeError:
        big = small = ImageFont.load_default()
    d.text((60, 40), "9:41", font=small, fill=(20, 20, 20))
    d.rectangle([w - 150, 48, w - 70, 76], outline=(20, 20, 20), width=3)
    d.text((60, 150), "< Notes", font=small, fill=(214, 160, 40))
    y = 300
    for i, ln in enumerate(lines):
        d.text((60, y), ln, font=big, fill=(18, 18, 18) if i == 0 else (40, 40, 40))
        y += 128
    d.text((60, h - 120), "Edited " + ["yesterday", "today"][seed % 2], font=small, fill=(150, 150, 150))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=88)
    return path


def draw_scene(job):
    """job = (path, w, h, kind, palette, seed). Draws at half size and upscales (soft, photo-like).

    kind "screenshot:N" draws text screenshot N; "clash-<scene>" draws the scene in the filter-phase look;
    "tight-<scene>" draws the scene and keeps a tight close-up of its middle."""
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    path, w, h, kind, pal, seed = job[:6]
    photo = job[6] if len(job) > 6 else None
    if kind.startswith("screenshot:"):
        n = int(kind.split(":")[1])
        return draw_screenshot(path, w, h, SHOT_TEXT[n % len(SHOT_TEXT)], n)
    look, tight = "film", False
    if kind.startswith("clash-"):
        kind, look = kind[6:], "clash"
    if kind.startswith("tight-"):
        kind, tight = kind[6:], True
    rng = random.Random(seed)
    if photo:
        im = ImageOps.fit(ImageOps.exif_transpose(Image.open(photo)).convert("RGB"), (w, h), Image.LANCZOS)
        if tight:
            cw, ch = int(w * 0.45), int(h * 0.45)
            x0, y0 = (w - cw) // 2, (h - ch) // 2
            im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BICUBIC)
        im = film_look(im, rng) if look == "film" else clash_look(im)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        im.save(path, "JPEG", quality=86)
        return path
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
                import math
                ang = k * math.pi / 3
                px, py = cx + int(math.cos(ang) * r * 0.7), cy + int(math.sin(ang) * r * 0.7)
                d.ellipse([px - r // 2, py - r // 2, px + r // 2, py + r // 2], fill=petal)
            d.ellipse([cx - r // 4, cy - r // 4, cx + r // 4, cy + r // 4], fill=mix(c, (240, 200, 60), 0.6))
    im = im.filter(ImageFilter.GaussianBlur(1.2)).resize((w, h), Image.BICUBIC)
    if tight:
        cw, ch = int(w * 0.34), int(h * 0.34)
        x0, y0 = (w - cw) // 2 + rng.randint(-w // 12, w // 12), (h - ch) // 2 + rng.randint(-h // 12, h // 12)
        im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BICUBIC)
    im = film_look(im, rng) if look == "film" else clash_look(im)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=84)  # a .heic name still gets JPEG bytes
    return path


def make_reel(job):
    """job = (path, still, seconds): a slow push across one still, 540x960, 30 fps."""
    path, still, secs = job
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frames = int(secs * 30)
    vf = (f"scale=1080:1920,zoompan=z='1+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=540x960:fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still, "-vf", vf, "-frames:v", str(frames),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", path], check=True)
    return path


def grid_problems(posts, reels, insights, jobs, root, nine_uris, liked, saved, end, rng):
    """Plants the grid's problems on the last 30 posts and reels: a run of five clashing posts, three tight crops, two
    text screenshots; gives the quiet, wide posts the strong likes and saves; adds the quiet feeds they like and save."""
    def ts_of(p):
        return p.get("creation_timestamp") or p["media"][0]["creation_timestamp"]
    grid = sorted([("post", p) for p in posts] + [("reel", r) for r in reels], key=lambda e: -ts_of(e[1]))[:30]
    ok = [kind == "post" and len(p["media"]) == 1 and p["media"][0]["uri"] not in nine_uris for kind, p in grid]
    job_of = {j[0]: i for i, j in enumerate(jobs)}
    ins_of = {i["media_map_data"]["Media Thumbnail"]["uri"]: i for i in insights}
    start = next(i for i in list(range(8, 20)) + list(range(0, 25)) if all(ok[i:i + 5]))
    used = set(range(start, start + 5))

    def near(want):
        pos = min((i for i in range(30) if ok[i] and i not in used and all(abs(i - u) > 1 for u in used)),
                  key=lambda i: abs(i - want))
        used.add(pos)
        return pos
    tight = [near(w) for w in (3, 17, 26)]
    shots = [near(w) for w in (5, 22)]

    def numbers(uri, likes, saves):
        sm = ins_of[uri]["string_map_data"]
        sm["Likes"]["value"], sm["Saves"]["value"] = str(likes), str(saves)
        sm["Comments"]["value"] = str(max(0, likes // rng.randint(10, 20)))

    for k, i in enumerate(range(start, start + 5)):
        item = grid[i][1]["media"][0]
        path, w, h, kind, pal, seed = jobs[job_of[str(root / item["uri"])]]
        jobs[job_of[str(root / item["uri"])]] = (path, w, h, "clash-" + kind.replace("tight-", ""), CLASH, seed)
        item["title"] = ig_text(CLASH_CAPTIONS[k] + " " + rng.choice(["\U0001F308", "\u26A1", ""]))
        numbers(item["uri"], rng.randint(28, 62), rng.randint(0, 3))
    for i in tight:
        item = grid[i][1]["media"][0]
        path, w, h, kind, pal, seed = jobs[job_of[str(root / item["uri"])]]
        jobs[job_of[str(root / item["uri"])]] = (path, w, h, "tight-" + kind, pal, seed)
        numbers(item["uri"], rng.randint(40, 75), rng.randint(1, 4))
    for n, i in enumerate(shots):
        item = grid[i][1]["media"][0]
        path, w, h, kind, pal, seed = jobs[job_of[str(root / item["uri"])]]
        jobs[job_of[str(root / item["uri"])]] = (path, 1080, 1350, f"screenshot:{n}", pal, seed)
        item["title"] = ig_text(SHOT_CAPTIONS[n])
        numbers(item["uri"], rng.randint(30, 55), rng.randint(2, 6))
    for i in range(30):
        if grid[i][0] == "post" and grid[i][1]["media"][0]["uri"] not in nine_uris and i not in used:
            likes = rng.randint(150, OTHER_CAP - 2)
            numbers(grid[i][1]["media"][0]["uri"], likes, likes // rng.randint(4, 6))

    for acct in TONAL:
        for _ in range(rng.randint(18, 34)):
            liked.setdefault(acct, []).append({"href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/",
                                               "value": ig_text("\U0001F44D"),
                                               "timestamp": int(dt.datetime(end.year, rng.randint(6, end.month), rng.randint(1, 28),
                                                                            tzinfo=dt.timezone.utc).timestamp())})
        for _ in range(rng.randint(3, 6)):
            saved.append({"title": acct, "string_map_data": {"Saved on": {
                "href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/",
                "timestamp": int(dt.datetime(end.year, rng.randint(6, end.month), rng.randint(1, 28),
                                             tzinfo=dt.timezone.utc).timestamp())}}})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest", nargs="?")
    ap.add_argument("--photos", help="the person's next photographs: write the note beside each and stop")
    ap.add_argument("--grid", help="draw every post, reel cover and story from the photographs under this folder")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--end", default="2026-10-18", help="last day of data (the export date)")
    a = ap.parse_args()
    if a.photos:
        print(json.dumps({"photos": a.photos, "notes": write_notes(a.photos)}))
        return 0
    if not a.dest:
        ap.error("DEST is required")
    rng = random.Random(a.seed)
    end = dt.date.fromisoformat(a.end)
    year = a.year
    months = [m for m in range(1, 13) if (year, m) <= (end.year, end.month)]
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest / f"instagram-{HANDLE}-{end.isoformat()}"
    fb = dest / f"facebook-{HANDLE.replace('.', '')}-{end.isoformat()}"
    for r in (root, fb):
        if r.exists():
            shutil.rmtree(r)
    jobs, counter = [], [0]

    def pal(m):
        return [EARTH[k] for k in SEASON[m][2]]

    def media_path(kind, ts, ext):
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        counter[0] += 1
        return f"media/{kind}/{d:%Y%m}/{17840000000000000 + counter[0] * 7919}{ext}"

    def caption(m):
        cap = rng.choice(CAPTIONS).format(e=rng.choice(EMOJI), f=rng.choice(FRIENDS), g=rng.choice(FRIENDS),
                                         p=SEASON[m][3] if SEASON[m][3] != "home" else "the city")
        if rng.random() < 0.45:
            cap += " " + " ".join(rng.sample(TAGS, rng.randint(1, 3)))
        return cap

    posts, insights = [], []
    for m in months:
        for _ in range(SEASON[m][0]):
            ts = ts_for(rng, year, m, end)
            cap = caption(m)
            n_media = 1 if rng.random() < 0.8 else rng.randint(2, 3)
            items = []
            for k in range(n_media):
                w, h = (1080, 1350) if rng.random() < 0.6 else (1080, 1080)
                ext = ".heic" if rng.random() < 0.1 else ".jpg"
                uri = media_path("posts", ts, ext)
                jobs.append((str(root / uri), w, h, rng.choice(SEASON[m][1]), pal(m), rng.random()))
                items.append({"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                              "title": ig_text(cap) if n_media == 1 else "", "cross_post_source": {"source_app": "FB"}})
            posts.append({"media": items} if n_media == 1 else {"media": items, "title": ig_text(cap), "creation_timestamp": ts})
            likes = min(OTHER_CAP - 1, int(rng.lognormvariate(4.0, 0.45)) + (45 if m == 7 else 0))
            insights.append({"media_map_data": {"Media Thumbnail": {"uri": items[0]["uri"], "creation_timestamp": ts, "title": ""}},
                             "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                                 "Likes": {"value": str(likes)},
                                                 "Comments": {"value": str(max(0, int(likes / rng.uniform(9, 22))))},
                                                 "Saves": {"value": str(int(likes / 12))}}})
    def insight(uri, ts, likes, comments):
        return {"media_map_data": {"Media Thumbnail": {"uri": uri, "creation_timestamp": ts, "title": ""}},
                "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                    "Likes": {"value": str(likes)}, "Comments": {"value": str(comments)},
                                    "Saves": {"value": str(int(likes / 12))}}}

    nine_reels, nine_uris = [], set()
    for k, (m, kind, scene, likes, comments, cap) in enumerate(NINE):
        ts = ts_for(rng, year, m, end)
        if kind == "reel":
            nine_reels.append((m, scene, likes, comments, cap, ts))
            continue
        w, h = (1080, 1350) if k % 2 == 0 else (1080, 1080)
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), w, h, scene, pal(m), rng.random()))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        insights.append(insight(uri, ts, likes, comments))
        nine_uris.add(uri)
    rng.shuffle(posts)

    # four reel clips, 25 reels that point at them
    clip_jobs, clip_uris = [], []
    for i, secs in enumerate((4, 6, 9, 12)):
        m = [7, 5, 3, 9][i]
        still = str(root / f"media/reels/clip{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, SEASON[m][1][0], pal(m), rng.random()))
        uri = f"media/reels/{17841000000000000 + i * 104729}.mp4"
        clip_jobs.append((str(root / uri), still, secs))
        clip_uris.append(uri)
    reels, reel_insights = [], []
    for i in range(25):
        m = rng.choice([mm for mm in months for _ in range(SEASON[mm][0])])
        ts = ts_for(rng, year, m, end)
        reels.append({"media": [{"uri": clip_uris[i % 4], "creation_timestamp": ts, "title": ig_text(caption(m)),
                                 "media_metadata": {"video_metadata": {}}}]})
        likes = min(OTHER_CAP - 1, int(rng.lognormvariate(3.7, 0.4)))
        reel_insights.append(insight(clip_uris[i % 4], ts, likes, max(0, int(likes / rng.uniform(8, 20)))))
    for i, (m, scene, likes, comments, cap, ts) in enumerate(nine_reels):
        still = str(root / f"media/reels/top{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, scene, pal(m), rng.random()))
        uri = f"media/reels/{17843000000000000 + i * 7907}.mp4"
        clip_jobs.append((str(root / uri), still, (6, 8)[i % 2]))
        reels.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(cap), "media_metadata": {"video_metadata": {}}}]})
        reel_insights.append(insight(uri, ts, likes, comments))

    stories = []
    for i in range(60):
        m = rng.choice([mm for mm in months for _ in range(SEASON[mm][0])])
        ts = ts_for(rng, year, m, end)
        uri = media_path("stories", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1920, rng.choice(SEASON[m][1]), pal(m), rng.random()))
        stories.append({"uri": uri, "creation_timestamp": ts, "title": "", "media_metadata": {"photo_metadata": {}}})
    stories.sort(key=lambda s: s["creation_timestamp"])

    weights = [1 / (i + 1) ** 0.9 for i in range(len(ACCOUNTS))]
    order = ACCOUNTS[:]
    rng.shuffle(order)
    liked = {}
    for i in range(900):
        acct = order[i] if i < len(order) else rng.choices(order, weights)[0]
        ts = ts_for(rng, year, rng.choice(months), end)
        liked.setdefault(acct, []).append({"href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/",
                                           "value": ig_text("\U0001F44D"), "timestamp": ts})
    saved = []
    for i in range(70):
        acct = rng.choices(order, weights)[0]
        ts = ts_for(rng, year, rng.choice(months), end)
        saved.append({"title": acct, "string_map_data": {"Saved on": {
            "href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/", "timestamp": ts}}})

    grid_problems(posts, reels, insights, jobs, root, nine_uris, liked, saved, end, random.Random(a.seed * 31 + 5))

    comment_lines = ["this is so good", "obsessed", "need to go here", "the colors!!", "ok this light ✨",
                     "save me a slice", "when are we going back", "\U0001F525\U0001F525", "that grain", "take me with you"]
    others = rng.sample(ACCOUNTS[6:], 18)
    comments = []
    for _ in range(200):
        acct = rng.choices(FRIENDS + others, [8, 6, 5, 3, 2, 2] + [1] * len(others))[0]
        ts = ts_for(rng, year, rng.choice(months), end)
        comments.append({"media_list_data": [{"uri": ""}],
                         "string_map_data": {"Comment": {"value": ig_text(rng.choice(comment_lines))},
                                             "Media Owner": {"value": acct}, "Time": {"timestamp": ts}}})

    followers = []
    for i in range(412):
        acct = f"{rng.choice(['sun', 'clay', 'wild', 'little', 'amber', 'quiet', 'olive', 'moss'])}.{rng.choice(['fox', 'cafe', 'pages', 'lens', 'trails', 'kitchen', 'notes'])}{i}"
        ts = (ts_for(rng, year, rng.choice(months), end) if i < 96 else
              int(dt.datetime(rng.randint(2019, year - 1), rng.randint(1, 12), rng.randint(1, 28), tzinfo=dt.timezone.utc).timestamp()))
        followers.append({"title": "", "media_list_data": [], "string_list_data": [
            {"href": f"https://www.instagram.com/{acct}", "value": acct, "timestamp": ts}]})
    following = []
    for i, acct in enumerate(ACCOUNTS + TONAL + [f"film.{w}{i}" for i, w in enumerate(["notes", "lab", "club", "days"] * 35)][:140]):
        following.append({"title": acct, "string_list_data": [
            {"href": f"https://www.instagram.com/_u/{acct}", "timestamp": ts_for(rng, rng.choice([2024, 2025, year]), rng.randint(1, 9), end)}]})

    def write(base, rel, obj):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2))

    write(root, "personal_information/personal_information/personal_information.json",
          {"profile_user": [{"title": "", "media_map_data": {}, "string_map_data": {
              "Username": {"value": HANDLE}, "Name": {"value": NAME},
              "Bio": {"value": ig_text("eating my way around on 35mm \U0001F35E\U0001F39E️\nlisbon / wherever the bread is")}}}]})
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
    write(root, "logged_information/past_instagram_insights/reels.json", {"organic_insights_reels": reel_insights})

    # Facebook: a handful of posts and two albums
    fb_posts, albums = [], []
    for k, (title, m, n) in enumerate((("Sicily, July 2026", 7, 8), ("Oaxaca kitchens", 5, 6))):
        photos = []
        for j in range(n):
            ts = ts_for(rng, year, m, end)
            uri = f"your_facebook_activity/posts/media/{title.split(',')[0].replace(' ', '')}_{k}/{10160000000000000 + k * 1000 + j}.jpg"
            jobs.append((str(fb / uri), 1080, 1350, rng.choice(SEASON[m][1]), pal(m), rng.random()))
            photos.append({"uri": uri, "creation_timestamp": ts, "title": ig_text(title)})
        albums.append({"name": ig_text(title), "photos": photos, "cover_photo": photos[0],
                       "last_modified_timestamp": photos[-1]["creation_timestamp"], "description": ""})
        write(fb, f"your_facebook_activity/posts/album/{k}.json", albums[-1])
    for i in range(14):
        m = rng.choice(months)
        ts = ts_for(rng, year, m, end)
        post = {"timestamp": ts, "data": [{"post": ig_text(caption(m))}], "title": ig_text(f"{NAME} updated their status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, rng.choice(SEASON[m][1]), pal(m), rng.random()))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    if a.grid:
        by, used = grid_photos(a.grid), {}
        jobs = [j if j[3].startswith("screenshot:") else j + (photo_for(by, j[3], j[5], used),) for j in jobs]
    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(make_reel, clip_jobs)
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "reel_clips": len(clip_jobs), "stories": len(stories), "likes": sum(len(v) for v in liked.values()), "liked_accounts": len(liked),
                      "saved": len(saved), "comments": len(comments), "followers": len(followers),
                      "following": len(following), "facebook_posts": len(fb_posts), "facebook_albums": len(albums),
                      "images": len(jobs)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
