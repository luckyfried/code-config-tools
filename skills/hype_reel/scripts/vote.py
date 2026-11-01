#!/usr/bin/env python3
"""Movement 3 (the panel scores the three storyboards, or the person picks one) and movement 4 (two critics watch the
timed cut before the film renders, and the film ships at the bar).

USAGE (in a run; S = this skill's folder):
    python3 S/scripts/vote.py ballot         # vote/ballot.md + vote/scores.json to fill in, for the three boards
    python3 S/scripts/vote.py tally          # vote.md + winner.json (the highest total among the boards that pass the
                                             # swap test, carrying the board as judged)
    python3 S/scripts/vote.py pick --board N [--why "..."]
                                             # the person's choice is the vote (or, with --why, the agent's pick by
                                             # their taste and its one-line reason): winner.json carries board N; in a run
                                             # that already has a cut or a film, every piece made from the last board
                                             # (music, film.json, the cut, the critics' rounds, the film) goes first
    python3 S/scripts/vote.py cut            # critic/cut-N.json to fill in for the newest timed cut (the half-size
                                             # proof.silent.mp4 while it is there, else film.silent.mp4): the newest
                                             # round when it is for this cut, else round N+1
    python3 S/scripts/vote.py verdict        # SHIP at the bar, else the worst thing

The panel (S/critic/critic.md has each critic's brief): a motion designer (craft, pacing, type, motion), an editor
(story, emotion, the ending) and the person, modeled from taste.md (is this unmistakably me; would I post it). Each
critic scores every board 1-5 on the seven criteria below, writes one paragraph per board and applies the swap test
(`swap`: would this board still read the same with another maker's photographs and another subject's name? pass only
when it would not); a board any critic fails on the swap test cannot win. The timed cut is scored by the motion
designer and the person on the same criteria, with the reads in READS, each a pass and a why.

The bar: the cut ships when the mean of every score of the latest round is at least BAR and no score is under FLOOR.
Under the bar, the one fix is the worst thing; a second round still under the bar ships, and deliver.py writes its
scores in the run's brief.md and nowhere the person reads. film.py render waits for a round on the current film.json
that passes every read and either meets the bar or has spent the one fix.

A round's `music` score and its `sound` read rest on the sound read `cut` writes (critic/sound.md: the cuts against
the beat grid, the music's end against the last frame, each effect's peak against the music under it, as film.py
render will lay them), naming in the round's `sound.cited` the rows they rest on. A round records the film.json it
scored (`film`) and its picture (`cut`: that hash with the motion bundle that drew the cut, proof.picture), so a cut
drawn by another bundle opens its own round, and a verdict on a round of another cut than the newest is refused.

Every round before the last scores the half-size proof (film.py cut --proof, proof.silent.mp4): `cut` reads the newest
cut and its first line says when that is the proof. Once the full-size cut of the same film.json is made, `cut` moves
the latest round to it and empties its `type` scores: the critics read the type again on the full-size cut, at the
size a phone shows it, and film.py render waits until they have scored it there.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import proof  # noqa: E402

CRITERIA = {
    "professional": "it looks like a professional motion designer made it",
    "them": "it is unmistakably them and unmistakably the subject (their voice and hook, the subject's own assets, the two palettes meeting)",
    "pacing": "the pacing holds attention to the end",
    "type": "type is a system, not a default",
    "motion": "every move and every cut is intentional",
    "music": "the music and the cuts agree",
    "ending": "the reveal lands and the date sticks",
}
# what the critics read the timed cut for, each a pass and a why: the frame first, then the four reads and monotony
READS = {
    "frame": "the picture owns the frame at every beat and the words are set into it the way the style sets them; no empty "
             "field waits behind the words",
    "carry": "every cut is one the style makes, landing on a beat of the music",
    "sound": "a sound only where a beat lands, under the music",
    "swap": "every move belongs to its photograph: under another photograph the move would stop making sense",
    "held": "one held thing per beat, and the beat moves on once its words have landed",
    "monotony": "the cut keeps changing how it moves, beat to beat; no one move repeats",
}
BAR, FLOOR = 4.5, 4  # the bar a cut ships at: the mean of every score of the round, and the lowest score
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def boards():
    out = []
    for f in sorted(Path("storyboards").glob("*/storyboard.json")):
        out.append(_env.read_json(f))
    if not out:
        sys.exit("no storyboards: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids, swap=True):
    entry = lambda: {"scores": {k: None for k in CRITERIA}, "paragraph": "", **({"swap": {"pass": None, "why": ""}} if swap else {})}
    return {"critics": {c: {"boards": {i: entry() for i in ids}} for c in panel}}


def read(field):
    """A filled-in pass/why read (`swap`, one of READS), or the reason it is not filled in."""
    if not isinstance((field or {}).get("pass"), bool):
        return "needs pass true or false"
    if len(((field or {}).get("why") or "").split()) < 8:
        return "needs a why of at least 8 words"
    return None


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score each storyboard 1-5 on each criterion, as each critic, and write one paragraph per board "
             "(what works, what fails, what you would change), and apply the swap test to each: put another maker's photographs "
             "and another subject's name in the board; if it would read the same, it fails (`swap`: pass false, and why). "
             "Judge each board against its own style: look at each sheet before scoring.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path(f"storyboards/{b['id']}")
        lines += [f"### {b['id']}: {b['name']}", "", b.get("idea", ""), "",
                  f"- style {b.get('style')}, {b.get('bpm')} bpm; the hook: \"{(b.get('hook') or {}).get('line')}\"",
                  f"- storyboard: {sb / 'storyboard.md'}", f"- style sheet: {sb / 'sheet.png'} (frames in {sb / 'frames'}/)", ""]
    lines += ["Fill in vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["id"] for b in bs]))
    print(f"ballot -> {d / 'ballot.md'}; scores to fill -> {f}")
    return 0


def problems(data, panel, ids, swap=True):
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
            why = read(e.get("swap")) if swap else None
            if why:
                bad.append(f"{c} / board {i} / swap: {why}")
    if not swap:
        for k in READS:
            why = read((data.get("reads") or {}).get(k))
            if why:
                bad.append(f"reads / {k}: {why}")
    return bad


def swapped(data, i):
    """The critics who fail board i on the swap test."""
    return [c for c in PANEL if not data["critics"][c]["boards"][i]["swap"]["pass"]]


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
    tot = {i: sum(sum(data["critics"][c]["boards"][i]["scores"].values()) for c in PANEL) for i in ids}
    person = {i: sum(data["critics"]["person"]["boards"][i]["scores"].values()) for i in ids}
    out = {i: swapped(data, i) for i in ids}
    if all(out.values()):
        print("the swap test fails: " + "; ".join(f"board {i} ({', '.join(out[i])})" for i in ids)
              + ". Change the board (storyboard.json) until it is unmistakably theirs, then ballot again")
        return 1
    order = sorted(ids, key=lambda i: (bool(out[i]), -tot[i], -person[i], i))
    win = order[0]
    tie = [i for i in ids if tot[i] == tot[win] and not out[i]]
    names = {b["id"]: b["name"] for b in bs}
    lines = ["# the vote", "", f"Winner: storyboard {win}, {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5})."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""), "",
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
            e = data["critics"][c]["boards"][i]
            lines += [f"**{PANEL[c]}.** {e['paragraph'].strip()} Swap test: {'pass' if e['swap']['pass'] else 'FAIL'}, {e['swap']['why'].strip()}", ""]
    _env.write_text("vote.md", "\n".join(lines))
    # the winner carries the board as the panel judged it: snap cuts this copy, never a storyboard.json edited since
    _env.write_json("winner.json", {"board": win, "name": names[win], "totals": tot, "order": order, "tie_broken_by_person": len(tie) > 1,
                                    "swap": {i: not out[i] for i in ids}, "storyboard": next(b for b in bs if b["id"] == win)})
    print(f"winner: storyboard {win} ({names[win]}), totals {tot} -> vote.md, winner.json")
    return 0


def cmd_pick(a):
    import storyboard
    bs = {b["id"]: b for b in boards()}
    n = str(a.board or "")
    if n not in bs:
        sys.exit(f"no board {n or '(none named)'}: the boards are {', '.join(bs)}; pick one with --board")
    gone = [p for p in dict.fromkeys(storyboard.FILMED + ["critic", "cut.json", "engine.json"]) if p != "out" and Path(p).exists()]
    for p in gone:
        shutil.rmtree(p) if Path(p).is_dir() else Path(p).unlink()
    out = Path("out")
    for f in out.glob("*") if out.is_dir() else []:
        if f.name != "boards.png":
            shutil.rmtree(f) if f.is_dir() else f.unlink()
    first = _env.read_json("winner.json") or {}
    b = bs[n]
    by = "the agent, by their taste" if a.why else "the person"
    _env.write_json("winner.json", {"board": n, "name": b["name"], "picked_by": by, "why": a.why or "", "totals": first.get("totals") or {},
                                    "order": [n] + [i for i in bs if i != n], "swap": {**(first.get("swap") or {}), n: True},
                                    "tie_broken_by_person": False, "storyboard": b})
    print(f"board {n} ({b['name']}, {b['style']}) picked by {by}" + (f": {a.why}" if a.why else "") + (f"; the last board's {', '.join(gone)} removed" if gone else "")
          + ". Next: music.py make, storyboard.py snap, music.py master, clips.py normalize, film.py cut, vote.py cut")
    return 0


def at_bar(data):
    """Whether a filled-in cut round meets the bar, with its mean and its lowest score and where that lowest is."""
    s = [(data["critics"][c]["boards"]["film"]["scores"][k], k, c) for c in CUT_PANEL for k in CRITERIA]
    mean = sum(x[0] for x in s) / len(s)
    return mean >= BAR and min(s)[0] >= FLOOR, round(mean, 2), min(s)


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def cmd_cut(a):
    import film
    cut = _env.read_json("cut.json") or {}
    scale = proof.scale(film.SILENT)
    picture = proof.newest(film.SILENT)
    if scale != 1:
        print(proof.reading(picture))
    if not picture.exists() or cut.get("film") != film.film_hash():
        sys.exit("there is no cut of the current film.json: run film.py cut --proof first")
    drawn = proof.picture(cut["film"], picture)
    rs = rounds()
    last = _env.read_json(rs[-1]) if rs else None
    # a round is for one cut: asking again for the same cut (the same film.json drawn by the same motion bundle) reopens
    # that round and never spends the one fix
    if last and last.get("film") == cut["film"] and last.get("cut") == drawn:
        if "sound" not in last:
            last["sound"] = sound_read()
            _env.write_json(rs[-1], last)
        if scale == 1 and last.get("scale") == proof.SCALE:
            # the full-size cut of the film.json the round scored on its proof: the same round, with the type read at
            # full size
            last["scale"] = 1
            for c in CUT_PANEL:
                last["critics"][c]["boards"]["film"]["scores"]["type"] = None
            _env.write_json(rs[-1], last)
            print(f"round {last.get('round')} moves to the full-size {picture}: as each critic, read the type again on it "
                  f"and on the strips in frames/, at the size a phone shows it, and score type in {rs[-1]}; the other "
                  "scores and the reads stand")
            return 0
        print(f"round {last.get('round')} is for this cut: fill in {rs[-1]} after watching {picture} and the strips in frames/{SAID}")
        return 0
    d = Path("critic")
    d.mkdir(parents=True, exist_ok=True)
    n = len(rs) + 1
    f = d / f"cut-{n}.json"
    data = blank(CUT_PANEL, ["film"], swap=False)
    data["round"] = n
    data["film"] = cut["film"]
    data["cut"] = drawn
    data["scale"] = scale
    data["reads"] = {k: {"pass": None, "why": "", "asks": v} for k, v in READS.items()}
    data["fixed"] = "" if n > 1 else None
    data["sound"] = sound_read()
    _env.write_json(f, data)
    print(f"round {n}: fill in {f} after watching {picture} and the strips in frames/ (scores, a paragraph, and each "
          "read's pass and why)" + (" and say in 'fixed' what changed since the last round" if n > 1 else "")
          + f"{SAID}; the read has {len(data['sound']['findings'])} findings")
    return 0


SOUND = Path("critic/sound.md")
SAID = (f"; score music and read sound from the sound read, {SOUND}, and say in sound.cited which of its rows they "
        "rest on")


def sound_read():
    """The sound film.py render lays under this cut, read before it is laid (sfx.py read: the cuts against the beat
    grid, the music's end against the board's stop and the last frame, the effects' peaks against the bed, ducked as the
    mux ducks it), from the effects board and music record the mux lays (fx_board of film.json, music.json), written to
    critic/sound.md and critic/sound.json; the cut is silent, so the read hears the board and the master. Its block in a
    round: the table, its findings, and `cited`, the sentence the critics fill in naming the rows the music score and
    the sound read rest on."""
    import film
    import sfx
    f = film.load_film()
    return sfx.critic_read(film.fx_board(f), _env.read_json("music.json") or {}, None, f["seconds"], _env.ffmpeg(), SOUND)


def sound_problems(data):
    """What a round's sound block still needs: the read itself, and the sentence that cites its rows."""
    import sfx
    return sfx.uncited(data.get("sound"), SOUND)


