#!/usr/bin/env python3
"""Movement 4: the timed cut, then the hype reel and its stills, rendered from film.json by the studio composition
(S/motion/studio).

USAGE (in a run, after storyboard.py snap and music.py master; S = this skill's folder):
    python3 S/scripts/film.py cut      # the picture: film.silent.mp4, its strips in frames/, qa/cut.json (the checks)
    python3 S/scripts/film.py render   # out/film.mp4 with the music and sound effects under it and its cover as frame 0, out/cover.png
                                       # and out/feed.png (1080x1350), and for a launch out/story-1.png, story-2.png,
                                       # story-3.png and countdown.png (1080x1920)
    python3 S/scripts/film.py frames [--film F] [--out D]   # the strips of a film (default out/film.mp4)

cut renders nothing while storyboard.py check finds anything on film.json, and exits with one line per finding.
It renders film.json silent to film.silent.mp4 (1080x1920, 30 fps, H.264 High) through render.py, writes its strips (frames/strip-<beat>.png: 12 frames across each beat; frames/film-strip.png: the whole
film at 2 fps) and runs qa.py check on it (qa/cut.json: the still seconds, the cuts per minute, the hook event, the
hook line, the board's checks; render/cut-report.json is the cut's render report). cut.json
stamps the film.json it was cut from and is written only once the picture, its strips and its checks are made and
pass; a cut removes it first. The critics read the cut (vote.py cut) before anything else renders.
render refuses until the latest critic round (critic/cut-N.json) is for this film.json, is filled in, passes every
read and ships (at the bar, vote.BAR, or with the one fix spent). It then lays the mastered music
(music.json `master`) under the cut into out/film.mp4 (AAC 192 kbps) with the board's sound effects over it (sfx.py: a
whoosh on each cut, a shutter as each photograph lands, an impact on each slammed word and on the closer, a riser into
the closer, a quiet room under it all, on the music's grid and in its key; alone when there is no music). The
stills are settled frames of the same film named by film.json `cards`: the cover (the reveal at rest, the strongest
settled frame) and, for a launch, the three stories (the hook, a beat of the build and the reveal at rest) and the
countdown card (the closer at rest) are the reel's frames in the story format, and the feed post is the closer laid for
1080x1350 (film.json `feed`) at rest; none is scaled and none is a second composition. The cover also replaces the
film's frame 0, so the feed shows it before the reel plays: the picture is encoded again with that one frame changed,
the length and the sound untouched. Every FONT_ERROR, IMAGE_ERROR and RENDER_ERROR (a lost graphics context or a shader that failed to validate among
them) lands in render-report.json, which qa.py reads: the cut's report and the latest attempt's stills; cards.json
names each still, its format, size, beat and frame. render makes everything under render/stills and moves it into out/
only once every still rendered, the reel last; render-report.json and engine.json, the gate's proof of out/, are
removed before the first move and written after the last, and a failed still leaves out/ and its proof as the last
render left them.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import sfx  # noqa: E402
import chunks  # noqa: E402
import clips  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402

FPS = 30
SILENT = Path("film.silent.mp4")
FILM = Path("out/film.mp4")
SIZES = {"reel": (1080, 1920), "story": (1080, 1920), "feed": (1080, 1350)}


def film_hash():
    p = Path("film.json")
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def load_film():
    film = _env.read_json("film.json")
    if not film or "timeline" not in film:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return film


def cmd_cut(a):
    film = load_film()
    storyboard.refuse_flagged([(Path("film.json"), film)])
    _env.need("PIL")
    _env.engine()
    # the run lock is taken before the first write and held through the strips and the checks, so a second command in
    # this run waits for the whole cut
    with chunks.lock("render", "render-report") as run:
        # cut.json certifies the picture, its strips and its checks: it and the checks go before any of them changes,
        # and cut.json comes back only once all three are made and the checks pass
        Path("cut.json").unlink(missing_ok=True)
        Path("qa/cut.json").unlink(missing_ok=True)
        t0 = time.time()
        tl = film["timeline"]
        rep = _env.render(run, [studio.video(film, SILENT, tl[-1]["start"] + tl[-1]["frames"])], "render/cut-report.json")
        seconds = round(time.time() - t0, 1)
        for f in rep.get("findings", []):
            print("finding:", f["text"][:400])
        if rep.get("failed") or not SILENT.exists():
            return 1
        n = strips(SILENT, film["timeline"], Path("frames"), run.spawn)
        where = f" on the {'graphics card' if rep.get('card') else 'CPU'} ({rep['gl']})" if rep.get("gl") else ""
        print(f"cut {film['seconds']:.1f} s in {time.time() - t0:.1f} s{where} "
              f"-> {SILENT}; {n} beat strips and film-strip.png in frames/")
        q = qa.report(qa.film_checks(SILENT, audio=False, spawn=run.spawn, report="render/cut-report.json"), "qa/cut.json")
        if q:
            print("the cut fails its checks (qa/cut.json): fix the board, snap and cut again before the critics watch it")
            return q
        _env.write_json("cut.json", {"film": film_hash(), "seconds": film["seconds"], "render_seconds": seconds, "card": rep.get("card")})
        print("next: the critics watch the cut (vote.py cut)")
        return 0


def ready():
    """Why render must wait, or None: the cut, and the critic round on it."""
    import vote
    h = film_hash()
    cut = _env.read_json("cut.json") or {}
    if not SILENT.exists() or cut.get("film") != h:
        return "film.json has no cut yet (or changed since it): run film.py cut"
    rs = vote.rounds()
    last = _env.read_json(rs[-1]) if rs else None
    if not last or last.get("film") != h:
        return "the critics have not watched this cut: run vote.py cut and fill it in"
    bad = vote.problems(last, vote.CUT_PANEL, ["film"], swap=False)
    if bad:
        return f"{rs[-1]} is not filled in: {bad[0]}"
    failed = [k for k in vote.READS if not last["reads"][k]["pass"]]
    if failed:
        return f"{rs[-1]} fails {', '.join(failed)}: {last['reads'][failed[0]]['why']}; fix the board, snap and cut again"
    if not vote.at_bar(last)[0] and len(rs) < 2:
        return "the cut is under the bar with the one fix unspent (vote.py verdict names it)"
    return None


# the encoder the cover's frame 0 is laid in with: render.py's settings, so the film reads as one encode
X264 = ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "18", "-maxrate", "12M",
        "-bufsize", "24M", "-r", str(FPS)]


# the layer each beat's form is drawn as, in the names the sound effects read
LAYER = {"title": "Title", "photo": "Photo", "clip": "Clip", "closer": "Closer"}


def fx_board(film):
    """film.json as the sound effects read a board: its tempo, and each beat's form, move, the cut into it, its start
    and end in musical beats and its words (the title's words, a photograph's label or words, the closer's last line)."""
    beats = []
    for b in film["beats"]:
        kind = LAYER.get(b["form"], b["form"].title())
        layer = {"kind": kind, "at": {"arrive": b["start"], "end": b["start"] + b["len"]}}
        if kind == "Title":
            layer["title"] = {"text": b.get("words") or ""}
        elif kind == "Closer":
            layer["signoff"] = {"text": film.get("signoff") or film.get("title") or ""}
        else:
            layer.update(label=b.get("label") or "", text=b.get("words") or "")
        beats.append({"id": b["id"], "form": b["form"], "move": b.get("move"), "transition": b.get("transition"),
                      "start": b["start"], "layers": [layer]})
    return {"id": film.get("id"), "bpm": film["bpm"], "beats": beats}


def mux(run, silent, out, seconds, board, cover=None):
    """The reel at `out`: the silent picture at `silent` with the sound effects of `board` (film.json) and the music
    master music.json names under it (sfx.py), spawned through `run`. With a `cover` still, that still replaces frame
    0 and the picture is encoded again; every other frame and the length are the picture's. Returns whether music is in
    it."""
    picture = silent
    covered = Path(out).with_name(".covered.mp4")
    if cover:
        run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(cover), "-filter_complex",
               "[1:v]scale=1080:1920,format=yuv420p[c];[0:v][c]overlay=0:0:enable='eq(n,0)':eof_action=repeat[v]",
               "-map", "[v]", *X264, "-an", str(covered)], check=True)
        picture = covered
    try:
        return sfx.mux(run.spawn, picture, out, seconds, fx_board(board), _env.read_json("music.json") or {}, _env.ffmpeg())
    finally:
        covered.unlink(missing_ok=True)


