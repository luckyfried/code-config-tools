#!/usr/bin/env python3
"""Movement 2: three storyboards of the year, one a style, and the step that cuts the winner to the music.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/storyboard.py draft            # build/storyboards/<style>/board-reel.json, plan.json, storyboard.md
                                                     # for each of the three styles, and storyboards/boards.json naming
                                                     # them in order; a new draft starts a new vote
    python3 S/scripts/storyboard.py check            # the three boards: the type inside the reel's safe area at every
                                                     # rest, its contrast, the subject clear of words, the length, the
                                                     # hook, and the styles three apart
    python3 S/scripts/storyboard.py sheets           # build/storyboards/<style>/sheet.png (the hook, a month and the
                                                     # closer at rest) and out/boards.png, the three side by side
    python3 S/scripts/storyboard.py snap             # the winner (winner.json) at the music's tempo -> build/film.json

The three styles are the trio (analog-home-movie, kinetic-type, swiss-grid), or, when taste.json `style` names one,
that style and the two that differ from it most (style.trio_for). Each board is drawn wholly from its style card
(styles/<id>.json): its faces, the colors its palette rule makes from the year's palette, its easing, finish and grade,
its closer, and for every beat one of its moves and one of its cuts, picked from what the beat shows (year.py). The
composition is the year's line (year.py): the wall, the months, the hook and the closer, every time in musical beats,
at the card's own tempo (the middle of its music recipe's range) until snap moves it to the music's.

The words are the person's: each month says the line of its moment (taste.json `moments`, as they wrote it in the
caption), else its post's first sentence (picks.json `said`); taste.json `words.signoff` replaces the sign-off below,
in their case and voice. A year of few months makes a shorter film, never a refusal; when taste.json `length` asks for
a length in seconds, the months stretch alike toward it (STRETCH), and snap takes the music's tempo multiple that runs
nearest it. check fails a board on any line outside the reel's safe area at its rest, any type under year.CONTRAST
over the photograph under it, a month's words over its photograph's subject, a row's name or the sign-off under its
smallest size, a length outside LENGTH, a hook event after frame 30, or a style break or template tell
(style.findings).

The months are laid out in calendar order whatever order picks.json lists them in. The handle on screen is the one the
export's profile files give (stats.json `handle`, from gather.py), or none; every command refuses a stand-in handle
(@you, @username, @your_handle and the like) as the handle or anywhere in the words on screen.

The cut (film.json) and each board's plan (plan.json, which check and sheets read with the board) name the board as it
is, so they go before the board changes and plan.json is written last, after the board and storyboard.md; only snap
writes film.json. The render report (render/film-report.json) vouches for out/ as the render of one cut, so it goes
first of all. A draft also removes each board's sheet.png, which the ballot shows, so a board drafted again is voted on
only once sheets has drawn it; sheets moves each new sheet in whole.
"""
import argparse
import calendar
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import style  # noqa: E402
import year  # noqa: E402

BOARDS = Path("storyboards")
FPS = 30
HOOK_FRAMES = 30
LENGTH = (6, 90)       # the shortest and longest film, seconds: a year of three photographs still makes one
STRETCH = (0.6, 4.0)   # how far an asked length shortens or lengthens every month, at most
# a handle that stands in for a name rather than being one, with or without its @
STAND_IN = re.compile(r"^(?:you|me|user|username|handle|name|account|instagram|insta|ig|example|someone|somebody|anonymous|"
                      r"unknown|none|null|undefined|placeholder|todo|tbd|x+|(?:your|my)[._]?(?:handle|name|username|account|ig|"
                      r"insta|instagram))$|[<>{}\[\]]|\.\.\.")


def stand_in(handle):
    """Whether a handle is a stand-in (@you, @your_handle, <handle>) rather than a name."""
    return bool(STAND_IN.search(str(handle).strip().lstrip("@").lower()))


def words_default(y):
    return {"signoff": f"see you in {y + 1}"}


