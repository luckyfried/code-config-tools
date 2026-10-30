#!/usr/bin/env python3
"""Movement 0, gather: every door to the person's own material, and to the named one's feed, merged into
B/library.json.

USAGE (from the workspace root; S = this skill's folder, B = the run's folder, build/<run stamp>/):
    python3 S/scripts/gather.py [--pulled build/pulled] [--feed DIR] [--door instagram_account="open: 120 posts"] \
        [--door browser="closed: no signed-in session"] [--year 2026] [--photos DIR] [--root .]

Doors, in order of preference (every one tried is recorded in library.json and in B/brief.md):
  1. Material the agent pulled itself from the person's connected Instagram or Facebook account or a signed-in
     browser session, saved under --pulled DIR as items.json (shape below) with the media files beside it.
  2. Instagram "Download your information" exports (JSON) anywhere under --root, as folders or .zip files (a zip is
     unpacked into B/export/): posts, reels, stories, likes, saves, comments, followers, following, per-post
     and per-reel likes and comments (past_instagram_insights), the username. Missing files are tolerated.
  3. Facebook "Download your information" exports under --root: posts, photos, albums.
  4. A posts file anywhere under --root: any .json whose top level is {"owner": "...", "posts": [{"date":
     "2026-03-14", "media": "photos/a.jpg", "caption": "...", "tagged": ["..."], "comments": [{"user": "...",
     "text": "..."}]}]} (owner, tagged and comments optional; a comment's writer is "user" or "account"; media paths
     are read beside the file, else from --root). A post with no date is left out, with one line saying so.
  5. --photos DIR, else the largest folder of photos under --root (dates from EXIF, else the file time).
With every door closed it writes out/brief.md with the one sentence on how to open one and exits 3: tell the
person that sentence and stop. Meta's text encoding (UTF-8 written as latin-1) is repaired everywhere.

items.json (every key optional; ts is a unix timestamp; media are paths relative to items.json; tagged names the
accounts tagged in the post; thread is the post's comments, each with the account that wrote it):
  {"source": "instagram account", "handle": "...", "name": "...",
   "posts": [{"ts": 0, "caption": "", "media": ["a.jpg"], "likes": 0, "comments": 0, "place": "", "tagged": ["..."],
              "thread": [{"account": "", "text": "", "ts": 0}]}],
   "reels": [...same...], "stories": [{"ts": 0, "media": ["s.jpg"]}],
   "likes": [{"account": "", "ts": 0, "caption": "", "media": ["liked.jpg"]}], "saved": [...same as likes...],
   "comments": [{"account": "", "text": "", "ts": 0}], "followers": [{"account": "", "ts": 0}],
   "following": [{"account": "", "ts": 0}], "facebook": [{"ts": 0, "caption": "", "media": [], "album": ""}]}

The named one's own feed, when the agent can reach it (their profile in a signed-in browser or a connected
account): saved the same way, as items.json with "feed_of": "<their handle>" (and their "name") and the photos
beside it, in any folder under the workspace (build/pulled/feed-<handle>/ is the usual place) or named with
--feed. Every such folder is read into library.json "feeds", keyed by handle; their posts carry their captions,
who they tag and the comment threads under them.

A tribute spans the whole friendship, so every dated row is kept; --year keeps one year only. "year" in
library.json is the latest year in the data. Links every media file into B/library/<kind>/ (posts, reels,
stories, likes, saved, facebook, feed-<handle>) under its date, writes B/library.json and prints a summary;
every choice it made is listed under "assumptions".
"""
import argparse
import datetime as dt
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PULLED = Path("build/pulled")  # what the agent saved from the account and the browser before gather: an input, shared by every run
SKIP = {"out", "build", ".claude", ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "custom-skills"}
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VID = {".mp4", ".mov", ".m4v"}
HOWTO = ("To make the video I need the photos you two share: connect your Instagram account here, or in the Instagram "
         "app go to Your activity, then Download your information, choose JSON, and put the folder or zip it sends you "
         "in this workspace. A folder of your photos together works too.")


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
            dest = Path(f"{_env.B}/export") / z.stem
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
            # a file found by its name alone, when no other file in media/ carries that name; a shared name picks neither
            self.by_name = {}
            for f in (self.root / "media").rglob("*") if (self.root / "media").exists() else []:
                if f.is_file():
                    self.by_name[f.name] = None if f.name in self.by_name else f
        f = self.by_name.get(Path(uri).name)
        return str(f.resolve()) if f else None


