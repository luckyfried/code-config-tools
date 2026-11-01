#!/usr/bin/env python3
"""Movement 4: the winning storyboard rendered by the studio compositions (S/motion/studio, built into S/motion/dist)
into the deliverables.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview     # the reel at half size with its sound, measured: preview/film.mp4, preview.json
    python3 S/scripts/film.py render --proof
                                          # the proof, every round before deliver: every video at half size beside
                                          # the full-size ones (out/proof.mp4, out/proof-series.mp4,
                                          # out/cards/proof-NN-story.mp4), the stills as the full render makes them
    python3 S/scripts/film.py render      # the deliver render, full size: out/film.mp4, out/cover.png, out/cards/ (and
                                          # out/series.mp4 when asked), then qa.py check

preview is what the critic's timed read (vote.py timed) watches before the film renders: the reel with its mastered
sound, its cuts as planned and as the picture shows them, the luma line and its quiet seconds, the hook frame, and the
1 and 2 fps strips. render refuses a board drafted from another taste.json than the run's (the board's `taste`), so a
change to the taste always reaches the film, and refuses until critic/timed.json holds the reads made for this board
(its hash); it prints any read that did not pass and renders the board all the same. It renders the storyboard of the
look that won the vote (winner.json `board`), one format (1080x1920 at 30 fps), in one bundle and one browser:
  out/film.mp4              the reel (the Reel composition, motion/studio/climb): their month as a walk through
                            its moments, as long as the board's reel, with its sound effects under the music, picture and music stopping
                            together on the board's stop and holding to the end
  out/series.mp4            only when the person asked for the cards as one video (the board's ask.series): the whole
                            series, every card in order (the Film composition, motion/studio/story), each card one
                            camera over one moment, with its sound effects under the music
  out/cards/NN-story.mp4    each card as its own 15 s story: the series' render and its effects cut at the card's
                            bounds, under the music
  out/cards/NN-story.png    each card's still: the card at its `still` beat, in its last whole-frame hold
  out/cover.png             the reel's cover: the closer's wall, every post of the month in its cell with the month's
                            line landed under it, the frame before the style's closing page comes over it
One card a moment, in date order, three or four of them as taste.json picks them.
Every video's sound is made one way: the music (music.py make), cut from the video's first frame by music.py
`master` (the music alone at -14 LUFS), and the board's sound effects (the reel's `fx`, every card's on the series'
clock: compose/sound.py), laid by sfx.mux on the music's grid and in its key and mastered with the music once: one gain
onto -14 LUFS, one limiter, one AAC encode without noise substitution, so the true peak stays under -1.5 dBTP. The reel's
music stops on its stop, and every card and the series fade over their last 1.2 s. render writes the reel's effect count
into the storyboard's Mixed line, and the music's energy under the reel, one number a frame, into music/energy.json.
Both commands render each video in chunks kept in the run (preview/chunks/, render/chunks/; 60 frames each without an
NVIDIA card, one per video with one): a render that is cut off resumes when the same command runs again, rendering
only the chunks still missing, and render.log in the same folder shows its progress. render makes every deliverable in
render/out/ and moves them into out/ by rename once all of them are made, the reel last, so a render cut off partway
leaves out/ as it was. Just before the first of them moves, render removes out/review.html, render-report.json,
cards.json and film.json, and writes them back (film.json last) once every file is in; preview removes preview.json
before it renders and writes it once the preview is measured.
Every finding and render error the compositions print lands in render-report.json once the render's files are all
in out/; a failed render leaves out/ and the records beside it as they were, and the renderer's own report stays in
render/render-report.json (preview/render-report.json for the preview); timeline.json carries each video's
figures (studio.measure) and timeline/<name>-strip.png and -strip2.png its 1 and 2 fps strips; cards.json names
every card's files; engine.json names the renderer and the compositions. Once the files are in, render runs qa.py check, so qa/check.json
describes the film out/ holds after every render.
--proof renders every video at half size (proof.py) under its proof name beside the full-size one in out/, never over
it, and the stills (the cards' stills, the cover) as the full render makes them; render-report.json's `scale` says
which render it was, and cards.json and timeline.json name the proof's videos. A full render takes the proof's videos
out of out/ and out/cards/, so out/proof.mp4 is there only while the newest render is the proof, which qa.py check and
vote.py cut read and deliver.py refuses.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import chunks  # noqa: E402
import music  # noqa: E402
import proof  # noqa: E402
import qa  # noqa: E402
import sfx  # noqa: E402
import studio  # noqa: E402

def card_start(board, ci):
    return sum(studio.card_frames(board, c) for c in board["beats"][:ci])


def still_frame(board, ci):
    """The series frame of card ci's still: the card's `still` beat."""
    card = board["beats"][ci]
    return card_start(board, ci) + min(studio.card_frames(board, card) - 1, studio.jround(card["still"] * studio.pulse(board)))


def series_fx(board, at=0):
    """The series' effects board on the clock of a video that starts at series frame `at`: every card's (compose/sound.py)
    beats offset by the beats of the cards before it, less `at`, so every card cut from the series plays the same effects
    at the same frames."""
    p = studio.pulse(board)

    def shifted(b, off):
        ly = b["layers"][0]
        moved = {k: round(v + off, 4) for k, v in ly["at"].items()}
        slam = {"slam": [round(ly["slam"][0] + off, 4), ly["slam"][1]]} if "slam" in ly else {}
        return {**b, "start": round(b["start"] + off, 4), "layers": [{**ly, "at": moved, **slam}]}

    beats = [shifted(b, (card_start(board, i) - at) / p) for i, c in enumerate(board["beats"])
             for b in (c.get("fx") or {}).get("beats", [])]
    return {"id": f"{board['id']}-series", "bpm": board["bpm"], "beats": beats}


def stop_of(r):
    """The reel's stop, in seconds from its first frame: where picture and sound stop together (its `stop` cue)."""
    return next((c["at"] * 60 / r["bpm"] for c in r.get("sound") or [] if c["kind"] == "stop"), None)


