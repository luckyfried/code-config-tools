#!/usr/bin/env python3
"""Movement 1: the research behind the taste profile, for one person and the one the video is for. Reads
build/library.json; writes build/research.json, a machine draft of build/taste.json, and build/taste.draft.md
(the numbers under the five headings the agent turns into build/taste.md).

USAGE (from the workspace root):
    python3 S/scripts/research.py --who "@dani.reyes" [--occasion "her 30th"] [--date 2026-10-24] [--words "..."]

It runs shared.py first with the same arguments (who the video is for, the occasion, the shared photos, the
exchanges between the two, the eras), then picks.py (the shared photos, prepared) and palette.py (mine, theirs,
together), then reads:
  the two     who it is for and how they were found, the runner-up and the account the person talks to most
  occasion    what it is and where that came from (the person's words win over their captions)
  shared      how many photos, stories and videos the two share, the first and the latest, the group photos
  eras        the friendship in chapters, each with its place and months
  exchanges   the lines the two trade, and the voice of each side (length, capitals, exclamation marks, emoji)
  love lines  the person's own lines about the named one, the source of a "things I love about you" list
  their feed  the named one's own captions (their humor, their emoji) when their feed was reachable
  captions    the person's own register: length, case, emoji, punctuation, hashtags
  reels       how long the person's reels run and how fast they cut (ffmpeg scene changes)
taste.json also carries the palette (together, mine, theirs), the type direction, pacing, register, texture and
the grade inputs; the agent edits it freely before storyboards are drafted.
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
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨]")


def run(script, args=()):
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


def theme_counts(texts):
    c = collections.Counter()
    for t in texts:
        toks = set(tokens(t))
        for theme, words in THEMES.items():
            if toks & set(words):
                c[theme] += 1
    return c


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
    for k in ("who", "occasion", "date", "words"):
        ap.add_argument(f"--{k}")
    a = ap.parse_args()
    lib = _env.read_json("build/library.json")
    if not lib:
        sys.exit("build/library.json is missing: run gather.py first")
    args = [x for k in ("who", "occasion", "date", "words") if getattr(a, k) for x in (f"--{k}", getattr(a, k))]
    print(run("shared.py", args).strip().splitlines()[0])
    for s in ("picks.py", "palette.py"):
        print(run(s).strip().splitlines()[-1])
    sh = _env.read_json("build/shared.json")
    pal = _env.read_json("build/palette.json") or {}
    who, occ, n = sh["who"], sh["occasion"], sh["counts"]
    mine_caps = caption_read(lib["posts"] + lib["reels"] + lib.get("facebook", []))
    feed = (lib.get("feeds") or {}).get(who["handle"]) or {}
    their_caps = caption_read(feed.get("posts", []))
    shared_caps = [x["caption"] for x in sh["items"]]
    themes = theme_counts(shared_caps + [p.get("caption") or "" for p in feed.get("posts", [])])
    own_themes = theme_counts([p.get("caption") or "" for p in lib["posts"] + lib["reels"]])
    pacing = reel_pacing(lib["reels"])
    td = type_direction(own_themes + themes, mine_caps, pacing)
    film = own_themes.get("film photography", 0) >= 5
    vm, vt = sh["voice"]["mine"], sh["voice"]["theirs"]
    swatch = lambda k: [{"hex": c["hex"], "name": c.get("name"), "share": c.get("share"), "photo": c.get("photo")} for c in pal.get(k) or []]
    research = {
        "handle": lib["handle"], "for": who, "occasion": occ, "source": lib["source"], "doors": lib.get("doors", {}),
        "counts": n, "first": sh["first"], "latest": sh["latest"], "eras": sh["eras"],
        "palette": {"together": swatch("together"), "mine": swatch("mine"), "theirs": swatch("theirs"), "roles": pal.get("roles")},
        "voice": sh["voice"], "pairs": sh["pairs"][:12], "love_lines": sh["love_lines"],
        "captions": mine_caps, "their_captions": their_caps, "themes": dict(themes.most_common()),
        "own_themes": dict(own_themes.most_common()), "reels": pacing, "type": td,
        "their_feed": sh["feed"], "assumptions": sh.get("assumptions", []),
    }
    _env.write_json("build/research.json", research)
    shot = pacing.get("avg_shot_seconds")
    loud = (vt.get("exclaims") or 0) >= 0.3 or (vt.get("emoji") or 0) >= 0.5
    taste = {
        "written_by": "research.py draft; the agent edits this file and writes taste.md",
        "handle": lib["handle"], "for": {"handle": who["handle"], "name": who["name"], "first": who["first"]},
        "occasion": {k: occ.get(k) for k in ("kind", "age", "years", "date", "label", "title")},
        "palette": {"together": swatch("together"), "mine": swatch("mine"), "theirs": swatch("theirs"),
                    "direction": "the colors the two share: theirs for the accent, mine for the grade"},
        "type": td,
        "pacing": {"reel_seconds": pacing.get("avg_seconds"), "shot_seconds": shot,
                   "beat_seconds": round(max(2.2, min(4.2, (shot or 2.8) * 1.4)), 2),
                   "energy": "high" if loud and td["lead"] == "kinetic" else "warm"},
        "register": {"lowercase": mine_caps.get("lowercase_share", 0) >= 0.6, "emoji": mine_caps.get("emoji_per_caption", 0),
                     "avg_words": mine_caps.get("avg_words"), "hashtags": mine_caps.get("top_hashtags", [])[:3],
                     "samples": mine_caps.get("samples", [])[:4]},
        "their_register": {"loud": loud, "exclaims": vt.get("exclaims"), "emoji": vt.get("emoji"), "capitals": vt.get("capitals"),
                           "samples": (vt.get("samples") or [])[:4]},
        "eras": [{"label": e["label"], "span": e["span"], "count": e["count"]} for e in sh["eras"]],
        "love_lines": [x["line"] for x in sh["love_lines"][:9]],
        "pillars": [t for t, _ in themes.most_common(4)],
        "texture": {"grain": 0.14 if film else 0, "vignette": 0.28 if film else 0.0, "leaks": film},
        "avoid": ["cold, clinical grading", "stock-photo gloss", "jokes at their expense"] + (["neon"] if film else []),
    }
    if not Path("build/taste.json").exists() or "research.py draft" in (_env.read_json("build/taste.json") or {}).get("written_by", ""):
        _env.write_json("build/taste.json", taste)
    f, l = sh["first"] or {}, sh["latest"] or {}
    lines = [f"# taste draft: @{lib['handle']} and @{who['handle']} ({occ['label']})", "",
             "The agent writes build/taste.md from this: one page, five paragraphs that start with the five headings below. "
             "\"You\" is the two of them: who they are together, what they like, how they look, how they talk, what to avoid.", "",
             "## you are",
             f"- the video is for @{who['handle']} ({who['name']}): {who['matched_by']}",
             f"- runner-up @{(who.get('runner_up') or {}).get('handle')}; most commented @{(who.get('most_frequent') or {}).get('handle')}",
             f"- occasion: {occ['kind']}, {occ['label']}{', on ' + occ['date'] if occ.get('date') else ''} (from {occ['from']})",
             f"- shared: {n['photos']} photos ({n['posts']} posts, {n['stories']} stories, {n['their_posts_with_you']} of their posts tagging you), "
             f"{n['videos']} videos, {n['group_photos']} group photos",
             f"- first together {f.get('date')}: \"{f.get('caption')}\"; latest {l.get('date')}: \"{l.get('caption')}\"",
             f"- eras: {'; '.join(e['label'] + ' (' + e['span'] + ', ' + str(e['count']) + ')' for e in sh['eras'])}",
             "", "## you like",
             f"- what the shared photos and their feed are about: {', '.join(f'{k} ({v})' for k, v in themes.most_common(5))}",
             f"- together palette: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in pal.get('together') or [])}",
             f"- your palette: {', '.join((c.get('name') or '') + ' ' + c['hex'] for c in pal.get('mine') or [])}",
             f"- their palette ({'their saved feed' if sh['feed']['reachable'] else 'not reachable'}): "
             f"{', '.join((c.get('name') or '') + ' ' + c['hex'] for c in pal.get('theirs') or []) or 'none'}",
             "", "## your style is",
             f"- your reels: {pacing.get('avg_seconds')} s on average, a cut every {shot} s" if shot else "- no reels of yours to measure",
             f"- texture: {'film grain and warm light' if film else 'clean'}; type lead: {td['lead']} ({td['why']})",
             "", "## your voice is",
             f"- you: {vm.get('lines')} lines to them, {vm.get('avg_words')} words a line, {int((vm.get('lowercase') or 0) * 100)}% lowercase, "
             f"{vm.get('emoji')} emoji a line: {' / '.join((vm.get('samples') or [])[:4])}",
             f"- them: {vt.get('lines')} lines to you, {vt.get('avg_words')} words a line, capitals in {int((vt.get('capitals') or 0) * 100)}%, "
             f"exclamation marks in {int((vt.get('exclaims') or 0) * 100)}%, {vt.get('emoji')} emoji a line: {' / '.join((vt.get('samples') or [])[:4])}",
             f"- their captions: {their_caps.get('avg_words')} words, {their_caps.get('emoji_per_caption')} emoji a caption: "
             f"{' / '.join(their_caps.get('samples', [])[:3])}" if their_caps.get("captions") else "- their own captions: feed not reachable",
             f"- your captions: {mine_caps.get('avg_words')} words, {int(mine_caps.get('lowercase_share', 0) * 100)}% lowercase, "
             f"hashtags {', '.join(mine_caps.get('top_hashtags', [])[:4])}",
             f"- love lines (yours, about them): {' / '.join(x['line'] for x in sh['love_lines'][:9])}",
             f"- pairs (a line and the answer): {' / '.join(p['first']['text'] + ' -> ' + p['answer']['text'] for p in sh['pairs'][:4])}",
             "", "## avoid", f"- {', '.join(taste['avoid'])}", ""]
    if sh.get("assumptions"):
        lines += ["## assumptions", *[f"- {x}" for x in sh["assumptions"]], ""]
    Path("build/taste.draft.md").write_text("\n".join(lines))
    print(f"for @{who['handle']} ({occ['label']}); {n['photos']} shared photos, {n['videos']} videos, {n['exchanges']} lines traded, {n['eras']} eras")
    print(f"together palette: {[c['hex'] + ' ' + (c.get('name') or '') for c in pal.get('together') or []]}")
    print(f"voice: you {vm.get('avg_words')} words lowercase {vm.get('lowercase')}; them exclaims {vt.get('exclaims')} emoji {vt.get('emoji')}")
    print(f"reels: {pacing.get('reels_measured')} measured, shot {shot} s; type lead {td['lead']}")
    print("wrote build/research.json, build/taste.json (draft) and build/taste.draft.md; now write build/taste.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