def pulse_of(bpm):
    return FPS * 60 / bpm


def tempo_of(c):
    """The style's own tempo: the middle of its music recipe's range."""
    import music_engine
    book = music_engine.recipes()
    rid = c.get("music") if c.get("music") in book["recipes"] else book["default"]
    lo, hi = book["recipes"][rid]["tempo"]
    return round((lo + hi) / 2)


def trio(run):
    return style.trio_for(run.taste.get("style") or None)


def safe():
    return {k: {x: v[x] for x in ("top", "bottom", "left", "right")}
            for k, v in _env.read_json(_env.SKILL / "design" / "safe-areas.json").items() if k != "about"}


def swatches_of(taste):
    """The year's swatches the card's palette rule reads (palette.swatches_of)."""
    import palette
    return palette.swatches_of(taste, _env.read_json("palette.json"))


def asked(run):
    """The length the person asked for, seconds, or None."""
    v = run.taste.get("length")
    try:
        return float(v) if v else None
    except (TypeError, ValueError):
        m = re.search(r"\d+(?:\.\d+)?", str(v))
        return float(m.group()) if m else None


class Run:
    """The year as every board lays it out: the months with a photograph (picks.json), in calendar order, each with its
    moment (taste.json `moments`): its line, its people and its place; the story's peak, the handle (the export's
    profile name, or "" for none), the year, the register and the words. A stand-in handle, as the handle or in any
    words on screen, is refused."""

    def __init__(self):
        self.stats = _env.read_json("stats.json")
        self.picks = _env.read_json("picks.json")
        if not self.stats or not self.picks:
            sys.exit("stats.json or picks.json is missing: run research.py first")
        if not Path("taste.md").exists():
            sys.exit("build/taste.md is missing: write the taste profile (movement 1) before the storyboard")
        self.taste = _env.read_json("taste.json") or {}
        self.year = int(self.stats["year"])
        name = str(self.stats.get("handle") or "").strip().lstrip("@")
        self.handle = "@" + name if name else ""
        self.lower = bool((self.taste.get("register") or {}).get("lowercase", True))
        moment = {}
        for mo in self.taste.get("moments") or []:
            n = mo.get("month")
            n = n if isinstance(n, int) else next((i for i in range(1, 13) if calendar.month_name[i].lower() == str(n).lower()), None)
            if n:
                moment[n] = mo
        self.months = []
        self.peak = None
        for p in sorted(self.picks["months"], key=lambda p: p["month"]):
            short = calendar.month_abbr[p["month"]]
            mo = moment.get(p["month"], {})
            if mo.get("peak"):
                self.peak = f"m{p['month']:02d}"
            said = mo["line"] if "line" in mo else p.get("said") or ""
            self.months.append({"id": f"m{p['month']:02d}", "month": p["month"], "short": short.lower() if self.lower else short,
                                "said": " ".join(str(said).split()), "people": mo.get("people", p.get("people") or []),
                                "place": mo.get("place", p.get("place")),
                                "file": p["file"], "size": p["size"], "focus": p["focus"],
                                "read": p.get("focus_from") == "read",
                                "line": p.get("line") or [0, 0.5, 1, 0.5],
                                "scene": p.get("scene") or "",
                                "extra": p.get("extra") or []})
        if not self.months:
            sys.exit("no month has a photograph: the storyboard needs at least one")
        unread = [m["short"] for m in self.months if not m["scene"]]
        if unread:
            sys.exit(f"no scene for {', '.join(unread)}: write what each photograph shows as its `scene` in build/picks.json, "
                     "from build/picks-sheet.jpg (movement 1, read the photographs)")
        self.words = {}
        words = [m["said"] for m in self.months]
        words += [str(v) for w in (self.taste.get("words") or {}).values() if isinstance(w, dict) for v in w.values()]
        shown = ([self.handle] if self.handle else []) + [w.rstrip(".,!?;:'\")") for text in words for w in re.findall(r"@\S+", text)]
        stand_ins = [h for h in shown if stand_in(h)]
        if stand_ins:
            sys.exit(f"a stand-in handle would be on screen ({', '.join(dict.fromkeys(stand_ins))}): the handle on screen is the one "
                     "the export's profile files give, or none; set build/stats.json `handle` to that name or to null, and take "
                     "the stand-in out of the words in build/taste.json and build/picks.json")

    def words_for(self, s):
        """The film's words: the defaults, then taste.json `words` (or `words.<style>` for one style alone)."""
        w = dict(words_default(self.year))
        given = self.taste.get("words") or {}
        w.update({k: v for k, v in given.items() if isinstance(v, str)})
        w.update(given.get(s) or {} if isinstance(given.get(s), dict) else {})
        return w


