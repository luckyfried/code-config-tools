#!/usr/bin/env python3
"""The next nine: which of their photos go up, in what order, on which day, with a caption in their voice for each.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/plan.py draft    # plan.json + plan.md from picks.json, grid.json and research.json
    python3 S/scripts/plan.py check    # validates plan.json and rewrites plan.md; exit 0 only when it holds

draft picks up to nine photos from the pool picks.json holds (the library photos that never had a grid spot of their
own), never two from one post and never two near copies, and places them as a tonal checkerboard: the calm photos on
the even slots (the corners and the center of a full nine), the detailed ones between them, so two busy frames never
touch. A pool with fewer than nine photos gives a shorter plan, and the film shows the posts it has. Post 1 goes up
first and ends at the bottom right of the posts; the last post lands at the top left.
Each post gets its crops (the 4:5 post and the 3:4 grid cell, centered on the photo's focal point), the post of theirs
it follows (the nearest in color among the posts with a photo that keep to their grid; none when no post on the grid
has its photo), a date from their own cadence (research.json: the weekday they post most, and the median gap between
their last 30 posts, kept between one and seven days), a draft caption (the words that came with that photo, or none)
and `said`, those same words, which are all the film's band ever shows of the post.
The drafts are a starting point. Write each caption fresh in their voice (taste.md: their register, length,
lowercase or not, emoji or not) by editing the "caption" fields of plan.json, each post's "shot" (the shot a
cinematographer would ask for to bring that photograph to life: its subject, the lens and the camera's height the
photograph was taken at, and its light; on a post the film passes in a beat, the texture between chapters: a close
look at a surface the photograph shows, on a lens of its own beside the passed post before it), and the film's own
words in "film": "hook", the line that states the glow-up in the first second, "ask", the line the closer holds on,
and "world", the shot of the world their grid comes from under the hook (clip 00, made from the old post the hook's
frame lands on). Then run check. check refuses a plan without its posts in order from 1 on rising dates, a caption that
is empty, a placeholder, too long, out of their register, a repeat of another post, or word for word the caption of a
post already on their grid; a hook or an ask that is not two to seven words in their register, or names a day or a
number; a shot or a world that does not name its subject, a lens in mm, the camera's height and its light; and two
posts the film passes one after the other on the same lens.
"""
import argparse
import datetime as dt
import math
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|caption here", re.I)
TAG = re.compile(r"#\w+")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like", "it's", "its",
        "i'm", "was", "are", "very", "through", "over", "into", "about", "after", "before", "under", "as", "if", "when",
        "than", "your", "our", "their", "his", "her"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_WORDS = 40
NINE = 9
ALIKE = 0.92
# what a shot names: a lens, the camera's height, and its light
LENS = re.compile(r"\b\d{2,3}\s?mm\b", re.I)
HEIGHT = re.compile(r"\b(overhead|top[- ]down|from above|from below|\w+[- ]height|\w+[- ]level|low|high)\b", re.I)
LIGHT = re.compile(r"\b(\w*light|lit|sun\w*|window|shade|shadows?|dusk|dawn|golden|overcast|lamps?|neon|backlit|glow\w*|"
                   r"candle\w*|haze|hazy|morning|evening|afternoon|noon|night)\b", re.I)


def plain(text):
    return re.sub(r"\s+", " ", TAG.sub("", text or "")).strip().lower()


