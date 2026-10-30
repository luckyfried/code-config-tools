#!/usr/bin/env python3
"""Movement 2: the nine drawn in three looks, each laid out for the reel, the square and the wide. Also the step that
cuts the chosen look to the music.

USAGE (from the workspace root; S = the folder this skill's SKILL.md was read from):
    python3 S/scripts/storyboard.py draft  --run R   # storyboards/<style>/board-{reel,square,wide}.json + storyboard.md for
                                                     # each of the three looks; a new draft starts a new choice (winner.json
                                                     # and vote/scores.json go)
    python3 S/scripts/storyboard.py check  --run R   # the bounds, the asked length, the hook, the style card and the
                                                     # template tells, every board
    python3 S/scripts/storyboard.py sheets --run R   # storyboards/<style>/sheet.png per look and out/boards.png: each look's
                                                     # hook, a middle beat and its closer, its name and one sentence under it
    python3 S/scripts/storyboard.py snap   --run R   # the chosen look (winner.json) at the music's tempo -> film.json

The three looks are three style cards (styles/<id>.json; styles/catalog.md says each in a sentence): the kit's trio,
swiss-grid, scrapbook and cinematic-letterbox, or, when taste.json names a `style`, that style and the two of the trio
that share the fewest of its axes. The story is the same in all three (scripts/story.py): the nine they love most as a
countdown with no number on screen, nine layouts for the nine, the grid, the closer. Each look takes its faces, its
colors (the card's palette rule over the photographs' swatches), its easing, its finish, its moves, its transitions and
its closer from its card, and from nowhere else.

The words are the person's: taste.json `words` (title, promise, ask) replaces any default below, in their case and
voice. The length is theirs too: taste.json `seconds`, from LENGTH[0] to LENGTH[1] s, and SECONDS when they named
none; a length outside that makes nothing (`not made: ...`, exit 1). Nine is the count: a run with fewer than nine of the
nine with a photograph makes nothing (`not delivered: <n> posts, nine needed`). taste.json `beats` changes one beat's
layout, move or length (story.py says how); a draft takes it.

check fails a board on any bounds finding (scripts/bounds.py), a length more than 1 s off the asked one, a hook event
after frame 30, and any style or template tell: a face, move, transition or color the card did not give; every shot
within 10 % of one length; the words in one place on most beats; one move on two beats in a row; a layout used twice in
the nine; two looks sharing more than two of the six axes. storyboard.md states each board's beats, cuts and sound.
"""
import argparse
import calendar
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import bounds  # noqa: E402
import compose  # noqa: E402
import palette  # noqa: E402
import story  # noqa: E402

BOARDS = Path("storyboards")
FPS = compose.FPS
HOOK_FRAMES = 30
LENGTH = (20, 45)
SECONDS = 30
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}
# the order the sheet shows a board's rests in
SHEET = ("hook", "ordinary", "card")


def words_default(year):
    return {"title": "my best nine.", "promise": f"see you in {year + 1}", "ask": "share yours"}


def asked(taste):
    """The reel's length, seconds: taste.json `seconds`, the length the person asked for, or SECONDS when they named
    none; a length outside LENGTH makes nothing, and says so."""
    seconds = taste.get("seconds")
    if seconds is None:
        return SECONDS
    lo, hi = LENGTH
    if not lo <= seconds <= hi:
        sys.exit(f"not made: the reel runs {lo} to {hi} s, and {seconds:g} s was asked; nothing shorter or longer is made in its place")
    return seconds


def sentence(style):
    """The style's one sentence for the person, from styles/catalog.md."""
    for row in (compose.STYLES / "catalog.md").read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == style:
            return cells[1]
    return compose.card(style)["name"]


