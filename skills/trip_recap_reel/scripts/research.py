#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile. Reads library.json; writes research.json,
a machine draft of taste.json, and taste.draft.md (the numbers under the five headings the agent
turns into taste.md).

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/research.py [--place "lisbon"] [--from 2026-10-03 --to 2026-10-08] [--album "..."] [--folder DIR]

Pass what the person named; it goes to trip.py unchanged, and their words win over anything inferred. It runs
trip.py, picks.py and palette.py first (which trip, its days, places, people and clips; the photos; the trip and
everyday palettes), then reads:
  trip      the dates, the days and what each one holds, the places in route order, who was there
  travel    how the trip looked and sounded against every other week: palette, brightness and saturation, how
            long their captions run, how often they posted, how fast their travel reels cut against their others
  palette   the trip's colors, their everyday colors, and the colors of what they like and save
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines from the trip
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  music     the music brief for this film, taste.json `music`: a mood word read from the trip's themes and the pace of
            their reels, and what to avoid; the bed's recipe and tempo are the winning look's, and `styles` stays empty
            until the person names a sound; never an artist, a band or a song (a track named on a travel post stays in
            research.json)
  moments   what happened at each place of each day, from the captions alone: where they were, who is in the line,
            and the line itself (their strongest caption there); nothing in it is counted
