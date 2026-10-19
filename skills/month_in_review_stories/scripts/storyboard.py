#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different series of story cards and a 15 s story film for the same month,
each with a rendered style sheet. Also the step that cuts the winning storyboard to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft [--template FILE]  # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: 3-5 cards, each 15 s with a still; the film 15 s; assets, text, clips
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (the month against the year, palette, type direction, pacing, register, the
pillars and the three moments and why each worked), then build/stats.json, picks.json, palette.json and
research.json. Every board is one design system (type, colors, texture, motion, the series mark) carried by a
numbered series of three to five story cards, one idea per card, and one 15 s story film that carries the whole
month. Each card is its own composition with its own beats, 15 s long, and names the one beat its static PNG is
drawn from, so the static and the animated card come from the same storyboard. The three boards differ on the
axis, on tone and on how generated clips are used:
  1  the series   five cards, one idea each: the month, what changed, the three        kinetic      clip-first;
                  that hit, what it was about, in my words                                           an opener clip per card
  2  the film     the film is the hero: the month's weather, the numbers, the three,    documentary  weather-first;
                  the colors and the sign-off in 15 s; three cards cut from it                       the weather and the three alive
  3  the diary    four diary pages with type: the month at a glance, the three taped    editorial    still-first;
                  in, the colors as paint chips, her own lines                                       openers, their stills animated
