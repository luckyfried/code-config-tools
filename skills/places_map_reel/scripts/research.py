#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile. Reads build/library.json; writes build/research.json,
a machine draft of build/taste.json, and build/taste.draft.md (the numbers under the five headings the agent
turns into build/taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py

It runs places.py, stats.py, picks.py and palette.py first (the places and the route, counts, each place's
photos, the palettes), then reads:
  places    every place of the year in the order they were visited, with its coordinates, its date span, its
            posts, stories and photos, where the place came from (the geotag, their words, both), the visits,
            the legs between them in kilometers, the total, the farthest place and the longest leg, the places
            named once and left off, and the region the map is drawn at (home's region, and the far trips)
  palette   the travel palette (photos away from home) against the everyday palette (photos at home) and how
            far apart they read, with the colors of what they like and save beside them
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines, and the words
            they use about each place
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  cadence   posts per month and weekday, streaks and gaps
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  people    who they talk to most
  moments   the busiest and quietest month, the far trip, the longest stay, the places they went back to
taste.json also carries the type direction, pacing, register, texture and the grade inputs; the agent edits it
freely (and runs places.py with --add, --drop, --home or --rename when the person says where they went) before
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



def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)









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


def moments(stats, pl):
    out = []
    b, q = stats.get("busiest") or {}, stats.get("quietest") or {}
    if b:
        out.append({"kind": "busiest month", "month": b.get("name"), "posts": b.get("posts"), "total": b.get("total")})
    if q:
        out.append({"kind": "quietest month", "month": q.get("name"), "posts": q.get("posts")})
    places = {p["id"]: p for p in pl.get("places", [])}
    away = [p for p in places.values() if not p["home"]]
    if away:
        far = max(away, key=lambda p: p["km_from_home"])
        out.append({"kind": "the farthest place", "place": far["name"], "km": far["km_from_home"], "from": far["first"], "to": far["last"]})
    vs = [v for v in pl.get("visits", []) if v.get("from") and places.get(v["place"]) and not places[v["place"]]["home"]]
    if vs:
        long = max(vs, key=lambda v: (dt.date.fromisoformat(v["to"]) - dt.date.fromisoformat(v["from"])).days)
        out.append({"kind": "the longest stay", "place": places[long["place"]]["name"], "from": long["from"], "to": long["to"],
                    "days": (dt.date.fromisoformat(long["to"]) - dt.date.fromisoformat(long["from"])).days + 1})
    back = [p["name"] for p in away if p["visits"] > 1]
    if back:
        out.append({"kind": "went back to", "places": back})
    if pl.get("legs"):
        lg = max(pl["legs"], key=lambda l: l["km"])
        out.append({"kind": "the longest leg", "from": places[lg["from"]]["name"], "to": places[lg["to"]]["name"], "km": lg["km"]})
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    for s in ("places.py", "stats.py", "picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    stats = _env.read_json("build/stats.json")
    pal = _env.read_json("build/palette.json") or {}
    pl = _env.read_json("build/places.json") or {}
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
    mom = moments(stats, pl)
    td = type_direction(own_themes + liked_themes, caps, pacing)
    keep = lambda pal_: [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")} for s in (pal_ or [])]
    year_palette, travel, everyday = keep(pal.get("year")), keep(pal.get("travel")), keep(pal.get("everyday"))
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    places = pl.get("places", [])
    far = [p for p in places if p["far"]]
    legs = pl.get("legs", [])
    place_rows = [{"id": p["id"], "name": p["name"], "country": p["country"], "lat": p["lat"], "lon": p["lon"], "home": p["home"],
                   "far": p["far"], "first": p["first"], "last": p["last"], "visits": p["visits"], "posts": p["posts"],
                   "stories": p["stories"], "photos": len(p["photos"]), "reels": len(p["clips"]), "km_from_home": p["km_from_home"],
                   "source": p["source"], "words": p["words"]} for p in places]
    research = {
        "handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": stats.get("counts"),
        "places": place_rows, "count": len(places), "route": pl.get("route"), "legs": legs, "total_km": pl.get("total_km"),
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
        "type": td,
        "assumptions": pl.get("assumptions", []),
    }
    _env.write_json("build/research.json", research)
    shot = pacing.get("avg_shot_seconds")
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "travel": travel, "everyday": everyday, "apart": pal.get("apart"), "likes": likes_palette,
                    "direction": "travel"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": [t for t, _ in (own_themes + liked_themes).most_common(4)],
        "people": [p["account"] for p in stats.get("people", [])[:5]],
        "places": [{"id": p["id"], "name": p["name"], "words": p["words"][:1]} for p in places],
        "count": len(places), "total_km": pl.get("total_km"),
        "moments": mom,
        "texture": {"grain": 0.16 if film else 0, "vignette": 0.32 if film else 0.0, "leaks": bool(film and warm_light)},
        "avoid": ["cold blue grading", "neon", "stock-photo gloss", "map tiles or a satellite look"] if film else
                 ["muddy grading", "map tiles or a satellite look"],
    }
    if not Path("build/taste.json").exists() or "research.py draft" in (_env.read_json("build/taste.json") or {}).get("written_by", ""):
        _env.write_json("build/taste.json", taste)
    names = {p["id"]: p["name"] for p in places}
    lines = [f"# taste draft for @{lib['handle']} ({lib['year']})", "",
             "The agent writes build/taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are",
             f"- {len(places)} places in {lib['year']}, home {names.get(pl.get('home'), '?')}; {pl.get('total_km', 0):,} km along the route",
             "- the places, in the order visited (first seen, visits, posts and stories, where the place came from, their words):"]
    lines += [f"  {i + 1}. {p['name']}, {p['country']}: {p['first']} to {p['last']}, {p['visits']} visit{'s' if p['visits'] > 1 else ''}, "
              f"{p['posts']} posts and {p['stories']} stories, {p['km_from_home']:,} km from home{', far' if p['far'] else ''}; {p['source']}"
              + (f"; \"{p['words'][0]}\"" if p['words'] else "") for i, p in enumerate(places)]
    lines += [f"- route: {' > '.join(names.get(r, r) for r in pl.get('route', []))}",
              f"- legs: {'; '.join(names[l['from']] + ' to ' + names[l['to']] + ' ' + format(l['km'], ',') + ' km' for l in legs)}",
              f"- left off the map: {', '.join(m['name'] for m in pl.get('mentioned') or []) or 'nothing'}; {pl.get('unplaced', 0)} rows with no place",
              f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
              f"- moments: {'; '.join(m['kind'] + ': ' + ', '.join(str(v) for k, v in m.items() if k != 'kind') for m in mom)}",
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
              f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
              "", "## your voice is",
              f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
              f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
              f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
              f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
              f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
              "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    Path("build/taste.draft.md").write_text("\n".join(lines))
    print(f"places: {len(places)} ({', '.join(p['name'] for p in places)}); route {len(pl.get('route', []))} stops, {pl.get('total_km', 0):,} km")
    print(f"themes: {dict(own_themes.most_common(4))}; liked themes: {dict(liked_themes.most_common(4))}")
    print(f"travel palette: {[s['hex'] for s in travel]}; everyday: {[s['hex'] for s in everyday]}; apart {pal.get('apart')}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s; type lead {td['lead']}")
    print(f"moments: {[m['kind'] for m in mom]}")
    print("wrote build/research.json, build/taste.json (draft) and build/taste.draft.md; now write build/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
