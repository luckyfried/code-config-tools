#!/usr/bin/env python3
"""Movement 2: the storyboards, the film for the same person drawn as three boards, one per style, and the step that
times the chosen one to the music before it renders.

USAGE (from the workspace root; S = this skill's folder, B = the run's folder, build/<run stamp>/):
    python3 S/scripts/storyboard.py draft            # B/storyboards/{1,2,3}/storyboard.json + storyboard.md, photos graded;
                                                     # a new draft starts a new vote (winner.json and vote/scores.json go)
    python3 S/scripts/storyboard.py check            # every board in every format: the frame, the photos, the words, the
                                                     # cut, the style
    python3 S/scripts/storyboard.py sheets           # every rest moment in 9:16, 1:1 and 16:9: B/storyboards/N/sheet*.png,
                                                     # and the three looks side by side: out/boards.png
    python3 S/scripts/storyboard.py snap             # the winner (B/winner.json) timed to B/music.json -> B/film.json
                                                     # (exit 1, nothing written, while a gate below refuses)

draft plans three boards with compose.py from what gather and research found (shared.json, picks.json, taste.json;
taste.md must exist first). Each is the kit's one story, "the year with you" (scripts/wall.py), in one style card:
the occasion photograph with the age on its line (the name, when the person gave no age), then one card per moment of
the year (taste.json "moments"), its name in the caption's own words landing on the photograph's edge with the line
they wrote or traded under it, the wall, the sheet over the wall with the age cut through it, its last figure punched
home and the wish. The styles are A scrapbook, B analog-home-movie and C editorial-quiet, or, when taste.json names a
`style`, that style and the two of those three that differ most from it. A board is one plan for every format: its
style, its length in seconds (`length`: the one the person asked for, else the photographs' own holds inside 20 to
60 s), its beats, each a form (hook, moment, closer), the post, the moment's name, the words it carries, the move and
the cut into it its card allows for what it holds, and, where the film wants a generated clip, the clip request
(`clip`); a card's `hold` is the seconds its photograph asks for, and the cards share what the hook and the closer
leave of the length in proportion to their holds. compose.py lays it out for 1080x1920, 1080x1080 and 1920x1080, and
its storyboard.md says per beat what the move reveals and what it carries across the cut, the music recipe and the
sound where each beat lands.

check refuses:
  length    the film outside 20 to 60 s, or more than 1 s off the board's `length`, at its tempo
  frame     a line that leaves the format's safe area, a line drawn under 28 px cap height (figure height for
            numerals), a line that crosses under its card's edge, a subject cut by its edge or by the frame, the giant age
            past the frame's margin (in all three formats)
  subject   a placed photograph with no subject box: storyboard.json "photos" carries, per photograph, the box that must
            stay whole under the edge, [x0, y0, x1, y1] in fractions of the photograph: the part the card is about
            (the person and what they hold, the part of a view its caption names, the thing in a still life), never the
            whole print by default. A redraft keeps each photograph's box.
  words     a line of the sender's or theirs that is not one they wrote: every moment's name, caption line and traded
            line is in a caption or a comment of theirs
  photos    a photograph that is not one the two share (picks.json "shared") or was not graded into B/public/graded
  hook      the hook's event after frame 30
  style     a board whose style is not one of the run's three, or a move or a cut its card does not allow

sheets renders the rest moments (the hook, the middle card, the closer) through motion/studio at quarter size, one
sheet per format, and writes each board's storyboard.md again; a font or photograph the page could not load is a
refusal there too. It then renders each board's hook, middle card and closer at half size into out/boards.png, one
row per board with its style's name and one plain sentence on how it looks, and each board's look alone into
B/storyboards/N/look.png. Its type read (B/storyboards/N/type.json) is written last and only by sheets: draft removes
it, and snap and vote.py ballot refuse a board without one.

snap cuts only the board that won the vote or that the person picked (B/winner.json) and refuses with no winner. It
applies the critics' swap gate and check again at the music's tempo, folded into the style's range, and writes
B/film.json with the reel's sound cues (music.py master mixes them) and the clip requests it lists (clips.py). The film
keeps the board's length at that tempo: the hook and the closer keep their beats, so their hits land on the music, and
the cards share the rest by their holds. The cut's figures (its cuts, how still each second is) are read by the critic
beside the preview's strip; none of them passes or fails.
"""
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import grade  # noqa: E402
import studio  # noqa: E402

