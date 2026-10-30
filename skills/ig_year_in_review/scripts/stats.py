#!/usr/bin/env python3
"""Movement 1, research: what the export holds. Reads build/library.json, writes build/stats.json.

USAGE (from the workspace root):
    python3 S/scripts/stats.py

What the data carries (posts, reels, stories, likes given, comments written, new followers; each null when the
data lacks it), every month's photographs, the people (accounts commented on and @mentioned most), the accounts
liked most, and the person's caption register (lowercase, emoji, length, hashtags, sample captions) for writing
copy in their voice. The film shows none of these counts: they tell research what the export holds.
"""
import calendar
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")


def when(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    d = _env.read_json("build/library.json")
    if not d:
        sys.exit("build/library.json is missing: run gather.py first")
    year, src = d["year"], d["source"]
    exp = src == "export"
    posts, reels, stories = d["posts"], d["reels"], d["stories"]
    has = lambda k: bool(d["found"].get(k)) if exp else False
    new_f = [f for f in d["followers"] if f.get("ts") and when(f["ts"]).year == year]
    counts = {
        "posts": len(posts),
        "reels": len(reels) if (has("reels") or reels) else None,
        "stories": len(stories) if has("stories") else None,
        "likes_given": len(d["likes"]) if has("likes") else None,
        "comments_written": len(d["comments"]) if has("comments") else None,
        "new_followers": len(new_f) if has("followers") else None,
        "photos": sum(len([m for m in p["media"] if Path(m).suffix.lower() not in (".mp4", ".mov")]) for p in posts),
    }

    last_month = when(max([p["ts"] for p in posts + reels + stories] or [dt.datetime(year, 12, 31).timestamp()])).month
    months = []
    for m in range(1, last_month + 1):
        inm = lambda rows: [r for r in rows if when(r["ts"]).month == m]
        pm = inm(posts)
        months.append({"month": m, "name": calendar.month_name[m], "posts": len(pm), "reels": len(inm(reels)),
                       "stories": len(inm(stories)), "photos": [x for p in pm for x in p["media"]
                                                                if Path(x).suffix.lower() not in (".mp4", ".mov")]})

    mentions = Counter(a.lower() for p in posts for a in re.findall(r"@([A-Za-z0-9._]{2,30}[A-Za-z0-9_])", p["caption"]))
    commented = Counter(c["account"] for c in d["comments"] if c.get("account"))
    handle = (d.get("handle") or "").lower()
    people = []
    for acct in set(mentions) | set(commented):
        if acct and acct.lower() != handle:
            people.append({"account": acct, "comments": commented.get(acct, 0), "mentions": mentions.get(acct, 0),
                           "total": commented.get(acct, 0) + mentions.get(acct, 0)})
    people.sort(key=lambda r: (-r["total"], r["account"]))
    liked = Counter(x["account"] for x in d["likes"] if x.get("account") and x["account"].lower() != handle)
    loved = [{"account": a, "likes": n} for a, n in sorted(liked.items(), key=lambda kv: (-kv[1], kv[0]))[:5]]

    caps = [p["caption"] for p in posts + reels if p.get("caption")]
    words = [len(c.split()) for c in caps]
    letters = [c for c in caps if re.search(r"[A-Za-z]", c)]
    tags = Counter(t.lower() for c in caps for t in re.findall(r"#\w+", c))
    emo = Counter(e for c in caps for e in EMOJI_RE.findall(c))
    step = max(1, len(caps) // 8)
    register = {
        "captions": len(caps),
        "lowercase_share": round(sum(1 for c in letters if c == c.lower()) / len(letters), 2) if letters else None,
        "emoji_per_caption": round(sum(emo.values()) / len(caps), 2) if caps else 0,
        "avg_words": round(sum(words) / len(words), 1) if words else 0,
        "top_hashtags": [t for t, _ in tags.most_common(6)],
        "top_emoji": [e for e, _ in emo.most_common(4)],
        "samples": caps[::step][:8],
    }
    out = {"handle": d["handle"], "name": d.get("name"), "year": year, "source": src, "range": d["range"],
           "counts": counts, "months": months, "people": people[:5], "loved": loved, "register": register}
    _env.write_json("build/stats.json", out)
    print(f"{'@' + d['handle'] if d['handle'] else 'no handle'} {year}: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in counts.items() if v is not None))
    print("people: " + ", ".join(f"@{p['account']} {p['total']}" for p in people[:5]))
    print("loved: " + ", ".join(f"@{p['account']} {p['likes']}" for p in loved))
    print(f"register: lowercase {register['lowercase_share']}, emoji/caption {register['emoji_per_caption']}, "
          f"avg words {register['avg_words']}, hashtags {register['top_hashtags'][:3]}")
    print("wrote build/stats.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
