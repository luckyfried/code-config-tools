#!/usr/bin/env python3
"""Build one invented person about to launch a product: their 2026 on Instagram and Facebook, as the two "Download
your information" exports, and the product's own asset folder.

USAGE:
    python3 make_person.py DEST [--seed 7] [--year 2026] [--end 2026-10-18] [--roll MEDIA]

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
    tide-table-launch/                       the product's assets: six studio stills (1080x1350) and one 5 s
                                             turntable clip (1080x1920 mp4), in the product's own palette
    camera-roll/                             with --roll MEDIA (the demo-media folder): their own photographs of the
                                             year, the making of Tide Table from their first wheel class to kiln day and
                                             their world around it (their table, their people, their places), each dated in
                                             its EXIF; manifest.json gives per photograph "caption" (the words they wrote
                                             with it, the four about Tide Table and two of their questions word for word
                                             as they posted them), "title" and "description" (what it shows)

The person has a clear taste: film-grain travel and food in warm earth tones (terracotta, ochre, olive, cream,
espresso). About 120 posts (some carousels), 27 reels, 60 stories, 900 likes across 40 accounts whose names share
that taste, 70 saves, 200 comments, 412 followers (96 new this year), 180 following. July (two weeks in Sicily) is
clearly the busiest month and February the quietest.

The launch: Tide Table, their line of ceramic tableware, drops on 2026-11-14 (the blind-run prompt states the name, the
date and the asset folder). The product's palette (cobalt, sea glass, lemon, porcelain, deep navy) is cool where
theirs is warm. Four posts about Tide Table are already in their feed (two of them among their most-responded posts).

Their nine most-responded posts (comments plus saves) are planted clear of everything else: 306, 278, 253, 215, 182,
159, 146, 129 and 106, while no other post or reel passes 45. Their likes run in a different order on purpose (the
list post about Sicily has the most likes and ranks fourth by response), so a ranking by likes is visibly wrong.
Their openers come in three styles, three each: a question ("would you ...?", "what would ...?", "which one ...?"),
a confession ("confession: ...", "i almost didn't ...", "honestly, ...") and a number list ("3 things ...",
"5 bread rules ...", "2 hours, 1 market, 0 plans"). The intended hook order is the response order above, and the
styles rank question (mean 239), confession (196), list (156). Strings are written the way Meta writes them (UTF-8
bytes escaped as latin-1). Images are drawn with Pillow; about one in ten carries a .heic name over plain JPEG
bytes. Needs Pillow and ffmpeg.
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


PRODUCT, LAUNCH, ASSETS = "Tide Table", "2026-11-14", "tide-table-launch"
COAST = {"cobalt": (32, 72, 168), "sea glass": (148, 198, 188), "lemon": (238, 208, 72), "porcelain": (244, 243, 238),
         "deep navy": (18, 28, 58)}
PLANTED = [  # (month, kind, scene, likes, comments, saves, style, caption): their nine most-responded, in response order
    (6, "post", "table", 260, 96, 210, "question", "would you eat breakfast off this? oaxaca, 7am, the light doing everything"),
    (10, "post", "plates", 205, 88, 190, "confession", "confession: i've been making plates in secret for a year. tide table is nearly ready"),
    (9, "post", "plates", 188, 71, 182, "question", "what would you cook first on a cobalt plate? asking for tide table"),
    (7, "post", "sunset", 486, 40, 175, "list", "3 things sicily taught me: eat late, swim early, never rush the bread"),
    (3, "post", "market", 240, 62, 120, "confession", "i almost didn't post this one. the porto market before anyone else woke up"),
    (1, "post", "coffee", 300, 55, 104, "question", "which one is your morning cup? lisbon, one window, two espressos"),
    (5, "reel", "market", 350, 18, 128, "list", "5 bread rules i live by, filmed at the oaxaca market at opening"),
    (8, "reel", "beach", 330, 39, 90, "confession", "honestly, the best meal of the year was this one, on the sand, with salt hair"),
    (4, "post", "oldtown", 280, 22, 84, "list", "2 hours, 1 market, 0 plans. porto in april"),
]
PRODUCT_POSTS = [  # (month, likes, comments, saves, caption): the other two posts about the product, ordinary numbers
    (9, 92, 6, 9, "glaze tests for tide table, round four"),
    (10, 88, 5, 8, "kiln day. tide table is close"),
]
OTHER_CAP = 225  # no other post or reel reaches this many likes, and none passes 45 comments plus saves
# their camera roll, in the order they shot it: (month, day, demo-media file, the words they wrote with it, "" for none)
ROLL = [
    (1, 9, "places/lisbon/05-alfama-alley-washing.jpg", "lost in alfama on purpose"),
    (1, 10, "tableware/01-brushstroke-mug-on-saucer.jpg", "which one is your morning cup? lisbon, one window, two espressos"),
    (1, 24, "pottery/02-empty-class-wheels.jpg", "signed up for a wheel class. no idea what i'm doing"),
    (1, 31, "pottery/01-raw-clay-dust.jpg", ""),
    (2, 2, "pottery/03-kick-wheel-with-clay.jpg", "first night on the wheel with @theo.makes. clay in my hair for days"),
    (2, 21, "pottery/04-first-lumpy-pot-in-hand.jpg", "lumpy, wonky, mine. my first pot"),
    (3, 2, "tableware/04-cobalt-cup-latte.jpg", "cobalt, always cobalt"),
    (3, 14, "pottery/05-first-bisque-mug-from-above.jpg", "first mug that actually holds coffee"),
    (4, 11, "pottery/06-stacked-rough-bowls.jpg", ""),
    (5, 9, "pottery/08-rounder-bisque-mug.jpg", "the walls finally stay up"),
    (6, 12, "places/oaxaca/02-flame-tree-santo-domingo.jpg", "oaxaca. every wall here is a color i want on a plate"),
    (6, 13, "feed/22-brunch-table.jpg", "would you eat breakfast off this? oaxaca, 7am, the light doing everything"),
    (6, 27, "pottery/13-first-decorated-mug.jpg", ""),
    (7, 5, "pottery/09-greenware-drying-shelves.jpg", ""),
    (7, 18, "places/porto/03-blue-tiled-church-steps.jpg", "cobalt on every wall. taking notes"),
    (7, 19, "people/03-beach-chairs-sunset-toast.jpg", "porto with @dani.reyes and @ines.walks. we stayed till the sun went"),
    (8, 8, "tableware/03-sea-glass-crackle-cup.jpg", "@theo.makes says this glaze is a keeper"),
    (8, 22, "people/16-barbecue-night-gathering.jpg", "@kofi.cooks fed the whole street"),
    (9, 12, "pottery/19-tea-bowl-on-dark-table.jpg", "glaze tests for tide table, round four"),
    (10, 3, "pottery/12-bisque-firing-in-kiln.jpg", "kiln day. tide table is close"),
    (10, 11, "pottery/10-rows-of-unglazed-pots.jpg", "confession: i've been making plates in secret for a year. tide table is nearly ready"),
]


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


def draw_scene(job):
    """job = (path, w, h, kind, palette, seed). Draws at half size and upscales (soft, photo-like)."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed = job
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
    elif kind == "plates":
        d.rectangle([0, 0, sw, sh], fill=mix(e, b, 0.4))
        for y in range(0, sh, 22):
            d.line([(0, y), (sw, y + rng.randint(-6, 6))], fill=mix(e, b, 0.5), width=2)
        for _ in range(rng.randint(2, 3)):
            r = rng.randint(sw // 6, sw // 4)
            cx, cy = rng.randint(r, sw - r), rng.randint(r, sh - r)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COAST["cobalt"])
            d.ellipse([cx - int(r * .84), cy - int(r * .84), cx + int(r * .84), cy + int(r * .84)], fill=COAST["porcelain"])
            d.ellipse([cx - int(r * .3), cy - int(r * .3), cx + int(r * .3), cy + int(r * .3)], fill=COAST["sea glass"])
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
    im = film_look(im, rng)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=84)  # a .heic name still gets JPEG bytes
    return path


