#!/usr/bin/env python3
"""Movement 4: the film and its stills, rendered by the studio composition from the cut storyboard (build/film.json).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview   # the reel at half size, measured: build/preview/film.mp4, preview.json, strips
    python3 S/scripts/film.py render    # out/film.mp4 (1080x1920), out/carousel/01..10.png (1080x1350),
                                        # out/stories/01..03.png (1080x1920), out/strip/01..08.jpg (540x960),
                                        # build/frames/*.png

preview is what the critic's timed read and qa.py timed look at before the film renders: the cuts as planned and as
the picture shows them, cuts per minute, the luma line and its quiet seconds, and the hook event's frame. It prints
every cut the picture shows that the storyboard does not plan, beside the board's sound cue nearest it: each one is a
move that reads as a cut, answered before the critic reads.
render refuses until qa.py timed has passed this cut (build/qa/timed.json names film.json's hash). It renders the
reel, lays the mastered music (the master build/music.json names) under it at AAC 192 kbps, and takes every still from the
film's own frames at rest, so the cards carry the film's grade and type:

  stories   01 the hook's window over the months' photographs, 02 the story's peak open with its line (the middle
            month's when the year has no peak), 03 the closer's wall at its stop
  carousel  01 the hook, 02-09 eight months open with their lines (spread evenly through the year, the peak among
            them, in calendar order), 10 the closer's wall; each a 1080x1350 window of the reel's frame around the
            type area
  strip     01 the hook, 02-07 six months open with their lines (spread evenly through the year, the peak among
            them, in calendar order), 08 the closer's wall; each the reel's frame at half size, the review page's strip
            beside the player, and 01 its poster

The film, the stories, the carousel and the strip are made in out.part/ beside out/ and move into out/ by rename once
every one of them is made, the reel last; a card or frame the new set does not make leaves after. The page that says
out/ is ready to post (out/review.html, which deliver writes) and the render report qa.py and vote.py cut read
(build/render/film-report.json: every finding the composition logged, and the hash of the cut out/ shows) both name
out/, so they go before the first file moves in, and the report is published after the reel; the render works on its
own report under a staging name until then. A render stopped between two files, or a retry stopped before its first
file moves, leaves a set the gate refuses. build/frames/ holds the hook, an
ordinary month, the story's peak and the closer at half size for the critics. preview.json names the cut its film
shows, so it goes before the preview renders and comes back after the measure.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import studio  # noqa: E402

OUT = Path("../out")
CARD = (1080, 1350)
STRIP = (540, 960)
# where a carousel card's window sits on the reel's frame: the reel's type area (270 to 1250 px) with room around it
CARD_TOP = 135


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f, _env.read_json(f["boards"]["reel"])


def month_rests(board):
    """Each month's frame at rest: its halves open, its line said, the camera not yet pulling back (the storyboard's
    rest frame)."""
    pulse = 30 * 60 / board["bpm"]
    return {m["id"]: round((m["at"]["pull"][0] - 0.1) * pulse) for m in board["year"]["months"]}


def cmd_preview(a, run):
    f, board = film()
    d = Path("preview")
    d.mkdir(exist_ok=True)
    (d / "preview.json").unlink(missing_ok=True)
    rep = studio.render([studio.video(board, d / "film.mp4", f["frames"], scale=0.5)], "preview", run)
    if rep["failed"]:
        sys.exit("the preview render failed; see build/render/preview.log")
    m = studio.measure(d / "film.mp4", f["cuts"], f["hook_frame"], run=run)
    m.update(hash=f["hash"], style=f["style"], findings=[x["text"][:200] for x in rep["findings"]])
    _env.write_json(d / "preview.json", m)
    print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_event_frame']}, "
          f"seconds under 0.5: {m['seconds_under_half']} -> build/{d / 'preview.json'}, strip {m['strip2']}")
    sec = 60 / board["bpm"]
    cues = [(c["at"] * sec, f"{c['beat']}, {c['what']}") for c in board.get("sound") or []]
    for t in m["extra_scene_cuts"]:
        at, what = min(cues, key=lambda c: abs(c[0] - t), default=(t, "no sound cue"))
        print(f"  unplanned cut {t:.2f} s: nearest cue {what} ({t - at:+.2f} s)")
    return 0


def mux(run, silent, out, seconds):
    master = (_env.read_json("music.json") or {}).get("master")
    if master:
        run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart",
                   str(out)], check=True)
    else:
        shutil.copyfile(silent, out)
    return bool(master)


def card(src, dst):
    """A carousel card: the 1080x1350 window of a reel frame around its type area."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    im.crop((0, CARD_TOP, CARD[0], CARD_TOP + CARD[1])).save(dst, "PNG")


