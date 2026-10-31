#!/usr/bin/env python3
"""Build one invented person's year on Instagram and Facebook, as the two "Download your information" exports,
plus a folder of the posts they liked.

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
    liked-posts/<account>_<n>.jpg            the media of posts they liked, saved from the app

The person has one consistent system, planted so a brand read can be checked against it:
  palette   every feed photo is led by one of four named colors at distinct proportions of the posts:
            terracotta 40%, cream 27%, olive 20%, chocolate 13% (the lead color covers more than half the frame)
  pillars   four subjects at clearly different shares: the table 45%, the market 25%, the streets 18%, coffee 12%
  voice     lowercase, three recurring devices: a short label and a colon to open ("market haul:"), a list of three
            ("figs, plums, quince."), and a blank line then a question to the reader; few emoji, one pillar hashtag
  cadence   three fixed weekdays and times (UTC): Tuesday 08:00, Thursday 12:30, Sunday 18:30
  likes     liked-posts/ holds liked media in a different, aspirational palette and subject: the sea and the coast in
            sea blue, ice blue, snow white and deep navy, from coastal accounts that also lead liked_posts.json
  outliers  five posts outside the system: loud colors, off-pillar subjects, a loud caption voice, off-cadence times
About 95 photo posts (some carousels), 20 reels, 60 stories, 900 likes, 70 saves, 200 comments, 412 followers.
Strings are written the way Meta writes them (UTF-8 bytes escaped as latin-1). Every picture is cut from the real
photographs in photos/ (SOURCES.md) and graded; about one in ten carries a .heic name over plain JPEG bytes. Needs Pillow and ffmpeg.
"""
import argparse
import datetime as dt
import json
import os
import random
import shutil
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path


HANDLE, NAME = "maren.okafor", "Maren Okafor"
# the four colors of their feed and the share of photo posts each one leads
PALETTE = {"terracotta": (200, 100, 70), "cream": (240, 228, 200), "olive": (120, 120, 60), "chocolate": (90, 60, 40)}
LEADS = {"terracotta": 0.40, "cream": 0.27, "olive": 0.20, "chocolate": 0.13}
# their four pillars and the share of posts and reels each one carries
PILLARS = {"table": 0.45, "market": 0.25, "streets": 0.18, "coffee": 0.12}
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
# the coast they like: the palette and the accounts of the posts they like and saves
SEA = {"sea blue": (40, 120, 170), "ice blue": (196, 214, 228), "snow white": (244, 244, 240), "deep navy": (28, 40, 80)}
ASPIRE = ["salt.and.sea", "coastal.quiet", "blue.hour.coast", "the.sea.edit", "linen.and.tide", "harbor.light.studio",
          "cliffside.mornings", "seaside.stills", "tidal.notes", "white.shore.studio", "north.coast.film", "open.water.days"]
