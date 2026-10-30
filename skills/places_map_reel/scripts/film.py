#!/usr/bin/env python3
"""Movement 4: the places film rendered by the studio composition (motion/studio) from the cut storyboard (film.json):
the reel, the 16:9 and square films, the posted image and the story card.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/film.py preview   # the reel at half size, measured: preview/film.mp4, preview/preview.json and
                                        # its strips at 1, 2 and 12 frames a second
    python3 S/scripts/film.py render    # out/film.mp4 (1080x1920), out/film-16x9.mp4 (1920x1080), out/film-square.mp4
                                        # (1080x1080), out/post.png (the square film's closer at rest, 1080x1080),
                                        # out/story.png (the reel's closer at rest, 1080x1920) and frames/<format>-<rest>.png

preview is what the critic's monotony read and qa.py timed look at before the film renders: the cuts as planned and
as the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook's frame. A preview that
fails (the graphics card lost its context, a job failed) leaves no preview.json and says so; run film.py preview
again, up to three tries in all, before anything after it. render refuses until qa.py timed has passed this cut
(qa/timed.json names film.json's hash). It renders the three films of the one storyboard and the two images, and lays the mastered music (the master
music.json names, from music.py master) under each film at AAC 192 kbps, 48 kHz; a film whose encoded peak is over
-1.6 dBFS is muxed again with its audio trimmed by the overshoot. frames/ holds the hook, the stop and the closer of
every format at rest for the critics. render/film-report.json carries every finding the composition logged, and
engine.json the wall and processor seconds the render took and whether it ran on the graphics card. Its last step is
qa.py check on what it made, so qa/check.json always describes the films in out/.
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402
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


def peak_of(run, path):
    r = run.spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    got = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return float(got[-1]) if got else -99.0


def mux(run, silent, part, seconds):
    """The silent film with the master music.json names under it, into `part`, a new file (a link kept to an earlier
    film keeps that film)."""
    named = (_env.read_json("music.json") or {}).get("master")
    master = Path(named) if named and Path(named).exists() else None

    # the fast coder: the default one's overshoot on a dense bed of sharp attacks (a marimba) jumps by a dB either way
    # with a quarter dB of level, past 0 dBFS at times, so no trim can hold its peak; the fast one's follows the level
    def once(trim):
        cmd = [_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent)]
        if master:
            cmd += ["-i", str(master), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", f"volume={trim:.2f}dB",
                    "-c:a", "aac", "-aac_coder", "fast", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}"]
        else:
            cmd += ["-c:v", "copy"]
        run.spawn(cmd + ["-movflags", "+faststart", str(part)], check=True)
    once(0.0)
    if master:
        # the AAC encode overshoots the master's peaks by up to about 1 dB on a soft bed
        peak = peak_of(run, part)
        if peak > -1.6:
            once(-1.6 - peak)
    return bool(master)


def cmd_render(a):
    f, boards = film()
    gate = _env.read_json("qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the monotony read) and qa.py timed first")
    with studio.lock("film") as run:
        render(f, boards, run)
        res, cut, _ = qa.film_checks(run)
        return qa.report(res, "qa/check.json", cut, "CHECKS")


def render(f, boards, run):
    """The three films and the two images render into render/silent/; out/ takes them only once every one of them is
    finished, each by a rename, so a failed render leaves out/ as the last finished render left it. out/review.html,
    qa/check.json and render/film-report.json, which vouch for the set, leave before the first rename, and the report
    and engine.json come back after the last, the reel last of the films, so a render cut short among the renames, or a
    render after it cut short before its renames, leaves a set the gate refuses."""
    silent = Path("render/silent")
    silent.mkdir(parents=True, exist_ok=True)
    jobs = [studio.video(boards[fmt], silent / name, f["frames"]) for fmt, name in NAMES.items()]
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
    for name in NAMES.values():
        music = mux(run, silent / name, silent / f"{Path(name).stem}.part.mp4", f["seconds"])
    OUT.mkdir(exist_ok=True)
    report = studio.RENDER / "film-report.json"
    for p in (OUT / "review.html", Path("qa/check.json"), report, Path("engine.json")):
        p.unlink(missing_ok=True)
    for name in CARDS:
        os.replace(silent / name, OUT / name)
    for name in sorted(NAMES.values(), key=lambda n: n == NAMES["reel"]):
        os.replace(silent / f"{Path(name).stem}.part.mp4", OUT / name)
        (silent / name).unlink()
    _env.write_json("engine.json", {"engine": "remotion", "card": rep.get("gpu"), "seconds": wall, "cpu_seconds": rep.get("cpu_seconds"),
                                    "jobs": len(jobs), "timings": rep.get("timings", [])})
    _env.write_json(report, rep)
    print(f"wrote {', '.join(str(OUT / n) for n in [*NAMES.values(), *CARDS])} and frames/ in {wall:.0f} s"
          + ("" if music else " (music.json names no master: the films are silent)"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    a = ap.parse_args()
    _env.enter_run()
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
