#!/usr/bin/env python3
"""Movement 2: three storyboards, each a different film, each with a rendered style sheet.
Also the step that turns the winning storyboard into the renderer's props, cut to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft            # build/storyboards/{1,2,3}/storyboard.json + storyboard.md
    python3 S/scripts/storyboard.py check            # every board: beats, assets, text, clips, 45-75 s
    python3 S/scripts/storyboard.py sheets           # six frames per board: build/storyboards/N/frames/01..06.png + sheet.png
    python3 S/scripts/storyboard.py snap [--board N] # the winner (build/winner.json) cut to build/music.json -> build/film.json

draft reads build/taste.json first (palette, type direction, pacing, register, pillars, people, places,
moments), then build/stats.json, picks.json, palette.json and research.json. The three boards differ on
structure, tone and how generated clips are used:
  1  month by month    chronological   quiet editorial  clips build the world (an establishing opener, the closer)
  2  by the numbers    chapters        kinetic          clips are texture between chapters
  3  one thread        the trip        documentary      their stills brought to life, their own reels inside
The agent may edit any storyboard.json (text, order, photos, prompts) before sheets; check validates it.
"""
import argparse
import copy
import datetime as dt
import json
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
TARGET = {"editorial": 58, "kinetic": 50, "documentary": 60}


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
        self.picks = (_env.read_json("build/picks.json") or {}).get("chapters", {})
        self.palette = _env.read_json("build/palette.json") or {}
        self.research = _env.read_json("build/research.json") or {}
        self.index = _env.read_json("build/photo_index.json") or []
        self.lib = _env.read_json("build/library.json") or {}
        self.handle = self.stats.get("handle") or self.taste.get("handle") or "you"
        self.year = int(self.stats.get("year") or self.taste.get("year"))
        self.lower = bool(self.taste.get("register", {}).get("lowercase"))
        self.used = set()

    def say(self, s):
        if s is None:
            return None
        return s.lower() if self.lower else s

    def photo(self, src):
        """A library photo as the graded file the renderer reads (relative to build/)."""
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import picks
        p = src if str(src).startswith(str(Path("build/photos").resolve())) else picks.prepare(src)
        if not p:
            return None
        return grade.graded_name(p)

    def chapter(self, name, n=None):
        out = [self.photo(p) for p in self.picks.get(name, [])]
        out = [p for p in out if p]
        return out[:n] if n else out

    def month_photos(self, m, n=1):
        rows = [r for r in self.index if r.get("month") == m and r.get("kind") == "post"]
        rows.sort(key=lambda r: -r.get("score", 0))
        out = []
        for r in rows:
            p = self.photo(r["src"])
            if p and p not in self.used:
                out.append(p)
                self.used.add(p)
            if len(out) >= n:
                break
        return out

    def place_photos(self, place, n=3):
        hits = []
        for r in self.lib.get("posts", []):
            if place in (r.get("caption") or "").lower() and r.get("media"):
                hits.append(r["media"][0])
        out = []
        for h in hits:
            p = self.photo(h)
            if p and p not in out:
                out.append(p)
            if len(out) >= n:
                break
        return out

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
        camera = {"editorial": "slow locked-off dolly, shallow depth of field, 35mm film look",
                  "kinetic": "fast push-in and whip pan, macro detail, bold graphic framing",
                  "documentary": "handheld, natural light, observational, 16mm grain"}[direction]
        light = "warm golden-hour light" if t.get("texture", {}).get("leaks") else "soft natural light"
        film = ", visible film grain" if t.get("texture", {}).get("grain") else ""
        return (f"{subject}. Palette: {', '.join(dict.fromkeys(c for c in colors if c))}. {camera}, {light}{film}. "
                f"Vertical 9:16, {seconds} seconds, one continuous shot. No text, no logos, no people's faces.")


def stat_rows(ctx, keys, labels=None):
    nums = {n["key"]: n for n in ctx.stats.get("numbers", [])}
    out = []
    for k in keys:
        n = nums.get(k)
        if n and n.get("value"):
            out.append({"value": n["value"], "label": ctx.say((labels or {}).get(k) or n["label"])})
    return out


