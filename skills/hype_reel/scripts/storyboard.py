#!/usr/bin/env python3
"""Movement 2: three storyboards of the hype reel, one in each of three styles, made from the subject's own stills and
footage and the person's own photographs, with their beats rendered at rest; and the step that cuts the chosen board to
the music.

USAGE (in a run, after research; S = this skill's folder):
    python3 S/scripts/storyboard.py draft            # storyboards/{1,2,3}/storyboard.json + storyboard.md; a new
                                                     # draft starts a new vote (winner.json and vote/scores.json go)
    python3 S/scripts/storyboard.py check [FILE...]  # every board (or the files named): see "check" below
    python3 S/scripts/storyboard.py sheets           # every beat at rest: storyboards/N/frames/*.png, storyboards/N/
                                                     # sheet.png, and out/boards.png, the three looks side by side
    python3 S/scripts/storyboard.py snap             # the chosen board (winner.json) cut to music.json -> film.json

draft casts the parts (cast.py), grades each of their photographs into public/photos/<part>.jpg, stages the subject's
stills and footage as they are into public/subject/, and lays the one story (drive.py) out three times, once per style:
the style the person named (taste.json `style`) and the two of the kit's three (kinetic-type, cinematic-letterbox,
swiss-grid) that differ most from it, or those three when they named none. Board 1 is the first of them. Each board
takes its style card's faces, its colors (the card's palette rule over the swatches of both palettes), its tempo (the
middle of the card's music recipe's range), the move and cut of each beat (chosen from the beat's content within the
card's allowlists), its finish and its closer. The agent may edit any storyboard.json; check validates it.

check fails a board on:
  style     the three boards' styles share more than two of the six axes pairwise; a face not the card's; a move or a
            cut outside the card's allowlist; a color the card's palette rule did not make; every shot within 10 % of
            one length; the words in one place of the frame on more than 70 % of the beats that carry them; one move on
            two beats running
  words     a line of words outside the format's safe area
  assets    a picture that is not in public/, or a subject picture that is not one of the subject's own stills or clips
  date      a launch's closer does not carry its date
  subject   the subject's own pictures fill less than half the time before the closer
  length    the film at the board's tempo outside 15-25 s
The film runs the length the person asked for (taste.json `seconds`), moved into 15-25 s; draft prints one line
saying the length and why when the ask is outside it. With no length asked, a board runs its own length, moved into
15-25 s. The plan in taste.json (`plan`) gives the hook line, the punchline the closer carries when the subject is not
a launch, and the tone (drive.TONES); taste.json `subject.lines` gives the line on each of the subject's stills.
While check finds anything on a board, sheets renders nothing.
snap cuts every beat on the music's beats (music.json from music.py make; with no music, on the board's tempo), sets
each beat's frames and pulse and the hits (the musical beats where a beat lands, each one music.py master sounds), and
names the frames the stills are taken from: the cover (the reveal at rest, the strongest settled frame, also laid
over the film's frame 0), the feed post (the closer laid for the feed, at rest), and for a launch the three stories
(the hook, a beat of the build and the reveal at rest) and the countdown card (the closer at rest). When this run
already has a film (out/film.mp4), draft and snap start a new run first, so a second film never overwrites the first.
"""
import argparse
import calendar
import copy
import datetime as dt
import math
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import cast  # noqa: E402
import chunks  # noqa: E402
import compose  # noqa: E402
import drive  # noqa: E402
import grade  # noqa: E402
import palette  # noqa: E402

BOARDS = Path("storyboards")
FPS = 30
LENGTH = (15, 25)
# the stills every reel has (the cover), and those only a launch has (the teaser stories and the countdown card)
CARDS = (("cover", "story", "made"),)
LAUNCH_CARDS = (("story-1", "story", "hook"), ("story-2", "story", "build"), ("story-3", "story", "made"),
                ("countdown", "story", "closer"))
NAMES = {"kinetic-type": "Kinetic type", "cinematic-letterbox": "Cinematic", "swiss-grid": "Swiss grid"}


# ------------------------------------------------------------------ draft
def say(taste):
    """How the film sets words: all capitals where the plan's tone says so, else lowercase where the person writes in
    lowercase, else as written."""
    tone = ((taste or {}).get("plan") or {}).get("tone")
    if drive.TONES.get(tone or "default", {}).get("case") == "upper":
        return lambda s: s.upper()
    lower = ((taste or {}).get("register") or {}).get("lowercase")
    return (lambda s: s.lower()) if lower else (lambda s: s)


def stage_assets():
    """The style faces inside public/, the folder the renderer serves, copied on every staging so a run always serves
    the kit's current files."""
    shutil.copytree(_env.SKILL / "fonts" / "styles", grade.PUBLIC / "fonts" / "styles", ignore=shutil.ignore_patterns("*.md"),
                    dirs_exist_ok=True)


