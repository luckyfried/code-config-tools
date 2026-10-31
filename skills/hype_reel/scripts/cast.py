#!/usr/bin/env python3
"""Who plays each part: the person's own photographs and the subject's own stills and footage cast into the film, by
rule.

USAGE (in a run, after research; S = this skill's folder):
    python3 S/scripts/cast.py looks     # looks.json: where each photograph's subject sits, plus looks.png, their
                                        # photographs and the subject's stills as a numbered sheet with each box drawn
    python3 S/scripts/cast.py show      # print the cast the storyboards will use, with the rule behind each part

What a photograph shows comes from its own words (library.json "feed": its caption, title or file name), read as
classes: people (how many, a pair, a gathering), a place (the sea, a street, a room they named), night and a low sun
(which keep their own color). Each photograph's entry in looks.json is keyed by its path in library.json. Where its
subject sits is a box in the photograph's own fractions: looks writes a first guess from color contrast against the
photograph's edges, and the agent corrects any box it disagrees with after looking at looks.png, setting "checked":
true on the photographs it looked at, and "skip": true on any photograph that should play no part. The subject's
stills take a box the same way, under "subject-<still's name>".

The parts and their rules (no photograph plays two parts). A photograph is of the making when their own words name the
subject or its handle, or, for a subject they made, making it (made, making, building, testing, a sketch, a draft, a
prototype, the studio, the workshop, the kitchen, the rehearsal); for a friend, an account, a creator, a band or a
place only naming it counts. Its line is the line taste.json moments gives that photograph, matched by its path (the
agent curates it from their own words; a photograph with no moment, or an empty line, is wordless):
  hook    the line they asked to lead with (taste.json said.hook), else their latest line about making it, over the
          photograph of the making they wrote it with; with no such photograph the subject's hero still opens, framed
          close, under that line or the subject's name.
  build   the rest of the making they photographed, in the order they made it (the date each carries), at most
          BUILD_MOST, the wordless ones leaving first; the subject's other stills and its footage play between them, so
          the subject is on screen for most of the film.
  reveal  the subject's hero still whole, under the subject's name: the still whose name says hero, cover or main, else
          the first.
  other   their remaining photographs, the closest to the subject's colors first (the countdown and the stories use them).
Each cast photograph of theirs is graded into public/photos/<part>.jpg: white balanced part of the way toward a warm
white (none for night and sunset), its mean light brought halfway to the film's, then the run's grade.json filter. The
subject's stills and footage keep their own color.
"""
import json
import math
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

WARM = (238, 224, 198)
LUMA, WB, LONG = 118, 0.35, 2400
PHOTOS = Path("public/photos")
SUBJECT = Path("public/subject")

PEOPLE = {"people", "person", "woman", "women", "man", "men", "friends", "friend", "couple", "crowd", "guest", "guests",
          "audience", "team", "students", "family", "kids", "children", "dancers", "band", "crew", "us", "we"}
GATHER = {"friends", "crowd", "gathered", "festival", "concert", "wedding", "party", "group", "audience", "guests", "team"}
PAIR = {"couple", "pair", "two"}
PLACE = {"beach", "sea", "surf", "waves", "ocean", "shore", "street", "city", "town", "rooftop", "roof", "park", "market",
         "shop", "studio", "kitchen", "room", "bar", "cafe", "garden", "mountain", "forest", "river", "station", "venue"}
NIGHT = {"night", "sunset", "silhouetted", "silhouette", "dusk"}
NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "dozen": 12}
# the making: words that say a photograph is of making the thing, in any trade
MAKING = {"made", "make", "making", "build", "building", "built", "test", "testing", "tested", "sketch", "sketches",
          "draft", "drafts", "prototype", "prototypes", "sample", "samples", "studio", "workshop", "rehearsal",
          "rehearsing", "recording", "process", "behind", "prep", "prepping", "designing", "design", "sewing", "mixing"}
# the kinds of subject the person did not make (a friend, an account they follow): a photograph of theirs is about
# such a subject only when its words name it or its handle, never because they say "making"
NOT_THEIRS = {"friend", "account", "creator", "band", "place"}
HERO = ("hero", "cover", "main")
CLIPS = (".mp4", ".mov", ".m4v", ".webm")
# the most photographs of the making the film runs through between the hook and the reveal
BUILD_MOST = 6

