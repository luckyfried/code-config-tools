#!/usr/bin/env python3
"""Movement 1, research: who the person spent the year with. Reads build/library.json, writes build/people.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/people.py [--top 5] [--people dani.reyes,theo.makes,...]

The person's own words win: --people (or build/people.txt, one handle per line) names the people and their order,
and the counts only fill in their details. Otherwise every account the person interacts with is counted into one
order, each signal once:
    tagged or @mentioned in a post or reel of theirs     2 per post
    tagged or @mentioned in a story of theirs            1 per story
    a post of that account's that tags the person        2 per post
    a comment that account wrote on the person's posts   1.5 per comment
    a comment the person wrote on that account's posts,
      or a reply of theirs that @mentions it             1 per comment
Ties go to the more photos together (posts of either that tag both), then the handle. No single signal decides:
people.json also records the order each signal alone would give, so the brief can show why it counts them all.

For each person: the score and every signal, the photos they are in, the months they appear in (their stretch of
the year is the months where they lead everyone else in the list), their best line (the comment of theirs with the
most specific words at a readable length, with a bonus when the person replied to it; with no comments, the
person's own caption about them), up to three other lines, their voice (length, capitals, emoji, "we"), and up to
three exchanges (their comment, the person's reply). Also the caption register (case, emoji, length) for copy
written in the person's voice. Every number a card shows comes from this file.
"""
import argparse
import calendar
import collections
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
MENTION = re.compile(r"@([A-Za-z0-9._]{1,30}[A-Za-z0-9_])")
WEIGHTS = {"her_tags": 2, "story_tags": 1, "tags_of_her": 2, "their_comments": 1.5, "her_comments": 1}
STOP = set("""a an and are as at be but by for from had has have i i'm im in is it it's its just me my of on or our so
that the then this to too was we were what when with you your yours us out up all one more very really here there like""".split())
GENERIC = {"obsessed", "love", "lovely", "amazing", "wow", "omg", "yes", "nice", "beautiful", "gorgeous", "stunning",
           "cute", "goals", "same", "mood", "hungry", "now", "ok", "okay", "lol", "haha"}


def month(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).month


def mentions(text):
    return {m.lower().rstrip(".") for m in MENTION.findall(text or "")}


def words(text):
    return re.findall(r"[a-z][a-z']+", (text or "").lower())


def line_score(text, replied):
    """How good a comment is on screen: specific words at a readable length; a reply from the person adds to it."""
    w = words(EMOJI_RE.sub("", text))
    n = len(w)
    if n < 3:
        return -5.0
    specific = [x for x in w if x not in STOP and x not in GENERIC and len(x) >= 4]
    fit = 1.0 if 6 <= n <= 18 else 0.4 if n <= 24 else -1.0
    return round(len(set(specific)) + 2 * fit + (2.5 if replied else 0) - (1.5 if not specific else 0), 2)


def clean(text):
    t = MENTION.sub("", text or "")
    t = re.sub(r"#\w+", "", t)
    return re.sub(r"\s+", " ", t).strip(" ,.-")


def voice(lines):
    if not lines:
        return {"comments": 0, "describe": "never comments; present in the photos"}
    n = len(lines)
    caps = sum(1 for t in lines if re.search(r"\b[A-Z]{3,}\b", t)) / n
    emo = sum(len(EMOJI_RE.findall(t)) for t in lines) / n
    avg = sum(len(t.split()) for t in lines) / n
    we = sum(1 for t in lines if re.search(r"\b(we|our|us)\b", t.lower())) / n
    top = collections.Counter(x for t in lines for x in words(t) if x not in STOP and x not in GENERIC and len(x) >= 4)
    d = []
    if caps >= 0.25:
        d.append("loud, in capitals")
    if emo >= 0.4:
        d.append("emoji")
    if we >= 0.4:
        d.append('speaks as "we"')
    if avg >= 11:
        d.append("long, slow sentences")
    elif avg <= 5:
        d.append("short and dry")
    if not d:
        d.append("plain and precise")
    if top:
        d.append("their words: " + ", ".join(w for w, _ in top.most_common(3)))
    return {"comments": n, "avg_words": round(avg, 1), "capitals": round(caps, 2), "emoji": round(emo, 2), "we": round(we, 2),
            "words": [w for w, _ in top.most_common(6)], "describe": ", ".join(d)}


