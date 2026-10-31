#!/usr/bin/env python3
"""The film's material, measured from the run: the photographs graded to one light, each with where its subject sits,
and the story the boards tell, the moments in the order the film plays them.

USAGE (from the workspace root, after research.py and brand.py system; storyboard.py draft runs it):
    python3 S/scripts/material.py

Reads brand.json, library.json, photo_index.json, research.json, taste.json and grade.json; writes
public/studio/photos/ (each photograph graded), public/studio/posted/ (each photograph as it was posted, for a card
whose finish shows it so), studio.json (the facts every board reads), and with a folder of photographs cast.json and
cast.png.

The story is taste.json `moments` as the agent curated them, in that order, each on its post's own photograph. While
taste.json is still research.py's draft, the story is each pillar's best-liked moment, the pillars in the order of
their shares, never a post that breaks the feed's habits (research.json `outliers`) and never a line said twice; its
peak, the best liked, plays last. The film opens on the best-liked moment the story does not play, and never on a
plain photograph (mostly sky, sea or wall): the first of those that has a subject, else the story's first.

The photographs are the posts' own pictures, or the folder the setting BRAND_PHOTOS names (a folder of the person's
photographs that stand in for the posts' pictures). With the folder each photograph is cast to the pillar whose words
its file name carries, the rest shared out so every pillar has photographs in proportion to its share, and each
pillar's first photograph plays it without words. A feed whose photographs carry no captions plays its best-liked
photographs without words. cast.json records the folder's cast: look at cast.png, move a photograph to the pillar it
shows in cast.json, and run this again; the cast is kept while the folder is the same.
"""
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PUB = Path("public")
OUT = PUB / "studio"
IMAGES = (".jpg", ".jpeg", ".png", ".webp", ".heic")
# the most moments a story plays
MOST = 6
# the photographs graded as the film's possible opening, the best liked first; the first that is not plain opens it
HOOK_TRIES = 4


def open_rgb(path):
    from PIL import Image, ImageOps
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def ffgrade(src, dest, filt, width=1600):
    """The photograph matched to the film (grade.match), then graded with the film's filter, `width` px wide."""
    from PIL import Image
    import grade
    with Image.open(src) as im:
        first = grade.match(im)
    subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", f"{first},{filt},scale={width}:-2", "-q:v", "2", str(dest)],
                   check=True)


def ffposted(src, dest, width=1600):
    """The photograph as it was posted, `width` px wide."""
    subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-vf", f"scale={width}:-2", "-q:v", "2", str(dest)],
                   check=True)


def tokens(text):
    return {w for w in re.split(r"[^a-z]+", text.lower()) if len(w) > 2}


def vocab(brand_pillar, research_pillar):
    """A pillar's words, weighted by rank: its name, then its caption words, its items and its labels."""
    out = {}
    words = [brand_pillar["name"], research_pillar.get("name", "")] + research_pillar.get("words", []) + \
        research_pillar.get("items", []) + research_pillar.get("labels", [])
    for k, phrase in enumerate(words):
        for w in tokens(phrase):
            if w not in {"the", "and", "home", "side", "first", "coming", "yours", "spot", "seat"}:
                out[w] = max(out.get(w, 0), 1 / (1 + 0.15 * k))
    return out


def cast_folder(files, pillars, rpillars):
    """Each photograph of the folder to a pillar: by the pillar words its file name carries, the rest shared out so
    every pillar holds photographs in proportion to its share."""
    vs = [vocab(p, rpillars[i] if i < len(rpillars) else {}) for i, p in enumerate(pillars)]
    cast, rest = {}, []
    for f in files:
        t = tokens(Path(f).stem)
        score = [sum(v.get(w, 0) for w in t) for v in vs]
        best = max(range(len(pillars)), key=lambda i: score[i])
        if score[best] > 0:
            cast[Path(f).name] = pillars[best]["name"]
        else:
            rest.append(Path(f).name)
    for name in rest:
        held = {p["name"]: sum(1 for v in cast.values() if v == p["name"]) for p in pillars}
        p = min(pillars, key=lambda p: (held[p["name"]] + 1) / max(p["share"], 0.01))
        cast[name] = p["name"]
    return cast