def tags_of(*parts):
    """The accounts tagged on a media item or its post, from any of the shapes Meta writes (tagged_users, usertags)."""
    out = []
    for x in parts:
        if not isinstance(x, dict):
            continue
        for key in ("tagged_users", "usertags", "tags", "tagged"):
            for t in x.get(key) or []:
                name = t if isinstance(t, str) else (t.get("username") or (t.get("user") or {}).get("username") or t.get("value")
                                                     if isinstance(t, dict) else None)
                name = fix(name or "").lstrip("@").lower()
                if name and name not in out:
                    out.append(name)
    return out


def media_items(entry):
    """Flatten Instagram's media shapes into [(uri, ts, title, tagged)]."""
    if not isinstance(entry, dict):
        return []
    items = entry.get("media") if isinstance(entry.get("media"), list) else [entry]
    out = []
    for m in items:
        if isinstance(m, dict) and m.get("uri"):
            out.append((m["uri"], m.get("creation_timestamp") or entry.get("creation_timestamp"), m.get("title") or "", tags_of(m, entry)))
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
            rec = {"likes": num("like"), "comments": num("comment")}
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
            paths = [md.resolve(u) for u, _, _, _ in items]
            ins = insights_ts.get(int(ts or 0)) or next((insights[Path(u).name] for u, _, _, _ in items if Path(u).name in insights), {})
            tagged = list(dict.fromkeys(t for it in items for t in it[3]))
            posts.append({"ts": ts, "caption": cap, "media": [p for p in paths if p],
                          "likes": ins.get("likes"), "comments": ins.get("comments"), "tagged": tagged})
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
                reels.append({"ts": ts, "caption": fix(items[0][2]), "media": [p for p in (md.resolve(u) for u, _, _, _ in items) if p],
                              "likes": ins.get("likes"), "comments": ins.get("comments"), "tagged": items[0][3]})
    stories = []
    sf = first(root, "content/stories.json")
    found["stories"] = [str(f) for f in sf]
    for f in sf:
        data = load(f) or {}
        rows = data.get("ig_stories", []) if isinstance(data, dict) else data
        for e in rows or []:
            for u, ts, t, tagged in media_items(e):
                stories.append({"ts": ts, "media": [p for p in [md.resolve(u)] if p], "tagged": tagged})
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
        thread = [{"account": fix(c.get("account") or "").lstrip("@").lower(), "text": fix(c.get("text") or ""), "ts": c.get("ts")}
                  for c in row.get("thread") or [] if isinstance(c, dict)]
        tagged = [fix(t).lstrip("@").lower() for t in row.get("tagged") or [] if isinstance(t, str)]
        extra = {"tagged": tagged, "thread": thread} if ("tagged" in row or "thread" in row) else {}
        return dict(row, media=out, caption=fix(row.get("caption") or ""), **extra)
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [media(r) if isinstance(r, dict) else r for r in data.get(k) or []] for k in keys}
    d.update(handle=data.get("handle"), name=data.get("name"), source=data.get("source") or "connected account",
             found={k: [str(f)] for k in keys if d[k]}, feed_of=(data.get("feed_of") or "").lstrip("@").lower() or None)
    return d


def find_feeds(root):
    """Every folder under the workspace holding an items.json that names whose feed it is (feed_of)."""
    out = []
    for d, kids in walk(root):
        if any(k.name == "items.json" for k in kids):
            data = load(d / "items.json")
            if isinstance(data, dict) and data.get("feed_of"):
                out.append(d)
    for extra in (PULLED.resolve(),):
        if extra.is_dir():
            for f in extra.glob("*/items.json"):
                data = load(f)
                if isinstance(data, dict) and data.get("feed_of") and f.parent not in out:
                    out.append(f.parent)
    return out


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


def largest_photo_folder(root):
    best = (0, None)
    for d, kids in walk(root):
        n = sum(1 for k in kids if k.suffix.lower() in IMG)
        if n > best[0]:
            best = (n, d)
    return best[1]


