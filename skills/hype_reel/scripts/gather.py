#!/usr/bin/env python3
"""Movement 0, gather: the subject (its name, what it is, its words, its pictures, and a date when it is a launch) and
every door to the person's own material, merged into library.json in a new run folder, build/<run stamp>/ under the
workspace root. Every later step works in that run.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/gather.py --subject "Rita Okafor" --kind friend --about rita/subject.md \
        [--date 2026-11-14] [--launch] [--assets DIR_OR_LINK] [--feed DIR ...] [--pulled pulled] \
        [--door instagram_account="open: 120 posts"] [--door browser="closed: no signed-in session"] \
        [--year 2026] [--photos DIR] [--root .]

The subject, in the person's own words (they win over anything inferred):
  --subject NAME   who or what the reel hypes: a product, a drop, an event, a friend, an idea, or a thing they
                   follow (an account, a creator, a band, a place, a repo, a page). --product is the same flag.
                   Without it the name comes from --about, else from the feed (the capitalized name its recent posts
                   repeat most), and the inference is listed as an assumption.
  --kind WORD      what the subject is, in one word (product, drop, event, friend, idea, account, creator, band, place,
                   repo, page, thing); from --about when it names one, else "product" for a launch and "thing" otherwise.
  --about FILE     a subject.md: "# Name", then "kind: friend", "handle: @rita.okafor", "date: 14 November" lines,
                   "- " facts (one true thing each, in the subject's or the person's own words), any plain sentences,
                   and a "## page" section holding text saved from the subject's page. With no --assets, the pictures
                   beside the file are the subject's pictures.
  --launch         the subject is a launch: the teaser stories and the countdown card are made. A date (--date, or a
                   date line in --about) makes it a launch too; with neither, only the reel, the feed post and the
                   share caption are made.
  --date TEXT      when: 2026-11-14, "November 14", "Nov 14 2026", "14/11"; a date with no year is the next one to
                   come. It is shown as written: "14 November" when the day leads, "November 14" when the month
                   does, the month's name written out. A date that cannot be read is kept and shown as written.
  --assets WHERE   a folder of subject stills and clips, or a link to the subject's page (its og:image and large
                   images are downloaded, at most 8). Without it: the folder holding --about, else a workspace folder
                   named like the subject, else the person's own posts that mention the subject.
Stills are linked into library/subject/stills/ under their own names, clips into library/subject/footage/; the
asset folder never counts as the person's photo folder. A still's words (its caption in a manifest.json beside it, or
a .txt of the same name) are kept by its linked path in the subject's "said", the line the film may show on it.

The feed, the photographs the storyboards cast from:
  --feed DIR       a folder of the person's own photographs (repeatable). Each photograph's words are the "caption"
                   of its entry in a manifest.json beside it ({"items": [{"file", "caption", "title", "description"}]}:
                   the caption is what the person wrote with it, the title and description what it shows), else a .txt
                   file of the same name; its date is the one its EXIF carries, else none. Without --feed the feed is
                   the photographs of the person's posts, with each post's caption and day.
library.json "settings" names what the storyboards read: feed_photos (the feed folders) and subject_assets (the subject
folder as linked here); "feed" lists every feed photograph with its caption (everything said of it: the person's words,
then what it shows), its words (the person's own words alone, "" when they wrote none) and its date.

Doors, in order of preference (every one tried is recorded in library.json and in out/brief.md):
  1. Material the agent pulled itself from the person's connected Instagram or Facebook account or a signed-in
     browser session, saved under --pulled DIR as items.json (shape below) with the media files beside it.
  2. Instagram "Download your information" exports (JSON) anywhere under --root, as folders or .zip files (a zip is
     unpacked into the run's export/): posts, reels, stories, likes, saves, comments, followers, following, per-post
     and per-reel likes and comments (past_instagram_insights), the username. Missing files are tolerated.
  3. Facebook "Download your information" exports under --root: posts, photos, albums.
  4. --photos DIR, else the largest folder of photos under --root (dates from EXIF, else the file time).
With every door closed it writes out/brief.md with the one sentence on how to open one and exits 3: tell the
person that sentence and stop. With no picture of the subject anywhere (no asset folder or link, no post that mentions
it) it prints "not delivered: " and one sentence naming what is missing, and exits 2: tell the person that sentence
and stop. Meta's text encoding (UTF-8 written as latin-1) is repaired everywhere.

items.json (every key optional; ts is a unix timestamp; media are paths relative to items.json):
  {"source": "instagram account", "handle": "...", "name": "...",
   "posts": [{"ts": 0, "caption": "", "media": ["a.jpg"], "likes": 0, "comments": 0, "place": ""}],
   "reels": [...same...], "stories": [{"ts": 0, "media": ["s.jpg"]}],
   "likes": [{"account": "", "ts": 0, "caption": "", "media": ["liked.jpg"]}], "saved": [...same as likes...],
   "comments": [{"account": "", "text": "", "ts": 0}], "followers": [{"account": "", "ts": 0}],
   "following": [{"account": "", "ts": 0}], "facebook": [{"ts": 0, "caption": "", "media": [], "album": ""}]}

The window: the 365 days ending at the latest post (or the calendar year given with --year). Links every media file
of the window into library/<kind>/ (posts, reels, stories, likes, saved, facebook) under its date, writes
library.json (with a "subject" block) and prints a summary; every choice it made is listed under "assumptions".
"""
import argparse
import datetime as dt
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

