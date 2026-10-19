#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film for the same person, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, shared photos only, assets, text, clips, 30-60 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (who it is for, the occasion, the palettes, type direction, pacing, register,
the eras and the love lines), then build/shared.json, picks.json, palette.json and research.json. Every photo a
board uses is one the two share (picks.json "shared"). The three boards differ on structure, tone and clip use:
  1  first to now      a timeline from the first photo together to the latest, era by era    editorial    clip-first;
                       the opener and closer generated, the first and the latest photo brought to life
  2  things i love     a "things I love about you" list in kinetic type over their photos,   kinetic      still-first;
     about you         the lines from the person's own comments and captions                              two generated bridges
  3  in your words     a documentary cut captioned with what the two wrote to each other     documentary  their footage first;
                       their own videos as they are, a generated opener and closer
Every board is one cut for both shapes: the 9:16 film and the 1:1 feed version are rendered from the same
beats (film.py), and the board's "card" (its closing beat, held still) is the 1080x1350 card. The agent may edit
any storyboard.json (text, order, photos, prompts) before sheets; check validates it.
"""
import argparse
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
TARGET = {"editorial": 44, "kinetic": 34, "documentary": 46}
LENGTH = (30, 60)
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
        self.shared = _env.read_json("build/shared.json") or {}
        self.picks = _env.read_json("build/picks.json") or {}
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.handle = self.taste.get("handle") or "you"
        who = self.taste.get("for") or self.shared.get("who") or {}
        self.who = who.get("handle") or "you"
        self.first = who.get("first") or self.who
        self.occ = {**(self.shared.get("occasion") or {}), **{k: v for k, v in (self.taste.get("occasion") or {}).items() if v}}
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.items = [dict(r, photo=grade.graded_name(r["photo"])) for r in self.picks.get("items", [])]
        self.videos = [dict(r, photo=grade.graded_name(r["photo"])) for r in self.picks.get("videos", [])]
        self.allowed = {grade.graded_name(x) for x in self.picks.get("shared", [])}
        self.used = set()

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def chapter(self, name, n=None):
        out = [grade.graded_name(p) for p in (self.picks.get("chapters") or {}).get(name, [])]
        return out[:n] if n else out

    def take(self, rows, n=1, avoid=()):
        """The strongest n of these shared photos not used yet in this board."""
        out = []
        for r in sorted(rows, key=lambda r: -r.get("score", 0)):
            if r["photo"] not in self.used and r["photo"] not in avoid:
                out.append(r)
                self.used.add(r["photo"])
            if len(out) >= n:
                break
        return out

    def near(self, ts, avoid=()):
        """The shared photo nearest in time to ts."""
        rows = [r for r in self.items if r["photo"] not in avoid] or self.items
        return min(rows, key=lambda r: abs(r["ts"] - (ts or 0)))

    def title(self):
        return self.say(self.occ.get("title") or f"for {self.first}")

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        pal = self.taste.get("palette", {})
        together = [s["hex"] for s in pal.get("together", []) if s.get("hex")] or ["#6b5440", "#b8a17f"]
        theirs = [s["hex"] for s in pal.get("theirs", []) if s.get("hex")]
        mine = [s["hex"] for s in pal.get("mine", []) if s.get("hex")]
        allc = together + theirs
        darkest = min(allc, key=lum)
        lightest = max(allc, key=lum)
        vivid = sorted(theirs or together, key=lambda h: -sat(h) * (0.4 + lum(h)))
        warm = sorted(mine or together, key=lambda h: -sat(h) * (0.4 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(warm[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = vivid[0]
            accent2 = warm[0]
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
            accent2 = warm[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        swatches = [{"hex": s["hex"], "name": self.say(s.get("name") or "")} for s in pal.get("together", [])][:5]
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, direction, seconds):
        t = self.taste
        pal = t.get("palette", {})
        colors = [s.get("name") for s in pal.get("together", [])[:4] if s.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16 with the subject in the middle square (a 1:1 cut is made from it), {seconds} seconds, "
                f"one continuous shot. No text, no logos, no people's faces.")


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


def day_label(iso, year=True):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{MONTHS[m - 1]} {d}" + (f", {y}" if year else "")


def places(ctx):
    return [e["place"] for e in ctx.shared.get("eras", []) if e.get("place")]


def alive(ctx, r, d, secs):
    what = r.get("era") if r.get("era") in places(ctx) else None
    return ctx.prompt(f"this photograph of two friends comes alive{' in ' + what if what else ''}: the light shifts across it, "
                      f"hair and fabric move a little, a slow push in", d, secs)


def closer(ctx, bid, photos, line, transition, clip=None):
    b = {"id": bid, "kind": "Closer", "frames": sec(4.2), "transition": transition, "photos": photos,
         "text": {"kicker": f"@{ctx.who}", "headline": ctx.title(), "line": line},
         "data": {"signoff": ctx.say(f"from @{ctx.handle}")}}
    if clip:
        b["clip"] = clip
    return b


def since(ctx):
    f = ctx.shared.get("first") or {}
    n = len(ctx.items)
    return ctx.say(f"{n} photos together since {MONTHS[int(f['date'][5:7]) - 1]}" if f.get("date") else f"{n} photos together")


def board_timeline(ctx):
    d = "editorial"
    ctx.used = set()
    first, latest = ctx.items[0], ctx.items[-1]
    ctx.used |= {first["photo"], latest["photo"], *ctx.chapter("opener", 1)}
    span = max(1, latest["ts"] - first["ts"])
    start = MONTHS[int(first["date"][5:7]) - 1][:3] + " " + first["date"][:4]
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(3.2), "transition": None, "photos": ctx.chapter("opener", 1), "clip": "01",
              "text": {"kicker": f"@{ctx.who}", "headline": ctx.title(), "line": ctx.say("from the first photo to now")}},
             {"id": "first", "kind": "ClipShot", "frames": sec(3.4), "transition": tr("dip", d), "photos": [first["photo"]], "clip": "02",
              "text": {"kicker": ctx.say(f"the first one, {day_label(first['date'])}"), "headline": ctx.say(short(first["caption"]) or "the first one")}}]
    eras = [e for e in ctx.shared.get("eras", [])]
    for k, e in enumerate(eras):
        rows = [r for r in ctx.items if r.get("era") == e["label"]]
        pick = ctx.take(rows, 2)
        if not pick:
            continue
        pick.sort(key=lambda r: r["ts"])
        mid = pick[0]["ts"]
        beats.append({"id": f"era-{k + 1}", "kind": "PhotoLive", "frames": sec(2.4 * len(pick)), "transition": tr("wipe" if k % 2 else "match", d, "from-right" if k % 2 else None),
                      "photos": [r["photo"] for r in pick],
                      "text": {"kicker": ctx.say(e["label"]), "headline": ctx.say(short(pick[0]["caption"]) or e["span"])},
                      "data": {"items": [{"kicker": ctx.say(f"{e['label']}, {e['span']}" if e["label"] != e["span"] else e["span"]),
                                          "headline": ctx.say(short(r["caption"]) or day_label(r["date"], False))} for r in pick],
                               "rule": {"at": round((mid - first["ts"]) / span, 3), "from": ctx.say(start), "to": ctx.say("now")}}})
    beats.append({"id": "latest", "kind": "ClipShot", "frames": sec(3.0), "transition": tr("dip", d), "photos": [latest["photo"]], "clip": "03",
                  "text": {"kicker": ctx.say(f"the latest, {day_label(latest['date'])}"), "headline": ctx.say(short(latest["caption"]) or "the latest")}})
    best = [p for p in ctx.chapter("best") if p not in (first["photo"], latest["photo"])][:3]
    beats.append(closer(ctx, "closer", [first["photo"], *best][:4], since(ctx), tr("match", d), clip="04"))
    pl = places(ctx)
    clips = [{"id": "01", "beat": "opener", "role": "the opener, in the palette the two share",
              "prompt": ctx.prompt(f"an establishing shot of a morning table by a window{' in ' + pl[0] if pl else ''}, two coffee cups, "
                                   f"light moving slowly across linen", d, 3), "seconds": 3, "image": None},
             {"id": "02", "beat": "first", "role": "the first photo together, brought to life", "prompt": alive(ctx, first, d, 3), "seconds": 3,
              "image": first["photo"]},
             {"id": "03", "beat": "latest", "role": "the latest photo together, brought to life", "prompt": alive(ctx, latest, d, 3), "seconds": 3,
              "image": latest["photo"]},
             {"id": "04", "beat": "closer", "role": "the closer, in the palette the two share",
              "prompt": ctx.prompt("candle flames and warm bokeh drifting over a long table at dusk, slow and soft", d, 4), "seconds": 4,
              "image": None}]
    return finish(ctx, {"id": "1", "name": ctx.say("first to now"), "direction": d,
                        "structure": "a timeline from the first photo together to the latest, era by era", "tone": "warm editorial",
                        "clip_use": "clip-first: a generated opener and closer, the first and the latest photo brought to life",
                        "idea": ctx.say(f"the story of the two of you in order: the first photo, then each chapter ({', '.join(e['label'] for e in eras)}) "
                                        f"with its date on a rule that runs toward now, then the latest photo and the wish."),
                        "music": {"direction": "warm, unhurried, 86 bpm: soft keys, brushed drums, a melody that opens up at the end", "bpm": 86, "mood": "warm"},
                        "beats": beats, "clips": clips})


def board_love(ctx):
    d = "kinetic"
    ctx.used = set()
    lines = [x["line"] for x in ctx.shared.get("love_lines", [])]
    lines = (ctx.taste.get("love_lines") or lines)[:6]
    big = str(ctx.occ.get("age") or ctx.occ.get("years") or ctx.first)
    op = ctx.chapter("opener", 1)
    ctx.used |= set(op)
    title_photo = ctx.take(ctx.items, 1)
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(2.6), "transition": None, "photos": op,
              "text": {"kicker": f"@{ctx.who}", "headline": ctx.title()}, "data": {"big": big}},
             {"id": "title", "kind": "KineticType", "frames": sec(2.8), "transition": tr("bars", d), "photos": [r["photo"] for r in title_photo],
              "text": {"kicker": ctx.say(f"for {ctx.first}")}, "data": {"rows": [{"text": ctx.say(w)} for w in ("things", "i love", "about", "you")]}}]
    era_rows = {}
    for r in ctx.items:
        era_rows.setdefault(r.get("era"), []).append(r)
    order = list(era_rows)
    bridge_at = {1: "01", 4: "02"}
    for k, line in enumerate(lines):
        rows = era_rows[order[k % len(order)]]
        pick = ctx.take(rows, 1) or ctx.take(ctx.items, 1)
        if not pick:
            break
        beats.append({"id": f"love-{k + 1}", "kind": "PhotoLive", "frames": sec(2.6), "transition": tr("whip", d, "from-right" if k % 2 else "from-left"),
                      "photos": [pick[0]["photo"]], "treatment": ["push", "mask", "push"][k % 3],
                      "text": {"headline": ctx.say(line)}, "data": {"items": [{"rank": f"{k + 1:02d}", "headline": ctx.say(line)}]}})
        if k in bridge_at:
            nxt = ctx.take(ctx.items, 1)
            beats.append({"id": f"bridge-{bridge_at[k]}", "kind": "ClipShot", "frames": sec(1.2), "transition": tr("whip", d, "from-right"),
                          "clip": bridge_at[k], "photos": [r["photo"] for r in nxt], "text": {}})
    best = [p for p in ctx.chapter("best") if p not in op][:4]
    beats.append(closer(ctx, "closer", best, ctx.say(f"and about a hundred more"), tr("bars", d)))
    colors = [s.get("name") for s in ctx.taste.get("palette", {}).get("together", [])[:3] if s.get("name")]
    bridge = lambda n: ctx.prompt(f"an abstract fast whip of light through colored glass in {', '.join(colors) or 'their colors'}, "
                                  f"{['streaks left to right', 'a burst outward from the center'][n]}", d, 1)
    clips = [{"id": f"{n + 1:02d}", "beat": f"bridge-{n + 1:02d}", "role": "a transition between lines", "prompt": bridge(n), "seconds": 1, "image": None}
             for n in range(2)]
    return finish(ctx, {"id": "2", "name": ctx.say("things i love about you"), "direction": d,
                        "structure": "a numbered list of what the person loves about them, one line per photo", "tone": "kinetic and loud",
                        "clip_use": "still-first: their photos carry it; two short generated bridges in the shared colors",
                        "idea": ctx.say(f"the big number lands, then a list in heavy type: things i love about you, one line per photo, "
                                        f"each line one the person already wrote to {ctx.first}, numbered, on the beat."),
                        "music": {"direction": "bright, bouncy, 116 bpm: claps, a bass hook, a big drop for the title", "bpm": 116, "mood": "drive"},
                        "beats": beats, "clips": clips})


def board_words(ctx):
    d = "documentary"
    ctx.used = set()
    me, them = f"@{ctx.handle}", f"@{ctx.who}"
    items_by_id = {}
    for r in ctx.items:
        items_by_id.setdefault(r["id"], r)
    pairs = ctx.shared.get("pairs", [])
    picked, seen_posts = [], set()
    for pr in pairs:
        if pr["post"] in seen_posts:
            continue
        seen_posts.add(pr["post"])
        picked.append(pr)
    picked = picked[:5]
    f, l = ctx.items[0], ctx.items[-1]
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(3.0), "transition": None, "photos": [f["photo"]], "clip": "01",
              "text": {"kicker": f"{f['date'].replace('-', '.')} to {l['date'].replace('-', '.')}", "headline": ctx.title(),
                       "line": ctx.say("in our own words")}}]
    vids = list(ctx.videos)
    vid_at = {1: 0, 3: 1}
    cid = 2
    clips = [{"id": "01", "beat": "opener", "role": "the opener, in the palette the two share",
              "prompt": ctx.prompt(f"handheld walk through {(places(ctx) or ['an old town'])[-1]} streets at first light, doorways and warm walls", d, 3),
              "seconds": 3, "image": None}]
    for k, pr in enumerate(picked):
        r = items_by_id.get(pr["post"]) or ctx.near((pr["first"] or {}).get("ts"), ctx.used)
        ctx.used.add(r["photo"])
        said = [{"by": me if x["account"] == ctx.handle else them, "text": re.sub(r"\s+", " ", EMOJI.sub("", x["text"])).strip(), "side": "mine" if x["account"] == ctx.handle else "theirs"}
                for x in (pr["first"], pr["answer"])]
        beats.append({"id": f"words-{k + 1}", "kind": "Exchange", "frames": sec(4.2), "transition": tr("fade" if k % 2 else "iris", d),
                      "photos": [r["photo"]], "text": {"kicker": ctx.say(day_label(r["date"]))}, "data": {"lines": said}})
        if k in vid_at and vid_at[k] < len(vids):
            v = vids[vid_at[k]]
            ident = f"{cid:02d}"
            cid += 1
            beats.append({"id": f"video-{vid_at[k] + 1}", "kind": "ClipShot", "frames": sec(4.0), "transition": tr("fade", d), "photos": [v["photo"]],
                          "clip": ident, "text": {"kicker": ctx.say(day_label(v["date"])), "headline": ctx.say(short(v["caption"]))}})
            clips.append({"id": ident, "beat": f"video-{vid_at[k] + 1}", "role": "their own video", "prompt": None, "source": v["src"],
                          "seconds": 4, "image": v["photo"]})
    best = [p for p in ctx.chapter("best") if p not in ctx.used][:4]
    ident = f"{cid:02d}"
    beats.append(closer(ctx, "closer", best, ctx.say(f"{len(ctx.shared.get('exchanges', []))} comments and counting"), tr("fade", d), clip=ident))
    clips.append({"id": ident, "beat": "closer", "role": "the closer, in the palette the two share",
                  "prompt": ctx.prompt("dusk light on a balcony, string lights swaying a little, the city soft behind", d, 4),
                  "seconds": 4, "image": None})
    return finish(ctx, {"id": "3", "name": ctx.say("in your words"), "direction": d,
                        "structure": "a documentary cut captioned with what the two wrote to each other", "tone": "documentary and tender",
                        "clip_use": "their footage first: their own videos as they are, a generated opener and closer",
                        "idea": ctx.say(f"no narration but theirs: the comments the two traded play as captions over the photos, "
                                        f"{ctx.handle}'s lines on the left and {ctx.who}'s answers on the right, with their own videos between."),
                        "music": {"direction": "cinematic and warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips})


def finish(ctx, board):
    """Fills the system, drops empty beats, scales durations to the direction's target, adds the card."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "for": ctx.who, "year": int((ctx.items[-1]["date"] if ctx.items else "2026")[:4]),
                  "occasion": ctx.occ.get("label"), "format": {"width": 1080, "height": 1920, "fps": FPS, "safe": "reel"},
                  "system": ctx.system(d)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        if bt["photos"] or bt.get("clip") or bt["kind"] == "KineticType":
            beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (TARGET[d] * FPS + overlap) / whole if whole else 1
    for bt in beats:
        bt["frames"] = max(sec(0.9), int(round(bt["frames"] * k)))
    board["beats"] = beats
    by = {b["id"]: b for b in beats}
    keep = [c for c in board["clips"] if c["beat"] in by]
    for c in keep:
        secs = max(1, round(by[c["beat"]]["frames"] / FPS))
        if c.get("prompt"):
            c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
    board["clips"] = keep
    last = next((b for b in reversed(beats) if b["kind"] == "Closer"), None)
    if last:
        card = {k: v for k, v in last.items() if k not in ("clip", "transition")}
        board["card"] = {**card, "id": "card", "frames": sec(3), "settle": 0, "transition": None}
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
             f"- for @{board['for']} ({board.get('occasion')})", f"- structure: {board['structure']}", f"- tone: {board['tone']}",
             f"- generated clips: {board['clip_use']}",
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps, rendered at 1080x1920 and again at 1080x1080 from the same beats",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']} (theirs), accent2 {s['colors']['accent2']} (yours); "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])} (together)",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             "", "## beats", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        if b["kind"] == "KineticType":
            txt = " / ".join(r["text"] for r in b["data"]["rows"]) + (f" ({txt})" if txt else "")
        if b["kind"] == "Exchange":
            txt = " / ".join(f"{x['by']}: {x['text']}" for x in b["data"]["lines"])
        assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips", ""]
    for c in board["clips"]:
        src = f" (their video: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", "The card (1080x1350) is the closing beat held still, in this board's palette and type.", ""]
    path.write_text("\n".join(lines))


