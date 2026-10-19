#!/usr/bin/env python3
"""Movement 1: the research behind the taste profile. Reads build/library.json; writes build/research.json, a
machine draft of build/taste.json, and build/taste.draft.md (the numbers under the five headings the agent turns
into build/taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py [--subject "my pottery"] [--terms clay,kiln] [--beats 12]

It runs timeline.py (the subject, its dated run, the milestones, the span, the voice early against recent),
picks.py (the posts the film carries) and palette.py (the subject's palette) first, then reads:
  timeline   first, latest, milestones (their words first, visible change when they name fewer than two), span
  voice      how the captions about the subject sound in the oldest third against the newest third
  changed    their own lines about what changed; these win over anything inferred from the photos
  progress   the style of the progress posts they like (a liked, likes, saved or inspo folder, or liked and saved
             posts whose captions read as before and after): how each splits the frame (left and right, top and
             bottom, a grid of four, or one photo), measured from the image's seams, and how the captions mark time
             ("day 1 vs day 400", "2024 -> 2025", "then / now", "month 1 vs month 12")
  palette    the subject's colors against the colors of the photos they like and save
  captions   length, case, emoji, punctuation, hashtags of the subject's captions
  reels      how long their reels of the subject run and how fast they cut (ffmpeg scene changes)
taste.json also carries the type direction, pacing, register, texture and the grade inputs; the agent edits it
freely before storyboards are drafted.
"""
import collections
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
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728]")
FILM = ["35mm", "film", "portra", "kodak", "grain", "analog", "shotonfilm", "filmphotography", "120"]
LIGHT = ["light", "golden", "sun", "sunbaked", "amber", "warm", "warmtones", "morning"]
PROGRESS = re.compile(r"(\bvs\.?\b|→|->|\bbefore\b.*\bafter\b|\bthen\b.*\bnow\b|\bday \d+|\bmonth \d+|\bweek \d+|"
                      r"\byears? (one|two|\d+)\b|\bone year\b|\bside by side\b|\bprogress\b|\b(19|20)\d\d\s*(→|->|vs|to)\s*(19|20)\d\d\b)", re.I)
MARKS = [("day N vs day N", re.compile(r"\bday \d+\b.*\bday \d+", re.I)),
         ("month N vs month N", re.compile(r"\bmonth \d+\b.*\bmonth \d+", re.I)),
         ("year -> year", re.compile(r"\b(19|20)\d\d\s*(→|->|vs|to)\s*(19|20)\d\d\b")),
         ("then / now", re.compile(r"\bthen\b.*\bnow\b", re.I)),
         ("before / after", re.compile(r"\bbefore\b.*\bafter\b", re.I)),
         ("first vs latest", re.compile(r"\bfirst\b.*\b(vs|and)\b.*\b(latest|this week|now)\b", re.I)),
         ("a span in words", re.compile(r"\b(one|two|three|a) (year|month)s?\b", re.I))]
LAYOUT_WORDS = {"lr": "left and right", "tb": "top and bottom", "grid": "a grid of four", "single": "one photo"}


def run(script, *args):
    p = subprocess.run([sys.executable, str(S / script), *args], capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{script} failed:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}")
    return p.stdout


