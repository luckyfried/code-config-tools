#!/usr/bin/env python3
"""The film: cut first (movement 4) and checked, then rendered in its three shapes with its story card and posted image,
and the stills when the person asked for them (movement 6).

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py cut       # the timed cut: the reel with its music -> cut.mp4, measured: cut.json, cut-strip.png,
                                        # cut-strip12.jpg (1 and 12 frames a second)
    python3 S/scripts/film.py render    # out/film.mp4 (reel), out/film-square.mp4, out/film-wide.mp4, out/story.png
                                        # and out/post.png
    python3 S/scripts/film.py render --also stories
                                        # and, when the person asked for a carousel, out/stills/*.png

Every job renders the studio composition (S/motion/studio, `studio.py`) from the boards storyboard.py snap named in
film.json. cut renders the reel at full size and lays the mastered music (music.json's master) under it at AAC
192 kbps: it is the reel as it is delivered, what qa.py check measures, picture and sound, and the critic watches
(vote.py cut). render refuses until qa/check.json passes for this cut, the critics' latest verdict ships it at the bar or says
the one fix is spent, and music.json names the master the cut carries; then the reel is the cut itself, square and
wide are rendered from their own boards with the same music, the story card (the reel's
cover) is the hook at rest and the posted image the square's peak moment with its line, and with `--also stories` the stills (the square film's beats at
rest, one a beat in the film's order and at most ten, for an Instagram carousel) come too. render.json carries the
wall time and CPU-seconds of each render, render/<name>-report.json every finding the composition logged, and the
film's report what the render made (`made`: its formats and whether the stills). The films, the cards and the stills
are made in out.part/ beside out/ and move into out/ by rename once every one of them is made, stills an earlier render
left that this one was not asked for leave, and the reel moves last; out/review.html goes first, so a render stopped
part way never leaves out/ reading as delivered (deliver.py writes the page again). Each command holds the run's render lock from before its
first write, and every process it starts holds it too.
"""
import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import studio  # noqa: E402

CUT = Path("cut.mp4")
OUT = Path("out")
STILLS = OUT / "stills"
MAX_STILLS = 10
NAMES = {"reel": "film.mp4", "square": "film-square.mp4", "wide": "film-wide.mp4"}
ALSO = ("stories",)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f, {fmt: _env.read_json(p) for fmt, p in f["boards"].items()}


def timed(jobs, name, run):
    """The render; a failed one publishes its report, which QA refuses, and stops."""
    rep = studio.render(jobs, name, run)
    for x in rep.get("findings", []):
        print("finding:", x["text"][:300])
    if rep["failed"]:
        studio.publish_report(name)
        sys.exit(f"a render job failed; see render/{name}.log and {studio.report_of(name)}")
    return rep


def record(name, rep):
    """render.json, which brief.md reads: the render's times, once what it made is published."""
    rec = _env.read_json("render.json") or {}
    rec[name] = {k: rep.get(k) for k in ("seconds", "cpu_seconds", "gpu", "jobs", "failed")}
    _env.write_json("render.json", rec)


def cmd_cut(a, run):
    f, boards = film()
    # cut.json and the cut's report name the cut and its strips: they go before any of them changes, the report comes
    # back after the measure and cut.json last
    Path("cut.json").unlink(missing_ok=True)
    studio.report_of("cut").unlink(missing_ok=True)
    silent = Path("render/silent") / CUT.name
    silent.parent.mkdir(parents=True, exist_ok=True)
    rep = timed([studio.video(boards["reel"], silent)], "cut", run)
    if not silent.exists():
        sys.exit("the cut did not render; see render/cut.log")
    CUT.unlink(missing_ok=True)
    mux(run, silent, CUT, f["seconds"])
    m = studio.measure(CUT, f["cuts"], f["hook_frame"], run=run)
    studio.publish_report("cut")
    beats, t = [], 0
    for x in boards["reel"]["beats"]:
        beats.append({"id": x["id"], "start": round(t / 30, 2), "seconds": round(x["frames"] / 30, 2), "rest": round((t + x["rest"]) / 30, 2)})
        t += x["frames"]
    _env.write_json("cut.json", {"file": str(CUT), "sha": sha(CUT), "hash": f["hash"], "look": f["board"], "style": f["style"], "seconds": f["seconds"],
                                 "bpm": f["bpm"], "master": (_env.read_json("music.json") or {}).get("master"), "shots": beats,
                                 "measured": m})
    print(f"cut: {f['name']}, {m['seconds']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), hook at frame {f['hook_frame']} "
          f"-> {CUT}, {m['strip']}, {m['strip12']}, cut.json; next: qa.py check, then vote.py cut")
    record("cut", rep)
    return 0


def ready():
    """Why the film may not render yet, or None."""
    if not CUT.exists():
        return "cut.mp4 is missing: run film.py cut"
    qa = _env.read_json("qa/check.json") or {}
    if qa.get("film") != sha(CUT):
        return "qa/check.json is not for this cut: run qa.py check"
    if not qa.get("pass"):
        return "qa.py check fails on the cut: " + "; ".join(c["check"] for c in qa.get("checks", []) if not c["pass"])
    v = _env.read_json("critic/verdict.json") or {}
    if v.get("film") != sha(CUT):
        return "the critic has not judged this cut: run vote.py cut, fill it in, then vote.py verdict"
    if v.get("verdict") not in ("ship", "spent"):
        return f"the critic's verdict on this cut is {v.get('verdict')}: {v.get('what')}"
    if (_env.read_json("cut.json") or {}).get("master") != (_env.read_json("music.json") or {}).get("master"):
        return "the music was mastered again after the cut: run film.py cut, qa.py check and the critic again"
    return None


