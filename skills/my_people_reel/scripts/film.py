#!/usr/bin/env python3
"""Movement 4: the film, cut first and finished once the cut passes, from film.json through the studio composition
(S/motion/studio, which renders the board in any of the three formats).

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/film.py cut --proof
                                       # the proof, every critic round before deliver: the timed cut at half size,
                                       # R/render/proof-cut.mp4 (540x960), with the same strip, beats at rest and cue
                                       # tiles in R/frames/ the full cut makes
    python3 S/scripts/film.py cut      # the full-size cut deliver takes: R/render/cut.mp4 (9:16 with the mastered music),
                                       # R/frames/film-strip.jpg (12 fps), R/frames/NN-<beat>.png (each beat at rest)
                                       # and R/frames/cues/ (the frames around each effect over its waveform)
    python3 S/scripts/film.py render   # once qa.py check passes on this cut and its critic round is scored:
                                       # out/film.mp4 (the cut), out/cover.png (the posted image: the closer at rest)
                                       # and out/story.png (the story card: the hook at rest, 1080x1920)
    python3 S/scripts/film.py render --also landscape square stories
                                       # and, each only when the person asked for it: out/film-wide.mp4 (1920x1080),
                                       # out/film-square.mp4 (1080x1080), out/people/NN-<handle>.png (each person's
                                       # story card, 1080x1920)

cut lays the storyboard in film.json out as the 9:16 drive board (R/render/board-reel.json) at the film's tempo, renders
it through the studio's drive film (1080x1920, 30 fps, H.264 High; on the graphics card when there is one), lays the
board's effects (sfx.py: whooshes on the cuts, shutters and pops as photographs and tags land, impacts on the title,
the slammed words and the wall, the riser into the wall, the room under it all, on the music's grid and in its key)
over the mastered music under it and measures it (cut.json's `sound`: the effects' count and loudness): render/cut.json carries the cuts as planned and as the picture shows them, the luma
line and its quiet seconds, and frames/ the 1 and 2 fps strips beside the 12 fps strip the critic reads. frames/cues/
holds one tile per sound effect (sfx.py's events) for the critic's sound read: the cut's frames every 0.2 s from 0.6 s before the cue to 0.8 s
after it in one row, over the waveform of the film's sound across the same span with the cue's time marked, each frame's
left edge over its own time; frames/cues.json names each tile's cue, its frames' times and the music's onsets in the
span. A board that has not changed since the last cut, drawn by the same built composition, is not rendered again. render takes the cut as the reel, renders its cover (the closer at
rest, 1080x1920) and its story card (the hook at rest, the title standing and every tag on, 1080x1920) and, for the formats --also names, lays the same storyboard out again for 1:1 or 16:9, each re-solved for its frame, renders it, and with stories
takes each person's still from the rest frame of the beat that names them. A film or story card out/ holds from an
earlier render that this one did not make is removed; engine.json's `made` names what this render made (the formats
and whether the story cards), which qa.py reads.
render/<name>-report.json carries every FONT_ERROR, IMAGE_ERROR and failed job. The renderer tries a job again when the
card's context is lost or a shader fails to compile; a film that still shows white frames fails the command, and out/
stays as it was.

Every film renders in chunks kept in R/render/chunks/ (60 frames each on a machine without an NVIDIA card), and its
progress is in R/render/<cut|final>.log.
An interrupted render (the machine restarted, the session died) is resumed by running the same command again: the
finished chunks are kept and only the missing ones render. A changed cut renders into chunks of its own.
out/film.mp4 is the index of out/: render takes out/review.html and then out/film.mp4 away before the first file moves
in, and once every format has rendered moves each deliverable into out/ by rename, then cards.json and engine.json,
and the reel last; a render stopped between two renames leaves no out/film.mp4, which the gate and deliver.py refuse.
deliver.py writes the page again. cut takes render/cut.json away before it lays the board out and writes it after the
measure, so a cut stopped on the way is one no later command reads.
--proof renders the cut at half size (proof.py) as R/render/proof-cut.mp4, beside render/cut.mp4 and never over it or
over out/film.mp4; the beats at rest, the strip and the cue tiles come out at the size the full cut gives them, and
render/cut.json carries the cut's `scale`. A full cut takes the proof away once it has measured, so
render/proof-cut.mp4 is there only while the newest cut is the proof: qa.py check and vote.py cut read it, and render
and deliver.py refuse it. render/cut.json's `cut` names the board and the music the cut was made from, so the critics'
round on a proof moves to the full-size cut of the same board and music.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import boards  # noqa: E402
import proof  # noqa: E402
import studio  # noqa: E402

FPS = 30
CUT = Path("render/cut.mp4")
CUT_JSON = Path("render/cut.json")
SILENT = Path("render/cut-silent.mp4")
OUTS = {"reel": Path("out/film.mp4"), "square": Path("out/film-square.mp4"), "wide": Path("out/film-wide.mp4")}
ALSO = ("landscape", "square", "stories")
FORMAT_OF = {"landscape": "wide", "square": "square"}


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def file_sha(p):
    return sha(Path(p).read_bytes())


def mux(run, silent, out, seconds, board):
    """The picture with its sound at `out`: the board's effects (sfx.py, from the board's `effects`: on the music's grid
    and in its key) over the master music.json names, the music coming down for each impact, the whole mix raised onto
    sfx.TARGET_LUFS and measured again through sfx.LIMIT, as sfx.mux masters it; the effects and the room alone when it
    names none. The effects are laid once: the one file is measured alone for qa.py's audio row and then mixed, and it
    lives only while ffmpeg reads it. Returns the effects' count, the integrated loudness of the effects alone and
    whether music is under them."""
    import music
    import sfx
    record = _env.read_json("music.json") or {}
    fx_board = board["effects"]
    out.parent.mkdir(parents=True, exist_ok=True)
    master = record.get("master")
    bed = master if master and Path(master).is_file() else None
    ff = _env.ffmpeg()
    with tempfile.TemporaryDirectory(dir=out.parent) as d:
        fx = Path(d) / "fx.wav"
        chans, impacts = sfx.lay(fx_board, seconds, record)
        sfx.write(fx, chans)
        lufs = music.integrated_file(fx)
        gain = 0.0
        if bed:
            gain = sfx.TARGET_LUFS - sfx.loudness(run.spawn, ff, silent, fx, bed, seconds, impacts, "")
            gain += sfx.TARGET_LUFS - sfx.loudness(run.spawn, ff, silent, fx, bed, seconds, impacts, f"volume={gain:.2f}dB,{sfx.LIMIT}")
        run.spawn(sfx.mux_cmd(ff, silent, fx, out, seconds, impacts, bed, gain), check=True)
    events, _ = sfx.events(fx_board, sfx.music_of(fx_board, record)[0])
    return {"effects": len(events), "fx_lufs": round(lufs, 2), "music": bool(bed)}


def the_film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f


def board_for(f, ctx, kind):
    b = boards.layout(f["storyboard"], ctx, kind, f["bpm"])
    _env.write_json(f"render/board-{kind}.json", b)
    return b


def frames_of(board):
    starts, run = [], 0
    for b in board["beats"]:
        starts.append(run)
        run += b["frames"]
    return starts, run


def strip_and_rests(run, board, starts, cut=CUT, silent=SILENT):
    """The critic's view of the cut: a 12 fps strip of the whole film, 24 frames a row, and every beat at rest, each at
    one size whatever the cut's scale."""
    ff = _env.ffmpeg()
    d = Path("frames")
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    secs = sum(b["frames"] for b in board["beats"]) / FPS
    run.spawn([ff, "-y", "-v", "error", "-i", str(cut), "-vf", f"fps=12,scale=-2:300,tile=24x{int(secs * 12 + 23) // 24}",
               "-frames:v", "1", "-update", "1", str(d / "film-strip.jpg")], check=True)
    for i, (s, b) in enumerate(zip(starts, board["beats"]), 1):
        n = s + b.get("rest", b["frames"] - 2)
        run.spawn([ff, "-y", "-v", "error", "-i", str(silent), "-vf", f"select='eq(n\\,{n})',scale=540:-1", "-frames:v", "1",
                   "-update", "1", str(d / f"{i:02d}-{b['id']}.png")], check=True)


