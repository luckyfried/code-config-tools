#!/usr/bin/env python3
"""The measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py timed --run R   # the cut, before the film renders (film.py render refuses without it)
    python3 S/scripts/qa.py check --run R   # the rendered films and stills (run before the critics watch the cut)
    python3 S/scripts/qa.py gate  --run R   # timed, check and the run's records; exit 0 only when every check passes

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strip, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them
timed reads them from the preview, check from the rendered reel.

timed (from film.json, preview/preview.json and critic/timed.json, all for the same cut):
  bounds    no bounds finding on the reel, the square or the wide board (storyboard.py check)
  length    the cut runs the length asked (taste.json `seconds`, else storyboard.SECONDS), within 1 s
  hook      the hook event lands inside the first 30 frames
  preview   preview/preview.json is for this cut
  template  the cut is no template: no two of the nine share a layout, no two beats in a row share a move, the shots'
            lengths vary and the words do not stand in one place of the frame (storyboard.style_findings); it fails
            whatever the monotony read says
  monotony  the critic's monotony read of the timed cut (vote.py timed) passed, for this cut
check (the rendered out/):
  format    out/film.mp4 1080x1920, and out/film-square.mp4 1080x1080 and out/film-wide.mp4 1920x1080 when the render
            made them: H.264, yuv420p, 30 fps, the length asked within 1 s; a film in out/ the render did not make (nobody
            asked for it) fails
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU, and with sound cues the effects
            stem at least music.FX_UNDER_BED_LU - 1 LU under the bed (both integrated, from music.json); the row
            names the two numbers and the cue and beat counts, and refuses nothing on count
  black     no black stretch of 0.4 s or more (blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting before the board's stop: frames
            that repeat, as a stalled render's do; a stretch inside one beat whose move holds the picture still once
            it settles is the held composition the board asked for, and the still from the board's stop to the end is
            the ending
  safe      no render job failed, and no type left its safe area or failed to load (render/film-report.json)
  stills    out/best-nine.png 1080x1080, and out/story.png 1080x1920 when the render made it, each a closer at rest
            that shows every one of the nine whole; a story
            card in out/ the render did not make fails
gate adds:
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  boards    the three looks, each with its three boards, storyboard.md and sheet.png, and out/boards.png
  vote      winner.json names one of the three looks: the person's pick, a pick by taste with its reason, or the
            panel's look that passed the swap test
  critic    the latest cut round in critic/ is for this film and at the bar (mean 4.5 or more, no criterion under 4),
            or the one fix is spent (the cut is delivered with its scores in brief.md)
  text      no placeholder in the words, the caption, the brief or the review page
  deliver   out/caption.md and out/review.html, the caption in their register, and brief.md in the run, not in out/
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
import bounds  # noqa: E402
import music  # noqa: E402
import story  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILMS = {"reel": (Path("out/film.mp4"), (1080, 1920)), "square": (Path("out/film-square.mp4"), (1080, 1080)),
         "wide": (Path("out/film-wide.mp4"), (1920, 1080))}
STORY, WALL = Path("out/story.png"), Path("out/best-nine.png")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p, run=None):
    r = (run.spawn if run else subprocess.run)(
        [_env.ffprobe(), "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
         "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(film, flt, key, run=None):
    r = (run.spawn if run else subprocess.run)([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt,
                                                "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def freezes(film, secs, run=None):
    """The film's frozen stretches of 1.0 s or more, as (start, end) seconds; one running to the end ends at `secs`."""
    lines = detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_", run)
    starts = [float(ln.split(":")[-1]) for ln in lines if "freeze_start" in ln]
    ends = [float(ln.split(":")[-1]) for ln in lines if "freeze_end" in ln]
    return [(s, ends[i] if i < len(ends) else secs) for i, s in enumerate(starts)]


def composed(board, start, end):
    """True when the frozen stretch from `start` to `end` lies inside one beat that holds its picture once it settles: the
    grid, whose tiles take no push once they land, the closer, whose title stands still once it is set, or a beat whose
    move puts none on the picture (story.still). That is a held composition the board asked for; a stalled render runs
    across a cut."""
    fps, t = board["format"]["fps"], 0.0
    for b in board["beats"]:
        a, t = t, t + b["frames"] / fps
        if a - 0.04 <= start and end <= t + 0.04:
            return b["form"] in ("wall", "closer") or story.still(b.get("move") or "")
    return False


