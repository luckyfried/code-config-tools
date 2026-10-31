#!/usr/bin/env python3
"""Movement 3 (the panel scores the three storyboards, and a look is picked) and movement 6 (two critics score the cut).

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/vote.py ballot     # vote/ballot.md + vote/scores.json to fill in
    python3 S/scripts/vote.py tally      # vote.md + winner.json: every board's scores against the bar, the best board
                                         # picked until the person or their taste picks another
    python3 S/scripts/vote.py pick --board N [--why "..."]
                                         # the film is made from board N: winner.json names it, and everything made
                                         # from the board picked before (the music, the timed films, the clips, the
                                         # render, the films and stills in out/, the critics' rounds, the checks and
                                         # the frames) is removed, so the next music.py make starts the look clean
    python3 S/scripts/vote.py cut        # critic/cut-N.json to fill in for the rendered film (next round N; the
                                         # newest round again while out/film.mp4 is the film it is for); refused
                                         # until qa.py check and film.py frames have run on this film
    python3 S/scripts/vote.py verdict    # SHIP when the latest round clears the bar, else the worst thing; refused for a
                                         # round whose frames are another film's, or whose paragraphs repeat the round
                                         # before word for word

The panel (S/motion/system/standards.md and S/critic/critic.md have each critic's brief): a motion designer (craft,
pacing, type, the moves), an editor (story, emotion, the ending) and the person, modeled from taste.md (is this
unmistakably me; would I post it). Each scores every storyboard 1-5 on the seven criteria below and writes one paragraph
on it, looking at its style sheet; storyboard.py check has already refused a board that fails the swap test or breaks
its look. The finished cut is scored by the motion designer and the person on the same criteria.

The bar: a board or a cut clears it when the mean of its scores is 4.5 or more and no criterion's mean is under 4.
Means are reported to two places, cut down, never rounded up. A cut still under the bar after its one fix ships as the
best cut there is, its scores written in brief.md (deliver.py), never on the review page.
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
    "moves": "every move of the camera and every cut carries the trip on, each one answering what its photograph holds",
    "music": "the music and the cuts agree",
    "ending": "the ending makes them want to post it",
}
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}
BAR, FLOOR = 4.5, 4  # the mean a board or a cut clears, and the least any criterion's mean may be


def boards():
    """The three storyboards, each with its style sheet."""
    from storyboard import BOARDS, NUMBERS
    out = [_env.read_json(BOARDS / n / "storyboard.json") for n in NUMBERS if (BOARDS / n / "sheet.png").exists()]
    if len(out) < len(NUMBERS):
        sys.exit(f"{len(out)} of {len(NUMBERS)} storyboards with a style sheet: run storyboard.py draft and sheets first")
    return out


def down(x):
    """`x` to two places, cut down."""
    return int(x * 100 + 1e-9) / 100


def against(data, panel, i):
    """Board or cut `i` against the bar: each criterion's mean over the panel, the mean of every score, whether it clears."""
    by = {k: sum(data["critics"][c]["boards"][i]["scores"][k] for c in panel) / len(panel) for k in CRITERIA}
    mean = sum(by.values()) / len(by)
    return {"criteria": {k: down(v) for k, v in by.items()}, "mean": down(mean), "clears": mean >= BAR and min(by.values()) >= FLOOR}


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score each storyboard 1-5 on each criterion, as each critic, and write one paragraph on it "
             "(what works, what fails, what you would change). Look at its style sheet before scoring, and at out/boards.png "
             f"for the three side by side. The bar: a mean of {BAR} or more, no criterion under {FLOOR}.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path(f"storyboards/{b['id']}")
        lines += [f"### {b['id']}: {b['name']}", "", b.get("idea", ""), "",
                  f"- the look {b['look']} ({b['style']}): {b['sentence']}",
                  f"- {len(b['beats'])} beats on {sum(x['bars'] for x in b['beats']):g} bars at {b.get('bpm')} bpm; moves "
                  f"{', '.join(x['move'] for x in b['beats'] if x.get('move'))}",
                  f"- storyboard: {sb / 'storyboard.md'}", f"- style sheet: {sb / 'sheet.png'} (frames in {sb / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
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
    data = _env.read_json("vote/scores.json")
    if not data:
        sys.exit("vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    res = {i: against(data, PANEL, i) for i in ids}
    person = {i: sum(data["critics"]["person"]["boards"][i]["scores"].values()) for i in ids}
    order = sorted(ids, key=lambda i: (-res[i]["mean"], -min(res[i]["criteria"].values()), -person[i], i))
    win = order[0]
    names = {b["id"]: b["name"] for b in bs}
    looks = {b["id"]: b["style"] for b in bs}
    cleared = [i for i in ids if res[i]["clears"]]
    lines = ["# the vote", "", f"The bar: a mean of {BAR} or more and no criterion under {FLOOR}. "
             + (f"{len(cleared)} of {len(ids)} boards clear it." if cleared else "No board clears it yet."), "",
             f"The best board is {win}, {names[win]} (mean {res[win]['mean']:.2f}); the film is made from it unless the "
             "person picks another look (vote.py pick --board N).", "",
             "| board | look | mean | lowest criterion | clears the bar |", "|---|---|---|---|---|"]
    for i in ids:
        lo = min(res[i]["criteria"], key=res[i]["criteria"].get)
        lines.append(f"| {i} | {looks[i]} | {res[i]['mean']:.2f} | {lo} {res[i]['criteria'][lo]:.2f} | {'yes' if res[i]['clears'] else 'no'} |")
    lines += ["", "## scores by criterion", "", "| board | critic | " + " | ".join(CRITERIA) + " |", "|---|---|" + "---|" * len(CRITERIA)]
    for i in ids:
        for c in PANEL:
            sc = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {i} | {c} | " + " | ".join(str(sc[k]) for k in CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### board {i}: {names[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
    _env.write_text("vote.md", "\n".join(lines))
    _env.write_json("winner.json", {"board": win, "name": names[win], "style": looks[win], "by": "the vote", "why": "",
                                    "scores": res, "order": order})
    print(f"the bar: mean {BAR}, no criterion under {FLOOR}")
    for i in ids:
        print(f"  board {i} ({looks[i]}): mean {res[i]['mean']:.2f}, lowest {min(res[i]['criteria'].values()):.2f}"
              f"{', clears' if res[i]['clears'] else ', under the bar'}")
    print(f"best: storyboard {win} ({names[win]}) -> vote.md, winner.json; show out/boards.png and let the person pick, "
          "or pick by their taste: vote.py pick --board N --why \"...\"")
    return 0


MADE = ("music.json", "film.json", "film-landscape.json", "film-square.json", "timeline.json", "clips.json", "music", "clips",
        "critic", "qa", "frames", "preview", "public/clips")


def cmd_pick(a):
    """The film is made from board `a.board`; everything made from the board picked before goes first, so nothing of
    one look reaches the film of another. out/boards.png stays (it is the three looks the person picks from), and so
    does a track the person placed."""
    import shutil
    import studio
    bs = {b["id"]: b for b in boards()}
    n = str(a.board)
    if n not in bs:
        sys.exit(f"no board {n}: the boards are {', '.join(bs)}")
    with studio.lock("pick"):
        win = _env.read_json("winner.json") or {}
        for name in MADE:
            p = Path(name)
            if name == "music" and p.is_dir():
                # a track the person placed (music/source.<ext>) is theirs, never the look's
                for f in p.iterdir():
                    if f.stem != "source":
                        shutil.rmtree(f) if f.is_dir() else f.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink(missing_ok=True)
        for p in list(Path("render").glob("*")) + list(Path("out").glob("*")):
            if p.name in ("boards.png",) or p.name.startswith(".") or p.name.endswith(".lock"):
                continue
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        b = bs[n]
        _env.write_json("winner.json", dict(win, board=n, name=b["name"], style=b["style"], by="the person" if not a.taste else "their taste",
                                            why=(a.why or "").strip()))
    print(f"picked storyboard {n} ({b['look']}){': ' + a.why.strip() if a.why else ''}; the music, the cut and the film of "
          "the look before are removed; next: music.py make, storyboard.py snap, film.py preview, qa.py check, music.py master, "
          "film.py render, deliver.py")
    return 0


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    """The next round for a film the critics have not had yet; for the film the newest round is already for, that
    round, so cut run again (after a kill, or twice) never spends the one fix on the same film."""
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    film = Path("out/film.mp4")
    # the render report is the index of out/: without it out/ is not one finished render
    if not Path("render/film-report.json").exists() or not film.exists():
        sys.exit("out/ is not a finished render (render/film-report.json or out/film.mp4 is missing): run film.py render")
    digest = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    stale = unread(digest)
    if stale:
        sys.exit(stale)
    rs = rounds()
    if rs and (_env.read_json(rs[-1]) or {}).get("film") == digest:
        print(f"round {len(rs)} is already for this out/film.mp4: fill in {rs[-1]}")
        return 0
    n = len(rs) + 1
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = digest
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f} after watching out/film.mp4 and the frames in frames/"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def unread(digest):
    """Why the film `digest` cannot be scored yet: its measurements (qa.py check) or its frames (film.py frames) are
    another film's; None when both are this film's."""
    if (_env.read_json("qa/check.json") or {}).get("film") != digest:
        return "qa/check.json does not describe out/film.mp4: run qa.py check on this render, then vote.py cut"
    if (_env.read_json("frames/frames.json") or {}).get("film") != digest:
        return "frames/ are not cut from out/film.mp4: run film.py frames on this render, then vote.py cut"
    return None


def repeated(data, before):
    """The critics whose paragraph in round `data` is the round `before`'s word for word."""
    words = lambda d, c: " ".join(((d.get("critics", {}).get(c) or {}).get("boards", {}).get("film", {}).get("paragraph") or "").split())
    return [c for c in CUT_PANEL if words(data, c) and words(data, c) == words(before, c)]


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    stale = unread(data.get("film"))
    if stale:
        print(f"{rs[-1]} is not a read of the film it is for: {stale}")
        return 1
    bad = problems(data, CUT_PANEL, ["film"])
    if len(rs) >= 2:
        before = _env.read_json(rs[-2]) or {}
        bad += [f"{c}: the paragraph is round {before.get('round')}'s word for word; watch this round's frames and write what they show"
                for c in repeated(data, before)]
        if len((data.get("fixed") or "").split()) < 3:
            bad.append("fixed: say what changed since the last round")
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    res = against(data, CUT_PANEL, "film")
    worst = min((v, k) for k, v in res["criteria"].items())
    if res["clears"]:
        print(f"SHIP: round {data.get('round')}, mean {res['mean']:.2f}, every criterion {FLOOR} or more")
        return 0
    if len(rs) >= 2:
        print(f"round {data.get('round')}: mean {res['mean']:.2f}, lowest {worst[1]} {worst[0]:.2f}, under the bar. The one fix "
              "is spent; deliver this cut, the best there is, and deliver.py writes its scores in brief.md")
        return 2
    print(f"FIX ONCE: mean {res['mean']:.2f}, the worst thing is {worst[1]} ({CRITERIA[worst[1]]}) at {worst[0]:.2f}. Fix it, "
          "re-render, then run vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "cut", "verdict"])
    ap.add_argument("--board", help="pick: the board the film is made from")
    ap.add_argument("--why", help="pick: why this look, in one line (from what the person said, or from their taste)")
    ap.add_argument("--taste", action="store_true", help="pick: the look was picked from their taste, not asked")
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "pick" and not a.board:
        sys.exit("pick needs --board N")
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
