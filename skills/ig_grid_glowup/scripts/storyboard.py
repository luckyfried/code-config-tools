#!/usr/bin/env python3
"""Movement 2: three grid directions, each the next nine posts designed and a 15 s before->after film of the
grid, each with a rendered style sheet (the next nine in place over their real grid). Also the step that turns
the winning direction into the renderer's props, cut to the music.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: the nine, the grid, beats, assets, text, clips, 15 s
    python3 S/scripts/storyboard.py sheets           # build/storyboards/N/sheet.png (the next nine over the real grid)
                                                     # + frames/01..06.png and frames.png (six moments of the film)
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json, with the
                                                     # plan's captions (build/plan.json) -> build/film.json, 450 frames

draft reads build/taste.json first (palette, type, register), then build/audit.json (the findings the film's
before shot draws over the grid), grid.json (their last 30 posts), picks.json (the photos the nine come from)
and library.json (profile, captions). The three boards are the three grid directions:
  1  tonal and quiet      one warm grade across the nine; calm photos on the corners and the center, the
                          detailed ones between them so two busy frames never touch; no type
  2  color-blocked        each row of three leans one color of their palette, light at the top to dark at the
                          bottom; one color tile with their words in the middle of the nine
  3  photo and type       a checkerboard: five photos, four type posts set in their own words
Each board picks its nine from the library photos that never had a grid spot of their own (carousel slides,
stories, Facebook, the photo folder), never two from the same post. A slot no library photo fits gets a
generated still in their palette (build/stills/<board>-<n>.png from the image model when the agent has one,
else clips.py paints a light-on-a-wall still in the row's color); the board names it and the plan says so.
Post n is the n-th to go up: post 9 lands at the top left, post 1 at the bottom right of the nine.
The film: the opener (generated clip 01), the real grid with the findings drawn on it, the reveal (generated
clip 02), the nine landing in posting order over the real grid, three of the nine full size, the whole profile.
The agent may edit any storyboard.json (posts, text, photos, prompts) before sheets; check validates it.
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

DESIGN = _env.SKILL / "design"
BOARDS = Path("build/storyboards")
FPS = 30
FILM_FRAMES = 450
LENGTH = (14.5, 15.5)
LOOKS = {
    "tonal": {"id": "1", "system": "editorial", "name": "tonal and quiet",
              "structure": "one warm grade across the nine; calm photos on the corners and the center, detailed ones between",
              "tone": "quiet editorial", "clip_use": "clip-first: a slow generated opener in their light; a generated reveal of prints settling",
              "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"}},
    "blocks": {"id": "2", "system": "kinetic", "name": "color-blocked",
               "structure": "each row of three leans one color of their palette, light at the top to dark at the bottom",
               "tone": "bold graphic", "clip_use": "still-first: a fast generated whip of their colors opens; a generated reveal of color cards",
               "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"}},
    "alternate": {"id": "3", "system": "documentary", "name": "photo and type",
                  "structure": "a checkerboard: five photos and four type posts in their own words",
                  "tone": "documentary", "clip_use": "still-first: a handheld generated opener of their world; a generated reveal of a contact sheet",
                  "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"}},
}
CALM_SLOTS = [0, 2, 4, 6, 8]
NEAR = 18
ALIKE = 0.92
BUSY_SLOTS = [1, 3, 5, 7]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}
LABELS = {"palette": "off-palette run", "rhythm": "screenshots", "spacing": "busy beside busy", "crops": "cropped tight",
          "tight": "cropped tight", "rows": "light, dark, light"}


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


def to_lab(rgb):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb)
    x, y, z = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047, r * 0.2126 + g * 0.7152 + b * 0.0722, \
        (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    g_ = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = g_(x), g_(y), g_(z)
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)]


def lab_dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


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


def parent(src):
    """The post a library file belongs to: a carousel's slides share it."""
    stem = Path(str(src)).stem
    return stem.rsplit("-", 1)[0] if re.search(r"-\d+$", stem) else stem


