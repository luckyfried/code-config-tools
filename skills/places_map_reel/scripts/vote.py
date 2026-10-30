#!/usr/bin/env python3
"""Movement 3 (the panel scores the three looks and one is chosen), the critic's read of the timed cut, and the
critics' score of the film.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/vote.py ballot    # vote/ballot.md + vote/scores.json to fill in (scores and the swap test)
    python3 S/scripts/vote.py tally     # vote.md + winner.json (highest total among the boards that pass the swap test)
    python3 S/scripts/vote.py pick --board N [--why "..."]
                                        # the look the film is made in: N is 1, 2 or 3 (first, second or third on
                                        # out/boards.png) or the style's id; the person's answer, or the agent's pick by
                                        # taste with its one-line reason in --why. A pick after a film starts the cut
                                        # again: the next steps run from the music in this run's folder
    python3 S/scripts/vote.py timed     # critic/timed.json to fill in: the monotony read of the timed cut
    python3 S/scripts/vote.py cut       # critic/cut-N/ (the frames of this render a round reads) and critic/cut-N.json
    python3 S/scripts/vote.py verdict   # SHIP at the bar, FIX ONCE with the lever that fixes the worst rule, or UNDER THE
                                        # BAR: the best cut is delivered with its scores in brief.md

The boards are the run's three looks, storyboards/<style>/ (storyboard.py styles()). The panel (S/critic/critic.md has
each critic's brief and the seven rules): a motion designer, an editor and the person, modeled from taste.md. Each
scores every look 1-5 on R1 to R7 and writes one paragraph per look. The motion designer also applies the swap test
to each look's three compositions (the hook, the stop and the closer, on its sheet): a composition passes when another
person's year, with their own places, route and photographs, would change the frame (the region the map shows, the
route the dot drew, the photograph, its place's name and line, the places named at the closer), and fails when any
year's photographs would sit in it unchanged. A look with a composition that fails cannot win the tally. The tally's
winner stands until a pick names another; the person's choice is the pick.

Before the film renders, the editor reads the timed cut (preview/film.mp4 and every strip, listed in `seen`) for
monotony; film.py render waits for that read to pass. The finished cut is scored by the motion designer and the person
on the same rules, from the frames vote.py cut takes from this render (the first frame, sixteen at equal spacing, each
beat as the camera leaves it, and each shape's closer at rest at full size, each listed in `seen`). A rule nobody in
the session can read is null with a sentence in `unread`. A score under 4 names a `lever` (critic.md's levers, or
"none" when no lever reaches it); round 2 opens only on a new film. The bar is a mean of 4.5 or more with no rule under
4. The verdict never blocks the film: it ships at the bar, asks once for the fix its lever names, or delivers the best
cut under the bar with every score in brief.md (verdict.json carries the verdict to deliver.py); scores never reach the
review page.
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

RESTS = ("hook", "stop", "closer")

CRITERIA = {
    "R1": "concept and motivated transitions: one idea from the first second, a motif that pays off, every move the style's own act, never a crossfade",
    "R2": "image treatment: layers that move at their own rates in every hold, shadows, grain, one grade over every photograph and the paper",
    "R3": "type in motion as a system: two faces, a scale, words entering on the kit's curve with tracking that resolves, settled within a second",
    "R4": "motion and rhythm: one camera with anticipation and overshoot, no two consecutive moves alike, the peak longest, the closer still",
    "R5": "sound to picture: cues only where beats land, effects 8 LU under the music, the music stopping with the picture",
    "R6": "generated shots: every clip request a shot a cinematographer would write, for the hook's world, texture or a still brought to life",
    "R7": "the deliverable: out/ holds the three films, the post, the story card, the caption and the review page as the film's cover",
}
# the frames at equal spacing a cut round is read from, how long before a landing the beat before it is read as the
# camera leaves it, the lowest score a rule may take, and the mean the scores reach at the bar
CUT_FRAMES, LEAVING, BAR, MEAN = 16, 0.5, 4, 4.5
# each shape's film in out/
SHAPES = {"reel": "film.mp4", "landscape": "film-16x9.mp4", "square": "film-square.mp4"}
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def styles():
    import storyboard
    return storyboard.styles()


def boards():
    """The three looks, whose boards are whole (plan.json) and whose sheet was rendered from them (storyboard.py removes
    the sheet when it writes the boards again)."""
    want = styles()
    out = [t for t in want if all((Path("storyboards") / t / x).exists() for x in ("plan.json", "sheet.png"))]
    if len(out) < len(want):
        sys.exit(f"{len(out)} of {len(want)} storyboards with plan.json and a sheet: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def blank_swap(ids):
    return {i: {r: {"pass": None, "why": ""} for r in RESTS} for i in ids}


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every look 1-5 on each criterion, as each critic, and write one paragraph per look "
             "(what works, what fails, what you would change). Look at each sheet before scoring.", "",
             "Then the swap test, as the motion designer, on each board's three compositions (the hook, the stop and the "
             "closer, left to right on its sheet): `pass` is true when another person's year, with their own places, moments "
             "and photographs, would change the frame (the region the map shows, the route, the photograph, a name, their line, "
             "the places named at the closer), false when any year's photographs would sit in it unchanged. "
             "`why` names what in the frame comes from the data, in one sentence. A board that fails one cannot win.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    import storyboard
    for k, b in enumerate(bs):
        sb = Path("storyboards") / b
        lines += [f"### {b} ({storyboard.LOOKS[k].lower()})", "", f"- storyboard: {sb.resolve() / 'storyboard.md'}",
                  f"- style sheet: {sb.resolve() / 'sheet.png'} (frames in {sb.resolve() / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, dict(blank(PANEL, bs), swap=blank_swap(bs)))
    print(f"ballot -> {(d / 'ballot.md').resolve()}; scores and the swap test to fill -> {f.resolve()}")
    return 0


def problems(data, panel, ids):
    """What a ballot or a cut round still lacks: a whole number 1-5 for every rule, or null with a sentence in
    `unread` saying why nobody in the session can read it; a paragraph per critic; on a cut round, every frame of the
    round in `seen`, a `lever` when a score is under 4, and from round 2 what changed."""
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            for k in CRITERIA:
                v = (e.get("scores") or {}).get(k)
                if v is None and len(((e.get("unread") or {}).get(k) or "").split()) >= 5:
                    continue
                if not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / board {i} / {k}: needs a whole number 1-5, or null with unread.{k} saying why nobody can read it (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / board {i}: the paragraph needs at least 25 words")
    if data.get("frames") is not None:
        missed = sorted(set(data["frames"]) - set(data.get("seen") or []))
        if missed:
            bad.append(f"seen: view every frame of this round and list it; not seen: {', '.join(missed[:6])}" + (" ..." if len(missed) > 6 else ""))
        sc = scores_of(data, panel)
        if sc and min(sc) < BAR:
            lv = data.get("lever") or {}
            if not lv.get("name") or (lv["name"] != "none" and len((lv.get("change") or "").split()) < 5):
                bad.append("lever: a score is under 4, so name the lever that fixes the worst rule (critic.md's levers: "
                           "name, and change in at least 5 words), or name \"none\" when no lever reaches it")
    if (data.get("round") or 1) > 1 and len((data.get("fixed") or "").split()) < 8:
        bad.append("fixed: say in at least 8 words what changed since the last round")
    return bad


def scores_of(data, panel):
    """Every score a round gave, the unread ones left out."""
    return [v for c in panel for e in ((data.get("critics", {}).get(c) or {}).get("boards") or {}).values()
            for v in (e.get("scores") or {}).values() if isinstance(v, int)]


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
    total = lambda c, i: sum(v for v in data["critics"][c]["boards"][i]["scores"].values() if isinstance(v, int))
    tot = {i: sum(total(c, i) for c in PANEL) for i in ids}
    person = {i: total("person", i) for i in ids}
    passed = {i: all(data["swap"][i][r]["pass"] for r in RESTS) for i in ids}
    if not any(passed.values()):
        print("no board passes the swap test: every one has a composition whose photograph could be swapped; "
              "change the builder's layout for those places and draft again")
        return 1
    order = sorted(ids, key=lambda i: (not passed[i], -tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if passed[i] and tot[i] == tot[win]]
    names = {i: i for i in ids}
    lines = ["# the vote", "", f"Winner: {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""),
             "",
             "| critic | " + " | ".join(f"board {i}" for i in ids) + " |", "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(str(total(c, i)) for i in ids) + " |")
    lines.append("| total | " + " | ".join(f"**{tot[i]}**" for i in ids) + " |")
    lines.append("| swap test | " + " | ".join("pass" if passed[i] else "fails: " + ", ".join(r for r in RESTS if not data["swap"][i][r]["pass"]) for i in ids) + " |")
    lines += ["", "## scores by criterion", "", "| board | critic | " + " | ".join(CRITERIA) + " |", "|---|---|" + "---|" * len(CRITERIA)]
    for i in ids:
        for c in PANEL:
            s = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {i} | {c} | " + " | ".join(str(s[k]) if s[k] is not None else "unread" for k in CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### {names[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
        lines += [f"**The swap test.** " + " ".join(f"{r}: {'passes' if data['swap'][i][r]['pass'] else 'fails'}, {data['swap'][i][r]['why'].strip()}" for r in RESTS), ""]
    # winner.json vouches for vote.md, so it goes before vote.md changes and comes back after
    Path("winner.json").unlink(missing_ok=True)
    _env.write_text("vote.md", "\n".join(lines))
    _env.write_json("winner.json", {"board": win, "name": names[win], "totals": tot, "order": order, "swap": passed,
                                    "swap_passed": passed[win], "tie_broken_by_person": len(tie) > 1, "by": "tally"})
    print(f"winner: {win}, totals {tot}, swap test {passed} -> vote.md, winner.json; show out/boards.png and ask which look "
          "where you may ask, then vote.py pick")
    return 0


# the steps a pick runs again from, in the run's folder
AFTER_PICK = ("music.py make (or find)", "storyboard.py snap", "storyboard.py sheets", "film.py preview", "vote.py timed",
              "qa.py timed", "music.py master", "film.py render", "vote.py cut", "vote.py verdict", "deliver.py")


def cmd_pick(a):
    """The look the film is made in. A pick of a look other than the one the last film was made in removes that film's
    cut (film.json) and its rounds, so the steps after it run again on the new look."""
    ids = boards()
    n = str(a.board).strip()
    style = ids[int(n) - 1] if n.isdigit() and 1 <= int(n) <= len(ids) else n
    if style not in ids:
        sys.exit(f"no look {a.board}: name 1 to {len(ids)} (as out/boards.png orders them) or one of {', '.join(ids)}")
    old = _env.read_json("winner.json") or {}
    cut = (_env.read_json("film.json") or {}).get("style")
    if cut and cut != style:
        for p in [Path("film.json"), Path("critic/timed.json"), Path("verdict.json"), *Path("critic").glob("cut-*.json")]:
            p.unlink(missing_ok=True)
    keep = {k: old[k] for k in ("totals", "order", "swap") if k in old}
    _env.write_json("winner.json", {**keep, "board": style, "name": style, "by": "taste" if a.why else "person",
                                    "why": a.why or None, "swap_passed": (old.get("swap") or {}).get(style)})
    print(f"the film is made in {style}" + (f" ({a.why})" if a.why else "") + "; next, in this run's folder: " + ", ".join(AFTER_PICK))
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
        miss = unseen(old)
        if miss:
            print(f"{path}: the read lists no view of {', '.join(miss)}; open every strip, add each to monotony.seen")
            return 1
        print(f"{path} already holds the read of this cut: {'pass' if old['monotony']['pass'] else 'fail'}")
        return 0 if old["monotony"]["pass"] else 2
    strips = strips_of(pv)
    _env.write_json(path, {"hash": f["hash"], "style": f["style"], "monotony": {"pass": None, "read": "", "seen": []},
                           "film": str(Path("preview/film.mp4").resolve()), "strips": strips,
                           "measured": {k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_event_frame")}})
    print(f"the monotony read, as the editor: watch {Path('preview/film.mp4').resolve()} and open every strip ({len(strips)}: "
          f"{', '.join(strips)}), then fill in {path.resolve()}: monotony.pass (false when moves repeat one shape, one size "
          "or one length so the eye stops expecting anything), monotony.read (at least 25 words: where the rhythm "
          "changes, where it does not) and monotony.seen (every strip you opened)")
    return 0


def strips_of(pv):
    """The preview's strips, by file name: the 2 fps strip and every 12 fps one."""
    return [Path(p).name for p in [pv.get("strip2"), *(pv.get("strip12") or [])] if p]