STEP, BEFORE, SHOWN, TILE_W = 0.2, 0.6, 8, 180
WHAT = {"air": "a soft whoosh on the cut", "sweep": "a warm whoosh on the cut", "bright": "the film's one bright whoosh, on its first cut",
        "shutter": "a photograph lands", "pop": "a mark or a tag lands", "impact": "a title or a slammed word lands, or the wall settles",
        "riser": "the build into the wall, cut off as it settles"}


def cue_tiles(run, board, cut=CUT):
    """The critic's sound read, one tile per effect in frames/cues/, and frames/cues.json (the module's USAGE says
    what each holds). A cut with no music still carries its effects and the room, so every cut has its tiles."""
    d = Path("frames/cues")
    d.mkdir(parents=True, exist_ok=True)
    secs = sum(b["frames"] for b in board["beats"]) / FPS
    span, wide = STEP * SHOWN, TILE_W * SHOWN
    start = float((_env.read_json("film.json") or {}).get("music_start") or 0)
    onsets = [t - start for t in (_env.read_json("music.json") or {}).get("onsets") or []]
    out = []
    import sfx
    fx = board["effects"]
    events, _ = sfx.events(fx, sfx.music_of(fx, _env.read_json("music.json") or {})[0])
    starts_s, t = [], 0
    for b in board["beats"]:
        starts_s.append((t / FPS, b["id"]))
        t += b["frames"]
    for i, (at, kind) in enumerate(events, 1):
        c = {"kind": kind, "beat": [bid for s0, bid in starts_s if s0 <= at + 1e-6][-1], "what": WHAT[kind]}
        t0 = min(max(0.0, at - BEFORE), max(0.0, secs - span))
        tile = d / f"{i:02d}-{c['kind']}-{at:.2f}.png"
        x = round((at - t0) / span * wide)
        run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{span:.3f}", "-i", str(cut), "-filter_complex",
                   f"[0:v]fps={1 / STEP:g},scale={TILE_W}:-2,tile={SHOWN}x1,format=rgba[v];"
                   f"[0:a]showwavespic=s={wide}x160:colors=0xf4efe8,drawbox=x={x}:y=0:w=3:h=160:color=0xe0402a:t=fill,format=rgba[w];"
                   "[v][w]vstack", "-frames:v", "1", "-update", "1", str(tile)], check=True)
        out.append({"tile": str(tile), "beat": c.get("beat"), "kind": c["kind"], "what": c.get("what"), "at": round(at, 3),
                    "frames": [round(t0 + k * STEP, 2) for k in range(SHOWN)],
                    "music_onsets": [round(t, 3) for t in onsets if t0 <= t < t0 + span]})
    _env.write_json("frames/cues.json", {"step": STEP, "cues": out})


