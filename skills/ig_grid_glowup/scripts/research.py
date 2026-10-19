#!/usr/bin/env python3
"""Movement 1, research: the grid read, the audit, and the taste profile. Reads build/library.json; writes
build/research.json, build/audit.json, out/audit.md, a machine draft of build/taste.json, and build/taste.draft.md.

USAGE (from the workspace root):
    python3 S/scripts/research.py            # runs picks.py and palette.py, then everything below
    python3 S/scripts/research.py audit      # re-renders out/audit.md from build/audit.json after the eye pass

It reads:
  grid      the last 30 posts and reels as a 3-wide grid (build/grid.json from picks.py): runs of posts whose color
            clashes with the rest, screenshots and text tiles, busy photos side by side, posts the 4:5 grid crops,
            the light and dark rhythm across rows
  numbers   their best-performing visual patterns by their own likes and saves, over every post with numbers: warm
            against cool, quiet against bold color, calm against busy, near their palette against far from it,
            photo against text; each pattern with its post count and its average likes and saves
  likes     what their likes and saves say they want their grid to look like: the themes and color words of the
            accounts they like, save and follow (and the colors of liked media when the library has it)
  palette   the palette their best posts share (palette.py), against the palette of what they like
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines (for the plan's voice)
  cadence   posts per month and weekday, the hour they post, gaps (for the posting plan's order and days)
build/audit.json is the audit's source: findings (each a plain title, a plain sentence, the grid positions it covers,
and its numbers), the patterns, what their likes say they want, the recommended grid direction (tonal, blocks or
alternate) and why. The agent looks at build/grid-sheet.png, edits audit.json (adds what only an eye sees, such as
close crops among wide ones; corrects anything the numbers got wrong), and runs `research.py audit`.
"""
import argparse
import collections
import datetime as dt
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

S = Path(__file__).resolve().parent
DIRECTIONS = {"tonal": "tonal and quiet", "blocks": "color-blocked", "alternate": "alternating photo and type"}

