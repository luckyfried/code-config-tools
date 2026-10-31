#!/usr/bin/env python3
"""The panel scores the three boards, and two critics score the finished film against the bar.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot     # vote/ballot.md + vote/scores.json to fill in: the three boards, scored
    python3 S/scripts/vote.py tally      # vote.md: each board's mean, best first, and the pick command for the best
    python3 S/scripts/vote.py cut        # critic/cut-N.json to fill in for the rendered film: the newest round when
                                         # it is for the reel render/film.json names, else the next round N
    python3 S/scripts/vote.py verdict    # the latest round against the bar: SHIP, FIX ONCE (rc 2) or DELIVER

The panel (S/critic/critic.md has each critic's brief): a designer, an editor and the person, modeled from taste.md
(is this unmistakably me; would I post it). Each critic scores each board (storyboards/<L>/sheet.png: the hook, the
densest post and the closer; out/boards.png has the three side by side) 1-5 on the five rules a board shows and
writes one paragraph. tally ranks the boards by their mean over every critic and rule; the pick is still made by
storyboard.py pick, by the person or by their taste.
The rendered film is scored by the designer and the person on all seven rules, after qa.py check has measured it.
Each rule's score is the lowest either critic gave it. The bar: a mean of 4.5 or more over the seven rules and no
rule under 4. The verdict: SHIP at the bar; FIX ONCE on the lowest rule that holds the film under the bar and has a
lever in the run (LEVERS), once; otherwise DELIVER, the film delivered as the best cut with every score stated in
brief.md. The verdict never stops a delivery.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CRITERIA = {
    "concept": "R1 one concept carried from the hook to the closer, the closer paying it off",
    "image": "R2 depth and light on every photograph, one grade, a composed closer with nothing cut by the frame",
    "type": "R3 type set as a designer sets it in the style's faces: a scale, letters that enter and settle, inside the safe area",
    "motion": "R4 one continuous camera, anticipation and settle, no two beats alike in a row, the peak held longest",
    "sound": "R5 music that belongs to the style, a cue only where a beat lands, the effects under the music, the stop on the ask",
    "posts": "R6 the nine posts designed in the style, each one a post the person would put up",
    "deliverable": "R7 out/ holds only the deliverables and the review page opens on the film",
}
BOARD = ("concept", "image", "type", "motion", "posts")
MEAN, FLOOR = 4.5, 4
REDRAFT = "storyboard.py draft, sheets and pick (the same board), then music.py make, master and every step after it"
LEVERS = {
    "concept": ("the film's hook line and ask in plan.json (film.hook, film.ask)", "plan.py check, then " + REDRAFT),
    "type": ("the film's hook line and ask in plan.json (film.hook, film.ask)", "plan.py check, then " + REDRAFT),
    "image": ("the grade: taste.json palette", REDRAFT),
    "sound": ("the music: their track at music/source.<ext>, or taste.json music styles", "music.py find, analyze and master, then film.py render and every step after it"),
    "posts": ("each post's caption in plan.json (the line a post sets)", "plan.py check, then " + REDRAFT),
}
PANEL = {"designer": "the designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"designer": "the designer", "person": "the person (from taste.md)"}
LETTERS = ("A", "B", "C")


def boards():
    """The letters of the drafted boards with their style ids, from storyboards/<L>/board.json."""
    got = {L: (_env.read_json(Path("storyboards") / L / "board.json") or {}).get("style") for L in LETTERS}
    got = {L: s for L, s in got.items() if s}
    if not got or not all((Path("storyboards") / L / "sheet.png").exists() for L in got):
        sys.exit("the boards or their sheets are missing: run storyboard.py draft and storyboard.py sheets first")
    return got


def blank(panel, ids, keys):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in keys}, "paragraph": ""} for i in ids}} for c in panel}}


def cmd_ballot(a):
    bs = boards()
    before = Path("grid-before.png").exists()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score each board 1-5 on each rule, as each critic, and write one paragraph each (what works, "
             "what fails, what you would change). Open each board's sheet at full size and its storyboard before scoring"
             + (", with their grid as it is now (grid-before.png) beside them." if before else "."), "",
             "## the rules a board shows", ""] + [f"- `{k}`: {CRITERIA[k]}" for k in BOARD] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", "",
              f"The three side by side: {Path('out/boards.png').resolve()}", ""]
    for L, style in bs.items():
        lines += [f"### {L}: {style}", "", f"- the hook, the densest post and the closer: {(Path('storyboards') / L / 'sheet.png').resolve()}",
                  f"- the storyboard, beat by beat: {(Path('storyboards') / L / 'storyboard.md').resolve()}", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists() or set(((_env.read_json(f) or {}).get("critics") or {}).get("designer", {}).get("boards", {})) != set(bs):
        _env.write_json(f, blank(PANEL, list(bs), BOARD))
    print(f"ballot -> {(d / 'ballot.md').resolve()}; scores to fill -> {f.resolve()}")
    return 0


def problems(data, panel, ids, keys=tuple(CRITERIA)):
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            for k in keys:
                v = (e.get("scores") or {}).get(k)
                if not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / {i} / {k}: needs a whole number 1-5 (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / {i}: the paragraph needs at least 25 words")
    return bad


def cmd_tally(a):
    bs = boards()
    data = _env.read_json("vote/scores.json")
    if not data:
        sys.exit("vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, list(bs), BOARD)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    score = lambda L, c, k: data["critics"][c]["boards"][L]["scores"][k]
    mean = {L: round(sum(score(L, c, k) for c in PANEL for k in BOARD) / (len(PANEL) * len(BOARD)), 2) for L in bs}
    order = sorted(bs, key=lambda L: (-mean[L], L))
    lines = ["# the vote", "", "| board | style | " + " | ".join(PANEL) + " | mean |", "|---|---|" + "---|" * (len(PANEL) + 1)]
    for L in order:
        lines.append(f"| {L} | {bs[L]} | " + " | ".join(f"{sum(score(L, c, k) for k in BOARD) / len(BOARD):.1f}" for c in PANEL)
                     + f" | **{mean[L]}** |")
    lines += ["", "## scores by rule", "", "| board | critic | " + " | ".join(BOARD) + " |", "|---|---|" + "---|" * len(BOARD)]
    for L in order:
        for c in PANEL:
            lines.append(f"| {L} | {c} | " + " | ".join(str(score(L, c, k)) for k in BOARD) + " |")
    lines += ["", "## what the critics said", ""]
    for L in order:
        lines += [f"### {L}: {bs[L]}", ""] + [f"**{PANEL[c]}.** {data['critics'][c]['boards'][L]['paragraph'].strip()}" for c in PANEL] + [""]
    _env.write_text("vote.md", "\n".join(lines))
    best = order[0]
    print(f"best board {best} ({bs[best]}), mean {mean[best]}; then " + ", ".join(f"{L} {mean[L]}" for L in order[1:]) + " -> vote.md")
    print(f"pick: storyboard.py pick {best} --by person|taste --reason \"...\" (the person's choice wins over the vote)")
    return 0


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    # a round judges a whole render: render/film.json, for this board, names its reel's digest
    done = _env.read_json("render/film.json") or {}
    if not done.get("reel") or done.get("hash") != (_env.read_json("board.json") or {}).get("hash"):
        sys.exit("render/film.json is not for this board: run film.py render first")
    digest = done["reel"]
    # the critic scores the frames and the measures of this render: qa.py check runs on it first
    if (_env.read_json("qa/check.json") or {}).get("film") != digest:
        sys.exit("qa/check.json is not for this render: run qa.py check, then vote.py cut")
    rs = rounds()
    # a round judges one film: the newest round is the one to fill while the reel is the film it was opened for
    if rs and (_env.read_json(rs[-1]) or {}).get("film") == digest:
        print(f"{rs[-1]} is the round for this film: fill it in, then run vote.py verdict")
        return 0
    # a round nobody filled in judged nothing: the new film takes its number, so every round counts a judged render
    n = len(rs) if rs and problems(_env.read_json(rs[-1]) or {}, CUT_PANEL, ["film"]) else len(rs) + 1
    f = Path("critic") / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"], CRITERIA)
    data["round"] = n
    data["board"] = (_env.read_json("winner.json") or {}).get("board")
    data["film"] = digest
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: watch out/film.mp4 at full size with the sound on, as a client would, then fill in {f} on the "
          "seven rules after looking at its rests in frames/ (full size), qa/film-strip12.jpg, out/story.png, "
          "out/grid-after.png, out/posts/, the out/ listing and qa/check.json"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    for k, v in CRITERIA.items():
        print(f"  {k}: {v}")
    return 0


def lowest(data):
    """Each rule's score as the lowest any critic of the cut gave it."""
    return {k: min(data["critics"][c]["boards"]["film"]["scores"][k] for c in CUT_PANEL) for k in CRITERIA}


