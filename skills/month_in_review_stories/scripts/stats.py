#!/usr/bin/env python3
"""Movement 1, research: what the month's data says about them, beside their photographs and captions. Reads the
run's library.json, writes the run's stats.json.

USAGE (from the workspace root):
    python3 S/scripts/stats.py

The month: posts, reels, stories, likes given, comments written and new followers (each null when the data lacks
it), posting days, posts a week, the weekday they posted most and the longest run of days in a row; the same counts
for every month of the twelve that end with it (only the months the data covers) and the average month before it.
Also the people of the month (accounts @mentioned in their captions and commented on most), the accounts liked most
that month, and the caption register of the month and of the rest of the year, for writing copy in their voice.
Nothing here picks a moment or reaches the screen: the moments are picked from their photographs and captions."""
import argparse
import calendar
import datetime as dt
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
VIDEO = (".mp4", ".mov", ".m4v")


def when(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)


def key(ts):
    d = when(ts)
    return f"{d.year}-{d.month:02d}"


def register(caps):
    words = [len(c.split()) for c in caps]
    letters = [c for c in caps if re.search(r"[A-Za-z]", c)]
    tags = Counter(t.lower() for c in caps for t in re.findall(r"#\w+", c))
    emo = Counter(e for c in caps for e in EMOJI_RE.findall(c))
    step = max(1, len(caps) // 8)
    return {
        "captions": len(caps),
        "lowercase_share": round(sum(1 for c in letters if c == c.lower()) / len(letters), 2) if letters else None,
        "emoji_per_caption": round(sum(emo.values()) / len(caps), 2) if caps else 0,
        "avg_words": round(sum(words) / len(words), 1) if words else 0,
        "top_hashtags": [t for t, _ in tags.most_common(6)],
        "top_emoji": [e for e, _ in emo.most_common(4)],
        "samples": caps[::step][:8],
    }


def rhythm(rows):
    days = sorted({when(r["ts"]).date() for r in rows})
    wd = Counter(d.strftime("%A") for d in days)
    streak = best = 1 if days else 0
    for a, b in zip(days, days[1:]):
        streak = streak + 1 if (b - a).days == 1 else 1
        best = max(best, streak)
    return {"posting_days": len(days), "top_weekday": wd.most_common(1)[0][0] if wd else None, "longest_run_days": best}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    run = _env.run()
    d = _env.read_json(run / "library.json")
    if not d or not d.get("month"):
        sys.exit(f"{run / 'library.json'} is missing or names no month: run gather.py first")
    mo, src = d["month"], d["source"]
    exp = src in ("export", "accounts")
    has = lambda k: bool(d["found"].get(k)) if exp else False
    inm = lambda rows: [r for r in rows if r.get("ts") and key(r["ts"]) == mo["key"]]
    posts, reels, stories = inm(d["posts"]), inm(d["reels"]), inm(d["stories"])
    new_f = [f for f in d["followers"] if f.get("ts") and key(f["ts"]) == mo["key"]]
    counts = {
        "posts": len(posts),
        "reels": len(reels) if (has("reels") or d["reels"]) else None,
        "stories": len(stories) if has("stories") else None,
        "likes_given": len(inm(d["likes"])) if has("likes") else None,
        "comments_written": len(inm(d["comments"])) if has("comments") else None,
        "new_followers": len(new_f) if has("followers") else None,
        "photos": sum(len([m for m in p["media"] if Path(m).suffix.lower() not in VIDEO]) for p in posts),
    }
    numbers = [{"key": k, "value": v, "label": lab} for k, lab in (("posts", "posts"), ("reels", "reels"), ("stories", "stories"),
                                                                  ("likes_given", "likes given"), ("comments_written", "comments written"),
                                                                  ("new_followers", "new followers"))
               for v in [counts[k]] if v]
    if src == "photos":
        numbers = [{"key": "posts", "value": counts["posts"], "label": "photos"}] + \
                  ([{"key": "reels", "value": counts["reels"], "label": "videos"}] if counts["reels"] else [])

    # every month of the window the data covers
    keys = sorted({key(r["ts"]) for r in d["posts"] + d["reels"] + d["stories"] if r.get("ts")} | {mo["key"]})
    months = []
    for k in keys:
        y, m = map(int, k.split("-"))
        sel = lambda rows: [r for r in rows if r.get("ts") and key(r["ts"]) == k]
        pm, rm, sm = sel(d["posts"]), sel(d["reels"]), sel(d["stories"])
        months.append({"key": k, "month": m, "year": y, "name": calendar.month_name[m], "posts": len(pm), "reels": len(rm),
                       "stories": len(sm), "total": len(pm) + len(rm) + len(sm), "posting_days": rhythm(pm + rm + sm)["posting_days"],
                       "is_month": k == mo["key"]})
    before = [x for x in months if not x["is_month"]]
    avg = lambda f: round(statistics.mean(f(x) for x in before), 1) if before else None
    usual = {"posts": avg(lambda x: x["posts"]), "reels": avg(lambda x: x["reels"]), "stories": avg(lambda x: x["stories"]),
             "total": avg(lambda x: x["total"]), "posting_days": avg(lambda x: x["posting_days"]), "months": len(before)}

    handle = (d.get("handle") or "").lower()
    mentions = Counter(a.lower() for p in posts + reels for a in re.findall(r"@([A-Za-z0-9._]{2,30}[A-Za-z0-9_])", p.get("caption") or ""))
    commented = Counter(c["account"] for c in inm(d["comments"]) if c.get("account"))
    people = sorted(({"account": a, "comments": commented.get(a, 0), "mentions": mentions.get(a, 0),
                      "total": commented.get(a, 0) + mentions.get(a, 0)} for a in set(mentions) | set(commented) if a and a.lower() != handle),
                    key=lambda r: (-r["total"], r["account"]))
    liked = Counter(x["account"] for x in inm(d["likes"]) if x.get("account") and x["account"].lower() != handle)
    loved = [{"account": a, "likes": n} for a, n in sorted(liked.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]
    caps = [p["caption"] for p in posts + reels if p.get("caption")]
    rest = [p["caption"] for p in d["posts"] + d["reels"] if p.get("caption") and key(p["ts"]) != mo["key"]]
    weeks = mo["days"] / 7
    posted = len(posts) + len(reels)
    cad = {**rhythm(posts + reels + stories), "posts_per_week": round(posted / weeks, 1),
           "usual_posts_per_week": round(usual["posts"] / (30.4 / 7), 1) if usual["posts"] is not None else None}
    out = {"handle": d["handle"], "name": d.get("name"), "year": mo["year"], "month": mo, "window": d.get("window"), "source": src,
           "range": d["range"], "counts": counts, "numbers": numbers, "cadence": cad, "usual": usual, "months": months,
           "people": people[:5], "loved": loved, "register": register(caps), "register_year": register(rest)}
    _env.write_json(run / "stats.json", out)
    print(f"@{d['handle']} {mo['name']} {mo['year']}: " + ", ".join(f"{n['value']} {n['label']}" for n in numbers))
    print(f"cadence: {cad['posts_per_week']} posts a week (usually {cad['usual_posts_per_week']}); {cad['posting_days']} posting days, "
          f"longest run {cad['longest_run_days']}")
    print("people: " + ", ".join(f"@{p['account']} {p['total']}" for p in people[:5]))
    print(f"wrote {run / 'stats.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