def top_items(ctx):
    items = []
    for i, t in enumerate(ctx.stats.get("top_posts", [])[:3]):
        num = t.get("likes") if t.get("likes") is not None else t.get("comments")
        unit = "likes" if t.get("likes") is not None else "comments"
        cap = (t.get("caption") or "").split("#")[0].strip()
        items.append({"rank": f"{i + 1:02d}", "kicker": ctx.say(t.get("date_label")),
                      "headline": ctx.say(cap or t.get("date_label")), "line": ctx.say(f"{num} {unit}") if num is not None else None})
    return items


def people_rows(ctx, n=5):
    return [{"text": f"@{p['account']}", "meta": ctx.say(f"{p['total']} {'comments' if p.get('comments') else 'mentions'}")}
            for p in ctx.stats.get("people", [])[:n]]


def loved_rows(ctx, n=5):
    return [{"text": f"@{p['account']}", "meta": ctx.say(f"{p['likes']} likes")} for p in ctx.stats.get("loved", [])[:n]]


def palette_beat(ctx, frames, transition):
    sw = []
    for s in ctx.taste.get("palette", {}).get("year", [])[:5]:
        ph = ctx.photo(s["photo"]) if s.get("photo") else None
        sw.append({"hex": s["hex"], "name": ctx.say(s.get("name") or ""), "photo": ph})
    likes = [s.get("name") for s in ctx.taste.get("palette", {}).get("likes", [])[:3] if s.get("name")]
    line = f"and the colors you liked: {', '.join(likes)}" if likes else None
    return {"id": "palette", "kind": "Mosaic", "frames": frames, "transition": transition,
            "text": {"kicker": ctx.say("your palette"), "headline": ctx.say(f"the colors of {ctx.year}"), "line": ctx.say(line)},
            "photos": [s["photo"] for s in sw if s["photo"]], "data": {"mode": "palette", "swatches": sw}}


def tr(preset, direction, d=None):
    f = design("transitions.json")["frames"][direction]
    return {"preset": preset, "frames": f, **({"direction": d} if d else {})}


def sec(s):
    return int(round(s * FPS))


