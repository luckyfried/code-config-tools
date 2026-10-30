#!/usr/bin/env python3
"""Movement 2, the storyboard: the posts as gather and research left them, made into the drive storyboard, checked
against the rules every film keeps, and shown as styleframes for the vote. Movement 4 calls `snap`.

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/storyboard.py draft    # frames the posts, writes three boards, one per style:
                                             # RUN/storyboards/<style>/storyboard.json + .md; a new draft starts a
                                             # new vote (winner.json, vote/scores.json, film.json and
                                             # storyboards/check.json go)
    python3 S/scripts/storyboard.py check    # the rules, on every board in every format -> RUN/storyboards/check.json
    python3 S/scripts/storyboard.py sheets   # each board's rest moments, and the three looks side by side in
                                             # RUN/out/boards.png
    python3 S/scripts/storyboard.py snap     # the picked board (winner.json) with its music -> RUN/film.json

draft reads RUN/subject.json (timeline.py), RUN/library.json (the name and handle) and RUN/taste.json (the film's
words, as the agent curated them), and refuses to run before RUN/taste.md exists or while taste.json has no moments.
The builder decides, from the posts and the curated words:
  the timeline   the posts with a date, oldest first. A post without a date is left out and named in storyboard.md;
                 fewer than two dated posts, or every post on one day, is no before-and-after: draft exits 2 with
                 the sentence to tell the person, and no board is written.
  the facts      day one and the latest, the span in days and in months (months only from two on), the span as a
                 caption says it and the count of posts, all on paper; and `said`, taste.json's `said_span`, their own
                 words for the span ("fourteen months in"), which the closer sets when they have them; and `music`,
                 taste.json's music brief, which the music engine composes from. The only numbers on screen are the
                 dates and the numbers in their curated words.
  the words      each post's line and, on a chapter, its next line: taste.json's moment for its photograph, matched by
                 the photograph's path. A post no moment names, or whose moment has no line, is wordless.
  the milestones timeline.py's rule: a post between the first and the latest whose caption says milestone, first,
                 finally, sold, proud or an ordinal (100th); only when fewer than two say so do the largest visible
                 steps join, up to three. Day one, the milestones and the latest are the film's chapters: they hold
                 longest, their next line rising under their line.
  the length     taste.json `seconds`, the length the person asked for, made as near as these photographs make
                 well (drive.lengths: each seen and its words read at the least, each at its longest hold at the
                 most, never past 60 s); every hold scales to it by what its photograph carries. With no ask the
                 film runs at its own pace. An ask outside the range is made at the nearest end of it, and draft
                 prints one plain line with the length made and why (length_said). When every word read at its least
                 runs past 60 s, ordinary posts' lines are left off (drive.told) and draft names those posts; day one,
                 the milestones and the latest keep every word. A set whose prints alone need more than 60 s is not
                 delivered: draft prints "not delivered: ", exits 2 and writes no board.
  the closer     their words for the span or their two dates, and the ask: taste.json `call_to_action` when they
                 asked for one, and their handle when they did not, in the style's closer shape.
  the look       the style: taste.json `style` when the person named a look (an id in styles/, which
                 styles/catalog.md describes), and with it the two styles of the trio that differ most from it; with no
                 named look, the trio (compose.TRIO). The style's palette rule makes the colors from their palette and
                 their likes (`look`, from taste.json); `taste` is the digest of taste.json the board was drafted from:
                 film.py refuses a board drafted from another taste.json, so a change to it reaches the film.
  the board      scripts/tones/drive.py: the wall, a grid of tiles in calendar order with day one, the peak and the
                 latest twice the size, crossed by a bare course the closer's words are set on; per post its print at
                 its station (its photograph at its own proportions above a paper label that carries their line and
                 its date, so no word sits on a photograph), the camera's path into it (from the step it crosses, never
                 the same path twice running), the style's move over it and the style's cut into it (each chosen from
                 what the beat is, within the style card's allowlists), every hold as long as its photograph carries
                 and the peak longest; the whole wall with their first and latest dates and the ask on the course; the
                 style's closer with their words for the span; a sound cue where each beat lands, the six clip
                 requests made from each photograph's own measures, and per beat its photograph, their line, what the
                 move reveals and what it carries across the cut.
Each board is laid out for reel (9:16) and again for square and landscape from the same posts.

check refuses, on the board in every format:
  type       a line a person reads under 28 px cap height on screen, at its card's station or on the closer's wall
  safe       type outside the format's safe lines where it is seen, with the camera pushed in to the end of its
             card's hold and the operator's hand at its furthest
  inset      type nearer its print's edge than drive.INSET
  over       type on its photograph instead of its label
  edge       a print that covers its station's frame edge to edge, so the wall does not show
  wall       a station whose frame reaches past the wall's edge
  course     a closer line that reaches off the course onto the tiles
  numbers    a number on screen that is not a date or a number in their curated words
  beats      a first event later than frame 30
and, across the three boards (each finding names the board and the rule): two styles that share more than two of the
six axes; a face that is not the board's card's; a move or a cut outside the card's allowlist; a color the card's
palette rule did not make from the photographs; every shot within 10 % of one length; words in one place of the frame
on more than 70 % of the beats that carry words; the same move on two beats in a row.
sheets renders each board's rest moments (RUN/storyboards/<style>/frames/{hook,ordinary,dense,closer,end}.png) and its
sheet.png, then RUN/out/boards.png: the three boards side by side, each its hook, its densest beat and its closer at
half size, with the style's name and one plain sentence under it. The person picks a look from it.
snap reads RUN/music.json (music.py make, which composes at the board's tempo): RUN/film.json carries the board, the
seconds and the music's start and tempo.
"""
import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
from timeline import milestones, span_of  # noqa: E402