def span_label(ms):
    names = [calendar.month_name[m].lower() for m in ms]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if ms == list(range(ms[0], ms[-1] + 1)):
        return f"{names[0]} to {names[-1]}" if len(names) > 2 else f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + " and " + names[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=5, help="how many people when the person named none (default 5)")
    ap.add_argument("--people", help="the person's own list, comma separated, in their order")
    a = ap.parse_args()
    d = _env.read_json("build/library.json")
    if not d:
        sys.exit("build/library.json is missing: run gather.py first")
    me = (d.get("handle") or "").lower()
    sig = collections.defaultdict(collections.Counter)
    when = collections.defaultdict(collections.Counter)
    together = collections.defaultdict(list)
    caption_lines = collections.defaultdict(list)

    def add(acct, key, ts, n=1):
        acct = (acct or "").lower().lstrip("@")
        if not acct or acct == me:
            return
        sig[acct][key] += n
        if ts:
            when[acct][month(ts)] += WEIGHTS[key] * n

    def photo(r, kind, owner, who):
        return {"src": r["media"][0], "ts": r["ts"], "kind": kind, "caption": r.get("caption") or "", "with": sorted(who), "owner": owner}

    for kind, rows in (("post", d["posts"]), ("reel", d["reels"])):
        for r in rows:
            who = {x.lower() for x in (r.get("tagged") or [])} | mentions(r.get("caption"))
            who.discard(me)
            for acct in who:
                add(acct, "her_tags", r.get("ts"))
                if r.get("media"):
                    together[acct].append(photo(r, kind, me, who - {acct}))
                if acct in mentions(r.get("caption")) and clean(r.get("caption")):
                    caption_lines[acct].append(clean(r["caption"]))
    for r in d["stories"]:
        for acct in {x.lower() for x in (r.get("tagged") or [])} | mentions(r.get("caption")):
            add(acct, "story_tags", r.get("ts"))
    for r in d.get("tagged_in", []):
        owner = (r.get("account") or "").lower()
        who = ({x.lower() for x in (r.get("tagged") or [])} | {owner}) - {me, ""}
        add(owner, "tags_of_her", r.get("ts"))
        if r.get("media"):
            for acct in who:
                together[acct].append(photo(r, "tagged", owner, who - {acct}))
    replies = collections.defaultdict(list)
    for c in d["comments"]:
        if c.get("account") and c["account"] != me:
            add(c["account"], "her_comments", c.get("ts"))
        elif c.get("account") == me:
            for acct in mentions(c.get("text")):
                add(acct, "her_comments", c.get("ts"))
                replies[acct].append(c)
    said = collections.defaultdict(list)
    for c in d.get("received", []):
        if c.get("account") and c["account"] != me:
            add(c["account"], "their_comments", c.get("ts"))
            said[c["account"]].append(c)

    def score(acct):
        return round(sum(WEIGHTS[k] * v for k, v in sig[acct].items()), 1)

    allp = sorted(sig, key=lambda x: (-score(x), -len(together[x]), x))
    named = a.people or (Path("build/people.txt").read_text() if Path("build/people.txt").exists() else "")
    named = [x.strip().lstrip("@").lower() for x in re.split(r"[,\n]", named) if x.strip()]
    chosen = named or allp[:a.top]
    ranked_by = "the person's own list" if named else "tags, mentions, comments both ways, and their posts of the person, each counted once"

    owner = {}
    for m in range(1, 13):
        best = max(chosen, key=lambda x: when[x][m]) if chosen else None
        if best and when[best][m] >= 2:
            owner[m] = best
    out_people = []
    for i, acct in enumerate(chosen):
        runs, cur = [], []
        for m in sorted(m for m, o in owner.items() if o == acct):
            if cur and m == cur[-1] + 1:
                cur.append(m)
            else:
                cur = [m]
                runs.append(cur)
        stretch = max(runs, key=len) if runs else ([when[acct].most_common(1)[0][0]] if when[acct] else [])
        def reply_to(c):
            same = [r for r in replies[acct] if r.get("on") and r.get("on") == c.get("on")]
            return next((r for r in same or replies[acct] if 0 <= (r.get("ts") or 0) - (c.get("ts") or 0) < 2 * 86400), None)
        cands = []
        for c in said[acct]:
            rep = reply_to(c) is not None
            cands.append({"text": c["text"].strip(), "score": line_score(c["text"], rep), "replied": rep, "ts": c.get("ts"),
                          "from": "their comment"})
        cands.sort(key=lambda x: (-x["score"], len(x["text"])))
        uniq = []
        for c in cands:
            if c["text"] not in [u["text"] for u in uniq]:
                uniq.append(c)
        if not uniq:
            caps = sorted(set(caption_lines[acct]), key=lambda t: (-line_score(t, False), len(t)))
            uniq = [{"text": t, "score": line_score(t, False), "replied": False, "ts": None, "from": "her caption"} for t in caps]
        ex = []
        for c in said[acct]:
            r = reply_to(c)
            if r and c["text"] not in [e["they"] for e in ex]:
                ex.append({"they": c["text"], "she": r["text"]})
        photos = sorted(together[acct], key=lambda p: p["ts"])
        out_people.append({
            "rank": i + 1, "handle": acct, "score": score(acct), "signals": {k: sig[acct].get(k, 0) for k in WEIGHTS},
            "photos_together": len({p["src"] for p in photos}), "photos": photos,
            "months": {calendar.month_name[m].lower(): round(when[acct][m], 1) for m in sorted(when[acct])},
            "stretch": {"months": stretch, "label": span_label(stretch)},
            "line": uniq[0] if uniq else None, "lines": uniq[1:4], "voice": voice([c["text"] for c in said[acct]]),
            "exchanges": ex[:3]})
    alone = {"tags_only": sorted(sig, key=lambda x: (-(sig[x]["her_tags"] + sig[x]["tags_of_her"]), x))[:a.top],
             "comments_only": sorted(sig, key=lambda x: (-(sig[x]["their_comments"] + sig[x]["her_comments"]), x))[:a.top]}
    nxt = [{"handle": x, "score": score(x)} for x in allp if x not in chosen][:3]

    caps = [p["caption"] for p in d["posts"] + d["reels"] if p.get("caption")]
    letters = [c for c in caps if re.search(r"[A-Za-z]", c)]
    emo = collections.Counter(e for c in caps for e in EMOJI_RE.findall(c))
    tags = collections.Counter(t.lower() for c in caps for t in re.findall(r"#\w+", c))
    register = {"captions": len(caps),
                "lowercase_share": round(sum(1 for c in letters if c == c.lower()) / len(letters), 2) if letters else None,
                "emoji_per_caption": round(sum(emo.values()) / len(caps), 2) if caps else 0,
                "avg_words": round(sum(len(c.split()) for c in caps) / len(caps), 1) if caps else 0,
                "top_hashtags": [t for t, _ in tags.most_common(6)], "top_emoji": [e for e, _ in emo.most_common(4)]}
    counts = {k: len(d.get(k) or []) for k in ("posts", "reels", "stories", "tagged_in", "comments", "received")}
    out = {"handle": d["handle"], "name": d.get("name"), "year": d["year"], "source": d["source"], "range": d["range"],
           "counts": counts, "ranked_by": ranked_by, "named": bool(named), "weights": WEIGHTS, "people": out_people,
           "next": nxt, "single_signal": alone,
           "eras": [{"month": calendar.month_name[m].lower(), "owner": o} for m, o in sorted(owner.items())],
           "register": register}
    if not out_people:
        out["note"] = "no account was tagged, mentioned or commented on in the data; name the people with --people"
    _env.write_json("build/people.json", out)
    print(f"@{d['handle']} {d['year']}: ranked by {ranked_by}")
    for p in out_people:
        s = p["signals"]
        print(f"  {p['rank']}. @{p['handle']:<16} {p['score']:>6.1f}  tags {s['her_tags']}+{s['story_tags']}, of her {s['tags_of_her']}, "
              f"comments {s['their_comments']}/{s['her_comments']}, photos {p['photos_together']}, stretch {p['stretch']['label'] or '-'}")
        if p["line"]:
            print(f"       line ({p['line']['from']}): {p['line']['text']}")
    print("next: " + ", ".join(f"@{x['handle']} {x['score']}" for x in nxt))
    print("tags alone: " + ", ".join(alone["tags_only"]) + "   comments alone: " + ", ".join(alone["comments_only"]))
    print("wrote build/people.json")
    return 0 if out_people else 1


if __name__ == "__main__":
    sys.exit(main())