class Ctx:
    def __init__(self):
        self.taste = _env.read_json("build/taste.json")
        if not self.taste:
            sys.exit("build/taste.json is missing: run research.py and write the taste profile first")
        if not Path("build/taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before storyboards")
        self.audit = _env.read_json("build/audit.json") or {}
        self.grid = _env.read_json("build/grid.json") or {}
        if not self.grid.get("cells"):
            sys.exit("build/grid.json is missing: run research.py first")
        self.pool = (_env.read_json("build/picks.json") or {}).get("pool", [])
        self.research = _env.read_json("build/research.json") or {}
        self.lib = _env.read_json("build/library.json") or {}
        self.handle = self.lib.get("handle") or self.taste.get("handle") or "you"
        self.year = int(self.taste.get("year") or self.lib.get("year") or dt.date.today().year)
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        endings = (self.research.get("captions") or {}).get("endings") or {}
        self.no_stop = endings.get(".", 0) <= 0.1 * max(1, sum(endings.values()))
        self.busy = (self.grid.get("median_detail") or 0.08) * 1.35
        self.captions = self.caption_index()
        self.taken = set()

    def say(self, s):
        """A line in their register: their case, and no closing full stop when they never end on one."""
        if s is None:
            return None
        s = s.lower() if self.lower else s
        return s[:-1] if self.no_stop and s.endswith(".") and not s.endswith("..") else s

    def caption_index(self):
        """Every library file's caption and date, so a photo of the nine can carry its own words."""
        out = {}
        for k in ("posts", "reels", "facebook"):
            for r in self.lib.get(k) or []:
                for m in r.get("media") or []:
                    out[str(m)] = (r.get("caption") or "", r.get("ts"))
        return out

    def words_for(self, row, taken):
        """The caption the photo was posted with, else the caption of the post nearest in time (a story's day),
        never one another of the nine already carries."""
        cap, _ = self.captions.get(str(row.get("src")), ("", None))
        if cap.strip() and cap not in taken:
            return cap
        ts = row.get("ts") or 0
        near = [(abs((r.get("ts") or 0) - ts), r.get("caption") or "") for r in self.lib.get("posts") or []
                if (r.get("caption") or "").strip() and r.get("caption") not in taken]
        near.sort(key=lambda x: x[0])
        return near[0][1] if near and near[0][0] <= 6 * 86400 else ""

    def photo(self, row):
        return grade.graded_name(row["photo"])

    def focal(self, row):
        f = row.get("focal") or [0.5, 0.45]
        return f"{round(f[0] * 100)}% {round(f[1] * 100)}%"

    def best_lines(self, n, used=(), limit=44):
        """Their own best lines: the lead line of the captions their audience liked and saved most."""
        rows = [r for r in (self.lib.get("posts") or []) + (self.lib.get("reels") or []) if (r.get("caption") or "").strip()]
        rows.sort(key=lambda r: -((r.get("likes") or 0) + 3 * (r.get("saves") or 0)))
        out, seen = [], set(used)
        for r in rows:
            line = self.say(short(r["caption"], limit))
            if line and len(line.split()) >= 3 and line not in seen:
                out.append({"line": line, "caption": r["caption"]})
                seen.add(line)
            if len(out) >= n:
                break
        return out

    def palette(self):
        sw = (self.taste.get("palette") or {})
        return [s for s in (sw.get("year") or []) + (sw.get("likes") or []) if s.get("hex")]

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

    def prompt(self, subject, direction, seconds):
        t = self.taste
        colors = [s.get("name") for s in t.get("palette", {}).get("likes", [])[:3] if s.get("name")] + \
                 [s.get("name") for s in t.get("palette", {}).get("year", [])[:2] if s.get("name")]
        camera = {"editorial": "a slow push-in, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")

    # ------------------------------------------------------------ the real grid and the profile
    def cells(self):
        """Their last 30 as the renderer reads them: the cover as posted, ungraded, at build/public/grid/NN.jpg."""
        if hasattr(self, "_cells"):
            return self._cells
        d = grade.PUBLIC / "grid"
        d.mkdir(parents=True, exist_ok=True)
        out = []
        for c in self.grid["cells"]:
            name = None
            if c.get("cover") and Path(c["cover"]).exists():
                name = f"grid/{c['pos']:02d}.jpg"
                shutil.copyfile(c["cover"], grade.PUBLIC / name)
            out.append({"pos": c["pos"], "photo": name, "kind": "reel" if c.get("kind") == "reel" else "post"})
        self._cells = out
        return out

    def profile(self):
        best = max(self.pool, key=lambda r: r.get("fit", 0)) if self.pool else None
        return {"name": self.lib.get("name") or self.handle, "bio": self.lib.get("bio") or "",
                "posts": len(self.lib.get("posts") or []) + len(self.lib.get("reels") or []),
                "followers": len(self.lib.get("followers") or []), "following": len(self.lib.get("following") or []),
                "avatar": self.photo(best) if best else None}

    def callouts(self):
        """Up to three findings the before shot draws over the grid, the ones with the fewest posts first."""
        out = []
        for f in sorted(self.audit.get("findings") or [], key=lambda f: len(f.get("positions") or [])):
            pos = [p for p in f.get("positions") or [] if p < len(self.grid["cells"])]
            if not pos or len(pos) > 7:
                continue
            out.append({"positions": sorted(pos), "label": self.say(f.get("label") or LABELS.get(f.get("kind"), f.get("title", "")))})
            if len(out) == 3:
                break
        return sorted(out, key=lambda c: min(c["positions"]))

    # ------------------------------------------------------------ choosing the nine
    def sig(self, row):
        """A photo's composition as edge directions in four quadrants (a small histogram of oriented gradients), so two
        shots of one scene read as alike whatever their colors, and two subjects that share a palette do not."""
        cache = self.__dict__.setdefault("_sig", {})
        if row["photo"] not in cache:
            import math
            from PIL import Image, ImageOps
            W, H = 64, 80
            im = ImageOps.fit(Image.open(row["photo"]).convert("L"), (W, H))
            px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
            bins = [0.0] * 32
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    gx = px[y * W + x + 1] - px[y * W + x - 1]
                    gy = px[(y + 1) * W + x] - px[(y - 1) * W + x]
                    m = math.hypot(gx, gy)
                    if m < 8:
                        continue
                    a = math.atan2(gy, gx) % math.pi
                    bins[(int(y >= H // 2) * 2 + int(x >= W // 2)) * 8 + int(a / math.pi * 8) % 8] += m
            norm = math.sqrt(sum(b * b for b in bins)) or 1
            cache[row["photo"]] = [b / norm for b in bins]
        return cache[row["photo"]]

    def alike(self, a, b):
        return sum(i * j for i, j in zip(self.sig(a), self.sig(b))) > ALIKE

    def take(self, rows, n, score, used):
        """The n best rows by score: never two from one post, never two near copies, never more than two of one scene
        in the nine (counting what the board already holds) while other scenes remain, then three, marked used."""
        out = []
        held = used.setdefault("rows", [])
        ranked = sorted(rows, key=score, reverse=True)
        for limit in (2, 3):
            for r in ranked:
                if len(out) == n:
                    break
                if parent(r["src"]) in used["parents"] or any(lab_dist(r["lab"], x["lab"]) < 5 for x in out):
                    continue
                if sum(1 for x in held + out if self.alike(r, x)) >= limit:
                    continue
                out.append(r)
                used["parents"].add(parent(r["src"]))
        held += out
        return out

    def post(self, n, row, taken=None, **kw):
        taken = self.taken if taken is None else taken
        cap = self.words_for(row, taken)
        taken.add(cap)
        return {"n": n, "kind": "photo", "photo": self.photo(row), "focal": self.focal(row), "source": row.get("src"),
                "from": row.get("kind"), "caption": self.say(EMOJI.sub("", cap).strip()) if cap else "", **kw}

    def standin(self, board_id, n, color, name, look):
        sid = f"{board_id}-{n}"
        subj = {"tonal": "late light falling across a plain linen wall, the soft shadow of a window frame",
                "blocks": f"a still life on a {name} ground: one ceramic cup and a folded cloth, the same {name} color all over",
                "alternate": "afternoon light through a shutter on a plaster wall, the shadow of a leaf"}[look]
        prompt = (f"A photograph: {subj}. In {name} ({color}), matching the rest of the feed. Shot on 35mm film, soft grain, "
                  f"4:5 portrait. No text, no logos, no people.")
        return {"n": n, "kind": "photo", "photo": f"stills/{sid}.jpg", "still": True, "focal": "50% 50%", "source": None,
                "caption": "", "still_id": sid, "still_prompt": prompt, "still_color": color}


def nine_tonal(ctx, bid):
    used = {"parents": set()}
    fit = lambda r: r.get("fit", 0) - (0.12 if r.get("detail", 0) > ctx.busy else 0)
    rows = ctx.take(ctx.pool, 9, fit, used)
    rows.sort(key=lambda r: r.get("detail", 0))
    calm, busy = rows[:5], rows[5:]
    calm.sort(key=lambda r: -r.get("bright", 0))
    slots = {}
    for s, r in zip([4, 0, 8, 2, 6], calm):
        slots[s] = r
    for s, r in zip(BUSY_SLOTS, busy):
        slots[s] = r
    posts = []
    for s in range(9):
        n = 9 - s
        posts.append(ctx.post(n, slots[s]) if s in slots else ctx.standin(bid, n, ctx.palette()[0]["hex"], ctx.palette()[0].get("name", ""), "tonal"))
    return posts


def row_colors(ctx):
    """Three colors of theirs for the three rows, light at the top, their boldest in the middle, dark at the bottom.
    A row whose color few library photos lean toward gets generated stills in that color."""
    labs = [(s, to_lab(hex_rgb(s["hex"]))) for s in ctx.palette()]

    def near(r, lab):
        cs = [c for c in r.get("colors") or [] if c.get("share", 0) >= 0.15][:2] or (r.get("colors") or [])[:1]
        return min((lab_dist(to_lab(c["rgb"]), lab) for c in cs), default=99)

    chroma = lambda lab: (lab[1] ** 2 + lab[2] ** 2) ** 0.5
    count = {s["hex"]: sum(1 for r in ctx.pool if near(r, lab) < NEAR) for s, lab in labs}
    ok = [x for x in labs if count[x[0]["hex"]] >= 2] or labs
    light = max(ok, key=lambda x: x[1][0])
    dark = min(ok, key=lambda x: x[1][0])
    apart = lambda x: min(lab_dist(x[1], light[1]), lab_dist(x[1], dark[1])) >= 20
    mid = max([x for x in ok if apart(x)] or [x for x in labs if apart(x)] or [light], key=lambda x: chroma(x[1]))
    return [light, mid, dark], near


def nine_blocks(ctx, bid):
    used = {"parents": set()}
    chosen, near = row_colors(ctx)
    lines = ctx.best_lines(1, limit=34)
    posts = []
    for row, (sw, lab) in enumerate(chosen):
        want = [s for s in range(row * 3, row * 3 + 3) if s != 4]
        cands = [r for r in ctx.pool if near(r, lab) < NEAR]
        got = ctx.take(cands, len(want), lambda r: -near(r, lab) + 10 * r.get("fit", 0), used)
        for s in want:
            n = 9 - s
            if got:
                posts.append(ctx.post(n, got.pop(0), tint=sw["hex"]))
            else:
                p = ctx.standin(bid, n, sw["hex"], sw.get("name") or "their color", "blocks")
                p["tint"] = sw["hex"]
                posts.append(p)
        if row == 1:
            fill = sw["hex"]
            line = lines[0] if lines else {"line": ctx.say(f"@{ctx.handle}"), "caption": ""}
            posts.append({"n": 5, "kind": "color", "photo": None, "bg": fill, "tint": fill,
                          "text": {"headline": line["line"]}, "caption": ctx.say(EMOJI.sub("", line["caption"]).strip())})
    return sorted(posts, key=lambda p: -p["n"])


def nine_alternate(ctx, bid):
    used = {"parents": set()}
    rows = ctx.take(ctx.pool, 5, lambda r: r.get("fit", 0), used)
    lines = ctx.best_lines(4, limit=46)
    sysd = ctx.system("documentary")
    fills = {1: sysd["colors"]["bg"], 3: sysd["colors"]["paper"], 5: sysd["colors"]["paper"], 7: sysd["colors"]["bg"]}
    posts = []
    places = [p for p in (ctx.taste.get("places") or []) if p != "home"]
    for s in range(9):
        n = 9 - s
        if s in CALM_SLOTS:
            posts.append(ctx.post(n, rows.pop(0)) if rows else ctx.standin(bid, n, ctx.palette()[0]["hex"], ctx.palette()[0].get("name", ""), "alternate"))
        else:
            ln = lines.pop(0) if lines else {"line": ctx.say(f"@{ctx.handle}"), "caption": ""}
            where = next((p for p in places if p in ln["caption"].lower()), None)
            posts.append({"n": n, "kind": "type", "photo": None, "bg": fills[s],
                          "text": {"kicker": ctx.say(where) if where else None, "headline": ln["line"]},
                          "caption": ctx.say(EMOJI.sub("", ln["caption"]).strip())})
    return sorted(posts, key=lambda p: -p["n"])


NINE = {"tonal": nine_tonal, "blocks": nine_blocks, "alternate": nine_alternate}


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def world_subject(ctx):
    pl = [x for x in (ctx.taste.get("places") or []) if x != "home"]
    pil = ctx.taste.get("pillars") or []
    where = ", ".join(pl[:3]) if pl else "a sunlit kitchen table"
    return f"the world this feed lives in: {where}, {', '.join(pil[:2]) or 'light'}, light moving slowly across it"


REVEAL = {"tonal": "a hand-sized stack of warm photo prints on a linen table; the prints slide apart and settle into a neat grid of nine",
          "blocks": "flat color cards in their palette slide in from the edges and snap into three rows on a table, top light, bottom dark",
          "alternate": "a contact sheet on a light table, a loupe gliding across it, frames lighting up one after another"}
TRANS = {"tonal": ("dip", "wipe", "match", "dip", "fade"),
         "blocks": ("bars", "whip", "slide", "whip", "bars"),
         "alternate": ("iris", "wipe", "match", "slide", "fade")}
AFTER_LINE = {"tonal": "one warm grade, nothing loud", "blocks": "a color a row, light to dark", "alternate": "a photo, then your words"}


def make_board(ctx, look):
    ctx.taken = set()
    L = LOOKS[look]
    d, bid = L["system"], L["id"]
    posts = NINE[look](ctx, bid)
    first = next((p for p in posts if p.get("photo") and not p.get("still")), None)
    callouts = ctx.callouts()
    t = TRANS[look]
    n_find = len(ctx.audit.get("findings") or [])
    show = [9, 5, 1]
    beats = [
        {"id": "opener", "kind": "Opener", "frames": sec(2.0), "transition": None, "clip": "01",
         "photos": [first["photo"]] if first else [], "data": {"word": "grid"},
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("your grid, glowed up"), "line": ctx.say("the next nine posts")}},
        {"id": "before", "kind": "Feed", "frames": sec(3.6), "transition": tr(t[0], d),
         "data": {"mode": "before", "callouts": callouts},
         "text": {"kicker": ctx.say("your grid now"), "headline": ctx.say(f"{n_find} things pull it apart" if n_find else "your last 30 posts")}},
        {"id": "reveal", "kind": "ClipShot", "frames": sec(2.4), "transition": tr(t[1], d, "from-right"), "clip": "02",
         "photos": [first["photo"]] if first else [], "text": {"kicker": ctx.say("the next nine"), "headline": ctx.say(L["name"])}},
        {"id": "after", "kind": "Feed", "frames": sec(4.2), "transition": tr(t[2], d),
         "data": {"mode": "after", "weights": [1] * 9 + [3]},
         "text": {"kicker": ctx.say("the next nine"), "headline": ctx.say(L["name"]), "line": ctx.say(AFTER_LINE[look])}},
        {"id": "posts", "kind": "Feed", "frames": sec(2.4), "transition": tr(t[3], d, "from-right"),
         "data": {"mode": "posts", "show": show, "weights": [1] * len(show)}},
        {"id": "end", "kind": "Feed", "frames": sec(1.8), "transition": tr(t[4], d),
         "data": {"mode": "end"}, "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("post them in this order")}},
    ]
    clips = [{"id": "01", "beat": "opener", "role": "the opener: the world the feed lives in",
              "prompt": ctx.prompt(world_subject(ctx), d, 2), "seconds": 2, "image": first["photo"] if first else None},
             {"id": "02", "beat": "reveal", "role": "the reveal: from the grid now to the next nine",
              "prompt": ctx.prompt(REVEAL[look], d, 3), "seconds": 3, "image": first["photo"] if first else None}]
    stills = [{"id": p["still_id"], "n": p["n"], "prompt": p["still_prompt"], "color": p["still_color"], "file": p["photo"]}
              for p in posts if p.get("still")]
    board = {"id": bid, "look": look, "name": ctx.say(L["name"]), "direction": d, "structure": L["structure"], "tone": L["tone"],
             "clip_use": L["clip_use"], "music": L["music"], "handle": ctx.handle, "year": ctx.year,
             "format": {"width": 1080, "height": 1920, "fps": FPS}, "system": ctx.system(d),
             "idea": ctx.say(idea(look, posts)), "posts": posts, "grid": ctx.cells(), "profile": ctx.profile(),
             "beats": beats, "clips": clips, "stills": stills}
    return finish(board)


def idea(look, posts):
    n_still = sum(1 for p in posts if p.get("still"))
    extra = f" {n_still} of the nine are generated stills in their palette, because no library photo fit the slot." if n_still else ""
    return {"tonal": "nine of their own photos under one warm grade, the quiet ones on the corners and the center so the eye rests "
                     "between the detailed ones; it continues the warm half of the grid and leaves the off-palette run behind.",
            "blocks": "the grid in three bands of their own colors, light at the top to dark at the bottom, every photo leaning toward "
                      "its row's color, one solid tile of their words holding the middle.",
            "alternate": "a checkerboard of five photos and four type posts in their own best lines, so text has a planned place "
                         "and never lands as a screenshot."}[look] + extra


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
    lo = sec(0.2)
    out = []
    for c in cuts:
        c = max(lo + (out[-1] if out else 0), min(bt["frames"] - lo, c))
        out.append(c)
    return out if len(set(out)) == len(out) else None


def finish(board):
    """Scales the beats so the film runs FILM_FRAMES after the transitions overlap, and cuts the many-shot beats."""
    beats = board["beats"]
    beats[0]["transition"] = None
    overlap = sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    whole = sum(b["frames"] for b in beats)
    k = (FILM_FRAMES + overlap) / whole
    for bt in beats:
        bt["frames"] = max(sec(1.0), int(round(bt["frames"] * k)))
    pin(beats)
    for bt in beats:
        cuts = shot_cuts(bt)
        if cuts:
            bt["data"]["cuts"] = cuts
    by = {b["id"]: b for b in beats}
    for c in board["clips"]:
        secs = max(1, round(by[c["beat"]]["frames"] / FPS))
        c["prompt"] = c["prompt"].replace(f"{c['seconds']} seconds", f"{secs} seconds")
        c["seconds"] = secs
    return board


def pin(beats):
    """The last beat takes up the difference so the whole film is exactly FILM_FRAMES."""
    beats[-1]["frames"] += FILM_FRAMES - film_frames(beats)


def film_frames(beats):
    return sum(b["frames"] for b in beats) - sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])


def film_seconds(beats):
    return film_frames(beats) / FPS


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t,
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]]})
        start += b["frames"]
    return out


