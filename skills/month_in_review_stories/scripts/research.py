#!/usr/bin/env python3
"""Movement 1: the counting behind the taste profile, the month set against the year. Reads build/library.json;
writes build/research.json, a machine draft of build/taste.json, and build/taste.draft.md (the numbers under the
six headings the agent turns into build/taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py

It runs stats.py, picks.py and palette.py first (counts, photo picks, the month's palette and the year's), then
reads:
  change    the month against their year: cadence (posts a week, posting days, the month's rank among the twelve),
            subjects (each theme's share of the month's captions against its share of the rest of the year, and the
            subjects that are new this month), the words that mark the month (the month's captions against the
            rest, by smoothed log-odds), the palette shift (the month's colors that sit far from the year's), and
            the voice shift (length, case, emoji, hashtags of the month against the rest)
  pillars   the month's three or four subjects with how many posts each carried, and the words behind each
  moments   the three best moments of the month by their own numbers, each with why it worked: how many times
            their usual likes, whether it beat the best post of the rest of the year, its subject, place and two
            strongest colors, and what its caption says
  voice     the month's captions: length, case, emoji, punctuation, hashtags, how they open and close, sample lines
  palette   the month's colors, the year's, and the colors of what they like and save
  likes     the like-graph: who gets their likes, how concentrated, the themes those accounts share
  reels     how long their reels run and how fast they cut (ffmpeg scene changes)
  places    places from the month's captions, albums and check-ins, and the year's
taste.json also carries the type direction, pacing, register, texture and the grade inputs; the agent edits it
freely before storyboards are drafted.
"""
import collections
import datetime as dt
import itertools
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
THEMES["ceramics"] = ["tiles", "tile", "zellige", "pottery", "ceramics", "glaze", "wheel", "bowl", "kiln", "clay"]
THEMES["gardens"] = ["garden", "gardens", "majorelle", "plants", "botanical", "courtyard"]
COLOR_WORDS.update({"cobalt": "#2654b2", "indigo": "#282e62", "majorelle": "#2f4fb0", "ultramarine": "#2a3fa8"})
STOP = set("""a an and the of in on at to for from with by is it its it's i i'm im me my we our you your this that these those
was were be been are am so just one all every more most very too then than but or not no yes out up down over into still
like what who how when where why there here day days week today again back first last new got get make made had have has
do did will can could would really some any much many little lot two three four five six seven eight nine ten""".split())



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


def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


def distinctive(month_caps, rest_caps, n=8):
    """The words that mark the month: smoothed log-odds of each word in the month's captions against the rest."""
    import math
    mc = collections.Counter(t for c in month_caps for t in set(tokens(re.sub(r"#\w+", "", c))) if t not in STOP and len(t) > 2 and not t.isdigit())
    rc = collections.Counter(t for c in rest_caps for t in set(tokens(re.sub(r"#\w+", "", c))) if t not in STOP and len(t) > 2 and not t.isdigit())
    nm, nr = max(1, len(month_caps)), max(1, len(rest_caps))
    score = {w: math.log((mc[w] + 0.5) / (nm + 1)) - math.log((rc[w] + 0.5) / (nr + 1)) for w in mc if mc[w] >= 3}
    return [{"word": w, "month": mc[w], "month_share": round(mc[w] / nm, 2), "year_share": round(rc[w] / nr, 3), "lift": round(score[w], 2)}
            for w in sorted(score, key=lambda w: -score[w])[:n] if score[w] > 0.7]


def theme_shift(month_caps, rest_caps):
    mt, rt = theme_counts(month_caps), theme_counts(rest_caps)
    nm, nr = max(1, len(month_caps)), max(1, len(rest_caps))
    rows = []
    for th in set(mt) | set(rt):
        a, b = mt.get(th, 0) / nm, rt.get(th, 0) / nr
        rows.append({"theme": th, "month": mt.get(th, 0), "month_share": round(a, 2), "year_share": round(b, 2),
                     "new": a >= 0.15 and b < 0.05, "up": a >= 0.1 and a >= 2 * b, "down": b >= 0.15 and a < 0.5 * b})
    return sorted(rows, key=lambda r: -r["month_share"])