FPS = 30
FORMATS = ("reel", "feed", "wide")
SHEET_SCALE = 0.25
LOOK_SCALE = 0.5  # the boards image: each look's hook, middle card and closer at half size
REQUEST = ("use", "subject", "move", "lens", "light", "duration", "loop")  # a clip request's parts (motion/system/standards.md)


def boards_dir():
    return Path(_env.B) / "storyboards"


def write_md(b, path):
    """storyboard.md for a board: drafted, at the board's own tempo; for the cut film.json (music.py master writes it), at
    the music's tempo and the film's length, with the music's origin and loudness from music.json."""
    secs = b.get("seconds") or compose.seconds_of(b["beats"], b["bpm"])
    m = _env.read_json(f"{_env.B}/music.json") or {}
    colors = b["colors"]
    card = compose.card(b["style"])
    fin = card["finish"]
    st = compose.lay(b, "reel")
    story = compose.story(b)
    sound = st["sound"]
    L = [f"# storyboard {b['id']}: {b['name']}", "", b["idea"], "",
         f"- for {b['for']} ({b.get('occasion')}), from @{b['handle']}", f"- structure: {b['structure']}", f"- style: {card['name']} ({b['style']}): {compose.name_of(b['style'])[1]}",
         f"- footage: {b['footage']}",
         f"- length: {secs:.1f} s ({b.get('length_from') or 'the board'}) at {b['bpm']} bpm, {len(b['beats'])} beats, rendered at 1080x1920, 1080x1080 and 1920x1080 from the same beats",
         f"- music: {m.get('origin') or 'none yet (music.py make); the ' + b['music']['recipe'] + ' recipe with the brief below'}",
         f"- the music brief (taste.json music): {json.dumps((_env.read_json(f'{_env.B}/taste.json') or {}).get('music'), ensure_ascii=False)}",
         f"- sound: {b['music']['direction']}; {len(sound)} sound cues over {len(b['beats'])} beats, the last a {sound[-1]['kind']} at beat {sound[-1]['at']}",
         "- mixed: " + (f"bed {m['bed_lufs']} LUFS, effects {m['fx_lufs']} LUFS, {m['bed_lufs'] - m['fx_lufs']:.1f} LU under; "
                        f"{len(sound)} sound cues over {len(b['beats'])} beats" if "fx_lufs" in m and b.get("seconds")
                        else "not yet; music.py master writes the bed's and the effects' loudness here"),
         f"- color: ground {colors['bg']}, ink {colors['ink']}, paper {colors['paper']}, accent {colors['accent']}, from the card's "
         f"{card['palette']['rule']} rule over the photographs' colors; grain {fin['grain']}, vignette {fin['vignette']}, closer {card['closer']}",
         f"- stills: the settled frames of {', '.join(b['rest'])}",
         "", "## beats", "", "| # | beat | form | seconds | move | cut in | moment | post | photograph | their words |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, bt in enumerate(compose.fit(b, b["bpm"])["beats"], 1):
        said = " / ".join(t["text"] for t in bt.get("talk") or []) or bt.get("words") or ""
        photo = Path(((b.get("photos") or {}).get(bt.get("post")) or {}).get("file") or "").name
        L.append(f"| {i} | {bt['id']} | {bt['form']} | {bt['pulses'] * 60 / b['bpm']:.2f} | {bt.get('move') or ''} | {bt.get('transition') or ''} | {bt.get('name') or ''}{' (peak)' if bt.get('peak') else ''} | "
                 f"{bt.get('post') or ''} | {photo} | {said[:120]} |")
    L += ["", "## what each move reveals and carries", ""] + [f"- **{k}**: {v}" for k, v in story.items()]
    L += ["", "## clip requests", "", "Each is a request for a video model; until one makes it, the film shows the photograph still.", ""]
    for c in st["clips"]:
        L.append(f"- {c['id']} under {c['beat']}, {c['use']} ({c['duration']} s)" + ("" if c["prompt"] else
                 ": no shot yet: open its photograph and write the beat's \"shot\""))
        L += [f"  - {k}: {c[k]}" for k in REQUEST[1:] if c.get(k)]
    _env.write_text(path, "\n".join(L) + "\n")


def stage_assets():
    """Fonts and the grain tile inside B/public/, the folder the renderer serves, copied on every staging."""
    studio.public()


def cmd_draft(a):
    if not Path(f"{_env.B}/taste.md").exists():
        sys.exit(f"{_env.B}/taste.md is missing: write the taste profile (movement 1) before storyboards")
    # the vote judged the boards it was shown, so a board drafted again is voted again; the render report (it vouches
    # for out/ as the film of one cut), the cut (film.json) and each board's type read (type.json) name the boards as
    # they were, so they go before the first board changes, and only render, snap and sheets write them again
    for old in (Path(_env.B) / "winner.json", Path(_env.B) / "vote" / "scores.json"):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    for old in (studio.render_dir() / "film-report.json", Path(_env.B) / "film.json", *boards_dir().glob("*/type.json")):
        old.unlink(missing_ok=True)
    ctx = compose.Ctx()
    _env.write_json(f"{_env.B}/grade.json", grade.recipe(ctx.taste))
    boards = [compose.finish(ctx, compose.plan(ctx, style), i) for i, style in enumerate(compose.styles_for(ctx.taste), 1)]
    seen = {r["file"]: r["subject"] for d in boards_dir().glob("*/storyboard.json") for r in (_env.read_json(d) or {}).get("photos", {}).values()
            if r.get("subject")}
    shots = {bt["post"]: bt["shot"] for d in boards_dir().glob("*/storyboard.json") for bt in (_env.read_json(d) or {}).get("beats", [])
             if bt.get("shot") and bt.get("post")}
    for b in boards:  # a subject box and a clip's shot belong to their photograph and outlive a redraft
        for r in b["photos"].values():
            if r["file"] in seen:
                r["subject"] = seen[r["file"]]
        for bt in b["beats"]:
            if bt.get("post") in shots:
                bt["shot"] = shots[bt["post"]]
        requests_into(b)
    files = sorted({Path(_env.B) / "photos" / Path(r["file"]).name for b in boards for r in b["photos"].values()})
    n, total = grade.grade_photos(files)
    stage_assets()
    for b in boards:
        d = boards_dir() / b["id"]
        d.mkdir(parents=True, exist_ok=True)
        _env.write_json(d / "storyboard.json", b)
        write_md(b, d / "storyboard.md")
        print(f"board {b['id']} {b['style']}: {len(b['beats'])} beats, {compose.seconds_of(b['beats'], b['bpm']):.1f} s -> {d}/storyboard.md")
    print(f"graded {n} of {total} photographs into {grade.GRADED}/")
    cmd_check(a)  # the boards' first read: the photographs still to be boxed, and anything else check refuses
    return 0


def requests_into(b):
    """Each beat the film wants a generated clip for carries its clip request, in the shape standards.md gives one."""
    asks = {c["beat"]: c for c in compose.lay(b, "reel")["clips"]}
    for bt in b["beats"]:
        bt.pop("clip", None)
        if bt["id"] in asks:
            bt["clip"] = {k: asks[bt["id"]][k] for k in REQUEST}


def load_boards():
    out = [_env.read_json(p) for p in sorted(boards_dir().glob("*/storyboard.json"))]
    if not out:
        sys.exit("no storyboards: run storyboard.py draft first")
    return out


def their_words(ctx):
    """Every line either of them wrote, whitespace folded: captions, comments, answers."""
    acc = [x.get("caption") or "" for x in ctx.items] + [r.get("caption") or "" for r in ctx.rows.values()]
    acc += [e.get("text") or "" for e in ctx.exchanges]
    for p in ctx.pairs:
        acc += [(p.get(k) or {}).get("text") or "" for k in ("first", "answer")]
    return [" ".join(s.split()).lower() for s in acc if s]


def fold_words(t):
    return " ".join(compose.UNSET.sub("", str(t or "")).split()).lower()


def unwritten(studio_board, board, ctx, pool=None):
    """The lines on the cards, a moment's name, its caption line, the lines the two traded, that are not their own."""
    pool = [fold_words(p) for p in (pool if pool is not None else their_words(ctx))]
    out = []
    for c in studio_board["film"]["cards"]:
        for l in [*([] if c.get("hook") else c["head"]), *c["lines"]]:
            if not str(l.get("name") or "").startswith(("head", "words", "talk")):
                continue
            t = fold_words(l["text"])
            if t and not any(t in p for p in pool):
                out.append(f"{c['key']}: '{l['text'][:60]}' is not a line either of them wrote")
    return out


def cut_issues(b, studio_board):
    secs = sum(x["frames"] for x in studio_board["beats"]) / FPS
    out = []
    if not compose.LENGTH[0] <= secs <= compose.LENGTH[1]:
        out.append(f"length {secs:.1f} s is outside {compose.LENGTH[0]}-{compose.LENGTH[1]} s")
    if abs(secs - b["length"]) > 1:
        out.append(f"length {secs:.1f} s is not the board's {b['length']:g} s ({b.get('length_from') or 'the board'})")
    hf = compose.hook_frame(b, studio_board["bpm"])
    if hf > 30:
        out.append(f"the hook's event lands at frame {hf}, after frame 30")
    return out


def board_issues(b, ctx, allowed, bpm=None):
    issues = []
    for p, r in sorted(b["photos"].items()):
        sub = r.get("subject")
        if not (isinstance(sub, list) and len(sub) == 4 and 0 <= sub[0] < sub[2] <= 1 and 0 <= sub[1] < sub[3] <= 1):
            issues.append(f"{p}: open {Path(_env.B) / 'photos' / Path(r['file']).name} and record its subject box in this "
                          "board's photos as \"subject\": [x0, y0, x1, y1], fractions of the photograph: the part the "
                          "beat is about")
    if issues:  # every crop is fitted to its box, so the frame is read once every box is recorded
        return issues
    pool = their_words(ctx)
    for fmt in FORMATS:
        s = compose.lay(b, fmt, bpm)
        issues += compose.bounds(s, b)
        if fmt == "reel":
            issues += cut_issues(b, s)
            issues += unwritten(s, b, ctx, pool)
            issues += [f"{c['beat']} ({c['use']}): open {Path(_env.B) / 'photos' / Path(c['image'] or '').name} and write in this "
                       "beat \"shot\": {\"subject\": what the photograph shows, in your words, \"moves\": what in it would move "
                       "in the clip}" for c in s["clips"] if not c["prompt"]]
    issues += style_findings(b)
    for p, r in sorted(b["photos"].items()):
        if r["file"] not in allowed:
            issues.append(f"{p}: {r['file']} is not a photograph the two share (picks.json shared)")
        elif not (grade.PUBLIC / r["file"]).exists():
            issues.append(f"{p}: {grade.PUBLIC / r['file']} was not graded")
    return issues


def style_findings(b):
    """A beat whose move or cut its board's style card does not allow."""
    c = compose.card(b.get("style") or "")
    moves, cuts = compose.ids(c, "moves"), compose.ids(c, "transitions")
    out = []
    for i, bt in enumerate(b["beats"]):
        if bt.get("move") not in moves:
            out.append(f"{bt['id']}: its move {bt.get('move')!r} is not one {b['style']} allows ({', '.join(moves)})")
        if i and bt.get("transition") not in cuts:
            out.append(f"{bt['id']}: its cut {bt.get('transition')!r} is not one {b['style']} allows ({', '.join(cuts)})")
    return out


def allowed_photos():
    return {grade.graded_name(p) for p in (_env.read_json(f"{_env.B}/picks.json") or {}).get("shared", [])}


def cmd_check(a):
    ctx = compose.Ctx()
    allowed = allowed_photos()
    boards = load_boards()
    bad = 0
    for b in boards:
        iss = board_issues(b, ctx, allowed)
        bad += len(iss)
        s = compose.lay(b, "reel")
        secs = sum(x["frames"] for x in s["beats"]) / FPS
        print(f"board {b['id']} ({b['name']}): {'ok' if not iss else str(len(iss)) + ' issue(s)'}, {secs:.1f} s, "
              f"{len(s['film']['cards'])} cards, {len(s['sound'])} sound cues, hook at frame {compose.hook_frame(b)}")
        for i in iss:
            print("  -", i)
    want = compose.styles_for(ctx.taste)
    if [b.get("style") for b in boards] != want:
        print(f"  - the storyboards must be one per style, in order: {', '.join(want)}")
        bad += 1
    return 1 if bad else 0


def type_findings(rep):
    """What the page could not load: a font or a photograph, or a frame that did not render."""
    return [f["text"][:240] for f in rep.get("findings") or [] if f["text"].startswith(("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR"))]


def cmd_sheets(a):
    _env.need("PIL")
    with studio.lock("sheets") as run:
        return _sheets(run)


def _sheets(run):
    from PIL import Image
    stage_assets()
    boards = load_boards()
    jobs, where = [], []
    for b in boards:  # each type read names the frames below, so it goes before they change
        (boards_dir() / b["id"] / "type.json").unlink(missing_ok=True)
    for b in boards:
        d = boards_dir() / b["id"]
        for fmt in FORMATS:
            fr = d / "frames" / fmt
            shutil.rmtree(fr, ignore_errors=True)
            fr.mkdir(parents=True)
            s = compose.lay(b, fmt)
            for n, (bid, frame) in enumerate(compose.rest_frames(s, b), 1):
                jobs.append(studio.still(s, frame, fr / f"{n:02d}-{bid}.png", scale=SHEET_SCALE))
            where.append((b, fmt, fr))
    looks = []
    for b in boards:  # each look's hook, middle card and closer at half size, for the boards image
        d = boards_dir() / b["id"] / "look"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        s = compose.lay(b, "reel")
        for n, (bid, frame) in enumerate(compose.rest_frames(s, b), 1):
            jobs.append(studio.still(s, frame, d / f"{n:02d}-{bid}.png", scale=LOOK_SCALE))
        looks.append((b, d))
    rep = studio.render(jobs, "sheets", run)
    boards_image(looks)
    for b, fmt, fr in where:
        ims = [Image.open(f).convert("RGB") for f in sorted(fr.glob("*.png"))]
        if not ims:
            continue
        w, h = ims[0].size
        cols = 3
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (w + 8) + 8, rows * (h + 8) + 8), "#111111")
        for i, im in enumerate(ims):
            sheet.paste(im, (8 + (i % cols) * (w + 8), 8 + (i // cols) * (h + 8)))
        name = "sheet.png" if fmt == "reel" else f"sheet-{fmt}.png"
        tmp = fr.parent.parent / f".{name}.part"
        sheet.save(tmp, "PNG")
        os.replace(tmp, fr.parent.parent / name)
    by_board = {}
    for b in boards:
        write_md(b, boards_dir() / b["id"] / "storyboard.md")
        mine = {"findings": [f for f in rep.get("findings") or [] if f"/storyboards/{b['id']}/" in f["job"]]}
        _env.write_json(boards_dir() / b["id"] / "type.json", mine)
        by_board[b["id"]] = type_findings(mine)
        tag = f"/storyboards/{b['id']}/"
        print(f"board {b['id']}: {sum(1 for j in jobs if tag in j['out'])} frames, "
              f"sheets {boards_dir() / b['id']}/sheet.png, sheet-feed.png, sheet-wide.png; {len(by_board[b['id']])} finding(s)")
        for f in by_board[b["id"]]:
            print("  -", f)
    return 0 if not rep.get("failed") and not any(by_board.values()) else 1


def boards_image(looks):
    """out/boards.png: one row per board, its letter, its style's name and one plain sentence on how it looks over its
    hook, middle card and closer; and each row alone as B/storyboards/N/look.png, for the review page's other looks."""
    from PIL import Image, ImageDraw, ImageFont
    rows = []
    for b, d in looks:
        ims = [Image.open(f).convert("RGB") for f in sorted(d.glob("*.png"))]
        if not ims:
            continue
        w, h = ims[0].size
        pad, head = 24, 132
        row = Image.new("RGB", (len(ims) * (w + pad) + pad, h + head + pad), "#f4f1ea")
        for i, im in enumerate(ims):
            row.paste(im, (pad + i * (w + pad), head))
        name, sentence = compose.name_of(b["style"])
        draw = ImageDraw.Draw(row)
        face = compose.card(b["style"])["faces"]
        big = ImageFont.truetype(str(_env.SKILL / face["display"]["file"]), 52)
        small = ImageFont.truetype(str(_env.SKILL / compose.card("editorial-quiet")["faces"]["text"]["file"]), 24)
        draw.text((pad, 22), f"{chr(64 + int(b['id']))}  {name}", font=big, fill="#1a1a1a")
        draw.text((pad, 88), sentence, font=small, fill="#4a4a4a")
        tmp = d.parent / ".look.png.part"
        row.save(tmp, "PNG")
        os.replace(tmp, d.parent / "look.png")
        rows.append(row)
    if not rows:
        return
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows)), "#f4f1ea")
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    out = Path("out")
    out.mkdir(exist_ok=True)
    tmp = out / ".boards.png.part"
    sheet.save(tmp, "PNG")
    os.replace(tmp, out / "boards.png")
    print(f"the three looks side by side -> {out / 'boards.png'}")