Generated clips: an opener per card, the month's "weather" (its mood as abstract motion in their palette) and the
three moments' stills brought to life; a clip that does not arrive is replaced by an animated treatment of the
named photo of theirs. --template names last month's out/template.json (default: out/template.json when it
exists): board 1 then follows its direction and card roles, so the series matches from month to month. The agent
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
FPS = 30
CARD_FRAMES = 450   # every card and the film run 15 s
STILL_FRAMES = 90
ROLES = ("cover", "change", "moments", "pillars", "voice")
TITLES = {"cover": "the month", "change": "what changed", "moments": "the three that hit", "pillars": "what it was about",
          "voice": "in my words"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
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




def clauses(cap):
    """A caption as its clauses, with no hashtags, emoji or mentions."""
    c = EMOJI.sub("", re.sub(r"[#@]\w[\w.]*", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    return [x.strip(" ,;:-") for x in re.split(r"(?<=[.!?;:])\s+|\s+-\s+|,\s+", c) if x.strip(" ,;:-.")]


def trim_stop(text):
    w = text.split()
    while len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


def short(cap, limit=60):
    """A caption's lead for the screen: whole clauses that fit, else the first clause cut at a word, never on a function word."""
    parts = clauses(cap)
    if not parts:
        return ""
    out = parts[0]
    if len(out) > limit * 1.2:
        out = out[:limit].rsplit(" ", 1)[0]
    for x in parts[1:]:
        if len(out) + 2 + len(x) > limit:
            break
        out = f"{out} {x}" if out.endswith((".", "!", "?")) else f"{out}, {x}"
    return trim_stop(out.rstrip(".!?"))


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def num(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def times(x):
    return f"{x:g}x" if x is not None else None


class Ctx:
    def __init__(self, template=None):
        self.taste = _env.read_json("build/taste.json")
        if not self.taste:
            sys.exit("build/taste.json is missing: run research.py and write the taste profile first")
        if not Path("build/taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before storyboards")
        self.stats = _env.read_json("build/stats.json") or {}
        if not self.stats.get("month"):
            sys.exit("build/stats.json names no month: run research.py first")
        self.picks = _env.read_json("build/picks.json") or {}
        self.chapters = self.picks.get("chapters", {})
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.index = _env.read_json("build/photo_index.json") or []
        self.lib = _env.read_json("build/library.json") or {}
        self.template = template
        self.used = set()
        self.handle = self.stats.get("handle") or self.taste.get("handle") or "you"
        m = self.stats["month"]
        self.month = {"key": m["key"], "name": m["name"], "short": m["short"], "year": m["year"]}
        self.year = int(m["year"])
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        nxt = int(m["month"]) % 12
        self.next_month = MONTHS[nxt]

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    @property
    def mname(self):
        return self.say(self.month["name"])

    def photo(self, src):
        """A library photo as the graded file the renderer reads (relative to build/public/)."""
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        return grade.graded_name(p)

    def chapter(self, name, n=None):
        out = [self.photo(p) for p in self.chapters.get(name, [])]
        out = [p for p in dict.fromkeys(out) if p]
        return out[:n] if n else out

    def three(self):
        """The month's three best moments in rank order: graded photo, numbers, date, the caption's lead line."""
        if hasattr(self, "_three"):
            return self._three
        info = {n["rank"]: n for n in self.picks.get("three", [])}
        why = {x["rank"]: x for x in self.research.get("moments", [])}
        out = []
        for t in self.stats.get("top_three", []):
            n = info.get(t["rank"])
            ph = self.photo(n["photo"]) if n else None
            if not ph:
                continue
            out.append({"rank": t["rank"], "kind": t["kind"], "photo": ph, "likes": t.get("likes"), "comments": t.get("comments"),
                        "times": t.get("times_usual"), "label": self.say(t.get("date_label") or ""),
                        "caption": self.say(short(t.get("caption") or "", 44) or t.get("date_label") or ""),
                        "video": n.get("video"), "subject": (why.get(t["rank"]) or {}).get("subject") or [],
                        "place": (why.get(t["rank"]) or {}).get("place")})
        self._three = out
        return out

    def numbers_line(self, t):
        if t.get("likes") is None:
            return self.say(f"{t['comments']} comments") if t.get("comments") is not None else None
        s = f"{t['likes']:,} likes"
        if t.get("times"):
            s += f" · {times(t['times'])} your usual"
        return self.say(s)

    def month_photos(self, n=12, skip=()):
        return [p for p in self.chapter("month") if p not in skip][:n]

    def pillar_photos(self, pillar, n=4):
        import research
        words = set(research.THEMES.get(pillar, []))
        out = []
        for r in self.lib.get("posts", []):
            if not r.get("media") or not r.get("ts") or f"{_ts(r['ts'])}" != self.month["key"]:
                continue
            if words & set(research.tokens(r.get("caption"))):
                ph = self.photo(r["media"][0])
                if ph and ph not in out:
                    out.append(ph)
            if len(out) >= n:
                break
        return out

    def lines(self, n=3, limit=30):
        """Her own lines from the month's captions: whole clauses short enough for one line of type each."""
        caps = [r.get("caption") or "" for r in self.lib.get("posts", []) if r.get("ts") and _ts(r["ts"]) == self.month["key"]] + \
               [c for c in (self.stats.get("register") or {}).get("samples", [])]
        out = []
        for c in caps:
            x = short(c, limit)
            if 8 <= len(x) <= limit and len(x.split()) >= 2 and x not in out:
                out.append(x)
            if len(out) >= n:
                break
        return [self.say(x) for x in out]

    def fresh(self, *cands):
        """The first candidate photo no other card of this board leads with yet; it is then taken."""
        flat = [p for c in cands for p in (c if isinstance(c, list) else [c]) if p]
        pick = next((p for p in flat if p not in self.used), flat[0] if flat else None)
        if pick:
            self.used.add(pick)
        return pick

    def colors(self):
        """The month's colors by the names she used for them when she named them, else by the palette's names."""
        words = [w["name"] for w in (self.research.get("change") or {}).get("color_words", [])]
        names = [s.get("name") for s in self.taste.get("palette", {}).get("month", []) if s.get("name")]
        return list(dict.fromkeys(words[:3] + names[:2]))

    def swatches(self, n=5):
        pal = self.taste.get("palette", {}).get("month") or self.taste.get("palette", {}).get("year") or []
        return [{"hex": s["hex"], "name": self.say(s.get("name") or ""), **({"photo": self.photo(s["photo"])} if s.get("photo") else {})} for s in pal[:n]]

    def system(self, direction):
        types = design("type.json")[direction]
        ease = design("easing.json")[direction]
        safe = {k: {x: v[x] for x in ("top", "bottom", "left", "right")} for k, v in design("safe-areas.json").items() if k != "about"}
        pal = self.taste.get("palette", {})
        month = [s["hex"] for s in (pal.get("month") or pal.get("year") or []) if s.get("hex")] or ["#6b5440", "#b8a17f"]
        shift = {s["hex"] for s in self.palette.get("shift", [])}
        darkest = min(month, key=lum)
        lightest = max(month, key=lum)
        vivid = sorted(month, key=lambda h: -sat(h) * (0.4 + lum(h)))
        new = [h for h in vivid if h in shift and h != vivid[0]]
        second = new[0] if new else (vivid[1] if len(vivid) > 1 else month[0])
        tex = self.taste.get("texture", {})
        lift = lambda c, bg, need: readable(mix(c, "#ffffff", 0.18) if sat(c) > 0.2 else c, bg, need)
        if direction == "editorial":
            paper = mix(lightest, "#f7f1e6", 0.62)
            bg, ink = paper, readable(mix(darkest, "#000000", 0.35), paper, 10)
            accent = readable(vivid[0], paper, 3.2)
            accent2 = readable(second, paper, 2.2)
            texture = {"grain": round(tex.get("grain", 0) * 0.7, 3), "vignette": 0, "leaks": False}
        elif direction == "kinetic":
            bg = mix(darkest, "#000000", 0.45)
            ink = mix(lightest, "#ffffff", 0.6)
            paper = ink
            accent = lift(vivid[0], bg, 3.0)
            accent2 = mix(second, "#000000", 0.15)
            if contrast(ink, accent) < 2.2:
                accent = mix(accent, "#000000", 0.25)
            if contrast(ink, accent2) < 3.0:
                accent2 = mix(accent2, "#000000", 0.35)
            texture = {"grain": round(tex.get("grain", 0) * 0.5, 3), "vignette": 0, "leaks": False}
        else:
            bg = mix(darkest, "#000000", 0.7)
            ink = mix(lightest, "#ffffff", 0.5)
            paper = mix(lightest, "#f4ead8", 0.5)
            accent = readable(vivid[0], bg, 4)
            accent2 = lift(second, bg, 3)
            texture = {"grain": tex.get("grain", 0), "vignette": tex.get("vignette", 0), "leaks": bool(tex.get("leaks"))}
        return {
            "direction": direction, "display": types["display"], "text": types["text"], "scale": types["scale"],
            "colors": {"bg": bg, "ink": ink, "accent": accent, "accent2": accent2, "muted": mix(ink, bg, 0.45), "paper": paper,
                       "swatches": [{"hex": w["hex"], "name": w["name"]} for w in self.swatches()]},
            "texture": texture, "ease": {k: ease[k] for k in ("enter", "exit", "move", "spring", "stagger")}, "safe": safe,
        }

    def prompt(self, subject, direction, seconds):
        colors = self.colors()
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        t = self.taste
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(colors) or 'their colors'}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")


def _ts(ts):
    import datetime as dt
    d = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc)
    return f"{d.year}-{d.month:02d}"


class Clips:
    """The clips one board asks for, numbered 01 onward; a clip used by several beats lists them all."""

    def __init__(self, ctx, direction):
        self.ctx, self.d, self.rows, self.by_key = ctx, direction, [], {}

    def ask(self, key, beat, role, subject=None, seconds=2, image=None, source=None):
        if key in self.by_key:
            c = self.by_key[key]
            c["beats"].append(beat)
            return c["id"]
        cid = f"{len(self.rows) + 1:02d}"
        c = {"id": cid, "key": key, "beats": [beat], "role": role, "seconds": seconds, "image": image}
        if source:
            c.update(prompt=None, source=source)
        else:
            c["prompt"] = self.ctx.prompt(subject, self.d, seconds)
        self.rows.append(c)
        self.by_key[key] = c
        return cid

    def weather(self, beat, seconds=3):
        ctx = self.ctx
        words = [w["word"] for w in (ctx.research.get("change") or {}).get("words", [])][:3]
        mood = {"editorial": "slow, calm, like a still afternoon", "kinetic": "quick gusts, bright and restless",
                "documentary": "a steady drift, like weather moving over a city"}[self.d]
        img = next((s["photo"] for s in ctx.swatches() if s.get("photo")), None) or (ctx.chapter("opener", 1) or [None])[0]
        return self.ask("weather", beat, f"the weather of {ctx.month['name']}: its mood as abstract motion in their palette",
                        f"the mood of {ctx.month['name']} as abstract motion: ribbons of pigment and soft light drifting and folding through "
                        f"each other{', the textures of ' + ', '.join(words) if words else ''}, {mood}", seconds, img)

    def opener(self, role, beat, image, seconds=2):
        ctx = self.ctx
        c = ctx.colors()
        subj = {
            "cover": f"an abstract opener: sheets of {c[0] if c else 'colored'} paper slide across each other and part to reveal light",
            "change": f"an abstract opener: one color floods into another, {(ctx.taste.get('palette', {}).get('year') or [{}])[0].get('name', 'warm brown')} "
                      f"giving way to {c[0] if c else 'a new color'}",
            "moments": f"an abstract opener: a fast push through a glowing {c[0] if c else 'warm'} frame, light flares across the lens",
            "pillars": f"macro textures of {', '.join((ctx.taste.get('change') or {}).get('words', [])[:3]) or 'their subjects'}, a slow sideways pan",
            "voice": f"an abstract opener: ink spreading slowly through wet paper in {', '.join(c[:2]) or 'their colors'}",
            "film": f"an abstract opener in {', '.join(c[:2]) or 'their colors'}: light sweeping across a textured wall",
        }[role]
        return self.ask(f"opener-{role}", beat, f"the opener of the card '{TITLES.get(role, role)}'" if role != "film" else "the film's opener",
                        subj, seconds, image)

    def alive(self, t, beat, seconds=3):
        ctx = self.ctx
        if t.get("video"):
            return self.ask(f"still-{t['rank']}", beat, "their own reel", seconds=seconds, image=t["photo"], source=t["video"])
        what = " and ".join(([t["place"]] if t.get("place") else []) + list(t.get("subject") or [])[:2]) or "this moment"
        return self.ask(f"still-{t['rank']}", beat, "their photo brought to life",
                        f"this photograph comes alive ({what}): the light shifts across it, a gentle movement, a slow push in", seconds, t["photo"])


VOCAB = {"kinetic": [("whip", "from-right"), ("bars", None), ("whip", "from-left"), ("slide", "from-bottom")],
         "documentary": [("iris", None), ("dip", None), ("fade", None), ("dip", None)],
         "editorial": [("wipe", "from-right"), ("dip", None), ("wipe", "from-left"), ("match", None)]}


def T(d, i):
    """The i-th cut in the direction's vocabulary of transitions."""
    pr, dr = VOCAB[d][i % len(VOCAB[d])]
    return tr(pr, d, dr)


def beat(bid, kind, seconds, transition=None, photos=None, text=None, clip=None, data=None, treatment=None):
    b = {"id": bid, "kind": kind, "frames": sec(seconds), "transition": transition, "photos": [p for p in (photos or []) if p],
         "text": {k: v for k, v in (text or {}).items() if v}}
    if clip:
        b["clip"] = clip
    if data is not None:
        b["data"] = data
    if treatment:
        b["treatment"] = treatment
    return b


def still_of(b, sid, **data):
    s = copy.deepcopy(b)
    s.update(id=sid, frames=STILL_FRAMES, transition=None, settle=0)
    s["from"] = b["id"]
    s.pop("clip", None)
    if data:
        s["data"] = {**(s.get("data") or {}), **data}
    return s


def facts(ctx):
    st = ctx.stats
    c, u, cad = st.get("counts") or {}, st.get("usual") or {}, st.get("cadence") or {}
    return c, u, cad


def num_stats(ctx, n=3):
    c, u, cad = facts(ctx)
    rows = [{"value": c.get("posts") or 0, "label": ctx.say("posts"),
             "line": ctx.say(f"a usual month has {round(u['posts'])}") if u.get("posts") is not None else None}]
    if cad.get("posting_days"):
        rows.append({"value": cad["posting_days"], "label": ctx.say("days I posted"),
                     "line": ctx.say(f"usually {round(u['posting_days'])}") if u.get("posting_days") is not None else None})
    if c.get("stories"):
        rows.append({"value": c["stories"], "label": ctx.say("stories"),
                     "line": ctx.say(f"usually {round(u['stories'])}") if u.get("stories") is not None else None})
    if cad.get("longest_run_days", 0) >= 2:
        rows.append({"value": cad["longest_run_days"], "label": ctx.say("days in a row"),
                     "line": ctx.say(f"most often on {cad['top_weekday']}s") if cad.get("top_weekday") else None})
    return [{k: v for k, v in r.items() if v is not None} for r in rows[:n]]


def vs_line(ctx):
    c, u, cad = facts(ctx)
    v = cad.get("vs_usual")
    if v and v >= 1.3:
        return ctx.say(f"{times(v)} a usual month")
    if v and v <= 0.75:
        return ctx.say(f"a quieter month: usually {round(u['posts'])}")
    return ctx.say(f"{cad.get('posts_per_week')} a week")


def new_line(ctx):
    ch = ctx.research.get("change") or {}
    if ch.get("new_subjects"):
        return ctx.say("new this month: " + " and ".join(ch["new_subjects"][:2]))
    if ch.get("places") and ch["places"][0] not in (ch.get("places_year") or []):
        return ctx.say(f"a month in {ch['places'][0]}")
    return None


def color_headline(ctx):
    shift = [c["name"] for c in ctx.palette.get("shift", [])]
    words = [w["name"] for w in (ctx.research.get("change") or {}).get("color_words", [])]
    if words:
        return ctx.say(" and ".join(words[:2]) + " all month")
    if shift:
        return ctx.say(f"{shift[0]} arrived")
    return ctx.say(f"the colors of {ctx.month['name']}")


def pillar_rows(ctx):
    out = []
    for p in (ctx.research.get("pillars") or [])[:4]:
        out.append({"text": ctx.say(p["pillar"]), "meta": ctx.say(f"{p['posts']} posts" + (" · new" if p.get("new") else ""))})
    return out


def pillar_groups(ctx):
    groups = []
    for p in (ctx.research.get("pillars") or [])[:3]:
        photos = ctx.pillar_photos(p["pillar"], 4)
        if len(photos) < 2:
            continue
        line = ctx.say("new this month" if p.get("new") else f"{int(round(p['year_share'] * 100))}% of my year")
        groups.append({"label": ctx.say(p["pillar"]), "headline": ctx.say(f"{p['posts']} posts of {p['pillar']}"), "line": line, "photos": photos})
        if len(groups) == 2:
            break
    return groups


# ------------------------------------------------------------------ the cards, one idea each
def card_cover(ctx, cl, d, p):
    op = ctx.chapter("opener", 1)
    ctx.fresh(op)
    month = ctx.month_photos(9)
    c, u, cad = facts(ctx)
    o = beat(f"{p}-open", "ClipShot", 1.5, photos=op)
    o["clip"] = cl.opener("cover", o["id"], op[0] if op else None)
    title = ctx.say("my month in review") if d == "kinetic" else ctx.say(f"{ctx.month['name']} in review")
    t = beat(f"{p}-title", "Opener", 5.4, T(d, 0), op, {"kicker": vs_line(ctx) if d == "documentary" else f"@{ctx.handle}", "headline": title,
                                                        "line": ctx.say(f"{c.get('posts', 0)} posts" + (f" · {c['stories']} stories" if c.get("stories") else ""))})
    m = beat(f"{p}-month", "Mosaic", 8.4, T(d, 1), month, data={"groups": [
        {"label": ctx.say(f"{ctx.month['name']} {ctx.year}"), "headline": ctx.say(f"{c.get('posts', 0)} posts this month"), "line": vs_line(ctx), "photos": month}]})
    return [o, t, m], still_of(t, f"{p}-still")


def card_change(ctx, cl, d, p):
    month = ctx.month_photos(12)
    sw = ctx.swatches()
    img = ctx.fresh([s["photo"] for s in sw if s.get("photo")], month)
    o = beat(f"{p}-open", "ClipShot", 1.5, photos=[img], text={"headline": ctx.say("what changed")} if d == "kinetic" else None)
    o["clip"] = cl.opener("change", o["id"], img)
    bgs = [ctx.fresh(month) for _ in range(3)]
    n = beat(f"{p}-numbers", "StatCard", 7.2, T(d, 0), bgs, {"kicker": ctx.say(f"{ctx.month['name']} against my year")},
             data={"stats": num_stats(ctx, 3)})
    pal = beat(f"{p}-colors", "Mosaic", 6.6, T(d, 1), [s.get("photo") for s in sw],
               {"kicker": ctx.say(f"the colors of {ctx.month['name']}"), "headline": color_headline(ctx), "line": new_line(ctx)},
               data={"mode": "palette", "swatches": sw})
    return [o, n, pal], still_of(n, f"{p}-still")


def card_moments(ctx, cl, d, p):
    three = ctx.three()
    o = beat(f"{p}-open", "ClipShot", 1.4, photos=[three[0]["photo"]], text={"headline": ctx.say("the three that hit")})
    o["clip"] = cl.opener("moments", o["id"], three[0]["photo"])
    beats = [o]
    for i, t in enumerate(sorted(three, key=lambda x: -x["rank"])):
        b = beat(f"{p}-no{t['rank']}", "ClipShot", 4.4, T(d, i), [t["photo"]],
                 {"kicker": t["label"], "headline": t["caption"], "line": ctx.numbers_line(t)}, data={"chapter": str(t["rank"])})
        b["clip"] = cl.alive(t, b["id"], 4)
        beats.append(b)
    likes = [t["likes"] for t in three if t.get("likes") is not None]
    line = ctx.say(", ".join(num(x) for x in likes[:-1]) + f" and {num(likes[-1])} likes") if len(likes) >= 2 else None
    st = beat(f"{p}-still", "PhotoLive", 3, None, [t["photo"] for t in three],
              {"kicker": ctx.say(f"most liked in {ctx.month['name']}"), "headline": ctx.say("the three that hit"), "line": line},
              data={"items": [{"rank": str(t["rank"])} for t in three]})
    return beats, still_of(st, f"{p}-still")


def card_pillars(ctx, cl, d, p):
    groups = pillar_groups(ctx)
    month = ctx.month_photos(4)
    img = ctx.fresh([g["photos"][0] for g in groups], ctx.month_photos(12))
    o = beat(f"{p}-open", "ClipShot", 1.4, photos=[img])
    o["clip"] = cl.opener("pillars", o["id"], img)
    k = beat(f"{p}-rows", "KineticType", 5.6, T(d, 0), [ctx.fresh(ctx.month_photos(12))], {"kicker": ctx.say(f"what {ctx.month['name']} was about")},
             data={"rows": pillar_rows(ctx)})
    beats = [o, k]
    if groups:
        beats.append(beat(f"{p}-groups", "Mosaic", 8.0, T(d, 1), [x for g in groups for x in g["photos"]], data={"groups": groups}))
    return beats, still_of(k, f"{p}-still")


def card_voice(ctx, cl, d, p):
    lines = ctx.lines(3, 26)
    c, u, cad = facts(ctx)
    three = ctx.three()
    op = ctx.chapter("opener", 1)
    img = ctx.fresh(ctx.month_photos(12)[2:], op)
    o = beat(f"{p}-open", "ClipShot", 1.4, photos=[img])
    o["clip"] = cl.opener("voice", o["id"], img)
    k = beat(f"{p}-lines", "KineticType", 6.0, T(d, 0), [img], {"kicker": ctx.say("in my words")},
             data={"rows": [{"text": l} for l in lines]})
    best = three[0]["likes"] if three and three[0].get("likes") is not None else None
    cl_ = beat(f"{p}-close", "Closer", 7.0, T(d, 1), [t["photo"] for t in three] + op,
               {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"see you in {ctx.next_month}"),
                "line": ctx.say(f"{ctx.month['name']}: {c.get('posts', 0)} posts" + (f", {num(best)} likes on the best" if best else ""))},
               data={"signoff": ctx.say(f"my {ctx.month['name']} on instagram")})
    return [o, k, cl_], still_of(cl_, f"{p}-still")


# ------------------------------------------------------------------ the diary pages
def diary_glance(ctx):
    c, u, cad = facts(ctx)
    lines = [{"n": num(c.get("posts", 0)), "text": ctx.say("posts" + (f", {times(cad['vs_usual'])} a usual month" if cad.get("vs_usual") else ""))}]
    if cad.get("posting_days"):
        lines.append({"n": num(cad["posting_days"]), "text": ctx.say("days I posted something")})
    if cad.get("longest_run_days", 0) >= 2:
        lines.append({"n": num(cad["longest_run_days"]), "text": ctx.say("days in a row")})
    if c.get("stories"):
        lines.append({"n": num(c["stories"]), "text": ctx.say("stories")})
    op = ctx.chapter("opener", 1)
    return {"kicker": ctx.say(f"{ctx.month['name']} {ctx.year}"), "headline": ctx.say(f"{ctx.month['name']}, in review"),
            "lines": lines[:4], "photos": (op + ctx.month_photos(3, skip=op))[:3]}


def diary_subject(ctx):
    ch = ctx.research.get("change") or {}
    pil = (ctx.research.get("pillars") or [{}])[0]
    head = ctx.say(f"{ch['new_subjects'][0]} took over") if ch.get("new_subjects") else ctx.say(f"mostly {pil.get('pillar', 'this')}")
    lines = [{"n": f"{int(round(pil.get('share', 0) * 100))}%", "text": ctx.say(f"of my posts were {pil.get('pillar', '')}")},
             {"n": f"{int(round(pil.get('year_share', 0) * 100))}%", "text": ctx.say("the rest of my year")}] if pil else []
    lines += [{"text": l} for l in ctx.lines(2, 30)]
    photos = ctx.pillar_photos(pil.get("pillar"), 2) if pil else []
    return {"kicker": ctx.say("what changed"), "headline": head, "lines": lines[:4], "photos": photos or ctx.month_photos(2)}


def diary_colors(ctx):
    sw = ctx.swatches(4)
    lines = [{"n": f"{int(round(s['share'] * 100))}%", "text": ctx.say(s.get("name") or "")}
             for s in (ctx.taste.get("palette", {}).get("month") or [])[:3]]
    return {"kicker": ctx.say(f"the colors of {ctx.month['name']}"), "headline": color_headline(ctx), "lines": lines,
            "swatches": [{"hex": s["hex"], "name": s["name"]} for s in sw], "photos": [s["photo"] for s in sw if s.get("photo")][:2]}


def diary_moment(ctx, t):
    lines = []
    if t.get("likes") is not None:
        lines.append({"n": num(t["likes"]), "text": ctx.say("likes")})
    if t.get("times"):
        lines.append({"n": times(t["times"]), "text": ctx.say("my usual")})
    if t.get("comments") is not None:
        lines.append({"n": num(t["comments"]), "text": ctx.say("comments")})
    return {"kicker": ctx.say(f"no. {t['rank']} · {t['label']}"), "headline": t["caption"], "lines": lines, "photos": [t["photo"]]}


def diary_voice(ctx):
    lines = ctx.lines(4, 30)
    return {"kicker": ctx.say("in my words"), "headline": lines[0] if lines else ctx.say(ctx.month["name"]),
            "lines": [{"text": l} for l in lines[1:4]], "photos": ctx.month_photos(4)[3:4]}


def card_diary_cover(ctx, cl, d, p):
    op = ctx.chapter("opener", 1)
    o = beat(f"{p}-open", "ClipShot", 1.5, photos=op)
    o["clip"] = cl.opener("cover", o["id"], op[0] if op else None)
    pg = beat(f"{p}-pages", "Diary", 13.5, T(d, 0), data={"pages": [diary_glance(ctx), diary_subject(ctx)]})
    return [o, pg], still_of(pg, f"{p}-still", still=0)


def card_diary_moments(ctx, cl, d, p):
    three = ctx.three()
    o = beat(f"{p}-open", "ClipShot", 1.4, photos=[three[0]["photo"]])
    o["clip"] = cl.opener("moments", o["id"], three[0]["photo"])
    pages = [diary_moment(ctx, t) for t in sorted(three, key=lambda x: -x["rank"])]
    pg = beat(f"{p}-pages", "Diary", 13.6, T(d, 0), data={"pages": pages})
    return [o, pg], still_of(pg, f"{p}-still", still=len(pages) - 1)


def card_diary_change(ctx, cl, d, p):
    sw = ctx.swatches()
    img = next((s["photo"] for s in sw if s.get("photo")), None)
    o = beat(f"{p}-open", "ClipShot", 1.5, photos=[img])
    o["clip"] = cl.opener("change", o["id"], img)
    pg = beat(f"{p}-pages", "Diary", 13.5, T(d, 0), data={"pages": [diary_colors(ctx), diary_subject(ctx)]})
    return [o, pg], still_of(pg, f"{p}-still", still=0)


def card_diary_voice(ctx, cl, d, p):
    beats, _ = card_voice(ctx, cl, d, p)
    pg = beat(f"{p}-lines", "Diary", 7.0, T(d, 0), data={"pages": [diary_voice(ctx)]})
    return [beats[0], pg, beats[2]], still_of(pg, f"{p}-still", still=0)


CARDS = {"cover": card_cover, "change": card_change, "moments": card_moments, "pillars": card_pillars, "voice": card_voice}
DIARY = {"cover": card_diary_cover, "moments": card_diary_moments, "change": card_diary_change, "voice": card_diary_voice}


# ------------------------------------------------------------------ the films
def film_beats(ctx, cl, d, kind):
    three = sorted(ctx.three(), key=lambda x: -x["rank"])
    op = ctx.chapter("opener", 1)
    c, u, cad = facts(ctx)
    month = ctx.month_photos(9)
    w = beat("f-weather", "ClipShot", 2.0 if kind != "film" else 2.4, None, op,
             {"kicker": ctx.say(f"{ctx.month['name']} {ctx.year}") if kind == "film" else None, "headline": ctx.say(ctx.month["name"])})
    w["clip"] = cl.weather(w["id"], 3)
    beats = [w]
    if kind == "diary":
        beats.append(beat("f-glance", "Diary", 3.6, T(d, 0), data={"pages": [diary_glance(ctx)]}))
    else:
        beats.append(beat("f-title", "Opener", 2.2, T(d, 0), op, {"kicker": f"@{ctx.handle}", "headline": ctx.say("my month in review"),
                                                                 "line": vs_line(ctx)}))
        beats.append(beat("f-numbers", "StatCard", 3.2 if kind == "film" else 2.6, T(d, 1), month[:3],
                          {"kicker": ctx.say(f"{ctx.month['name']} against my year")}, data={"stats": num_stats(ctx, 2)}))
        if kind == "film":
            sw = ctx.swatches()
            beats.append(beat("f-colors", "Mosaic", 2.2, T(d, 2), [s.get("photo") for s in sw],
                              {"kicker": ctx.say(f"the colors of {ctx.month['name']}"), "headline": color_headline(ctx)},
                              data={"mode": "palette", "swatches": sw}))
        else:
            beats.append(beat("f-month", "Mosaic", 2.2, T(d, 2), month, data={"groups": [
                {"label": ctx.say(f"{ctx.month['name']} {ctx.year}"), "headline": ctx.say(f"{c.get('posts', 0)} posts this month"), "photos": month}]}))
    for i, t in enumerate(three):
        b = beat(f"f-no{t['rank']}", "ClipShot", 1.7, T(d, i + 1), [t["photo"]],
                 {"kicker": t["label"], "headline": t["caption"], "line": ctx.numbers_line(t)}, data={"chapter": str(t["rank"])})
        b["clip"] = cl.alive(t, b["id"], 3)
        beats.append(b)
    if kind == "diary":
        beats.append(beat("f-colors", "Diary", 2.8, T(d, 0), data={"pages": [diary_colors(ctx)]}))
    best = three[-1]["likes"] if three and three[-1].get("likes") is not None else None
    beats.append(beat("f-close", "Closer", 2.6, T(d, 3), [t["photo"] for t in reversed(three)] + op,
                      {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"see you in {ctx.next_month}"),
                       "line": ctx.say(f"{ctx.month['name']}: {c.get('posts', 0)} posts" + (f", {num(best)} likes on the best" if best else ""))},
                      data={"signoff": ctx.say(f"my {ctx.month['name']} on instagram")}))
    return beats


