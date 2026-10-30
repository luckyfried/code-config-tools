#!/usr/bin/env python3
"""Build one invented person's 2026 on Instagram and Facebook, as the two "Download your information" exports.

USAGE:
    python3 make_person.py DEST [--seed 7] [--year 2026] [--end 2026-10-18]
    TRIBUTE_PHOTOS=DIR[:DIR...] python3 make_person.py DEST
    python3 make_person.py DEST --subjects B     # the storyboard agent's look at each placed photograph, from the table

TRIBUTE_PHOTOS names the photo sets that stand in for the photographs the two share: folders read as files and never
written, searched in order for each file a post names. Unset, the set is photos/ beside this script (real CC0
photographs, SOURCES.md names each); set to an empty value, every photograph is drawn. With a set, each post, clip and
post of the friend's that carries a photograph in its own row (TOGETHER, CLIPS_TOGETHER, FEED, and GENERATED for the
generated posts by their place in the year) is that set photograph (cut where the row says, at most 2400 px on the
long side) in place of the drawing; everything else stays drawn, so every count is the same either way.
Every caption on a set photograph is written from that photograph: it names what the picture shows and never a
thing it does not, and no set photograph appears in two rows.

Every photograph written carries a subject box, the box that must stay in frame ([x0, y0, x1, y1], fractions of the
photograph): the people a drawing stands in its foreground, SUBJECTS for a set photograph (the part its caption is
about, never the whole print by default), the middle of a drawing with no one in it. DEST/fixture-subjects.json holds them by the SHA-1 of each photograph's bytes. --subjects B
writes each one into the "photos" of B's storyboards, the record the storyboard agent writes after opening each
photograph (pipeline/2-storyboards.md), so a fixture run checks and renders the way a real one does.

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
    dani.reyes-feed/                         the named friend's own feed as an agent saves it from a browser:
        items.json (feed_of, handle, name, the posts with captions and comment threads), *.jpg

The person has a clear taste: film-grain travel and food in warm earth tones (terracotta, ochre, olive, cream,
espresso). About 120 posts (some carousels), 27 reels, 60 stories, 900 likes across 40 accounts whose names share
that taste, 70 saves, 200 comments, 412 followers (96 new this year), 180 following. July (two weeks in Sicily) is
clearly the busiest month and February the quietest.

Her nine most-liked of the year are unambiguous: seven posts and two reels, one in each of nine months from January
to October, between 291 and 486 likes, while nothing else reaches 225 (the tenth sits at least 66 below the
ninth). Each of the nine carries a caption that says why it landed (the light, the sound, the color, the table). The friend the film is for is Dani Reyes (@dani.reyes): tagged in more than twenty posts and stories, in most of the
group photos, a first photo together in January and a latest one in October, more than forty comments traded in two
distinct voices (hers lowercase and warm, Dani's loud with emoji), two short clips the two shot together
(media/reels/together*.mp4), and a caption that names the birthday (October 24, Dani turns 30). @theo.makes is the
account she writes to most, with a much thinner shared history, so the most frequent account is not the named one.
Dani's own feed is a dozen posts in a cool, bright palette unlike hers.

Strings are written the way
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
    """job = (path, w, h, kind, palette, seed[, figures[, look]]). Draws at half size and upscales (soft,
    photo-like); figures > 0 stands that many people in the foreground (the photos the two are in); look "clean"
    skips the person's warm film grade (the friend's own phone photos)."""
    from PIL import Image, ImageDraw, ImageFilter
    path, w, h, kind, pal, seed = job[:6]
    figures = job[6] if len(job) > 6 else 0
    look = job[7] if len(job) > 7 else "film"
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
    if figures:
        ground = int(sh * 0.97)
        span = sw * (0.34 + 0.12 * min(figures, 4))
        x0 = (sw - span) / 2
        for k in range(figures):
            cx = int(x0 + span * (k + 0.5) / figures + rng.randint(-8, 8))
            tall = int(sh * rng.uniform(0.36, 0.44))
            r = max(8, int(tall * 0.13))
            body = mix(e, (20, 16, 14), 0.35 + 0.15 * (k % 2))
            d.rounded_rectangle([cx - int(r * 1.5), ground - tall + 2 * r, cx + int(r * 1.5), ground], radius=r, fill=body)
            d.ellipse([cx - r, ground - tall, cx + r, ground - tall + 2 * r], fill=mix(body, a, 0.25))
    im = im.filter(ImageFilter.GaussianBlur(1.2)).resize((w, h), Image.BICUBIC)
    if look == "film":
        im = film_look(im, rng)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=84)  # a .heic name still gets JPEG bytes
    return path


def make_reel(job):
    """job = (path, still, seconds): a slow push across one still, 540x960, 30 fps."""
    path, still, secs = job
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frames = int(secs * 30)
    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='1+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=540x960:fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", still, "-vf", vf, "-frames:v", str(frames),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", path], check=True)
    return path


FRIEND, FRIEND_NAME = "dani.reyes", "Dani Reyes"
BIRTHDAY = (10, 24)  # the day the person names in a caption: dani turns 30
SECOND = "theo.makes"  # the account she writes to most, with a much thinner shared history
TOGETHER = [  # (month, day, scene, place, others tagged, caption, photograph): the year of photos the two are in;
    # the photograph is a set file, (file, cut) or a list of files for a carousel
    (1, 3, "coffee", "lisbon", [], "first coffee of the year with @dani.reyes, same window, same order", "coffee.jpg"),
    (1, 18, "oldtown", "lisbon", [], "@dani.reyes found the only bakery open on a sunday", "bakery.jpg"),
    (2, 7, "table", "home", ["ines.walks", "kofi.cooks"], "ramen night at dani's, she made enough for twelve", "ramen.jpg"),
    (3, 9, "oldtown", "porto", [], "porto with @dani.reyes, she stopped at every painted wall", "alfama.jpg"),
    (3, 22, "market", "porto", ["theo.makes"], "spring in porto, theo stopped at every flower bed", "picnic.jpg"),
    (4, 12, "coffee", "porto", [], "porto in black and white, on the film camera dani laughs at", "bicycle.jpg"),
    (5, 4, "market", "oaxaca", [], "oaxaca with @dani.reyes, she picked the tomatoes, i held the bowl", "tomatoes.jpg"),
    (5, 26, "table", "oaxaca", ["kofi.cooks", "liv.outside"], "pottery class in oaxaca, dani's bowl came out better than mine", "hands-pottery.jpg"),
    (6, 14, "hills", "oaxaca", [], "6am on the ridge with @dani.reyes, worth every step", "mountain-hike.jpg"),
    (7, 6, "beach", "sicily", ["theo.makes", "ines.walks"], "the whole crew in sicily", "crew-sunset-shore.jpg"),
    (7, 11, "beach", "sicily", [], "the surfers were up before breakfast and so were we @dani.reyes", "surf.jpg"),
    (7, 19, "market", "sicily", [], "@dani.reyes says this palace looks like a lemon", "sintra.jpg"),
    (7, 27, "sunset", "sicily", [], "last night of the trip, dani cried at the sunset and so did i", "sunset-beach.jpg"),
    (8, 9, "table", "sicily", ["kofi.cooks", "sam_and_june"], "the grill was going until 2am", "city-night.jpg"),
    (9, 5, "oldtown", "marrakech", [], "front row in marrakech with my favorite travel partner @dani.reyes", "concert.jpg"),
    (9, 20, "oldtown", "marrakech", [], "the whole city from the top, @dani.reyes found the lookout", "graca.jpg"),
    (10, 3, "table", "home", [], "dani turns 30 on october 24 and i'm already planning the table @dani.reyes", ["birthday-cake.jpg", "balloons.jpg"]),
    (10, 12, "table", "home", ["ines.walks", "theo.makes", "liv.outside"], "sunday walk through the garden, the usual suspects", "garden.jpg"),
]
GROUP_WITHOUT = [  # group photos she is not in
    (6, 2, "table", "oaxaca", ["theo.makes", "kofi.cooks", "liv.outside"], "dinner with the oaxaca crew"),
    (8, 30, "beach", "sicily", ["theo.makes", "sam_and_june", "ines.walks"], "beach day minus one, we missed you"),
]
THEO_ONLY = [
    (2, 21, "coffee", "home", "@theo.makes and his third espresso"),
    (4, 25, "oldtown", "porto", "theo shooting the same doorway as me @theo.makes"),
]
STORIES_TOGETHER = [(1, 4, "coffee"), (2, 8, "table"), (3, 10, "oldtown"), (5, 5, "market"), (6, 15, "hills"),
                    (7, 12, "beach"), (7, 20, "market"), (9, 6, "oldtown"), (10, 4, "table")]
CLIPS_TOGETHER = [  # the two short videos the two shot together: (month, day, scene, place, seconds, caption, the still the clip opens on)
    (7, 12, "beach", "sicily", 5, "@dani.reyes and the whole empty beach, the video", "couple-beach.jpg"),
    (9, 21, "oldtown", "marrakech", 7, "dani lost in the rug shop in the medina @dani.reyes", "fes.jpg"),
]
HER_LINES = [  # what the person writes under dani's posts: lowercase, no full stops, warm and plain
    "you look so happy here", "this light on you", "i still think about this lunch", "you are the best travel partner",
    "save me a seat always", "ok this is your best one", "the way you laugh", "you make every trip better",
    "still thinking about that lemon", "i miss this already", "you and your pastry map", "best hair in sicily",
    "come back to lisbon soon", "you always know the place", "nobody packs a picnic like you", "so proud of you",
    "you make soup an event", "this is the one", "you never stop dancing", "my favorite person to get lost with",
    "you made it look easy", "the best laugh in porto", "ten years of this and counting",
]
DANI_LINES = [  # how dani writes: capitals, exclamation marks, emoji
    "MAREN!!! \U0001F62D this is everything", "Okay but who let you be this talented??", "Still not over this trip \U0001F34B\U0001F34B",
    "Best day. Best human. \U0001F49B", "Book the flights. I'm serious!!", "You and that camera \U0001F4F7 haha",
    "Crying at my desk \U0001F62D\U0001F62D", "THE LIGHT. The light!!", "Take me back immediately ☀️",
    "You're a menace and I love you", "Who's hungry?? (me. always me)", "Frame this one!!!",
    "Pastry map 2.0 coming soon \U0001F950", "I look like a tomato and I don't care \U0001F345", "Next year: Japan?? \U0001F440",
    "My favorite photographer!!", "Soup club forever \U0001F372", "Ok you win, it's perfect", "Dancing until they close!! \U0001F483",
    "Love you more \U0001F49B", "Same order, always ☕", "Can't wait for the table!!!",
]
UNDER_TAGGED = {  # the first exchange under each post of dani's that tags the person, by its day: the two of them on what is in it
    (1, 19): ("you in the tulips, finally", "WE DID IT!! Tulip day \U0001F337"),
    (3, 11): ("you and every painted wall in porto", "I'd stop at every one again!!"),
    (5, 6): ("i'd carry your bags anywhere", "Best market. Best bag holder. \U0001F33A"),
    (7, 13): ("the water was so cold and you went in first", "Someone had to!! \U0001F30A"),
    (7, 28): ("ok i was crying", "WE BOTH WERE \U0001F62D"),
    (9, 22): ("you never stop dancing", "Dancing until they close!! \U0001F483"),
}
COOL = {  # dani's own feed: cool, bright, nothing like the person's earth tones
    "teal": (40, 140, 150), "coral": (240, 112, 98), "cobalt": (42, 82, 172), "mint": (168, 222, 196),
    "white": (244, 246, 248), "pink": (238, 150, 176), "sky": (126, 186, 230), "navy": (28, 40, 82),
}
FEED = [  # (month, day, scene, four cool colors, tags maren, caption, photograph)
    (1, 10, "city", ["sky", "cobalt", "white", "navy"], False, "Wedding season starts NOW ✌️", "wedding-arms-up.jpg"),
    (1, 19, "flowers", ["pink", "coral", "white", "teal"], True, "Tulip fields with @maren.okafor!! \U0001F337", "flowers.jpg"),
    (2, 14, "flowers", ["pink", "coral", "white", "navy"], False, "Park bench, two coffees, zero plans \U0001F49B", "park-portrait.jpg"),
    (3, 11, "city", ["teal", "sky", "white", "navy"], True, "Porto!!! With my favorite photographer @maren.okafor", "lisbon-tram.jpg"),
    (4, 2, "rain", ["cobalt", "sky", "white", "navy"], False, "Rain day = couch day", "living-room.jpg"),
    (5, 6, "flowers", ["coral", "pink", "mint", "teal"], True, "Oaxaca market haul \U0001F33A @maren.okafor held the bags", ("market.jpg", (0.0, 0.48, 1.0, 1.0))),
    (6, 16, "hills", ["mint", "teal", "sky", "navy"], False, "6am club. Never again. (Again tomorrow)", "morning-run.jpg"),
    (7, 13, "beach", ["teal", "sky", "white", "cobalt"], True, "Sunset swim with @maren.okafor \U0001F30A", None),
    (7, 28, "sunset", ["coral", "pink", "sky", "navy"], True, "Not crying, you're crying \U0001F62D @maren.okafor", "desert-sunset.jpg"),
    (8, 20, "city", ["cobalt", "teal", "white", "navy"], False, "Still finding streamers in my hair \U0001F389", None),
    (9, 22, "flowers", ["coral", "teal", "pink", "navy"], True, "Marrakech dance floor \U0001F483 @maren.okafor", "crowd-lights.jpg"),
    (10, 9, "beach", ["sky", "mint", "white", "cobalt"], False, "Almost 30 and still the one who rows", "dolomites.jpg"),
]


# The generated posts that carry a set photograph, by their place in the year's generation order (seed 7), each with
# the caption written from that photograph: the dinners and the trip post the films' tables set.
GENERATED = {
    46: ("rooftop-garden.jpg", "the rooftop garden from the ninth floor, dinner up there next week"),
    62: ("spice-stalls.jpg", "the spice stalls before dinner with @theo.makes, he bought one of everything"),
    64: ("candle.jpg", "dinner by candlelight with @liv.outside"),
    98: ("bairro-alto.jpg", "dinner downtown with @ines.walks, the fountain all lit up"),
    117: ("skyline-night.jpg", "last night out, the whole city lit up below the tower"),
}
SET_LONGEST = 2400
SUBJECTS = {  # each set photograph's subject box in its own frame, before any cut: the part its caption is about, drawn
    # as tight as a careful person would (the people and what they hold, the part of a view, the thing in a still life);
    "coffee.jpg": [0.3, 0.1, 0.7, 0.4],
    "bakery.jpg": [0.32, 0.06, 0.72, 0.6],
    "ramen.jpg": [0.2, 0.33, 0.92, 0.88],
    "alfama.jpg": [0.48, 0.38, 0.8, 0.82],
    "picnic.jpg": [0.25, 0.25, 0.75, 0.75],
    "bicycle.jpg": [0.4, 0.42, 0.7, 0.88],
    "tomatoes.jpg": [0.33, 0.25, 0.67, 0.82],
    "mountain-hike.jpg": [0.32, 0.4, 0.68, 0.8],
    "crew-sunset-shore.jpg": [0.22, 0.6, 0.53, 0.93],
    "surf.jpg": [0.2, 0.4, 0.36, 0.62],
    "sintra.jpg": [0.62, 0.22, 1.0, 0.9],
    "sunset-beach.jpg": [0.04, 0.42, 0.32, 0.74],
    "city-night.jpg": [0.25, 0.3, 0.62, 0.75],
    "concert.jpg": [0.2, 0.3, 0.8, 1.0],
    "graca.jpg": [0.25, 0.47, 0.75, 0.85],
    "balloons.jpg": [0.25, 0.05, 0.82, 0.45],
    "birthday-cake.jpg": [0.15, 0.05, 0.93, 0.7],
    "garden.jpg": [0.32, 0.35, 0.68, 0.85],
    "hands-pottery.jpg": [0.3, 0.0, 0.77, 0.75],
    "flowers.jpg": [0.2, 0.25, 0.8, 0.9],
    "dolomites.jpg": [0.15, 0.45, 0.85, 1.0],
    "bairro-alto.jpg": [0.15, 0.05, 0.7, 0.85],
    "couple-beach.jpg": [0.6, 0.45, 0.72, 0.67],
    "fes.jpg": [0.25, 0.15, 0.75, 0.85],
    "wedding-arms-up.jpg": [0.05, 0.3, 0.9, 0.8],
    "park-portrait.jpg": [0.3, 0.25, 0.75, 1.0],
    "lisbon-tram.jpg": [0.47, 0.47, 0.8, 0.8],
    "living-room.jpg": [0.35, 0.42, 1.0, 0.85],
    "market.jpg": [0.39, 0.51, 0.79, 0.66],
    "morning-run.jpg": [0.55, 0.35, 0.7, 0.7],
    "desert-sunset.jpg": [0.1, 0.3, 0.7, 0.7],
    "crowd-lights.jpg": [0.3, 0.68, 0.85, 1.0],
    "rooftop-garden.jpg": [0.15, 0.5, 0.52, 1.0],
    "spice-stalls.jpg": [0.1, 0.2, 0.9, 0.8],
    "candle.jpg": [0.1, 0.3, 0.75, 0.85],
    "skyline-night.jpg": [0.6, 0.05, 0.85, 0.75],
}


def subject_of(job):
    """The subject box of the photograph a draw job writes: its set photograph's, carried through the cut, or the
    people the drawing stands in its foreground (draw_scene's geometry), or the middle of a drawing with no one in it."""
    path, w, h = job[:3]
    figures = job[6] if len(job) > 6 else 0
    if path in SETS:
        src, cut = SETS[path]
        x0, y0, x1, y1 = SUBJECTS[Path(src).name]
        c = cut or (0, 0, 1, 1)
        fit = lambda v, a, b: round(min(1.0, max(0.0, (v - a) / (b - a))), 3)
        return [fit(x0, c[0], c[2]), fit(y0, c[1], c[3]), fit(x1, c[0], c[2]), fit(y1, c[1], c[3])]
    if not figures:  # a drawing with no one in it is a pattern: its middle stands for the part a person would box
        return [0.3, 0.3, 0.7, 0.7]
    sw, sh = w // 2, h // 2
    span = 0.34 + 0.12 * min(figures, 4)
    reach = (1.5 * max(8, sh * 0.44 * 0.13) + 8) / sw
    return [round(max(0.0, (1 - span) / 2 + span / (2 * figures) - reach), 3), 0.53,
            round(min(1.0, (1 - span) / 2 + span * (1 - 1 / (2 * figures)) + reach), 3), 0.97]


def subjects_by_file(ws, B):
    """{photo file name in B: its subject box}, from DEST/fixture-subjects.json through the bytes of each library copy."""
    import hashlib
    table = json.loads((Path(ws) / "fixture-subjects.json").read_text())
    picks = json.loads((Path(B) / "picks.json").read_text())
    return {Path(r["photo"]).name: table[hashlib.sha1((Path(B) / r["src"]).read_bytes()).hexdigest()] for r in picks.get("items") or []}


def record_subjects(ws, B):
    """Write each storyboard photograph's subject box into B's storyboards."""
    boxes = subjects_by_file(ws, B)
    n = 0
    for f in sorted(Path(B).glob("storyboards/*/storyboard.json")):
        b = json.loads(f.read_text())
        for r in b["photos"].values():
            r["subject"] = boxes[Path(r["file"]).name]
            n += 1
        f.write_text(json.dumps(b, indent=2, ensure_ascii=False))
    print(f"recorded {n} subject boxes into {B}/storyboards")


def set_photo(photo):
    """A row's photograph as (path, cut) when TRIBUTE_PHOTOS names the sets, or None to draw it."""
    named = os.environ.get("TRIBUTE_PHOTOS", str(Path(__file__).resolve().parent / "photos"))
    folders = [Path(f) for f in named.split(os.pathsep) if f]
    if not folders or not photo:
        return None
    name, cut = photo if isinstance(photo, tuple) else (photo, None)
    for f in folders:
        if (f / name).exists():
            return str(f / name), cut
    sys.exit(f"TRIBUTE_PHOTOS has no {name}")


def place_set_photo(job):
    """job = (path, (source, cut)): the set photograph written as a JPEG at path, in place of the drawing."""
    from PIL import Image, ImageOps
    path, (src, cut) = job
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if cut:
        w, h = im.size
        im = im.crop((round(cut[0] * w), round(cut[1] * h), round(cut[2] * w), round(cut[3] * h)))
    im.thumbnail((SET_LONGEST, SET_LONGEST))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=92)
    return path


