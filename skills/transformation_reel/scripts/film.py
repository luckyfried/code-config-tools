#!/usr/bin/env python3
"""Movement 4, the film: the storyboard timed and looked at before anything is finished, then rendered as the reel
with its cover and story cards, and in the other formats only when the person asked for them.

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/film.py draft              # the timed cut at half size with its sound, its strips and its figures
    python3 S/scripts/film.py render             # the film in 9:16, its cover, story cards and then/now, into RUN/cut/
    python3 S/scripts/film.py render --also landscape square
                                                 # and, each only when the person asked for it: the film in 16:9, the
                                                 # film square

Both refuse a board drafted from another taste.json than the one in the run (the board's facts `taste`): a change
to the taste reaches the film only through storyboard.py draft.

draft renders RUN/film.json's board (storyboard.py snap) at half size to RUN/draft/film.mp4 with the mastered music
under it, and writes what the critic's timing round reads beside the storyboard: RUN/frames/strip-<beat>.png (12
frames across each beat), RUN/frames/film-strip.png (one frame a second), RUN/timeline.json (each beat's start and
length, every move from one card to the next, the stop, the rest moments) and RUN/draft/check.json (qa.py's figures
for the cut: its length, its cuts, the rest line, the hook, the sound cues and the last one). It also writes the
board's six shot requests to RUN/clips/requests.json (clips.py), so they are there for the agent before the render.

render refuses until RUN/critic/timing.json passes for this board. It renders the board laid out for the reel, cut/film.mp4 (1080x1920), and for each format
--also names, cut/film-square.mp4 (1080x1080) and cut/film-16x9.mp4 (1920x1080), 30 fps, H.264 High, with the mastered
music (the master RUN/music.json names, AAC 192 kbps) under each; cut/then-now.png (then_now: day one and the latest
as two prints side by side on the film's wall, their words for the span over them, each date under its print, set in
the style's faces and colors); cut/cover.png, the reel's frame at the closer's rest moment (the poster the review page and the
post use); and the story cards cut/stories/01-hook.png, 02-dense.png and 03-closer.png, the reel's own frames at the
board's rest moments. Everything is made under RUN/render/ first; once all of it is, cut/ is
replaced whole by it, cut/film.mp4 last, and RUN/render/report.json records what the render made (`made`: the formats). Then render runs qa.py check on the new cut, so RUN/qa/check.json always describes the
cut in cut/, and exits nonzero when a check fails. Render first conforms every clip saved in RUN/clips/ (clips.py
normalize), and each plays on its photograph's card. Once the run's film is delivered (RUN/out/film.mp4),
draft and render start the next run first and carry this one's inputs into it, so no render overwrites a delivered
film; before that a render, the one fix's included, replaces the run's cut, and a render stopped before its report is
finished in the same run.
RUN/render/report.json, which qa.py and deliver.py read, is the report of the films in cut/: render removes it
before cut/ changes and writes it after the last file, so a render stopped between two files leaves no report and
the gate refuses. A failed render prints every FONT_ERROR, IMAGE_ERROR and render error and leaves cut/ and its
report as they were. The render's log is RUN/render/<name>.log.

The film is drawn by the built composition (S/motion/dist) in a windowless Chromium, one frame at a time, and encoded
with ffmpeg (scripts/render.py): on the graphics card when there is one it can draw on, on the processor otherwise. A
job's attempt that fails (a browser that stops answering, a lost graphics context, a flat render) runs again in a fresh
browser, three attempts in all; a frame that is not ready in 30 s stops the render and names the frame.

Every film renders in chunks kept in the run (scripts/chunks.py), RUN/render/chunks/<name>/<key>/<first>-<last>.mp4,
and is joined from them once every chunk is whole. A chunk is published only once the renderer's checks pass. An interrupted draft or render resumes when
the same command runs again: chunks that probe whole are kept and only the rest render. The key covers the job, the
run's public folder and the kit's composition source, so a changed cut renders into a folder of its own and a cut put
back finds its chunks again. One render runs in a run at a time: another one started meanwhile exits nonzero and names
the running one's log. Every process a draft or a render starts holds the run's lock with it.
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
import chunks  # noqa: E402

FPS = 30
FORMATS = {"reel": "film.mp4", "square": "film-square.mp4", "landscape": "film-16x9.mp4"}
ALSO = ("landscape", "square")
# the renderer, and the built composition it draws (scripts/dev/build_motion.py builds it from motion/)
RENDERER = _env.SKILL / "scripts" / "render.py"
DIST = _env.SKILL / "motion" / "dist"
STORIES = (("hook", "01-hook.png"), ("dense", "02-dense.png"), ("closer", "03-closer.png"))


# ------------------------------------------------------------------ where it renders
def held(name):
    """The run's render lock named `name` (chunks.lock), taken before the command's first write into the run. The tools
    (setup.py) resolve first, so while it is held every process starts through the lock's run.spawn, which hands the
    lock to the child."""
    _env.tools()
    return chunks.lock(_env.b("render"), name)


def render_jobs(run, jobs):
    """`jobs` rendered through chunks.render under the run's lock `run` (chunks.lock): every video job in chunks kept in
    RUN/render/chunks/<name>/ and joined into its `out` once they are whole, every still at its `out`. Returns the report;
    render.py's log is RUN/render/<name>.log and its own report RUN/render/<name>-chunks.json."""
    t = _env.tools()
    if not t.get("chromium") or not t.get("dist"):
        sys.exit(f"the film cannot render here: python3 {_env.SKILL / 'scripts' / 'setup.py'} says what is missing")
    public = _env.b("public").resolve()

    def invoke(pending, spawn):
        jf, report = run.render_dir / f"{run.name}.jobs.json", run.render_dir / f"{run.name}-chunks.json"
        report.unlink(missing_ok=True)
        _env.write_json(jf, {"publicDir": str(public), "report": str(report), "jobs": pending, "ffmpeg": _env.ffmpeg(),
                             "chromium": t["chromium"]})
        with open(run.render_dir / f"{run.name}.log", "w") as f:
            code = spawn([sys.executable, str(RENDERER), "--jobs", str(jf.resolve())], env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1"),
                         stdout=f, stderr=subprocess.STDOUT).returncode
        return _env.read_json(report) or chunks.unreported(pending, code, run.render_dir / f"{run.name}.log")

    rep = chunks.render(run, jobs, public, [DIST], _env.ffmpeg(), _env.ffprobe(), invoke)
    rep["device"] = {True: "card", False: "processor"}.get(rep.get("card"))
    return rep


