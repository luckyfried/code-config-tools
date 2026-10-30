#!/usr/bin/env python3
"""Movement 5: the measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/qa.py timed   # the cut, before the film renders (film.py render refuses without it)
    python3 S/scripts/qa.py check   # the rendered film and what else was asked for (run before the critics watch the cut)
    python3 S/scripts/qa.py gate    # timed, check and the run's records; exit 0 only when every check passes

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strips, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them
timed reads them from the preview, check from the rendered reel.

timed (from film.json, preview/preview.json and critic/timed.json, all for the same cut):
  board     no finding on the reel, the landscape or the square board on disk, measured as qa runs (storyboard.py check: bounds, binding, formats,
            story, sound, length, hook)
  length    the cut runs inside its band (film.json `length`): 20 to 40 s, or from the longest film its stops' holds
            reach when that is under 20 s
  hook      the hook's first event lands inside the first 30 frames
  preview   preview/preview.json is for this cut
  monotony  the critic's monotony read of the timed cut (vote.py timed) passed, for this cut, with every strip seen
check (the rendered out/; film.py render runs it as its last step, so qa/check.json is always the delivered film's):
  format    out/film.mp4 1080x1920 H.264 High, out/film-16x9.mp4 1920x1080 and out/film-square.mp4 1080x1080 H.264:
            yuv420p, 30 fps, inside the cut's band
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated within 1 LU, true peak at -1.5 dBTP or under;
            with sound cues, the effects stem at least FX_UNDER_BED_LU - 1 LU (7) under the bed, as music.py master
            measured both (the line names the two and how many cues over how many beats)
  black     no black stretch of 0.4 s or more (blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting more than LANDING before the board's stop: frames that
            repeat, as a stalled render's do; the film grain moving under a held composition is change, and the still
            the board holds from its stop to the end is the ending
  safe      no render job failed, and no font, photograph or shader failed (render/film-report.json)
  cards     out/post.png 1080x1080 and out/story.png 1080x1920, neither an empty frame
gate adds:
  text      no placeholder in the words, the caption, the brief or the review page
  inputs    the taste, the cast and the places the draft read (source.json `inputs`) are the files in the run now
  places    every place of the year is named on screen (a stop's name on its strip)
  count     the caption states the count of places, and no other
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  boards    each of the three styles: its reel, landscape and square boards, storyboard.md and sheet.png; and out/boards.png
  vote      winner.json, from a ballot whose swap test the winner passed on all three compositions
  critic    the latest cut round in critic/ is complete and for this film; its scores are stated and never fail the gate
  deliver   out/ holds the three films, post.png, story.png, caption.md, review.html and boards.png and nothing else, brief.md is
            in the run's folder, and the caption is in their register
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
import music as music_mod  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILMS = {"reel": (Path("out/film.mp4"), (1080, 1920)), "landscape": (Path("out/film-16x9.mp4"), (1920, 1080)),
         "square": (Path("out/film-square.mp4"), (1080, 1080))}
CARDS = {Path("out/post.png"): (1080, 1080), Path("out/story.png"): (1080, 1920)}
DELIVERED = {*(p.name for p, _ in FILMS.values()), *(p.name for p in CARDS), "caption.md", "review.html", "boards.png"}
FLAT = 6.0
NOUNS = r"(?:places|cities|towns|stops|destinations|spots)"
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                    "fifteen sixteen seventeen eighteen nineteen twenty".split())}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def start(run):
    """How a check starts a process: through run.spawn under a command's lock (`run`, deliver's), so the lock lasts
    while it lives."""
    return run.spawn if run else subprocess.run


def probe(p, run=None):
    r = start(run)([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def detect(film, flt, key, run=None):
    r = start(run)([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def mix(info, cues, beats):
    """The effects under the music: the bed's and the effects stem's integrated loudness music.py master measured, the
    effects at least FX_UNDER_BED_LU - 1 LU under the bed. The cue count is named beside them and refuses nothing."""
    bed, fx = info.get("bed_lufs"), info.get("fx_lufs")
    if bed is None or fx is None:
        return False, f"music.json has no bed and effects loudness (run music.py master); {cues} sound cues over {beats} beats"
    return (bed - fx >= music_mod.FX_UNDER_BED_LU - 1,
            f"bed {bed} LUFS, effects {fx} LUFS, {bed - fx:.1f} LU under (at least {music_mod.FX_UNDER_BED_LU - 1}); "
            f"{cues} sound cues over {beats} beats")


# a hard ease (swiss-grid's quart) moves the picture less than a pixel in its last frames, so a film with no grain is
# still from up to this many seconds before the stop it lands on; a freeze that starts in that window is the landing
LANDING = 0.15

def held_from(f):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    stop = next((c["at"] for c in f.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / f["bpm"] if stop is not None else float("inf")


def loudness(film, run=None):
    """Integrated loudness (LUFS) and true peak (dBTP) as the AAC track decodes."""
    r = start(run)([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", "ebur128=framelog=quiet:peak=true", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    tp = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", r.stderr)
    return (float(m[-1]) if m else None), (float(tp[-1]) if tp else None)


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
    bad = storyboard.findings(storyboard.load_plans(f["style"]), storyboard.source()["photos"])
    res("board", not bad, f"{len(bad)} findings on the {f['style']} boards" + (f": {bad[0]}" if bad else ""))
    lo, hi = f["length"]
    res("length", storyboard.in_band(f["seconds"], f["length"]), f"{f['seconds']} s, band {lo:g}-{hi:g} s")
    res("hook", f["hook_frame"] <= storyboard.HOOK_FRAMES, f"the hook's first event at frame {f['hook_frame']}")
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
        read = ct.get("monotony") or {}
        miss = vote.unseen(ct)
        res("monotony", read.get("pass") is True and len((read.get("read") or "").split()) >= 25 and not miss,
            f"the critic's read: {'pass' if read.get('pass') else 'fail' if read.get('pass') is False else 'not written'}"
            + (f"; strips not seen: {', '.join(miss)}" if miss else ""))
    return res, f


def cards_check():
    """The posted image and the story card: each at its size, neither an empty frame."""
    _env.need("PIL")
    from PIL import Image, ImageStat
    bad = []
    for p, size in CARDS.items():
        if not p.exists():
            bad.append(f"{p.name} missing")
            continue
        with Image.open(p) as im:
            if im.size != size:
                bad.append(f"{p.name} is {im.size[0]}x{im.size[1]}, not {size[0]}x{size[1]}")
            elif ImageStat.Stat(im.convert("L").resize((108, 108))).stddev[0] < FLAT:
                bad.append(f"{p.name} is an empty frame")
    return not bad, "out/post.png 1080x1080 and out/story.png 1080x1920" + (f": {'; '.join(bad)}" if bad else "")


def film_checks(run=None):
    res = Checks()
    f = cut()
    info = _env.read_json("music.json") or {}
    music = info.get("file")
    held = held_from(f)
    if music and f.get("sound"):
        reel = (f.get("boards") or {}).get("reel")
        res("audio", *mix(info, len(f["sound"]), len((_env.read_json(reel) or {}).get("beats") or []) if reel else 0))
    measured = None
    for fmt, (film, size) in FILMS.items():
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film, run)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        ok = (v.get("width"), v.get("height")) == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and storyboard.in_band(secs, f["length"]) and (fmt != "reel" or v.get("profile") == "High")
        res("format", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s, {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        if music:
            lu, tp = loudness(film, run) if a else (None, None)
            br = int((a or {}).get("bit_rate") or 0)
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                and tp is not None and tp <= -1.5,
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated, true peak {tp} dBTP" if a else "no audio track"))
        black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start", run)
        res("black", not black, f"{film}: {len(black)} black stretches of 0.4 s or more")
        frozen = [ln for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start", run) if float(ln.split(":")[-1]) < held - LANDING]
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more before the stop at {held:.2f} s"
            + (f" ({frozen[0][-40:]})" if frozen else ""))
        if fmt == "reel":
            measured = studio.measure(film, f["cuts"], f["hook_frame"], strips="qa", run=run)
            _env.write_json("qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x[:160] for x in studio.faults(rep)] if rep else ["render/film-report.json is missing"]
    res("safe", not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    res("cards", *cards_check())
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


def norm(t):
    return " " + re.sub(r"[^\w]+", " ", str(t).lower()) + " "


def places_check(board, places):
    """Every place of the year is named on screen: a stop's name on its strip."""
    said = norm(" ".join(ln["text"] for c in board["route"]["cards"] for ln in c["lines"]))
    miss = [p["name"] for p in places if norm(p["name"]) not in said]
    return bool(places) and not miss, f"{len(places) - len(miss)} of {len(places)} places named on screen" + (f"; on no strip: {miss}" if miss else "")


