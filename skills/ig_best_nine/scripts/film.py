#!/usr/bin/env python3
"""Movement 4: the films and the stills, rendered by the studio composition from the cut storyboard (film.json).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview --run R   # the reel at half size, measured: preview/film.mp4, preview.json, strips
    python3 S/scripts/film.py render  --run R   # out/film.mp4 (reel 1080x1920), out/film-square.mp4 (1080x1080),
                                                # out/film-wide.mp4 (1920x1080), out/story.png, out/best-nine.png,
                                                # frames/<format>-<rest>.png

preview is what the critic's monotony read and qa.py timed look at before the film renders: the cuts as planned and
as the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook event's frame.
render refuses until qa.py timed has passed this cut (critic/timed.json and qa/timed.json name film.json's hash).
It renders the three formats of the one storyboard, lays the mastered music (music/master.wav) under each at AAC
192 kbps, and takes the stills from the films' rest moments: the story card is the reel's closer at rest, the
best-nine image is the square's closer at rest, and frames/ holds the hook, the densest beat and the closer of
every format for the critics. render/film-report.json carries every finding the composition logged.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import studio  # noqa: E402

OUT = Path("out")
NAMES = {"reel": "film.mp4", "square": "film-square.mp4", "wide": "film-wide.mp4"}


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f, {fmt: _env.read_json(p) for fmt, p in f["boards"].items()}


def cmd_preview(a):
    f, boards = film()
    d = Path("preview")
    d.mkdir(exist_ok=True)
    rep = studio.render([studio.video(boards["reel"], d / "film.mp4", scale=0.5)], "preview")
    if rep["failed"]:
        sys.exit(f"the preview render failed; see render/preview.log")
    m = studio.measure(d / "film.mp4", f["cuts"], f["hook_frame"])
    m.update(hash=f["hash"], tone=f["tone"], findings=[x["text"][:200] for x in rep["findings"]])
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}, strip {m['strip2']}")
    return 0


def mux(silent, out, seconds):
    master = Path("music/master.wav")
    if master.exists():
        cmd = [_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    else:
        shutil.copyfile(silent, out)
    return master.exists()


def cmd_render(a):
    f, boards = film()
    gate = _env.read_json("qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the monotony read) and qa.py timed first")
    OUT.mkdir(exist_ok=True)
    silent = Path("render/silent")
    silent.mkdir(parents=True, exist_ok=True)
    jobs = [studio.video(boards[fmt], silent / NAMES[fmt]) for fmt in NAMES]
    rests = f["rests"]
    jobs.append(studio.still(boards["reel"], rests["reel"]["closer"], OUT / "story.png"))
    jobs.append(studio.still(boards["square"], rests["square"]["closer"], OUT / "best-nine.png"))
    for fmt in NAMES:
        for k, fr in rests[fmt].items():
            jobs.append(studio.still(boards[fmt], fr, Path("frames") / f"{fmt}-{k}.png", scale=0.5))
    rep = studio.render(jobs, "film")
    if rep["failed"]:
        sys.exit("a render job failed; see render/film.log and render/film-report.json")
    music = False
    for fmt, name in NAMES.items():
        music = mux(silent / name, OUT / name, f["seconds"])
    print(f"wrote {', '.join(str(OUT / n) for n in NAMES.values())}, {OUT / 'story.png'}, {OUT / 'best-nine.png'} and frames/"
          + ("" if music else " (no music/master.wav: the films are silent)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