def asked(taste):
    """The film's length in seconds as taste.json `seconds` carries the person's ask, or None when they named none."""
    x = (taste or {}).get("seconds")
    if x in (None, "", 0):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        sys.exit(f"taste.json seconds is {x!r}: write the length they asked for in seconds (20), or null")


def length_said(seconds, want):
    """The one plain line that says how long the film runs and why, when the person asked for a length the film cannot
    run; None when they asked for none or the film runs the length asked."""
    if not want or abs(seconds - want) < 0.75:
        return None
    if seconds < want:
        return f"You asked for {want:g} s; a hype reel runs at most {seconds:.0f} s, so the reel is {seconds:.0f} s."
    return f"You asked for {want:g} s; a hype reel runs at least {seconds:.0f} s, so the reel is {seconds:.0f} s."


def subject_lines(subj):
    """The line each of the subject's stills may carry, by its path: its own words (a caption beside it), else the
    subject's facts in turn, each a line as research.line_of cuts it; a still with neither carries none."""
    import research
    facts = [research.line_of(f, subj.get("name") or "") for f in subj.get("facts") or []]
    said = subj.get("said") or {}
    out, k = {}, 0
    for p in subj.get("stills") or []:
        if said.get(p):
            out[p] = research.line_of(said[p], subj.get("name") or "")
        elif facts:
            out[p] = facts[k % len(facts)] if k < len(facts) else ""
            k += 1
    return out


def context(lib, taste, subject, c):
    """What the film is made of: the subject's words, its stills (each with its line) and footage, their cast
    photographs graded into public/photos, the hook's line, and the plan's tone. A launch's closer carries its date as
    they wrote it; anything else's carries the plan's punchline."""
    from PIL import Image
    subj = lib.get("subject") or {}
    plan = (taste or {}).get("plan") or {}
    sw = say(taste)
    launch = bool(subj.get("launch"))
    iso = subj.get("date") if launch else None
    day = dt.date.fromisoformat(iso) if iso and re.fullmatch(r"\d{4}-\d\d-\d\d", iso) else None
    handle = lib.get("handle")
    lines = {**subject_lines(subj), **(((taste or {}).get("subject") or {}).get("lines") or {})}
    first = subject["pieces"][0]["path"] if subject["pieces"] else None
    stills = [{"file": f"subject/{p['file']}", "aspect": p["aspect"], "subject": p["subject"], "size": p["size"],
               "id": p["path"], "line": "" if p["path"] == first else sw(lines.get(p["path"]) or ""),
               "ground": [p["top"], p["foot"]]} for p in subject["pieces"]]
    label = sw(subj.get("date_label") or subj.get("date_text") or "soon") if launch else sw(plan.get("punchline") or "")
    ctx = {"name": sw(subj.get("name") or "the subject"),
           "handle": subj.get("handle") or (f"@{handle}" if handle and handle != "you" else ""),
           "date_label": label, "hook_label": label if launch else "", "launch": launch, "tone": plan.get("tone") or "default",
           "month": sw(calendar.month_name[day.month]) if day else "", "day": str(day.day) if day else "",
           "stills": stills, "hero": stills[0] if stills else None, "seconds": asked(taste)}
    ft = subject.get("footage")
    ctx["footage"] = {"file": f"subject/{Path(ft['file']).stem}.png", "clip": f"subject/{ft['file']}", "aspect": ft["aspect"],
                      "subject": ft["subject"], "size": ft["size"], "id": ft["path"], "line": ""} if ft else None
    filt = grade.ensure_recipe()["filter"]
    entries = []

    def take(part, p):
        dst = cast.PHOTOS / f"{part}.jpg"
        night = p["classes"]["night"] or p["classes"]["low_sun"]
        g = cast.grade_photo(p["file"], dst, filt, wb=0 if night else cast.WB)
        w, h = Image.open(dst).size
        entries.append({"part": part, "id": p["id"], "caption": p["caption"], "line": p.get("line") or "", "date": p.get("date"),
                        "subject": p["subject"], "subject_from": p.get("subject_from"), "grade": g})
        return {"file": f"photos/{part}.jpg", "aspect": round(h / w, 4), "subject": p["subject"], "size": [w, h], "id": p["id"],
                "line": p.get("line") or "", "classes": p["classes"], "date": p.get("date")}

    ctx["hook"] = take("hook", c["hook"]) if c["hook"] else None
    ctx["hook_line"] = sw(plan.get("hook") or c["hook_line"] or ctx["name"])
    ctx["build"] = [take(f"build-{i}", p) for i, p in enumerate(c["build"], 1)]
    return ctx, entries