SKIP = {"out", "build", ".claude", ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "custom-skills"}
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VID = {".mp4", ".mov", ".m4v"}
HOWTO = ("To make your hype reel I need some pictures of what it is about: connect your Instagram account here, or put a "
         "folder of photos of it in this workspace, or in the Instagram app go to Your activity, then Download your "
         "information, choose JSON, and put the folder or zip it sends you here.")
KINDS = ("product", "drop", "event", "friend", "idea", "account", "creator", "band", "place", "repo", "page", "thing")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]


def fix(s):
    if not isinstance(s, str):
        return ""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def walk(root, depth=6):
    stack = [(Path(root), 0)]
    while stack:
        d, n = stack.pop()
        try:
            kids = list(d.iterdir())
        except OSError:
            continue
        yield d, kids
        if n < depth:
            stack += [(k, n + 1) for k in kids if k.is_dir() and k.name not in SKIP and not k.name.startswith(".")]


def is_export(d):
    return (d / "your_instagram_activity").is_dir() or (d / "content" / "posts_1.json").is_file()


def find_exports(root, test=None):
    test = test or is_export
    found, zips = [], []
    for d, kids in walk(root):
        if test(d):
            found.append(d)
        zips += [k for k in kids if k.suffix.lower() == ".zip" and k.is_file()]
    for z in zips:
        try:
            names = zipfile.ZipFile(z).namelist()
        except (zipfile.BadZipFile, OSError):
            continue
        if test is is_export and any("your_instagram_activity/" in n or n.endswith("content/posts_1.json") for n in names) or \
                test is is_fb_export and any("your_facebook_activity/" in n for n in names):
            dest = Path("export") / z.stem
            if not dest.exists():
                zipfile.ZipFile(z).extractall(dest)
            for d, _ in walk(dest, 3):
                if test(d):
                    found.append(d)
                    break
    return [d for d in found if not any(o != d and o in d.parents for o in found)]


def act_dir(root):
    return root / "your_instagram_activity" if (root / "your_instagram_activity").is_dir() else root


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def first(root, *rels):
    for r in rels:
        for base in (act_dir(root), root):
            hits = sorted(base.glob(r))
            if hits:
                return hits
    return []


class Media:
    def __init__(self, root):
        self.root = root
        self.by_name = None

    def resolve(self, uri):
        if not uri or re.match(r"^https?://", uri):
            return None
        p = self.root / uri
        if p.exists():
            return str(p.resolve())
        if self.by_name is None:
            self.by_name = unique_names(f for f in (self.root / "media").rglob("*") if f.is_file()) if (self.root / "media").exists() else {}
        f = self.by_name.get(Path(uri).name)
        return str(f.resolve()) if f else None


def unique_names(paths):
    """Each path under its file name, for the names exactly one path carries: a name two folders share names nothing."""
    seen = {}
    for f in paths:
        seen.setdefault(Path(f).name, []).append(f)
    return {n: fs[0] for n, fs in seen.items() if len(fs) == 1}


def media_items(entry):
    """Flatten Instagram's media shapes into [(uri, ts, title)]."""
    if not isinstance(entry, dict):
        return []
    items = entry.get("media") if isinstance(entry.get("media"), list) else [entry]
    out = []
    for m in items:
        if isinstance(m, dict) and m.get("uri"):
            out.append((m["uri"], m.get("creation_timestamp") or entry.get("creation_timestamp"), m.get("title") or ""))
    return out