def short(cap, limit=60):
    """A caption's lead line for the screen: no hashtags or emoji, cut at a clause or a word, never on a function word."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    for sep in (". ", ": ", "; ", " - "):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


HANDLE = re.compile(r"@[\w.]+")
CLAUSE = re.compile(r"[.:;!?]\s|,\s|\s[-–—]\s")


def bare(cap):
    """A caption as a cell sets it: no hashtags, no emoji, one space between words (a no-break space stays)."""
    return re.sub(r"[^\S\u00a0]+", " ", EMOJI.sub("", TAG.sub("", cap or ""))).strip(" ,;:-–—")


def ends_well(words):
    """words with the trailing function words and stray punctuation taken off, never below one word."""
    w = [x for x in words if x]
    while len(w) > 1 and w[-1].lower().strip(",.;:!?") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-–—")


def cell_words(cap, fits):
    """The words of a caption a cell sets, the one rule for every cell that shows a caption: the caption whole, else
    with its @handles dropped, else its first clause, else the longest lead of that clause, at a word, that ends on a
    content word; the first of these fits accepts. A word is never cut: when not one whole word fits, the cell sets no
    caption ("")."""
    whole = bare(cap)
    free = ends_well(HANDLE.sub("", whole).split(" "))
    first = ends_well(CLAUSE.split(free, 1)[0].split(" ")) if free else ""
    for t in (whole, free, first):
        if t and fits(t):
            return t
    words = first.split(" ")
    while len(words) > 1:
        words.pop()
        t = ends_well(words)
        if fits(t):
            return t
    return ""


def lab_dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def parent(src):
    """The post a library file belongs to: a carousel's slides share it, and a file of one name in another folder is
    another post."""
    path = Path(str(src))
    stem = path.stem
    base = stem.rsplit("-", 1)[0] if re.search(r"-\d+$", stem) else stem
    return str(path.parent / base)


def crop(w, h, focal, aspect, scale=1.0):
    """The [x, y, w] crop box (fractions of the source) at aspect (width over height), as large as the photo allows
    times scale, centered on the focal point and kept inside the photo."""
    bw = min(1.0, aspect * h / w) * scale
    bh = bw * w / aspect / h
    x = min(max(0.0, focal[0] - bw / 2), 1 - bw)
    y = min(max(0.0, focal[1] - bh / 2), 1 - bh)
    return [round(x, 3), round(y, 3), round(bw, 3)]


def crops(size, focal):
    """A post's 4:5 post crop and its 3:4 grid crop, both centered on its focal point."""
    return crop(*size, focal, 4 / 5), crop(*size, focal, 3 / 4, 0.9)


