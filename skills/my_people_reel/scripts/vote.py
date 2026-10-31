#!/usr/bin/env python3
"""Movement 3 (the panel scores the three looks, then a look is picked) and movement 5 (two critics score the timed cut
before the film renders).

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/vote.py ballot     # R/vote/ballot.md + R/vote/scores.json to fill in, one entry per look
    python3 S/scripts/vote.py tally      # R/vote.md: each look's scores and the panel's order
    python3 S/scripts/vote.py pick LOOK [--why "..."]
                                         # R/winner.json: the look to make (A, B or C, first, second or third, or a
                                         # style id); --why is the one-line reason when the agent picks by taste
    python3 S/scripts/vote.py cut        # R/critic/cut-N.json to fill in for the timed cut (round N + 1 only when
                                         # the cut changed since round N)
    python3 S/scripts/vote.py verdict    # the latest round against the bar, and what to do next

The three looks are the boards storyboard.py drafted (storyboards/looks.json, A first). The panel (S/critic/critic.md
has each critic's brief): a motion designer (craft), an editor (story and rhythm) and the person, modeled from
R/taste.md (is this unmistakably me; would I post it). Each scores every look 1-5 on the six scored rules of
S/motion/system/standards.md (R1 to R6), each read against that look's own style card, from its sheets and its
storyboard.md, and writes one paragraph. tally orders the looks by total (the person's critic breaks a tie). The pick
is the person's when the agent may ask them (they are shown out/boards.png), else the agent's by taste with its reason
(taste.json `ask: false`); a look picked later ("make the second one") is picked the same way and the film is made
again from music in the same run folder.

The timed cut is scored before the film renders by the motion designer and the person on the same rules, each from its
own evidence: the 12 fps strip, the beats at rest, the cue tiles (the frames around each sound cue over the
waveform), R/qa/check.json and R/clips/requests.json. A rule's score is the lower of the two critics'; the bar is a
mean of BAR_MEAN with no rule under BAR_LEAST. The verdict never blocks the render: at the bar it says render; under it
in round 1 it names the rule furthest under the bar to fix once, when a lever reaches it; under it after that, the cut
renders as the best one, and its scores go in R/brief.md, never on the person's page. `scored` is what film.py render
and qa.py gate ask: the latest round is for this cut and complete, with its standing against the bar.
"""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import storyboard  # noqa: E402
import style  # noqa: E402

CRITERIA = {
    "R1": "one idea, carried by the look's moves: the tag finds each person, each beat moves and cuts the way its style card does, and it pays off on the wall",
    "R2": "the picture in the look's finish: its grain, light, grade and the way a print is mounted, one finish from hook to closer",
    "R3": "type that reads, in the look's two faces: set like a designer set it, words that land and are level and clear at rest",
    "R4": "motion and rhythm: every move gathers before it goes and settles where it lands, no two beats in a row move alike, the peak held longest, a closer that lands",
    "R5": "sound to picture: each cue's onset on the frame where its thing lands (the cue tiles), effects 8 LU under the music",
    "R6": "generated shots: each request in clips/requests.json a shot a cinematographer would write (subject, move, lens, light, length, loop)",
}
BAR_MEAN, BAR_LEAST = 4.5, 4
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}


