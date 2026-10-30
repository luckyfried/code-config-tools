#!/usr/bin/env python3
"""Movement 3 (the panel picks a storyboard), the critic's read of the timed cut, and the critics' score of the film.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot  --run R   # vote/ballot.md + vote/scores.json to fill in: the three looks scored
    python3 S/scripts/vote.py tally   --run R   # vote.md + winner.json: the panel's look (the highest total that passes the swap test)
    python3 S/scripts/vote.py pick    --run R --board B [--why "<one line>"]
                                                # the look the film is made in: the person's answer, or with --why the pick by
                                                # taste where nothing may be asked; B is a style id, A, B or C, or 1, 2 or 3
    python3 S/scripts/vote.py timed   --run R   # critic/timed.json to fill in: the monotony read of the timed cut
    python3 S/scripts/vote.py cut     --run R   # critic/cut-N.json to fill in for the rendered film (next round N)
    python3 S/scripts/vote.py verdict --run R   # SHIP at the bar (mean 4.5 or more, no criterion under 4), else the fix and its levers

The boards are the run's three looks, storyboards/<style>/, in the order out/boards.png shows them (A, B, C). The panel
(S/critic/critic.md has each critic's brief): a motion designer, an editor and the person, modeled from taste.md.
Each scores every look 1-5 on the seven criteria below and writes one paragraph per look. The motion designer also
applies the swap test to each look's three compositions (the hook, the densest beat and the closer, on its sheet): a
composition passes when another person's nine, with their own photographs, moments and words, would change what fills
the frame, and fails when any nine would sit in it unchanged. A look with a composition that fails cannot win the
tally. `pick` is the choice the film is made in; it takes away everything made from an earlier choice in the run (the
cut, the music made for that look, the preview, the reads and the critics' rounds), so the sequence from the music on
runs again for the look picked. Before the film renders, the editor reads the timed cut (preview/film.mp4 and its
strip) for monotony. The finished cut is scored by the motion designer and the person on the same criteria; it ships
at the bar, and under it the one fix names the levers (a beat's layout, move and seconds in taste.json `beats`).
"""
import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402

RESTS = ("hook", "dense", "closer")
BAR = 4.5
FLOOR = 4
LEVERS = ("layout", "move", "seconds")
# what a pick takes away: everything made for the look chosen before; a track the person gave (music/source.*) stays
STALE = ("film.json", "preview", "critic", "qa/timed.json", "qa/check.json", "qa/gate.json", "music.json",
         "render/film-report.json")

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


def looks():
    """The run's three looks in the order the sheets show them: the trio, or the style taste.json names and the two that
    differ most from it."""
    return compose.three((_env.read_json("taste.json") or {}).get("style"))


def boards():
    ids = looks()
    out = [t for t in ids if (Path("storyboards") / t / "sheet.png").exists()]
    if len(out) < len(ids):
        sys.exit(f"{len(out)} of {len(ids)} looks with sheets: run storyboard.py draft and sheets first")
    return out