def where(rep):
    """Where the render drew, as a summary says it: ` on the graphics card (angle-egl)`, ` on the CPU (swangle)`, or
    nothing when it drew nothing."""
    return f" on the {'graphics card' if rep.get('card') else 'CPU'} ({rep['gl']})" if rep.get("gl") else ""


# ------------------------------------------------------------------ the board in time
def props(board):
    """The composition's input: the board and the generated clips placed on its cards."""
    import clips
    return {"board": board, "clips": clips.placed()}


def stop_frame(board):
    """The frame where picture and music stop together (the board's stop cue)."""
    stop = next(c["at"] for c in board["sound"] if c["kind"] == "stop")
    return round(stop * board["film"]["pulse"])


def timeline(board):
    """Each beat's start and length in frames, every move from one card to the next (a beat boundary: the camera
    leaves the card it held), the stop and the rest moments."""
    import storyboard
    ss, total = storyboard.starts(board)
    beats = [{"id": b["id"], "start": s, "frames": b["frames"]} for s, b in zip(ss, board["beats"])]
    return {"fps": FPS, "frames": total, "seconds": round(total / FPS, 3), "style": board["style"], "format": board["format"]["name"],
            "width": board["format"]["width"], "height": board["format"]["height"], "beats": beats, "cuts": ss[1:],
            "hook_frame": storyboard.hook_frame(board), "stop_frame": stop_frame(board), "stills": board.get("stills", {})}


def board_sha(board):
    import json
    return hashlib.sha256(json.dumps(board, sort_keys=True).encode()).hexdigest()[:16]


def chosen():
    import storyboard
    film = _env.read_json(_env.b("film.json"))
    if not film:
        sys.exit("RUN/film.json is missing: run storyboard.py snap first")
    drafted = (storyboard.lay_out(film["board"]).get("facts") or {}).get("taste")
    if drafted != storyboard.taste_sha():
        sys.exit("RUN/taste.json changed after the storyboard was drafted, so the board does not carry it: run storyboard.py draft, "
                 "then the vote, snap and film.py draft again")
    return film


