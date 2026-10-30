#!/usr/bin/env python3
"""Movement 2: the three storyboards of the year's places, one per style, laid out for the reel, the landscape and the
square, and the step that cuts the chosen one to the music.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/storyboard.py draft    # grade the cast, source.json, and for each of the three styles
                                             # storyboards/<style>/board-{reel,landscape,square}.json, plan.json and
                                             # storyboard.md, each board checked; a new draft starts a new vote
                                             # (winner.json and vote/scores.json go); when the person's lines take longer
                                             # to read than the longest film, the longest are set to their first clause
                                             # and storyboard.md names each one
    python3 S/scripts/storyboard.py check    # solve the boards again from source.json and check them (exit 1 on a finding)
    python3 S/scripts/storyboard.py sheets   # storyboards/<style>/frames/{hook,stop,closer}.png and sheet.png, each at
                                             # rest, and out/boards.png: the three sheets, first, second and third look
    python3 S/scripts/storyboard.py snap     # the chosen look (winner.json) at the music's tempo -> film.json (exit 1 on
                                             # a finding); its boards are solved again, so sheets runs again after it

The three styles: the one taste.json `style` names and the two of the kit's three (look.TRIO: swiss-grid,
cinematic-letterbox, scrapbook) that differ most from it, or the three when it names none, in that order. A board is
the kit's one story, the dot drawing the year's route and every place it reaches opening into the person's photograph
(board_drive.py), drawn in one style: the style card (styles/<id>.json) gives its faces, colors, easing, finish, the
photograph's layout, the moves each beat may take and the closer. The source (source.json) is everything the builder
reads: the places and the route in date order (places.json), the graded photographs of each visit (public/photos.json,
from cast.json through grade.py) and the handle (taste.json). The builder computes every number, projection and
position from it in px of one format; nothing on a board is typed by hand. An edit goes in taste.json, places.json or
cast.json, and draft solves again; source.json records a digest of each (`inputs`), so qa.py can tell a film cut from
inputs that have changed since. One storyboard gives all three formats: the layout is solved again for each frame,
never scaled to fit.

Each board names its rests, the settled frames the sheets and the stills are taken from: the hook, the stop (the
peak, else the middle stop) and the closer. storyboard.md states, per beat, its move and the cut into it, what it
reveals and what it carries across the cut, where the music came from, the person's music brief, the mix's loudness
(music.py master writes it), the sound cues where each beat lands, the cuts and cuts per minute and the hook's frame,
as figures for the critics.

check refuses a board on any of these, in any format:
  bounds     bounds.py: a photograph enlarged past its pixels, type outside the safe area or under its floor, the
             closer's names over each other or off their pins, a pin outside the closer's window
  binding    a photograph shown at a place it was not taken in
  formats    a format whose beats differ from the reel's in their ids or bars (every format is cut on one grid)
  story      a beat without what it reveals or what it carries
  sound      no stop cue, a cue after the stop, or a stop less than a second before the end (the film holds still and
             silent after it)
  length     the film outside its board's band (board_drive.timing()): 20 to 42 s, or from the longest film its stops'
             holds reach when that is under 20 s, to 42 s
  hook       the hook's first event after frame 30
  style      look.style_findings over the three reels: a move or cut the card does not allow, a hex the palette rule did
             not make, two boards in one style, or one board's layout the same as another's
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import board_drive  # noqa: E402
import bounds  # noqa: E402
import look  # noqa: E402

BOARDS = Path("storyboards")
PUBLIC = Path("public")
REPORT = Path("render/film-report.json")  # film.py render's report: out/ as the render of the current cut
FORMATS = ("reel", "landscape", "square")
FPS = board_drive.FPS
HOOK_FRAMES = 30
# beats before the camera leaves a place that its words start to leave (motion/studio/route/words.tsx LEAVE); a rest is
# taken before them, so the sheet and the stills show the words whole
WORDS_SINK = 0.35
# the files the source is built from, each recorded in source.json `inputs` by its digest
INPUTS = ("taste.json", "cast.json", "places.json")
CUES = {"hit", "riser", "impact", "stop"}


# ------------------------------------------------------------------ the source
def digest(name):
    """The first 16 hex digits of the file's sha256, or None when it is missing."""
    p = Path(name)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def moments_of(taste, own):
    """Each visit's words and the peak, as taste.json's moments keep them: the person's line only where its moment has its own
    photograph (`own`, from grade.own_prints), so a reel's moment is wordless on the place's own print."""
    rows = []
    for m in taste.get("moments") or []:
        if m.get("place"):
            k = (m["place"], m.get("n", 1))
            rows.append({"place": k[0], "n": k[1], "line": m.get("line") if own.get(k) else None, "peak": bool(m.get("peak"))})
    return rows