def read_export(root):
    md = Media(root)
    found, notes = {}, []
    posts = []
    files = first(root, "content/posts_*.json", "media/posts_*.json")
    found["posts"] = [str(f) for f in files]
    insights, insights_ts = {}, {}
    for f in first(root, "../logged_information/past_instagram_insights/*.json", "logged_information/past_instagram_insights/*.json",
                   "past_instagram_insights/*.json"):
        data = load(f) or {}
        tables = [v for v in data.values() if isinstance(v, list)] if isinstance(data, dict) else []
        for row in (r for t in tables for r in t if isinstance(r, dict)):
            thumb = ((row.get("media_map_data") or {}).get("Media Thumbnail") or {})
            smd = row.get("string_map_data") or {}

            def num(word):
                """The first count whose label names the word (Likes, Instagram media like count, Comments ...)."""
                for k, v in smd.items():
                    if word in k.lower() and "un" + word not in k.lower():
                        try:
                            return int(re.sub(r"[^\d]", "", str((v or {}).get("value", ""))) or 0)
                        except ValueError:
                            return None
                return None
            rec = {"likes": num("like"), "comments": num("comment"), "saves": num("save")}
            if thumb.get("uri"):
                insights.setdefault(Path(thumb["uri"]).name, rec)
            if thumb.get("creation_timestamp"):
                insights_ts[int(thumb["creation_timestamp"])] = rec
        found.setdefault("insights", []).append(str(f))
    for f in files:
        data = load(f) or []
        for e in data if isinstance(data, list) else []:
            items = media_items(e)
            if not items:
                continue
            ts = e.get("creation_timestamp") or items[0][1]
            cap = fix(e.get("title") or items[0][2])
            paths = [md.resolve(u) for u, _, _ in items]
            ins = insights_ts.get(int(ts or 0)) or next((insights[Path(u).name] for u, _, _ in items if Path(u).name in insights), {})
            posts.append({"ts": ts, "caption": cap, "media": [p for p in paths if p],
                          "likes": ins.get("likes"), "comments": ins.get("comments"), "saves": ins.get("saves")})
    reels = []
    rf = first(root, "content/reels.json")
    found["reels"] = [str(f) for f in rf]
    for f in rf:
        data = load(f) or {}
        rows = data.get("ig_reels_media", []) if isinstance(data, dict) else data
        for e in rows or []:
            items = media_items(e)
            if items:
                ts = items[0][1]
                ins = insights_ts.get(int(ts or 0)) or {}
                reels.append({"ts": ts, "caption": fix(items[0][2]), "media": [p for p in (md.resolve(u) for u, _, _ in items) if p],
                              "likes": ins.get("likes"), "comments": ins.get("comments"), "saves": ins.get("saves")})
    stories = []
    sf = first(root, "content/stories.json")
    found["stories"] = [str(f) for f in sf]
    for f in sf:
        data = load(f) or {}
        rows = data.get("ig_stories", []) if isinstance(data, dict) else data
        for e in rows or []:
            for u, ts, t in media_items(e):
                stories.append({"ts": ts, "media": [p for p in [md.resolve(u)] if p]})
    likes = []
    lf = first(root, "likes/liked_posts.json")
    found["likes"] = [str(f) for f in lf]
    for f in lf:
        data = load(f) or {}
        rows = data.get("likes_media_likes", []) if isinstance(data, dict) else data
        for e in rows or []:
            acct = fix(e.get("title") or "")
            for s in e.get("string_list_data") or []:
                likes.append({"account": acct or fix(s.get("value", "")), "ts": s.get("timestamp")})
            if not e.get("string_list_data") and e.get("timestamp"):
                likes.append({"account": acct, "ts": e.get("timestamp")})
    comments = []
    cf = first(root, "comments/post_comments_*.json")
    found["comments"] = [str(f) for f in cf]
    for f in cf:
        data = load(f) or []
        rows = data.get("comments_media_comments", []) if isinstance(data, dict) else data
        for e in rows or []:
            smd = e.get("string_map_data") or {}
            comments.append({"account": fix((smd.get("Media Owner") or {}).get("value", "")),
                             "text": fix((smd.get("Comment") or {}).get("value", "")),
                             "ts": (smd.get("Time") or {}).get("timestamp")})
    followers = []
    ff = first(root, "../connections/followers_and_following/followers_*.json", "connections/followers_and_following/followers_*.json",
               "followers_and_following/followers_*.json")
    found["followers"] = [str(f) for f in ff]
    for f in ff:
        data = load(f) or []
        rows = data.get("relationships_followers", []) if isinstance(data, dict) else data
        for e in rows or []:
            for s in e.get("string_list_data") or []:
                followers.append({"account": fix(s.get("value", "")), "ts": s.get("timestamp")})
    saved = []
    svf = first(root, "saved/saved_posts.json")
    found["saved"] = [str(f) for f in svf]
    for f in svf:
        data = load(f) or {}
        for e in (data.get("saved_saved_media", []) if isinstance(data, dict) else data) or []:
            smd = e.get("string_map_data") or {}
            saved.append({"account": fix(e.get("title") or ""), "ts": (smd.get("Saved on") or {}).get("timestamp")})
    following = []
    fwf = first(root, "../connections/followers_and_following/following.json", "connections/followers_and_following/following.json")
    found["following"] = [str(f) for f in fwf]
    for f in fwf:
        data = load(f) or {}
        for e in (data.get("relationships_following", []) if isinstance(data, dict) else data) or []:
            for s_ in e.get("string_list_data") or [{}]:
                acct = fix(e.get("title") or s_.get("value") or "")
                if acct:
                    following.append({"account": acct, "ts": s_.get("timestamp")})
    handle, name = None, None
    for f in first(root, "../personal_information/personal_information/personal_information.json",
                   "personal_information/personal_information/personal_information.json", "account_information/personal_information.json"):
        data = load(f) or {}
        for u in data.get("profile_user", []) if isinstance(data, dict) else []:
            smd = u.get("string_map_data") or {}
            handle = handle or fix((smd.get("Username") or {}).get("value", "")) or None
            name = name or fix((smd.get("Name") or {}).get("value", "")) or None
    if not handle:
        m = re.match(r"instagram-([A-Za-z0-9._]+?)-\d{4}-\d{2}-\d{2}", root.name)
        if m:
            handle = m.group(1)
            notes.append(f"Username taken from the export's folder name ({root.name}).")
    return {"posts": posts, "reels": reels, "stories": stories, "likes": likes, "comments": comments,
            "followers": followers, "saved": saved, "following": following, "handle": handle, "name": name,
            "found": found, "notes": notes}


def is_fb_export(d):
    return (d / "your_facebook_activity").is_dir()


def read_facebook(root):
    """Facebook posts with their photos, and album photos, as [{ts, caption, media, album}]."""
    act = root / "your_facebook_activity" / "posts"
    rows = []
    for f in sorted(act.glob("your_posts*.json")):
        for e in load(f) or []:
            if not isinstance(e, dict):
                continue
            text = " ".join(fix(x.get("post", "")) for x in e.get("data") or [] if isinstance(x, dict)).strip()
            media = []
            for att in e.get("attachments") or []:
                for x in att.get("data") or []:
                    uri = ((x or {}).get("media") or {}).get("uri")
                    if uri and (root / uri).exists():
                        media.append(str((root / uri).resolve()))
            rows.append({"ts": e.get("timestamp"), "caption": text, "media": media, "album": ""})
    for f in sorted((act / "album").glob("*.json")):
        a = load(f) or {}
        for ph in a.get("photos") or []:
            uri = ph.get("uri")
            if uri and (root / uri).exists():
                rows.append({"ts": ph.get("creation_timestamp"), "caption": fix(ph.get("title") or ""),
                             "media": [str((root / uri).resolve())], "album": fix(a.get("name") or "")})
    return rows