def unseen(read):
    """The strips of the timed cut its monotony read does not list as seen."""
    return [s for s in read.get("strips") or [] if s not in set((read.get("monotony") or {}).get("seen") or [])]


def cmd_cut(a):
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    film = Path("out/film.mp4")
    # render/film-report.json is the index of out/: it comes back only once every film is in place
    if not Path("render/film-report.json").exists() or not film.exists():
        sys.exit("render/film-report.json or out/film.mp4 is missing: run film.py render first")
    digest = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    # an unscored round is kept for the same film; a scored round under the bar with a lever opens round 2 once the
    # lever's change has reached a new film; there are two rounds at most
    rs = rounds()
    last = (_env.read_json(rs[-1]) or {}) if rs else {}
    scored = bool(rs) and not problems(last, CUT_PANEL, ["film"])
    if rs and not scored and last.get("film") == digest:
        print(f"round {len(rs)}: {rs[-1].resolve()} is the round of this out/film.mp4; view every frame in {Path('critic') / f'cut-{len(rs)}'}/ and fill it in")
        return 0
    if scored and (len(rs) >= 2 or ending(last)):
        print(f"round {len(rs)} is scored and no further round opens: run vote.py verdict")
        return 0
    if scored and last.get("film") == digest:
        lv = last.get("lever") or {}
        sys.exit(f"out/film.mp4 is the film round {len(rs)} scored: the lever ({lv.get('name')}: {lv.get('change')}) has not "
                 "reached the film; make its change and run the steps after it through film.py render, then vote.py cut")
    n = len(rs) + 1
    frames = cut_frames(film, d / f"cut-{n}")
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    for c in CUT_PANEL:
        data["critics"][c]["boards"]["film"]["unread"] = {}
    data.update(round=n, film=digest, frames=frames, seen=[], lever=None, fixed="" if n > 1 else None)
    _env.write_json(f, data)
    print(f"round {n}: view every frame in {(d / f'cut-{n}').resolve()}/ ({len(frames)}), watch out/film.mp4, then fill in {f.resolve()}"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def cut_frames(film, into):
    """The frames a round is read from, as JPEGs in `into`: the film's first frame; CUT_FRAMES at equal spacing, each in
    the middle of its share of the film; each beat as the camera leaves it, LEAVING seconds before the next landing
    (film.json's cuts); and each shape's closer at rest, at full size (film.json's rests)."""
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(film)],
                       capture_output=True, text=True)
    secs = float(r.stdout.strip() or 0)
    timing = _env.read_json(Path("film.json")) or {}
    fps = timing["frames"] / timing["seconds"] if timing.get("frames") and timing.get("seconds") else 30
    shots = [("first", film, 0.0)] + [(f"f{i + 1:02d}", film, (i + 0.5) * secs / CUT_FRAMES) for i in range(CUT_FRAMES)]
    shots += [(f"leave{k + 1:02d}", film, c - LEAVING) for k, c in enumerate(timing.get("cuts") or []) if c > LEAVING]
    shots += [(f"closer-{shape}", Path("out") / SHAPES[shape], rest["closer"] / fps)
              for shape, rest in (timing.get("rests") or {}).items() if shape in SHAPES and (Path("out") / SHAPES[shape]).exists()]
    into.mkdir(parents=True, exist_ok=True)
    for old in into.glob("*.jpg"):
        old.unlink()
    out = []
    for label, src, at in shots:
        name = f"{label}-t{at:06.3f}.jpg"
        subprocess.run([_env.ffmpeg(), "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(src), "-frames:v", "1", "-q:v", "2",
                        str(into / name)], check=True)
        out.append(name)
    return out