SETS = {}  # path -> (set photograph, cut): the photographs place_set_photo writes over the drawings


def friendship(rng0, year, end, months, root, jobs, clip_jobs, pal, media_path, insight):
    """The year the person shares with dani: photos and stories they are both in, two clips they shot together, the
    comments she writes under dani's posts, a thinner history with theo (written to far more often) and dani's own
    feed, each comment thread carrying both voices."""
    rng = random.Random(rng0.random())
    on = lambda m, d, hh=13: int(dt.datetime(year, m, d, hh, rng.randint(0, 59), tzinfo=dt.timezone.utc).timestamp())
    tag = lambda names: [{"username": n} for n in names]
    out = {"posts": [], "insights": [], "reels": [], "reel_insights": [], "stories": [], "comments": [], "feed": []}

    def post(m, d, scene, place, tagged, cap, figures, photo=None):
        ts = on(m, d)
        w, h = (1080, 1350) if rng.random() < 0.7 else (1080, 1080)
        seed = rng.random()
        media = []
        for ph in (photo if isinstance(photo, list) else [photo]):
            uri = media_path("posts", ts, ".jpg")
            jobs.append((str(root / uri), w, h, scene, pal(m), seed, figures))
            if (sp := set_photo(ph)):
                SETS[str(root / uri)] = sp
            media.append({"uri": uri, "creation_timestamp": ts, "title": ig_text(cap) if len(media) == 0 and not isinstance(photo, list) else "",
                          "media_metadata": {"photo_metadata": {"exif_data": []}},
                          "tagged_users": tag(tagged), "cross_post_source": {"source_app": "FB"}})
        out["posts"].append({"media": media} if len(media) == 1 else {"media": media, "title": ig_text(cap), "creation_timestamp": ts})
        uri = media[0]["uri"]
        likes = int(rng.uniform(120, 210))
        out["insights"].append(insight(uri, ts, likes, int(likes / rng.uniform(8, 14))))

    for m, d, scene, place, others, cap, photo in TOGETHER:
        post(m, d, scene, place, [FRIEND] + others, cap, 2 + len(others), photo)
    for m, d, scene, place, others, cap in GROUP_WITHOUT:
        post(m, d, scene, place, others, cap, len(others) + 1)
    for m, d, scene, place, cap in THEO_ONLY:
        post(m, d, scene, place, [SECOND], cap, 2)
    for m, d, scene in STORIES_TOGETHER:
        ts = on(m, d, 18)
        uri = media_path("stories", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1920, scene, pal(m), rng.random(), 2))
        out["stories"].append({"uri": uri, "creation_timestamp": ts, "title": "", "media_metadata": {"photo_metadata": {}},
                               "tagged_users": tag([FRIEND])})
    for i, (m, d, scene, place, secs, cap, photo) in enumerate(CLIPS_TOGETHER):
        ts = on(m, d, 9)
        still = str(root / f"media/reels/together{i + 1}-still.jpg")
        jobs.append((still, 1080, 1920, scene, pal(m), rng.random(), 2))
        if (sp := set_photo(photo)):
            SETS[still] = sp
        uri = f"media/reels/{17845000000000000 + i * 6007}.mp4"
        clip_jobs.append((str(root / uri), still, secs))
        out["reels"].append({"media": [{"uri": uri, "creation_timestamp": ts, "title": ig_text(cap),
                                        "media_metadata": {"video_metadata": {}}, "tagged_users": tag([FRIEND])}]})
        out["reel_insights"].append(insight(uri, ts, int(rng.uniform(140, 200)), int(rng.uniform(12, 20))))

    def comment(owner, text, ts):
        return {"media_list_data": [{"uri": ""}], "string_map_data": {"Comment": {"value": ig_text(text)},
                                                                    "Media Owner": {"value": owner}, "Time": {"timestamp": ts}}}

    # dani's feed: every post gets a thread; the person's lines and dani's replies alternate down the year
    her = HER_LINES[:]
    dani = DANI_LINES[:]
    k = 0
    for m, d, scene, cols, tags_her, cap, photo in FEED:
        ts = on(m, d, 12)
        thread = []
        for j in range(2):
            t1 = ts + 3600 * (2 + 5 * j) + rng.randint(0, 900)
            t2 = t1 + 1800 + rng.randint(0, 900)
            mine, theirs = UNDER_TAGGED.get((m, d), (None, None)) if j == 0 else (None, None)
            thread.append({"account": HANDLE, "text": mine or her[k % len(her)], "ts": t1})
            thread.append({"account": FRIEND, "text": theirs or dani[k % len(dani)], "ts": t2})
            k += 1
        if rng.random() < 0.5:
            thread.insert(1, {"account": rng.choice(["ines.walks", "kofi.cooks", "liv.outside"]), "text": "obsessed", "ts": ts + 5400})
        out["feed"].append({"ts": ts, "caption": cap, "photo": photo, "scene": scene, "colors": cols, "tagged": [HANDLE] if tags_her else [],
                            "comments": thread, "figures": 2 if tags_her else 1})
        out["comments"] += [comment(FRIEND, c["text"], c["ts"]) for c in thread if c["account"] == HANDLE]
    for line in her[k:]:  # the rest of her lines sit under dani's older posts, outside the reachable feed
        out["comments"].append(comment(FRIEND, line, ts_for(rng, year, rng.choice(months), end)))
    tagged = sum(1 for p in out["posts"] if any(t["username"] == FRIEND for t in p["media"][0]["tagged_users"]))
    groups = [p for p in out["posts"] if len(p["media"][0]["tagged_users"]) >= 3]
    out["summary"] = {"handle": FRIEND, "name": FRIEND_NAME, "birthday": "%d-%02d-%02d" % (year, *BIRTHDAY),
                      "posts_tagged": tagged, "stories_tagged": len(out["stories"]), "clips_together": len(out["reels"]),
                      "group_photos": len(groups),
                      "group_photos_with_her": sum(1 for p in groups if any(t["username"] == FRIEND for t in p["media"][0]["tagged_users"])),
                      "first_together": "%d-%02d-%02d" % (year, TOGETHER[0][0], TOGETHER[0][1]),
                      "latest_together": "%d-%02d-%02d" % (year, TOGETHER[-1][0], TOGETHER[-1][1]),
                      "comments_traded": sum(len(f["comments"]) for f in out["feed"]) + len(her[k:]),
                      "second_friend": SECOND}
    return out