def effects_count(fx):
    """How many effects an effects board lays."""
    return len(sfx.events(fx)[0]) if fx else 0


def won(run):
    """The look that won the vote: winner.json's `board`."""
    w = (_env.read_json(run / "winner.json") or {}).get("board")
    if not w:
        sys.exit("no winner: the boards have not passed the vote; run vote.py ballot, fill it in, then vote.py tally")
    return w


def board_of(run):
    f = run / "storyboards" / won(run) / "storyboard.json"
    board = _env.read_json(f)
    if not board:
        sys.exit(f"{f} is missing: run storyboard.py draft")
    return board


def bed(run):
    m = _env.read_json(run / "music.json") or {}
    if not m.get("file") or not Path(m["file"]).exists():
        sys.exit("no music: run music.py make first")
    return Path(m["file"])


def sound(silent, wav, seconds, out, fx, record, start=0.0, stop=None, energy=None, fps=30, spawn=subprocess.run):
    """The silent render with its sound: the music (music.master: the bed from `start`, stopping at `stop` seconds) and
    the effects board `fx` (its beats on the render's clock) laid and mastered together by sfx.mux under the music
    `record` (music.json) describes, put at `out` by rename once it is whole, the music's master left beside it
    (<name>.wav); with `energy`, the master's energy written there, one number a frame at `fps`, where the shared layer
    reads it. Every process starts through `spawn`."""
    out = Path(out)
    master, part = out.with_suffix(".wav"), out.with_name(f"{out.stem}.part.mp4")
    music.master(wav, seconds, master, start=start, stop=stop, spawn=spawn)
    if energy:
        sfx.energy(_env.ffmpeg(), master, fps, energy)
    sfx.mux(spawn, silent, part, seconds, fx, dict(record or {}, master=str(master)), _env.ffmpeg())
    os.replace(part, out)


