#!/usr/bin/env python3
"""Movement 4: the trip film at 9:16, and the 16:9 and square films and the five story cards when asked, rendered from the timed storyboard.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/film.py preview  # the reel at half size, measured: preview/film.mp4, preview/preview.json, strips
    python3 S/scripts/film.py render   # out/film.mp4 (1080x1920), out/cover.png (1080x1920) and frames/
    python3 S/scripts/film.py render --also landscape square stories
                                       # and, naming only what the person asked for, out/film-16x9.mp4 (1920x1080),
                                       # out/film-square.mp4 (1080x1080), out/story-1.png .. out/story-5.png (1080x1920)
    python3 S/scripts/film.py frames   # frames/strip-<beat>.png (12 frames across each beat) and frames/film-strip.png
                                       # (the film at 1 fps), from out/film.mp4; frames/frames.json names that film

The engine is the studio composition built into S/motion/dist, drawn frame by frame in a headless browser by
scripts/render.py; with a graphics card it draws and encodes there (studio.py). film.json, film-landscape.json and film-square.json (storyboard.py snap) are one storyboard timed once
and framed for three pictures: the same spans, cues and photographs, the camera framing each picture's own shape.

preview is what the critic's timed read looks at before the film renders: the cuts as planned and as the picture
shows them, the luma line and its quiet seconds, and the 1 and 2 fps strips. render writes the silent reel, and the
other formats --also names, to render/silent/, lays the mastered music under each (music/master.wav from music.py
master, AAC 192 kbps, 48 kHz; a film whose encoded peak is over -1.6 dBTP is muxed again with its audio trimmed by the
overshoot), and takes the stills from the films' rests: the cover (out/cover.png) is the reel at its closer's held
still, the look's own closer, the picture the reel posts with; the story cards (--also stories) are the reel at the rests
film.json names in `stories`, and frames/ holds every rest of every rendered format for the critics. An extra an
earlier render left in out/ that this render was not asked for is taken away. render/film-report.json carries every
finding the composition logged and what the render made (`made`: its formats and whether the story cards); a shader error or a lost WebGL context fails that attempt in render.py, so it never reaches a film. qa.py
reads the report. A render that changes out/ removes out/review.html first, so the page deliver.py writes never
stands beside films it did not check. preview and render take the run's render lock before their first write into
the run, so a second render in the same run is refused before it changes anything.
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import studio  # noqa: E402

FPS = 30
ALSO = ("landscape", "square", "stories")
FILMS = {"reel": ("film.json", "out/film.mp4"), "landscape": ("film-landscape.json", "out/film-16x9.mp4"),
         "square": ("film-square.json", "out/film-square.mp4")}
FAULTS = ("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR")


def faults(rep):
    """The findings of a render report that refuse a film, and the failed jobs."""
    bad = [f["text"] for f in rep.get("findings", []) if f["text"].startswith(FAULTS)]
    return bad + [f"{rep['failed']} render jobs failed"] * bool(rep.get("failed"))


def films():
    out = {k: _env.read_json(f) for k, (f, _) in FILMS.items()}
    if not out["reel"]:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return out


def cmd_preview(a, run):
    f = films()["reel"]
    d = Path("preview")
    # preview.json describes the preview film beside it: it goes before that film changes and comes back after measure
    (d / "preview.json").unlink(missing_ok=True)
    rep = studio.render([studio.video(f, d / "film.mp4", scale=0.5)], "preview", run)
    bad = faults(rep)
    if bad:
        for t in bad:
            print("refused:", t[:400])
        sys.exit("the preview render failed; see render/preview.log")
    m = studio.measure(d / "film.mp4", f["cuts"], 0, run=run)
    m.update(style=f["style"], findings=[x["text"][:200] for x in rep["findings"]], render_seconds=rep.get("seconds"))
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts, seconds under 0.5: {m['seconds_under_half']} -> {d / 'preview.json'}, strip {m['strip2']}")
    return 0


def peak_of(path, run):
    r = run.spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                  capture_output=True, text=True)
    got = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return float(got[-1]) if got else -99.0


def mux(silent, out, seconds, run):
    """The silent film with the master music.json names under it, made under a temporary name and moved to `out` whole;
    the ffmpeg processes start through the command's lock (`run.spawn`)."""
    named = (_env.read_json("music.json") or {}).get("master")
    master = Path(named) if named and Path(named).exists() else None
    part = _env.part(out)

    def once(trim):
        cmd = [_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent)]
        if master is not None:
            cmd += ["-i", str(master), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", f"volume={trim:.2f}dB",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}"]
        else:
            cmd += ["-c:v", "copy"]
        run.spawn(cmd + ["-movflags", "+faststart", str(part)], check=True)
    once(0.0)
    if master is not None:
        # the AAC encode overshoots the master's peaks by up to about 1 dB on a soft bed
        peak = peak_of(part, run)
        if peak > -1.6:
            once(-1.6 - peak)
    os.replace(part, out)
    return master is not None


