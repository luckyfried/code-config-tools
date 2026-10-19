#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different launch film of the same product, each with a rendered style
sheet, and every board carrying the three teaser stories, the countdown card and the feed post in its own palette
and type. Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, cards, the date, product assets, text, clips, 15-30 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (the launch as the person gave it, what they said, the two palettes and where they
meet, the hooks ranked by response, type direction, pacing, register), then build/stats.json, picks.json and
research.json. The three boards differ on structure, tone and how generated clips are used:
  1  the trilogy      tease, tease harder, reveal: the film sums up the three stories     editorial    clip-first;
                      the product's world opens the reveal, its own footage the hero moment
  2  the hype cut     20 s built on their best hook line, the product cut on the beat      kinetic      still-first;
                      generated light sweeps are the reveal transitions
  3  the countdown    the countdown series opens the film: the days falling to the date    documentary  still-first;
                      the product's world between the count and the reveal, its own footage after
Every product beat carries a still from the product's own assets (its folder or link) when there is one; a clip that
does not arrive is replaced by an animated treatment of that still. Cards: three stories (1080x1920: tease, tease
harder, reveal), the countdown card (1080x1920, the date the person gave), the feed post (1080x1350).
The agent may edit any storyboard.json (text, order, photos, prompts) before sheets; check validates it.
"""
import argparse
import calendar
import copy
import datetime as dt
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
FPS = 30
TARGET = {"editorial": 26, "kinetic": 20, "documentary": 22}
LENGTH = (15, 30)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}
CARDS = ("stories", "countdown", "feed")


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
        self.stats = _env.read_json("build/stats.json") or {}
        self.picks = _env.read_json("build/picks.json") or {}
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.lib = _env.read_json("build/library.json") or {}
        self.handle = self.stats.get("handle") or self.taste.get("handle") or "you"
        self.year = int(self.stats.get("year") or self.taste.get("year"))
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.launch = {**(self.lib.get("launch") or {}), **{k: v for k, v in (self.taste.get("launch") or {}).items() if v is not None}}
        self.product = self.launch.get("product") or "the new thing"
        self.date = self.launch.get("date")
        self.date_label = self.launch.get("date_label") or self.launch.get("date_text") or "soon"
        self.days = days_to(self.date) if self.date else None

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def photo(self, src):
        """A prepared photo as the graded file the renderer reads (relative to build/public/)."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        return grade.graded_name(p)

    def stills(self):
        """The product's stills as graded files, best first (its own asset folder or link; else posts about it)."""
        return [g for g in (self.photo(e["photo"]) for e in self.picks.get("product") or []) if g]

    def still(self, i):
        st = self.stills() or self.feed()
        return st[i % len(st)] if st else None

    def footage(self):
        return [{"file": e["file"], "poster": self.photo(e["poster"])} for e in self.picks.get("footage") or [] if e.get("poster")]

    def feed(self):
        return [g for g in (self.photo(p) for p in (self.picks.get("chapters") or {}).get("feed") or []) if g]

    def hook(self):
        """Their best hook line (the opener of the post that drew the most response), in their register."""
        said = (self.taste.get("said") or {}).get("hook")
        h = said or (self.taste.get("best_hook") or {}).get("hook") or ""
        return self.say(short(h, 64)) if h else None

    def top_photo(self, rank=1):
        for e in self.picks.get("top") or []:
            if e["rank"] == rank:
                return self.photo(e["photo"])
        return None

    def days_line(self):
        if self.days is None:
            return self.say("soon")
        if self.days <= 0:
            return self.say("out now")
        return self.say(f"{self.days} day{'s' if self.days != 1 else ''} to go")

    def date_data(self):
        d = {"date": self.date, "label": self.say(self.date_label), "days": self.days}
        if self.date:
            x = dt.date.fromisoformat(self.date)
            d.update(day=x.day, month=self.say(calendar.month_name[x.month]), weekday=self.say(calendar.day_name[x.weekday()]))
        return d

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        pal = self.taste.get("palette", {})
        year = [s["hex"] for s in pal.get("year", []) if s.get("hex")] or ["#6b5440", "#b8a17f"]
        prod = [s["hex"] for s in pal.get("product", []) if s.get("hex")]
        allc = year + prod
        darkest = min(allc, key=lum)
        lightest = max(allc, key=lum)
        vivid = sorted(prod or year, key=lambda h: -sat(h) * (0.4 + lum(h)))
        theirs = sorted(year, key=lambda h: -sat(h) * (0.4 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(theirs[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = vivid[0]
            accent2 = vivid[1] if len(vivid) > 1 else theirs[0]
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
            accent2 = theirs[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        swatches = [{"hex": s["hex"], "name": self.say(s.get("name") or "")} for s in (pal.get("product") or pal.get("year") or [])][:5]
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def colors_said(self):
        pal = self.taste.get("palette", {})
        return [s.get("name") for s in (pal.get("product") or [])[:3] if s.get("name")] + \
               [s.get("name") for s in (pal.get("year") or [])[:2] if s.get("name")]

    def prompt(self, subject, direction, seconds):
        t = self.taste
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in self.colors_said() if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")


def days_to(iso):
    try:
        return (dt.date.fromisoformat(iso) - dt.date.today()).days
    except (TypeError, ValueError):
        return None


def short(cap, limit=60):
    """A caption's lead line for the screen: no hashtags or emoji, cut at a clause or a word, never on a function word."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    for sep in (". ", ": ", "; ", " - "):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def tease(bid, photo, frm, to, seconds, transition, text):
    """The product behind a mask that opens from one level to another (0 hidden, 1 whole)."""
    return {"id": bid, "kind": "Tease", "frames": sec(seconds), "transition": transition, "photos": [photo], "text": text,
            "data": {"from": frm, "to": to, "product": True}}


def date_beat(ctx, bid, seconds, transition, text, photo, ticks=None):
    """The date the person gave, over a product still; with ticks, the days counting down to it first."""
    data = {**ctx.date_data(), "product": photo in ctx.stills()}
    if ticks:
        data["ticks"] = ticks
        data["weights"] = [1] * len(ticks) + [1.6]
    return {"id": bid, "kind": "DateCard", "frames": sec(seconds), "transition": transition, "photos": [photo], "text": text,
            "data": data}


def clip_beat(bid, seconds, transition, clip, photo, text=None, product=True):
    b = {"id": bid, "kind": "ClipShot", "frames": sec(seconds), "transition": transition, "photos": [photo], "text": text or {},
         "data": {"product": product}}
    if clip:
        b["clip"] = clip
    return b


def hook_beat(bid, seconds, transition, text, photo, style, product=False):
    return {"id": bid, "kind": "Hook", "frames": sec(seconds), "transition": transition, "photos": [photo], "text": text,
            "data": {"style": style, "product": product}}


def ticks_for(days):
    if not days or days <= 0:
        return None
    marks = [m for m in (60, 30, 21, 14, 7, 3, 1) if m < days]
    return [days] + marks[-4:]


def world_clip(ctx, cid, beat, d, secs):
    colors = ", ".join(dict.fromkeys(c for c in ctx.colors_said()[:3] if c)) or "its colors"
    return {"id": cid, "beat": beat, "role": "the product's world", "seconds": secs, "image": None,
            "prompt": ctx.prompt(f"the world of {ctx.product}, abstract: slow shapes, glazed surfaces and light moving in {colors}, "
                                 f"textures that echo it; the product itself is not shown", d, secs)}


def hero_clip(ctx, cid, beat, d, secs, photo):
    f = ctx.footage()
    if f:
        return {"id": cid, "beat": beat, "role": "the product's own footage", "prompt": None, "source": f[0]["file"],
                "seconds": secs, "image": f[0]["poster"]}
    return {"id": cid, "beat": beat, "role": "a hero moment of the product", "seconds": secs, "image": photo,
            "prompt": ctx.prompt(f"a hero moment for {ctx.product}: this product still comes alive, the camera moving slowly "
                                 f"around it, light gliding across its surface", d, secs)}


def sweep_clip(ctx, cid, beat, d, secs):
    colors = ", ".join(dict.fromkeys(c for c in ctx.colors_said()[:3] if c)) or "its colors"
    return {"id": cid, "beat": beat, "role": "a reveal transition", "seconds": secs, "image": None,
            "prompt": ctx.prompt(f"an abstract reveal transition: a fast sweep of light through colored glass in {colors}, "
                                 f"streaks left to right opening onto a bright center", d, secs)}


def name(ctx):
    return ctx.say(ctx.product)


def board_trilogy(ctx):
    d = "editorial"
    hero = ctx.still(0)
    beats = [
        tease("tease", hero, 0.0, 0.16, 3.0, None, {"kicker": f"@{ctx.handle}", "headline": ctx.say("something's coming")}),
        tease("tease-harder", hero, 0.16, 0.45, 3.0, tr("wipe", d, "from-right"),
              {"kicker": ctx.say(ctx.date_label), "headline": ctx.say("nearly ready")}),
        clip_beat("world", 2.4, tr("dip", d), "01", ctx.still(1)),
        tease("reveal", hero, 0.45, 1.0, 4.0, tr("match", d), {"kicker": ctx.say("introducing"), "headline": name(ctx)}),
        clip_beat("hero", 3.2, tr("fade", d), "02", ctx.still(2)),
        date_beat(ctx, "date", 3.4, tr("wipe", d, "from-left"),
                  {"kicker": name(ctx), "headline": ctx.say(ctx.date_label), "line": ctx.days_line()}, ctx.still(1)),
        tease("closer", ctx.still(3), 1.0, 1.0, 3.0, tr("dip", d),
              {"kicker": f"@{ctx.handle}", "headline": name(ctx), "line": ctx.say(f"out {ctx.date_label}")}),
    ]
    clips = [world_clip(ctx, "01", "world", d, 2), hero_clip(ctx, "02", "hero", d, 3, ctx.still(2))]
    return finish(ctx, {"id": "1", "name": ctx.say("the trilogy"), "direction": d,
                        "structure": "tease, tease harder, reveal: the film sums up the three stories", "tone": "quiet editorial",
                        "clip_use": "clip-first: the product's world opens the reveal, its own footage is the hero moment",
                        "idea": ctx.say(f"the three stories as one film: a sliver of {ctx.product}, then more of it, then all of it on "
                                        f"paper-white pages in a soft serif, the date set like a printed invitation."),
                        "music": {"direction": "warm, unhurried, 84 bpm: soft keys, brushed drums, a lift at the reveal", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips})


def board_hype(ctx):
    d = "kinetic"
    hero = ctx.still(0)
    style = (ctx.taste.get("best_hook") or {}).get("style") or "statement"
    beats = [
        hook_beat("hook", 2.6, None, {"kicker": f"@{ctx.handle}", "headline": ctx.hook() or name(ctx)}, hero, style, product=True),
    ]
    for i in range(4):
        beats.append(clip_beat(f"cut-{i + 1}", 0.9, tr("whip", d, "from-right" if i % 2 == 0 else "from-left"), None, ctx.still(i + 1)))
    beats += [
        clip_beat("sweep", 1.2, tr("whip", d, "from-right"), "01", ctx.still(1)),
        tease("reveal", hero, 0.25, 1.0, 3.0, tr("bars", d), {"kicker": ctx.say("introducing"), "headline": name(ctx)}),
        clip_beat("hero", 2.4, tr("whip", d, "from-left"), "02", ctx.still(2)),
        date_beat(ctx, "date", 2.4, tr("slide", d, "from-bottom"),
                  {"kicker": name(ctx), "headline": ctx.say(ctx.date_label), "line": ctx.days_line()}, ctx.still(3)),
        tease("closer", ctx.still(1), 1.0, 1.0, 2.6, tr("bars", d),
              {"kicker": f"@{ctx.handle}", "headline": name(ctx), "line": ctx.say(ctx.date_label)}),
    ]
    clips = [sweep_clip(ctx, "01", "sweep", d, 1), hero_clip(ctx, "02", "hero", d, 2, ctx.still(2))]
    best = (ctx.taste.get("best_hook") or {}).get("response")
    return finish(ctx, {"id": "2", "name": ctx.say("the hype cut"), "direction": d,
                        "structure": "20 s built on their best hook line, the product cut on the beat", "tone": "kinetic",
                        "clip_use": "still-first: generated light sweeps are the reveal transitions, the product's own footage the hero",
                        "idea": ctx.say(f"their best hook ({style}, the opener that drew {best} comments and saves) slams in over "
                                        f"{ctx.product}, then four hard cuts on the beat, a light sweep, the name in heavy type and the date."),
                        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
                        "beats": beats, "clips": clips})


def board_countdown(ctx):
    d = "documentary"
    hero = ctx.still(0)
    about = (ctx.stats.get("product_posts") or [])
    words = ctx.say(short(about[0]["caption"], 56)) if about else ctx.hook()
    words_photo = ctx.photo(about[0]["media"]) if about else ctx.top_photo(1)
    beats = [
        date_beat(ctx, "count", 5.0, None, {"kicker": name(ctx), "headline": ctx.say(ctx.date_label), "line": ctx.days_line()},
                  ctx.still(2), ticks=ticks_for(ctx.days)),
        clip_beat("world", 2.6, tr("iris", d), "01", ctx.still(1)),
        hook_beat("words", 2.8, tr("fade", d), {"kicker": f"@{ctx.handle}", "headline": words}, words_photo or hero, "theirs") if words else None,
        tease("tease", hero, 0.0, 0.35, 2.6, tr("dip", d), {"headline": ctx.say("almost here")}),
        tease("reveal", hero, 0.35, 1.0, 3.4, tr("iris", d), {"kicker": ctx.say("introducing"), "headline": name(ctx)}),
        clip_beat("hero", 3.0, tr("fade", d), "02", ctx.still(2)),
        date_beat(ctx, "date", 3.0, tr("dip", d), {"kicker": name(ctx), "headline": ctx.say(ctx.date_label), "line": ctx.days_line()},
                  ctx.still(3)),
    ]
    clips = [world_clip(ctx, "01", "world", d, 3), hero_clip(ctx, "02", "hero", d, 3, ctx.still(2))]
    return finish(ctx, {"id": "3", "name": ctx.say("the countdown"), "direction": d,
                        "structure": "the countdown series opens the film: the days fall to the date, then the reveal", "tone": "documentary",
                        "clip_use": "still-first: the product's world between the count and the reveal, its own footage after",
                        "idea": ctx.say(f"the countdown cards come first: the days fall in mono numerals over {ctx.product}, their own "
                                        f"words about it, then the reveal and the date, like a field log of the last weeks."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a ticking pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": [b for b in beats if b], "clips": clips})


def cards(ctx):
    """The four still formats every board carries: three stories, the countdown card, the feed post."""
    hero = ctx.still(0)
    def still(bid, kind, photo, text, data):
        return {"id": bid, "kind": kind, "frames": sec(3), "transition": None, "settle": 0, "photos": [photo], "text": text, "data": data}
    stories = [
        still("story-1", "Tease", hero, {"kicker": f"@{ctx.handle}", "headline": ctx.say("something's coming"), "line": ctx.say(ctx.date_label)},
              {"from": 0.16, "to": 0.16, "product": True, "step": "tease"}),
        still("story-2", "Tease", hero, {"kicker": ctx.say(ctx.date_label), "headline": ctx.say("nearly ready"), "line": ctx.days_line()},
              {"from": 0.45, "to": 0.45, "product": True, "step": "tease harder"}),
        still("story-3", "Tease", hero, {"kicker": ctx.say("introducing"), "headline": name(ctx), "line": ctx.say(f"out {ctx.date_label}")},
              {"from": 1.0, "to": 1.0, "product": True, "step": "reveal"}),
    ]
    countdown = still("countdown", "DateCard", ctx.still(1),
                      {"kicker": name(ctx), "headline": ctx.say(ctx.date_label), "line": ctx.days_line()},
                      {**ctx.date_data(), "product": True})
    feed = still("feed", "Tease", ctx.still(0), {"kicker": f"@{ctx.handle}", "headline": name(ctx), "line": ctx.say(f"out {ctx.date_label}")},
                 {"from": 1.0, "to": 1.0, "product": True})
    return {"stories": stories, "countdown": countdown, "feed": feed}


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a many-shot beat, from its weights, snapped to the music's beats when given."""
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
    """Fills the system, drops empty beats, scales durations to the direction's target, adds the four still formats."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "year": ctx.year, "product": ctx.product, "launch": {"date": ctx.date, "label": ctx.date_label},
                  "format": {"width": 1080, "height": 1920, "fps": FPS}, "system": ctx.system(d)})
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
        bt["frames"] = max(sec(0.8), int(round(bt["frames"] * k)))
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
    board.update(cards(ctx))
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
             f"- the launch: {board['product']}, {board['launch']['label']}" + (f" ({board['launch']['date']})" if board['launch'].get('date') else ""),
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps, 1080x1920",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             "", "## beats", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(str(v) for v in (b.get("text") or {}).values() if v)
        assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
        if (b.get("data") or {}).get("product"):
            assets += " (product)"
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        if (b.get("data") or {}).get("ticks"):
            assets += f"; counts {', '.join(str(x) for x in b['data']['ticks'])}"
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (the product's own footage: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from the still {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; the product footage'}")
    lines += ["", "## the stills", "", "| card | format | text |", "|---|---|---|"]
    for c in card_list(board):
        lines.append(f"| {c[0]} | {c[1]} | {' / '.join(str(v) for v in (c[2].get('text') or {}).values() if v)} |")
    lines.append("")
    path.write_text("\n".join(lines))


def card_list(b):
    """(name, format, beat) for every still the board carries."""
    out = [(f"story {i + 1}", "story", x) for i, x in enumerate(b.get("stories") or [])]
    if b.get("countdown"):
        out.append(("countdown", "story", b["countdown"]))
    if b.get("feed"):
        out.append(("feed", "feed", b["feed"]))
    return out


def all_photos(b):
    out = set()
    for x in b["beats"] + [c[2] for c in card_list(b)]:
        out |= set(x.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    if not ctx.stills():
        sys.exit("no product still and no photo of theirs to stand in: picks.py names what could not be opened")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    grade.grade_photos()
    boards = [make(ctx) for make in (board_trilogy, board_hype, board_countdown)]
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


KINDS = {"Hook", "Tease", "DateCard", "ClipShot"}
PRESETS = set(design("transitions.json")["presets"])


def product_files():
    """Every graded file made from the product's own assets (stills and footage posters), when it has any."""
    picks = _env.read_json("build/picks.json") or {}
    own = [e for e in picks.get("product") or [] if e.get("own")]
    files = {grade.graded_name(e["photo"]) for e in own} | {grade.graded_name(e["poster"]) for e in picks.get("footage") or []}
    return files


def board_issues(b):
    issues = []
    secs = film_seconds(b["beats"])
    if not LENGTH[0] <= secs <= LENGTH[1]:
        issues.append(f"length {secs:.1f} s is outside {LENGTH[0]}-{LENGTH[1]} s")
    clips = {c["id"] for c in b.get("clips", [])}
    own = product_files()
    launch = (_env.read_json("build/library.json") or {}).get("launch") or {}
    product = (b.get("product") or "").lower()
    for i, bt in enumerate(b["beats"] + [c[2] for c in card_list(b)]):
        film = i < len(b["beats"])
        if bt["kind"] not in KINDS:
            issues.append(f"{bt['id']}: unknown component {bt['kind']}")
        if film and bt["frames"] < sec(0.8):
            issues.append(f"{bt['id']}: {bt['frames']} frames is under 0.8 s")
        t = bt.get("transition")
        if film and i and not t:
            issues.append(f"{bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{bt['id']}: clip {bt['clip']} is not in the clip list")
        if (bt.get("data") or {}).get("product") and own and not set(bt.get("photos") or []) <= own:
            issues.append(f"{bt['id']}: a product beat must carry a still from the product's own assets")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    if len(b.get("stories") or []) != 3:
        issues.append("three stories are needed (tease, tease harder, reveal)")
    cd = b.get("countdown")
    if not cd:
        issues.append("no countdown card")
    elif launch.get("date") and (cd.get("data") or {}).get("date") != launch["date"]:
        issues.append(f"the countdown card carries {(cd.get('data') or {}).get('date')}, not the date given ({launch['date']})")
    if not b.get("feed"):
        issues.append("no feed post")
    if not any(product and product in str((bt.get("text") or {}).get("headline") or "").lower() for bt in b["beats"]):
        issues.append(f"no beat of the film names {b.get('product')}")
    if not any(bt["kind"] == "DateCard" for bt in b["beats"]):
        issues.append("the film has no date beat")
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
    sigs = set()
    for b in boards:
        sigs.add((b["structure"], b["tone"], b["clip_use"]))
        iss = board_issues(b)
        bad += len(iss)
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'} , {film_seconds(b['beats']):.1f} s")
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