def board_for(style, posts, fmt, words, handle, year, bpm=None, seconds=None, swatches=None, levers=None):
    """The board for `posts` (each with its `pick`, 1 the top of the countdown) in style `style` and format `fmt`, a
    film of `seconds`, and its plan: {board, cuts, hook_frame, rests, rest_beats, seconds, frames}. Rests map each rest
    to the frame it comes to rest at."""
    c = compose.card(style)
    bpm = bpm or story.BPM
    fr = compose.Frame(fmt, c["finish"].get("bars", 0.0))
    r = story.build(c, posts, fr, words, handle, year, bpm, seconds or SECONDS, swatches, levers)
    pulse = compose.pulse_of(bpm)
    beats, starts = [], {}
    for b in r["beats"]:
        f0, f1 = round(b["at"] * pulse), round((b["at"] + b["beats"]) * pulse)
        starts[b["id"]] = f0
        beats.append(dict(b, start=b["at"], frames=f1 - f0, bars=round(b["beats"] / 4, 3)))
        beats[-1].pop("tags", None)
    frames = sum(b["frames"] for b in beats)
    closer = next(b for b in beats if b["form"] == "closer")
    board = {"id": f"nine-{style}-{fmt}", "name": words["title"], "style": style, "handle": handle, "year": year, "bpm": bpm,
             "format": {"width": fr.W, "height": fr.H, "fps": FPS, "name": fmt}, "fps": FPS, "system": r["system"],
             "title": words["title"], "signoff": words["promise"], "ask": words["ask"],
             "closer": {"at": closer["at"], "still": r["settle"]}, "end": r["end"], "beats": beats,
             "sound": [dict(q, frame=round(q["at"] * pulse)) for q in r["sound"]], "clips": r["clips"]}
    rests = {k: starts[bid] + min(round(at * pulse), next(b["frames"] for b in beats if b["id"] == bid) - 1)
             for k, (bid, at) in r["rest_at"].items()}
    return {"board": board, "cuts": [round(b["start"] / bpm * 60, 2) for b in beats if b["start"] > 0],
            "hook_frame": round(r["hook"] * pulse), "rests": rests, "rest_beats": {k: v[0] for k, v in r["rest_at"].items()},
            "seconds": round(frames / FPS, 2), "frames": frames}


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


def posts_of(stats, picks, taste):
    """The nine with a photograph as the posts the story lays out, ranked by the numbers, each with its `pick`: its place
    in taste.json `order` (the post's ts, the strongest first), else its rank. Each says its moment's line from taste.json
    `moments` (joined by the post's `ts`) as written, and the lead of its caption, in their case, when no moment names it;
    a moment's `people` and `place` come along for the move each beat takes."""
    info = {n["rank"]: n for n in picks["nine"]}
    lower = bool((taste.get("register") or {}).get("lowercase", True))
    moment = {mo["ts"]: mo for mo in taste.get("moments") or [] if "ts" in mo}
    order = [str(t) for t in taste.get("order") or []]
    out = []
    for t in stats["top_nine"]:
        n = info.get(t["rank"])
        if not n:
            continue
        d = dt.date.fromisoformat(t["date"])
        mo = moment.get(t["ts"], {})
        if "line" in mo:
            said = " ".join(str(mo["line"]).split())
        else:
            said = short(t.get("caption") or "")
            said = said.lower() if lower else said
        out.append({"rank": len(out) + 1, "caption": said, "date": f"{d.day} {calendar.month_abbr[d.month].lower()}", "ts": t["ts"],
                    "file": n["file"], "aspect": n["aspect"], "focus": n["focus"], "crop": n["crop"], "line": n.get("line"),
                    "look": n.get("look"), "people": list(mo.get("people") or []), "place": mo.get("place") or ""})
    named = [p for p in out if str(p["ts"]) in order]
    rest = [p for p in out if str(p["ts"]) not in order]
    for i, p in enumerate(sorted(named, key=lambda p: order.index(str(p["ts"]))) + rest):
        p["pick"] = i + 1
    return out


class Run:
    """The run's nine as the posts the story lays out, with the handle, the year, the words, the swatches, the levers and
    the asked length."""

    def __init__(self):
        self.stats = _env.read_json("stats.json")
        self.picks = _env.read_json("picks.json")
        if not self.stats or not self.picks:
            sys.exit("stats.json or picks.json is missing: run research.py first")
        self.taste = _env.read_json("taste.json") or {}
        self.year = int(self.stats["year"])
        h = (self.stats.get("handle") or "").lstrip("@")
        self.handle = "@" + h if h else ""
        self.posts = posts_of(self.stats, self.picks, self.taste)
        if len(self.posts) < 9:
            sys.exit(f"not delivered: {len(self.posts)} posts, nine needed")
        self.seconds = asked(self.taste)
        self.swatches = palette.swatches_of(self.taste, _env.read_json("palette.json"))
        self.levers = {k: v for k, v in (self.taste.get("beats") or {}).items() if isinstance(v, dict)}
        self.styles = compose.three(self.taste.get("style"))

    def words(self):
        w = dict(words_default(self.year))
        w.update({k: v for k, v in (self.taste.get("words") or {}).items() if k in w and isinstance(v, str) and v.strip()})
        return w

    def plan(self, style, fmt, bpm=None):
        return board_for(style, [dict(p) for p in self.posts], fmt, self.words(), self.handle, self.year, bpm, self.seconds,
                         self.swatches, self.levers)