def words(text):
    """Every word, a hyphenated word counted as its parts (hand-sewn is hand and sewn)."""
    return re.findall(r"[a-z0-9']+", (text or "").lower())

def whole_words(text):
    """Every word with a hyphenated word kept whole (sea-glass and sea-green are colors, not the sea)."""
    return re.findall(r"[a-z0-9'-]+", (text or "").lower())

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def rgb_hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c[:3])

def dist(a, b):
    return math.sqrt(sum((p - q) ** 2 for p, q in zip(a, b)))

def swatches(f, n=4):
    """A photograph's few main colors and their shares."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    im.thumbnail((64, 64))
    q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    tot = sum(c for c, _ in counts) or 1
    return [(tuple(pal[i * 3:i * 3 + 3]), c / tot) for c, i in counts]

def closeness(sw, palette):
    """Mean distance of a photograph's colors to the nearest of a palette's (lower is closer)."""
    if not palette:
        return 0.0
    return sum(share * min(dist(c, p) for p in palette) for c, share in sw)

def subject_guess(f, n=128):
    """A first guess at the subject's box (fractions of the photograph): the pixels far in color from every color of the
    photograph's edges, trimmed of their outer two percent."""
    from PIL import Image, ImageFilter, ImageOps
    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    w, h = im.size
    s = n / max(w, h)
    g = im.resize((max(8, round(w * s)), max(8, round(h * s))), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))
    W, H = g.size
    px = g.load()
    border = [px[x, y] for x in range(W) for y in (0, 1, H - 2, H - 1)] + [px[x, y] for y in range(H) for x in (0, 1, W - 2, W - 1)]
    cents = border[::max(1, len(border) // 12)][:12]
    for _ in range(6):
        groups = [[] for _ in cents]
        for c in border:
            groups[min(range(len(cents)), key=lambda i: dist(c, cents[i]))].append(c)
        cents = [tuple(sum(ch) / len(gr) for ch in zip(*gr)) if gr else cents[i] for i, gr in enumerate(groups)]
    far = [[min(dist(px[x, y], c) for c in cents) for x in range(W)] for y in range(H)]
    flat = sorted(v for row in far for v in row)
    thr = max(40, flat[len(flat) // 2])
    xs = sorted(x for y in range(H) for x in range(W) if far[y][x] > thr)
    ys = sorted(y for y in range(H) for x in range(W) if far[y][x] > thr)
    if len(xs) < 0.03 * W * H:
        return [0.15, 0.15, 0.85, 0.85]
    q = lambda a, t: a[min(len(a) - 1, int(len(a) * t))]
    return [round(q(xs, .02) / W, 3), round(q(ys, .02) / H, 3), round((q(xs, .98) + 1) / W, 3), round((q(ys, .98) + 1) / H, 3)]


def edge_color(im, rows):
    """The median color of a band of rows (a still's ground at its top or its foot)."""
    px = im.load()
    W, _ = im.size
    got = [px[x, y] for y in rows for x in range(0, W, 4)]
    return rgb_hex([statistics.median(c[i] for c in got) for i in range(3)])

def lum(h):
    r, g, b = hex_rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def piece_box(f, n=160, far=48):
    """Where a subject still's piece sits, in the still's fractions. A subject still is a piece drawn on a flat ground, so
    each row's ground is the mean of its outer pixels and the piece is every pixel far from it; a still the piece fills
    (a close-up of its surface) is all subject."""
    from PIL import Image
    im = Image.open(f).convert("RGB")
    W0, H0 = im.size
    s = im.resize((n, max(1, round(n * H0 / W0))))
    W, H = s.size
    px = s.load()
    rows, colhit, cnt = [], [0] * W, 0
    for y in range(H):
        side = [px[x, y] for x in (0, 1, 2, W - 3, W - 2, W - 1)]
        g = [sum(c[i] for c in side) / len(side) for i in range(3)]
        hit = [x for x in range(W) if math.dist(px[x, y], g) > far]
        if len(hit) >= 2:
            rows.append(y)
            for x in hit:
                colhit[x] += 1
        cnt += len(hit)
    cols = [x for x in range(W) if colhit[x] >= 2]
    if not rows or not cols or cnt > 0.85 * W * H:
        return [0.0, 0.0, 1.0, 1.0]
    return [round(cols[0] / W, 3), round(rows[0] / H, 3), round((cols[-1] + 1) / W, 3), round((rows[-1] + 1) / H, 3)]

def sentences(text):
    """The text cut into its sentences, each keeping its own mark; a stop inside a word (@theo.makes) ends nothing."""
    return [x.strip() for x in re.split(r"(?<=[.?!])\s+", (text or "").strip()) if x.strip(" .?!")]

def by_date(rows):
    return sorted(rows, key=lambda p: (p.get("date") or "9999", p["id"]))

def grade_photo(src, dst, filt, wb=WB):
    """A photograph matched to the others and to the run's grade: a partial gray-world gain toward a warm white, its mean
    light brought halfway to the film's, then the grade filter. Returns what was done."""
    from PIL import Image, ImageOps, ImageStat
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((LONG, LONG), Image.LANCZOS)
    y0 = ImageStat.Stat(im.convert("L")).mean[0]
    r, g, b = ImageStat.Stat(im).mean
    grey = (r + g + b) / 3
    wr, wg, wbb = (c / (sum(WARM) / 3) for c in WARM)
    gains = [1 + wb * ((grey * w) / max(1, m) - 1) for m, w in ((r, wr), (g, wg), (b, wbb))]
    im = Image.merge("RGB", [ch.point(lambda v, k=k: max(0, min(255, int(v * k)))) for ch, k in zip(im.split(), gains)])
    y = ImageStat.Stat(im.convert("L")).mean[0]
    k = ((y0 + LUMA) / 2) / max(1, y)
    im = im.point(lambda v: max(0, min(255, int(v * k))))
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    mid = dst.with_name(f".{dst.stem}.png")
    im.save(mid)
    subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-i", str(mid), "-vf", filt, "-q:v", "2", str(dst)], check=True)
    mid.unlink()
    return {"white_balance": wb, "luma": [round(y0), round(y0 * k * y / max(1, y))], "filter": "grade.json"}

def photo_id(row):
    """A photograph's identity: its full path."""
    return str(row["file"])


def classes(caption):
    """What a photograph shows, read from its own words."""
    ws = set(words(caption))
    count = max([NUMBERS[w] for w in ws if w in NUMBERS] + [0])
    people = bool(PEOPLE & ws)
    return {"people": people, "gathering": people and (bool(GATHER & ws) or count >= 3), "pair": people and bool(PAIR & ws),
            "place": bool(PLACE & set(whole_words(caption))), "night": "night" in ws, "low_sun": bool(NIGHT & ws)}


def moment_lines(taste):
    """The line each photograph says on screen: taste.json moments' line, by the photograph's path."""
    return {m["photo"]: (m.get("line") or "").strip() for m in (taste or {}).get("moments") or [] if m.get("photo")}


def feed_photos(lib, looks=None, lines=None):
    """Their photographs as the cast reads them: each with its id, caption, date, classes, size, subject box and the line
    it says (`lines`, by its path)."""
    from PIL import Image, ImageOps
    looks, lines = looks or {}, lines or {}
    out = []
    for row in lib.get("feed") or []:
        f = Path(row["file"])
        if not f.exists():
            continue
        try:
            w, h = ImageOps.exif_transpose(Image.open(f)).size
        except OSError:
            continue
        pid = photo_id(row)
        lk = looks.get(pid) or {}
        if lk.get("skip"):
            continue
        out.append({"id": pid, "file": str(f), "caption": row.get("caption") or "", "words": row.get("words") or "",
                    "line": lines.get(row["file"], ""), "date": row.get("date"), "date_from": row.get("date_from"),
                    "classes": classes(row.get("caption")), "aspect": round(h / w, 4), "size": [w, h],
                    "subject": lk.get("subject"),
                    "subject_from": "agent" if lk.get("checked") else ("machine" if lk.get("subject") else None)})
    return out


def stills_of(lib):
    return [Path(s) for s in (lib.get("subject") or {}).get("stills") or [] if Path(s).exists()]


def cmd_looks(a):
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageOps
    lib = _env.read_json("library.json") or sys.exit("library.json is missing: run gather.py first")
    old = _env.read_json("looks.json") or {}
    looks, tiles = {}, []
    rows = [(p["id"], p["file"], {"subject": subject_guess(p["file"]), "caption": p["caption"][:140], "checked": False})
            for p in feed_photos(lib, old)]
    rows += [(f"subject-{f.stem}", str(f), {"own": True, "subject": piece_box(f), "checked": False}) for f in stills_of(lib)]
    for key, f, guess in rows:
        keep = old.get(key) if (old.get(key) or {}).get("checked") else None
        looks[key] = keep or guess
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        im.thumbnail((360, 360))
        d = ImageDraw.Draw(im)
        if looks[key].get("subject"):
            x0, y0, x1, y1 = looks[key]["subject"]
            d.rectangle([x0 * im.width, y0 * im.height, x1 * im.width - 1, y1 * im.height - 1], outline=(255, 40, 40), width=3)
        d.rectangle([0, 0, im.width, 18], fill=(0, 0, 0))
        d.text((4, 3), Path(key).name[:52], fill=(255, 255, 0))
        tiles.append(im)
    looks.update({k: v for k, v in old.items() if v.get("skip")})
    _env.write_json("looks.json", looks)
    if tiles:
        cols = 5
        sheet = Image.new("RGB", (cols * 364, -(-len(tiles) // cols) * 364), "white")
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * 364, (i // cols) * 364))
        sheet.save(_env.staged("looks.png"))
        os.replace(_env.staged("looks.png"), "looks.png")
    print(f"{len(looks)} photographs -> looks.json, looks.png. Look at looks.png; where a red box is not the photograph's "
          "subject (the subject, the people), set that entry's subject to [left, top, right, bottom] in fractions of the "
          "photograph, and set checked to true on every photograph you looked at.")
    return 0


# ------------------------------------------------------------------ the subject
def poster(clip, frame=0):
    """A clip's first frame, as the picture its beat holds before it plays and the frame its print measures."""
    out = Path(f"cast/{Path(clip).stem}-{frame}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-i", str(clip), "-vf", f"select='eq(n\\,{frame})'", "-frames:v", "1",
                        "-update", "1", str(_env.staged(out))], check=True)
        os.replace(_env.staged(out), out)
    return out


def measure_subject(lib, looks=None):
    """The subject's own stills and footage from its folder: each still's size, the ground at its top and foot, where
    the subject sits in it (looks.json's box where the agent set one, else measured), and which still is the hero; the
    first clip with its first frame."""
    from PIL import Image
    looks = looks if looks is not None else (_env.read_json("looks.json") or {})
    subj = lib.get("subject") or {}
    pieces = []
    for f in stills_of(lib):
        im = Image.open(f).convert("RGB")
        W, H = im.size
        lk = looks.get(f"subject-{f.stem}") or {}
        p = {"file": f.name, "path": str(f), "size": [W, H], "aspect": round(H / W, 4), "top": edge_color(im, range(0, 8)),
             "foot": edge_color(im, range(H - 12, H)), "subject": lk.get("subject") if lk.get("checked") else piece_box(f)}
        p["ink"] = "dark" if lum(p["foot"]) > 0.45 else "light"
        pieces.append(p)
    hero = next((p for p in pieces if any(w in words(Path(p["file"]).stem.replace("-", " ").replace("_", " ")) for w in HERO)),
                pieces[0] if pieces else None)
    if hero:
        pieces.remove(hero)
        pieces.insert(0, hero)
    footage = None
    for c in [Path(s) for s in subj.get("footage") or [] if Path(s).exists() and Path(s).suffix.lower() in CLIPS][:1]:
        fr = poster(c)
        im = Image.open(fr).convert("RGB")
        footage = {"file": c.name, "path": str(c), "size": list(im.size), "aspect": round(im.size[1] / im.size[0], 4),
                   "poster": str(fr), "subject": piece_box(fr)}
    return {"pieces": pieces, "footage": footage}


# ------------------------------------------------------------------ the cast
def making(p, subject, theirs=True, handle=""):
    """Whether a photograph is of the making: their words name the subject or its handle, or, when the subject is
    theirs, making it."""
    said = (p.get("words") or "").lower()
    name = (subject or "").lower().strip()
    tag = (handle or "").lower().lstrip("@")
    return bool(name and name in said) or bool(tag and tag in said) or (theirs and bool(MAKING & set(words(said))))


def theirs_of(subj):
    """Whether the person made the subject (anything but a friend, an account, a creator, a band or a place)."""
    return (subj or {}).get("kind") not in NOT_THEIRS


def cast(lib, taste, subject, looks=None):
    """The film's parts, each with its photograph (or None): the hook, the build in the order they made it, and their
    other photographs; the reveal is always the subject's hero still."""
    _env.need("PIL")
    feed = feed_photos(lib, looks, moment_lines(taste))
    for p in feed:
        if not p["subject"]:
            p["subject"], p["subject_from"] = subject_guess(p["file"]), "machine"
    subj = lib.get("subject") or {}
    name = subj.get("name") or ""
    made = by_date([p for p in feed if making(p, name, theirs_of(subj), subj.get("handle") or "")])
    for p in feed:
        p["making"] = any(p is m for m in made)
    mine = (((taste or {}).get("said") or {}).get("hook") or "").strip()
    worded = [p for p in made if p["line"]]
    hook = worded[-1] if worded else None
    line = mine or (hook["line"] if hook else name)
    used = {hook["id"]} if hook else set()
    build = [p for p in made if p["id"] not in used]
    while len(build) > BUILD_MOST:
        quiet = [p for p in build if not p["line"]]
        build.remove(quiet[0] if quiet else build[0])
    used |= {p["id"] for p in build}
    pal = [hex_rgb(s["hex"]) for s in ((taste or {}).get("palette") or {}).get("subject") or [] if s.get("hex")]
    for p in feed:
        if p["id"] not in used:
            p["swatches"] = swatches(p["file"])
    other = sorted((p for p in feed if p["id"] not in used), key=lambda p: (closeness(p["swatches"], pal), p["id"]))
    return {"feed": feed, "hook": hook, "hook_line": line, "build": build, "other": other}


def stage_subject(subject):
    """The subject's stills and its clip, as they are, in the render's public folder (a still is never graded: the
    subject keeps its own color)."""
    import shutil
    SUBJECT.mkdir(parents=True, exist_ok=True)
    for p in subject["pieces"] + ([subject["footage"]] if subject["footage"] else []):
        dst = SUBJECT / p["file"]
        if not dst.exists() or dst.stat().st_size != Path(p["path"]).stat().st_size:
            shutil.copy2(Path(p["path"]).resolve(), dst)
    if subject["footage"]:
        shutil.copy2(subject["footage"]["poster"], SUBJECT / f"{Path(subject['footage']['file']).stem}.png")


def cmd_show(a):
    lib = _env.read_json("library.json") or sys.exit("library.json is missing: run gather.py first")
    subject = measure_subject(lib)
    c = cast(lib, _env.read_json("taste.json") or {}, subject, _env.read_json("looks.json"))
    name = lambda p: Path(p["id"]).name if p else "-"
    print(f"hook    {name(c['hook'])} {c['hook_line']!r}")
    print("build   " + (", ".join(name(p) + (f" {p['line']!r}" if p["line"] else "") for p in c["build"]) or "-"))
    print("reveal  " + (subject["pieces"][0]["file"] if subject["pieces"] else "-"))
    print("other   " + (", ".join(name(p) for p in c["other"]) or "-"))
    print("subject " + ", ".join(p["file"] for p in subject["pieces"]) + (f"; footage {subject['footage']['file']}" if subject["footage"] else ""))
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["looks", "show"])
    a = ap.parse_args()
    _env.enter_run()
    _env.need("PIL")
    return {"looks": cmd_looks, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
