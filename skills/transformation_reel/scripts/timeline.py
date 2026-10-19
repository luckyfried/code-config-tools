#!/usr/bin/env python3
"""Movement 1, research: the subject and its timeline. Reads build/library.json, writes build/subject.json and
build/photo_index.json, and prepares the subject's photos in build/photos/.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/timeline.py [--subject "my pottery"] [--terms clay,kiln]

The subject: the one the person named (--subject, matched on their captions and hashtags through the word groups
below, plus --terms), otherwise the subject with the longest dated run of posts: for each word group, the posts
that name it, split into runs wherever two posts sit more than 62 days apart; the longest run in days wins, ties
to the run with more posts. A named subject with no posts exits 2 and prints the candidates; so does a feed where
nothing runs for at least two months.

The timeline is every post and reel of the subject, oldest first, each with its date, caption, photo (a reel
stands in by its poster frame and stays available as footage) and how far it has moved from the first photo
(the visible change: a small picture of each photo against the first, 0 at the first, 1 at the farthest).
  first, latest   the subject's earliest and latest dated posts: the film runs from one to the other
  milestones      the posts whose captions say so (milestone, first, finally, sold, proud, 100th); their own words
                  win, and only when they name fewer than two does the largest visible step join as a milestone
  span            the months (or weeks, or years) between first and latest, the number every card and the caption say
  voice           how the captions about the subject sound early (the oldest third) against recent (the newest third)
  changed         their own lines about what changed ("taller", "a year ago", "now"), newest first
"""
import argparse
import calendar
import datetime as dt
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

SUBJECTS = {
    "pottery": ["pottery", "ceramics", "ceramic", "clay", "wheel", "glaze", "glazed", "kiln", "bisque", "throwing", "thrown",
                "greenware", "stoneware", "porcelain", "mug", "mugs", "vase", "vases", "bowl", "bowls", "potter", "wheelthrown"],
    "garden": ["garden", "gardening", "balconygarden", "seedling", "seedlings", "plants", "planted", "sprouts", "harvest",
               "greenhouse", "allotment", "raisedbed", "growyourown"],
    "fitness": ["gym", "workout", "lift", "lifting", "deadlift", "squat", "run", "running", "marathon", "5k", "10k", "fitness",
                "training", "pr", "fitnessjourney", "gains", "yoga", "pilates"],
    "home": ["renovation", "reno", "renovating", "diy", "kitchen", "bathroom", "flat", "apartment", "house", "home",
             "makeover", "paint", "tiles", "homeproject", "fixerupper", "beforeandafter"],
    "art": ["art", "painting", "paint", "drawing", "sketch", "sketchbook", "watercolor", "watercolour", "illustration", "canvas",
            "oilpainting", "artjourney", "doodle", "inktober"],
    "baking": ["sourdough", "bread", "loaf", "bake", "baking", "crumb", "starter", "pastry", "croissant", "cake"],
    "knitting": ["knit", "knitting", "crochet", "yarn", "sweater", "embroidery", "sewing", "quilt"],
    "music": ["guitar", "piano", "violin", "drums", "practice", "chords", "cover", "singing"],
    "glow-up": ["glowup", "selfie", "skincare", "hair", "transformation", "weightloss", "progresspic"],
    "woodworking": ["woodworking", "wood", "carving", "joinery", "workbench", "furniture"],
    "pet": ["puppy", "kitten", "dog", "cat", "pup"],
    "calligraphy": ["calligraphy", "lettering", "handlettering", "brushlettering"],
}
# words that name a subject only as a hashtag: in running text they mean anything ("home by the sea", "a run of luck")
HASHTAG_ONLY = {"home", "flat", "house", "paint", "hair", "cover", "practice", "run", "pr", "lift", "wood", "starter", "crumb",
                "cake", "cat", "dog", "art", "sketch", "transformation"}
