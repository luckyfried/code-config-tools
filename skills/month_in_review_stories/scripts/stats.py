#!/usr/bin/env python3
"""Movement 1, research: the numbers of the month and of the year it is measured against. Reads build/library.json,
writes build/stats.json.

USAGE (from the workspace root):
    python3 S/scripts/stats.py

The month: posts, reels, stories, likes given, comments written and new followers (each null when the data lacks
it), posting days, posts a week, the weekday they posted most, the longest run of days in a row, and the three best
moments by their own numbers: the month's three most-liked posts and reels, ties broken by comments, then by the more
recent (by comments alone, or by photo quality later in picks.py, when the data has no likes per post), each with
how many times their usual likes it got. The year: the same counts for every month of the twelve months that end
with the month (only the months the data covers), the average month before it, the month's rank among them, the
year's median post, the year's most-liked post and where the month's best sits against it. Also the people of the
month (accounts commented on and @mentioned most), the accounts liked most that month, and the caption register of
the month and of the rest of the year, for writing copy in their voice. Every number a card shows comes from this
file.
"""
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


def label(ts):
    d = when(ts)
    return f"{calendar.month_name[d.month]} {d.day}"


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
    d = _env.read_json("build/library.json")
    if not d or not d.get("month"):
        sys.exit("build/library.json is missing or names no month: run gather.py first")
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

    # the year: every month of the window the data covers
    keys = sorted({key(r["ts"]) for r in d["posts"] + d["reels"] + d["stories"] if r.get("ts")} | {mo["key"]})
    months = []
    for k in keys:
        y, m = map(int, k.split("-"))
        sel = lambda rows: [r for r in rows if r.get("ts") and key(r["ts"]) == k]
        pm, rm, sm = sel(d["posts"]), sel(d["reels"]), sel(d["stories"])
        likes = [p["likes"] for p in pm + rm if p.get("likes") is not None]
        months.append({"key": k, "month": m, "year": y, "name": calendar.month_name[m], "posts": len(pm), "reels": len(rm),
                       "stories": len(sm), "total": len(pm) + len(rm) + len(sm), "posting_days": rhythm(pm + rm + sm)["posting_days"],
                       "likes_median": statistics.median(likes) if likes else None, "is_month": k == mo["key"]})
    before = [x for x in months if not x["is_month"]]
    avg = lambda f: round(statistics.mean(f(x) for x in before), 1) if before else None
    usual = {"posts": avg(lambda x: x["posts"]), "reels": avg(lambda x: x["reels"]), "stories": avg(lambda x: x["stories"]),
             "total": avg(lambda x: x["total"]), "posting_days": avg(lambda x: x["posting_days"]), "months": len(before)}
    cur = next(x for x in months if x["is_month"])
    by_posts = sorted(months, key=lambda x: (-x["posts"], -x["total"]))
    rank = by_posts.index(cur) + 1
    busiest = by_posts[0] if months else None
    quietest = by_posts[-1] if months else None

    rows = [dict(p, kind="post") for p in posts if p["media"]] + [dict(r, kind="reel") for r in reels if r["media"]]
    if any(p.get("likes") is not None for p in rows):
        ranked, by = sorted(rows, key=lambda p: (-(p.get("likes") or 0), -(p.get("comments") or 0), -p["ts"])), "likes"
    elif any(p.get("comments") for p in rows):
        ranked, by = sorted(rows, key=lambda p: (-(p.get("comments") or 0), -p["ts"])), "comments"
    else:
        ranked, by = sorted(rows, key=lambda p: -p["ts"]), "photo quality (picks.py)"
    year_rows = [p for p in d["posts"] + d["reels"] if p.get("likes") is not None and key(p["ts"]) != mo["key"]]
    median = statistics.median(p["likes"] for p in year_rows) if year_rows else None
    month_likes = [p["likes"] for p in rows if p.get("likes") is not None]
    top = []
    for i, p in enumerate(ranked[:3]):
        media = p["media"][0]
        top.append({"rank": i + 1, "kind": p["kind"], "ts": p["ts"], "date": when(p["ts"]).date().isoformat(), "date_label": label(p["ts"]),
                    "likes": p.get("likes"), "comments": p.get("comments"), "caption": p.get("caption") or "", "media": media,
                    "video": media if Path(media).suffix.lower() in VIDEO else None,
                    "times_usual": round(p["likes"] / median, 1) if median and p.get("likes") is not None else None})
    year_best = max(year_rows, key=lambda p: (p["likes"], p.get("comments") or 0), default=None)
    fourth = ranked[3] if len(ranked) > 3 else None
    against = {
        "year_best_likes": year_best["likes"] if year_best else None,
        "year_best_date": when(year_best["ts"]).date().isoformat() if year_best else None,
        "beats_year_best": sum(1 for t in top if year_best and t.get("likes") is not None and t["likes"] > year_best["likes"]),
        "fourth_likes": fourth.get("likes") if fourth else None,
        "gap_to_fourth": (top[-1]["likes"] - fourth["likes"]) if top and fourth and top[-1].get("likes") is not None and fourth.get("likes") is not None else None,
        "month_median_likes": statistics.median(month_likes) if month_likes else None,
        "year_median_likes": median,
    }

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
    cad = {**rhythm(posts + reels + stories), "posts_per_week": round(len(posts) / weeks, 1),
           "usual_posts_per_week": round(usual["posts"] / (30.4 / 7), 1) if usual["posts"] is not None else None,
           "vs_usual": round(len(posts) / usual["posts"], 1) if usual["posts"] else None, "rank_by_posts": rank, "of_months": len(months)}
    out = {"handle": d["handle"], "name": d.get("name"), "year": mo["year"], "month": mo, "window": d.get("window"), "source": src,
           "range": d["range"], "counts": counts, "numbers": numbers, "cadence": cad, "usual": usual, "months": months,
           "busiest": busiest, "quietest": quietest, "top_three": top, "top_ranked_by": by, "against": against,
           "median_likes": median, "people": people[:5], "loved": loved, "register": register(caps), "register_year": register(rest)}
    _env.write_json("build/stats.json", out)
    print(f"@{d['handle']} {mo['name']} {mo['year']}: " + ", ".join(f"{n['value']} {n['label']}" for n in numbers))
    print(f"cadence: {cad['posts_per_week']} posts a week (usually {cad['usual_posts_per_week']}), {cad['vs_usual']}x the usual month, "
          f"#{rank} of {len(months)} months by posts; {cad['posting_days']} posting days, longest run {cad['longest_run_days']}")
    print("best three (by %s): " % by + "; ".join(f"{t['rank']}. {t['date_label']} {t['kind']} {t['likes'] if t['likes'] is not None else ''}"
                                                  f"{' (' + str(t['times_usual']) + 'x usual)' if t['times_usual'] else ''}" for t in top))
    print(f"against the year: best before {against['year_best_likes']} likes; {against['beats_year_best']} of the three beat it; "
          f"the fourth sits {against['gap_to_fourth']} below the third")
    print("people: " + ", ".join(f"@{p['account']} {p['total']}" for p in people[:5]))
    print("wrote build/stats.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