def ending(data):
    """A scored round that closes the cut: at the bar, or under it where no lever reaches."""
    return not scores_of(data, CUT_PANEL) or at_bar(data) or (data.get("lever") or {}).get("name") == "none"


def worst_of(data):
    """The lowest score of a filled cut round, with its rule and critic (none when every rule is unread)."""
    got = [(v, k, c) for c in CUT_PANEL for k, v in data["critics"][c]["boards"]["film"]["scores"].items() if isinstance(v, int)]
    return min(got) if got else (None, None, None)


def stated(data):
    """Every rule's score from each critic, the unread ones named as such, and the mean of the scores read."""
    rows = []
    for k in CRITERIA:
        got = [data["critics"][c]["boards"]["film"]["scores"].get(k) for c in CUT_PANEL]
        rows.append(f"{k} " + "/".join("unread" if v is None else str(v) for v in got))
    sc = scores_of(data, CUT_PANEL)
    return ", ".join(rows) + (f"; mean {sum(sc) / len(sc):.2f}" if sc else "")


def mean_of(data):
    sc = scores_of(data, CUT_PANEL)
    return sum(sc) / len(sc) if sc else None


def at_bar(data):
    """Whether a scored round is at the bar: the mean of its scores at MEAN or over and no rule under BAR."""
    sc = scores_of(data, CUT_PANEL)
    return bool(sc) and min(sc) >= BAR and sum(sc) / len(sc) >= MEAN


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
    worst = worst_of(data)
    scores = stated(data)
    mean = mean_of(data)
    lever = data.get("lever") or {}
    record = {"round": data.get("round"), "mean": None if mean is None else round(mean, 2), "worst": worst[0], "scores": scores}
    if at_bar(data):
        _env.write_json("verdict.json", {**record, "verdict": "ship"})
        print(f"SHIP: round {data.get('round')} is at the bar (mean {mean:.2f}, no rule under {BAR}): {scores}")
        return 0
    if len(rs) < 2 and lever.get("name") not in (None, "none"):
        _env.write_json("verdict.json", {**record, "verdict": "fix"})
        print(f"FIX ONCE: the worst rule is {worst[1]} ({CRITERIA[worst[1]]}), {worst[2]} gave {worst[0]}. The lever: "
              f"{lever.get('name')}, {lever.get('change')}. Make that change, run the steps after it through film.py render, "
              f"then vote.py cut for round 2. Scores: {scores}")
        return 2
    _env.write_json("verdict.json", {**record, "verdict": "under"})
    print(f"UNDER THE BAR: round {data.get('round')}, mean {'unread' if mean is None else f'{mean:.2f}'}, worst {worst[1]} at "
          f"{worst[0]}; the cut is delivered as the best the run made, and brief.md carries every score: {scores}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timed", "cut", "verdict"])
    ap.add_argument("--board", help="pick: 1, 2 or 3 as out/boards.png orders the looks, or the style's id")
    ap.add_argument("--why", help="pick: the one-line reason, when the agent picks by taste because it may not ask")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.board:
        ap.error("pick needs --board")
    _env.enter_run()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timed": cmd_timed, "cut": cmd_cut,
            "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