def board_monthly(ctx):
    d = "editorial"
    b = ctx.stats.get("busiest") or {}
    q = ctx.stats.get("quietest") or {}
    opener = ctx.chapter("opener", 1) or ctx.month_photos(1)
    beats = [{"id": "opener", "kind": "Opener", "frames": sec(5), "transition": None,
              "text": {"kicker": f"@{ctx.handle}", "headline": str(ctx.year), "line": ctx.say("the year, month by month")},
              "photos": opener, "clip": "01"}]
    last = max([int(m) for m in [r.get("month") for r in ctx.stats.get("months", []) if r.get("posts")]] or [12])
    spans = [(1, 4), (5, 6), (8, last)]
    months = {r["month"]: r for r in ctx.stats.get("months", [])}
    for k, (a, z) in enumerate(spans):
        ms = [m for m in range(a, z + 1) if months.get(m, {}).get("posts")]
        if not ms:
            continue
        pick = ms if len(ms) <= 3 else [ms[0], ms[len(ms) // 2], ms[-1]]
        photos, items = [], []
        for m in pick:
            ph = ctx.month_photos(m)
            if not ph:
                continue
            photos += ph
            row = months[m]
            note = f"{row['posts']} posts" + (". the quiet one" if q.get("month") == m else "")
            items.append({"kicker": MONTHS[m - 1], "headline": ctx.say(caption_for(ctx, m)), "line": ctx.say(note)})
        beats.append({"id": f"months-{k + 1}", "kind": "PhotoLive", "frames": sec(4.8 if len(photos) > 2 else 3.6),
                      "transition": tr("wipe", d, "from-right") if k else tr("dip", d), "photos": photos,
                      "text": items[0] if items else {}, "data": {"items": items}})
        if k == 0:
            beats.append({"id": "numbers", "kind": "StatCard", "frames": sec(6), "transition": tr("match", d),
                          "text": {"kicker": ctx.say("the year in numbers")},
                          "photos": ctx.chapter("numbers", 3), "data": {"stats": stat_rows(ctx, ["posts", "likes_given", "comments_written"])}})
        if k == 1 and b:
            beats.append({"id": "busiest", "kind": "Mosaic", "frames": sec(5), "transition": tr("dip", d),
                          "photos": ctx.chapter("busiest", 12),
                          "data": {"groups": [{"label": ctx.say("your busiest month"), "headline": ctx.say(f"{b['name']}, {b['posts']} posts"),
                                               "line": ctx.say(f"{b.get('total', b['posts'])} things shared in one month"), "photos": ctx.chapter("busiest", 12)}]}})
    beats += [
        {"id": "top", "kind": "PhotoLive", "frames": sec(6), "transition": tr("dip", d), "photos": ctx.chapter("top", 3),
         "text": {"kicker": ctx.say("your top three"), "headline": ctx.say("the ones everyone loved")}, "data": {"items": top_items(ctx)}},
        {"id": "people", "kind": "KineticType", "frames": sec(4.6), "transition": tr("fade", d), "photos": ctx.chapter("people", 1),
         "text": {"kicker": ctx.say("your people"), "line": ctx.say("the ones in your comments all year")}, "data": {"rows": people_rows(ctx)}},
        {"id": "loved", "kind": "KineticType", "frames": sec(4.4), "transition": tr("wipe", d, "from-bottom"), "photos": ctx.chapter("loved", 1),
         "text": {"kicker": ctx.say("what you loved"), "line": ctx.say(loved_line(ctx))}, "data": {"rows": loved_rows(ctx, 4)}},
        palette_beat(ctx, sec(4.4), tr("match", d)),
        {"id": "closer", "kind": "Closer", "frames": sec(5.4), "transition": tr("dip", d), "photos": ctx.chapter("top", 3) + ctx.chapter("closer", 1),
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"see you in {ctx.year + 1}"), "line": ctx.say(f"that was {ctx.year}.")},
         "clip": "02", "data": {"signoff": ctx.say(f"my {ctx.year} on instagram")}},
    ]
    clips = [
        {"id": "01", "beat": "opener", "role": "the opener's world",
         "prompt": ctx.prompt(world_subject(ctx), d, 5), "seconds": 5, "image": None},
        {"id": "02", "beat": "closer", "role": "the closer, behind the prints",
         "prompt": ctx.prompt(f"late light on a table at the end of a long day, {', '.join(ctx.taste.get('pillars', [])[:2])}", d, 5),
         "seconds": 5, "image": None},
    ]
    return finish(ctx, {"id": "1", "name": ctx.say("month by month"), "direction": d, "structure": "chronological months",
                        "tone": "quiet editorial", "clip_use": "world-building: an establishing opener and the closer",
                        "idea": ctx.say(f"{ctx.year} told in order, one month after the next, on paper-white pages in a soft serif. "
                                        "the photos carry it; the type stays quiet and the cuts breathe."),
                        "music": {"direction": "warm, unhurried lo-fi around 84 bpm: soft keys, brushed drums", "bpm": 84, "mood": "calm"},
                        "beats": beats, "clips": clips})


