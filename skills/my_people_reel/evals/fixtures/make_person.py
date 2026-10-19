#!/usr/bin/env python3
"""Build one invented person's 2026 on Instagram and Facebook, as the two "Download your information" exports,
with the people she spent the year with.

USAGE:
    python3 make_person.py DEST [--seed 7] [--year 2026] [--end 2026-10-18]

DEST is a folder (a workspace). It receives:
    instagram-maren.okafor-2026-10-18/       the Instagram export, JSON layout:
        personal_information/personal_information/personal_information.json
        your_instagram_activity/content/posts_1.json, reels.json, stories.json   (media carry "tagged_users")
        your_instagram_activity/content/posts_you_are_tagged_in.json             (their posts that tag her)
        your_instagram_activity/likes/liked_posts.json
        your_instagram_activity/saved/saved_posts.json
        your_instagram_activity/comments/post_comments_1.json                    (comments she wrote, replies included)
        your_instagram_activity/comments/comments_on_your_posts.json             (comments others wrote on hers)
        connections/followers_and_following/followers_1.json, following.json
        logged_information/past_instagram_insights/posts.json, reels.json
        media/posts/YYYYMM/*.jpg|*.heic, media/reels/*.mp4, media/stories/YYYYMM/*.jpg, media/tagged/YYYYMM/*.jpg
    facebook-marenokafor-2026-10-18/         a small Facebook export (posts and two albums)

The person, Maren Okafor (@maren.okafor), has a clear taste: film-grain travel and food in warm earth tones. About
140 posts, 29 reels, 60 stories, 900 likes across 40 accounts, saves, comments, followers and following.

Her people are six recurring accounts with clearly different volumes, each the one she is with most in one stretch
of the year:

    person          stretch          her tags  story tags  tag her  comments to her  her comments  voice
    dani.reyes      July-August         24         6          7           30              30       loud, capitals, emoji
    theo.makes      March-April         15         4          5           21              20       dry, precise, a maker
    ines.walks      May-June            11         3          4           24              20       slow, a walker, images
    liv.outside     January             26         4          8            0               3       never comments
    kofi.cooks      September-October    8         2          3           12              10       food first
    sam_and_june    February             3         1          1            4               4       a couple, "we", warm

Eleven group photos and two short group reels (mp4, 5 s) tag three to five of them at once; each person also has
one or two portraits that tag them alone. Their comments come in six distinct voices (liv.outside writes none), and
Maren replies to about four in ten with an @mention. The intended order, every signal counted once, is

    1 dani.reyes   2 theo.makes   3 ines.walks   4 liv.outside   5 kofi.cooks   (6 sam_and_june, far below)

Tags alone put liv.outside first; comments alone drop her from the five. Strings are written the way Meta writes
them (UTF-8 bytes escaped as latin-1). Images are drawn with Pillow; about one in ten carries a .heic name over
plain JPEG bytes. Needs Pillow and ffmpeg.
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
    1: (16, ["coffee", "oldtown", "table"], ["cream", "espresso", "sand", "rust"], "lisbon"),
    2: (6, ["coffee", "table"], ["sand", "espresso", "cream", "rust"], "home"),
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
    "back in {p} for a while", "dinner ran late again", "terracotta everything", "tomatoes, olive oil, sea salt. done",
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

# handle -> (name, stretch months, her post tags, story tags, tags of her, their comments, her comments)
PEOPLE = {
    "dani.reyes": ("Dani Reyes", (7, 8), 24, 6, 7, 30, 30),
    "theo.makes": ("Theo Marsh", (3, 4), 15, 4, 5, 21, 20),
    "ines.walks": ("Ines Duarte", (5, 6), 11, 3, 4, 24, 20),
    "liv.outside": ("Liv Hart", (1,), 26, 4, 8, 0, 3),
    "kofi.cooks": ("Kofi Mensah", (9, 10), 8, 2, 3, 12, 10),
    "sam_and_june": ("Sam and June", (2,), 3, 1, 1, 4, 4),
}
INTENDED = ["dani.reyes", "theo.makes", "ines.walks", "liv.outside", "kofi.cooks"]
GROUPS = [  # (month, the people in frame): group photos she posted
    (1, ["liv.outside", "sam_and_june", "dani.reyes"]), (1, ["liv.outside", "theo.makes", "ines.walks"]),
    (3, ["theo.makes", "liv.outside", "dani.reyes"]), (4, ["theo.makes", "ines.walks", "kofi.cooks", "liv.outside"]),
    (5, ["ines.walks", "dani.reyes", "liv.outside"]), (6, ["ines.walks", "theo.makes", "kofi.cooks"]),
    (7, ["dani.reyes", "liv.outside", "theo.makes", "ines.walks", "kofi.cooks"]),
    (7, ["dani.reyes", "liv.outside", "sam_and_june", "theo.makes"]), (8, ["dani.reyes", "ines.walks", "liv.outside"]),
    (9, ["kofi.cooks", "dani.reyes", "liv.outside"]), (10, ["kofi.cooks", "theo.makes", "dani.reyes", "liv.outside"]),
]
GROUP_REELS = [(7, ["dani.reyes", "liv.outside", "theo.makes", "ines.walks"]), (9, ["kofi.cooks", "dani.reyes", "liv.outside"])]
GROUP_CAPTIONS = ["the whole table, finally", "everyone i love in one bad photo", "my people, sunburnt",
                  "the crew, round two", "a long lunch with the good ones", "nobody blinked, a miracle",
                  "last night of the trip with these ones", "this lot \U0001F35E", "the usual suspects",
                  "found them all at the market", "dinner ran until two again"]
PORTRAIT_CAPTIONS = {
    "dani.reyes": ["@{h} at the harbor, refusing to pose", "@{h} owned this whole summer"],
    "theo.makes": ["@{h} in his workshop in porto", "@{h} measuring the light twice"],
    "ines.walks": ["@{h} eleven kilometres in and still smiling", "@{h} on the ridge above oaxaca"],
    "liv.outside": ["@{h} in lisbon, the first good day of the year", "@{h} on every hill in lisbon"],
    "kofi.cooks": ["@{h} and the tagine we nearly burned", "@{h} at the stove, as always"],
    "sam_and_june": ["@{h} on their sofa, which is now my sofa"],
}
VOICES = {  # the comments each one wrote on her posts
    "dani.reyes": ["MAREN. the light. i'm screaming \U0001F62D", "THIS IS US. framing it for the kitchen \U0001F34B\U0001F34B",
                   "ok who said you could be this good", "PUT ME IN EVERY PHOTO FOREVER", "obsessed obsessed obsessed",
                   "remember when we missed the last ferry and it turned into the best night of the whole summer",
                   "i am never recovering from this trip \U0001F62D", "the HAIR. the SEA. the ICONS",
                   "best summer of my life and you have the receipts", "\U0001F525\U0001F525\U0001F525"],
    "theo.makes": ["the composition on this is unfair", "you underexposed by half a stop and it still beats mine",
                   "i'd frame this. i'd build the frame first, but i'd frame it",
                   "porto in april has a light i keep trying to mix and never get right", "noted the angle. stealing it",
                   "good lines", "this is what a straight horizon looks like, everyone"],
    "ines.walks": ["remember the walk up there, the dust on our shoes and the whole valley going gold",
                   "eleven kilometres for this view and i'd walk it twice", "slow mornings with you are a kind of prayer",
                   "the quiet before the market opens is my favorite sound in oaxaca", "this one smells like rain",
                   "take me back to the ridge"],
    "kofi.cooks": ["that bread still lives in my head rent free. next time i'm cooking", "save me a seat and a spoon",
                   "salt, oil, fire. you get it", "the tagine we burned and ate anyway >>>", "who made the sauce. be honest",
                   "hungry now"],
    "sam_and_june": ["We miss you already! June says come back for her birthday!", "Sam cried at this one. June did not. (June did.)",
                     "Our favorite house guest!!", "Come back to Lisbon soon, the sofa is yours!"],
}
REPLIES = ["@{h} you're in every good photo i took this year", "@{h} stop it \U0001F62D", "@{h} next time, i promise",
           "@{h} only because you were there", "@{h} we're going back, that's final", "@{h} this one is for you"]


NINE = [  # (month, kind, scene, likes, comments, caption): her nine most-liked, planted clear of everything else
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
    elif kind.startswith("group") or kind == "portrait":
        n = 1 if kind == "portrait" else int(kind[5:] or 3)
        for y in range(sh):
            d.line([(0, y), (sw, y)], fill=mix(c, a, y / sh))
        r = rng.randint(sw // 9, sw // 6)
        cx, cy = rng.randint(sw // 4, 3 * sw // 4), rng.randint(sh // 8, sh // 3)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(c, (255, 248, 225), 0.6))
        d.rectangle([0, int(sh * 0.78), sw, sh], fill=mix(e, b, 0.45))
        for k in range(n):
            if n == 1:
                fx, scale = sw // 2 + rng.randint(-sw // 12, sw // 12), 2.2
            else:
                fx, scale = int(sw * (k + 0.5) / n + rng.randint(-sw // (4 * n), sw // (4 * n))), 1.05 - 0.02 * n + rng.uniform(-0.08, 0.08)
            hr = int(sw * 0.075 * scale)
            hy = int(sh * (0.36 if n == 1 else 0.5) + rng.randint(-sh // 30, sh // 30))
            body = mix(rng.choice([a, b, e]), e, 0.35 + 0.15 * rng.random())
            d.rounded_rectangle([fx - int(hr * 2.0), hy + int(hr * 1.1), fx + int(hr * 2.0), sh + hr], radius=int(hr * 1.4), fill=body)
            d.ellipse([fx - hr, hy - hr, fx + hr, hy + hr], fill=mix(body, (90, 60, 45), 0.4))
            d.arc([fx - hr, hy - hr, fx + hr, hy + hr], 200, 340, fill=mix(c, (255, 240, 210), 0.7), width=max(2, hr // 6))
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
    a = ap.parse_args()
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

    nine_reels = []
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

    comment_lines = ["this is so good", "obsessed", "need to go here", "the colors!!", "ok this light ✨",
                     "save me a slice", "when are we going back", "\U0001F525\U0001F525", "that grain", "take me with you"]
    others = rng.sample(ACCOUNTS[6:], 18)
    comments = []
    for _ in range(120):
        acct = rng.choice(others)
        ts = ts_for(rng, year, rng.choice(months), end)
        comments.append({"media_list_data": [{"uri": ""}],
                         "string_map_data": {"Comment": {"value": ig_text(rng.choice(comment_lines))},
                                             "Media Owner": {"value": acct}, "Time": {"timestamp": ts}}})


    # her people: portraits, group photos, group reels, tags on posts and stories, their posts of her, comments both ways
    def month_of(ts):
        return dt.datetime.fromtimestamp(ts, dt.timezone.utc).month

    def spread(h, n):
        """n months for one person's events: three in four inside their stretch, the rest anywhere else."""
        stretch = [m for m in PEOPLE[h][1] if m in months]
        rest = [m for m in months if m not in stretch]
        k = round(n * 0.75)
        return [rng.choice(stretch) for _ in range(k)] + [rng.choice(rest) for _ in range(n - k)]

    def tag(item, handles):
        have = [t["value"] for t in item.get("tagged_users", [])]
        item["tagged_users"] = [{"value": h} for h in have + [h for h in handles if h not in have]]

    counts = {h: [0, 0, 0, 0, 0, 0] for h in PEOPLE}
    shown = {h: 0 for h in PEOPLE}
    for k, (m, who) in enumerate(GROUPS):
        ts = ts_for(rng, year, m, end)
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1350, f"group{len(who)}", pal(m), rng.random()))
        cap = GROUP_CAPTIONS[k % len(GROUP_CAPTIONS)]
        item = {"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}
        tag(item, who)
        posts.append({"media": [item]})
        insights.append(insight(uri, ts, rng.randint(120, OTHER_CAP - 1), rng.randint(12, 30)))
        for h in who:
            shown[h] += 1
    for h, caps in PORTRAIT_CAPTIONS.items():
        for cap in caps:
            m = rng.choice([mm for mm in PEOPLE[h][1] if mm in months])
            ts = ts_for(rng, year, m, end)
            uri = media_path("posts", ts, ".jpg")
            jobs.append((str(root / uri), 1080, 1350, "portrait", pal(m), rng.random()))
            item = {"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                    "title": ig_text(cap.format(h=h)), "cross_post_source": {"source_app": "FB"}}
            tag(item, [h])
            posts.append({"media": [item]})
            insights.append(insight(uri, ts, rng.randint(90, OTHER_CAP - 1), rng.randint(8, 24)))
            shown[h] += 1
    by_month = {}
    for post in posts:
        by_month.setdefault(month_of(post["media"][0]["creation_timestamp"]), []).append(post)
    for h, (name, stretch, her_tags, story_tags, tags_of_her, theirs, hers) in PEOPLE.items():
        for m in spread(h, her_tags - shown[h]):
            free = [p for p in by_month.get(m, []) if not p["media"][0].get("tagged_users")] or \
                [p for p in by_month.get(m, []) if h not in [t["value"] for t in p["media"][0].get("tagged_users", [])]]
            tag(rng.choice(free or posts)["media"][0], [h])
        for m in spread(h, story_tags):
            free = [st for st in stories if month_of(st["creation_timestamp"]) == m and not st.get("tagged_users")]
            tag(rng.choice(free or stories), [h])
        counts[h][1] = story_tags
    for post in posts:
        for t in post["media"][0].get("tagged_users", []):
            counts[t["value"]][0] += 1

    for k, (m, who) in enumerate(GROUP_REELS):
        ts = ts_for(rng, year, m, end)
        still = str(root / f"media/reels/group{k + 1}-still.jpg")
        jobs.append((still, 1080, 1920, f"group{len(who)}", pal(m), rng.random()))
        uri = f"media/reels/{17845000000000000 + k * 6113}.mp4"
        clip_jobs.append((str(root / uri), still, 5))
        item = {"uri": uri, "creation_timestamp": ts, "title": ig_text(GROUP_CAPTIONS[(k + 4) % len(GROUP_CAPTIONS)]),
                "media_metadata": {"video_metadata": {}}}
        tag(item, who)
        reels.append({"media": [item]})
        reel_insights.append(insight(uri, ts, rng.randint(150, OTHER_CAP - 1), rng.randint(15, 30)))

    tagged_in, received = [], []
    for h, (name, stretch, her_tags, story_tags, tags_of_her, theirs, hers) in PEOPLE.items():
        for m in spread(h, tags_of_her):
            ts = ts_for(rng, year, m, end)
            uri = media_path("tagged", ts, ".jpg")
            others_in = [o for o in PEOPLE if o != h and rng.random() < 0.15]
            jobs.append((str(root / uri), 1080, 1350, f"group{2 + len(others_in)}", pal(m), rng.random()))
            tagged_in.append({"owner": h, "uri": uri, "creation_timestamp": ts,
                              "title": ig_text(f"with @{HANDLE} " + rng.choice(EMOJI)),
                              "tagged_users": [{"value": HANDLE}] + [{"value": o} for o in others_in]})
        counts[h][2] = tags_of_her
        lines = VOICES.get(h, [])
        for i, m in enumerate(spread(h, theirs)):
            own = by_month.get(m) or posts
            ts = ts_for(rng, year, m, end)
            uri = rng.choice(own)["media"][0]["uri"]
            text = lines[i % len(lines)] if i < len(lines) else rng.choice(lines)
            received.append({"media_list_data": [{"uri": uri}],
                             "string_map_data": {"Comment": {"value": ig_text(text)}, "Author": {"value": h},
                                                 "Time": {"timestamp": ts}}})
            if rng.random() < 0.4:
                comments.append({"media_list_data": [{"uri": uri}],
                                 "string_map_data": {"Comment": {"value": ig_text(rng.choice(REPLIES).format(h=h))},
                                                     "Media Owner": {"value": HANDLE},
                                                     "Time": {"timestamp": ts + rng.randint(300, 20000)}}})
                counts[h][5] += 1
        counts[h][3] = theirs
        for m in spread(h, hers):
            comments.append({"media_list_data": [{"uri": ""}],
                             "string_map_data": {"Comment": {"value": ig_text(rng.choice(comment_lines))},
                                                 "Media Owner": {"value": h}, "Time": {"timestamp": ts_for(rng, year, m, end)}}})
        counts[h][4] = hers
    tagged_in.sort(key=lambda t: t["creation_timestamp"])
    received.sort(key=lambda c: c["string_map_data"]["Time"]["timestamp"])
    comments.sort(key=lambda c: c["string_map_data"]["Time"]["timestamp"])

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
    write(root, "your_instagram_activity/comments/comments_on_your_posts.json", received)
    write(root, "your_instagram_activity/content/posts_you_are_tagged_in.json", {"ig_tagged_media": tagged_in})
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
        post = {"timestamp": ts, "data": [{"post": ig_text(caption(m))}], "title": ig_text(f"{NAME} updated her status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, rng.choice(SEASON[m][1]), pal(m), rng.random()))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(make_reel, clip_jobs)
    print(json.dumps({"workspace": str(dest), "intended_order": INTENDED, "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "reel_clips": len(clip_jobs), "stories": len(stories), "likes": 900, "liked_accounts": len(liked),
                      "saved": len(saved), "comments": len(comments), "followers": len(followers),
                      "following": len(following), "facebook_posts": len(fb_posts), "facebook_albums": len(albums),
                      "images": len(jobs), "tagged_in": len(tagged_in), "comments_received": len(received),
                      "people": {h: dict(zip(("her_tags", "story_tags", "tags_of_her", "their_comments", "her_comments", "her_replies"), v))
                                 for h, v in counts.items()}}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