# the story every board tells, whatever its style
STORY = ("one camera walks the wall they built, from day one to the latest, in chapters told in their own captions: each "
         "photograph lifts out of the wall as a print with their line entering under it, day one, every milestone and the "
         "latest holding longest with their next line under it, the peak longest of all, then drops back into its tile, so "
         "every photograph adds up, in calendar order, to the wall the film ends on")


def look_said(style):
    """The style's name and the one plain sentence styles/catalog.md says it in, for the person."""
    for row in (compose.STYLES / "catalog.md").read_text().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if cells and cells[0] == style and len(cells) > 1:
            return style.replace("-", " ").capitalize(), cells[1]
    return style.replace("-", " ").capitalize(), ""

FRAMES = ("hook", "ordinary", "dense", "closer", "end")
# the rest moments boards.png shows for each look: how it opens, its densest beat, how it ends
SHOWN = ("hook", "dense", "end")


class Refusal(Exception):
    """The posts make no before-and-after; the message is the sentence to tell the person."""


def dated(posts):
    """The posts with a date, oldest first, and the ones without."""
    have = sorted((p for p in posts if p.get("date")), key=lambda p: p["date"])
    return have, [p for p in posts if not p.get("date")]


def facts(posts):
    """The build's facts, computed from the dated posts (framing.py's rows): its first and latest dates, its span and its posts."""
    if len(posts) < 2:
        raise Refusal("A before-and-after needs at least two dated posts of the subject, and there "
                      + ("is one." if len(posts) == 1 else "are none.") + " Ask for more photos of it, or a different subject.")
    first, latest = posts[0], posts[-1]
    sp = span_of(date.fromisoformat(first["date"]), date.fromisoformat(latest["date"]))
    if sp["days"] < 1:
        raise Refusal("Every post of the subject is from the same day, so there is no before and after yet.")
    return {"first": first["date"], "latest": latest["date"], "days": sp["days"], "months": sp["months"] if sp["months"] >= 2 else None,
            "label": sp["label"], "count": len(posts)}


def told(posts, moments):
    """Each post's words from taste.json's curated `moments`, matched by its photograph's path: its `line` and, on a
    chapter, its `next`. A post no moment names, or whose moment has no line, is wordless."""
    by = {m.get("photo"): m for m in moments if isinstance(m, dict)}
    for p in posts:
        m = by.get(p.get("src") or p.get("photo")) or {}
        p["line"] = (m.get("line") or "").strip()
        p["next"] = (m.get("next") or "").strip() if p["line"] else ""
    return posts