def describe(p):
    if p["kind"] == "photo":
        what = f"generated still in {p.get('still_color') or 'their palette'}" if p.get("still") else f"their photo {Path(p['photo']).name} (from a {p.get('from') or 'library'} photo)"
        return what + (f", leaning {p['tint']}" if p.get("tint") else "")
    t = p.get("text") or {}
    return f"{p['kind']} post on {p.get('bg')}: \"{t.get('headline')}\"" + (f" ({t['kicker']})" if t.get("kicker") else "")


def write_md(board, path):
    s = board["system"]
    lines = [f"# direction {board['id']}: {board['name']}", "", board["idea"], "",
             f"- the nine: {board['structure']}", f"- tone: {board['tone']}", f"- generated clips: {board['clip_use']}",
             f"- the film: {film_seconds(board['beats']):.1f} s at {FPS} fps, 1080x1920", f"- music: {board['music']['direction']}",
             f"- type: {s['display']['family']} for headlines, {s['text']['family']} for labels",
             f"- color: bg {s['colors']['bg']}, ink {s['colors']['ink']}, accent {s['colors']['accent']}, paper {s['colors']['paper']}",
             f"- style sheet: sheet.png (the next nine above the line, their grid now below it)", "",
             "## the next nine (post 1 goes up first; post 9 ends at the top left)", "", "| post | slot | what | caption draft |", "|---|---|---|---|"]
    for p in sorted(board["posts"], key=lambda p: p["n"]):
        slot = 9 - p["n"]
        lines.append(f"| {p['n']} | row {slot // 3 + 1}, {['left', 'middle', 'right'][slot % 3]} | {describe(p)} | {p.get('caption') or ''} |")
    lines += ["", "## the film", "", "| # | time | beat | component | text | transition in |", "|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        comp = b["kind"] + (f" ({b['data']['mode']})" if b["kind"] == "Feed" else "") + (f", clip {b['clip']}" if b.get("clip") else "")
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {comp} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{img}: {c['prompt']}")
    if board.get("stills"):
        lines += ["", "## stills the image model makes (no library photo fit these slots)", ""]
        for st in board["stills"]:
            lines.append(f"- post {st['n']} (build/stills/{st['id']}.png, 1080x1350): {st['prompt']}")
    path.write_text("\n".join(lines) + "\n")


def all_photos(b):
    out = {p["photo"] for p in b["posts"] if p.get("photo")}
    out |= {c["photo"] for c in b["grid"] if c.get("photo")}
    for x in b["beats"]:
        out |= set(x.get("photos") or [])
    out |= {c["image"] for c in b["clips"] if c.get("image")}
    if b["profile"].get("avatar"):
        out.add(b["profile"]["avatar"])
    return out


def cmd_draft(a):
    ctx = Ctx()
    if len(ctx.pool) < 1:
        sys.exit("picks.json has no library photos to draw the nine from; picks.py names what it could not open")
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    boards = [make_board(ctx, look) for look in LOOKS]
    referenced = sorted({p for b in boards for p in all_photos(b) if p.startswith("graded/")})
    grade.grade_photos([Path("build/photos") / Path(p).name for p in referenced])
    stage_assets()
    import clips
    clips.make_stills([st for b in boards for st in b.get("stills", [])])
    for b in boards:
        d = BOARDS / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        n_st = len(b.get("stills", []))
        print(f"direction {b['id']} {b['name']}: nine posts ({n_st} generated still{'s' if n_st != 1 else ''}), "
              f"{len(b['beats'])} beats, {film_seconds(b['beats']):.1f} s -> {d}/storyboard.md")
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


KINDS = {"Opener", "ClipShot", "Feed"}
MODES = {"before", "after", "posts", "end"}
PRESETS = set(design("transitions.json")["presets"])
PLACEHOLDER = ("{", "}", "TODO", "lorem", "None", "XX")


def board_issues(b):
    issues = []
    secs = film_seconds(b["beats"])
    if not LENGTH[0] <= secs <= LENGTH[1]:
        issues.append(f"length {secs:.2f} s is outside {LENGTH[0]}-{LENGTH[1]} s")
    posts = b.get("posts") or []
    if sorted(p.get("n") for p in posts) != list(range(1, 10)):
        issues.append(f"the nine must be posts 1 to 9 once each, has {sorted(p.get('n') for p in posts)}")
    photos = [p["photo"] for p in posts if p.get("photo")]
    if len(photos) != len(set(photos)):
        issues.append("a photo is used twice in the nine")
    for p in posts:
        if p.get("kind") not in ("photo", "type", "color"):
            issues.append(f"post {p.get('n')}: unknown kind {p.get('kind')}")
        if p.get("kind") == "photo" and not p.get("photo"):
            issues.append(f"post {p.get('n')}: a photo post with no photo")
        if p.get("kind") in ("type", "color") and not (p.get("text") or {}).get("headline"):
            issues.append(f"post {p.get('n')}: a {p['kind']} post with no words")
        for v in list((p.get("text") or {}).values()) + [p.get("caption")]:
            if v and any(x in str(v) for x in PLACEHOLDER):
                issues.append(f"post {p.get('n')}: placeholder in text: {v}")
    if len(b.get("grid") or []) < 3:
        issues.append("the real grid is missing (grid.json had fewer than three posts)")
    clips = {c["id"] for c in b.get("clips", [])}
    for i, bt in enumerate(b["beats"]):
        if bt["kind"] not in KINDS:
            issues.append(f"{bt['id']}: unknown component {bt['kind']}")
        if bt["kind"] == "Feed" and (bt.get("data") or {}).get("mode") not in MODES:
            issues.append(f"{bt['id']}: Feed needs a mode out of {sorted(MODES)}")
        if bt["frames"] < sec(0.8):
            issues.append(f"{bt['id']}: {bt['frames']} frames is under 0.8 s")
        t = bt.get("transition")
        if i and not t:
            issues.append(f"{bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and not isinstance(bt["clip"], str):
            issues.append(f"{bt['id']}: the clip is named by its id (a string); film.py resolves the file")
        elif bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{bt['id']}: clip {bt['clip']} is not in the clip list")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in PLACEHOLDER):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    for p in sorted(all_photos(b)):
        if not (grade.PUBLIC / p).exists():
            issues.append(f"missing asset build/public/{p}")
    for c in b.get("clips", []):
        if not c.get("prompt"):
            issues.append(f"clip {c['id']}: no prompt")
        elif "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
    for st in b.get("stills", []):
        if "no text" not in (st.get("prompt") or "").lower():
            issues.append(f"still {st['id']}: the prompt must say no text")
    faces = {b["system"]["display"]["family"], b["system"]["text"]["family"]}
    if len(faces) > 2:
        issues.append("more than two type faces")
    return issues


def cmd_check(a):
    bad = 0
    boards = load_boards()
    sigs = set()
    for b in boards:
        sigs.add((b.get("look"), b["structure"], b["tone"]))
        iss = board_issues(b)
        bad += len(iss)
        print(f"direction {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'}, {film_seconds(b['beats']):.2f} s")
        for i in iss:
            print("  -", i)
    if len(boards) != 3 or len(sigs) != 3 or len({b.get("look") for b in boards}) != 3:
        print("  - the three boards must be the three directions (tonal, blocks, alternate)")
        bad += 1
    return 1 if bad else 0


def sheet_frames(b):
    """Six moments of the film: the opener, the grid with its findings, the reveal, the nine landed, a post, the end."""
    out = []
    for t in timeline(b["beats"]):
        sh = t["shots"]
        lo, hi = (sh[-2], sh[-1]) if t["id"] == "after" else (sh[0], sh[1])
        lo = max(lo, t["transition"])
        out.append((t["id"], t["start"] + lo + int((hi - lo) * 0.75)))
    return out[:6]


def cmd_sheets(a):
    import film
    stage_assets()
    boards = load_boards()
    jobs = []
    for b in boards:
        props = film.props_for(b)
        d = BOARDS / b["id"]
        fr = d / "frames"
        fr.mkdir(parents=True, exist_ok=True)
        for f in fr.glob("*.png"):
            f.unlink()
        jobs.append({"type": "still", "composition": "Sheet", "props": {**props, "rows": 7}, "frame": 0, "scale": 1,
                     "out": str((d / "sheet.png").resolve())})
        for n, (bid, frame) in enumerate(sheet_frames(b), 1):
            jobs.append({"type": "still", "composition": "Film", "props": props, "frame": frame, "scale": 0.5,
                         "out": str((fr / f"{n:02d}-{bid}.png").resolve())})
    rep = film.render_jobs(jobs, "build/sheets-report.json")
    _env.need("PIL")
    from PIL import Image
    for b in boards:
        d = BOARDS / b["id"]
        frames = sorted((d / "frames").glob("*.png"))
        if frames:
            ims = [Image.open(f).convert("RGB") for f in frames]
            w, h = ims[0].size
            sheet = Image.new("RGB", (w * 3 + 40, h * 2 + 30), "#111111")
            for i, im in enumerate(ims[:6]):
                sheet.paste(im, (10 + (i % 3) * (w + 10), 10 + (i // 3) * (h + 10)))
            sheet.save(d / "frames.png")
        ok = (d / "sheet.png").exists()
        print(f"direction {b['id']}: style sheet {d / 'sheet.png' if ok else '(not rendered)'}; {len(frames)} film frames -> {d / 'frames.png'}")
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
    plan = _env.read_json("build/plan.json") or {}
    caps = {s["n"]: s.get("caption") for s in plan.get("slots") or [] if s.get("caption")}
    for p in b["posts"]:
        if caps.get(p["n"]):
            p["caption"] = caps[p["n"]]
    music = _env.read_json("build/music.json") or {}
    grid_s = music.get("beats") or []
    down = music.get("downbeats") or grid_s
    beats = b["beats"]
    snapped, start = 0, 0
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
        prev["frames"] = max(sec(1.0), int(round(new_cut * FPS + t / 2 - prev_start)))
        start = prev_start + prev["frames"] - t
    pin(beats)
    if beats[-1]["frames"] < sec(1.0):
        give = sec(1.0) - beats[-1]["frames"]
        longest = max(beats[:-1], key=lambda x: x["frames"])
        longest["frames"] -= give
        beats[-1]["frames"] += give
    for bt, t in zip(beats, timeline(beats)):
        cuts = shot_cuts(bt, grid_s, 0.2, t["start"])
        if cuts:
            bt["data"]["cuts"] = cuts
    b["beats"] = beats
    b["timeline"] = timeline(beats)
    b["seconds"] = film_seconds(beats)
    b["music"] = {**b.get("music", {}), **{k: music.get(k) for k in ("file", "bpm", "origin") if music.get(k)}}
    _env.write_json("build/film.json", b)
    print(f"direction {bid}: {len(beats)} beats, {snapped} cuts moved onto the music, {film_frames(beats)} frames "
          f"({b['seconds']:.2f} s), {len(caps)} captions from the plan -> build/film.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("--board")
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