def colors_of(style, taste):
    """The board's colors: the six roles the style's palette rule made from both palettes' swatches, and the swatches."""
    made = palette.palette_of(compose.card(style)["palette"], palette.swatches_of(taste))
    names = {h: f"swatch {i + 1}" for i, h in enumerate(made["swatches"])}
    return {**made["roles"], "swatches": [{"hex": h, "name": names[h]} for h in made["swatches"]]}


def tempo_of(style):
    """The board's tempo: the middle of its card's music recipe's range."""
    import music_engine
    lo, hi = music_engine.recipes()["recipes"][compose.card(style)["music"]]["tempo"]
    return round((lo + hi) / 2)


def board(ctx, style, n, entries, taste):
    c = compose.card(style)
    bpm = tempo_of(style)
    want = ctx.get("seconds")
    secs = None
    if want:
        secs = min(max(want, LENGTH[0]), LENGTH[1])
    d = drive.build(ctx, c, bpm, secs)
    total = sum(b["len"] for b in d["beats"])
    if not secs and not LENGTH[0] + 0.5 <= total * 60 / bpm <= LENGTH[1] - 0.5:
        d = drive.build(ctx, c, bpm, min(max(total * 60 / bpm, LENGTH[0] + 0.5), LENGTH[1] - 0.5))
        total = sum(b["len"] for b in d["beats"])
    system = compose.system(c, colors_of(style, taste))
    used = {(b.get("picture") or {}).get("file") for b in d["beats"]}
    return {"id": str(n), "name": NAMES.get(style, c["name"]), "style": style, "idea": c.get("name", style),
            "subject": ctx["name"], "handle": ctx["handle"], "title": ctx["name"],
            "signoff": signoff_of(ctx, c["closer"]),
            "launch": ctx["launch"], "tone": ctx["tone"],
            "date": {"label": ctx["date_label"], "month": ctx["month"], "day": ctx["day"]},
            "bpm": bpm, "music": {"recipe": c["music"], "bpm": bpm},
            "format": {"width": 1080, "height": 1920, "fps": FPS, "name": "reel"}, "system": system, "beats": d["beats"],
            "sound": d["sound"], "story": d["story"],
            "feed": {"format": {"width": 1080, "height": 1350, "fps": FPS, "name": "feed"}, "beats": drive.feed(ctx, c)},
            "hook": {"line": ctx["hook_line"], "photo": (ctx.get("hook") or {}).get("id")},
            "cast": [e for e in entries if f"photos/{e['part']}.jpg" in used],
            "clips": clip_list(d["beats"], bpm, ctx["name"], c)}


# the closers that set the film's title above the signoff, so their signoff carries the date alone
TITLED = {"title-card", "poster", "book-cover"}


def signoff_of(ctx, closer):
    """The closer's line: on a closer that sets the title above it, the date or the punchline alone. On a closer that
    sets one line, a launch's name and date, and anything else's punchline (the reveal before it has set the name, and
    a name run into a punchline reads as one sentence), or its name when there is no punchline."""
    if closer in TITLED:
        return ctx["date_label"]
    if ctx["launch"]:
        return f"{ctx['name']} {ctx['date_label']}".strip()
    return ctx["date_label"] or ctx["name"]

CAMERA = {"slam": "a quick push in that lands hard on the beat", "dolly": "a slow lateral dolly on rails",
          "snap": "a locked-off frame that steps once, cleanly"}


def clip_list(beats, bpm, name, card):
    """The shots an image-to-video model would make for the board, one per beat on one of their photographs, each a shot
    as a cinematographer writes it; the subject's own footage plays on its beat as it is. No model is reachable on this
    machine, so each shot has its stand-in: the beat's move and the card's camera on the still in its place."""
    move = CAMERA.get(card["axes"]["camera"], "a slow push in")
    out = []
    for b in beats:
        p = b.get("picture")
        if not p or b["part"] == "closer":
            continue
        secs = round(b["len"] * 60 / bpm, 2)
        if p.get("clip"):
            out.append({"id": b["id"], "beat": b["id"], "role": "the subject's own footage", "image": p["file"], "source": p["clip"],
                        "seconds": secs, "prompt": "", "stand_in": "the footage's first frame under the beat's move and the card's camera"})
            continue
        if b["own"]:
            continue
        said = f", the moment of \"{b['words']}\"" if b["words"] else ""
        out.append({"id": b["id"], "beat": b["id"], "role": "a step of the making brought to life", "image": p["file"],
                    "seconds": secs, "prompt": (f"Subject: this photograph{said}, kept exactly as it is (its shapes, its colors, "
                                                f"its place in the frame). Camera: {move}, over {secs} s. Light: the photograph's own "
                                                f"light. Loop: seamless, one continuous shot, no cuts, no new objects, no text."),
                    "stand_in": "the beat's move and the card's camera on the still"})
    return out


