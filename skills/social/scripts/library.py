#!/usr/bin/env python3
"""
The reference library: examples of excellent posts to STUDY. Never fill one in.

USAGE:
    python3 scripts/library.py find offer                       # 3-5 closest examples for a job
    python3 scripts/library.py find offer --family bold_type    # prefer the brand's style direction (+ contrast picks from others)
    python3 scripts/library.py find "photo of the product" --photo yes --n 5
    python3 scripts/library.py list                             # every example, one line each
    python3 scripts/library.py show bold_type/offer             # one example in full

`find` prints, per example: the image to LOOK at (open it with the Read tool), the job it does,
its structure (what NOT to copy) and why it works (what to borrow), and the template HTML to read
for technique. It appends to build/library-log.json (the step-4 gate checks that you looked).
Jobs: offer, event, quote, list, statement, hero, versus, carousel, story ... or plain words.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
INDEX = SKILL / "library" / "index.json"

# words that point at a layout (the strongest signal), then plain word overlap with each example's job tags
KEYS = {
    "offer": ["offer", "price", "deal", "promo", "discount", "special", "sale", "tacos", "$", "bogo", "coupon"],
    "event": ["event", "date", "workshop", "open house", "class", "party", "market", "countdown", "tonight", "saturday", "saturdays", "busy", "hours", "opening"],
    "quote": ["quote", "testimonial", "review", "customer", "proof", "praise"],
    "list": ["list", "tips", "steps", "rules", "how-to", "howto", "menu", "checklist", "ways"],
    "statement": ["statement", "type-only", "typeonly", "opinion", "voice", "manifesto", "line"],
    "hero": ["hero", "photo", "picture", "product", "item", "new", "dish", "photo-led"],
    "versus": ["versus", "vs", "before", "after", "comparison", "compare", "choice", "poll", "this-or-that"],
    "carousel-cover": ["carousel", "cover", "swipe", "series"],
    "carousel-inner": ["carousel", "inner", "slide", "explainer"],
    "carousel-cta": ["carousel", "closing", "visit", "booking", "cta"],
    "story": ["story", "stories", "9:16", "vertical", "reel", "stock"],
}


def load():
    return json.loads(INDEX.read_text())["examples"]


def tokens(q):
    return [t for t in re.split(r"[^a-z0-9:\-]+", q.lower()) if t]


def score(ex, q, family, photo):
    toks = tokens(q)
    s = 0.0
    for t in toks:
        if t in KEYS.get(ex["layout"], []):
            s += 10
        elif any(t in w.split() or t == w for w in [x.lower() for x in ex["job"]]):
            s += 3
    if s and photo:
        s += 2 if ex["photo"] == photo else (1 if ex["photo"] == "optional" else 0)
    if s and family and ex["family"] == family:
        s += 2
    return s


def show(ex, rank=None, tag=""):
    img = (SKILL / ex["image"]).resolve()
    lines = [f"{'#' + str(rank) + ' ' if rank else ''}{ex['id']}{tag}",
             f"  image:     {img}",
             f"  job:       {', '.join(ex['job'])}   (photo: {ex['photo']}; for {ex['best_for']})",
             f"  look:      {ex['look']}",
             f"  structure: {ex['structure']}   <- do not copy this",
             "  why it works (borrow these):"]
    lines += [f"    - {w}" for w in ex["why"]]
    lines.append(f"  technique: {(SKILL / ex['html']).resolve()}")
    return "\n".join(lines)


def cmd_find(a):
    ex = load()
    q = " ".join(a.query)
    js = lambda e: score(e, q, None, a.photo)          # job-only score
    ranked = sorted(ex, key=lambda e: -js(e))
    top = js(ranked[0]) if ranked else 0
    n = max(3, min(5, a.n))
    picks = []
    if a.family:  # the brand's style direction first, but only examples that do this job
        picks += [e for e in ranked if e["family"] == a.family and js(e) >= max(3, top * 0.5)][: max(2, n - 2)]
    seen = {p["family"] for p in picks}
    for e in ranked:  # then the best example from each other family (contrast, so one look doesn't dominate)
        if len(picks) >= n:
            break
        if e not in picks and e["family"] not in seen and js(e) > 0:
            picks.append(e)
            seen.add(e["family"])
    for e in ranked:
        if len(picks) >= max(3, n - 1):
            break
        if e not in picks:
            picks.append(e)
    own_fam = a.family
    print(f"Closest {len(picks)} reference examples for '{q}'"
          + (f" (style direction: {own_fam}; the others are contrast picks)" if own_fam else "") + ".")
    print("READ ALL %d IMAGES (one Read call each), then write what you will borrow. Do not pipe this output through head/tail:" % len(picks))
    for e in picks:
        print("   " + str((SKILL / e["image"]).resolve()))
    print("Borrow a PRINCIPLE (scale contrast, crop, spacing, colour discipline), never the layout.\n")
    for i, e in enumerate(picks, 1):
        print(show(e, i, " [contrast pick]" if own_fam and e["family"] != own_fam else ""))
        print()
    if own_fam:
        print(f"Family contact sheet: {(SKILL / 'library' / ('_sheet-' + own_fam + '.jpg')).resolve()}")
    log = Path("build/library-log.json")
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(log.read_text()) if log.exists() else []
        data.append({"query": q, "family": own_fam, "ids": [e["id"] for e in picks]})
        log.write_text(json.dumps(data, indent=1))
    except OSError:
        pass
    return 0


def cmd_list(a):
    for e in load():
        print(f"{e['id']:<28} {', '.join(e['job'][:4]):<52} photo:{e['photo']}")
    return 0


def cmd_show(a):
    for e in load():
        if e["id"] == a.id:
            print(show(e))
            return 0
    print("no such example; try `library.py list`", file=sys.stderr)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("query", nargs="+")
    f.add_argument("--family")
    f.add_argument("--photo", choices=["yes", "no"])
    f.add_argument("--n", type=int, default=4)
    sub.add_parser("list")
    s = sub.add_parser("show")
    s.add_argument("id")
    a = ap.parse_args()
    return {"find": cmd_find, "list": cmd_list, "show": cmd_show}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
