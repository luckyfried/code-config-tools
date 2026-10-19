#!/usr/bin/env python3
"""Movement 1, research: the numbers. Reads build/library.json, writes build/stats.json.

USAGE (from the workspace root):
    python3 S/scripts/stats.py

Counts (posts, reels, stories, likes given, comments written, new followers; each null when the data lacks it),
the audience's response: every post and reel scored by the comments and saves it drew (comments alone when the data
has no saves; likes when it has neither), the nine that drew the most as "top", each with its hook (the caption's
opening line) and the hook's style (question, confession, list or statement), the styles ranked by the mean
response of their posts, the median post's response and likes, the posts that already mention the product, every
month's activity, the people (accounts commented on and @mentioned most), the accounts liked most, and the
person's caption register (lowercase, emoji, length, hashtags, sample captions) for writing copy in their voice.
Every number the film, the cards or the brief show comes from this file.
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


def label(ts):
    d = when(ts)
    return f"{calendar.month_name[d.month]} {d.day}"


HOOK_END = re.compile(r"(?<=[?!.:;])\s|\s[-\u2013\u2014]\s|\n")
CONFESS = ("confession", "honestly", "i almost", "i never", "truth", "i have to admit", "not gonna lie", "can i be honest",
           "real talk", "i've been", "ive been", "i was scared", "secret")
ASK = ("would", "what", "which", "who", "how", "why", "do", "does", "did", "is", "are", "can", "could", "have", "ever",
       "where", "when", "should", "will", "anyone")
NUMBER = re.compile(r"^(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b")


def hook_of(cap):
    """The caption's opening line: up to its first sentence end, colon or line break, without hashtags or emoji."""
    c = EMOJI_RE.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    h = next((c[:m.start()] for m in HOOK_END.finditer(c) if len(c[:m.start()].split()) >= 3), c)
    return re.sub(r"\s+", " ", h).strip(" ,;.:")[:110]


def style_of(hook):
    h = (hook or "").lower().strip()
    if not h:
        return "statement"
    if h.endswith("?") or h.split()[0] in ASK and "?" in h:
        return "question"
    if h.startswith(CONFESS) or any(w in h for w in ("confession", "in secret", "almost didn't")):
        return "confession"
    if NUMBER.match(h):
        return "list"
    return "statement"