def tokens(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


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
    return [{"hex": "#%02x%02x%02x" % k, "name": color_name(k), "share": round(v / total, 3)} for k, v in acc.most_common(5)]


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


def color_name(rgb):
    """The nearest of the named colors, by distance in RGB."""
    def dist(h):
        c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    w = min(COLOR_WORDS, key=lambda k: dist(COLOR_WORDS[k]))
    return SPOKEN.get(w, w)


def seams(path):
    """How much of the photo's center line is a seam, vertical and horizontal (0 to 1): the share of the line where
    a thin divider stands out from both sides, or where the picture breaks hard across it. Two photos joined at the
    middle score near 1 (a split needs 0.9); a horizon or a shelf rarely sits on the exact middle across the whole line."""
    import picks
    im = picks.open_image(path, draft=(256, 256)).convert("L").resize((128, 128))
    px = im.load()
    def at(k, j, vertical):
        return px[k, j] if vertical else px[j, k]
    def share(k, vertical):
        hit = 0
        for j in range(128):
            a, b, c = at(k - 3, j, vertical), at(k, j, vertical), at(k + 3, j, vertical)
            line = b - max(a, c) > 8 or min(a, c) - b > 8
            join = abs(at(k + 1, j, vertical) - at(k - 1, j, vertical)) > 12
            hit += line or join
        return hit / 128
    return (round(max(share(k, True) for k in range(61, 68)), 2), round(max(share(k, False) for k in range(61, 68)), 2))


def layout_of(path):
    v, h = seams(path)
    if v >= 0.9 and h >= 0.9:
        return "grid", v, h
    if v >= 0.9:
        return "lr", v, h
    if h >= 0.9:
        return "tb", v, h
    return "single", v, h


def progress_style(lib):
    """The progress posts they like: how each splits the frame, and how its caption marks time."""
    rows = [r for r in lib.get("likes", []) + lib.get("saved", []) if r.get("media") and
            (r.get("folder") or PROGRESS.search(r.get("caption") or ""))]
    seen, posts = set(), []
    for r in rows:
        m = next((m for m in r["media"] if Path(m).exists() and Path(m).suffix.lower() not in (".mp4", ".mov", ".m4v")), None)
        if not m or m in seen:
            continue
        seen.add(m)
        try:
            lay, v, h = layout_of(m)
        except Exception:
            continue
        marks = [name for name, rx in MARKS if rx.search(r.get("caption") or "")]
        posts.append({"account": r.get("account"), "caption": r.get("caption") or "", "media": m, "layout": lay,
                      "seam_vertical": v, "seam_horizontal": h, "marks": marks, "from": "their liked folder" if r.get("folder") else "a liked or saved post"})
    if not posts:
        return {"posts": 0, "lead": "lr", "why": "no liked progress posts to read; side by side, left and right, is the default"}
    lays = collections.Counter(p["layout"] for p in posts)
    marks = collections.Counter(m for p in posts for m in p["marks"])
    split = [p for p in posts if p["layout"] in ("lr", "tb")]
    lead = collections.Counter(p["layout"] for p in split).most_common(1)[0][0] if split else "lr"
    return {"posts": len(posts), "layouts": dict(lays.most_common()), "lead": lead, "lead_words": LAYOUT_WORDS[lead],
            "marks": dict(marks.most_common()), "examples": [p["caption"] for p in posts[:5]], "read": posts,
            "why": f"{lays[lead]} of the {len(posts)} progress posts they like put then and now {LAYOUT_WORDS[lead]}"
                   + (f"; their captions mark time as {', '.join(m for m, _ in marks.most_common(3))}" if marks else "")}


def type_direction(caps, pacing, style):
    loud = caps.get("emoji_per_caption", 0) > 1 or (pacing.get("avg_shot_seconds") or 9) < 1.2
    counted = sum(n for m, n in (style.get("marks") or {}).items() if m in ("day N vs day N", "month N vs month N", "year -> year"))
    if loud:
        return {"lead": "kinetic", "display": "Archivo Black", "text": "Archivo",
                "why": "heavy emoji and fast reels read as loud: a heavy grotesk that can slam"}
    if counted >= max(3, (style.get("posts") or 0) // 2):
        return {"lead": "documentary", "display": "Space Grotesk", "text": "JetBrains Mono",
                "why": "the progress posts they like count the days: a documentary grotesk with mono dates"}
    return {"lead": "editorial", "display": "Fraunces", "text": "Inter",
            "why": "quiet, plain captions about something made by hand: a soft serif with a plain sans for the dates"}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", help="the subject the person named, in their words")
    ap.add_argument("--terms", default="", help="more words or hashtags that name the subject, comma separated")
    ap.add_argument("--beats", default="12", help="how many posts the film carries")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    targs = (["--subject", a.subject] if a.subject else []) + (["--terms", a.terms] if a.terms else [])
    out = run("timeline.py", *targs)
    print("\n".join(l for l in out.strip().splitlines() if l.startswith(("subject:", "timeline:"))))
    print(run("picks.py", "--beats", str(a.beats)).strip().splitlines()[0])
    run("palette.py")
    sub = _env.read_json("build/subject.json")
    picks = _env.read_json("build/picks.json") or {}
    pal = _env.read_json("build/palette.json") or {}
    posts = sub["posts"]
    caps = caption_read(posts)
    style = progress_style(lib)
    liked_media = [m for r in lib["likes"] + lib.get("saved", []) for m in (r.get("media") or []) if Path(m).exists()]
    like_accounts = collections.Counter(r.get("account") for r in lib["likes"] if r.get("account"))
    saved_accounts = collections.Counter(r.get("account") for r in lib.get("saved", []) if r.get("account"))
    follow = [r.get("account") for r in lib.get("following", []) if r.get("account")]
    liked_text = list(like_accounts.elements()) + list(saved_accounts.elements()) + follow + \
        [r.get("caption") or "" for r in lib["likes"] + lib.get("saved", [])]
    likes_palette = image_palette(liked_media) if len(liked_media) >= 8 else lexicon_palette(liked_text)
    likes_palette_from = "the photos they liked and saved" if len(liked_media) >= 8 else \
        "the color words in the names and captions of the accounts they like, save and follow"
    reels = [{"media": [p["video"]]} for p in posts if p.get("video")]
    pacing = reel_pacing(reels)
    td = type_direction(caps, pacing, style)
    subject_palette = [{"hex": c["hex"], "name": c.get("name"), "share": c.get("share"), "photo": c.get("photo")}
                       for c in (pal.get("subject") or [])]
    every = [r.get("caption") or "" for r in lib["posts"] + lib["reels"]] + liked_text
    film = sum(1 for t in every if set(tokens(t)) & set(FILM)) >= 5
    warm = sum(1 for t in every if set(tokens(t)) & set(LIGHT)) >= 4
    span = sub["span"]
    timeline = {"first": sub["first"], "latest": sub["latest"], "milestones": sub["milestones"], "span": span,
                "posts": len(posts), "chosen_by": sub["chosen_by"], "changed": sub["changed"], "steadiness": sub["steadiness"],
                "sequence": [p["id"] for p in picks.get("sequence", [])]}
    research = {
        "handle": lib["handle"], "subject": sub["subject"], "named": sub.get("named"), "source": lib["source"],
        "doors": lib.get("doors", {}), "range": lib.get("range"), "candidates": sub["candidates"],
        "timeline": timeline, "voice": sub["voice"], "progress_style": {k: v for k, v in style.items() if k != "read"},
        "progress_read": style.get("read", []),
        "palette": {"subject": subject_palette, "likes": likes_palette, "likes_from": likes_palette_from, "roles": pal.get("roles")},
        "captions": caps, "reels": pacing, "type": td,
        "likes": {"accounts": len(like_accounts), "top": [{"account": x, "likes": n} for x, n in like_accounts.most_common(8)]},
    }
    _env.write_json("build/research.json", research)
    shot = pacing.get("avg_shot_seconds")
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "subject": sub["subject"], "span": span,
        "palette": {"subject": subject_palette, "likes": likes_palette,
                    "direction": "toward their likes" if likes_palette else "their subject's own colors"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(1.8, min(4.0, (shot or 2.6) * 1.2)), 2),
                   "energy": "high" if td["lead"] == "kinetic" else "measured" if td["lead"] == "documentary" else "calm"},
        "register": {"lowercase": caps.get("lowercase_share", 0) >= 0.6, "emoji": caps.get("emoji_per_caption", 0),
                     "avg_words": caps.get("avg_words"), "hashtags": caps.get("top_hashtags", [])[:3],
                     "samples": caps.get("samples", [])[:4]},
        "voice": {"early": (sub["voice"].get("early") or {}).get("lines", []), "recent": (sub["voice"].get("recent") or {}).get("lines", []),
                  "summary": sub["voice"].get("summary")},
        "timeline": {"first": sub["first"]["date"], "latest": sub["latest"]["date"],
                     "milestones": [{"date": m["date"], "label": m["label"], "why": m["why"]} for m in sub["milestones"]],
                     "changed": [c["line"] for c in sub["changed"]]},
        "progress_style": {"lead": style["lead"], "marks": list((style.get("marks") or {}).keys())[:3], "why": style["why"]},
        "texture": {"grain": 0.16 if film else 0.08, "vignette": 0.3 if film else 0.0, "leaks": bool(film and warm)},
        "avoid": ["grading that hides the change between photos", "stock time-lapse gloss", "cold blue grading"],
    }
    if not Path("build/taste.json").exists() or "research.py draft" in (_env.read_json("build/taste.json") or {}).get("written_by", ""):
        _env.write_json("build/taste.json", taste)
    v = sub["voice"]
    lines = [f"# taste draft for @{lib['handle']}: {sub['subject']}, {span['label']}", "",
             "The agent writes build/taste.md from this: one page, five paragraphs that start with the five headings below.",
             "Their own words about what changed win over anything read from the photos.", "",
             "## you are",
             f"- the subject: {sub['subject']}, {sub['chosen_by']}; {len(posts)} posts from {span['first']} to {span['latest']} ({span['label']})",
             f"- other runs in the feed: {'; '.join(c['subject'] + ' ' + str(c['run_days']) + ' days' for c in sub['candidates'][1:4])}",
             f"- first: {sub['first']['date']}, \"{sub['first']['caption']}\"",
             *[f"- milestone {m['date']} ({m['why']}): \"{m['caption']}\"" for m in sub["milestones"]],
             f"- latest: {sub['latest']['date']}, \"{sub['latest']['caption']}\"",
             f"- what they say changed: {' / '.join(c['line'] for c in sub['changed'][:4]) or 'nothing in so many words'}",
             f"- the photos move away from the first one with steadiness {sub['steadiness']} (1 is every post further than the last)",
             "", "## you like",
             f"- progress posts they like: {style.get('posts', 0)}; layouts {style.get('layouts')}; {style['why']}",
             f"- their captions: {' / '.join(style.get('examples', [])[:4])}",
             f"- palette of the subject: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in subject_palette)}",
             f"- palette of their likes ({likes_palette_from}): {', '.join(c['name'] + ' ' + c['hex'] for c in likes_palette)}",
             "", "## your style is",
             f"- reels of the subject: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels of the subject to measure",
             f"- texture: {'film grain and warm light' if film else 'clean, a little grain'}; type lead: {td['lead']} ({td['why']})",
             "", "## your voice is",
             f"- {v.get('summary') or 'too few captions to compare early and recent'}",
             f"- early lines: {' / '.join((v.get('early') or {}).get('lines', []))}",
             f"- recent lines: {' / '.join((v.get('recent') or {}).get('lines', []))}",
             f"- {caps.get('avg_words')} words a caption, {int(caps.get('lowercase_share', 0) * 100)}% lowercase, "
             f"{caps.get('emoji_per_caption')} emoji a caption; hashtags {', '.join(caps.get('top_hashtags', [])[:5])}",
             "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    Path("build/taste.draft.md").write_text("\n".join(lines))
    print(f"progress style: {style['why']}")
    print(f"subject palette: {[c['hex'] for c in subject_palette]}; likes palette: {[c['hex'] + ' ' + c['name'] for c in likes_palette]}")
    print(f"voice: {v.get('summary')}")
    print(f"reels: {pacing.get('reels_measured')} measured, {pacing.get('avg_seconds')} s, shot {shot} s; type lead {td['lead']}")
    print("wrote build/research.json, build/taste.json (draft) and build/taste.draft.md; now write build/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
