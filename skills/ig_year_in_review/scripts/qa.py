#!/usr/bin/env python3
"""The measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py timed   # the cut, before the film renders (film.py render refuses without it)
    python3 S/scripts/qa.py check   # the newest render, the half-size proof or the film, and the cards (run before
                                    # the critics watch the cut)
    python3 S/scripts/qa.py gate    # timed, check and the run's records; exit 0 only when every check passes

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strip, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them
timed reads them from the preview, check from the rendered film.

timed (from build/film.json, build/preview/preview.json and build/critic/timed.json, all for the same cut):
  bounds    no finding on the board (storyboard.py check: the type inside the reel's safe area at every rest)
  length    the cut runs inside the length band, storyboard.LENGTH
  hook      the hook event lands inside the first 30 frames
  preview   build/preview/preview.json is for this cut
  reads     the critic's four reads of the timed cut (vote.py timed) passed, for this cut
check (the newest render in out/: the half-size proof while out/proof.mp4 is there, which its first line says, else
the full-size film; the gate reads the full-size film alone):
  format    out/film.mp4 1080x1920, H.264, yuv420p, 30 fps, inside the length band. The proof (out/proof.mp4) is
            measured in board units: its size is divided by the proof's scale before it is held to 1080x1920
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU, and its true peak at
            PEAK dBTP or under (the music and the effects mastered together by the mux); the row names both
            numbers and the cue and beat counts, and refuses nothing on count
  black     no black stretch of 0.4 s or more (blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) anywhere in the film, its ending too: frames
            that repeat, as a stalled render's do; the film grain moving under a held composition is change, and the
            closer keeps its slow push from the stop to the last frame
  safe      no render job failed, and no font or photograph failed to load (build/render/film-report.json)
  cards     out/carousel/ is 10 PNGs at 1080x1350, out/stories/ is 3 PNGs at 1080x1920
gate adds:
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  boards    each of the three styles' board, storyboard.md and sheet.png, and out/boards.png
  vote      winner.json names one of the three: the person's pick, or the panel's board when its swap test passed on
            all three compositions
  clips     every clip the board lists is accounted for in clips.json, generated or stand-in
  critic    the latest cut round in build/critic/ is for this film and at the bar (vote.BAR: the mean 4.5 or more,
            none under 4), or the one fix is spent and build/brief.md carries the scores
  text      no placeholder in the words, the caption, the brief or the review page
  deliver   out/caption.md, out/review.html and build/brief.md, the caption in their register, and out/ holding
            only what is posted and the review page with its strip
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
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
OUT = Path("../out")
FILMS = {"reel": (OUT / "film.mp4", (1080, 1920))}
# out/ holds what is posted and the review page with its strip, nothing else
DELIVERABLES = {"film.mp4", "carousel", "stories", "strip", "caption.md", "review.html", "boards.png", "looks"}
CARDS = {"carousel": (10, (1080, 1350)), "stories": (3, (1080, 1920))}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p, run=None):
    r = (run.spawn if run else subprocess.run)([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(film, flt, key, run=None):
    return [ln for ln in studio.ff(["-i", str(film), "-vf", flt, "-an", "-f", "null", "-"], run).splitlines() if key in ln]


def frozen_in(film, run=None):
    """Every frozen stretch of 1.0 s or more in the film (freezedetect at -80 dB), its ending included."""
    return detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start", run)


PEAK = -1.5  # dBTP: the mux limits 4 dB under full scale and encodes AAC without noise substitution


def true_peak(film, run=None):
    """The film's true peak, dBTP (ebur128 reads it oversampled), or None when it has no sound."""
    m = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", studio.ff(["-i", str(film), "-af", "ebur128=peak=true:framelog=quiet", "-vn",
                                                               "-f", "null", "-"], run))
    return float(m[-1]) if m else None


def loudness(film, run=None):
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", studio.ff(["-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"], run))
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


def timed_checks():
    res = Checks()
    f = cut()
    res("bounds", not f["findings"], f"{len(f['findings'])} findings on the board" + (f": {f['findings'][0]}" if f["findings"] else ""))
    lo, hi = storyboard.LENGTH
    res("length", lo <= f["seconds"] <= hi, f"{f['seconds']} s, band {lo}-{hi} s")
    res("hook", f["hook_frame"] <= storyboard.HOOK_FRAMES, f"the hook event at frame {f['hook_frame']}")
    pv = _env.read_json("preview/preview.json") or {}
    if pv.get("hash") != f["hash"]:
        res("preview", False, "build/preview/preview.json is not for this cut: run film.py preview")
    else:
        res("preview", True, f"build/preview/preview.json, {pv['seconds']} s")
        figures(res, pv)
    ct = _env.read_json("critic/timed.json") or {}
    if ct.get("hash") != f["hash"]:
        res("reads", False, "build/critic/timed.json is not for this cut: run vote.py timed and write the four reads")
    else:
        reads = ct.get("reads") or {}
        state = {k: (reads.get(k) or {}).get("pass") for k in vote.READS}
        res("reads", vote.timed_ok(ct), "the critic's reads: " + ", ".join(f"{k} {'pass' if v else 'fail' if v is False else 'not written'}" for k, v in state.items()))
    return res, f


