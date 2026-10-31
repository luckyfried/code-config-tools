#!/usr/bin/env python3
"""Movement 4: the places film rendered by the studio composition (motion/studio) from the cut storyboard (film.json):
the reel, the 16:9 and square films, the posted image and the story card.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/film.py preview   # the reel at half size, measured: preview/film.mp4, preview/preview.json and
                                        # its strips at 1, 2 and 12 frames a second
    python3 S/scripts/film.py render --proof
                                        # the proof, every round before deliver: the three films at half size as
                                        # out/proof.mp4, out/proof-16x9.mp4 and out/proof-square.mp4, with out/post.png,
                                        # out/story.png and frames/ as the full render makes them
    python3 S/scripts/film.py render    # the deliver render, full size: out/film.mp4 (1080x1920), out/film-16x9.mp4
                                        # (1920x1080), out/film-square.mp4 (1080x1080), out/post.png (the square film's
                                        # closer at rest, 1080x1080), out/story.png (the reel's closer at rest, 1080x1920)
                                        # and frames/<format>-<rest>.png

preview is what the critic's monotony read and qa.py timed look at before the film renders: the cuts as planned and
as the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook's frame. A preview that
fails (the graphics card lost its context, a job failed) leaves no preview.json and says so; run film.py preview
again, up to three tries in all, before anything after it. render refuses until qa.py timed has passed this cut
(qa/timed.json names film.json's hash). It renders the three films of the one storyboard and the two images, and lays
under each film, at AAC 192 kbps, 48 kHz, the shared layer's sound effects (sfx.py, from the reel board's
board_drive.fx_board(): a whoosh on every cut and the camera's dive, a shutter as every photograph lands, an impact as
the title lands and as the closer arrives, the riser into it, all on the music's quarter-beat grid and in its key) over
the mastered music music.json names (music.py master), music and effects mastered together by the shared mux to -14
LUFS under -1.5 dBTP in one encode, or alone when there is none. frames/ holds the hook, the stop and the closer of
every format at rest for the critics. render/film-report.json carries every finding the composition logged, and
engine.json the wall and processor seconds the render took and whether it ran on the graphics card; both carry
`scale`, which says which render it was. Its last step is qa.py check on what it made, so qa/check.json always
describes the newest films in out/.
--proof renders every film at half size (proof.py) beside the films in out/, never over them, and the two images and
frames/ as the full render makes them; a full render takes the proof's films out of out/, so out/proof.mp4 is there
only while the newest render is the proof, which qa.py check and vote.py cut read and deliver.py refuses.
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import board_drive  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import sfx  # noqa: E402
import studio  # noqa: E402

OUT = Path("out")
NAMES = {"reel": "film.mp4", "landscape": "film-16x9.mp4", "square": "film-square.mp4"}
# the posted image and the story card: each format's closer at rest, at full size
CARDS = {"post.png": "square", "story.png": "reel"}


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f, {fmt: _env.read_json(p) for fmt, p in f["boards"].items()}


def cmd_preview(a):
    f, boards = film()
    with studio.lock("preview") as run:
        return preview(f, boards, run)


def preview(f, boards, run):
    """preview.json goes first and comes back last, so a preview cut short leaves no preview.json for qa.py timed or
    vote.py timed to read as this cut's."""
    d = Path("preview")
    d.mkdir(exist_ok=True)
    (d / "preview.json").unlink(missing_ok=True)
    rep = studio.render([studio.video(boards["reel"], d / "film.mp4", f["frames"], scale=0.5)], "preview", run)
    bad = studio.faults(rep)
    if bad:
        sys.exit("the preview render failed: " + "; ".join(dict.fromkeys(x[:200] for x in bad))
                 + " (render/preview.log); run film.py preview again, up to three tries in all")
    m = studio.measure(d / "film.mp4", f["cuts"], f["hook_frame"], run=run)
    m.update(hash=f["hash"], style=f["style"], findings=[x["text"][:200] for x in rep["findings"]])
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}; strips {m['strip2']} and {', '.join(m['strip12'])}")
    return 0