def draw_product(job):
    """job = (path, w, h, shot, seed): a clean studio still of the tableware, in the product's palette (no film look)."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, shot, seed = job
    rng = random.Random(seed)
    sw, sh = w // 2, h // 2
    C = COAST
    bg = {"plate": C["cobalt"], "bowl": C["lemon"], "cup": C["sea glass"], "stack": C["deep navy"], "glaze": C["cobalt"],
          "set": C["porcelain"]}[shot]
    im = Image.new("RGB", (sw, sh), bg)
    d = ImageDraw.Draw(im)
    for y in range(sh):
        d.line([(0, y), (sw, y)], fill=mix(bg, (0, 0, 0), 0.18 * y / sh))
    cx, cy = sw // 2, int(sh * 0.48)

    def plate(cx, cy, r, rim=C["cobalt"], well=C["porcelain"], dot=C["lemon"]):
        d.ellipse([cx - r + 8, cy - r + 14, cx + r + 8, cy + r + 14], fill=mix(bg, (0, 0, 0), 0.35))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rim)
        d.ellipse([cx - int(r * .86), cy - int(r * .86), cx + int(r * .86), cy + int(r * .86)], fill=well)
        for k in range(12):
            ang = k * math.pi / 6
            px, py = cx + int(math.cos(ang) * r * .93), cy + int(math.sin(ang) * r * .93)
            d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=dot)
    if shot == "plate":
        plate(cx, cy, int(sw * 0.38))
    elif shot == "bowl":
        r = int(sw * 0.32)
        d.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2 + 10], fill=mix(bg, (0, 0, 0), 0.3))
        d.chord([cx - r, cy - r, cx + r, cy + r], 0, 180, fill=C["cobalt"])
        d.ellipse([cx - r, cy - r // 4, cx + r, cy + r // 4], fill=C["porcelain"])
        d.ellipse([cx - int(r * .8), cy - r // 6, cx + int(r * .8), cy + r // 6], fill=C["sea glass"])
    elif shot == "cup":
        r = int(sw * 0.2)
        d.rectangle([cx - r, cy - r, cx + r, cy + int(r * 1.3)], fill=C["porcelain"])
        d.ellipse([cx - r, cy - r - r // 4, cx + r, cy - r + r // 4], fill=C["cobalt"])
        d.ellipse([cx - r, cy + int(r * 1.3) - r // 4, cx + r, cy + int(r * 1.3) + r // 4], fill=C["porcelain"])
        d.arc([cx + r - 10, cy - r // 3, cx + r + r // 2 + 10, cy + r // 2 + 20], 270, 90, fill=C["porcelain"], width=14)
        d.rectangle([cx - r, cy + r // 3, cx + r, cy + r // 3 + 16], fill=C["lemon"])
    elif shot == "stack":
        for k in range(5):
            y = cy + int(sh * 0.12) - k * 26
            d.ellipse([cx - int(sw * .34), y - 22, cx + int(sw * .34), y + 22], fill=[C["cobalt"], C["porcelain"]][k % 2])
        plate(cx, cy - int(sh * 0.08), int(sw * 0.3))
    elif shot == "glaze":
        for _ in range(240):
            x, y, r = rng.randint(0, sw), rng.randint(0, sh), rng.randint(6, 40)
            d.ellipse([x - r, y - r, x + r, y + r], fill=mix(C["cobalt"], rng.choice([C["sea glass"], C["deep navy"], C["porcelain"]]), rng.random() * 0.5))
    else:  # set
        plate(int(sw * 0.34), int(sh * 0.4), int(sw * 0.26))
        plate(int(sw * 0.68), int(sh * 0.62), int(sw * 0.22), rim=C["lemon"], dot=C["cobalt"])
        r = int(sw * 0.1)
        d.ellipse([int(sw * 0.7) - r, int(sh * 0.26) - r, int(sw * 0.7) + r, int(sh * 0.26) + r], fill=C["cobalt"])
    im = im.filter(ImageFilter.GaussianBlur(0.8)).resize((w, h), Image.BICUBIC)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=90)
    return path


def make_turntable(still, path, secs=5):
    """The product's short clip: the plate turning on its cobalt ground, 1080x1920, 30 fps."""
    frames = int(secs * 30)
    bg = "0x%02x%02x%02x" % COAST["cobalt"]
    vf = (f"scale=1080:1350,pad=1080:1920:0:285:color={bg},rotate='t*0.5':ow=iw:oh=ih:c={bg},"
          f"zoompan=z='1+0.08*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still, "-vf", vf, "-frames:v", str(frames),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", path], check=True)
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