def voice_shift(m, y):
    out = []
    if m.get("captions") and y.get("captions"):
        if abs(m["avg_words"] - y["avg_words"]) >= 2:
            out.append(f"{'longer' if m['avg_words'] > y['avg_words'] else 'shorter'} captions: {m['avg_words']} words against {y['avg_words']}")
        if abs(m["emoji_per_caption"] - y["emoji_per_caption"]) >= 0.15:
            out.append(f"{'more' if m['emoji_per_caption'] > y['emoji_per_caption'] else 'fewer'} emoji: {m['emoji_per_caption']} a caption against {y['emoji_per_caption']}")
        if abs(m["lowercase_share"] - y["lowercase_share"]) >= 0.1:
            out.append(f"lowercase {int(m['lowercase_share'] * 100)}% against {int(y['lowercase_share'] * 100)}%")
        new_tags = [t for t in m.get("top_hashtags", []) if t not in y.get("top_hashtags", [])]
        if new_tags:
            out.append("new hashtags: " + ", ".join(new_tags[:4]))
    return out or ["the same voice as the rest of the year"]


def moments_read(stats, picks):
    """Why each of the three worked, from their own numbers, the photo and the caption."""
    info = {n["rank"]: n for n in picks.get("three", [])}
    ag = stats.get("against") or {}
    out = []
    for t in stats.get("top_three", []):
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
        beats = bool(ag.get("year_best_likes") and t.get("likes") is not None and t["likes"] > ag["year_best_likes"])
        why = []
        if t.get("times_usual"):
            why.append(f"{t['times_usual']}x your usual likes")
        if beats:
            why.append("more than any post of the rest of the year")
        if t.get("kind") == "reel":
            why.append("a reel")
        if subject or place:
            why.append(" and ".join(([place] if place else []) + subject[:2]))
        if colors:
            why.append(" and ".join(colors[:2]))
        out.append({"rank": t["rank"], "kind": t["kind"], "date": t["date"], "date_label": t.get("date_label"), "likes": t.get("likes"),
                    "comments": t.get("comments"), "times_usual": t.get("times_usual"), "beats_year_best": beats, "subject": subject,
                    "place": place, "colors": colors[:3], "bright": n.get("bright"), "caption": cap, "why": "; ".join(why)})
    return out


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


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib or not lib.get("month"):
        sys.exit("build/library.json is missing or names no month: run gather.py first")
    for s in ("stats.py", "picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    stats = _env.read_json("build/stats.json")
    pal = _env.read_json("build/palette.json") or {}
    picks = _env.read_json("build/picks.json") or {}
    mo = lib["month"]
    inm = lambda r: r.get("ts") and f"{dt.datetime.fromtimestamp(r['ts'], dt.timezone.utc):%Y-%m}" == mo["key"]
    posts = lib["posts"]
    captioned = posts + lib["reels"] + lib.get("facebook", [])
    m_rows = [r for r in captioned if inm(r)]
    y_rows = [r for r in captioned if not inm(r)]
    m_caps = [r.get("caption") or "" for r in m_rows if (r.get("caption") or "").strip()]
    y_caps = [r.get("caption") or "" for r in y_rows if (r.get("caption") or "").strip()]
    caps, caps_year = caption_read(m_rows), caption_read(y_rows)
    like_accounts = collections.Counter(r.get("account") for r in lib["likes"] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved", []) if r.get("account"))
    follow = [r.get("account") for r in lib.get("following", []) if r.get("account")]
    liked_text = [a for a in like_accounts.elements()] + [a for a in saved_accounts.elements()] + follow + \
                 [r.get("caption") or "" for r in lib["likes"] + lib.get("saved", [])]
    liked_media = [m for r in lib["likes"] + lib.get("saved", []) for m in (r.get("media") or []) if Path(m).exists()]
    likes_palette = image_palette(liked_media) if len(liked_media) >= 8 else lexicon_palette(liked_text)
    likes_palette_from = "the photos they liked and saved" if len(liked_media) >= 8 else \
        "the color words in the names and captions of the accounts they like, save and follow"
    own_themes = theme_counts(m_caps)
    year_themes = theme_counts(y_caps)
    liked_themes = theme_counts(list(like_accounts.elements()) + list(saved_accounts.elements()) + follow)
    top10 = sum(n for _, n in like_accounts.most_common(10))
    pacing = reel_pacing(lib["reels"])
    places, _ = places_in([r for r in posts + lib["reels"] if inm(r)], [r for r in lib.get("facebook", []) if inm(r)])
    places_year, _ = places_in([r for r in posts + lib["reels"] if not inm(r)], [r for r in lib.get("facebook", []) if not inm(r)])
    themes = theme_shift(m_caps, y_caps)
    words = distinctive(m_caps, y_caps)
    voice = voice_shift(caps, caps_year)
    color_words = lexicon_palette(m_caps)
    moments = moments_read(stats, picks)
    cad = stats["cadence"]
    pillars = []
    for th in [t for t in themes if t["month"]][:4]:
        ws = [w["word"] for w in words if w["word"] in THEMES.get(th["theme"], [])] or \
             [w for w in THEMES.get(th["theme"], []) if any(w in tokens(c) for c in m_caps)][:3]
        pillars.append({"pillar": th["theme"], "posts": th["month"], "share": th["month_share"], "year_share": th["year_share"],
                        "new": th["new"], "words": ws[:3]})
    change = {
        "cadence": {"posts": stats["counts"]["posts"], "usual_posts": stats["usual"]["posts"], "vs_usual": cad.get("vs_usual"),
                    "posts_per_week": cad.get("posts_per_week"), "usual_posts_per_week": cad.get("usual_posts_per_week"),
                    "posting_days": cad.get("posting_days"), "usual_posting_days": stats["usual"]["posting_days"],
                    "rank_by_posts": cad.get("rank_by_posts"), "of_months": cad.get("of_months"),
                    "longest_run_days": cad.get("longest_run_days"), "top_weekday": cad.get("top_weekday")},
        "subjects": themes[:8], "new_subjects": [t["theme"] for t in themes if t["new"]],
        "up": [t["theme"] for t in themes if t["up"] and not t["new"]], "down": [t["theme"] for t in themes if t["down"]],
        "words": words, "color_words": color_words,
        "palette": {"new": [{"name": c["name"], "hex": c["hex"], "nearest_year": c.get("nearest_year")} for c in pal.get("shift", [])],
                    "month": [c["name"] for c in pal.get("month", [])], "year": [c["name"] for c in pal.get("year", [])]},
        "voice": voice,
        "places": [p for p, _ in places.most_common(4) if p != "home"],
        "places_year": [p for p, _ in places_year.most_common(4) if p != "home"],
    }
    headline = []
    if cad.get("vs_usual") and cad["vs_usual"] >= 1.4:
        headline.append(f"{stats['counts']['posts']} posts, {cad['vs_usual']}x a usual month")
    elif cad.get("vs_usual") and cad["vs_usual"] <= 0.7:
        headline.append(f"a quieter month: {stats['counts']['posts']} posts against {stats['usual']['posts']} usually")
    if change["new_subjects"]:
        headline.append("new: " + ", ".join(change["new_subjects"]))
    if change["places"] and change["places"][0] not in change["places_year"]:
        headline.append("in " + change["places"][0])
    if change["palette"]["new"]:
        headline.append("new colors: " + ", ".join(c["name"] for c in change["palette"]["new"][:2]))
    if moments and moments[0].get("beats_year_best"):
        headline.append(f"{sum(1 for m in moments if m['beats_year_best'])} posts beat the best of the year before it")
    change["headline"] = headline
    td = type_direction(own_themes + liked_themes, caps, pacing)
    swatch = lambda c: {"hex": c["hex"], "name": c.get("name"), "share": c.get("share"), "photo": c.get("photo")}
    month_palette = [swatch(c) for c in pal.get("month") or []]
    year_palette = [swatch(c) for c in pal.get("year") or []]
    all_themes = own_themes + year_themes + liked_themes
    film = all_themes.get("film photography", 0) >= 5
    warm_light = all_themes.get("light", 0) >= 4
    blue = any("blue" in (c.get("name") or "") or "navy" in (c.get("name") or "") or "indigo" in (c.get("name") or "") or "cobalt" in (c.get("name") or "")
               for c in month_palette) or any(w["name"] in ("cobalt", "indigo", "blue", "navy", "majorelle", "ultramarine") for w in color_words)
    research = {
        "handle": lib["handle"], "year": lib["year"], "month": mo, "window": lib.get("window"), "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": stats.get("counts"), "usual": stats.get("usual"), "months": stats.get("months"),
        "change": change, "pillars": pillars, "moments": moments, "against": stats.get("against"),
        "palette": {"month": month_palette, "year": year_palette, "shift": pal.get("shift", []), "likes": likes_palette,
                    "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "captions": caps, "captions_year": caps_year,
        "likes": {"accounts": len(like_accounts), "top": [{"account": a, "likes": n} for a, n in like_accounts.most_common(10)],
                  "top10_share": round(top10 / max(1, sum(like_accounts.values())), 2),
                  "saved_top": [{"account": a, "saves": n} for a, n in saved_accounts.most_common(5)],
                  "themes": dict(liked_themes.most_common()), "loved_this_month": stats.get("loved", [])},
        "reels": pacing, "people": stats.get("people", [])[:8],
        "places": [{"place": p, "posts": n} for p, n in places.most_common(8)],
        "ranked_by": stats.get("top_ranked_by"), "median_likes": stats.get("median_likes"), "type": td,
    }
    _env.write_json("build/research.json", research)
    shot = pacing.get("avg_shot_seconds")
    avoid = (["neon", "stock-photo gloss", "grading the month's blues toward the year's warmth"] if blue else
             ["cold blue grading", "neon", "stock-photo gloss"]) if film else ["muddy grading"]
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "year": lib["year"],
        "month": {"key": mo["key"], "name": mo["name"], "short": mo["short"], "year": mo["year"]},
        "palette": {"month": month_palette, "year": year_palette, "likes": likes_palette,
                    "shift": [c["name"] for c in pal.get("shift", [])], "direction": "the month's own colors"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.6, min(4.0, (shot or 2.4) * 1.3)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", caps_year.get("lowercase_share", 0)) >= 0.6,
                     "emoji": caps.get("emoji_per_caption", 0), "avg_words": caps.get("avg_words"),
                     "hashtags": (caps.get("top_hashtags") or caps_year.get("top_hashtags") or [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "pillars": [p["pillar"] for p in pillars],
        "change": {"headline": headline, "new_subjects": change["new_subjects"], "words": [w["word"] for w in words[:5]],
                   "voice": voice, "cadence": change["cadence"]},
        "moments": [{"rank": x["rank"], "why": x["why"]} for x in moments],
        "people": [p["account"] for p in stats.get("people", [])[:5]],
        "places": change["places"] or [p for p, _ in places_year.most_common(3) if p != "home"],
        "texture": {"grain": 0.16 if film else 0, "vignette": 0.32 if film else 0.0, "leaks": bool(film and warm_light)},
        "avoid": avoid,
    }
    if not Path("build/taste.json").exists() or "research.py draft" in (_env.read_json("build/taste.json") or {}).get("written_by", ""):
        _env.write_json("build/taste.json", taste)
    sub = lambda t: f"{t['theme']} {int(t['month_share'] * 100)}% of the month, {int(t['year_share'] * 100)}% of the year"
    lines = [f"# taste draft for @{lib['handle']}: {mo['name']} {mo['year']} against {lib.get('window', {}).get('label', 'the year')}", "",
             "The agent writes build/taste.md from this: one page, six paragraphs that start with the six headings below.", "",
             "## this month against your year",
             f"- in short: {'; '.join(headline) or 'a month like the rest of the year'}",
             f"- cadence: {stats['counts']['posts']} posts ({cad.get('posts_per_week')} a week; usually {cad.get('usual_posts_per_week')}), "
             f"{cad.get('vs_usual')}x a usual month, #{cad.get('rank_by_posts')} of {cad.get('of_months')} months; {cad.get('posting_days')} posting days "
             f"(usually {stats['usual']['posting_days']}), longest run {cad.get('longest_run_days')} days, most often on {cad.get('top_weekday')}",
             f"- subjects: {'; '.join(sub(t) for t in themes[:6])}",
             f"- new this month: {', '.join(change['new_subjects']) or 'nothing new'}; up: {', '.join(change['up']) or 'none'}; down: {', '.join(change['down']) or 'none'}",
             f"- words that mark the month: {', '.join(w['word'] + ' (' + str(w['month']) + ')' for w in words) or 'none stand out'}",
             f"- palette: the month {', '.join(c['name'] + ' ' + c['hex'] for c in month_palette)}; the year {', '.join(c['name'] + ' ' + c['hex'] for c in year_palette)}; "
             f"new: {', '.join(c['name'] for c in pal.get('shift', [])) or 'none'}; color words in the month's captions: {', '.join(w['name'] for w in color_words) or 'none'}",
             f"- voice: {'; '.join(voice)}",
             f"- places: the month {', '.join(change['places']) or 'none named'}; the year {', '.join(change['places_year']) or 'none named'}",
             "", "## you are",
             f"- the month's pillars: {'; '.join(p['pillar'] + ' (' + str(p['posts']) + ' posts' + (', new' if p['new'] else '') + ')' for p in pillars)}",
             "- the three best moments (rank, kind, likes, why it worked; caption):"]
    lines += [f"  {x['rank']}. {x['kind']} {x['date']}, {x['likes']} likes, {x['comments']} comments: {x['why']}; \"{x['caption']}\"" for x in moments]
    ag = stats.get("against") or {}
    lines += [f"- against the year: the best post before this month had {ag.get('year_best_likes')} likes; the fourth of the month sits "
              f"{ag.get('gap_to_fourth')} below the third; ranked by {stats.get('top_ranked_by')}",
              f"- people this month: {', '.join('@' + p['account'] for p in stats.get('people', [])[:5])}",
              "", "## you like",
              f"- {len(like_accounts)} accounts got {sum(like_accounts.values())} likes over the twelve months; the top ten got {int(research['likes']['top10_share'] * 100)}%",
              f"- loved this month: {', '.join(x['account'] for x in stats.get('loved', []))}",
              f"- what those accounts share: {', '.join(f'{k} ({v})' for k, v in liked_themes.most_common(5))}",
              f"- palette of their likes ({likes_palette_from}): {', '.join(s['name'] + ' ' + s['hex'] for s in likes_palette)}",
              "", "## your style is",
              f"- reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels to measure",
              f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
              "", "## your voice is",
              f"- this month: {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
              f"{caps.get('emoji_per_caption')} emoji a caption, endings {caps.get('endings')}",
              f"- opens with: {', '.join(caps.get('opens_with', []))}; closes with: {', '.join(caps.get('closes_with', []))}",
              f"- hashtags: {', '.join(caps.get('top_hashtags', []))}",
              f"- lines: {' / '.join(caps.get('samples', [])[:4])}",
              "", "## avoid", f"- {', '.join(avoid)}", ""]
    Path("build/taste.draft.md").write_text("\n".join(lines))
    print(f"{mo['name']} {mo['year']} against {lib.get('window', {}).get('label')}: {'; '.join(headline)}")
    print(f"subjects: {'; '.join(sub(t) for t in themes[:4])}")
    print(f"words: {', '.join(w['word'] for w in words)}; voice: {'; '.join(voice)}")
    print(f"palette: month {[c['name'] for c in month_palette]}; new {[c['name'] for c in pal.get('shift', [])]}; type lead {td['lead']}")
    for x in moments:
        print(f"  {x['rank']}. {x['kind']:<5} {x['likes']} likes: {x['why']}")
    print("wrote build/research.json, build/taste.json (draft) and build/taste.draft.md; now write build/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