def person(lib):
    lib = lib or {}
    h = (lib.get("handle") or "").strip()
    return {"name": lib.get("name") or h or "", "handle": ("@" + h.lstrip("@")) if h else ""}


# ------------------------------------------------------------------ timing and checks
def frames_of(b):
    return b["frames"]


def starts(board):
    out, s = [], 0
    for b in board["beats"]:
        out.append(s)
        s += frames_of(b)
    return out, s


def hook_frame(board):
    """The frame of the film's first event: the opening's first word when the film opens on their words, else day
    one's photograph landing (as the board's check reads it)."""
    f = board["film"]
    return 0 if f.get("opening") else round(f["cards"][0]["arrive"] * f["pulse"])


def taste_sha():
    """The digest of RUN/taste.json as it stands, which the board carries (facts `taste`)."""
    import hashlib
    p = _env.b("taste.json")
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def look_of(taste):
    """The colors their style's palette rule reads, from taste.json: their palette's colors and their likes' colors."""
    pal = taste.get("palette") or {}
    hexes = lambda xs: [c["hex"] for c in xs or [] if isinstance(c, dict) and c.get("hex")]
    return {"palette": hexes(pal.get("subject")), "likes": hexes(pal.get("likes"))}


def allowed_numbers(fx, posts):
    """The numbers they would say: each post's date and the numbers in their curated words (their lines, their next
    lines and their words for the span) and in the call to action they asked for."""
    ok = set(re.findall(r"\d+", f"{fx.get('said') or ''} {fx.get('call_to_action') or ''}"))
    for p in posts:
        d = date.fromisoformat(p["date"])
        ok |= {str(d.day), str(d.year)}
        ok |= set(re.findall(r"\d+", f"{p.get('line') or ''} {p.get('next') or ''}"))
    return ok


def words_of(board):
    """Every line of type the film sets: each card's line, date and next line, the peak's line its type mask sets, the
    opening's words, the dates and the ask on the course, and the closer's words."""
    film = board["film"]
    out = []
    for c in film["cards"]:
        out += [ln["text"] for ln in c["title"]] + [c["dateLine"]["text"]] + [ln["text"] for ln in c["rest"]] + ([c["mask"]] if c.get("mask") else [])
    out += [film["timeline"]["beats"][0]["words"]] + [ln["text"] for ln in film["closer"]["lines"]]
    return out + [v for v in (film["look"].get(k) for k in ("title", "signoff", "handle")) if v]


def check_board(board, posts, fx):
    """Every rule on one laid-out board; the findings as sentences."""
    from tones import drive
    return drive.check(board, posts, allowed_numbers(fx, posts), board["system"]["safe"][board["format"]["name"]])


