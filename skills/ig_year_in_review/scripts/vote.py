#!/usr/bin/env python3
"""Movement 3 (the panel scores the three storyboards, and the look is picked), the critic's four reads of the timed
cut, and the critics' score of the film.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot    # build/vote/ballot.md + build/vote/scores.json to fill in (scores and the swap test)
    python3 S/scripts/vote.py tally     # build/vote.md + build/winner.json (the panel's board, when it passes the swap test)
    python3 S/scripts/vote.py pick N|STYLE [--why "one line"]
                                        # the person's look (1, 2, 3 in out/boards.png's order, or the style's id) ->
                                        # build/winner.json; everything made from another look goes
    python3 S/scripts/vote.py timed     # build/critic/timed.json to fill in: the four reads of the timed cut
    python3 S/scripts/vote.py cut       # build/critic/cut-N.json to fill in for the newest render (next round N; the
                                        # newest round again while the reel in out/ is the one it scores)
    python3 S/scripts/vote.py verdict   # SHIP at the bar (the mean of the latest round's scores 4.5 or more and none
                                        # under 4), else the worst thing

The draft makes three storyboards, one a style (storyboards/boards.json names them in order). The panel scores all
three and the swap test decides which can be made; tally writes the panel's board to winner.json. The person then
picks the look: pick writes their board to winner.json with the reason, and removes the cut, the music, the preview,
the reads and the scores made from any other look, so the run goes on from the pick with nothing of another look in it.

The panel (S/critic/critic.md has each critic's brief): a motion designer, an editor and the person, modeled from
taste.md. Each scores every storyboard 1-5 on the seven criteria below and writes one paragraph. The motion designer
also applies the swap test to each board's three compositions (the hook, a month and the closer, on its sheet): a
composition passes when their photographs, their moments and their words move the frame (a month's slit cut along
its own photograph's line with their own line for that month standing on it is the passing case), and fails when
another person's year would sit in it unchanged. A board with a composition that fails is not the panel's choice.
Before the film renders, the editor watches the timed cut (build/preview/film.mp4 and its strip) and makes the four
reads below from what it shows and plays; film.py render waits for all four to pass. The finished cut is scored by the
motion designer and the person on the same criteria.

Every round before deliver scores the half-size proof (film.py render --proof, out/proof.mp4): `cut` reads the newest
render and its first line says when that is the proof. Once the full-size film of the same cut is rendered, `cut` moves
the latest round to it and empties its `type` scores: the critics read the type again on the full-size film, at the
size a phone shows it, and the round is complete once they have scored it there.
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import proof  # noqa: E402

BAR = (4.5, 4)  # the film ships when its scores' mean is at least the first and no score is under the second
RESTS = ("hook", "month", "closer")
READS = {
    "carried": "one element is carried across every transition (the dot and its line)",
    "sound": "a sound where each beat lands and nowhere else, under the music",
    "swap": "the motion belongs to the photograph: under another photograph the move stops making sense",
    "held": "one held thing per beat",
}

CRITERIA = {
    "professional": "it looks like a professional motion designer made it",
    "them": "it is unmistakably them (their photos carry it, their colors, their voice)",
    "pacing": "the pacing holds attention to the end",
    "type": "type is a system, not a default",
    "transitions": "every transition is intentional",
    "music": "the music and the cuts agree",
    "ending": "the ending makes them want to post it",
}
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def boards():
    """The drafted boards' styles, in order, once each has its sheet."""
    order = (_env.read_json("storyboards/boards.json") or {}).get("order") or []
    out = [b for b in order if (Path("storyboards") / b / "sheet.png").exists()]
    if not order or len(out) < len(order):
        sys.exit(f"{len(out)} of {len(order) or 3} storyboards with sheets: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def blank_swap(ids):
    return {i: {r: {"pass": None, "why": ""} for r in RESTS} for i in ids}


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every storyboard 1-5 on each criterion, as each critic, and write one paragraph per board "
             "(what works, what fails, what you would change). Look at each style sheet before scoring.", "",
             "Then the swap test, as the motion designer, on the board's three compositions (the hook, a month and the "
             "closer, left to right on its sheet): `pass` is true when their photographs, their moments and their words "
             "move the frame (a line, a crop, their own line standing on it), false when another person's year would "
             "sit in it unchanged; a month's slit cut along its photograph's own line under their words is the passing "
             "case. `why` names what in the frame is theirs, in one sentence. A board that fails one is not the panel's choice.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path("storyboards") / b
        lines += [f"### {b}", "", f"- storyboard: {sb.resolve() / 'storyboard.md'}",
                  f"- style sheet: {sb.resolve() / 'sheet.png'} (frames in {sb.resolve() / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, dict(blank(PANEL, bs), swap=blank_swap(bs)))
    print(f"ballot -> {(d / 'ballot.md').resolve()}; scores and the swap test to fill -> {f.resolve()}")
    return 0


def problems(data, panel, ids):
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            for k in CRITERIA:
                v = (e.get("scores") or {}).get(k)
                if not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / board {i} / {k}: needs a whole number 1-5 (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / board {i}: the paragraph needs at least 25 words")
    return bad


def swap_problems(data, ids):
    bad = []
    for i in ids:
        for r in RESTS:
            e = ((data.get("swap") or {}).get(i) or {}).get(r) or {}
            if not isinstance(e.get("pass"), bool):
                bad.append(f"swap / board {i} / {r}: pass needs true or false")
            if len((e.get("why") or "").split()) < 8:
                bad.append(f"swap / board {i} / {r}: why needs a sentence")
    return bad


def cmd_tally(a):
    ids = boards()
    data = _env.read_json("vote/scores.json")
    if not data:
        sys.exit("vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids) + swap_problems(data, ids)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    tot = {i: sum(sum(data["critics"][c]["boards"][i]["scores"].values()) for c in PANEL) for i in ids}
    person = {i: sum(data["critics"]["person"]["boards"][i]["scores"].values()) for i in ids}
    passed = {i: all(data["swap"][i][r]["pass"] for r in RESTS) for i in ids}
    if not any(passed.values()):
        print("no board passes the swap test: every one has a composition whose photograph could be swapped; "
              "choose other lines for those months in picks.json and draft again")
        return 1
    order = sorted(ids, key=lambda i: (not passed[i], -tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if passed[i] and tot[i] == tot[win]]
    lines = ["# the vote", "", f"The panel's board: {win} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""),
             "",
             "| critic | " + " | ".join(f"board {i}" for i in ids) + " |", "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(str(sum(data['critics'][c]['boards'][i]['scores'].values())) for i in ids) + " |")
    lines.append("| total | " + " | ".join(f"**{tot[i]}**" for i in ids) + " |")
    lines.append("| swap test | " + " | ".join("pass" if passed[i] else "fails: " + ", ".join(r for r in RESTS if not data["swap"][i][r]["pass"]) for i in ids) + " |")
    lines += ["", "## scores by criterion", "", "| board | critic | " + " | ".join(CRITERIA) + " |", "|---|---|" + "---|" * len(CRITERIA)]
    for i in ids:
        for c in PANEL:
            s = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {i} | {c} | " + " | ".join(str(s[k]) for k in CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### {i}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
        lines += [f"**The swap test.** " + " ".join(f"{r}: {'passes' if data['swap'][i][r]['pass'] else 'fails'}, {data['swap'][i][r]['why'].strip()}" for r in RESTS), ""]
    _env.write_text("vote.md", "\n".join(lines))
    clear_cut(win)
    _env.write_json("winner.json", {"board": win, "name": win, "by": "panel", "totals": tot, "order": order, "swap": passed,
                                    "swap_passed": passed[win], "tie_broken_by_person": len(tie) > 1})
    print(f"the panel's board: {win}, totals {tot}, swap test {passed} -> vote.md, winner.json; the person picks the look "
          "next (vote.py pick)")
    return 0


# everything made from one look: the cut, its music, its preview, its render report, and the reads and scores of it
MADE = ("film.json", "music.json", "music", "preview", "render/film-report.json", "critic/timed.json")


def clear_cut(board):
    """Remove what was made from a look other than `board`, so nothing of it reaches the film."""
    if (_env.read_json("winner.json") or {}).get("board") == board:
        return
    for name in MADE:
        p = Path(name)
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for p in rounds():
        p.unlink()


def cmd_pick(a):
    ids = boards()
    want = str(a.board).strip()
    board = ids[int(want) - 1] if want.isdigit() and 1 <= int(want) <= len(ids) else want
    if board not in ids:
        sys.exit(f"no look {want!r}: pick 1 to {len(ids)} (out/boards.png's order) or one of {', '.join(ids)}")
    panel = _env.read_json("winner.json") or {}
    clear_cut(board)
    _env.write_json("winner.json", {"board": board, "name": board, "by": "person", "why": (a.why or "").strip(),
                                    "order": ids, "panel": panel.get("board") if panel.get("by") == "panel" else panel.get("panel")})
    print(f"the look: {board}" + (f" ({a.why.strip()})" if a.why else "") + " -> winner.json; next: music.py find, then storyboard.py snap")
    return 0


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def timed_ok(t):
    """Whether a timed read passes: every one of the four reads written and passed."""
    reads = (t or {}).get("reads") or {}
    return all((reads.get(k) or {}).get("pass") is True and len(((reads.get(k) or {}).get("read") or "").split()) >= 25 for k in READS)


def cmd_timed(a):
    f = _env.read_json("film.json") or {}
    pv = _env.read_json("preview/preview.json") or {}
    if not f or pv.get("hash") != f.get("hash"):
        sys.exit("build/preview/preview.json is not for the current cut: run storyboard.py snap and film.py preview first")
    path = Path("critic/timed.json")
    old = _env.read_json(path) or {}
    if old.get("hash") == f["hash"] and all(isinstance(((old.get("reads") or {}).get(k) or {}).get("pass"), bool) for k in READS):
        print(f"build/{path} already holds the reads of this cut: {'pass' if timed_ok(old) else 'fail'}")
        return 0 if timed_ok(old) else 2
    _env.write_json(path, {"hash": f["hash"], "style": f["style"], "reads": {k: {"pass": None, "read": ""} for k in READS},
                           "film": str(Path("preview/film.mp4").resolve()), "strip": pv.get("strip2"),
                           "measured": {k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_event_frame")}})
    print(f"the four reads, as the editor: watch {Path('preview/film.mp4').resolve()} and its strip {pv.get('strip2')}, "
          f"and make each read from what the film shows and plays, then fill in {path.resolve()}: for each read a pass (true or false) and a read "
          "of at least 25 words naming the beats it holds and fails on:\n" + "\n".join(f"  {k}: {v}" for k, v in READS.items()))
    return 0


def cmd_cut(a):
    """A round for the newest reel in out/ (the proof while out/proof.mp4 is there), once the render report names the
    current cut: the newest round when it scores this same reel, the same round with its type read again when the reel
    is the full-size film of the cut that round scored on its proof, a new one only when the reel changed."""
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    reel = Path("../out/film.mp4")
    scale = proof.scale(reel)
    film = proof.newest(reel)
    shown = Path("out") / film.name
    if scale != 1:
        print(proof.reading(shown))
    f = _env.read_json("film.json") or {}
    if not f or (_env.read_json("render/film-report.json") or {}).get("hash") != f.get("hash"):
        sys.exit("out/ holds no whole render of the current cut (build/render/film-report.json names it): run film.py render --proof first")
    digest = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    mine = rounds()
    last = _env.read_json(mine[-1]) if mine else {}
    if last.get("film") == digest:
        print(f"round {last.get('round')} ({mine[-1].resolve()}) already scores this reel: fill it in after watching "
              f"{shown} and the frames in build/frames/")
        return 0
    if scale == 1 and last.get("scale") == proof.SCALE and last.get("cut") == f.get("hash"):
        # the full-size film of the cut the round scored on its proof: the same round, with the type read at full size
        last.update(film=digest, scale=1, proof_film=last["film"])
        for c in CUT_PANEL:
            last["critics"][c]["boards"]["film"]["scores"]["type"] = None
        _env.write_json(mine[-1], last)
        print(f"round {last.get('round')} moves to the full-size {shown}: as each critic, read the type again on it and on "
              f"the frames in build/frames/, at the size a phone shows it, and score type in {mine[-1].resolve()}; the "
              "other scores stand")
        return 0
    n = len(mine) + 1
    out = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = digest
    data["scale"] = scale
    data["cut"] = f.get("hash")
    data["fixed"] = "" if n > 1 else None
    _env.write_json(out, data)
    print(f"round {n}: fill in {out.resolve()} after watching {shown} and the frames in build/frames/"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def at_bar(scores):
    """Whether a round's scores reach the bar: their mean at least BAR[0] and none under BAR[1]."""
    return sum(scores) / len(scores) >= BAR[0] and min(scores) >= BAR[1]


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    bad = problems(data, CUT_PANEL, ["film"])
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    scores = [(data["critics"][c]["boards"]["film"]["scores"][k], k, c) for c in CUT_PANEL for k in CRITERIA]
    values = [x[0] for x in scores]
    mean = round(sum(values) / len(values), 2)
    # a round on the proof ends in the full-size render, where the critics read the type once more before deliver
    full = ("; render the full-size film (film.py render), run qa.py check, then vote.py cut: the critics read the type "
            "again at full size" if data.get("scale") == proof.SCALE else "")
    if at_bar(values):
        print(f"SHIP: round {data.get('round')}, mean {mean}, none under {BAR[1]}" + full)
        return 0
    low = min(values)
    worst = "; ".join(f"{k} ({CRITERIA[k]}), {c}" for v, k, c in scores if v == low)
    if len(rs) >= 2:
        print(f"round {data.get('round')}: mean {mean}, lowest {low} on {worst}, under the bar ({BAR[0]} mean, none under "
              f"{BAR[1]}). The one fix is spent: deliver this cut; deliver.py writes its scores into build/brief.md" + full)
        return 2
    print(f"FIX ONCE: mean {mean}, lowest {low} on {worst}. Read the paragraphs, fix the one cause behind them, render "
          "the proof again (film.py render --proof), then run vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timed", "cut", "verdict"])
    ap.add_argument("board", nargs="?", help="pick: 1, 2, 3 (out/boards.png's order) or the style's id")
    ap.add_argument("--why", default="", help="pick: the reason, in one line")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.board:
        ap.error("pick needs the look: 1, 2, 3 or the style's id")
    _env.enter_build()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timed": cmd_timed, "cut": cmd_cut,
            "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