def write_feed(dest, end, jobs, feed):
    """dani's own profile as an agent saves it from a browser: items.json in the pulled shape, with feed_of naming
    whose feed it is, and the photos beside it."""
    base = dest / f"{FRIEND}-feed"
    if base.exists():
        shutil.rmtree(base)
    posts = []
    for i, f in enumerate(feed):
        name = f"media/{i + 1:02d}.jpg"
        jobs.append((str(base / name), 1080, 1350, f["scene"], [COOL[c] for c in f["colors"]], random.Random(i).random(), f["figures"], "clean"))
        if (sp := set_photo(f["photo"])):
            SETS[str(base / name)] = sp
        posts.append({"ts": f["ts"], "caption": f["caption"], "media": [name], "tagged": f["tagged"], "thread": f["comments"]})
    (base).mkdir(parents=True, exist_ok=True)
    (base / "items.json").write_text(json.dumps({"source": f"browser: instagram.com/{FRIEND}", "feed_of": FRIEND,
                                                 "handle": FRIEND, "name": FRIEND_NAME, "saved": end.isoformat(),
                                                 "posts": posts}, indent=2, ensure_ascii=False))
    return {"folder": base.name, "posts": len(posts), "tag_her": sum(1 for p in posts if p["tagged"]),
            "comments": sum(len(p["thread"]) for p in posts)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dest")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--end", default="2026-10-18", help="last day of data (the export date)")
    ap.add_argument("--subjects", metavar="B", help="write the fixture's subject boxes into run folder B's storyboards")
    a = ap.parse_args()
    if a.subjects:
        return record_subjects(a.dest, a.subjects)
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
    made = 0
    for m in months:
        for _ in range(SEASON[m][0]):
            ts = ts_for(rng, year, m, end)
            cap = caption(m)
            made += 1
            if made in GENERATED and set_photo(GENERATED[made][0]):
                cap = GENERATED[made][1]
            n_media = 1 if rng.random() < 0.8 else rng.randint(2, 3)
            items = []
            for k in range(n_media):
                w, h = (1080, 1350) if rng.random() < 0.6 else (1080, 1080)
                ext = ".heic" if rng.random() < 0.1 else ".jpg"
                uri = media_path("posts", ts, ext)
                jobs.append((str(root / uri), w, h, rng.choice(SEASON[m][1]), pal(m), rng.random()))
                if k == 0 and made in GENERATED and (sp := set_photo(GENERATED[made][0])):
                    SETS[str(root / uri)] = sp
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
    for _ in range(200):
        acct = rng.choices(FRIENDS + others, [2, 14, 5, 3, 2, 2] + [1] * len(others))[0]
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

    friends = friendship(rng, year, end, months, root, jobs, clip_jobs, pal, media_path, insight)
    posts += friends["posts"]
    insights += friends["insights"]
    reels += friends["reels"]
    reel_insights += friends["reel_insights"]
    stories = sorted(stories + friends["stories"], key=lambda st: st["creation_timestamp"])
    comments += friends["comments"]

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

    feed = write_feed(dest, end, jobs, friends["feed"])

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(draw_scene, jobs, chunksize=4)
        pool.map(place_set_photo, list(SETS.items()))
        pool.map(make_reel, clip_jobs)
    import hashlib
    (dest / "fixture-subjects.json").write_text(json.dumps(
        {hashlib.sha1(Path(j[0]).read_bytes()).hexdigest(): subject_of(j) for j in jobs}, indent=1))
    print(json.dumps({"workspace": str(dest), "instagram": root.name, "facebook": fb.name, "handle": HANDLE,
                      "posts": len(posts), "post_media": sum(len(p["media"]) for p in posts), "reels": len(reels),
                      "reel_clips": len(clip_jobs), "stories": len(stories), "likes": 900, "liked_accounts": len(liked),
                      "saved": len(saved), "comments": len(comments), "followers": len(followers),
                      "following": len(following), "facebook_posts": len(fb_posts), "facebook_albums": len(albums),
                      "images": len(jobs), "set_photos": len(SETS), "friend": friends["summary"], "friend_feed": feed}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