def write_md(b, path):
    secs = sum(x["len"] for x in b["beats"]) * 60 / b["bpm"]
    lines = [f"# storyboard {b['id']}: {b['name']} ({b['style']})", "",
             f"{b['bpm']} bpm, {sum(x['len'] for x in b['beats'])} beats ({secs:.1f} s), faces {b['system']['display']['family']} and "
             f"{b['system']['text']['family']}, closer {b['system']['closer']}, {len(b['sound'])} sound cues.", "",
             "| beat | beats | picture | words on screen | move | cut in | what it shows |", "|---|---|---|---|---|---|---|"]
    story = {x["beat"]: x for x in b.get("story") or []}
    for x in b["beats"]:
        pic = (x.get("picture") or {}).get("file", "-")
        lines.append(f"| {x['id']} | {x['len']} | {pic} | {x['words'] or x['label']} | {x['move']} | {x['transition'] or '-'} | "
                     f"{story.get(x['id'], {}).get('reveals', '')} |")
    lines += ["", "## sound", "", ", ".join(f"{c['kind']} {c['at']}" for c in b["sound"]), "",
              "## their photographs", "", "| part | photograph | line | subject (who set it) |", "|---|---|---|---|"]
    for e in b["cast"]:
        lines.append(f"| {e['part']} | {Path(e['id']).name}: {e['caption'][:80]} | {e['line']} | {e['subject']} ({e['subject_from']}) |")
    if not b["cast"]:
        lines.append("| - | none: the film is made from the subject alone | | |")
    Path(path).write_text("\n".join(lines) + "\n")