def name_of(style):
    return compose.card(style)["name"]


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def blank_swap(ids):
    return {i: {r: {"pass": None, "why": ""} for r in RESTS} for i in ids}


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every look 1-5 on each criterion, as each critic, and write one paragraph per look "
             "(what works, what fails, what you would change). Look at out/boards.png and each look's sheet before scoring.", "",
             "Then the swap test, as the motion designer, on each board's three compositions (the hook, the densest beat and "
             "the closer, left to right on its sheet): `pass` is true when another person's nine, with their own photographs, "
             "moments and words, would change the frame (the order their numbers give, the line each is cut along, their caption "
             "on it, its day), false when any nine would sit in it unchanged; the closer's three by three grid, each tile its "
             "photograph cut square around its own subject in the order their numbers give, is the posted image's standard and "
             "the passing case, never a reason to fail. All nine present, each legible, every one their own. "
             "`why` names what in the frame comes from their photographs and words, in one sentence. A look that fails one cannot win.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the looks", ""]
    for x, b in zip("ABC", bs):
        sb = Path("storyboards") / b
        lines += [f"### {x}. {b} ({name_of(b)})", "", f"- storyboard: {sb.resolve() / 'storyboard.md'}",
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
        print("no look passes the swap test: every one has a composition whose photograph could be swapped; "
              "change those moments' layouts in taste.json beats and draft again")
        return 1
    order = sorted(ids, key=lambda i: (not passed[i], -tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if passed[i] and tot[i] == tot[win]]
    names = {i: name_of(i) for i in ids}
    lines = ["# the vote", "", f"The panel's look: {win}, {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""),
             "",
             "| critic | " + " | ".join(ids) + " |", "|---|" + "---|" * len(ids)]
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
        lines += [f"### {i}: {names[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
        lines += [f"**The swap test.** " + " ".join(f"{r}: {'passes' if data['swap'][i][r]['pass'] else 'fails'}, {data['swap'][i][r]['why'].strip()}" for r in RESTS), ""]
    _env.write_text("vote.md", "\n".join(lines))
    _env.write_json("winner.json", {"board": win, "name": names[win], "picked_by": "the panel", "why": "", "looks": ids,
                                    "totals": tot, "order": order, "swap": passed, "swap_passed": passed[win],
                                    "tie_broken_by_person": len(tie) > 1})
    print(f"the panel's look: {win}, totals {tot}, swap test {passed} -> vote.md, winner.json")
    return 0


def chosen(word, ids):
    """The look a person's word names: a style id, a look's name, its letter on the sheets, or its place."""
    w = (word or "").strip().lower()
    for i, x in enumerate(ids):
        if w in (x, name_of(x).lower(), "abc"[i], str(i + 1)):
            return x
    return None


def cmd_pick(a):
    ids = looks()
    win = chosen(a.board, ids)
    if not win:
        sys.exit(f"no look {a.board or '(none named)'}: the looks are {', '.join(f'{x} {i}' for x, i in zip('ABC', ids))}; "
                 "name one with --board")
    old = _env.read_json("winner.json") or {}
    if old.get("board") != win or old.get("picked_by") == "the panel":
        made = [p for p in Path("music").glob("*") if p.stem != "source"] if Path("music").is_dir() else []
        # the look cut before, picked again after its boards are drawn again, is the fix round: its scored rounds stay,
        # so the next cut is the next round
        again = any((_env.read_json(r) or {}).get("style") == win for r in rounds())
        for p in [*map(Path, STALE), *made]:
            if again and p == Path("critic") and p.is_dir():
                for f in p.iterdir():
                    if not re.fullmatch(r"cut-\d+\.json", f.name):
                        f.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
    who = "taste" if a.why else "the person"
    _env.write_json("winner.json", {**{k: v for k, v in old.items() if k in ("totals", "order", "swap")},
                                    "board": win, "name": name_of(win), "picked_by": who, "why": (a.why or "").strip(),
                                    "looks": ids, "swap_passed": (old.get("swap") or {}).get(win, True)})
    print(f"the film is made in {win} ({name_of(win)}), picked by {who}"
          + (f": {a.why.strip()}" if a.why else "") + "; next: music.py find -> winner.json")
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
    _env.write_json(path, {"hash": f["hash"], "style": f["style"], "monotony": {"pass": None, "read": ""},
                           "film": str(Path("preview/film.mp4").resolve()), "strip": pv.get("strip2"),
                           "measured": {k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_event_frame")}})
    print(f"the monotony read, as the editor: watch {Path('preview/film.mp4').resolve()} and its strip {pv.get('strip2')}, then fill in "
          f"{path.resolve()}: monotony.pass (false when shots repeat one move, one size or one length so the eye stops "
          "expecting anything) and monotony.read (at least 25 words: where the rhythm changes, where it does not)")
    return 0


def cmd_cut(a):
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    film = Path("out/film.mp4")
    # render/film-report.json stands only over a whole out/, so a round is opened only for a reel that finished
    if not Path("render/film-report.json").exists() or not film.exists():
        sys.exit("render/film-report.json is missing: run film.py render first")
    digest = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    rs = rounds()
    # a round scores one film: the same reel keeps its round and what the critics have filled in, a new reel opens the next
    if rs and (_env.read_json(rs[-1]) or {}).get("film") == digest:
        print(f"round {len(rs)} is this film's: fill in {rs[-1].resolve()} after watching out/film.mp4 and the frames in frames/")
        return 0
    n = len(rs) + 1
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["style"] = (_env.read_json("film.json") or {}).get("style")
    data["film"] = digest
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f.resolve()} after watching out/film.mp4 and the frames in frames/"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def at_bar(data):
    """(mean, the worst (score, criterion, critic), whether the cut is at the bar) of a filled round."""
    got = [(data["critics"][c]["boards"]["film"]["scores"][k], k, c) for c in CUT_PANEL for k in CRITERIA]
    mean = round(sum(x[0] for x in got) / len(got), 2)
    worst = min(got)
    return mean, worst, mean >= BAR and worst[0] >= FLOOR


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
    mean, worst, ship = at_bar(data)
    if ship:
        print(f"SHIP: round {data.get('round')}, mean {mean} of 5, every criterion 4 or more")
        return 0
    if len(rs) >= 2:
        print(f"UNDER THE BAR: round {data.get('round')}, mean {mean} (the bar is {BAR}), {worst[1]} at {worst[0]} ({worst[2]}). "
              "The one fix is spent: deliver this cut; deliver.py writes its scores into the run's brief.md")
        return 2
    print(f"FIX ONCE: mean {mean} (the bar is {BAR}, no criterion under {FLOOR}); the worst thing is {worst[1]} "
          f"({CRITERIA[worst[1]]}), {worst[2]} gave {worst[0]}. The levers are each beat's layout, move and seconds, in "
          "taste.json beats.<beat id> (a layout and a move the look offers, a hold in seconds), and the words in taste.json; "
          "change what the worst thing names, then storyboard.py snap, film.py preview, vote.py timed, qa.py timed, "
          "film.py render and vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timed", "cut", "verdict"])
    ap.add_argument("--board", help="pick: the look the film is made in (a style id, A, B or C, or 1, 2 or 3)")
    ap.add_argument("--why", help="pick: the one-line reason, when the look is picked by taste because nothing may be asked")
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timed": cmd_timed, "cut": cmd_cut,
            "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
