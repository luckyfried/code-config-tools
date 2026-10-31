#!/usr/bin/env python3
"""Movement 1: the reading behind the taste profile. Reads R/library.json; writes R/research.json,
a machine draft of R/taste.json, and R/taste.draft.md (the draft under the five headings the agent
turns into R/taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py [--top 5] [--people a,b,c]

It runs people.py (with --top and --people passed on), picks.py and palette.py first (the people and their order,
each person's best photo and the group photos, the year's palette), then reads:
  palette   the year's colors versus the colors of what they like and save (from the liked media when the
            library has it, else from the color words in the names and captions of the accounts they like,
            save and follow)
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  cadence   posts per month and weekday, streaks and gaps
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  places    places from captions, albums and check-ins, and the trips by month
  people    for each person: why they are in the film (their signals in plain words, nothing counted), their stretch
            of the year, their moment, their best line and where it came from, their voice, the exchanges between
            them and the person, and the colors of their best photo; who came next
  moments   each person's moment: the photograph of the two of them, the month it was posted and the place its caption
            names (else the one the person named most that month, when more than home), the person's caption of it and
            the line the other wrote; and the year as stretches, each led by one person
taste.json also carries the type direction, pacing, register, texture, the people with their lines (the agent may
swap a line for one of the person's other lines in people.json), the palette, and music: the brief the film's music is
made from (a mood, calm, drive or film, which is how the person describes the feel; `styles`, genre and instrument
words that steer the picked look's recipe and stay empty unless the person names some; an optional `tempo`; and what
to avoid; never an artist, band or song); the agent edits it freely before storyboards are drafted.
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
PLACES = ["lisbon", "porto", "oaxaca", "sicily", "palermo", "marrakech", "paris", "rome", "london", "tokyo", "mexico city",
          "new york", "berlin", "barcelona", "madrid", "naples", "athens", "istanbul", "kyoto", "seoul", "bali", "cdmx",
          "los angeles", "san francisco", "chicago", "amsterdam", "copenhagen", "vienna", "prague", "budapest", "home"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
FILM = {"film photography"}
QUIET = {"slow living", "food", "coffee", "light"}  # pillars a calm bed carries, when their reels do not cut fast


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


def place_in(place_by_month, m):
    """The place the person named most in month `m`, when they named it more than home; None otherwise."""
    c = (place_by_month.get(m) if m else None) or {}
    away = [(n, pl) for pl, n in c.items() if pl != "home"]
    n, top = max(away) if away else (0, None)
    return top if n > c.get("home", 0) else None


def named_place(text):
    """The first place a caption names, other than home; None when it names none."""
    text = (text or "").lower()
    return next((pl for pl in PLACES if pl != "home" and re.search(rf"\b{re.escape(pl)}\b", text)), None)


def moments(ppl, picks):
    """Each person's moment: the photograph of the two of them picks.py chose, the month it was posted and its place (the
    one its caption names, none when it names none), the person's caption of it, and the line the other wrote (the one
    picks.py carries with that photograph: left on it when one of their lines was)."""
    photo = {x["handle"]: x for x in picks.get("people", [])}
    out = []
    for p in ppl.get("people", []):
        ph = photo.get(p["handle"]) or {}
        m = month(ph["ts"]) if ph.get("ts") else None
        out.append({"who": p["handle"], "when": MONTHS[m - 1].lower() if m else (p.get("stretch") or {}).get("label"),
                    "where": named_place(ph.get("caption")), "what": ph.get("caption"),
                    "they_said": (ph.get("line") or p.get("line") or {}).get("text")})
    return out


def stretches(ppl, place_by_month):
    """The year in stretches: who leads each run of months, and the place the person named most in its first month."""
    eras, cur = [], None
    for e in ppl.get("eras", []):
        if cur and cur["owner"] == e["owner"]:
            cur["to"] = e["month"]
        else:
            cur = {"owner": e["owner"], "from": e["month"], "to": e["month"]}
            eras.append(cur)
    for e in eras:
        e["place"] = place_in(place_by_month, MONTHS.index(e["from"].capitalize()) + 1)
    return eras


def where_when(m):
    """A moment's place and month as one phrase: "sicily, july", or the month alone where no place was named."""
    return ", ".join(x for x in (m.get("where"), m.get("when")) if x)