def mux(run, silent, part, seconds, board):
    """The silent film with the shared layer's effects for `board` (sfx.py) over the master music.json names, music and
    effects mastered together by the shared mux to -14 LUFS under -1.5 dBTP in one encode, into `part`, a new file (a
    link kept to an earlier film keeps that film). Returns whether music is in it."""
    return sfx.mux(run.spawn, silent, part, seconds, board, _env.read_json("music.json") or {}, _env.ffmpeg())


def cmd_render(a):
    f, boards = film()
    gate = _env.read_json("qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the monotony read) and qa.py timed first")
    scale = proof.SCALE if a.proof else 1
    with studio.lock("film") as run:
        render(f, boards, run, scale)
        if scale != 1:
            print(proof.reading(proof.of(OUT / NAMES["reel"])))
        res, cut, _ = qa.film_checks(run, scale)
        return qa.report(res, "qa/check.json", cut, "CHECKS")


def render(f, boards, run, scale=1):
    """The three films and the two images render into render/silent/; out/ takes them only once every one of them is
    finished, each by a rename, so a failed render leaves out/ as the last finished render left it. out/review.html,
    qa/check.json and render/film-report.json, which vouch for the set, leave before the first rename, and the report
    and engine.json come back after the last, the reel last of the films, so a render cut short among the renames, or a
    render after it cut short before its renames, leaves a set the gate refuses. At a `scale` under 1 the films are the
    proof's, under proof.of() names; a full render takes the proof's films away with the index."""
    names = {fmt: proof.of(n).name if scale != 1 else n for fmt, n in NAMES.items()}
    silent = Path("render/silent")
    silent.mkdir(parents=True, exist_ok=True)
    jobs = [studio.video(boards[fmt], silent / name, f["frames"], scale=scale) for fmt, name in names.items()]
    jobs += [studio.still(boards[fmt], f["rests"][fmt]["closer"], silent / name) for name, fmt in CARDS.items()]
    for fmt in NAMES:
        for k, fr in f["rests"][fmt].items():
            jobs.append(studio.still(boards[fmt], fr, Path("frames") / f"{fmt}-{k}.png", scale=0.5))
    t0 = time.time()
    rep = studio.render(jobs, "film", run)
    wall = round(time.time() - t0, 1)
    bad = studio.faults(rep)
    if bad:
        for x in dict.fromkeys(bad):
            print("fault:", x[:400])
        sys.exit("the render has faults; see render/film.log and render/film-report.part.json")
    music = False
    fx = board_drive.fx_board(boards["reel"])
    for name in names.values():
        music = mux(run, silent / name, silent / f"{Path(name).stem}.part.mp4", f["seconds"], fx)
    OUT.mkdir(exist_ok=True)
    report = studio.RENDER / "film-report.json"
    # the full-size films take the proof's place: out/proof.mp4 stays only while the newest render is the proof
    for p in (OUT / "review.html", Path("qa/check.json"), report, Path("engine.json"), *([] if scale != 1 else proof.films(OUT))):
        p.unlink(missing_ok=True)
    for name in CARDS:
        os.replace(silent / name, OUT / name)
    for name in sorted(names.values(), key=lambda n: n == names["reel"]):
        os.replace(silent / f"{Path(name).stem}.part.mp4", OUT / name)
        (silent / name).unlink()
    _env.write_json("engine.json", {"engine": "remotion", "card": rep.get("gpu"), "seconds": wall, "cpu_seconds": rep.get("cpu_seconds"),
                                    "jobs": len(jobs), "scale": scale, "timings": rep.get("timings", [])})
    _env.write_json(report, {**rep, "scale": scale})
    print(f"wrote {', '.join(str(OUT / n) for n in [*names.values(), *CARDS])} and frames/ in {wall:.0f} s"
          + (" (the half-size proof)" if scale != 1 else "")
          + ("" if music else " (music.json names no master: the films carry the effects alone)"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    ap.add_argument("--proof", action="store_true",
                    help="render: the films at half size as out/proof.mp4, out/proof-16x9.mp4 and out/proof-square.mp4, "
                         "for every round before deliver")
    a = ap.parse_args()
    _env.enter_run()
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