def at_bar(low):
    return sum(low.values()) / len(low) >= MEAN and min(low.values()) >= FLOOR


def decide(rs):
    """The latest round against the bar: (word, message, scores), the word SHIP, FIX or DELIVER; None when the round
    is not complete."""
    data = _env.read_json(rs[-1])
    if problems(data, CUT_PANEL, ["film"]):
        return None
    low = lowest(data)
    mean = sum(low.values()) / len(low)
    scores = ", ".join(f"{k} {v}" for k, v in low.items()) + f"; mean {mean:.2f}"
    if at_bar(low):
        return "SHIP", f"SHIP: round {data.get('round')} is at the bar ({scores})", low
    # the rules holding the film under the bar, lowest first: every rule under 4, else every rule under 5
    under = sorted((v, k) for k, v in low.items() if v < FLOOR) or sorted((v, k) for k, v in low.items() if v < 5)
    named = ", ".join(f"{k} {v}" for v, k in under)
    pull = [(v, k) for v, k in under if k in LEVERS]
    if len(rs) >= 2 or not pull:
        why = "the one fix is spent" if len(rs) >= 2 else "no rule under the bar has a lever in the run"
        return "DELIVER", (f"DELIVER: round {data.get('round')} is under the bar (a mean of {MEAN} and no rule under {FLOOR}) on "
                           f"{named}; {why}, so this render is delivered as the best cut with every score stated in brief.md "
                           f"({scores})"), low
    v, k = pull[0]
    lever, then = LEVERS[k]
    return "FIX", (f"FIX ONCE: {k} is {v} ({CRITERIA[k]}). Pull its lever, {lever}; run {then}, film.py render, "
                   f"qa.py check, then vote.py cut for round 2 on the new render"), low


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    got = decide(rs)
    if got is None:
        print(f"{rs[-1]} is not complete:")
        for x in problems(_env.read_json(rs[-1]), CUT_PANEL, ["film"]):
            print("  -", x)
        return 1
    print(got[1])
    return 2 if got[0] == "FIX" else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "cut", "verdict"])
    a = ap.parse_args()
    _env.enter_run()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