def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


SIGNALS = (("own_tags", "in your photographs"), ("tags_of_owner", "you in theirs"), ("their_comments", "their comments under yours"),
           ("owner_comments", "yours under theirs"), ("story_tags", "in your stories"))


def people_read(ppl, picks, moments):
    """Each person in plain words: why they are in the film, their stretch, their moment, their line, their voice, the
    colors of their photo."""
    photo = {x["handle"]: x for x in picks.get("people", [])}
    mom = {m["who"]: m for m in moments}
    out = []
    for p in ppl.get("people", []):
        s = p.get("signals") or {}
        why = [what for key, what in SIGNALS if s.get(key)]
        m = mom.get(p["handle"]) or {}
        ph = photo.get(p["handle"]) or {}
        colors = []
        for c in sorted(ph.get("colors", []), key=lambda c: -c["share"]):
            nm = color_name(c["rgb"])
            if nm not in colors:
                colors.append(nm)
        line = ph.get("line") or p.get("line") or {}
        out.append({"rank": p["rank"], "handle": p["handle"], "why": ", ".join(why), "stretch": p["stretch"]["label"],
                    "when": m.get("when"), "where": m.get("where"), "what": m.get("what"), "line": line.get("text"), "line_from": line.get("from"),
                    "other_lines": [x["text"] for x in [p.get("line")] + p.get("lines", []) if x and x["text"] != line.get("text")][:3],
                    "voice": p["voice"].get("describe"),
                    "exchanges": p.get("exchanges", []), "photos_together": p.get("photos_together"),
                    "photo_colors": colors[:3], "photo": ph.get("photo")})
    return out


