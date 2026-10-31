#!/usr/bin/env python3
"""The three storyboards of the drive film, one per style, their sheets, and the one the person picks.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/storyboard.py draft [--style ID]  # storyboards/A, B and C/board.json, one per style; exit 1 on a
                                                        # bounds fault in any of them
    python3 S/scripts/storyboard.py check               # the three boards' bounds and type floor again, from their files
    python3 S/scripts/storyboard.py sheets              # storyboards/<L>/sheet.png (the hook, the densest post and the
                                                        # closer of each) and out/boards.png, the three side by side
    python3 S/scripts/storyboard.py pick A|B|C --by person|taste --reason "..."
                                                        # board.json is that board; winner.json names it and why

The story is the kit's and is the same in every board: the person's grid before, the posts that break its first screen,
the next posts dropping into the grid one by one in the frame the film carries, and their profile with the nine in
place at the end. A board is that story set in one style: drive.py builds it from the style card (styles/<id>.json),
which supplies the faces and their case, the colors (its palette rule over their taste and palette), the easing, the
finish, the camera's pace, the move each beat makes (chosen from what the beat shows within the card's allowlist), the
caption's entrance and the closer's shape. The three styles are A swiss-grid, B kinetic-type and C editorial-quiet;
with no --style the style taste.json names (`style`, from their type direction) takes A and the two others follow;
--style names any style, and the two trio styles that differ most from it take B and C.

Each board is drafted at its own music's tempo: the card's recipe (music/recipes.json), its tempo chosen from the
recipe's range by the run's name, so `music.py make` later composes the bed at the tempo the cut is on.

draft writes, per board, storyboards/<L>/board.json and storyboards/<L>/storyboard.md, in every format (`boards`:
reel 9:16, landscape 16:9, square 1:1, each re-placed for its frame). The bounds check runs on every format: each
page's words (the hook's title and each held post's caption) inside the format's type area and the page's line box at
a cap height of FLOOR px or more, off the photograph where the card sets them beside it, and the closer's header
inside the type area. A fault names the board, the format, the beat and the line, and draft exits 1.

The rests are each board's settled frames: the hook with its words, the densest post and the closer. sheets renders
them from the composition the film uses. pick copies the chosen board to board.json and writes winner.json, and
everything made from an earlier pick (the music master, the preview, the films, the verdicts) goes, so the steps
after the pick run again on the new board in the same run.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import drive  # noqa: E402
import grade  # noqa: E402
import music_engine  # noqa: E402
import studio  # noqa: E402
from plan import bare, cell_words  # noqa: E402

PUBLIC = Path("public")
BOARDS = Path("storyboards")
FPS = drive.FPS
FORMATS = ("reel", "landscape", "square")
FLOOR = drive.FLOOR
LETTERS = compose.LETTERS
# what a pick makes stale: every file the steps after the pick wrote from the board before it
AFTER_PICK = ("winner.json", "preview", "render/film.json", "qa", "brief.md")
# what out/ keeps through a pick: the looks to choose from and their grid as it is now
KEEP_OUT = ("boards.png", "grid-before.png")


HOOK_FRAMES = 30
LENGTH = (15, 30)


def length_band(n):
    """The reel's length band: 15-30 s for nine posts; fewer posts make a shorter film, so the floor scales with them."""
    return (round(LENGTH[0] * min(9, n) / 9, 2), LENGTH[1])


def hook_frame(reel):
    """The frame of the hook's first event: the hook line entering on the first frame, else the frame landing on the
    first post that breaks the grid."""
    if reel["hook"].get("title"):
        return 0
    land = next(k for k in reel["beats"][0]["layers"][1]["keys"] if k["ease"] == "land")
    return round(land["t"] * drive.PULSE)