COLOR_WORDS = {
    "terracotta": "#c8643f", "ochre": "#c98b2b", "olive": "#7d7a3a", "rust": "#a5482a", "linen": "#e8dcc6",
    "saffron": "#e0a030", "amber": "#d9902f", "golden": "#d8a443", "gold": "#d4a640", "lemon": "#e9d36a",
    "sand": "#d9c19a", "clay": "#b46a4c", "sunbaked": "#d58a4f", "honey": "#d9a441", "cream": "#efe4cc",
    "sage": "#97a585", "moss": "#6b7444", "ocean": "#2f6f8f", "sea": "#3a7ea1", "harbor": "#4c6f84",
    "sky": "#8fb8d6", "blue": "#3d6fa8", "navy": "#24324f", "pink": "#e6a3b0", "rose": "#c9707f", "coral": "#e9775f",
    "peach": "#f0b38a", "berry": "#7f2f4f", "plum": "#6a3c5e", "lavender": "#b5a2cf", "mint": "#a8d8bd",
    "forest": "#2f5236", "green": "#4f8a4a", "black": "#141414", "noir": "#161616", "mono": "#7a7a7a",
    "neon": "#ff3ea5", "chrome": "#c9ccd1", "coffee": "#5b3a29", "espresso": "#3b2418", "chocolate": "#5a3a28",
    "tomato": "#d0432f", "red": "#c23b2e", "orange": "#e57a33", "yellow": "#efc94c", "white": "#f4f1ea",
    "warmtones": "#c9824f", "sunset": "#e9773f", "dusk": "#5a4a73", "salt": "#f1ece2", "bread": "#cf9a5b",
    "crumb": "#c8955f", "kodak": "#e0b23a", "portra": "#d9a27c", "neutral": "#cbbfae", "muted": "#a89a8a",
    "tonal": "#b59a7e", "beige": "#d8c7ac", "oat": "#d9ccb4", "stone": "#a39a8c", "minimal": "#e6dfd3",
}
SPOKEN = {"warmtones": "warm tones", "sunbaked": "sun-baked"}
THEMES = {
    "film photography": ["35mm", "film", "portra", "kodak", "grain", "analog", "shotonfilm", "filmphotography", "frames", "120"],
    "food": ["eats", "food", "table", "kitchen", "plate", "bread", "mezze", "crumb", "salt", "slowfood", "cook", "cooks",
             "tomatoes", "olive", "breakfast", "lunch", "dinner", "pasta", "tacos", "market"],
    "coffee": ["espresso", "coffee", "cafe", "latte", "stops"],
    "travel": ["wanderer", "travel", "paths", "atlas", "getaways", "streets", "doorways", "postcard", "slowtravel", "road",
               "trip", "train", "harbor", "foodtravel"],
    "slow living": ["slow", "slowly", "mornings", "afternoons", "linen", "notes", "journal", "home"],
    "light": ["light", "golden", "hour", "sun", "sunbaked", "amber", "warm", "warmtones"],
    "fitness": ["gym", "run", "lift", "fit", "yoga", "training"],
    "music": ["music", "vinyl", "dj", "gig", "band", "live"],
    "fashion": ["outfit", "ootd", "style", "fit", "wear", "thrift"],
    "design": ["design", "type", "studio", "poster", "print"],
    "quiet tonal": ["quiet", "tonal", "tones", "muted", "soft", "neutral", "still", "calm", "minimal", "linen", "beige",
                    "oat", "stone", "mornings"],
    "bold color": ["neon", "color", "colour", "pop", "bright", "vivid", "rainbow", "loud", "chroma"],
    "type and words": ["quotes", "words", "type", "letters", "poster", "notes", "journal", "zine"],
}
PLACES = ["lisbon", "porto", "oaxaca", "sicily", "palermo", "marrakech", "paris", "rome", "london", "tokyo", "mexico city",
          "new york", "berlin", "barcelona", "madrid", "naples", "athens", "istanbul", "kyoto", "seoul", "bali", "cdmx",
          "los angeles", "san francisco", "chicago", "amsterdam", "copenhagen", "vienna", "prague", "budapest", "home"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
FILM = {"film photography"}


def run(script):
    p = subprocess.run([sys.executable, str(S / script)], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{script} failed:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def month(ts):
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).month


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def caption_read(rows):
    caps = [r.get("caption") or "" for r in rows if (r.get("caption") or "").strip()]
    if not caps:
        return {"captions": 0}
    words = [len(c.split()) for c in caps]
    letters = [ch for c in caps for ch in c if ch.isalpha()]
    lower = sum(1 for ch in letters if ch.islower()) / max(1, len(letters))
    first = collections.Counter(tokens(c)[0] for c in caps if tokens(c))
    def last_word(c):
        t = [w for w in tokens(re.sub(r"#\w+", "", c))]
        return t[-1] if t else None
    last = collections.Counter(w for w in map(last_word, caps) if w)
    stripped = [re.sub(r"(#\w+|\s)+$", "", EMOJI.sub("", c)).strip() for c in caps]
    ends = collections.Counter(("..." if s.endswith("...") else "." if s.endswith(".") else "!" if s.endswith("!") else
                                "?" if s.endswith("?") else "no mark") for s in stripped if s)
    tags = collections.Counter(t.lower() for c in caps for t in re.findall(r"#\w+", c))
    emo = collections.Counter(e for c in caps for e in EMOJI.findall(c))
    return {
        "captions": len(caps),
        "avg_words": round(statistics.mean(words), 1),
        "median_chars": int(statistics.median(len(c) for c in caps)),
        "lowercase_share": round(lower, 2),
        "emoji_per_caption": round(sum(emo.values()) / len(caps), 2),
        "top_emoji": [e for e, _ in emo.most_common(5)],
        "endings": dict(ends.most_common()),
        "hashtags_per_caption": round(sum(tags.values()) / len(caps), 2),
        "top_hashtags": [t for t, _ in tags.most_common(8)],
        "opens_with": [w for w, _ in first.most_common(6)],
        "closes_with": [w for w, _ in last.most_common(6)],
        "samples": sorted(set(caps), key=lambda c: -len(c))[:3] + sorted(set(caps), key=len)[:3],
    }


def theme_counts(texts):
    c = collections.Counter()
    for t in texts:
        toks = set(tokens(t))
        for theme, words in THEMES.items():
            if toks & set(words):
                c[theme] += 1
    return c


def lexicon_palette(texts):
    c = collections.Counter()
    for t in texts:
        for tok in tokens(t):
            if tok in COLOR_WORDS:
                c[tok] += 1
    total = sum(c.values()) or 1
    return [{"hex": COLOR_WORDS[w], "name": SPOKEN.get(w, w), "share": round(n / total, 3), "mentions": n} for w, n in c.most_common(6)]


def image_palette(files):
    sys.path.insert(0, str(S))
    import picks  # noqa: E402
    acc = collections.Counter()
    for f in files[:80]:
        try:
            for col in picks.analyse(f)["colors"]:
                q = tuple((v // 24) * 24 + 12 for v in col["rgb"])
                acc[q] += col["share"]
        except Exception:
            continue
    total = sum(acc.values()) or 1
    return [{"hex": "#%02x%02x%02x" % k, "name": "", "share": round(v / total, 3)} for k, v in acc.most_common(5)]


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
            out.append({"file": f, "seconds": round(dur, 1), "cuts": cuts, "shot_seconds": round(dur / (cuts + 1), 2)})
    if not out:
        return {"reels_measured": 0}
    return {
        "reels_measured": len(out),
        "avg_seconds": round(statistics.mean(r["seconds"] for r in out), 1),
        "avg_shot_seconds": round(statistics.mean(r["shot_seconds"] for r in out), 2),
        "reels": out,
    }


def cadence(rows):
    by_m = collections.Counter(month(r["ts"]) for r in rows if r.get("ts"))
    days = sorted({dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).date() for r in rows if r.get("ts")})
    wd = collections.Counter(d.strftime("%A") for d in days)
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    streak = best = 1
    for g in gaps:
        streak = streak + 1 if g == 1 else 1
        best = max(best, streak)
    return {
        "per_month": {MONTHS[m - 1]: by_m.get(m, 0) for m in range(1, 13) if m <= max(by_m or [1])},
        "top_weekday": wd.most_common(1)[0][0] if wd else None,
        "longest_streak_days": best if days else 0,
        "longest_gap_days": max(gaps) if gaps else 0,
        "posting_days": len(days),
    }


def type_direction(themes, register, pacing):
    film = themes.get("film photography", 0)
    loud = register.get("emoji_per_caption", 0) > 1 or (pacing.get("avg_shot_seconds") or 9) < 1.2
    if loud:
        return {"lead": "kinetic", "display": "Archivo Black", "text": "Archivo",
                "why": "heavy emoji and fast reels read as loud: a heavy grotesk that can slam"}
    if film and themes.get("travel", 0) >= film:
        return {"lead": "documentary", "display": "Space Grotesk", "text": "JetBrains Mono",
                "why": "travel carried on film: a documentary grotesk with mono timestamps"}
    return {"lead": "editorial", "display": "Fraunces", "text": "Inter",
            "why": "quiet captions and film photography: a soft serif with a plain sans for labels"}



def where(positions, rows_too=True):
    """Grid positions (0 is the top left) in plain words: post numbers counted from the top left, and their rows."""
    nums = [p + 1 for p in positions]
    rows = sorted({p // 3 + 1 for p in positions})
    rw = ("row " + str(rows[0])) if len(rows) == 1 else ("rows " + ", ".join(map(str, rows[:-1])) + " and " + str(rows[-1]))
    if not rows_too:
        return ("posts " + ", ".join(map(str, nums[:-1])) + f" and {nums[-1]}") if len(nums) > 1 else f"post {nums[0]}"
    if len(nums) > 2 and nums == list(range(nums[0], nums[-1] + 1)):
        return f"posts {nums[0]} to {nums[-1]} ({rw})"
    if len(nums) == 1:
        return f"post {nums[0]} ({rw})"
    return "posts " + ", ".join(map(str, nums[:-1])) + f" and {nums[-1]} ({rw})"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 1) if xs else None


def runs(flags):
    out, cur = [], []
    for i, f in enumerate(flags):
        if f:
            cur.append(i)
        else:
            if cur:
                out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def numbers_of(cells):
    return {"likes": mean(c.get("likes") for c in cells), "saves": mean(c.get("saves") for c in cells), "posts": len(cells)}


def grid_findings(grid, palette_names):
    cells = grid["cells"]
    photos = [c for c in cells if c.get("a")]
    base = [c for c in photos if not c["flags"]]
    usual = numbers_of(base or photos)
    out = []
    def vs(group):
        n = numbers_of(group)
        rest = [c for c in photos if c not in group and c.get("likes") is not None]
        usual = numbers_of(rest or photos)
        if n["likes"] is None or usual["likes"] is None:
            return "", n
        bits = f" They got {n['likes']:.0f} likes"
        if n["saves"] is not None and usual["saves"] is not None:
            bits += f" and {n['saves']:.0f} saves on average, against {usual['likes']:.0f} likes and {usual['saves']:.0f} saves for the rest of your grid."
        else:
            bits += f" on average, against {usual['likes']:.0f} for the rest of your grid."
        return bits, n
    clash = runs(["clash" in c["flags"] for c in cells])
    for r in sorted(clash, key=len, reverse=True):
        group = [cells[i] for i in r]
        names = sorted({color_name(tuple(x["rgb"])) for c in group for x in c["a"]["colors"][:2]})[:4]
        tail, n = vs(group)
        title = f"A run of {len(r)} posts in colors your grid never uses" if len(r) > 1 else "One post in a color your grid never uses"
        out.append({"kind": "palette", "title": title, "positions": r, "numbers": n,
                    "plain": f"{where(r).capitalize()} sit in {', '.join(names)}, far from the {palette_names} the rest of "
                             f"your grid lives in, so that stretch reads as someone else's feed.{tail}"})
    text = [c["pos"] for c in cells if "text" in c["flags"]]
    if text:
        tail, n = vs([cells[i] for i in text])
        out.append({"kind": "rhythm", "title": f"{len(text)} screenshot{'s' if len(text) > 1 else ''} breaking the rhythm",
                    "positions": text, "numbers": n,
                    "plain": f"{where(text).capitalize()} {'are' if len(text) > 1 else 'is'} flat white text, which reads "
                             f"as a hole in the grid between your photos.{tail}"})
    pairs = [(a, a + 1) for a in range(len(cells) - 1) if a % 3 < 2] + [(a, a + 3) for a in range(len(cells) - 3)]
    busy_pairs = [(a, b) for a, b in pairs if "busy" in cells[a]["flags"] and "busy" in cells[b]["flags"]]
    busy = sorted({p for ab in busy_pairs for p in ab})
    if len(busy_pairs) >= 2:
        out.append({"kind": "spacing", "title": "Busy photos packed side by side", "positions": busy,
                    "numbers": {"pairs": len(busy_pairs), "of": len(pairs)},
                    "plain": f"{where(busy).capitalize()} are full of detail from edge to edge, and "
                             f"{len(busy_pairs)} of your grid's {len(pairs)} neighbor pairs put two of them together, so the eye "
                             f"gets no quiet space to rest on between them."})
    square = [c["pos"] for c in cells if "square" in c["flags"]]
    if len(square) >= 4:
        out.append({"kind": "crops", "title": f"{len(square)} of your {len(cells)} posts were posted square",
                    "positions": square, "numbers": {"posts": len(square)},
                    "plain": f"Your profile shows every post as a tall 4:5 tile, so the square ones ({where(square, False)}) get "
                             f"their sides trimmed on the grid, and their crops jump in size next to the tall ones."})
    bright = [c["a"]["bright"] for c in photos]
    if len(bright) >= 9:
        rows = [statistics.mean(c["a"]["bright"] for c in cells[i:i + 3] if c.get("a")) for i in range(0, len(cells) - 2, 3)
                if any(c.get("a") for c in cells[i:i + 3])]
        swing = max(rows) - min(rows)
        if swing > 0.18:
            dark = rows.index(min(rows)) + 1
            light = rows.index(max(rows)) + 1
            out.append({"kind": "rhythm", "title": "Rows that jump from light to dark", "positions": [],
                        "numbers": {"darkest_row": dark, "lightest_row": light, "swing": round(swing, 2)},
                        "plain": f"Row {light} is the lightest on your grid and row {dark} the darkest; the brightness swings "
                                 f"by {swing:.0%} between rows, so the grid reads in bands instead of one even feed."})
    return out, usual


def patterns(index, grid):
    """Their best-performing visual patterns: every post cover with numbers, split by one visual trait at a time."""
    posts = [e for e in index if e.get("likes") is not None and e["kind"] in ("grid", "post")]
    if len(posts) < 8:
        return []
    med_l = statistics.median(e["lab"][0] for e in posts)
    med_c = statistics.median(e["chroma"] for e in posts)
    med_d = statistics.median(e["detail"] for e in posts)
    centre = grid.get("median_lab") or [med_l, 0, 0]
    dist = lambda e: sum((a - b) ** 2 for a, b in zip(e["lab"], centre)) ** 0.5
    med_dist = statistics.median(dist(e) for e in posts)
    text = lambda e: e["flat"] > 0.5 and e["chroma"] < 12
    tests = [
        ("warm", "warm color", lambda e: e["warmth"] >= 10 and not text(e), "cool color", lambda e: e["warmth"] < 10 and not text(e)),
        ("quiet", "quiet, muted color", lambda e: e["chroma"] <= med_c * 1.25 and not text(e), "bold, saturated color",
         lambda e: e["chroma"] > max(30, med_c * 1.6)),
        ("calm", "calm frames with space", lambda e: e["detail"] <= med_d and not text(e), "busy, detailed frames",
         lambda e: e["detail"] > med_d * 1.4),
        ("tonal", "posts near your own palette", lambda e: dist(e) <= med_dist and not text(e), "posts far from your palette",
         lambda e: dist(e) > med_dist * 2.2 and not text(e)),
        ("photo", "photos", lambda e: not text(e), "text and screenshots", text),
    ]
    out = []
    for key, a_name, a_test, b_name, b_test in tests:
        A, B = [e for e in posts if a_test(e)], [e for e in posts if b_test(e)]
        if len(A) < 3 or len(B) < 2:
            continue
        na = {"likes": mean(e["likes"] for e in A), "saves": mean(e.get("saves") for e in A), "posts": len(A)}
        nb = {"likes": mean(e["likes"] for e in B), "saves": mean(e.get("saves") for e in B), "posts": len(B)}
        metric = "saves" if na["saves"] is not None and nb["saves"] is not None and (nb["saves"] or 0) > 0 else "likes"
        ratio = round((na[metric] or 0) / max(0.1, nb[metric] or 0.1), 1)
        win, lose = (a_name, b_name) if ratio >= 1 else (b_name, a_name)
        out.append({"key": key, "a": a_name, "b": b_name, "A": na, "B": nb, "metric": metric, "ratio": ratio,
                    "winner": win, "plain": f"{win.capitalize()} did better than {lose}: {na['likes']:.0f} against {nb['likes']:.0f} likes"
                    + (f" and {na['saves']:.0f} against {nb['saves']:.0f} saves" if na["saves"] is not None and nb["saves"] is not None else "")
                    + f" on average ({na['posts']} and {nb['posts']} posts)." if ratio >= 1 else
                    f"{win.capitalize()} did better than {lose}: {nb['likes']:.0f} against {na['likes']:.0f} likes"
                    + (f" and {nb['saves']:.0f} against {na['saves']:.0f} saves" if na["saves"] is not None and nb["saves"] is not None else "")
                    + f" on average ({nb['posts']} and {na['posts']} posts)."})
    out.sort(key=lambda p: -max(p["ratio"], 1 / max(p["ratio"], 0.01)))
    return out


def recommend(pats, liked_themes, caps):
    """The grid direction their numbers and their likes point at."""
    win = {p["key"]: p["ratio"] >= 1 for p in pats}
    ratio = {p["key"]: p["ratio"] for p in pats}
    score = {"tonal": 0.0, "blocks": 0.0, "alternate": 0.0}
    why = {"tonal": [], "blocks": [], "alternate": []}
    for k in ("quiet", "tonal", "calm", "warm"):
        if win.get(k):
            score["tonal"] += min(4, ratio[k])
            why["tonal"].append(next(p["plain"] for p in pats if p["key"] == k))
        elif k in win:
            score["blocks"] += min(4, 1 / max(ratio[k], 0.25))
            why["blocks"].append(next(p["plain"] for p in pats if p["key"] == k))
    if "photo" in win and not win["photo"]:
        score["alternate"] += min(4, 1 / max(ratio["photo"], 0.25)) * 2
        why["alternate"].append(next(p["plain"] for p in pats if p["key"] == "photo"))
    total = sum(liked_themes.values()) or 1
    for theme, d in (("quiet tonal", "tonal"), ("bold color", "blocks"), ("type and words", "alternate")):
        n = liked_themes.get(theme, 0)
        if n:
            score[d] += 4 * n / total * 3
            why[d].append(f"{n} of the accounts they like, save and follow are about {theme}.")
    if (caps.get("avg_words") or 0) > 25:
        score["alternate"] += 1
        why["alternate"].append(f"Their captions run {caps['avg_words']} words, enough to carry type posts.")
    best = max(score, key=score.get)
    return best, {k: round(v, 2) for k, v in score.items()}, why


def color_name(rgb):
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


def hours(rows):
    c = collections.Counter(dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).hour for r in rows if r.get("ts"))
    return c.most_common(1)[0][0] if c else None


def render_audit(audit, handle):
    """out/audit.md: one page in plain words."""
    L = [f"# Your grid, read: @{handle}", "",
         f"These are your last {audit['grid_size']} posts as your profile shows them, three across, newest at the top left "
         f"(the picture is `grid-before.png`, numbered from the top left).", "", "## What your grid is doing", ""]
    for i, f in enumerate(audit["findings"], 1):
        L.append(f"{i}. **{f['title']}.** {f['plain']}")
    L += ["", "## What your own numbers say works", ""]
    for p in [p for p in audit["patterns"] if max(p["ratio"], 1 / max(p["ratio"], 0.01)) >= 1.2][:5]:
        L.append(f"- {p['plain']}")
    L += ["", "## What your likes say you want", "", audit["want"], "",
          f"## The direction: {DIRECTIONS[audit['recommend']]}", "", audit["why"], ""]
    Path("out").mkdir(exist_ok=True)
    Path("out/audit.md").write_text("\n".join(L))


def cmd_audit():
    a = _env.read_json("build/audit.json")
    if not a:
        sys.exit("build/audit.json is missing: run research.py first")
    lib = _env.read_json("build/library.json") or {}
    render_audit(a, lib.get("handle") or "you")
    print(f"wrote out/audit.md ({len(a['findings'])} findings)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", choices=["audit"])
    a = ap.parse_args()
    if a.cmd == "audit":
        return cmd_audit()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    for s in ("picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    pal = _env.read_json("build/palette.json") or {}
    grid = _env.read_json("build/grid.json")
    index = _env.read_json("build/photo_index.json") or []
    posts = lib["posts"]
    captioned = posts + lib["reels"] + lib.get("facebook", [])
    caps = caption_read(captioned)
    like_accounts = collections.Counter(r.get("account") for r in lib["likes"] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved", []) if r.get("account"))
    follow = [r.get("account") for r in lib.get("following", []) if r.get("account")]
    liked_text = list(like_accounts) + list(saved_accounts) + follow + \
        [r.get("caption") or "" for r in lib["likes"] + lib.get("saved", [])]
    liked_media = [m for r in lib["likes"] + lib.get("saved", []) for m in (r.get("media") or []) if Path(m).exists()]
    likes_palette = image_palette(liked_media) if len(liked_media) >= 8 else lexicon_palette(liked_text)
    likes_palette_from = "the photos they liked and saved" if len(liked_media) >= 8 else \
        "the color words in the names and captions of the accounts they like, save and follow"
    own_themes = theme_counts([p.get("caption") or "" for p in captioned])
    liked_themes = theme_counts(list(like_accounts) + list(saved_accounts) + follow +
                                [r.get("caption") or "" for r in lib["likes"] + lib.get("saved", [])])
    saved_themes = theme_counts(list(saved_accounts))
    pacing = reel_pacing(lib["reels"])
    td = type_direction(own_themes + liked_themes, caps, pacing)
    year_palette = [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")}
                    for s in (pal.get("year") or [])]
    names = sorted({(s.get("name") or "").split()[-1] for s in year_palette if s.get("name")})
    palette_names = ", ".join(names[:3]) + " tones" if names else "tones"
    findings, usual = grid_findings(grid, palette_names)
    pats = patterns(index, grid)
    best, scores, why = recommend(pats, liked_themes, caps)
    top_saved = [a for a, _ in saved_accounts.most_common(4)]
    want_bits = []
    if liked_themes:
        want_bits.append("The accounts you like, save and follow lean " +
                         ", ".join(f"{k} ({v})" for k, v in liked_themes.most_common(3)) + ".")
    if top_saved:
        want_bits.append(f"You save posts from {', '.join('@' + x for x in top_saved)} most.")
    if likes_palette:
        want_bits.append(f"The color words in those accounts point at {', '.join(s['name'] for s in likes_palette[:4])}.")
    good = [p for p in pats if p["ratio"] >= 1.3]
    if good:
        want_bits.append("And your own audience agrees: " + good[0]["plain"][0].lower() + good[0]["plain"][1:])
    want = " ".join(want_bits) or "Your likes and saves are not in the data, so the direction follows your own numbers."
    audit = {"written_by": "research.py draft; the agent looks at build/grid-sheet.png, edits this file, then runs research.py audit",
             "grid_size": len(grid["cells"]), "findings": findings, "usual": usual, "patterns": pats, "want": want,
             "recommend": best, "scores": scores,
             "why": f"The {DIRECTIONS[best]} direction: " + " ".join(why[best][:3]) if why[best] else
                    f"The {DIRECTIONS[best]} direction fits the grid you already have."}
    if not Path("build/audit.json").exists() or "research.py draft" in (_env.read_json("build/audit.json") or {}).get("written_by", ""):
        _env.write_json("build/audit.json", audit)
    else:
        audit = _env.read_json("build/audit.json")
    render_audit(audit, lib["handle"])
    cad = cadence(posts + lib["reels"])
    cad["top_hour_utc"] = hours(posts + lib["reels"])
    research = {"handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
                "counts": {k: len(lib.get(k) or []) for k in ("posts", "reels", "stories", "likes", "saved", "comments",
                                                               "followers", "following", "facebook")},
                "palette": {"year": year_palette, "likes": likes_palette, "likes_from": likes_palette_from, "roles": pal.get("roles")},
                "captions": caps,
                "likes": {"accounts": len(like_accounts), "top": [{"account": x, "likes": n} for x, n in like_accounts.most_common(10)],
                          "saved_top": [{"account": x, "saves": n} for x, n in saved_accounts.most_common(6)],
                          "themes": dict(liked_themes.most_common()), "saved_themes": dict(saved_themes.most_common())},
                "posts_themes": dict(own_themes.most_common()), "cadence": cad, "reels": pacing, "type": td,
                "grid": {"findings": [f["title"] for f in findings], "usual": usual}, "patterns": pats,
                "recommend": best, "scores": scores}
    _env.write_json("build/research.json", research)
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    shot = pacing.get("avg_shot_seconds")
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "likes": likes_palette, "direction": "toward their likes" if likes_palette else "their own"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": [t for t, _ in (own_themes + liked_themes).most_common(4)],
        "grid": {"recommend": best, "keep": [p["winner"] for p in pats if p["ratio"] >= 1.2][:4],
                 "drop": [f["title"] for f in findings][:4]},
        "texture": {"grain": 0.16 if film else 0, "vignette": 0.32 if film else 0.0, "leaks": bool(film and warm_light)},
        "avoid": (["cold blue grading", "neon", "screenshots on the grid"] if best == "tonal" else ["muddy grading"]),
    }
    if not Path("build/taste.json").exists() or "research.py draft" in (_env.read_json("build/taste.json") or {}).get("written_by", ""):
        _env.write_json("build/taste.json", taste)
    lines = [f"# taste draft for @{lib['handle']}", "",
             "The agent writes build/taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are", f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
             f"- the grid now: {'; '.join(f['title'] for f in findings)}",
             f"- the usual grid post: {usual.get('likes')} likes, {usual.get('saves')} saves",
             "", "## you like",
             f"- {len(like_accounts)} accounts got their likes; most saved: {', '.join(top_saved)}",
             f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
             f"- palette of their best posts: {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in year_palette)}",
             f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
             "", "## your style is"] + [f"- {p['plain']}" for p in pats] + [
             f"- direction scores: {scores}; recommended {best} ({DIRECTIONS[best]})",
             f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
             "", "## your voice is",
             f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
             f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
             f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
             f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
             f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
             f"- posts most on {cad.get('top_weekday')}, around {cad.get('top_hour_utc')}:00 UTC",
             "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    Path("build/taste.draft.md").write_text("\n".join(lines))
    print(f"grid findings: {len(findings)}")
    for f in findings:
        print(f"  - {f['title']} {[p + 1 for p in f['positions']]}")
    for p in pats:
        print(f"  pattern {p['key']}: {p['plain']}")
    print(f"liked themes: {dict(liked_themes.most_common(4))}")
    print(f"direction scores {scores}; recommended {best}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print("wrote build/research.json, build/audit.json, out/audit.md, build/taste.json (draft) and build/taste.draft.md;")
    print("now look at build/grid-sheet.png, edit build/audit.json, run research.py audit, and write build/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
