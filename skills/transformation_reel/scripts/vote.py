#!/usr/bin/env python3
"""The critic's three rounds: the storyboard (movement 3), the timed cut (movement 4) and the finished film (movement 5).

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/vote.py ballot     # RUN/vote/ballot.md + RUN/vote/scores.json to fill in
    python3 S/scripts/vote.py tally      # RUN/vote.md + RUN/winner.json (the board, when its styleframes pass the swap test)
    python3 S/scripts/vote.py pick <style> [--why "..."]
                                         # the look the person chose (or the one taste.json picks, with the reason):
                                         # RUN/winner.json names it; a different look than the run's film clears the cut
                                         # made for the other look, in this same run folder
    python3 S/scripts/vote.py timing     # the four reads on the timed cut's frames: RUN/critic/timing.json to fill in, then again to record it
    python3 S/scripts/vote.py cut        # RUN/critic/cut-<board>-N.json to fill in for the rendered cut, RUN/cut/film.mp4
                                         # (a new round N only when the cut changed since the newest round)
    python3 S/scripts/vote.py verdict    # the latest round against the bar: SHIP, FIX ONCE (the rule and its lever),
                                         # or DELIVER WITH SCORES

The run drafts three boards, one per look (storyboard.styles_of: A, B and C), and the vote scores all three. The panel
(S/critic/critic.md has each critic's brief): a motion designer (craft, pacing, type, transitions), an editor (story,
emotion, the ending) and the person, modeled from RUN/taste.md (is this unmistakably me; would I post it). Each scores each board 1-5
on the seven rules below (R1 to R7, the bar every film is held to: a mean of 4.5 and no rule under 4) and writes one
paragraph. A rule nobody in the session can read (the sound, without ears) goes in the critic's `not_read` with its
score empty, and is reported as not read, never as a pass. The motion designer also answers the swap test on the board's
styleframes (hook, ordinary beat, densest beat, closer): "holds" when the design is built on that photograph (its
edges, its piece, its date), "swappable" when another of their photographs could stand in it with nothing else
changed. A board with a swappable frame does not go on to the film. The tally recommends the board with the highest
total; the look the person picks (pick) is the one that is made.
The timing round is the motion designer's read of the timed cut, before anything is finished: the strips, the film
strip, the draft and the figures film.py draft wrote, with the four reads every film is held to (critic.md). It passes when the read says pass, no beat repeats the one before, and the first event lands in
the first 30 frames; a read in its `not_read` is recorded as not read. The rendered cut is scored by the motion
designer and the person on the seven rules, only once RUN/qa/check.json is the check of that cut. The verdict never
stops a delivery: the one fix is taken when a rule under the bar has a lever (LEVERS), and a cut still under the bar
after it, or with no lever for the rules under it, is delivered with its scores stated.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CRITERIA = {
    "concept": "R1 one idea, and every transition is motivated by it",
    "image": "R2 depth, light and one grade",
    "type": "R3 type in motion, designed as a system",
    "motion": "R4 motion with weight and a rhythm that varies",
    "sound": "R5 sound designed to the picture",
    "shots": "R6 the generated shots are the spectacle",
    "deliverable": "R7 the deliverable is unmistakable",
}
BAR, FLOOR = 4.5, 4
# the rules a session may be unable to read: the sound needs ears
UNREADABLE = {"sound"}
# what a run can change to raise a rule (critic.md, the levers), and what it reruns; None where no lever is inside a run
LEVERS = {
    "concept": "the subject, its posts and its milestones: research.py --subject \"...\" [--terms ...], then movements 1 to 5 again",
    "image": "the colors: palette in RUN/taste.json, then storyboard.py draft and movements 2 to 5 again",
    "type": "the look's type: the words' colors in RUN/taste.json, or, when taste picked the look, another look's faces "
            "(vote.py pick <style>; a look the person chose stays), then storyboard.py draft and movements 2 to 5 again",
    "motion": None,
    "sound": "the music: music.py find or music.py make, then music.py analyze, storyboard.py snap, music.py master, film.py draft, "
             "vote.py timing, film.py render",
    "shots": "the generated clips: make each clip RUN/clips/requests.json asks for with the session's video model, save it at "
             "its save_as path, then film.py render, qa.py check and vote.py cut",
    "deliverable": "the words around the film: RUN/caption.md, then deliver.py",
}
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}
FRAMES = ("hook", "ordinary", "dense", "closer")
READS = {
    "carried": "one element carried across every transition: what crosses each cut, and the cut where nothing does",
    "sound": "a sound where each beat lands and nowhere else, under the music",
    "belongs": "the motion belongs to the photograph (the swap test on the move): put another photograph under it and it stops making sense",
    "held": "one held thing per beat: what each beat holds still for the eye, and the beat that holds two or none",
}
# the reads a session may be unable to make: hearing the draft
UNHEARD = {"sound"}


def boards():
    """The run's boards in board order, A first."""
    import storyboard
    if not list(_env.b("storyboards").glob("*/storyboard.json")):
        sys.exit("no storyboard: run storyboard.py draft and sheets first")
    return storyboard.load_boards()