def build_source(own):
    pl = _env.read_json("places.json")
    rows = (_env.read_json(PUBLIC / "photos.json") or {}).get("photos")
    taste = _env.read_json("taste.json") or {}
    if not pl:
        sys.exit("places.json is missing: run research.py first")
    if not rows:
        sys.exit("public/photos.json is missing: run storyboard.py draft (it grades cast.json)")
    bare = [p["name"] for p in pl["places"] if p["id"] not in {r["place"] for r in rows}]
    if bare:
        sys.exit(f"{', '.join(bare)} {'has' if len(bare) == 1 else 'have'} no photograph of theirs, and every place on the film "
                 "opens into its photograph: give it one in cast.json, or leave it off with places.py --drop and research.py")
    keep = ("id", "name", "country", "lat", "lon")
    places = {"year": pl.get("year"), "home": pl.get("home"), "home_said": bool(pl.get("home_said")),
              "places": [{k: p.get(k) for k in keep} for p in pl["places"]],
              "route_visits": [{k: v.get(k) for k in ("place", "from", "to", "rows")} for v in pl.get("route_visits") or []]}
    if not places["route_visits"]:
        places["route"] = pl.get("route") or []
    # the person's case and the year's colors, which the style card's palette rule makes the film's colors from; the
    # card gives everything else
    look_ = {"register": {"lowercase": bool((taste.get("register") or {}).get("lowercase"))},
             "palette": {"year": [{"hex": c["hex"], "name": c.get("name")} for c in (taste.get("palette") or {}).get("year") or []]}}
    moments = moments_of(taste, own)
    return {"places": places, "photos": rows, "handle": (taste.get("handle") or pl.get("handle") or "").lstrip("@") or None, "taste": look_,
            "moments": moments, "seconds": taste.get("seconds"), "inputs": {n: digest(n) for n in INPUTS}}


# ------------------------------------------------------------------ the plan
def starts_of(board):
    """Each beat's first frame, and the film's frames."""
    out, f = [], 0
    for b in board["beats"]:
        out.append(f)
        f += b["frames"]
    return out, f


