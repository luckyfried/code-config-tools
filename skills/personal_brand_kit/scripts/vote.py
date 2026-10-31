#!/usr/bin/env python3
"""The three looks scored as boards, the look the person picks, and the critics' scores of the timed cut against the
bar before it renders.

USAGE (from the workspace root; S = this skill's folder; every script works in the run build/run names):
    python3 S/scripts/vote.py ballot               # vote/ballot.md + vote/scores.json to fill in, one entry per look
    python3 S/scripts/vote.py tally                # vote.md: the three looks' scores side by side
    python3 S/scripts/vote.py pick <a|b|c> [--why "..."]
                                                   # winner.json: the look the film is made in; --why is the one-line
                                                   # reason when the agent picks by taste (taste.json ask: false)
    python3 S/scripts/vote.py cut                  # critic/cut-N.json to fill in for the timed cut (next round N)
    python3 S/scripts/vote.py verdict              # SHIP at the bar; under it, round 1 names the one thing to fix and
                                                   # round 2 delivers the cut with its scores in brief.md

The panel (S/critic/critic.md has each critic's brief): a motion designer (craft, pacing, type, cuts), an editor (story,
the ending) and the person, modeled from taste.md (is this unmistakably me; would I post it). Each scores every look's
board 1-5 on the criteria below, one per rule of motion/system/standards.md that a board can show, from out/boards.png,
the look's sheet and its storyboard.md, with one paragraph each. The scores tell the person what the critics think when
they ask; the person picks the look (`pick`), and with taste.json `ask` false the agent picks by taste and says why in
one line.

The timed cut is scored by the motion designer and the person on every criterion, from the cut's frames and strips and
qa/check.json, before film.py render makes the three formats from it. The bar: the mean of every score 4.5 or more and
no score under 4. Under the bar, round 1 names the lowest score for the one fix; round 2 is the spent budget: the cut is
delivered as it stands, and its scores go in brief.md, never on the review page.
"""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CRITERIA = {
    "idea": "R1 the hook states one idea from their own words and moments, every move and cut is the look's own, the "
            "closer pays it off",
    "picture": "R2 one finish, the look's; every color a photograph's own or the look's palette's; the closer holds still",
    "type": "R3 two faces, a scale, lines that enter and settle, every line reads on its ground, nothing colliding",
    "motion": "R4 every move anticipates and settles, no two beats in a row alike, the peak held longest, cuts on the beat",
    "sound": "R5 the bed belongs to the look, a cue only where a line lands, effects under the music, quiet from the stop",
    "own": "its own film: the hook and the closer read as this look and no other",
}
# what a board can show: no sound yet (what out/ holds, R7, is the gate's to check)
BOARD_CRITERIA = ("idea", "picture", "type", "motion", "own")
BAR_MEAN, BAR_MIN = 4.5, 4
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def looks():
    import storyboard
    out = []
    for letter in storyboard.letters():
        d = storyboard.BOARDS / letter
        if not (d / "sheet.png").exists():
            sys.exit(f"{d}/sheet.png is missing: run storyboard.py sheets first")
        r = _env.read_json(d / "plan.json")["reel"]
        b = _env.read_json(d / "board-reel.json")
        out.append({"id": letter, "name": b["name"], "style": b["style"], "seconds": r["seconds"], "cuts": len(r["cuts"])})
    if not out:
        sys.exit("no boards: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids, criteria):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in criteria}, "paragraph": ""} for i in ids}} for c in panel}}


def problems(data, panel, ids, criteria):
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            for k in criteria:
                v = (e.get("scores") or {}).get(k)
                if not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / {i} / {k}: needs a whole number 1-5 (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / {i}: the paragraph needs at least 25 words")
    return bad


def cmd_ballot(a):
    ls = looks()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every look 1-5 on each criterion, as each critic, and write one paragraph per look (what "
             "works, what fails, what you would change). Look at out/boards.png and each look's sheet before scoring.", "",
             "## criteria", ""] + [f"- `{k}`: {CRITERIA[k]}" for k in BOARD_CRITERIA] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the looks", ""]
    for b in ls:
        sb = Path(f"storyboards/{b['id']}")
        lines += [f"### {b['id']}: {b['name']}", "", f"- {b['seconds']} s, {b['cuts']} cuts", f"- storyboard: {sb / 'storyboard.md'}",
                  f"- sheet: {sb / 'sheet.png'} (the hook, a middle beat and the closer at rest, in {sb / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["id"] for b in ls], BOARD_CRITERIA))
    print(f"ballot -> {d / 'ballot.md'}; scores to fill -> {f}")
    return 0


def cmd_tally(a):
    ls = looks()
    ids = [b["id"] for b in ls]
    data = _env.read_json("vote/scores.json")
    if not data:
        sys.exit("vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids, BOARD_CRITERIA)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    names = {b["id"]: b["name"] for b in ls}
    scores = {i: [data["critics"][c]["boards"][i]["scores"][k] for c in PANEL for k in BOARD_CRITERIA] for i in ids}
    mean = {i: sum(v) / len(v) for i, v in scores.items()}
    lines = ["# the looks, scored", "", "| critic | " + " | ".join(f"{i.upper()} {names[i]}" for i in ids) + " |",
             "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(
            f"{sum(data['critics'][c]['boards'][i]['scores'].values()) / len(BOARD_CRITERIA):.2f}" for i in ids) + " |")
    lines.append("| mean | " + " | ".join(f"**{mean[i]:.2f}**" for i in ids) + " |")
    lines.append("| lowest | " + " | ".join(str(min(scores[i])) for i in ids) + " |")
    lines += ["", "## scores by criterion", "", "| look | critic | " + " | ".join(BOARD_CRITERIA) + " |",
              "|---|---|" + "---|" * len(BOARD_CRITERIA)]
    for i in ids:
        for c in PANEL:
            s = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {i} | {c} | " + " | ".join(str(s[k]) for k in BOARD_CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### {i.upper()}: {names[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
    _env.write_text("vote.md", "\n".join(lines))
    best = max(ids, key=lambda i: (mean[i], min(scores[i]), -ids.index(i)))
    print(f"vote.md: " + ", ".join(f"{i.upper()} {mean[i]:.2f}" for i in ids) + f"; the critics lean {best.upper()} ({names[best]}). "
          "Show out/boards.png and ask which look, then vote.py pick <letter>")
    return 0


def cmd_pick(a):
    import storyboard
    ls = {b["id"]: b for b in looks()}
    letter = a.letter.lower()
    if letter not in ls:
        sys.exit(f"no look {a.letter!r}: the looks are {', '.join(f'{k.upper()} {v['name']}' for k, v in ls.items())}")
    taste = _env.read_json("taste.json") or {}
    by = "taste" if taste.get("ask") is False else "person"
    if by == "taste" and not (a.why or "").strip():
        sys.exit("taste.json ask is false, so the agent picks: pass --why with the one-line reason from their taste")
    old = (_env.read_json("winner.json") or {}).get("board")
    if old and old != letter:
        # a new look starts the film again from the pick: its own music (when it was made here), its own cut and rounds
        music = _env.read_json("music.json") or {}
        if music.get("recipe"):
            Path("music.json").unlink(missing_ok=True)
            shutil.rmtree("music", ignore_errors=True)
        for f in (*storyboard.CUT_SET, Path("film.json")):
            f.unlink(missing_ok=True)
        shutil.rmtree("critic", ignore_errors=True)
    b = ls[letter]
    _env.write_json("winner.json", {"board": letter, "name": b["name"], "style": b["style"], "by": by, "why": (a.why or "").strip()})
    print(f"picked {letter.upper()} {b['name']}" + (f" by their taste: {a.why.strip()}" if by == "taste" else "")
          + "; next: music.py find, storyboard.py snap")
    return 0


# what the critics look at before they score the cut: the picture from its frames, the sound from the audio row
LOOK = ("watching cut.mp4 with sound, reading its strips cut-strip.png and cut-strip12.jpg row by row (and any frame "
        "you cut from cut.mp4), and qa/check.json's audio row")


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    # cut.json certifies the cut and its strips; the round reads it, never cut.mp4 alone
    if not Path("cut.json").exists():
        sys.exit("cut.json is missing: run film.py cut first")
    digest = hashlib.sha256(Path("cut.mp4").read_bytes()).hexdigest()[:16]
    qa = _env.read_json("qa/check.json") or {}
    if qa.get("film") != digest:
        sys.exit("qa/check.json is not for this cut: run qa.py check first")
    # a round belongs to the cut it judges: the newest round is this cut's until the cut changes; a round never filled
    # in (the cut changed before it was scored) is opened again for the new cut
    done = rounds()
    last = _env.read_json(str(done[-1])) if done else None
    if last is not None and last.get("film") == digest:
        print(f"round {last['round']} is this cut's: fill in {done[-1]} after {LOOK}")
        return 0
    blank_last = last is not None and any(v is None for c in last["critics"].values() for b in c["boards"].values() for v in b["scores"].values())
    n = len(done) + (0 if blank_last else 1)
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"], CRITERIA)
    data.update(round=n, film=digest, fixed="" if n > 1 else None, criteria=CRITERIA, bar={"mean": BAR_MEAN, "min": BAR_MIN})
    _env.write_json(f, data)
    for c in qa.get("checks") or []:
        if c["check"] == "audio":
            print(f"audio: {c['detail']}")
    print(f"round {n}: fill in {f} after {LOOK}" + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def scores_of(data):
    """{critic: {criterion: score}} of a round's film."""
    return {c: data["critics"][c]["boards"]["film"]["scores"] for c in CUT_PANEL}


def at_bar(data):
    v = [s for c in scores_of(data).values() for s in c.values()]
    return sum(v) / len(v), min(v)


def cmd_verdict(a):
    # critic/verdict.json is the verdict on the round as it reads now: it goes first and comes back only with the
    # verdict this run reaches
    Path("critic/verdict.json").unlink(missing_ok=True)
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    bad = problems(data, CUT_PANEL, ["film"], CRITERIA)
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    mean, low = at_bar(data)
    worst = min((s, k, c) for c, sc in scores_of(data).items() for k, s in sc.items())
    what = f"{worst[1]} ({CRITERIA[worst[1]]}): {worst[2]} gave {worst[0]}"
    def record(verdict):
        _env.write_json("critic/verdict.json", {"round": data.get("round"), "film": data.get("film"), "verdict": verdict,
                                                "mean": round(mean, 2), "lowest": low, "bar": {"mean": BAR_MEAN, "min": BAR_MIN},
                                                "scores": scores_of(data), "what": None if verdict == "ship" else what})
    if mean >= BAR_MEAN and low >= BAR_MIN:
        record("ship")
        print(f"SHIP: round {data.get('round')}, mean {mean:.2f}, lowest {low}: at the bar")
        return 0
    if len(rs) >= 2:
        record("spent")
        print(f"round {data.get('round')}: mean {mean:.2f}, lowest {low}, under the bar on {what}. The one fix is spent; "
              "render the cut as it stands (film.py render); brief.md carries its scores")
        return 0
    record("fix")
    print(f"FIX ONCE: mean {mean:.2f}, lowest {low}; the lowest is {what}. Fix it (the levers in critic.md), cut again "
          "(film.py cut, qa.py check), then run vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "cut", "verdict"])
    ap.add_argument("letter", nargs="?", help="pick: the look, a, b or c")
    ap.add_argument("--why", help="pick: the one-line reason, when the agent picks by their taste")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.letter:
        ap.error("pick needs the look's letter: vote.py pick a")
    _env.enter()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
