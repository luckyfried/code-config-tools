#!/usr/bin/env python3
"""Movement 1, research: each visit's moment, each place's photos and the film's cast. Reads library.json and
places.json; writes photo_index.json, picks.json, photos/*.jpg, cast.json and cast.png.

USAGE (from the workspace root; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/picks.py [--per-place 6] [--set DIR]

--set DIR names the person's own set of photographs of the year's places: a folder per place, named by the place
(its id or its name, accents and case aside), each ranked best first by a manifest.json beside the files ({items:
[{rank, file, description}]}) or, without one, by file name. The set is read as files, never run or changed. With a
set, the cast comes from it; without one, from each place's best photos in picks.json.

A visit's moment is drafted as the first of their posts, reels and stories from that place within the visit's dates:
its caption (hashtags and emoji set aside) as their line, with the people it tags, and its photograph. Caption and
photograph come from the one post, so a moment whose post has no photograph (a reel) is wordless on the place's own
print. Every caption of the visit follows it in time order as a candidate; the line kept in taste.json wins.

cast.json lists the visits in route order ({place, n, from, shots}), each with the photographs it shows, the first
the visit's own print: the moment's photograph, set or no set, then the best the place has that an earlier visit
has not shown, two in all for a visit in the home region, three for a far place. cast.png shows every visit's shots beside the place's other photographs. Look at it
and correct cast.json by eye before storyboards: a cast whose visits still match the route is kept as you set it on
every later run.

Scores every photo of the year (color, contrast, exposure), finds each one's focal point (where the detail is,
so a cover crop keeps it), converts HEIC and rotates by EXIF, and saves a 1600 px JPEG copy in photos/.
Every photo carries the place places.py gave its post or story. picks.json carries, per place, its best photos
(one from each visit of a place visited twice, then by how the photograph reads), its own reels with a poster frame
each (ffmpeg, 40% of the way in), the "opener" chapter (the year's most striking photo taken away from home), and
the moments, one per visit of the route ({place, n, from, to, line, with, post, photo, captions: [{post, line}]}).
"""
import collections
import datetime as dt
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageFilter, ImageOps, ImageStat  # noqa: E402

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

PHOTOS = Path("photos")
VIDEO = {".mp4", ".mov", ".m4v"}
IMG = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
SHOTS = {"near": 2, "far": 3}
KINDS = ("posts", "reels", "stories", "facebook")
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27bf\u2b50\u2728\ufe0f\u200d]")