def then_now(board, rows, dst):
    """The then/now image at `dst`, 1080x1080: day one and the latest as two prints side by side on the film's wall,
    each photograph at its own proportions (as the film shows it) in its paper border over its shadow, their words
    for the span over them in the words' color, each date under its print, all of it in the board's style card's faces,
    case and colors, so it posts as a frame of the film."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
    import compose
    from tones import drive
    film = board["film"]
    col = film["colors"]
    compose.use(board["style"])
    S, M, GAP, BORDER = 1080, 64, 40, 14
    font = lambda face, size: ImageFont.truetype(str(_env.SKILL / compose.face_of(face)["file"]), size)  # noqa: E731
    im = Image.new("RGB", (S, S), col["ground"])
    d = ImageDraw.Draw(im)
    span = compose.cased(film["closer"]["span"], "display")
    size = 120
    while size > 40 and font("display", size).getlength(span) > S - 2 * M:
        size -= 2
    slot_w = (S - 2 * M - GAP) // 2 - 2 * BORDER
    sized = []
    for r in (rows[0], rows[-1]):
        ph = ImageOps.exif_transpose(Image.open(_env.b("public", r["photo"]))).convert("RGB")
        own = ph.width / ph.height
        a = min(drive.ASPECT[1], max(drive.ASPECT[0], own))
        u0, v0, u1, v1 = drive.window(own, a, 1.0, r.get("focal") or [0.5, 0.5])
        ph = ph.crop((round(u0 * ph.width), round((1 - v1) * ph.height), round(u1 * ph.width), round((1 - v0) * ph.height)))
        w, h = (slot_w, round(slot_w / a)) if a >= slot_w / 600 else (round(600 * a), 600)
        sized.append((ph, w, h, r))
    # the span, the two prints standing on one line and their dates, as one block in the middle of the square
    tallest = max(h for _, _, h, _ in sized) + 2 * BORDER
    block = size * 0.7 + 72 + tallest + 64
    base = round((S - block) / 2 + size * 0.7)
    d.text((S / 2, base), span, font=font("display", size), fill=col["words"], anchor="ms")
    floor = base + 72 + tallest
    prints = []
    for i, (ph, w, h, r) in enumerate(sized):
        x0 = M + i * (slot_w + 2 * BORDER + GAP) + (slot_w - w) // 2
        prints.append((ph.resize((w, h), Image.LANCZOS), x0, floor - h - 2 * BORDER, w, h, r))
    shadow = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(shadow)
    for _, x0, y0, w, h, _ in prints:
        sd.rectangle([x0 + 10, y0 + 18, x0 + w + 2 * BORDER + 10, y0 + h + 2 * BORDER + 18], fill=150)
    dark = tuple(round(int(col["ground"][k:k + 2], 16) * 0.12) for k in (1, 3, 5))
    im.paste(Image.new("RGB", (S, S), dark), (0, 0), shadow.filter(ImageFilter.GaussianBlur(16)))
    for ph, x0, y0, w, h, r in prints:
        d.rectangle([x0, y0, x0 + w + 2 * BORDER - 1, y0 + h + 2 * BORDER - 1], fill=col["paper"])
        im.paste(ph, (x0 + BORDER, y0 + BORDER))
        d.text((x0 + BORDER + w / 2, floor + 56), compose.cased(drive.short(r["date"]), "text"), font=font("text", 40), fill=col["line"], anchor="ms")
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def grab(run, video, sheets):
    """Contact sheets of `video` in one pass over it, under the run's lock `run`: each sheet (frames, dst, cols, size)
    is its frames tiled `cols` to a row at `size`, written to dst."""
    graph, outs = [f"[0:v]split={len(sheets)}" + "".join(f"[in{i}]" for i in range(len(sheets)))], []
    for i, (frames, dst, cols, size) in enumerate(sheets):
        pick = "+".join(f"eq(n\\,{f})" for f in frames)
        rows = -(-len(frames) // cols)
        graph.append(f"[in{i}]select='{pick}',scale={size}:flags=area,tile={cols}x{rows}:padding=4:color=black[out{i}]")
        outs += ["-map", f"[out{i}]", "-frames:v", "1", "-fps_mode", "passthrough", "-update", "1", str(dst)]
    run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(video), "-filter_complex", ";".join(graph), *outs], check=True)


def cmd_draft(a, run):
    import qa
    import storyboard
    film = chosen()
    board = storyboard.lay_out(film["board"])
    # draft/check.json is the draft's completion (vote.py timing reads it): it goes before the draft's media change
    _env.b("draft", "check.json").unlink(missing_ok=True)
    tl = timeline(board)
    _env.write_json(_env.b("timeline.json"), tl)
    import clips
    reqs = clips.write_requests(board)
    print(f"{len(reqs)} shot requests -> {_env.b('clips', 'requests.json')} (clips.py list prints them)")
    silent = _env.b("draft", "silent.mp4")
    out = _env.b("draft", "film.mp4")
    for d in (_env.b("draft"), _env.b("frames")):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    t0 = time.time()
    rep = render_jobs(run, [{"type": "video", "composition": "Film", "props": props(board), "frames": tl["frames"], "out": str(silent.resolve()), "scale": 0.5}])
    if rep.get("failed"):
        print("the draft did not render: " + "; ".join(f["text"][:200] for f in rep.get("findings", [])[:3]))
        return 1
    mux(run, silent, out, tl["seconds"])
    t1 = time.time()
    sheets = [([b["start"] + min(b["frames"] - 1, round((i + 0.5) * b["frames"] / 12)) for i in range(12)], _env.b("frames", f"strip-{b['id']}.png"), 12, "180:320")
              for b in tl["beats"]]
    grab(run, out, sheets + [(list(range(0, tl["frames"], FPS)), _env.b("frames", "film-strip.png"), 10, "144:256")])
    strips = time.time() - t1
    m = qa.measure(out, tl, board, run)
    m["board"] = film["board"]
    m["board_sha"] = board_sha(board)
    _env.write_json(_env.b("draft", "check.json"), m)
    print(f"draft {film['board']}: {tl['seconds']:.1f} s in {time.time() - t0:.0f} s{where(rep)}; " + qa.summary(m))
    print(f"strips in {strips:.1f} s -> {_env.b('frames')}/strip-<beat>.png and film-strip.png; figures -> {_env.b('draft', 'check.json')}; next: vote.py timing")
    return 0


def mux(run, silent, out, seconds):
    """The silent film with the master RUN/music.json names under it, at `out`, under the run's lock `run`."""
    ff = _env.ffmpeg()
    name = (_env.read_json(_env.b("music.json")) or {}).get("master")
    master = _env.b("music", name) if name else None
    if master:
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(out)]
    else:
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-c:v", "copy", "-movflags", "+faststart", str(out)]
    run.spawn(cmd, check=True)
    return bool(master)