# ------------------------------------------------------------------ the three boards
def make_board(ctx, bid, axis, d, roles, makers, film_kind, meta):
    cl = Clips(ctx, d)
    ctx.used = set()
    cards = []
    for n, role in enumerate(roles, 1):
        p = f"c{n}"
        beats, still = makers[role](ctx, cl, d, p)
        cards.append({"n": n, "id": f"{n:02d}-{role}", "role": role, "title": ctx.say(TITLES[role]), "beats": beats, "still": still})
    film = {"beats": film_beats(ctx, cl, d, film_kind)}
    return finish(ctx, {"id": bid, "axis": axis, "direction": d, **meta, "cards": cards, "film": film, "clips": cl.rows})


def usable_roles(ctx, roles):
    out = [r for r in roles if r != "moments" or ctx.three()]
    out = [r for r in out if r != "pillars" or ctx.research.get("pillars")]
    return out


def board_series(ctx):
    tpl = (ctx.template or {}).get("board") or {}
    d = tpl.get("direction") if tpl.get("direction") in ("kinetic", "editorial", "documentary") else "kinetic"
    roles = [c["role"] for c in (ctx.template or {}).get("cards", []) if c.get("role") in CARDS] or list(ROLES)
    roles = usable_roles(ctx, roles)[:5]
    follows = f"follows last month's template ({ctx.template['_path']})" if ctx.template else None
    return make_board(ctx, "1", "series", d, roles, CARDS, "series", {
        "name": ctx.say("the series"), "structure": "a numbered series of five stories, one idea each, and a film of the whole month",
        "tone": "kinetic", "clip_use": "clip-first: a generated opener in their colors leads every card; the three moments come alive",
        "idea": ctx.say(f"five stories, one idea each: {ctx.month['name']} at a glance, what changed against the year, the three that hit, "
                        "what it was about, and the month in her own words. heavy type that slams on the beat, the month's colors full frame."),
        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
        **({"follows": follows} if follows else {})})