def newest(data):
    """Why a verdict on round `data` cannot stand when it scored another cut than the newest (another film.json, or the
    same drawn by another motion bundle); None when it scored that cut."""
    import film
    picture = proof.newest(film.SILENT)
    if not picture.exists() or data.get("film") != film.film_hash() or data.get("cut") != proof.picture(data.get("film"), picture):
        return (f"round {data.get('round')} scored another cut than the newest, {picture}: run vote.py cut, which opens "
                "that cut's round, and fill it in")
    return None


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    stale = newest(data)
    if stale:
        print(f"{rs[-1]} is not a read of the newest cut: {stale}")
        return 1
    bad = problems(data, CUT_PANEL, ["film"], swap=False) + sound_problems(data)
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    failed = [k for k in READS if not data["reads"][k]["pass"]]
    if failed:
        print(f"FIX: the cut fails {', '.join(failed)} ({data['reads'][failed[0]]['why']}). Change the board, snap, cut "
              "the proof again (film.py cut --proof), then run vote.py cut again")
        return 2
    ok, mean, worst = at_bar(data)
    # a round on the proof ends in the full-size cut, where the critics read the type once more before the render
    full = (" Next: the full-size cut (film.py cut), then vote.py cut: the critics read the type again at full size "
            "before film.py render" if data.get("scale") == proof.SCALE else "")
    if ok:
        print(f"SHIP: round {data.get('round')} meets the bar, mean {mean} (at least {BAR}), every score {FLOOR} or more."
              + full)
        return 0
    if len(rs) >= 2:
        print(f"round {data.get('round')}: under the bar, mean {mean}, lowest {worst[1]} ({worst[2]}: {worst[0]}). The one fix "
              "is spent: render it, and deliver.py writes the scores in the run's brief.md." + full)
        return 2
    print(f"FIX ONCE: under the bar (mean {mean}); the worst thing is {worst[1]} ({CRITERIA[worst[1]]}), {worst[2]} gave {worst[0]}. Fix it, snap, "
          "cut the proof again (film.py cut --proof), then run vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "cut", "verdict"])
    ap.add_argument("--board", help="pick only: the board chosen (1, 2 or 3)")
    ap.add_argument("--why", help="pick only, where the agent may not ask: the one-line reason their taste picks this board")
    a = ap.parse_args()
    _env.enter_run()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