BLANK = 0.25  # seconds of white a lost context leaves at the least; a burn or flash frame is white for a frame or two


def white_stretches(ys, fps):
    """The starts, in seconds, of each stretch of frames whose darkest pixel (`ys`, one a frame at `fps`) is over 200
    luma for BLANK seconds or more."""
    out, run = [], 0
    for i, y in enumerate(list(ys) + [0.0]):
        if y >= 200:
            run += 1
            continue
        if run >= BLANK * fps:
            out.append(round((i - run) / fps, 2))
        run = 0
    return out


def white_seconds(run, mp4):
    """The seconds of `mp4` where a blank stretch starts: a tab that lost the card's context hands back white frames
    under the grain for the rest of its chunk and the job still reports success. Every frame of the film carries a
    photograph or ink type, so its darkest pixel at 64 px wide is far under 200 luma; a blank frame's is over it. A
    roll burn or a flash frame whites the picture out for a frame or two at a cut, so only a stretch of BLANK seconds
    or more is blank."""
    import re
    if not Path(mp4).exists():
        return []
    fps = 30
    out = run.spawn([_env.ffmpeg(), "-hide_banner", "-i", str(mp4), "-vf", f"fps={fps},scale=64:-2,signalstats,metadata=print:key=lavfi.signalstats.YMIN",
                     "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
    return white_stretches([float(x) for x in re.findall(r"YMIN=([\d.]+)", out)], fps)


def drew_white(run, mp4s):
    """The films of `mp4s` that show a white frame, each named with its white seconds."""
    return [f"{Path(m).name} at {', '.join(f'{t:g}' for t in w)} s" for m in mp4s if (w := white_seconds(run, m))]


def publish(src, out):
    """`src` put at `out` in one step, so a deliverable is either the finished file or the one before it."""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, out)


def cmd_cut(a, run):
    f = the_film()
    ctx = boards.Ctx()
    scale = proof.SCALE if getattr(a, "proof", False) else 1
    cut, silent = (proof.of(CUT), proof.of(SILENT)) if scale != 1 else (CUT, SILENT)
    prior = _env.read_json("render/cut.json") or {}
    # cut.json names the cut, its board and what it measured, so it goes before the board is laid out again and comes
    # back after the measure: a cut stopped on the way leaves none, and qa.py check, vote.py cut and film.py render refuse
    CUT_JSON.unlink(missing_ok=True)
    board = board_for(f, ctx, "reel")
    starts, total = frames_of(board)
    # the board and the drawing that renders it: a rebuilt composition renders the cut again
    drawn = sorted((q.relative_to(studio.DIST).as_posix(), file_sha(q)) for q in studio.DIST.rglob("*") if q.is_file())
    key = sha({"board": board, "clips": studio.props(board)["clips"], "drawn": drawn})
    rep = None
    if prior.get("board") == key and prior.get("scale", 1) == scale and silent.exists() and not a.again:
        print("the board has not changed since the last cut; laying the music under it again")
    else:
        jobs = [studio.video(board, silent, total, scale=scale)]
        rep = studio.render(jobs, "cut", run)
        for x in rep.get("findings", []):
            print("finding:", x["text"][:400])
        white = drew_white(run, [silent]) if silent.exists() else []
        if rep.get("failed") or not silent.exists() or white:
            print("the cut did not render" + (f": white frames in {'; '.join(white)}" if white else "")
                  + "; render/cut-report.json and render/cut.log name the failure")
            return 1
    sound = mux(run, silent, cut, total / FPS, board)
    music = sound["music"]
    strip_and_rests(run, board, starts, cut, silent)
    cue_tiles(run, board, cut)
    m = studio.measure(cut, [s / FPS for s in starts[1:]], boards.hook_frame(board), strips=Path("frames"), run=run, name="cut")
    roles = boards.roles(board)
    # the full-size cut takes the proof's place: render/proof-cut.mp4 stays only while the newest cut is the proof
    for old in ([] if scale != 1 else (proof.of(CUT), proof.of(SILENT))):
        old.unlink(missing_ok=True)
    master = (_env.read_json("music.json") or {}).get("master")
    info = {"board": key, "cut": sha({"board": key, "master": master}), "film": file_sha(cut), "scale": scale,
            "style": f["style"], "bpm": f["bpm"], "frames": total, "seconds": round(total / FPS, 3),
            "beats": [{"id": b["id"], "start": s, "frames": b["frames"]} for b, s in zip(board["beats"], starts)],
            "hook_frame": boards.hook_frame(board), "roles": {k: board["beats"][i]["id"] for k, i in roles.items()},
            "cards": f["storyboard"].get("cards", {}), "music": music, "sound": sound, "measure": m,
            "render": {k: rep.get(k) for k in ("seconds", "cpu_seconds", "gpu")} if rep else prior.get("render")}
    eng = _env.read_json("engine.json") or {}
    eng.update(engine="remotion", cut=info["render"])
    _env.write_json("engine.json", eng)
    _env.write_json(CUT_JSON, info)
    r = info["render"] or {}
    print(f"cut: {total / FPS:.1f} s, {len(board['beats'])} beats, {m['cuts']} cuts{' with music' if music else ' (no music)'} -> {cut}"
          f"{' (the half-size proof)' if scale != 1 else ''}; "
          f"strips and rests in frames/; render {r.get('seconds')} s wall, {r.get('cpu_seconds')} CPU-s")
    return 0


def card_file(n, handle):
    return Path("out/people") / f"{n:02d}-{handle}.png"


# the stills render here and move to out/ only once every format of the render has succeeded
STAGED_PEOPLE = Path("render/people")
STAGED_COVER, COVER = Path("render/cover.png"), Path("out/cover.png")
STAGED_STORY, STORY = Path("render/story.png"), Path("out/story.png")
CARDS_JSON = Path("cards.json")


def cmd_render(a, run):
    import vote
    f = the_film()
    if proof.scale(CUT) != 1:
        sys.exit(f"the newest cut is the half-size proof {proof.of(CUT)}: run film.py cut for the full-size cut, then "
                 "qa.py check and vote.py cut, where the critics read the type at full size, then film.py render")
    cut = _env.read_json("render/cut.json") or {}
    if not CUT.exists() or not cut:
        sys.exit("render/cut.mp4 is missing: run film.py cut first")
    if cut.get("film") != file_sha(CUT):
        sys.exit("render/cut.mp4 changed after its cut: run film.py cut again")
    check = _env.read_json("qa/check.json") or {}
    if not check.get("pass") or check.get("cut") != cut["film"]:
        sys.exit("qa/check.json has not passed on this cut: run qa.py check and fix what it names")
    ok, why = vote.scored(cut["film"])
    if not ok:
        sys.exit(why)
    also = getattr(a, "also", None) or ()
    kinds = [k for k in ("square", "wide") if k in {FORMAT_OF.get(x) for x in also}]
    ctx = boards.Ctx()
    reel = _env.read_json("render/board-reel.json")
    starts, _ = frames_of(reel)
    videos = [Path(f"render/{kind}-silent.mp4") for kind in kinds]
    jobs, boards_of = [], {}
    for kind, v in zip(kinds, videos):
        board = boards_of[kind] = board_for(f, ctx, kind)
        jobs.append(studio.video(board, v, frames_of(board)[1]))
    ids = [b["id"] for b in reel["beats"]]
    # the cover, the image the reel is posted with: the closer at rest
    closer = reel["beats"][-1]
    STAGED_COVER.unlink(missing_ok=True)
    jobs.append(studio.still(reel, starts[-1] + closer.get("rest", closer["frames"] - 2), STAGED_COVER))
    # the story card the reel is shared to stories with: the hook at rest, the title standing and every tag on
    STAGED_STORY.unlink(missing_ok=True)
    jobs.append(studio.still(reel, boards.rest_frame(reel, 0), STAGED_STORY))
    cards = []
    for p in ctx.people if "stories" in also else ():
        bid = (f["storyboard"].get("cards") or {}).get(p.handle)
        if bid not in ids:
            continue
        i = ids.index(bid)
        out = card_file(len(cards) + 1, p.handle)
        frame = starts[i] + reel["beats"][i].get("rest", reel["beats"][i]["frames"] - 2)
        cards.append({"handle": p.handle, "file": str(out), "beat": bid, "frame": frame})
        jobs.append(studio.still(reel, frame, STAGED_PEOPLE / out.name))
    if STAGED_PEOPLE.exists():
        shutil.rmtree(STAGED_PEOPLE)
    rep = studio.render(jobs, "final", run)
    for x in rep.get("findings", []):
        print("finding:", x["text"][:400])
    done = all(Path(j["out"]).exists() for j in jobs)
    white = drew_white(run, videos) if done else []
    if rep.get("failed") or not done or white:
        print("the render did not finish" + (f": white frames in {'; '.join(white)}" if white else "")
              + "; out/ is unchanged, render/final-report.json and render/final.log name the failure, and the same "
              "command run again renders what is missing")
        return 1
    # every format is finished: each deliverable is made beside out/ and put in place in one step
    staged = {"reel": Path("render/film.mp4"), "square": Path("render/film-square.mp4"), "wide": Path("render/film-wide.mp4")}
    shutil.copyfile(CUT, staged["reel"])
    for kind, v in zip(kinds, videos):
        mux(run, v, staged[kind], cut["frames"] / FPS, boards_of[kind])
    # out/film.mp4 is the index of out/: the gate holds it against the checked cut and deliver.py starts only when it is
    # there, so it goes before the first file moves in and comes back after the last. The review page speaks for the
    # whole delivered set, so it goes first; deliver.py writes it again.
    for f in (Path("out/review.html"), OUTS["reel"]):
        f.unlink(missing_ok=True)
    for kind in ("square", "wide"):
        if kind in kinds:
            publish(staged[kind], OUTS[kind])
        else:
            OUTS[kind].unlink(missing_ok=True)
    publish(STAGED_COVER, COVER)
    publish(STAGED_STORY, STORY)
    people = Path("out/people")
    stills = sorted(STAGED_PEOPLE.iterdir()) if STAGED_PEOPLE.exists() and cards else []
    for f in stills:
        publish(f, people / f.name)
    for f in sorted(people.iterdir()) if people.exists() else []:
        if f.name not in {s.name for s in stills}:
            f.unlink()
    if people.exists() and not stills:
        people.rmdir()
    _env.write_json(CARDS_JSON, {"size": [1080, 1920], "cards": cards})
    eng = _env.read_json("engine.json") or {}
    eng.update(engine="remotion", render={k: rep.get(k) for k in ("seconds", "cpu_seconds", "gpu")},
               made={"formats": ["reel", *kinds], "stories": bool(cards)})
    _env.write_json("engine.json", eng)
    publish(staged["reel"], OUTS["reel"])
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs: " + ", ".join([str(OUTS[k]) for k in ("reel", *kinds)] + [str(COVER), str(STORY)])
          + (f", {len(cards)} story cards in out/people/" if cards else ""))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cut", "render"])
    ap.add_argument("--again", action="store_true", help="cut: run the render even when the board has not changed (its finished chunks are kept)")
    ap.add_argument("--proof", action="store_true",
                    help="cut: the cut at half size as render/proof-cut.mp4, for every critic round before deliver")
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the wide film, the square film, the story cards)")
    a = ap.parse_args()
    _env.enter_run()
    # the run's lock is taken before the command writes anything into the run, and held until it ends
    with studio.lock({"cut": "cut", "render": "final"}[a.cmd]) as run:
        return {"cut": cmd_cut, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