def strip_frame(src, dst):
    """A frame of the review page's strip: a reel frame at half size."""
    from PIL import Image
    Image.open(src).convert("RGB").resize(STRIP, Image.LANCZOS).save(dst, "JPEG", quality=88)


def spread(ms, n, peak):
    """n of the months, spread evenly through the year with the peak among them, in calendar order; every month when
    the year has n or fewer."""
    pick = [ms[round(i * (len(ms) - 1) / (n - 1))] for i in range(n)] if len(ms) > n else list(ms)
    if peak not in pick:
        pick[min(range(len(pick)), key=lambda i: abs(pick[i]["month"] - peak["month"]))] = peak
    return sorted(pick, key=lambda m: m["month"])


def publish(part, rep):
    """Moves every file made in `part` into out/ by rename, the reel last, with the review page and the render report
    (`rep`) gone while they move; then the report comes back and the cards and frames of out/ the new set does not
    make leave."""
    made = {p.relative_to(part) for p in part.rglob("*") if p.is_file()}
    report = Path("render/film-report.json")
    (OUT / "review.html").unlink(missing_ok=True)
    report.unlink(missing_ok=True)
    for rel in sorted(made, key=lambda r: (r == Path("film.mp4"), str(r))):
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
        os.replace(part / rel, OUT / rel)
    _env.write_json(report, rep)
    for d in ("carousel", "stories", "strip"):
        for p in (OUT / d).glob("*.*"):
            if p.relative_to(OUT) not in made:
                p.unlink()
    shutil.rmtree(part)


def cmd_render(a, run):
    f, board = film()
    gate = _env.read_json("qa/timed.json") or {}
    if gate.get("hash") != f["hash"] or not gate.get("pass"):
        sys.exit("qa.py timed has not passed this cut: run film.py preview, vote.py timed (the critic's timed read) and qa.py timed first")
    y = board["year"]
    rests = f["rests"]["reel"]
    months = month_rests(board)
    ms = y["months"]
    peak = next((m for m in ms if m["peak"]), ms[len(ms) // 2])
    eight = spread(ms, 8, peak)
    part = OUT.with_name("out.part")
    shutil.rmtree(part, ignore_errors=True)
    for d in (part / "carousel", part / "stories", part / "strip", Path("render/silent"), Path("render/stills"), Path("frames")):
        d.mkdir(parents=True, exist_ok=True)
    stills = {"hook": rests["hook"], "closer": rests["closer"], **months}
    jobs = [studio.video(board, Path("render/silent/film.mp4"), f["frames"])]
    jobs += [studio.still(board, fr, Path("render/stills") / f"{k}.png") for k, fr in stills.items()]
    jobs += [studio.still(board, fr, Path("frames") / f"{k}.png", scale=0.5) for k, fr in rests.items()]
    rep = studio.render(jobs, "film", run)
    if rep["failed"]:
        sys.exit("a render job failed; see build/render/film.log and build/render/film-report.part.json")
    music = mux(run, Path("render/silent/film.mp4"), part / "film.mp4", f["seconds"])
    S = Path("render/stills")
    for i, k in enumerate(("hook", peak["id"], "closer"), 1):
        shutil.copyfile(S / f"{k}.png", part / "stories" / f"{i:02d}-{k}.png")
    for i, k in enumerate(["hook", *[m["id"] for m in eight], "closer"], 1):
        card(S / f"{k}.png", part / "carousel" / f"{i:02d}-{k}.png")
    for i, k in enumerate(["hook", *[m["id"] for m in spread(ms, 6, peak)], "closer"], 1):
        strip_frame(S / f"{k}.png", part / "strip" / f"{i:02d}-{k}.jpg")
    publish(part, dict(rep, hash=f["hash"]))
    print("wrote out/film.mp4, out/carousel/ (10 cards), out/stories/ (3 cards), out/strip/ (8 frames) and build/frames/"
          + ("" if music else " (music.json names no master: the film is silent)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    a = ap.parse_args()
    _env.need("PIL")
    _env.enter_build()
    # the render lock is taken before the command's first write into the run, so a refused second one changes nothing
    with studio.lock({"preview": "preview", "render": "film"}[a.cmd]) as run:
        return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