def blank(panel, ids, swap=False):
    def entry(c):
        e = {"scores": {k: None for k in CRITERIA}, "not_read": [], "paragraph": ""}
        if swap and c == "motion_designer":
            e["swap"] = {f: None for f in FRAMES}
        return e
    return {"critics": {c: {"boards": {i: entry(c) for i in ids}} for c in panel}}


def cmd_ballot(a):
    bs = boards()
    unsheeted = [x["style"] for x in bs if not _env.b("storyboards", x["style"], "sheet.png").exists()]
    if unsheeted:
        sys.exit(f"RUN/storyboards/{unsheeted[0]}/sheet.png is missing: run storyboard.py sheets first")
    d = _env.b("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score the storyboard 1-5 on each criterion, as each critic, and write one paragraph "
             "(what works, what fails, what you would change). Look at each styleframe at full size before scoring.", "",
             "## the seven rules", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["",
             "A rule nobody in the session can read (the sound, without ears) goes in the critic's `not_read` with its score "
             "empty; it is reported as not read, never as a pass.", "", "## the swap test", "",
             "The motion designer answers it on each of the board's styleframes, in `swap`: \"holds\" when the design is built on "
             "that photograph (its edges, its piece, its date), \"swappable\" when another of their photographs could stand in it "
             "with nothing else changed. A board with a swappable frame does not go on to the film.", "", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = _env.b("storyboards", b["style"])
        lines += [f"### {b['id']}: {b.get('title', '')}", "", b.get("idea", "") + ".", "",
                  f"- styleframes: " + ", ".join(str(sb / 'frames' / f'{f}.png') for f in FRAMES),
                  f"- sheet: {sb / 'sheet.png'}", ""]
    lines += ["Fill in RUN/vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["style"] for b in bs], swap=True))
    print(f"ballot -> {d / 'ballot.md'}; scores to fill -> {f}")
    return 0


def problems(data, panel, ids, swap=False):
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            unread = set(e.get("not_read") or [])
            for k in sorted(unread - UNREADABLE):
                bad.append(f"{c} / board {i} / not_read {k}: only {', '.join(sorted(UNREADABLE))} can go unread (the picture is always there to read)")
            for k in CRITERIA:
                v = (e.get("scores") or {}).get(k)
                if k in unread & UNREADABLE:
                    if v is not None:
                        bad.append(f"{c} / board {i} / {k}: is in not_read, so its score stays empty (got {v!r})")
                elif not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / board {i} / {k}: needs a whole number 1-5, or {k} in not_read when nobody in the session can read it"
                               if k in UNREADABLE else f"{c} / board {i} / {k}: needs a whole number 1-5 (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / board {i}: the paragraph needs at least 25 words")
            if swap and c == "motion_designer":
                for f in FRAMES:
                    v = (e.get("swap") or {}).get(f)
                    if v not in ("holds", "swappable"):
                        bad.append(f"{c} / board {i} / swap {f}: \"holds\" or \"swappable\" (got {v!r})")
    return bad


def cmd_tally(a):
    bs = boards()
    # only a tally that reaches a winner leaves one
    _env.b("winner.json").unlink(missing_ok=True)
    ids = [b["style"] for b in bs]
    data = _env.read_json(_env.b("vote", "scores.json"))
    if not data:
        sys.exit("RUN/vote/scores.json is missing: run vote.py ballot and fill it in")
    bad = problems(data, PANEL, ids, swap=True)
    if bad:
        print("the ballot is not complete:")
        for x in bad[:30]:
            print("  -", x)
        return 1
    swap = {i: {f: data["critics"]["motion_designer"]["boards"][i]["swap"][f] == "holds" for f in FRAMES} for i in ids}
    tot = {i: sum(v or 0 for c in PANEL for v in data["critics"][c]["boards"][i]["scores"].values()) for i in ids}
    eligible = sorted((i for i in ids if all(swap[i].values())), key=lambda i: -tot[i])
    titles = {b["style"]: b.get("title", b["style"]) for b in bs}
    lines = ["# the vote", ""]
    if eligible:
        win = eligible[0]
        lines.append(f"The film: storyboard {win}, {titles[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5}); its styleframes pass the swap test.")
    else:
        win = None
        lines.append("No storyboard goes on to the film: a styleframe's photograph could be swapped with nothing else changed.")
    lines += ["", "| critic | " + " | ".join(f"board {i}" for i in ids) + " |", "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(str(sum(v or 0 for v in data['critics'][c]['boards'][i]['scores'].values())) for i in ids) + " |")
    lines.append("| total | " + " | ".join(f"**{tot[i]}**" for i in ids) + " |")
    lines.append("| swap test | " + " | ".join(", ".join(f"{f} {'holds' if v else 'SWAPPABLE'}" for f, v in swap[i].items()) for i in ids) + " |")
    lines += ["", "## scores by criterion", "", "| board | critic | " + " | ".join(CRITERIA) + " |", "|---|---|" + "---|" * len(CRITERIA)]
    for i in ids:
        for c in PANEL:
            s = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {i} | {c} | " + " | ".join("not read" if s[k] is None else str(s[k]) for k in CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### board {i}: {titles[i]}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
    _env.write_text(_env.b("vote.md"), "\n".join(lines))
    if not win:
        print("the swap test failed on " + ", ".join(f"{i} {f}" for i in ids for f, v in swap[i].items() if not v)
              + ": the builder places each card from its own photograph and their line on it, so read the frame again against its photograph, "
              "and name the frame to the person in brief.md when it holds no better -> " + str(_env.b("vote.md")))
        return 1
    _env.write_json(_env.b("winner.json"), {"board": win, "title": titles[win], "recommended": win, "chosen": None,
                                            "totals": tot, "swap": swap})
    print(f"recommended: storyboard {win} ({titles[win]}), total {tot[win]} -> {_env.b('vote.md')}, {_env.b('winner.json')}. "
          "Next: show out/boards.png and ask which look, then vote.py pick <style>")
    return 0


# what a run makes for its one look after the boards: a different look starts these again from its own board (out/
# keeps boards.png, the three looks the person chose from)
MADE_FOR_THE_LOOK = ("cut", "draft", "frames", "qa", "music", "render", "clips", "public/clips", "film.json",
                     "music.json", "timeline.json", "clips.json", "critic", "caption.md", "brief.md")


def cmd_pick(a):
    bs = {b["style"]: b for b in boards()}
    if a.style not in bs:
        sys.exit(f"no board in the look {a.style!r}: the run's looks are {', '.join(bs)}")
    w = _env.read_json(_env.b("winner.json")) or {}
    was = (_env.read_json(_env.b("film.json")) or {}).get("board")
    gone = []
    if was and was != a.style:
        import shutil
        # a deliver the gate refused carried boards.png into cut/ and left no out/; it goes back where the boards are shown
        if _env.cut("boards.png").exists() and not _env.out("boards.png").exists():
            _env.out().mkdir(parents=True, exist_ok=True)
            _env.cut("boards.png").replace(_env.out("boards.png"))
        for p in sorted(_env.out().glob("*")) if _env.out().is_dir() else []:
            if p.name != "boards.png":
                shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
                gone.append(f"out/{p.name}")
        for name in MADE_FOR_THE_LOOK:
            p = _env.b(*name.split("/"))
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p)
                gone.append(name)
            elif p.exists() or p.is_symlink():
                p.unlink()
                gone.append(name)
    _env.write_json(_env.b("winner.json"), {**w, "board": a.style, "title": bs[a.style].get("title", a.style),
                                            "recommended": w.get("recommended"), "chosen": a.why or "you"})
    said = f"the look: {a.style} ({bs[a.style].get('title', a.style)})" + (f", because {a.why}" if a.why else ", chosen by the person")
    if gone:
        said += f"; cleared what was made for {was}: {', '.join(gone)}"
    print(f"{said} -> {_env.b('winner.json')}. Next: music.py, storyboard.py snap, film.py draft, vote.py timing, "
          "music.py master, film.py render, qa.py check, vote.py cut and verdict, deliver.py")
    return 0


def cmd_timing(a):
    import film
    import qa
    import storyboard
    f = _env.b("critic", "timing.json")
    m = _env.read_json(_env.b("draft", "check.json"))
    if not m:
        sys.exit("RUN/draft/check.json is missing: run film.py draft first")
    sha = film.board_sha(storyboard.lay_out(m["board"]))
    data = _env.read_json(f)
    if not data or data.get("board_sha") != sha:
        data = {"board": m["board"], "board_sha": sha, "figures": m, "pass": False,
                "read": {**{k: "" for k in READS}, "not_read": [], "repeats": [], "verdict": None}}
        _env.write_json(f, data)
        print(f"timing round for {m['board']}: open {_env.b('frames')}/strip-<beat>.png and film-strip.png full size, watch "
              f"{_env.b('draft', 'film.mp4')} with its sound, and read the figures ({qa.summary(m)}). Then fill in 'read' in {f}, "
              f"a sentence or more on each of the four reads, each from the frames it saw:")
        for k, v in READS.items():
            print(f"  {k}: {v}")
        print("  not_read: the reads nobody in this session can make (sound, when nobody can hear the draft), each recorded as not read; "
              "repeats: the beats that read the same as the one before; verdict: pass or fix. Then run vote.py timing again.")
        return 0
    r = data.get("read") or {}
    unread = set(r.get("not_read") or [])
    wrong = sorted(unread - UNHEARD)
    bad = [k for k in READS if k not in unread and len((r.get(k) or "").split()) < 12]
    if wrong or bad or r.get("verdict") not in ("pass", "fix"):
        print(f"{f} is not filled in: " + ", ".join([f"{k} can not go unread (only {', '.join(sorted(UNHEARD))})" for k in wrong]
                                                   + [f"{k} needs a sentence or more, or {k} in not_read when nobody can make it" if k in UNHEARD else f"{k} needs a sentence or more" for k in bad]
                                                   + ([] if r.get("verdict") in ("pass", "fix") else ["verdict is pass or fix"])))
        return 1
    hook = [] if qa.hook_ok(m) else ["no event in the first 30 frames"]
    data["pass"] = r["verdict"] == "pass" and not r.get("repeats") and not hook
    data["unread"] = sorted(unread)
    for k in unread:
        r[k] = "not read in this session"
    data["figures"] = m
    _env.write_json(f, data)
    if data["pass"]:
        print(f"timing passes for {m['board']}: {qa.summary(m)}" + "".join(f"; {k} was not read in this session" for k in sorted(unread))
              + "; next: film.py render")
        return 0
    why = hook + ([f"beats that repeat: {', '.join(r['repeats'])}"] if r.get("repeats") else []) + (["the read says fix"] if r["verdict"] == "fix" else [])
    print(f"timing does not pass for {m['board']}: {'; '.join(why)}. The builder decides the beats from the posts: fix the cause in the "
          "builder (scripts/tones/drive.py) or the research it read, then storyboard.py draft, snap, music.py master, film.py draft and vote.py timing again")
    return 2


def rounds():
    """The cut rounds of the board RUN/film.json names, oldest first."""
    board = (_env.read_json(_env.b("film.json")) or {}).get("board")
    return sorted(_env.b("critic").glob(f"cut-{board}-*.json"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def cmd_cut(a):
    # the render's report (RUN/render/report.json) is the completion of cut/: without it cut/film.mp4 may be a
    # render stopped partway
    rep = _env.read_json(_env.b("render", "report.json")) or {}
    if not rep or rep.get("failed"):
        sys.exit("the render has not finished (RUN/render/report.json is missing or names failed jobs): run film.py render first")
    d = _env.b("critic")
    d.mkdir(parents=True, exist_ok=True)
    board = (_env.read_json(_env.b("film.json")) or {}).get("board")
    film = _env.cut("film.mp4")
    if not film.exists():
        sys.exit("cut/film.mp4 is missing: run film.py render first")
    sha = digest(film)
    # the critic reads this cut's strip and checks, so the round waits for the check of this cut
    if (_env.read_json(_env.b("qa", "check.json")) or {}).get("film") != sha:
        sys.exit("RUN/qa/check.json is not the check of this cut: run qa.py check, then vote.py cut")
    rs = rounds()
    look = f"{film}, RUN/qa/strip.png, RUN/cut/then-now.png, the story cards in RUN/cut/stories/ and RUN/clips/requests.json"
    # a round scores one reel, so the newest round stands while the reel is the one it scores
    if rs and (_env.read_json(rs[-1]) or {}).get("film") == sha:
        print(f"round {len(rs)} is for this cut already: fill in {rs[-1]} after watching {look}")
        return 0
    n = len(rs) + 1
    f = d / f"cut-{board}-{n}.json"
    data = blank(CUT_PANEL, ["film"])
    data["round"] = n
    data["film"] = sha
    data["fixed"] = "" if n > 1 else None
    _env.write_json(f, data)
    print(f"round {n}: fill in {f} after watching {look}" + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
    return 0


def standing(data):
    """A round against the bar: each rule's score (the lower of its critics' scores), the rules nobody read, and the mean
    of the rules read."""
    by, unread = {}, []
    for k in CRITERIA:
        got = [e["boards"]["film"]["scores"].get(k) for e in (data.get("critics") or {}).values()]
        got = [v for v in got if isinstance(v, int)]
        if got:
            by[k] = min(got)
        else:
            unread.append(k)
    mean = round(sum(by.values()) / len(by), 2) if by else 0
    return by, unread, mean


def short(by, mean):
    """The rules that keep a round under the bar, lowest first: every rule under 4, or with none under 4 and the mean
    under 4.5, every rule under 4.5."""
    low = [k for k in by if by[k] < FLOOR] or ([k for k in by if by[k] < BAR] if mean < BAR else [])
    return sorted(low, key=lambda k: (by[k], list(CRITERIA).index(k)))


def outcome(rs):
    """The latest round's verdict: ("SHIP" | "FIX ONCE" | "DELIVER WITH SCORES", the rule the fix is for or None, why)."""
    data = _env.read_json(rs[-1])
    by, unread, mean = standing(data)
    low = short(by, mean)
    if not low:
        return "SHIP", None, f"a mean of {mean} and no rule under {FLOOR}"
    # the clips are made before the render; a render that played none of them was made by a session with no video
    # model, so making them is no lever inside this run
    made = any(c.get("status") == "generated" for c in ((_env.read_json(_env.b("clips.json")) or {}).get("clips") or {}).values())
    reach = [k for k in low if LEVERS[k] and (k != "shots" or made)]
    if len(rs) >= 2:
        return "DELIVER WITH SCORES", None, "the one fix is spent"
    if not reach:
        return "DELIVER WITH SCORES", None, "no lever inside a run reaches " + ", ".join(low)
    return "FIX ONCE", reach[0], LEVERS[reach[0]]


def scores_line(data):
    by, unread, mean = standing(data)
    return ", ".join(f"{CRITERIA[k].split(' ')[0]} {k} {by[k]}" if k in by else f"{CRITERIA[k].split(' ')[0]} {k} not read" for k in CRITERIA) \
        + f"; mean {mean} against the bar of {BAR} with no rule under {FLOOR}"


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    film = _env.cut("film.mp4")
    if not film.exists() or data.get("film") != digest(film):
        sys.exit(f"{rs[-1]} is not for the current cut/film.mp4: run qa.py check and vote.py cut, and score the cut you see")
    bad = problems(data, CUT_PANEL, ["film"])
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    print(f"round {data.get('round')}: {scores_line(data)}")
    _, unread, _ = standing(data)
    for k in unread:
        print(f"  {k} was not read in this session; the brief says so")
    what, rule, why = outcome(rs)
    if what == "SHIP":
        print(f"SHIP: {why}. Next: deliver.py")
        return 0
    if what == "DELIVER WITH SCORES":
        print(f"DELIVER WITH SCORES: {why}. Deliver this cut as the run's best; brief.md states every score. Next: deliver.py")
        return 0
    by, _, _ = standing(data)
    print(f"FIX ONCE: {rule} ({CRITERIA[rule]}) is at {by[rule]}. The lever: {why}. Take it, follow it through to film.py render, "
          "qa.py check, then vote.py cut for round 2, saying in 'fixed' what changed")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timing", "cut", "verdict"])
    ap.add_argument("style", nargs="?", help="pick: the look the person chose (a board's style)")
    ap.add_argument("--why", help="pick: the one-line reason, when taste.json picks the look instead of the person")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.style:
        ap.error("pick names the look: vote.py pick <style>")
    # pick works in the run that holds the boards, even once a film of another look is rendered there
    if a.cmd in ("ballot", "tally", "timing"):
        _env.open_run()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timing": cmd_timing, "cut": cmd_cut,
            "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