def read_pulled(folder):
    """Material the agent pulled from a connected account or a browser session (items.json, shape in the usage)."""
    f = Path(folder) / "items.json"
    data = load(f)
    if not isinstance(data, dict):
        return None
    base = f.parent

    def media(row):
        out = []
        for m in row.get("media") or []:
            p = (base / m) if not Path(m).is_absolute() else Path(m)
            if p.exists():
                out.append(str(p.resolve()))
        return dict(row, media=out)
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [media(r) if isinstance(r, dict) else r for r in data.get(k) or []] for k in keys}
    d.update(handle=data.get("handle"), name=data.get("name"), source=data.get("source") or "connected account",
             found={k: [str(f)] for k in keys if d[k]})
    return d


def photo_date(p):
    try:
        from PIL import Image
        ex = Image.open(p).getexif()
        v = ex.get(36867) or ex.get(306) or (ex.get_ifd(0x8769) or {}).get(36867)
        if v:
            return int(dt.datetime.strptime(str(v)[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
    except Exception:
        pass
    return int(Path(p).stat().st_mtime)


def read_photos(folder):
    files = sorted(f for f in Path(folder).rglob("*") if f.suffix.lower() in IMG and f.is_file())
    posts = [{"ts": photo_date(f), "caption": "", "media": [str(f.resolve())], "likes": None, "comments": None} for f in files]
    vids = [{"ts": int(f.stat().st_mtime), "caption": "", "media": [str(f.resolve())]}
            for f in sorted(Path(folder).rglob("*")) if f.suffix.lower() in VID]
    return posts, vids


def largest_photo_folder(root, skip=None):
    best = (0, None)
    for d, kids in walk(root):
        if skip and (d == skip or skip in d.parents):
            continue
        n = sum(1 for k in kids if k.suffix.lower() in IMG)
        if n > best[0]:
            best = (n, d)
    return best[1] if best[0] >= 8 else None


def year_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).year


def pick_window(rows, asked):
    """(first ts, last ts, the end year, why): a named calendar year, else the 365 days ending at the latest post."""
    if asked:
        lo = dt.datetime(asked, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        hi = dt.datetime(asked + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp() - 1
        return lo, hi, asked, f"The window is {asked}, as asked."
    stamps = [int(r["ts"]) for r in rows if r.get("ts")]
    if not stamps:
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        return now - 365 * 86400, now, dt.date.today().year, "No dates in the data; used the last 365 days."
    hi = max(stamps)
    end = dt.datetime.fromtimestamp(hi, dt.timezone.utc).date()
    return hi - 365 * 86400, hi, end.year, f"The window is the 365 days up to the latest post ({end.isoformat()})."


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def next_day(today, d):
    """The next calendar day numbered `d` from `today` on: this month's when it is still ahead, else the next month that
    has one."""
    y, m = today.year, today.month
    for _ in range(13):
        try:
            when = dt.date(y, m, d)
        except ValueError:
            when = None
        if when and when >= today:
            return when
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return None


def names_month(text):
    """Whether a date as written names its month: a month's name, or two numbers (11/14, 2026-11-14)."""
    low = (text or "").lower()
    named = any(n.startswith(w) for w in re.findall(r"[a-z]{3,}", low) for n in MONTHS)
    return named or len(re.findall(r"\d+", low)) >= 2


def parse_date(text, today=None):
    """(iso or None, label): ISO, 'November 14', 'Nov 14 2026', '14 Nov', '11/14', '14/11/2026'; no year means the next one.
    A day with no month ('the 14th') is the next day of that number, and a weekday ('friday') the next one after today.
    The label is the day and the month's name written out, in the order the text gives them: '14 November' when the day
    leads, 'November 14' when the month leads (and for ISO)."""
    today = today or dt.date.today()
    t = (text or "").strip()
    if not t:
        return None, ""
    low = t.lower().replace(",", " ")
    y = m = d = None
    day_first = False
    words = re.findall(r"[a-z]+", low)
    short = [x[:3] for x in WEEKDAYS]
    week = next((short.index(w[:3]) for w in words if w in WEEKDAYS or len(w) == 3 and w in short), None)
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", low):
        y, m, d = (int(x) for x in re.findall(r"\d+", low)[:3])
    else:
        month_of = lambda w: next((i + 1 for i, n in enumerate(MONTHS) if len(w) >= 3 and n.startswith(w)), None)
        mon = next((month_of(w) for w in re.findall(r"[a-z]+", low) if month_of(w)), None)
        nums = [int(x) for x in re.findall(r"\d+", low)]
        yrs = [n for n in nums if n > 31]
        days = [n for n in nums if n <= 31]
        if mon and days:
            m, d, y = mon, days[0], (yrs[0] if yrs else None)
            lead = next(w for w in re.findall(r"[a-z]+|\d+", low) if w.isdigit() and int(w) <= 31 or month_of(w))
            day_first = lead.isdigit()
        elif len(days) >= 2:
            a, b = days[0], days[1]
            m, d = (a, b) if a <= 12 and (b > 12 or "/" in low and not low.startswith(str(b))) else (b, a)
            day_first = d == a != b
            y = yrs[0] if yrs else (days[2] + 2000 if len(days) > 2 and days[2] < 100 else None)
        elif len(days) == 1 and not yrs and not mon:
            when = next_day(today, days[0])
            if when:
                return when.isoformat(), f"{when.day} {MONTHS[when.month - 1].capitalize()}"
        elif week is not None and not nums:
            when = today + dt.timedelta(days=(week - today.weekday() - 1) % 7 + 1)
            return when.isoformat(), f"{MONTHS[when.month - 1].capitalize()} {when.day}"
    try:
        if y is None:
            when = dt.date(today.year, m, d)
            when = when if when >= today else dt.date(today.year + 1, m, d)
        else:
            when = dt.date(y, m, d)
    except (TypeError, ValueError):
        return None, t
    month = MONTHS[when.month - 1].capitalize()
    return when.isoformat(), f"{when.day} {month}" if day_first else f"{month} {when.day}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def mentions(text, subject):
    """Whether a caption names the subject (spacing, hyphens and case ignored)."""
    return bool(subject) and slug(subject) in slug(text)


def infer_subject(rows):
    """The capitalized name the latest posts repeat most (two words or one), or None."""
    counts = {}
    for r in sorted(rows, key=lambda r: -(r.get("ts") or 0))[:60]:
        for name in re.findall(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?)\b", r.get("caption") or ""):
            counts[name] = counts.get(name, 0) + 1
    best = max(counts.items(), key=lambda kv: (kv[1], len(kv[0])), default=(None, 0))
    return best[0] if best[1] >= 2 else None


def fetch_link(url, dest, limit=8):
    """Download the page's og:image and its large images into dest; returns (paths, note)."""
    dest.mkdir(parents=True, exist_ok=True)
    hdr = {"User-Agent": "Mozilla/5.0 (hype-reel)"}
    try:
        html = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=15).read(3_000_000).decode("utf-8", "replace")
    except Exception as e:
        return [], f"The link {url} did not open ({type(e).__name__})."
    srcs = re.findall(r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)', html, re.I)
    srcs += re.findall(r'<img[^>]+src=["\']([^"\']+)', html, re.I)
    got, seen = [], set()
    for src in srcs:
        u = urllib.parse.urljoin(url, src)
        if u in seen or u.startswith("data:") or re.search(r"\.(svg|gif)(\?|$)", u, re.I):
            continue
        seen.add(u)
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers=hdr), timeout=15).read(20_000_000)
        except Exception:
            continue
        if len(data) < 20_000:
            continue
        ext = Path(urllib.parse.urlparse(u).path).suffix.lower()
        f = dest / f"link-{len(got) + 1:02d}{ext if ext in IMG else '.jpg'}"
        f.write_bytes(data)
        got.append(f)
        if len(got) >= limit:
            break
    return got, (f"Downloaded {len(got)} images from {url}." if got else f"The link {url} had no large images.")


def find_asset_folder(root, subject):
    """A workspace folder whose name carries the subject's name and that holds images or clips."""
    key = slug(subject)
    best = None
    for d, kids in walk(root):
        if d == root or not key or key not in slug(d.name):
            continue
        n = sum(1 for k in kids if k.suffix.lower() in IMG | VID)
        if n and (best is None or n > best[0]):
            best = (n, d)
    return best[1] if best else None


def read_about(path):
    """A subject.md as {name, kind, handle, date, facts, about, page}: the "# " heading is the name, "key: value" lines
    the kind, handle and date, "- " lines the facts, other lines the sentences about it, and the "## page" section the
    text saved from its page. A file with no facts takes its sentences, then its page's first sentences, as facts."""
    out = {"name": "", "kind": "", "handle": "", "date": "", "facts": [], "about": [], "page": ""}
    if not path:
        return out
    page, in_page = [], False
    for ln in Path(path).read_text(errors="replace").splitlines():
        t = ln.strip()
        if re.match(r"^##\s+page\b", t, re.I):
            in_page = True
            continue
        if in_page:
            page.append(t)
            continue
        m = re.match(r"^#\s+(.+)$", t)
        kv = re.match(r"^(kind|handle|date)\s*:\s*(.+)$", t, re.I)
        if m and not out["name"]:
            out["name"] = m.group(1).strip()
        elif kv:
            out[kv.group(1).lower()] = kv.group(2).strip()
        elif t.startswith(("- ", "* ")):
            out["facts"].append(t[2:].strip())
        elif t and not t.startswith("#"):
            out["about"].append(t)
    out["page"] = "\n".join(page).strip()
    sentences = lambda text: [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if len(x.split()) >= 3]
    if not out["facts"]:
        out["facts"] = sentences(" ".join(out["about"]))[:4] or sentences(" ".join(page))[:4]
    if out["handle"] and not out["handle"].startswith("@"):
        out["handle"] = "@" + out["handle"]
    return out


def still_words(files):
    """Each picture's own words, by its file: the caption of its manifest.json entry, else a .txt of the same name."""
    out, manifests = {}, {}
    for f in files:
        folder = Path(f).parent
        if folder not in manifests:
            m = folder / "manifest.json"
            items = (load(m) or {}).get("items", []) if m.is_file() else []
            manifests[folder] = manifest_of(folder, items)
        _, words, _ = caption_of(Path(f), manifests[folder])
        if words:
            out[str(f)] = words
    return out


def subject_block(a, root, lib, assumptions):
    """The subject: its name, kind, words, its date when it is a launch, and its own pictures, linked under
    library/subject/."""
    rows = lib["posts"] + lib["reels"]
    about = read_about(a.about)
    subject = (a.subject or about["name"] or "").strip()
    if not subject:
        subject = infer_subject(rows) or ""
        assumptions.append(f"No subject name was given; the feed's most repeated name is {subject!r}." if subject
                           else "No subject name was given and the feed names none; the film says 'something new'.")
    when = a.date or about["date"] or None
    launch = bool(when or a.launch)
    iso, label = parse_date(when)
    if when and not iso:
        assumptions.append(f"The date {when!r} could not be read as a calendar day; it is shown as written.")
    elif when and not names_month(when):
        assumptions.append(f"The date {when!r} names no month; it is read as the next one, {label} {iso[:4]}.")
    elif launch:
        assumptions.append("It is a launch with no date given; the countdown card says 'soon'.")
    else:
        assumptions.append("No date and no launch, so the reel, the feed post and the share caption are made, no "
                           "teaser stories and no countdown.")
    kinds = (a.kind or about["kind"] or ("product" if launch else "thing")).strip().lower()
    days = (dt.date.fromisoformat(iso) - dt.date.today()).days if iso else None
    base = Path("library/subject").resolve()
    if base.exists():
        shutil.rmtree(base)
    stills_dir, footage_dir = base / "stills", base / "footage"
    stills_dir.mkdir(parents=True)
    footage_dir.mkdir(parents=True)
    kind, where, notes, files = None, None, [], []
    if a.assets and re.match(r"^https?://", a.assets):
        files, note = fetch_link(a.assets, base / "link")
        notes.append(note)
        kind, where = ("link", a.assets) if files else (None, None)
    elif a.assets:
        folder = Path(a.assets) if Path(a.assets).is_absolute() else root / a.assets
        if folder.is_dir():
            kind, where = "folder", folder
        else:
            notes.append(f"The asset folder {a.assets} is not there.")
    if not kind and a.about:
        kind, where = "folder", Path(a.about).resolve().parent
    if not kind:
        folder = find_asset_folder(root, subject)
        if folder:
            kind, where = "folder", folder
            notes.append(f"No assets were named; used {rel(folder, root)}, the folder named like the subject.")
    if kind == "folder":
        files = sorted(f for f in where.rglob("*") if f.is_file() and f.suffix.lower() in IMG | VID)
    feed = [r for r in rows if mentions(r.get("caption"), subject)]
    if not files and feed:
        kind, where = "feed", None
        files = [Path(m) for r in sorted(feed, key=lambda r: -(r.get("ts") or 0)) for m in r.get("media") or []
                 if Path(m).suffix.lower() in IMG][:12]
        notes.append(f"No subject folder or link; the subject's pictures are the {len(feed)} posts that mention {subject}.")
    stills, footage, said = [], [], {}
    words = still_words(files) if kind == "folder" else {}
    for f in files:
        vid = f.suffix.lower() in VID
        dst = (footage_dir if vid else stills_dir) / f"{len(footage if vid else stills) + 1:02d}-{Path(f).stem[:60]}{f.suffix.lower()}"
        try:
            dst.symlink_to(Path(f).resolve())
        except OSError:
            shutil.copy2(f, dst)
        (footage if vid else stills).append(str(dst))
        if str(f) in words:
            said[str(dst)] = words[str(f)]
    if not files:
        notes.append("No subject pictures anywhere: no asset folder or link, and no post that mentions the subject.")
    assumptions += notes
    return {"name": subject, "kind": kinds, "handle": about["handle"], "launch": launch, "facts": about["facts"],
            "about": " ".join(about["about"]), "page": about["page"], "said": said,
            "date": iso, "date_text": when or "", "date_label": (label or when or "soon") if launch else "",
            "days_to_go": days, "assets": str(where) if where else None, "assets_kind": kind or "none",
            "stills": stills, "footage": footage, "feed_posts": len(feed), "notes": notes}


def write_howto(out):
    out.mkdir(exist_ok=True)
    (out / "brief.md").write_text(f"# Hype reel: no material found\n\n## Assumptions\n\n- No Instagram export, subject "
                                  f"folder or folder of photos was found in this workspace.\n\n## What to do\n\n{HOWTO}\n")


def merge(base, extra):
    """Rows from a lower door join the library when no row with the same time and caption is already there."""
    seen = {(r.get("ts"), (r.get("caption") or "")[:40]) for r in base}
    return base + [r for r in extra if (r.get("ts"), (r.get("caption") or "")[:40]) not in seen]


def rel(p, root):
    p = Path(p)
    return p.relative_to(root) if p.is_relative_to(root) else p


def shelve(lib):
    """Every media file of the year, linked into library/<kind>/ under its date; the rows point at the links."""
    base = Path("library").resolve()
    for kind in ("posts", "reels", "stories", "likes", "saved", "facebook"):
        for n, row in enumerate(lib[kind]):
            media = []
            for i, m in enumerate(row.get("media") or []):
                src = Path(m)
                if not src.is_file() or base in src.resolve().parents:
                    media.append(m)
                    continue
                day = dt.datetime.fromtimestamp(row["ts"], dt.timezone.utc).date().isoformat()
                dst = base / kind / f"{day}-{n:03d}-{i}{src.suffix.lower()}"
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    try:
                        dst.symlink_to(src.resolve())
                    except OSError:
                        shutil.copy2(src, dst)
                media.append(str(dst))
            row["media"] = media


def manifest_of(folder, items):
    """A folder's manifest entries, each under the exact path its `file` names."""
    return {(folder / i["file"]).resolve(): i for i in items if isinstance(i, dict) and i.get("file")}


def caption_of(f, manifest):
    """Everything said of a photograph, the person's own words among it, and where it came from: its manifest entry by
    its exact path (the caption they wrote, then its title and description), a .txt beside it (their words), else its
    file name."""
    m = manifest.get(Path(f).resolve())
    if m:
        words = (m.get("caption") or "").strip()
        return " ".join(x for x in (words, m.get("title"), m.get("description")) if x).strip(), words, "manifest"
    t = f.with_suffix(".txt")
    if t.is_file():
        words = t.read_text(errors="replace").strip()
        return words, words, "text file"
    return re.sub(r"[-_]+", " ", re.sub(r"^\d+[-_]", "", f.stem)).strip(), "", "file name"


def exif_day(f):
    try:
        from PIL import Image
        ex = Image.open(f).getexif()
        v = ex.get(36867) or ex.get(306) or (ex.get_ifd(0x8769) or {}).get(36867)
        return dt.datetime.strptime(str(v)[:10], "%Y:%m:%d").date().isoformat() if v else None
    except Exception:
        return None


def read_feed(folders, assumptions):
    """Every photograph in the --feed folders, linked into library/feed/ under its row's number, with its caption and
    the day it carries."""
    _env.need("PIL")
    base = Path("library/feed").resolve()
    base.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in folders:
        folder = Path(folder)
        if not folder.is_dir():
            assumptions.append(f"The feed folder {folder} is not there.")
            continue
        try:
            items = json.loads((folder / "manifest.json").read_text()).get("items") or []
        except (OSError, ValueError, AttributeError):
            items = []
        manifest = manifest_of(folder, items)
        for f in sorted(x for x in folder.iterdir() if x.is_file() and x.suffix.lower() in IMG):
            caption, words, said = caption_of(f, manifest)
            dst = base / f"{len(rows):03d}-{f.name}"
            if dst.resolve() != f.resolve():
                dst.unlink(missing_ok=True)
                try:
                    dst.symlink_to(f.resolve())
                except OSError:
                    shutil.copy2(f, dst)
            day = exif_day(f)
            rows.append({"file": str(dst), "source": str(f.resolve()), "caption": caption, "words": words, "caption_from": said,
                         "date": day, "date_from": "exif" if day else None})
    assumptions.append(f"The feed is the {len(rows)} photographs in " + ", ".join(str(Path(x).name) for x in folders) +
                       "; a photograph's date is the one its EXIF carries, never its file time.")
    return rows


def post_feed(lib):
    """The feed from the posts: every photograph of a post, with the post's caption and day."""
    rows = []
    for r in lib["posts"]:
        day = dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).date().isoformat() if r.get("ts") else None
        for m in r.get("media") or []:
            if Path(m).suffix.lower() in IMG and Path(m).exists():
                rows.append({"file": m, "source": m, "caption": r.get("caption") or "", "words": r.get("caption") or "", "caption_from": "post",
                             "date": day, "date_from": "post" if day else None, "likes": r.get("likes")})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--year", type=int, help="a calendar year the person named instead of the last 365 days")
    ap.add_argument("--subject", "--product", dest="subject", help="who or what the reel hypes, in the person's words")
    ap.add_argument("--kind", help=f"what the subject is: {', '.join(KINDS)}")
    ap.add_argument("--about", help="a subject.md with the subject's name, kind, handle, facts and saved page text")
    ap.add_argument("--launch", action="store_true", help="the subject is a launch: make the teaser stories and countdown")
    ap.add_argument("--date", help="when it launches, as the person wrote it")
    ap.add_argument("--assets", help="a folder or link with the subject's photos and clips")
    ap.add_argument("--photos", help="a folder of photos the person named")
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--door", action="append", default=[], help='name="open: ..." or name="closed: why"')
    ap.add_argument("--feed", action="append", default=[], help="a folder of the person's own photographs to cast from")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    here = Path.cwd()
    absolute = lambda x: str(Path(x) if Path(x).is_absolute() else (here / x).resolve())
    a.photos = absolute(a.photos) if a.photos else None
    a.feed = [absolute(x) for x in a.feed]
    a.pulled = [absolute(x) for x in a.pulled]
    a.about = absolute(a.about) if a.about else None
    if a.assets and not re.match(r"^https?://", a.assets) and not Path(a.assets).is_absolute():
        a.assets = str(root / a.assets) if (root / a.assets).exists() else absolute(a.assets)
    run = _env.enter_run(new=True)
    print(f"run: {run}")
    Path("library").mkdir(parents=True, exist_ok=True)
    assumptions, doors = [], {}
    for x in a.door:
        k, _, v = x.partition("=")
        doors[k.strip()] = v.strip() or "tried"
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [] for k in keys}
    d.update(handle=None, name=None, found={}, notes=[])
    sources = []
    pulled = a.pulled or ([str(root / "pulled")] if (root / "pulled" / "items.json").exists() else [])
    for folder in pulled:
        p = read_pulled(folder)
        if not p:
            doors[f"pulled:{folder}"] = "closed: no readable items.json"
            continue
        for k in keys:
            d[k] = merge(d[k], p[k])
        d["handle"], d["name"] = d["handle"] or p["handle"], d["name"] or p["name"]
        d["found"].update(p["found"])
        sources.append(p["source"])
        doors.setdefault(p["source"], f"open: {len(p['posts'])} posts, {len(p['likes'])} likes pulled")
    exports = [] if a.photos else find_exports(root)
    if exports:
        reads = [(e, read_export(e)) for e in exports]
        export, x = max(reads, key=lambda r: max([0] + [int(p["ts"] or 0) for p in r[1]["posts"]]))
        if len(exports) > 1:
            assumptions.append(f"Found {len(exports)} Instagram downloads; used the newest, {export.name}.")
        for k in keys:
            if k in x:
                d[k] = merge(d[k], x[k])
        d["handle"], d["name"] = d["handle"] or x["handle"], d["name"] or x["name"]
        for k, v in x["found"].items():
            d["found"].setdefault(k, v)
        d["notes"] += x["notes"]
        sources.append("instagram download")
        doors["instagram_download"] = f"open: {rel(export, root)}"
    else:
        doors.setdefault("instagram_download", "closed: none under the workspace")
    fbs = [] if a.photos else find_exports(root, is_fb_export)
    opened = []
    for f in fbs:
        rows = read_facebook(f)
        d["facebook"] = merge(d["facebook"], rows)
        opened.append(f"{rel(f, root)} ({len(rows)} posts and photos)")
        d["found"]["facebook"] = [str(f)]
    if opened:
        doors["facebook_download"] = "open: " + ", ".join(opened)
    else:
        doors.setdefault("facebook_download", "closed: none under the workspace")
    source = ("accounts" if sources and sources[0] != "instagram download" else "export") if sources else None
    if not d["posts"] and not d["reels"]:
        _env.need("PIL")
        skip = (root / a.assets).resolve() if a.assets and not re.match(r"^https?://", a.assets) else \
            Path(a.about).resolve().parent if a.about else None
        folder = Path(a.photos) if a.photos else largest_photo_folder(root, skip)
        if folder:
            posts, vids = read_photos(folder)
            d["posts"], d["reels"] = posts, vids
            d["found"]["photos"] = str(folder)
            source = "photos"
            doors["photo_folder"] = f"open: {len(posts)} photos in {rel(folder, root)}"
            assumptions.append(f"No Instagram account or download was reachable, so the film is made from the {len(posts)} "
                               f"photos in {rel(folder, root)}. Likes, comments and followers need the account or the download.")
        elif d["facebook"]:
            source = "facebook"
            d["posts"] = [dict(r, likes=None, comments=None) for r in d["facebook"]]
            assumptions.append("Only a Facebook download was found, so the film is made from its posts and photos.")
        elif a.assets or a.subject or a.about:
            source = "subject"
            assumptions.append("No Instagram account, download or photo folder was reachable, so the film is made from the "
                               "subject's own assets alone; hooks and their palette need the account or the download.")
        else:
            write_howto(Path("out"))
            print(HOWTO)
            return 3
    lo, hi, year, why = pick_window(d["posts"] + d["reels"] + d["stories"], a.year)
    assumptions.append(why)
    handle = d["handle"] or "you"
    assumptions.append(f"Handle: @{handle}." if d["handle"] else "No username in the data; the cards say 'you'.")
    inyear = lambda rows: sorted((r for r in rows if r.get("ts") and lo <= int(r["ts"]) <= hi), key=lambda r: r["ts"])
    lib = {k: inyear(d[k]) for k in ("posts", "reels", "stories", "likes", "saved", "comments", "facebook")}
    dates = [r["ts"] for r in lib["posts"] + lib["reels"] + lib["stories"]]
    span = {"first": dt.datetime.fromtimestamp(min(dates), dt.timezone.utc).date().isoformat() if dates else None,
            "last": dt.datetime.fromtimestamp(max(dates), dt.timezone.utc).date().isoformat() if dates else None}
    if source in ("export", "accounts"):
        missing = [k for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers") if not d["found"].get(k)]
        if missing:
            assumptions.append("Not in the data (left out): " + ", ".join(missing) + ".")
        if not any(p.get("likes") is not None for p in lib["posts"] + lib["reels"]):
            assumptions.append("The data has no counts per post, so hooks are ranked by caption order alone.")
        elif not any(p.get("saves") is not None for p in lib["posts"] + lib["reels"]):
            assumptions.append("The data has no saves per post, so response is comments alone.")
    shelve(lib)
    subj = subject_block(a, root, lib, assumptions)
    no_media = sum(1 for p in lib["posts"] if not p["media"])
    if no_media:
        assumptions.append(f"{no_media} posts point at media files that are not there; they count but show no photo.")
    feed = read_feed(a.feed, assumptions) if a.feed else post_feed(lib)
    settings = {"feed_photos": a.feed or None, "subject_assets": str(Path("library/subject").resolve())}
    out = {"source": source, "sources": sources, "doors": doors, "root": str(root), "handle": handle, "name": d["name"],
           "year": year, "range": span, "subject": subj, "settings": settings, "feed": feed, "found": d["found"], **lib,
           "followers": d["followers"], "following": d["following"], "assumptions": assumptions + d["notes"]}
    _env.write_json("library.json", out)
    print(f"source: {source}   handle: @{handle}   range: {span['first']} to {span['last']}")
    print(f"subject: {subj['name'] or '-'} ({subj['kind']}{', a launch on ' + (subj['date'] or subj['date_label']) if subj['launch'] else ''})   assets: "
          f"{subj['assets_kind']} ({len(subj['stills'])} stills, {len(subj['footage'])} clips, "
          f"{subj['feed_posts']} posts mention it)")
    print("  ".join(f"{k} {len(out[k])}" for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers",
                                                   "following", "facebook")))
    for k, v in doors.items():
        print(f"door {k}: {v}")
    for x in out["assumptions"]:
        print("assumption:", x)
    print(f"feed: {len(feed)} photographs" + (f" from {', '.join(a.feed)}" if a.feed else " from the posts"))
    print("wrote library.json")
    if not subj["stills"]:
        print(f"not delivered: there is no picture of {subj['name'] or 'the subject'}, and the film opens on the subject, "
              f"so it needs at least one photograph of it, in a folder or on its page.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
