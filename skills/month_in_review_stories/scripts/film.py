#!/usr/bin/env python3
"""Movement 4: the winning storyboard rendered by the studio compositions (S/motion/studio, built into S/motion/dist)
into the deliverables.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py preview     # the reel at half size with its sound, measured: preview/film.mp4, preview.json
    python3 S/scripts/film.py render      # out/film.mp4, out/cover.png, out/cards/ (and out/series.mp4 when asked), then qa.py check

preview is what the critic's timed read (vote.py timed) watches before the film renders: the reel with its mastered
sound, its cuts as planned and as the picture shows them, the luma line and its quiet seconds, the hook frame, and the
1 and 2 fps strips. render refuses a board drafted from another taste.json than the run's (the board's `taste`), so a
change to the taste always reaches the film, and refuses until critic/timed.json holds the reads made for this board
(its hash); it prints any read that did not pass and renders the board all the same. It renders the storyboard of the
look that won the vote (winner.json `board`), one format (1080x1920 at 30 fps), in one bundle and one browser:
  out/film.mp4              the reel (the Reel composition, motion/studio/climb): their month as a walk through
                            its moments, as long as the board's reel, with its sound cues under the music, picture and music stopping together
                            on the board's stop and holding to the end
  out/series.mp4            only when the person asked for the cards as one video (the board's ask.series): the whole
                            series, every card in order (the Film composition, motion/studio/story), each card one
                            camera over one moment, with its own sound cues under the music
  out/cards/NN-story.mp4    each card as its own 15 s story: the series' render cut at the card's bounds, its cues
                            under the music
  out/cards/NN-story.png    each card's still: the card at its `still` beat, in its last whole-frame hold
  out/cover.png             the reel's cover: the closer's wall, every post of the month in its cell with the month's
                            line landed under it, the frame before the style's closing page comes over it
One card a moment, in date order, three or four of them as taste.json picks them.
Every video's sound is mastered one way (music.py `master`): the music (music.py make) from the video's first frame,
the video's sound cues under it by loudness, the whole at -14 LUFS under a peak limiter; the reel stops on its stop,
and every card and the series fade over their last 1.2 s. render writes the reel's mix (the bed's and the effects'
loudness and the cue count) into music.json and the storyboard's Mixed line.
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
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402

def card_start(board, ci):
    return sum(studio.card_frames(board, c) for c in board["beats"][:ci])


def still_frame(board, ci):
    """The series frame of card ci's still: the card's `still` beat."""
    card = board["beats"][ci]
    return card_start(board, ci) + min(studio.card_frames(board, card) - 1, studio.jround(card["still"] * studio.pulse(board)))


def series_cues(board):
    """Every card's sound cues on the series' clock: each card's beats offset by the beats of the cards before it."""
    p = studio.pulse(board)
    return [{**x, "at": round(x["at"] + card_start(board, i) / p, 3)} for i, c in enumerate(board["beats"]) for x in c.get("sound", [])]


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


def sound(silent, wav, seconds, out, fx, start=0.0, cues=(), bpm=None, spawn=subprocess.run):
    """The silent render with its sound mastered (music.master) under its cues, `at` in beats of `bpm` from its first
    frame, put at `out` by rename once it is whole, its master and stems left beside it (<name>.wav, .bed.wav,
    .fx.wav, .mix.wav); the cues play the effect files `fx` names. Returns music.master's loudness. Every process starts
    through `spawn`."""
    out = Path(out)
    master, part = out.with_suffix(".wav"), out.with_name(f"{out.stem}.part.mp4")
    mix = music.master(wav, seconds, master, start=start, cues=cues, bpm=bpm, fx=fx, spawn=spawn)
    spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(part)], check=True)
    os.replace(part, out)
    return mix


