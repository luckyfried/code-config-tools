#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film of the same brand guide, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, the ten cards, assets, text, clips, 20-30 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/brand.json (brand.py system writes it from taste.json), build/taste.json, build/taste.md,
research.json and photo_index.json. Every board carries the same ten guide cards, in this order:
  01 palette  02 type  03 compositions  04 voice  05 pillars  06 cadence  07 aspire  08 stop  09 statement  10 week
and sets them in the brand's own type direction. The boards differ on how the guide is shown, on tone, and on how
generated clips are used:
  1  one card at a time   a reel that reveals the cards one by one on a dark field   bold        clips open the film
                          and bridge the two halves of the guide
  2  the swipe            a guide you swipe: the cards share one grid on a paper     calm        clips open the film
                          field and slide in, five and five                                      and carry the turn
  3  the poster           one poster of all ten panels; the camera moves panel to    cinematic   clips open the film
                          panel and pulls back to the whole                                      and play behind the poster
The film backgrounds are their photos in the film's grade; the photos on the cards are plain copies. The agent
may edit any storyboard.json (text, order, photos, prompts) before sheets; check validates it.
"""
import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import grade  # noqa: E402

DESIGN = _env.SKILL / "design"
BOARDS = Path("build/storyboards")
PLAIN = grade.PUBLIC / "plain"
FPS = 30
TARGET = {"1": 25, "2": 24, "3": 26}
LENGTH = (20, 30)
CARD_KINDS = ["palette", "type", "compositions", "voice", "pillars", "cadence", "aspire", "stop", "statement", "week"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")


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


def readable(c, bg, need=3.0):
    """Move c toward black or white until it reads on bg."""
    target = "#000000" if lum(bg) > 0.3 else "#ffffff"
    for i in range(21):
        x = mix(c, target, i / 20)
        if contrast(x, bg) >= need:
            return x
    return target


def pct(x):
    return f"{round((x or 0) * 100)}%"


class Ctx:
    def __init__(self):
        self.taste = _env.read_json("build/taste.json")
        if not self.taste:
            sys.exit("build/taste.json is missing: run research.py and write the taste profile first")
        if not Path("build/taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before storyboards")
        self.brand = _env.read_json("build/brand.json")
        if not self.brand:
            sys.exit("build/brand.json is missing: run brand.py system (and brand.py plan) first")
        self.research = _env.read_json("build/research.json") or {}
        self.index = _env.read_json("build/photo_index.json") or []
        self.picks = (_env.read_json("build/picks.json") or {}).get("chapters", {})
        self.handle = self.brand.get("handle") or self.taste.get("handle") or "you"
        self.lower = (self.brand.get("voice") or {}).get("case") == "lowercase"
        self.direction = (self.brand.get("type") or {}).get("direction") or "editorial"

    def say(self, s):
        """A line in their register: lowercase when they write lowercase."""
        if s is None:
            return None
        return s.lower() if self.lower else s

    def graded(self, src):
        """A photo of theirs as the graded file the film reads (relative to build/public)."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        return grade.graded_name(p) if p else None

    def plain(self, src):
        """A photo as a plain copy for the cards (relative to build/public): the guide shows their photos as posted."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        PLAIN.mkdir(parents=True, exist_ok=True)
        dst = PLAIN / Path(p).name
        if not dst.exists():
            shutil.copyfile(p, dst)
        return f"plain/{dst.name}"

    def roles(self):
        pal = self.brand.get("palette") or []
        by = {c.get("role"): c["hex"] for c in pal}
        lead = by.get("lead") or (pal[0]["hex"] if pal else "#b5654a")
        ground = by.get("ground") or max((c["hex"] for c in pal), key=lum, default="#efe6d6")
        ink = by.get("ink") or min((c["hex"] for c in pal), key=lum, default="#2b211b")
        accent = by.get("accent") or lead
        return lead, ground, ink, accent

    def system(self, field):
        d = self.direction
        types = design("type.json")[d]
        ease = design("easing.json")[d]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        lead, ground, ink, accent = self.roles()
        paper = mix(ground, "#ffffff", 0.45)
        card_ink = readable(ink, paper, 9)
        if field == "dark":
            bg = mix(ink, "#000000", 0.55)
            fg = readable(paper, bg, 10)
            fa = readable(lead, bg, 3.2)
        elif field == "lead":
            bg = lead
            fg = readable(paper, bg, 4.5)
            fa = readable(ground, bg, 3)
        else:
            bg = mix(ground, ink, 0.06)
            fg = readable(ink, bg, 9)
            fa = readable(lead, bg, 3.2)
        tex = self.taste.get("texture") or {}
        return {
            "direction": d, "field": field, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": fg, "accent": fa, "accent2": readable(accent, bg, 2.2), "muted": mix(fg, bg, 0.45),
                       "paper": paper, "card": paper, "cardInk": card_ink, "cardAccent": readable(lead, paper, 3.2),
                       "cardMuted": mix(card_ink, paper, 0.45),
                       "swatches": [{"hex": c["hex"], "name": self.say(c["name"])} for c in self.brand.get("palette", [])]},
            "texture": {"grain": round(float(tex.get("grain", 0)) * (0.5 if field == "paper" else 0.8), 3),
                        "vignette": float(tex.get("vignette", 0)) if field != "paper" else 0, "leaks": bool(tex.get("leaks"))},
            "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, seconds, camera):
        names = [c["name"] for c in self.brand.get("palette", [])[:4]]
        film = ", visible film grain" if (self.taste.get("texture") or {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(names)}. {camera}, soft natural light{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")

    def own_photos(self):
        """Their on-brand photos, best first: each pillar's most-liked posts, then the posts that lead each color."""
        if hasattr(self, "_own"):
            return self._own
        out = []
        pils = self.research.get("pillars") or []
        for k in range(3):
            for p in pils:
                ph = (p.get("photos") or [])[k:k + 1]
                out += ph
        out += [c.get("photo") for c in (self.taste.get("palette") or {}).get("feed", []) if c.get("photo")]
        seen, keep = set(), []
        for p in out:
            if p and p not in seen:
                seen.add(p)
                keep.append(p)
        if not keep:
            keep = list(self.picks.get("opener") or [])
        self._own = keep
        return keep

    def research_pillar(self, p):
        """The measured pillar a brand pillar came from: the same name, else the most shared words."""
        rp = self.research.get("pillars") or []
        for r in rp:
            if r["name"] == p["name"]:
                return r
        return max(rp, key=lambda r: len(set(r.get("words", [])) & set(p.get("words", []))), default={})

    def liked_photos(self, n=3):
        subj = (self.research.get("likes") or {}).get("subjects") or []
        accts = {a for s in subj[:2] for a in s.get("accounts", [])}
        rows = [r for r in self.index if r.get("kind") == "liked"]
        rows.sort(key=lambda r: (r.get("account") not in accts, -r.get("score", 0)))
        out = []
        for r in rows:
            p = self.plain(r["src"])
            if p and p not in out:
                out.append(p)
            if len(out) >= n:
                break
        return out