def film_checks(run=None, scale=1):
    """The rendered out/: the full-size film, or the proof's at `scale` (proof.SCALE), measured in board units; under a
    command's lock (`run`, deliver's) every process starts through run.spawn."""
    res = Checks()
    f = cut()
    lo, hi = storyboard.LENGTH
    track = _env.read_json("music.json") or {}
    reel = _env.read_json(f["boards"]["reel"]) or {}
    beats, cues = len(reel.get("beats") or []), len(reel.get("sound") or [])
    measured = None
    for fmt, (film, size) in FILMS.items():
        film = proof.of(film) if scale != 1 else film
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film, run)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        got = proof.board((v.get("width") or 0, v.get("height") or 0), scale)
        ok = got == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and lo <= secs <= hi
        res("format", ok, f"{film}: " + (f"{got[0]}x{got[1]} in board units, rendered at " if scale != 1 else "")
                          + f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s, {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        if track.get("file"):
            lu = loudness(film, run) if a else None
            tp = true_peak(film, run) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                and tp is not None and tp <= PEAK,
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated, true peak {tp} dBTP (at most {PEAK})"
                               if a else "no audio track")
                + f"; the music and the effects mastered together; {cues} sound cues over {beats} beats")
        black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start", run)
        res("black", not black, f"{film}: {len(black)} black stretches of 0.4 s or more")
        frozen = frozen_in(film, run)
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more" + (f" ({frozen[0][-40:]})" if frozen else ""))
        if fmt == "reel":
            # the strips are the newest render's, qa/film-strip.png and qa/film-strip2.png, for the proof as for the film
            measured = studio.measure(film, f["cuts"], f["hook_frame"], strips="qa", run=run, name="film")
            _env.write_json("qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings"
        + (f": {bad[0]}" if bad else ""))
    for folder, (count, size) in CARDS.items():
        pngs = sorted((OUT / folder).glob("*.png"))
        sizes = {png_size(p) for p in pngs}
        res("cards", len(pngs) == count and sizes == {size}, f"out/{folder}/: {len(pngs)} PNGs at {', '.join('%dx%d' % z for z in sizes) or '-'} (wants {count} at {size[0]}x{size[1]})")
    return res, f, measured


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
    """deliver calls it in its own process with its lock (`run`)."""
    tres, f = timed_checks()
    res, f, _ = film_checks(run)
    res = Checks(tres + res)
    texts = words_in([_env.read_json(p) for p in f["boards"].values()], [])
    for p in (OUT / "caption.md", Path("brief.md"), OUT / "review.html"):
        if p.exists():
            texts.append(p.read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    order = (_env.read_json("storyboards/boards.json") or {}).get("order") or []
    full = [t for t in order if all((Path("storyboards") / t / x).exists() for x in ("board-reel.json", "storyboard.md", "sheet.png"))]
    shown = (OUT / "boards.png").exists()
    res("boards", len(order) == 3 and len(full) == 3 and shown,
        f"{len(full)} of 3 styles with the board, storyboard.md and sheet.png" + ("" if shown else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    chosen = win.get("board") in order and (win.get("by") == "person" or win.get("swap_passed"))
    res("vote", chosen, f"the look {win.get('board')}, " + ("the person's pick" if win.get("by") == "person" else
        "the panel's board" + ("" if win.get("swap_passed") else ", without a passed swap test")))
    listed = {c["id"] for c in (_env.read_json(f["boards"]["reel"]) or {}).get("clips") or []}
    got = set(((_env.read_json("clips.json") or {}).get("clips") or {}).keys())
    res("clips", listed <= got, f"{len(listed & got)} of {len(listed)} clips accounted for in clips.json" + ("" if listed <= got else ": run clips.py normalize"))
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    film = FILMS["reel"][0]
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        same = film.exists() and last.get("film") == sha(film)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"])
        scores = [] if bad else [last["critics"][c]["boards"]["film"]["scores"][k] for c in vote.CUT_PANEL for k in vote.CRITERIA]
        named = Path("brief.md").exists() and "## the scores" in Path("brief.md").read_text()
        res("critic", same and not bad and (vote.at_bar(scores) or (len(rounds) >= 2 and named)),
            f"round {len(rounds)}, " + (bad[0] if bad else f"mean {sum(scores) / len(scores):.2f}, lowest {min(scores)}")
            + ("" if same else "; the round is not for the current out/film.mp4"))
    cap = (OUT / "caption.md").read_text() if (OUT / "caption.md").exists() else ""
    lower = (_env.read_json("taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    extra = sorted(p.name for p in OUT.iterdir() if p.name not in DELIVERABLES) if OUT.is_dir() else []
    res("deliver", reg and (OUT / "review.html").exists() and Path("brief.md").exists() and not extra,
        f"caption {len(cap.split())} words, {len(tags)} hashtags" + ("" if (OUT / "review.html").exists() else "; review.html missing")
        + ("" if Path("brief.md").exists() else "; build/brief.md missing")
        + (f"; out/ holds what is not posted: {extra}" if extra else ""))
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
    a = ap.parse_args()
    _env.enter_build()
    if a.cmd == "timed":
        res, f = timed_checks()
        return report(res, "qa/timed.json", f, "TIMED")
    if a.cmd == "check":
        scale = proof.scale(FILMS["reel"][0])
        if scale != 1:
            print(proof.reading(Path("out") / proof.of(FILMS["reel"][0]).name))
        res, f, _ = film_checks(scale=scale)
        return report(res, "qa/check.json", f, "CHECKS")
    res, f = gate_checks()
    return report(res, "qa/gate.json", f, "GATE")


if __name__ == "__main__":
    sys.exit(main())