def day(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()


def said(caption):
    """A caption as their line: hashtags and emoji set aside, their words and mentions as they wrote them."""
    s = EMOJI.sub("", re.sub(r"#\w+", "", caption or ""))
    return re.sub(r"\s+", " ", s).strip(" ,;-")


def image_of(row):
    return next((m for m in row.get("media") or [] if Path(m).suffix.lower() in IMG), None)


def visit_moments(lib, pl):
    """One moment per visit of the route, in route order: its first post, the caption and the photograph together."""
    rowmap = pl.get("rows") or {}
    rows = [(r["ts"], f"{k}:{i}", r) for k in KINDS for i, r in enumerate(lib.get(k) or []) if r.get("ts") is not None]
    rows.sort(key=lambda t: (t[0], t[1]))
    out, seen = [], collections.Counter()
    for v in pl.get("route_visits") or []:
        k = v["place"]
        seen[k] += 1
        mine = [(key, r) for ts, key, r in rows if rowmap.get(key) == k and v.get("from") and v["from"] <= day(ts) <= v["to"]]
        key, r = mine[0] if mine else (None, {})
        line = (said(r.get("caption")) or None) if image_of(r) else None
        out.append({"place": k, "n": seen[k], "from": v.get("from"), "to": v.get("to"), "line": line,
                    "with": re.findall(r"@([A-Za-z0-9._]*[A-Za-z0-9_])", line or ""), "post": key,
                    "captions": [{"post": key_, "line": said(r_.get("caption"))} for key_, r_ in mine if said(r_.get("caption"))]})
    return out


def own_print(lib, m):
    """A moment's own photograph: the one the curation pairs with it (`photo`), else its post's photograph as photos/
    holds it; None for a post with none (a reel), whose moment is wordless."""
    if m.get("photo"):
        return m["photo"]
    kind, _, i = (m.get("post") or "").partition(":")
    rows = lib.get(kind) or []
    image = image_of(rows[int(i)]) if i.isdigit() and int(i) < len(rows) else None
    ph = prepare(image) if image else None
    return shown(ph) if ph else None


def open_image(path, draft=None):
    im = Image.open(path)
    if draft and im.format == "JPEG":
        im.draft("RGB", draft)
    im = ImageOps.exif_transpose(im)
    return im.convert("RGB")


def prepare(path):
    """A 1600 px JPEG copy in photos/ (HEIC converted, EXIF rotation applied). Returns its path or None."""
    src = Path(path)
    dest = PHOTOS / (hashlib.sha1(str(src.resolve()).encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    try:
        im = open_image(src)
    except Exception as e:
        print(f"skip {src.name}: cannot open ({e}){' ; HEIC needs pillow-heif' if src.suffix.lower() in ('.heic', '.heif') else ''}",
              file=sys.stderr)
        return None
    im.thumbnail((1600, 1600), Image.LANCZOS)
    PHOTOS.mkdir(parents=True, exist_ok=True)
    # a copy is whole once it carries its name, so a copy cut short is made again
    part = dest.with_name(f".{dest.name}.part")
    im.save(part, "JPEG", quality=90)
    os.replace(part, dest)
    return str(dest.resolve())


def poster(video):
    """A reel's poster frame as a 1600 px JPEG in photos/, 40% of the way in. Returns its path or None."""
    src = Path(video)
    dest = PHOTOS / (hashlib.sha1((str(src.resolve()) + "#poster").encode()).hexdigest()[:12] + ".jpg")
    if dest.exists():
        return str(dest.resolve())
    PHOTOS.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    try:
        at = float(r.stdout.strip()) * 0.4
    except ValueError:
        at = 0.5
    part = dest.with_name(f".{dest.stem}.part.jpg")
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(src), "-frames:v", "1",
                    "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", str(part)], capture_output=True)
    if not (part.exists() and part.stat().st_size > 0):
        part.unlink(missing_ok=True)
        return None
    os.replace(part, dest)
    return str(dest.resolve())


def analyse(path):
    im = open_image(path, draft=(160, 200))
    w, h = im.size
    small = im.resize((64, max(1, round(64 * h / w))))
    hsv = small.convert("HSV")
    sat = ImageStat.Stat(hsv.getchannel("S")).mean[0] / 255
    light = ImageStat.Stat(small.convert("L"))
    bright, contrast = light.mean[0] / 255, light.stddev[0] / 128
    expo = 1 - min(1, abs(bright - 0.52) * 2.2)
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES)
    px = edges.load()
    sw, sh = edges.size
    tot = sx = sy = 0
    for y in range(sh):
        for x in range(sw):
            v = px[x, y]
            tot += v
            sx += v * x
            sy += v * y
    fx, fy = (sx / tot / sw, sy / tot / sh) if tot else (0.5, 0.5)
    q = small.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:15]
    cols = sorted(q.getcolors(), reverse=True)
    dom = [{"rgb": pal[3 * i:3 * i + 3], "share": round(n / (sw * sh), 3)} for n, i in cols]
    score = round(0.45 * sat + 0.35 * min(1, contrast) + 0.2 * expo, 3)
    return {"w": w, "h": h, "score": score, "bright": round(bright, 3),
            "focal": [round(min(0.8, max(0.2, fx)), 2), round(min(0.8, max(0.2, fy)), 2)], "colors": dom}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-place", type=int, default=6)
    ap.add_argument("--set", help="a folder of the person's photographs, one folder per place")
    a = ap.parse_args()
    _env.enter_run()
    d = _env.read_json("library.json")
    pl = _env.read_json("places.json")
    if not d or not pl:
        sys.exit("run gather.py and places.py first")
    rowmap = pl.get("rows") or {}
    index, skipped = [], 0
    for kind in ("posts", "stories", "facebook"):
        for i, r in enumerate(d.get(kind) or []):
            for m in r.get("media") or []:
                if Path(m).suffix.lower() in VIDEO:
                    continue
                try:
                    an = analyse(m)
                except Exception:
                    skipped += 1
                    continue
                month = dt.datetime.fromtimestamp(int(r["ts"]), dt.timezone.utc).month
                index.append({"src": m, "kind": kind.rstrip("s") if kind != "facebook" else "facebook", "ts": r["ts"], "month": month,
                              "place": rowmap.get(f"{kind}:{i}"), **an})
    if not index:
        sys.exit("no photos could be opened; the film needs at least one photo")
    _env.write_json("photo_index.json", index)
    visits = collections.defaultdict(list)
    for v in pl.get("visits") or []:
        visits[v["place"]].append(v)
    out = {"places": {}, "chapters": {}, "focal": {}, "source_of": {}}

    def keep(e):
        ph = prepare(e["src"])
        if ph:
            out["focal"][ph] = f"{e['focal'][0] * 100:.0f}% {e['focal'][1] * 100:.0f}%"
            out["source_of"][ph] = e["src"]
        return ph

    def worth(e):
        return e["score"] + (0.05 if e["kind"] == "post" else 0) - (0.3 if e["bright"] < 0.18 else 0)

    for p in pl["places"]:
        mine = sorted((e for e in index if e.get("place") == p["id"]), key=lambda e: -worth(e))
        chosen = []
        for v in visits.get(p["id"], []) if p["visits"] > 1 and not p["home"] else []:
            lo, hi = v["from"], v["to"]
            first = next((e for e in mine if lo <= dt.datetime.fromtimestamp(int(e["ts"]), dt.timezone.utc).date().isoformat() <= hi
                          and e not in chosen), None)
            if first:
                chosen.append(first)
        for e in mine:
            if len(chosen) >= a.per_place:
                break
            if e not in chosen:
                chosen.append(e)
        chosen.sort(key=lambda e: -worth(e))
        photos = [ph for ph in (keep(e) for e in chosen) if ph]
        clips = []
        for c in p.get("clips") or []:
            still = poster(c)
            if still:
                clips.append({"video": c, "poster": still})
                out["source_of"][still] = c
        out["places"][p["id"]] = {"photos": photos, "clips": clips,
                                  "bright": [e["bright"] for e in chosen], "colors": [e["colors"] for e in chosen[:3]]}
    away = [e for e in index if e.get("place") and e["place"] != pl.get("home") and e["bright"] > 0.25] or index
    opener = max(away, key=worth)
    op = keep(opener)
    out["chapters"]["opener"] = [op] if op else []
    moments = visit_moments(d, pl)
    for m in moments:
        m["photo"] = own_print(d, m)
    out["moments"] = moments
    _env.write_json("picks.json", out)
    empty = [p["name"] for p in pl["places"] if not out["places"][p["id"]]["photos"]]
    print(f"indexed {len(index)} photos ({skipped} could not be opened); prepared {len(list(PHOTOS.glob('*.jpg')))} in photos/")
    for p in pl["places"]:
        got = out["places"][p["id"]]
        print(f"  {p['name']:<14} {len(got['photos'])} photos, {len(got['clips'])} of their reels")
    if empty:
        print("no photo at: " + ", ".join(empty) + " (their beat uses the map alone)")
    options = set_photos(_env.home_path(a.set), pl) if a.set else \
        {k: [(str(Path(f).resolve()), "") for f in v["photos"]] for k, v in out["places"].items()}
    cast = write_cast(pl, options, a.set, moments)
    worded = sum(1 for m in moments if m["line"])
    print(f"moments: {worded} of {len(moments)} visits have a line of theirs; the rest are wordless")
    print(f"wrote picks.json, photo_index.json and cast.json ({len(cast['visits'])} visits, {cast['kept']}); look at cast.png")
    return 0