# a card is re-encoded the way the render encodes: NVENC at constant quality 14 with the NVIDIA device, x264 crf 17 without,
# both under the renderer's ceiling of 12 Mbit/s over a 24 Mbit buffer
ENCODE = (["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "14", "-b:v", "0", "-maxrate", "12M", "-bufsize", "24M"]
          if Path("/dev/nvidia0").exists() else ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-maxrate", "12M", "-bufsize", "24M"])


def cut(series, start, seconds, out, spawn=subprocess.run):
    """seconds of the silent series from start, re-encoded so the cut lands on the frame."""
    spawn([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", str(series), "-t", f"{seconds:.3f}", "-an",
           *ENCODE, "-profile:v", "high", "-pix_fmt", "yuv420p", str(out)], check=True)


def report(rep, work):
    """The render's report; a failed render exits, its renderer's report left in `work`."""
    found = studio.findings(rep)
    record = {"failed": rep.get("failed"), "exit": rep.get("exit"), "seconds": rep.get("seconds"), "findings": found,
              "lines": studio.lines(found)}
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
        lufs = sound(d / "film-silent.mp4", bed(run), seconds, d / "film.mp4", music.effects(run, r["bpm"]), cues=r["sound"],
                     bpm=r["bpm"], spawn=hold.spawn)["lufs"]
        m = studio.measure(d / "film.mp4", r["cuts"], strips=d, spawn=hold.spawn)
        m.update(hash=studio.board_hash(board), lufs=round(lufs, 1), findings=studio.lines(found))
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
        jobs += [{"type": "video", "composition": "Reel", "props": props, "frames": r["frames"], "out": str((work / "film-silent.mp4").resolve()), "crf": 17},
                 {"type": "video", "composition": "Film", "props": props, "frames": series_frames, "out": str((work / "series-silent.mp4").resolve()), "crf": 17}]
        record = report(studio.render(jobs, work, "render", board=board, run=run, hold=hold), work)
        film_s = r["frames"] / r["fps"]
        series_s = series_frames / studio.FPS
        fx = music.effects(run, r["bpm"])
        mix = sound(work / "film-silent.mp4", wav, film_s, made / "film.mp4", fx, cues=r["sound"], bpm=r["bpm"], spawn=hold.spawn)
        # the reel's mix goes on the music's record and the storyboard's Mixed line, where qa.py's audio row reads it
        track = {**(_env.read_json(run / "music.json") or {}), **{k: v for k, v in mix.items() if k != "lufs"}, "sound_cues": len(r["sound"])}
        _env.write_json(run / "music.json", track)
        said = qa.mixed(track, len(r["beats"]))[1]
        music.noted(run / "storyboards" / won(run) / "storyboard.md", f"Mixed: {said}.")
        print(f"mixed: {said}")
        timeline = {"style": board["style"], "bpm": board["bpm"], "hash": h,
                    "film": {**studio.measure(made / "film.mp4", r["cuts"], strips=tl_dir, spawn=hold.spawn), "file": str(out / "film.mp4")}}
        if series:
            sound(work / "series-silent.mp4", wav, series_s, made / "series.mp4", fx, cues=series_cues(board), bpm=board["bpm"], spawn=hold.spawn)
            timeline["series"] = {**studio.measure(made / "series.mp4", studio.cut_frames(board), strips=tl_dir, spawn=hold.spawn),
                                  "file": str(out / "series.mp4")}
        rows, at = [], 0
        for i, c in enumerate(board["beats"]):
            f = studio.card_frames(board, c)
            silent = work / f"{names[i]}-silent.mp4"
            cut(work / "series-silent.mp4", at / studio.FPS, f / studio.FPS, silent, spawn=hold.spawn)
            sound(silent, wav, f / studio.FPS, made / "cards" / f"{names[i]}.mp4", fx, start=at / studio.FPS, cues=c.get("sound", []),
                  bpm=board["bpm"], spawn=hold.spawn)
            rows.append({"n": i + 1, "id": c["id"], "role": c["idea"], "png": f"out/cards/{names[i]}.png",
                         "mp4": f"out/cards/{names[i]}.mp4", "from_frame": at, "frames": f, "still_frame": still_frame(board, i) - at})
            at += f
        # out/ changes from here: the page that says the film is ready to post and the records that vouch for its files
        # go first, every file moves in by rename with the reel last, and the records come back once all of them are in,
        # film.json, the board these files show, last
        for x in (out / "review.html", run / "render-report.json", run / "cards.json", run / "film.json", *([] if series else [out / "series.mp4"])):
            x.unlink(missing_ok=True)
        for rel in [*(f"cards/{x}.{ext}" for x in names for ext in ("png", "mp4")), "cover.png", *(["series.mp4"] if series else []), "film.mp4"]:
            os.replace(made / rel, out / rel)
        _env.write_json(run / "render-report.json", record)
        timeline["cards"] = rows
        _env.write_json(run / "timeline.json", timeline)
        _env.write_json(run / "cards.json", {"of": n, "cards": rows, **({"series": "out/series.mp4"} if series else {}), "film": "out/film.mp4"})
        _env.write_json(run / "engine.json", {"engine": "chromium", "compositions": "motion/dist", "board": board["style"],
                                              "format": board["format"]})
        _env.write_json(run / "film.json", board)
        fl = timeline["film"]
        print(f"film   {fl['seconds']} s, {fl['cuts']} cuts ({fl['cuts_per_minute']} a minute), hook frame {fl['hook_frame']}, strip {fl['strip']}")
        if series:
            s = timeline["series"]
            print(f"series {s['seconds']} s, {s['cuts']} cuts ({s['cuts_per_minute']} a minute), hook frame {s['hook_frame']}")
        print(f"{n} cards and the cover -> {out}/")
    # the measured checks run again on every render, so qa/check.json always describes the film out/ holds
    qa.report(qa.checks(run, False), run / "qa" / "check.json", False)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["preview", "render"])
    a = ap.parse_args()
    return {"preview": cmd_preview, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