def crop_sheet(plan, out="crops.png"):
    """Every post's photograph whole, numbered, with its 4:5 post crop (white) and the box the film closes onto
    (orange), so a crop that cuts the subject the caption names is seen before the board."""
    from PIL import Image, ImageDraw
    import drive
    tiles = []
    for sl in plan["slots"]:
        im = Image.open(sl["photo"]).convert("RGB")
        im.thumbnail((420, 420))
        w, h = im.size
        d = ImageDraw.Draw(im)
        x, y, cw = sl["crop45"]
        d.rectangle([x * w, y * h, (x + cw) * w, y * h + cw * w * 5 / 4], outline="white", width=3)
        c = sl["crop34"]
        focal = sl.get("focal") or [c[0] + c[2] / 2, c[1] + c[2] * sl["size"][0] * 4 / 3 / sl["size"][1] / 2]
        x, y, cw = crop(*sl["size"], focal, 3 / 4, drive.SUBJECT)
        d.rectangle([x * w, y * h, (x + cw) * w, y * h + cw * w * 4 / 3], outline="#ff7a1a", width=4)
        d.rectangle([0, 0, 34, 30], fill="black")
        d.text((10, 8), str(sl["n"]), fill="white")
        tiles.append(im)
    sheet = Image.new("RGB", (3 * 430, 430 * math.ceil(len(tiles) / 3)), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * 430 + 5, (i // 3) * 430 + 5))
    Path(out).parent.mkdir(exist_ok=True)
    _env.unready()
    tmp = _env.part(out)
    sheet.save(tmp)
    os.replace(tmp, out)
    return out


class Pool:
    def __init__(self):
        self.lib = _env.read_json("library.json") or {}
        self.grid = _env.read_json("grid.json") or {}
        if "cells" not in self.grid:
            sys.exit("grid.json is missing: run research.py first")
        self.rows = (_env.read_json("picks.json") or {}).get("pool", [])
        self.taste = _env.read_json("taste.json") or {}
        self.busy = (self.grid.get("median_detail") or 0.08) * 1.35
        self.captions = self.captions_of(self.lib, self.taste)
        self._sig = {}

    @staticmethod
    def captions_of(lib, taste):
        """The words each library file came with, by its path: its post's caption, or the words the person put with a
        photograph they named; a line set in taste.json "said" for that path is the one the film carries."""
        out = {str(m): r.get("caption") or "" for k in ("posts", "reels", "facebook", "photos") for r in lib.get(k) or []
               for m in r.get("media") or []}
        return out | {str(k): v for k, v in (taste.get("said") or {}).items()}

    def sig(self, row):
        """A photo's composition as edge directions in four quadrants, so two shots of one scene read as alike whatever
        their colors, and two subjects that share a palette do not."""
        if row["photo"] not in self._sig:
            from PIL import Image, ImageOps
            W, H = 64, 80
            im = ImageOps.fit(Image.open(row["photo"]).convert("L"), (W, H))
            px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
            bins = [0.0] * 32
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    gx = px[y * W + x + 1] - px[y * W + x - 1]
                    gy = px[(y + 1) * W + x] - px[(y - 1) * W + x]
                    m = math.hypot(gx, gy)
                    if m < 8:
                        continue
                    a = math.atan2(gy, gx) % math.pi
                    bins[(int(y >= H // 2) * 2 + int(x >= W // 2)) * 8 + int(a / math.pi * 8) % 8] += m
            norm = math.sqrt(sum(b * b for b in bins)) or 1
            self._sig[row["photo"]] = [b / norm for b in bins]
        return self._sig[row["photo"]]

    def alike(self, a, b):
        return sum(i * j for i, j in zip(self.sig(a), self.sig(b))) > ALIKE

    def take(self, n):
        """The n best photos by fit: never two from one post, never two near copies, never more than two of one scene
        while other scenes remain, then three."""
        score = lambda r: r.get("fit", 0) - (0.12 if r.get("detail", 0) > self.busy else 0)
        ranked = sorted(self.rows, key=score, reverse=True)
        out, parents = [], set()
        for limit in (2, 3):
            for r in ranked:
                if len(out) == n:
                    break
                if r in out or parent(r["src"]) in parents or any(lab_dist(r["lab"], x["lab"]) < 5 for x in out):
                    continue
                if sum(1 for x in out if self.alike(r, x)) >= limit:
                    continue
                out.append(r)
                parents.add(parent(r["src"]))
        return out

    def words_for(self, row, taken):
        """The caption the photo was posted with, never one another of the nine already carries; a photo with no words
        of its own has none."""
        cap = self.captions.get(str(row.get("src")), "")
        return cap if cap.strip() and cap not in taken else ""


def checkerboard(m):
    """The slots of a plan of m posts: the even slots are the calm places, the odd ones the busy places; calm photos go
    center first, then the corners."""
    calm = sorted((s for s in range(m) if s % 2 == 0), key=lambda s: (s != 4, s))
    busy = [s for s in range(m) if s % 2 == 1]
    return calm, busy


def cadence():
    cad = (_env.read_json("research.json") or {}).get("cadence") or {}
    ts = sorted(c["ts"] for c in (_env.read_json("grid.json") or {}).get("cells", []) if c.get("ts"))
    gaps = [(b - a) / 86400 for a, b in zip(ts, ts[1:])]
    gap = min(7, max(1, round(statistics.median(gaps)))) if gaps else 3
    last = dt.datetime.fromtimestamp(ts[-1], dt.timezone.utc).date() if ts else dt.date.today()
    weekday = cad.get("top_weekday") if cad.get("top_weekday") in DAYS else None
    theirs = isinstance(cad.get("top_hour_utc"), int)
    return {"weekday": weekday, "hour_utc": cad["top_hour_utc"] if theirs else 18, "their_hour": theirs, "gap_days": gap,
            "after": str(max(last, dt.date.today()))}


def dates(cad, m):
    day = dt.date.fromisoformat(cad["after"]) + dt.timedelta(days=1)
    if cad["weekday"]:
        while DAYS[day.weekday()] != cad["weekday"]:
            day += dt.timedelta(days=1)
    return [day + dt.timedelta(days=cad["gap_days"] * i) for i in range(m)]


def grid_spot(n, m):
    slot = m - n
    return f"row {slot // 3 + 1}, {['left', 'middle', 'right'][slot % 3]}"


def cmd_draft(a):
    _env.need("PIL")
    if not Path("taste.md").exists():
        sys.exit("taste.md is missing: research comes first (pipeline/1-research.md), then the plan")
    pool = Pool()
    rows = pool.take(NINE)
    if not rows:
        sys.exit("picks.json has no photos to plan with: run research.py (and gather.py --photos for a photo folder) first")
    m = len(rows)
    from PIL import Image
    import critic
    for r in rows:
        r["size"] = list(Image.open(r["photo"]).size)
        r["focal"] = r.get("focal") or [0.5, 0.45]
        r["crop45"], r["crop34"] = crops(r["size"], r["focal"])
        # Placed by the measure the critic's swap test reads: the detail of the photo as its grid cell shows it.
        r["cell_detail"] = critic.detail(r["photo"], r["crop34"])
    rows.sort(key=lambda r: r["cell_detail"])
    calm_slots, busy_slots = checkerboard(m)
    calm, busy = rows[:len(calm_slots)], rows[len(calm_slots):]
    calm.sort(key=lambda r: -r.get("bright", 0))
    at = {s: (r, "calm") for s, r in zip(calm_slots, calm)} | {s: (r, "busy") for s, r in zip(busy_slots, busy)}
    cad = cadence()
    days = dates(cad, m)
    lower = bool((pool.taste.get("register") or {}).get("lowercase"))
    measured = [c for c in pool.grid["cells"] if c.get("a")]
    keep = [c for c in measured if not set(c.get("flags") or []) & {"clash", "text"}] or measured
    cells = pool.grid["cells"]
    texts = [c.get("saves") or 0 for c in cells if "text" in (c.get("flags") or [])]
    lessons = bool(texts) and statistics.median(texts) > statistics.median([c.get("saves") or 0 for c in cells])
    taken, used, slots = set(), set(), []
    for n in range(1, m + 1):
        r, place = at[m - n]
        cap = pool.words_for(r, taken)
        taken.add(cap)
        cap = EMOJI.sub("", TAG.sub("", cap)).strip()
        cap = re.sub(r"\s+", " ", cap.lower() if lower else cap)
        near = sorted((c for c in keep if c["pos"] not in used), key=lambda c: lab_dist(c["a"]["lab"], r["lab"])) or keep
        if near:
            used.add(near[0]["pos"])
        src = Path(r["photo"])
        day = days[n - 1]
        slots.append({"n": n, "date": str(day), "weekday": DAYS[day.weekday()], "time_utc": f"{cad['hour_utc']:02d}:00",
                      "file": f"posts/{n:02d}.png", "photo": str(src), "source": r.get("src"), "size": r["size"],
                      "place": place, "slot": m - n, "grid_spot": grid_spot(n, m),
                      "focal": r["focal"], "crop45": r["crop45"], "crop34": r["crop34"],
                      "follows": near[0]["pos"] + 1 if near else None, "caption": short(cap, 120) if cap else "",
                      "said": pool.captions.get(str(r.get("src")), ""), "shot": "", "lesson": None})
    plan = {"handle": pool.lib.get("handle") or pool.taste.get("handle") or "you", "cadence": cad, "drafted": True,
            "lessons": lessons, "film": {"hook": "", "ask": "", "world": ""}, "slots": slots}
    publish(plan)
    print(f"plan: {m} posts from {slots[0]['date']} to {slots[-1]['date']}, every {cad['gap_days']} day(s) at "
          f"{cad['hour_utc']:02d}:00 UTC -> plan.json, plan.md. Now write each caption fresh in their voice in "
          "plan.json, each post's shot, the film's hook, ask and world (and a lesson title on a post that teaches, when "
          "lessons is true) and run plan.py check")
    return 0


def problems(plan):
    bad = []
    slots = plan.get("slots") or []
    if not slots or len(slots) > NINE or [s.get("n") for s in slots] != list(range(1, len(slots) + 1)):
        bad.append(f"the plan needs one to nine posts in posting order from 1 (got {[s.get('n') for s in slots]})")
    days = [s.get("date") or "" for s in slots]
    if any(not x for x in days) or days != sorted(days) or len(set(days)) != len(days):
        bad.append("every post needs its own date, rising from post 1 to the last")
    for s in slots:
        if not s.get("photo") or not Path(s["photo"]).exists():
            bad.append(f"post {s.get('n')}: its photo {s.get('photo')} is missing")
    reg = (_env.read_json("taste.json") or {}).get("register") or {}
    old = {plain(c.get("caption")) for c in (_env.read_json("grid.json") or {}).get("cells", []) if c.get("caption")}
    seen = set()
    for s in slots:
        cap = (s.get("caption") or "").strip()
        body = plain(cap)
        where = f"post {s.get('n')}"
        if not body:
            bad.append(f"{where}: the caption is empty")
            continue
        if PLACEHOLDER.search(cap) or PLACEHOLDER.search(s.get("lesson") or ""):
            bad.append(f"{where}: the caption carries a placeholder")
        if len(body.split()) > MAX_WORDS:
            bad.append(f"{where}: the caption runs {len(body.split())} words; keep it under {MAX_WORDS}")
        if reg.get("lowercase") and TAG.sub("", cap) != TAG.sub("", cap).lower():
            bad.append(f"{where}: they write in lowercase; this caption has capitals")
        named = [d.lower() for d in DAYS if re.search(rf"\b{d.lower()}", body)]
        if named and (s.get("weekday") or "").lower() not in named:
            bad.append(f"{where}: the caption says {named[0]} but the post goes up on a {s.get('weekday')}")
        if body in seen:
            bad.append(f"{where}: the same caption as another post")
        if body in old:
            bad.append(f"{where}: word for word the caption of a post already on their grid; write a new line in their voice")
        seen.add(body)
        bad += shot_problems(s.get("shot"), where + "'s shot", cap)
        i = slots.index(s)
        held = held_posts(len(slots))
        lens = LENS.search(s.get("shot") or "")
        prev = LENS.search(slots[i - 1].get("shot") or "") if i and i - 1 not in held and i not in held else None
        if lens and prev and re.sub(r"\s", "", lens.group().lower()) == re.sub(r"\s", "", prev.group().lower()):
            bad.append(f"{where}'s shot: the film passes this post right after post {slots[i - 1].get('n', i)} on the same "
                       f"{lens.group()} lens; give each passed post its own lens so the textures between chapters vary")
    film = plan.get("film") or {}
    first = (slots[0].get("weekday") or "").lower() if slots else ""
    for key, what in (("hook", "the hook"), ("ask", "the ask")):
        line_ = (film.get(key) or "").strip()
        n = len(line_.split())
        if not 2 <= n <= 7 or PLACEHOLDER.search(line_):
            bad.append(f"film: {what} is {n} words; write it as two to seven words in their voice")
        elif re.search(r"\d", line_):
            bad.append(f"film: {what} carries a number; no date or count is ever on screen")
        elif any(re.search(rf"\b{d.lower()}", line_.lower()) for d in DAYS if d.lower() != first):
            bad.append(f"film: {what} names a day the first post does not go up on (it goes up on a {first})")
        elif reg.get("lowercase") and line_ != line_.lower():
            bad.append(f"film: they write in lowercase; {what} has capitals")
    bad += shot_problems(film.get("world"), "film: the world", "", least=8)
    return bad


def held_posts(m):
    """The posts the film holds on, by index: the first, the last from three posts on, and the middle from five on, so
    no two held posts follow each other. It passes the others in a beat."""
    return {0} | ({m - 1} if m >= 3 else set()) | ({m // 2} if m >= 5 else set()) if m else set()


def shot_problems(text, where, caption, least=6):
    """What a shot is missing: its subject in `least` words or more, never the caption pasted in, a lens in mm, the
    camera's height, and its light."""
    text = (text or "").strip()
    if len(text.split()) < least or PLACEHOLDER.search(text):
        return [f"{where} is {len(text.split())} words; name its subject, the lens in mm, the camera's height and its light"]
    if caption and plain(caption) in plain(text):
        return [f"{where} pastes in the caption; write the shot the photograph asks for"]
    return [f"{where} names no {what}" for what, rx in (("lens in mm", LENS), ("camera height", HEIGHT), ("light", LIGHT))
            if not rx.search(text)]


def cmd_check(a):
    plan = _env.read_json("plan.json")
    if not plan:
        sys.exit("plan.json is missing: run plan.py draft")
    bad = problems(plan)
    if bad:
        print("the plan does not hold yet:")
        for x in bad:
            print("  -", x)
        return 1
    for sl in plan["slots"]:
        if sl.get("focal"):
            sl["crop45"], sl["crop34"] = crops(sl["size"], sl["focal"])
    # the critic's swap test on the cells as planned, so a photo moved or a focal point changed is placed again here
    import critic
    _, obj = critic.swap([{"n": sl["n"], "file": sl["photo"], "place": sl["place"], "crop": sl["crop34"]} for sl in plan["slots"]])
    if obj:
        print("the plan does not hold yet:")
        for o in obj:
            print("  -", o["text"], "(give the two posts each other's photo, caption and focal point)")
        return 1
    plan["drafted"] = False
    publish(plan, sheet=True)
    n = len(plan["slots"])
    print(f"plan ok: {n} captions in order, {plan['slots'][0]['date']} to {plan['slots'][-1]['date']} -> plan.md; "
          f"the crops -> crops.png")
    return 0


def publish(plan, sheet=False):
    """(With `sheet`) crops.png, then plan.json, then plan.md, the completion file QA's plan gate reads,
    published last. plan.md goes first, so a stop part way leaves a plan the gate refuses; plan.json is the
    agent's input, its captions, lesson titles and focal points, and is only ever replaced whole, never removed."""
    _env.unready()
    Path("plan.md").unlink(missing_ok=True)
    if sheet:
        crop_sheet(plan)
    _env.write_json("plan.json", plan)
    write_md(plan)


def write_md(plan):
    cad = plan["cadence"]
    m = len(plan["slots"])
    lines = [f"# Your next {m if m < NINE else 'nine'}", "",
             ("Post them in this order, one a day" if cad["gap_days"] == 1 else f"Post them in this order, one every {cad['gap_days']} days")
             + (f", starting on a {cad['weekday']}" if cad.get("weekday") else "")
             + f", around {cad['hour_utc']:02d}:00 UTC, " + ("the hour you post most. " if cad.get("their_hour") else "a suggested time. ")
             + "Post 1 goes up first and ends at the bottom right; the last post goes up last and lands at the top "
             "left. `grid-after.png` shows how your profile will look when they are all up."
             + ("" if (_env.read_json("grid.json") or {}).get("cells") else " There was no feed to compare against, so it shows the new posts alone."),
             "",
             "| # | date | file | where it lands | caption |", "|---|---|---|---|---|"]
    for s in plan["slots"]:
        cap = (s["caption"] + (f" (title on the cover: {s['lesson']})" if s.get("lesson") else "")).replace("|", "/")
        lines.append(f"| {s['n']} | {s['weekday'][:3]} {s['date']}, {s['time_utc']} UTC | `{s['file']}` | {s['grid_spot']} | {cap} |")
    lines.append("")
    _env.unready()
    _env.write_text("plan.md", "\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check"])
    a = ap.parse_args()
    _env.enter_run()
    return {"draft": cmd_draft, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
