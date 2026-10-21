#!/usr/bin/env python3
"""Movement 3 (the panel picks a storyboard), the critic's read of the timed cut, and the critics' score of the film.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot  --run R   # vote/ballot.md + vote/scores.json to fill in (scores and the swap test)
    python3 S/scripts/vote.py tally   --run R   # vote.md + winner.json (highest total among the boards that pass the swap test)
    python3 S/scripts/vote.py timed   --run R   # critic/timed.json to fill in: the monotony read of the timed cut
    python3 S/scripts/vote.py cut     --run R   # critic/cut-N.json to fill in for the rendered film (next round N)
    python3 S/scripts/vote.py verdict --run R   # SHIP when every score of the latest round is 4 or more, else the worst thing

The panel (S/critic/critic.md has each critic's brief): a motion designer, an editor and the person, modeled from
taste.md. Each scores every storyboard 1-5 on the seven criteria below and writes one paragraph per board. The
motion designer also applies the swap test to each board's three compositions (the hook, the densest beat and the
closer, on its sheet): a composition passes when another person's nine, with their own ranks, likes and dates,
would change the frame (the drive closer's ranked grid of counts is the passing case), and fails when any nine would
sit in it unchanged. A board with a composition that fails cannot win. Before the film renders, the editor reads the timed
cut (preview/film.mp4 and its strip) for monotony; film.py render waits for that read to pass. The finished cut
is scored by the motion designer and the person on the same criteria.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

TONES = ("drive",)
RESTS = ("hook", "dense", "closer")

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
    out = [t for t in TONES if (Path("storyboards") / t / "sheet.png").exists()]
    if len(out) < len(TONES):
        sys.exit(f"{len(out)} of {len(TONES)} storyboards with sheets: run storyboard.py draft and sheets first")
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
             "Then the swap test, as the motion designer, on each board's three compositions (the hook, the densest beat and "
             "the closer, left to right on its sheet): `pass` is true when another person's nine, with their own ranks, likes "
             "and dates, would change the frame (the order, a size, a count, a string), false when any nine would sit in it "
             "unchanged; the drive closer's even grid in rank order with each count on its square is the passing case. "
             "`why` names what in the frame comes from the data, in one sentence. A board that fails one cannot win.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path("storyboards") / b
        lines += [f"### {b}", "", f"- storyboard: {sb.resolve() / 'storyboard.md'}",
                  f"- style sheet: {sb.resolve() / 'sheet.png'} (frames in {sb.resolve() / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    (d / "ballot.md").write_text("\n".join(lines))
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
              "change the tone builder's layout for those posts and draft again")
        return 1
    order = sorted(ids, key=lambda i: (not passed[i], -tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if passed[i] and tot[i] == tot[win]]
    names = {i: i for i in ids}
    lines = ["# the vote", "", f"Winner: storyboard {win}, {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
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
        lines += [f"### board {i}: {names[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
        lines += [f"**The swap test.** " + " ".join(f"{r}: {'passes' if data['swap'][i][r]['pass'] else 'fails'}, {data['swap'][i][r]['why'].strip()}" for r in RESTS), ""]
    Path("vote.md").write_text("\n".join(lines))
    _env.write_json("winner.json", {"board": win, "name": names[win], "totals": tot, "order": order, "swap": passed,
                                    "swap_passed": passed[win], "tie_broken_by_person": len(tie) > 1})
    print(f"winner: {win}, totals {tot}, swap test {passed} -> vote.md, winner.json")
    return 0


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_timed(a):
    f = _env.read_json("film.json") or {}
    pv = _env.read_json("preview/preview.json") or {}
    if not f or pv.get("hash") != f.get("hash"):
        sys.exit("preview/preview.json is not for the current cut: run storyboard.py snap and film.py preview first")
    path = Path("critic/timed.json")
    old = _env.read_json(path) or {}
    if old.get("hash") == f["hash"] and isinstance((old.get("monotony") or {}).get("pass"), bool):
        print(f"{path} already holds the read of this cut: {'pass' if old['monotony']['pass'] else 'fail'}")
        return 0 if old["monotony"]["pass"] else 2
    _env.write_json(path, {"hash": f["hash"], "tone": f["tone"], "monotony": {"pass": None, "read": ""},
                           "film": str(Path("preview/film.mp4").resolve()), "strip": pv.get("strip2"),
                           "measured": {k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_event_frame")}})
    print(f"the monotony read, as the editor: watch {Path('preview/film.mp4').resolve()} and its strip {pv.get('strip2')}, then fill in "
          f"{path.resolve()}: monotony.pass (false when shots repeat one move, one size or one length so the eye stops "
          "expecting anything) and monotony.read (at least 25 words: where the rhythm changes, where it does not)")
    return 0


def cmd_cut(a):
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    n = len(rounds()) + 1
    f = d / f"cut-{n}.json"
    film = Path("out/film.mp4")
    if not film.exists():
        sys.exit("out/film.mp4 is missing: run film.py render first")
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f.resolve()} after watching out/film.mp4 and the frames in frames/"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


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
    worst = min(((data["critics"][c]["boards"]["film"]["scores"][k], k, c) for c in CUT_PANEL for k in CRITERIA))
    if worst[0] >= 4:
        print(f"SHIP: round {data.get('round')}, every score is 4 or more")
        return 0
    if len(rs) >= 2:
        print(f"round {data.get('round')}: still below 4 on {worst[1]} ({worst[2]}: {worst[0]}). The one fix is spent; "
              "ship and name it in brief.md")
        return 2
    print(f"FIX ONCE: the worst thing is {worst[1]} ({CRITERIA[worst[1]]}), {worst[2]} gave {worst[0]}. Fix it, re-render, "
          "then run vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "timed", "cut", "verdict"])
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    return {"ballot": cmd_ballot, "tally": cmd_tally, "timed": cmd_timed, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