def camera_roll(dest, media, year, end):
    """Their camera roll: each ROLL photograph taken by `end` (the export's last day) copied from the demo-media folder, at
    most 2048 px on its long side, its day written into its EXIF, and manifest.json with their words beside what each
    photograph shows."""
    from PIL import Image, ImageOps
    out = dest / "camera-roll"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    roll = [r for r in ROLL if dt.date(year, r[0], r[1]) <= end]
    shows = {}
    for f in {Path(media) / r[2] for r in roll}:
        for it in json.loads((f.parent / "manifest.json").read_text()).get("items") or []:
            shows[(str(f.parent), it.get("file"))] = it
    items = []
    for k, (m, d, rel, words) in enumerate(roll, 1):
        src = Path(media) / rel
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        im.thumbnail((2048, 2048), Image.LANCZOS)
        exif = Image.Exif()
        exif[306] = f"{year}:{m:02d}:{d:02d} 09:{k:02d}:00"
        name = f"IMG_{year}{m:02d}{d:02d}_{k:02d}.jpg"
        im.save(out / name, quality=90, exif=exif)
        it = shows.get((str(src.parent), src.name)) or {}
        items.append({"file": name, "caption": words, "title": it.get("title") or "", "description": it.get("description") or "",
                      "source": rel, "license": it.get("license") or ""})
    (out / "manifest.json").write_text(json.dumps({"items": items}, indent=1, ensure_ascii=False))
    return len(items)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--end", default="2026-10-18", help="last day of data (the export date)")
    ap.add_argument("--roll", help="the demo-media folder: write their camera roll (camera-roll/) from its photographs")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    end = dt.date.fromisoformat(a.end)
    year = a.year
    months = [m for m in range(1, 13) if (year, m) <= (end.year, end.month)]
    dest = Path(a.dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest / f"instagram-{HANDLE}-{end.isoformat()}"
    fb = dest / f"facebook-{HANDLE.replace('.', '')}-{end.isoformat()}"
    assets = dest / ASSETS
    for r in (root, fb, assets):
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

    def insight(uri, ts, likes, comments, saves=None):
        if saves is None:  # an ordinary post: comments plus saves stay at or under 40
            comments = min(comments, 30)
            saves = min(int(likes / rng.uniform(9, 16)), 40 - comments)
        return {"media_map_data": {"Media Thumbnail": {"uri": uri, "creation_timestamp": ts, "title": ""}},
                "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                    "Likes": {"value": str(likes)}, "Comments": {"value": str(comments)},
                                    "Saves": {"value": str(saves)}}}

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
            insights.append(insight(items[0]["uri"], ts, likes, max(0, int(likes / rng.uniform(9, 22)))))

    nine_reels = []
    rows = [(m, kind, scene, likes, comments, saves, cap) for m, kind, scene, likes, comments, saves, _, cap in PLANTED] + \
           [(m, "post", "plates", likes, comments, saves, cap) for m, likes, comments, saves, cap in PRODUCT_POSTS]
    for k, (m, kind, scene, likes, comments, saves, cap) in enumerate(rows):
        ts = ts_for(rng, year, m, end)
        if kind == "reel":
            nine_reels.append((m, scene, likes, comments, saves, cap, ts))
            continue
        w, h = (1080, 1350) if k % 2 == 0 else (1080, 1080)
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), w, h, scene, pal(m), rng.random()))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        insights.append(insight(uri, ts, likes, comments, saves))
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
    for i, (m, scene, likes, comments, saves, cap, ts) in enumerate(nine_reels):
        still = str(root / f"media/reels/top{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, scene, pal(m), rng.random()))
        uri = f"media/reels/{17843000000000000 + i * 7907}.mp4"
        clip_jobs.append((str(root / uri), still, (6, 8)[i % 2]))
        reels.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(cap), "media_metadata": {"video_metadata": {}}}]})
        reel_insights.append(insight(uri, ts, likes, comments, saves))

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
    for i, acct in enumerate(ACCOUNTS + [f"film.{w}{i}" for i, w in enumerate(["notes", "lab", "club", "days"] * 35)][:140]):
        following.append({"title": acct, "string_list_data": [
            {"href": f"https://www.instagram.com/_u/{acct}", "timestamp": ts_for(rng, rng.choice([2024, 2025, year]), rng.randint(1, 9), end)}]})

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

    shots = ["plate", "bowl", "cup", "stack", "glaze", "set"]
    product_jobs = [(str(assets / f"tide-table-{k + 1:02d}-{s}.jpg"), 1080, 1350, s, rng.random()) for k, s in enumerate(shots)]
    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(draw_product, product_jobs)
        pool.map(make_reel, clip_jobs)
    make_turntable(product_jobs[0][0], str(assets / "tide-table-turntable.mp4"))
    roll = camera_roll(dest, a.roll, year, end) if a.roll else 0
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "reel_clips": len(clip_jobs), "stories": len(stories), "likes": 900, "liked_accounts": len(liked),
                      "saved": len(saved), "comments": len(comments), "followers": len(followers),
                      "following": len(following), "facebook_posts": len(fb_posts), "facebook_albums": len(albums),
                      "images": len(jobs), "product": PRODUCT, "launch": LAUNCH, "assets": ASSETS,
                      "product_stills": len(product_jobs), "product_clips": 1, "camera_roll": roll,
                      "intended_hooks": [{"rank": i + 1, "response": c + s, "style": st, "opener": cap}
                                         for i, (_, _, _, _, c, s, st, cap) in enumerate(PLANTED)],
                      "intended_styles": ["question", "confession", "list"]}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