def cmd_render(a, run):
    """The reel and the formats --also names render and mux into render/ first. Only once every job of the command
    succeeded does out/ change: review.html and render/film-report.json go first, so a render stopped partway never
    leaves a page that reads delivered or a report the gate takes as proof, then any extra this render was not asked
    for leaves, the story cards, the cover and the films move in, each by os.replace, the reel last; timeline.json, which describes
    the reel, goes with them and comes back once the reel is in, and the report once every file is. A failed render
    leaves out/ as it was."""
    fs = films()
    also = getattr(a, "also", None) or ()
    silent, cards, staged = Path("render/silent"), Path("render/stories"), Path("render/out")
    jobs, made, stories = [], [], []
    names = [k for k in FILMS if (k == "reel" or k in also) and fs[k]]
    for k in names:
        out = FILMS[k][1]
        jobs.append(studio.video(fs[k], silent / Path(out).name))
        made.append((silent / Path(out).name, out, fs[k]["seconds"]))
    reel = fs["reel"]
    # the cover is the closer's held still, the look's own closer: the picture the reel posts with
    jobs.append(studio.still(reel, reel["rests"]["closer"], cards / "cover.png"))
    if "stories" in also:
        for n, key in enumerate(reel["stories"], 1):
            jobs.append(studio.still(reel, reel["rests"][key], cards / f"story-{n}.png"))
            stories.append(f"story-{n}.png")
    for k in names:
        for key, fr in fs[k].get("rests", {}).items():
            jobs.append(studio.still(fs[k], fr, Path("frames") / f"{k}-{key}.png", scale=0.5))
    rep = studio.render(jobs, "film", run)
    bad = faults(rep)
    for t in bad:
        print("fault:", t[:400])
    if bad:
        print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {rep.get('seconds', 0):.0f} s; out/ unchanged")
        return 1
    staged.mkdir(parents=True, exist_ok=True)
    music = False
    for sil, out, secs in made:
        music = mux(sil, staged / Path(out).name, secs, run)
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    # the render report is qa.py's proof that out/ is this render's: it goes with the review page and comes back
    # after the last file is in, so a render stopped between two moves leaves a set the gate refuses
    report = studio.RENDER / "film-report.json"
    report.unlink(missing_ok=True)
    (out_dir / "review.html").unlink(missing_ok=True)
    Path("timeline.json").unlink(missing_ok=True)
    for f in out_dir.glob("story-*.png"):
        if f.name not in stories:
            f.unlink()
    for k, (_, out) in FILMS.items():
        if k not in names:
            Path(out).unlink(missing_ok=True)
    for name in stories + ["cover.png"]:
        os.replace(cards / name, out_dir / name)
    for _, out, _ in reversed(made):
        os.replace(staged / Path(out).name, out)
    _env.write_json("timeline.json", {"fps": FPS, "seconds": reel["seconds"], "beats": reel["timeline"]})
    _env.write_json(report, dict(rep, made={"formats": names, "stories": bool(stories)}))
    done = [out for _, out, _ in made] + [f"out/{n}" for n in stories + ["cover.png"]]
    tail = f"; {reel['seconds']:.1f} s{' with music' if music else ' (no music track)'} -> {', '.join(done)}" if done else ""
    print(f"rendered {len(jobs)} of {len(jobs)} jobs in {rep.get('seconds', 0):.0f} s{tail}; run deliver.py for the review page")
    return 0


