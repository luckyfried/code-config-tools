#!/usr/bin/env python3
"""Movement 0, gather: every door to the person's own material, with every geotag and place name, into library.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/gather.py [--pulled pulled] [--door instagram_account="open: 120 posts"] \
        [--door browser="closed: no signed-in session"] [--year 2026] [--photos DIR] [--root .]

Doors, in order of preference (every one tried is recorded in library.json and in the run's brief.md):
  1. Material the agent pulled itself from the person's connected Instagram or Facebook account or a signed-in
     browser session, saved under --pulled DIR as items.json (shape below) with the media files beside it.
  2. Instagram "Download your information" exports (JSON) anywhere under --root, as folders or .zip files (a zip is
     unpacked into export/): posts, reels, stories, likes, saves, comments, followers, following, per-post
     and per-reel likes and comments (past_instagram_insights), the username. Missing files are tolerated.
  3. Facebook "Download your information" exports under --root: posts, photos, albums.
  4. --photos DIR, else the largest folder of photos under --root (dates and GPS from EXIF, else the date in the file
     name, else the file time; the folder each photo sits in and the words of its file name are kept, since a folder
     named "Porto 2026" or a file named 2026-05-17_fes.jpg names the place).
With every door closed it writes the run's brief.md with the one sentence on how to open one and exits 3: tell the
person that sentence and stop. Meta's text encoding (UTF-8 written as latin-1) is repaired everywhere.

items.json (every key optional; ts is a unix timestamp; media are paths relative to items.json):
  {"source": "instagram account", "handle": "...", "name": "...",
   "posts": [{"ts": 0, "caption": "", "media": ["a.jpg"], "likes": 0, "comments": 0, "place": "", "lat": 0, "lon": 0}],
   "reels": [...same...], "stories": [{"ts": 0, "media": ["s.jpg"], "place": "", "lat": 0, "lon": 0}],
   "likes": [{"account": "", "ts": 0, "caption": "", "media": ["liked.jpg"]}], "saved": [...same as likes...],
   "comments": [{"account": "", "text": "", "ts": 0}], "followers": [{"account": "", "ts": 0}],
   "following": [{"account": "", "ts": 0}], "facebook": [{"ts": 0, "caption": "", "media": [], "album": "", "place": ""}],
   "bio": ""}
Every row keeps the geotag it carries (lat, lon: from media_metadata exif_data, a check-in, or photo EXIF) and any
place name the data attaches to it (place, album, folder, file); movement 1 turns them into the year's places.

The year: --year when the person named one, else the latest year with at least 12 posts, reels and stories.
Links every media file of the year into library/<kind>/ (posts, reels, stories, likes, saved, facebook)
under its date, writes library.json and prints a summary; every choice it made is listed under "assumptions".
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

SKIP = {"out", "build", ".claude", ".git", "node_modules", ".venv", "venv", "__pycache__", ".cache", "custom-skills"}
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VID = {".mp4", ".mov", ".m4v"}
HOWTO = ("To map your year of places I need your Instagram or your photos: connect your Instagram account here, or in "
         "the Instagram app go to Your activity, then Download your information, choose JSON, and put the folder or zip "
         "it sends you in this workspace. A folder of your phone's photos works too, since they carry where they were taken.")


def fix(s):
    if not isinstance(s, str):
        return ""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def geo_of(x, depth=0):
    """The first latitude and longitude pair anywhere inside a row (exif_data, place, location, coordinate)."""
    if depth > 6:
        return None
    if isinstance(x, dict):
        lat, lon = x.get("latitude", x.get("lat")), x.get("longitude", x.get("lon", x.get("lng")))
        try:
            lat, lon = float(lat), float(lon)
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat, lon) != (0.0, 0.0):
                return round(lat, 6), round(lon, 6)
        except (TypeError, ValueError):
            pass
        for v in x.values():
            g = geo_of(v, depth + 1)
            if g:
                return g
    elif isinstance(x, list):
        for v in x:
            g = geo_of(v, depth + 1)
            if g:
                return g
    return None


def place_of(x, depth=0):
    """A place name the data attaches to a row: a place, location, or check-in's name."""
    if depth > 6:
        return ""
    if isinstance(x, dict):
        for k in ("place", "location", "check_in", "checkin"):
            v = x.get(k)
            if isinstance(v, str) and v.strip():
                return fix(v.strip())
            if isinstance(v, dict) and isinstance(v.get("name"), str) and v["name"].strip():
                return fix(v["name"].strip())
        for v in x.values():
            if isinstance(v, (dict, list)):
                n = place_of(v, depth + 1)
                if n:
                    return n
    elif isinstance(x, list):
        for v in x:
            n = place_of(v, depth + 1)
            if n:
                return n
    return ""