def type_direction(themes, register, pacing):
    film = themes.get("film photography", 0)
    loud = register.get("emoji_per_caption", 0) > 1 or (pacing.get("avg_shot_seconds") or 9) < 1.2
    if loud:
        return {"lead": "kinetic", "why": "heavy emoji and fast reels read as loud"}
    if film and themes.get("travel", 0) >= film:
        return {"lead": "documentary", "why": "travel carried on film reads as a record of places"}
    return {"lead": "editorial", "why": "quiet captions and film photography read as calm"}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=5, help="how many people when the person named none")
    ap.add_argument("--people", help="the person's own list, comma separated, in their order")
    a = ap.parse_args()
    _env.enter_run()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    pass_on = ["--top", str(a.top)] + (["--people", a.people] if a.people else [])
    for s, args in (("people.py", pass_on), ("picks.py", []), ("palette.py", [])):
        print(run(s, *args).strip().splitlines()[-1])
    ppl = _env.read_json("people.json")
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
    picks = _env.read_json("picks.json") or {}
    mom = moments(ppl, picks)
    eras = stretches(ppl, place_by_month)
    people = people_read(ppl, picks, mom)
    # the film runs in taste.json's order: the person's own list as they gave it, else their moments in the order the
    # year had them; the agent sets the order the story runs in
    when = {x["handle"]: x.get("ts") or 0 for x in picks.get("people", [])}
    order = people if ppl.get("named") else sorted(people, key=lambda x: when.get(x["handle"], 0))
    td = type_direction(own_themes + liked_themes, caps, pacing)
    year_palette = [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")}
                    for s in (pal.get("year") or [])]
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    research = {
        "handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": ppl.get("counts"),
        "palette": {"year": year_palette, "likes": likes_palette, "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "captions": caps,
        "likes": {"accounts": len(like_accounts), "top": [{"account": a, "likes": n} for a, n in like_accounts.most_common(10)],
                  "top10_share": round(top10 / max(1, sum(like_accounts.values())), 2),
                  "saved_top": [{"account": a, "saves": n} for a, n in saved_accounts.most_common(5)],
                  "themes": dict(liked_themes.most_common())},
        "posts_themes": dict(own_themes.most_common()),
        "cadence": cadence(posts + lib["reels"]),
        "reels": pacing,
        "people": people, "ranked_by": ppl.get("ranked_by"), "next": ppl.get("next"),
        "places": [{"place": p, "posts": n} for p, n in places.most_common(8)],
        "moments": mom, "eras": eras,
        "wall": [{"date": dt.datetime.fromtimestamp(t["ts"], dt.timezone.utc).date().isoformat(), "people": t["people"],
                  "reel": bool(t.get("video")), "caption": t.get("caption")} for t in picks.get("wall", [])],
        "type": td,
    }
    _env.write_json("research.json", research)
    shot = pacing.get("avg_shot_seconds")
    pillars = [t for t, _ in (own_themes + liked_themes).most_common(4)]
    # a film of the people who made their year: the kit's drive bed unless their texture or their quiet says otherwise
    mood = "drive" if td["lead"] == "kinetic" else "film" if film else "calm" if QUIET & set(pillars) else "drive"
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "likes": likes_palette,
                    "direction": "toward their likes" if likes_palette else "their year"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": pillars,
        "people": [{"rank": x["rank"], "handle": x["handle"], "stretch": x["stretch"], "when": x["when"], "where": x["where"], "what": x["what"],
                    "line": x["line"], "line_from": x["line_from"], "voice": x["voice"], "why": x["why"]} for x in order],
        "eras": eras,
        "places": [p for p, _ in places.most_common(5) if p != "home"],
        "moments": mom,
        "avoid": ["cold blue grading", "neon", "stock-photo gloss"] if film else ["muddy grading"],
        "music": {"mood": mood, "styles": [],
                  "avoid": ["vocals", "spoken word", "harsh distortion"]},
    }
    if not Path("taste.json").exists() or "research.py draft" in (_env.read_json("taste.json") or {}).get("written_by", ""):
        _env.write_json("taste.json", taste)
    lines = [f"# taste draft for {'@' + lib['handle'] if lib['handle'] else 'the person'} ({lib['year']})", "",
             "The agent writes R/taste.md from this: one page, five paragraphs that start with the five headings below.", "",
             "## you are", f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
             f"- places: {', '.join(f'{p} ({n})' for p, n in places.most_common(6))}",
             f"- moments: {'; '.join('@' + m['who'] + ' ' + where_when(m) + ': ' + repr(m['what'] or '') for m in mom)}",
             f"- your people, found from {ppl.get('ranked_by')}:"]
    for x in people:
        lines.append(f"  {x['rank']}. @{x['handle']}: {x['why']}; {where_when(x)}: \"{x['what']}\"; owns {x['stretch'] or 'no single stretch'}; "
                     f"voice: {x['voice']}; best line ({x['line_from']}): \"{x['line']}\"")
        for e in x["exchanges"][:2]:
            lines.append(f"     they: \"{e['they']}\" / you: \"{e['own']}\"")
    lines += [f"- the year in stretches: {'; '.join('@' + e['owner'] + ' ' + e['from'] + ('-' + e['to'] if e['to'] != e['from'] else '') + (' (' + e['place'] + ')' if e.get('place') else '') for e in eras)}",
              f"- next after them: {', '.join('@' + x['handle'] for x in ppl.get('next', []))}",
              f"- the wall's group photos: {'; '.join(w['date'] + ' ' + ', '.join('@' + h for h in w['people']) for w in research['wall'])}",
              "", "## you like",
             f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes; the top ten got {int(research['likes']['top10_share'] * 100)}%",
             f"- most liked: {', '.join(a for a, _ in like_accounts.most_common(6))}",
             f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
             f"- palette of the year: {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in year_palette)}",
             f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
             "", "## your style is",
             f"- reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels to measure",
             f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
             f"- music: {mood}; the picked look's own recipe makes the bed"
             + (f", steered by {', '.join(taste['music']['styles'])}" if taste["music"]["styles"] else "")
             + f"; no {', no '.join(taste['music']['avoid'])}",
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
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s; type lead {td['lead']}")
    print(f"moments: {'; '.join('@' + m['who'] + ' ' + where_when(m) for m in mom)}; stretches: {'; '.join(e['owner'] + ' ' + e['from'] for e in eras)}")
    for x in people:
        print(f"  {x['rank']}. @{x['handle']}: {x['why']}; line ({x['line_from']}): {x['line']}")
    print("wrote R/research.json, R/taste.json (draft) and R/taste.draft.md; now write R/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