def board_numbers(ctx):
    d = "kinetic"
    b = ctx.stats.get("busiest") or {}
    q = ctx.stats.get("quietest") or {}
    stats = stat_rows(ctx, ["posts", "reels", "stories", "likes_given", "comments_written", "new_followers"],
                      {"likes_given": "likes given", "comments_written": "comments written", "new_followers": "new followers"})
    def chapter(n, title, clip):
        return {"id": f"chapter-{n}", "kind": "ClipShot", "frames": sec(1.8), "transition": tr("bars", d),
                "text": {"kicker": ctx.say(f"chapter {n}"), "headline": ctx.say(title)}, "clip": clip, "data": {"chapter": f"{n:02d}"},
                "photos": ctx.chapter("numbers", 1)}
    groups = []
    if b:
        groups.append({"label": ctx.say("busiest"), "headline": ctx.say(f"{b['name']}: {b['posts']} posts"), "photos": ctx.chapter("busiest", 12)})
    if q:
        groups.append({"label": ctx.say("quietest"), "headline": ctx.say(f"{q['name']}: {q['posts']} posts"), "photos": ctx.chapter("quietest", 3)})
    beats = [
        {"id": "opener", "kind": "Opener", "frames": sec(3.2), "transition": None, "photos": ctx.chapter("opener", 1),
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say("the year in numbers")}},
        chapter(1, "the numbers", "01"),
        {"id": "numbers", "kind": "StatCard", "frames": sec(1.45 * max(1, len(stats))), "transition": tr("whip", d, "from-right"),
         "photos": ctx.chapter("numbers", 6), "data": {"stats": stats}},
        chapter(2, "the top three", "02"),
        {"id": "top", "kind": "PhotoLive", "frames": sec(5.4), "transition": tr("whip", d, "from-right"), "photos": ctx.chapter("top", 3),
         "text": {"kicker": ctx.say("top three")}, "data": {"items": top_items(ctx)}},
        chapter(3, "the months", "03"),
        {"id": "months", "kind": "Mosaic", "frames": sec(5.2), "transition": tr("whip", d, "from-right"), "photos": ctx.chapter("busiest", 12),
         "data": {"groups": groups}},
        {"id": "people", "kind": "KineticType", "frames": sec(3.6), "transition": tr("slide", d, "from-bottom"), "photos": ctx.chapter("people", 1),
         "text": {"kicker": ctx.say("your people")}, "data": {"rows": people_rows(ctx)}},
        {"id": "loved", "kind": "KineticType", "frames": sec(3.6), "transition": tr("whip", d, "from-left"), "photos": ctx.chapter("loved", 1),
         "text": {"kicker": ctx.say("you loved")}, "data": {"rows": loved_rows(ctx)}},
        palette_beat(ctx, sec(3.4), tr("bars", d)),
        {"id": "closer", "kind": "Closer", "frames": sec(4.6), "transition": tr("whip", d, "from-right"),
         "photos": ctx.chapter("top", 3) + ctx.chapter("closer", 1),
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"{ctx.year + 1}, your move")}, "clip": None,
         "data": {"signoff": ctx.say(f"my {ctx.year} in numbers")}},
    ]
    texture = lambda n: ctx.prompt(f"abstract slow-motion {['paint pour', 'light through warm glass', 'grain of a film strip'][n]} in their colors", d, 2)
    clips = [{"id": f"{n + 1:02d}", "beat": f"chapter-{n + 1}", "role": "texture between chapters", "prompt": texture(n), "seconds": 2, "image": None}
             for n in range(3)]
    return finish(ctx, {"id": "2", "name": ctx.say("by the numbers"), "direction": d, "structure": "by-the-numbers chapters",
                        "tone": "kinetic", "clip_use": "texture between chapters",
                        "idea": ctx.say(f"{ctx.year} as a scoreboard: every number lands like a hit, in heavy type over their colors. "
                                        "short beats, whip pans, three chapters."),
                        "music": {"direction": "driving, bright, 118 bpm: four-on-the-floor, claps, a hook", "bpm": 118, "mood": "drive"},
                        "beats": beats, "clips": clips})