def boards():
    looks = storyboard.looks()
    out = [dict(_env.read_json(Path("storyboards") / t / "storyboard.json"), id=t) for t in looks
           if (Path("storyboards") / t / "sheet.png").exists()]
    if len(out) < len(looks):
        sys.exit(f"{len(out)} of {len(looks)} looks with sheets: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids):
    return {"critics": {c: {"boards": {i: {"scores": {k: None for k in CRITERIA}, "paragraph": ""} for i in ids}} for c in panel}}


def cmd_ballot(a):
    bs = boards()
    d = Path("vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score each look 1-5 on each criterion, as each critic, against that look's own style card, and "
             "write one paragraph (what works, what fails, what you would change). Look at its sheets and read its "
             "storyboard.md before scoring.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for letter, b in zip("ABC", bs):
        sb = Path("storyboards") / b["id"]
        lines += [f"### {letter}. {style.card(b['id'])['name']} ({b['id']})", "", style.sentence(b["id"]), "",
                  f"- style card: {_env.SKILL / 'styles' / (b['id'] + '.json')}",
                  f"- storyboard: {sb / 'storyboard.md'}",
                  f"- sheets: {sb / 'sheet.png'} (9:16), {sb / 'sheet-square.png'}, {sb / 'sheet-wide.png'}: the hook, the densest beat "
                  f"and the closer at rest (frames in {sb / 'frames'}/)", ""]
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
            if not isinstance(e, dict) or not isinstance(e.get("scores") or {}, dict):
                bad.append(f"{c} / board {i}: needs an object with scores and a paragraph (got {type(e).__name__})")
                continue
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
    tot = {i: sum(sum(data["critics"][c]["boards"][i]["scores"].values()) for c in PANEL) for i in ids}
    person = {i: sum(data["critics"]["person"]["boards"][i]["scores"].values()) for i in ids}
    order = sorted(ids, key=lambda i: (-tot[i], -person[i], ids.index(i)))
    letter = dict(zip(ids, "ABC"))
    tie = [i for i in ids if tot[i] == tot[order[0]]]
    lines = ["# the vote", "", f"The panel's order: " + ", ".join(f"{letter[i]} {i} ({tot[i]} of {len(PANEL) * len(CRITERIA) * 5})" for i in order) + "."
             + (f" {', '.join(tie)} tie on total; the person's critic orders them." if len(tie) > 1 else ""),
             "", "The look is picked next: `vote.py pick LOOK` (the person's choice from out/boards.png, or the agent's by taste "
             "with --why).", "",
             "| critic | " + " | ".join(f"{letter[i]} {i}" for i in ids) + " |", "|---|" + "---|" * len(ids)]
    for c in PANEL:
        lines.append(f"| {PANEL[c]} | " + " | ".join(str(sum(data['critics'][c]['boards'][i]['scores'].values())) for i in ids) + " |")
    lines.append("| total | " + " | ".join(f"**{tot[i]}**" for i in ids) + " |")
    lines += ["", "## scores by criterion", "", "| look | critic | " + " | ".join(CRITERIA) + " |", "|---|---|" + "---|" * len(CRITERIA)]
    for i in ids:
        for c in PANEL:
            s = data["critics"][c]["boards"][i]["scores"]
            lines.append(f"| {letter[i]} {i} | {c} | " + " | ".join(str(s[k]) for k in CRITERIA) + " |")
    lines += ["", "## what the critics said", ""]
    for i in ids:
        lines += [f"### {letter[i]}. {style.card(i)['name']}", ""]
        for c in PANEL:
            lines += [f"**{PANEL[c]}.** {data['critics'][c]['boards'][i]['paragraph'].strip()}", ""]
    _env.write_text("vote.md", "\n".join(lines))
    _env.write_json("vote/order.json", {"order": order, "totals": tot})
    print(f"the panel's order: {', '.join(f'{letter[i]} {i} {tot[i]}' for i in order)} -> vote.md; pick next: vote.py pick LOOK")
    return 0


ORDINALS = {"first": 0, "1": 0, "a": 0, "second": 1, "2": 1, "b": 1, "third": 2, "3": 2, "c": 2}


def look_of(said, looks):
    """The look a person's words name: A, B or C, first, second or third, the look's name, or its style id."""
    w = said.strip().lower()
    if w in ORDINALS and ORDINALS[w] < len(looks):
        return looks[ORDINALS[w]]
    for t in looks:
        if w in (t, style.card(t)["name"].lower()):
            return t
    return None


def cmd_pick(a):
    looks = list(storyboard.looks())
    t = look_of(a.look, looks)
    if not t:
        sys.exit(f"{a.look!r} names none of the three looks: " + ", ".join(f"{l} {x}" for l, x in zip("ABC", looks)))
    taste = _env.read_json("taste.json") or {}
    if taste.get("ask") is False and not a.why:
        sys.exit("taste.json says the person is not asked: pass --why, one line on why this look fits their taste")
    sb = _env.read_json(storyboard.sb_path(t)) or {}
    before = (_env.read_json("winner.json") or {}).get("board")
    _env.write_json("winner.json", {"board": t, "name": sb.get("name"), "look": style.card(t)["name"],
                                    "by": "taste" if a.why else "the person", "why": a.why or ""})
    if before and before != t:
        # a film made in another look goes with it: the music, the cut and the critics' rounds were made for that look
        for old in (Path("film.json"), Path("music.json")):
            old.unlink(missing_ok=True)
        for old in Path("critic").glob("cut-*.json"):
            old.unlink()
        print(f"the look was {before}; the music, the cut and its rounds are made again for {t}")
    print(f"picked {'ABC'[looks.index(t)]}. {style.card(t)['name']} ({t})" + (f": {a.why}" if a.why else "")
          + "; next: music.py find, storyboard.py snap, the preview and check, music.py master, film.py render, deliver.py")
    return 0


def rounds():
    return sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def standing(data):
    """({rule: score}, mean, least) of one complete cut round: each rule's score is the lower of the two critics'."""
    s = {k: min(data["critics"][c]["boards"]["film"]["scores"][k] for c in CUT_PANEL) for k in CRITERIA}
    return s, round(sum(s.values()) / len(s), 2), min(s.values())


def at_bar(mean, least):
    return mean >= BAR_MEAN and least >= BAR_LEAST


def told(s, mean, least):
    """The scores against the bar, in words."""
    under = [f"{k} {v}" for k, v in s.items() if v < BAR_LEAST]
    return (f"mean {mean} (bar {BAR_MEAN}), least {least} (bar {BAR_LEAST}): " + ("at the bar" if at_bar(mean, least) else "under the bar")
            + (f", under {BAR_LEAST} on {', '.join(under)}" if under else ""))


def scored(film_sha):
    """(ok, why): the latest round is for this cut and filled in; `why` states its scores against the bar. A cut under
    the bar is still scored: the scores are stated, never a reason to stop the render."""
    rs = rounds()
    if not rs:
        return False, "no cut round in critic/: run vote.py cut and fill it in"
    data = _env.read_json(rs[-1])
    if data.get("film") != film_sha:
        return False, f"round {data.get('round')} is not for the current cut: run vote.py cut and score it"
    if problems(data, CUT_PANEL, ["film"]):
        return False, f"{rs[-1]} is not complete: run vote.py verdict"
    return True, f"round {data.get('round')}, " + told(*standing(data))


def cmd_cut(a):
    film = Path("render/cut.mp4")
    cut = _env.read_json("render/cut.json") or {}
    if not film.exists() or not cut:
        sys.exit("render/cut.mp4 is missing or unfinished: run film.py cut first")
    sha = hashlib.sha256(film.read_bytes()).hexdigest()[:16]
    if sha != cut.get("film"):
        sys.exit("render/cut.mp4 is not the cut render/cut.json measured: run film.py cut again")
    rs = rounds()
    last = (_env.read_json(rs[-1]) or {}) if rs else None
    # a round belongs to one cut: the same cut keeps its round, a changed cut opens the next one, and a round left
    # unscored is taken over by the cut that replaced it, so no round is ever counted without its scores
    if last is not None and last.get("film") == sha:
        f, n = rs[-1], int(rs[-1].stem.split("-")[1])
    else:
        n = len(rs) + 1 if last is None or not problems(last, CUT_PANEL, ["film"]) else len(rs)
        f = Path("critic") / f"cut-{n}.json"
        data = blank(CUT_PANEL, ["film"])
        data["round"] = n
        data["film"] = sha
        data["fixed"] = "" if n > 1 else None
        _env.write_json(f, data)
    print(f"round {n}: fill in {f} with R1 to R6, each read from its evidence (critic.md, the cut): frames/film-strip.jpg "
          "(12 fps), the beats at rest in frames/, the cue tiles in frames/cues/ with frames/cues.json, qa/check.json and "
          "clips/requests.json" + (" (say in 'fixed' what changed since the last round)" if n > 1 else ""))
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
    s, mean, least = standing(data)
    if at_bar(mean, least):
        print(f"AT THE BAR: round {data.get('round')}, {told(s, mean, least)}. Render: film.py render")
        return 0
    if len(rs) >= 2:
        print(f"UNDER THE BAR after the fix: round {data.get('round')}, {told(s, mean, least)}. Render this cut as the best "
              "one (film.py render); its scores go in brief.md, never on the person's page")
        return 0
    worst = min(s, key=lambda k: (s[k], k))
    print(f"FIX ONCE: round 1, {told(s, mean, least)}. Furthest under is {worst} ({CRITERIA[worst]}) at {s[worst]}. When a "
          "lever in critic.md reaches it, fix it, cut again (storyboard.py check and snap, music.py master, film.py cut, "
          "qa.py check, clips.py list) and score round 2 (vote.py cut); when none does, the budget is spent: render this "
          "cut (film.py render)")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "cut", "verdict"])
    ap.add_argument("look", nargs="?", help="pick: A, B or C, first, second or third, the look's name, or its style id")
    ap.add_argument("--why", help="pick: the one-line reason, when the agent picks by the person's taste")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.look:
        ap.error("pick needs the look: A, B or C")
    _env.enter_run()
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