def stretch_for(run, bpm):
    """How far every month stretches so the film runs the asked length at `bpm` (1 when none is asked)."""
    want = asked(run)
    if not want:
        return 1.0
    months = sum(year.month_beats(i, m["id"] == run.peak) for i, m in enumerate(run.months))
    fixed = year.HOOK + year.CLOSER + year.HOLD * bpm / 60
    k = (want * bpm / 60 - fixed) / months
    return round(min(STRETCH[1], max(STRETCH[0], k)), 3)


def beats_of(y, pulse):
    """The board's beats, one a cut: the hook's title, its flashes, each month, the closer; each with its form, the
    card's move and cut picked for it, its words and label, and its start and end in musical beats."""
    h = y["hook"]
    bounds = [("hook", 0.0, "title", h["moves"][0], None, y["title"]["text"], "", False),
              ("flashes", h["split"], "wall", h["moves"][1], h["transition"], "", "", False)]
    bounds += [(m["id"], m["start"], "photo", m["move"], m["transition"], "", "", m["peak"]) for m in y["months"]]
    c = y["closer"]
    bounds += [("closer", c["at"], "closer", c["move"], c["transition"], "", "", False)]
    ends = [b[1] for b in bounds[1:]] + [c["end"]]
    out = []
    for (bid, t0, form, move, cut, words, label, peak), t1 in zip(bounds, ends):
        out.append({"id": bid, "bars": 1, "frames": round(t1 * pulse) - round(t0 * pulse), "layers": [], "form": form,
                    "move": move, "transition": cut, "words": words, "label": label, "peak": peak,
                    "at": round(t0, 3), "end": round(t1, 3)})
    return out


