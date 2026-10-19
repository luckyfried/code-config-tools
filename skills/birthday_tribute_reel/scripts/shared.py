#!/usr/bin/env python3
"""Movement 1, research: who the video is for, and everything the two share. Reads build/library.json, writes
build/ask.json (what the person said) and build/shared.json.

USAGE (from the workspace root):
    python3 S/scripts/shared.py --who "@dani.reyes" [--occasion "her 30th birthday"] [--date 2026-10-24] \\
        [--words "my favorite travel partner, always late, always worth it"]

--who is the person's own words for the one the video is for: a handle, a name ("Dani", "my mom, Ana Okafor") or
"us". It is saved in build/ask.json, so later runs may leave it out. The person's words win: an exact handle
is taken as it is; a name is matched against every account in the data (tagged in their posts, reels and stories,
@mentioned or named in captions, the owners of posts they comment on, the authors in a saved feed's threads, the
name on a saved feed); "us", "my partner", "my husband" and the like, or no --who at all, take the account they
share the most photos with, and that choice is written down as an assumption. The runner-up and the account they
talk to most are recorded too, so the brief can say why it is this one and not the other.

--occasion and --date are the person's words for the occasion; without them the occasion is read from their
captions about the named one ("turns 30 on october 24", "happy birthday", "five years"), and failing that it is
"a tribute". --words is anything else the person said about the named one; those lines lead the love list.

shared.json carries:
  who         handle, name, how it was matched, the person's words, the runner-up, the most frequent account
  occasion    kind (birthday, anniversary, tribute), age or years when known, the date, a plain label, where it came from
  items       every post, reel and story the two share (tagged, @mentioned or named), and the named one's own posts
              that tag the person, oldest first, each with its media, caption, date, place and how it counts as shared
  videos      the clips among them; first and latest: the first photo together and the latest
  exchanges   every comment the two traded (the person's comments on their posts, both sides of the threads on
              their saved feed), oldest first; pairs: a line and the answer under the same post
  voice       for each side: how many lines, words a line, capitals, exclamation marks, emoji, samples
  eras        the friendship in at most six chapters (a place, or a run of months), each with its items
  love_lines  the person's own lines about or to the named one (3 to 9 words, cleaned), "you" lines first
  counts      the numbers above in one place
"""
import argparse
import collections
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PLACES = ["lisbon", "porto", "oaxaca", "sicily", "palermo", "marrakech", "paris", "rome", "london", "tokyo", "mexico city",
          "new york", "berlin", "barcelona", "madrid", "athens", "istanbul", "kyoto", "seoul", "bali", "cape town", "naples",
          "florence", "venice", "amsterdam", "copenhagen", "dublin", "edinburgh", "montreal", "chicago", "los angeles"]
US = {"us", "we", "me and", "my partner", "partner", "my husband", "husband", "my wife", "wife", "my boyfriend", "boyfriend",
      "my girlfriend", "girlfriend", "my friend", "friend", "my best friend", "best friend", "bestie", "my love", "babe"}
RELATION = re.compile(r"\b(mom|mum|mother|dad|father|sister|brother|grandma|grandpa|aunt|uncle|son|daughter|wife|husband|"
                      r"partner|boyfriend|girlfriend|friend|bestie|best friend)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]
NUMBERS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                      "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
NUMBERS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90})


def day(ts):
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date().isoformat()


def parts(handle):
    return [p for p in re.split(r"[._\d]+", handle.lower()) if len(p) >= 2]


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def number(word):
    word = word.lower()
    return int(word) if word.isdigit() else NUMBERS.get(word)


def candidates(lib):
    """Every account in the data, with how often it shows up in each way."""
    c = collections.defaultdict(collections.Counter)
    for kind in ("posts", "reels", "stories"):
        for r in lib.get(kind, []):
            for t in r.get("tagged") or []:
                c[t]["tagged"] += 1
            for m in set(re.findall(r"@([\w.]+)", r.get("caption") or "")):
                c[m.lower().rstrip(".")]["mentioned"] += 1
    for r in lib.get("comments", []):
        if r.get("account"):
            c[r["account"].lower()]["commented_on"] += 1
    for h, f in (lib.get("feeds") or {}).items():
        c[h]["saved_feed"] += 1
        for p in f.get("posts", []):
            for x in p.get("thread") or []:
                if x.get("account") and x["account"] != h:
                    c[x["account"]]["in_their_threads"] += 1
    c.pop(lib.get("handle") or "", None)
    return c