def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s.lower() if c.isalnum())


def set_photos(root, pl):
    """{place id: [(file, description)]} best first, from a photo set: a folder per place."""
    import json
    if not root.is_dir():
        sys.exit(f"--set {root} is not a folder")
    folders = {norm(d.name): d for d in root.iterdir() if d.is_dir()}
    out = {}
    for p in pl["places"]:
        d = folders.get(norm(p["id"])) or folders.get(norm(p["name"]))
        if not d:
            continue
        man = d / "manifest.json"
        if man.exists():
            items = sorted(json.loads(man.read_text()).get("items") or [], key=lambda it: it.get("rank", 1e9))
            files = [(d / Path(it["file"]).name, it.get("description") or it.get("title") or "") for it in items]
        else:
            files = [(f, "") for f in sorted(d.iterdir()) if f.suffix.lower() in IMG]
        out[p["id"]] = [(str(f), why) for f, why in files if f.is_file() and f.suffix.lower() in IMG]
    return out


def shown(f):
    """A photograph's path as cast.json names it: from the workspace root when it lies inside it."""
    try:
        return str(Path(f).resolve().relative_to(_env.HOME))
    except ValueError:
        return str(Path(f).resolve())


def write_cast(pl, options, set_dir, moments=()):
    visits, used, seen = [], collections.defaultdict(set), collections.Counter()
    far = set(pl.get("far") or [])
    print_of = {(m["place"], m["n"]): str(_env.home_path(m["photo"]).resolve()) for m in moments if m.get("photo")}
    for v in pl.get("route_visits") or [{"place": k} for k in pl.get("route") or []]:
        k = v["place"]
        seen[k] += 1
        opts = [f for f, _ in options.get(k) or []]
        own = print_of.get((k, seen[k]))
        rest = [f for f in opts if f != own]
        free = [f for f in rest if f not in used[k]] or rest
        free = [own] + free if own else free
        shots = free[:SHOTS["far" if k in far else "near"]]
        used[k].update(shots)
        visits.append({"place": k, "n": seen[k], "from": v.get("from"), "shots": [shown(f) for f in shots]})
    # a cast.json they corrected is kept while its visits are the route's; one with no visits list is not a cast
    have = _env.read_json("cast.json") or {}
    same = "visits" in have and [(v["place"], v["n"]) for v in have["visits"]] == [(v["place"], v["n"]) for v in visits]
    cast = have if same else {"set": shown(_env.home_path(set_dir)) if set_dir else None, "visits": visits}
    _env.write_json("cast.json", cast)
    contact(cast, options)
    return dict(cast, kept="kept as you set it" if same else "from the default rule")