def mux(run, silent, out, seconds):
    """The film with the master music.json names under it, or the silent film when it names none."""
    master = (_env.read_json("music.json") or {}).get("master")
    if not master:
        shutil.copyfile(silent, out)
        return False
    run.spawn([_env.ffmpeg(), "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}", "-movflags", "+faststart",
                    str(out)], check=True)
    return True


def still_picks(board):
    """Every beat at rest in the film's order, at most ten: the hook and the closer always, the shortest beats between
    them dropped first."""
    rows, t = [], 0
    for x in board["beats"]:
        rows.append((x, t + x["rest"]))
        t += x["frames"]
    while len(rows) > MAX_STILLS:
        rows.pop(min(range(1, len(rows) - 1), key=lambda j: (rows[j][0]["frames"], -j)))
    return rows


def publish(part):
    """Moves every file made in `part` into out/ by rename, after out/review.html is gone, and the reel last: the
    films, the story card and the stills of out/ the new set does not make go before it, so out/film.mp4 changes only
    when the rest of the set is in.
    The render's report is what QA reads as proof of the films in out/: it is away while they change and is published
    after the last, so a set stopped part way is one the gate refuses."""
    (OUT / "review.html").unlink(missing_ok=True)
    studio.report_of("film").unlink(missing_ok=True)
    reel = Path(NAMES["reel"])
    made = {q.relative_to(part) for q in part.rglob("*") if q.is_file()}
    for rel in sorted(made - {reel}):
        (OUT / rel).parent.mkdir(parents=True, exist_ok=True)
        os.replace(part / rel, OUT / rel)
    for q in [OUT / n for n in NAMES.values()] + [OUT / "story.png", OUT / "post.png", OUT / "stills.json"] + list(STILLS.glob("*.png")):
        if q.relative_to(OUT) not in made:
            q.unlink(missing_ok=True)
    if STILLS.exists() and not any(STILLS.iterdir()):
        STILLS.rmdir()
    os.replace(part / reel, OUT / reel)
    studio.publish_report("film")
    shutil.rmtree(part)


def cmd_render(a, run):
    why = ready()
    if why and not a.force:
        sys.exit(f"not rendering: {why}")
    f, boards = film()
    also = getattr(a, "also", None) or ()
    formats = ["square", "wide"]
    part = OUT.with_name("out.part")
    shutil.rmtree(part, ignore_errors=True)
    silent = Path("render/silent")
    for d in (part, silent):
        d.mkdir(parents=True, exist_ok=True)
    jobs = [studio.video(boards[fmt], silent / NAMES[fmt]) for fmt in formats]
    # the cover is the hook as it settles, the frame that stops a thumb; the image to post is the story's peak moment
    # with its line, in the person's own words, and the hook where the story has no moments
    jobs.append(studio.still(boards["reel"], f["rests"]["reel"]["hook"], part / "story.png"))
    sq = f["rests"]["square"]
    jobs.append(studio.still(boards["square"], sq.get("peak", sq["hook"]), part / "post.png"))
    picks = still_picks(boards["square"]) if "stories" in also else []
    if picks:
        (part / "stills").mkdir()
    for n, (x, fr) in enumerate(picks, 1):
        jobs.append(studio.still(boards["square"], fr, part / "stills" / f"{n:02d}-{x['id']}.png"))
    rep = timed(jobs, "film", run)
    _env.write_json(_env.part(studio.report_of("film")), dict(rep, made={"formats": ["reel"] + formats, "stories": bool(picks)}))
    shutil.copyfile(CUT, part / NAMES["reel"])
    music = bool((_env.read_json("music.json") or {}).get("master"))
    for fmt in formats:
        mux(run, silent / NAMES[fmt], part / NAMES[fmt], f["seconds"])
    if picks:
        _env.write_json(part / "stills.json", {"stills": [{"file": f"stills/{n:02d}-{x['id']}.png", "shot": x["id"], "frame": fr}
                                                          for n, (x, fr) in enumerate(picks, 1)]})
    publish(part)
    record("film", rep)
    made = [str(OUT / NAMES[fmt]) for fmt in ["reel"] + formats] + [str(OUT / "story.png"), str(OUT / "post.png")] \
        + ([f"{len(picks)} stills in {STILLS}/"] if picks else [])
    print(f"film: {f['name']}, {f['seconds']:.2f} s{' with music' if music else ' (music.json names no master: the films are silent)'} -> "
          f"{', '.join(made)}; next: qa.py gate")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cut", "render"])
    ap.add_argument("--also", nargs="*", choices=ALSO, default=[],
                    help="render: what the person asked for beyond the films and cards (stories: the stills for a carousel)")
    ap.add_argument("--force", action="store_true", help="render: render a cut the check or the critic has not passed (the gate still refuses it)")
    a = ap.parse_args()
    _env.enter()
    # the render lock is taken before the command's first write into the run, so a refused second one changes nothing
    with studio.lock({"cut": "cut", "render": "film"}[a.cmd]) as run:
        return {"cut": cmd_cut, "render": cmd_render}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