def held_from(f):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    board = _env.read_json((f.get("boards") or {}).get("reel", "")) if (f.get("boards") or {}).get("reel") else {}
    stop = next((c["at"] for c in (board or {}).get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / board["bpm"] if stop is not None else float("inf")


def loudness(film, run=None):
    r = (run.spawn if run else subprocess.run)([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af",
                                                "ebur128=framelog=quiet", "-vn", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


class Checks(list):
    """Checks, (name, passed, detail), and figures, (name, None, detail, values): a figure is measured and shown,
    never passed or failed."""

    def __call__(self, name, ok, detail):
        self.append((name, bool(ok), detail))

    def figure(self, name, detail, values):
        self.append((name, None, detail, values))


def figures(res, m):
    """The cut's two figures from a measurement (`studio.measure`)."""
    res.figure("cuts", f"{m['cuts']} cuts, {m['cuts_per_minute']} a minute", {k: m[k] for k in ("cuts", "cuts_per_minute", "planned_cuts", "extra_scene_cuts")})
    res.figure("still", f"seconds under 0.5: {m['seconds_under_half']}, longest run {m['longest_run_under_half']}",
               {k: m[k] for k in ("luma", "seconds_under_half", "longest_run_under_half")})


def cut():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f


def posts_n():
    return len(storyboard.Run().posts)


def asked():
    """The length the person asked for, seconds (storyboard.asked)."""
    return storyboard.asked(_env.read_json("taste.json") or {})


def timed_checks():
    res = Checks()
    f = cut()
    want = asked()
    res("bounds", not f["findings"], f"{len(f['findings'])} findings on the three boards" + (f": {f['findings'][0]}" if f["findings"] else ""))
    res("length", abs(f["seconds"] - want) <= 1, f"{f['seconds']} s, asked {want:g} s")
    res("hook", f["hook_frame"] <= storyboard.HOOK_FRAMES, f"the hook event at frame {f['hook_frame']}")
    pv = _env.read_json("preview/preview.json") or {}
    if pv.get("hash") != f["hash"]:
        res("preview", False, "preview/preview.json is not for this cut: run film.py preview")
    else:
        res("preview", True, f"preview/preview.json, {pv['seconds']} s")
        figures(res, pv)
    reel = _env.read_json(f["boards"]["reel"]) or {}
    tells = [x for x in storyboard.style_findings({f["style"]: reel}, storyboard.Run().swatches) if any(
        k in x for k in ("vary the beats' lengths", "the words sit in one place", "consecutive beats move differently", "takes a layout of its own"))]
    res("template", not tells, f"{len(tells)} template tells" + (f": {tells[0]}" if tells else ""))
    ct = _env.read_json("critic/timed.json") or {}
    if ct.get("hash") != f["hash"]:
        res("monotony", False, "critic/timed.json is not for this cut: run vote.py timed and write the monotony read")
    else:
        read = (ct.get("monotony") or {})
        res("monotony", read.get("pass") is True and len((read.get("read") or "").split()) >= 25,
            f"the critic's read: {'pass' if read.get('pass') else 'fail' if read.get('pass') is False else 'not written'}")
    return res, f


def made():
    """What the last render made (render/film-report.json's `made`): the formats and whether the story card; the reel
    alone when the report names nothing."""
    m = (_env.read_json("render/film-report.json") or {}).get("made") or {}
    return set(m.get("formats") or ["reel"]) | {"reel"}, bool(m.get("stories"))


def film_checks(run=None):
    """The rendered out/; under deliver's lock (`run`) every process starts through run.spawn."""
    res = Checks()
    f = cut()
    formats, card = made()
    want, n = asked(), posts_n()
    track = _env.read_json("music.json") or {}
    beats = len((_env.read_json(f["boards"]["reel"]) or {}).get("beats") or [])
    held = held_from(f)
    measured = None
    for fmt, (film, size) in FILMS.items():
        if fmt not in formats:
            if film.exists():
                res("format", False, f"{film} is in out/, and the render did not make it (nobody asked for it)")
            continue
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film, run)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        ok = (v.get("width"), v.get("height")) == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and abs(secs - want) <= 1
        res("format", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s, asked {want:g} s, "
                          f"{film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        if track.get("file"):
            lu = loudness(film, run) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            cues = track.get("sound_cues") or 0
            under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
            mix = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU - 1})"
                   if under is not None else "no effects stem measured")
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                and (not cues or (under is not None and under >= music.FX_UNDER_BED_LU - 1)),
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated" if a else "no audio track")
                + f"; {mix}; {cues} sound cues over {beats} beats")
        black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start", run)
        res("black", not black, f"{film}: {len(black)} black stretches of 0.4 s or more")
        frozen = [x for x in freezes(film, secs, run) if x[0] < held - 0.04 and not composed(_env.read_json(f["boards"][fmt]), *x)]
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more outside a held composition"
            + (f" (from {frozen[0][0]:.2f} s to {frozen[0][1]:.2f} s)" if frozen else ""))
        if fmt == "reel":
            measured = studio.measure(film, f["cuts"], f["hook_frame"], strips="qa", run=run)
            _env.write_json("qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings"
        + (f": {bad[0]}" if bad else ""))
    if not card and STORY.exists():
        res("stills", False, f"{STORY} is in out/, and the render did not make it (nobody asked for it)")
    for png, size, fmt in ((STORY, (1080, 1920), "reel"), (WALL, (1080, 1080), "square"))[0 if card else 1:]:
        sz = png_size(png) if png.exists() else None
        board = _env.read_json(f["boards"][fmt])
        whole = shown_at(board, f["rests"][fmt]["closer"])
        res("stills", sz == size and whole >= n, f"{png} {'at %dx%d' % sz if sz else 'is missing'}, {whole} of {n} photographs shown at the closer's rest")
    return res, f, measured


