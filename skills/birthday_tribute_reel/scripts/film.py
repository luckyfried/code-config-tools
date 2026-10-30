#!/usr/bin/env python3
"""Movement 4: the film at 9:16, the posted image and the story card, rendered from B/film.json through motion/studio;
the square and wide films and the stills only when the person asked for them.

USAGE (from the workspace root; S = this skill's folder, B = the run's folder):
    python3 S/scripts/film.py preview   # the reel at half size, measured: B/preview/film.mp4, preview.json and its strips
    python3 S/scripts/film.py render    # out/film.mp4 (1080x1920), out/post.png (1080x1080, the closer laid out for
                                        # the feed) and out/story.png (1080x1920, the hook at rest)
    python3 S/scripts/film.py render --also landscape square stories
                                        # and, each only when the person asked for it: out/film-wide.mp4 (1920x1080),
                                        # out/film-square.mp4 (1080x1080), out/stills/<format>-<beat>.png
    python3 S/scripts/film.py frames    # the settled frame of every rest moment of out/film.mp4 into B/frames/NN-<beat>.png

preview is what the critic's timed read (vote.py timed) and qa.py timed look at before the film renders: the cuts as
planned and as the picture shows them, cuts a minute, each second's change and its quiet seconds, and the hook event's
frame, with a 1 fps and a 2 fps strip. render refuses until qa.py timed has passed this cut (B/qa/timed.json names
film.json's hash). It renders the reel and the other formats of the one storyboard that --also names (compose.py lays
the timed board out for each format's own frame), lays the mastered music (the master B/music.json names) under each at
AAC 192 kbps, and, with --also stories, takes the stills, the settled frames of the board's rest moments in each
rendered format at full size. A film or still out/ holds from an earlier render that this one did not make is removed.
With an NVIDIA card the browser draws on it and NVENC encodes; B/render/film-report.json carries the render's seconds,
every finding the composition logged (FONT_ERROR, IMAGE_ERROR, RENDER_ERROR) and what it made (`made`: the formats and
whether the stills), which qa.py reads.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import studio  # noqa: E402

FPS = 30
OUT = {"reel": "out/film.mp4", "feed": "out/film-square.mp4", "wide": "out/film-wide.mp4"}
STILLS = Path("out/stills")
ALSO = ("landscape", "square", "stories")
FORMAT_OF = {"landscape": "wide", "square": "feed"}


def film():
    f = _env.read_json(f"{_env.B}/film.json")
    if not f:
        sys.exit(f"{_env.B}/film.json is missing: run storyboard.py snap first")
    return f


def cmd_preview(a):
    f = film()
    with studio.lock("preview") as run:
        return _preview(f, run)


def _preview(f, run):
    d = Path(_env.B) / "preview"
    d.mkdir(parents=True, exist_ok=True)
    # preview.json names the cut its film shows, so it goes before the film changes and comes back after the measure
    (d / "preview.json").unlink(missing_ok=True)
    rep = studio.render([studio.video(compose.lay(f, "reel", f["bpm"]), d / "film.mp4", f["frames"], scale=0.5)], "preview", run)
    if rep["failed"]:
        sys.exit(f"the preview render failed; see {_env.B}/render/preview.log")
    m = studio.measure(d / "film.mp4", f["cuts"], f["hook_frame"], run=run)
    m.update(hash=f["hash"], style=f["style"], findings=[x["text"][:200] for x in rep["findings"]])
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}, strip {m['strip2']}")
    return 0


def mux(silent, out, seconds, run):
    """The silent film with the master B/music.json names laid under it; the silent film when it names none."""
    master = (_env.read_json(f"{_env.B}/music.json") or {}).get("master")
    if not master:
        shutil.copyfile(silent, out)
        return False
    run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", master, "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}",
               "-movflags", "+faststart", "-f", "mp4", str(out)], check=True)
    return True


def cmd_render(a):
    f = film()
    gate = _env.read_json(f"{_env.B}/qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the critic's read) and qa.py timed first")
    with studio.lock("film") as run:
        return _render(f, run, getattr(a, "also", None) or ())


def _render(f, run, also=()):
    """The films and stills are made in the run, and out/ takes them by os.replace only once every format succeeded, so
    a failed render leaves out/ as it was. The page that says out/ is ready to post (out/review.html) and the render
    report QA reads (render/film-report.json) both name out/, so they go before the first file moves in; the stills move
    in before the films, the reel last, and only then is the render's working report published under that name, with
    the reel's digest. deliver writes the page again. Only the reel, the formats `also` names and, when it names
    stories, their stills are made; out/ loses the films and stills it holds from an earlier render that this one did
    not make."""
    silent = Path(_env.B) / "render" / "silent"
    silent.mkdir(parents=True, exist_ok=True)
    stills = Path(_env.B) / "render" / "stills"
    shutil.rmtree(stills, ignore_errors=True)
    names = {fmt: name for fmt, name in OUT.items() if fmt == "reel" or fmt in {FORMAT_OF.get(x) for x in also}}
    laid = {fmt: compose.lay(f, fmt, f["bpm"]) for fmt in names}
    jobs = [studio.video(laid[fmt], silent / Path(names[fmt]).name, f["frames"]) for fmt in names]
    if "stories" in also:
        for fmt in names:
            for bid, frame in compose.rest_frames(laid[fmt], f):
                jobs.append(studio.still(laid[fmt], frame, stills / f"{fmt}-{bid}.png"))
    # the posted image is the closer laid out for the feed's own frame, the story card the hook at rest in the reel
    posts = Path(_env.B) / "render" / "posts"
    feed = laid.get("feed") or compose.lay(f, "feed", f["bpm"])
    jobs.append(studio.still(laid["reel"], compose.rest_frames(laid["reel"], f)[0][1], posts / "story.png"))
    jobs.append(studio.still(feed, compose.rest_frames(feed, f)[-1][1], posts / "post.png"))
    rep = studio.render(jobs, "film", run)
    if rep["failed"]:
        sys.exit(f"a render job failed; see {_env.B}/render/film.log and film-report.part.json")
    music = False
    for fmt, name in names.items():
        music = mux(silent / Path(name).name, silent / f"{Path(name).stem}.muxed.mp4", f["seconds"], run)
    Path("out").mkdir(exist_ok=True)
    Path("out/review.html").unlink(missing_ok=True)
    report = studio.render_dir() / "film-report.json"
    report.unlink(missing_ok=True)
    made = {p.name for p in stills.glob("*.png")}
    if made:
        STILLS.mkdir(exist_ok=True)
    for name in made:
        os.replace(stills / name, STILLS / name)
    for name in ("post.png", "story.png"):
        os.replace(posts / name, Path("out") / name)
    if STILLS.exists():
        for p in STILLS.iterdir():
            if p.name not in made:
                p.unlink()
        if not made:
            STILLS.rmdir()
    for name in set(OUT.values()) - set(names.values()):
        Path(name).unlink(missing_ok=True)
    for name in sorted(names.values(), key=lambda n: n == OUT["reel"]):
        os.replace(silent / f"{Path(name).stem}.muxed.mp4", name)
    rep["reel"] = hashlib.sha256(Path(OUT["reel"]).read_bytes()).hexdigest()[:16]  # the reel this report certifies
    rep["made"] = {"formats": list(names), "stories": bool(made), "posts": True}
    _env.write_json(report, rep)
    print(f"wrote {', '.join(names.values())}, out/post.png, out/story.png and {len(made)} stills" + (f" in {STILLS}/" if made else "")
          + ("" if music else f" (no master in {_env.B}/music.json: the films are silent)"))
    return 0


def cmd_frames(a):
    f = film()
    src = Path(OUT["reel"])
    if not (studio.render_dir() / "film-report.json").exists():
        sys.exit(f"{_env.B}/render/film-report.json is missing: out/ is not a whole render; run film.py render first")
    out = Path(a.out or f"{_env.B}/frames")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    rest = compose.rest_frames(compose.lay(f, "reel", f["bpm"]), f)
    for i, (bid, frame) in enumerate(rest, 1):  # the critic opens each frame as it is, so each lands whole
        dst = out / f"{i:02d}-{bid}.png"
        part = out / f".{dst.name}.part.png"
        subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-i", str(src), "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1",
                        "-update", "1", str(part)], check=True)
        os.replace(part, dst)
    print(f"{len(rest)} frames -> {out}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render", "frames"])
    ap.add_argument("--out")
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the wide film, the square film, the stills)")
    a = ap.parse_args()
    return {"preview": cmd_preview, "render": cmd_render, "frames": cmd_frames}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