def read_posts_file(f, root):
    """A posts file (shape in the usage) as (owner, rows, undated), or None when the file is not one: a list of posts at
    least one of which has a date. Each row carries its post's comments as its thread; `undated` counts the posts
    left out for having no date that reads."""
    data = load(f)
    posts = data.get("posts") if isinstance(data, dict) else None
    if not isinstance(posts, list) or not any(isinstance(p, dict) and p.get("date") for p in posts):
        return None
    rows, undated = [], 0
    for p in posts:
        try:
            when = dt.datetime.fromisoformat(str(p["date"]))
            ts = int((when if when.tzinfo else when.replace(tzinfo=dt.timezone.utc)).timestamp())
        except (KeyError, TypeError, ValueError):
            undated += 1
            continue
        media = []
        for m in p.get("media") if isinstance(p.get("media"), list) else [p.get("media")]:
            hit = next((b / m for b in (f.parent, root) if isinstance(m, str) and (b / m).is_file()), None)
            if hit:
                media.append(str(hit.resolve()))
        thread = [{"account": fix(c.get("user") or c.get("account") or "").lstrip("@").lower(), "text": fix(c.get("text") or ""),
                   "ts": c.get("ts")} for c in p.get("comments") or [] if isinstance(c, dict)]
        rows.append({"ts": ts, "caption": str(p.get("caption") or ""), "media": media, "likes": None, "comments": len(thread),
                     "tagged": tags_of(p), "thread": thread})
    return (str(data.get("owner") or "").lstrip("@").lower() or None), rows, undated


def year_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).year


def write_howto(out):
    out.mkdir(exist_ok=True)
    (out / "brief.md").write_text(f"# Tribute video: no photos found\n\n## Assumptions\n\n- No Instagram export and no folder of "
                                  f"photos was found in this workspace.\n\n## What to do\n\n{HOWTO}\n")


def merge(base, extra):
    """Rows from a lower door join the library when no row with the same time and caption is already there."""
    seen = {(r.get("ts"), (r.get("caption") or "")[:40]) for r in base}
    return base + [r for r in extra if (r.get("ts"), (r.get("caption") or "")[:40]) not in seen]


def rel(p, root):
    p = Path(p)
    return p.relative_to(root) if p.is_relative_to(root) else p