def board_thread(ctx):
    d = "documentary"
    trip = next((m for m in ctx.taste.get("moments", []) if m.get("kind") == "the trip"), None)
    b = ctx.stats.get("busiest") or {}
    place = (trip or {}).get("place") or (ctx.taste.get("places") or [None])[0]
    tmonth = (trip or {}).get("month") or b.get("name")
    thread = f"{place}, {tmonth}".lower() if place else f"{tmonth}"
    trip_photos = (ctx.place_photos(place, 6) if place else []) or ctx.chapter("busiest", 6)
    lead = trip_photos[0] if trip_photos else (ctx.chapter("opener", 1) or [None])[0]
    before = [ctx.month_photos(m)[0] for m in (1, 3, 5) if ctx.month_photos(m)]
    eras = ctx.research.get("eras", [])
    before_items = [{"kicker": ctx.say(f"{e['from']}" + (f" to {e['to']}" if e['to'] != e['from'] else "")), "headline": ctx.say(e["place"])}
                    for e in eras[:3]] or [{"kicker": "", "headline": ""}]
    reels = sorted({m for r in ctx.lib.get("reels", []) for m in (r.get("media") or []) if str(m).lower().endswith((".mp4", ".mov"))})
    stats = stat_rows(ctx, ["posts", "reels", "likes_given"], {"likes_given": "likes given"})
    beats = [
        {"id": "opener", "kind": "Opener", "frames": sec(5.4), "transition": None, "photos": [lead] if lead else [],
         "text": {"kicker": ctx.say(thread), "headline": str(ctx.year), "line": ctx.say(f"the year, and the {tmonth} it was about")},
         "clip": "01"},
        {"id": "before", "kind": "PhotoLive", "frames": sec(5.4), "transition": tr("dip", d), "photos": before[:3],
         "text": before_items[0], "data": {"items": before_items[:len(before)]}},
        {"id": "their-reel", "kind": "ClipShot", "frames": sec(3.6), "transition": tr("fade", d), "clip": "02",
         "photos": before[:1], "text": {"kicker": ctx.say("from your reels"), "headline": ctx.say(reel_caption(ctx))}},
        {"id": "the-trip", "kind": "Mosaic", "frames": sec(5.6), "transition": tr("iris", d), "photos": trip_photos,
         "data": {"groups": [{"label": ctx.say(thread), "headline": ctx.say(f"{b.get('name', tmonth)}: {b.get('posts', '')} posts"),
                              "line": ctx.say(f"the busiest month of your year"), "photos": (ctx.chapter("busiest", 12) or trip_photos)}]}},
        {"id": "alive", "kind": "ClipShot", "frames": sec(4), "transition": tr("dip", d), "clip": "03", "photos": trip_photos[1:2] or [lead],
         "text": {"kicker": ctx.say(place or ""), "headline": ctx.say(caption_with(ctx, place) or thread)}},
        {"id": "numbers", "kind": "StatCard", "frames": sec(5.4), "transition": tr("fade", d), "photos": ctx.chapter("numbers", 3),
         "text": {"kicker": ctx.say("the year, counted")}, "data": {"stats": stats}},
        {"id": "top", "kind": "PhotoLive", "frames": sec(5.6), "transition": tr("match", d), "photos": ctx.chapter("top", 3),
         "text": {"kicker": ctx.say("the three that landed")}, "data": {"items": top_items(ctx)}},
        {"id": "people", "kind": "KineticType", "frames": sec(4.4), "transition": tr("iris", d), "photos": ctx.chapter("people", 1),
         "text": {"kicker": ctx.say("who was there"), "line": ctx.say("in your comments, all year")}, "data": {"rows": people_rows(ctx, 4)}},
        {"id": "loved", "kind": "KineticType", "frames": sec(4.2), "transition": tr("fade", d), "photos": ctx.chapter("loved", 1),
         "text": {"kicker": ctx.say("what you kept coming back to"), "line": ctx.say(loved_line(ctx))}, "data": {"rows": loved_rows(ctx, 4)}},
        palette_beat(ctx, sec(4.2), tr("dip", d)),
        {"id": "closer", "kind": "Closer", "frames": sec(5.6), "transition": tr("dip", d), "photos": ctx.chapter("top", 3) + ctx.chapter("closer", 1),
         "text": {"kicker": f"@{ctx.handle}", "headline": ctx.say(f"see you in {ctx.year + 1}"), "line": ctx.say(f"back to {place} someday" if place else None)},
         "clip": "04", "data": {"signoff": ctx.say(f"my {ctx.year} on instagram")}},
    ]
    clips = [
        {"id": "01", "beat": "opener", "role": "their still brought to life", "prompt": ctx.prompt(f"this photograph of {place or 'their year'} comes alive: gentle wind, drifting light, slow camera move", d, 5),
         "seconds": 5, "image": lead},
        {"id": "02", "beat": "their-reel", "role": "their own reel", "prompt": None, "seconds": 3.6, "image": before[0] if before else lead,
         "source": reels[0] if reels else None},
        {"id": "03", "beat": "alive", "role": "their still brought to life", "prompt": ctx.prompt(f"this photograph from {place or 'the trip'} comes alive: light moves across it, a slow push", d, 4),
         "seconds": 4, "image": (trip_photos[1:2] or [lead])[0]},
        {"id": "04", "beat": "closer", "role": "the closer's world", "prompt": ctx.prompt(f"dusk over {place or 'a quiet street'}, the last light of the day", d, 5),
         "seconds": 5, "image": None},
    ]
    return finish(ctx, {"id": "3", "name": ctx.say(f"one thread: {thread}"), "direction": d, "structure": f"one narrative thread: {thread}",
                        "tone": "documentary", "clip_use": "their stills brought to life, and their own reel",
                        "idea": ctx.say(f"the year as a documentary about {thread}: everything before leads there, everything after remembers it. "
                                        "full-bleed photos, mono timestamps, grain and light leaks."),
                        "music": {"direction": "cinematic, warm, 92 bpm: a slow pulse, a piano figure, room", "bpm": 92, "mood": "film"},
                        "beats": beats, "clips": clips})