# ------------------------------------------------------------------ the before grid and the posts
def hexc(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def lum(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def before_posts(grid):
    PUBLIC.joinpath("before").mkdir(parents=True, exist_ok=True)
    out = []
    for c in grid["cells"]:
        pos = c["pos"] + 1
        file = None
        size = None
        if c.get("cover") and Path(c["cover"]).exists():
            file = f"before/{pos:02d}.jpg"
            tmp = _env.part(PUBLIC / file)
            shutil.copyfile(c["cover"], tmp)
            os.replace(tmp, PUBLIC / file)
            from PIL import Image
            size = list(Image.open(PUBLIC / file).size)
        colors = (c.get("a") or {}).get("colors") or [{"rgb": [120, 100, 80]}]
        by_l = sorted(colors, key=lambda x: lum(x["rgb"]))
        out.append({"pos": pos, "caption": cell_words(c.get("caption"), lambda t: len(t) <= 40), "file": file, "size": size,
                    "plate": [hexc(by_l[-1]["rgb"]), hexc(by_l[0]["rgb"])], "flags": sorted(set(c.get("flags") or []))})
    return out


def breaks_of(before):
    """The posts that break the first screen, among the first nine with their cover on the wall: the off-palette and
    text posts, else the three whose colors stand furthest from the rest of the nine; ordered around their middle so
    the line through them draws one shape. None when no post among the nine has its cover."""
    first = [b for b in before if b["pos"] <= 9 and b.get("file") and b.get("size")]
    if not first:
        return []
    out = [b for b in first if set(b["flags"]) & {"clash", "text"}]
    if len(out) < 2:
        rgb = {b["pos"]: [int(h[i:i + 2], 16) for h in b["plate"] for i in (1, 3, 5)] for b in first}
        mid = [sum(v[k] for v in rgb.values()) / len(rgb) for k in range(6)]
        out = sorted(first, key=lambda b: -math.dist(rgb[b["pos"]], mid))[:3]
    xy = {b["pos"]: ((b["pos"] - 1) % 3, (b["pos"] - 1) // 3) for b in out}
    cx = sum(x for x, _ in xy.values()) / len(xy)
    cy = sum(y for _, y in xy.values()) / len(xy)
    return sorted(xy, key=lambda p: (math.atan2(xy[p][0] - cx, -(xy[p][1] - cy)) + 2 * math.pi) % (2 * math.pi))


def next_posts(plan):
    """The new posts as the film shows them: each page carries the words its photograph came with (`said`) whole, else
    the post's caption as the plan wrote it in their voice; the plan's caption is also the moment, for the storyboard,
    and its shot is the clip it asks for."""
    files = [s["photo"] for s in plan["slots"]]
    grade.grade_photos(files)
    out = []
    for s in plan["slots"]:
        p = {"n": s["n"], "file": grade.graded_name(s["photo"]), "size": s["size"], "crop45": s["crop45"], "crop34": s["crop34"],
             "focal": s.get("focal"), "caption": bare(s.get("said") or s.get("caption")),
             "moment": s.get("caption") or "", "shot": s.get("shot") or "", "follows": s["follows"], "place": s["place"]}
        if s.get("lesson"):
            p["lesson"] = s["lesson"]
        out.append(p)
    return out


# ------------------------------------------------------------------ the bounds check
def faults(fmt, board):
    """Bounds and type floor of one format's board: each page's words inside the type area and its line box and off a
    photograph they stand beside, and the closer's header inside the type area, cap height >= FLOOR."""
    compose.use(board["style"])
    bad = [f"{fmt} {name}: the words '{text}' do not fit their place at the type floor" for name, text in (board.get("unfit") or {}).items()]
    W, H = board["format"]["width"], board["format"]["height"]
    safe = board["system"]["safe"][fmt]
    # each page's words: inside the type area and the page's line box, at the floor, and off the photograph on a page
    # that sets them beside it
    pages = [("hook", board.get("page"))] + [(b["id"], b["layers"][0].get("page")) for b in board["beats"] if b["id"].startswith("post-")]
    for name, pg in pages:
        if not pg:
            continue
        box, pic = pg["box"], pg["pic"]
        for ln in pg["lines"] + ([dict(pg["label"], face=pg["label"]["face"])] if pg.get("label") else []):
            face = ln.get("face", "display")
            cap = ln["size"] * drive.CAP[face]
            x1 = ln["x"] + drive.em(ln["text"], face) * ln["size"]
            if face == "display" and cap < FLOOR - 0.5:
                bad.append(f"{fmt} {name}: '{ln['text']}' sets at a cap height of {cap:.0f} px, under {FLOOR}")
            if ln["x"] < safe["left"] - 1 or x1 > W - safe["right"] + 1 or ln["y"] - cap < safe["top"] - 1 or ln["y"] > H - safe["bottom"] + 1:
                bad.append(f"{fmt} {name}: '{ln['text']}' leaves the type area (x {ln['x']:.0f} to {x1:.0f}, baseline {ln['y']:.0f})")
            elif x1 > box[2] + 1 or ln["y"] > box[3] + 1:
                bad.append(f"{fmt} {name}: '{ln['text']}' runs out of its line box (x to {x1:.0f}, baseline {ln['y']:.0f})")
            if not pg["over"] and ln["x"] < pic[2] and pic[0] < x1 and ln["y"] - cap < pic[3] and pic[1] < ln["y"]:
                bad.append(f"{fmt} {name}: '{ln['text']}' stands on the photograph")
    # the closer's header: every line inside the type area and at the floor
    for ln in (board.get("header") or {}).get("lines", []):
        cap = ln["size"] * drive.CAP[ln["face"] if ln["face"] == "display" else "text"]
        if cap < FLOOR - 0.5 and ln["name"] != "bio":
            bad.append(f"{fmt} closer: '{ln['text']}' sets at a cap height of {cap:.0f} px, under {FLOOR}")
        if ln["y"] - cap < safe["top"] - 1 or ln["y"] > H - safe["bottom"] + 1:
            bad.append(f"{fmt} closer: '{ln['text']}' leaves the type area (baseline {ln['y']:.0f})")
    return bad


# ------------------------------------------------------------------ draft
def tempo_of(card, brief, seed):
    """The tempo the board is cut on: the card's recipe (or the one the brief's words name), its tempo picked from the
    recipe's range by the run's name, as music.py make will compose it."""
    book = music_engine.recipes()
    _, recipe, _ = music_engine.resolve(book, card["music"], brief.get("styles") or [], brief.get("avoid") or [])
    return music_engine.tempo(recipe, None, None, seed)


def boards_of(style, tempo, before, nine, plan, audit, breaks, taste, palette, handle, bio):
    """One style's board in every format: the reel's first, and every other format on the reel's beat frames."""
    args = (before, nine, plan, audit, breaks, taste, palette, handle, bio)
    reel = drive.build("reel", *args, style=style, tempo=tempo)
    frames = [b["frames"] for b in reel["beats"][:-1]]
    return {fmt: reel if fmt == "reel" else drive.build(fmt, *args, frames, style=style, tempo=tempo) for fmt in FORMATS}


def board_of(letter, style, inputs, first_day, handle):
    before, nine, plan, audit, breaks, taste, palette, bio = inputs
    card = compose.card(style)
    tempo = tempo_of(card, (taste or {}).get("music") or {}, Path.cwd().name)
    boards = boards_of(style, tempo, before, nine, plan, audit, breaks, taste, palette, handle, bio)
    reel = boards["reel"]
    board = {"letter": letter, "style": style, "name": card["name"], "tempo": tempo, "handle": handle, "first_day": first_day,
             "fps": FPS, "frames": sum(b["frames"] for b in reel["beats"]), "seconds": reel["seconds"],
             "stop_seconds": reel["stop_seconds"],
             "before": [{k: b[k] for k in ("pos", "caption", "file", "size", "plate")} for b in before],
             "nine": [{k: p[k] for k in ("n", "file", "size", "crop45", "crop34", "caption", "lesson") if k in p} for p in nine],
             "places": {str(p["n"]): p["place"] for p in nine}, "breaks": breaks, "boards": boards,
             "rests": drive.rests(reel), "cuts_at": [c for c in drive.planned_cuts(reel) if c > 0],
             "hook_frame": hook_frame(reel), "grade": hashlib.sha256(Path("grade.json").read_bytes()).hexdigest()[:16]}
    bad = [f"{letter} {f}" for fmt, b in boards.items() for f in faults(fmt, b)]
    board["check"] = {"pass": not bad, "faults": bad}
    board["hash"] = hashlib.sha256(json.dumps(board, sort_keys=True).encode()).hexdigest()[:16]
    return board, bad


def reset_after_pick(keep=None):
    """Clear the pick and everything made from it. The critic's cut rounds of board `keep` stay, so the redraft a
    FIX ONCE asks for counts as that board's one fix; a pick of another board starts its rounds at one."""
    for p in Path("critic").glob("*") if Path("critic").is_dir() else ():
        if not (keep and p.name.startswith("cut-") and (_env.read_json(p) or {}).get("board") == keep):
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    if Path("critic").is_dir() and not any(Path("critic").iterdir()):
        Path("critic").rmdir()
    for name in AFTER_PICK:
        p = Path(name)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink(missing_ok=True)
    for p in Path("out").glob("*") if Path("out").is_dir() else ():
        if p.name not in KEEP_OUT:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in Path("music").glob("master.*"):
        p.unlink()


def cmd_draft(a):
    _env.need("PIL")
    grid_ = _env.read_json("grid.json")
    plan = _env.read_json("plan.json")
    if not grid_ or "cells" not in grid_:
        sys.exit("grid.json is missing: run research.py first")
    if not plan or not plan.get("slots"):
        sys.exit("plan.json is missing: run plan.py draft and check first")
    if plan.get("drafted"):
        print("note: plan.json still holds the drafted captions; write them in their voice and run plan.py check", file=sys.stderr)
    taste, palette, audit = _env.read_json("taste.json"), _env.read_json("palette.json"), _env.read_json("audit.json")
    styles = compose.trio(a.style or (taste or {}).get("style"))
    # a new draft is a new choice: the pick, the vote and everything made from them go first, and each board's file is
    # written last; the picked board's cut rounds stay for the pick that follows
    reset_after_pick(keep=(_env.read_json("winner.json") or {}).get("board"))
    for p in (Path("board.json"), Path("vote.md")):
        p.unlink(missing_ok=True)
    shutil.rmtree("vote", ignore_errors=True)
    if BOARDS.exists():
        shutil.rmtree(BOARDS)
    studio.public()
    before = before_posts(grid_)
    nine = next_posts(plan)
    breaks = breaks_of(before)
    first = dt.date.fromisoformat(plan["slots"][0]["date"])
    first_day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][first.weekday()]
    handle = plan.get("handle") or "you"
    bio = (_env.read_json("library.json") or {}).get("bio")
    inputs = (before, nine, plan, audit, breaks, taste, palette, bio)
    every = []
    for letter, style in zip(LETTERS, styles):
        board, bad = board_of(letter, style, inputs, first_day, handle)
        _env.write_text(BOARDS / letter / "storyboard.md", storyboard_md(board))
        _env.write_json(BOARDS / letter / "board.json", board)
        every += bad
        reel = board["boards"]["reel"]
        moves = sorted({x["move"] for x in reel["timeline"]["beats"] if x["move"]})
        print(f"board {letter}: {style}, {len(nine)} posts, {board['seconds']:.1f} s at {board['tempo']:g} bpm, "
              f"moves {', '.join(moves)}, closer {reel['closerShape']['name']}; "
              + ("bounds and type floor hold" if not bad else f"{len(bad)} faults") + f" -> {BOARDS / letter / 'board.json'}")
    for f in every:
        print("FAULT", f)
    print("next: storyboard.py sheets, then show out/boards.png and pick (storyboard.py pick A|B|C)")
    return 1 if every else 0


def drafted():
    found = {L: _env.read_json(BOARDS / L / "board.json") for L in LETTERS}
    if not all(found.values()):
        sys.exit("the three boards are missing: run storyboard.py draft first")
    return found


def cmd_check(a):
    bad = []
    for L, board in drafted().items():
        bad += [f"{L} {f}" for fmt, b in board["boards"].items() for f in faults(fmt, b)]
    for f in bad:
        print("FAULT", f)
    print("check: " + ("the three boards hold their bounds and type floor" if not bad else f"{len(bad)} faults"))
    return 1 if bad else 0


def storyboard_md(board):
    reel = board["boards"]["reel"]
    at, out = 0, [f"# Storyboard {board['letter']}: {board['name']}, reel", "",
                  f"Cut at {board['tempo']:g} bpm, the tempo its music is composed at.", "",
                  "| beat | from (s) | move | what the move reveals | what it carries across the cut |", "|---|---|---|---|---|"]
    for b, s in zip(reel["beats"], reel["story"]):
        a0, a1 = at / FPS * board["tempo"] / 60, (at + b["frames"]) / FPS * board["tempo"] / 60
        move = ", then ".join(t["move"] for t in reel["timeline"]["beats"] if t["move"] and t["at"] < a1 - 0.01 and t["end"] > a0 + 0.01) or "held still"
        out.append(f"| {b['id']} | {at / FPS:.2f} | {move} | {s['reveals']} | {s['carries']} |")
        at += b["frames"]
    out += ["", "## Sound", "", "Music: not yet; music.py master names it here.",
            "Mixed: not yet; music.py master writes the bed's and the effects' loudness here.", "",
            f"One cue where each beat lands ({len(reel['sound'])} cues over {len(reel['beats'])} beats), under the music:", "",
            "| at (s) | cue | what it is on |", "|---|---|---|"]
    for c in reel["sound"]:
        out.append(f"| {c['at'] * 60 / reel['bpm']:.2f} | {c['kind']} | {c['what']} |")
    out += ["", "## Clips", ""]
    for c in reel["clips"]:
        out.append(f"- {c['id']} ({c['beat']}, {c['seconds']} s, {c['image']}): {c['prompt']}. Stands in: {c['stand_in']}.")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ sheets
REST_NAMES = ("hook", "dense", "closer")


def cmd_sheets(a):
    found = drafted()
    jobs = [studio.still(b["boards"]["reel"], f, BOARDS / L / f"{rest}.png")
            for L, b in found.items() for rest, f in b["rests"].items()]
    _env.need("PIL")
    from PIL import Image, ImageDraw
    with studio.lock("sheets") as run:
        # the sheets a ballot reads go before the frames they are made from change
        for L in found:
            (BOARDS / L / "sheet.png").unlink(missing_ok=True)
        Path("out/boards.png").unlink(missing_ok=True)
        rep = studio.render(jobs, "sheets", run)
        studio.publish("sheets", rep)
        for f in rep.get("findings", []):
            print("finding:", f["text"][:300])
        if rep.get("failed"):
            print(f"sheets: {rep['failed']} of {len(jobs)} frames failed; render/sheets.log says why")
            return 1
        w, h, gap = 360, 640, 16
        rows = []
        for L, b in found.items():
            ims = [Image.open(BOARDS / L / f"{r}.png").convert("RGB").resize((w, h), Image.LANCZOS) for r in REST_NAMES]
            sheet = Image.new("RGB", (3 * w + 2 * gap, h), "#ffffff")
            for i, im in enumerate(ims):
                sheet.paste(im, (i * (w + gap), 0))
            tmp = _env.part(BOARDS / L / "sheet.png")
            sheet.save(tmp)
            os.replace(tmp, BOARDS / L / "sheet.png")
            rows.append((L, b, sheet))
        # out/boards.png: the three looks side by side, each named the way the person can ask for it
        label = 64
        both = Image.new("RGB", (3 * (3 * w + 2 * gap) + 2 * 3 * gap, h + label), "#ffffff")
        d = ImageDraw.Draw(both)
        font = _env.pil_font(36, "text")
        for i, (L, b, sheet) in enumerate(rows):
            x = i * (sheet.width + 3 * gap)
            both.paste(sheet, (x, label))
            d.text((x, 12), f"{L}  {b['name'].lower()}", font=font, fill="#111111")
        Path("out").mkdir(exist_ok=True)
        tmp = _env.part(Path("out/boards.png"))
        both.save(tmp)
        os.replace(tmp, Path("out/boards.png"))
        print(f"sheets: {len(jobs)} frames -> storyboards/<A|B|C>/sheet.png and out/boards.png")
        return 1 if rep.get("findings") else 0


# ------------------------------------------------------------------ pick
def cmd_pick(a):
    found = drafted()
    board = found[a.letter]
    if not board["check"]["pass"]:
        sys.exit(f"board {a.letter} fails its bounds check: fix the words or the plan, then run storyboard.py draft")
    if not a.reason.strip():
        sys.exit("--reason is one plain line on why this look")
    reset_after_pick(keep=a.letter)
    others = [L for L in LETTERS if L != a.letter]
    _env.write_json("winner.json", {"board": a.letter, "style": board["style"], "name": board["name"], "by": a.by,
                                    "reason": a.reason.strip(), "others": others, "hash": board["hash"]})
    shutil.copyfile(BOARDS / a.letter / "storyboard.md", Path("storyboard.md"))
    _env.write_json("board.json", board)
    print(f"picked {a.letter} ({board['name']}) by {a.by}: {a.reason.strip()}")
    print("next: music.py find, analyze and master, then film.py render")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft")
    d.add_argument("--style", help="a style id (styles/<id>.json) for board A")
    sub.add_parser("check")
    sub.add_parser("sheets")
    p = sub.add_parser("pick")
    p.add_argument("letter", choices=list(LETTERS))
    p.add_argument("--by", choices=["person", "taste"], required=True)
    p.add_argument("--reason", required=True)
    a = ap.parse_args()
    _env.enter_run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "pick": cmd_pick}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