def shown_at(board, frame):
    """How many of the posts' photographs the board shows whole in the frame at `frame`: the photographs and grid tiles
    of the beat on screen then, at rest, each inside the frame."""
    W, H = board["format"]["width"], board["format"]["height"]
    f = 0
    for beat in board["beats"]:
        if frame < f + beat["frames"]:
            return len({(L["photo"] or {}).get("file") for L in beat["layers"] if L["kind"] in ("Photo", "Slice")
                        and bounds.inside(bounds.rect(L["box"]), (0, 0, W, H))})
        f += beat["frames"]
    return 0


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                acc.append(v)
            else:
                words_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            words_in(v, acc)
    return acc


def gate_checks(run=None):
    tres, f = timed_checks()
    res, f, _ = film_checks(run)
    res = Checks(tres + res)
    texts = words_in([_env.read_json(p) for p in f["boards"].values()], [])
    for p in ("out/caption.md", "brief.md", "out/review.html"):
        if Path(p).exists():
            texts.append(Path(p).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    looks = vote.looks()
    full = [t for t in looks if all((Path("storyboards") / t / x).exists() for x in
                                    ("board-reel.json", "board-square.json", "board-wide.json", "storyboard.md", "sheet.png"))]
    res("boards", len(full) == len(looks) and Path("out/boards.png").exists(),
        f"{len(full)} of {len(looks)} looks with three boards, storyboard.md and sheet.png"
        + ("" if Path("out/boards.png").exists() else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    by = win.get("picked_by")
    ok = win.get("board") in looks and (by == "the person" or (by == "taste" and win.get("why")) or (by == "the panel" and win.get("swap_passed")))
    res("vote", ok, f"{win.get('board')}, picked by {by}" + (f": {win['why']}" if win.get("why") else ""))
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    film = FILMS["reel"][0]
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        same = film.exists() and last.get("film") == sha(film)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"])
        mean, worst, ship = vote.at_bar(last) if not bad else (None, None, False)
        res("critic", same and not bad and (ship or len(rounds) >= 2),
            f"round {len(rounds)}, " + (bad[0] if bad else f"mean {mean}, lowest {worst[0]} ({worst[1]})"
                                        + ("" if ship else ", under the bar: the scores go in brief.md"))
            + ("" if same else "; the round is not for the current out/film.mp4"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    res("deliver", reg and Path("out/review.html").exists() and Path("brief.md").exists() and not Path("out/brief.md").exists(),
        f"caption {len(cap.split())} words, {len(tags)} hashtags" + ("" if Path("out/review.html").exists() else "; review.html missing")
        + ("" if Path("brief.md").exists() else "; brief.md missing") + ("; brief.md is in out/" if Path("out/brief.md").exists() else ""))
    return res, f


def report(res, path, f, label):
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, "hash": f["hash"],
                           "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(f"{label} " + ("GREEN" if not bad else f"RED ({len(bad)} failing)"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["timed", "check", "gate"])
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    if a.cmd == "timed":
        res, f = timed_checks()
        return report(res, "qa/timed.json", f, "TIMED")
    if a.cmd == "check":
        res, f, _ = film_checks()
        return report(res, "qa/check.json", f, "CHECKS")
    res, f = gate_checks()
    return report(res, "qa/gate.json", f, "GATE")


if __name__ == "__main__":
    sys.exit(main())