def caption_for(ctx, m):
    caps = [(r.get("caption") or "").split("#")[0].strip() for r in ctx.lib.get("posts", [])
            if r.get("ts") and dt.datetime.fromtimestamp(r["ts"], dt.timezone.utc).month == m]
    caps = [c for c in caps if 8 <= len(c) <= 48]
    plain = [c for c in caps if "@" not in c]
    return max(plain or caps, key=len) if caps else MONTHS[m - 1]


def caption_with(ctx, word):
    if not word:
        return None
    caps = [(r.get("caption") or "").split("#")[0].strip() for r in ctx.lib.get("posts", []) if word in (r.get("caption") or "").lower()]
    caps = [c for c in caps if 8 <= len(c) <= 48]
    return caps[0] if caps else None


def reel_caption(ctx):
    caps = [(r.get("caption") or "").split("#")[0].strip() for r in ctx.lib.get("reels", []) if r.get("caption")]
    caps = [c for c in caps if 6 <= len(c) <= 44]
    return caps[0] if caps else "in motion"


def loved_line(ctx):
    themes = list((ctx.research.get("likes", {}).get("themes") or {}).keys())[:3]
    return f"mostly {', '.join(themes[:-1])} and {themes[-1]}" if len(themes) >= 2 else None


def world_subject(ctx):
    pl = ctx.taste.get("places") or []
    pil = ctx.taste.get("pillars") or []
    return f"an establishing shot of {pl[0] if pl else 'a sunlit old town'} at golden hour, {', '.join(pil[:2])}"


def finish(ctx, board):
    """Fills the system, drops empty beats, scales durations to the direction's target, adds cards."""
    d = board["direction"]
    board.update({"handle": ctx.handle, "year": ctx.year, "format": {"width": 1080, "height": 1920, "fps": FPS},
                  "system": ctx.system(d)})
    beats = []
    for bt in board["beats"]:
        bt["photos"] = [p for p in (bt.get("photos") or []) if p]
        kind = bt["kind"]
        empty = (kind == "StatCard" and not bt.get("data", {}).get("stats")) or \
                (kind in ("PhotoLive", "Mosaic") and not bt["photos"] and bt.get("data", {}).get("mode") != "palette") or \
                (kind == "KineticType" and not bt.get("data", {}).get("rows"))
        if not empty:
            beats.append(bt)
    if beats:
        beats[0]["transition"] = None
    total = film_seconds(beats)
    k = TARGET[d] / total if total else 1
    for bt in beats:
        bt["frames"] = max(sec(1.3), int(round(bt["frames"] * k)))
    board["beats"] = beats
    by = {b["id"]: b for b in beats}
    keep = [c for c in board["clips"] if c["beat"] in by]
    board["clips"] = keep
    stats_all = stat_rows(ctx, ["posts", "reels", "stories", "likes_given", "comments_written", "new_followers"],
                          {"likes_given": "likes given", "comments_written": "comments written", "new_followers": "new followers"})
    def card(bid, **over):
        b = copy.deepcopy(by.get(bid)) if bid in by else None
        if b is None:
            return None
        b.update(over)
        b["transition"] = None
        b.pop("clip", None)
        return b
    q = ctx.stats.get("quietest") or {}
    bz = ctx.stats.get("busiest") or {}
    cover = card("opener", text={"kicker": f"@{ctx.handle}", "headline": str(ctx.year), "line": ctx.say("my year on instagram")})
    if cover and not cover["photos"]:
        cover["photos"] = ctx.chapter("cover", 1) or ctx.chapter("opener", 1)
    cards = [
        cover,
        {"id": "card-numbers", "kind": "StatCard", "frames": sec(3), "photos": ctx.chapter("numbers", 1),
         "text": {"kicker": ctx.say("by the numbers")}, "data": {"stats": stats_all}},
        card("top"),
        {"id": "card-busiest", "kind": "Mosaic", "frames": sec(3), "photos": ctx.chapter("busiest", 9),
         "data": {"groups": [{"label": ctx.say("busiest month"), "headline": ctx.say(f"{bz.get('name')}, {bz.get('posts')} posts"), "photos": ctx.chapter("busiest", 9)}]}} if bz else None,
        {"id": "card-quietest", "kind": "Mosaic", "frames": sec(3), "photos": ctx.chapter("quietest", 3),
         "data": {"groups": [{"label": ctx.say("quietest month"), "headline": ctx.say(f"{q.get('name')}, {q.get('posts')} posts"), "photos": ctx.chapter("quietest", 3)}]}} if q else None,
        card("people"), card("loved"), card("palette"),
        card("closer"),
        card("closer", id="card-share", text={"kicker": ctx.say("your turn"), "headline": ctx.say("share yours"),
                                                "line": ctx.say(f"what did your {ctx.year} look like?")}),
    ]
    cards = [c for c in cards if c]
    for c in cards:
        c["settle"] = 0
    board["cards"] = cards[:10]
    board["stories"] = [copy.deepcopy(c) for c in cards if c["id"] in ("opener", "top", "closer")][:3]
    return board


