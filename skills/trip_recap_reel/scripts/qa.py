#!/usr/bin/env python3
"""Movement 6: the measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/qa.py check     # the newest render's films, any asked-for formats and story cards, and the board
                                      # (run before the critics watch the cut)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes

Three figures are printed and written beside the checks (qa/check.json, qa/gate.json, under `figures`) and are never a
pass or a fail: the critic reads them with the strips.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them
  sound     what the film sounds (film.json `sound`, the shared effects): how many, and the last one before the stop

check reads the newest render in out/: the half-size proof while out/proof.mp4 is there, which its first line says,
else the full-size films; the gate reads the full-size films alone. A proof's films (out/proof.mp4, out/proof-16x9.mp4,
out/proof-square.mp4) are measured in board units: a size read on them is divided by the proof's scale before it is
held to the film's, so a proof passes or fails where the full-size film would.

The checks (check runs film to board; gate runs them all):
  film      out/film.mp4 is not 1080x1920 H.264 high profile yuv420p at 30 fps, or its length is more than a frame off
            the timed cut's
  audio     music was found but the film has no AAC track near 192 kbps, its loudness (the music with the shared
            effects over it) is off -14 LUFS by more than 1 LU, or its true peak is over -1.5 dBTP; the row prints the
            effect and beat counts and refuses nothing on count
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect) that ends before the closer opens; one that runs into
            the closer is the cut into it
  frozen    a frozen stretch of 1.0 s or more (freezedetect at -80 dB) anywhere in the film, its ending too: frames
            that repeat, as a stalled render's do; the closer keeps its slow push from the stop to the last frame
  white     a frame whose mean luma is over 0.82 (0 to 1 across the video range), or over the look's paper and a little
            where the look lays its pictures on paper: a white frame from a shader that failed; a frame inside a
            white cut (flash-frame, roll-burn) while the cut plays is the cut's light
  safe      a render job that failed (a shader error or a lost WebGL context fails it), or a font or a photograph
            that did not load
            (render/film-report.json)
  landscape when the render made it (render/film-report.json's `made`, from film.py render --also): out/film-16x9.mp4
            is not 1920x1080 H.264 at 30 fps, or its length is more than 1 s off the film's; when it did not, the file
            is in out/ (nobody asked for it)
  square    the same for out/film-square.mp4 at 1080x1080
  stories   when the render made them: out/story-1.png .. out/story-5.png are not five 1080x1920 frames with a picture
            on them, one per beat the board names in `stories` (a card whose pixels barely vary is an empty frame, and
            two cards whose mean gray difference is under 4 of 255 are one picture); when it did not, a story card is
            in out/
  board     the film's storyboard fails storyboard.py check (the swap test, the structure, the look's own rules) or
            film.json fails the monotony read: the same reads snap runs before the film renders
gate adds:
  text      a placeholder string anywhere in the film's words, the caption, the brief or the review page
  research  taste.md (you are / you like / your style / your voice / avoid) or taste.json is missing
  boards    the three boards, one per look, each with storyboard.md, storyboard.json and sheet.png, and out/boards.png
  vote      vote.md and winner.json are missing
  clips     the film's storyboard lists clips and clips.json does not account for every one
  critic    the latest cut round in critic/ is not for this film, is a round the vote refuses (a score missing or a
            paragraph under 25 words; the row names the first reason), or scores below 4 with the one fix unspent
  deliver   out/caption.md, out/review.html, out/cover.png or brief.md (in the run's folder) is missing, out/ holds a file
            that is not a deliverable (the films, the cover, the story cards, the caption, the review page and the boards), or the
            caption is not in their register
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import proof  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILM = Path("out/film.mp4")
FORMATS = (("landscape", Path("out/film-16x9.mp4"), (1920, 1080)), ("square", Path("out/film-square.mp4"), (1080, 1080)))
STORIES = [Path(f"out/story-{i}.png") for i in range(1, 6)]
DELIVERABLES = {FILM.name, "cover.png", "caption.md", "review.html", "boards.png"} | {p.name for _, p, _ in FORMATS} | {p.name for p in STORIES}
WHITE = 0.82
FLAT = 6.0
APART = 4.0  # mean gray difference (0-255) under which two cards are one picture
FAULTS = ("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def tool(argv, run=None):
    """A tool's output; under a command's lock (`run`, deliver's) the process starts through run.spawn and holds it."""
    return (run.spawn if run else subprocess.run)(argv, capture_output=True, text=True)


def probe(p, run=None):
    r = tool([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], run)
    return json.loads(r.stdout or "{}")


def detect(flt, key, run=None, film=FILM):
    r = tool([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt, "-an", "-f", "null", "-"], run)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def closer_from(film):
    """Where the closer opens (the impact it opens on, else the route's closer), in seconds; never, without one. The
    closer is the look's own ending, its title on its ground, so a black stretch running into it is the cut into the
    closer."""
    at = next((c["at"] for c in film.get("sound") or [] if c["kind"] == "impact" and c.get("beat") == "closer"), None)
    at = at if at is not None else ((film.get("route") or {}).get("closer") or {}).get("at")
    return at * 60 / film["bpm"] if at is not None else float("inf")


def white_line(film):
    """The brightest a frame may be: WHITE, or a little over the look's paper where the look lays its pictures on paper
    (a page turning over the whole frame is the paper, never a failed shader's white)."""
    paper = ((film.get("system") or {}).get("colors") or {}).get("paper")
    if not paper or not ((film.get("system") or {}).get("photo") or {}).get("ground") == "paper":
        return WHITE
    r, g, b = (int(paper.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return max(WHITE, round(0.2126 * r + 0.7152 * g + 0.0722 * b + 0.04, 3))


WHITE_CUTS = {"flash-frame": 0.5, "roll-burn": 1.6}


def flashes(film):
    """The seconds the look's white cuts (each with its length in beats, as its cut file plays it) light the frame: the
    cut's length centered on the start of the beat it cuts into."""
    spb = 60 / film["bpm"]
    return [((b["at"] - WHITE_CUTS[b["transition"]] / 2) * spb, (b["at"] + WHITE_CUTS[b["transition"]] / 2) * spb)
            for b in film.get("beats") or [] if b.get("transition") in WHITE_CUTS]


def black_end(line):
    """The end, in seconds, of one blackdetect line."""
    m = re.search(r"black_end:([\d.]+)", line)
    return float(m.group(1)) if m else float("inf")


def held_from(film):
    """Where the board's `stop` falls, in seconds; never, without one."""
    stop = next((c["at"] for c in film.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / film["bpm"] if stop is not None else float("inf")


def loudness(run=None, film=FILM):
    """The film's integrated loudness (LUFS) and true peak (dBTP) as its AAC track decodes."""
    r = tool([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", "ebur128=framelog=quiet:peak=true", "-vn", "-f", "null", "-"], run)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", r.stderr)
    return (float(m[-1]) if m else None), (float(tp[-1]) if tp else None)


def frame_luma(run=None, film=FILM):
    """Every frame's mean luma, 0 to 1 across the video range (Y 16-235), read at a tenth of the frame."""
    r = tool([_env.ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", str(film), "-vf",
              "scale=108:192:flags=area,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-an", "-f", "null", "-"], run)
    return [max(0.0, min(1.0, (float(v) - 16) / 219)) for v in re.findall(r"YAVG=([\d.]+)", r.stdout)]


class Checks(list):
    """Checks, (name, passed, detail), and figures, (name, None, detail, values): a figure is measured and shown,
    never passed or failed."""

    def __call__(self, name, ok, detail):
        self.append((name, bool(ok), detail))

    def figure(self, name, detail, values):
        self.append((name, None, detail, values))


def figures(res, m, film):
    """The cut's figures from a measurement (`studio.measure`) and what the film sounds."""
    res.figure("cuts", f"{m['cuts']} cuts, {m['cuts_per_minute']} a minute", {k: m[k] for k in ("cuts", "cuts_per_minute", "planned_cuts", "extra_scene_cuts")})
    res.figure("still", f"seconds under 0.5: {m['seconds_under_half']}, longest run {m['longest_run_under_half']}",
               {k: m[k] for k in ("luma", "seconds_under_half", "longest_run_under_half")})
    cues = [c for c in film.get("sound") or [] if c["kind"] != "stop"]
    last = max(cues, key=lambda c: c["at"]) if cues else None
    sec = 60 / film["bpm"]
    res.figure("sound", f"{len(cues)} sound events" + (f", the last at {last['at'] * sec:.2f} s: {last.get('what', last['kind'])}" if last else "")
               + (f"; the picture and the music stop at {held_from(film):.2f} s" if cues else ""),
               {"events": len(cues), "last": last and {"at_s": round(last["at"] * sec, 2), "what": last.get("what")}, "stop_s": round(held_from(film), 2)})


def stories_check(film):
    """Five story cards, 1080x1920, five different pictures, none an empty frame, one per beat the board names."""
    from PIL import Image, ImageStat
    names = film.get("stories") or []
    got, sizes, flat, thumbs = [], [], [], []
    for f in STORIES:
        if not f.exists():
            continue
        got.append(f)
        with Image.open(f) as im:
            sizes.append(im.size)
            g = im.convert("L").resize((108, 192))
            if ImageStat.Stat(g).stddev[0] < FLAT:
                flat.append(f.name)
            thumbs.append((f.name, g.tobytes()))
    same = [f"{a} and {b}" for i, (a, x) in enumerate(thumbs) for b, y in thumbs[i + 1:]
            if sum(abs(p - q) for p, q in zip(x, y)) / len(x) < APART]
    missing = [f.name for f in STORIES if f not in got]
    ok = not missing and set(sizes) == {(1080, 1920)} and not same and not flat and len(names) == 5
    detail = f"{len(got)} of 5 cards, sizes {sorted(set(sizes))}" + (f", of the beats {', '.join(names)}" if names else "")
    if same:
        detail += f"; the same picture: {', '.join(same)}"
    if missing:
        detail += f"; missing {missing}"
    if flat:
        detail += f"; empty frames {flat}"
    if len(names) != 5:
        detail += f"; film.json names {len(names)} story beats, not 5"
    return ok, detail


def board_check(film):
    """storyboard.py check on the film's own storyboard and the monotony read on film.json, as snap runs them before the
    render."""
    import storyboard
    board = _env.read_json(storyboard.BOARDS / str(film.get("id")) / "storyboard.json") if film.get("id") else None
    if not board:
        return False, "film.json names no storyboard: run storyboard.py snap"
    _, issues = storyboard.check_board(board)
    read = storyboard.monotony(film)
    swaps = sum(1 for t in issues if t.startswith("swap"))
    return not issues and not read, (f"board {board['id']} ({board['style']}): {len(issues)} faults ({swaps} from the swap test), "
                                     f"{len(read)} monotony refusals" + (f": {(issues + read)[0]}" if issues or read else ""))


def made():
    """What the last render made (render/film-report.json's `made`): the formats and whether the story cards; the reel
    alone when the report names nothing."""
    m = (_env.read_json("render/film-report.json") or {}).get("made") or {}
    return set(m.get("formats") or ["reel"]) | {"reel"}, bool(m.get("stories"))


def sized(v, scale):
    """A film's size in board units, and how the row says it: a proof's size read is divided by its scale."""
    got = proof.board((v.get("width") or 0, v.get("height") or 0), scale)
    return got, f"{got[0]}x{got[1]}" + (f" in board units, rendered at {v.get('width')}x{v.get('height')}" if scale != 1 else "")


def film_checks(run=None, scale=1):
    """The film checks on the full-size films, or on the proof's at `scale` (proof.SCALE), measured in board units;
    deliver passes its lock (`run`), so every process they start holds it."""
    import studio
    res = Checks()
    film = _env.read_json("film.json") or {}
    if not film:
        sys.exit("film.json is missing: run storyboard.py snap first")
    mp4 = FILM if scale == 1 else proof.of(FILM)
    if not mp4.exists():
        res("film", False, f"{mp4} is missing")
        return res
    p = probe(mp4, run)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
    secs = float(p.get("format", {}).get("duration") or 0)
    got, said = sized(v, scale)
    ok = got == (1080, 1920) and v.get("codec_name") == "h264" and v.get("profile") == "High" \
        and v.get("pix_fmt") == "yuv420p" and v.get("r_frame_rate") == "30/1" and abs(secs - film["seconds"]) <= 1 / 30 + 0.01
    res("film", ok, f"{said} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                    f"{v.get('r_frame_rate')} fps, {secs:.2f} s against the cut's {film['seconds']:.2f} s, {mp4.stat().st_size / 1e6:.1f} MB, {mp4.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
    music = _env.read_json("music.json") or {}
    if music.get("file"):
        if not a:
            res("audio", False, "music was found but the film has no audio track")
        else:
            lu, tp = loudness(run, mp4)
            br = int(a.get("bit_rate") or 0)
            fx = sum(1 for c in film.get("sound") or [] if c["kind"] != "stop")
            res("audio", a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0 and tp is not None and tp <= -1.5,
                f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated, true peak {tp} dBTP; "
                f"{fx} effects over {len(film.get('beats') or [])} beats (sfx.py)")
    else:
        res("audio", True, "no music was found; no audio track is required" + (" (the film has one)" if a else ""))
    closes = closer_from(film)
    black = [ln for ln in detect("blackdetect=d=0.4:pix_th=0.10", "black_start", run, mp4) if black_end(ln) < closes - 0.04]
    res("black", not black, f"{len(black)} black stretches of 0.4 s or more ending before the closer at {closes:.2f} s"
        + (f": {black[0][-80:]}" if black else ""))
    frozen = detect("freezedetect=n=-80dB:d=1.0", "freeze_start", run, mp4)
    res("frozen", not frozen, f"{len(frozen)} frozen stretches of 1.0 s or more" + (f" ({frozen[0][-40:]})" if frozen else ""))
    luma = frame_luma(run, mp4)
    top = white_line(film)
    lit = flashes(film)
    white = [(f, x) for f, x in enumerate(luma) if x > top and not any(a <= f / 30 <= z for a, z in lit)]
    res("white", luma and not white, f"{len(luma)} frames, brightest {max(luma) if luma else 0:.3f}, {len(white)} over {top:.3f}"
        + (": " + ", ".join(f"{f / 30:.2f} s {x:.3f}" for f, x in white[:6]) if white else ""))
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(FAULTS)]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, "
        f"{len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    formats, cards = made()
    for name, path, size in FORMATS:
        path = path if scale == 1 else proof.of(path)
        if name not in formats:
            if path.exists():
                res(name, False, f"{path} is in out/, and the render did not make it (nobody asked for it)")
            continue
        if not path.exists():
            res(name, False, f"{path} is missing")
            continue
        q = probe(path, run)
        lv = next((x for x in q.get("streams", []) if x.get("codec_type") == "video"), {})
        ls = float(q.get("format", {}).get("duration") or 0)
        lgot, lsaid = sized(lv, scale)
        res(name, lgot == size and lv.get("codec_name") == "h264" and lv.get("r_frame_rate") == "30/1"
            and abs(ls - secs) <= 1.0, f"{lsaid} {lv.get('codec_name')} {lv.get('r_frame_rate')} fps, {ls:.1f} s "
            f"({ls - secs:+.2f} s against the film)")
    if cards:
        res("stories", *stories_check(film))
    else:
        extra = sorted(p.name for p in Path("out").glob("story-*.png"))
        res("stories", not extra, "no story cards asked for" + (f", and out/ holds {', '.join(extra)}" if extra else ", none in out/"))
    res("board", *board_check(film))
    # the strips are the newest render's, qa/film-strip.png and qa/film-strip2.png, for the proof as for the film
    m = studio.measure(mp4, film["cuts"], 0, strips="qa", run=run, name="film")
    figures(res, m, film)
    return res


def words_of(film):
    """Every word the film sets on screen: the trip's name and dates, the sign-off, and each stop's name, date and
    caption."""
    r = film.get("route") or {}
    return [str(x) for x in (r.get("title"), r.get("kicker"), r.get("signoff")) if x] + \
        [str(s.get(k)) for s in film.get("stops") or [] for k in ("name", "date", "caption") if s.get(k)]


def gate_checks(run=None):
    res = film_checks(run)
    film = _env.read_json("film.json") or {}
    texts = words_of(film)
    for f in ("out/caption.md", "brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    import storyboard
    full = [n for n in storyboard.NUMBERS if all((storyboard.BOARDS / n / x).exists() for x in ("storyboard.md", "storyboard.json", "sheet.png"))]
    sheet = Path("out/boards.png").exists()
    res("boards", len(full) == len(storyboard.NUMBERS) and sheet,
        f"{len(full)} of {len(storyboard.NUMBERS)} storyboards with storyboard.md and sheet.png" + ("" if sheet else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    res("vote", Path("vote.md").exists() and win.get("board"), f"winner {win.get('board')} ({win.get('name')})")
    want = {c["id"] for c in film.get("clips") or []}
    got = set(((_env.read_json("clips.json") or {}).get("clips") or {}).keys())
    res("clips", want <= got, f"{len(want)} clips listed, {len(want & got)} accounted for" + (f"; missing {sorted(want - got)}" if want - got else ""))
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        import vote
        last = _env.read_json(rounds[-1])
        sc = [x for c in last.get("critics", {}).values() for e in c.get("boards", {}).values() for x in (e.get("scores") or {}).values()]
        same = FILM.exists() and last.get("film") == sha(FILM)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"]) + ([vote.unread(last.get("film"))] if same and vote.unread(last.get("film")) else [])
        res("critic", same and not bad and (min(sc) >= 4 or len(rounds) >= 2),
            f"round {len(rounds)}, " + (bad[0] if bad else f"lowest {min(sc)}") + ("" if same else "; the round is not for the current out/film.mp4"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    from deliver import their_tags
    theirs = their_tags((_env.read_json("taste.json") or {}).get("register") or {})
    reg = cap and (not lower or body == body.lower()) and (1 <= len(tags) <= 10 if theirs else not tags)
    need = [f for f in ("out/review.html", "out/cover.png", "brief.md") if not Path(f).exists()]
    stray = sorted(p.name for p in Path("out").iterdir() if p.name not in DELIVERABLES) if Path("out").is_dir() else []
    res("deliver", reg and not need and not stray,
        f"caption {len(cap.split())} words, {len(tags)} hashtags" + ("" if theirs else " (they use none)") + (", lowercase like theirs" if lower else "") +
        "".join(f"; {f} missing" for f in need) + (f"; out/ holds {', '.join(stray)}, which is not a deliverable" if stray else ""))
    return res


def full_render():
    """The command that renders the full-size films of what the newest render made: the reel and the --also it had."""
    formats, cards = made()
    also = [k for k in ("landscape", "square") if k in formats] + ["stories"] * cards
    return "film.py render" + (" --also " + " ".join(also) if also else "")


def report(res, path, label, film=FILM):
    """Prints the rows and writes them to `path`, naming the film they read (`film`)."""
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, "film": sha(film) if Path(film).exists() else None,
                           "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(f"{label} " + ("GREEN" if not bad else f"RED ({len(bad)} failing)"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    _env.enter_run()
    _env.need("PIL")
    if a.cmd == "check":
        scale = proof.scale(FILM)
        if scale != 1:
            print(proof.reading(proof.of(FILM)))
        return report(film_checks(scale=scale), "qa/check.json", "CHECKS", proof.newest(FILM))
    return report(gate_checks(), "qa/gate.json", "GATE")


if __name__ == "__main__":
    sys.exit(main())
