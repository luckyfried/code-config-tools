#!/usr/bin/env python3
"""Movement 4: the reel and the best-nine image, rendered by the studio composition from the cut storyboard
(film.json); the square and wide films and the story card only when the person asked for them.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview --run R   # the reel at half size, measured: preview/film.mp4, preview.json, strips
    python3 S/scripts/film.py render  --run R --proof [--also ...]
                                                # the proof, every round before deliver: each film at half size as
                                                # out/proof.mp4, out/proof-wide.mp4, out/proof-square.mp4, with
                                                # out/best-nine.png, out/story.png and frames/ as the full render makes them
    python3 S/scripts/film.py render  --run R   # the deliver render, full size: out/film.mp4 (reel 1080x1920),
                                                # out/best-nine.png, frames/reel-<rest>.png
    python3 S/scripts/film.py render  --run R --also landscape square stories
                                                # and, each only when the person asked for it: out/film-wide.mp4
                                                # (1920x1080), out/film-square.mp4 (1080x1080), out/story.png (1080x1920)

preview is what the critic's monotony read and qa.py timed look at before the film renders: the cuts as planned and
as the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook event's frame.
render refuses until qa.py timed has passed this cut (critic/timed.json and qa/timed.json name film.json's hash).
It renders the reel, and the other formats of the one storyboard that --also names, lays the mastered music
(music.json `master`) under each at AAC 192 kbps with the shared sound effects over it (sfx.py, from each format's
board through story.fx_board: a whoosh on each cut, a shutter as each photograph lands, an impact as the title and the
year land, a riser into the closer and an impact where it settles, on the music's grid and in its key; alone when there
is no music), the whole mix mastered once onto -14 LUFS by the shared mux, and takes the stills from the boards' rest moments: the best-nine
image is the square's closer at rest, the story card (--also stories) the reel's, and frames/ holds the hook, the
densest beat and the closer of every rendered format for the critics. A film or story card out/ holds from an earlier
render that this one did not make is removed. render/film-report.json carries every finding the composition logged,
what the render made (`made`: the formats and whether the story card), and each film's sound (`sound`: per format the
effects laid, their integrated loudness and the music's, LUFS), which qa.py and deliver.py read, and its `scale`
says which render it was; it is written once the films and the stills are in out/, so it stands only over a whole set. The films and the stills reach
out/ together, only once every one of them rendered, so a failed or stopped render leaves out/ as it was.
--proof renders every film at half size (proof.py) beside the films in out/, never over them, and the stills as the
full render makes them; a full render takes the proof's films out of out/, so out/proof.mp4 is there only while the
newest render is the proof, which qa.py check and vote.py cut read and deliver.py refuses. Each command holds the run's
render lock from its first write to its last, and a second command in the same run exits at once naming the running
one's log.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import proof  # noqa: E402
import sfx  # noqa: E402
import story  # noqa: E402
import studio  # noqa: E402

OUT = Path("out")
NAMES = {"reel": "film.mp4", "square": "film-square.mp4", "wide": "film-wide.mp4"}
ALSO = ("landscape", "square", "stories")
ASKED = {"reel": "reel", "square": "square", "wide": "landscape"}


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f, {fmt: _env.read_json(p) for fmt, p in f["boards"].items()}


def cmd_preview(a, run):
    f, boards = film()
    d = Path("preview")
    d.mkdir(exist_ok=True)
    # the measurement goes first and comes back only with the new film's, so a preview stopped partway never leaves
    # vote.py timed or qa.py timed reading an earlier film's figures and strips
    (d / "preview.json").unlink(missing_ok=True)
    rep = studio.render([studio.video(boards["reel"], d / "film.mp4", f["frames"], scale=0.5)], "preview", run)
    if rep["failed"]:
        sys.exit(f"the preview render failed; see render/preview.log")
    m = studio.measure(d / "film.mp4", f["cuts"], f["hook_frame"], run=run)
    m.update(hash=f["hash"], style=f["style"], findings=[x["text"][:200] for x in rep["findings"]])
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}, strip {m['strip2']}")
    return 0


def loudness(run, wav):
    """A sound file's integrated loudness, LUFS (None when the meter reads nothing)."""
    r = run.spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(wav), "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                  capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def mux(run, silent, out, seconds, board):
    """The film at `out`: its picture, the board's effects (sfx.py) and the mastered music under them when music.json
    names one that exists, the whole mix mastered once by the shared mux. Returns the film's sound: whether music is in
    it, the effects laid, and the effects' and the music's integrated loudness."""
    record = _env.read_json("music.json") or {}
    fx = story.fx_board(board)
    with tempfile.TemporaryDirectory(dir=Path(out).parent) as d:
        wav = Path(d) / "fx.wav"
        sfx.write(wav, sfx.lay(fx, seconds, record)[0])
        fx_lufs = loudness(run, wav)
    music = sfx.mux(run.spawn, silent, out, seconds, fx, record, _env.ffmpeg())
    bpm, _, _ = sfx.music_of(fx, record)
    return {"music": bool(music), "effects": len(sfx.events(fx, bpm)[0]), "fx_lufs": fx_lufs,
            "music_lufs": record.get("master_lufs") if music else None}