def film_seconds(beats):
    frames = sum(b["frames"] for b in beats) - sum((b.get("transition") or {}).get("frames", 0) for b in beats[1:])
    return frames / FPS


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t})
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
             "", "## beats", "", "| # | time | beat | component | carried by | text | transition in |", "|---|---|---|---|---|---|---|"]
    for i, (b, t) in enumerate(zip(board["beats"], timeline(board["beats"]))):
        txt = " / ".join(v for v in (b.get("text") or {}).values() if v)
        assets = ", ".join(Path(p).name for p in (b.get("photos") or [])[:4]) + (" ..." if len(b.get("photos") or []) > 4 else "")
        if b.get("clip"):
            assets = f"clip {b['clip']}; " + assets
        tri = (b.get("transition") or {}).get("preset", "-")
        lines.append(f"| {i + 1} | {t['start'] / FPS:.1f}-{(t['start'] + t['frames']) / FPS:.1f} s | {b['id']} | {b['kind']} | {assets} | {txt} | {tri} |")
    lines += ["", "## clips the video model makes", ""]
    for c in board["clips"]:
        src = f" (their reel: {Path(c['source']).name})" if c.get("source") else ""
        img = f" (from their photo {Path(c['image']).name})" if c.get("image") and c.get("prompt") else ""
        lines.append(f"- {c['id']} for `{c['beat']}`, {c['role']}, {c['seconds']} s{src}{img}: {c.get('prompt') or 'no generation; their own footage'}")
    lines += ["", f"Cards: {len(board['cards'])} carousel cards ({', '.join(c['id'] for c in board['cards'])}); "
              f"stories: {', '.join(c['id'] for c in board['stories'])}.", ""]
    path.write_text("\n".join(lines))


def cmd_draft(a):
    ctx = Ctx()
    g = grade.recipe(ctx.taste)
    _env.write_json("build/grade.json", g)
    grade.grade_photos()
    boards = [board_monthly(ctx), board_numbers(ctx), board_thread(ctx)]
    referenced = sorted({p for b in boards for x in b["beats"] + b["cards"] for p in (x.get("photos") or [])} |
                        {p for b in boards for x in b["beats"] + b["cards"] for s in (x.get("data") or {}).get("swatches", []) if (p := s.get("photo"))} |
                        {p for b in boards for x in b["beats"] + b["cards"] for gr in (x.get("data") or {}).get("groups", []) for p in gr.get("photos", [])} |
                        {c["image"] for b in boards for c in b["clips"] if c.get("image")})
    grade.grade_photos([Path("build/photos") / Path(p).name for p in referenced])
    for b in boards:
        d = BOARDS / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        print(f"board {b['id']} {b['name']}: {len(b['beats'])} beats, {film_seconds(b['beats']):.1f} s, {len(b['clips'])} clips, "
              f"{len(b['cards'])} cards -> {d}/storyboard.md")
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


KINDS = {"Opener", "StatCard", "PhotoLive", "Mosaic", "KineticType", "ClipShot", "Closer"}
PRESETS = set(design("transitions.json")["presets"])