def board_film(ctx):
    return make_board(ctx, "2", "film", "documentary", usable_roles(ctx, ["cover", "moments", "change"]), CARDS, "film", {
        "name": ctx.say("the film"), "structure": "one 15 s story film carries the whole month; three cards are cut from it",
        "tone": "documentary", "clip_use": "weather-first: the month's weather opens the film, the three moments alive, an opener per card",
        "idea": ctx.say(f"one unbroken 15 seconds: {ctx.month['name']}'s weather in their colors, the numbers in mono, the colors, "
                        "the three that hit alive, and the sign-off. the cards are the film's chapters, held."),
        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"}})


def board_diary(ctx):
    return make_board(ctx, "3", "diary", "editorial", usable_roles(ctx, ["cover", "moments", "change", "voice"]), DIARY, "diary", {
        "name": ctx.say("the diary"), "structure": "four diary pages with type: prints taped in, entries that write themselves, paint chips",
        "tone": "quiet editorial", "clip_use": "still-first: a short opener per page, the three moments' stills brought to life in the film",
        "idea": ctx.say(f"{ctx.month['name']} as a diary: ruled paper, a soft serif, her prints taped in, the numbers in the margin, "
                        "the colors as paint chips, and her own lines typing themselves out."),
        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"}})


def fit(beats, total=CARD_FRAMES):
    """Scales a beat set so it runs exactly `total` frames after the transition overlaps; the last beat takes the rounding."""
    beats = [b for b in beats if b.get("photos") or b.get("clip") or b["kind"] in ("StatCard", "KineticType", "Diary")]
    if beats:
        beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (total + overlap) / whole if whole else 1
    for b in beats:
        b["frames"] = max(sec(0.9), int(round(b["frames"] * k)))
    beats[-1]["frames"] += total - set_frames(beats)
    return beats


def set_frames(beats):
    return sum(b["frames"] for b in beats) - sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])


def shots(b):
    data = b.get("data") or {}
    if b["kind"] == "StatCard":
        return len(data.get("stats") or [])
    if b["kind"] == "Mosaic" and data.get("mode") != "palette":
        return len(data.get("groups") or [])
    if b["kind"] == "Diary":
        return len(data.get("pages") or [])
    if b["kind"] == "PhotoLive":
        return min(len(b.get("photos") or []), len(data.get("items") or []))
    return 1


def shot_cuts(b, grid_s=None, tol=0.25, start=0):
    """The sub-shot cut points of a many-shot beat (equal parts), snapped to the music's beats when given."""
    n = shots(b)
    if n < 2:
        return None
    lead = (b.get("transition") or {}).get("frames", 0)
    cuts = []
    for i in range(1, n):
        ideal = lead + (b["frames"] - lead) * i / n
        if grid_s:
            ideal = snap_to((start + ideal) / FPS, grid_s, tol) * FPS - start
        cuts.append(int(round(ideal)))
    lo, out = sec(0.6), []
    for c in cuts:
        out.append(max(lo + (out[-1] if out else 0), min(b["frames"] - lo, c)))
    return out if len(set(out)) == len(out) else None


def all_sets(board):
    """Every beat set of a board: the film's, then each card's, with the name its renders take."""
    return [("film", board["film"]["beats"])] + [(c["id"], c["beats"]) for c in board["cards"]]


def finish(ctx, board):
    """Fills the system and the month, fits every beat set to 15 s, records each clip's beats and length."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "year": ctx.year, "month": ctx.month, "format": {"width": 1080, "height": 1920, "fps": FPS},
                  "system": ctx.system(d)})
    for c in board["cards"]:
        c["beats"] = fit(c["beats"])
        c["still"]["photos"] = [p for p in c["still"].get("photos") or [] if p]
        for b in c["beats"]:
            cuts = shot_cuts(b)
            if cuts:
                b["data"]["cuts"] = cuts
    board["film"]["beats"] = fit(board["film"]["beats"])
    for b in board["film"]["beats"]:
        cuts = shot_cuts(b)
        if cuts:
            b["data"]["cuts"] = cuts
    by = {b["id"]: b for _, bs in all_sets(board) for b in bs}
    keep = []
    for c in board["clips"]:
        c["beats"] = [x for x in c["beats"] if x in by]
        if not c["beats"]:
            continue
        c["beat"] = c["beats"][0]
        secs = max(1, round(max(by[x]["frames"] for x in c["beats"]) / FPS))
        if c.get("prompt"):
            c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
        c.pop("key", None)
        keep.append(c)
    board["clips"] = keep
    return board


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
             f"- axis: {board['axis']}; {board['structure']}", f"- tone: {board['tone']}", f"- generated clips: {board['clip_use']}",
             f"- the series: {len(board['cards'])} story cards, each 15 s at {FPS} fps, 1080x1920, with a static PNG; one 15 s story film",
             f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines and numbers, {s['text']['family']} for labels and lines; scale {s['scale']}",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, accent2 {s['colors']['accent2']}; "
             f"swatches {', '.join(w['hex'] for w in s['colors']['swatches'])}",
             f"- texture: grain {s['texture']['grain']}, vignette {s['texture']['vignette']}, light leaks {'on' if s['texture']['leaks'] else 'off'}",
             f"- motion: enter {s['ease']['enter']}, spring {s['ease']['spring']}, stagger {s['ease']['stagger']} frames",
             f"- series mark: \"{board['month']['name'].upper()} {board['year']}  01 / {len(board['cards']):02d}\" with one progress segment per card"]
    if board.get("follows"):
        lines.append(f"- {board['follows']}")

    def table(title, beats, still=None):
        out = ["", f"## {title}", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
        for i, (b, t) in enumerate(zip(beats, timeline(beats))):
            txt = " / ".join(str(v) for v in (b.get("text") or {}).values() if v)
            data = b.get("data") or {}
            if b["kind"] == "Diary":
                txt = " // ".join((pg.get("headline") or "") for pg in data.get("pages", []))
            elif b["kind"] in ("KineticType",):
                txt += " / " + " · ".join(r["text"] for r in data.get("rows", []))
            elif b["kind"] == "StatCard":
                txt += " / " + " · ".join(f"{x['value']} {x['label']}" for x in data.get("stats", []))
            assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:2])
            if b.get("clip"):
                assets = f"clip {b['clip']}; " + assets
            tri = (b.get("transition") or {}).get("preset", "-")
            out.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
        if still:
            out.append(f"\nstatic PNG: `{still['id']}`, {still['kind']} at its settled frame")
        return out

    for c in board["cards"]:
        lines += table(f"card {c['n']:02d}: {c['title']} ({c['role']})", c["beats"], c["still"])
    lines += table("the film", board["film"]["beats"])
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (their reel: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for {', '.join('`' + x + '`' for x in c['beats'])}, {c['role']}, {c['seconds']} s{src}{img}: "
                     f"{c.get('prompt') or 'no generation; their own footage'}")
    path.write_text("\n".join(lines) + "\n")


def beat_photos(x):
    out = set(x.get("photos") or [])
    data = x.get("data") or {}
    for g in data.get("groups", []):
        out |= set(g.get("photos") or [])
    for pg in data.get("pages", []):
        out |= set(pg.get("photos") or [])
    out |= {w["photo"] for w in data.get("swatches", []) if w.get("photo")}
    return {p for p in out if p}


def all_photos(b):
    out = set()
    for _, beats in all_sets(b):
        for x in beats:
            out |= beat_photos(x)
    for c in b["cards"]:
        out |= beat_photos(c["still"])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    return out


def load_template(path):
    p = Path(path) if path else Path("out/template.json")
    if not p.exists():
        if path:
            sys.exit(f"{path} does not exist")
        return None
    t = _env.read_json(p) or {}
    t["_path"] = str(p)
    return t


def cmd_draft(a):
    ctx = Ctx(load_template(a.template))
    if not ctx.chapter("month"):
        sys.exit("no photo of the month could be prepared; picks.py names the ones that could not be opened")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    grade.grade_photos()
    boards = [make(ctx) for make in (board_series, board_film, board_diary)]
    referenced = sorted(set().union(*(all_photos(b) for b in boards)))
    grade.grade_photos([Path("build/photos") / Path(p).name for p in referenced])
    for b in boards:
        d = BOARDS / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        print(f"board {b['id']} {b['name']}: {len(b['cards'])} cards ({', '.join(c['role'] for c in b['cards'])}), film "
              f"{set_frames(b['film']['beats']) / FPS:.1f} s, {len(b['clips'])} clips -> {d}/storyboard.md")
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
    out = [_env.read_json(d) for d in sorted(BOARDS.glob("*/storyboard.json"))]
    if not out:
        sys.exit("no storyboards: run storyboard.py draft first")
    return out


KINDS = {"Opener", "ClipShot", "StatCard", "Mosaic", "KineticType", "PhotoLive", "Closer", "Diary"}
PRESETS = set(design("transitions.json")["presets"])
PLACEHOLDER = ("{", "}", "TODO", "lorem", "None", "XX")


def texts(b):
    out = [v for v in (b.get("text") or {}).values() if v]
    data = b.get("data") or {}
    for pg in data.get("pages", []):
        out += [pg.get("kicker"), pg.get("headline")] + [l.get("text") for l in pg.get("lines", [])]
    out += [r.get("text") for r in data.get("rows", [])] + [x.get("label") for x in data.get("stats", [])]
    out += [g.get(k) for g in data.get("groups", []) for k in ("label", "headline", "line")]
    return [str(x) for x in out if x]


def set_issues(name, beats, clips):
    issues = []
    n = set_frames(beats)
    if abs(n - CARD_FRAMES) > 15:
        issues.append(f"{name}: {n / FPS:.2f} s, not 15 s")
    for i, bt in enumerate(beats):
        if bt["kind"] not in KINDS:
            issues.append(f"{name} {bt['id']}: unknown component {bt['kind']}")
        t = bt.get("transition")
        if bt["frames"] < sec(0.8) + ((t or {}).get("frames", 0)):
            issues.append(f"{name} {bt['id']}: {bt['frames']} frames is under 0.8 s past its transition")
        if i and not t:
            issues.append(f"{name} {bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{name} {bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{name} {bt['id']}: clip {bt['clip']} is not in the clip list")
        if bt["kind"] in ("Opener", "ClipShot", "Closer", "PhotoLive", "Mosaic") and not beat_photos(bt) and not bt.get("clip"):
            issues.append(f"{name} {bt['id']}: {bt['kind']} has no photo")
        for v in texts(bt):
            if any(x in v for x in PLACEHOLDER):
                issues.append(f"{name} {bt['id']}: placeholder in text: {v}")
    return issues


def board_issues(b):
    issues = []
    clips = {c["id"] for c in b.get("clips", [])}
    if not 3 <= len(b.get("cards", [])) <= 5:
        issues.append(f"{len(b.get('cards', []))} cards; a series has three to five")
    ids = [x["id"] for _, bs in all_sets(b) for x in bs]
    if len(ids) != len(set(ids)):
        issues.append("beat ids repeat across the board's cards and film")
    for name, beats in all_sets(b):
        issues += set_issues(name, beats, clips)
    for c in b.get("cards", []):
        st = c.get("still")
        if not st or st.get("kind") not in KINDS:
            issues.append(f"card {c['id']}: no still beat for its static PNG")
        elif any(any(x in v for x in PLACEHOLDER) for v in texts(st)):
            issues.append(f"card {c['id']}: placeholder in the still's text")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
        if not c.get("image"):
            issues.append(f"clip {c['id']}: no photo named to stand in when it does not arrive")
    return issues


def cmd_check(a):
    bad = 0
    boards = load_boards()
    sigs = set()
    for b in boards:
        sigs.add((b["axis"], b["tone"], b["clip_use"]))
        iss = board_issues(b)
        bad += len(iss)
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'}, {len(b['cards'])} cards, "
              f"film {set_frames(b['film']['beats']) / FPS:.1f} s")
        for i in iss:
            print("  -", i)
    if len(boards) != 3 or len(sigs) != 3:
        print("  - the three boards must differ on axis, tone and clip use")
        bad += 1
    return 1 if bad else 0


def film_moments(beats, n):
    """n settled moments spread across a beat set."""
    cands = []
    tl = timeline(beats)
    for k, t in enumerate(tl):
        sh = list(t["shots"])
        sh[-1] = max(sh[-2] + 1, sh[-1] - (tl[k + 1]["transition"] if k + 1 < len(tl) else 0))
        for lo, hi in zip(sh, sh[1:]):
            lo = max(lo, t["transition"])
            cands.append((t["id"], t["start"] + lo + int((hi - lo) * 0.7)))
    if len(cands) <= n:
        return cands
    pick = sorted({round(i * (len(cands) - 1) / max(1, n - 1)) for i in range(n)})
    return [cands[i] for i in pick]


def cmd_sheets(a):
    import film
    stage_assets()
    boards = load_boards()
    jobs = []
    for b in boards:
        fr = BOARDS / b["id"] / "frames"
        fr.mkdir(parents=True, exist_ok=True)
        for f in fr.glob("*.png"):
            f.unlink()
        k = 0
        for c in b["cards"][:6]:
            k += 1
            jobs.append({"type": "still", "composition": "Card", "props": film.still_props(b, c), "frame": 0, "scale": 0.5,
                         "out": str((fr / f"{k:02d}.png").resolve())})
        props = film.props_for(b, b["film"]["beats"])
        for _, frame in film_moments(b["film"]["beats"], 6 - k):
            k += 1
            jobs.append({"type": "still", "composition": "Film", "props": props, "frame": frame, "scale": 0.5,
                         "out": str((fr / f"{k:02d}.png").resolve())})
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


def snap_set(beats, down, grid_s):
    """Moves every cut of a beat set onto the music, then sets the last beat so the set still runs 15 s."""
    moved, start = 0, 0
    for i in range(1, len(beats)):
        prev, bt = beats[i - 1], beats[i]
        t = (bt.get("transition") or {}).get("frames", 0)
        cut = (start + prev["frames"] - t / 2) / FPS
        new = snap_to(cut, down, 0.45)
        if new == cut:
            new = snap_to(cut, grid_s, 0.3)
        floor = sec(0.8) + ((prev.get("transition") or {}).get("frames", 0) if i > 1 else 0)
        frames = max(floor, int(round(new * FPS + t / 2 - start)))
        if frames != prev["frames"]:
            moved += 1
        prev["frames"] = frames
        start = start + prev["frames"] - t
    beats[-1]["frames"] += CARD_FRAMES - set_frames(beats)
    if beats[-1]["frames"] < sec(1.2):
        return fit(beats), moved
    for bt, tl in zip(beats, timeline(beats)):
        cuts = shot_cuts(bt, grid_s, 0.25, tl["start"])
        if cuts:
            bt["data"]["cuts"] = cuts
    return beats, moved


def cmd_snap(a):
    win = _env.read_json("build/winner.json")
    bid = a.board or (win or {}).get("board")
    if not bid:
        sys.exit("no winner: run vote.py tally first (or pass --board N)")
    b = _env.read_json(BOARDS / str(bid) / "storyboard.json")
    music = _env.read_json("build/music.json") or {}
    grid_s = music.get("beats") or []
    down = music.get("downbeats") or grid_s
    moved = 0
    b["film"]["beats"], m = snap_set(b["film"]["beats"], down, grid_s)
    moved += m
    for c in b["cards"]:
        c["beats"], m = snap_set(c["beats"], down, grid_s)
        moved += m
    b["film"]["timeline"] = timeline(b["film"]["beats"])
    for c in b["cards"]:
        c["timeline"] = timeline(c["beats"])
    b["seconds"] = CARD_FRAMES / FPS
    b["music"] = {**b.get("music", {}), **{k: music.get(k) for k in ("file", "bpm", "origin") if music.get(k)}}
    _env.write_json("build/film.json", b)
    print(f"board {bid}: the film and {len(b['cards'])} cards, {moved} cuts moved onto the music, each {b['seconds']:.1f} s -> build/film.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("--board")
    ap.add_argument("--template", help="draft: last month's out/template.json (default: out/template.json when it exists)")
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
