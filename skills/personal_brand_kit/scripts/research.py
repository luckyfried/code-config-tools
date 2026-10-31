#!/usr/bin/env python3
"""Movement 1: the measured read behind the brand kit. Reads library.json; writes research.json, a
machine draft of taste.json (with the brand draft under "brand"), and taste.draft.md (every finding
with its number and its example, under the five headings the agent turns into taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py

It runs stats.py, picks.py and palette.py first, then measures:
  palette       the colors their posts lead with, as the share of posts each named color leads (palette.py)
  compositions  how they frame: orientation, a centered subject versus one on a third, one color field covering
                half the frame or more, brightness; each with its share and three example photos
  voice         caption devices, each with its share and three of their real captions: an opening label ending
                in a colon, a list of three, a closing question, a question set off by a blank line, line
                breaks, an emoji sign-off, a hashtag line; plus case, length, emoji and the words they lean on
  pillars       subjects found by clustering the words of their captions (words that travel together across
                posts form one pillar; words every pillar uses are set aside), each post counted once, the shares
                summing to 1, each with its words and an example caption
  cadence       posts a week, the weekdays they post on and the usual time on each, and how often a post lands
                on that rhythm
  likes         what their likes say they aspire to: the palette of the liked images (or of the color words in
                the accounts they like) and the subjects of the accounts they like and save, against their own
  outliers      posts that break two or more of their palette, pillars, voice and cadence (at least one of them
                the palette or the cadence, since a short caption alone misses both pillar and voice), with how
                they landed
  moments       every captioned post with a photograph, in date order, as what happened: the caption's own first
                line, the place it names, the people it tags and its pillar; the agent curates them in taste.json
                `moments`, and each card of the film is one of them
The draft's `music` is the brief the film's music is made from (music.py): plain words for the feeling and what to
avoid, never an artist, a band or a song; the look's own recipe carries the tempo and the instruments.
A feed with photographs and no captions reads its voice and pillars from the bio's sentences instead.
Anything the person said about themselves (bio, the request) outranks all of it: the agent writes their words
into taste.json and taste.md over the draft.
"""
import collections
import datetime as dt
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

S = Path(__file__).resolve().parent