def cmd_draft(a):
    _env.need("PIL")
    new_run_if_filmed()
    for old in (Path("winner.json"), Path("vote/scores.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    lib = _env.read_json("library.json") or sys.exit("library.json is missing: run gather.py first")
    if not Path("taste.md").exists():
        sys.exit("taste.md is missing: research comes first (pipeline/1-research.md)")
    taste = _env.read_json("taste.json") or {}
    subject = cast.measure_subject(lib)
    c = cast.cast(lib, taste, subject, _env.read_json("looks.json"))
    Path("film.json").unlink(missing_ok=True)
    shutil.rmtree(BOARDS, ignore_errors=True)
    shutil.rmtree(cast.PHOTOS, ignore_errors=True)
    cast.stage_subject(subject)
    stage_assets()
    ctx, entries = context(lib, taste, subject, c)
    styles = compose.trio_for((taste or {}).get("style"))
    boards = {}
    for n, style in enumerate(styles, 1):
        b = board(ctx, style, n, entries, taste)
        part = Path(f".storyboard-{n}.part")
        shutil.rmtree(part, ignore_errors=True)
        _env.write_json(part / "storyboard.json", b)
        write_md(b, part / "storyboard.md")
        BOARDS.mkdir(exist_ok=True)
        os.replace(part, BOARDS / str(n))
        boards[str(n)] = b
    found = issues(boards)
    for n, b in boards.items():
        secs = sum(x["len"] for x in b["beats"]) * 60 / b["bpm"]
        mine = [x for x in found if x.startswith(f"board {n}:")]
        print(f"board {n}: {b['style']}, {len(b['beats'])} beats, {secs:.1f} s at {b['bpm']} bpm, hook '{b['hook']['line']}', "
              f"moves {', '.join(x['move'] for x in b['beats'])}; {len(mine)} check findings")
    said = length_said(sum(x["len"] for x in boards["1"]["beats"]) * 60 / boards["1"]["bpm"], ctx.get("seconds"))
    if said:
        print(said)
    for x in found:
        print("   ", x)
    print(f"{len(ctx['build']) + bool(ctx['hook'])} of their photographs graded into public/photos; "
          f"{len(subject['pieces'])} subject stills{' and its footage' if subject['footage'] else ''} in public/subject")
    return 1 if found else 0


# ------------------------------------------------------------------ check
def hexes_in(o):
    if isinstance(o, dict):
        return [h for k, v in o.items() for h in ([v.lower()] if k == "color" and isinstance(v, str) and v.startswith("#") else hexes_in(v))]
    if isinstance(o, list):
        return [h for v in o for h in hexes_in(v)]
    return []


def style_findings(boards, taste):
    """The template tells and style breaks a set of boards ({n: board}) has, each one plain sentence naming the board
    and the rule."""
    out = []
    names = list(boards)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa, sb = boards[a].get("style"), boards[b].get("style")
            if sa and sb:
                same = compose.shared_axes(sa, sb)
                if len(same) > 2:
                    out.append(f"board {a}: its style and board {b}'s ({sa}, {sb}) share {len(same)} of the six axes "
                               f"({', '.join(same)}), more than two; give one of them a style that differs more")
    swatches = palette.swatches_of(taste)
    for n, b in boards.items():
        if not b.get("style"):
            out.append(f"board {n}: it names no style; draft it again so it carries one")
            continue
        c = compose.card(b["style"])
        s = b["system"]
        for k in ("display", "text"):
            if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
                out.append(f"board {n}: its {k} face {s[k]['family']} is not the {k} face of {c['id']} ({c['faces'][k]['family']})")
        if s.get("photo") != c["photo"]:
            out.append(f"board {n}: it does not carry the photo layout of {c['id']}; draft it again")
        for bt in b["beats"]:
            if bt.get("layout") != "card":
                continue
            if not bt.get("fits", True):
                out.append(f"board {n}: beat {bt['id']}'s words are too long for the line box of {c['id']}, even at half its size; "
                           f"shorten the line they wrote with that photograph")
            for l in bt.get("lines") or []:
                x0 = l["x"] - (l["w"] / 2 if l["align"] == "center" else 0)
                bx0, by0, bx1, by1 = l["box"]
                if x0 < bx0 - 1 or x0 + l["w"] > bx1 + 1 or l["top"] < by0 - 1 or l["top"] + l["size"] > by1 + 1:
                    out.append(f"board {n}: beat {bt['id']}'s line '{l['text']}' overruns the line box of {c['id']}")
        moves, cuts = compose.ids(c, "moves"), compose.ids(c, "transitions")
        for bt in b["beats"]:
            if bt.get("move") not in moves:
                out.append(f"board {n}: beat {bt['id']} moves by {bt.get('move')!r}, which is not a move of {c['id']} ({', '.join(moves)})")
            if bt.get("transition") is not None and bt["transition"] not in cuts:
                out.append(f"board {n}: beat {bt['id']} is cut to by {bt['transition']!r}, which is not a transition of {c['id']}")
        made = set(palette.palette_of(c["palette"], swatches)["made"])
        shown = [v.lower() for k, v in s["colors"].items() if k != "swatches"] + [w["hex"].lower() for w in s["colors"].get("swatches") or []]
        for h in sorted(set(shown + hexes_in(b["beats"])) - made):
            out.append(f"board {n}: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make")
        lens = sorted(bt["len"] for bt in b["beats"])
        if len(lens) >= 3:
            mid = lens[len(lens) // 2]
            if all(abs(x - mid) <= 0.1 * mid for x in lens):
                out.append(f"board {n}: every shot runs within 10 % of {mid} beats; vary the beats' lengths")
        # the card's photo layout puts every photo beat's words in one box by design: those beats count as one place
        cells = [("card",)] if any(bt.get("layout") == "card" and bt.get("lines") for bt in b["beats"]) else []
        for bt in b["beats"]:
            ls = bt.get("lines") or []
            if ls and bt.get("layout") != "card":
                xs = [l["x"] - (l["w"] / 2 if l["align"] == "center" else 0) for l in ls]
                cx = (min(xs) + max(x + l["w"] for x, l in zip(xs, ls))) / 2
                cy = (ls[0]["top"] + ls[-1]["top"] + ls[-1]["size"]) / 2
                cells.append((min(2, max(0, int(3 * cx / 1080))), min(2, max(0, int(3 * cy / 1920)))))
        if len(cells) >= 3:
            top = max(set(cells), key=cells.count)
            if cells.count(top) > 0.7 * len(cells):
                where = "card's line box" if top == ("card",) else ("top", "middle", "bottom")[top[1]] + " " + ("left", "center", "right")[top[0]]
                out.append(f"board {n}: the words sit in one place, the {where} of the frame, on {cells.count(top)} of the "
                           f"{len(cells)} beats that carry them; move them with what each beat shows")
        for x, y in zip(b["beats"], b["beats"][1:]):
            if x.get("move") and x.get("move") == y.get("move"):
                out.append(f"board {n}: beats {x['id']} and {y['id']} both move by {x['move']}; consecutive beats move differently")
    return out


def line_issues(n, bt, fmt):
    sf = compose.SAFE[fmt]
    out = []
    for l in (bt.get("lines") or []) + (bt.get("still") or []):
        x0 = l["x"] - (l["w"] / 2 if l["align"] == "center" else 0)
        if x0 < sf["left"] - 1 or x0 + l["w"] > sf["width"] - sf["right"] + 1 or l["top"] < sf["top"] - 1 or \
                l["top"] + l["size"] > sf["height"] - sf["bottom"] + 1:
            out.append(f"board {n}: beat {bt['id']}'s line '{l['text']}' runs outside the {fmt} safe area")
    return out


def board_issues(n, b):
    out = []
    for bt in b["beats"]:
        out += line_issues(n, bt, "reel")
    subj = (_env.read_json("library.json") or {}).get("subject") or {}
    own = {f"subject/{Path(p).name}" for p in subj.get("stills", []) + subj.get("footage", [])}
    own |= {f"subject/{Path(p).stem}.png" for p in subj.get("footage", [])}
    for bt in b["beats"] + b["feed"]["beats"]:
        p = bt.get("picture") or {}
        for fl in (p.get("file"), p.get("clip")):
            if fl and not (grade.PUBLIC / fl).exists():
                out.append(f"board {n}: beat {bt['id']} shows {fl}, which is not in public/")
            if fl and fl.startswith("subject/") and fl not in own:
                out.append(f"board {n}: beat {bt['id']} shows {fl} as the subject, which is not one of its own stills or clips")
    shown = f"{b.get('title', '')} {b.get('signoff', '')}".lower()
    d = b["date"]
    if b.get("launch", True) and d["label"].lower() not in shown:
        out.append(f"board {n}: the closer does not carry {d['label']}")
    body = b["beats"][:-1]
    total = sum(x["len"] for x in body)
    prod = sum(x["len"] for x in body if x.get("own") and x.get("move") not in drive.COVERS)
    if b["beats"][0].get("picture") and total and prod < 0.5 * total:
        out.append(f"board {n}: the subject's own pictures fill {prod} of the {total} beats before the closer, under half")
    if not any(c["kind"] == "stop" for c in b.get("sound") or []):
        out.append(f"board {n}: no stop, so the picture and the music never stop together")
    secs = sum(x["len"] for x in b["beats"]) * 60 / b["bpm"]
    if not LENGTH[0] - 0.5 <= secs <= LENGTH[1] + 0.5:
        out.append(f"board {n}: {secs:.1f} s at {b['bpm']} bpm, outside {LENGTH[0]}-{LENGTH[1]} s")
    return out


def issues(boards):
    taste = _env.read_json("taste.json") or {}
    out = style_findings(boards, taste)
    for n, b in boards.items():
        out += board_issues(n, b)
    return out


def refuse_flagged(boards):
    """Exits before anything renders when check finds anything on these boards ([(file, board), ...]), one line per
    finding."""
    found = [f"{f} is not rendered: {x}" for f, b in boards for x in board_issues(str(f), b)]
    if found:
        sys.exit("\n".join(found))


def load_boards(files=None):
    fs = [Path(f) for f in files] if files else sorted(BOARDS.glob("*/storyboard.json"))
    return {f.parent.name: _env.read_json(f) for f in fs}


def cmd_check(a):
    boards = load_boards(a.files)
    if not boards:
        sys.exit("no storyboards: run storyboard.py draft first")
    found = issues(boards)
    for n, b in boards.items():
        mine = [x for x in found if x.startswith(f"board {n}:")]
        print(f"{'ok  ' if not mine else 'FAIL'} board {n} ({b['style']}): {len(b['beats'])} beats, {len(mine)} findings")
    for x in found:
        print("    ", x)
    return 1 if found else 0


# ------------------------------------------------------------------ timing
def jround(x):
    """Rounding the way the renderer rounds (half up), so a frame counted here is the frame drawn there."""
    return int(math.floor(x + 0.5))


def timed(board, music=None):
    """The board with each beat's frames and pulse (frames per musical beat) set from the music's beats, measured from
    the first, where master starts the track, else from the board's tempo. Every beat is a whole number of musical
    beats, so every cut sits on a beat of the music."""
    out = copy.deepcopy(board)
    music = music or {}
    bpm = float(music.get("bpm") or out["bpm"])
    beats = [float(x) for x in music.get("beats") or []]
    offset = beats[0] if beats else 0.0
    grid = [x - offset for x in beats] or [0.0]
    need = sum(round(b["len"]) for b in out["beats"]) + 1
    while len(grid) < need:
        grid.append(grid[-1] + 60.0 / bpm)
    pos = 0
    for b in out["beats"]:
        n = round(b["len"])
        s, e = jround(grid[pos] * FPS), jround(grid[pos + n] * FPS)
        b["frames"] = e - s
        b["pulse"] = round((e - s) / n, 4)
        b["hits"] = sorted(set(b.get("hits_at") or []))
        pos += n
    out["bpm"] = round(bpm, 3)
    out["music_offset"] = round(offset, 3)
    out["seconds"] = round(sum(b["frames"] for b in out["beats"]) / FPS, 3)
    return out


def timeline(board):
    out, start = [], 0
    for b in board["beats"]:
        out.append({"id": b["id"], "bars": b["bars"], "start": start, "frames": b["frames"], "transition": b.get("transition"),
                    "start_s": round(start / FPS, 3), "seconds": round(b["frames"] / FPS, 3), "cuts": []})
        start += b["frames"]
    return out


# the musical beats a beat's words take to leave before its cut (HypeFilm's Words)
EXIT = 0.25


def rest(tl, beat, board=None):
    """The frame a beat comes to rest on: two frames before its words begin to leave (EXIT) or the cut out of it begins
    to draw, whichever is first (its end, for the closer), and never inside the cut into it."""
    t = tl[beat]
    pulse = t["frames"] / max(1, round(4 * t["bars"]))
    out = max(EXIT, drive.cut_beats(tl[beat + 1]["transition"]) / 2) if beat + 1 < len(tl) else 0
    into = drive.cut_beats(t["transition"]) / 2
    return max(t["start"] + math.ceil(into * pulse), t["start"] + t["frames"] - 2 - math.ceil(out * pulse))


def stills_of(film):
    """The frames the story-sized stills are taken from (the cover, and for a launch the three stories and the
    countdown), and the feed post's board.

    The build's still is its middle beat that carries the person's words, so the story between the hook and the
    reveal says something; a build with no words takes its middle beat. A beat whose words land one a beat has the
    whole line at rest on its still (its `still` lines, the card's "still" board)."""
    tl = film["timeline"]
    ids = [t["id"] for t in tl]
    parts = [b["part"] for b in film["beats"]]
    cards = []
    for out, fmt, part in CARDS + (LAUNCH_CARDS if film.get("launch", True) else ()):
        if part == "build":
            mids = [i for i, p in enumerate(parts) if p in ("build", "detail")]
            said = [i for i in mids if film["beats"][i].get("words")]
            mids = said or mids
            i = mids[len(mids) // 2] if mids else 0
        else:
            i = parts.index(part) if part in parts else len(ids) - 1
        cards.append({"out": f"out/{out}.png", "format": fmt, "beat": ids[i], "frame": rest(tl, i, film),
                      **({"board": "still"} if film["beats"][i].get("still") else {})})
    closer = film["beats"][-1]
    feed = feed_board(film, closer)
    cards.append({"out": "out/feed.png", "format": "feed", "beat": closer["id"], "frame": closer["frames"] - 2, "board": "feed"})
    return cards, feed


def feed_board(b, closer):
    feed = {k: copy.deepcopy(b[k]) for k in ("id", "name", "style", "subject", "handle", "title", "signoff", "date", "bpm", "system")}
    feed["launch"] = b.get("launch", True)
    feed["format"] = b["feed"]["format"]
    feed["beats"] = copy.deepcopy(b["feed"]["beats"])
    for x in feed["beats"]:
        x.update({"frames": closer["frames"], "pulse": closer["pulse"], "hits": closer.get("hits", []), "len": closer["len"],
                  "stop": closer.get("stop", x["stop"]), "bars": closer["bars"]})
    feed["sound"] = [{"kind": "stop", "at": closer.get("stop", 6)}]
    return feed


FILMED = ["out", "film.json", "timeline.json", "film.silent.mp4", "render", "render-report.json", "cut.json", "cards.json",
          "critic", "qa", "frames", "music", "music.json", "clips.json"]


def new_run_if_filmed():
    if Path("out/film.mp4").exists():
        print(f"this run has its film; the new one is made in {_env.fork_run(FILMED)}")


def cmd_snap(a):
    new_run_if_filmed()
    win = _env.read_json("winner.json") or {}
    bid, b = win.get("board"), win.get("storyboard")
    if not bid:
        sys.exit("no board chosen: run vote.py ballot, fill it in, then vote.py tally (or vote.py pick N)")
    if not b:
        sys.exit("winner.json does not carry its board: run vote.py tally again")
    music = _env.read_json("music.json") or {}
    if music.get("beats") and abs(float(music.get("bpm") or 0) - b["bpm"]) > 0.08 * b["bpm"]:
        print(f"music.json is at {music.get('bpm')} bpm and board {bid} at {b['bpm']}: run music.py make for this board, then snap again")
    if not music.get("beats"):
        print("no beats in music.json: cutting on the board's tempo")
    film = timed(b, music)
    film["timeline"] = timeline(film)
    film["board"] = str(bid)
    film["cards"], film["feed"] = stills_of(film)
    film["music"] = {**b.get("music", {}), **{k: music.get(k) for k in ("file", "bpm", "origin", "recipe") if music.get(k)}}
    _env.write_json("film.json", film)
    _env.write_json("timeline.json", {"fps": FPS, "seconds": film["seconds"], "beats": film["timeline"]})
    hits = sum(len(x["hits"]) for x in film["beats"])
    print(f"board {bid} ({b['style']}): {len(film['beats'])} beats at {film['bpm']} bpm, every cut on a beat; {hits} hits; "
          f"{film['seconds']:.1f} s -> film.json")
    return 0


# ------------------------------------------------------------------ sheets
def sheet_of(frames, label, font):
    from PIL import Image, ImageDraw
    ims = [Image.open(o).convert("RGB") for o in frames]
    ims = [im.resize((300, round(300 * im.height / im.width))) for im in ims]
    sheet = Image.new("RGB", (len(ims) * 312 + 12, max(im.height for im in ims) + 64), "#111111")
    dr = ImageDraw.Draw(sheet)
    dr.text((12, 10), label, fill="#f0e6d0", font=font)
    for i, im in enumerate(ims):
        sheet.paste(im, (12 + i * 312, 52))
    return sheet


# one plain sentence per style, under its frames on out/boards.png
LOOKS = {
    "kinetic-type": "Your words slammed big and bold on flat color, cut hard to a fast beat.",
    "cinematic-letterbox": "Your photographs between black bars, with slow dissolves and quiet subtitles, scored like a trailer.",
    "swiss-grid": "Clean white pages with your photographs set in a grid and crisp type, cut to a steady pulse.",
    "editorial-quiet": "Your photographs in wide paper margins with small serif captions, calm and unhurried.",
    "scrapbook": "Your photographs as taped prints with handwritten lines, warm and homemade.",
    "analog-home-movie": "Your photographs as old home movie footage, with typed captions and soft film light.",
}


def look_beats(b):
    """The three beats that show a board's look: its hook, its middle beat (the middle one of their words, where there
    are) and its closer."""
    parts = [x["part"] for x in b["beats"]]
    mids = [i for i, p in enumerate(parts) if p in ("build", "detail")] or [len(parts) // 2]
    mids = [i for i in mids if b["beats"][i]["words"]] or mids
    return 0, mids[len(mids) // 2], len(parts) - 1


def looks_sheet(boards, where, font):
    """out/boards.png: each board's three look beats at half size in a row, its number and style name over them and its
    one sentence under them."""
    from PIL import Image, ImageDraw
    small = _env.pil_font(26, "text")
    rows = []
    for n, b in boards.items():
        frames = [o for w, o in where if w == n]
        ims = [Image.open(frames[i]).convert("RGB") for i in look_beats(b)]
        fw, fh = ims[0].size
        row = Image.new("RGB", (3 * fw + 4 * 24, fh + 150), "#111111")
        dr = ImageDraw.Draw(row)
        dr.text((24, 18), f"{n}  {b['name']}", fill="#f0e6d0", font=font)
        for k, im in enumerate(ims):
            row.paste(im.resize((fw, fh)), (24 + k * (fw + 24), 70))
        dr.text((24, fh + 92), LOOKS.get(b["style"], b["name"]), fill="#cfc6b4", font=small)
        rows.append(row)
    whole = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), "#111111")
    y = 0
    for r in rows:
        whole.paste(r, (0, y))
        y += r.height
    Path("out").mkdir(exist_ok=True)
    whole.save(_env.staged("out/boards.png"))
    os.replace(_env.staged("out/boards.png"), "out/boards.png")


def cmd_sheets(a):
    _env.need("PIL")
    from PIL import Image
    boards = load_boards()
    found = issues(boards)
    if found:
        sys.exit("\n".join(f"not rendered: {x}" for x in found))
    _env.engine()
    with chunks.lock("render", "sheets-report") as run:
        jobs, where = [], []
        for n, b in boards.items():
            t = timed(b)
            tl = timeline(t)
            d = BOARDS / n / "frames"
            (BOARDS / n / "sheet.png").unlink(missing_ok=True)
            shutil.rmtree(d, ignore_errors=True)
            for i, x in enumerate(tl):
                out = d / f"{i + 1:02d}-{x['id']}.png"
                jobs.append({"type": "still", "composition": "Film", "props": {"board": t}, "frame": rest(tl, i, t),
                             "out": str(out.resolve()), "scale": 0.5})
                where.append((n, out))
        rep = _env.render(run, jobs, "render/sheets-report.json")
        font = _env.pil_font(30, "text")
        sheets = []
        for n, b in boards.items():
            frames = [o for w, o in where if w == n and o.exists()]
            if not frames:
                continue
            sh = sheet_of(frames, f"{n}  {b['name']}", font)
            sh.save(_env.staged(BOARDS / n / "sheet.png"))
            os.replace(_env.staged(BOARDS / n / "sheet.png"), BOARDS / n / "sheet.png")
            sheets.append(sh)
            print(f"board {n} ({b['style']}): {len(frames)} frames -> {BOARDS / n / 'sheet.png'}")
        if all(o.exists() for _, o in where):
            looks_sheet(boards, where, font)
            print("the three looks side by side -> out/boards.png")
        for x in rep.get("findings", []):
            print("finding:", x["text"][:300])
        return 1 if rep.get("failed") else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    ap.add_argument("files", nargs="*", help="check: storyboard files to check alone")
    a = ap.parse_args()
    _env.enter_run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