def first_line(cap):
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    return re.sub(r"\s+", " ", c.split("\n")[0]).strip()


def clean(cap):
    """A caption as it reads on a card: their words and line breaks, no trailing hashtag line."""
    lines = [ln.strip() for ln in (cap or "").split("\n")]
    while lines and (not lines[-1] or all(w.startswith("#") for w in lines[-1].split())):
        lines.pop()
    return "\n".join(ln for i, ln in enumerate(lines) if ln or (i and lines[i - 1]))


def cards(ctx):
    """The ten guide cards, from brand.json (the agent's words) with the numbers and photos research measured."""
    b = ctx.brand
    say = ctx.say
    r = ctx.research
    out = []
    pal = b.get("palette") or []
    out.append({"kind": "palette", "title": say("your palette"),
                "colors": [{"name": say(c["name"]), "hex": c["hex"], "share": c.get("share"), "role": c.get("role"),
                            "label": say(f"{pct(c.get('share'))} of your posts")} for c in pal],
                "line": say(f"{len(pal)} colors carry {pct(sum(c.get('share') or 0 for c in pal))} of your feed")})
    t = b.get("type") or {}
    voice = b.get("voice") or {}
    ex = [x for d in voice.get("devices", []) for x in d.get("examples", [])]
    out.append({"kind": "type", "title": say("your type"), "display": t.get("display"), "text": t.get("text"),
                "why": say(t.get("why")), "sample": b.get("statement"), "caption": clean(ex[0]) if ex else ""})
    comps = {c["name"]: c for c in r.get("compositions") or []}
    habits = []
    for name in (b.get("compositions") or [])[:3]:
        c = comps.get(name) or {}
        ph = next((p for p in (ctx.plain(e) for e in c.get("examples", [])) if p), None)
        habits.append({"name": say(name), "share": c.get("share"), "label": say(f"{pct(c.get('share'))} of your photos") if c.get("share") else "",
                       "photo": ph})
    out.append({"kind": "compositions", "title": say("how you frame"), "habits": habits})
    seen, three = set(), []
    for d in voice.get("devices", []):
        for x in d.get("examples", []):
            k = clean(x)
            if k and k not in seen and len(three) < 3:
                seen.add(k)
                three.append(k)
    out.append({"kind": "voice", "title": say("how you write"),
                "devices": [{"name": say(d["name"]), "share": d.get("share"), "label": pct(d.get("share"))} for d in voice.get("devices", [])[:4]],
                "examples": three, "case": voice.get("case")})
    pils = []
    for p in b.get("pillars") or []:
        rp = ctx.research_pillar(p)
        ph = next((x for x in (ctx.plain(e) for e in (rp.get("photos") or [])[:2]) if x), None)
        pils.append({"name": say(p["name"]), "share": p["share"], "label": pct(p["share"]), "words": [say(w) for w in p.get("words", [])[:3]],
                     "photo": ph})
    out.append({"kind": "pillars", "title": say("what you post about"), "pillars": pils})
    cad = b.get("cadence") or {}
    rc = r.get("cadence") or {}
    counts = rc.get("weekday_counts") or {}
    slots = {s["day"]: s["time"] for s in cad.get("slots", [])}
    out.append({"kind": "cadence", "title": say("when you post"),
                "days": [{"day": say(d[:3]), "posts": counts.get(d, 0), "time": slots.get(d)} for d in DAYS],
                "line": say(f"{cad.get('per_week')} posts a week; {pct(rc.get('on_rhythm'))} land on these days, within the hour"
                            if rc.get("on_rhythm") is not None else f"{cad.get('per_week')} posts a week"),
                "timezone": cad.get("timezone")})
    asp = b.get("aspire") or {}
    out.append({"kind": "aspire", "title": say("what your likes say"),
                "colors": [{"name": say(c["name"]), "hex": c["hex"]} for c in asp.get("palette", [])[:5]],
                "subjects": [say(s) for s in asp.get("subjects", [])[:3]], "line": say(asp.get("line")),
                "photos": ctx.liked_photos(3)})
    out.append({"kind": "stop", "title": say("what to let go of"),
                "items": [{"line": say(s["line"]), "why": say(s.get("why"))} for s in (b.get("stop") or [])[:3]]})
    out.append({"kind": "statement", "title": say("your brand in one line"), "statement": b.get("statement"),
                "handle": f"@{ctx.handle}", "swatches": [c["hex"] for c in pal]})
    week = []
    for e in b.get("first_week") or []:
        week.append({"date": e["date"], "day": say(e.get("day") or ""), "kind": say(e.get("kind")), "time": e.get("time") or "",
                     "pillar": say(e.get("pillar")), "caption": first_line(e.get("caption"))})
    out.append({"kind": "week", "title": say("your first week"), "days": week})
    for n, c in enumerate(out, 1):
        c["n"] = n
        c["id"] = f"{n:02d}-{c['kind']}"
    return out


