#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile. Reads library.json; writes research.json,
a machine draft of taste.json, and taste.draft.md (the numbers under the six headings the agent
turns into taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py

It runs stats.py, picks.py and palette.py first (counts and response, the subject's assets and the photos, the two
palettes), then reads:
  response  which posts drew the most comments and saves, how many times their usual response each drew, and what
            those posts share that the rest do not (hook style, subject, place, kind, whether they name the subject)
  hooks     the openers of those posts ranked by response, and the hook styles (question, confession, list,
            statement) ranked by the mean response of the top posts in each, for the written brief; the film never
            reads them
  moments   what they did: every photograph of theirs they wrote words with, by its path, in date order, with the people
            tagged, the place named, whether it is of the making, and its line drafted as their whole caption; the agent cuts
            each line in taste.json to what the beat says, and the line is what the film says on that photograph; taste.md's "you are" tells them as the year's story
  subject   the subject, what it is, its handle, its facts, whether it is a launch (and then the date as they wrote it
            and as a day, the days to go), the assets (a folder, a link, or only their posts), and the posts already
            about it
  palette   their colors against the subject's and where the two meet (palette.py), and the colors of what they like
  captions  length, case, emoji, punctuation, hashtags, how they open and close, sample lines
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  cadence   posts per month and weekday, streaks and gaps
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  people    who they talk to most; places from captions, albums and check-ins
taste.json also carries the plan (`plan`: the six answers the inspect step gives before anything is planned, what it
is, who it is for, what sets it apart, the best true claim, the hook line and the share caption, then the angle, the
punchline the closer carries when it is not a launch, and the tone, one of drive.TONES; drafted here from the
subject's own facts, the agent writes every answer in the subject's or the person's own words and never invents a
number, a quote or a testimonial), the subject as given with `lines`, the line each of its stills may carry (its own
words, else its facts in turn; the agent cuts or clears any), the pacing, register, texture and the grade inputs, `style` (a style
the person named, else null: the three looks are then the kit's own three), `ask` (true: the agent shows the three
looks and asks which; false where it cannot ask, and it picks by this taste), and music, the brief the film's music
is made from (genre and instrument words and what to avoid, never an artist, band or song; the look's own music
supplies the rest, and the brief's words win over it); the agent edits it freely before storyboards are drafted, and
the person's own words about the subject or their audience replace anything inferred here.
"""
import collections
import colorsys
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


LINE_MOST = 8


def line_of(said, name):
    """A caption as a line on screen: whole up to LINE_MOST words, else its sentence naming the subject, else its first."""
    if len(said.split()) <= LINE_MOST:
        return said
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", said) if len(x.split()) >= 2]
    named = [x for x in parts if name and name.lower() in x.lower()]
    return ((named or parts or [said])[0]).rstrip(".")


def moments(lib, place_by_month):
    """What they did, from the photographs the film is cast from: each one they wrote words with, by its path, in date
    order, with the people they tagged, the place they named, whether it is of the making (cast.making) and its line,
    drafted as the caption cut to one sentence where it runs past LINE_MOST words (the sentence naming the subject, else
    the first), for the agent to cut further to what the beat says; and the eras, the place each stretch of months was spent in."""
    import cast
    subj = lib.get("subject") or {}
    name = subj.get("name") or ""
    out = []
    for r in sorted(lib.get("feed") or [], key=lambda r: (r.get("date") or "9999", r.get("file") or "")):
        said = (r.get("words") or "").strip()
        if not said:
            continue
        low = said.lower()
        out.append({"date": r.get("date"), "said": said, "people": re.findall(r"@[a-z0-9._]+[a-z0-9_]", low),
                    "place": next((pl for pl in PLACES if pl != "home" and re.search(rf"\b{re.escape(pl)}\b", low)), None),
                    "making": cast.making({"words": said, "caption": r.get("caption") or ""}, name, cast.theirs_of(subj),
                                          subj.get("handle") or ""),
                    "photo": r.get("file") or "", "line": line_of(said, name)})
    eras, cur = [], None
    for m in sorted(place_by_month):
        top = place_by_month[m].most_common(1)[0][0]
        if cur and cur["place"] == top:
            cur["to"] = MONTHS[m - 1]
        else:
            cur = {"place": top, "from": MONTHS[m - 1], "to": MONTHS[m - 1]}
            eras.append(cur)
    return out, eras


def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


def hooks_read(stats):
    """The posts that drew the most response, each with its hook, its style and why it drew."""
    usual = stats.get("median_response") or 0
    out = []
    for t in stats.get("top", []):
        cap = re.sub(r"#\w+", "", t.get("caption") or "").strip()
        toks = set(tokens(cap))
        subject = [th for th, ws in THEMES.items() if toks & set(ws)]
        place = next((pl for pl in PLACES if re.search(rf"\b{re.escape(pl)}\b", cap.lower()) and pl != "home"), None)
        times = round(t["response"] / usual, 1) if usual else None
        why = [f"{t['style']} hook"]
        if times:
            why.append(f"{times}x your usual response")
        if t.get("mentions_subject"):
            why.append("names the subject")
        if t.get("kind") == "reel":
            why.append("a reel")
        if subject or place:
            why.append(" and ".join(([place] if place else []) + subject[:2]))
        out.append({"rank": t["rank"], "kind": t["kind"], "date": t["date"], "response": t["response"], "likes": t.get("likes"),
                    "comments": t.get("comments"), "saves": t.get("saves"), "hook": t["hook"], "style": t["style"],
                    "times_usual": times, "subject": subject, "place": place, "mentions_subject": t.get("mentions_subject"),
                    "caption": cap, "why": "; ".join(why)})
    return out


def response_shared(top, rows, stats):
    """What the posts that drew the most share, set against the rest of the window's posts."""
    caps = {x["caption"] for x in top}
    rest = [p for p in rows if re.sub(r"#\w+", "", p.get("caption") or "").strip() not in caps]
    lines = []
    for h in stats.get("hook_styles") or []:
        lines.append(f"{h['style']} hooks: {h['in_top']} of the top {len(top)}, mean response {h['mean_response']} "
                     f"(across all {h['posts']} posts in that style, {h['mean_response_all']})")
    for th in THEMES:
        a = sum(1 for x in top if th in x["subject"])
        b = sum(1 for p in rest if set(tokens(p.get("caption"))) & set(THEMES[th]))
        if a >= 3 and a / max(1, len(top)) > 1.3 * b / max(1, len(rest)):
            lines.append(f"{th}: {a} of the top {len(top)}, {round(100 * b / max(1, len(rest)))}% of the rest")
    named = sum(1 for x in top if x.get("mentions_subject"))
    if named:
        lines.append(f"{named} of the top {len(top)} already name the subject")
    reels = sum(1 for x in top if x["kind"] == "reel")
    if reels:
        lines.append(f"{reels} of the top {len(top)} are reels")
    liked = sorted((p for p in rows if p.get("likes") is not None), key=lambda p: -p["likes"])
    if liked and top:
        first = re.sub(r"#\w+", "", liked[0].get("caption") or "").strip()
        at = next((x["rank"] for x in top if x["caption"] == first), None)
        lines.append(f"their most-liked post ({liked[0]['likes']} likes) is " +
                     (f"number {at} by response" if at else "outside the top by response") + ": likes and response differ")
    return lines


def is_cool(hex_):
    """A saturated blue or teal: a color the subject owns that a 'cold blue' avoid rule would grade away."""
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, sat = colorsys.rgb_to_hls(r, g, b)
    return 0.45 <= h <= 0.72 and sat >= 0.3 and 0.08 <= l <= 0.85


def subject_read(lib, stats, pal):
    la = lib.get("subject") or {}
    return {"name": la.get("name"), "kind": la.get("kind"), "handle": la.get("handle"), "launch": bool(la.get("launch")),
            "facts": la.get("facts") or [], "about": la.get("about") or "",
            "date": la.get("date"), "date_text": la.get("date_text"),
            "date_label": la.get("date_label"), "days_to_go": la.get("days_to_go"), "assets_kind": la.get("assets_kind"),
            "assets": la.get("assets"), "stills": len(la.get("stills") or []), "footage": len(la.get("footage") or []),
            "posts_about_it": [{"date": p["date"], "response": p["response"], "caption": p["caption"]} for p in stats.get("subject_posts") or []],
            "palette": pal.get("subject") or [], "meet": pal.get("meet") or []}


def storyboard_lines(lib):
    """The line each subject still may carry (storyboard.subject_lines), drafted for the agent to cut."""
    import storyboard
    return storyboard.subject_lines(lib.get("subject") or {})


# the tone each kind of subject starts from; the agent or the person's ask changes it
TONE_OF_KIND = {"product": "app-store", "drop": "chaotic", "event": "cinematic", "friend": "cinematic", "idea": "yc-parody",
                "account": "default", "creator": "default", "band": "chaotic", "place": "polished", "repo": "yc-parody",
                "page": "default", "thing": "default"}


def plan_draft(subj):
    """The plan as the subject's own words draft it: what it is (its first sentence about itself, else its first fact),
    what sets it apart and the best true claim (its next facts), the hook (its name), the punchline (its last fact,
    cut to a line), the share caption (its name and first fact) and the tone its kind starts from. Who it is for and
    the angle are left for the agent; nothing here is invented."""
    facts = [f.strip().rstrip(".") for f in subj.get("facts") or [] if f.strip()]
    name = subj.get("name") or ""
    first = (subj.get("about") or "").split(". ")[0].strip().rstrip(".") or (facts[0] if facts else None)
    return {"what": first, "for": None, "apart": facts[1] if len(facts) > 1 else None,
            "claim": facts[2] if len(facts) > 2 else (facts[0] if facts else None), "hook": None,
            "share": f"{name}: {facts[0]}." if name and facts else None, "angle": None,
            "punchline": line_of(facts[-1], name) if facts and not subj.get("launch") else None,
            "tone": TONE_OF_KIND.get(subj.get("kind") or "thing", "default")}


def type_direction(themes, register, pacing):
    """How loud the type reads from their captions and reels: kinetic, documentary, or editorial, and why."""
    film = themes.get("film photography", 0)
    loud = register.get("emoji_per_caption", 0) > 1 or (pacing.get("avg_shot_seconds") or 9) < 1.2
    if loud:
        return {"lead": "kinetic", "why": "heavy emoji and fast reels read as loud"}
    if film and themes.get("travel", 0) >= film:
        return {"lead": "documentary", "why": "travel carried on film"}
    return {"lead": "editorial", "why": "quiet captions and film photography"}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    _env.enter_run()
    lib = _env.read_json("library.json")
    if not lib:
        sys.exit("library.json is missing: run gather.py first")
    for s in ("stats.py", "picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    stats = _env.read_json("stats.json")
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
    mom, eras = moments(lib, place_by_month)
    hooks = hooks_read(stats)
    hooks_shared = response_shared(hooks, posts + lib["reels"], stats)
    subj = subject_read(lib, stats, pal)
    subject_palette = [{"hex": c["hex"], "name": c.get("name"), "share": c.get("share"), "photo": c.get("photo")}
                       for c in (pal.get("subject") or [])]
    td = type_direction(own_themes + liked_themes, caps, pacing)
    year_palette = [{"hex": s["hex"], "name": s.get("name"), "share": s.get("share"), "photo": s.get("photo")}
                    for s in (pal.get("year") or [])]
    cool_subject = any(is_cool(c["hex"]) for c in subject_palette)
    film = (own_themes.get("film photography", 0) + liked_themes.get("film photography", 0)) >= 5
    warm_light = (own_themes.get("light", 0) + liked_themes.get("light", 0)) >= 4
    research = {
        "handle": lib["handle"], "year": lib["year"], "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": stats.get("counts"),
        "palette": {"year": year_palette, "subject": subject_palette, "meet": pal.get("meet") or [], "likes": likes_palette,
                    "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "subject": subj,
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
        "moments": mom, "eras": eras,
        "hooks": hooks, "response_shared": hooks_shared, "hook_styles": stats.get("hook_styles"),
        "median_response": stats.get("median_response"), "median_likes": stats.get("median_likes"),
        "ranked_by": stats.get("ranked_by"),
        "type": td,
    }
    _env.write_json("research.json", research)
    shot = pacing.get("avg_shot_seconds")
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "palette": {"year": year_palette, "subject": subject_palette, "meet": pal.get("meet") or [], "likes": likes_palette,
                    "direction": "where the subject's colors meet theirs" if subject_palette else "their year"},
        "subject": {**{k: subj[k] for k in ("name", "kind", "handle", "launch", "facts", "date", "date_text", "date_label",
                                            "days_to_go", "assets_kind")},
                    "lines": storyboard_lines(lib)},
        "plan": plan_draft(subj),
        "said": {"subject": None, "audience": None, "hook": None},
        "seconds": None,
        "style": None,
        "ask": True,
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": [t for t, _ in (own_themes + liked_themes).most_common(4)],
        "people": [p["account"] for p in stats.get("people", [])[:5]],
        "places": [p for p, _ in places.most_common(5) if p != "home"],
        "moments": mom,
        "texture": {"grain": 0.16 if film else 0, "vignette": 0.32 if film else 0.0, "leaks": bool(film and warm_light)},
        "avoid": ([] if cool_subject else ["cold blue grading"]) + ["neon", "stock-photo gloss"] if film else ["muddy grading"],
        "music": {"styles": [], "avoid": ["vocals", "spoken word", "harsh distortion"]},
    }
    if not Path("taste.json").exists() or "research.py draft" in (_env.read_json("taste.json") or {}).get("written_by", ""):
        _env.write_json("taste.json", taste)
    lines = [f"# taste draft for @{lib['handle']} ({lib['year']})", "",
             "The agent writes taste.md from this: one page, six paragraphs that start with the six headings below.", "",
             "## you are", f"- posts are about: {', '.join(f'{k} ({v})' for k, v in own_themes.most_common(5))}",
             f"- places: {', '.join(f'{p} ({n})' for p, n in places.most_common(6))}",
             f"- eras: {'; '.join(e['place'] + ' ' + e['from'] + ('-' + e['to'] if e['to'] != e['from'] else '') for e in eras)}",
             "- the making, in the order they made it (their words, who was there, where):"]
    told = lambda m: (f"  {m['date'] or 'undated'}: \"{m['said']}\"" + (f" with {', '.join(m['people'])}" if m["people"] else "")
                      + (f", {m['place']}" if m["place"] else "") + f" ({Path(m['photo']).name})")
    lines += [told(m) for m in mom if m["making"]] or ["  none: no photograph of theirs is of the making"]
    lines += ["- the rest of their year (their table, their people, their places):"]
    lines += [told(m) for m in mom if not m["making"]] or ["  none"]
    lines += ["", "## you like",
             f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes; the top ten got {int(research['likes']['top10_share'] * 100)}%",
             f"- most liked: {', '.join(a for a, _ in like_accounts.most_common(6))}",
             f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
             f"- palette of the year: {', '.join((s.get('name') or '') + ' ' + s['hex'] for s in year_palette)}",
             f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
             "", "## your style is",
             f"- reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels to measure",
             f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
             f"- music: each look brings its own; their words for it, if any, go in taste.json music styles; no {', no '.join(taste['music']['avoid'])}",
             "", "## your voice is",
             f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
             f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
             f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
             f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
             f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
             "", "## the subject",
             f"- {subj['name']}, a {subj.get('kind') or 'thing'}" + (f" ({subj['handle']})" if subj.get("handle") else "")
             + (f", a launch on {subj['date_label'] or subj['date_text'] or 'a day not given'}" if subj.get("launch") else ", not a launch")
             + (f" ({subj['days_to_go']} days to go)" if subj.get("launch") and subj.get("days_to_go") is not None else ""),
             f"- its facts, in its own words: {' / '.join(subj.get('facts') or []) or 'none given; ask, or read its page'}",
             "- the plan (taste.json \"plan\"): what it is, who it is for, what sets it apart, the best true claim, the hook,"
             " the share caption; then the angle, the punchline and the tone",
             f"- assets: {subj['assets_kind']} ({subj['stills']} stills, {subj['footage']} clips) {subj.get('assets') or ''}",
             f"- subject palette: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in subject_palette) or 'none'}",
             f"- where it meets theirs: {'; '.join(m['subject_name'] + ' / ' + m['theirs_name'] + ' (' + m['reads'] + ')' for m in subj['meet'])}",
             f"- posts already about it: {'; '.join(str(p.get('date') or '') + ' ' + p['caption'][:70] for p in subj['posts_about_it']) or 'none'}",
             "- what they said about the subject and their audience (their words win; put them in taste.json \"said\"):",
             "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    _env.write_text("taste.draft.md", "\n".join(lines))
    print(f"themes: {dict(own_themes.most_common(4))}; liked themes: {dict(liked_themes.most_common(4))}")
    print(f"year palette: {[s['hex'] for s in year_palette]}; likes palette: {[s['hex'] + ' ' + s['name'] for s in likes_palette]}")
    print(f"voice: {caps.get('avg_words')} words, lowercase {caps.get('lowercase_share')}, emoji {caps.get('emoji_per_caption')}")
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s; type lead {td['lead']}")
    print(f"moments: {len(mom)} ({sum(m['making'] for m in mom)} of the making); eras: {len(eras)}")
    print(f"subject: {subj['name']} ({subj.get('kind')}"
          + (f", a launch on {subj['date_label'] or subj['date_text']}" if subj.get("launch") else "")
          + f"), assets {subj['assets_kind']} ({subj['stills']} stills, {subj['footage']} clips), {len(subj.get('facts') or [])} facts")
    print("wrote research.json, taste.json (draft) and taste.draft.md; now write taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