def shared_score(n):
    return n["tagged"] * 3 + n["mentioned"] * 2 + n["commented_on"] + n["in_their_threads"]


def resolve(lib, words):
    """The named one from the person's words. Returns (handle, name, matched_by, runner_up, assumptions)."""
    c = candidates(lib)
    feeds = lib.get("feeds") or {}
    names = {h: (f.get("name") or "") for h, f in feeds.items()}
    ranked = sorted(c, key=lambda h: -shared_score(c[h]))
    most_frequent = max(c, key=lambda h: c[h]["commented_on"] + c[h]["in_their_threads"], default=None)
    w = (words or "").strip()
    low = w.lower()
    notes = []
    handle = None
    m = re.search(r"@([\w.]+)", w)
    exact = (m.group(1) if m else low).rstrip(".")
    if exact in c:
        handle, by = exact, "the handle you gave"
    elif m:
        handle, by = exact, "the handle you gave"
        notes.append(f"@{exact} is not tagged or named anywhere in the data, so the video has no shared photos to use.")
    elif w and low not in US and not (RELATION.fullmatch(low.replace("my ", "")) if low else False):
        toks = [t for t in re.findall(r"[a-z]+", low) if t not in {"my", "the", "for", "our", "a", "an"} and not RELATION.fullmatch(t)]
        def score(h):
            hp = parts(h) + [p for p in re.findall(r"[a-z]+", names.get(h, "").lower())]
            return sum(1 for t in toks if t in hp or any(len(t) >= 3 and len(p) >= 4 and (p.startswith(t) or t.startswith(p)) for p in hp))
        hits = sorted((h for h in c if score(h)), key=lambda h: (-score(h), -shared_score(c[h])))
        if hits:
            handle, by = hits[0], f"the name \"{w}\" matched to @{hits[0]}"
            if len(hits) > 1 and score(hits[1]) == score(hits[0]):
                notes.append(f"\"{w}\" also matches @{hits[1]}; @{hits[0]} is used because you share more photos with them.")
        else:
            notes.append(f"\"{w}\" matches no account in the data, so the account you share the most photos with is used.")
    if not handle:
        if not ranked:
            return None, None, "nothing to match", None, most_frequent, ["No account is tagged or named in the data."]
        handle = ranked[0]
        by = (f"\"{w}\" taken as the account you share the most photos with" if w else
              "no one named, so the account you share the most photos with")
        notes.append(f"The video is for @{handle}, the account you share the most photos with; say who it is for to change that.")
    runner = next((h for h in ranked if h != handle), None)
    name = names.get(handle) or ""
    if not name:
        first = parts(handle)[0] if parts(handle) else handle
        name = first.capitalize()
    return handle, name, by, runner, most_frequent, notes


def place_of(text):
    t = (text or "").lower()
    return next((p for p in PLACES if re.search(rf"\b{re.escape(p)}\b", t)), None)


def clean_line(text, handle, first):
    t = re.sub(r"@[\w.]+", "", text or "")
    t = re.sub(r"#\w+", "", t)
    t = EMOJI.sub("", t).replace("️", "")
    t = re.sub(r"\s+", " ", t).strip(" ,.;:-!")
    return t