def board_for(s, run, bpm=None):
    """The board and its plan for style `s`: {board, cuts, hook_frame, rests, seconds, frames, story}."""
    c = style.card(s)
    style.use(s)
    bpm = bpm or tempo_of(c)
    colors = style.colors_of(c, swatches_of(run.taste))
    run.words = run.words_for(s)
    looks = list(trio(run))
    y = year.build(run, style.measure, style.box_of, bpm, c, colors, stretch_for(run, bpm),
                   rank=looks.index(s) if s in looks else 0)
    style.set_lines(y)
    pulse = pulse_of(bpm)
    beats = beats_of(y, pulse)
    frames = sum(b["frames"] for b in beats)
    board = {"id": f"{s}-reel", "name": c["name"], "style": s, "handle": run.handle, "bpm": bpm,
             "format": {"width": year.W, "height": year.H, "fps": FPS, "name": "reel"},
             "system": style.system(c, colors, safe()), "beats": beats, "year": y,
             "sound": year.sound(y), "clips": year.clips(y, bpm)}
    peak = next((mo for mo in y["months"] if mo["peak"]), y["months"][len(y["months"]) // 2])
    rest_of = [mo for mo in y["months"] if mo is not peak] or [peak]
    ordinary = rest_of[len(rest_of) // 2]
    rest = lambda mo: round((mo["at"]["pull"][0] - 0.1) * pulse)
    rests = {"hook": round(y["hook"]["rest"] * pulse), "month": rest(ordinary), "peak": rest(peak),
             "closer": min(frames - 1, round(y["closer"]["still"] * pulse) + 2)}
    cuts = [round(b["at"] * pulse / FPS, 2) for b in beats[1:]]
    cuts += [round(b * pulse / FPS, 2) for b in y["hook"]["flash"][:-1]]
    return {"board": board, "cuts": sorted(set(cuts)), "hook_frame": round(sum(y["hook"]["slam"]) * pulse), "rests": rests,
            "rest_beats": {"hook": "hook", "month": ordinary["id"], "peak": peak["id"], "closer": "closer"},
            "seconds": round(frames / FPS, 2), "frames": frames, "story": year.story(y), "asked": asked(run)}


def board_hash(board):
    return hashlib.sha256(json.dumps(board, sort_keys=True).encode()).hexdigest()[:16]


def write_md(run, s, p):
    b = p["board"]
    y = b["year"]
    sec = 60 / b["bpm"]
    d = BOARDS / s
    want = f", asked for {p['asked']:g} s" if p.get("asked") else ""
    lines = [f"# {s}: {b['name']}", "", style.sentence(s), "",
             f"{len(y['months'])} months, {b['bpm']} bpm, {p['seconds']} s{want}, {len(p['cuts'])} cuts "
             f"(as the picture changes: the hook's flashes, each month's arrival and the closer), the hook at frame {p['hook_frame']}.",
             f"Faces: {b['system']['display']['family']} and {b['system']['text']['family']}; closer: {y['closer']['shape']}; "
             f"colors: " + ", ".join(f"{k} {v}" for k, v in y["colors"].items()) + ".", "",
             "| beat | starts | seconds | form | move | cut | the moment | on screen |", "|---|---|---|---|---|---|---|---|"]
    f = 0
    cell = lambda t: str(t).replace("|", "/")
    by_id = {x["id"]: x for x in run.months}
    for bt in b["beats"]:
        mo = next((x for x in y["months"] if x["id"] == bt["id"]), None)
        if mo:
            r = by_id[mo["id"]]
            with_ = ", ".join("@" + a.lstrip("@") for a in r["people"])
            moment = "; ".join(x for x in (mo["scene"], f"with {with_}" if with_ else "", r["place"] or "", "the story's peak" if mo["peak"] else "") if x)
            said = f"{mo['short']} / {mo['text']}" if mo["text"] else mo["short"]
        elif bt["id"] == "hook":
            moment, said = "the year opens", y["title"]["text"]
        elif bt["id"] == "flashes":
            moment, said = "every month's photograph flashes in the window", ""
        else:
            moment, said = "the year's chapters whole, then the card's closer", " / ".join(x["text"] for x in (y["handle"], y["signoff"]) if x)
        lines.append(f"| {bt['id']} | {f / FPS:.2f} s | {bt['frames'] / FPS:.2f} | {bt['form']} | {bt['move']} | {bt['transition'] or '-'} "
                     f"| {cell(moment)} | {cell(said)} |")
        f += bt["frames"]
    lines += ["", "What each move reveals, and what it carries across the cut:", "", "| beat | reveals | carries |", "|---|---|---|"]
    lines += [f"| {r['id']} | {r['reveals']} | {r['carries']} |" for r in p["story"]]
    music = _env.read_json("music.json") or {}
    mixed = (f"bed {music['bed_lufs']} LUFS, effects {music['fx_lufs']} LUFS" if "bed_lufs" in music else
             "not yet; music.py master writes the bed's and the effects' loudness here")
    lines += ["", "Music: " + (music.get("origin") or f"none yet (music.py find composes the {s} recipe)") + ".",
              "The music brief (taste.json `music`): " + json.dumps(run.taste.get("music"), ensure_ascii=False) + ".",
              f"Mixed: {mixed}.",
              "", f"Sound, where each beat lands (the bed's own effects, mixed under it; {len(b['sound'])} cues):", "",
              "| at | beat | cue | what |", "|---|---|---|---|"]
    lines += [f"| {c['at'] * sec:.2f} s | {c['beat']} | {c['kind']} | {c['what']} |" for c in b["sound"]]
    lines += ["", "Generated clips (clips.py list asks the video model for them; clips.py normalize places what arrives):", "",
              "| clip | beat | role | seconds | prompt | in its place until it arrives |", "|---|---|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['beat']} | {c['role']} | {c['seconds']} | {c['prompt']} | {c['stand_in']} |" for c in b["clips"]]
    lines += ["", "Rests (the sheet and the stills): " + ", ".join(f"{k} {p['rest_beats'][k]} at frame {v}" for k, v in p["rests"].items()), "",
              "The words, from taste.json `words` over the defaults: " + json.dumps(run.words, ensure_ascii=False), "",
              "The photographs (scene, focus and line from picks.json):", ""]
    lines += [f"- {m['short']}: {m['scene']}: {m['file']} focus {m['focus']} line {m['line']}" for m in run.months]
    _env.write_text(d / "storyboard.md", "\n".join(lines) + "\n")


def write_board(run, s, bpm=None):
    d = BOARDS / s
    d.mkdir(parents=True, exist_ok=True)
    p = board_for(s, run, bpm)
    # the render report vouches for out/ as the render of one cut, so it goes before the cut changes
    for old in (Path("render/film-report.json"), Path("film.json"), d / "plan.json"):
        old.unlink(missing_ok=True)
    _env.write_json(d / "board-reel.json", p["board"])
    write_md(run, s, p)
    _env.write_json(d / "plan.json", {"reel": {k: v for k, v in p.items() if k != "board"}})
    return p


def shown_of(b, bt):
    """The boxes of the words a beat shows at rest."""
    y = b["year"]
    if bt["form"] == "photo":
        m = next(x for x in y["months"] if x["id"] == bt["id"])
        return [style.box_of(ln) for ln in [m["name"], *m["said"]]]
    if bt["form"] == "title":
        return [style.box_of(y["title"])]
    if bt["form"] == "closer":
        return [style.box_of(ln) for ln in (y["signoff"], y["handle"]) if ln]
    return []


def findings(p):
    out = []
    b = p["board"]
    style.use(b["style"])
    y = b["year"]
    sa = b["system"]["safe"]["reel"]
    W, H = b["format"]["width"], b["format"]["height"]
    area = [sa["left"], sa["top"], W - sa["right"], H - sa["bottom"]]
    box_of = style.box_of

    def inside(where, ln):
        x0, y0, x1, y1 = box_of(ln)
        if x0 < area[0] - 0.5 or y0 < area[1] - 0.5 or x1 > area[2] + 0.5 or y1 > area[3] + 0.5:
            out.append(f"{where}: \"{ln['text']}\" at [{x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f}] leaves the safe area {area}")

    for k in ("title", "handle", "signoff"):
        if y[k]:
            inside(f"wall {k}", y[k])
    for r in y["rows"]:
        inside("wall row", r["label"])
    for m in y["months"]:
        for ln in [m["name"], *m["said"]]:
            inside(m["id"], ln)
        cell = year.area_box(year.layout_of(b["system"]["photo"], m["size"])["line"]["box"])
        over = [ln["text"] for ln in [m["name"], *m["said"]] if box_of(ln)[2] > cell[2] + 0.5 or box_of(ln)[0] < cell[0] - 0.5]
        if over:
            out.append(f"{m['id']}: \"{' '.join(over)}\" runs past the card's line box {cell}: shorten the month's line (taste.json moments `line`)")
        if m.get("on_subject"):
            out.append(f"{m['id']}: its words cover {m['on_subject']} px of its photograph's subject wherever they stand: shorten the month's line (taste.json moments `line`)")
    lines = [("wall title", y["title"]), ("wall handle", y["handle"]), ("wall sign-off", y["signoff"])]
    lines += [("wall row", r["label"]) for r in y["rows"]] + [(m["id"], ln) for m in y["months"] for ln in [m["name"], *m["said"]]]
    for where, ln in lines:
        if ln and (ln.get("contrast") or 0) < year.CONTRAST:
            out.append(f"{where}: \"{ln['text']}\" holds {ln.get('contrast') or 0}:1 over the photograph under it, under {year.CONTRAST}:1")
    for where, ln, least in [("wall row", r["label"], year.LABEL[0]) for r in y["rows"]] + [("wall sign-off", y["signoff"], year.SIGNOFF[0])]:
        if ln["size"] < least:
            out.append(f"{where}: \"{ln['text']}\" is set at {ln['size']} px, under its smallest, {least} px")
    if y["handle"] and stand_in(y["handle"]["text"]):
        out.append(f"wall handle: \"{y['handle']['text']}\" is a stand-in, not a name from the export's profile files")
    lo, hi = LENGTH
    if not lo <= p["seconds"] <= hi:
        out.append(f"{p['seconds']} s is outside {lo}-{hi} s")
    if p["hook_frame"] > HOOK_FRAMES:
        out.append(f"the hook event lands at frame {p['hook_frame']}, after frame {HOOK_FRAMES}")
    return out


def load_plan(s):
    d = BOARDS / s
    if not (d / "plan.json").exists():
        sys.exit(f"{d}/plan.json is missing: run storyboard.py draft")
    return dict(_env.read_json(d / "plan.json")["reel"], board=_env.read_json(d / "board-reel.json"))


def order():
    """The styles of the drafted boards, in the order the person sees them."""
    got = (_env.read_json(BOARDS / "boards.json") or {}).get("order")
    if not got:
        sys.exit("storyboards/boards.json is missing: run storyboard.py draft")
    return got


def all_findings(plans, taste):
    """Each board's own findings, and the set's style breaks and template tells, as {style: [finding]}."""
    out = {s: findings(p) for s, p in plans.items()}
    for line in style.findings({s: p["board"] for s, p in plans.items()}, swatches_of(taste), shown_of):
        who = next((s for s in plans if line.startswith(s)), next(iter(plans)))
        out[who].append(line)
    return out


def cmd_draft(a, run):
    # the vote judged the boards it was shown, so a board drafted again is voted again
    for old in (Path("winner.json"), Path("vote/scores.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    styles = list(trio(run))
    (BOARDS / "boards.json").unlink(missing_ok=True)
    for s in styles:
        (BOARDS / s / "sheet.png").unlink(missing_ok=True)
    plans = {s: write_board(run, s) for s in styles}
    _env.write_json(BOARDS / "boards.json", {"order": styles})
    bad = all_findings(plans, run.taste)
    for s in styles:
        p = plans[s]
        print(f"{s}: {p['seconds']} s, {len(p['cuts'])} cuts, {len(p['board']['sound'])} sound cues, hook at frame {p['hook_frame']}, "
              f"{len(bad[s])} findings -> {BOARDS / s}/")
        for x in bad[s][:12]:
            print("   ", x)
    return 0


def cmd_check(a, run):
    plans = {s: load_plan(s) for s in order()}
    bad = all_findings(plans, run.taste)
    for s, f in bad.items():
        print(f"{'PASS' if not f else 'FAIL'}  {s}: {len(f)} findings")
        for x in f[:20]:
            print("   ", x)
    return 1 if any(bad.values()) else 0


def boards_png(styles):
    """out/boards.png: the three sheets one over another, each under its style's name and its one sentence, set in that
    style's own display and text faces."""
    from PIL import Image, ImageDraw
    sheets = [Image.open(BOARDS / s / "sheet.png").convert("RGB") for s in styles]
    w = max(im.width for im in sheets)
    head = 110
    out = Image.new("RGB", (w, sum(im.height + head for im in sheets)), "white")
    d = ImageDraw.Draw(out)
    y = 0
    for i, (s, im) in enumerate(zip(styles, sheets)):
        style.use(s)
        d.text((14, y + 14), style.cased(f"{i + 1}. {style.card(s)['name']}", "display"), fill="#111111", font=_env.pil_font(40, "display"))
        d.text((14, y + 66), style.sentence(s)[:150], fill="#444444", font=_env.pil_font(24, "text"))
        out.paste(im, (0, y + head))
        y += im.height + head
    dst = _env.WORKSPACE / "out" / "boards.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(".boards.png.part")
    out.save(tmp, "PNG")
    os.replace(tmp, dst)
    return dst


def cmd_sheets(a, run):
    import studio
    _env.need("PIL")
    from PIL import Image
    keys = ("hook", "month", "closer")
    styles = order()
    jobs = []
    for s in styles:
        p = load_plan(s)
        for k in keys:
            jobs.append(studio.still(p["board"], p["rests"][k], BOARDS / s / "frames" / f"{k}.png", scale=0.5))
    rep = studio.render(jobs, "sheets")
    for s in styles:
        ims = [Image.open(BOARDS / s / "frames" / f"{k}.png") for k in keys]
        w, h = ims[0].size
        sheet = Image.new("RGB", (3 * w + 4 * 12, h + 24), "white")
        for i, im in enumerate(ims):
            sheet.paste(im.convert("RGB"), (12 + i * (w + 12), 12))
        tmp = BOARDS / s / ".sheet.png.part"
        sheet.save(tmp, "PNG")
        os.replace(tmp, BOARDS / s / "sheet.png")
        print(f"{s}: {BOARDS / s / 'sheet.png'} (the hook, an ordinary month and the closer, each at rest)")
    print(f"boards: {boards_png(styles)}")
    return 1 if rep["failed"] else 0


def cmd_snap(a, run):
    won = (_env.read_json("winner.json") or {}).get("board")
    if won not in (_env.read_json(BOARDS / "boards.json") or {}).get("order", []):
        sys.exit("no winner: the boards have not been voted on; run vote.py ballot, fill it in, then vote.py tally (or vote.py pick)")
    music = _env.read_json("music.json") or {}
    base = tempo_of(style.card(won))
    lo, hi = LENGTH
    want = asked(run)
    bpm, why = base, f"the {won} tempo, {base} bpm (no music tempo)"
    if music.get("bpm"):
        best = None
        for k in (0.5, 1, 2):
            cand = round(music["bpm"] * k, 2)
            secs = board_for(won, run, cand)["seconds"]
            if not lo <= secs <= hi:
                continue
            key = abs(secs - want) if want else abs(cand - base)
            if best is None or key < best[0]:
                best = (key, cand)
        if best:
            bpm = best[1]
            why = f"the music's {music['bpm']} bpm" + (f" at {bpm / music['bpm']:g}x" if bpm != music["bpm"] else "")
    p = write_board(run, won, bpm)
    bad = findings(p)
    downs = music.get("downbeats") or []
    film = {"style": won, "board": won, "bpm": bpm, "tempo": why, "seconds": p["seconds"], "asked": want, "frames": p["frames"],
            "music_start": downs[0] if downs else 0.0, "hook_frame": p["hook_frame"], "cuts": p["cuts"],
            "rests": {"reel": p["rests"]}, "boards": {"reel": str(BOARDS / won / "board-reel.json")}, "findings": bad,
            "still": round(p["board"]["year"]["closer"]["still"] * pulse_of(bpm)), "hash": board_hash(p["board"])}
    _env.write_json("film.json", film)
    print(f"{won} at {bpm} bpm ({why}): {p['seconds']} s" + (f" (asked {want:g} s)" if want else "") +
          f", {len(p['cuts'])} cuts, hook at frame {p['hook_frame']}, {len(bad)} findings -> film.json")
    for x in bad[:10]:
        print("   ", x)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    a = ap.parse_args()
    _env.need("PIL")
    _env.enter_build()
    run = Run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