STOP = {"my", "the", "a", "an", "of", "our", "me", "i", "and", "year", "progress", "journey", "video", "reel", "this"}
MILESTONE = re.compile(r"\b(milestone|first|finally|sold|proud|\d+(?:st|nd|rd|th))\b", re.I)
CHANGED = re.compile(r"\b(now|ago|months? in|years? in|weeks? in|taller|thinner|lighter|bigger|stronger|better|faster|"
                     r"every time|exactly|anymore|used to|no longer|since)\b", re.I)
UNSURE = re.compile(r"\b(supposed|wobbly|sort of|kind of|lol|ugly|collapse|collapses|nowhere|hardest|hurt|oops|trying|"
                    r"attempt|messy|crooked|lopsided|fingers crossed|nobody warned)\b", re.I)
SURE = re.compile(r"\b(exactly|every time|matching|set of|commission|sold|planned|holding|all thrown|trimmed and glazed)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
GAP_DAYS = 62
VIDEO = {".mp4", ".mov", ".m4v"}


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def matches(row, terms):
    cap = (row.get("caption") or "").lower()
    toks = set(tokens(re.sub(r"#\w+", " ", cap)))
    tags = [t.lower() for t in re.findall(r"#(\w+)", cap)]
    return bool(toks & (terms - HASHTAG_ONLY)) or any(t in tags or any(len(x) >= 4 and x in tag for tag in tags) for t in terms for x in [t])


def date_of(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date()


def runs(rows):
    out, cur = [], []
    for r in rows:
        if cur and (r["ts"] - cur[-1]["ts"]) > GAP_DAYS * 86400:
            out.append(cur)
            cur = []
        cur.append(r)
    if cur:
        out.append(cur)
    return out


def span_of(d1, d2):
    """Whole months between two dates (the day of the month decides a partial one), said the way a caption says it."""
    months = (d2.year - d1.year) * 12 + d2.month - d1.month - (1 if d2.day < d1.day else 0)
    days = (d2 - d1).days
    if months < 2:
        weeks = days // 7
        label = f"{days} days" if weeks < 2 else f"{weeks} weeks"
    elif months % 12 == 0:
        label = "a year" if months == 12 else f"{months // 12} years"
    else:
        label = f"{months} months"
    return {"first": d1.isoformat(), "latest": d2.isoformat(), "months": months, "days": days, "label": label,
            "from": f"{calendar.month_name[d1.month]} {d1.year}", "to": f"{calendar.month_name[d2.month]} {d2.year}"}


def rows_of(lib):
    rows = []
    for kind in ("posts", "reels"):
        for r in lib.get(kind) or []:
            if r.get("ts") and r.get("media"):
                rows.append(dict(r, kind="reel" if kind == "reels" else "post"))
    if not rows:
        rows = [dict(r, kind="post") for r in lib.get("facebook") or [] if r.get("ts") and r.get("media")]
    rows.sort(key=lambda r: r["ts"])
    return rows


def terms_for(named, extra):
    words = [w for w in tokens(named or "") if w not in STOP]
    words = words + [w[:-1] for w in words if w.endswith("s") and len(w) > 3]
    group = next((g for g, ws in SUBJECTS.items() if g in words or set(words) & set(ws)), None)
    terms = set(words) | set(extra)
    if group:
        terms |= set(SUBJECTS[group])
    return (group or (words[0] if words else named)), terms


def candidates(rows):
    out = []
    for g, ws in SUBJECTS.items():
        hit = [r for r in rows if matches(r, set(ws))]
        if not hit:
            continue
        best = max(runs(hit), key=lambda run: (run[-1]["ts"] - run[0]["ts"], len(run)))
        out.append({"subject": g, "posts": len(hit), "first": date_of(hit[0]["ts"]).isoformat(),
                    "latest": date_of(hit[-1]["ts"]).isoformat(), "run_days": (best[-1]["ts"] - best[0]["ts"]) // 86400,
                    "run_posts": len(best), "run_first": date_of(best[0]["ts"]).isoformat(),
                    "run_latest": date_of(best[-1]["ts"]).isoformat()})
    out.sort(key=lambda c: (-c["run_days"], -c["run_posts"]))
    return out


def signature(path):
    """A small picture of the photo: 16x20 gray levels and the mean color, for measuring visible change."""
    import picks
    im = picks.open_image(path, draft=(160, 200)).resize((16, 20))
    gray = [v / 255 for v in im.convert("L").tobytes()]
    rgb = im.convert("RGB").tobytes()
    n = len(rgb) // 3
    mean = [sum(rgb[i::3]) / n / 255 for i in range(3)]
    return gray + [m * 3 for m in mean]


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for k, i in enumerate(order):
            r[i] = k
        return r
    if len(xs) < 3:
        return None
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    return round(1 - 6 * sum((a - b) ** 2 for a, b in zip(rx, ry)) / (n * (n * n - 1)), 2)


def clean(cap):
    return re.sub(r"\s+", " ", EMOJI.sub("", re.sub(r"#\w+", "", cap or ""))).strip(" .,")


def voice(posts):
    caps = [p for p in posts if (p.get("caption") or "").strip()]
    if len(caps) < 3:
        return {"captions": len(caps)}
    k = max(1, len(caps) // 3)

    def read(part):
        text = [p["caption"] for p in part]
        words = [len(clean(t).split()) for t in text]
        return {"posts": len(part), "from": part[0]["date"], "to": part[-1]["date"],
                "avg_words": round(statistics.mean(words), 1),
                "unsure": sum(1 for t in text if UNSURE.search(t)), "sure": sum(1 for t in text if SURE.search(t)),
                "emoji": round(sum(len(EMOJI.findall(t)) for t in text) / len(text), 2),
                "hashtags": round(sum(len(re.findall(r"#\w+", t)) for t in text) / len(text), 2),
                "lines": [clean(t) for t in text[:3]]}
    early, recent = read(caps[:k]), read(caps[-k:])
    def tone(v):
        if v["unsure"] > v["sure"]:
            return "unsure of themselves, laughing at the misses"
        if v["sure"] > v["unsure"]:
            return "sure of the craft, naming what they made"
        return "plain, saying what is on the shelf"
    summary = (f"early ({early['from'][:7]} to {early['to'][:7]}): {early['avg_words']} words a caption, {tone(early)} "
               f"(\"{early['lines'][0]}\"); recent ({recent['from'][:7]} to {recent['to'][:7]}): {recent['avg_words']} words, "
               f"{tone(recent)} (\"{recent['lines'][-1]}\")")
    return {"early": early, "recent": recent, "summary": summary}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", help="the subject the person named, in their words")
    ap.add_argument("--terms", default="", help="more words or hashtags that name the subject, comma separated")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    _env.need("PIL")
    import picks
    rows = rows_of(lib)
    cands = candidates(rows)
    extra = [t.strip().lower().lstrip("#") for t in a.terms.split(",") if t.strip()]
    if a.subject:
        name, terms = terms_for(a.subject, extra)
        hit = [r for r in rows if matches(r, terms)]
        chosen_by = f"named by the person (\"{a.subject}\")"
    else:
        top = next((c for c in cands if c["run_days"] >= 60 and c["run_posts"] >= 4), None)
        name, terms = (top["subject"], set(SUBJECTS[top["subject"]]) | set(extra)) if top else (None, set())
        hit = [r for r in rows if matches(r, terms)] if top else []
        if top:
            hit = [r for r in hit if top["run_first"] <= date_of(r["ts"]).isoformat() <= top["run_latest"]]
        chosen_by = (f"the longest dated run of posts ({top['run_posts']} posts over {top['run_days']} days, "
                     f"{top['run_first']} to {top['run_latest']})") if top else ""
    if len(hit) < 2:
        print("candidates: " + "; ".join(f"{c['subject']} {c['posts']} posts, run {c['run_days']} days" for c in cands[:6]))
        sys.exit(f"no subject with at least two dated posts{' for ' + repr(a.subject) if a.subject else ' runs two months'}: "
                 "ask the person which subject to follow, then run timeline.py --subject \"...\" (add --terms for their hashtags)")
    posts = []
    for r in hit:
        media = r["media"][0]
        video = media if Path(media).suffix.lower() in VIDEO else None
        photo = picks.poster(media) if video else next((picks.prepare(m) for m in r["media"] if Path(m).suffix.lower() not in VIDEO), None)
        if not photo:
            continue
        posts.append({"date": date_of(r["ts"]).isoformat(), "ts": r["ts"], "kind": r["kind"], "caption": r.get("caption") or "",
                      "src": media, "video": video, "photo": photo, "likes": r.get("likes")})
    for i, p in enumerate(posts, 1):
        p["id"] = f"p{i:02d}"
    sigs = [signature(p["photo"]) for p in posts]
    far = [dist(s, sigs[0]) for s in sigs]
    top = max(far) or 1
    for i, p in enumerate(posts):
        an = picks.analyse(p["photo"])
        p.update(change=round(far[i] / top, 3), step=round(dist(sigs[i], sigs[i - 1]) / top, 3) if i else 0.0,
                 score=an["score"], bright=an["bright"], focal=an["focal"], calm=an["calm"], colors=an["colors"])
    first, latest = posts[0], posts[-1]
    said = [p for p in posts[1:-1] if MILESTONE.search(p["caption"])]
    miles = [{"id": p["id"], "date": p["date"], "caption": p["caption"], "label": clean(p["caption"]), "why": "their words"} for p in said]
    if len(miles) < 2:
        for p in sorted(posts[1:-1], key=lambda p: -p["step"]):
            if len(miles) >= 3:
                break
            if p["id"] not in {m["id"] for m in miles}:
                miles.append({"id": p["id"], "date": p["date"], "caption": p["caption"], "label": clean(p["caption"]) or p["date"],
                              "why": f"visible change: the largest step between two posts ({p['step']:.2f} of the whole change)"})
        miles.sort(key=lambda m: m["date"])
    for p in posts:
        p["milestone"] = p["id"] in {m["id"] for m in miles}
    span = span_of(dt.date.fromisoformat(first["date"]), dt.date.fromisoformat(latest["date"]))
    changed = [{"id": p["id"], "date": p["date"], "line": clean(p["caption"])} for p in reversed(posts) if CHANGED.search(p["caption"])][:6]
    v = voice(posts)
    steady = spearman(list(range(len(posts))), [p["change"] for p in posts])
    out = {"subject": name, "named": a.subject, "chosen_by": chosen_by, "terms": sorted(terms), "candidates": cands,
           "posts": posts, "first": {k: first[k] for k in ("id", "date", "caption", "photo")},
           "latest": {k: latest[k] for k in ("id", "date", "caption", "photo")}, "milestones": miles, "span": span,
           "voice": v, "changed": changed, "steadiness": steady,
           "steadiness_means": "how steadily the photos move away from the first one as the dates go on (1 is every post further than the last)"}
    _env.write_json("build/subject.json", out)
    index = [{"src": p["src"], "photo": p["photo"], "kind": p["kind"], "ts": p["ts"], "date": p["date"], "id": p["id"],
              "score": p["score"], "bright": p["bright"], "focal": p["focal"], "calm": p["calm"], "colors": p["colors"]} for p in posts]
    _env.write_json("build/photo_index.json", index)
    print(f"subject: {name}, {chosen_by}")
    print("candidates: " + "; ".join(f"{c['subject']} {c['posts']} posts, longest run {c['run_days']} days ({c['run_posts']} posts)" for c in cands[:5]))
    print(f"timeline: {len(posts)} posts, {span['first']} to {span['latest']} ({span['label']}); visible change steadiness {steady}")
    print(f"  first  {first['date']} {first['id']}: {clean(first['caption'])}")
    for m in miles:
        print(f"  mile   {m['date']} {m['id']}: {m['label']} [{m['why']}]")
    print(f"  latest {latest['date']} {latest['id']}: {clean(latest['caption'])}")
    if v.get("summary"):
        print(f"voice: {v['summary']}")
    print("wrote build/subject.json and build/photo_index.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