def style_findings(boards):
    """The template tells and style breaks a set of boards (reel layouts) has, each one plain sentence naming the board
    and the rule: two styles that share more than two of the six axes; a face not in the board's card; a move or a cut
    outside the card's allowlist; a color the card's palette rule did not make from the photographs; every shot within
    10 % of one length; words in one place of the frame on more than 70 % of the beats that carry words; the same move
    on two beats in a row. A beat with no move is the print and the camera alone, and a beat with no cut is the film's
    first."""
    import palette
    out = []
    for i, a in enumerate(boards):
        for b in boards[i + 1:]:
            same = compose.shared_axes(a["style"], b["style"])
            if len(same) > 2:
                out.append(f"boards {a['style']} and {b['style']} share {len(same)} of the six axes ({', '.join(same)}), more than two")
    for b in boards:
        n, c, s = b["style"], compose.card(b["style"]), b["system"]
        for k in ("display", "text"):
            if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
                out.append(f"board {n}: its {k} face {s[k]['family']} is not its card's ({c['faces'][k]['family']})")
        beats = b["film"]["timeline"]["beats"]
        moves, cuts = compose.ids(c, "moves"), compose.ids(c, "transitions")
        for bt in beats:
            if bt["move"] is not None and bt["move"] not in moves:
                out.append(f"board {n}: beat {bt['id']} moves by {bt['move']!r}, which is not a move of {n}")
            if bt["transition"] is not None and bt["transition"] not in cuts:
                out.append(f"board {n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {n}")
        made = set(palette.palette_of(c["palette"], compose.swatches_of(b["facts"].get("look")))["made"])
        shown = {v.lower() for k, v in s["colors"].items() if k != "swatches"} | {v.lower() for v in b["film"]["colors"].values()}
        for h in sorted(shown - made):
            out.append(f"board {n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {n} did not make from the photographs")
        lengths = sorted(bt["end"] - bt["at"] for bt in beats if bt["form"] == "photo")
        if len(lengths) >= 3:
            mid = lengths[len(lengths) // 2]
            if all(abs(x - mid) <= 0.1 * mid for x in lengths):
                out.append(f"board {n}: every shot runs within 10 % of {mid:.1f} beats")
        cells = anchors(b)
        if len(cells) >= 3:
            top = max(set(cells), key=cells.count)
            if cells.count(top) > 0.7 * len(cells):
                where = ("top", "middle", "bottom")[top[1]] + " " + ("left", "center", "right")[top[0]]
                out.append(f"board {n}: the words sit in one place, the {where} of the frame, on {cells.count(top)} of the {len(cells)} beats that carry words")
        for x, y in zip(beats, beats[1:]):
            if x["move"] and x["move"] == y["move"]:
                out.append(f"board {n}: beats {x['id']} and {y['id']} both move by {x['move']}; two beats in a row move differently")
    return out


def anchors(b):
    """Per beat that carries words, the third of the frame across and down the middle of its words stands in, on the
    reel's screen at the beat's rest: each print's label at its station, then the course on the whole wall."""
    W, H = b["format"]["width"], b["format"]["height"]
    out = []

    def cell(x, y):
        return min(2, max(0, int(3 * x / W))), min(2, max(0, int(3 * y / H)))
    for c in b["film"]["cards"]:
        lines = [c["dateLine"]] + c["title"] + c["rest"]
        st = c["station"]
        k = H / st["h"]
        xs = [(ln["x"] - st["c"][0]) * k + W / 2 for ln in lines]
        ys = [(ln["y"] - st["c"][1]) * k + H / 2 for ln in lines]
        if c["title"]:
            out.append(cell((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    lines = b["film"]["closer"]["lines"]
    if lines:
        out.append(cell(W / 2, sum(ln["y"] for ln in lines) / len(lines)))
    return out


# ------------------------------------------------------------------ the commands
def measured():
    m = _env.read_json(_env.b("public", "matched", "measure.json"))
    if not m:
        sys.exit("RUN/public/matched/measure.json is missing: run storyboard.py draft first")
    return m["posts"]


def boards_dir():
    return _env.b("storyboards")


def write_md(board, fx, left_out, path, passed=()):
    """One board's storyboard: per beat its photograph, their line, the style's move and cut, what the move reveals and
    what it carries across the cut, the music, the sound cues and the clips."""
    title, idea = board["title"], board["idea"]
    secs = sum(b["frames"] for b in board["beats"]) / compose.FPS
    chapters = "; ".join(f"\"{sc['line']}\" ({c['date']})" for c, sc in zip(board['film']['cards'], board['scenes']) if c['kind'] != "ordinary" and sc["line"])
    lines = [f"# {board['style']}: {title}", "", idea + ".", "",
             f"{len(board['beats'])} beats at {board['bpm']:g} bpm, {secs:.1f} s; picture and music stop together at beat "
             f"{board['film']['closer']['still']:.2f} and the {board['film']['shape']} closer holds silent to the end. From {fx['first']} to {fx['latest']}"
             + (f", the span in their words: \"{fx['said']}\"" if fx.get('said') else "") + (f"; the chapters: {chapters}" if chapters else "") + ".", ""]
    if left_out:
        lines += [f"Left out: {len(left_out)} posts without a date ({', '.join(p.get('id', '?') for p in left_out)}).", ""]
    if passed:
        lines += [f"Left out of this look: {posts(len(passed))}, so the film runs inside 60 s ({', '.join(passed)}).", ""]
    if board["film"]["unsaid"]:
        lines += [unsaid_said(board["film"]["unsaid"]), ""]
    moves = {bt["id"]: bt for bt in board["film"]["timeline"]["beats"]}
    lines += ["| beat | frames | photograph | their line | move | cut into it | the move reveals | it carries across the cut |",
              "|---|---|---|---|---|---|---|---|"]
    for b, sc in zip(board["beats"], board["scenes"]):
        bt = moves.get(b["id"]) or moves["closer" if b["id"] == "closer" else board["film"]["cards"][0]["id"]]
        lines.append(f"| {b['id']} | {b['frames']} | {sc['photo']} | {sc['line'] or '(no words)'} | {bt['move'] or '(none)'} | "
                     f"{bt['transition'] or '(none)'} | {sc['reveals']} | {sc['carries']} |")
    lines += ["", "## Music", "", "Music: not yet; music.py make writes where the track came from here.",
              "The music brief (taste.json `music`): " + json.dumps(fx.get("music"), ensure_ascii=False) + ".",
              "Mixed: not yet; music.py master writes the bed's and the effects' loudness here.",
              "", "## Sound cues", "", f"Where each beat lands (the music engine makes each effect in the style's recipe and "
              f"music.py master mixes it under the bed; {sum(1 for c in board['sound'] if c['kind'] != 'stop')} cues, then the stop):", "",
              "| beat | at (beats) | cue | what |", "|---|---|---|---|"]
    for c in board["sound"]:
        lines.append(f"| {c['beat']} | {c['at']:.2f} | {c['kind']} | {c['what']} |")
    lines += ["", "## Clips", "", "The six shots an image-to-video model would make (clips.py list writes them as requests for the agent; "
              "until a clip comes back, the still print stands in with its own move):", "",
              "| clip | beat | role | seconds | lens | light | move | prompt |", "|---|---|---|---|---|---|---|---|"]
    for c in board["clips"]:
        lines.append(f"| {c['id']} | {c['beat']} | {c['role']} | {c['seconds']} | {c['lens']} | {c['light']} | {c['move']} | {c['prompt']} |")
    lines += ["", "Rest moments (styleframes and story cards): " + ", ".join(f"{k} frame {v}" for k, v in board["stills"].items()) + "."]
    _env.write_text(path, "\n".join(lines) + "\n")


def styles_of(taste):
    """The three styles a run's boards take (compose.trio), from taste.json `style` when the person named a look."""
    return compose.trio((taste.get("style") or "").strip() or None)


def cmd_draft(a):
    _env.need("PIL")
    # the vote judged the boards it was shown, so boards drafted again are voted again; the cut (film.json, which only
    # snap writes), the rules' findings (check.json, which check writes), the boards (storyboard.json, laid out from the
    # photographs framing makes), their sheets and boards.png named the old boards, so they go before they change, each
    # index before the files it names
    for old in (_env.b("winner.json"), _env.b("vote", "scores.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    for old in (_env.b("film.json"), boards_dir() / "check.json", _env.out("boards.png")):
        old.unlink(missing_ok=True)
    for d in boards_dir().glob("*/"):
        (d / "storyboard.json").unlink(missing_ok=True)
        (d / "sheet.png").unlink(missing_ok=True)
        shutil.rmtree(d / "frames", ignore_errors=True)
    import framing
    sub = _env.read_json(_env.b("subject.json"))
    if not sub:
        sys.exit("RUN/subject.json is missing: run research.py first")
    if not _env.b("taste.md").exists():
        sys.exit("RUN/taste.md is missing: research comes first (S/pipeline/1-research.md says how to write it)")
    taste = _env.read_json(_env.b("taste.json")) or {}
    if not isinstance(taste.get("moments"), list):
        sys.exit("RUN/taste.json has no moments: run research.py, then curate them (S/pipeline/1-research.md)")
    styles = styles_of(taste)
    posts, left_out = dated(told(sub["posts"], taste["moments"]))
    try:
        if len(posts) < 2:
            facts([{"date": p["date"], "milestone": False, "day": 1} for p in posts])
        milestones(posts)
        m = framing.frame(posts, _env.b("public"))
        framing.furnish(_env.b("public"))
        rows = m["posts"]
        fx = facts(rows) | {"said": (taste.get("said_span") or "").strip(), "music": taste.get("music"), "seconds": asked(taste),
                            "call_to_action": (taste.get("call_to_action") or "").strip(), "look": look_of(taste), "taste": taste_sha(),
                            "seed": _env.b().name}
    except Refusal as e:
        print(f"no storyboard: {e}")
        return 2
    from tones import drive
    who = person(_env.read_json(_env.b("library.json")))
    ask, made = fx["seconds"], 0
    for style in styles:
        c = compose.card(style)
        compose.use(style)
        bpm = compose.bpm_of(c, fx["seed"])
        kept, passed = drive.fitting(rows, fx["said"], c, bpm)
        lo, hi = drive.lengths_for(kept, fx["said"], c, bpm)
        if lo > hi:
            print(f"{style}: not delivered: these {len(rows)} photographs need at least {lo:g} s to be seen and read in this look, "
                  f"longer than the {drive.LONGEST:g} s a reel runs.")
            continue
        fb = dict(fx, seconds=min(max(ask, lo), hi) if ask else None)
        b = finished(compose.board(style, kept, fb, who, seed=fx["seed"]), fb)
        d = boards_dir() / style
        d.mkdir(parents=True, exist_ok=True)
        # storyboard.json is the board's completion, so it follows its text
        write_md(b, fb, left_out, d / "storyboard.md", passed)
        _env.write_json(d / "storyboard.json", b)
        made += 1
        secs = starts(b)[1] / compose.FPS
        print(f"{style}: {len(b['beats'])} beats at {b['bpm']:g} bpm, {secs:.1f} s (these photographs make {lo:g} to {hi:g} s in this look) "
              f"-> {d / 'storyboard.md'}")
        said = length_said(secs, ask, len(rows))
        if said:
            print(said)
        if passed:
            print(passed_said(passed, style))
        if b["film"]["unsaid"]:
            print(unsaid_said(b["film"]["unsaid"]))
    if not made:
        print(f"not delivered: these {len(rows)} photographs need more than {drive.LONGEST:g} s to be seen and read in every look.")
        return 2
    return cmd_check(a)


def posts(n):
    """`n` ordinary posts, in words that agree with the count."""
    return f"{n} ordinary post" + ("" if n == 1 else "s")


def passed_said(ids, style):
    """The one plain line naming the ordinary posts a slower look leaves out of its film so it runs inside 60 s."""
    return (f"{posts(len(ids))} {'is' if len(ids) == 1 else 'are'} left out of the {style} film so every photograph it shows is seen inside 60 s: "
            f"{', '.join(ids)}. Day one, the milestones and the latest are always in it.")


def unsaid_said(ids):
    """The one plain line naming the posts whose line the film leaves off so every word it sets is read."""
    return (f"{posts(len(ids))} {'passes' if len(ids) == 1 else 'pass'} over {'its' if len(ids) == 1 else 'their'} date alone, the line left off, so every line the film sets is read "
            f"inside 60 s: {', '.join(ids)}. Curate fewer lines in taste.json to choose which.")


def length_said(seconds, asked, n):
    """The one plain line that says how long the film runs and why, when the person asked for a length these `n`
    photographs cannot make well; None when they asked for none or the film runs the length asked."""
    if not asked or abs(seconds - asked) < 0.5:
        return None
    if seconds < asked:
        return f"You asked for {asked:g} s; these {n} photographs carry at most {seconds:.1f} s, so the film is {seconds:.1f} s."
    return (f"You asked for {asked:g} s; these {n} photographs need at least {seconds:.1f} s to be seen and their words read, "
            f"so the film is {seconds:.1f} s.")


def asked(taste):
    """The reel's length in seconds as taste.json `seconds` carries the person's ask, or None when they named none."""
    x = taste.get("seconds")
    if x in (None, "", 0):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        sys.exit(f"RUN/taste.json seconds is {x!r}: write the length they asked for in seconds (30), or null")


def finished(b, fx):
    """A laid-out board with its title, its idea and its facts (drive.build sets its rest moments)."""
    name, sentence = look_said(b["style"])
    b["title"], b["idea"], b["look_said"] = name, f"{STORY}, in the {name.lower()} look: {sentence[:1].lower() + sentence[1:].rstrip('.')}", sentence
    b["facts"] = fx
    return b


def told_by(b, rows):
    """The posts the board `b` tells, of the measured `rows` (a slower look leaves ordinary posts out)."""
    ids = {c["id"] for c in b["film"]["cards"]}
    return [r for r in rows if r["id"] in ids]


def lay_out(style, fmt="reel"):
    """The style's storyboard in one format: the drafted reel board, or the same posts and facts laid out again for
    square or landscape."""
    stored = _env.read_json(boards_dir() / style / "storyboard.json")
    if not stored:
        sys.exit(f"RUN/storyboards/{style}/storyboard.json is missing: run storyboard.py draft first")
    if fmt == "reel":
        return stored
    who = {"name": stored["name"], "handle": stored["handle"]}
    return finished(compose.board(style, told_by(stored, measured()), stored["facts"], who, fmt, seed=stored["facts"].get("seed", "")),
                    stored["facts"])


def check_all(boards, rows):
    """Every board laid out in every format and checked: {style: {format: [findings]}}, and the findings across the
    boards under "boards"."""
    out = {}
    for b in boards:
        fx = b["facts"]
        who = {"name": b["name"], "handle": b["handle"]}
        mine = told_by(b, rows)
        out[b["style"]] = {}
        for fmt in compose.FORMATS:
            compose.use(b["style"])
            laid = b if fmt == "reel" else compose.board(b["style"], mine, fx, who, fmt, seed=fx.get("seed", ""))
            out[b["style"]][fmt] = check_board(laid, rows, fx)
    out["boards"] = {"all": style_findings(boards)}
    return out


def load_boards():
    """The run's boards in board order (A, B, C as draft made them from taste.json), the order boards.png and the
    review page number them in."""
    order = styles_of(_env.read_json(_env.b("taste.json")) or {})
    bs = sorted((_env.read_json(f) for f in boards_dir().glob("*/storyboard.json")),
                key=lambda b: (order.index(b["style"]) if b["style"] in order else len(order), b["style"]))
    if not bs:
        sys.exit("no storyboards: run storyboard.py draft first")
    return bs


def cmd_check(a):
    _env.need("PIL")
    res = check_all(load_boards(), measured())
    _env.write_json(boards_dir() / "check.json", res)
    n = 0
    for style, by in res.items():
        for fmt, bad in by.items():
            n += len(bad)
            print(f"{style} {fmt}: {'ok' if not bad else str(len(bad)) + ' findings'}")
            for x in bad[:12]:
                print("  -", x)
    print(f"check: {n} findings -> {boards_dir() / 'check.json'}")
    return 0 if n == 0 else 1


def cmd_sheets(a):
    import film
    _env.need("PIL")
    from PIL import Image, ImageDraw
    boards = load_boards()
    jobs = []
    for b in boards:
        d = boards_dir() / b["style"] / "frames"
        for name, f in b["stills"].items():
            jobs.append({"type": "still", "composition": "Film", "props": film.props(b), "frame": f, "out": str((d / f"{name}.png").resolve())})
    with film.held("sheets") as run:
        # a sheet is the index of its styleframes, and boards.png of the sheets' frames: each goes before they render
        # and comes back after all of them
        _env.out("boards.png").unlink(missing_ok=True)
        for b in boards:
            (boards_dir() / b["style"] / "sheet.png").unlink(missing_ok=True)
        rep = film.render_jobs(run, jobs)
        if rep.get("failed"):
            return 1
        for b in boards:
            d = boards_dir() / b["style"] / "frames"
            ims = [Image.open(d / f"{n}.png").convert("RGB") for n in b["stills"]]
            w, h = ims[0].width // 2, ims[0].height // 2
            sheet = Image.new("RGB", (w * len(ims) + 24 * (len(ims) - 1), h), (12, 12, 12))
            for i, im in enumerate(ims):
                sheet.paste(im.resize((w, h), Image.LANCZOS), (i * (w + 24), 0))
            with _env.whole(d.parent / "sheet.png") as tmp:
                sheet.save(tmp, "PNG")
            print(f"{b['style']}: {d}/{{{','.join(b['stills'])}}}.png, sheet {d.parent / 'sheet.png'}")
        # boards.png: one row per look, its hook, its densest beat and its closer at half size, its name and its
        # sentence under them
        rows_ = []
        for i, b in enumerate(boards):
            d = boards_dir() / b["style"] / "frames"
            ims = [Image.open(d / f"{n}.png").convert("RGB") for n in SHOWN]
            w, h = ims[0].width // 2, ims[0].height // 2
            rows_.append((b, [im.resize((w, h), Image.LANCZOS) for im in ims], w, h))
        w, h = rows_[0][2], rows_[0][3]
        pad, under = 24, 120
        out = Image.new("RGB", (pad + len(SHOWN) * (w + pad), len(rows_) * (h + under) + pad), (250, 249, 246))
        draw = ImageDraw.Draw(out)
        for r, (b, ims, _, _) in enumerate(rows_):
            y = pad + r * (h + under)
            for i, im in enumerate(ims):
                out.paste(im, (pad + i * (w + pad), y))
            name = f"{'ABC'[r] if r < 3 else r + 1}. {b['title']}"
            draw.text((pad, y + h + 14), name, fill=(20, 20, 20), font=_env.pil_font(40, "display", style=b["style"]))
            draw.text((pad, y + h + 66), b["look_said"], fill=(80, 80, 80), font=_env.pil_font(28, "text", style=b["style"]))
        _env.out().mkdir(parents=True, exist_ok=True)
        with _env.whole(_env.out("boards.png")) as tmp:
            out.save(tmp, "PNG")
        print(f"the three looks side by side: {_env.out('boards.png')}")
    return 0


def cmd_snap(a):
    style = (_env.read_json(_env.b("winner.json")) or {}).get("board")
    if not style or not (boards_dir() / style / "storyboard.json").exists():
        sys.exit("no pick: run vote.py tally (or vote.py pick <style> when the person chose a look) first")
    b = _env.read_json(boards_dir() / style / "storyboard.json")
    music = _env.read_json(_env.b("music.json")) or {}
    seconds = round(starts(b)[1] / compose.FPS, 3)
    start, tempo, note = 0.0, 1.0, "no music: the film is silent"
    if music.get("recipe"):
        if music.get("board") != style or abs((music.get("bpm") or 0) - b["bpm"]) >= 0.01:
            sys.exit(f"RUN/music.json was composed for {music.get('board')} at {music.get('bpm')} bpm: run music.py make for {style} first")
        note = f"the bed composed for this board at its {b['bpm']:g} bpm, from its first beat"
    elif music.get("file"):
        if not music.get("downbeats"):
            sys.exit("RUN/music.json has no beat grid for the placed track: run music.py analyze first")
        # a placed track starts on its first downbeat and is brought to the board's tempo
        start, tempo = float(music["downbeats"][0]), b["bpm"] / music["bpm"]
        note = f"their track from its first downbeat, its {music['bpm']:g} bpm brought to the board's {b['bpm']:g}"
    _env.write_json(_env.b("film.json"), {"board": style, "seconds": seconds, "bpm": b["bpm"], "music_start": start, "tempo": tempo, "note": note})
    print(f"{style}: {seconds:.1f} s, {note} -> {_env.b('film.json')}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    a = ap.parse_args()
    _env.open_run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