COLOR_WORDS = {
    "terracotta": "#c8643f", "ochre": "#c98b2b", "olive": "#7d7a3a", "rust": "#a5482a", "linen": "#e8dcc6",
    "saffron": "#e0a030", "amber": "#d9902f", "golden": "#d8a443", "gold": "#d4a640", "lemon": "#e9d36a",
    "sand": "#d9c19a", "clay": "#b46a4c", "honey": "#d9a441", "cream": "#efe4cc", "sage": "#97a585", "moss": "#6b7444",
    "ocean": "#2f6f8f", "sea": "#3a7ea1", "harbor": "#4c6f84", "sky": "#8fb8d6", "blue": "#3d6fa8", "navy": "#24324f",
    "pink": "#e6a3b0", "rose": "#c9707f", "coral": "#e9775f", "peach": "#f0b38a", "berry": "#7f2f4f", "plum": "#6a3c5e",
    "lavender": "#b5a2cf", "mint": "#a8d8bd", "forest": "#2f5236", "green": "#4f8a4a", "black": "#141414",
    "noir": "#161616", "mono": "#7a7a7a", "neon": "#ff3ea5", "chrome": "#c9ccd1", "coffee": "#5b3a29",
    "espresso": "#3b2418", "chocolate": "#5a3a28", "tomato": "#d0432f", "red": "#c23b2e", "orange": "#e57a33",
    "yellow": "#efc94c", "white": "#f4f1ea", "sunset": "#e9773f", "dusk": "#5a4a73", "salt": "#f1ece2",
}
THEMES = {
    "film photography": ["35mm", "film", "portra", "kodak", "grain", "analog", "shotonfilm", "filmphotography", "frames"],
    "food": ["eats", "food", "table", "kitchen", "plate", "bread", "mezze", "crumb", "slowfood", "cook", "cooks",
             "tomatoes", "breakfast", "lunch", "dinner", "pasta", "tacos"],
    "markets": ["market", "markets", "stall", "haul", "grocer", "farmers"],
    "coffee": ["espresso", "coffee", "cafe", "latte", "cortado"],
    "the sea and the coast": ["sea", "coast", "coastal", "shore", "tide", "tidal", "harbor", "seaside", "cliffside",
                              "beach", "ocean", "waves", "surf", "water", "blue"],
    "travel": ["wanderer", "travel", "paths", "atlas", "getaways", "postcard", "slowtravel", "road", "trip", "train"],
    "streets and doorways": ["streets", "street", "doorways", "doors", "door", "walk", "town"],
    "slow living": ["slow", "slowly", "mornings", "afternoons", "linen", "quiet", "journal", "home"],
    "light": ["light", "golden", "hour", "sun", "sunbaked", "amber", "warm", "warmtones"],
    "fitness": ["gym", "run", "lift", "fit", "yoga", "training", "grind", "gymlife"],
    "music": ["music", "vinyl", "dj", "gig", "band", "concert"],
    "fashion": ["outfit", "ootd", "style", "wear", "thrift", "kicks"],
    "design": ["design", "type", "studio", "poster", "print", "setup"],
}
STOP = set("""a an the and or but of to in on at for with from by as is are was were be been it its this that these those
i me my we our you your he she they them his her their what which who whom when where why how all any both each few more
most other some such no nor not only own same so than too very can will just don should now one two three im ive i'm i've
what's where's who's here there then up down out over again once about into after before under also get got go going went
new day today yesterday still really little bit lot would could did do does done had has have made make know back
finally always enough last first works got let good great nice""".split())
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def run(script):
    p = subprocess.run([sys.executable, str(S / script)], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{script} failed:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def words(text):
    """Content words of a caption, hashtags kept as words (their # dropped); an @mention is one of their people, never
    a word of a subject."""
    t = re.sub(r"@[\w.]+", " ", (text or "").lower().replace("’", "'"))
    return {w.lstrip("#").replace("'s", "") for w in re.findall(r"#?[a-z][a-z']+", t)} - STOP


def when(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)


def clean(c):
    """The caption without hashtags, emoji and trailing space."""
    return re.sub(r"\s+$", "", EMOJI.sub("", re.sub(r"#\w+", "", c or "")).replace("️", ""))


def spaced(rows, k=3):
    """k rows spread evenly through the list (so examples come from across the window)."""
    if len(rows) <= k:
        return rows
    step = len(rows) / k
    return [rows[int(i * step + step / 2)] for i in range(k)]


# voice -------------------------------------------------------------------------------------------------------------

ITEM = r"[^,.:;\n?!]{2,32}"
LIST3 = rf"(?:^|:\s*|[.!?]\s+)({ITEM}),\s+({ITEM}),\s+(?:and\s+)?({ITEM})(?:[.!\n]|$)"
DEVICES = {
    "opening label": ("opens with a short label and a colon (\"sunday table:\")",
                      lambda c: bool(re.match(r"^\s*[^\s:#][^:\n]{1,28}:\s", c)) and len(c.split(":")[0].split()) <= 4),
    "list of three": ("names three things in a row (\"figs, plums, quince.\")",
                      lambda c: any(all(len(x.split()) <= 4 for x in m) for m in
                                    re.findall(rf"({ITEM}),\s+({ITEM}),\s+(?:and\s+)?({ITEM})(?:[.!\n]|$)", clean(c)))),
    "closing question": ("ends on a question to the reader",
                         lambda c: clean(c).rstrip().endswith("?")),
    "question after a blank line": ("sets the closing question off with a blank line",
                                    lambda c: bool(re.search(r"\n\s*\n[^\n]*\?\s*$", clean(c)))),
    "line breaks": ("breaks the caption into lines", lambda c: "\n" in c.strip()),
    "emoji sign-off": ("signs off with an emoji", lambda c: bool(EMOJI.search(re.sub(r"#\w+", "", c).strip()[-3:]))),
    "short plain line": ("writes one short plain line, twelve words or fewer, no hashtags",
                         lambda c: 0 < len(clean(c).split()) <= 12 and "#" not in c and "\n" not in c.strip()),
    "hashtag line": ("puts its hashtags on a line of their own",
                     lambda c: any(l.strip() and all(w.startswith("#") for w in l.split()) for l in c.splitlines()[1:])),
}
# a weekday is one of their posting days when it carries this share of their posts
SLOT = 0.2
LOUD = lambda c: (sum(ch.isupper() for ch in c) > 0.3 * max(1, sum(ch.isalpha() for ch in c))) or "!!" in c or \
    len(EMOJI.findall(c)) >= 3


def voice(rows):
    caps = [r for r in rows if (r.get("caption") or "").strip()]
    if not caps:
        return {"captions": 0, "devices": [], "all_devices": []}
    texts = [r["caption"] for r in caps]
    measured = []
    for name, (what, test) in DEVICES.items():
        hits = [r for r in caps if test(r["caption"])]
        measured.append({"name": name, "what": what, "share": round(len(hits) / len(caps), 3), "count": len(hits),
                         "examples": [r["caption"] for r in spaced(hits)]})
    measured.sort(key=lambda d: -d["share"])
    letters = [ch for c in texts for ch in c if ch.isalpha()]
    lower_caps = [c for c in texts if re.search(r"[A-Za-z]", c) and c == c.lower()]
    df = collections.Counter(w for c in texts for w in words(c) if not c.count("#" + w))
    emo = collections.Counter(e for c in texts for e in EMOJI.findall(c))
    tags = collections.Counter(t.lower() for c in texts for t in re.findall(r"#\w+", c))
    n_words = [len(clean(c).split()) for c in texts]
    return {
        "captions": len(caps),
        "devices": [d for d in measured if d["share"] >= 0.3],
        "all_devices": measured,
        "case": "lowercase" if len(lower_caps) / len(texts) >= 0.6 else "sentence case",
        "lowercase_share": round(len(lower_caps) / len(texts), 3),
        "letters_lower": round(sum(ch.islower() for ch in letters) / max(1, len(letters)), 3),
        "avg_words": round(statistics.mean(n_words), 1),
        "median_words": statistics.median(n_words),
        "emoji_per_caption": round(sum(emo.values()) / len(texts), 2),
        "top_emoji": [e for e, _ in emo.most_common(4)],
        "hashtags_per_caption": round(sum(tags.values()) / len(texts), 2),
        "hashtags": [t for t, _ in tags.most_common(6)],
        "lean_words": [{"word": w, "captions": k, "share": round(k / len(texts), 3)} for w, k in df.most_common(10)],
    }


def moments(rows, pls, photo_of):
    """The moments draft: each row with a photograph (`photo_of`, row to picture) and words in its caption, oldest
    first, as its date, its line (the caption's first paragraph without hashtags or emoji), the place it was posted
    from, the people it tags and its pillar."""
    pillar_of = {k: p["name"] for p in pls for k in p["rows"]}
    out = []
    for k in sorted(photo_of, key=lambda k: rows[k].get("ts") or 0):
        r = rows[k]
        line = re.sub(r"\s+", " ", re.split(r"\n\s*\n", clean(r.get("caption")).strip())[0]).strip()
        if not line:
            continue
        out.append({"date": when(r["ts"]).strftime("%Y-%m-%d"), "row": k, "photo": photo_of[k], "line": line,
                    "place": r.get("place"), "people": re.findall(r"@[\w.]*\w", r.get("caption") or ""), "pillar": pillar_of.get(k)})
    return out


# pillars -----------------------------------------------------------------------------------------------------------

def _agglomerate(vocab, docs, df, n, threshold):
    """Average-linkage clusters of words, by the cosine of their PPMI co-occurrence profiles."""
    co = {w: collections.Counter() for w in vocab}
    for d in docs:
        for a in d:
            for b in d:
                if a != b:
                    co[a][b] += 1
    vec = {}
    for w in vocab:
        v = {b: math.log(k * n / (df[w] * df[b])) for b, k in co[w].items()}
        v = {b: x for b, x in v.items() if x > 0}
        v[w] = math.log(n / df[w])
        vec[w] = v
    norm = {w: math.sqrt(sum(x * x for x in v.values())) or 1 for w, v in vec.items()}
    sim = {}
    for a in vocab:
        for b in vocab:
            if a < b:
                sim[a, b] = sum(x * vec[b].get(k, 0) for k, x in vec[a].items()) / (norm[a] * norm[b])
    s = lambda a, b: sim[(a, b) if a < b else (b, a)]
    clusters = [[w] for w in vocab]
    while len(clusters) > 1:
        best = max(((sum(s(a, b) for a in clusters[i] for b in clusters[j]) / (len(clusters[i]) * len(clusters[j])), i, j)
                    for i in range(len(clusters)) for j in range(i + 1, len(clusters))))
        if best[0] < threshold:
            break
        clusters[best[1]] += clusters.pop(best[2])
    return clusters


def _assign(docs, clusters, df):
    out = []
    for d in docs:
        sc = max(((len(d & set(c)), sum(df[w] for w in c), i) for i, c in enumerate(clusters)), default=(0, 0, None))
        out.append(sc[2] if sc[0] else None)
    return out


def few(rows, caps, docs):
    """A feed too small for words to repeat: its best-liked captions, up to six, each its own pillar named by the
    caption's first subject word, so the guide and the film still stand on the person's own words."""
    order = sorted((k for k, d in enumerate(docs) if d), key=lambda k: -(rows[k].get("likes") or 0))[:6]
    out, seen = [], set()
    for k in order:
        first = noun(clean(caps[k]), docs[k] - seen)
        if not first:
            continue
        seen.add(first)
        out.append({"name": first, "share": 0, "posts": 1, "words": [first], "hashtag": None, "example": clean(caps[k]), "rows": [k]})
    if len(out) < 2:
        return [], list(range(len(rows)))
    for p in out:
        p["share"] = round(1 / len(out), 3)
    out[0]["share"] = round(1 - sum(p["share"] for p in out[1:]), 3)
    claimed = {k for p in out for k in p["rows"]}
    return out, [k for k in range(len(rows)) if k not in claimed]


def noun(text, allowed):
    """The caption's subject word: the longest of its content words that reads as a thing (not an -ed, -ly or -ing
    form when another word is there), ties to the earliest."""
    ws = [w for w in re.findall(r"[a-z][a-z']+", text.lower()) if w in allowed]
    things = [w for w in ws if not re.search(r"(ed|ly|ing)$", w)] or ws
    return max(things, key=lambda w: (len(w), -ws.index(w)), default=None)


def pillars(rows, threshold=0.3, top=80, min_share=0.05):
    """Pillars from caption words: [{name, share, posts, words, hashtag, example, rows}], shares summing to 1, and
    the row indices no pillar claims."""
    caps = [r.get("caption") or "" for r in rows]
    docs = [words(c) for c in caps]
    n = len(docs)
    df = collections.Counter(w for d in docs for w in d)
    tag_only = {w for w in df if all(("#" + w) in c.lower() or w not in words(c) for c in caps)}
    vocab = [w for w, k in df.most_common() if 3 <= k <= 0.6 * n][:top]
    if len(vocab) < 4:
        return few(rows, caps, docs)
    for _ in range(5):  # words every pillar uses link pillars together: set them aside and cluster again
        vs = set(vocab)
        dv = [d & vs for d in docs]
        clusters = _agglomerate(vocab, dv, df, n, threshold)
        lab = _assign(dv, clusters, df)
        shared = []
        for w in vocab:
            got = collections.Counter(l for d, l in zip(dv, lab) if w in d and l is not None)
            if got and got.most_common(1)[0][1] / sum(got.values()) < 0.6:
                shared.append(w)
        if not shared:
            break
        vocab = [w for w in vocab if w not in shared]
    while True:
        lab = _assign(dv, clusters, df)
        cnt = collections.Counter(l for l in lab if l is not None)
        small = {i for i in range(len(clusters)) if cnt[i] < min_share * n}
        if not small:
            break
        clusters = [c for i, c in enumerate(clusters) if i not in small]
    total = sum(cnt.values()) or 1
    out = []
    for i, c in enumerate(clusters):
        mine = [k for k, l in enumerate(lab) if l == i]
        ws = sorted(c, key=lambda w: -df[w])
        plain = [w for w in ws if w not in tag_only] or ws
        ex = max(mine, key=lambda k: (len(docs[k] & set(c)), -abs(len(caps[k]) - 70)))
        out.append({"name": plain[0], "share": cnt[i] / total, "posts": cnt[i], "words": plain[:8],
                    "hashtag": next(("#" + w for w in ws if w in tag_only), None), "example": caps[ex], "rows": mine})
    out.sort(key=lambda p: -p["posts"])
    # shares rounded to three places that still sum to exactly 1
    for p in out:
        p["share"] = round(p["share"], 3)
    if out:
        out[0]["share"] = round(1 - sum(p["share"] for p in out[1:]), 3)
    return out, [k for k, l in enumerate(lab) if l is None]


# compositions ------------------------------------------------------------------------------------------------------

def compositions(photos):
    import palette as P
    if not photos:
        return []
    rows = []
    for e in photos:
        r = e["w"] / max(1, e["h"])
        orient = "portrait" if r < 0.95 else "landscape" if r > 1.05 else "square"
        fx, fy = e["focal"]
        centered = abs(fx - 0.5) <= 0.12 and abs(fy - 0.5) <= 0.12
        cols = e["colors"]
        field = max(sum(o["share"] for o in cols if P.dist(tuple(o["rgb"]), tuple(c["rgb"])) < 16) for c in cols)
        rows.append({"src": e["src"], "orient": orient, "centered": centered, "field": field, "bright": e["bright"]})
    n = len(rows)
    out = []
    for orient in ("portrait", "square", "landscape"):
        hits = [r for r in rows if r["orient"] == orient]
        if hits:
            label = {"portrait": "tall 4:5 frames", "square": "square frames", "landscape": "wide frames"}[orient]
            out.append({"name": label, "share": round(len(hits) / n, 3), "examples": [r["src"] for r in spaced(hits)]})
    c = [r for r in rows if r["centered"]]
    out.append({"name": "subject centered", "share": round(len(c) / n, 3), "examples": [r["src"] for r in spaced(c)]})
    t = [r for r in rows if not r["centered"]]
    out.append({"name": "subject off center (on a third or low in the frame)", "share": round(len(t) / n, 3),
                "examples": [r["src"] for r in spaced(t)]})
    f = [r for r in rows if r["field"] >= 0.5]
    out.append({"name": "one color field covers half the frame or more", "share": round(len(f) / n, 3),
                "examples": [r["src"] for r in spaced(sorted(f, key=lambda r: -r["field"]))]})
    b = statistics.mean(r["bright"] for r in rows)
    light = [r for r in rows if r["bright"] >= 0.5]
    out.append({"name": "bright, airy exposure" if b >= 0.5 else "low, moody exposure",
                "share": round((len(light) if b >= 0.5 else n - len(light)) / n, 3),
                "examples": [r["src"] for r in spaced(light if b >= 0.5 else [r for r in rows if r["bright"] < 0.5])],
                "mean_brightness": round(b, 3)})
    return out


# cadence -----------------------------------------------------------------------------------------------------------

def cadence(rows):
    ts = sorted(r["ts"] for r in rows if r.get("ts"))
    if len(ts) < 4:
        return {"per_week": None, "slots": [], "on_rhythm": None}
    weeks = max(1.0, (ts[-1] - ts[0]) / (7 * 86400))
    per_week = len(ts) / weeks
    wd = collections.Counter(when(t).weekday() for t in ts)
    # their days: every weekday that carries a fifth of their posts or more, and always the one that carries the most
    days = [d for d, n in wd.most_common() if n >= SLOT * len(ts)] or [wd.most_common(1)[0][0]]
    slots, near = [], 0
    for d in sorted(days):
        mins = sorted(when(t).hour * 60 + when(t).minute for t in ts if when(t).weekday() == d)
        med = int(statistics.median(mins))
        med = int(round(med / 5) * 5)
        slots.append({"day": WEEKDAYS[d], "time": f"{med // 60:02d}:{med % 60:02d}", "posts": wd[d],
                      "share": round(wd[d] / len(ts), 3)})
        near += sum(1 for m in mins if abs(m - med) <= 60)
    return {"per_week": round(per_week, 1), "slots": slots, "timezone": "UTC",
            "on_rhythm": round(near / len(ts), 3),
            "weekday_counts": {WEEKDAYS[d]: wd.get(d, 0) for d in range(7)}}


def off_cadence(ts, cad):
    if not cad["slots"]:
        return False
    d = when(ts)
    for s in cad["slots"]:
        if s["day"] == WEEKDAYS[d.weekday()]:
            h, m = map(int, s["time"].split(":"))
            return abs(d.hour * 60 + d.minute - (h * 60 + m)) > 90
    return True


# likes -------------------------------------------------------------------------------------------------------------

def theme_counts(texts):
    c = collections.Counter()
    for t in texts:
        toks = set(tokens(t))
        for theme, ws in THEMES.items():
            if toks & set(ws):
                c[theme] += 1
    return c


def lexicon_palette(texts):
    c = collections.Counter(tok for t in texts for tok in tokens(t) if tok in COLOR_WORDS)
    total = sum(c.values()) or 1
    return [{"hex": COLOR_WORDS[w], "name": w, "area": round(n / total, 3), "mentions": n} for w, n in c.most_common(5)]


def reel_pacing(reels):
    files = sorted({m for r in reels for m in (r.get("media") or []) if str(m).lower().endswith((".mp4", ".mov"))})
    out = []
    for f in files[:12]:
        if not Path(f).exists():
            continue
        p = subprocess.run([_env.ffmpeg(), "-hide_banner", "-i", f, "-vf", "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"],
                           capture_output=True, text=True)
        cuts = p.stderr.count("pts_time:")
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
        dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
        if dur:
            out.append({"seconds": round(dur, 1), "cuts": cuts, "shot_seconds": round(dur / (cuts + 1), 2)})
    if not out:
        return {"reels_measured": 0}
    return {"reels_measured": len(out), "avg_seconds": round(statistics.mean(r["seconds"] for r in out), 1),
            "avg_shot_seconds": round(statistics.mean(r["shot_seconds"] for r in out), 2)}


def bio_rows(bio):
    """The bio's sentences as captions, for a feed whose photographs carry no words."""
    return [{"caption": s.strip()} for s in re.split(r"(?<=[.!?])\s+|\n+", bio or "") if len(s.split()) >= 2]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    _env.enter()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    for s in ("stats.py", "picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    stats = _env.read_json("stats.json")
    pal = _env.read_json("palette.json") or {}
    idx = _env.read_json("photo_index.json") or []
    posts, reels = lib["posts"], lib["reels"]
    rows = posts + reels  # one caption and one time each; posts first so row k < len(posts) is a post
    said_rows = rows if any((r.get("caption") or "").strip() for r in rows) else bio_rows(lib.get("bio"))
    vc = voice(said_rows)
    pls, unclaimed = pillars(said_rows)
    if said_rows is not rows:  # pillars read from the bio claim no post
        pls, unclaimed = [dict(p, rows=[]) for p in pls], list(range(len(rows)))
    cad = cadence(rows)
    post_photos = [e for e in idx if e["kind"] == "post"]
    comps = compositions(post_photos)
    photo_of = {}
    for e in post_photos:
        photo_of.setdefault(e["row"], e["src"])
    for p in pls:
        p["examples"] = [rows[k]["caption"] for k in spaced(p["rows"])]
        found = collections.Counter(x.strip() for k in p["rows"] for m in re.findall(LIST3, clean(rows[k]["caption"]))
                                    for x in m[-3:] if len(x.split()) <= 4)
        p["items"] = [x for x, _ in found.most_common(12)]
        p["labels"] = [x for x, _ in collections.Counter(m.group(1) for k in p["rows"]
                                                         for m in [re.match(r"^\s*([^:\n#]{2,28}):\s", rows[k]["caption"])] if m).most_common(4)]

    # likes: what they aspire to
    like_accounts = collections.Counter(r.get("account") for r in lib["likes"] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved", []) if r.get("account"))
    liked_media_accounts = collections.Counter(r.get("account") for r in lib.get("liked_media", []) if r.get("account"))
    own_themes = theme_counts([r.get("caption") or "" for r in rows])
    liked_themes = theme_counts(list(like_accounts.elements()) + list(saved_accounts.elements()) +
                                list(liked_media_accounts.elements()))
    n_liked = sum(like_accounts.values()) + sum(saved_accounts.values()) + sum(liked_media_accounts.values())
    likes_palette = pal.get("likes") or lexicon_palette(list(like_accounts) + list(saved_accounts))
    likes_from = "the liked images" if pal.get("likes") else "the color words in the names of the accounts they like and save"
    subjects = []
    for th, k in liked_themes.most_common(6):
        mine = own_themes.get(th, 0) / max(1, len(rows))
        share = k / max(1, n_liked)
        accts = [a for a, _ in (like_accounts + saved_accounts + liked_media_accounts).most_common()
                 if set(tokens(a)) & set(THEMES[th])][:4]
        subjects.append({"subject": th, "likes_share": round(share, 3), "own_share": round(mine, 3),
                         "lift": round(share / mine, 1) if mine else None, "accounts": accts})
    aspire = [s for s in subjects if s["likes_share"] >= 0.15 and (not s["own_share"] or s["likes_share"] >= 2 * s["own_share"])]
    pacing = reel_pacing(reels)

    # outliers: posts that break two or more of palette, pillar, voice, cadence
    off_pal = set(pal.get("off_palette") or [])
    kept = [d["name"] for d in vc["devices"]]
    outliers, usual = [], stats.get("median_likes")
    unclaimed_set = set(unclaimed)
    for k, r in enumerate(rows):
        breaks = []
        if k < len(posts) and k in off_pal:
            breaks.append("palette")
        if k in unclaimed_set:
            breaks.append("pillar")
        cap = r.get("caption") or ""
        if LOUD(cap):
            breaks.append("loud")
        elif kept and not any(DEVICES[d][1](cap) for d in kept):
            breaks.append("voice")
        if r.get("ts") and off_cadence(r["ts"], cad):
            breaks.append("cadence")
        if len(breaks) >= 2 and not set(breaks) <= {"pillar", "voice"}:  # a short caption alone is not an outlier
            outliers.append({"date": when(r["ts"]).strftime("%Y-%m-%d %a %H:%M"), "kind": "post" if k < len(posts) else "reel",
                             "caption": cap, "breaks": breaks, "likes": r.get("likes"),
                             "times_usual": round(r["likes"] / usual, 2) if usual and r.get("likes") is not None else None,
                             "photo": photo_of.get(k)})

    feed = pal.get("feed") or []
    did = moments(rows, pls, photo_of)
    research = {
        "handle": lib["handle"], "name": lib.get("name"), "bio": lib.get("bio"), "window": lib.get("window"),
        "source": lib["source"], "doors": lib.get("doors", {}), "counts": stats.get("counts"),
        "palette": {"feed": feed, "others": pal.get("others"), "off_palette_posts": len(off_pal),
                    "posts_read": pal.get("posts_read"), "lead_floor": pal.get("lead_floor"),
                    "likes": likes_palette, "likes_from": likes_from},
        "compositions": comps, "voice": vc,
        "pillars": [{k: v for k, v in p.items() if k != "rows"} for p in pls], "unclaimed_posts": len(unclaimed),
        "cadence": cad, "likes": {"accounts": len(like_accounts), "likes": sum(like_accounts.values()),
                                  "saves": sum(saved_accounts.values()), "liked_images": len(lib.get("liked_media", [])),
                                  "top": [{"account": a, "likes": n} for a, n in like_accounts.most_common(8)],
                                  "subjects": subjects, "aspire": aspire, "own_themes": dict(own_themes.most_common())},
        "outliers": outliers, "median_likes": usual, "reels": pacing,
    }
    _env.write_json("research.json", research)

    # the brand draft: the agent rewrites the statement, stop list and voice lines in their words
    pnames = [p["name"] for p in pls]
    cnames = [c["name"] for c in feed]
    days = [s["day"] for s in cad["slots"]]
    stop = []
    said = {"cadence": "posting off your days and times",
            "palette": "colors outside your palette",
            "loud": "shouting captions",
            "voice": "captions outside your voice",
            "pillar": "posts outside what you post about"}
    for brk in sorted(said, key=lambda x: -sum(1 for o in outliers if x in o["breaks"])):
        hit = [o for o in outliers if brk in o["breaks"]]
        lows = [o["times_usual"] for o in hit if o["times_usual"] is not None]
        # a habit goes on the stop list only when the posts that had it landed under their usual likes
        if len(stop) < 3 and len(hit) >= 2 and (not lows or statistics.mean(lows) < 1):
            used = {x["example"] for x in stop}
            stop.append({"line": said[brk], "why": f"{len(hit)} posts did" +
                         (f", and they got {statistics.mean(lows):.1f}x your usual likes" if lows else ""),
                         "example": next((o["caption"] for o in hit if o["caption"] not in used), hit[0]["caption"])})
    if cad["on_rhythm"] is not None and cad["on_rhythm"] < 0.8:
        stop.append({"line": "posting off your rhythm", "why": f"only {cad['on_rhythm']:.0%} of posts land on your days and times"})
    low = [r for r in posts if usual and r.get("likes") is not None and r["likes"] < usual / 2 and clean(r.get("caption"))]
    if not stop and low:  # the posts that landed under half their usual likes, said as what they share
        r = min(low, key=lambda r: r["likes"])
        stop.append({"line": f"posts like \"{clean(r['caption']).strip()}\"",
                     "why": f"{len(low)} post{'s' if len(low) > 1 else ''} got under half your usual likes; this one {r['likes']}",
                     "example": r["caption"]})
    if vc.get("hashtags_per_caption", 0) > 4:
        stop.append({"line": "long hashtag blocks", "why": f"{vc['hashtags_per_caption']} hashtags a caption"})
    weak = [d for d in vc["all_devices"] if 0 < d["share"] < 0.3 and d["name"] in ("emoji sign-off",)]
    brand = {
        "statement": (f"{', '.join(pnames[:-1])} and {pnames[-1]}" if len(pnames) > 1 else (pnames or ['your days'])[0]) +
                     f", in {' and '.join(cnames[:2]) or 'your colors'}" +
                     (f", on {' and '.join(d + 's' for d in days)}" if days else "") + ".",
        "palette": [{"name": c["name"], "hex": c["hex"], "share": c["share"], "posts": c["posts"]} for c in feed],
        "compositions": [c["name"] for c in comps if c["share"] >= 0.5],
        "pillars": [{"name": p["name"], "share": p["share"], "words": p["words"][:5], "example": p["example"]} for p in pls],
        "cadence": {"per_week": cad["per_week"], "slots": [{"day": s["day"], "time": s["time"]} for s in cad["slots"]],
                    "timezone": cad.get("timezone", "UTC")},
        "voice": {"case": vc.get("case"), "avg_words": vc.get("avg_words"), "emoji_per_caption": vc.get("emoji_per_caption"),
                  "devices": [{"name": d["name"], "share": d["share"], "examples": d["examples"]} for d in vc["devices"]],
                  "lean_words": [w["word"] for w in vc.get("lean_words", [])[:6]], "hashtags": vc.get("hashtags", [])[:4]},
        "aspire": {"palette": [{"name": c["name"], "hex": c["hex"]} for c in likes_palette[:4]],
                   "subjects": [s["subject"] for s in aspire] or [s["subject"] for s in subjects[:2]]},
        "stop": stop,
    }
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "name": lib.get("name"), "bio": lib.get("bio"), "window": lib.get("window"),
        "palette": {"feed": [{"hex": c["hex"], "name": c["name"], "share": c["share"], "photo": c.get("photo")} for c in feed],
                    "likes": likes_palette},
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": pacing.get("avg_shot_seconds")},
        "ask": True, "style": None, "hook": None, "question": None, "signoff": None,
        "register": {"lowercase": vc.get("case") == "lowercase", "emoji": vc.get("emoji_per_caption"),
                     "avg_words": vc.get("avg_words"), "hashtags": vc.get("hashtags", [])[:3],
                     "samples": [d["examples"][0] for d in vc["devices"][:4] if d["examples"]]},
        "pillars": pnames,
        "moments": did,
        "avoid": ["neon", "loud all-caps captions", "stock-photo gloss"] if cnames else ["muddy grading"],
        "brand": brand,
        "music": {"words": [], "avoid": []},
    }
    if not Path("taste.json").exists() or "research.py draft" in (_env.read_json("taste.json") or {}).get("written_by", ""):
        _env.write_json("taste.json", taste)

    pct = lambda x: f"{x:.0%}" if x is not None else "n/a"
    q = lambda c: re.sub(r"\s*\n\s*", " / ", (c or "").strip())
    L = [f"# taste draft for @{lib['handle']} ({' to '.join(lib.get('window') or [])})", "",
         "The agent writes taste.md from this: one page, five paragraphs that start with the five headings below,",
         "every claim carrying its number and an example. Their own words (bio, what they asked) outrank every line here.", "",
         "## you are",
         f"- bio: {lib.get('bio') or '(none in the data)'}",
         f"- pillars ({len(rows) - len(unclaimed)} of {len(rows)} posts and reels claimed):"]
    L += [f"  - {p['name']}: {pct(p['share'])} ({p['posts']} posts); words {', '.join(p['words'][:6])}"
          f"{'; tag ' + p['hashtag'] if p['hashtag'] else ''}; e.g. \"{q(p['example'])}\"" for p in pls]
    L += [f"- cadence: {cad['per_week']} posts a week; " + ", ".join(f"{s['day']} {s['time']} ({s['posts']} posts)" for s in cad["slots"]) +
          f"; {pct(cad['on_rhythm'])} land within an hour of that rhythm",
          f"- moments ({len(did)} posts with a photograph and words; taste.json `moments` holds them for the film):"]
    L += [f"  - {m['date']} \"{m['line']}\"" + "".join(f"; {x}" for x in (m["place"], ", ".join(m["people"])) if x) +
          f" ({m['pillar'] or 'no pillar'}; {m['photo']})" for m in did]
    L += ["", "## you like",
          f"- {research['likes']['likes']} likes to {len(like_accounts)} accounts, {research['likes']['saves']} saves, "
          f"{research['likes']['liked_images']} liked images",
          f"- palette of what you like ({likes_from}): " + ", ".join(f"{c['name']} {c['hex']} ({pct(c.get('area'))})" for c in likes_palette)]
    L += [f"- {s['subject']}: {pct(s['likes_share'])} of your likes and saves, {pct(s['own_share'])} of your own captions; "
          f"accounts {', '.join(s['accounts'])}" for s in subjects[:5]]
    L += ["", "## your style is",
          f"- palette (share of {pal.get('posts_read')} posts each color leads; floor {pct(pal.get('lead_floor'))}): " +
          ", ".join(f"{c['name']} {c['hex']} {pct(c['share'])} ({c['posts']} posts)" for c in feed) +
          f"; {len(off_pal)} posts lead with none of them"]
    L += [f"- {c['name']}: {pct(c['share'])}" for c in comps]
    L += ["- music: the look's own; add words the person uses for it (\"no drums\", \"piano\") to taste.json `music`", "", "## your voice is",
          f"- {vc.get('captions')} captions, {vc.get('case')} ({pct(vc.get('lowercase_share'))} all lowercase), {vc.get('avg_words')} words, "
          f"{vc.get('emoji_per_caption')} emoji and {vc.get('hashtags_per_caption')} hashtags a caption"]
    for d in vc["all_devices"]:
        L.append(f"- {d['name']} ({d['what']}): {pct(d['share'])}" + (" (kept)" if d["share"] >= 0.3 else ""))
        L += [f"    \"{q(e)}\"" for e in d["examples"][:3]] if d["share"] >= 0.3 else []
    L += [f"- words you lean on: {', '.join(w['word'] + ' ' + pct(w['share']) for w in vc.get('lean_words', [])[:8])}",
          "", "## avoid"]
    L += [f"- outlier {o['date']} ({', '.join(o['breaks'])}; {o['likes']} likes, {o['times_usual']}x usual): \"{q(o['caption'])}\"" for o in outliers]
    L += [f"- {s['line']}: {s['why']}" for s in stop] + [""]
    _env.write_text("taste.draft.md", "\n".join(L).replace("\n\n\n", "\n\n"))
    print("palette: " + ", ".join(f"{c['name']} {pct(c['share'])}" for c in feed) + f"; off palette {len(off_pal)}")
    print("pillars: " + ", ".join(f"{p['name']} {pct(p['share'])}" for p in pls) + f"; unclaimed {len(unclaimed)}")
    print("voice: " + ", ".join(f"{d['name']} {pct(d['share'])}" for d in vc["devices"]))
    print(f"cadence: {cad['per_week']}/week " + ", ".join(f"{s['day'][:3]} {s['time']}" for s in cad["slots"]) + f"; on rhythm {pct(cad['on_rhythm'])}")
    print("likes: " + ", ".join(c["name"] for c in likes_palette) + "; aspire " + ", ".join(s["subject"] for s in aspire))
    print(f"outliers: {len(outliers)}")
    print("wrote research.json, taste.json (draft) and taste.draft.md; now write taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
