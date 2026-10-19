#!/usr/bin/env python3
"""Build one invented person's fourteen months on Instagram and Facebook, as the two "Download your information"
exports, with one subject tracked across all of it.

USAGE:
    python3 make_person.py DEST [--seed 7] [--year 2026] [--end 2026-10-18]

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

Her nine most-liked of the year are unambiguous: seven posts and two reels, one in each of nine months from January
to October, between 291 and 486 likes, while nothing else reaches 225 (the tenth sits at least 66 below the
ninth). Each of the nine carries a caption that says why it landed (the light, the sound, the color, the table). Strings are written the way
Meta writes them (UTF-8 bytes escaped as latin-1). Images are drawn with Pillow; about one in ten carries a .heic
name over plain JPEG bytes. Needs Pillow and ffmpeg.

The subject this kit is for: her pottery, 24 posts and 2 reels from 2025-08-09 (day one at the wheel) to
2026-10-14 (a shelf of vases, "fourteen months in"), one or two a month, interleaved with about 140 unrelated
travel and food posts from August 2025 on. The images progress monotonically with the date: one lumpy raw-clay
bowl becomes a shelf of six tall, symmetric, glazed pieces. Four posts are milestones and say so in the caption
(2025-10-18 the first bowl that stayed whole, 2026-01-24 the first glaze firing, 2026-05-16 the first matching set,
2026-09-12 the first sale). The early captions are short and self-deprecating, the recent ones longer and sure.
A second, shorter subject: her balcony garden, 9 posts from 2026-04-05 to 2026-09-20. The two reels are short mp4
clips of the wheel (2026-02-20 and 2026-08-02). liked-progress/ holds 12 progress posts she liked (images and
captions.json): seven side-by-side then/now splits, three top/bottom splits, one four-up and one single, captions
that put dates on both sides ("day 1 vs day 400"). The intended timeline is printed in the summary ("intended").
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

POTTERY = [  # (date, caption, milestone): her pottery, day one to fourteen months in
    ("2025-08-09", "day one at the wheel. it's supposed to be a bowl #pottery", False),
    ("2025-08-23", "wobbly again. back tomorrow #pottery", False),
    ("2025-09-06", "clay everywhere, bowl nowhere #pottery", False),
    ("2025-09-20", "centering is the hardest part, nobody warned me #pottery", False),
    ("2025-10-04", "three collapses tonight. one survivor, sort of #pottery", False),
    ("2025-10-18", "milestone: the first bowl that stayed in one piece off the wheel. lopsided, and i love it #pottery", True),
    ("2025-11-08", "trimming feet all evening, my arms hurt #pottery", False),
    ("2025-11-29", "a shelf of greenware drying by the window #ceramics", False),
    ("2025-12-20", "cylinders, a little taller every week #pottery", False),
    ("2026-01-10", "bisque day. fingers crossed #ceramics", False),
    ("2026-01-24", "milestone: first glaze firing out of the kiln today, and it actually holds water #ceramics", True),
    ("2026-02-14", "glaze tests, round three. the olive one is winning #ceramics", False),
    ("2026-03-07", "handles are their own skill entirely #pottery", False),
    ("2026-03-28", "bowls with actual foot rings now #pottery", False),
    ("2026-04-18", "pulling walls thinner, the pots feel lighter in the hand #pottery", False),
    ("2026-05-16", "milestone: my first matching set of four mugs, same height, same handle #pottery", True),
    ("2026-06-06", "a stack of plates, glazed in terracotta and cream #ceramics", False),
    ("2026-06-27", "taller forms this month, 30 cm and holding their shape #pottery", False),
    ("2026-07-25", "the glaze is doing exactly what i planned now, every time #pottery", False),
    ("2026-08-15", "a set of six bowls for a friend's kitchen, trimmed and glazed in one week #pottery", False),
    ("2026-08-29", "vases with a cream glaze breaking over the rim #ceramics", False),
    ("2026-09-12", "milestone: sold my first pieces at the saturday market. a year ago i couldn't center a lump of clay #ceramics", True),
    ("2026-10-03", "a commission for a cafe in the city: twelve cups, all matching #pottery", False),
    ("2026-10-14", "fourteen months in. a shelf of vases, all thrown this month #pottery #ceramics", False),
]
POTTERY_REELS = [("2026-02-20", "thirty seconds of throwing a cylinder #pottery", 5),
                 ("2026-08-02", "pulling up a vase, start to finish #ceramics", 7)]
GARDEN = [  # (date, caption): the second, shorter run
    ("2026-04-05", "seedlings on the balcony #balconygarden"), ("2026-04-26", "basil, two tomato plants and a lot of hope #balconygarden"),
    ("2026-05-17", "the balcony is getting greener #balconygarden"), ("2026-06-07", "taller than the railing now #balconygarden"),
    ("2026-06-28", "herbs for every dinner this week #balconygarden"), ("2026-07-19", "watering at dawn before the heat #balconygarden"),
    ("2026-08-09", "the balcony jungle #balconygarden"), ("2026-08-30", "picking something every morning #balconygarden"),
    ("2026-09-20", "the last of the summer garden #balconygarden"),
]
LIKED = [  # (account, caption, layout, subject): progress posts she liked
    ("wheel.and.wedge", "day 1 vs day 400 #pottery", "lr", "pottery"),
    ("slow.clay.studio", "2024 → 2025, same wheel, same hands #ceramics", "lr", "pottery"),
    ("kiln.diaries", "one year of throwing, side by side", "lr", "pottery"),
    ("glaze.notes", "before / after: my first mug and my latest", "lr", "pottery"),
    ("the.thrown.pot", "month 1 vs month 12 #pottery", "lr", "pottery"),
    ("mud.to.mug", "first bowl vs this week's bowl", "lr", "pottery"),
    ("balcony.greens", "april vs august on the balcony", "lr", "garden"),
    ("clay.year.one", "then (top), now (bottom): a year of clay", "tb", "pottery"),
    ("studio.on.film", "day 30 vs day 365", "tb", "pottery"),
    ("potter.progress", "two years at the wheel, then and now", "tb", "pottery"),
    ("from.lump.to.lidded", "year one of clay, in four photos", "grid", "pottery"),
    ("pinch.and.coil", "lidded jars this week", "single", "pottery"),
]
CLAY = {"raw": (150, 132, 116), "bisque": (214, 182, 150), "terracotta": (190, 96, 62), "olive": (112, 118, 64),
        "cream": (236, 224, 200), "espresso": (62, 42, 34), "wall": (226, 214, 194), "wood": (128, 86, 56)}


def epoch(day, hour=17):
    return int(dt.datetime.fromisoformat(day).replace(hour=hour, tzinfo=dt.timezone.utc).timestamp())


def draw_pot(d, cx, base, w, h, t, rng, glaze):
    """One thrown piece: a profile that wobbles less, stands taller and carries more glaze as t goes from 0 to 1."""
    wob = (1 - t) * 0.16
    pts_l, pts_r = [], []
    belly = 0.35 + 0.25 * t
    ph1, ph2, fr = rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(2.5, 4.5)
    for k in range(25):
        y = k / 24
        prof = 0.55 + 0.45 * math.sin(math.pi * min(1, y * (0.8 + 0.4 * belly)))
        neck = 1 - 0.35 * t * max(0, y - 0.7) / 0.3
        half = w / 2 * prof * neck
        jl = math.sin(y * fr * math.pi + ph1) * wob * w
        jr = math.sin(y * fr * math.pi + ph2) * wob * w
        yy = base - y * h
        pts_l.append((cx - half + jl, yy))
        pts_r.append((cx + half + jr, yy))
    body = pts_l + pts_r[::-1]
    d.polygon(body, fill=glaze)
    if t > 0.35:
        hi = mix(glaze, (255, 252, 240), 0.3)
        d.line([(cx - w * 0.2, base - h * 0.7), (cx - w * 0.2, base - h * 0.3)], fill=hi, width=max(2, int(w * 0.05)))
    if t > 0.6:
        band = mix(glaze, CLAY["espresso"], 0.5)
        for f in (0.3, 0.55):
            y = base - h * f
            d.line([(cx - w * 0.42, y), (cx + w * 0.42, y)], fill=band, width=max(2, int(w * 0.03)))
    if t > 0.8:
        rim = mix(CLAY["cream"], glaze, 0.2)
        d.polygon(pts_l[-6:] + pts_r[-6:][::-1], fill=rim)
    d.ellipse([cx - w * 0.4, base - 6, cx + w * 0.4, base + 6], fill=mix(glaze, CLAY["espresso"], 0.6))


def draw_pottery(d, sw, sh, t, rng):
    """The studio shelf: one lumpy raw bowl at t=0, six tall glazed pieces at t=1."""
    for y in range(sh):
        d.line([(0, y), (sw, y)], fill=mix(CLAY["wall"], CLAY["bisque"], y / sh * 0.5))
    shelf = int(sh * 0.74)
    d.rectangle([0, shelf, sw, sh], fill=CLAY["wood"])
    d.rectangle([0, shelf, sw, shelf + 10], fill=mix(CLAY["wood"], CLAY["cream"], 0.3))
    n = 1 + int(round(t * 5))
    glazes = [CLAY["terracotta"], CLAY["olive"], CLAY["cream"], CLAY["espresso"]]
    for i in range(n):
        cx = sw * (i + 0.5) / n + rng.uniform(-6, 6)
        w = sw / max(2.2, n * 1.15) * (0.9 + 0.2 * t)
        h = sh * (0.12 + 0.36 * t) * (0.8 + 0.4 * rng.random() * t)
        glaze = CLAY["raw"] if t < 0.3 else mix(CLAY["bisque"], glazes[i % 4], min(1, (t - 0.25) * 1.6))
        draw_pot(d, cx, shelf, w, h, t, rng, glaze)


def draw_garden(d, sw, sh, t, rng):
    """The balcony: bare pots at t=0, plants over the railing at t=1."""
    for y in range(sh):
        d.line([(0, y), (sw, y)], fill=mix((200, 214, 222), (236, 224, 200), y / sh))
    rail = int(sh * 0.55)
    for x in range(0, sw, 28):
        d.line([(x, rail), (x, sh)], fill=(70, 62, 54), width=4)
    d.rectangle([0, rail - 6, sw, rail + 4], fill=(70, 62, 54))
    for i in range(4):
        cx = sw * (i + 0.5) / 4
        top = sh * 0.86
        hgt = sh * (0.05 + 0.5 * t) * (0.8 + 0.4 * rng.random())
        for k in range(int(6 + 40 * t)):
            lx = cx + rng.uniform(-1, 1) * (20 + 60 * t)
            ly = top - rng.random() * hgt
            r = rng.randint(6, 14)
            d.ellipse([lx - r, ly - r / 2, lx + r, ly + r / 2], fill=mix((60, 110, 50), (120, 160, 70), rng.random()))
        if t > 0.55:
            for k in range(int(10 * t)):
                lx, ly = cx + rng.uniform(-50, 50) * t, top - rng.random() * hgt * 0.8
                d.ellipse([lx - 7, ly - 7, lx + 7, ly + 7], fill=(200, 60, 44))
        d.polygon([(cx - 48, top), (cx + 48, top), (cx + 36, sh - 8), (cx - 36, sh - 8)], fill=CLAY["terracotta"])


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


def draw_progress(d, im, sw, sh, kind, rng):
    """pottery:T, garden:T, or liked:LAYOUT:SUBJECT, a progress post someone else made (then and now in one image)."""
    from PIL import Image, ImageDraw
    parts = kind.split(":")
    if parts[0] in ("pottery", "garden"):
        (draw_pottery if parts[0] == "pottery" else draw_garden)(d, sw, sh, float(parts[1]), rng)
        return
    layout, subj = parts[1], parts[2]
    draw = draw_pottery if subj == "pottery" else draw_garden
    cells = {"lr": [(0, 0, 0.5, 1, 0.05), (0.5, 0, 1, 1, 0.95)], "tb": [(0, 0, 1, 0.5, 0.05), (0, 0.5, 1, 1, 0.95)],
             "grid": [(0, 0, 0.5, 0.5, 0.0), (0.5, 0, 1, 0.5, 0.35), (0, 0.5, 0.5, 1, 0.7), (0.5, 0.5, 1, 1, 1.0)],
             "single": [(0, 0, 1, 1, 0.9)]}[layout]
    for x0, y0, x1, y1, t in cells:
        cw, ch = int((x1 - x0) * sw), int((y1 - y0) * sh)
        cell = Image.new("RGB", (cw, ch))
        draw(ImageDraw.Draw(cell), cw, ch, t, rng)
        im.paste(cell, (int(x0 * sw), int(y0 * sh)))
    line = (246, 240, 228)
    if layout in ("lr", "grid"):
        d.rectangle([sw // 2 - 4, 0, sw // 2 + 4, sh], fill=line)
    if layout in ("tb", "grid"):
        d.rectangle([0, sh // 2 - 4, sw, sh // 2 + 4], fill=line)


def draw_scene(job):
    """job = (path, w, h, kind, palette, seed). Draws at half size and upscales (soft, photo-like)."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed = job
    rng = random.Random(seed)
    sw, sh = w // 2, h // 2
    im = Image.new("RGB", (sw, sh))
    d = ImageDraw.Draw(im)
    a, b, c, e = (tuple(max(0, min(255, v + rng.randint(-18, 18))) for v in col) for col in pal)
    if kind.startswith(("pottery:", "garden:", "liked:")):
        draw_progress(d, im, sw, sh, kind, rng)
    elif kind in ("snow", "hills", "beach", "sunset", "rain", "forest"):
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

    def insight(uri, ts, likes, comments):
        return {"media_map_data": {"Media Thumbnail": {"uri": uri, "creation_timestamp": ts, "title": ""}},
                "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                    "Likes": {"value": str(likes)}, "Comments": {"value": str(comments)},
                                    "Saves": {"value": str(int(likes / 12))}}}

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
    # August to December 2025: the unrelated posts that run before and around the subject
    for m in range(8, 13):
        for _ in range(max(2, SEASON[m][0] * 2 // 3)):
            ts = ts_for(rng, year - 1, m, end)
            cap = caption(m)
            w, h = (1080, 1350) if rng.random() < 0.6 else (1080, 1080)
            uri = media_path("posts", ts, ".jpg")
            jobs.append((str(root / uri), w, h, rng.choice(SEASON[m][1]), pal(m), rng.random()))
            posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                     "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
            likes = int(rng.lognormvariate(3.9, 0.45))
            insights.append(insight(uri, ts, min(OTHER_CAP - 1, likes), max(0, int(likes / rng.uniform(9, 22)))))
    t0, t1 = epoch(POTTERY[0][0]), epoch(POTTERY[-1][0])
    for day, cap, _ in POTTERY:
        ts = epoch(day, rng.randint(16, 21))
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1350, f"pottery:{(epoch(day) - t0) / (t1 - t0):.4f}", pal(8), rng.random()))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        likes = int(rng.lognormvariate(3.9, 0.35) * (0.8 + 0.8 * (ts - t0) / (t1 - t0)))
        insights.append(insight(uri, ts, min(OTHER_CAP - 1, likes), max(0, int(likes / rng.uniform(9, 22)))))
    g0, g1 = epoch(GARDEN[0][0]), epoch(GARDEN[-1][0])
    for day, cap in GARDEN:
        ts = epoch(day, rng.randint(7, 10))
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1350, f"garden:{(epoch(day) - g0) / (g1 - g0):.4f}", pal(5), rng.random()))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        likes = int(rng.lognormvariate(3.8, 0.35))
        insights.append(insight(uri, ts, likes, max(0, int(likes / 14))))
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

    for i, (day, cap, secs) in enumerate(POTTERY_REELS):
        ts = epoch(day, 18)
        still = str(root / f"media/reels/wheel{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, f"pottery:{(epoch(day) - t0) / (t1 - t0):.4f}", pal(8), rng.random()))
        uri = f"media/reels/{17845000000000000 + i * 7901}.mp4"
        clip_jobs.append((str(root / uri), still, secs))
        reels.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(cap), "media_metadata": {"video_metadata": {}}}]})
        reel_insights.append(insight(uri, ts, 180 + 20 * i, 14 + i))

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
        post = {"timestamp": ts, "data": [{"post": ig_text(caption(m))}], "title": ig_text(f"{NAME} updated her status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, rng.choice(SEASON[m][1]), pal(m), rng.random()))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    liked_dir = dest / "liked-progress"
    if liked_dir.exists():
        shutil.rmtree(liked_dir)
    liked_rows = {}
    for i, (acct, cap, layout, subj) in enumerate(LIKED):
        name = f"{i + 1:02d}-{acct.replace('.', '-')}.jpg"
        jobs.append((str(liked_dir / name), 1080, 1350 if layout != "lr" else 1080, f"liked:{layout}:{subj}", pal(8), rng.random()))
        liked_rows[name] = {"account": acct, "caption": cap, "ts": ts_for(rng, year, rng.randint(1, end.month), end)}
    liked_dir.mkdir(parents=True)
    (liked_dir / "captions.json").write_text(json.dumps(liked_rows, indent=2, ensure_ascii=False))

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(make_reel, clip_jobs)
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "reel_clips": len(clip_jobs), "stories": len(stories), "likes": 900, "liked_accounts": len(liked),
                      "saved": len(saved), "comments": len(comments), "followers": len(followers),
                      "following": len(following), "facebook_posts": len(fb_posts), "facebook_albums": len(albums),
                      "images": len(jobs), "liked_progress": len(LIKED),
                      "intended": {"subject": "pottery", "posts": len(POTTERY), "reels": len(POTTERY_REELS),
                                   "first": POTTERY[0][0], "latest": POTTERY[-1][0], "span": "14 months",
                                   "milestones": [d for d, _, m in POTTERY if m],
                                   "second_subject": {"subject": "balcony garden", "posts": len(GARDEN),
                                                      "first": GARDEN[0][0], "latest": GARDEN[-1][0]}}}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