def located(row, src):
    """The row with the geotag and place name its source carries (a row's own values win)."""
    g = geo_of(src)
    if g and row.get("lat") is None:
        row["lat"], row["lon"] = g
    n = place_of(src)
    if n and not row.get("place"):
        row["place"] = n
    return row


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

    def resolve(self, uri):
        """The file at the path the export names, or None: a file of the same name elsewhere is another post's."""
        if not uri or re.match(r"^https?://", uri):
            return None
        p = self.root / uri
        return str(p.resolve()) if p.is_file() else None


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
            posts.append(located({"ts": ts, "caption": cap, "media": [p for p in paths if p],
                                  "likes": ins.get("likes"), "comments": ins.get("comments")}, e))
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
                reels.append(located({"ts": ts, "caption": fix(items[0][2]), "media": [p for p in (md.resolve(u) for u, _, _ in items) if p],
                                      "likes": ins.get("likes"), "comments": ins.get("comments")}, e))
    stories = []
    sf = first(root, "content/stories.json")
    found["stories"] = [str(f) for f in sf]
    for f in sf:
        data = load(f) or {}
        rows = data.get("ig_stories", []) if isinstance(data, dict) else data
        for e in rows or []:
            for u, ts, t in media_items(e):
                stories.append(located({"ts": ts, "media": [p for p in [md.resolve(u)] if p]}, e))
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
    handle, name, bio = None, None, ""
    for f in first(root, "../personal_information/personal_information/personal_information.json",
                   "personal_information/personal_information/personal_information.json", "account_information/personal_information.json"):
        data = load(f) or {}
        for u in data.get("profile_user", []) if isinstance(data, dict) else []:
            smd = u.get("string_map_data") or {}
            handle = handle or fix((smd.get("Username") or {}).get("value", "")) or None
            name = name or fix((smd.get("Name") or {}).get("value", "")) or None
            bio = bio or fix((smd.get("Bio") or {}).get("value", ""))
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
            rows.append(located({"ts": e.get("timestamp"), "caption": text, "media": media, "album": ""}, e))
    for f in sorted((act / "album").glob("*.json")):
        a = load(f) or {}
        for ph in a.get("photos") or []:
            uri = ph.get("uri")
            if uri and (root / uri).exists():
                rows.append(located({"ts": ph.get("creation_timestamp"), "caption": fix(ph.get("title") or ""),
                                     "media": [str((root / uri).resolve())], "album": fix(a.get("name") or "")}, ph))
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
    d.update(handle=data.get("handle"), name=data.get("name"), bio=data.get("bio") or "",
             source=data.get("source") or "connected account",
             found={k: [str(f)] for k in keys if d[k]})
    return d


DAY_IN_NAME = re.compile(r"(?<!\d)(20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")
CAMERA_WORD = re.compile(r"(img|dsc|dscn|dji|pxl|mvimg|photo|image|\d+)", re.I)


def name_words(f):
    """The words a photo's file name carries once its date and camera counters are out: "lisbon belem" from
    2026-03-08_lisbon-belem.jpg, nothing from IMG_4512.jpg."""
    words = re.sub(r"[_.-]+", " ", DAY_IN_NAME.sub(" ", Path(f).stem)).split()
    return " ".join(w for w in words if not CAMERA_WORD.fullmatch(w))


