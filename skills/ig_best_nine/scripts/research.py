#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile. Reads the run's library.json; writes research.json, a
machine draft of taste.json, and taste.draft.md (the numbers under the five headings the agent turns into
taste.md), all in the run.

USAGE (from the workspace root):
    python3 S/scripts/research.py --run R

It runs stats.py, picks.py and palette.py first (counts, photo picks, the year's palette), then reads the rest. A year
with fewer than nine posts and reels makes nothing: it prints `not delivered: <n> posts, nine needed` and exits 4.
It reads:
  palette   the year's colors versus the colors of what they like and save (from the liked media when the
            library has it, else from the color words in the names and captions of the accounts they like,
            save and follow)
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  cadence   posts per month and weekday, streaks and gaps
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  people    who they talk to most; places from captions, albums and check-ins
  moments   the nine as the moments they were, in the film's order (the ninth first, the first last): the day, their
            caption line, the people tagged and the place named; and the eras, the runs of months one place leads their captions
  nine      what each of the nine shows: its subject (from the caption, the places and the themes), its two strongest
            colors by name, what its caption says; and what the nine share that the rest of the year does not
taste.json carries what the storyboards read: their register (lowercase or not), the words the film sets on screen
(`words`: the title, the promise and the ask, drafted in the first person, which the agent rewrites in their voice),
`order` (the nine by their `ts`, the strongest first: the countdown ends on the first, and the agent reorders it by
what their words and photographs make strongest), `style` (a style the person named, else null: the three looks are
then the trio), `ask` (true where the agent may ask the person which look; false where nothing may be asked, and the
agent picks by taste), `seconds` (the length they asked for, else null), the palette, why each of the nine worked,
what to avoid, and music, the brief the film's bed is made from (its tempo, genre and instrument words that name a
recipe when they want another than the look's, and what to avoid; never an artist, band or song). The agent edits it
before storyboards are drafted.
"""
import collections
import datetime as dt
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import story  # noqa: E402
from stats import short_of_nine  # noqa: E402

S = Path(__file__).resolve().parent

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
    "crumb": "#c8955f", "kodak": "#e0b23a", "portra": "#d9a27c",
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
}
PLACES = ["lisbon", "porto", "oaxaca", "sicily", "palermo", "marrakech", "paris", "rome", "london", "tokyo", "mexico city",
          "new york", "berlin", "barcelona", "madrid", "naples", "athens", "istanbul", "kyoto", "seoul", "bali", "cdmx",
          "los angeles", "san francisco", "chicago", "amsterdam", "copenhagen", "vienna", "prague", "budapest", "home"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
QUIET = {"slow living", "food", "coffee", "light"}  # pillars a calm bed carries, when their reels do not cut fast


def run(script, where):
    p = subprocess.run([sys.executable, str(S / script), "--run", str(where)], capture_output=True, text=True, cwd=_env.WORKSPACE)
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


def places_in(rows, facebook):
    c = collections.Counter()
    by_month = collections.defaultdict(collections.Counter)
    for r in rows + facebook:
        text = " ".join([r.get("caption") or "", r.get("album") or "", r.get("place") or ""]).lower()
        for p in PLACES:
            if re.search(rf"\b{re.escape(p)}\b", text):
                c[p] += 1
                if r.get("ts"):
                    by_month[month(r["ts"])][p] += 1
    return c, by_month


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


def moments(stats):
    """The nine as the moments they were, in the film's order, the ninth first and the first last: the rank, the day,
    their own caption line (no hashtags), the people they tagged, the place the caption names, and whether it was a
    post or a reel."""
    out = []
    for t in sorted(stats.get("top_nine") or [], key=lambda t: -t["rank"]):
        cap = t.get("caption") or ""
        line = re.sub(r"\s+", " ", re.sub(r"#\w+", "", cap)).strip()
        place = next((pl for pl in PLACES if pl != "home" and re.search(rf"\b{re.escape(pl)}\b", line.lower())), None)
        out.append({"rank": t["rank"], "ts": t["ts"], "date": t["date"], "kind": t.get("kind"), "line": line, "people": re.findall(r"@([\w.]*\w)", cap), "place": place})
    return out


def eras(place_by_month):
    """The runs of months the same place leads their captions."""
    out, cur = [], None
    for m in sorted(place_by_month):
        top = place_by_month[m].most_common(1)[0][0]
        if cur and cur["place"] == top:
            cur["to"] = MONTHS[m - 1]
        else:
            cur = {"place": top, "from": MONTHS[m - 1], "to": MONTHS[m - 1]}
            out.append(cur)
    return out


def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


def nine_read(stats, picks):
    """What each of the nine shows, from the photo and the caption."""
    info = {n["rank"]: n for n in picks.get("nine", [])}
    out = []
    for t in stats.get("top_nine", []):
        n = info.get(t["rank"], {})
        cap = re.sub(r"#\w+", "", t.get("caption") or "").strip()
        toks = set(tokens(cap))
        subject = [th for th, ws in THEMES.items() if toks & set(ws)]
        place = next((pl for pl in PLACES if re.search(rf"\b{re.escape(pl)}\b", cap.lower()) and pl != "home"), None)
        colors = []
        for c in sorted(n.get("colors", []), key=lambda c: -c["share"]):
            nm = color_name(c["rgb"])
            if nm not in colors:
                colors.append(nm)
        why = []
        if t.get("kind") == "reel":
            why.append("a reel")
        if subject or place:
            why.append(" and ".join(([place] if place else []) + subject[:2]))
        if colors:
            why.append(" and ".join(colors[:2]))
        out.append({"rank": t["rank"], "kind": t["kind"], "date": t["date"], "month": t["month"], "likes": t.get("likes"),
                    "comments": t.get("comments"), "subject": subject, "place": place,
                    "colors": colors[:3], "bright": n.get("bright"), "caption": cap, "why": "; ".join(why)})
    return out


def shared(nine, posts):
    """What the nine have in common, set against the rest of the year's posts."""
    rest = [p for p in posts if (p.get("caption") or "") not in {x["caption"] for x in nine}]
    lines = []
    for th in THEMES:
        a = sum(1 for x in nine if th in x["subject"])
        b = sum(1 for p in rest if set(tokens(p.get("caption"))) & set(THEMES[th]))
        if a >= 3 and a / max(1, len(nine)) > 1.3 * b / max(1, len(rest)):
            lines.append(f"{th}: {a} of the nine, {round(100 * b / max(1, len(rest)))}% of the rest")
    cols = collections.Counter(c for x in nine for c in x["colors"][:2])
    if cols:
        lines.append("colors of the nine: " + ", ".join(f"{c} ({n})" for c, n in cols.most_common(4)))
    reels = sum(1 for x in nine if x["kind"] == "reel")
    if reels:
        lines.append(f"{reels} of the nine are reels")
    months = sorted({x["month"] for x in nine})
    lines.append(f"the nine come from {len(months)} months: " + ", ".join(MONTHS[m - 1] for m in months))
    return lines


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _env.run_arg(ap)
    where = _env.enter_run(ap.parse_args().run)
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    print(run("stats.py", where).strip().splitlines()[-1])
    stats = _env.read_json("stats.json")
    # a best nine is nine: a year with fewer makes nothing, and says so
    short = short_of_nine(stats)
    if short:
        print(short)
        return 4
    for s in ("picks.py", "palette.py"):
        print(run(s, where).strip().splitlines()[-1])
    pal = _env.read_json("palette.json") or {}
    posts = lib["posts"]
    captioned = posts + lib["reels"] + lib.get("facebook", [])
    caps = caption_read(captioned)
    like_accounts = collections.Counter(r.get("account") for r in lib["likes"] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved", []) if r.get("account"))
    follow = [r.get("account") for r in lib.get("following", []) if r.get("account")]
    liked_text = [a for a in like_accounts.elements()] + [a for a in saved_accounts.elements()] + follow + \
                 [r.get("caption") or "" for r in lib["likes"] + lib.get("saved", [])]
    liked_media = [m for r in lib["likes"] + lib.get("saved", []) for m in (r.get("media") or []) if Path(m).exists()]
    likes_palette = image_palette(liked_media) if len(liked_media) >= 8 else lexicon_palette(liked_text)
    likes_palette_from = "the photos they liked and saved" if len(liked_media) >= 8 else \
        "the color words in the names and captions of the accounts they like, save and follow"
    own_themes = theme_counts([p.get("caption") or "" for p in captioned])
    liked_themes = theme_counts(list(like_accounts.elements()) + list(saved_accounts.elements()) + follow)
    top10 = sum(n for _, n in like_accounts.most_common(10))
    pacing = reel_pacing(lib["reels"])
    places, place_by_month = places_in(posts + lib["reels"], lib.get("facebook", []))
    mom, runs = moments(stats), eras(place_by_month)
    picks = _env.read_json("picks.json") or {}
    nine = nine_read(stats, picks)
    nine_shared = shared(nine, posts + lib["reels"])
    year_palette = [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")}
                    for s in (pal.get("year") or [])]
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    research = {
        "handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": stats.get("counts"),
        "palette": {"year": year_palette, "likes": likes_palette, "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "captions": caps,
        "likes": {"accounts": len(like_accounts), "top": [{"account": a, "likes": n} for a, n in like_accounts.most_common(10)],
                  "top10_share": round(top10 / max(1, sum(like_accounts.values())), 2),
                  "saved_top": [{"account": a, "saves": n} for a, n in saved_accounts.most_common(5)],
                  "themes": dict(liked_themes.most_common())},
        "posts_themes": dict(own_themes.most_common()),
        "cadence": cadence(posts + lib["reels"]),
        "reels": pacing,
        "people": stats.get("people", [])[:8],
        "places": [{"place": p, "posts": n} for p, n in places.most_common(8)],
        "moments": mom, "eras": runs,
        "nine": nine, "nine_shared": nine_shared, "tenth": stats.get("tenth"), "median_likes": stats.get("median_likes"),
        "ranked_by": stats.get("top_ranked_by"),
    }
    _env.write_json("research.json", research)
    shot = pacing.get("avg_shot_seconds")
    pillars = [t for t, _ in (own_themes + liked_themes).most_common(4)]
    # quiet pillars and slow reels take the bed under the look's tempo, fast reels and emoji over it
    lively = bool(shot and shot < 1.5) or caps.get("emoji_per_caption", 0) >= 1
    tempo = story.BPM + 10 if lively else story.BPM - 10 if QUIET & set(pillars) else None
    import storyboard  # noqa: E402
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "likes": likes_palette},
        "words": storyboard.words_default(int(lib["year"])),
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": pillars,
        "people": [p["account"] for p in stats.get("people", [])[:5]],
        "places": [p for p, _ in places.most_common(5) if p != "home"],
        "moments": mom,
        "order": [x["ts"] for x in sorted(stats.get("top_nine") or [], key=lambda t: t["rank"])],
        "style": None,
        "ask": True,
        "seconds": None,
        "nine": [{"rank": x["rank"], "why": x["why"]} for x in nine],
        "avoid": ["cold blue grading", "neon", "stock-photo gloss"] if film else ["muddy grading"],
        "music": {"tempo": tempo, "styles": [], "avoid": ["vocals", "spoken word", "harsh distortion"]},
    }
    if not Path("taste.json").exists() or "research.py draft" in (_env.read_json("taste.json") or {}).get("written_by", ""):
        _env.write_json("taste.json", taste)
    lines = [f"# taste draft for {'@' + lib['handle'] if lib['handle'] else 'them'} ({lib['year']})", "",
             "The agent writes taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are", f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
             f"- places: {', '.join(f'{p} ({n})' for p, n in places.most_common(6))}",
             f"- eras: {'; '.join(e['place'] + ' ' + e['from'] + ('-' + e['to'] if e['to'] != e['from'] else '') for e in runs)}",
             "- the nine as the moments they were, in the film's order, the ninth first (rank, day, what happened in their words, with whom, where):"]
    lines += [f"  {m['rank']}. {m['date']} {m['kind']}: \"{m['line']}\"" + (f", with {', '.join('@' + p for p in m['people'])}" if m["people"] else "")
              + (f", in {m['place']}" if m["place"] else "") for m in mom]
    lines += ["- what each of the nine shows (rank, kind, what it shows):"]
    lines += [f"  {x['rank']}. {x['kind']} {x['date']}: {x['why']}" for x in nine]
    lines += [f"- what the nine share: {'; '.join(nine_shared)}",
             f"- the tenth: {(stats.get('tenth') or {}).get('likes')} likes, {(stats.get('tenth') or {}).get('gap')} below the ninth; ranked by {stats.get('top_ranked_by')}",
             "", "## you like",
             f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes; the top ten got {int(research['likes']['top10_share'] * 100)}%",
             f"- most liked: {', '.join(a for a, _ in like_accounts.most_common(6))}",
             f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
             f"- palette of the year: {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in year_palette)}",
             f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
             "", "## your style is",
             f"- reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels to measure",
             f"- texture: {'film grain and warm light' if film else 'clean'}",
             f"- the look: {taste['style'] or 'none named, so the three looks are the trio'}",
             f"- music: the look's own recipe" + (f" at {tempo} bpm" if tempo else "") + f"; no {', no '.join(taste['music']['avoid'])}",
             "", "## your voice is",
             f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
             f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
             f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
             f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
             f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
             "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    _env.write_text("taste.draft.md", "\n".join(lines))
    print(f"themes: {dict(own_themes.most_common(4))}; liked themes: {dict(liked_themes.most_common(4))}")
    print(f"year palette: {[s['hex'] for s in year_palette]}; likes palette: {[s['hex'] + ' ' + s['name'] for s in likes_palette]}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s")
    print(f"moments: {len(mom)} in the film's order, the ninth first; eras: {len(runs)}")
    for x in nine:
        print(f"  {x['rank']}. {x['kind']:<5} {x['date']}: {x['why']}")
    print(f"wrote research.json, taste.json (draft) and taste.draft.md in {where}; now write taste.md there")
    return 0


if __name__ == "__main__":
    sys.exit(main())