def names_product(text, product):
    if not product or not text:
        return False
    t = re.sub(r"[^a-z0-9]+", " ", text.lower())
    p = re.sub(r"[^a-z0-9]+", " ", product.lower()).strip()
    return f" {p} " in f" {t} " or f" {p.replace(' ', '')} " in f" {t} "


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
    numbers = [(k, v, lab) for k, lab in (("posts", "posts"), ("reels", "reels"), ("stories", "stories"),
                                           ("likes_given", "likes given"), ("comments_written", "comments written"),
                                           ("new_followers", "new followers"))
               for v in [counts[k]] if v]
    if src == "photos":
        numbers = [("posts", counts["posts"], "photos")] + ([("reels", counts["reels"], "videos")] if counts["reels"] else [])

    rows = [dict(p, kind="post") for p in posts if p["media"]] + [dict(r, kind="reel") for r in reels if r["media"]]
    saves = any(p.get("saves") is not None for p in rows)
    comments = any(p.get("comments") is not None for p in rows)
    if comments or saves:
        by = "comments and saves" if saves and comments else "saves" if saves else "comments"
        score = lambda p: (p.get("comments") or 0) + (p.get("saves") or 0)
    else:
        by = "likes"
        score = lambda p: p.get("likes") or 0
    ranked = sorted(rows, key=lambda p: (-score(p), -(p.get("likes") or 0), -p["ts"]))
    product = (d.get("launch") or {}).get("product") or ""
    top = []
    for i, p in enumerate(ranked[:9]):
        cap = p.get("caption") or ""
        h = hook_of(cap)
        top.append({"rank": i + 1, "kind": p["kind"], "ts": p["ts"], "date": when(p["ts"]).date().isoformat(),
                    "date_label": label(p["ts"]), "month": when(p["ts"]).month, "response": score(p),
                    "likes": p.get("likes"), "comments": p.get("comments"), "saves": p.get("saves"), "caption": cap,
                    "hook": h, "style": style_of(h), "mentions_product": names_product(cap, product),
                    "media": p["media"][0], "video": p["media"][0] if Path(p["media"][0]).suffix.lower() in (".mp4", ".mov", ".m4v") else None})
    resp = sorted(score(p) for p in rows)
    like_counts = sorted(p["likes"] for p in rows if p.get("likes") is not None)
    styles = {}
    for p in rows:
        styles.setdefault(style_of(hook_of(p.get("caption") or "")), []).append(score(p))
    top_styles = {}
    for t in top:
        top_styles.setdefault(t["style"], []).append(t["response"])
    hook_styles = sorted(({"style": k, "in_top": len(v), "mean_response": round(sum(v) / len(v)),
                           "posts": len(styles.get(k, [])), "mean_response_all": round(sum(styles[k]) / len(styles[k]))}
                          for k, v in top_styles.items()), key=lambda r: (-r["in_top"] * r["mean_response"], -r["mean_response"]))
    about = [{"date": when(p["ts"]).date().isoformat(), "kind": p["kind"], "response": score(p), "likes": p.get("likes"),
              "caption": p.get("caption") or "", "media": p["media"][0]} for p in ranked if names_product(p.get("caption"), product)]

    last_month = when(max([p["ts"] for p in posts + reels + stories] or [dt.datetime(year, 12, 31).timestamp()])).month
    months = []
    for m in range(1, last_month + 1):
        inm = lambda rows: [r for r in rows if when(r["ts"]).month == m]
        pm = inm(posts)
        months.append({"month": m, "name": calendar.month_name[m], "posts": len(pm), "reels": len(inm(reels)),
                       "stories": len(inm(stories)), "photos": [x for p in pm for x in p["media"]
                                                                if Path(x).suffix.lower() not in (".mp4", ".mov")]})
    for mo in months:
        mo["total"] = mo["posts"] + mo["reels"] + mo["stories"]
    busiest = max(months, key=lambda m: (m["posts"], m["total"])) if months else None
    quietest = min(months, key=lambda m: (m["posts"], m["total"])) if months else None

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
           "counts": counts, "numbers": [{"key": k, "value": v, "label": lab} for k, v, lab in numbers],
           "top": top, "ranked_by": by, "hook_styles": hook_styles, "product_posts": about,
           "median_response": resp[len(resp) // 2] if resp else None,
           "median_likes": like_counts[len(like_counts) // 2] if like_counts else None, "months": months, "busiest": busiest, "quietest": quietest,
           "people": people[:5], "loved": loved, "register": register}
    _env.write_json("build/stats.json", out)
    print(f"@{d['handle']} {year}: " + ", ".join(f"{v} {lab}" for _, v, lab in numbers))
    print(f"response (by {by}), median {out['median_response']}; the hooks that drew the most:")
    for t in top:
        print(f"  {t['rank']}. {t['response']:>4} {t['style']:<10} {t['hook']}")
    print("hook styles: " + ", ".join(f"{h['style']} {h['in_top']} in the top, mean {h['mean_response']}" for h in hook_styles))
    print(f"{len(about)} posts already mention {product or 'the product'}")
    if busiest:
        print(f"busiest {busiest['name']} ({busiest['posts']} posts), quietest {quietest['name']} ({quietest['posts']} posts)")
    print("people: " + ", ".join(f"@{p['account']} {p['total']}" for p in people[:5]))
    print("loved: " + ", ".join(f"@{p['account']} {p['likes']}" for p in loved))
    print(f"register: lowercase {register['lowercase_share']}, emoji/caption {register['emoji_per_caption']}, "
          f"avg words {register['avg_words']}, hashtags {register['top_hashtags'][:3]}")
    print("wrote build/stats.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
