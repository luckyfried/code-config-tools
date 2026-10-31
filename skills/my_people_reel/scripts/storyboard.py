#!/usr/bin/env python3
"""Movement 2: the three boards, their sheets, and the step that sets the picked one on the music's tempo.

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/storyboard.py draft [--style ID]   # R/storyboards/<style>/storyboard.json + storyboard.md for each
                                             # of the three looks; a new draft starts a new vote and a new snap
                                             # (winner.json, vote/scores.json, film.json and the boards' sheets go)
    python3 S/scripts/storyboard.py check    # each board laid out 9:16, 1:1 and 16:9, and the three against their
                                             # style cards (exit 1 on a problem)
    python3 S/scripts/storyboard.py sheets   # R/storyboards/<style>/frames/ and sheet.png, sheet-square.png,
                                             # sheet-wide.png, and out/boards.png, the three looks one over another
    python3 S/scripts/storyboard.py snap     # the picked board (winner.json) at the music's tempo -> R/film.json

The film is "tagged": the tag that marks each of the account's people in its photographs finds them one by one, in the
order taste.json lists them, and the year's cut of each closes into one wall of them (board_drive.py says how). The
story is the same in every look; a look is a style card (styles/<id>.json, named in one sentence in styles/catalog.md)
and supplies the faces, colors, moves, cuts, finish, closer and music. The three looks are the style taste.json names
(`style`, or --style) and the two of scrapbook, analog-home-movie and kinetic-type that differ most from it, or those
three when none is named; storyboards/looks.json keeps their order, A first.

The draft is read from the run: people.json (who, in what order, their own lines), taste.json (the order the agent
settled, and each person's moment: where and when the photograph of the two of them was taken), cast.json and
public/matched/ (each person's photographs, matched to one light). A storyboard.json is format-free: beats that name a
composition, a person and one of their own lines, each with a length in pulses (beats of the tempo), and the style it
is drawn in. The agent may edit it (order, lengths, which of their own lines) and runs check. storyboard.md carries,
per beat, what its move reveals and what it carries across the cut, the music (its origin, the person's music brief and
the loudness of the bed and the effects music.py master mixed), the sound cues and the generated shots the film asks
for; once the board is snapped its length, its tempo and every time in it are the film's, at the tempo the music plays
at, and music.py master writes it again with the mix.

check lays each board out in all three formats and refuses: type outside the format's safe area (on a card, as the
camera's lens sees type standing in front of the photograph) or under its edge onto the photograph, type under 28 px
cap height, a line of type running into another, a tag outside the safe area or into the type, type or a tag over the
face the cast names, a print on the wall that cuts its face, shows less than half of its photograph's shorter side or
has type over its face, a closer with no wall that lays out (a FAIL line naming the photographs to change in
cast.json), a line that is not one of that person's own (or the account's replies to them), a person in no beat, and a
first event later than frame 30. It also refuses three boards whose styles share more than two of the six axes, a face
not in the board's card, a move or transition outside the card's allowlist, a color the card's palette rule did not
make from the photographs, every shot within 10 % of one length, and the same move on two beats in a row; each refusal
names the board and the rule.
sheets renders the hook, the densest beat and the closer at rest in each format; the old sheets go before the first
frame renders and sheet.png, the index of a board's sheets, is tiled after the others, so a sheets stopped on the way
leaves no sheet.png. out/boards.png puts the three reel sheets one over another, each under its look's name and its
one sentence, set in that look's own faces: the picture the person is shown to choose a look from. snap cuts only the
picked board (R/winner.json) and refuses with no pick; it writes R/film.json: the storyboard with the tempo it is cut
at (the music's, folded by halves or doubles to the board's own) and the downbeat the music starts on.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import boards  # noqa: E402
import style as S  # noqa: E402

FORMATS = ("reel", "square", "wide")
HOOK = 30


LOOKS = Path("storyboards") / "looks.json"


def sb_path(style):
    return Path("storyboards") / style / "storyboard.json"


def looks(named=None):
    """The run's three looks, A first: the ones the last draft wrote, else the trio for the named style (taste.json's
    `style` when none is passed)."""
    kept = _env.read_json(LOOKS)
    if kept and not named:
        return tuple(kept["looks"])
    return S.trio_for(named or (_env.read_json("taste.json") or {}).get("style"))


def own_lines(p):
    """Every line a person may say on screen: their own comments and captions people.json carries, and the person's
    replies to them."""
    raw = p.raw
    out = set(p.replies.values())
    out |= {x.get("text") for x in raw.get("lines", []) if x.get("text")}
    out |= {(raw.get("line") or {}).get("text")}
    for x in raw.get("exchanges", []):
        out |= {x.get("they"), x.get("own")}
    return {boards.said(t) for t in out} - {None}


def problems(sb, ctx, bpm=None):
    """[(where, message)] for one storyboard at `bpm` (its own when unset); an empty list passes."""
    out = []
    for b in sb["beats"]:
        p = ctx.by.get(b.get("person"))
        if b.get("person") and not p:
            out.append((b["id"], f"{b['person']} is not one of this film's people"))
        line = b.get("of") or b.get("line")   # a sentence carried over a cut names the whole sentence in "of"
        if b.get("of") and b.get("line") not in b["of"]:
            out.append((b["id"], f"{b['line'][:40]!r} is not part of the sentence it carries"))
        if line and p and line not in own_lines(p) and line not in {r for q in ctx.people for r in q.replies.values()}:
            out.append((b["id"], f"{line[:40]!r} is not one of {p.handle}'s own lines in people.json"))
    named = {b.get("person") for b in sb["beats"]}
    for h in sb.get("people", []):
        if h not in named:
            out.append(("film", f"{h} is in no beat"))
    m = boards.builder()
    for kind in FORMATS:
        try:
            board = boards.layout(sb, ctx, kind, bpm)
        except m.Unfit as e:
            out.append((kind, str(e)))
            continue
        found = m.problems(board)
        out += [(f"{kind} {bid}", msg) for bid, msg in found]
        if kind == "reel":
            hook = boards.hook_frame(board)
            if hook > HOOK:
                out.append(("hook", f"the first event lands at frame {hook}, after frame {HOOK}"))
    return out


def summary(sb, ctx, bpm=None):
    board = boards.layout(sb, ctx, "reel", bpm)
    cpm, secs = boards.cuts_per_minute(board)
    return {"seconds": round(secs, 2), "beats": len(board["beats"]), "cuts_per_minute": cpm, "hook_frame": boards.hook_frame(board),
            "roles": {k: board["beats"][i]["id"] for k, i in boards.roles(board).items()}}


def markdown(sb, ctx):
    bpm = (_env.read_json("film.json") or {}).get("bpm") or sb["bpm"]
    s = summary(sb, ctx, bpm)
    pulse = 60 / bpm
    L = [f"# {S.card(sb['style'])['name']}: {sb['name']}", "", sb["idea"], "",
         f"{s['seconds']:.1f} s at {bpm:g} bpm, {s['beats']} beats, {s['cuts_per_minute']} cuts a minute, the first event at "
         f"frame {s['hook_frame']}. People, in order: " + ", ".join(f"@{h}" for h in sb["people"]) + ".", "",
         "The swap test reads the hook (" + s["roles"]["hook"] + "), the densest beat (" + s["roles"]["dense"] + ") and the closer ("
         + s["roles"]["closer"] + "): frames/hook-reel.png, dense-reel.png, closer-reel.png after `storyboard.py sheets`.", "",
         "| # | beat | composition | person | seconds | where and when | the photograph | their words |", "|---|---|---|---|---|---|---|---|"]
    for i, b in enumerate(sb["beats"], 1):
        words = b.get("line") or b.get("mark") or b.get("credit") or ""
        p = ctx.by.get(b.get("person"))
        L.append(f"| {i} | {b['id']} | {b['comp']} | {('@' + b['person']) if b.get('person') else ''} | {b['pulses'] * pulse:.2f} | "
                 f"{p.stamp if p else ''} | {(p.what or '') if p else ''} | {words} |")
    L += ["", "Each person's still is the settled frame of their beat: " + ", ".join(f"@{h} {bid}" for h, bid in sb["cards"].items()) + "."]
    board = boards.layout(sb, ctx, "reel", bpm)
    L += ["", "## What each move reveals and carries", ""]
    for i, b in enumerate(board["beats"], 1):
        L.append(f"{i}. **{b['id']}** reveals {b['reveals']}. It carries {b['carries']}.")
    track = _env.read_json("music.json") or {}
    cues = board.get("sound") or []
    mixed = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {track['bed_lufs'] - track['fx_lufs']:.1f} LU under; "
             f"{track.get('sound_cues')} sound cues over {s['beats']} beats" if "fx_lufs" in track else "not yet; music.py master writes the bed's and the effects' loudness here")
    L += ["", "## Music", "", "Music: " + (track.get("origin") or "none yet (music.py find)") + ".",
          "The music brief (taste.json `music`): " + json.dumps((_env.read_json("taste.json") or {}).get("music"), ensure_ascii=False) + ".",
          f"Mixed: {mixed}."]
    L += ["", f"## Sound: {len(cues)} cues, where each beat lands (music.py synthesises each and mixes it under the bed)", "",
          "| at (s) | beat | cue | what |", "|---|---|---|---|"]
    for c in sorted(cues, key=lambda c: c["at"]):
        L.append(f"| {c['at'] * pulse:.2f} | {c['beat']} | {c['kind']} | {c['what']} |")
    clips = board.get("clips") or []
    L += ["", f"## Clips: the {len(clips)} generated shots the film asks for (clips.py list writes them for the video model after the cut)", "",
          "| # | beat | what it is | seconds | the request |", "|---|---|---|---|---|"]
    for c in clips:
        L.append(f"| {c['id']} | {c['beat']} | {c['role']} | {c['seconds']} | {c['prompt']} |")
    return "\n".join(L) + "\n"


def cmd_draft(a):
    if not Path("taste.md").exists():
        sys.exit("taste.md is missing from the run folder: write the taste profile (movement 1) before storyboards")
    # the vote judged the boards it was shown and film.json is the winner cut to the music, so a board drafted again
    # is voted and snapped again
    for old in (Path("winner.json"), Path("vote/scores.json"), Path("film.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new vote (vote.py ballot and tally, then pick) and snap")
    styles = S.trio_for(a.style or (_env.read_json("taste.json") or {}).get("style"))
    ctx = boards.Ctx()
    bad = 0
    for t in styles:
        sb = boards.draft(t, ctx)
        # the board's sheets, frames and check were made from the board before, so they go with it: the folder is
        # renamed away in one step before anything in it is deleted
        d, gone = sb_path(t).parent, _env.part(sb_path(t).parent)
        shutil.rmtree(gone, ignore_errors=True)
        if d.exists():
            os.replace(d, gone)
        shutil.rmtree(gone, ignore_errors=True)
        _env.write_json(sb_path(t), sb)
        try:
            _env.write_text(sb_path(t).parent / "storyboard.md", markdown(sb, ctx))
            s = summary(sb, ctx)
        except boards.builder().Unfit as e:
            print(f"FAIL  {t}: {e}")
            bad += 1
            continue
        print(f"{t}: {sb['name']}: {len(sb['people'])} people ({', '.join(sb['people'])}), {s['beats']} beats, {s['seconds']:.1f} s, "
              f"{s['cuts_per_minute']} cuts a minute -> {sb_path(t)}")
    _env.write_json(LOOKS, {"looks": list(styles)})
    return 1 if bad else 0


def load(t):
    sb = _env.read_json(sb_path(t))
    if not sb:
        sys.exit(f"{sb_path(t)} is missing: run storyboard.py draft first")
    return sb


def cmd_check(a):
    ctx = boards.Ctx()
    bad = 0
    laid = {}
    for t in looks():
        sb = load(t)
        ps = problems(sb, ctx)
        try:
            s = summary(sb, ctx)
            _env.write_text(sb_path(t).parent / "storyboard.md", markdown(sb, ctx))
            laid[t] = boards.layout(sb, ctx, "reel")
        except boards.builder().Unfit:
            s = {}
        _env.write_json(sb_path(t).parent / "check.json", {"pass": not ps, **s, "problems": [f"{w}: {m}" for w, m in ps]})
        print(f"{'PASS' if not ps else 'FAIL'}  {t}: {len(ps)} problems")
        for w, m in ps[:40]:
            print(f"    {w}: {m}")
        bad += len(ps)
    import palette
    swatches = palette.swatches_of(_env.read_json("taste.json") or {}, _env.read_json("palette.json") or {})
    against = S.findings(laid, swatches) if laid else []
    print(f"{'PASS' if not against else 'FAIL'}  the three against their style cards: {len(against)} problems")
    for x in against:
        print(f"    {x}")
    return 1 if bad or against else 0


def tile(run, files, out):
    ff = _env.ffmpeg()
    args = [x for f in files for x in ("-i", str(f))]
    run.spawn([ff, "-y", "-v", "error", *args, "-filter_complex", f"hstack=inputs={len(files)}", "-frames:v", "1", str(_env.part(out))],
              check=True)
    os.replace(_env.part(out), out)


def cmd_sheets(a):
    import studio
    # the run's lock is taken before the command writes anything into the run, and held until it ends
    with studio.lock("sheets") as run:
        return sheets(a, studio, run)


def sheets(a, studio, run):
    ctx = boards.Ctx()
    jobs, sheets = [], []
    styles = looks()
    for t in styles:
        sb = load(t)
        d = sb_path(t).parent / "frames"
        d.mkdir(parents=True, exist_ok=True)
        for kind in FORMATS:
            board = boards.layout(sb, ctx, kind)
            row = []
            for role, i in boards.roles(board).items():
                f = d / f"{role}-{kind}.png"
                jobs.append(studio.still(board, boards.rest_frame(board, i), f, scale=0.5))
                row.append(f)
            sheets.append((t, row, sb_path(t).parent / ("sheet.png" if kind == "reel" else f"sheet-{kind}.png")))
    # a sheet speaks for the frames it was tiled from, so every sheet goes before the first frame is drawn again
    for _, _, out in sheets:
        out.unlink(missing_ok=True)
    rep = studio.render(jobs, "sheets", run)
    for f in rep.get("findings", []):
        print("finding:", f["text"][:300])
    # sheet.png is the index of a board's sheets (vote.py and out/boards.png read it), so it is tiled last, and only
    # when every other format of that board was tiled
    for t in styles:
        mine = [(row, out) for look, row, out in sheets if look == t]
        if not all(f.exists() for row, _ in mine for f in row):
            continue
        for row, out in sorted(mine, key=lambda r: r[1].name == "sheet.png"):
            tile(run, row, out)
    print(f"{len(jobs) - rep.get('failed', 0)} of {len(jobs)} frames in {rep.get('seconds', 0):.0f} s; sheets: "
          + ", ".join(str(o) for _, _, o in sheets))
    if rep.get("failed") or not all(sb_path(t).parent.joinpath("sheet.png").exists() for t in styles):
        return 1
    print(f"the three looks one over another -> {boards_png(styles)}")
    return 0


def boards_png(styles):
    """out/boards.png: the three reel sheets one over another, each under its look's letter, name and one sentence,
    set in that look's own display and text faces."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFont
    skill = Path(__file__).resolve().parent.parent
    sheets = [Image.open(sb_path(t).parent / "sheet.png").convert("RGB") for t in styles]
    w = max(im.width for im in sheets)
    head = 120
    out = Image.new("RGB", (w, sum(im.height + head for im in sheets)), "#ffffff")
    d = ImageDraw.Draw(out)
    y = 0
    for letter, t, im in zip("ABC", styles, sheets):
        c = S.card(t)
        big = ImageFont.truetype(str(skill / c["faces"]["display"]["file"]), 44)
        small = ImageFont.truetype(str(skill / c["faces"]["text"]["file"]), 24)
        d.text((16, y + 14), S.cased(f"{letter}. {c['name']}", c["faces"]["display"]), fill="#111111", font=big)
        d.text((16, y + 76), S.cased(S.sentence(t), c["faces"]["text"])[:160], fill="#444444", font=small)
        out.paste(im, (0, y + head))
        y += im.height + head
    dst = Path("out") / "boards.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = _env.part(dst)
    out.save(tmp, "PNG")
    os.replace(tmp, dst)
    return dst