def contact(cast, folder_of, heroes, pillars, path):
    """cast.png: one row of photographs per pillar, each named, the hero marked."""
    from PIL import Image, ImageDraw
    th, pad, label, per = 180, 12, 300, 10
    rows = [[n for n, p in cast.items() if p == q["name"]] for q in pillars]
    lines = [max(1, -(-len(r) // per)) for r in rows]
    width = label + min(per, max(1, max((len(r) for r in rows), default=1))) * (th + pad) + pad
    sheet = Image.new("RGB", (width, sum(lines) * (th + 60) + pad), (24, 20, 16))
    d = ImageDraw.Draw(sheet)
    big, small = _env.pil_font(30, "text"), _env.pil_font(15, "text")
    top = pad
    for q, names, nl in zip(pillars, rows, lines):
        d.text((pad, top + 8), q["name"], font=big, fill=(243, 237, 226))
        d.text((pad, top + 48), f"{len(names)} photographs", font=small, fill=(180, 170, 150))
        for k, n in enumerate(sorted(names)):
            x = label + pad + (k % per) * (th + pad)
            y = top + (k // per) * (th + 60)
            im = open_rgb(folder_of[n])
            m = min(im.size)
            im = im.crop(((im.width - m) // 2, (im.height - m) // 2, (im.width + m) // 2, (im.height + m) // 2)).resize((th, th))
            sheet.paste(im, (x, y))
            mark = "HERO" if heroes.get(q["name"]) == n else ""
            if mark:
                d.rectangle((x, y, x + th - 1, y + th - 1), outline=(246, 200, 80), width=5)
                d.text((x + 8, y + 6), mark, font=big, fill=(246, 200, 80))
            d.text((x, y + th + 4), n[:22], font=small, fill=(220, 210, 190))
        top += nl * (th + 60)
    sheet.save(path)


def _line(text):
    return re.sub(r"[^a-z ]+", "", (text or "").lower()).strip()[:40]


def story(curated, lib, res, drafted):
    """The moments the film plays, in order, each with its likes: the agent's own (taste.json `moments`), or while
    taste.json is the draft each pillar's best-liked moment that breaks no habit, then a second round while the story
    is under four, the peak (best liked) moved last."""
    rows = lib["posts"] + lib["reels"]
    likes = lambda m: (rows[m["row"]].get("likes") or 0) if isinstance(m.get("row"), int) and m["row"] < len(rows) else 0
    ms = [dict(m, likes=likes(m)) for m in curated if m.get("photo")]
    if not drafted:
        return ms[:MOST]
    off = {_line(o.get("caption")) for o in res.get("outliers", [])}
    pool = [m for m in ms if m.get("pillar") and m.get("line") and _line(m["line"]) not in off]
    order = [p["name"] for p in res.get("pillars", [])]
    out, said = [], set()
    for rnd in range(2):
        for name in order:
            if len(out) >= (MOST - 1 if rnd == 0 else 4):
                break
            mine = sorted((m for m in pool if m["pillar"] == name and _line(m["line"]) not in said), key=lambda m: -m["likes"])
            if mine:
                out.append(mine[0])
                said.add(_line(mine[0]["line"]))
    if not out:
        out = sorted((m for m in ms if _line(m.get("line")) not in off), key=lambda m: -m["likes"])[:4]
    if not out:
        return []
    peak = max(out, key=lambda m: m["likes"])
    return [m for m in out if m is not peak] + [peak]


def hook_pool(curated, lib, res, told):
    """The photographs the film may open on, best liked first: every moment's photograph the story does not already
    play, never a post that breaks the feed's habits; the story's own photographs after them."""
    rows = lib["posts"] + lib["reels"]
    likes = lambda m: (rows[m["row"]].get("likes") or 0) if isinstance(m.get("row"), int) and m["row"] < len(rows) else 0
    off = {_line(o.get("caption")) for o in res.get("outliers", [])}
    played = {Path(m["photo"]).name for m in told}
    rest = sorted((m for m in curated if m.get("photo") and Path(m["photo"]).name not in played and _line(m.get("line")) not in off),
                  key=lambda m: -likes(m))
    return [Path(m["photo"]).name for m in rest[:HOOK_TRIES]] + [Path(m["photo"]).name for m in told]


def build():
    _env.need("PIL")
    import grade
    brand = _env.read_json("brand.json")
    lib = _env.read_json("library.json")
    idx = _env.read_json("photo_index.json")
    res = _env.read_json("research.json")
    taste = _env.read_json("taste.json") or {}
    if not (brand and lib and idx is not None and res):
        sys.exit("brand.json, library.json, photo_index.json and research.json are needed: run research.py and brand.py system first")
    filt = grade.ensure_recipe()["filter"]
    # studio.json names every file below: it goes before the first of them changes and comes back after the last
    Path("studio.json").unlink(missing_ok=True)
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "photos").mkdir(parents=True, exist_ok=True)
    (OUT / "posted").mkdir(parents=True, exist_ok=True)
    pillars = brand["pillars"]
    rows = lib["posts"] + lib["reels"]
    posts = sorted((e for e in idx if e["kind"] == "post"), key=lambda e: e["ts"])
    likes_of = lambda e: (rows[e["row"]].get("likes") or 0) if isinstance(e.get("row"), int) and e["row"] < len(rows) else 0
    setting = os.environ.get("BRAND_PHOTOS")
    folder = _env.at_root(setting).resolve() if setting else None
    cast, moments = {}, []
    if folder:
        files = sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMAGES)
        if not files:
            sys.exit(f"BRAND_PHOTOS names {folder}, which holds no photographs")
        folder_of = {f.name: f for f in files}
        old = _env.read_json("cast.json") or {}
        kept = old.get("folder") == str(folder)
        cast = {n: p for n, p in (old.get("photos") or {}).items() if kept and n in folder_of and p in {q["name"] for q in pillars}}
        if pillars:
            cast.update(cast_folder([n for n in folder_of if n not in cast], pillars, res.get("pillars", [])))
    else:
        folder_of = {Path(e["src"]).name: Path(e["src"]) for e in posts}
        moments = story(taste.get("moments") or [], lib, res, "research.py draft" in str(taste.get("written_by", "")))
    if not folder_of:
        sys.exit("no photograph to play: the posts have no pictures and BRAND_PHOTOS is not set")
    heroes = {q["name"]: n for q in pillars for n in sorted(k for k, p in cast.items() if p == q["name"])[:1]}
    if folder:
        shown = list(heroes.values()) or sorted(folder_of)[:MOST]
        opens = [n for n in sorted(folder_of) if n not in shown][:HOOK_TRIES] + shown
        beats = [{"photo": Path(heroes[q]).stem, "line": "", "pillar": q, "likes": 0} for q in heroes] or \
                [{"photo": Path(n).stem, "line": "", "pillar": None, "likes": 0} for n in shown]
    elif moments:
        shown = [Path(m["photo"]).name for m in moments if Path(m["photo"]).name in folder_of]
        opens = [n for n in hook_pool(taste.get("moments") or [], lib, res, moments) if n in folder_of]
        beats = [{k: m.get(k) for k in ("date", "line", "pillar", "people", "place", "likes")} | {"photo": Path(m["photo"]).stem}
                 for m in moments if Path(m["photo"]).name in folder_of]
    else:
        ranked = sorted(posts, key=lambda e: -likes_of(e))
        best = ranked[:MOST]
        shown = [Path(e["src"]).name for e in posts if e in best]
        opens = [Path(e["src"]).name for e in ranked[MOST:MOST + HOOK_TRIES]] + shown
        beats = [{"photo": Path(n).stem, "line": "", "pillar": None, "likes": 0} for n in shown]

    def graded(n):
        dest = OUT / "photos" / f"{Path(n).stem}.jpg"
        ffgrade(folder_of[n], dest, filt)
        ffposted(folder_of[n], OUT / "posted" / dest.name)
        return n, dest
    with ThreadPoolExecutor(8) as ex:
        done = dict(ex.map(graded, list(dict.fromkeys(shown + opens[:HOOK_TRIES]))))
    import picks  # reads the photographs with Pillow, which setup.py checks before any movement runs
    photos = {}
    for n, p in done.items():
        im = open_rgb(p)
        where, plain = picks.subject(p)
        photos[Path(n).stem] = {"file": f"studio/photos/{Path(n).stem}.jpg", "posted": f"studio/posted/{Path(n).stem}.jpg",
                                "aspect": round(im.height / im.width, 4),
                                "subject": where, "plain": plain}
    if folder:
        _env.write_json("cast.json", {
            "about": "Which pillar each photograph plays. Move a photograph to the pillar it shows, then run storyboard.py draft again.",
            "folder": str(folder), "photos": dict(sorted(cast.items())), "heroes": heroes})
        contact(cast, folder_of, heroes, pillars, "cast.png")
    out = {
        "handle": brand["handle"], "name": lib.get("name"), "bio": lib.get("bio"), "statement": brand["statement"],
        "pillars": [p["name"] for p in pillars], "voice": brand.get("voice") or {},
        "photos": photos, "story": [b for b in beats if b["photo"] in photos],
        "hook": next((Path(n).stem for n in opens if Path(n).stem in photos and not photos[Path(n).stem]["plain"]),
                      next((b["photo"] for b in beats if b["photo"] in photos), None)),
    }
    _env.write_json("studio.json", out)
    print(f"wrote studio.json: {len(photos)} photographs, a story of {len(out['story'])} moments, "
          f"{sum(1 for b in out['story'] if b['line'])} with their words")
    return out


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter()
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