def cmd_render(a, run):
    import qa
    import storyboard
    film = chosen()
    style = film["board"]
    reel = storyboard.lay_out(style)
    timing = _env.read_json(_env.b("critic", "timing.json")) or {}
    if not timing.get("pass") or timing.get("board_sha") != board_sha(reel):
        sys.exit("the timed cut has no passing timing round for this board: run film.py draft, then vote.py timing, and render once it passes")
    import clips
    clips.normalize(reel)
    also = getattr(a, "also", None) or ()
    fmts = [f for f in FORMATS if f == "reel" or f in also]
    boards = {f: storyboard.lay_out(style, f) for f in fmts}
    # every deliverable is made under render/ and moves into cut/ only once all of them are, cut/film.mp4 last, and
    # render/report.json, which with the reel marks a finished run (_env.open_run), follows the last of them
    render = _env.b("render")
    render.mkdir(parents=True, exist_ok=True)
    jobs = [{"type": "video", "composition": "Film", "props": props(boards[f]), "frames": storyboard.starts(boards[f])[1],
             "out": str((render / f"silent-{f}.mp4").resolve())} for f in fmts]
    # the cover is the reel's own frame at the closer's rest moment, the whole wall with their words on it
    stills = [(reel, reel["stills"]["closer"], "cover.png")]
    stills += [(reel, reel["stills"][key], f"stories/{name}") for key, name in STORIES]
    jobs += [{"type": "still", "composition": "Film", "props": props(b), "frame": f, "out": str((render / "stills" / rel).resolve())} for b, f, rel in stills]
    _env.write_json(_env.b("timeline.json"), timeline(reel))
    t0 = time.time()
    rep = render_jobs(run, jobs)
    secs = timeline(reel)["seconds"]
    music = None
    for f in rep.get("findings", []):
        print("finding:", f["text"][:300])
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {time.time() - t0:.0f} s{where(rep)}")
    if rep.get("failed"):
        return 1
    staged = []
    for f in fmts:
        staged.append((render / f"film-{f}.mp4", FORMATS[f]))
        music = mux(run, render / f"silent-{f}.mp4", staged[-1][0], secs)
    staged += [(render / "stills" / rel, rel) for _, _, rel in stills]
    then_now(boards.get("square") or storyboard.lay_out(style, "square"), storyboard.measured(), render / "stills" / "then-now.png")
    staged.append((render / "stills" / "then-now.png", "then-now.png"))
    report = render / "report.json"
    report.unlink(missing_ok=True)
    shutil.rmtree(_env.cut(), ignore_errors=True)
    for src, rel in sorted(staged, key=lambda m: m[1] == FORMATS["reel"]):
        _env.cut(rel).parent.mkdir(parents=True, exist_ok=True)
        os.replace(src, _env.cut(rel))
    _env.write_json(report, {**rep, "made": {"formats": fmts}})
    print(f"the cut, {secs:.1f} s{' with music' if music else ' without music'} -> {_env.cut()}/; checking it (qa.py check):")
    res = qa.Checks()
    return qa.report(res, "check.json", qa.film_checks(res, run))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "render"])
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the reel (the 16:9 film, the square film, the story cards)")
    a = ap.parse_args()
    _env.open_run()
    with held({"draft": "draft", "render": "report"}[a.cmd]) as run:
        return {"draft": cmd_draft, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
