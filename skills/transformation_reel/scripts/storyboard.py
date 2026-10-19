#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film of the same timeline, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, dates in order, first and latest, assets, 30-60 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (palette, type direction, pacing, register, voice, the timeline and the style of
the progress posts they like), then build/subject.json, picks.json, palette.json and research.json. The three
boards differ on structure, tone and how generated clips are used:
  1  the timeline     a straight run from the first post to the latest, every photo dated, a  documentary  still-first;
                      progress rail under it, the milestones marked                                         generated time-lapse
                                                                                                            bridges and the opener
  2  then and now     the first and the latest side by side; the divider between them         editorial    clip-first;
                      becomes the wipe that carries the film through every date and back                    every key photo brought
                      to the pair                                                                           to life, their reels play
  3  chapters         one chapter per milestone, their own caption on screen as the narration kinetic      generated opener and
                                                                                                            closer, their reels play
Every photo beat carries "post" (the subject post's id) and "at" (its date), and the photo beats of every board run
in date order from the subject's earliest post to its latest. A then/now beat (Split) pairs the first and the latest
and carries both. Every board carries the then/now card (1080x1350): the first and the latest photo side by side
with the span between them, in the board's palette and type. The agent may edit any storyboard.json (text, order,
photos, prompts) before sheets; check validates it.
"""
import argparse
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import grade  # noqa: E402
import timeline as tl  # noqa: E402

DESIGN = _env.SKILL / "design"
BOARDS = Path("build/storyboards")
FPS = 30
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
TARGET = {"editorial": 36, "kinetic": 44, "documentary": 40}
LENGTH = (30, 60)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728\uFE0F\u200D]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}
PHRASE = {"pottery": "pottery", "garden": "the garden", "fitness": "training", "home": "the home", "art": "my art",
          "baking": "baking", "knitting": "knitting", "music": "music", "glow-up": "me", "woodworking": "woodworking",
          "pet": "this one", "calligraphy": "lettering"}
WORLD = {"pottery": "a potter's wheel turning in a quiet studio, wet clay rising between two hands, shelves of bisque behind",
         "garden": "a small balcony garden at dawn, leaves unfurling, light moving across pots and soil",
         "fitness": "an empty gym at first light, chalk dust in the air, a barbell waiting",
         "home": "an empty room with dust sheets and paint tins, light moving across bare walls",
         "art": "an artist's desk with brushes, paper and paint, light moving slowly across it",
         "baking": "a floured kitchen counter at dawn, dough rising in a bowl, steam from an oven"}


def design(name):
    return json.loads((DESIGN / name).read_text())


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)


def mix(a, b, t):
    a, b = hex_rgb(a), hex_rgb(b)
    return rgb_hex([x + (y - x) * t for x, y in zip(a, b)])


def lum(h):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in hex_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sat(h):
    r, g, b = (c / 255 for c in hex_rgb(h))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0 if mx == 0 else (mx - mn) / mx


def readable(c, bg, need=3.0):
    """Move c toward black or white until it reads on bg."""
    target = "#000000" if lum(bg) > 0.4 else "#ffffff"
    for i in range(21):
        x = mix(c, target, i / 20)
        if contrast(x, bg) >= need:
            return x
    return target


class Ctx:
    def __init__(self):
        self.taste = _env.read_json("build/taste.json")
        if not self.taste:
            sys.exit("build/taste.json is missing: run research.py and write the taste profile first")
        if not Path("build/taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before storyboards")
        self.sub = _env.read_json("build/subject.json") or {}
        self.picks = _env.read_json("build/picks.json") or {}
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.lib = _env.read_json("build/library.json") or {}
        if not self.sub.get("posts") or not self.picks.get("sequence"):
            sys.exit("build/subject.json or build/picks.json is missing: run research.py first")
        self.handle = self.taste.get("handle") or self.lib.get("handle") or "you"
        self.subject = self.sub["subject"]
        named = [w for w in re.split(r"\s+", (self.sub.get("named") or "").strip().lower()) if w]
        while named and named[0] in ("my", "the", "a", "our", "of"):
            named.pop(0)
        self.phrase = ("my " + " ".join(named)) if named else PHRASE.get(self.subject, self.subject)
        self.span = self.sub["span"]
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.first_day = dt.date.fromisoformat(self.span["first"])
        self.last_day = dt.date.fromisoformat(self.span["latest"])
        lead = (self.taste.get("progress_style") or {}).get("lead") or "lr"
        self.split = "tb" if lead == "tb" else "lr"

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def photo(self, src):
        """A prepared photo as the graded file the renderer reads (relative to build/)."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        return grade.graded_name(p) if p else None

    def seq(self):
        """The posts the film carries, oldest first, each with its graded photo."""
        if not hasattr(self, "_seq"):
            out = []
            for p in self.picks["sequence"]:
                ph = self.photo(p["photo"])
                if ph:
                    out.append(dict(p, graded=ph))
            self._seq = out
        return self._seq

    def first(self):
        return self.seq()[0]

    def latest(self):
        return self.seq()[-1]

    def when(self, p, direction):
        d = dt.date.fromisoformat(p["date"])
        if direction == "documentary":
            return d.strftime("%Y.%m.%d")
        if direction == "kinetic":
            return self.say(f"{MONTHS[d.month - 1][:3]} {d.year}")
        return self.say(f"{MONTHS[d.month - 1]} {d.day}, {d.year}")

    def count(self, p):
        """The day of the run (day 1 is the first post) and the whole months since the first post."""
        d = dt.date.fromisoformat(p["date"])
        return (d - self.first_day).days + 1, tl.span_of(self.first_day, d)["months"]

    def since(self, p):
        """The time since the first post, measured the way the caption measures the span: "day one", "3 weeks in", "14 months in"."""
        d = dt.date.fromisoformat(p["date"])
        return self.say("day one" if d == self.first_day else f"{tl.span_of(self.first_day, d)['label']} in")

    def progress(self, p):
        whole = (self.last_day - self.first_day).days or 1
        return round((dt.date.fromisoformat(p["date"]) - self.first_day).days / whole, 4)

    def words(self, p, limit=60, whole=False):
        """Their caption for the screen: the milestone prefix dropped, the lead line kept (or every sentence that fits), in their register."""
        cap = re.sub(r"^\s*milestone\s*[:\-–]\s*", "", p.get("caption") or "", flags=re.I)
        return self.say(short(cap, limit, whole)) or self.when(p, "editorial")

    def title(self):
        return self.say(f"{self.span['label']} of {self.phrase}")

    def span_line(self):
        return self.say(f"{self.span['from']} to {self.span['to']}")

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        own = [c["hex"] for c in self.taste.get("palette", {}).get("subject", []) if c.get("hex")] or ["#6b5440", "#b8a17f"]
        likes = [c["hex"] for c in self.taste.get("palette", {}).get("likes", []) if c.get("hex")]
        allc = own + likes
        darkest = min(allc, key=lum)
        lightest = max(allc, key=lum)
        vivid = sorted(likes + own, key=lambda h: -sat(h) * (0.4 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(vivid[1] if len(vivid) > 1 else own[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = vivid[0]
            accent2 = vivid[1] if len(vivid) > 1 else own[0]
            if contrast(ink, accent) < 2.2:
                accent = mix(accent, "#000000", 0.25)
            if contrast(ink, accent2) < 2.2:
                accent2 = mix(accent2, "#000000", 0.35)
            texture = {"grain": round(tex.get("grain", 0) * 0.5, 3), "vignette": 0, "leaks": False}
        else:
            bg = mix(darkest, "#000000", 0.7)
            ink = mix(lightest, "#ffffff", 0.5)
            paper = mix(lightest, "#f4ead8", 0.5)
            accent = readable(vivid[0], bg, 4)
            accent2 = vivid[1] if len(vivid) > 1 else own[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        swatches = [{"hex": c["hex"], "name": self.say(c.get("name") or "")} for c in self.taste.get("palette", {}).get("subject", [])][:5]
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, what, direction, seconds):
        t = self.taste
        colors = [c.get("name") for c in t.get("palette", {}).get("likes", [])[:3] if c.get("name")] + \
                 [c.get("name") for c in t.get("palette", {}).get("subject", [])[:2] if c.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "locked-off tripod, natural light, observational, 16mm grain"}[direction]
        light = "warm window light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{what}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")

    def world(self):
        return WORLD.get(self.subject, f"the place where {self.phrase} happens, light moving slowly across it")


def short(cap, limit=60, whole=False):
    """A caption's lead line for the screen: no hashtags or emoji, cut at a clause or a word, never on a function word.
    whole keeps every sentence that fits the limit, for a beat that carries their caption as the narration."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = whole_c = re.sub(r"\s+", " ", c)
    for sep in (() if whole else (". ", ": ", "; ", " - ")):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if whole and len(c) > limit and ". " in c[:limit]:
        c = c[:limit].rsplit(". ", 1)[0]
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while c != whole_c and len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


def tr(preset, direction, d=None, frames=None):
    f = frames or design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def dated(ctx, p, d, seconds, transition, line=None, clip=None, bid=None):
    """One post of the timeline at full frame: its photo, its date, its own words."""
    day, month = ctx.count(p)
    kicker = ctx.when(p, d)
    if p.get("milestone"):
        kicker = f"{kicker} · {ctx.say('milestone')}"
    b = {"id": bid or f"{p['id']}-{p['date']}", "kind": "Dated", "frames": sec(seconds), "transition": transition,
         "post": p["id"], "at": p["date"], "photos": [p["graded"]],
         "text": {"kicker": kicker, "headline": ctx.words(p), "line": line},
         "data": {"day": day, "month": month, "progress": ctx.progress(p), "milestone": bool(p.get("milestone")), "calm": p.get("calm") or "bottom",
                  "ticks": [ctx.progress(q) for q in ctx.seq() if q.get("milestone")],
                  "index": next(i for i, q in enumerate(ctx.seq()) if q["id"] == p["id"]), "of": len(ctx.seq())}}
    if clip:
        b["clip"] = clip
    return b


def split(ctx, bid, mode, seconds, transition, text, d):
    a, z = ctx.first(), ctx.latest()
    return {"id": bid, "kind": "Split", "frames": sec(seconds), "transition": transition, "photos": [a["graded"], z["graded"]],
            "posts": [a["id"], z["id"]], "at": [a["date"], z["date"]], "text": text,
            "data": {"mode": mode, "layout": ctx.split, "labels": [ctx.say("then") + " · " + ctx.when(a, d), ctx.say("now") + " · " + ctx.when(z, d)],
                     "span": ctx.say(ctx.span["label"])}}


def alive(ctx, p, d, secs):
    return ctx.prompt(f"this photograph of {ctx.phrase} comes alive: the light shifts across it, a gentle movement, "
                      f"a slow push in, nothing in it changes shape", d, secs)


def board_timeline(ctx):
    d = "documentary"
    seq = ctx.seq()
    steps = sorted(range(1, len(seq)), key=lambda i: -(seq[i].get("change", 0) - seq[i - 1].get("change", 0)))[:2]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: the world of the subject",
              "prompt": ctx.prompt(f"{ctx.world()}, a time-lapse of one day passing", d, 3), "seconds": 3, "image": ctx.first()["graded"]}]
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(3.0), "transition": None, "photos": [ctx.first()["graded"]], "clip": "01",
              "text": {"kicker": f"{ctx.span['first'].replace('-', '.')} → {ctx.span['latest'].replace('-', '.')}", "headline": ctx.title(),
                       "line": ctx.say(f"{len(ctx.sub['posts'])} posts, oldest first")}}]
    n = 1
    for i, p in enumerate(seq):
        if i in steps:
            n += 1
            cid = f"{n:02d}"
            a = seq[i - 1]
            clips.append({"id": cid, "beat": f"lapse-{cid}", "role": "a time-lapse transition between two dates",
                          "prompt": ctx.prompt(f"a time-lapse of {ctx.phrase} changing over weeks, from the state in this photograph toward "
                                               f"something more finished, days flickering past in the light", d, 1.5),
                          "seconds": 1.5, "image": a["graded"]})
            beats.append({"id": f"lapse-{cid}", "kind": "ClipShot", "frames": sec(1.5), "transition": tr("fade", d), "clip": cid,
                          "photos": [a["graded"]], "text": {"kicker": ctx.say(f"{(dt.date.fromisoformat(p['date']) - dt.date.fromisoformat(a['date'])).days} days later")}})
        day, month = ctx.count(p)
        trn = tr("dip", d) if p.get("milestone") else tr("fade", d)
        beats.append(dated(ctx, p, d, 2.9 if p.get("milestone") or i in (0, len(seq) - 1) else 2.3, trn,
                           line=ctx.say(f"day {day}")))
    beats.append(split(ctx, "then-now", "split", 4.2, tr("wipe", d, "from-right" if ctx.split == "lr" else "from-bottom"),
                       {"kicker": ctx.span_line(), "headline": ctx.title(), "line": ctx.say(f"@{ctx.handle}")}, d))
    return finish(ctx, {"id": "1", "name": ctx.say("the timeline"), "direction": d,
                        "structure": "a straight timeline: every post dated, oldest to latest, a progress rail under it, the milestones marked",
                        "tone": "documentary", "clip_use": "still-first: generated time-lapse bridges across the biggest changes, and a generated opener",
                        "idea": ctx.say(f"the plain record: every photo with its date stamped in mono and a rail filling from the first day to the "
                                        f"latest, the milestones lit on it; two time-lapse bridges carry the biggest jumps, and the "
                                        f"first and the latest meet side by side at the end."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips})


def board_then_now(ctx):
    d = "editorial"
    seq = ctx.seq()
    way = "from-right" if ctx.split == "lr" else "from-bottom"
    clips = []
    beats = [split(ctx, "then-now-open", "split", 3.6, None,
                   {"kicker": f"@{ctx.handle}", "headline": ctx.say("then and now"), "line": ctx.span_line()}, d)]
    n = 0
    for i, p in enumerate(seq):
        key = i in (0, len(seq) - 1) or p.get("milestone") or p.get("video")
        clip = None
        if key:
            n += 1
            clip = f"{n:02d}"
            secs = 3 if p.get("milestone") or i in (0, len(seq) - 1) else 2
            c = {"id": clip, "beat": f"{p['id']}-{p['date']}", "seconds": secs, "image": p["graded"],
                 "role": "their own reel" if p.get("video") else "their photo brought to life"}
            if p.get("video"):
                c.update(prompt=None, source=p["video"])
            else:
                c["prompt"] = alive(ctx, p, d, secs)
            clips.append(c)
        beats.append(dated(ctx, p, d, 3.0 if key else 2.1, tr("edge", d, way, frames=14), clip=clip,
                           line=ctx.since(p)))
    changed = next((c["line"] for c in ctx.sub.get("changed") or [] if c["id"] != ctx.latest()["id"]), None)
    beats.append(split(ctx, "then-now", "wipe", 4.4, tr("edge", d, way, frames=14),
                       {"kicker": ctx.span_line(), "headline": ctx.title(), "line": ctx.say(short(re.sub(r"^\s*milestone\s*[:\-–]\s*", "", changed or "", flags=re.I), 70)) or None}, d))
    return finish(ctx, {"id": "2", "name": ctx.say("then and now"), "direction": d,
                        "structure": "a split-screen then/now whose divider becomes the wipe that carries every date in order, back to the pair",
                        "tone": "quiet editorial", "clip_use": "clip-first: the first, the latest and every milestone brought to life, their own reels playing",
                        "idea": ctx.say("the first and the latest side by side on paper white; the line between them starts to move and "
                                        "becomes the edge that wipes from each date to the next, each photo alive under a soft serif, "
                                        "until the pair is back together with the span between them."),
                        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips})


def board_chapters(ctx):
    d = "kinetic"
    seq = ctx.seq()
    heads = [0] + [i for i, p in enumerate(seq) if p.get("milestone") and 0 < i < len(seq) - 1] + [len(seq) - 1]
    clips = [{"id": "01", "beat": "opener", "role": "the opener", "prompt": ctx.prompt(f"{ctx.world()}, close and fast", d, 2),
              "seconds": 2, "image": ctx.first()["graded"]}]
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(2.6), "transition": None, "photos": [ctx.first()["graded"]], "clip": "01",
              "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say(ctx.span["label"]), "line": ctx.say(f"of {ctx.phrase}, in chapters")}}]
    n = 1
    for k, i in enumerate(heads):
        p = seq[i]
        title = ctx.say("day one") if k == 0 else ctx.say("now") if i == len(seq) - 1 else ctx.say(f"chapter {k + 1}")
        beats.append({"id": f"chapter-{k + 1}", "kind": "Chapter", "frames": sec(3.6), "transition": tr("bars" if k else "whip", d, "from-right"),
                      "post": p["id"], "at": p["date"], "photos": [p["graded"]],
                      "text": {"kicker": f"{title} · {ctx.when(p, d)}", "headline": ctx.words(p, 110, whole=True)},
                      "data": {"n": k + 1, "of": len(heads), "label": title, "progress": ctx.progress(p)}})
        stop = heads[k + 1] if k + 1 < len(heads) else len(seq)
        for j in range(i + 1, stop):
            q = seq[j]
            clip = None
            if q.get("video"):
                n += 1
                clip = f"{n:02d}"
                clips.append({"id": clip, "beat": f"{q['id']}-{q['date']}", "role": "their own reel", "prompt": None, "source": q["video"],
                              "seconds": 3, "image": q["graded"]})
            beats.append(dated(ctx, q, d, 2.4 if clip else 1.8, tr("whip", d, "from-left" if j % 2 else "from-right"), clip=clip,
                               line=ctx.since(q)))
    n += 1
    clips.append({"id": f"{n:02d}", "beat": "closer", "role": "the closer",
                  "prompt": ctx.prompt(f"{ctx.world()}, the camera pulling back to show everything made so far", d, 3), "seconds": 3,
                  "image": ctx.latest()["graded"]})
    beats.append({"id": "closer", "kind": "ClipShot", "frames": sec(3.4), "transition": tr("slide", d, "from-bottom"), "clip": f"{n:02d}",
                  "photos": [ctx.latest()["graded"]],
                  "text": {"kicker": f"@{ctx.handle}", "headline": ctx.title(), "line": ctx.span_line()}})
    return finish(ctx, {"id": "3", "name": ctx.say("chapters"), "direction": d,
                        "structure": "chapters: one per milestone, each opened by their own caption on screen as the narration",
                        "tone": "kinetic", "clip_use": "a generated opener and closer around their stills, their own reels playing in their chapter",
                        "idea": ctx.say("the story in their own words: a heavy chapter card for day one, for every milestone they named and for now, "
                                        "each carrying the caption they wrote that day, with the posts in between whipping past on the beat."),
                        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
                        "beats": beats, "clips": clips})


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a beat with weights, snapped to the music's beats when given."""
    w = (bt.get("data") or {}).get("weights") or []
    if len(w) < 2:
        return None
    tot = sum(w)
    cuts, acc = [], 0
    for x in w[:-1]:
        acc += x
        ideal = bt["frames"] * acc / tot
        if grid_s:
            ideal = snap_to((start + ideal) / FPS, grid_s, tol) * FPS - start
        cuts.append(int(round(ideal)))
    lo = sec(0.25)
    out = []
    for c in cuts:
        c = max(lo + (out[-1] if out else 0), min(bt["frames"] - lo, c))
        out.append(c)
    return out if len(set(out)) == len(out) else None


def finish(ctx, board):
    """Fills the system, drops empty beats, scales durations to the direction's target, adds the then/now card."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "subject": ctx.subject, "phrase": ctx.phrase, "span": ctx.span, "format": {"width": 1080, "height": 1920, "fps": FPS},
                  "system": ctx.system(d)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        if bt["photos"] or bt.get("clip"):
            beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (TARGET[d] * FPS + overlap) / whole if whole else 1
    for bt in beats:
        bt["frames"] = max(sec(0.9), int(round(bt["frames"] * k)))
        cuts = shot_cuts(bt)
        if cuts:
            bt["data"]["cuts"] = cuts
    board["beats"] = beats
    by = {b["id"]: b for b in beats}
    keep = [c for c in board["clips"] if c["beat"] in by]
    for c in keep:
        secs = max(1, round(by[c["beat"]]["frames"] / FPS))
        if c.get("prompt"):
            c["prompt"] = re.sub(r"\b[\d.]+ seconds", f"{secs} seconds", c["prompt"])
        c["seconds"] = secs
    board["clips"] = keep
    card = split(ctx, "then-now-card", "card", 3, None, {"kicker": f"@{ctx.handle}", "headline": ctx.say(ctx.span["label"]),
                                                          "line": ctx.span_line()}, d)
    card["settle"] = 0
    board["card"] = card
    return board


def film_seconds(beats):
    frames = sum(b["frames"] for b in beats) - sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    return frames / FPS


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t,
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]]})
        start += b["frames"]
    return out


def write_md(board, path):
    s = board["system"]
    lines = [f"# storyboard {board['id']}: {board['name']}", "", board["idea"], "",
             f"- structure: {board['structure']}", f"- tone: {board['tone']}", f"- generated clips: {board['clip_use']}",
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps, 1080x1920",
             f"- the span: {board['span']['first']} to {board['span']['latest']}, {board['span']['label']}",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for dates and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             "", "## beats", "", "| # | time | beat | component | post (date) | carried by | text | transition in |", "|---|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        post = f"{b['post']} ({b['at']})" if b.get("post") else (" and ".join(f"{p} ({a})" for p, a in zip(b["posts"], b["at"])) if b.get("posts") else "-")
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {post} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (their reel: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", "The then/now card (1080x1350) is the first and the latest photo side by side with the span, in this board's palette and type.", ""]
    path.write_text("\n".join(lines))


def all_photos(b):
    out = set()
    for x in b["beats"] + [b["card"]]:
        out |= set(x.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    if len(ctx.seq()) < 2:
        sys.exit("the subject needs at least two photos the film can carry; timeline.py names what it found")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    boards = [make(ctx) for make in (board_timeline, board_then_now, board_chapters)]
    referenced = sorted(set().union(*(all_photos(b) for b in boards)))
    grade.grade_photos([Path("build/photos") / Path(p).name for p in referenced])
    for b in boards:
        d = BOARDS / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        print(f"board {b['id']} {b['name']}: {len(b['beats'])} beats, {film_seconds(b['beats']):.1f} s, {len(b['clips'])} clips -> {d}/storyboard.md")
    stage_assets()
    return 0 if cmd_check(a) == 0 else 1


def stage_assets():
    """Fonts and the grain tile inside build/public/, the folder the renderer serves."""
    dst = grade.PUBLIC / "fonts"
    if not dst.exists():
        shutil.copytree(_env.SKILL / "fonts", dst, ignore=shutil.ignore_patterns("*.md"))
    fx = grade.PUBLIC / "fx" / "grain.png"
    if not fx.exists():
        fx.parent.mkdir(parents=True, exist_ok=True)
        grade.grain_tile(fx)


def load_boards():
    out = []
    for d in sorted(BOARDS.glob("*/storyboard.json")):
        out.append(_env.read_json(d))
    if not out:
        sys.exit("no storyboards: run storyboard.py draft first")
    return out


KINDS = {"Opener", "ClipShot", "Dated", "Split", "Chapter"}
PRESETS = set(design("transitions.json")["presets"])


def photo_beats(b):
    """The beats that carry one post of the timeline, in film order: (beat id, post id, date)."""
    return [(bt["id"], bt["post"], bt.get("at")) for bt in b["beats"] if bt.get("post")]


def order_issues(b, sub):
    """The timeline rules: every post real and dated as in the feed, oldest to latest, first and latest at the ends,
    every then/now pair the first and the latest."""
    posts = {p["id"]: p for p in (sub or {}).get("posts", [])}
    if not posts:
        return ["build/subject.json is missing: run research.py"]
    first, latest = sub["posts"][0], sub["posts"][-1]
    out = []
    pb = photo_beats(b)
    if len(pb) < 2:
        return [f"{len(pb)} photo beats: the film needs the first post and the latest at least"]
    for bid, pid, at in pb:
        if pid not in posts:
            out.append(f"{bid}: post {pid} is not one of the subject's posts")
        elif at != posts[pid]["date"]:
            out.append(f"{bid}: dated {at}, but post {pid} is from {posts[pid]['date']}")
    dates = [posts[pid]["date"] for _, pid, _ in pb if pid in posts]
    for (bid, _, _), (_, _, _), x, y in zip(pb, pb[1:], dates, dates[1:]):
        if y < x:
            out.append(f"photo beats out of date order after {bid}: {x} then {y}")
    if pb[0][1] != first["id"]:
        out.append(f"the first photo beat ({pb[0][0]}) is post {pb[0][1]}, not the earliest post {first['id']} ({first['date']})")
    if pb[-1][1] != latest["id"]:
        out.append(f"the last photo beat ({pb[-1][0]}) is post {pb[-1][1]}, not the latest post {latest['id']} ({latest['date']})")
    for x in b["beats"] + [b.get("card") or {}]:
        if x.get("kind") == "Split" and list(x.get("posts") or []) != [first["id"], latest["id"]]:
            out.append(f"{x['id']}: a then/now pair must be the first ({first['id']}) and the latest ({latest['id']}), has {x.get('posts')}")
    return out


def board_issues(b, sub=None):
    issues = []
    sub = sub if sub is not None else _env.read_json("build/subject.json")
    secs = film_seconds(b["beats"])
    if not LENGTH[0] <= secs <= LENGTH[1]:
        issues.append(f"length {secs:.1f} s is outside {LENGTH[0]}-{LENGTH[1]} s")
    clips = {c["id"] for c in b.get("clips", [])}
    for i, bt in enumerate(b["beats"]):
        if bt["kind"] not in KINDS:
            issues.append(f"{bt['id']}: unknown component {bt['kind']}")
        if bt["frames"] < sec(0.8):
            issues.append(f"{bt['id']}: {bt['frames']} frames is under 0.8 s")
        t = bt.get("transition")
        if i and not t:
            issues.append(f"{bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{bt['id']}: clip {bt['clip']} is not in the clip list")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    issues += order_issues(b, sub)
    card = b.get("card")
    if not card or card.get("kind") != "Split" or (card.get("data") or {}).get("mode") != "card":
        issues.append("no then/now card (a Split in card mode with the first and the latest photo)")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
    faces = {b["system"]["display"]["family"], b["system"]["text"]["family"]}
    if len(faces) > 2:
        issues.append("more than two type faces")
    return issues


def cmd_check(a):
    bad = 0
    boards = load_boards()
    sub = _env.read_json("build/subject.json")
    sigs = set()
    for b in boards:
        sigs.add((b["structure"], b["tone"], b["clip_use"]))
        iss = board_issues(b, sub)
        bad += len(iss)
        pb = photo_beats(b)
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'}, {film_seconds(b['beats']):.1f} s, "
              f"{len(pb)} photo beats {pb[0][2] if pb else '-'} to {pb[-1][2] if pb else '-'}")
        for i in iss:
            print("  -", i)
    if len(boards) != 3 or len(sigs) != 3:
        print("  - the three boards must differ on structure, tone and clip use")
        bad += 1
    return 1 if bad else 0


def sheet_frames(b):
    """Six frames that show the direction: settled moments spread across the film, the first and the last included."""
    cands = []
    for t in timeline(b["beats"]):
        sh = t["shots"]
        spans = list(zip(sh, sh[1:]))
        for lo, hi in spans:
            lo = max(lo, t["transition"])
            cands.append((t["id"], t["start"] + lo + int((hi - lo) * 0.7)))
    if len(cands) <= 6:
        return cands
    pick = sorted({round(i * (len(cands) - 1) / 5) for i in range(6)})
    return [cands[i] for i in pick]


def cmd_sheets(a):
    import film
    stage_assets()
    boards = load_boards()
    jobs = []
    for b in boards:
        props = film.props_for(b)
        fr = BOARDS / b["id"] / "frames"
        fr.mkdir(parents=True, exist_ok=True)
        for f in fr.glob("*.png"):
            f.unlink()
        for n, (bid, frame) in enumerate(sheet_frames(b), 1):
            out = (fr / f"{n:02d}.png").resolve()
            jobs.append({"type": "still", "composition": "Film", "props": props, "frame": frame, "scale": 0.5, "out": str(out)})
    rep = film.render_jobs(jobs, "build/sheets-report.json")
    _env.need("PIL")
    from PIL import Image
    for b in boards:
        frames = sorted((BOARDS / b["id"] / "frames").glob("*.png"))
        if not frames:
            continue
        ims = [Image.open(f).convert("RGB") for f in frames]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * 3 + 40, h * 2 + 30), "#111111")
        for i, im in enumerate(ims[:6]):
            sheet.paste(im, (10 + (i % 3) * (w + 10), 10 + (i // 3) * (h + 10)))
        sheet.save(BOARDS / b["id"] / "sheet.png")
        print(f"board {b['id']}: {len(frames)} frames -> {BOARDS / b['id'] / 'frames'}/, sheet {BOARDS / b['id'] / 'sheet.png'}")
    for f in rep.get("findings", []):
        print("finding:", f["text"][:300])
    return 0 if not rep.get("failed") else 1


def snap_to(t, grid, tol):
    best = min(grid, key=lambda g: abs(g - t)) if grid else t
    return best if abs(best - t) <= tol else t


def cmd_snap(a):
    win = _env.read_json("build/winner.json")
    bid = a.board or (win or {}).get("board")
    if not bid:
        sys.exit("no winner: run vote.py tally first (or pass --board N)")
    b = _env.read_json(BOARDS / str(bid) / "storyboard.json")
    music = _env.read_json("build/music.json") or {}
    grid_s = music.get("beats") or []
    down = music.get("downbeats") or grid_s
    beats = b["beats"]
    snapped = 0
    start = 0
    for i, bt in enumerate(beats):
        if i == 0:
            continue
        prev = beats[i - 1]
        t = (bt.get("transition") or {}).get("frames", 0)
        prev_start = start
        cut = (prev_start + prev["frames"] - t / 2) / FPS
        new_cut = snap_to(cut, down, 0.45)
        if new_cut == cut:
            new_cut = snap_to(cut, grid_s, 0.3)
        if new_cut != cut:
            snapped += 1
        prev["frames"] = max(sec(0.8), int(round(new_cut * FPS + t / 2 - prev_start)))
        start = prev_start + prev["frames"] - t
    last = beats[-1]
    end = (start + last["frames"]) / FPS
    if down:
        later = [g for g in down if g >= end - 0.4]
        if later and (later[0] * FPS - start) + sec(0.5) <= LENGTH[1] * FPS - start:
            last["frames"] = max(sec(2.5), int(round(later[0] * FPS - start)) + sec(0.5))
    for bt, t in zip(beats, timeline(beats)):
        cuts = shot_cuts(bt, grid_s, 0.25, t["start"])
        if cuts:
            bt["data"]["cuts"] = cuts
    b["beats"] = beats
    b["timeline"] = timeline(beats)
    b["seconds"] = film_seconds(beats)
    b["music"] = {**b.get("music", {}), **{k: music.get(k) for k in ("file", "bpm", "origin") if music.get(k)}}
    _env.write_json("build/film.json", b)
    print(f"board {bid}: {len(beats)} beats, {snapped} cuts moved onto the music, {b['seconds']:.1f} s -> build/film.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("--board")
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