def caption_counts(cap):
    """Every count the caption states beside a place noun, in digits or words ('11 places', 'eleven cities')."""
    body = re.sub(r"#\w+", "", cap.lower())
    found = [int(n) for n in re.findall(r"\b(\d+)\s+(?:\w+\s+)?" + NOUNS + r"\b", body)]
    found += [WORDS[w] for w in re.findall(r"\b(" + "|".join(WORDS) + r")\s+(?:\w+\s+)?" + NOUNS + r"\b", body)]
    return found


def gate_checks(run=None):
    """Every check of the gate; deliver runs them in its own process under its lock (`run`)."""
    tres, f = timed_checks()
    res, f, _ = film_checks(run)
    res = Checks(tres + res)
    boards = {fmt: _env.read_json(p) for fmt, p in f["boards"].items()}
    texts = words_in(list(boards.values()), [])
    for p in ("out/caption.md", "brief.md", "out/review.html"):
        if Path(p).exists():
            texts.append(Path(p).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    read = (_env.read_json("source.json") or {}).get("inputs") or {}
    moved = [n for n in storyboard.INPUTS if read.get(n) != storyboard.digest(n)]
    res("inputs", read and not moved, "the draft read the taste, the cast and the places in the run now" if read and not moved
        else f"changed since the draft: {', '.join(moved)}; run storyboard.py draft and the steps after it")
    places = (_env.read_json("source.json") or {}).get("places", {}).get("places") or []
    res("places", *places_check(boards["reel"], places))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    said = caption_counts(cap)
    res("count", places and said and set(said) == {len(places)}, f"the caption states {sorted(set(said)) or 'no count'}, the year has {len(places)} places")
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    need = [f"board-{fmt}.json" for fmt in storyboard.FORMATS] + ["storyboard.md", "sheet.png"]
    looks = storyboard.styles()
    full = [t for t in looks if all((storyboard.BOARDS / t / x).exists() for x in need)]
    res("boards", len(full) == len(looks) and Path("out/boards.png").exists(),
        f"{len(full)} of {len(looks)} styles with their reel, landscape and square boards, storyboard.md and sheet.png"
        + ("" if Path("out/boards.png").exists() else "; out/boards.png is missing: run storyboard.py sheets"))
    win = _env.read_json("winner.json") or {}
    res("vote", win.get("board") and win.get("swap_passed"), f"winner {win.get('board')}" + ("" if win.get("swap_passed") else ", without a passed swap test"))
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    film = FILMS["reel"][0]
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        same = film.exists() and last.get("film") == sha(film)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"])
        res("critic", same and not bad, f"round {len(rounds)}, " + (vote.stated(last) if not bad else bad[0])
            + ("" if same else "; the round is not for the current out/film.mp4"))
    their = (_env.read_json("taste.json") or {}).get("register", {})
    lower = their.get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    # a person who writes no hashtags gets none; one who does gets a few
    reg = cap and (not lower or body == body.lower()) and len(tags) <= 10 and (bool(tags) or not their.get("hashtags"))
    held = {p.name for p in Path("out").iterdir()} if Path("out").is_dir() else set()
    res("deliver", reg and held == DELIVERED and Path("brief.md").exists(),
        f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "")
        + (f"; out/ lacks {', '.join(sorted(DELIVERED - held))}" if DELIVERED - held else "")
        + (f"; out/ also holds {', '.join(sorted(held - DELIVERED))}" if held - DELIVERED else "")
        + ("" if Path("brief.md").exists() else "; brief.md missing"))
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
    _env.enter_run()
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