def strips(video, tl, out, per_beat=12):
    """12 frames across each beat tiled 6x2 (strip-<beat>.png) and the whole film at 1 fps (film-strip.png), from one decode."""
    _env.need("PIL")
    from PIL import Image, ImageDraw
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for f in list(out.glob("strip-*.png")) + list(out.glob("film-strip.png")):
        f.unlink()
    total = tl[-1]["start"] + tl[-1]["frames"]
    want = {b["id"]: [b["start"] + int((k + 0.5) * b["frames"] / per_beat) for k in range(per_beat)] for b in tl}
    film = list(range(FPS // 2, total, FPS))
    frames = sorted({f for fs in want.values() for f in fs} | set(film))
    work = out / ".cut"
    work.mkdir(exist_ok=True)
    for f in work.glob("*.png"):
        f.unlink()
    expr = work / "select.txt"
    expr.write_text("select=" + "+".join(f"eq(n\\,{f})" for f in frames) + ",scale=270:-2")
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-i", str(video), "-filter_script:v", str(expr), "-fps_mode", "passthrough",
                    str(work / "%05d.png")], check=True)
    got = sorted(work.glob("*.png"))
    at = dict(zip(frames, got))
    font = _env.pil_font(16, "text")

    def sheet(fs, cols, label):
        ims = [Image.open(at[f]).convert("RGB") for f in fs if f in at]
        if not ims:
            return None
        w, h = ims[0].size
        rows = (len(ims) + cols - 1) // cols
        im = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 22) + 30), "#111111")
        d = ImageDraw.Draw(im)
        d.text((6, 6), label, fill="#f0e6d0", font=font)
        for i, (f, x) in enumerate(zip(fs, ims)):
            ox, oy = 4 + (i % cols) * (w + 4), 30 + (i // cols) * (h + 22)
            im.paste(x, (ox, oy))
            d.text((ox + 2, oy + h + 2), f"{f / FPS:.2f} s", fill="#a09880", font=font)
        return im
    n = 0
    for b in tl:
        im = sheet(want[b["id"]], 6, f"{b['id']}  {b['bars']} bars  {b['start_s']:.2f}-{b['start_s'] + b['seconds']:.2f} s  in: {b['transition'] or '-'}")
        if im:
            im.save(out / f"strip-{b['id']}.png")
            n += 1
    im = sheet(film, 10, f"the film at 1 fps, {total / FPS:.1f} s")
    if im:
        im.save(out / "film-strip.png")
    for f in got:
        f.unlink()
    expr.unlink()
    work.rmdir()
    return n


def cmd_frames(a):
    tl = _env.read_json("timeline.json")
    film = Path(a.film)
    if not tl or not film.exists():
        sys.exit("out/film.mp4 and timeline.json are needed: run film.py render first")
    n = strips(film, tl["beats"], a.out)
    # the frames name the film they were cut from, so a critic's round is read from this film's frames and no other
    _env.write_json(Path(a.out) / "frames.json", {"film": hashlib.sha256(film.read_bytes()).hexdigest()[:16]})
    print(f"{n} beat strips + film-strip.png -> {a.out}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render", "frames"])
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the 16:9 film, the square film, the story cards)")
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="frames")
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "frames":
        return cmd_frames(a)
    # the render lock is taken before the command's first write into the run, so a refused second one changes nothing;
    # setup.py's tool probe runs before it, since no process outside run.spawn starts under the lock
    _env.tools()
    with studio.lock({"preview": "preview", "render": "film"}[a.cmd]) as run:
        return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