def stop_index(board):
    """The stop the sheet shows beside the hook and the closer: the peak, else the middle stop."""
    cards = board["route"]["cards"]
    peak = [c["i"] for c in cards[1:] if c["kind"] == "peak"]
    return peak[0] if peak else max(1, len(cards) // 2)


def styles():
    """The run's three styles, in the order the sheet shows them: taste.json `style` and the two that differ most from
    it, else the kit's three."""
    return list(look.trio_for((_env.read_json("taste.json") or {}).get("style")))


def plan(source, fmt, bpm=None, style=look.TRIO[0]):
    """The board in `style` and format `fmt` at `bpm` (the kit's own when None), and its plan: {board, cuts (seconds),
    hook_frame, rests ({hook, stop, closer: frame}), rest_beats, seconds, frames}."""
    b = board_drive.build(source, fmt, bpm, style=style)
    b["bpm"] = bpm or board_drive.BPM
    board_drive.frames(b)
    pulse = FPS * 60 / b["bpm"]
    first, total = starts_of(b)
    beat_at, _ = board_drive.starts(b)
    cards = b["route"]["cards"]
    ids = [x["id"] for x in b["beats"]]

    def rest(i):
        # a stop at rest: its photograph whole with its name and line, just before its words leave
        if i == len(ids) - 1:
            return total - 2
        leave = beat_at[ids[i + 1]]
        return round((leave - cards[i]["go"] - WORDS_SINK - 0.1) * pulse)
    stop = stop_index(b)
    rests = {"hook": rest(0), "stop": rest(stop), "closer": rest(len(ids) - 1)}
    return {"board": b, "cuts": [round(f / FPS, 3) for f in first[1:]], "hook_frame": round(b["route"]["hook"]["dive"] * pulse),
            "rests": rests, "rest_beats": {"hook": ids[0], "stop": ids[stop], "closer": ids[-1]},
            "seconds": round(total / FPS, 2), "frames": total}


def board_hash(boards):
    return hashlib.sha256(json.dumps(boards, sort_keys=True).encode()).hexdigest()[:16]


# ------------------------------------------------------------------ the findings
def binding(board, rows):
    of = {r["file"]: r["place"] for r in rows}
    return [f"binding: {c['id']} shows {c['file']} ({of[c['file']]}) as {c['place']}"
            for c in board["route"]["cards"] if c["file"] in of and of[c["file"]] != c["place"]]


def sound_findings(board, seconds):
    cues = board.get("sound") or []
    out = [f"sound: a cue of kind {c['kind']}, which music.py does not know" for c in cues if c["kind"] not in CUES]
    stop = [c["at"] for c in cues if c["kind"] == "stop"]
    if len(stop) != 1:
        return out + [f"sound: {len(stop)} stop cues; the film has one, where the picture and the music stop together"]
    sec = 60 / board["bpm"]
    late = [c for c in cues if c["at"] > stop[0]]
    out += [f"sound: {c['kind']} at {c['at'] * sec:.2f} s comes after the stop" for c in late]
    if seconds - stop[0] * sec < 1.0:
        out.append(f"sound: the stop lands {seconds - stop[0] * sec:.2f} s before the end; the film holds still and silent a second or more")
    return out


def in_band(seconds, band):
    """The film's length inside the band its board is held to (board `length`, from board_drive.timing()), to the
    frame."""
    return band[0] - 1 / FPS <= seconds <= band[1] + 1 / FPS


def length_said(seconds, asked, stops):
    """The film's length, with the length asked for beside it when the two differ."""
    if asked and abs(seconds - asked) >= 0.05:
        return f"{seconds:g} s ({asked:g} s asked: the nearest length on the beat these {stops} stops make)"
    return f"{seconds:g} s"


def findings(plans, rows):
    out = []
    shape = lambda b: [(x["id"], x["bars"]) for x in b["beats"]]
    reel = plans["reel"]["board"]
    for fmt, p in plans.items():
        b = p["board"]
        out += [f"{fmt}: {x}" for x in bounds.check(b)]
        if shape(b) != shape(reel):
            out.append(f"{fmt}: formats: its beats are {shape(b)}, the reel's {shape(reel)}")
        if not in_band(p["seconds"], b["length"]):
            out.append(f"{fmt}: length: {p['seconds']} s is outside {b['length'][0]:g}-{b['length'][1]:g} s")
        if p["hook_frame"] > HOOK_FRAMES:
            out.append(f"{fmt}: hook: the first event lands at frame {p['hook_frame']}, after frame {HOOK_FRAMES}")
    out += binding(reel, rows)
    out += [f"story: {b['id']} does not say what it {k}" for b in reel["beats"] for k in ("reveals", "carries") if not b.get(k)]
    out += sound_findings(reel, plans["reel"]["seconds"])
    return out


def style_findings(by_style, source):
    """look.style_findings over the reels of the three styles."""
    taste = _env.read_json("taste.json") or {}
    sw = look.swatches_of(taste, (source.get("taste") or {}).get("palette"))
    return [f"style: {x}" for x in look.style_findings({s: p["reel"]["board"] for s, p in by_style.items()}, sw)]


# ------------------------------------------------------------------ the boards on disk
def words_of(board, i):
    cards = board["route"]["cards"]
    if i < len(cards):
        return [ln["text"] for ln in cards[i]["lines"]]
    cl = board["route"]["closer"]
    return [w for w in (cl["title"], cl["signoff"], board.get("handle")) if w]


def write_board(source, style, bpm=None):
    """The style's reel, landscape and square boards, storyboard.md and plan.json; returns the plans by format."""
    d = BOARDS / style
    d.mkdir(parents=True, exist_ok=True)
    plans = {fmt: plan(source, fmt, bpm, style) for fmt in FORMATS}
    # plan.json names the three boards and storyboard.md as one set, film.json was cut from boards and the sheet was
    # rendered from them, and render/film-report.json vouches for out/ as the render of that cut, so the report goes
    # first and the rest before the first board changes; plan.json comes back after storyboard.md, film.json and the
    # sheet only from snap and sheets, and the report only from film.py render
    for old in (REPORT, d / "plan.json", Path("film.json"), d / "sheet.png"):
        old.unlink(missing_ok=True)
    for fmt, p in plans.items():
        _env.write_json(d / f"board-{fmt}.json", p["board"])
    reel = plans["reel"]
    b = reel["board"]
    first, _ = starts_of(b)
    sec = 60 / b["bpm"]
    cuts = len(reel["cuts"])
    lines = [f"# {style}: {look.sentence(style)}", "",
             f"{len(b['route']['cards'])} stops, {b['bpm']:g} bpm, {length_said(reel['seconds'], source.get('seconds'), len(b['route']['cards']))}, {cuts} cuts "
             f"({cuts / (reel['seconds'] / 60):.1f} a minute), the hook's first event at frame {reel['hook_frame']}.", "",
             "| beat | starts | seconds | words |", "|---|---|---|---|"]
    for i, x in enumerate(b["beats"]):
        lines.append(f"| {x['id']} | {first[i] / FPS:.2f} s | {x['frames'] / FPS:.2f} | {' / '.join(words_of(b, i))[:90]} |")
    lines += ["", "Each beat's move and the cut into it (the card's own), what it reveals and what it carries across the cut:", "",
              "| beat | move | cut | reveals | carries |", "|---|---|---|---|---|"]
    lines += [f"| {x['id']} | {x.get('move')} | {x.get('transition') or '(the first)'} | {x.get('reveals', '')} | {x.get('carries', '')} |" for x in b["beats"]]
    cues = b.get("sound") or []
    lines += ["", "Music: " + ((_env.read_json("music.json") or {}).get("origin") or "none yet (music.py find)") + ".",
              "The music brief (taste.json `music`): " + json.dumps((_env.read_json("taste.json") or {}).get("music"), ensure_ascii=False) + ".",
              "Mixed: not yet; music.py master writes the bed's and the effects' loudness here.",
              "", f"Sound, where each beat lands (music.py synthesises each and mixes it under the bed; {len(cues)} cues):", "",
              "| at | beat | cue | what |", "|---|---|---|---|"]
    lines += [f"| {c['at'] * sec:.2f} s | {c['beat']} | {c['kind']} | {c['what']} |" for c in cues]
    if b.get("clips"):
        lines += ["", "Generated clips, one shot per stop (clips.py list writes them to clips/requests.json; clips.py normalize places "
                  "what arrives):", "", "| clip | beat | use | seconds | subject and light | move | lens and height | in its place until it arrives |",
                  "|---|---|---|---|---|---|---|---|"]
        lines += [f"| {c['id']} | {c['beat']} | {c['role']} | {c['seconds']} | {c['subject']} | {c['move']} | {c['camera']} | {c['stand_in']} |"
                  for c in b["clips"]]
    lines += ["", "Rests (the sheet and the stills): " + ", ".join(f"{k} {reel['rest_beats'][k]} at frame {v}" for k, v in reel["rests"].items()), "",
              "| stop | place | photograph | the line | the way the dot leaves |", "|---|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['name']} | {c['file']} | {c.get('said') or '(no line: the name alone)'} | {c['travel']} |" for c in b["route"]["cards"]]
    cut = source.get("trimmed") or []
    if cut:
        lines += ["", f"The lines took longer to read than the {board_drive.LENGTH[1]} s film leaves with the peak holding longest, so draft shortened {len(cut)}: a line of "
                  "more than one clause to its first, a line of one clause left out with its place keeping its name. To say one "
                  "another way, change it in taste.json `moments` and run draft again:", "", "| place | visit | the line | on the film |",
                  "|---|---|---|---|"]
        lines += [f"| {t['place']} | {t['n']} | {t['line']} | {t['now'] or '(the name alone)'} |" for t in cut]
    _env.write_text(d / "storyboard.md", "\n".join(lines) + "\n")
    _env.write_json(d / "plan.json", {fmt: {k: v for k, v in p.items() if k != "board"} for fmt, p in plans.items()})
    return plans


def load_plans(style):
    d = BOARDS / style
    if not (d / "plan.json").exists():
        sys.exit(f"{d}/plan.json is missing: run storyboard.py draft")
    meta = _env.read_json(d / "plan.json")
    return {fmt: dict(meta[fmt], board=_env.read_json(d / f"board-{fmt}.json")) for fmt in FORMATS}


def source():
    s = _env.read_json("source.json")
    if not s:
        sys.exit("source.json is missing: run storyboard.py draft")
    return s


def say(style, plans, bad, asked=None):
    r = plans["reel"]
    said = length_said(r["seconds"], asked, len(r["board"]["route"]["cards"]))
    print(f"{style}: {said}, {len(r['cuts'])} cuts, hook at frame {r['hook_frame']}, {len(bad)} findings -> {BOARDS / style}/")
    for x in bad[:20]:
        print("   ", x)


# ------------------------------------------------------------------ commands
def cmd_draft(a):
    if not _env.read_json("taste.json") or not Path("taste.md").exists():
        sys.exit("taste.json and taste.md are missing: write the taste profile (movement 1) before the storyboard")
    if not _env.read_json("cast.json"):
        sys.exit("cast.json is missing: run research.py --set <photo set>, look at cast.png and correct cast.json first")
    # the vote judged the boards it was shown and snap cut film.json from the winner, so a board drafted again is voted
    # and snapped again, and the render of the old cut vouches for nothing
    REPORT.unlink(missing_ok=True)
    for old in (Path("winner.json"), Path("vote/scores.json"), Path("film.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    import grade
    own = grade.own_prints()
    rows = grade.grade_cast(own)
    src = board_drive.fit_lines(build_source(own))
    _env.write_json("source.json", src)
    bad = 0
    by = {}
    for st in styles():
        by[st] = write_board(src, st)
        f = findings(by[st], src["photos"])
        say(st, by[st], f, src.get("seconds"))
        bad += len(f)
    sf = style_findings(by, src)
    for x in sf:
        print("   ", x)
    bad += len(sf)
    if src["trimmed"]:
        print(f"{len(src['trimmed'])} of the lines shortened to fit {board_drive.LENGTH[1]} s with the peak holding longest; storyboard.md names them")
    print(f"graded {len(rows)} photographs; wrote source.json and storyboards/; next: storyboard.py sheets")
    return 1 if bad else 0


def cmd_check(a):
    src = source()
    bad = 0
    by = {}
    for st in styles():
        by[st] = write_board(src, st)
        f = findings(by[st], src["photos"])
        bad += len(f)
        print(f"{'PASS' if not f else 'FAIL'}  {st}: {len(f)} findings")
        for x in f[:20]:
            print("   ", x)
    sf = style_findings(by, src)
    print(f"{'PASS' if not sf else 'FAIL'}  the three styles apart: {len(sf)} findings")
    for x in sf[:20]:
        print("   ", x)
    return 1 if bad or sf else 0


LOOKS = ("First look", "Second look", "Third look")


def cmd_sheets(a):
    import studio
    _env.need("PIL")
    from PIL import Image, ImageDraw
    sts = styles()
    jobs = []
    for st in sts:
        # the sheet goes before the frames it is drawn from change, so a sheets run stopped partway never leaves a
        # sheet over frames it does not show
        (BOARDS / st / "sheet.png").unlink(missing_ok=True)
        p = load_plans(st)["reel"]
        for k in ("hook", "stop", "closer"):
            jobs.append(studio.still(p["board"], p["rests"][k], BOARDS / st / "frames" / f"{k}.png", scale=0.5))
    rep = studio.render(jobs, "sheets")
    bad = studio.faults(rep)
    for x in dict.fromkeys(bad):
        print("fault:", x[:400])
    if bad:
        return 1
    sheets = []
    for st in sts:
        ims = [Image.open(BOARDS / st / "frames" / f"{k}.png") for k in ("hook", "stop", "closer")]
        w, h = ims[0].size
        sheet = Image.new("RGB", (3 * w + 4 * 12, h + 24), "white")
        for i, im in enumerate(ims):
            sheet.paste(im.convert("RGB"), (12 + i * (w + 12), 12))
        sheet.save(BOARDS / st / ".sheet.png.part", "PNG")
        os.replace(BOARDS / st / ".sheet.png.part", BOARDS / st / "sheet.png")
        sheets.append(sheet)
        print(f"{st}: {BOARDS / st / 'sheet.png'} (the hook, the stop and the closer, each at rest)")
    # out/boards.png: the three sheets one over another, each named by its place (the words a person answers with) and
    # its look's name, with the look's one sentence for the person under it
    w, h = sheets[0].size
    band = 104
    board = Image.new("RGB", (w, len(sheets) * (h + band)), "white")
    draw = ImageDraw.Draw(board)
    face = str(_env.FONT_FILES["text"])
    from PIL import ImageFont
    font, small = ImageFont.truetype(face, 34), ImageFont.truetype(face, 24)
    for i, (st, sh) in enumerate(zip(sts, sheets)):
        y = i * (h + band)
        draw.text((14, y + 52), f"{LOOKS[i]}: {look.card(st)['name']}", fill="#111111", font=font, anchor="ls")
        draw.text((14, y + 88), look.sentence(st) or "", fill="#555555", font=small, anchor="ls")
        board.paste(sh, (0, y + band))
    Path("out").mkdir(exist_ok=True)
    board.save("out/.boards.png.part", "PNG")
    os.replace("out/.boards.png.part", "out/boards.png")
    print(f"out/boards.png: {', '.join(f'{LOOKS[i].lower()} {st}' for i, st in enumerate(sts))}")
    return 0


def cmd_snap(a):
    style = (_env.read_json("winner.json") or {}).get("board")
    if style not in styles():
        sys.exit("no look is chosen: run vote.py ballot and tally, then vote.py pick with the person's choice or yours")
    src = source()
    music = _env.read_json("music.json") or {}
    base = board_drive.BPM
    bpm, why = base, f"the kit's tempo, {base} bpm (no music tempo)"
    if music.get("bpm"):
        best = None
        for k in (0.5, 1, 2):
            cand = round(music["bpm"] * k, 2)
            try:
                p = plan(src, "reel", cand, style)
            except ValueError:
                continue
            if in_band(p["seconds"], p["board"]["length"]) and (best is None or abs(cand - base) < abs(best - base)):
                best = cand
        if best:
            bpm, why = best, f"the music's {music['bpm']} bpm" + (f" at {best / music['bpm']:g}x" if best != music["bpm"] else "")
    plans = write_board(src, style, bpm)
    bad = findings(plans, src["photos"])
    reel = plans["reel"]
    downs = music.get("downbeats") or []
    film = {"style": style, "bpm": bpm, "tempo": why, "seconds": reel["seconds"], "length": reel["board"]["length"], "frames": reel["frames"],
            "music_start": downs[0] if downs else 0.0, "hook_frame": reel["hook_frame"], "cuts": reel["cuts"],
            "rests": {fmt: p["rests"] for fmt, p in plans.items()},
            "boards": {fmt: str(BOARDS / style / f"board-{fmt}.json") for fmt in FORMATS}, "sound": reel["board"]["sound"],
            "hash": board_hash({fmt: p["board"] for fmt, p in plans.items()})}
    _env.write_json("film.json", film)
    say(style, plans, bad, src.get("seconds"))
    print(f"{style} at {bpm:g} bpm ({why}) -> film.json; next: storyboard.py sheets (the boards are at the new tempo)")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    a = ap.parse_args()
    _env.enter_run()
    try:
        return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)
    except ValueError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    sys.exit(main())