def still_board(film, beat):
    """The film with `beat`'s words at rest, the whole line as its still shows it."""
    return {**film, "beats": [{**b, "lines": b["still"]} if b["id"] == beat else b for b in film["beats"]]}


def card_jobs(film):
    jobs, rows = [], []
    for c in film["cards"]:
        b = film["feed"] if c["format"] == "feed" else {**film, "format": {**film["format"], "name": c["format"]}}
        if c.get("board") == "still":
            b = still_board(b, c["beat"])
        jobs.append({"type": "still", "composition": "Film", "props": {"board": b, "clips": clips.placed() if c["format"] != "feed" else []}, "frame": c["frame"], "out": str(Path(c["out"]).resolve())})
        rows.append({"file": c["out"], "format": c["format"], "size": list(SIZES[c["format"]]), "beat": c["beat"], "frame": c["frame"]})
    return jobs, rows


def cmd_render(a):
    film = load_film()
    why = ready()
    if why:
        sys.exit(f"not yet: {why}")
    _env.engine()
    # the run lock is taken before the first write, so a refused second render changes nothing
    with chunks.lock("render", "cards-report") as run:
        # the page that reads as delivered goes before out/ changes; deliver writes it again once its gate passes
        Path("out").mkdir(exist_ok=True)
        (Path("out") / "review.html").unlink(missing_ok=True)
        t0 = time.time()
        jobs, rows = card_jobs(film)
        staged = (Path("render") / "stills").resolve()
        jobs = [{**j, "out": str(staged / Path(j["out"]).name)} for j in jobs]
        rep = _env.render(run, jobs, "render/cards-report.json")
        _env.write_json("cards.json", {"film": film_hash(), "cards": rows})
        # everything is made in render/stills first; it reaches out/ only once every still rendered, the reel last.
        # render-report.json and engine.json are what the gate reads as proof of out/: they go before the first file
        # moves in and come back after the last, so a render killed between two moves leaves a set the gate refuses
        music = None
        if not rep.get("failed"):
            Path("render-report.json").unlink(missing_ok=True)
            Path("engine.json").unlink(missing_ok=True)
            reel = staged / FILM.name
            cover = staged / "cover.png"
            music = mux(run, SILENT, reel, film["seconds"], film, cover if cover.exists() else None)
            for j, r in zip(jobs, rows):
                os.replace(j["out"], r["file"])
            os.replace(reel, FILM)
            # the film's report is the cut's and this attempt's stills, published after the last move; a failed attempt
            # publishes nothing and leaves the last render's set and its report as they were
            cut_rep = _env.read_json("render/cut-report.json") or {}
            _env.write_json("render-report.json", {**cut_rep, "jobs": cut_rep.get("jobs", 0) + rep.get("jobs", 0),
                                                   "failed": cut_rep.get("failed", 0) + rep.get("failed", 0),
                                                   "findings": cut_rep.get("findings", []) + rep.get("findings", [])})
            cut = _env.read_json("cut.json") or {}
            _env.write_json("engine.json", {"engine": "render.py", "card": cut.get("card"), "film": film_hash(), "cut_seconds": cut.get("render_seconds"),
                                            "stills_seconds": round(time.time() - t0, 1), "jobs": 1 + len(jobs)})
        for f in rep.get("findings", []):
            print("finding:", f["text"][:400])
        if rep.get("failed"):
            print(f"{rep['failed']} of {len(jobs)} stills failed, so out/ is as the last render left it: run film.py render again")
            return 1
        print(f"film {film['seconds']:.1f} s{' with music and its sound effects' if music else ' with its sound effects (no music)'} -> {FILM}; "
              f"{len(jobs)} stills in out/ in {time.time() - t0:.1f} s")
        return 0