OUTLIERS = [  # (caption, weekday, hour, minute, photograph): the five posts outside their system
    ("NEW KICKS!!! \U0001F525\U0001F525\U0001F525 link in bio", 5, 23, 40, "outlier-balloons"),
    ("Monday motivation!!! \U0001F4AA\U0001F4AA #grind #gymlife", 0, 6, 5, "outlier-tulips"),
    ("GUYS the concert last night was INSANE \U0001F92F\U0001F3A4", 5, 1, 20, "outlier-concert"),
    ("Rate my new desk setup 1-10?? \U0001F4BB✨ #setup", 4, 22, 10, "outlier-night"),
    ("SALE ends tonight!!! use code MAREN20 \U0001F6CD️", 2, 21, 50, "outlier-wedding"),
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


PHOTOS = Path(__file__).resolve().parent / "photos"
SHOTS = {  # kind -> the photographs a picture of that kind is made from (photos/SOURCES.md names each one)
    "p-table": ["table-loaf", "table-ramen", "table-tomatoes"],
    "p-market": ["market-greens", "market-spices", "market-bakery", "market-rugs"],
    "p-streets": ["streets-tram", "streets-alfama", "streets-bike", "streets-sintra", "streets-rooftops", "streets-cat"],
    "p-coffee": ["coffee-flat-white", "coffee-cappuccino", "coffee-cup"],
    "coast-beach": ["coast-tower", "coast-swim"],
    "coast-hills": ["coast-lake"],
}
GRADE = {"p": 0.8, "coast": 0.7, "outlier": 0.0}  # by the kind's first word: how far the grade pulls toward the lead


def graded(im, color, t):
    """Her preset: the photograph's light kept, its color pulled toward one color by t, the color landing on the
    photograph's middle tone."""
    from PIL import Image, ImageOps, ImageStat
    gray = im.convert("L")
    middle = min(200, max(50, int(ImageStat.Stat(gray).median[0])))
    dark = tuple(int(v * 0.22) for v in color)
    light = tuple(int(v + (255 - v) * 0.8) for v in color)
    return Image.blend(im, ImageOps.colorize(gray, dark, light, mid=color, midpoint=middle), t)


def picture(job):
    """job = (path, w, h, kind, palette, seed): one picture of the person's year, a photograph of its kind (or the
    photograph the kind names) cropped to w x h at a framing of its own, graded toward palette[0]. A .heic name still
    gets JPEG bytes."""
    from PIL import Image
    path, w, h, kind, pal, seed = job[:6]
    rng = random.Random(seed)
    im = Image.open(PHOTOS / f"{rng.choice(SHOTS.get(kind, [kind]))}.jpg").convert("RGB")
    scale = max(w / im.width, h / im.height) * rng.uniform(1.0, 1.18)
    im = im.resize((max(w, round(im.width * scale)), max(h, round(im.height * scale))), Image.LANCZOS)
    x, y = rng.randint(0, im.width - w), rng.randint(0, im.height - h)
    im = im.crop((x, y, x + w, y + h))
    t = GRADE[kind.split("-")[0]]
    if t:
        im = graded(im, pal[0], t)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=86)
    return path


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
                                             "personal brand, plus a folder of the posts they like.")
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

    # every Tuesday, Thursday and Sunday at their three times; a few skipped, about one in six a reel
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

    # the five posts outside their system: off-day, off-hour, loud colors, loud words
    outlier_days = []
    for k, (cap, wd, hour, minute, shot) in enumerate(OUTLIERS):
        day = dt.date(year, 2 + k * 2, 3)
        day += dt.timedelta(days=(wd - day.weekday()) % 7)
        ts = stamp(day, hour, minute, spread=4)
        uri = media_path("posts", ts, ".jpg")
        jobs.append((str(root / uri), 1080, 1350, shot, None, rng.random()))
        posts.append({"media": [{"uri": uri, "creation_timestamp": ts, "media_metadata": {"photo_metadata": {"exif_data": []}},
                                 "title": ig_text(cap), "cross_post_source": {"source_app": "FB"}}]})
        insights.append(insight(uri, ts, int(rng.lognormvariate(3.4, 0.3))))
        outlier_days.append(f"{day.isoformat()} {hour:02d}:{minute:02d}")
    rng.shuffle(posts)

    # four reel clips drawn in their system, the reels point at them
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

    # what they like: the coast. The coastal accounts take most of their likes and saves, and their posts sit in
    # liked-posts/ as the media they saved
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
            scene = "coast-beach" if rng.random() < 0.6 else "coast-hills"
            w, h = (1080, 1350) if rng.random() < 0.7 else (1080, 1080)
            jobs.append((str(likes_dir / f"{acct}_{n}.jpg"), w, h, scene, pal, rng.random()))

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

    # Facebook: a handful of posts in their voice and two albums in their palette
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
                "title": ig_text(f"{NAME} updated their status.")}
        if rng.random() < 0.6:
            uri = f"your_facebook_activity/posts/media/timeline/{10161000000000000 + i}.jpg"
            jobs.append((str(fb / uri), 1080, 1080, f"p-{pillar}", look(rng.choice(list(PALETTE))), rng.random()))
            post["attachments"] = [{"data": [{"media": {"uri": uri, "creation_timestamp": ts, "title": ""}}]}]
        fb_posts.append(post)
    write(fb, "your_facebook_activity/posts/your_posts__check_ins__photos_and_videos_1.json", fb_posts)
    write(fb, "personal_information/profile_information/profile_information.json",
          {"profile_v2": {"name": {"full_name": NAME}}})

    with Pool(max(2, os.cpu_count() or 2)) as pool:
        pool.map(picture, jobs, chunksize=4)
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
