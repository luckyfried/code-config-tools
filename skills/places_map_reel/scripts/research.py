#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile. Reads library.json; writes research.json,
a machine draft of taste.json, and taste.draft.md (the numbers under the five headings the agent
turns into taste.md).

USAGE (from the workspace root; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/research.py [--set DIR]

It runs places.py, stats.py, picks.py and palette.py first (the places and the route, counts, each place's
photos, the palettes), then reads:
  places    every place of the year in the order they were visited, with its coordinates, its date span, its
            posts, stories and photos, where the place came from (the geotag, their words, both), the visits,
            the legs between them, the places named once and left off, and the region the map is drawn at (home's
            region, and the far trips)
  palette   the travel palette (photos away from home) against the everyday palette (photos at home) and how
            far apart they read, with the colors of what they like and save beside them
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines, and the words
            they use about each place
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  cadence   posts per month and weekday, streaks and gaps
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  people    who they talk to most
  moments   one per visit of the route: its first post (their line, the people tagged in it, its photograph) and every
            caption of the visit in time order with its post, from picks.py
taste.json also carries the look they named (`style`, none until they name one) and whether the agent may ask them
to choose (`ask`), pacing, register, the grade inputs and music, the brief the film's music is made from (a tempo
only when they name one, genre and instrument words, and what to avoid; never an artist, band or song); the agent edits it freely (and runs places.py with --add, --drop, --home or --rename when the person says where they went) before
storyboards are drafted.
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
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")


def run(script, *args):
    p = subprocess.run([sys.executable, str(S / script), *args], capture_output=True, text=True)
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



def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)









def lean(themes, register, pacing):
    """Which of the kit's three looks their year leans to, and why, for the pick made without asking (taste.json `ask`
    false): film photography reads as the letterbox, fast cuts and heavy emoji as the poster grid, and everything
    else, slow and warm, as the scrapbook."""
    loud = register.get("emoji_per_caption", 0) > 1 or (pacing.get("avg_shot_seconds") or 9) < 1.2
    if themes.get("film photography", 0) >= 3:
        return {"style": "cinematic-letterbox", "why": "they shoot and like film photography: a film's frame and its slow fades"}
    if loud:
        return {"style": "swiss-grid", "why": "fast reels and heavy emoji: a bold poster grid that cuts on the beat"}
    return {"style": "scrapbook", "why": "quiet captions and slow travel: prints taped into a travel journal"}


