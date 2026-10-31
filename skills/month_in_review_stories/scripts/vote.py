#!/usr/bin/env python3
"""Movement 3 (the panel scores the three boards, and the person picks a look), the timed read before the render, and
movement 5 (two critics score the finished cut).

USAGE (from the workspace root; S = this skill's folder; every path below is inside the run's build folder):
    python3 S/scripts/vote.py ballot     # vote/ballot.md + vote/scores.json to fill in
    python3 S/scripts/vote.py tally      # vote.md + winner.json: the boards ranked by their mean, the first the winner
    python3 S/scripts/vote.py pick N|STYLE [--reason "..."]
                                         # the look the person picked (or, where the agent may not ask, the one it
                                         # picked by their taste, the reason in one line) becomes the winner
    python3 S/scripts/vote.py timed      # critic/timed.json: the four reads of the previewed reel, to fill in; run it
                                         # again once they are written, and it records what they found
    python3 S/scripts/vote.py cut        # critic/cut-N.json to fill in for the rendered film, series and cards (round N)
    python3 S/scripts/vote.py verdict    # the latest round against the bar: AT THE BAR, FIX ONCE (the lowest rule the
                                         # agent has a lever for), or SPENT (deliver the best cut with its scores)

The boards are three looks of one story (storyboard.py draft). The panel (S/critic/critic.md has each critic's brief):
a motion designer (craft, pacing, type, motion), an editor (story, one idea per beat, the series as a set) and the
person, modeled from taste.md (is this unmistakably my month; would I post it). Each scores every board on the seven
rules of studio grade below (CRITERIA, R1 to R7) and writes one paragraph a board; tally ranks the boards by the mean
of their scores (board order between equals) and the first is the winner until the person picks. pick makes the look
the person picked the winner (1, 2 or 3 in out/boards.png's order, or its style id); a pick of another look than the
winner removes everything made for the old one (music.json and music/, preview/, critic/timed.json, the cut rounds,
film.json), so the steps after the vote run again for the new look in the same run folder. A score is a whole number 1-5,
or "not read" when nobody in the session can make that read, and the paragraph says why; "not read" never counts as
meeting the rule. A board stands only when its gates passed (storyboards/check.json, with the swap test, and
storyboards/sheets.json). The timed read watches the previewed reel (film.py preview) with the four reads below, each
a pass, a fail, or "not read"; film.py render needs the reads made for this board and reports what they found, and
never refuses on a failed read. The finished cut (the film, the series when they asked for it, every animated card and
every still) is scored by the motion designer and the person on the same rules; the round records a fingerprint of
those files so the gate knows it is current, and a round after the first names what was fixed and reads the new
frames: none of its paragraphs repeats the round before. Each rule's score is the lower of the two critics'. The bar
is BAR: a mean of 4.5 over the seven rules and none under 4. Under the bar after the first cut, the verdict names the
lowest rule the agent has a lever for (LEVERS) and the one fix it makes; with no lever left, or after the second cut,
the fix is spent and the cut is delivered as the best one, every score stated against the bar.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CRITERIA = {
    "R1": "one concept: the hook states the month in its first second, the line recurs on every beat and pays off in the "
          "closer lighting every moment, and every move between beats is the line's own act, never a crossfade",
    "R2": "image treatment: the photograph, its ground and the wall move at different rates with the camera, light wraps "
          "every cut edge, a shadow sits under every floating card, grain over all and one grade on every photograph and "
          "field in the board's style; the stand-in for a clip is this layered move, and the closer's still stays still",
    "R3": "type in motion: the style's two faces and a scale, words entering on its curves with tracking that resolves, never "
          "a fade, settled within a second of their beat, every line at rest inside the safe area, nothing colliding",
    "R4": "motion and rhythm: one continuous camera with anticipation before a big move and overshoot where a thing "
          "lands, no two consecutive beats making the same move, the peak held longest, the closer still and silent after the ask",
    "R5": "sound to picture: a cue only where a beat lands, the effects 8 LU under the music, the music stopping where the ask lands",
    "R6": "generated shots: every clip request a shot a cinematographer would write (subject, move, lens, light, the "
          "beat's duration, a seamless loop) for the hook's world, the texture between chapters, or a still brought to life",
    "R7": "the deliverable: out/ holds the films, the cover, the cards, the caption and the review page as the film's "
          "cover, and nothing a viewer could mistake for the product",
}
NOT_READ = "not read"
BAR = {"mean": 4.5, "least": 4}
# what the agent changes when a rule is under the bar after the first cut; R2 and R7 are the motion system's and the
# kit's own, so the agent has no lever for them
LEVERS = {
    "R1": "taste.json: the moments and the line each says on screen",
    "R3": "taste.json: each moment's line, shorter so it sets larger and breaks cleanly",
    "R4": "taste.json: which moment is the peak and the line each moment holds for",
    "R5": "taste.json `music`: the styles and avoid words of the bed",
    "R6": "taste.json `moments[].shot`: each shot rewritten as a cinematographer would write it from its photograph",
}
AGAIN = ("then movement 2 again (storyboard.py draft, check, sheets, the vote) and movement 4 (music.py make, clips.py "
         "list and normalize, film.py preview, vote.py timed, film.py render), and vote.py cut for round 2")
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}
# the four reads of the timed cut, each a pass, a fail, or "not read", with at least 25 words on where it holds and
# where it does not, or on why nobody in the session can make it
READS = {
    "carried": "one element is carried across every transition (the line, the photograph setting into its post's cell on the wall of the month's posts)",
    "sound": "a sound where each beat lands and nowhere else, under the music",
    "swap": "the motion belongs to the photograph: under another photograph the same move would stop making sense",
    "held": "one held thing per beat, and no beat holds longer than its words need",
}


def gated(run):
    """The styles whose board checks and rest sheets both passed."""
    ck = (_env.read_json(run / "storyboards" / "check.json") or {}).get("boards", {})
    sh = (_env.read_json(run / "storyboards" / "sheets.json") or {}).get("boards", {})
    return {t for t in ck if ck[t].get("ok") and t in sh and not sh[t].get("findings")}


def boards(run):
    import storyboard
    out = list(storyboard.load_boards(run).values())
    ok = gated(run)
    if not out or (_env.read_json(run / "storyboards" / "check.json") or {}).get("ok") is not True or any(b["style"] not in ok for b in out):
        sys.exit("the three boards have not passed storyboard.py check and sheets: run them and fix what they name")
    return out


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def cmd_ballot(a):
    run = _env.run()
    bs = boards(run)
    d = run / "vote"
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score each of the three boards 1-5 on each rule, as each critic, and write one paragraph a board "
             "(what works, what fails, what you would change). Look at each board's reel sheet and rest sheet before scoring. "
             f"A rule nobody can read from a board is scored \"{NOT_READ}\", and the paragraph says why.", "",
             "## the rules", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for n, b in enumerate(bs, 1):
        sb = run / "storyboards" / b["style"]
        lines += [f"### {n}. {b['style']}: {b['name']}", "", "; ".join(f"{i + 1:02d} {c['idea']}" for i, c in enumerate(b["beats"])), "",
                  f"- {b['bpm']} bpm, {sum(len(c['shots']) for c in b['beats'])} shots" + ("; follows last month's template" if b.get("follows") else ""),
                  f"- storyboard: {sb / 'storyboard.md'}", f"- reel sheet: {sb / 'reel-sheet.png'}",
                  f"- rest sheet: {sb / 'sheet.png'} (stills in {sb / 'rest'}/)", ""]
    lines += [f"Fill in {d / 'scores.json'}, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["style"] for b in bs]))
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
                if v != NOT_READ and (not isinstance(v, int) or isinstance(v, bool) or not 1 <= v <= 5):
                    bad.append(f"{c} / board {i} / {k}: needs a whole number 1-5, or \"{NOT_READ}\" (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / board {i}: the paragraph needs at least 25 words")
    return bad


def cmd_tally(a):
    run = _env.writable_run()
    bs = boards(run)
    ids = [b["style"] for b in bs]
    data = _env.read_json(run / "vote" / "scores.json")
    if not data:
        sys.exit(f"{run / 'vote' / 'scores.json'} is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    read = {i: [v for c in PANEL for v in data["critics"][c]["boards"][i]["scores"].values() if v != NOT_READ] for i in ids}
    tot = {i: sum(v) for i, v in read.items()}
    means = {i: round(sum(v) / len(v), 2) if v else 0.0 for i, v in read.items()}
    ranked = sorted(ids, key=lambda i: (-means[i], ids.index(i)))
    win = ranked[0]
    names = {b["style"]: b["name"] for b in bs}
    follows = next((b["style"] for b in bs if b.get("follows")), None)
    lines = ["# the vote", "", f"The board: {win}, {names[win]} (a mean of {means[win]} over the {len(read[win])} scores read)."
             + (f" {follows} follows last month's template, so the series matches." if follows else ""), "",
             "| board | critic | " + " | ".join(CRITERIA) + " | mean |", "|---|---|" + "---|" * (len(CRITERIA) + 1)]
    for i in ranked:
        for c in PANEL:
            sc = data["critics"][c]["boards"][i]["scores"]
            got = [v for v in sc.values() if v != NOT_READ]
            lines.append(f"| {i} | {PANEL[c]} | " + " | ".join(str(sc[k]) for k in CRITERIA) + f" | {sum(got) / len(got) if got else 0:.2f} |")
    lines += ["", "## what the critics said", ""]
    for i in ranked:
        lines += [f"### {i}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
    # winner.json vouches for vote.md, so it goes before vote.md changes and comes back after it
    (run / "winner.json").unlink(missing_ok=True)
    _env.write_text(run / "vote.md", "\n".join(lines))
    _env.write_json(run / "winner.json", {"board": win, "name": names[win], "totals": tot, "means": means, "order": ids,
                                          "ranked": ranked, "picked_by": "the panel", "follows": follows})
    print(f"the board: {win} ({names[win]}), a mean of {means[win]}; ranked {', '.join(f'{i} {means[i]}' for i in ranked)} -> "
          f"{run / 'vote.md'}, {run / 'winner.json'}. Show out/boards.png and ask which look; vote.py pick N makes it the winner")
    return 0


# what was made for the winning look, and goes when another look is picked
MADE_FOR_WINNER = ("music.json", "film.json", "critic/timed.json", "preview/preview.json")


def cmd_pick(a):
    run = _env.writable_run()
    win = _env.read_json(run / "winner.json") or {}
    if not win.get("board"):
        sys.exit("no vote yet: run vote.py ballot, fill it in, then vote.py tally")
    order = win.get("order") or []
    want = order[int(a.look) - 1] if a.look.isdigit() and 1 <= int(a.look) <= len(order) else a.look
    if want not in order:
        sys.exit(f"{a.look!r} is not one of the looks: 1, 2 or 3, or {', '.join(order)}")
    by = f"the agent, by their taste: {a.reason.strip()}" if a.reason else "the person"
    if want != win["board"]:
        import shutil
        for rel in MADE_FOR_WINNER:
            (run / rel).unlink(missing_ok=True)
        for p in rounds(run):
            p.unlink()
        shutil.rmtree(run / "music", ignore_errors=True)
    names = {b["style"]: b["name"] for b in boards(run)}
    _env.write_json(run / "winner.json", dict(win, board=want, name=names[want], picked_by=by))
    print(f"the look: {want} ({names[want]}), picked by {by} -> {run / 'winner.json'}"
          + (f"; what was made for {win['board']} is gone, so run music.py make and every step after it" if want != win["board"] else ""))
    return 0


def cmd_timed(a):
    import studio
    run = _env.run()
    won = (_env.read_json(run / "winner.json") or {}).get("board")
    if not won:
        sys.exit("no winner: run vote.py tally (and vote.py pick) first")
    sb = run / "storyboards" / won
    b = _env.read_json(sb / "storyboard.json")
    pv = _env.read_json(run / "preview" / "preview.json") or {}
    h = studio.board_hash(b) if b else None
    if not b or pv.get("hash") != h:
        sys.exit("preview/preview.json is not for the current board: run storyboard.py draft and film.py preview first")
    path = run / "critic" / "timed.json"
    old = _env.read_json(path) or {}
    if old.get("hash") == h:
        reads = old.get("reads") or {}
        made = lambda v: isinstance(v, bool) or v == NOT_READ
        bad = [k for k in READS if not made((reads.get(k) or {}).get("pass")) or len(((reads.get(k) or {}).get("read") or "").split()) < 25]
        if bad:
            print(f"{path} is not complete: {', '.join(bad)} need a pass (true, false or \"{NOT_READ}\") and a read of at least 25 words")
            return 1
        # the reads are made: true only when every one of them passed, false when one failed, else "not read"
        got = [reads[k]["pass"] for k in READS]
        old["pass"] = False if False in got else True if all(v is True for v in got) else NOT_READ
        _env.write_json(path, old)
        print("the timed read of this board: " + "; ".join(f"{k} {'pass' if reads[k]['pass'] is True else 'fail' if reads[k]['pass'] is False else NOT_READ}"
                                                            for k in READS) + ". film.py render reports these and renders the board")
        return 0
    _env.write_json(path, {"hash": h, "pass": None, "reads": {k: {"pass": None, "read": ""} for k in READS},
                           "film": str((run / "preview" / "film.mp4").resolve()), "strips": [pv.get("strip"), pv.get("strip2")],
                           "storyboard": str((sb / "storyboard.md").resolve()),
                           "measured": {k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_frame", "lufs")}})
    print(f"the timed read: read {sb / 'storyboard.md'}, watch {(run / 'preview' / 'film.mp4').resolve()} "
          f"with sound and look at its strips, then fill in {path.resolve()}, each read a pass (true, false, or \"{NOT_READ}\" when "
          "nobody in this session can make it) and at least 25 words:")
    for k, v in READS.items():
        print(f"  {k}: {v}")
    print("then run vote.py timed again")
    return 0


def cut_files(run):
    out = run / "out"
    return [out / "series.mp4", out / "film.mp4", out / "cover.png"] + sorted((out / "cards").glob("*.mp4")) + sorted((out / "cards").glob("*.png"))


def fingerprint(run):
    """One hash over the film, the series when it was made, the cover, and every card, animated and still."""
    h = hashlib.sha256()
    for f in cut_files(run):
        if f.exists():
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]


def rounds(run):
    return sorted((run / "critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    run = _env.run()
    d = run / "critic"
    d.mkdir(parents=True, exist_ok=True)
    # film.json is written once every file of a render is in out/, so a round only ever opens on a whole render
    if not (run / "film.json").exists():
        sys.exit(f"{run / 'film.json'} is missing: run film.py render first")
    # a round belongs to the files it scored: the newest round is reused while they stand, and only a new render opens one
    rs, fp = rounds(run), fingerprint(run)
    if rs and (_env.read_json(rs[-1]) or {}).get("film") == fp:
        print(f"round {len(rs)} is for the current files: fill in {rs[-1]} (a new round opens only after a new render)")
        return 0
    n = len(rs) + 1
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = fp
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f} after watching {run / 'out'}/film.mp4" + (" and series.mp4" if (run / "out" / "series.mp4").exists() else "")
          + f" with sound, every card in {run / 'out' / 'cards'}/ "
          f"and the strips in {run / 'timeline'}/, which this render wrote" + (" (say in 'fixed' what changed since the last round; "
          "each paragraph reads this cut's frames, never the last round's)" if n > 1 else ""))
    return 0


def round_problems(rs):
    """What the latest cut round still needs: every score and paragraph, and after the first round what was fixed and a
    read of the new frames, so no paragraph repeats the round before."""
    data = _env.read_json(rs[-1]) or {}
    bad = problems(data, CUT_PANEL, ["film"])
    if len(rs) >= 2:
        before = _env.read_json(rs[-2]) or {}
        if len((data.get("fixed") or "").split()) < 5:
            bad.append("fixed: say what changed since the last round")
        said = lambda d, c: " ".join((((d.get("critics") or {}).get(c) or {}).get("boards", {}).get("film") or {}).get("paragraph", "").split())
        bad += [f"{c}: the paragraph is the last round's; read the new cut's frames" for c in CUT_PANEL if said(data, c) and said(data, c) == said(before, c)]
    return bad


def standing(data):
    """Each rule's score in a round: the lower of the critics' whole numbers, or "not read" when one did not read it."""
    out = {}
    for k in CRITERIA:
        got = [data["critics"][c]["boards"]["film"]["scores"][k] for c in CUT_PANEL]
        out[k] = NOT_READ if NOT_READ in got else min(got)
    return out


def against_bar(sc):
    """(at the bar, the mean of the rules read, the words that state every score against the bar)."""
    got = [v for v in sc.values() if v != NOT_READ]
    mean = sum(got) / len(got) if got else 0.0
    ok = len(got) == len(sc) and mean >= BAR["mean"] and min(got) >= BAR["least"]
    said = (", ".join(f"{k} {v}" for k, v in sc.items()) + f"; mean {mean:.2f} over the {len(got)} rules read, against the bar "
            f"of a mean of {BAR['mean']} with none under {BAR['least']}")
    return ok, mean, said


def cmd_verdict(a):
    rs = rounds(_env.run())
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    bad = round_problems(rs)
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    data = _env.read_json(rs[-1])
    sc = standing(data)
    ok, mean, said = against_bar(sc)
    n = data.get("round")
    if ok:
        print(f"AT THE BAR: round {n}: {said}")
        return 0
    fixable = sorted((v, k) for k, v in sc.items() if k in LEVERS and v != NOT_READ and v < 5)
    if len(rs) >= 2 or not fixable:
        print(f"SPENT: round {n} is under the bar: {said}. " + ("The one fix is spent" if len(rs) >= 2 else "No rule under it has a lever")
              + "; deliver this cut as the best one, and build/<run>/brief.md states every score against the bar")
        return 0
    v, k = fixable[0]
    print(f"FIX ONCE: round {n} is under the bar: {said}. The lowest rule with a lever is {k} at {v} ({CRITERIA[k]}). "
          f"Change {LEVERS[k]}, {AGAIN}")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timed", "cut", "verdict"])
    ap.add_argument("look", nargs="?", help="pick: 1, 2 or 3 (out/boards.png's order), or the look's style id")
    ap.add_argument("--reason", help="pick: where the agent may not ask, why their taste picks this look, in one line")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.look:
        ap.error("pick needs the look: 1, 2 or 3, or its style id")
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timed": cmd_timed, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