taste.json also carries the pacing, the register and the palette inputs; the agent edits it
freely before storyboards are drafted.
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
from trip import mentions  # noqa: E402

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
# pillars that ask for the calm bed, when their reels are not quick and their captions carry no emoji
QUIET = {"slow living", "food", "coffee", "light"}
# what no track for this film carries
NO_MUSIC = ["vocals", "spoken word", "harsh distortion"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
def caption_read(rows):
    caps = [r.get("caption") or "" for r in rows if (r.get("caption") or "").strip()]
    if not caps:
        return {"captions": 0}
    words = [len(c.split()) for c in caps]
    # a person who writes in lowercase writes whole captions without a capital; sentence case is mostly lowercase letters too
    lower = sum(1 for c in caps if not any(ch.isupper() for ch in re.sub(r"[#@][\w.]+", "", c))) / len(caps)
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




def run(script, args=()):
    p = subprocess.run([sys.executable, str(S / script), *args], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{script} failed:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def day_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()


WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def date_label(iso):
    d = dt.date.fromisoformat(iso)
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}"


def clean(cap):
    return re.sub(r"\s+", " ", EMOJI.sub("", re.sub(r"[#@][\w.]+", "", cap or ""))).strip(" ,.-")


def best_of(captions):
    """A day's strongest caption, as they posted it: four to twelve words first, then the longest."""
    said = [c for c in captions if clean(c)]
    return max(said, key=lambda c: (4 <= len(clean(c).split()) <= 12, len(clean(c))), default="")


def line_of(captions):
    """A day's line: its strongest caption with the handles and tags taken out."""
    return clean(best_of(captions))


def moments_of(trip):
    """The trip's moments, one for each place of each day that has a line: the date, the place, who is in the line (the
    handles they tagged in it) and the line itself. Built from their captions, places and dates alone; nothing is counted."""
    out = []
    for d in trip["days"]:
        said = {}
        for it in d.get("items") or []:
            said.setdefault(it.get("place") or (d["places"] or [""])[0], []).append(it.get("caption") or "")
        for place, captions in said.items():
            best = best_of(captions)
            if best:
                out.append({"date": d["date"], "place": place, "with": sorted(set(mentions(best))), "line": clean(best)})
    return out


def per_day(rows, lo, hi):
    days = {day_of(r["ts"]) for r in rows if r.get("ts")}
    if not days:
        return 0
    span = (dt.date.fromisoformat(max(days)) - dt.date.fromisoformat(min(days))).days + 1
    return round(len([r for r in rows if r.get("ts")]) / max(1, span), 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--place")
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--album")
    ap.add_argument("--folder")
    a = ap.parse_args()
    _env.enter_run()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    named = []
    for flag, v in (("--place", a.place), ("--from", a.date_from), ("--to", a.date_to), ("--album", a.album), ("--folder", a.folder)):
        if v:
            named += [flag, v]
    print(run("trip.py", named).strip().splitlines()[0])
    for s in ("picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    trip = _env.read_json("trip.json")
    pal = _env.read_json("palette.json") or {}
    lo, hi = trip["from"], trip["to"]
    spans = [(lo, hi)] + [(o["from"], o["to"]) for o in trip.get("others") or []]
    def on_trip(r):
        return r.get("ts") and lo <= day_of(r["ts"]) <= hi
    def away(r):
        return r.get("ts") and any(x <= day_of(r["ts"]) <= y for x, y in spans)
    posts, reels, fb = lib.get("posts") or [], lib.get("reels") or [], lib.get("facebook") or []
    captioned = posts + reels + fb
    trip_rows = [r for r in captioned if on_trip(r)]
    every_rows = [r for r in captioned if not away(r)]
    caps = caption_read(captioned)
    trip_caps, every_caps = caption_read(trip_rows), caption_read(every_rows)
    like_accounts = collections.Counter(r.get("account") for r in lib.get("likes") or [] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved") or [] if r.get("account"))
    follow = [r.get("account") for r in lib.get("following") or [] if r.get("account")]
    liked_text = list(like_accounts.elements()) + list(saved_accounts.elements()) + follow + \
        [r.get("caption") or "" for r in (lib.get("likes") or []) + (lib.get("saved") or [])]
    liked_media = [m for r in (lib.get("likes") or []) + (lib.get("saved") or []) for m in (r.get("media") or []) if Path(m).exists()]
    likes_palette = image_palette(liked_media) if len(liked_media) >= 8 else lexicon_palette(liked_text)
    likes_from = "the photos they liked and saved" if len(liked_media) >= 8 else \
        "the color words in the names and captions of the accounts they like, save and follow"
    own_themes = theme_counts([r.get("caption") or "" for r in captioned])
    trip_themes = theme_counts([r.get("caption") or "" for r in trip_rows])
    liked_themes = theme_counts(list(like_accounts.elements()) + list(saved_accounts.elements()) + follow)
    top10 = sum(n for _, n in like_accounts.most_common(10))
    travel_reels = [r for r in reels if away(r)]
    trip_pacing = reel_pacing([r for r in reels if on_trip(r)] or travel_reels)
    every_pacing = reel_pacing([r for r in reels if not away(r)])
    shift = pal.get("shift") or {}
    style = {
        "palette_trip": [c["name"] for c in pal.get("trip") or []],
        "palette_everyday": [c["name"] for c in pal.get("everyday") or []],
        "trip_only_colors": shift.get("trip_only") or [],
        "brightness": {"trip": (shift.get("bright") or [None])[0], "everyday": (shift.get("bright") or [None, None])[1]},
        "saturation": {"trip": (shift.get("saturation") or [None])[0], "everyday": (shift.get("saturation") or [None, None])[1]},
        "caption_words": {"trip": trip_caps.get("avg_words"), "everyday": every_caps.get("avg_words")},
        "posts_per_day": {"trip": per_day([r for r in posts + reels + (lib.get("stories") or []) if on_trip(r)], lo, hi),
                          "everyday": per_day([r for r in posts + reels if not away(r)], None, None)},
        "reel_shot_seconds": {"trip": trip_pacing.get("avg_shot_seconds"), "everyday": every_pacing.get("avg_shot_seconds")},
        "themes": {"trip": dict(trip_themes.most_common(4)), "everyday": dict(own_themes.most_common(4))},
    }
    days = [{"date": d["date"], "label": date_label(d["date"]), "places": d["places"], "items": d["n"], "line": line_of(d.get("captions") or [])}
            for d in trip["days"]]
    moments = moments_of(trip)
    heard = trip.get("music") or {}
    music_note = ({"seen": heard.get("seen"), "direction": "the tracks on their travel posts"} if heard.get("seen") else
                  {"seen": [], "direction": "not in the data: the bed follows the pace of their travel reels"})
    trip_palette = [{"hex": c["hex"], "name": c.get("name"), "share": c.get("share"), "photo": c.get("photo")} for c in pal.get("trip") or []]
    every_palette = [{"hex": c["hex"], "name": c.get("name"), "share": c.get("share")} for c in pal.get("everyday") or []]
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    places = [p["name"] for p in trip["places"]]
    people = [p["handle"] for p in trip.get("people") or []]
    research = {
        "handle": lib["handle"], "source": lib["source"], "doors": lib.get("doors", {}),
        "trip": {k: trip.get(k) for k in ("name", "from", "to", "days_count", "chosen_by", "found_by", "items", "geotagged")},
        "places": trip["places"], "route": trip.get("route"), "people": trip.get("people"), "days": days,
        "clips": [{k: c.get(k) for k in ("file", "day", "place", "seconds", "caption")} for c in trip.get("clips") or []],
        "others": trip.get("others"), "travel_vs_everyday": style,
        "palette": {"trip": trip_palette, "everyday": every_palette, "likes": likes_palette, "likes_from": likes_from, "roles": pal.get("roles")},
        "captions": caps, "captions_trip": trip_caps, "captions_everyday": every_caps,
        "likes": {"accounts": len(like_accounts), "top": [{"account": x, "likes": n} for x, n in like_accounts.most_common(10)],
                  "top10_share": round(top10 / max(1, sum(like_accounts.values())), 2),
                  "saved_top": [{"account": x, "saves": n} for x, n in saved_accounts.most_common(5)],
                  "themes": dict(liked_themes.most_common())},
        "reels_trip": trip_pacing, "reels_everyday": every_pacing, "music": music_note, "moments": moments,
        "assumptions": trip.get("assumptions"),
    }
    _env.write_json("research.json", research)
    shot = trip_pacing.get("avg_shot_seconds") or every_pacing.get("avg_shot_seconds")
    pillars = [t for t, _ in (trip_themes + own_themes + liked_themes).most_common(4)]
    # the music brief: a mood word (film texture, a quiet pillar with unhurried reels, else lively); the recipe and the
    # tempo are the winning look's. A track named on a travel post stays in research.json: a name is not a taste.
    lively = (shot or 9) < 1.5 or (caps.get("emoji_per_caption") or 0) >= 1
    mood = "film" if film else "calm" if QUIET & set(pillars) and not lively else "drive"
    brief = {"mood": mood, "tempo": None, "styles": [], "avoid": NO_MUSIC}
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"],
        "trip": {"name": trip["name"], "from": lo, "to": hi, "days": len(days)},
        "palette": {"trip": trip_palette, "everyday": every_palette, "likes": likes_palette,
                    "direction": "the trip's own colors" + (f", led by {', '.join(style['trip_only_colors'][:2])}" if style["trip_only_colors"] else "")},
        "pacing": {"reel_seconds": trip_pacing.get("avg_seconds"), "shot_seconds": shot},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": (trip_caps.get("top_hashtags") or caps.get("top_hashtags") or [])[:3],
                     "samples": (trip_caps.get("samples") or caps.get("samples") or [])[:4]},
        "pillars": pillars,
        "people": people[:5],
        "places": places,
        "days": [{"date": x["date"], "label": x["label"], "places": x["places"], "line": x["line"]} for x in days],
        "moments": moments,
        "avoid": ["digital sharpness and gloss", "neon", "stock travel footage", "a map that is not their route"] if film else
                 ["muddy grading", "stock travel footage", "a map that is not their route"],
        "music": brief,
    }
    old = _env.read_json("taste.json") or {}
    stale = (old.get("trip") or {}).get("from") != lo or (old.get("trip") or {}).get("to") != hi
    if not old or stale or "research.py draft" in old.get("written_by", ""):
        _env.write_json("taste.json", taste)
    def pair(k, unit=""):
        v = style[k]
        return f"{v['trip']}{unit} on the trip, " + (f"{v['everyday']}{unit} on other days" if v["everyday"] is not None else "no posts from other days")
    lines = [f"# taste draft for @{lib['handle']}: {trip['name']}, {lo} to {hi}", "",
             "The agent writes taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are",
             f"- the trip: {trip['name']}, {len(days)} days ({trip['chosen_by']}; found by {trip['found_by']})",
             f"- the route: {' -> '.join(r['place'] for r in trip.get('route') or []) or ', '.join(places)}",
             f"- with: {', '.join('@' + h for h in people) or 'nobody tagged'}",
             "- what happened, day by day (their line, who is in it):"]
    lines += [f"  {date_label(m['date'])}: {m['place'] or '-'}; \"{m['line']}\""
              + (f" with {', '.join('@' + h for h in m['with'])}" if m["with"] else "") for m in moments]
    lines += [f"- their clips from the trip: {len(research['clips'])} ("
              + ", ".join(f"{c['day']} {c['place']} {c['seconds']} s" for c in research["clips"]) + ")",
              f"- other trips in the data: {'; '.join(o['from'] + ' to ' + o['to'] for o in trip.get('others') or []) or 'none'}",
              "", "## you like",
              f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes; the top ten got {int(research['likes']['top10_share'] * 100)}%",
              f"- most liked: {', '.join(x for x, _ in like_accounts.most_common(6))}",
              f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
              f"- palette of their likes ({likes_from}): {', '.join(c['name'] + ' ' + c['hex'] for c in likes_palette)}",
              "", "## your style is",
              f"- the trip's palette: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in trip_palette)}",
              f"- their everyday palette: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in every_palette)}",
              f"- only on the trip: {', '.join(style['trip_only_colors']) or 'no new colors'}",
              f"- brightness {pair('brightness')}; saturation {pair('saturation')}",
              f"- posts a day: {pair('posts_per_day')}; a reel cut every {pair('reel_shot_seconds', ' s')}",
              f"- themes on the trip: {style['themes']['trip']}; on other days: {style['themes']['everyday']}",
              f"- texture: {'film photography' + (' and warm light' if warm_light else '') if film else 'clean'}",
              f"- music brief: {mood}; the look's own recipe and tempo; no {', no '.join(NO_MUSIC)}"
              + (f" (their travel posts carry {', '.join(music_note['seen'])}; a name never enters the brief)" if music_note["seen"] else ""),
              "", "## your voice is",
              f"- {caps.get('avg_words')} words a caption ({pair('caption_words')}), {int(caps.get('lowercase_share', 0) * 100)}% of captions all lowercase, "
              f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
              f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
              f"- hashtags on the trip: {', '.join(trip_caps.get('top_hashtags', []))}",
              f"- lines from the trip: {' / '.join(trip_caps.get('samples', [])[:4])}",
              "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    _env.write_text("taste.draft.md", "\n".join(lines))
    print(f"trip: {trip['name']} {lo} to {hi}, {len(days)} days; places {places}; people {people}")
    print(f"travel vs everyday: palette {style['palette_trip'][:3]} vs {style['palette_everyday'][:3]}; "
          f"brightness {style['brightness']}; captions {style['caption_words']}; reel cuts {style['reel_shot_seconds']}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print(f"music brief: {mood}; the look's own recipe and tempo; no {', no '.join(NO_MUSIC)}")
    print("wrote research.json, taste.json (draft) and taste.draft.md; now write taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
