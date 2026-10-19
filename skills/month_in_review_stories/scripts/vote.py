#!/usr/bin/env python3
"""Movement 3 (the panel picks a storyboard) and movement 6 (two critics score the finished cut).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot     # build/vote/ballot.md + build/vote/scores.json to fill in
    python3 S/scripts/vote.py tally      # build/vote.md + build/winner.json (highest total; a tie goes to the person)
    python3 S/scripts/vote.py cut        # build/critic/cut-N.json to fill in for the rendered film and cards (next round N)
    python3 S/scripts/vote.py verdict    # SHIP when every score of the latest round is 4 or more, else the worst thing

The panel (S/critic/critic.md has each critic's brief): a motion designer (craft, pacing, type, transitions), an
editor (story, one idea per card, the series as a set) and the person, modeled from build/taste.md (is this unmistakably me; would I
post it). Each scores every storyboard 1-5 on the seven criteria below and writes one paragraph per board.
The finished cut (the film, every animated card and every static card) is scored by the motion designer and the
person on the same criteria; the round records a fingerprint of those files so the gate knows it is current.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CRITERIA = {
    "professional": "it looks like a professional motion designer made it",
    "them": "it is unmistakably them (their photos carry it, their colors, their voice)",
    "pacing": "the pacing holds attention to the end",
    "type": "type is a system, not a default",
    "transitions": "every transition is intentional",
    "music": "the music and the cuts agree",
    "series": "the cards read as one numbered series, one idea each, and they would post every one",
}
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def boards():
    out = []
    for f in sorted(Path("build/storyboards").glob("*/storyboard.json")):
        out.append(_env.read_json(f))
    if len(out) < 2:
        sys.exit("fewer than two storyboards: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def cmd_ballot(a):
    bs = boards()
    d = Path("build/vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every storyboard 1-5 on each criterion, as each critic, and write one paragraph per board "
             "(what works, what fails, what you would change). Look at each style sheet before scoring.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path(f"build/storyboards/{b['id']}")
        lines += [f"### {b['id']}: {b['name']}", "", b.get("idea", ""), "",
                  f"- structure {b.get('structure')}; tone {b.get('tone')}; clips: {b.get('clip_use')}",
                  f"- storyboard: {sb / 'storyboard.md'}", f"- style sheet: {sb / 'sheet.png'} (frames in {sb / 'frames'}/)", ""]
    lines += ["Fill in build/vote/scores.json, then run vote.py tally.", ""]
    (d / "ballot.md").write_text("\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["id"] for b in bs]))
    print(f"ballot -> {d / 'ballot.md'}; scores to fill -> {f}")
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


def cmd_tally(a):
    bs = boards()
    ids = [b["id"] for b in bs]
    data = _env.read_json("build/vote/scores.json")
    if not data:
        sys.exit("build/vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    tot = {i: sum(sum(data["critics"][c]["boards"][i]["scores"].values()) for c in PANEL) for i in ids}
    person = {i: sum(data["critics"]["person"]["boards"][i]["scores"].values()) for i in ids}
    order = sorted(ids, key=lambda i: (-tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if tot[i] == tot[win]]
    names = {b["id"]: b["name"] for b in bs}
    lines = ["# the vote", "", f"Winner: storyboard {win}, {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""),
             f"Runners-up: " + ", ".join(f"{i} {names[i]} ({tot[i]})" for i in order[1:]) + ". They stay on the review page; "
             "say \"do the second one\" and the kit renders that storyboard.", "",
             "| critic | " + " | ".join(f"board {i}" for i in ids) + " |", "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(str(sum(data['critics'][c]['boards'][i]['scores'].values())) for i in ids) + " |")
    lines.append("| total | " + " | ".join(f"**{tot[i]}**" for i in ids) + " |")
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
    Path("build/vote.md").write_text("\n".join(lines))
    _env.write_json("build/winner.json", {"board": win, "name": names[win], "totals": tot, "order": order, "tie_broken_by_person": len(tie) > 1})
    print(f"winner: storyboard {win} ({names[win]}), totals {tot} -> build/vote.md, build/winner.json")
    return 0


def cut_files():
    return [Path("out/film.mp4")] + sorted(Path("out/cards").glob("*.mp4")) + sorted(Path("out/cards").glob("*.png"))


def fingerprint():
    """One hash over the film and every card, animated and static."""
    h = hashlib.sha256()
    for f in cut_files():
        if f.exists():
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]


def rounds():
    return sorted(Path("build/critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    d = Path("build/critic")
    d.mkdir(parents=True, exist_ok=True)
    n = len(rounds()) + 1
    f = d / f"cut-{n}.json"
    film = Path("out/film.mp4")
    if not film.exists():
        sys.exit("out/film.mp4 is missing: run film.py render first")
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = fingerprint()
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f} after watching out/film.mp4, every card in out/cards/ and the frames in build/frames/"
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
    ap.add_argument("cmd", choices=["ballot", "tally", "cut", "verdict"])
    a = ap.parse_args()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