def shelve(lib):
    """Every media file, linked into B/library/<kind>/ under its date; the rows point at the links."""
    base = Path(f"{_env.B}/library").resolve()
    shelves = [(kind, lib[kind]) for kind in ("posts", "reels", "stories", "likes", "saved", "facebook")]
    shelves += [(f"feed-{h}", f["posts"] + f["reels"] + f["stories"]) for h, f in (lib.get("feeds") or {}).items()]
    for kind, rows in shelves:
        for n, row in enumerate(rows):
            media = []
            for i, m in enumerate(row.get("media") or []):
                src = Path(m)
                if not src.is_file() or base in src.resolve().parents:
                    media.append(m)
                    continue
                day = dt.datetime.fromtimestamp(int(row.get("ts") or src.stat().st_mtime), dt.timezone.utc).date().isoformat()
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
    ap.add_argument("--year", type=int)
    ap.add_argument("--photos", help="a folder of photos the person named")
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--feed", action="append", default=[], help="a folder holding the named one's feed (items.json with feed_of)")
    ap.add_argument("--door", action="append", default=[], help='name="open: ..." or name="closed: why"')
    a = ap.parse_args()
    root = Path(a.root).resolve()
    _env.start_run()
    Path(f"{_env.B}/library").mkdir(parents=True, exist_ok=True)
    assumptions, doors = [], {}
    for x in a.door:
        k, _, v = x.partition("=")
        doors[k.strip()] = v.strip() or "tried"
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [] for k in keys}
    d.update(handle=None, name=None, found={}, notes=[])
    sources = []
    pulled = a.pulled or ([str(PULLED)] if (PULLED / "items.json").exists() else [])
    feeds = {}
    for folder in list(dict.fromkeys([Path(f).resolve() for f in a.feed] + find_feeds(root))):
        p = read_pulled(folder)
        if not p or not p.get("feed_of"):
            doors[f"feed:{rel(folder, root)}"] = "closed: no items.json naming whose feed it is (feed_of)"
            continue
        feeds[p["feed_of"]] = {"handle": p["feed_of"], "name": p["name"], "source": p["source"], "folder": str(rel(folder, root)),
                               "posts": p["posts"], "reels": p["reels"], "stories": p["stories"]}
        doors[f"their_feed:{p['feed_of']}"] = f"open: {len(p['posts'])} posts from {p['source']} ({rel(folder, root)})"
    if not feeds:
        doors.setdefault("their_feed", "closed: no saved feed of the named one under the workspace")
    for folder in pulled:
        p = read_pulled(folder)
        if not p:
            doors[f"pulled:{folder}"] = "closed: no readable items.json"
            continue
        if p.get("feed_of"):
            continue
        for k in keys:
            d[k] = merge(d[k], p[k])
        d["handle"], d["name"] = d["handle"] or p["handle"], d["name"] or p["name"]
        d["found"].update(p["found"])
        sources.append(p["source"])
        # the door the agent named for this source ("instagram_account" for "instagram account") keeps its own words
        doors.setdefault(p["source"].replace(" ", "_"), f"open: {len(p['posts'])} posts, {len(p['likes'])} likes pulled")
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
    files = []
    for folder, kids in ([] if a.photos else walk(root)):
        for f in sorted(k for k in kids if k.suffix.lower() == ".json" and k.is_file()):
            got = read_posts_file(f, root)
            if got:
                owner, rows, undated = got
                if undated:
                    assumptions.append(f"Left out {undated} {'post' if undated == 1 else 'posts'} in {rel(f, root)} with no date.")
                d["posts"] = merge(d["posts"], rows)
                d["handle"] = d["handle"] or owner
                d["found"].setdefault("posts", []).append(str(f))
                if any(r["thread"] for r in rows):
                    d["found"].setdefault("comments", []).append(str(f))
                files.append(f"{len(rows)} posts in {rel(f, root)}")
    if files:
        sources.append("posts file")
        doors["posts_file"] = "open: " + ", ".join(files)
    else:
        doors.setdefault("posts_file", "closed: none under the workspace")
    source = ("accounts" if sources and sources[0] not in ("instagram download", "posts file") else "export") if sources else None
    if not d["posts"] and not d["reels"]:
        _env.need("PIL")
        folder = Path(a.photos) if a.photos else largest_photo_folder(root)
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
        else:
            write_howto(Path("out"))
            print(HOWTO)
            return 3
    if a.year:
        year = a.year
        assumptions.append(f"Only {year} is used, as asked.")
        keep = lambda rows: sorted((r for r in rows if r.get("ts") and year_of(r["ts"]) == year), key=lambda r: r["ts"])
    else:
        dated = [r["ts"] for r in d["posts"] + d["reels"] + d["stories"] if r.get("ts")]
        year = year_of(max(dated)) if dated else dt.date.today().year
        keep = lambda rows: sorted((r for r in rows if r.get("ts")), key=lambda r: r["ts"])
    handle = d["handle"] or "you"
    assumptions.append(f"Handle: @{handle}." if d["handle"] else "No username in the data; the cards say 'you'.")
    lib = {k: keep(d[k]) for k in ("posts", "reels", "stories", "likes", "saved", "comments", "facebook")}
    lib["feeds"] = {h: dict(f, posts=keep(f["posts"]), reels=keep(f["reels"]), stories=keep(f["stories"])) for h, f in feeds.items()}
    dates = [r["ts"] for r in lib["posts"] + lib["reels"] + lib["stories"]]
    span = {"first": dt.datetime.fromtimestamp(min(dates), dt.timezone.utc).date().isoformat() if dates else None,
            "last": dt.datetime.fromtimestamp(max(dates), dt.timezone.utc).date().isoformat() if dates else None}
    if span["first"]:
        assumptions.append(f"Your photos run from {span['first']} to {span['last']}; the whole span is searched for the two of you.")
    if source in ("export", "accounts"):
        missing = [k for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers") if not d["found"].get(k)]
        if missing:
            assumptions.append("Not in the data (left out): " + ", ".join(missing) + ".")
    shelve(lib)
    no_media = sum(1 for p in lib["posts"] if not p["media"])
    if no_media:
        assumptions.append(f"{no_media} posts point at media files that are not there; they count but show no photo.")
    out = {"source": source, "sources": sources, "doors": doors, "root": str(root), "handle": handle, "name": d["name"],
           "year": year, "range": span, "found": d["found"], **lib, "followers": d["followers"],
           "following": d["following"], "assumptions": assumptions + d["notes"]}
    _env.write_json(f"{_env.B}/library.json", out)
    print(f"source: {source}   handle: @{handle}   range: {span['first']} to {span['last']}")
    print("  ".join(f"{k} {len(out[k])}" for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers",
                                                   "following", "facebook")))
    for h, f in out["feeds"].items():
        print(f"feed of @{h}: {len(f['posts'])} posts, {sum(len(p.get('thread') or []) for p in f['posts'])} comments in their threads")
    for k, v in doors.items():
        print(f"door {k}: {v}")
    for x in out["assumptions"]:
        print("assumption:", x)
    print(f"wrote {_env.B}/library.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
