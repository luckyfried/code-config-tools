#!/usr/bin/env python3
"""Build one invented person's year on Instagram and Facebook, as the two "Download your information" exports,
plus a folder of the posts she liked.

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
    liked-posts/<account>_<n>.jpg            the media of posts she liked, saved from the app

The person has one consistent system, planted so a brand read can be checked against it:
  palette   every feed photo is led by one of four named colors at distinct proportions of the posts:
            terracotta 40%, cream 27%, olive 20%, chocolate 13% (the lead color covers more than half the frame)
  pillars   four subjects at clearly different shares: the table 45%, the market 25%, the streets 18%, coffee 12%
  voice     lowercase, three recurring devices: a short label and a colon to open ("market haul:"), a list of three
            ("figs, plums, quince."), and a blank line then a question to the reader; few emoji, one pillar hashtag
  cadence   three fixed weekdays and times (UTC): Tuesday 08:00, Thursday 12:30, Sunday 18:30
  likes     liked-posts/ holds liked media in a different, aspirational palette and subject: the sea and the coast in
            sea blue, ice blue, snow white and deep navy, from coastal accounts that also lead liked_posts.json
  outliers  five posts outside the system: neon colors, off-pillar subjects, a loud caption voice, off-cadence times
About 95 photo posts (some carousels), 20 reels, 60 stories, 900 likes, 70 saves, 200 comments, 412 followers.
Strings are written the way Meta writes them (UTF-8 bytes escaped as latin-1). Images are drawn with Pillow;
about one in ten carries a .heic name over plain JPEG bytes. Needs Pillow and ffmpeg.
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
# the four colors of her feed and the share of photo posts each one leads
PALETTE = {"terracotta": (200, 100, 70), "cream": (240, 228, 200), "olive": (120, 120, 60), "chocolate": (90, 60, 40)}
LEADS = {"terracotta": 0.40, "cream": 0.27, "olive": 0.20, "chocolate": 0.13}
# her four pillars and the share of posts and reels each one carries
PILLARS = {"table": 0.45, "market": 0.25, "streets": 0.18, "coffee": 0.12}
POST_KINDS = {"p-table", "p-market", "p-streets", "p-coffee"}
VOICE = {  # pillar -> (opening labels, list items, closing questions, hashtag)
    "table": (["sunday table:", "tonight's table:", "lunch at home:", "from the table:"],
              ["tomatoes", "olive oil", "sea salt", "bread", "lemons", "basil", "anchovies", "white beans", "butter",
               "burrata", "garlic", "parsley"],
              ["what's on your table tonight?", "what are you cooking this week?", "who's coming over?"], "#fromthetable"),
    "market": (["market haul:", "saturday market:", "at the market:", "market morning:"],
               ["figs", "peaches", "chard", "quince", "green almonds", "plums", "apricots", "radishes", "cherries",
                "fennel"],
               ["what's in your bag?", "what's in season where you are?", "which stall would you hit first?"],
               "#marketmornings"),
    "streets": (["the walk home:", "side street:", "on the way:", "old town walk:"],
                ["blue doors", "cracked plaster", "a cat", "laundry lines", "tiled steps", "shutters", "bougainvillea",
                 "church bells", "a bakery"],
                ["where should i walk next?", "door or window?", "which street is yours?"], "#doorwaysandstreets"),
    "coffee": (["first coffee:", "coffee break:", "morning cup:"],
               ["one espresso", "a window seat", "the paper", "a cornetto", "rain outside", "a cortado", "nowhere to be"],
               ["how do you take yours?", "where's your coffee spot?"], "#coffeefirst"),
}
PLAIN = ["slow and simple.", "nothing fancy, just good.", "same as always.", "worth the wait.", "the good kind of quiet."]
SLOTS = {1: (8, 0), 3: (12, 30), 6: (18, 30)}  # weekday (Monday 0) -> hour, minute in UTC: Tuesday, Thursday, Sunday
# the coast she likes: the palette and the accounts of the posts she likes and saves
SEA = {"sea blue": (40, 120, 170), "ice blue": (196, 214, 228), "snow white": (244, 244, 240), "deep navy": (28, 40, 80)}
ASPIRE = ["salt.and.sea", "coastal.quiet", "blue.hour.coast", "the.sea.edit", "linen.and.tide", "harbor.light.studio",
          "cliffside.mornings", "seaside.stills", "tidal.notes", "white.shore.studio", "north.coast.film", "open.water.days"]
OUTLIERS = [  # (caption, weekday, hour, minute, neon palette): the five posts outside her system
    ("NEW KICKS!!! \U0001F525\U0001F525\U0001F525 link in bio", 5, 23, 40, [(255, 40, 160), (0, 210, 255), (20, 10, 40), (140, 0, 255)]),
    ("Monday motivation!!! \U0001F4AA\U0001F4AA #grind #gymlife", 0, 6, 5, [(0, 210, 255), (255, 40, 160), (20, 10, 40), (140, 0, 255)]),
    ("GUYS the concert last night was INSANE \U0001F92F\U0001F3A4", 5, 1, 20, [(140, 0, 255), (255, 40, 160), (20, 10, 40), (0, 210, 255)]),
    ("Rate my new desk setup 1-10?? \U0001F4BB✨ #setup", 4, 22, 10, [(255, 40, 160), (140, 0, 255), (20, 10, 40), (0, 210, 255)]),
    ("SALE ends tonight!!! use code MAREN20 \U0001F6CD️", 2, 21, 50, [(0, 210, 255), (140, 0, 255), (20, 10, 40), (255, 40, 160)]),
]
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


def counts(shares, n):
    """Whole counts for n items at these shares, by largest remainder."""
    raw = {k: v * n for k, v in shares.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: -(raw[k] - out[k]))[:n - sum(out.values())]:
        out[k] += 1
    return out


def dealt(shares, n, rng):
    """n labels at these shares, shuffled."""
    out = [k for k, c in counts(shares, n).items() for _ in range(c)]
    rng.shuffle(out)
    return out


def brand_caption(rng, pillar):
    labels, items, questions, tag = VOICE[pillar]
    head = rng.choice(labels) + " " if rng.random() < 0.85 else ""
    if rng.random() < 0.75:
        a, b, c = rng.sample(items, 3)
        body = f"{a}, {b}, {c}."
    else:
        body = rng.choice(PLAIN)
    cap = head + body
    if rng.random() < 0.65:
        cap += "\n\n" + rng.choice(questions)
    if rng.random() < 0.15:
        cap += " \U0001F33F"
    if rng.random() < 0.5:
        cap += "\n" + tag
    return cap


def light_grain(im):
    from PIL import Image
    w, h = im.size
    grain = Image.effect_noise((w // 2, h // 2), 40).resize((w, h)).convert("RGB")
    return Image.blend(im, grain, 0.05)


def draw_post(job):
    """job = (path, w, h, "p-<pillar>", [lead, second, third], seed): one feed photo of her system. The lead color is
    the field and covers more than half the frame; the subject sits on it in the other two."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed = job[:6]
    rng = random.Random(seed)
    jit = lambda col, k=10: tuple(max(0, min(255, v + rng.randint(-k, k))) for v in col)
    lead, second, third = jit(pal[0], 8), jit(pal[1]), jit(pal[2])
    sw, sh = w // 2, h // 2
    im = Image.new("RGB", (sw, sh))
    d = ImageDraw.Draw(im)
    for y in range(sh):
        d.line([(0, y), (sw, y)], fill=mix(lead, tuple(int(v * 0.9) for v in lead), y / sh))
    subject = kind[2:]
    if subject == "table":  # overhead, plates gathered at the center
        for _ in range(rng.randint(2, 3)):
            r = rng.randint(sw // 9, sw // 6)
            cx, cy = sw // 2 + rng.randint(-sw // 6, sw // 6), sh // 2 + rng.randint(-sh // 7, sh // 7)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=second)
            r2 = int(r * 0.66)
            d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=third)
            for _ in range(5):
                ox, oy, rr = rng.randint(-r2 // 2, r2 // 2), rng.randint(-r2 // 2, r2 // 2), rng.randint(4, 10)
                d.ellipse([cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr], fill=mix(second, third, 0.5))
    elif subject == "market":  # crates along the bottom third
        top = int(sh * 0.68)
        x = 0
        while x < sw:
            cw = rng.randint(sw // 5, sw // 3)
            d.rectangle([x + 3, top, x + cw - 3, sh], fill=second)
            for _ in range(10):
                r = rng.randint(6, 12)
                cx, cy = rng.randint(x + r + 4, max(x + r + 5, x + cw - r - 4)), rng.randint(top + r, top + (sh - top) // 2)
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=third)
            x += cw
    elif subject == "streets":  # a doorway on one third
        dw, dh = int(sw * 0.26), int(sh * 0.5)
        cx = int(sw * (0.33 if rng.random() < 0.5 else 0.67))
        y0 = int(sh * 0.36)
        d.rectangle([cx - dw // 2, y0, cx + dw // 2, sh], fill=second)
        d.ellipse([cx - dw // 2, y0 - dw // 2, cx + dw // 2, y0 + dw // 2], fill=second)
        d.rectangle([cx - dw // 3, y0 + dw // 6, cx + dw // 3, sh], fill=third)
    else:  # coffee: one cup at the center
        cx, cy = sw // 2 + rng.randint(-12, 12), sh // 2 + rng.randint(-16, 16)
        r = sw // 6
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=second)
        r2 = int(r * 0.6)
        d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=third)
        r3 = int(r * 0.42)
        d.ellipse([cx - r3, cy - r3, cx + r3, cy + r3], fill=mix(third, (30, 18, 12), 0.6))
    im = im.filter(ImageFilter.GaussianBlur(1.0)).resize((w, h), Image.BICUBIC)
    im = light_grain(im)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=86)
    return path


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
    """job = (path, w, h, kind, palette, seed[, look]). Draws at half size and upscales (soft, photo-like).
    look False keeps the colors as drawn (a light grain only) instead of the warm film grade."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed = job[:6]
    look = job[6] if len(job) > 6 else True
    if kind in POST_KINDS:
        return draw_post(job)
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
                import math
                ang = k * math.pi / 3
                px, py = cx + int(math.cos(ang) * r * 0.7), cy + int(math.sin(ang) * r * 0.7)
                d.ellipse([px - r // 2, py - r // 2, px + r // 2, py + r // 2], fill=petal)
            d.ellipse([cx - r // 4, cy - r // 4, cx + r // 4, cy + r // 4], fill=mix(c, (240, 200, 60), 0.6))
    im = im.filter(ImageFilter.GaussianBlur(1.2)).resize((w, h), Image.BICUBIC)
    im = film_look(im, rng) if look else light_grain(im)
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
    ap = argparse.ArgumentParser(description="Build a synthetic Instagram + Facebook export for one person with a clear "
                                             "personal brand, plus a folder of the posts she likes.")
    ap.add_argument("dest", help="workspace folder to create")
    ap.add_argument("--seed", type=int, default=9, help="random seed")
    ap.add_argument("--year", type=int, default=2026, help="first year of posts")
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
    likes_dir = dest / "liked-posts"
    for r in (root, fb, likes_dir):
        if r.exists():
            shutil.rmtree(r)
    jobs, counter = [], [0]

    def media_path(kind, ts, ext):
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        counter[0] += 1
        return f"media/{kind}/{d:%Y%m}/{17840000000000000 + counter[0] * 7919}{ext}"

    def stamp(day, hour, minute, spread=12):
        t = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=dt.timezone.utc)
        return int(t.timestamp()) + rng.randint(-spread, spread) * 60

    def look(lead):
        rest = [k for k in PALETTE if k != lead]
        rng.shuffle(rest)
        return [PALETTE[lead], PALETTE[rest[0]], PALETTE[rest[1]]]

    def insight(uri, ts, likes):
        return {"media_map_data": {"Media Thumbnail": {"uri": uri, "creation_timestamp": ts, "title": ""}},
                "string_map_data": {"Creation Timestamp": {"value": dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%b %d, %Y %I:%M %p")},
                                    "Likes": {"value": str(likes)},
                                    "Comments": {"value": str(max(0, int(likes / rng.uniform(9, 22))))},
                                    "Saves": {"value": str(int(likes / 12))}}}

    # every Tuesday, Thursday and Sunday at her three times; a few skipped, about one in six a reel
    day, slots = dt.date(year, 1, 1), []
    while day <= end:
        if day.weekday() in SLOTS:
            slots.append(day)
        day += dt.timedelta(days=1)
    for k in sorted(rng.sample(range(len(slots)), 8), reverse=True):
        slots.pop(k)
    pillars = dealt(PILLARS, len(slots), rng)
    reel_at = set(rng.sample(range(len(slots)), 20))
    photo_idx = [i for i in range(len(slots)) if i not in reel_at]
    leads = dict(zip(photo_idx, dealt(LEADS, len(photo_idx), rng)))

    posts, insights, reels, reel_insights, reel_rows = [], [], [], [], []
    for i, day in enumerate(slots):
        ts = stamp(day, *SLOTS[day.weekday()])
        pillar, cap = pillars[i], brand_caption(rng, pillars[i])
        if i in reel_at:
            reel_rows.append((ts, pillar, cap))
            continue
        lead, pal = leads[i], None
        n_media = 1 if rng.random() < 0.85 else rng.randint(2, 3)
        items = []
        for k in range(n_media):
            w, h = (1080, 1350) if rng.random() < 0.7 else (1080, 1080)
            ext = ".heic" if rng.random() < 0.1 else ".jpg"
            uri = media_path("posts", ts, ext)
            jobs.append((str(root / uri), w, h, f"p-{pillar}", look(lead), rng.random()))
            items.append({"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                          "title": ig_text(cap) if n_media == 1 else "", "cross_post_source": {"source_app": "FB"}})
        posts.append({"media": items} if n_media == 1 else {"media": items, "title": ig_text(cap), "creation_timestamp": ts})
        insights.append(insight(items[0]["uri"], ts, int(rng.lognormvariate(4.3, 0.4))))

    # the five posts outside her system: off-day, off-hour, neon, loud
    outlier_days = []
    for k, (cap, wd, hour, minute, neon) in enumerate(OUTLIERS):
        day = dt.date(year, 2 + k * 2, 3)
        day += dt.timedelta(days=(wd - day.weekday()) % 7)
        ts = stamp(day, hour, minute, spread=4)
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1350, "city", neon, rng.random(), False))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        insights.append(insight(uri, ts, int(rng.lognormvariate(3.4, 0.3))))
        outlier_days.append(f"{day.isoformat()} {hour:02d}:{minute:02d}")
    rng.shuffle(posts)

    # four reel clips drawn in her system, the reels point at them
    clip_jobs, clip_uris = [], []
    for i, (secs, pillar, lead) in enumerate(((4, "table", "terracotta"), (6, "market", "cream"),
                                              (9, "streets", "terracotta"), (12, "coffee", "olive"))):
        still = str(root / f"media/reels/clip{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, f"p-{pillar}", look(lead), rng.random()))
        uri = f"media/reels/{17841000000000000 + i * 104729}.mp4"
        clip_jobs.append((str(root / uri), still, secs))
        clip_uris.append(uri)
    clip_of = {"table": 0, "market": 1, "streets": 2, "coffee": 3}
    for ts, pillar, cap in reel_rows:
        uri = clip_uris[clip_of[pillar]]
        reels.append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(cap),
                                 "media_metadata": {"video_metadata": {}}}]})
        reel_insights.append(insight(uri, ts, int(rng.lognormvariate(4.0, 0.4))))

    stories = []
    story_pillars = dealt(PILLARS, 60, rng)
    story_leads = dealt(LEADS, 60, rng)
    for i in range(60):
        ts = ts_for(rng, year, rng.choice(months), end)
        uri = media_path("stories", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1920, f"p-{story_pillars[i]}", look(story_leads[i]), rng.random()))
        stories.append({"uri": uri, "creation_timestamp": ts, "title": "", "media_metadata": {"photo_metadata": {}}})
    stories.sort(key=lambda s: s["creation_timestamp"])

    # what she likes: the coast. The coastal accounts take most of her likes and saves, and their posts sit in
    # liked-posts/ as the media she saved
    weights = [1 / (i + 1) ** 0.9 for i in range(len(ACCOUNTS))]
    order = ACCOUNTS[:]
    rng.shuffle(order)
    liked = {}
    for i in range(900):
        if i < len(ASPIRE):
            acct = ASPIRE[i]
        elif i < len(ASPIRE) + len(order):
            acct = order[i - len(ASPIRE)]
        else:
            acct = rng.choice(ASPIRE) if rng.random() < 0.55 else rng.choices(order, weights)[0]
        ts = ts_for(rng, year, rng.choice(months), end)
        liked.setdefault(acct, []).append({"href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/",
                                           "value": ig_text("\U0001F44D"), "timestamp": ts})
    saved = []
    for i in range(70):
        acct = rng.choice(ASPIRE) if rng.random() < 0.8 else rng.choices(order, weights)[0]
        ts = ts_for(rng, year, rng.choice(months), end)
        saved.append({"title": acct, "string_map_data": {"Saved on": {
            "href": f"https://www.instagram.com/p/{rng.getrandbits(40):x}/", "timestamp": ts}}})
    sea = list(SEA.values())
    for acct in ASPIRE:
        for n in range(1, 5):
            pal = sea[:]
            rng.shuffle(pal)
            scene = "beach" if rng.random() < 0.6 else "hills"
            w, h = (1080, 1350) if rng.random() < 0.7 else (1080, 1080)
            jobs.append((str(likes_dir / f"{acct}_{n}.jpg"), w, h, scene, pal, rng.random(), False))

    comment_lines = ["this is so good", "obsessed", "need to go here", "the colors!!", "ok this light ✨",
                     "save me a slice", "when are we going back", "\U0001F525\U0001F525", "that table", "take me with you"]
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
    for i, acct in enumerate(ACCOUNTS + ASPIRE + [f"film.{w}{i}" for i, w in enumerate(["notes", "lab", "club", "days"] * 35)][:128]):
        following.append({"title": acct, "string_list_data": [
            {"href": f"https://www.instagram.com/_u/{acct}", "timestamp": ts_for(rng, rng.choice([2024, 2025, year]), rng.randint(1, 9), end)}]})

    def write(base, rel, obj):
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2))

    write(root, "personal_information/personal_information/personal_information.json",
          {"profile_user": [{"title": "", "media_map_data": {}, "string_map_data": {
              "Username": {"value": HANDLE}, "Name": {"value": NAME},
              "Bio": {"value": ig_text("home cooking, market mornings and the walk home \U0001F33F three posts a week from my table")}}}]})
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

    # Facebook: a handful of posts in her voice and two albums in her palette
    fb_posts, albums = [], []
    for k, (title, pillar, m, n) in enumerate((("Sunday tables", "table", 3, 8), ("Market mornings", "market", 6, 6))):
        photos = []
        for j in range(n):
            ts = ts_for(rng, year, m, end)
            uri = f"your_facebook_activity/posts/media/{title.replace(' ', '')}_{k}/{10160000000000000 + k * 1000 + j}.jpg"
            jobs.append((str(fb / uri), 1080, 1350, f"p-{pillar}", look(rng.choice(list(PALETTE))), rng.random()))
            photos.append({"uri": uri, "creation_timestamp": ts, "title": ig_text(title)})
        albums.append({"name": ig_text(title), "photos": photos, "cover_photo": photos[0],
                       "last_modified_timestamp": photos[-1]["creation_timestamp"], "description": ""})
        write(fb, f"your_facebook_activity/posts/album/{k}.json", albums[-1])
    for i in range(14):
        m = rng.choice(months)
        ts = ts_for(rng, year, m, end)
        pillar = rng.choice(list(PILLARS))
        post = {"timestamp": ts, "data": [{"post": ig_text(brand_caption(rng, pillar))}],
                "title": ig_text(f"{NAME} updated her status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, f"p-{pillar}", look(rng.choice(list(PALETTE))), rng.random()))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(make_reel, clip_jobs)
    photo_leads = counts(LEADS, len(photo_idx))
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "likes_folder": likes_dir.name,
                      "handle": HANDLE, "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts),
                      "reels": len(reels), "reel_clips": len(clip_jobs), "stories": len(stories), "likes": 900,
                      "liked_accounts": len(liked), "liked_media": len(ASPIRE) * 4, "saved": len(saved),
                      "comments": len(comments), "followers": len(followers), "following": len(following),
                      "facebook_posts": len(fb_posts), "facebook_albums": len(albums), "images": len(jobs),
                      "intended": {
                          "palette_leads": {k: round(v / len(photo_idx), 3) for k, v in photo_leads.items()},
                          "pillars": {k: round(v / len(slots), 3) for k, v in counts(PILLARS, len(slots)).items()},
                          "cadence": ["Tue 08:00", "Thu 12:30", "Sun 18:30"],
                          "voice": ["label-colon opener", "list of three", "closing question after a blank line"],
                          "aspire_palette": list(SEA), "aspire_subject": "the sea and the coast",
                          "outliers": outlier_days}}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