def board_hash(boards):
    return hashlib.sha256(json.dumps(boards, sort_keys=True).encode()).hexdigest()[:16]


def write_style(run, style, bpm=None):
    """The look's three boards and its storyboard.md; returns the plans by format."""
    d = BOARDS / style
    d.mkdir(parents=True, exist_ok=True)
    plans = {fmt: run.plan(style, fmt, bpm) for fmt in compose.FORMATS}
    # the render report vouches for out/ as the films of one cut, and film.json and plan.json name these boards, so
    # none of them stands while a board changes: the report comes back only from film.py render of the new cut,
    # film.json only from snap, and plan.json once the three boards and storyboard.md are written
    for index in (Path("render/film-report.json"), Path("film.json"), d / "plan.json"):
        index.unlink(missing_ok=True)
    for fmt, p in plans.items():
        _env.write_json(d / f"board-{fmt}.json", p["board"])
    reel = plans["reel"]
    b = reel["board"]
    sec = 60 / b["bpm"]
    cell = lambda t: str(t).replace("|", "/")
    lines = [f"# {compose.card(style)['name']}: {sentence(style)}", "",
             f"{len(run.posts)} posts, {b['bpm']} bpm, {reel['seconds']} s (asked {run.seconds:g} s), {len(reel['cuts'])} cuts "
             f"({len(reel['cuts']) / (reel['seconds'] / 60):.1f} a minute), the hook at frame {reel['hook_frame']}.", "",
             "| beat | layout | move | cut into it | starts | seconds | words |", "|---|---|---|---|---|---|---|"]
    for bt in b["beats"]:
        said = [ln["text"] for L in bt["layers"] if L["kind"] == "Words" for ln in L["lines"]]
        if not said and (bt["words"] or bt["label"]) and bt["form"] != "closer":
            said = [f"({bt['move']} sets: {' / '.join(x for x in (bt['words'], bt['label']) if x)})"]
        held = f" (held: {bt['held']})" if bt.get("held") else ""
        lines.append(f"| {bt['id']}{held} | {bt['layout']} | {bt['move']} | {bt['transition'] or 'none'} | {bt['start'] * sec:.2f} s | "
                     f"{bt['frames'] / FPS:.2f} | {cell(' / '.join(said))[:90]} |")
    lines += ["", "Music: " + ((_env.read_json("music.json") or {}).get("origin") or "none yet (music.py find)") + ".",
              "The music brief (taste.json `music`): " + json.dumps(run.taste.get("music"), ensure_ascii=False) + ".",
              "Mixed: not yet; music.py master writes the bed's and the effects' loudness here.",
              "", f"Sound, where each beat lands (music.py places each under the bed; {len(b['sound'])} cues):", "",
              "| at | beat | cue | what |", "|---|---|---|---|"]
    lines += [f"| {q['at'] * sec:.2f} s | {q['beat']} | {q['kind']} | {cell(q['what'])} |" for q in b["sound"]]
    lines += ["", "Generated clips (clips.py list asks the video model for them; clips.py normalize places what arrives):", "",
              "| clip | beat | role | seconds | prompt | in its place until it arrives |", "|---|---|---|---|---|---|"]
    lines += [f"| {q['id']} | {q['beat']} | {q['role']} | {q['seconds']} | {cell(q['prompt'])} | {cell(q['stand_in'])} |" for q in b["clips"]]
    lines += ["", "Rests (the sheet and the stills): " + ", ".join(f"{k} {reel['rest_beats'][k]} at frame {v}" for k, v in reel["rests"].items()), "",
              "The words, from taste.json `words` over the defaults: " + json.dumps(run.words(), ensure_ascii=False), "",
              "The photographs, in the film's order (focus and square crop from picks.json):", ""]
    lines += [f"- piece-{p['rank']}, {p['date']}, \"{p['caption']}\": {p['file']} focus {p['focus']} crop {p['crop']}"
              for p in story.film_order(run.posts)]
    _env.write_text(d / "storyboard.md", "\n".join(lines) + "\n")
    _env.write_json(d / "plan.json", {fmt: {k: v for k, v in p.items() if k != "board"} for fmt, p in plans.items()})
    return plans


