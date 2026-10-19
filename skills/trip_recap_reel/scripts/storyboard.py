#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film of the same trip, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, places, assets, text, clips, 30-60 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (the trip, its palette, type direction, pacing, register, places, people, the
line of each day), then build/trip.json, picks.json and research.json. The three boards differ on structure, tone
and how generated clips are used:
  1  the route      day by day in order, the route drawing itself across a map     documentary  their own clips in
                    of their own coordinates, ending on the whole route                          their days; a generated
                                                                                                 establishing shot and flyover
  2  the mood       place by place cut to the music, photos on the beat, almost    kinetic      clip-first: generated
                    no words                                                                     weather and texture b-roll
                                                                                                 between places, their clips
  3  postcards      one postcard per place, their own caption set as type, a       editorial    a generated establishing
                    stamp with the place and the date                                            shot before each postcard
Every board ends on the route and carries five story cards (1080x1920) in its palette and type. One storyboard
makes both films: 9:16 (1080x1920) and 16:9 (1920x1080). The map is drawn from the trip's coordinates alone; no
map service is asked for anything. The agent may edit any storyboard.json (text, order, photos, prompts) before
sheets; check validates it.
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
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
TARGET = {"editorial": 44, "kinetic": 40, "documentary": 46}
LENGTH = (30, 60)
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2728\uFE0F\u200D]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}
PLACE_KINDS = ("Day", "Montage", "Postcard")


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
        self.trip = _env.read_json("build/trip.json") or {}
        self.picks = _env.read_json("build/picks.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        if not self.trip or not self.picks:
            sys.exit("build/trip.json and build/picks.json are missing: run research.py first")
        self.handle = self.taste.get("handle") or self.research.get("handle") or "you"
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        t = self.taste.get("trip") or {}
        self.name = t.get("name") or self.trip.get("name") or "the trip"
        self.lo, self.hi = t.get("from") or self.trip["from"], t.get("to") or self.trip["to"]
        self.days = [d for d in self.trip.get("days") or [] if self.lo <= d["date"] <= self.hi]
        lines = {d["date"]: d for d in self.taste.get("days") or []}
        for d in self.days:
            d["line"] = (lines.get(d["date"]) or {}).get("line") or ""
        order = self.taste.get("places") or [p["name"] for p in self.trip.get("places") or []]
        known = {p["name"]: p for p in self.trip.get("places") or []}
        self.places = [known.get(n, {"name": n, "lat": None, "lon": None, "days": []}) for n in order]
        self.route = [r for r in self.trip.get("route") or [] if r.get("lat") is not None]
        self.people = self.taste.get("people") or [p["handle"] for p in self.trip.get("people") or []]
        self.used = set()

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def photo(self, src):
        """A library photo as the graded file the renderer reads (relative to build/public/)."""
        import picks
        if not src:
            return None
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        return grade.graded_name(p) if p else None

    def fresh(self, pool, n=1):
        """Up to n photos from the pool not yet used on this board, the pool's order kept."""
        out = []
        for src in pool:
            g = self.photo(src)
            if g and g not in self.used and g not in out:
                out.append(g)
            if len(out) >= n:
                break
        if len(out) < n:
            for src in pool:
                g = self.photo(src)
                if g and g not in out:
                    out.append(g)
                if len(out) >= n:
                    break
        self.used |= set(out)
        return out

    def day_photos(self, date, n):
        d = next((x for x in self.picks.get("days") or [] if x["date"] == date), {})
        return self.fresh(d.get("photos") or [], n)

    def place_photos(self, name, n):
        pl = next((x for x in self.picks.get("places") or [] if x["name"] == name), {})
        pool = pl.get("photos") or [p for d in self.picks.get("days") or [] if name in d["places"] for p in d["photos"]]
        return self.fresh(pool, n)

    def date_of(self, graded):
        """The day a graded photo was taken on, from the trip's days in picks.json, else None."""
        for d in self.picks.get("days") or []:
            if any(grade.graded_name(src) == graded for src in d.get("photos") or []):
                return d["date"]
        return None

    def caption_of(self, graded):
        for src, cap in (self.picks.get("caption_of") or {}).items():
            if grade.graded_name(src) == graded:
                return cap
        return ""

    def opener(self):
        return self.fresh([self.picks.get("opener")], 1)

    def closer(self):
        return self.fresh([self.picks.get("closer")], 1)

    def clips(self):
        return [c for c in self.picks.get("clips") or [] if c.get("file")]

    def range_line(self):
        a, b = dt.date.fromisoformat(self.lo), dt.date.fromisoformat(self.hi)
        if a == b:
            s = f"{MONTHS[a.month - 1]} {a.day}, {a.year}"
        elif a.month == b.month:
            s = f"{MONTHS[a.month - 1]} {a.day} to {b.day}, {a.year}"
        else:
            s = f"{MONTHS[a.month - 1]} {a.day} to {MONTHS[b.month - 1]} {b.day}, {b.year}"
        return self.say(s)

    def day_label(self, date):
        d = dt.date.fromisoformat(date)
        return self.say(f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1][:3]} {d.day}")

    def with_line(self):
        if not self.people:
            return None
        hs = [f"@{h}" for h in self.people[:3]]
        return self.say("with " + (", ".join(hs[:-1]) + " and " + hs[-1] if len(hs) > 1 else hs[0]))

    def route_data(self, upto=None):
        pts = [{"lat": r["lat"], "lon": r["lon"], "place": self.say(r["place"]), "day": r.get("day")} for r in self.route]
        if not pts:
            pts = [{"lat": p["lat"], "lon": p["lon"], "place": self.say(p["name"]), "day": (p.get("days") or [None])[0]}
                   for p in self.places if p.get("lat") is not None]
        return {"points": pts, "upto": list(upto) if upto else [0, max(0, len(pts) - 1)]}

    def route_index(self, date):
        """The last route point reached by the end of this date."""
        idx = 0
        for i, r in enumerate(self.route):
            if (r.get("day") or "") <= date:
                idx = i
        return idx

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        pal = self.taste.get("palette", {})
        trip = [s["hex"] for s in pal.get("trip") or [] if s.get("hex")] or ["#6b5440", "#b8a17f"]
        darkest = min(trip, key=lum)
        lightest = max(trip, key=lum)
        vivid = sorted(trip, key=lambda h: -sat(h) * (0.4 + lum(h)))
        tex = self.taste.get("texture", {})
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.55)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(vivid[1] if len(vivid) > 1 else trip[0], paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            # the accent draws the route and the bars on the dark ground and carries light type: it reads on both
            accent = readable(vivid[0], bg, 2.6)
            accent2 = vivid[1] if len(vivid) > 1 else trip[0]
            if contrast(ink, accent) < 2.2:
                accent = mix(accent, "#000000", 0.25)
            if contrast(ink, accent2) < 2.2:
                accent2 = mix(accent2, "#000000", 0.35)
            texture = {"grain": round(tex.get("grain", 0) * 0.5, 3), "vignette": 0, "leaks": False}
        else:
            bg = mix(darkest, "#000000", 0.7)
            ink = mix(lightest, "#ffffff", 0.5)
            paper = mix(lightest, "#f4ead8", 0.5)
            # the accent sets the small kickers over scrimmed photos, which are lighter than bg: it carries margin
            accent = readable(vivid[0], bg, 7)
            accent2 = vivid[1] if len(vivid) > 1 else trip[0]
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        swatches = [{"hex": s["hex"], "name": self.say(s.get("name") or "")} for s in pal.get("trip") or []][:5]
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": swatches},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, direction, seconds):
        t = self.taste
        colors = [s.get("name") for s in t.get("palette", {}).get("trip", [])[:4] if s.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "a fast push-in and a whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")


def clean(cap):
    return re.sub(r"\s+", " ", EMOJI.sub("", re.sub(r"[#@][\w.]+", "", cap or ""))).strip(" ,.-")


def short(cap, limit=60):
    """A caption's lead line for the screen: no hashtags or emoji; a long one is cut at a clause or a word, never on a function word."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    whole = c
    for sep in (". ", ": ", "; ", " - "):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while c != whole and len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def beat(bid, kind, seconds, transition, photos=None, text=None, data=None, clip=None):
    b = {"id": bid, "kind": kind, "frames": sec(seconds), "transition": transition, "photos": [p for p in (photos or []) if p],
         "text": {k: v for k, v in (text or {}).items() if v}}
    if data is not None:
        b["data"] = data
    if clip:
        b["clip"] = clip
    return b


def their_clip_beats(ctx, date, clips, transition, seconds=2.6):
    """A ClipShot for each of their own clips shot on this date, each with its caption as the line."""
    out = []
    for c in [c for c in ctx.clips() if c.get("day") == date]:
        cid = f"{len(clips) + 1:02d}"
        poster = ctx.photo(c.get("poster")) if c.get("poster") else None
        clips.append({"id": cid, "beat": f"clip-{cid}", "role": "their own clip", "prompt": None, "source": c["file"],
                      "seconds": round(seconds), "image": poster})
        out.append(beat(f"clip-{cid}", "ClipShot", seconds, transition, [poster] if poster else ctx.day_photos(date, 1),
                        {"kicker": ctx.say(c.get("place") or ""), "headline": ctx.say(short(clean(c.get("caption")), 40))}, clip=cid))
    return out


def board_route(ctx):
    d = "documentary"
    first = ctx.places[0]["name"] if ctx.places else ctx.name
    last = next((p["name"] for p in reversed(ctx.places) if p["name"] != first), first)
    clips = [{"id": "01", "beat": "opener", "role": "establishing shot", "image": None, "seconds": 3,
              "prompt": ctx.prompt(f"an establishing shot of {first} at first light, the whole place seen from a distance", d, 3)}]
    op = ctx.opener()
    clips[0]["image"] = op[0] if op else None
    beats = [beat("opener", "Opener", 3.0, None, op,
                  {"kicker": ctx.range_line(), "headline": ctx.say(ctx.name),
                   "line": ctx.say(f"{len(ctx.days)} days, {len(ctx.places)} places")}, clip="01"),
             beat("route", "Route", 4.2, tr("iris", d), [],
                  {"kicker": ctx.say("the route"), "headline": ctx.say(f"{first} to {last}" if last != first else first)},
                  ctx.route_data())]
    if len(ctx.places) >= 2:
        clips.append({"id": "02", "beat": "flyover", "role": "map flyover", "seconds": 2,
                      "image": (ctx.place_photos(ctx.places[1]["name"], 1) or [None])[0],
                      "prompt": ctx.prompt(f"an aerial flyover from {first} toward {ctx.places[1]['name']}, "
                                           "the land and the light passing slowly below", d, 2)})
        beats.append(beat("flyover", "ClipShot", 2.2, tr("dip", d), [clips[-1]["image"]], {}, clip="02"))
    prev = 0
    for i, day in enumerate(ctx.days, 1):
        here = ctx.route_index(day["date"])
        place = (day["places"] or [ctx.places[0]["name"] if ctx.places else ctx.name])[-1]
        photos = ctx.day_photos(day["date"], 2)
        beats.append(beat(f"day-{i}", "Day", 4.2, tr("wipe", d, "from-right"), photos,
                          {"kicker": ctx.say(f"day {i}") + " · " + ctx.day_label(day["date"]), "headline": ctx.say(" and ".join(day["places"]) or place),
                           "line": ctx.say(short(day.get("line") or "", 64))},
                          {**ctx.route_data((prev, here)), "day": i, "of": len(ctx.days), "weights": [1] * max(1, len(photos))}))
        prev = here
        beats += their_clip_beats(ctx, day["date"], clips, tr("dip", d))
    beats.append(beat("closer", "Closer", 4.4, tr("iris", d), ctx.closer(),
                      {"kicker": f"@{ctx.handle}", "headline": ctx.say(ctx.name), "line": ctx.with_line() or ctx.range_line()},
                      ctx.route_data()))
    return finish(ctx, {"id": "1", "name": ctx.say("the route"), "direction": d,
                        "structure": "day by day in order, the route drawing itself across a map of their coordinates",
                        "tone": "documentary", "clip_use": "their own clips in their days; a generated establishing shot and a flyover",
                        "idea": ctx.say(f"the trip as it happened: a dated title, the whole route drawn from {first} to {last}, then one "
                                        "beat a day with its photos, its line and the map thread inset, their own clips where they "
                                        "shot them, and the full route to close."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips})


def texture_subjects(ctx):
    pil = " ".join(ctx.taste.get("pillars") or [])
    names = [s.get("name") for s in (ctx.taste.get("palette") or {}).get("trip", [])[:3] if s.get("name")]
    base = ["sunlight glittering on moving sea water, close and abstract",
            "a warm wind moving through leaves and hanging laundry",
            "late light sliding across old plaster walls",
            "spray and foam breaking against dark rocks in slow motion"]
    if "food" in pil:
        base[1] = "steam rising off a table in a warm kitchen, crumbs and light"
    return [f"{b}, in {', '.join(names)}" if names else b for b in base]


def board_mood(ctx):
    d = "kinetic"
    clips = []
    beats = [beat("opener", "Opener", 2.0, None, ctx.opener(), {"kicker": ctx.range_line(), "headline": ctx.say(ctx.name)})]
    tex = texture_subjects(ctx)
    theirs = ctx.clips()
    k = 0
    for i, pl in enumerate(ctx.places):
        photos = ctx.place_photos(pl["name"], 6)
        beats.append(beat(f"place-{i + 1}", "Montage", 4.0, tr("whip", d, "from-right" if i % 2 == 0 else "from-left"), photos,
                          {"headline": ctx.say(pl["name"])}, {"weights": [1] * max(1, len(photos)), "place": ctx.say(pl["name"])}))
        if i < len(ctx.places) - 1:
            cid = f"{len(clips) + 1:02d}"
            img = (ctx.place_photos(pl["name"], 1) or [None])[0]
            clips.append({"id": cid, "beat": f"broll-{cid}", "role": "weather and texture b-roll", "seconds": 2, "image": img,
                          "prompt": ctx.prompt(tex[i % len(tex)], d, 2)})
            beats.append(beat(f"broll-{cid}", "ClipShot", 1.6, tr("bars", d), [img], {}, clip=cid))
        mine = [c for c in theirs if c.get("place") == pl["name"]][:1]
        for c in mine:
            if k >= 2:
                break
            k += 1
            cid = f"{len(clips) + 1:02d}"
            poster = ctx.photo(c.get("poster")) if c.get("poster") else None
            clips.append({"id": cid, "beat": f"clip-{cid}", "role": "their own clip", "prompt": None, "source": c["file"],
                          "seconds": 2, "image": poster})
            beats.append(beat(f"clip-{cid}", "ClipShot", 2.2, tr("whip", d, "from-right"), [poster],
                              {"headline": ctx.say(short(clean(c.get("caption")), 28))}, clip=cid))
    beats.append(beat("closer", "Closer", 3.6, tr("slide", d, "from-bottom"), ctx.closer(),
                      {"kicker": f"@{ctx.handle}", "headline": ctx.say(ctx.name), "line": ctx.range_line()}, ctx.route_data()))
    return finish(ctx, {"id": "2", "name": ctx.say("the mood"), "direction": d,
                        "structure": "place by place cut to the music, photos on the beat, almost no words",
                        "tone": "kinetic", "clip_use": "clip-first: generated weather and texture b-roll between places, their own clips on the beat",
                        "idea": ctx.say("how the trip felt rather than what happened: each place a burst of its photos cut on the beat "
                                        "under one heavy word, sea and wind and light between them, and the route snapping in at the end."),
                        "music": {"direction": "bright and driving, 112 bpm: claps, a hook, a lift into each place", "bpm": 112, "mood": "drive"},
                        "beats": beats, "clips": clips})


def board_postcards(ctx):
    d = "editorial"
    clips = []
    beats = [beat("opener", "Opener", 3.2, None, ctx.opener(),
                  {"kicker": ctx.range_line(), "headline": ctx.say(ctx.name),
                   "line": ctx.say(f"postcards from {len(ctx.places)} places" if len(ctx.places) > 1 else "a postcard")})]
    for i, pl in enumerate(ctx.places):
        first = next((x for x in ctx.picks.get("days") or [] if pl["name"] in x["places"]), None)
        # A place visited twice gets its first visit's photo and caption, so the postcards follow the route.
        photos = (ctx.fresh(first["photos"], 2) if first and first.get("photos") else []) or ctx.place_photos(pl["name"], 2)
        cap = clean(ctx.caption_of(photos[0])) if photos else ""
        day = next((x for x in ctx.days if pl["name"] in x["places"]), None)
        line = cap or (day or {}).get("line") or pl["name"]
        date = (ctx.date_of(photos[0]) if photos and cap else None) or (pl.get("days") or [day["date"] if day else ctx.lo])[0]
        cid = f"{len(clips) + 1:02d}"
        img = photos[1] if len(photos) > 1 else (photos[0] if photos else None)
        clips.append({"id": cid, "beat": f"arrive-{i + 1}", "role": "establishing shot", "seconds": 2, "image": img,
                      "prompt": ctx.prompt(f"an establishing shot of {pl['name']}: the place seen whole from a distance, light moving across it", d, 2)})
        beats.append(beat(f"arrive-{i + 1}", "ClipShot", 2.0, tr("dip", d) if i == 0 else tr("fade", d), [img], {}, clip=cid))
        beats.append(beat(f"postcard-{i + 1}", "Postcard", 4.8, tr("slide", d, "from-right"), photos[:1],
                          {"kicker": ctx.say(pl["name"]), "headline": ctx.say(short(line, 70)), "line": ctx.day_label(date)},
                          {"stamp": {"place": ctx.say(pl["name"]), "date": ctx.day_label(date)}, "no": i + 1, "of": len(ctx.places)}))
    beats.append(beat("closer", "Closer", 4.2, tr("match", d), ctx.closer(),
                      {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"greetings from {ctx.name}"), "line": ctx.with_line() or ctx.range_line()},
                      ctx.route_data()))
    return finish(ctx, {"id": "3", "name": ctx.say("postcards"), "direction": d,
                        "structure": "one postcard per place, their own caption set as type, a stamp with the place and the date",
                        "tone": "quiet editorial", "clip_use": "a generated establishing shot of each place before its postcard",
                        "idea": ctx.say("the trip as a stack of postcards on paper: each place arrives in a short establishing shot, then "
                                        "its photo as a print with their own caption set in a soft serif and a stamp for the day, ending "
                                        "on the route across the back of the last card."),
                        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips})


def shot_cuts(bt, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a many-photo beat, from its weights, snapped to the music's beats when given."""
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


def stories(ctx, beats):
    """Five story cards from the board's own beats: the title, three places, the route."""
    opener = next((b for b in beats if b["kind"] == "Opener"), beats[0])
    closer = next((b for b in reversed(beats) if b["kind"] == "Closer"), beats[-1])
    places, seen = [], set()
    for b in beats:
        if b["kind"] in PLACE_KINDS:
            key = (b.get("text") or {}).get("headline") if b["kind"] != "Postcard" else (b.get("text") or {}).get("kicker")
            if key not in seen:
                seen.add(key)
                places.append(b)
    if len(places) > 3:
        places = [places[round(i * (len(places) - 1) / 2)] for i in range(3)]
    rest = [b for b in beats if b not in places and b is not opener and b is not closer and b.get("photos")]
    while len(places) < 3 and rest:
        places.append(rest.pop(0))
    while len(places) < 3:
        places.append(opener)
    out = []
    for n, b in enumerate([opener, *places[:3], closer], 1):
        c = copy.deepcopy(b)
        c.update({"id": f"story-{n}", "transition": None, "settle": 0})
        c.pop("clip", None)
        if c.get("data"):
            c["data"].pop("cuts", None)
            c["data"]["weights"] = [1]
            if "upto" in c["data"] and c["kind"] == "Day":
                c["data"]["upto"] = [0, c["data"]["upto"][1]]
        out.append(c)
    return out


def finish(ctx, board):
    """Fills the system, drops empty beats, scales durations to the direction's target, adds the five story cards."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "trip": {"name": ctx.name, "from": ctx.lo, "to": ctx.hi, "days": len(ctx.days),
                                                  "places": [ctx.say(p["name"]) for p in ctx.places]},
                  "format": {"width": 1080, "height": 1920, "fps": FPS}, "system": ctx.system(d)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        empty = bt["kind"] not in ("Route",) and not bt["photos"] and not bt.get("clip")
        if not empty:
            beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (TARGET[d] * FPS + overlap) / whole if whole else 1
    for bt in beats:
        bt["frames"] = max(sec(1.2), int(round(bt["frames"] * k)))
        if bt.get("data") and bt["data"].get("weights") and len(bt["data"]["weights"]) != max(1, len(bt["photos"])):
            bt["data"]["weights"] = [1] * max(1, len(bt["photos"]))
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
    board["stories"] = stories(ctx, beats)
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
             f"- length: {film_seconds(board['beats']):.1f} s at {FPS} fps; one cut makes both films, 1080x1920 and 1920x1080",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             f"- places: {', '.join(board['trip']['places'])}",
             "", "## beats", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        if b["kind"] in ("Route", "Closer"):
            pts = (b.get("data") or {}).get("points") or []
            assets = f"the route, {len(pts)} points" + (", " + Path(b["photos"][0]).name if b.get("photos") else "")
        else:
            assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:3])
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips", ""]
    for c in board["clips"]:
        src = f" (their clip: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", "## story cards (1080x1920)", ""]
    for st in board["stories"]:
        lines.append(f"- {st['id']}: {st['kind']}, " + " / ".join(v for v in (st.get("text") or {}).values() if v))
    lines.append("")
    path.write_text("\n".join(lines))


def all_photos(b):
    out = set()
    for x in b["beats"] + b.get("stories", []):
        out |= set(x.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def cmd_draft(a):
    ctx = Ctx()
    if not ctx.days:
        sys.exit("the trip has no days: run research.py again, naming the trip")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    grade.grade_photos()
    boards = []
    for make in (board_route, board_mood, board_postcards):
        ctx.used = set()
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


KINDS = {"Opener", "Route", "Day", "Montage", "Postcard", "ClipShot", "Closer"}
PRESETS = set(design("transitions.json")["presets"])


def words_of(x):
    """Every word a beat puts on screen: its text and the place labels in its data."""
    out = [str(v) for v in (x.get("text") or {}).values() if v]
    data = x.get("data") or {}
    out += [str(p.get("place")) for p in data.get("points") or [] if p.get("place")]
    out += [str(v) for k, v in data.items() if k == "place" and v]
    out += [str(v) for v in (data.get("stamp") or {}).values() if v]
    return " ".join(out).lower()


def missing_places(b, places):
    seen = " ".join(words_of(x) for x in b["beats"])
    return [p for p in places if p and p.lower() not in seen]


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
        if bt["kind"] in ("Route", "Closer", "Day") and not (bt.get("data") or {}).get("points") and (b.get("trip") or {}).get("places"):
            issues.append(f"{bt['id']}: a {bt['kind']} beat with no route points")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    miss = missing_places(b, (b.get("trip") or {}).get("places") or [])
    if miss:
        issues.append(f"places in no beat: {', '.join(miss)} (every place of the trip appears in at least one beat)")
    st = b.get("stories") or []
    if len(st) != 5:
        issues.append(f"{len(st)} story cards; the board carries five")
    for x in st:
        if x["kind"] not in KINDS:
            issues.append(f"{x['id']}: unknown component {x['kind']}")
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