def strips(video, tl, out, spawn=subprocess.run, per_beat=12):
    """12 frames across each beat tiled 6x2 (strip-<beat>.png) and the whole film at 2 fps (film-strip.png), from one decode."""
    _env.need("PIL")
    from PIL import Image, ImageDraw
    out = Path(out)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    total = tl[-1]["start"] + tl[-1]["frames"]
    want = {b["id"]: [b["start"] + int((k + 0.5) * b["frames"] / per_beat) for k in range(per_beat)] for b in tl}
    film = list(range(FPS // 4, total, FPS // 2))
    frames = sorted({f for fs in want.values() for f in fs} | set(film))
    work = out / ".cut"
    work.mkdir()
    expr = work / "select.txt"
    expr.write_text("select=" + "+".join(f"eq(n\\,{f})" for f in frames) + ",scale=270:-2")
    spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(video), "-filter_script:v", str(expr), "-fps_mode", "passthrough",
                    str(work / "%05d.png")], check=True)
    at = dict(zip(frames, sorted(work.glob("*.png"))))
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
        im = sheet(want[b["id"]], 6, f"{b['id']}  {b['start_s']:.2f}-{b['start_s'] + b['seconds']:.2f} s")
        if im:
            im.save(out / f"strip-{b['id']}.png")
            n += 1
    im = sheet(film, 10, f"the film at 2 fps, {total / FPS:.1f} s")
    if im:
        im.save(out / "film-strip.png")
    shutil.rmtree(work, ignore_errors=True)
    return n


def cmd_frames(a):
    film = load_film()
    video = Path(a.film)
    if not video.exists():
        sys.exit(f"{video} is missing: run film.py cut (or render) first")
    n = strips(video, film["timeline"], a.out)
    print(f"{n} beat strips + film-strip.png -> {a.out}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cut", "render", "frames"])
    ap.add_argument("--film", default=str(FILM))
    ap.add_argument("--out", default="frames")
    a = ap.parse_args()
    _env.enter_run()
    return {"cut": cmd_cut, "render": cmd_render, "frames": cmd_frames}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