def fold(bpm, target):
    """The music's tempo halved or doubled to the one nearest the board's own."""
    best = bpm
    for k in (0.25, 0.5, 1, 2, 4):
        c = bpm * k
        if abs(c / target - 1) < abs(best / target - 1):
            best = c
    return best


def cmd_snap(a):
    look = (_env.read_json("winner.json") or {}).get("board")
    if look not in looks():
        sys.exit("no look picked: run vote.py ballot and tally, then vote.py pick")
    sb = load(look)
    music = _env.read_json("music.json") or {}
    bpm, start = sb["bpm"], 0.0
    if music.get("bpm"):
        bpm = round(fold(music["bpm"], sb["bpm"]), 3)
        downs = [d for d in music.get("downbeats") or [] if d >= 0]
        start = downs[0] if downs else 0.0
    ctx = boards.Ctx()
    ps = problems(sb, ctx, bpm)
    s = summary(sb, ctx, bpm)
    _env.write_json("film.json", {"style": look, "name": sb["name"], "bpm": bpm, "board_bpm": sb["bpm"], "music_start": round(start, 3),
                                  "seconds": s["seconds"], "storyboard": sb,
                                  "storyboard_sha": hashlib.sha256(json.dumps(sb, sort_keys=True).encode()).hexdigest()[:16]})
    print(f"{look}: {s['beats']} beats at {bpm} bpm (the board's {sb['bpm']}), {s['seconds']:.1f} s, {s['cuts_per_minute']} cuts a minute, "
          f"the music from {start:.2f} s -> film.json")
    for w, m in ps:
        print(f"    {w}: {m}")
    if ps:
        print("the film does not pass at this tempo: make a bed in the board's tempo (music.py make --bpm "
              f"{sb['bpm']}) or place a track nearer {sb['bpm']} bpm, then snap again")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("--style", help="draft: the look the person named (a style id); the other two are the two of the "
                                    "trio that differ most from it")
    a = ap.parse_args()
    _env.enter_run(again=a.cmd in ("draft", "snap"))
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