def moments(picks, pl):
    """The year's moments, one per visit of the route: their line from that visit, who is in it, its photograph."""
    names = {p["id"]: p["name"] for p in pl.get("places", [])}
    return [{"place": m["place"], "name": names.get(m["place"], m["place"]), "n": m["n"], "from": m["from"], "to": m["to"],
             "line": m["line"], "with": m["with"], "post": m["post"], "photo": m["photo"], "captions": m["captions"]}
            for m in (picks or {}).get("moments") or []]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", help="a folder of the person's photographs, one folder per place (picks.py --set)")
    a = ap.parse_args()
    _env.enter_run()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    for s in ("places.py", "stats.py", "picks.py", "palette.py"):
        print(run(s, *(["--set", str(_env.home_path(a.set))] if s == "picks.py" and a.set else [])).strip().splitlines()[-1])
    stats = _env.read_json("stats.json")
    pal = _env.read_json("palette.json") or {}
    pl = _env.read_json("places.json") or {}
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
    mom = moments(_env.read_json("picks.json"), pl)
    td = lean(own_themes + liked_themes, caps, pacing)
    keep = lambda pal_: [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")} for s in (pal_ or [])]
    year_palette, travel, everyday = keep(pal.get("year")), keep(pal.get("travel")), keep(pal.get("everyday"))
    places = pl.get("places", [])
    far = [p for p in places if p["far"]]
    legs = pl.get("legs", [])
    place_rows = [{"id": p["id"], "name": p["name"], "country": p["country"], "lat": p["lat"], "lon": p["lon"], "home": p["home"],
                   "far": p["far"], "first": p["first"], "last": p["last"], "visits": p["visits"], "posts": p["posts"],
                   "stories": p["stories"], "photos": len(p["photos"]), "reels": len(p["clips"]),
                   "source": p["source"], "words": p["words"]} for p in places]
    research = {
        "handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": stats.get("counts"),
        "places": place_rows, "count": len(places), "route": pl.get("route"), "legs": legs,
        "home": pl.get("home"), "far": [p["id"] for p in far], "mentioned": pl.get("mentioned"), "unplaced": pl.get("unplaced"),
        "palette": {"year": year_palette, "travel": travel, "everyday": everyday, "apart": pal.get("apart"),
                    "likes": likes_palette, "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "captions": caps,
        "likes": {"accounts": len(like_accounts), "top": [{"account": a, "likes": n} for a, n in like_accounts.most_common(10)],
                  "top10_share": round(top10 / max(1, sum(like_accounts.values())), 2),
                  "saved_top": [{"account": a, "saves": n} for a, n in saved_accounts.most_common(5)],
                  "themes": dict(liked_themes.most_common())},
        "posts_themes": dict(own_themes.most_common()),
        "cadence": cadence(posts + lib["reels"]),
        "reels": pacing,
        "people": stats.get("people", [])[:8],
        "moments": mom,
        "lean": td,
        "assumptions": pl.get("assumptions", []),
    }
    _env.write_json("research.json", research)
    shot = pacing.get("avg_shot_seconds")
    pillars = [t for t, _ in (own_themes + liked_themes).most_common(4)]
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "travel": travel, "everyday": everyday, "apart": pal.get("apart"), "likes": likes_palette,
                    "direction": "travel"},
        # the look the person names ("style", one of look.TRIO or any card in styles/), and whether the agent may ask
        # them to choose from the boards (false: it picks by this taste, from research.json's lean)
        "style": None, "ask": True,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if shot and shot < 1.5 else "calm" if shot and shot > 3 else "measured"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": pillars,
        # the film's length in seconds when they ask for one (20 to 40, made as near as the places make); none runs it at
        # its own pace
        "seconds": None,
        "people": [p["account"] for p in stats.get("people", [])[:5]],
        "places": [{"id": p["id"], "name": p["name"], "words": p["words"][:1]} for p in places],
        "count": len(places),
        "moments": [{k: m[k] for k in ("place", "n", "line", "with", "post")} for m in mom],
        "avoid": ["map tiles or a satellite look"],
        # the music brief, in their words: a tempo only when they name one (else the board's), genre and instrument
        # words the picked style's recipe takes in, and what to keep out; never an artist, band or song
        "music": {"tempo": None, "styles": [], "avoid": ["vocals", "spoken word"]},
    }
    if not Path("taste.json").exists() or "research.py draft" in (_env.read_json("taste.json") or {}).get("written_by", ""):
        _env.write_json("taste.json", taste)
    names = {p["id"]: p["name"] for p in places}
    lines = [f"# taste draft{' for @' + lib['handle'] if lib['handle'] else ''} ({lib['year']})", "",
             "The agent writes taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are",
             f"- {len(places)} places in {lib['year']}, home {names.get(pl.get('home'), '?')}",
             "- the places, in the order visited (first seen, visits, where the place came from, their words):"]
    lines += [f"  {i + 1}. {p['name']}, {p['country']}: {p['first']} to {p['last']}, {p['visits']} visit{'s' if p['visits'] > 1 else ''}"
              f"{', far' if p['far'] else ''}; {p['source']}"
              + (f"; \"{p['words'][0]}\"" if p['words'] else "") for i, p in enumerate(places)]
    lines += [f"- route: {' > '.join(names.get(r, r) for r in pl.get('route', []))}",
              f"- left off the map: {', '.join(m['name'] for m in pl.get('mentioned') or []) or 'nothing'}; {pl.get('unplaced', 0)} rows with no place",
              f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
              "- moments, one per visit (its first post's line, else wordless; every caption of the visit after it, [post]):"]
    lines += [f"  {i + 1}. {m['name']}{' again' if m['n'] > 1 else ''}, {m['from']}: "
              + (f"\"{m['line']}\"" if m["line"] else "wordless")
              + f" [{m['post']}]" + "".join(f" / {c['line']} [{c['post']}]" for c in m["captions"] if c["post"] != m["post"])
              for i, m in enumerate(mom)]
    lines += [
              "", "## you like",
              f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes; the top ten got {int(research['likes']['top10_share'] * 100)}%",
              f"- most liked: {', '.join(a for a, _ in like_accounts.most_common(6))}",
              f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
              f"- travel palette (photos away from home): {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in travel)}",
              f"- everyday palette (photos at home): {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in everyday) or 'no photos at home'}",
              f"- travel against everyday: {pal.get('apart')} apart (above 20 reads as two palettes)",
              f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
              "", "## your style is",
              f"- reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels to measure",
              f"- the look their year leans to: {td['style']} ({td['why']})",
              f"- pillars: {', '.join(pillars)}",
              "", "## your voice is",
              f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
              f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
              f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
              f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
              f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
              "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    _env.write_text("taste.draft.md", "\n".join(lines))
    print(f"places: {len(places)} ({', '.join(p['name'] for p in places)}); route {len(pl.get('route', []))} stops")
    print(f"themes: {dict(own_themes.most_common(4))}; liked themes: {dict(liked_themes.most_common(4))}")
    print(f"travel palette: {[s['hex'] for s in travel]}; everyday: {[s['hex'] for s in everyday]}; apart {pal.get('apart')}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s; leans to {td['style']}")
    print(f"moments: {sum(1 for m in mom if m['line'])} of {len(mom)} visits with a line of theirs")
    print("wrote research.json, taste.json (draft) and taste.draft.md; now write taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