def board_issues(b):
    issues = []
    secs = film_seconds(b["beats"])
    if not 45 <= secs <= 75:
        issues.append(f"length {secs:.1f} s is outside 45-75 s")
    clips = {c["id"] for c in b.get("clips", [])}
    for i, bt in enumerate(b["beats"]):
        if bt["kind"] not in KINDS:
            issues.append(f"{bt['id']}: unknown component {bt['kind']}")
        if bt["frames"] < sec(1.2):
            issues.append(f"{bt['id']}: {bt['frames']} frames is under 1.2 s")
        t = bt.get("transition")
        if i and not t:
            issues.append(f"{bt['id']}: no transition named (every cut is chosen)")
        if t and t["preset"] not in PRESETS:
            issues.append(f"{bt['id']}: unknown transition {t['preset']}")
        if bt.get("clip") and bt["clip"] not in clips:
            issues.append(f"{bt['id']}: clip {bt['clip']} is not in the clip list")
        for p in bt.get("photos") or []:
            if not (grade.PUBLIC / p).exists():
                issues.append(f"{bt['id']}: missing asset build/public/{p}")
        for v in (bt.get("text") or {}).values():
            if v and any(x in str(v) for x in ("{", "}", "TODO", "lorem", "None", "XX")):
                issues.append(f"{bt['id']}: placeholder in text: {v}")
    for c in b.get("clips", []):
        if not c.get("prompt") and not c.get("source"):
            issues.append(f"clip {c['id']}: no prompt and no source")
        if c.get("prompt") and "no text" not in c["prompt"].lower():
            issues.append(f"clip {c['id']}: the prompt must say no text, no logos, no faces")
    faces = {b["system"]["display"]["family"], b["system"]["text"]["family"]}
    if len(faces) > 2:
        issues.append("more than two type faces")
    if len(b.get("cards", [])) != 10:
        issues.append(f"{len(b.get('cards', []))} carousel cards (needs 10)")
    if len(b.get("stories", [])) != 3:
        issues.append(f"{len(b.get('stories', []))} story cards (needs 3)")
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
    """Six frames that show the direction: the settled moment of six different beats."""
    tl = timeline(b["beats"])
    want = ["opener", "StatCard", "PhotoLive", "Mosaic", "KineticType", "closer"]
    chosen = []
    for w in want:
        for t in tl:
            if (t["id"] == w or t["kind"] == w) and t["id"] not in [c["id"] for c in chosen]:
                chosen.append(t)
                break
    for t in tl:
        if len(chosen) >= 6:
            break
        if t["id"] not in [c["id"] for c in chosen]:
            chosen.append(t)
    chosen.sort(key=lambda t: t["start"])
    return [(t["id"], t["start"] + int(t["frames"] * (0.62 if t["kind"] != "StatCard" else 0.3))) for t in chosen[:6]]


def cmd_sheets(a):
    import film
    stage_assets()
    boards = load_boards()
    jobs, plan = [], []
    for b in boards:
        props = film.props_for(b)
        for n, (bid, frame) in enumerate(sheet_frames(b), 1):
            out = (BOARDS / b["id"] / "frames" / f"{n:02d}.png").resolve()
            jobs.append({"type": "still", "composition": "Film", "props": props, "frame": frame, "scale": 0.5, "out": str(out)})
            plan.append((b["id"], n, bid, frame))
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
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    grid = music.get("beats") or []
    down = music.get("downbeats") or grid
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
            new_cut = snap_to(cut, grid, 0.3)
        if new_cut != cut:
            snapped += 1
        prev["frames"] = max(sec(1.2), int(round(new_cut * FPS + t / 2 - prev_start)))
        start = prev_start + prev["frames"] - t
    last = beats[-1]
    end = (start + last["frames"]) / FPS
    if down:
        later = [g for g in down if g >= end - 0.4]
        if later:
            last["frames"] = max(sec(2.5), int(round(later[0] * FPS - start)) + sec(0.5))
    tl = timeline(beats)
    for bt, t in zip(beats, tl):
        n = len((bt.get("data") or {}).get("stats") or (bt.get("data") or {}).get("items") or (bt.get("data") or {}).get("groups") or [])
        if n > 1 and bt["kind"] in ("StatCard", "PhotoLive", "Mosaic"):
            cuts = []
            for k in range(1, n):
                ideal = (t["start"] + bt["frames"] * k / n) / FPS
                c = snap_to(ideal, grid, 0.25)
                cuts.append(int(round(c * FPS - t["start"])))
            cuts = sorted(set(max(sec(0.8), min(bt["frames"] - sec(0.8), c)) for c in cuts))
            if len(cuts) == n - 1:
                bt.setdefault("data", {})["cuts"] = cuts
        if bt.get("clip"):
            c = clips.get(bt["clip"]) or {}
            bt["clip"] = {"id": bt["clip"], "file": c.get("file"), "image": c.get("image") or (bt.get("photos") or [None])[0],
                          "status": c.get("status", "substituted")}
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
