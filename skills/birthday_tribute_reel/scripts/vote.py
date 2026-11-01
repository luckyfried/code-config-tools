#!/usr/bin/env python3
"""Movement 3 (the panel scores the storyboard), the critic's read of the timed cut, and movement 5 (two critics
score the finished cut).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/vote.py ballot     # B/vote/ballot.md + B/vote/scores.json to fill in (B = build/<run stamp>/)
    python3 S/scripts/vote.py tally      # B/vote.md + B/winner.json (the board, its scores and its swap test)
    python3 S/scripts/vote.py pick N --reason "..."   # the look the person chose (or the agent chose by taste):
                                         # B/winner.json names board N, and the cut made from another look goes
    python3 S/scripts/vote.py timed      # B/critic/timed.json to fill in: the four reads of the timed cut, with
                                         # 24 frames of the preview cut fresh for this cut
    python3 S/scripts/vote.py cut        # B/critic/cut-N.json to fill in for the newest reel, with 24 frames of it in
                                         # B/critic/cut-N/: out/proof.mp4 while the proof is the newest render, else
                                         # out/film.mp4 (a new round N for a new reel; the newest round again while it
                                         # scores this reel or nobody has scored it yet)
    python3 S/scripts/vote.py verdict    # SHIP when the latest round is at the bar, else the worst thing a critic found

The ballot holds the three storyboards, one per style. The panel (S/critic/critic.md has each critic's
brief): a motion designer (image, type, motion), an editor (concept, rhythm, sound) and the person, modeled from
B/taste.md (is this unmistakably us; would I send it to them). Each scores every storyboard 1-5 on the seven rules of
motion/system/standards.md (CRITERIA) and writes one paragraph. The bar is a mean of BAR with no score under FLOOR.
Each also applies the swap test to the board: "swap" lists the beats whose photograph could trade places with a
neighboring beat's and come out the same design ([] when none). A board with such a beat scores 3 or less on
"concept"; the named beats go into winner.json, and storyboard.py snap refuses until each is redesigned. tally names
the board with the highest total; the person's own choice of look (`pick`, which the agent makes by taste with a
one-line reason when taste.json says it may not ask) replaces it, and everything cut from another look goes with it:
the cut, the made music, the preview, the reads, the rounds, the clips and the render report, so the chosen look is
made again from its music onward and reuses nothing.
Before the film renders, the editor reads the timed cut from its frames (B/preview/film.mp4, its strip and the 24
frames timed cuts from it) with the four reads in READS: each a pass, a fail, or "not made" with the reason it could
not be made, and each read that is made names at least one of those frames. film.py render waits while a read
fails; a read not made leaves the gate open. The finished cut is scored by the motion designer and the person on the
same rules from the round's 24 frames, each critic's paragraph naming the frames it read, and each names the worst
thing in the film in "worst", which the verdict quotes.
Every round before deliver scores the half-size proof (film.py render --proof, out/proof.mp4): `cut` reads the newest
render and its first line says when that is the proof. Once the full-size reel of the same cut is rendered, `cut`
moves the latest round to it, cuts the round's frames again from the full-size reel under the same names, and empties
each critic's `type` score: the critics read the type again at full size, at the size a phone shows it, and the round
is complete once they have scored it there.

The `sound` score is read from the sound read `cut` writes (B/critic/sound.md: the cuts against the beat grid, the
music's end against the last frame, each effect's peak in the laid effects against the music under it), naming in the
round's `sound.cited` the rows the score rests on. A round records the reel it scored (its bytes' hash, which the
render report certifies) and its picture (`cut`: film.json's hash with the motion bundle that drew it, proof.picture),
so a reel drawn by another bundle opens its own round, and a verdict on a round that scored another reel than the
newest render is refused.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import proof  # noqa: E402

CRITERIA = {
    "concept": "R1 one idea, the wall of their year: stated in the first second, a motif on every beat that pays off in the closer, "
               "every move between beats the wall's own act or a cut the style card names, never a crossfade",
    "image": "R2 the photograph, its field and the wall move at different rates, every photograph whole and in register; a "
             "light wrap and a shadow on every card that flies; the style card's finish (grain, vignette, bloom, dust) over "
             "all; one grade on every photograph; the closer settles and keeps only its slow push",
    "type": "R3 the style card's two faces and a scale; names and figures enter by letter or word with tracking that resolves, "
            "settled within a second; the name over its words on every card; every line at rest inside the safe area, "
            "nothing colliding",
    "motion": "R4 one continuous camera with anticipation and settle on the style card's easing; each beat's move from the "
              "card's own moves, chosen for what the beat holds, never the same move twice in a row; a fast run before a "
              "held card; the peak holds longest; the closer's shape lands, then keeps only its slow push, silent",
    "sound": "R5 a cue only where a beat lands, the effects 8 LU under the music, the music made from the style's recipe and "
             "the brief's words, stopping on the wish",
    "clips": "R6 every clip request (clips/requests.json) a shot a cinematographer would write: subject, move, lens, light, the "
             "beat's length, loopable; for the hook's world, texture between chapters, or a still brought to life; a beat "
             "whose clip was not made is called a still, never a clip; a clip the person recorded plays on its card as one "
             "shot the length of its beat, its sound left out, and asks nothing of a model",
    "deliverable": "R7 out/ holds out/boards.png, the films asked for, the posted image, the story card, the caption and the "
                   "review page that opens on the film's cover and offers the other two looks, and nothing else",
}
BAR, FLOOR = 4.5, 4  # a round is at the bar when its scores average BAR or more and none is under FLOOR
FRAMES = 24  # the frames each read and each round is made from, at (i + 0.5) * seconds / FRAMES
PANEL = {"motion_designer": "the motion designer", "editor": "the editor", "person": "the person (from taste.md)"}
CUT_PANEL = {"motion_designer": "the motion designer", "person": "the person (from taste.md)"}
READS = {
    "carry": "one element is carried across every transition (the wall of their year, each moment's photograph going to its cell)",
    "sound": "a sound where each beat lands and nowhere else, under the music (the effects music.py master places, a whoosh "
             "peaking on each cut, against where the effects' sounds start, both in timed.json's measured)",
    "photograph": "the motion belongs to the photograph: put another photograph under the same move and it stops making sense",
    "held": "one held thing per beat, the moment's photograph and its line, and no beat holds still longer than its words need",
}


def boards():
    out = []
    for f in sorted(Path(f"{_env.B}/storyboards").glob("*/storyboard.json")):
        out.append(_env.read_json(f))
    if not out:
        sys.exit("no storyboard: run storyboard.py draft and sheets first")
    return out


def blank(panel, ids, swap=True):
    entry = lambda: {"scores": {k: None for k in CRITERIA}, "paragraph": "", **({"swap": None} if swap else {"worst": ""})}
    return {"critics": {c: {"boards": {i: entry() for i in ids}} for c in panel}}


def at_bar(scores):
    return bool(scores) and min(scores) >= FLOOR and sum(scores) / len(scores) >= BAR


def against_bar(scores):
    """The scores against the bar, in words."""
    return (f"mean {sum(scores) / len(scores):.2f} of {BAR} wanted, lowest {min(scores)} of {FLOOR} wanted, "
            + ("at the bar" if at_bar(scores) else "below the bar"))


def cut_frames(src, folder, tag, seconds):
    """FRAMES frames of `src` at equal spacing into `folder`, each named <tag>NN-<seconds>s.png; a read names a frame by
    the part before its seconds (for example r1-f07), so a read written for another cut names no frame of this one."""
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
    for i in range(FRAMES):
        t = (i + 0.5) * seconds / FRAMES
        subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                        str(folder / f"{tag}{i + 1:02d}-{t:.2f}s.png")], check=True)
    return sorted(folder.glob("*.png"))


def cites(text, folder):
    """The frames of `folder` that `text` names."""
    return [p.name for p in sorted(Path(folder).glob("*.png")) if p.name.rsplit("-", 1)[0] in (text or "")]


def cmd_ballot(a):
    bs = boards()
    # a board's type read (type.json) is written by sheets once its storyboard.md, frames and sheets are this draft's
    unread = [b["id"] for b in bs if not Path(f"{_env.B}/storyboards/{b['id']}/type.json").exists()]
    if unread:
        sys.exit(f"board {', '.join(unread)} has no type read for this draft: run storyboard.py sheets first")
    d = Path(f"{_env.B}/vote")
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# ballot", "", "Score every storyboard 1-5 on each criterion, as each critic, and write one paragraph per board "
             "(what works, what fails, what you would change). Look at each style sheet before scoring.", "",
             "Apply the swap test to every beat with a photograph: if its photograph could trade places with the neighboring beat's "
             "and the design would come out the same, the beat is a template. List those beat ids in the board's \"swap\" ([] when "
             "none); a board with one scores 3 or less on concept.", "",
             "## criteria", ""] + [f"- `{k}`: {v}" for k, v in CRITERIA.items()] + ["", "## the panel", ""]
    lines += [f"- `{k}`: {v}" for k, v in PANEL.items()]
    lines += ["", "Briefs: " + str(_env.SKILL / "critic" / "critic.md"), "", "## the boards", ""]
    for b in bs:
        sb = Path(f"{_env.B}/storyboards/{b['id']}")
        lines += [f"### {b['id']}: {b['name']}, {compose.name_of(b['style'])[0]}", "", b.get("idea", ""), "",
                  f"- structure {b.get('structure')}; style {b.get('style')}: {compose.name_of(b['style'])[1]}; footage: {b.get('footage')}",
                  f"- storyboard: {sb / 'storyboard.md'}",
                  f"- sheets, the hook, the peak card and the closer at rest: {sb / 'sheet.png'} (9:16), {sb / 'sheet-feed.png'} (1:1), {sb / 'sheet-wide.png'} (16:9); "
                  f"frames in {sb / 'frames'}/", ""]
    lines += [f"Fill in {_env.B}/vote/scores.json, then run vote.py tally.", ""]
    _env.write_text(d / "ballot.md", "\n".join(lines))
    f = d / "scores.json"
    if not f.exists():
        _env.write_json(f, blank(PANEL, [b["id"] for b in bs]))
    print(f"ballot -> {d / 'ballot.md'}; scores to fill -> {f}")
    return 0


def problems(data, panel, ids, beats=None, frames=None):
    """What keeps a ballot from counting; `beats` (board id -> its beat ids) asks for the swap test too, and `frames`
    (a cut round's folder) asks each critic for the worst thing and for the round's frames named."""
    bad = []
    for c in panel:
        cb = (data.get("critics", {}).get(c) or {}).get("boards", {})
        for i in ids:
            e = cb.get(str(i)) or {}
            if beats is not None:
                sw = e.get("swap")
                if not isinstance(sw, list) or any(x not in beats[i] for x in sw):
                    bad.append(f"{c} / board {i} / swap: needs a list of that board's beat ids ([] when none; got {sw!r})")
                elif sw and isinstance((e.get("scores") or {}).get("concept"), int) and e["scores"]["concept"] > 3:
                    bad.append(f"{c} / board {i}: the swap test names {', '.join(sw)}, so concept is 3 or less")
            for k in CRITERIA:
                v = (e.get("scores") or {}).get(k)
                if not isinstance(v, int) or not 1 <= v <= 5:
                    bad.append(f"{c} / board {i} / {k}: needs a whole number 1-5 (got {v!r})")
            if len((e.get("paragraph") or "").split()) < 25:
                bad.append(f"{c} / board {i}: the paragraph needs at least 25 words")
            if frames is not None:
                if len((e.get("worst") or "").split()) < 8:
                    bad.append(f"{c} / board {i} / worst: needs the worst thing you saw in this film, in at least 8 words")
                if not cites(f"{e.get('paragraph')} {e.get('worst')}", frames):
                    bad.append(f"{c} / board {i}: name the frames of {frames} you read (for example "
                               f"{next(iter(p.name.rsplit('-', 1)[0] for p in sorted(Path(frames).glob('*.png'))), 'r1-f01')})")
    return bad


def cmd_tally(a):
    bs = boards()
    ids = [b["id"] for b in bs]
    data = _env.read_json(f"{_env.B}/vote/scores.json")
    if not data:
        sys.exit(f"{_env.B}/vote/scores.json is missing: run vote.py ballot and fill it in")
    beats = {b["id"]: {bt["id"]: bt for bt in b["beats"]} for b in bs}
    bad = problems(data, PANEL, ids, beats)
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
    names = {b["id"]: f"{b['name']}, {compose.name_of(b['style'])[0]}" for b in bs}
    lines = ["# the vote", "", f"Winner: storyboard {win}, {names[win]} ({tot[win]} of {len(PANEL) * len(CRITERIA) * 5}; "
             + against_bar([s for c in PANEL for s in data["critics"][c]["boards"][win]["scores"].values()]) + ")."
             + (f" Tied on total with {', '.join(i for i in tie if i != win)}; the person's critic broke the tie." if len(tie) > 1 else ""),
             "",
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
    swap = {i: sorted({x for c in PANEL for x in data["critics"][c]["boards"][i]["swap"]}) for i in ids}
    lines += ["## the swap test", ""] + [f"- board {i}: " + (", ".join(swap[i]) if swap[i] else "every beat answers its own photograph")
                                          for i in ids]
    if swap[win]:
        lines += ["", f"Before snap, redesign each of these around its own photograph: {', '.join(swap[win])}. Snap refuses until each has changed."]
    _env.write_text(f"{_env.B}/vote.md", "\n".join(lines) + "\n")
    _env.write_json(f"{_env.B}/winner.json", {"board": win, "name": names[win], "style": next(b["style"] for b in bs if b["id"] == win),
                                          "picked_by": "the vote", "totals": tot, "order": order, "tie_broken_by_person": len(tie) > 1,
                                          "swap": {x: _env.digest(beats[win][x]) for x in swap[win]}})
    print(f"winner: storyboard {win} ({names[win]}), totals {tot} -> {_env.B}/vote.md, {_env.B}/winner.json")
    return 0


# what a cut made from one look leaves in the run, each removed when another look is picked; a track the person placed
# (music/source.<ext>) stays
FROM_A_CUT = ("film.json", "clips.json", "preview", "critic", "qa", "public/clips", "render/film-report.json")


def cmd_pick(a):
    bs = boards()
    by = {b["id"]: b for b in bs}
    bid = str(a.board)
    if bid not in by:
        sys.exit(f"there is no board {bid}: the boards are {', '.join(by)}")
    if not (a.reason or "").strip():
        sys.exit("say in one line why this look: --reason \"...\"")
    old = _env.read_json(f"{_env.B}/winner.json") or {}
    if str(old.get("board")) != bid:
        import shutil
        for rel in FROM_A_CUT:
            p = Path(_env.B) / rel
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        m = Path(_env.B) / "music"
        info = _env.read_json(f"{_env.B}/music.json") or {}
        if info.get("recipe") or not any(f.stem == "source" for f in m.glob("source.*")):
            Path(f"{_env.B}/music.json").unlink(missing_ok=True)
        for f in m.glob("*") if m.exists() else ():
            if f.is_file() and f.stem != "source":
                f.unlink()
    b = by[bid]
    name = f"{b['name']}, {compose.name_of(b['style'])[0]}"
    _env.write_json(f"{_env.B}/winner.json", {**{k: old[k] for k in ("totals", "order") if k in old}, "board": bid, "name": name,
                                          "style": b["style"], "picked_by": a.by, "reason": a.reason.strip(),
                                          "swap": old.get("swap") if str(old.get("board")) == bid else {}})
    print(f"picked: storyboard {bid} ({name}), {a.reason.strip()} -> {_env.B}/winner.json; next: music.py make, storyboard.py snap")
    return 0


def all_rounds():
    return sorted(Path(f"{_env.B}/critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))


def rounds():
    """The cut rounds of the board being cut now (B/film.json)."""
    bid = str((_env.read_json(f"{_env.B}/film.json") or {}).get("id"))
    return [p for p in all_rounds() if str((_env.read_json(p) or {}).get("board")) == bid]


NOT_MADE = "not made"


def read_problems(t):
    """What keeps the timed reads in `t` (timed.json) from counting, and the reads not made."""
    bad, open_ = [], []
    folder = t.get("frames") or ""
    for k in READS:
        r = (t.get("reads") or {}).get(k) or {}
        if r.get("pass") == NOT_MADE:
            (open_ if len((r.get("read") or "").split()) >= 8 else bad).append(k)
        elif not isinstance(r.get("pass"), bool) or len((r.get("read") or "").split()) < 25:
            bad.append(k)
        elif not cites(r.get("read"), folder):
            bad.append(f"{k} (it names none of the frames in {folder})")
    return bad, open_


# a stem is read in windows of WINDOW seconds; its floor is the quietest ROOM_SHARE of them (the room under the effects);
# a sound is a run of windows over HUSH times the floor, after QUIET seconds under it, that reaches RISE times the floor,
# and it starts where the run leaves the quiet (a whoosh or a riser swells up to its cue, so it starts before it); a dip
# shorter than QUIET inside a swell is part of the swell
WINDOW, ROOM_SHARE, RISE, HUSH, QUIET = 0.02, 0.2, 2.5, 1.6, 0.04


def onsets(wav):
    """Where each sound of a stem starts, in seconds: where its level leaves the room after a quiet spell, on its way
    well over it."""
    import array
    rate = 8000
    r = subprocess.run([_env.ffmpeg(), "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                       capture_output=True)
    pcm = array.array("h", r.stdout[:len(r.stdout) // 2 * 2])
    n = int(rate * WINDOW)
    levels = [math.sqrt(sum(v * v for v in pcm[i:i + n]) / n) for i in range(0, len(pcm) - n + 1, n)]
    if not levels:
        return []
    floor = max(1.0, sorted(levels)[int(len(levels) * ROOM_SHARE)])
    out, quiet, start, armed = [], 0, None, True
    for i, lv in enumerate(levels):
        if lv <= HUSH * floor:
            quiet += 1
            if quiet * WINDOW >= QUIET:
                start, armed = None, True
            continue
        quiet = 0
        if armed and start is None:
            start = i
        if start is not None and lv > RISE * floor:
            out.append(round(start * WINDOW, 2))
            start, armed = None, False
    return out


def cmd_timed(a):
    f = _env.read_json(f"{_env.B}/film.json") or {}
    pv = _env.read_json(f"{_env.B}/preview/preview.json") or {}
    if not f or pv.get("hash") != f.get("hash"):
        sys.exit("B/preview/preview.json is not for the current cut: run storyboard.py snap and film.py preview first")
    path = Path(f"{_env.B}/critic/timed.json")
    old = _env.read_json(path) or {}
    if old.get("hash") == f["hash"] and not read_problems(old)[0]:
        _, open_ = read_problems(old)
        failed = [k for k in READS if old["reads"][k]["pass"] is False]
        print(f"{path} already holds the reads of this cut: " + (f"failed: {', '.join(failed)}" if failed else "pass")
              + (f"; not made: {', '.join(open_)}" if open_ else ""))
        return 2 if failed else 0
    folder = Path(_env.B) / "critic" / f"timed-{f['hash'][:8]}"
    shots = cut_frames(Path(_env.B) / "preview" / "film.mp4", folder, f"{f['hash'][:4]}-t", f["seconds"])
    fx = Path(_env.B) / "music" / "fx.wav"
    land = sorted({round(t, 2) for t, _ in (_env.read_json(f"{_env.B}/music.json") or {}).get("effects") or []})
    _env.write_json(path, {"hash": f["hash"], "style": f["style"], "reads": {k: {"pass": None, "read": ""} for k in READS},
                           "film": str((Path(_env.B) / "preview" / "film.mp4").resolve()), "strip": pv.get("strip2"),
                           "frames": str(folder.resolve()),
                           "measured": {**{k: pv.get(k) for k in ("seconds", "cuts", "cuts_per_minute", "seconds_under_half", "hook_event_frame")},
                                        "cue_seconds": land, "effect_onsets": onsets(fx) if fx.exists() else None}})
    print(f"the four reads, as the editor, from frames: open every frame in {folder}/ "
          f"({len(shots)}, cut from this cut's preview) and its strip {pv.get('strip2')}; for sound, the effects master places "
          f"(measured.cue_seconds) against where the effects' sounds start (measured.effect_onsets). Then fill in {path}: "
          "for each read, pass (true or false) and read (at least 25 words naming the beats and the frames, for example "
          f"{shots[0].name.rsplit('-', 1)[0] if shots else ''}); a read you cannot make from what is here is pass \"not made\" "
          "and read the reason:\n" + "\n".join(f"  {k}: {v}" for k, v in READS.items()))
    return 0


def cmd_cut(a):
    """A round for the newest reel in out/ (the proof while out/proof.mp4 is there), read from the render report that
    certifies out/ (B/render/film-report.json): the newest round when it scores this same reel, the same round moved to
    the full-size reel of the cut it scored on the proof, a new one only when the reel changed."""
    digest = (_env.read_json(f"{_env.B}/render/film-report.json") or {}).get("reel")
    scale, src = proof.scale(), proof.newest()
    if scale != 1:
        print(proof.reading(src))
    if not digest:
        sys.exit(f"{_env.B}/render/film-report.json is missing: out/ is not a whole render; run film.py render --proof first")
    d = Path(f"{_env.B}/critic")
    d.mkdir(parents=True, exist_ok=True)
    mine = rounds()
    last = _env.read_json(mine[-1]) if mine else {}
    film = _env.read_json(f"{_env.B}/film.json") or {}
    cut = proof.picture(film.get("hash"), src)
    if last.get("film") == digest:
        if "sound" not in last:
            last["sound"] = sound_read(src)
            _env.write_json(mine[-1], last)
        print(f"round {last.get('round')} ({mine[-1]}) already scores this reel: fill it in from the frames in "
              f"{last.get('frames')}/{said()}")
        return 0
    if scale == 1 and last.get("scale") == proof.SCALE and last.get("cut") == cut:
        # the full-size reel of the cut the round scored on its proof: the same round, its frames cut again from the
        # full-size reel under the same names, and the type read again at full size
        # and the sound read again on it, the critics' citation standing
        cut_frames(src, Path(last["frames"]), f"r{last['round']}-f", film.get("seconds") or 60)
        last.update(film=digest, scale=1, proof_film=last["film"],
                    sound={**sound_read(src), "cited": (last.get("sound") or {}).get("cited", "")})
        for c in CUT_PANEL:
            last["critics"][c]["boards"]["film"]["scores"]["type"] = None
        _env.write_json(mine[-1], last)
        print(f"round {last['round']} moves to the full-size {src}: as each critic, open every frame in {last['frames']}/ "
              f"again, cut from it, read the type at the size a phone shows it, and score type in {mine[-1]}; the other "
              "scores stand")
        return 0
    unscored = last and not any(isinstance(v, int) for e in last["critics"].values() for v in e["boards"]["film"]["scores"].values())
    n = last["round"] if unscored else len(mine) + 1
    f = mine[-1] if unscored else d / f"cut-{len(all_rounds()) + 1}.json"
    shots = cut_frames(src, d / f.stem, f"r{n}-f", film.get("seconds") or 60)
    data = blank(CUT_PANEL, ["film"], swap=False)
    data["round"] = n
    data["board"] = str(film.get("id"))
    data["film"] = digest
    data["scale"] = scale
    data["cut"] = cut
    data["frames"] = str(d / f.stem)
    data["fixed"] = "" if n > 1 else None
    data["sound"] = sound_read(src)
    _env.write_json(f, data)
    print(f"round {n}: open every frame in {d / f.stem}/ ({len(shots)}, cut from {src}), then fill in {f}: each critic "
          f"scores the seven rules, writes a paragraph naming the frames it read (for example "
          f"{shots[0].name.rsplit('-', 1)[0] if shots else ''}) and the worst thing in the film in 'worst'"
          + (" (say in 'fixed' what changed since the last round)" if n > 1 else "")
          + f"{said()}; the read has {len(data['sound']['findings'])} findings")
    return 0


def sound_md():
    """The sound read's page in the current run."""
    return Path(f"{_env.B}/critic/sound.md")


def said():
    return f"; score sound from the sound read, {sound_md()}, and say in sound.cited which of its rows the score rests on"


def sound_read(film):
    """The rendered reel's sound read (sfx.py read: the cuts against the beat grid, the music's end against the last
    frame, the effects' peaks against the bed) over the board's effects as music.py master laid them (wall.effects_board
    of B/film.json, B/music/fx.wav) and the master B/music.json names, the bed as film.py mux lays it (no ducks beyond
    the dip at each impact), written to B/critic/sound.md and sound.json; its block in a round: the table, its findings,
    and `cited`, the sentence the critics fill in naming the rows the sound score rests on."""
    import sfx
    import wall
    f = _env.read_json(f"{_env.B}/film.json") or {}
    track = _env.read_json(f"{_env.B}/music.json") or {}
    fx = track.get("effects_wav")
    return sfx.critic_read(wall.effects_board(f), track, str(film), f.get("seconds"), _env.ffmpeg(), sound_md(),
                           fx=fx if fx and Path(fx).is_file() else None, ducked=False)


def sound_problems(data):
    """What a round's sound block still needs: the read itself, and the sentence that cites its rows."""
    import sfx
    return sfx.uncited(data.get("sound"), sound_md())


def cmd_verdict(a):
    rs = rounds()
    if not rs:
        sys.exit("no cut scores: run vote.py cut and fill it in")
    data = _env.read_json(rs[-1])
    src = proof.newest()
    stale = proof.stale(data, proof.digest(src), src) if src.exists() else f"{src} is missing: run film.py render --proof"
    if stale:
        print(f"{rs[-1]} is not a read of the newest render: {stale}")
        return 1
    bad = problems(data, CUT_PANEL, ["film"], frames=data.get("frames") or rs[-1].with_suffix("")) + sound_problems(data)
    if bad:
        print(f"{rs[-1]} is not complete:")
        for x in bad:
            print("  -", x)
        return 1
    film = {c: data["critics"][c]["boards"]["film"] for c in CUT_PANEL}
    scores = [s for e in film.values() for s in e["scores"].values()]
    # a round on the proof ends in the full-size render, where the critics read the type once more before deliver
    full = (". Render the full-size film (film.py render, with the same --also), run qa.py check, then vote.py cut: the "
            "critics read the type again at full size" if data.get("scale") == proof.SCALE else "")
    if at_bar(scores):
        print(f"SHIP: round {data.get('round')}, {against_bar(scores)}{full}")
        return 0
    # the critic who scored lowest names the fix, in the words they used for the worst thing they saw
    who = min(CUT_PANEL, key=lambda c: (min(film[c]["scores"].values()), list(CUT_PANEL).index(c)))
    low = min(film[who]["scores"], key=lambda k: (film[who]["scores"][k], list(CRITERIA).index(k)))
    found = f"{CUT_PANEL[who]} found the worst thing: {film[who]['worst'].strip()} (lowest: {low} {film[who]['scores'][low]})"
    if len(rs) >= 2:
        print(f"round {data.get('round')}: {against_bar(scores)}. {found}. The one fix is spent: deliver the best cut, and the "
              f"gate and B/brief.md carry its scores against the bar{full}")
        return 2
    print(f"FIX ONCE ({against_bar(scores)}): {found}. Fix that, render the proof again (film.py render --proof), then run "
          "vote.py cut for round 2")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ballot", "tally", "pick", "timed", "cut", "verdict"])
    ap.add_argument("board", nargs="?", help="pick: the board the person chose (1, 2 or 3)")
    ap.add_argument("--reason", help="pick: in one line, why this look")
    ap.add_argument("--by", default="the person", help="pick: who chose it: the person, or taste when the agent chose by taste")
    a = ap.parse_args()
    if a.cmd == "pick" and not a.board:
        ap.error("pick needs the board: vote.py pick 2 --reason \"...\"")
    return {"ballot": cmd_ballot, "tally": cmd_tally, "pick": cmd_pick, "timed": cmd_timed, "cut": cmd_cut, "verdict": cmd_verdict}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