def unswapped(board, win):
    """The beats the panel named in the swap test that are still as they were voted."""
    named = (win or {}).get("swap") or {}
    if str((win or {}).get("board")) != str(board["id"]):
        return []
    now = {bt["id"]: _env.digest(bt) for bt in board["beats"]}
    return [i for i, h in named.items() if now.get(i) == h]


def fold(bpm, style):
    """The music's tempo moved by octaves into the style's range; the planned tempo when there is none to fold."""
    lo, hi = compose.tempo_range(style)
    if not bpm:
        return compose.tempo_of(style)
    for k in (1, 2, 0.5, 4, 0.25):
        if lo <= bpm * k <= hi:
            return round(bpm * k, 2)
    return compose.tempo_of(style)


def cuts_of(studio_board):
    """The seconds each beat after the first starts at: the planned cuts."""
    out, at = [], 0
    for x in studio_board["beats"][:-1]:
        at += x["frames"]
        out.append(round(at / FPS, 3))
    return out


def cmd_snap(a):
    win = _env.read_json(f"{_env.B}/winner.json")
    bid = (win or {}).get("board")
    if not bid:
        sys.exit("no winner: the board has not passed the vote; run vote.py ballot, fill it in, then vote.py tally")
    b = _env.read_json(boards_dir() / str(bid) / "storyboard.json")
    left = unswapped(b, win)
    if left:
        print(f"the swap test refuses board {bid}, beats {', '.join(left)}: each would come out the same with a neighbor's photograph. "
              "Redesign each around its own photograph (its own words, its own date) in storyboard.json, then snap again")
        return 1
    music = _env.read_json(f"{_env.B}/music.json") or {}
    bpm = fold(music.get("bpm"), b["style"])
    ctx = compose.Ctx()
    iss = board_issues(b, ctx, allowed_photos(), bpm)
    sheet = _env.read_json(boards_dir() / str(bid) / "type.json")
    iss += type_findings(sheet) if sheet else [f"board {bid} has no type read: run storyboard.py sheets"]
    if iss:
        print(f"board {bid} at {bpm} bpm is refused:")
        for i in iss:
            print("   ", i)
        return 1
    s = compose.lay(b, "reel", bpm)
    secs = sum(x["frames"] for x in s["beats"]) / FPS
    film = {**compose.fit(b, bpm), "bpm": bpm, "seconds": round(secs, 3), "frames": sum(x["frames"] for x in s["beats"]),
            "hook_frame": compose.hook_frame(b, bpm), "hook_event": compose.hook_event(b), "story": compose.story(b),
            "sound": s["sound"], "clips": s["clips"], "cuts": cuts_of(s),
            "music": {**b["music"], **{k: music.get(k) for k in ("file", "bpm", "origin") if music.get(k)}}}
    film["hash"] = _env.digest(film)  # the cut's identity: the preview, the critic's timed read and qa timed name it
    # the render report vouches for out/ as the film of the cut it replaces, so it goes before the cut changes
    (studio.render_dir() / "film-report.json").unlink(missing_ok=True)
    _env.write_json(f"{_env.B}/film.json", film)
    print(f"board {bid}: {len(s['beats'])} beats at {bpm} bpm (the music's {music.get('bpm') or 'no'} bpm folded into "
          f"{compose.tempo_range(b['style'])}), {secs:.1f} s -> {_env.B}/film.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