# a card is re-encoded the way the render encodes: NVENC at constant quality 14 on the NVIDIA card, x264 crf 17 without it
# (chunks.GPU, which VS_GPU=0 turns off), both under the renderer's ceiling of 12 Mbit/s over a 24 Mbit buffer
ENCODE = (["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "14", "-b:v", "0", "-maxrate", "12M", "-bufsize", "24M"]
          if chunks.GPU else ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-maxrate", "12M", "-bufsize", "24M"])


def cut(series, start, seconds, out, spawn=subprocess.run):
    """seconds of the silent series from start, re-encoded so the cut lands on the frame."""
    spawn([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(series), "-t", f"{seconds:.3f}", "-an",
           *ENCODE, "-profile:v", "high", "-pix_fmt", "yuv420p", str(out)], check=True)


def report(rep, work, scale=1):
    """The render's report at `scale` (1, or proof.SCALE for the proof); a failed render exits, its renderer's report
    left in `work`."""
    found = studio.findings(rep)
    record = {"failed": rep.get("failed"), "exit": rep.get("exit"), "seconds": rep.get("seconds"), "findings": found,
              "lines": studio.lines(found), "scale": scale}
    if rep.get("failed") or rep.get("exit"):
        print("\n".join(studio.lines(found)[:20]))
        sys.exit(f"the render failed ({rep.get('failed')} jobs); see {work / 'render.log'}")
    return record


def cmd_preview(a):
    run = _env.writable_run()
    board = board_of(run)
    r = board["reel"]
    d = run / "preview"
    with studio.lock(d, "render") as hold:
        # preview.json vouches for the files beside it, so it goes before they change and comes back once they are measured
        (d / "preview.json").unlink(missing_ok=True)
        job = {"type": "video", "composition": "Reel", "props": studio.props(board, run), "scale": 0.5, "frames": r["frames"],
               "out": str((d / "film-silent.mp4").resolve())}
        rep = studio.render([job], d, "render", board=board, run=run, hold=hold)
        found = report(rep, d)["findings"]
        seconds = r["frames"] / r["fps"]
        sound(d / "film-silent.mp4", bed(run), seconds, d / "film.mp4", r["fx"], _env.read_json(run / "music.json"),
              stop=stop_of(r), spawn=hold.spawn)
        m = studio.measure(d / "film.mp4", r["cuts"], strips=d, spawn=hold.spawn)
        lufs = qa.loudness(d / "film.mp4", spawn=hold.spawn)
        m.update(hash=studio.board_hash(board), lufs=None if lufs is None else round(lufs, 1), findings=studio.lines(found))
        _env.write_json(d / "preview.json", m)
        print(f"preview: {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {m['hook_frame']}, "
              f"seconds under 0.5: {m['seconds_under_half']}, {m['lufs']} LUFS -> {d / 'preview.json'}; strips {m['strip']}, {m['strip2']}")
        return 0


def cmd_render(a):
    run = _env.writable_run()
    board = board_of(run)
    h = studio.board_hash(board)
    if board.get("taste") != studio.taste_hash(run):
        sys.exit("taste.json changed since the board was drafted: run storyboard.py draft, check, sheets, the vote and "
                 "movement 4 again, so the change reaches the film")
    timed = _env.read_json(run / "critic" / "timed.json") or {}
    if timed.get("hash") != h or timed.get("pass") is None:
        sys.exit("the timed read is not made for this board: run film.py preview and vote.py timed, and write the four reads first")
    unmet = [k for k, v in (timed.get("reads") or {}).items() if (v or {}).get("pass") is not True]
    if unmet:
        print(f"the timed read: {', '.join(f'{k} ' + ('fail' if timed['reads'][k].get('pass') is False else str(timed['reads'][k].get('pass'))) for k in unmet)}; "
              "rendering the board, and the gate states it")
    r = board["reel"]
    # the proof draws every video at half size and names it beside the full-size one; the stills are drawn as the full
    # render draws them
    scale = proof.SCALE if getattr(a, "proof", False) else 1
    named = (lambda rel: proof.of(rel).as_posix()) if scale != 1 else str
    # the series' render is what every card is cut from; it is delivered as one video only when the person asked for it
    series = bool((board.get("ask") or {}).get("series"))
    wav = bed(run)
    out, work, tl_dir = run / "out", run / "render", run / "timeline"
    # every deliverable is made in render/out/ and moves into out/ by rename once all of them are made, so a render
    # that fails or is cut off partway leaves out/ as it was
    made = work / "out"
    # the run's lock is held from the command's first write to its last
    with studio.lock(work, "render") as hold:
        # timeline.json names the strips the measures below write again
        (run / "timeline.json").unlink(missing_ok=True)
        for x in (made / "cards", out / "cards", tl_dir):
            x.mkdir(parents=True, exist_ok=True)
        props = studio.props(board, run)
        n = len(board["beats"])
        names = [f"{i + 1:02d}-story" for i in range(len(board["beats"]))]
        jobs = [{"type": "still", "composition": "Film", "props": props, "frame": still_frame(board, i), "scale": 1,
                 "out": str((made / "cards" / f"{names[i]}.png").resolve())} for i in range(n)]
        series_frames = sum(studio.card_frames(board, c) for c in board["beats"])
        # the cover: the closer's wall with the month's line landed, the frame before that line starts to leave for the
        # closing page (its last word first, a word every 0.6 of its step, the last gone 0.3 beats after it starts)
        month_line = r["closer"]["lines"][0]
        leaving = (len(month_line["text"].split()) - 1) * (month_line.get("step") or r["enter"]["step"]) * 0.6 + 0.3
        cover_at = round((r["closer"]["sign"] - leaving - 0.1) * 60 / r["bpm"] * r["fps"])
        jobs.append({"type": "still", "composition": "Reel", "props": props, "frame": min(r["frames"] - 1, cover_at), "scale": 1,
                     "out": str((made / "cover.png").resolve())})
        # a full-size video's job carries no scale: the renderer draws a job without one at the board's size
        at = {"scale": scale} if scale != 1 else {}
        jobs += [{"type": "video", "composition": "Reel", "props": props, "frames": r["frames"], **at,
                  "out": str((work / "film-silent.mp4").resolve()), "crf": 17},
                 {"type": "video", "composition": "Film", "props": props, "frames": series_frames, **at,
                  "out": str((work / "series-silent.mp4").resolve()), "crf": 17}]
        record = report(studio.render(jobs, work, "render", board=board, run=run, hold=hold), work, scale)
        film_s = r["frames"] / r["fps"]
        series_s = series_frames / studio.FPS
        rec = _env.read_json(run / "music.json") or {}
        reel, whole = named("film.mp4"), named("series.mp4")
        sound(work / "film-silent.mp4", wav, film_s, made / reel, r["fx"], rec, stop=stop_of(r),
              energy=run / "music" / "energy.json", fps=r["fps"], spawn=hold.spawn)
        said = qa.mixed(effects_count(r["fx"]), len(r["beats"]))
        music.noted(run / "storyboards" / won(run) / "storyboard.md", f"Mixed: {said}.")
        print(f"mixed: {said}")
        timeline = {"style": board["style"], "bpm": board["bpm"], "hash": h,
                    "film": {**studio.measure(made / reel, r["cuts"], strips=tl_dir, spawn=hold.spawn, name="film"), "file": str(out / reel)}}
        if series:
            sound(work / "series-silent.mp4", wav, series_s, made / whole, series_fx(board), rec, spawn=hold.spawn)
            timeline["series"] = {**studio.measure(made / whole, studio.cut_frames(board), strips=tl_dir, spawn=hold.spawn, name="series"),
                                  "file": str(out / whole)}
        rows, at = [], 0
        for i, c in enumerate(board["beats"]):
            f = studio.card_frames(board, c)
            silent = work / f"{names[i]}-silent.mp4"
            cut(work / "series-silent.mp4", at / studio.FPS, f / studio.FPS, silent, spawn=hold.spawn)
            story = named(f"cards/{names[i]}.mp4")
            sound(silent, wav, f / studio.FPS, made / story, series_fx(board, at), rec, start=at / studio.FPS,
                  spawn=hold.spawn)
            rows.append({"n": i + 1, "id": c["id"], "role": c["idea"], "png": f"out/cards/{names[i]}.png",
                         "mp4": f"out/{story}", "from_frame": at, "frames": f, "still_frame": still_frame(board, i) - at})
            at += f
        # out/ changes from here: the page that says the film is ready to post and the records that vouch for its files
        # go first, every file moves in by rename with the reel last, and the records come back once all of them are in,
        # film.json, the board these files show, last
        for x in (out / "review.html", run / "render-report.json", run / "cards.json", run / "film.json", *([] if series else [out / whole])):
            x.unlink(missing_ok=True)
        # the full-size videos take the proof's place: out/proof.mp4 stays only while the newest render is the proof
        for x in ([] if scale != 1 else proof.films(out) + proof.films(out / "cards")):
            x.unlink()
        for rel in [*(f"cards/{x}.png" for x in names), *(named(f"cards/{x}.mp4") for x in names), "cover.png",
                    *([whole] if series else []), reel]:
            os.replace(made / rel, out / rel)
        _env.write_json(run / "render-report.json", record)
        timeline["cards"] = rows
        _env.write_json(run / "timeline.json", timeline)
        _env.write_json(run / "cards.json", {"of": n, "cards": rows, **({"series": f"out/{whole}"} if series else {}), "film": f"out/{reel}"})
        _env.write_json(run / "engine.json", {"engine": "chromium", "compositions": "motion/dist", "board": board["style"],
                                              "format": board["format"]})
        _env.write_json(run / "film.json", board)
        fl = timeline["film"]
        print(f"film   {fl['seconds']} s, {fl['cuts']} cuts ({fl['cuts_per_minute']} a minute), hook frame {fl['hook_frame']}, strip {fl['strip']}")
        if series:
            s = timeline["series"]
            print(f"series {s['seconds']} s, {s['cuts']} cuts ({s['cuts_per_minute']} a minute), hook frame {s['hook_frame']}")
        print(f"{n} cards and the cover -> {out}/" + (f" (the half-size proof: {out / reel})" if scale != 1 else ""))
    # the measured checks run again on every render, so qa/check.json always describes the film out/ holds
    qa.report(qa.checks(run, False), run / "qa" / "check.json", False)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    ap.add_argument("--proof", action="store_true",
                    help="render: every video at half size beside the full-size ones (out/proof.mp4), for every round before deliver")
    a = ap.parse_args()
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
