#!/usr/bin/env python3
"""Movement 0, gather: the launch (product, date, assets) and every door to the person's own material, merged into
build/library.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/gather.py --product "Tide Table" --date 2026-11-14 --assets tide-table-launch/ \
        [--pulled build/library/pulled] [--door instagram_account="open: 120 posts"] \
        [--door browser="closed: no signed-in session"] [--year 2026] [--photos DIR] [--root .]

The launch, in the person's own words (they win over anything inferred):
  --product NAME   what is launching (a product, a drop, an event). Without it the name is inferred from the feed
                   (the capitalized name its recent posts repeat most) and the inference is listed as an assumption.
  --date TEXT      when: 2026-11-14, "November 14", "Nov 14 2026", "14/11"; a date with no year is the next one to
                   come. A date that cannot be read is kept as written and shown as written.
  --assets WHERE   a folder of product stills and clips, or a link to the product's page (its og:image and large
                   images are downloaded, at most 8). Without it: a workspace folder named like the product, else the
                   person's own posts that mention the product.
Stills are linked into build/library/product/stills/, clips into build/library/product/footage/; the asset folder
never counts as the person's photo folder.

Doors, in order of preference (every one tried is recorded in library.json and in out/brief.md):
  1. Material the agent pulled itself from the person's connected Instagram or Facebook account or a signed-in
     browser session, saved under --pulled DIR as items.json (shape below) with the media files beside it.
  2. Instagram "Download your information" exports (JSON) anywhere under --root, as folders or .zip files (a zip is
     unpacked into build/export/): posts, reels, stories, likes, saves, comments, followers, following, per-post
     and per-reel likes and comments (past_instagram_insights), the username. Missing files are tolerated.
  3. Facebook "Download your information" exports under --root: posts, photos, albums.
  4. --photos DIR, else the largest folder of photos under --root (dates from EXIF, else the file time).
With every door closed it writes out/brief.md with the one sentence on how to open one and exits 3: tell the
person that sentence and stop. Meta's text encoding (UTF-8 written as latin-1) is repaired everywhere.

items.json (every key optional; ts is a unix timestamp; media are paths relative to items.json):
  {"source": "instagram account", "handle": "...", "name": "...",
   "posts": [{"ts": 0, "caption": "", "media": ["a.jpg"], "likes": 0, "comments": 0, "place": ""}],
   "reels": [...same...], "stories": [{"ts": 0, "media": ["s.jpg"]}],
   "likes": [{"account": "", "ts": 0, "caption": "", "media": ["liked.jpg"]}], "saved": [...same as likes...],
   "comments": [{"account": "", "text": "", "ts": 0}], "followers": [{"account": "", "ts": 0}],
   "following": [{"account": "", "ts": 0}], "facebook": [{"ts": 0, "caption": "", "media": [], "album": ""}]}

The window: the 365 days ending at the latest post (or the calendar year given with --year). Links every media file
of the window into build/library/<kind>/ (posts, reels, stories, likes, saved, facebook) under its date, writes
build/library.json (with a "launch" block) and prints a summary; every choice it made is listed under "assumptions".
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
HOWTO = ("To make your launch film I need your Instagram, or at least your product's photos: connect your Instagram "
         "account here, or in the Instagram app go to Your activity, then Download your information, choose JSON, and put "
         "the folder or zip it sends you in this workspace, along with a folder of your product's photos.")
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
            dest = Path("build/export") / z.stem
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
            self.by_name = {f.name: f for f in (self.root / "media").rglob("*") if f.is_file()} if (self.root / "media").exists() else {}
        f = self.by_name.get(Path(uri).name)
        return str(f.resolve()) if f else None


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


def parse_date(text, today=None):
    """(iso or None, label): ISO, 'November 14', 'Nov 14 2026', '14 Nov', '11/14', '14/11/2026'; no year means the next one."""
    today = today or dt.date.today()
    t = (text or "").strip()
    if not t:
        return None, ""
    low = t.lower().replace(",", " ")
    y = m = d = None
    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", low):
        y, m, d = (int(x) for x in re.findall(r"\d+", low)[:3])
    else:
        mon = next((i + 1 for i, n in enumerate(MONTHS) for w in re.findall(r"[a-z]+", low) if len(w) >= 3 and n.startswith(w)), None)
        nums = [int(x) for x in re.findall(r"\d+", low)]
        yrs = [n for n in nums if n > 31]
        days = [n for n in nums if n <= 31]
        if mon and days:
            m, d, y = mon, days[0], (yrs[0] if yrs else None)
        elif len(days) >= 2:
            a, b = days[0], days[1]
            m, d = (a, b) if a <= 12 and (b > 12 or "/" in low and not low.startswith(str(b))) else (b, a)
            y = yrs[0] if yrs else (days[2] + 2000 if len(days) > 2 and days[2] < 100 else None)
    try:
        if y is None:
            when = dt.date(today.year, m, d)
            when = when if when >= today else dt.date(today.year + 1, m, d)
        else:
            when = dt.date(y, m, d)
    except (TypeError, ValueError):
        return None, t
    return when.isoformat(), f"{MONTHS[when.month - 1].capitalize()} {when.day}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def mentions(text, product):
    """Whether a caption names the product (spacing, hyphens and case ignored)."""
    return bool(product) and slug(product) in slug(text)


def infer_product(rows):
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
    hdr = {"User-Agent": "Mozilla/5.0 (launch-hype-reel)"}
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


def find_asset_folder(root, product):
    """A workspace folder whose name carries the product's name and that holds images or clips."""
    key = slug(product)
    best = None
    for d, kids in walk(root):
        if d == root or not key or key not in slug(d.name):
            continue
        n = sum(1 for k in kids if k.suffix.lower() in IMG | VID)
        if n and (best is None or n > best[0]):
            best = (n, d)
    return best[1] if best else None


