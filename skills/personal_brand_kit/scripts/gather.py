#!/usr/bin/env python3
"""Movement 0, gather: every door to the person's own material, merged into library.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/gather.py [--pulled build/pulled] [--door instagram_account="open: 120 posts"] \
        [--door browser="closed: no signed-in session"] [--since 2025-10-19] [--photos DIR] [--likes DIR] [--root .]

Doors, in order of preference (every one tried is recorded in library.json and in out/brief.md):
  1. Material the agent pulled itself from the person's connected Instagram or Facebook account or a signed-in
     browser session, saved under --pulled DIR (by default build/pulled in the workspace) as items.json (shape below) with the media files beside it.
  2. Instagram "Download your information" exports (JSON) anywhere under --root, as folders or .zip files (a zip is
     unpacked into export/): posts, reels, stories, likes, saves, comments, followers, following, per-post
     and per-reel likes and comments (past_instagram_insights), the username. Missing files are tolerated.
  3. Facebook "Download your information" exports under --root: posts, photos, albums.
  4. --photos DIR, else the largest folder of photos under --root (dates from EXIF, else the file time).
  4b. A table of posts the person keeps: a posts.csv anywhere under --root with a header naming date and caption, and
     time, image (a path beside the table), likes and comments where it has them; a likes.csv beside it (account,
     subject) lists the posts they like, and a bio.txt beside it, or under --root, is their bio.
  5. Liked media: --likes DIR, else a folder under --root whose name says likes, liked, saved, inspiration or
     moodboard and holds at least 8 images (the posts the person likes or saves, as screenshots or downloads; an
     export lists likes without their pictures). File names starting "<account>_" name the account.
With every door closed it writes out/brief.md with the one sentence on how to open one and exits 3: tell the
person that sentence and stop. Meta's text encoding (UTF-8 written as latin-1) is repaired everywhere.

items.json (every key optional; ts is a unix timestamp; media are paths relative to items.json):
  {"source": "instagram account", "handle": "...", "name": "...",
   "posts": [{"ts": 0, "caption": "", "media": ["a.jpg"], "likes": 0, "comments": 0, "place": ""}],
   "reels": [...same...], "stories": [{"ts": 0, "media": ["s.jpg"]}],
   "likes": [{"account": "", "ts": 0, "caption": "", "media": ["liked.jpg"]}], "saved": [...same as likes...],
   "comments": [{"account": "", "text": "", "ts": 0}], "followers": [{"account": "", "ts": 0}],
   "following": [{"account": "", "ts": 0}], "facebook": [{"ts": 0, "caption": "", "media": [], "album": ""}]}

The window: from --since when the person named a start, else the twelve months that end on the latest post.
Starts a run: a new folder build/<run stamp>/ under the workspace (build/run names it), where this and every later
script writes; out/ in it holds the deliverables, and a prior run's folder is never touched. Folders given on the
command line are read from the workspace root.
Links every media file of the window into library/<kind>/ (posts, reels, stories, likes, saved, facebook,
liked_media) under its date, writes library.json and prints a summary; every choice it made is listed under
"assumptions".
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

PULLED = Path("build/pulled")
SKIP = {"out", "build", ".claude", ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "custom-skills"}
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VID = {".mp4", ".mov", ".m4v"}
HOWTO = ("To read your style I need your Instagram: connect your Instagram account here, or in the Instagram app go "
         "to Your activity, then Download your information, choose JSON, and put the folder or zip it sends you in this "
         "workspace. A folder of the posts you like or save, as screenshots, makes the kit sharper.")
LIKE_WORDS = ("like", "liked", "saved", "inspiration", "moodboard", "mood-board", "mood_board")


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
            # a name found in two folders could be either post's photograph, so it finds nothing
            self.by_name = {}
            for f in (self.root / "media").rglob("*") if (self.root / "media").exists() else ():
                if f.is_file():
                    self.by_name[f.name] = None if f.name in self.by_name else f
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
            paths = [md.resolve(u) for u, _, _ in items]
            ins = insights_ts.get(int(ts or 0)) or next((insights[Path(u).name] for u, _, _ in items if Path(u).name in insights), {})
            posts.append({"ts": ts, "caption": cap, "media": [p for p in paths if p],
                          "likes": ins.get("likes"), "comments": ins.get("comments")})
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
                              "likes": ins.get("likes"), "comments": ins.get("comments")})
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
    handle, name, bio = None, None, None
    for f in first(root, "../personal_information/personal_information/personal_information.json",
                   "personal_information/personal_information/personal_information.json", "account_information/personal_information.json"):
        data = load(f) or {}
        for u in data.get("profile_user", []) if isinstance(data, dict) else []:
            smd = u.get("string_map_data") or {}
            handle = handle or fix((smd.get("Username") or {}).get("value", "")) or None
            name = name or fix((smd.get("Name") or {}).get("value", "")) or None
            bio = bio or fix((smd.get("Bio") or {}).get("value", "")) or None
    if not handle:
        m = re.match(r"instagram-([A-Za-z0-9._]+?)-\d{4}-\d{2}-\d{2}", root.name)
        if m:
            handle = m.group(1)
            notes.append(f"Username taken from the export's folder name ({root.name}).")
    return {"posts": posts, "reels": reels, "stories": stories, "likes": likes, "comments": comments,
            "followers": followers, "saved": saved, "following": following, "handle": handle, "name": name,
            "bio": bio, "found": found, "notes": notes}


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
    d.update(handle=data.get("handle"), name=data.get("name"), bio=data.get("bio"), source=data.get("source") or "connected account",
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


def read_table(root):
    """The posts table under the workspace (posts.csv, the newest when there are several) as library rows, with the
    likes.csv beside it as liked accounts and the bio.txt beside it or at the root as the bio; None when there is none."""
    import csv
    tables = sorted((f for d, kids in walk(root) for f in kids if f.name.lower() == "posts.csv"), key=lambda f: -f.stat().st_mtime)
    for f in tables:
        rows = list(csv.DictReader(f.read_text(encoding="utf-8-sig").splitlines()))
        if not rows or not {"date", "caption"} <= {k.strip().lower() for k in rows[0]}:
            continue
        posts = []
        for r in rows:
            r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
            try:
                when = dt.datetime.strptime(f"{r['date']} {r.get('time') or '12:00'}"[:16], "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            img = (f.parent / r["image"]) if r.get("image") else None
            num = lambda k: int(r[k]) if r.get(k, "").isdigit() else None
            posts.append({"ts": int(when.replace(tzinfo=dt.timezone.utc).timestamp()), "caption": r.get("caption", ""),
                          "media": [str(img.resolve())] if img and img.is_file() else [], "likes": num("likes"), "comments": num("comments")})
        latest = max((p["ts"] for p in posts), default=0)
        likes = []
        lk = f.parent / "likes.csv"
        if lk.is_file():
            for r in csv.DictReader(lk.read_text(encoding="utf-8-sig").splitlines()):
                r = {k.strip().lower(): (v or "").strip() for k, v in r.items() if k}
                if r.get("account"):
                    likes.append({"account": r["account"].lstrip("@"), "ts": latest, "caption": r.get("subject", ""), "media": []})
        bio = next((b.read_text().strip() for b in (f.parent / "bio.txt", root / "bio.txt") if b.is_file()), None)
        return {"file": f, "posts": posts, "likes": likes, "bio": bio}
    return None


def is_likes_folder(d):
    return any(w in d.name.lower() for w in LIKE_WORDS)


def likes_folder(root):
    """The folder of liked or saved images: named for likes, at least 8 images."""
    best = (0, None)
    for d, kids in walk(root):
        n = sum(1 for k in kids if k.suffix.lower() in IMG)
        if is_likes_folder(d) and n > best[0]:
            best = (n, d)
    return best[1] if best[0] >= 8 else None


def read_likes(folder):
    rows = []
    for f in sorted(f for f in Path(folder).rglob("*") if f.suffix.lower() in IMG and f.is_file()):
        acct = re.match(r"^(.+?)_\d+$", f.stem)
        rows.append({"account": acct.group(1) if acct else "", "ts": photo_date(f), "media": [str(f.resolve())]})
    return rows


def largest_photo_folder(root, least=8):
    best = (0, None)
    for d, kids in walk(root):
        if is_likes_folder(d):
            continue
        n = sum(1 for k in kids if k.suffix.lower() in IMG)
        if n > best[0]:
            best = (n, d)
    return best[1] if best[0] >= least else None


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def pick_window(rows, since):
    """(first day, last day, why): from the asked start, else the twelve months ending on the latest post."""
    dates = [day_of(r["ts"]) for r in rows if r.get("ts")]
    last = max(dates) if dates else dt.date.today()
    if since:
        return since, last, f"The window starts {since}, as asked, and ends on the latest post, {last}."
    first = last - dt.timedelta(days=364)
    return first, last, f"The window is the twelve months that end on the latest post: {first} to {last}."


def write_howto(out):
    out.mkdir(exist_ok=True)
    (out / "brief.md").write_text(f"# Brand kit: no data found\n\n## Assumptions\n\n- No Instagram export and no folder of "
                                  f"photos was found in this workspace.\n\n## What to do\n\n{HOWTO}\n")


def merge(base, extra):
    """Rows from a lower door join the library when no row with the same time and caption is already there."""
    seen = {(r.get("ts"), (r.get("caption") or "")[:40]) for r in base}
    return base + [r for r in extra if (r.get("ts"), (r.get("caption") or "")[:40]) not in seen]


def rel(p, root):
    p = Path(p)
    return p.relative_to(root) if p.is_relative_to(root) else p


def shelve(lib):
    """Every media file of the window, linked into library/<kind>/ under its date; the rows point at the links."""
    base = Path("library").resolve()
    for kind in ("posts", "reels", "stories", "likes", "saved", "facebook", "liked_media"):
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
    ap.add_argument("--since", type=dt.date.fromisoformat, help="first day of the window the person named (YYYY-MM-DD)")
    ap.add_argument("--photos", help="a folder of photos the person named")
    ap.add_argument("--likes", help="a folder of the images the person likes or saves")
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--door", action="append", default=[], help='name="open: ..." or name="closed: why"')
    a = ap.parse_args()
    root = _env.at_root(a.root).resolve()
    a.photos = str(_env.at_root(a.photos)) if a.photos else None
    a.likes = str(_env.at_root(a.likes)) if a.likes else None
    a.pulled = [str(_env.at_root(f)) for f in a.pulled] or ([str(_env.ROOT / PULLED)] if (_env.ROOT / PULLED / "items.json").exists() else [])
    run = _env.enter(new=True)
    print(f"run folder: {run}")
    Path("library").mkdir(parents=True, exist_ok=True)
    assumptions, doors = [], {}
    for x in a.door:
        k, _, v = x.partition("=")
        doors[k.strip()] = v.strip() or "tried"
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [] for k in keys}
    d.update(handle=None, name=None, bio=None, found={}, notes=[])
    sources = []
    for folder in a.pulled:
        p = read_pulled(folder)
        if not p:
            doors[f"pulled:{folder}"] = "closed: no readable items.json"
            continue
        for k in keys:
            d[k] = merge(d[k], p[k])
        d["handle"], d["name"], d["bio"] = d["handle"] or p["handle"], d["name"] or p["name"], d["bio"] or p["bio"]
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
        d["handle"], d["name"], d["bio"] = d["handle"] or x["handle"], d["name"] or x["name"], d["bio"] or x["bio"]
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
    table = None if (d["posts"] or d["reels"] or a.photos) else read_table(root)
    if table and table["posts"]:
        d["posts"], d["likes"] = table["posts"], table["likes"]
        d["bio"] = d["bio"] or table["bio"]
        d["found"].update(posts=[str(table["file"])], **({"likes": [str(table["file"].parent / "likes.csv")]} if table["likes"] else {}))
        source = "export"
        sources.append("posts table")
        doors["posts_table"] = f"open: {len(table['posts'])} posts and {len(table['likes'])} likes in {rel(table['file'], root)}"
        assumptions.append(f"The posts are the {len(table['posts'])} rows of {rel(table['file'], root)}, each with its photograph, "
                           "caption and likes as the table gives them.")
    if not d["posts"] and not d["reels"] and not a.photos and (root / "bio.txt").is_file():
        d["bio"] = d["bio"] or (root / "bio.txt").read_text().strip()
    if not d["posts"] and not d["reels"]:
        _env.need("PIL")
        folder = Path(a.photos) if a.photos else largest_photo_folder(root, 3)
        if folder:
            posts, vids = read_photos(folder)
            d["posts"], d["reels"] = posts, vids
            d["found"]["photos"] = str(folder)
            source = "photos"
            doors["photo_folder"] = f"open: {len(posts)} photos in {rel(folder, root)}"
            assumptions.append(f"No Instagram account or download was reachable, so the kit reads the {len(posts)} photos in "
                               f"{rel(folder, root)}. Captions, cadence and likes need the account or the download.")
        elif d["facebook"]:
            source = "facebook"
            d["posts"] = [dict(r, likes=None, comments=None) for r in d["facebook"]]
            assumptions.append("Only a Facebook download was found, so the kit reads its posts and photos.")
        else:
            write_howto(Path("out"))
            print(HOWTO)
            return 3
    first_day, last_day, why = pick_window(d["posts"] + d["reels"] + d["stories"], a.since)
    assumptions.append(why)
    handle = d["handle"] or "you"
    assumptions.append(f"Handle: @{handle}." if d["handle"] else "No username in the data; the film says 'you'.")
    inwindow = lambda rows: sorted((r for r in rows if r.get("ts") and first_day <= day_of(r["ts"]) <= last_day),
                                 key=lambda r: r["ts"])
    lib = {k: inwindow(d[k]) for k in ("posts", "reels", "stories", "likes", "saved", "comments", "facebook")}
    lfolder = Path(a.likes) if a.likes else likes_folder(root)
    lib["liked_media"] = read_likes(lfolder) if lfolder else []
    lib["liked_media"] += [r for r in d["likes"] + d["saved"] if r.get("media")]
    if lfolder:
        doors["liked_media"] = f"open: {len(lib['liked_media'])} liked images in {rel(lfolder, root)}"
        d["found"]["liked_media"] = [str(lfolder)]
    else:
        doors["liked_media"] = ("open: pulled with the account" if lib["liked_media"] else
                                "closed: no folder of liked or saved images; the likes are read by account only")
    dates = [r["ts"] for r in lib["posts"] + lib["reels"] + lib["stories"]]
    span = {"first": dt.datetime.fromtimestamp(min(dates), dt.timezone.utc).date().isoformat() if dates else None,
            "last": dt.datetime.fromtimestamp(max(dates), dt.timezone.utc).date().isoformat() if dates else None}

    if source in ("export", "accounts"):
        missing = [k for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers") if not d["found"].get(k)]
        if missing:
            assumptions.append("Not in the data (left out): " + ", ".join(missing) + ".")
        if not any(p.get("likes") is not None for p in lib["posts"] + lib["reels"]):
            assumptions.append("The data has no likes per post, so what lands best is read from comments, else left out.")
    shelve(lib)
    no_media = sum(1 for p in lib["posts"] if not p["media"])
    if no_media:
        assumptions.append(f"{no_media} posts point at media files that are not there; they count but show no photo.")
    out = {"source": source, "sources": sources, "doors": doors, "root": str(root), "handle": handle, "name": d["name"],
           "bio": d["bio"], "year": last_day.year, "window": [str(first_day), str(last_day)], "range": span, "found": d["found"], **lib, "followers": d["followers"],
           "following": d["following"], "assumptions": assumptions + d["notes"]}
    _env.write_json("library.json", out)
    print(f"source: {source}   handle: @{handle}   range: {span['first']} to {span['last']}")
    print("  ".join(f"{k} {len(out[k])}" for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers",
                                                   "following", "facebook", "liked_media")))
    for k, v in doors.items():
        print(f"door {k}: {v}")
    for x in out["assumptions"]:
        print("assumption:", x)
    print("wrote library.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
