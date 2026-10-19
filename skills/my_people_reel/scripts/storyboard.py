#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film of the same people, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, every person, the wall, assets, text, clips, 30-60 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (palette, type direction, register, the people in their order with each one's
stretch, line and why, and the eras), then build/people.json, picks.json, palette.json and research.json. The three
boards differ on structure, on tone, and on how generated clips are used:
  1  the board       a leaderboard that builds person by person to the beat, up to    kinetic      still-first;
                     number one, then the whole board held                                         generated clips are the
                                                                                                   texture between people
  2  portraits       one portrait per person in the order they owned the year, a      editorial    clip-first;
                     line of theirs set as type, ending on the party wall                          each portrait's photo
                                                                                                   brought to life
  3  the party wall  one continuous camera across a 3x3 wall of the photos with the   documentary  still-first;
                     most of them in it, then the pull back                                        a generated opener for
                                                                                                   the wall's world, their
                                                                                                   own reels in their tiles
Every board carries `cards`: one story card (1080x1920) per person, their best photo and their line, in the board's
palette and type. The agent may edit any storyboard.json (text, order, photos, prompts) before sheets; check
validates it.
"""
import argparse
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
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
TARGET = {"editorial": 40, "kinetic": 32, "documentary": 36}
LENGTH = (30, 60)
SNAKE = [0, 1, 2, 5, 4, 3, 6, 7, 8]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728\uFE0F\u200D]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}


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
        self.stats = _env.read_json("build/people.json") or {}
        self.picked = _env.read_json("build/picks.json") or {}
        self.picks = self.picked.get("chapters", {})
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.index = _env.read_json("build/photo_index.json") or []
        self.lib = _env.read_json("build/library.json") or {}
        self.handle = self.stats.get("handle") or self.taste.get("handle") or "you"
        self.year = int(self.stats.get("year") or self.taste.get("year"))
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.used = set()
        self.said = set()

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def photo(self, src):
        """A library photo as the graded file the renderer reads (relative to build/)."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        return grade.graded_name(p)

    def people(self):
        """The people in their order (taste.json, which the agent may edit, wins over the counts), each with their
        graded best photo, score, stretch and line, in her register."""
        if hasattr(self, "_people"):
            return self._people
        photo = {x["handle"]: x for x in self.picked.get("people", [])}
        score = {x["handle"]: x for x in self.stats.get("people", [])}
        out = []
        for k, t in enumerate(self.taste.get("people") or []):
            h = t["handle"]
            pk = photo.get(h) or {}
            ph = self.photo(t.get("photo") or pk.get("photo")) if (t.get("photo") or pk.get("photo")) else None
            if not ph:
                continue
            sc = score.get(h) or {}
            out.append({"rank": k + 1, "handle": h, "photo": ph, "image": pk.get("src"), "score": sc.get("score") or 0,
                        "stretch": self.say(t.get("stretch") or (sc.get("stretch") or {}).get("label") or ""),
                        "first": min((sc.get("stretch") or {}).get("months") or [13]),
                        "line": self.say(short(t.get("line") or "", 110)) or None, "line_from": t.get("line_from"),
                        "together": sc.get("photos_together") or 0,
                        "place": next((e["place"] for e in self.taste.get("eras") or [] if e.get("owner") == h and e.get("place")), None)})
        self._people = out
        return out

    def handles(self):
        return [x["handle"] for x in self.people()]

    def place_in(self, ts):
        if not ts:
            return None
        m = MONTHS[dt.datetime.fromtimestamp(ts, dt.timezone.utc).month - 1]
        for e in self.taste.get("eras") or []:
            a, b = MONTHS.index(e["from"]), MONTHS.index(e["to"])
            if a <= MONTHS.index(m) <= b and e.get("place"):
                return e["place"]
        return None

    def wall(self):
        """The party wall: the group photos picks.py chose (fewest photos that hold everyone, filled to nine), in date
        order, each tile with its date and place, the handles in it, and her caption's lead line."""
        if hasattr(self, "_wall"):
            return self._wall
        mine = set(self.handles())
        out = []
        for k, t in enumerate(self.picked.get("wall", [])):
            ph = self.photo(t["photo"])
            if not ph:
                continue
            when = dt.datetime.fromtimestamp(t["ts"], dt.timezone.utc) if t.get("ts") else None
            place = self.place_in(t.get("ts"))
            label = " · ".join(x for x in ((f"{MONTHS[when.month - 1]} {when.day}" if when else ""), place or "") if x)
            ppl = [h for h in t.get("people", []) if h in mine] or t.get("people", [])
            cap = short(re.sub(r"@[\w.]+", "", t.get("caption") or ""), 50)
            out.append({"rank": len(out) + 1, "photo": ph, "people": ppl, "label": self.say(label),
                        "caption": " ".join("@" + h for h in ppl), "line": self.say(cap) if len(cap) >= 8 else None,
                        "video": t.get("video"), "kind": "reel" if t.get("video") else "photo", "image": t.get("src")})
        self._wall = out
        return out

    def chapter(self, name, n=None):
        out = [self.photo(p) for p in self.picks.get(name, [])]
        out = [p for p in out if p]
        return out[:n] if n else out

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        year = [s["hex"] for s in self.taste.get("palette", {}).get("year", []) if s.get("hex")] or ["#6b5440", "#b8a17f"]
        likes = [s["hex"] for s in self.taste.get("palette", {}).get("likes", []) if s.get("hex")]
        allc = year + likes
        darkest = min(allc, key=lum)
        lightest = max(allc, key=lum)
        vivid = sorted(likes or year, key=lambda h: -sat(h) * (0.4 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(vivid[1] if len(vivid) > 1 else year[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = vivid[0]
            accent2 = vivid[1] if len(vivid) > 1 else year[0]
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
            accent2 = vivid[1] if len(vivid) > 1 else year[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        swatches = [{"hex": s["hex"], "name": self.say(s.get("name") or "")} for s in self.taste.get("palette", {}).get("year", [])][:5]
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, direction, seconds, faces=False):
        t = self.taste
        colors = [s.get("name") for s in t.get("palette", {}).get("likes", [])[:3] if s.get("name")] + \
                 [s.get("name") for s in t.get("palette", {}).get("year", [])[:2] if s.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, "
                + ("every face kept exactly as it is in the photograph." if faces else "no people's faces."))


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


def tiles(ctx, clips=None):
    """The wall for a Grid, in date order, each tile with its clip id when the board gives it one."""
    return [{"rank": t["rank"], "photo": t["photo"], "people": t["people"], "label": t["label"], "caption": t["caption"],
             "line": t["line"], "kind": t["kind"], **({"clip": clips[t["rank"]]} if clips and t["rank"] in clips else {})}
            for t in ctx.wall()]


def grid(ctx, bid, mode, seconds, transition, text, clips=None, stagger=None):
    order = [t["rank"] for t in ctx.wall()]
    weights = [1] * len(order) + [2.2] if mode == "camera" else [1]
    data = {"mode": mode, "tiles": tiles(ctx, clips), "order": order, "weights": weights, "shots": len(weights)}
    if mode == "camera":
        data["path"] = SNAKE
    if stagger is not None:
        data["stagger"] = stagger
    return {"id": bid, "kind": "Grid", "frames": sec(seconds), "transition": transition, "text": text,
            "photos": [t["photo"] for t in ctx.wall()], "data": data}


def rows(ctx):
    return [{"rank": x["rank"], "handle": x["handle"], "photo": x["photo"], "score": x["score"], "stretch": x["stretch"]}
            for x in ctx.people()]


def attribution(ctx, x):
    """Whose words the line is, and when in the year they were there."""
    who = f"@{x['handle']}" if x.get("line_from") == "their comment" else f"me, about @{x['handle']}"
    return ctx.say(f"{who} · {x['stretch']}" if x.get("stretch") else who)


def board_row(ctx, x, seconds, transition, shown):
    return {"id": f"no-{x['rank']}", "kind": "Leaderboard", "frames": sec(seconds), "transition": transition, "photos": [x["photo"]],
            "text": {"kicker": ctx.say(f"no. {x['rank']} · @{x['handle']}"), "headline": x["line"] or f"@{x['handle']}",
                     "line": ctx.say(f"{x['together']} photos together" if x["together"] else x["stretch"])},
            "data": {"rows": rows(ctx), "shown": shown, "me": x["rank"]}}


def portrait(ctx, x, seconds, transition, clip=None, bid=None):
    b = {"id": bid or f"person-{x['rank']}", "kind": "Portrait", "frames": sec(seconds), "transition": transition, "photos": [x["photo"]],
         "text": {"kicker": ctx.say(f"no. {x['rank']} · @{x['handle']}"), "headline": x["line"] or f"@{x['handle']}",
                  "line": attribution(ctx, x)},
         "data": {"rank": x["rank"], "handle": x["handle"]}}
    if clip:
        b["clip"] = clip
    return b


def tags_line(ctx):
    return " ".join("@" + h for h in ctx.handles())


def world_subject(ctx):
    pl = [x for x in (ctx.taste.get("places") or []) if x != "home"]
    where = ", ".join(pl[:3]) if pl else "a long table outside on a warm evening"
    return (f"an establishing shot of the places this group shared: {where}; an empty long table after a dinner, "
            "string lights, glasses catching the light, slow movement")


def alive_prompt(ctx, x, d, secs):
    where = f" in {x['place']}" if x.get("place") else ""
    return ctx.prompt(f"this photograph of a friend{where} comes alive: the light shifts across it, hair and fabric move "
                      "gently in a breeze, a slow push in", d, secs, faces=True)


def board_leader(ctx):
    d = "kinetic"
    ppl = ctx.people()
    n = len(ppl)
    beats = [
        {"id": "opener", "kind": "Opener", "frames": sec(2.4), "transition": None, "photos": ctx.chapter("opener", 1),
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("my people"), "line": ctx.say(f"the {n} who made my {ctx.year}")}},
        {"id": "bridge-1", "kind": "ClipShot", "frames": sec(1.4), "transition": tr("whip", d, "from-right"), "clip": "01",
         "photos": [ppl[-1]["photo"]] if ppl else [], "text": {"headline": ctx.say("counted by every tag and every comment")}},
    ]
    shown = []
    for k, x in enumerate(reversed(ppl)):
        shown = shown + [x["rank"]]
        if x["rank"] == 1 and n > 1:
            beats.append({"id": "bridge-2", "kind": "ClipShot", "frames": sec(1.2), "transition": tr("whip", d, "from-right"), "clip": "02",
                          "photos": [x["photo"]], "text": {"headline": ctx.say("and number one")}})
        trn = tr("bars", d) if x["rank"] == 1 else tr("whip", d, "from-right" if k % 2 == 0 else "from-left")
        beats.append(board_row(ctx, x, 4.4 if x["rank"] == 1 else 3.4, trn, list(shown)))
    beats.append({"id": "board", "kind": "Leaderboard", "frames": sec(3.6), "transition": tr("slide", d, "from-bottom"),
                  "photos": ctx.chapter("opener", 1),
                  "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"my people {ctx.year}")},
                  "data": {"rows": rows(ctx), "shown": [x["rank"] for x in ppl], "me": None}})
    colors = [s.get("name") for s in ctx.taste.get("palette", {}).get("year", [])[:3] if s.get("name")]
    bridge = lambda k: ctx.prompt(f"an abstract fast whip of warm light through confetti and glass in {', '.join(colors) or 'their colors'}, "
                                  f"{['streaks left to right', 'a burst outward from the center'][k]}", d, 1)
    clips = [{"id": f"{k + 1:02d}", "beat": f"bridge-{k + 1}", "role": "texture between people", "prompt": bridge(k), "seconds": 1, "image": None}
             for k in range(2)]
    return finish(ctx, {"id": "1", "name": ctx.say("the board"), "direction": d,
                        "structure": "a leaderboard that builds person by person to number one, then the whole board", "tone": "kinetic",
                        "clip_use": "still-first: short generated bursts in their colors are the texture between people",
                        "idea": ctx.say(f"the board fills from number {n} to number one, one person per beat, each landing over "
                                        "their best photo with a line of theirs in heavy type; the whole board holds at the end."),
                        "music": {"direction": "driving, bright, 120 bpm: four-on-the-floor, claps, a hook", "bpm": 120, "mood": "drive"},
                        "beats": [b for b in beats if b], "clips": clips})


def board_portraits(ctx):
    d = "editorial"
    ppl = sorted(ctx.people(), key=lambda x: (x["first"], x["rank"]))
    clips = [{"id": "01", "beat": "opener", "role": "the world they shared", "prompt": ctx.prompt(world_subject(ctx), d, 3),
              "seconds": 3, "image": None}]
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(3.0), "transition": None, "photos": ctx.chapter("opener", 1),
              "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("my people"), "line": ctx.say(f"{ctx.year}, in the order you owned it")},
              "clip": "01"}]
    for k, x in enumerate(ppl):
        cid = f"{k + 2:02d}"
        beats.append(portrait(ctx, x, 5.0, tr("wipe", d, "from-right" if k % 2 == 0 else "from-left") if k else tr("dip", d), clip=cid))
        clips.append({"id": cid, "beat": f"person-{x['rank']}", "role": "a portrait transition: their photo brought to life",
                      "seconds": 4, "image": x["photo"], "prompt": alive_prompt(ctx, x, d, 4)})
    beats.append(grid(ctx, "wall", "reveal", 4.4, tr("match", d),
                      {"kicker": ctx.say(f"my people {ctx.year}"), "headline": tags_line(ctx)}, stagger=4))
    return finish(ctx, {"id": "2", "name": ctx.say("portraits"), "direction": d,
                        "structure": "one portrait per person in the order they owned the year, then the party wall",
                        "tone": "quiet editorial", "clip_use": "clip-first: each portrait's photo brought to life as the move into that person",
                        "idea": ctx.say("a portrait series on paper-white pages in a soft serif: each person gets their stretch of the "
                                        "year, their photo alive and a line of theirs set as type; the wall of all of you closes it."),
                        "music": {"direction": "warm, unhurried, 86 bpm: soft keys, brushed drums, a bass that walks", "bpm": 86, "mood": "calm"},
                        "beats": beats, "clips": clips})


def board_wall(ctx):
    d = "documentary"
    wall = ctx.wall()
    clips = [{"id": "01", "beat": "opener", "role": "the party wall's world", "prompt": ctx.prompt(world_subject(ctx), d, 3),
              "seconds": 3, "image": None}]
    ids = {}
    for k, t in enumerate([t for t in wall if t.get("video")]):
        cid = f"{k + 2:02d}"
        ids[t["rank"]] = cid
        clips.append({"id": cid, "beat": "wall", "tile": t["rank"], "role": "their own reel, playing in its tile", "prompt": None,
                      "source": t["video"], "seconds": 4, "image": t["photo"]})
    first = (ctx.stats.get("range") or {}).get("first") or f"{ctx.year}-01-01"
    last = (ctx.stats.get("range") or {}).get("last") or f"{ctx.year}-12-31"
    beats = [
        {"id": "opener", "kind": "Opener", "frames": sec(2.6), "transition": None, "photos": ctx.chapter("opener", 1), "clip": "01",
         "text": {"kicker": f"{first.replace('-', '.')} to {last.replace('-', '.')}", "headline": ctx.say("my people"),
                  "line": ctx.say(f"{len(wall)} nights with all of you")}},
        grid(ctx, "wall", "camera", 33.0, tr("iris", d),
             {"kicker": ctx.say(f"my people {ctx.year}"), "headline": tags_line(ctx)}, clips=ids),
    ]
    return finish(ctx, {"id": "3", "name": ctx.say("the party wall"), "direction": d,
                        "structure": "one continuous camera across a 3x3 wall of the photos with the most of them in it, then the pull back",
                        "tone": "documentary", "clip_use": "still-first: a generated opener for the wall's world, their own reels playing in their tiles",
                        "idea": ctx.say("one unbroken camera move across the wall of group photos, tile to tile, with mono dates and the "
                                        "handles of whoever is in each; it pulls back at the end and everyone is there."),
                        "music": {"direction": "cinematic, warm, 94 bpm: a slow pulse, a piano figure, room noise", "bpm": 94, "mood": "film"},
                        "beats": beats, "clips": clips})


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a Grid beat, from its weights, snapped to the music's beats when given."""
    w = (bt.get("data") or {}).get("weights") or []
    if bt["kind"] != "Grid" or len(w) < 2:
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
    """Fills the system, drops empty beats, scales durations to the direction's target, adds one story card per person."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "year": ctx.year, "format": {"width": 1080, "height": 1920, "fps": FPS},
                  "system": ctx.system(d)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        empty = (bt["kind"] in ("Portrait", "Opener") and not bt["photos"] and not bt.get("clip")) or \
                (bt["kind"] == "Grid" and not (bt.get("data") or {}).get("tiles")) or \
                (bt["kind"] == "Leaderboard" and not (bt.get("data") or {}).get("rows"))
        if not empty:
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
        if c.get("tile"):
            continue
        secs = max(1, round(by[c["beat"]]["frames"] / FPS))
        if c.get("prompt"):
            c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
    board["clips"] = keep
    board["cards"] = [{**portrait(ctx, x, 3, None, bid=f"card-{x['rank']:02d}-{x['handle']}"), "settle": 0} for x in ctx.people()]
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
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             f"- the people, in rank order: {', '.join('@' + c['data']['handle'] for c in board.get('cards', []))}",
             "", "## beats", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        if b["kind"] == "Grid":
            assets = f"the party wall ({b['data']['mode']}" + (", their reels in their tiles" if any(x.get("clip") for x in b["data"]["tiles"]) else "") + ")"
        elif b["kind"] == "Leaderboard":
            assets = f"the board ({len(b['data']['shown'])} of {len(b['data']['rows'])} shown); " + ", ".join(Path(p).name for p in (b.get("photos") or [])[:1])
        else:
            assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (their reel: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", "## story cards (1080x1920, one per person, in this board's palette and type)", ""]
    for c in board.get("cards", []):
        t = c.get("text") or {}
        lines.append(f"- {c['id']}: {Path(c['photos'][0]).name if c.get('photos') else '-'}; {t.get('headline')} ({t.get('line')})")
    lines.append("")
    path.write_text("\n".join(lines))


def all_photos(b):
    out = set()
    for x in b["beats"] + b.get("cards", []):
        out |= set(x.get("photos") or [])
        data = x.get("data") or {}
        out |= {t["photo"] for t in data.get("tiles", []) if t.get("photo")}
        out |= {r["photo"] for r in data.get("rows", []) if r.get("photo")}
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    if len(ctx.people()) < len(ctx.taste.get("people") or []) or not ctx.people():
        sys.exit(f"only {len(ctx.people())} of the {len(ctx.taste.get('people') or [])} people have a photo; picks.py names the ones that could not be opened")
    if len(ctx.wall()) < 9:
        sys.exit(f"the party wall has {len(ctx.wall())} of 9 photos; picks.py names the ones that could not be opened")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    grade.grade_photos()
    boards = []
    for make in (board_leader, board_portraits, board_wall):
        boards.append(make(ctx))
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


KINDS = {"Opener", "ClipShot", "Grid", "Leaderboard", "Portrait"}
PRESETS = set(design("transitions.json")["presets"])


def wall_issues(name, x):
    photos = [t.get("photo") for t in (x.get("data") or {}).get("tiles", [])]
    out = []
    if len(photos) != 9 or len(set(photos)) != 9:
        out.append(f"{name}: the party wall needs nine distinct photos, has {len(set(p for p in photos if p))}")
    order = (x.get("data") or {}).get("order") or []
    if sorted(order) != sorted(t.get("rank") for t in (x.get("data") or {}).get("tiles", [])):
        out.append(f"{name}: the wall order does not place every tile once")
    return out


def people_in(bt):
    """The handles a beat shows: its board rows, its portrait, the people in its tiles."""
    data = bt.get("data") or {}
    out = set()
    if bt["kind"] == "Leaderboard":
        shown = set(data.get("shown") or [])
        out |= {r["handle"] for r in data.get("rows", []) if r["rank"] in shown}
    if bt["kind"] == "Portrait" and data.get("handle"):
        out.add(data["handle"])
    for t in data.get("tiles", []):
        out |= set(t.get("people") or [])
    return out


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
        if bt["kind"] == "Grid":
            issues += wall_issues(bt["id"], bt)
            for tl in bt["data"]["tiles"]:
                if tl.get("clip") and tl["clip"] not in clips:
                    issues.append(f"{bt['id']}: tile {tl['rank']} clip {tl['clip']} is not in the clip list")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    cards = b.get("cards") or []
    handles = [c.get("data", {}).get("handle") for c in cards]
    if not cards:
        issues.append("no cards (one story card per person comes from the board)")
    for c in cards:
        if c["kind"] != "Portrait" or not c.get("photos"):
            issues.append(f"{c['id']}: a card is a Portrait with that person's photo")
        if not (c.get("text") or {}).get("headline"):
            issues.append(f"{c['id']}: a card carries a line of theirs")
    seen = set().union(*(people_in(bt) for bt in b["beats"])) if b["beats"] else set()
    for h in handles:
        if h not in seen:
            issues.append(f"@{h} is in no beat of the film")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text and no logos")
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