def tr(preset, d=None, frames=None, direction="editorial"):
    f = frames or design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def opener(ctx, seconds, clip, line):
    own = ctx.own_photos()
    return {"id": "opener", "kind": "Opener", "frames": sec(seconds), "transition": None,
            "photos": [ctx.graded(own[0])] if own else [], "clip": clip,
            "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("your brand kit"), "line": line}}


def bg_photo(ctx, k):
    own = ctx.own_photos()
    return [ctx.graded(own[k % len(own)])] if own else []


def board_reveal(ctx, deck):
    d = ctx.direction
    beats = [opener(ctx, 2.4, "01", ctx.say("ten cards, read from your own feed"))]
    for k, c in enumerate(deck):
        if k == 5:
            beats.append({"id": "bridge", "kind": "ClipShot", "frames": sec(1.2), "transition": tr("whip", "from-right", direction=d),
                          "clip": "02", "photos": bg_photo(ctx, 5), "text": {"headline": ctx.say("and where it goes next")}})
        trn = tr("slide", "from-bottom" if k % 2 else "from-right", direction=d) if k else tr("dip", direction=d)
        beats.append({"id": f"card-{c['n']:02d}", "kind": "Reveal", "frames": sec(3.0 if c["kind"] == "statement" else 2.1),
                      "transition": trn, "photos": bg_photo(ctx, k), "data": {"card": c["n"], "of": len(deck)}})
    names = ", ".join(c["name"] for c in ctx.brand.get("palette", [])[:3])
    clips = [{"id": "01", "beat": "opener", "role": "the opener: the world of their feed",
              "prompt": ctx.prompt(f"an establishing shot of the world this feed lives in, built from {names}: "
                                   f"{', '.join(p['name'] for p in ctx.brand.get('pillars', [])[:2])}, light moving slowly across it",
                                   3, "a slow push-in, shallow depth of field"), "seconds": 3, "image": None},
             {"id": "02", "beat": "bridge", "role": "a transition between the two halves of the guide",
              "prompt": ctx.prompt(f"an abstract sweep of {names} paint and light filling the frame from right to left", 1,
                                   "a fast lateral whip, macro detail"), "seconds": 1, "image": None}]
    return finish(ctx, {"id": "1", "name": ctx.say("one card at a time"), "field": "dark",
                        "structure": "a reel that reveals the ten cards one at a time", "tone": "bold",
                        "clip_use": "a generated opener for the feed's world, and a generated bridge between the halves",
                        "idea": ctx.say("each card lands on its own beat, full and readable, on a dark field cut from your photos; "
                                        "the statement holds longest."),
                        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
                        "beats": beats, "clips": clips}, deck)


def board_swipe(ctx, deck):
    d = ctx.direction
    own = ctx.own_photos()
    beats = [opener(ctx, 2.2, "01", ctx.say("swipe through your style guide")),
             {"id": "swipe-1", "kind": "Swipe", "frames": sec(9.0), "transition": tr("slide", "from-right", direction=d),
              "photos": bg_photo(ctx, 1), "data": {"cards": [c["n"] for c in deck[:5]], "weights": [1] * 5}},
             {"id": "turn", "kind": "ClipShot", "frames": sec(1.4), "transition": tr("wipe", "from-right", direction=d), "clip": "02",
              "photos": bg_photo(ctx, 2), "text": {"headline": ctx.say("now, the plan")}},
             {"id": "swipe-2", "kind": "Swipe", "frames": sec(9.0), "transition": tr("wipe", "from-right", direction=d),
              "photos": bg_photo(ctx, 3), "data": {"cards": [c["n"] for c in deck[5:]], "weights": [1] * 5}},
             {"id": "closer", "kind": "ClipShot", "frames": sec(2.6), "transition": tr("dip", direction=d), "photos": bg_photo(ctx, 4),
              "text": {"kicker": f"@{ctx.handle}", "headline": ctx.brand.get("statement")}}]
    names = ", ".join(c["name"] for c in ctx.brand.get("palette", [])[:3])
    turn = own[2] if len(own) > 2 else (own[0] if own else None)
    clips = [{"id": "01", "beat": "opener", "role": "the opener: their colors as a place",
              "prompt": ctx.prompt(f"a sunlit tabletop and wall in {names}, objects arranged with care, the light shifting", 3,
                                   "a slow overhead drift, 35mm film look"), "seconds": 3, "image": None},
             {"id": "02", "beat": "turn", "role": "the turn from the guide to the plan: one of their photos brought to life",
              "prompt": ctx.prompt("this photograph comes alive: the light shifts across it, a gentle movement, a slow push in", 2,
                                   "a slow push-in"), "seconds": 2, "image": ctx.graded(turn) if turn else None}]
    return finish(ctx, {"id": "2", "name": ctx.say("the swipe"), "field": "paper",
                        "structure": "a swipeable guide: the cards share one grid and slide in, five and five", "tone": "calm",
                        "clip_use": "a generated opener in their colors, and one of their photos brought to life for the turn",
                        "idea": ctx.say("the guide as you would swipe it: one grid, one card after another sliding in on paper, "
                                        "a breath at the turn, and the statement to close."),
                        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips}, deck)


def board_poster(ctx, deck):
    d = ctx.direction
    names = ", ".join(c["name"] for c in ctx.brand.get("palette", [])[:3])
    weights = [1.6, 1.3] + [1.0] * len(deck) + [2.2]
    beats = [opener(ctx, 2.4, "01", ctx.say("your brand on one page")),
             {"id": "poster", "kind": "Poster", "frames": sec(22.5), "transition": tr("iris", direction=d), "clip": "02",
              "photos": bg_photo(ctx, 1), "data": {"cards": [c["n"] for c in deck], "weights": weights,
                                                   "header": {"handle": f"@{ctx.handle}", "statement": ctx.brand.get("statement")}}}]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: the world of their feed",
              "prompt": ctx.prompt(f"an establishing shot of a quiet street and a table in {names}, light moving slowly across it", 3,
                                   "handheld, natural light, observational"), "seconds": 3, "image": None},
             {"id": "02", "beat": "poster", "role": "the poster's backdrop: their palette as moving light",
              "prompt": ctx.prompt(f"slow drifting fields of {names} light and soft shadow on a plaster wall", 6,
                                   "a locked-off camera, very slow drift"), "seconds": 6, "image": None}]
    return finish(ctx, {"id": "3", "name": ctx.say("the poster"), "field": "lead",
                        "structure": "one poster of all ten panels: the camera moves panel to panel, then pulls back", "tone": "cinematic",
                        "clip_use": "a generated opener, and their palette as moving light behind the poster",
                        "idea": ctx.say("the whole guide is one poster in your lead color; one unbroken camera reads it panel by "
                                        "panel and pulls back so the page is whole."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips}, deck)


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a many-shot beat (Swipe, Poster), from its weights, snapped to the music when given."""
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


def finish(ctx, board, deck):
    """Fills the system and the cards, drops empty beats, scales durations to the board's target length."""
    board.update({"handle": ctx.handle, "format": {"width": 1080, "height": 1920, "fps": FPS},
                  "direction": ctx.direction, "system": ctx.system(board["field"]), "cards": copy.deepcopy(deck)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        if bt["kind"] in ("Opener", "ClipShot") and not bt["photos"] and not bt.get("clip"):
            continue
        beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (TARGET[board["id"]] * FPS + overlap) / whole if whole else 1
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
            c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
    board["clips"] = keep
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
             f"- how the guide is shown: {board['structure']}", f"- tone: {board['tone']}", f"- generated clips: {board['clip_use']}",
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps, 1080x1920",
             f"- music: {board['music']['direction']}",
             f"- type ({s['direction']}): {s['display']['family']} for headlines and the statement, {s['text']['family']} for labels "
             f"and captions; scale {s['scale']}",
             f"- field: {s['field']} ({s['colors']['bg']}), ink {s['colors']['ink']}, accent {s['colors']['accent']}; cards on "
             f"{s['colors']['card']} in {s['colors']['cardInk']}; palette {', '.join(w['name'] + ' ' + w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             "", "## the ten cards", ""]
    for c in board["cards"]:
        lines.append(f"{c['n']:>2}. {c['kind']}: {c['title']}")
    lines += ["", "## beats", "", "| # | time | beat | component | carried by | text or cards | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        data = b.get("data") or {}
        if data.get("card"):
            txt = f"card {data['card']}"
        elif data.get("cards"):
            txt = "cards " + ", ".join(str(n) for n in data["cards"])
        else:
            txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{img}: {c.get('prompt')}")
    lines += ["", "The ten cards (1080x1350 each) are rendered from this board's system into out/cards/.", ""]
    path.write_text("\n".join(lines))


def card_photos(c):
    out = set()
    for key in ("habits", "pillars"):
        out |= {x["photo"] for x in c.get(key, []) if x.get("photo")}
    out |= {p for p in c.get("photos", []) if p}
    return out


def all_photos(b):
    out = set()
    for x in b["beats"]:
        out |= set(x.get("photos") or [])
    for c in b.get("cards", []):
        out |= card_photos(c)
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    deck = cards(ctx)
    boards = [make(ctx, deck) for make in (board_reveal, board_swipe, board_poster)]
    referenced = sorted(p for p in set().union(*(all_photos(b) for b in boards)) if p.startswith("graded/"))
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


KINDS = {"Opener", "ClipShot", "Reveal", "Swipe", "Poster"}
PRESETS = set(design("transitions.json")["presets"])
PLACEHOLDER = ("{", "}", "TODO", "lorem", "None", "XX")


def text_of(x):
    if isinstance(x, dict):
        return [t for v in x.values() for t in text_of(v)]
    if isinstance(x, list):
        return [t for v in x for t in text_of(v)]
    return [x] if isinstance(x, str) else []


def deck_issues(b):
    issues = []
    deck = b.get("cards") or []
    if [c.get("kind") for c in deck] != CARD_KINDS:
        issues.append(f"the cards must be the ten, in order: {', '.join(CARD_KINDS)}")
    for c in deck:
        for v in text_of({k: v for k, v in c.items() if k not in ("photo", "photos")}):
            if any(x in v for x in PLACEHOLDER):
                issues.append(f"card {c.get('n')}: placeholder in text: {v[:60]}")
    voice = next((c for c in deck if c.get("kind") == "voice"), {})
    if len(voice.get("examples") or []) != 3:
        issues.append("card 4 (voice) needs three real captions of theirs")
    week = next((c for c in deck if c.get("kind") == "week"), {})
    if len(week.get("days") or []) != 7:
        issues.append("card 10 (week) needs the plan's first seven days: run brand.py plan")
    shown = []
    for b_ in b["beats"]:
        data = b_.get("data") or {}
        shown += [data["card"]] if data.get("card") else list(data.get("cards") or [])
    if sorted(shown) != list(range(1, len(deck) + 1)):
        issues.append(f"the film shows cards {shown}; every card shows once")
    return issues


def board_issues(b):
    issues = []
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
        for v in text_of(bt.get("text") or {}):
            if any(x in v for x in PLACEHOLDER):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    issues += deck_issues(b)
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
    return issues


def cmd_check(a):
    bad = 0
    boards = load_boards()
    sigs = set()
    for b in boards:
        sigs.add((b["structure"], b["tone"], b["clip_use"]))
        iss = board_issues(b)
        bad += len(iss)
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'}, {film_seconds(b['beats']):.1f} s")
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
        for lo, hi in zip(sh, sh[1:]):
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