def cmd_render(a, run):
    f, boards = film()
    gate = _env.read_json("qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the monotony read) and qa.py timed first")
    silent = Path("render/silent")
    # every deliverable is finished here first and moved into out/ only once all of them are, so out/ never holds a
    # film or a still from a render that failed or was stopped
    done = Path("render/out")
    done.mkdir(parents=True, exist_ok=True)
    silent.mkdir(parents=True, exist_ok=True)
    also = getattr(a, "also", None) or ()
    scale = proof.SCALE if getattr(a, "proof", False) else 1
    # the proof's films carry the proof's names (proof.of), so a proof never stands where a film does
    place = (lambda n: proof.of(n).name) if scale != 1 else (lambda n: n)
    names = {fmt: place(name) for fmt, name in NAMES.items() if fmt == "reel" or ASKED[fmt] in also}
    stills = ["story.png", "best-nine.png"] if "stories" in also else ["best-nine.png"]
    jobs = [studio.video(boards[fmt], silent / name, f["frames"], scale=scale) for fmt, name in names.items()]
    rests = f["rests"]
    if "stories" in also:
        jobs.append(studio.still(boards["reel"], rests["reel"]["closer"], done / "story.png"))
    jobs.append(studio.still(boards["square"], rests["square"]["closer"], done / "best-nine.png"))
    for fmt in names:
        for k, fr in rests[fmt].items():
            jobs.append(studio.still(boards[fmt], fr, Path("frames") / f"{fmt}-{k}.png", scale=0.5))
    rep = studio.render(jobs, "film", run)
    if rep["failed"]:
        sys.exit("a render job failed; see render/film.log and render/staging/film-report.json")
    sound = {fmt: mux(run, silent / name, done / name, f["seconds"], boards[fmt]) for fmt, name in names.items()}
    music = sound["reel"]["music"]
    OUT.mkdir(exist_ok=True)
    # out/ reads not delivered while the files move in: the review page and the render report, which the gate reads as
    # the index of out/, go first, and the report comes back once the reel, whose hash the critics' round and the gate
    # key on, has moved in last
    report = studio.RENDER / "film-report.json"
    for index in (OUT / "review.html", report):
        index.unlink(missing_ok=True)
    for name in {place(NAMES["square"]), place(NAMES["wide"]), "story.png"} - set(names.values()) - set(stills):
        (OUT / name).unlink(missing_ok=True)
    # the full-size films take the proof's place: out/proof.mp4 stays only while the newest render is the proof
    for old in (proof.films(OUT) if scale == 1 else []):
        old.unlink()
    for name in sorted([*names.values(), *stills], key=lambda n: n == names["reel"]):
        os.replace(done / name, OUT / name)
    _env.write_json(report, {**rep, "made": {"formats": list(names), "stories": "story.png" in stills}, "sound": sound,
                             "scale": scale})
    print(f"wrote {', '.join(str(OUT / n) for n in [*names.values(), *stills])} and frames/"
          + (" (the half-size proof)" if scale != 1 else "")
          + ("" if music else " (no mastered music in music.json: the films carry the effects alone)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the wide film, the square film, the story card)")
    ap.add_argument("--proof", action="store_true",
                    help="render: the films at half size as out/proof.mp4 and its siblings, for every round before deliver")
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    # the run lock is taken before the command writes anything into the run, so a refused command changes nothing
    with studio.lock({"preview": "preview", "render": "film"}[a.cmd]) as run:
        return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