def launch_block(a, root, lib, assumptions):
    """The launch: product, date and the product's own assets, linked under build/library/product/."""
    rows = lib["posts"] + lib["reels"]
    product = (a.product or "").strip()
    if not product:
        product = infer_product(rows) or ""
        assumptions.append(f"No product name was given; the feed's most repeated name is {product!r}." if product
                           else "No product name was given and the feed names none; the film says 'something new'.")
    iso, label = parse_date(a.date)
    if a.date and not iso:
        assumptions.append(f"The date {a.date!r} could not be read as a calendar day; it is shown as written.")
    elif not a.date:
        assumptions.append("No launch date was given; the countdown card says 'soon'.")
    days = (dt.date.fromisoformat(iso) - dt.date.today()).days if iso else None
    base = Path("build/library/product").resolve()
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
    if not kind:
        folder = find_asset_folder(root, product)
        if folder:
            kind, where = "folder", folder
            notes.append(f"No assets were named; used {rel(folder, root)}, the folder named like the product.")
    if kind == "folder":
        files = sorted(f for f in where.rglob("*") if f.is_file() and f.suffix.lower() in IMG | VID)
    feed = [r for r in rows if mentions(r.get("caption"), product)]
    if not files and feed:
        kind, where = "feed", None
        files = [Path(m) for r in sorted(feed, key=lambda r: -(r.get("ts") or 0)) for m in r.get("media") or []
                 if Path(m).suffix.lower() in IMG][:12]
        notes.append(f"No product folder or link; the product's pictures are the {len(feed)} posts that mention {product}.")
    stills, footage = [], []
    for f in files:
        vid = f.suffix.lower() in VID
        dst = (footage_dir if vid else stills_dir) / f"{len(footage if vid else stills) + 1:02d}{f.suffix.lower()}"
        try:
            dst.symlink_to(Path(f).resolve())
        except OSError:
            shutil.copy2(f, dst)
        (footage if vid else stills).append(str(dst))
    if not files:
        notes.append("No product pictures anywhere; product beats use type, color and generated clips.")
    assumptions += notes
    return {"product": product, "date": iso, "date_text": a.date or "", "date_label": label or (a.date or "soon"),
            "days_to_go": days, "assets": str(where) if where else None, "assets_kind": kind or "none",
            "stills": stills, "footage": footage, "feed_posts": len(feed), "notes": notes}


def write_howto(out):
    out.mkdir(exist_ok=True)
    (out / "brief.md").write_text(f"# Launch film: no material found\n\n## Assumptions\n\n- No Instagram export, product "
                                  f"folder or folder of photos was found in this workspace.\n\n## What to do\n\n{HOWTO}\n")


def merge(base, extra):
    """Rows from a lower door join the library when no row with the same time and caption is already there."""
    seen = {(r.get("ts"), (r.get("caption") or "")[:40]) for r in base}
    return base + [r for r in extra if (r.get("ts"), (r.get("caption") or "")[:40]) not in seen]


def rel(p, root):
    p = Path(p)
    return p.relative_to(root) if p.is_relative_to(root) else p


def shelve(lib):
    """Every media file of the year, linked into build/library/<kind>/ under its date; the rows point at the links."""
    base = Path("build/library").resolve()
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--year", type=int, help="a calendar year the person named instead of the last 365 days")
    ap.add_argument("--product", help="what is launching, in the person's words")
    ap.add_argument("--date", help="when it launches, as the person wrote it")
    ap.add_argument("--assets", help="a folder or link with the product's photos and clips")
    ap.add_argument("--photos", help="a folder of photos the person named")
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--door", action="append", default=[], help='name="open: ..." or name="closed: why"')
    a = ap.parse_args()
    root = Path(a.root).resolve()
    Path("build/library").mkdir(parents=True, exist_ok=True)
    assumptions, doors = [], {}
    for x in a.door:
        k, _, v = x.partition("=")
        doors[k.strip()] = v.strip() or "tried"
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [] for k in keys}
    d.update(handle=None, name=None, found={}, notes=[])
    sources = []
    pulled = a.pulled or (["build/library/pulled"] if Path("build/library/pulled/items.json").exists() else [])
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
        skip = (root / a.assets).resolve() if a.assets and not re.match(r"^https?://", a.assets) else None
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
        elif a.assets or a.product:
            source = "product"
            assumptions.append("No Instagram account, download or photo folder was reachable, so the film is made from the "
                               "product's own assets alone; hooks and their palette need the account or the download.")
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
    launch = launch_block(a, root, lib, assumptions)
    no_media = sum(1 for p in lib["posts"] if not p["media"])
    if no_media:
        assumptions.append(f"{no_media} posts point at media files that are not there; they count but show no photo.")
    out = {"source": source, "sources": sources, "doors": doors, "root": str(root), "handle": handle, "name": d["name"],
           "year": year, "range": span, "launch": launch, "found": d["found"], **lib, "followers": d["followers"],
           "following": d["following"], "assumptions": assumptions + d["notes"]}
    _env.write_json("build/library.json", out)
    print(f"source: {source}   handle: @{handle}   range: {span['first']} to {span['last']}")
    print(f"launch: {launch['product'] or '-'}   date: {launch['date'] or launch['date_label']}   assets: "
          f"{launch['assets_kind']} ({len(launch['stills'])} stills, {len(launch['footage'])} clips, "
          f"{launch['feed_posts']} posts mention it)")
    print("  ".join(f"{k} {len(out[k])}" for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers",
                                                   "following", "facebook")))
    for k, v in doors.items():
        print(f"door {k}: {v}")
    for x in out["assumptions"]:
        print("assumption:", x)
    print("wrote build/library.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