def hexes_in(o):
    """Every hex color a board's layers name (a role name is the system's own color)."""
    if isinstance(o, dict):
        return [h for k, v in o.items() for h in ([v.lower()] if k == "color" and isinstance(v, str) and v.startswith("#") else hexes_in(v))]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return []


def text_boxes(b, bt):
    """The boxes of the words a beat shows at rest, for the anchor rule. The grid's year and ask are its frame, not an
    anchor."""
    if bt["form"] == "wall":
        return []
    S = b["system"]
    return [compose.text_box(S, ln) for L in bt["layers"] if L["kind"] == "Words" for ln in L["lines"] if ln.get("text")]


def style_findings(boards, swatches):
    """The template tells and style breaks a set of boards ({style: board}) has, each one plain sentence naming the
    board and the rule: two looks sharing more than two of the six axes; a face not in the board's card; a move or
    transition outside the card's allowlist; a color the card's palette rule did not make; every shot within 10 % of one
    length; words in one third of the safe area on more than 70 % of the beats that carry words; one move on two beats in a
    row; one layout on two of the nine."""
    out = []
    names = list(boards)
    for i, a in enumerate(names):
        for o in names[i + 1:]:
            same = compose.shared_axes(a, o)
            if len(same) > 2:
                out.append(f"looks {a} and {o} share {len(same)} of the six axes ({', '.join(same)}), more than two; draw one in a style that differs more")
    for n, b in boards.items():
        c = compose.card(b["style"])
        compose.use(c["id"])
        s = b["system"]
        for k in ("display", "text"):
            if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
                out.append(f"board {n}: its {k} face {s[k]['family']} is not the {k} face of {c['id']} ({c['faces'][k]['family']})")
        moves, cuts = compose.ids(c, "moves"), compose.ids(c, "transitions")
        for bt in b["beats"]:
            if bt.get("move") not in moves:
                out.append(f"board {n}: beat {bt['id']} moves by {bt.get('move')!r}, which is not a move of {c['id']} ({', '.join(moves)})")
            if bt.get("transition") is not None and bt["transition"] not in cuts:
                out.append(f"board {n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {c['id']} ({', '.join(cuts)})")
        made = set(palette.palette_of(c["palette"], swatches)["made"])
        shown = [v.lower() for k, v in s["colors"].items() if k != "swatches"] + [w["hex"].lower() for w in s["colors"].get("swatches") or []]
        for h in sorted(set(shown + hexes_in(b["beats"])) - made):
            out.append(f"board {n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make from the photographs")
        lengths = sorted(bt["frames"] for bt in b["beats"])
        mid = lengths[len(lengths) // 2]
        if all(abs(x - mid) <= 0.1 * mid for x in lengths):
            out.append(f"board {n}: every shot runs within 10 % of {mid} frames; vary the beats' lengths")
        # the places are the thirds of the safe area, the part of the frame words may stand in
        sx0, sy0, sx1, sy1 = compose.Frame(b["format"]["name"], s["finish"].get("bars", 0.0)).safe
        cells = []
        for bt in b["beats"]:
            boxes = text_boxes(b, bt)
            if boxes:
                cx = (min(x[0] for x in boxes) + max(x[2] for x in boxes)) / 2
                cy = (min(x[1] for x in boxes) + max(x[3] for x in boxes)) / 2
                cells.append((min(2, max(0, int(3 * (cx - sx0) / (sx1 - sx0)))), min(2, max(0, int(3 * (cy - sy0) / (sy1 - sy0))))))
        if len(cells) >= 3:
            top = max(set(cells), key=cells.count)
            if cells.count(top) > 0.7 * len(cells):
                where = ("top", "middle", "bottom")[top[1]] + " " + ("left", "center", "right")[top[0]]
                out.append(f"board {n}: the words sit in one place, the {where} of the frame, on {cells.count(top)} of the "
                           f"{len(cells)} beats that carry words; move them with what each beat shows")
        for x, y in zip(b["beats"], b["beats"][1:]):
            if x.get("move") and x.get("move") == y.get("move"):
                out.append(f"board {n}: beats {x['id']} and {y['id']} both move by {x['move']}; consecutive beats move differently")
        layouts = [bt["layout"] for bt in b["beats"] if bt["form"] == "photo"]
        for lay in sorted({x for x in layouts if layouts.count(x) > 1}):
            out.append(f"board {n}: {layouts.count(lay)} of the nine are laid out {lay}; every one of the nine takes a layout of its own")
    return out


def findings(plans, seconds):
    out = []
    for fmt, p in plans.items():
        out += [f"{fmt}: {x}" for x in bounds.check(p["board"])]
        if abs(p["seconds"] - seconds) > 1:
            out.append(f"{fmt}: {p['seconds']} s is not the asked {seconds:g} s")
        if p["hook_frame"] > HOOK_FRAMES:
            out.append(f"{fmt}: the hook event lands at frame {p['hook_frame']}, after frame {HOOK_FRAMES}")
    return out


def load_plans(style):
    d = BOARDS / style
    if not (d / "plan.json").exists():
        sys.exit(f"{d}/plan.json is missing: run storyboard.py draft")
    meta = _env.read_json(d / "plan.json")
    return {fmt: dict(meta[fmt], board=_env.read_json(d / f"board-{fmt}.json")) for fmt in compose.FORMATS}


def cmd_draft(a, run):
    # the choice was made from the boards and the sheets shown, so a board drafted again is shown and chosen again
    stale = [Path("winner.json"), Path("vote/scores.json"), Path("out/boards.png")]
    stale += [p / "sheet.png" for p in BOARDS.glob("*") if p.is_dir()]
    for old in stale:
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft is shown and chosen again (storyboard.py sheets, then vote.py)")
    for style in run.styles:
        plans = write_style(run, style)
        bad = findings(plans, run.seconds) + style_findings({style: plans["reel"]["board"]}, run.swatches)
        r = plans["reel"]
        print(f"{style}: {r['seconds']} s, {len(r['cuts'])} cuts, hook at frame {r['hook_frame']}, {len(bad)} findings -> {BOARDS / style}/")
        for x in bad[:8]:
            print("   ", x)
    return 0


def cmd_check(a, run):
    bad = 0
    reels = {}
    for style in run.styles:
        plans = load_plans(style)
        reels[style] = plans["reel"]["board"]
        f = findings(plans, run.seconds) + style_findings({style: reels[style]}, run.swatches)
        bad += len(f)
        print(f"{'PASS' if not f else 'FAIL'}  {style}: {len(f)} findings")
        for x in f[:20]:
            print("   ", x)
    across = [x for x in style_findings(reels, run.swatches) if x.startswith("looks ")]
    bad += len(across)
    print(f"{'PASS' if not across else 'FAIL'}  the three looks together: {len(across)} findings")
    for x in across:
        print("   ", x)
    return 1 if bad else 0


def cmd_sheets(a, run):
    import studio
    _env.need("PIL")
    from PIL import Image, ImageDraw
    with studio.lock("sheets") as held:
        # a sheet is drawn from its frames, so it goes before they are rendered again and comes back made from them
        Path("out/boards.png").unlink(missing_ok=True)
        for style in run.styles:
            (BOARDS / style / "sheet.png").unlink(missing_ok=True)
        jobs = []
        for style in run.styles:
            p = load_plans(style)["reel"]
            for k in SHEET:
                jobs.append(studio.still(p["board"], p["rests"][k], BOARDS / style / "frames" / f"{k}.png", scale=0.5))
        rep = studio.render(jobs, "sheets", held)
        if rep["failed"]:
            return 1
        rows = []
        for style in run.styles:
            ims = [Image.open(BOARDS / style / "frames" / f"{k}.png").convert("RGB") for k in SHEET]
            w, h = ims[0].size
            sheet = Image.new("RGB", (3 * w + 4 * 12, h + 24), load_plans(style)["reel"]["board"]["system"]["colors"]["bg"])
            for i, im in enumerate(ims):
                sheet.paste(im, (12 + i * (w + 12), 12))
            # the sheet moves in whole, so the choice is never made from a half-written one
            tmp = BOARDS / style / ".sheet.png.part"
            sheet.save(tmp, format="PNG")
            os.replace(tmp, BOARDS / style / "sheet.png")
            rows.append((style, sheet))
            print(f"{style}: {BOARDS / style / 'sheet.png'} (the hook, a middle beat and the closer, each at rest)")
        sw, sh = rows[0][1].size
        cap = 150
        out = Image.new("RGB", (sw, len(rows) * (sh + cap)))
        draw = ImageDraw.Draw(out)
        for i, (style, sheet) in enumerate(rows):
            # each look's name and sentence set in its own faces and colors, so the row reads as the look it shows
            S = load_plans(style)["reel"]["board"]["system"]
            bg = S["colors"]["bg"]
            ink = max((S["colors"]["ink"], S["colors"]["paper"]), key=lambda h: palette.contrast(palette.hex_rgb(h), palette.hex_rgb(bg)))
            head = compose.font_for(S, {"face": "display", "size": 40})
            body = compose.font_for(S, {"face": "text", "size": 26})
            y = i * (sh + cap)
            draw.rectangle((0, y, sw, y + sh + cap), fill=bg)
            out.paste(sheet, (0, y))
            words = compose.cased(S, "display", f"{'ABC'[i]}. {compose.card(style)['name']}")
            draw.text((24, y + sh + 14), words, fill=ink, font=head)
            text, line = sentence(style), ""
            ty = y + sh + 70
            for wd in text.split():
                if draw.textlength(f"{line} {wd}".strip(), font=body) > sw - 48:
                    draw.text((24, ty), line, fill=ink, font=body)
                    ty, line = ty + 34, wd
                else:
                    line = f"{line} {wd}".strip()
            draw.text((24, ty), line, fill=ink, font=body)
        Path("out").mkdir(exist_ok=True)
        out.save("out/.boards.png.part", format="PNG")
        os.replace("out/.boards.png.part", "out/boards.png")
        print(f"out/boards.png: the three looks, {', '.join(f'{x} {s}' for x, s in zip('ABC', run.styles))}")
        return 0


def cmd_snap(a, run):
    style = (_env.read_json("winner.json") or {}).get("board")
    if style not in run.styles:
        sys.exit("no look chosen: show out/boards.png and run vote.py pick --board <style>, or vote.py ballot and tally")
    music = _env.read_json("music.json") or {}
    base = story.BPM
    bpm, why = base, f"{base} bpm (no music tempo)"
    if music.get("bpm"):
        best = None
        # the music's tempo, its half or its double, whichever the nine fit at the asked length nearest the story's
        for k in (0.5, 1, 2):
            cand = round(music["bpm"] * k, 2)
            asked_ = {kk: v["seconds"] for kk, v in run.levers.items() if v.get("seconds")}
            if story.fits(run.posts, run.seconds, cand, asked_) and (best is None or abs(cand - base) < abs(best - base)):
                best = cand
        if best:
            bpm, why = best, f"the music's {music['bpm']} bpm" + (f" at {best / music['bpm']:g}x" if best != music["bpm"] else "")
    plans = write_style(run, style, bpm)
    bad = findings(plans, run.seconds) + style_findings({style: plans["reel"]["board"]}, run.swatches)
    boards = {fmt: str(BOARDS / style / f"board-{fmt}.json") for fmt in compose.FORMATS}
    reel = plans["reel"]
    downs = music.get("downbeats") or []
    film = {"style": style, "bpm": bpm, "tempo": why, "seconds": reel["seconds"], "frames": reel["frames"],
            "music_start": downs[0] if downs else 0.0, "hook_frame": reel["hook_frame"], "cuts": reel["cuts"],
            "rests": {fmt: p["rests"] for fmt, p in plans.items()}, "boards": boards, "findings": bad,
            "hash": board_hash({fmt: p["board"] for fmt, p in plans.items()})}
    _env.write_json("film.json", film)
    print(f"{style} at {bpm} bpm ({why}): {reel['seconds']} s, {len(reel['cuts'])} cuts, hook at frame {reel['hook_frame']}, "
          f"{len(bad)} findings -> film.json")
    for x in bad[:10]:
        print("   ", x)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    run = Run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
