#!/usr/bin/env python3
"""Movement 4: the reel and the best-nine image, rendered by the studio composition from the cut storyboard
(film.json); the square and wide films and the story card only when the person asked for them.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview --run R   # the reel at half size, measured: preview/film.mp4, preview.json, strips
    python3 S/scripts/film.py render  --run R   # out/film.mp4 (reel 1080x1920), out/best-nine.png, frames/reel-<rest>.png
    python3 S/scripts/film.py render  --run R --also landscape square stories
                                                # and, each only when the person asked for it: out/film-wide.mp4
                                                # (1920x1080), out/film-square.mp4 (1080x1080), out/story.png (1080x1920)

preview is what the critic's monotony read and qa.py timed look at before the film renders: the cuts as planned and
as the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook event's frame.
render refuses until qa.py timed has passed this cut (critic/timed.json and qa/timed.json name film.json's hash).
It renders the reel, and the other formats of the one storyboard that --also names, lays the mastered music
(music.json `master`) under each at AAC 192 kbps, and takes the stills from the boards' rest moments: the best-nine
image is the square's closer at rest, the story card (--also stories) the reel's, and frames/ holds the hook, the
densest beat and the closer of every rendered format for the critics. A film or story card out/ holds from an earlier
render that this one did not make is removed. render/film-report.json carries every finding the composition logged
and what the render made (`made`: the formats and whether the story card), which qa.py and deliver.py read; it is
written once the films and the stills are in out/, so it stands only over a whole set. The films and the stills reach
out/ together, only once every one of them rendered, so a failed or stopped render leaves out/ as it was. Each command holds the run's render lock from its first write to its last, and a second command in the
same run exits at once naming the running one's log.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
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


def mux(run, silent, out, seconds):
    master = (_env.read_json("music.json") or {}).get("master")
    if not (master and Path(master).exists()):
        shutil.copyfile(silent, out)
        return False
    cmd = [_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(out)]
    run.spawn(cmd, check=True)
    return True


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
    names = {fmt: name for fmt, name in NAMES.items() if fmt == "reel" or ASKED[fmt] in also}
    stills = ["story.png", "best-nine.png"] if "stories" in also else ["best-nine.png"]
    jobs = [studio.video(boards[fmt], silent / name, f["frames"]) for fmt, name in names.items()]
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
    music = False
    for name in names.values():
        music = mux(run, silent / name, done / name, f["seconds"])
    OUT.mkdir(exist_ok=True)
    # out/ reads not delivered while the files move in: the review page and the render report, which the gate reads as
    # the index of out/, go first, and the report comes back once the reel, whose hash the critics' round and the gate
    # key on, has moved in last
    report = studio.RENDER / "film-report.json"
    for index in (OUT / "review.html", report):
        index.unlink(missing_ok=True)
    for name in {NAMES["square"], NAMES["wide"], "story.png"} - set(names.values()) - set(stills):
        (OUT / name).unlink(missing_ok=True)
    for name in sorted([*names.values(), *stills], key=lambda n: n == NAMES["reel"]):
        os.replace(done / name, OUT / name)
    _env.write_json(report, {**rep, "made": {"formats": list(names), "stories": "story.png" in stills}})
    print(f"wrote {', '.join(str(OUT / n) for n in [*names.values(), *stills])} and frames/"
          + ("" if music else " (no mastered music in music.json: the films are silent)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the wide film, the square film, the story card)")
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    # the run lock is taken before the command writes anything into the run, so a refused command changes nothing
    with studio.lock({"preview": "preview", "render": "film"}[a.cmd]) as run:
        return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