def all_photos(b):
    out = set()
    for x in b["beats"] + ([b["card"]] if b.get("card") else []):
        out |= set(x.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    if len(ctx.items) < 6:
        sys.exit(f"only {len(ctx.items)} photos of the two of you could be prepared; the film needs at least six")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    boards = [make(ctx) for make in (board_timeline, board_love, board_words)]
    grade.grade_photos([Path("build/photos") / Path(p).name for p in ctx.picks.get("shared", [])])
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


KINDS = {"Opener", "ClipShot", "PhotoLive", "KineticType", "Exchange", "Closer"}
PRESETS = set(design("transitions.json")["presets"])


def allowed_photos():
    """The graded names of every photo the two share: the only photos a board may show."""
    return {grade.graded_name(p) for p in (_env.read_json("build/picks.json") or {}).get("shared", [])}


def board_issues(b, allowed):
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
        if bt["kind"] in ("PhotoLive", "Exchange", "Closer") and not bt.get("photos"):
            issues.append(f"{bt['id']}: a {bt['kind']} beat needs a photo of the two")
        if bt["kind"] == "Exchange" and not (bt.get("data") or {}).get("lines"):
            issues.append(f"{bt['id']}: an Exchange beat needs their lines")
        for v in list((bt.get("text") or {}).values()) + [x.get("text") for x in (bt.get("data") or {}).get("lines", [])]:
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    if not b.get("card"):
        issues.append("no card (the 1080x1350 card is the board's closing beat)")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
        elif p not in allowed:
            issues.append(f"{p} is not a photo of the two of them (picks.json shared)")
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
    allowed = allowed_photos()
    sigs = set()
    for b in boards:
        sigs.add((b["structure"], b["tone"], b["clip_use"]))
        iss = board_issues(b, allowed)
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


def photo_cuts(bt, n, grid_s, start):
    """Where a beat of n photos cuts from one to the next: equal parts, each moved onto the nearest music beat."""
    cuts, lo = [], sec(0.6)
    for i in range(1, n):
        ideal = bt["frames"] * i / n
        if grid_s:
            ideal = snap_to((start + ideal) / FPS, grid_s, 0.25) * FPS - start
        c = max(lo + (cuts[-1] if cuts else 0), min(bt["frames"] - lo, int(round(ideal))))
        cuts.append(c)
    return cuts


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
        n = len(bt.get("photos") or []) if bt["kind"] == "PhotoLive" else 0
        if n > 1:
            bt.setdefault("data", {})["cuts"] = photo_cuts(bt, n, grid_s, t["start"])
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
