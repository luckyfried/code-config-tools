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
  length    the cut runs inside the length band: 15-30 s for nine posts, the floor scaled down for fewer
  hook      the hook event lands inside the first 30 frames
  preview   preview/preview.json is for this cut
  monotony  the critic's monotony read of the timed cut (vote.py timed) passed, for this cut
check (the rendered out/):
  format    out/film.mp4 1080x1920, out/film-square.mp4 1080x1080, out/film-wide.mp4 1920x1080: H.264, yuv420p,
            30 fps, inside the length band
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU
  black     no black stretch of 0.4 s or more (blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting before the board's stop: frames
            that repeat, as a stalled render's do; the film grain moving under a held composition is change, and the
            still a board holds from its stop to the end is the ending
  safe      no render job failed, and no type left its safe area or failed to load (render/film-report.json)
  stills    out/story.png 1080x1920 and out/best-nine.png 1080x1080, each a closer at rest that shows every one of
            the nine, whole or as a slice at least bounds.SHOWN px on its short side
gate adds:
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  boards    every tone, each with its three boards, storyboard.md and sheet.png
  vote      winner.json, from a ballot whose swap test the winner passed on all three compositions
  critic    the latest cut round in critic/ is for this film, scores 4 or more, or the one fix is spent
  text      no placeholder in the words, the caption, the brief or the review page
  deliver   out/caption.md, out/review.html and out/brief.md, the caption in their register
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
import storyboard  # noqa: E402
import studio  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILMS = {"reel": (Path("out/film.mp4"), (1080, 1920)), "square": (Path("out/film-square.mp4"), (1080, 1080)),
         "wide": (Path("out/film-wide.mp4"), (1920, 1080))}
STORY, WALL = Path("out/story.png"), Path("out/best-nine.png")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(film, flt, key):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def held_from(f):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    board = _env.read_json((f.get("boards") or {}).get("reel", "")) if (f.get("boards") or {}).get("reel") else {}
    stop = next((c["at"] for c in (board or {}).get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / board["bpm"] if stop is not None else float("inf")


def loudness(film):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
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


def timed_checks():
    res = Checks()
    f = cut()
    n = posts_n()
    res("bounds", not f["findings"], f"{len(f['findings'])} findings on the three boards" + (f": {f['findings'][0]}" if f["findings"] else ""))
    lo, hi = storyboard.length_band(n)
    res("length", lo <= f["seconds"] <= hi, f"{f['seconds']} s, band {lo}-{hi} s")
    res("hook", f["hook_frame"] <= storyboard.HOOK_FRAMES, f"the hook event at frame {f['hook_frame']}")
    pv = _env.read_json("preview/preview.json") or {}
    if pv.get("hash") != f["hash"]:
        res("preview", False, "preview/preview.json is not for this cut: run film.py preview")
    else:
        res("preview", True, f"preview/preview.json, {pv['seconds']} s")
        figures(res, pv)
    ct = _env.read_json("critic/timed.json") or {}
    if ct.get("hash") != f["hash"]:
        res("monotony", False, "critic/timed.json is not for this cut: run vote.py timed and write the monotony read")
    else:
        read = (ct.get("monotony") or {})
        res("monotony", read.get("pass") is True and len((read.get("read") or "").split()) >= 25,
            f"the critic's read: {'pass' if read.get('pass') else 'fail' if read.get('pass') is False else 'not written'}")
    return res, f


def film_checks():
    res = Checks()
    f = cut()
    n = posts_n()
    lo, hi = storyboard.length_band(n)
    music = (_env.read_json("music.json") or {}).get("file")
    held = held_from(f)
    measured = None
    for fmt, (film, size) in FILMS.items():
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        ok = (v.get("width"), v.get("height")) == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and lo <= secs <= hi
        res("format", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s")
        if music:
            lu = loudness(film) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0,
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated" if a else "no audio track"))
        black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start")
        res("black", not black, f"{film}: {len(black)} black stretches of 0.4 s or more")
        frozen = [ln for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start") if float(ln.split(":")[-1]) < held - 0.04]
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more" + (f" ({frozen[0][-40:]})" if frozen else ""))
        if fmt == "reel":
            measured = studio.measure(film, f["cuts"], f["hook_frame"], strips="qa")
            _env.write_json("qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(("SAFE_BREACH", "FONT_ERROR", "RENDER_ERROR", "UNKNOWN_KIND", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings"
        + (f": {bad[0]}" if bad else ""))
    for png, size, fmt in ((STORY, (1080, 1920), "reel"), (WALL, (1080, 1080), "square")):
        sz = png_size(png) if png.exists() else None
        board = _env.read_json(f["boards"][fmt])
        whole = shown_at(board, f["rests"][fmt]["closer"])
        res("stills", sz == size and whole >= n, f"{png} {'at %dx%d' % sz if sz else 'is missing'}, {whole} of {n} photographs shown at the closer's rest")
    return res, f, measured


def shown_at(board, frame):
    """How many of the posts' photographs the board shows in the frame at `frame`: held whole, or as a slice showing
    at least bounds.SHOWN px on its short side."""
    f = 0
    for i, beat in enumerate(board["beats"]):
        if frame < f + beat["frames"]:
            sh = bounds.Shot(board, i, frame - f)
            F = bounds.framebox(sh.frame)
            return len({e.get("owner") for e in sh.items if (e["kind"] == "photo" and not e.get("empty") and bounds.inside(e["box"], F))
                        or (e["kind"] == "slice" and bounds.shown(e["poly"], F[2], F[3]) >= bounds.SHOWN.get(sh.frame.name, 0) - 0.5)})
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


def gate_checks():
    tres, f = timed_checks()
    res, f, _ = film_checks()
    res = Checks(tres + res)
    texts = words_in([_env.read_json(p) for p in f["boards"].values()], [])
    for p in ("out/caption.md", "out/brief.md", "out/review.html"):
        if Path(p).exists():
            texts.append(Path(p).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    full = [t for t in storyboard.TONES if all((Path("storyboards") / t / x).exists() for x in
                                               ("board-reel.json", "board-square.json", "board-wide.json", "storyboard.md", "sheet.png"))]
    res("boards", len(full) == len(storyboard.TONES), f"{len(full)} of {len(storyboard.TONES)} tones with three boards, storyboard.md and sheet.png")
    win = _env.read_json("winner.json") or {}
    res("vote", win.get("board") and win.get("swap_passed"), f"winner {win.get('board')}" + ("" if win.get("swap_passed") else ", without a passed swap test"))
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    film = FILMS["reel"][0]
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        sc = [v for c in last.get("critics", {}).values() for e in c.get("boards", {}).values() for v in (e.get("scores") or {}).values()]
        same = film.exists() and last.get("film") == sha(film)
        done = sc and all(isinstance(x, int) for x in sc)
        res("critic", same and done and (min(sc) >= 4 or len(rounds) >= 2),
            f"round {len(rounds)}, lowest {min(sc) if done else '?'}" + ("" if same else "; the round is not for the current out/film.mp4"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    res("deliver", reg and Path("out/review.html").exists() and Path("out/brief.md").exists(),
        f"caption {len(cap.split())} words, {len(tags)} hashtags" + ("" if Path("out/review.html").exists() else "; review.html missing")
        + ("" if Path("out/brief.md").exists() else "; brief.md missing"))
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