def contact(cast, options):
    """cast.png: a row per visit, its shots large and numbered, the place's other photographs small beside them."""
    from PIL import ImageDraw
    rows, H, h = [], 220, 120
    font = _env.pil_font(18, "label")
    for v in cast["visits"]:
        shots = [str(_env.home_path(s["file"] if isinstance(s, dict) else s)) for s in v["shots"]]
        rest = [f for f, _ in options.get(v["place"]) or [] if str(Path(f).resolve()) not in {str(Path(s).resolve()) for s in shots}]
        tiles = []
        for f, size in [(s, H) for s in shots] + [(f, h) for f in rest]:
            try:
                im = open_image(f, (size * 3, size * 3))
            except Exception:
                continue
            im.thumbnail((size * 2, size))
            tiles.append(im)
        rows.append((f"{v['place']} visit {v['n']}  ({len(shots)} shots, then the place's other photographs)", tiles, len(shots)))
    W = max([sum(t.size[0] + 8 for t in r[1]) + 16 for r in rows] + [600])
    sheet = Image.new("RGB", (W, sum(H + 40 for _ in rows) + 16), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    y = 8
    for label, tiles, n in rows:
        d.text((8, y), label, fill=(240, 236, 226), font=font)
        x = 8
        for j, t in enumerate(tiles):
            sheet.paste(t, (x, y + 28))
            if j < n:
                d.rectangle([x, y + 28, x + t.size[0] - 1, y + 28 + t.size[1] - 1], outline=(242, 170, 46), width=3)
                d.text((x + 6, y + 32), str(j + 1), fill=(242, 170, 46), font=font)
            x += t.size[0] + 8
        y += H + 40
    sheet.save(".cast.png.part", "PNG")
    os.replace(".cast.png.part", "cast.png")


if __name__ == "__main__":
    sys.exit(main())