def photo_facts(p):
    """(unix time, (lat, lon) or None) from a photo's EXIF, else the date its file name carries (2026-03-08_fes.jpg,
    IMG_20260308_1412.jpg), else the file time; a photo without EXIF has no geotag."""
    ts, g = None, None
    try:
        from PIL import Image
        with Image.open(p) as im:
            ex = im.getexif()
            v = ex.get(36867) or ex.get(306) or (ex.get_ifd(0x8769) or {}).get(36867)
            gps = ex.get_ifd(0x8825) or {}
        if v:
            ts = int(dt.datetime.strptime(str(v)[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
        if gps.get(2) and gps.get(4):
            deg = lambda t: float(t[0]) + float(t[1]) / 60 + float(t[2]) / 3600
            lat, lon = deg(gps[2]), deg(gps[4])
            lat = -lat if str(gps.get(1, "N")).upper().startswith("S") else lat
            lon = -lon if str(gps.get(3, "E")).upper().startswith("W") else lon
            g = (round(lat, 6), round(lon, 6))
    except Exception:
        pass
    m = None if ts else DAY_IN_NAME.search(Path(p).stem)
    if m:
        ts = int(dt.datetime(int(m[1]), int(m[2]), int(m[3]), 12, tzinfo=dt.timezone.utc).timestamp())
    return ts or int(Path(p).stat().st_mtime), g


def read_photos(folder):
    folder = Path(folder)
    files = sorted(f for f in folder.rglob("*") if f.suffix.lower() in IMG and f.is_file())
    posts = []
    for f in files:
        ts, g = photo_facts(f)
        row = {"ts": ts, "caption": "", "media": [str(f.resolve())], "likes": None, "comments": None,
               "folder": f.parent.name if f.parent != folder else folder.name}
        if g:
            row["lat"], row["lon"] = g
        if name_words(f):
            row["file"] = name_words(f)
        posts.append(row)
    vids = [{"ts": int(f.stat().st_mtime), "caption": "", "media": [str(f.resolve())], "folder": f.parent.name}
            for f in sorted(Path(folder).rglob("*")) if f.suffix.lower() in VID]
    return posts, vids


def largest_photo_folder(root):
    best = (0, None)
    for d, kids in walk(root):
        n = sum(1 for k in kids if k.suffix.lower() in IMG)
        if n > best[0]:
            best = (n, d)
    return best[1] if best[0] >= 8 else None


def year_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).year


def pick_year(rows, asked):
    if asked:
        return asked, f"The year is {asked}, as asked."
    counts = {}
    for r in rows:
        if r.get("ts"):
            counts[year_of(r["ts"])] = counts.get(year_of(r["ts"]), 0) + 1
    if not counts:
        return dt.date.today().year, "No dates in the data; used the current year."
    full = [y for y, n in counts.items() if n >= 12]
    y = max(full) if full else max(counts)
    return y, f"The year is {y}: the latest year with enough posts, reels and stories ({counts[y]})."


def write_howto():
    """The run's brief.md, beside out/, when every door is closed: out/ holds only the deliverables."""
    _env.write_text(Path("brief.md"), f"# A year of places: no data found\n\n## Assumptions\n\n- No Instagram export and no folder of "
                                      f"photos was found in this workspace.\n\n## What to do\n\n{HOWTO}\n")


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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--year", type=int)
    ap.add_argument("--photos", help="a folder of photos the person named")
    ap.add_argument("--pulled", action="append", default=[], help="a folder holding items.json the agent pulled")
    ap.add_argument("--door", action="append", default=[], help='name="open: ..." or name="closed: why"')
    a = ap.parse_args()
    _env.enter_run(new=True)
    root = _env.home_path(a.root).resolve()
    Path("library").mkdir(parents=True, exist_ok=True)
    assumptions, doors = [], {}
    for x in a.door:
        k, _, v = x.partition("=")
        doors[k.strip()] = v.strip() or "tried"
    keys = ("posts", "reels", "stories", "likes", "saved", "comments", "followers", "following", "facebook")
    d = {k: [] for k in keys}
    d.update(handle=None, name=None, bio="", found={}, notes=[])
    sources = []
    pulled = [_env.home_path(p) for p in a.pulled] or ([_env.HOME / "pulled"] if (_env.HOME / "pulled/items.json").exists() else [])
    for folder in pulled:
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
    if not d["posts"] and not d["reels"]:
        _env.need("PIL")
        folder = _env.home_path(a.photos) if a.photos else largest_photo_folder(root)
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
            write_howto()
            print(HOWTO)
            return 3
    year, why = pick_year(d["posts"] + d["reels"] + d["stories"], a.year)
    assumptions.append(why)
    # a handle is kept without its "@", which every place that shows it adds
    handle = (d["handle"] or "").lstrip("@") or None
    assumptions.append(f"Handle: @{handle}." if handle else "No username in the data; the film shows the year alone where a handle would stand.")
    inyear = lambda rows: sorted((r for r in rows if r.get("ts") and year_of(r["ts"]) == year), key=lambda r: r["ts"])
    lib = {k: inyear(d[k]) for k in ("posts", "reels", "stories", "likes", "saved", "comments", "facebook")}
    dates = [r["ts"] for r in lib["posts"] + lib["reels"] + lib["stories"]]
    span = {"first": dt.datetime.fromtimestamp(min(dates), dt.timezone.utc).date().isoformat() if dates else None,
            "last": dt.datetime.fromtimestamp(max(dates), dt.timezone.utc).date().isoformat() if dates else None}
    if span["last"] and span["last"] < f"{year}-12-01":
        assumptions.append(f"The data runs to {span['last']}, so the year covers January to that day.")
    if source in ("export", "accounts"):
        missing = [k for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers") if not d["found"].get(k)]
        if missing:
            assumptions.append("Not in the data (left out): " + ", ".join(missing) + ".")
    shelve(lib)
    no_media = sum(1 for p in lib["posts"] if not p["media"])
    if no_media:
        assumptions.append(f"{no_media} posts point at media files that are not there; they count but show no photo.")
    tagged = sum(1 for k in ("posts", "reels", "stories", "facebook") for r in lib[k] if r.get("lat") is not None)
    total = sum(len(lib[k]) for k in ("posts", "reels", "stories", "facebook"))
    out = {"source": source, "sources": sources, "doors": doors, "root": str(root), "handle": handle, "name": d["name"],
           "bio": d["bio"], "geotagged": tagged,
           "year": year, "range": span, "found": d["found"], **lib, "followers": d["followers"],
           "following": d["following"], "assumptions": assumptions + d["notes"]}
    _env.write_json("library.json", out)
    print(f"source: {source}   handle: {'@' + handle if handle else 'none'}   year: {year}   range: {span['first']} to {span['last']}")
    print("  ".join(f"{k} {len(out[k])}" for k in ("posts", "reels", "stories", "likes", "saved", "comments", "followers",
                                                   "following", "facebook")))
    print(f"geotagged rows: {tagged} of {total}")
    for k, v in doors.items():
        print(f"door {k}: {v}")
    for x in out["assumptions"]:
        print("assumption:", x)
    print("wrote library.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