def occasion_of(ask, captions, first, now):
    """The occasion: the person's words first, then their captions about the named one."""
    words = " ".join(x for x in (ask.get("occasion"), ask.get("who"), ask.get("words")) if x)
    out = {"kind": None, "age": None, "years": None, "date": ask.get("date"), "from": None}
    def read(text):
        t = text.lower()
        k = {}
        m = re.search(r"\bturns? (\d{1,3}|[a-z]+)\b", t) or re.search(r"\b(\d{1,3})(?:st|nd|rd|th)\b(?: birthday)?", t)
        if m and number(m.group(1)) and number(m.group(1)) > 0:
            k.update(kind="birthday", age=number(m.group(1)))
        if re.search(r"\b(birthday|bday|b-day)\b", t):
            k["kind"] = "birthday"
        if re.search(r"\banniversary\b", t) or re.search(r"\b(\d+|[a-z]+) years?\b(?! old)", t) and not k.get("kind"):
            ym = re.search(r"\b(\d+|[a-z]+) years?\b", t)
            if ym and number(ym.group(1)):
                k["years"] = number(ym.group(1))
            k.setdefault("kind", "anniversary")
        dm = re.search(rf"\b({'|'.join(MONTHS)}) (\d{{1,2}})(?:st|nd|rd|th)?\b", t) or \
            re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)? (?:of )?({'|'.join(MONTHS)})\b", t)
        if dm:
            a, b = dm.groups()
            mon, d = (a, b) if a in MONTHS else (b, a)
            yr = now.year if (MONTHS.index(mon) + 1, int(d)) >= (now.month, now.day) else now.year + 1
            try:
                k["date"] = dt.date(yr, MONTHS.index(mon) + 1, int(d)).isoformat()
            except ValueError:
                pass
        return k
    said = read(words) if words else {}
    for key, v in said.items():
        if v and not out.get(key):
            out[key] = v
    if said:
        out["from"] = "your words"
    for cap in captions:
        k = read(cap)
        if not k:
            continue
        filled = False
        for key, v in k.items():
            if v and not out.get(key):
                out[key] = v
                filled = True
        if filled:
            out["from"] = (out["from"] + " and " if out["from"] else "") + f"your caption \"{cap}\""
    if out["kind"] == "birthday" and out["age"]:
        out["label"] = f"{first} turns {out['age']}"
        out["title"] = f"happy {ordinal(out['age'])}, {first.lower()}"
    elif out["kind"] == "birthday":
        out["label"] = f"{first}'s birthday"
        out["title"] = f"happy birthday, {first.lower()}"
    elif out["kind"] == "anniversary" and out["years"]:
        out["label"] = f"{out['years']} years"
        out["title"] = f"{out['years']} years of us"
    elif out["kind"] == "anniversary":
        out["label"] = "our anniversary"
        out["title"] = "happy anniversary"
    else:
        out["kind"] = out["kind"] or "tribute"
        out["label"] = f"for {first}"
        out["title"] = f"for {first.lower()}"
        out["from"] = out["from"] or "no occasion named or found, so a tribute"
    return out


def voice(lines):
    if not lines:
        return {"lines": 0}
    words = [len(x.split()) for x in lines]
    return {"lines": len(lines), "avg_words": round(sum(words) / len(words), 1),
            "capitals": round(sum(1 for x in lines if re.search(r"[A-Z]", x)) / len(lines), 2),
            "exclaims": round(sum(1 for x in lines if "!" in x) / len(lines), 2),
            "questions": round(sum(1 for x in lines if "?" in x) / len(lines), 2),
            "emoji": round(sum(len(EMOJI.findall(x)) for x in lines) / len(lines), 2),
            "lowercase": round(sum(1 for x in lines if x == x.lower()) / len(lines), 2),
            "samples": lines[:6]}


def eras_of(items, limit=6):
    """Chapters of the friendship. An item takes the place in its caption, else the place of the nearest item
    within 7 days that names one; runs of one place (or of none) are the chapters; a run of one item joins the
    neighbor nearest in time, and the smallest runs merge until at most `limit` remain."""
    placed = [x for x in items if x["place"]]
    for x in items:
        x["era_place"] = x["place"] or next((y["place"] for y in sorted(placed, key=lambda y: abs(y["ts"] - x["ts"]))
                                             if abs(y["ts"] - x["ts"]) <= 7 * 86400), None)
    runs = []
    for x in items:
        if runs and runs[-1]["place"] == x["era_place"]:
            runs[-1]["items"].append(x)
        else:
            runs.append({"place": x["era_place"], "items": [x]})

    def merge(i):
        if len(runs) < 2:
            return False
        left = runs[i]["items"][0]["ts"] - runs[i - 1]["items"][-1]["ts"] if i > 0 else None
        right = runs[i + 1]["items"][0]["ts"] - runs[i]["items"][-1]["ts"] if i < len(runs) - 1 else None
        j = i - 1 if right is None or (left is not None and left <= right) else i + 1
        a, b = sorted((i, j))
        big = runs[a] if len(runs[a]["items"]) >= len(runs[b]["items"]) else runs[b]
        runs[a] = {"place": big["place"], "items": runs[a]["items"] + runs[b]["items"]}
        del runs[b]
        return True
    while any(len(r["items"]) == 1 for r in runs) and len(runs) > 1:
        merge(next(i for i, r in enumerate(runs) if len(r["items"]) == 1))
    while len(runs) > limit:
        merge(min(range(len(runs)), key=lambda k: len(runs[k]["items"])))
    k = 1
    while k < len(runs):
        if runs[k]["place"] == runs[k - 1]["place"]:
            runs[k - 1]["items"] += runs.pop(k)["items"]
        else:
            k += 1
    out = []
    for r in runs:
        f, t = day(r["items"][0]["ts"]), day(r["items"][-1]["ts"])
        mf, mt = MONTHS[int(f[5:7]) - 1], MONTHS[int(t[5:7]) - 1]
        span = mf if f[:7] == t[:7] else f"{mf} to {mt}"
        out.append({"label": r["place"] or span, "place": r["place"], "from": f, "to": t, "span": span,
                    "items": [x["id"] for x in r["items"]], "count": len(r["items"])})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--who")
    ap.add_argument("--occasion")
    ap.add_argument("--date", help="the day of the occasion, YYYY-MM-DD")
    ap.add_argument("--words", help="anything else the person said about the named one")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    ask = _env.read_json("build/ask.json") or {}
    for k in ("who", "occasion", "date", "words"):
        if getattr(a, k):
            ask[k] = getattr(a, k)
    _env.write_json("build/ask.json", ask)
    me = (lib.get("handle") or "").lower()
    handle, name, by, runner, frequent, notes = resolve(lib, ask.get("who"))
    if not handle:
        sys.exit("no account is tagged or named in the data; the video needs photos of the two of you")
    first = name.split()[0] if name else handle
    feed = (lib.get("feeds") or {}).get(handle) or {}
    name_re = re.compile(rf"\b{re.escape(first.lower())}('s)?\b") if len(first) >= 3 else None

    items = []
    for kind, one in (("posts", "post"), ("reels", "reel"), ("stories", "story")):
        for i, r in enumerate(lib.get(kind, [])):
            cap = r.get("caption") or ""
            why = []
            if handle in (r.get("tagged") or []):
                why.append("tagged")
            if re.search(rf"@{re.escape(handle)}\b", cap, re.I):
                why.append("mentioned")
            if not why and name_re and name_re.search(cap.lower()):
                why.append("named")
            if why and r.get("media"):
                items.append({"id": f"{one}:{i}", "kind": one, "from": "mine", "ts": r["ts"], "date": day(r["ts"]),
                              "caption": cap, "media": r["media"], "tagged": r.get("tagged") or [], "why": why,
                              "place": place_of(cap) or place_of(r.get("place")),
                              "video": any(Path(m).suffix.lower() in {".mp4", ".mov", ".m4v"} for m in r["media"])})
    for i, r in enumerate(feed.get("posts", [])):
        if me and (me in (r.get("tagged") or []) or re.search(rf"@{re.escape(me)}\b", r.get("caption") or "", re.I)) and r.get("media"):
            items.append({"id": f"feed:{i}", "kind": "post", "from": "theirs", "ts": r["ts"], "date": day(r["ts"]),
                          "caption": r.get("caption") or "", "media": r["media"], "tagged": r.get("tagged") or [],
                          "why": ["their post tagging you"], "place": place_of(r.get("caption")),
                          "video": any(Path(m).suffix.lower() in {".mp4", ".mov", ".m4v"} for m in r["media"])})
    items.sort(key=lambda x: x["ts"])
    photos = [x for x in items if not x["video"]]
    videos = [x for x in items if x["video"]]

    seen, ex = set(), []
    for r in lib.get("comments", []):
        if (r.get("account") or "").lower() == handle and r.get("text"):
            key = (r["text"].strip(), int(r.get("ts") or 0))
            if key not in seen:
                seen.add(key)
                ex.append({"by": me or "you", "to": handle, "text": r["text"].strip(), "ts": r.get("ts"), "post": None})
    pairs = []
    for i, p in enumerate(feed.get("posts", [])):
        th = [x for x in p.get("thread") or [] if x.get("account") in (me, handle) and x.get("text")]
        for x in th:
            key = (x["text"].strip(), int(x.get("ts") or 0))
            if key in seen:
                for e in ex:
                    if (e["text"], int(e["ts"] or 0)) == key:
                        e["post"] = f"feed:{i}"
                continue
            seen.add(key)
            ex.append({"by": x["account"], "to": handle if x["account"] == me else me, "text": x["text"].strip(), "ts": x.get("ts"),
                       "post": f"feed:{i}"})
        k = 0
        while k < len(th) - 1:
            if th[k]["account"] != th[k + 1]["account"]:
                pairs.append({"post": f"feed:{i}", "photo": (p.get("media") or [None])[0], "first": th[k], "answer": th[k + 1]})
                k += 2
            else:
                k += 1
    ex.sort(key=lambda e: int(e["ts"] or 0))
    mine_lines = [e["text"] for e in ex if e["by"] == (me or "you")]
    their_lines = [e["text"] for e in ex if e["by"] == handle]

    love, keyset = [], set()
    for src in [ask.get("words") or ""] + mine_lines + [x["caption"] for x in items if x["from"] == "mine"]:
        for piece in re.split(r"[,.;!?\n]| - | — ", src):
            t = clean_line(piece, handle, first)
            n = len(t.split())
            k = t.lower()
            if 3 <= n <= 9 and k not in keyset and not re.search(r"\b(turns|october|planning)\b", k):
                keyset.add(k)
                love.append({"line": t, "from": "your words" if src == ask.get("words") else
                             "your comment" if src in mine_lines else "your caption", "you": bool(re.search(r"\byou(r|'re)?\b", k))})
    love.sort(key=lambda x: (x["from"] != "your words", not x["you"]))

    caps_about = [x["caption"] for x in items if x["from"] == "mine"]
    occ = occasion_of(ask, caps_about, first, dt.date.today())
    eras = eras_of(photos)
    c = candidates(lib)
    def row(h):
        return {"handle": h, "shared_score": shared_score(c[h]), **dict(c[h])} if h else None
    out = {
        "who": {"handle": handle, "name": name, "first": first, "matched_by": by, "words": ask.get("who"),
                "named_one": row(handle), "runner_up": row(runner), "most_frequent": row(frequent)},
        "me": me, "occasion": occ,
        "items": items, "videos": videos,
        "first": photos[0] if photos else None, "latest": photos[-1] if photos else None,
        "exchanges": ex, "pairs": pairs, "voice": {"mine": voice(mine_lines), "theirs": voice(their_lines)},
        "eras": eras, "love_lines": love[:14],
        "feed": {"handle": handle, "reachable": bool(feed), "posts": len(feed.get("posts", [])), "source": feed.get("source"),
                 "folder": feed.get("folder")},
        "counts": {"shared": len(items), "photos": len(photos), "videos": len(videos),
                   "posts": sum(1 for x in items if x["kind"] == "post" and x["from"] == "mine"),
                   "stories": sum(1 for x in items if x["kind"] == "story"),
                   "their_posts_with_you": sum(1 for x in items if x["from"] == "theirs"),
                   "exchanges": len(ex), "pairs": len(pairs), "eras": len(eras),
                   "group_photos": sum(1 for x in items if len(x["tagged"]) >= 3)},
        "assumptions": notes,
    }
    _env.write_json("build/shared.json", out)
    print(f"the video is for @{handle} ({name}): {by}")
    for k in ("runner_up", "most_frequent"):
        r = out["who"][k]
        if r:
            print(f"  {k.replace('_', ' ')}: @{r['handle']} (shared score {r['shared_score']})")
    print(f"occasion: {occ['kind']}, {occ['label']}{', ' + occ['date'] if occ.get('date') else ''} (from {occ['from']})")
    n = out["counts"]
    print(f"shared: {n['photos']} photos, {n['videos']} videos ({n['their_posts_with_you']} from their feed); "
          f"first {out['first']['date'] if out['first'] else '-'}, latest {out['latest']['date'] if out['latest'] else '-'}")
    print(f"exchanges: {n['exchanges']} lines, {n['pairs']} pairs; voice mine {out['voice']['mine'].get('avg_words')} words "
          f"lowercase {out['voice']['mine'].get('lowercase')}, theirs {out['voice']['theirs'].get('avg_words')} words "
          f"exclaims {out['voice']['theirs'].get('exclaims')} emoji {out['voice']['theirs'].get('emoji')}")
    print("eras: " + "; ".join(f"{e['label']} ({e['span']}, {e['count']})" for e in eras))
    print(f"love lines: {len(out['love_lines'])}: " + " / ".join(x["line"] for x in out["love_lines"][:5]))
    for x in notes:
        print(f"assumption: {x}")
    print("wrote build/shared.json")
    return 0 if photos else 1


if __name__ == "__main__":
    sys.exit(main())
