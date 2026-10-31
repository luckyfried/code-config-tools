#!/usr/bin/env python3
"""Movement 5: the measured checks on the rendered film and stories, and the gate before delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the renders only; writes qa/check.json (film.py render runs it after every render)
    python3 S/scripts/qa.py gate      # every check below; writes qa/gate.json; exit 0 only when all pass

Each command writes its own record and leaves the other's, so qa/check.json always describes the delivered film. The
gate reports and never judges taste: the measured checks fail on a broken file, and the critics' scores and the timed
reads are stated against the bar, never a reason to refuse the film.

Every figure is measured again from the files in the run's out/, never read back from what film.py wrote. Two
figures are written beside the checks and are never a pass or a fail: the critic reads them with the strips, and a
held composition is quiet by design.
  cuts      the film's and (when made) the series' cuts, as planned and as the picture shows them, and cuts a minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them

check (the renders):
  film      out/film.mp4, the reel, is 1080x1920 H.264 High yuv420p at 30 fps and runs the board's reel (+-0.5 s)
  length    when the person asked for a length (the board's ask.seconds), the reel is that many seconds to the frame
            (seconds x 30 frames) and the film runs it within a frame
  series    when the person asked for it (the board's ask.series), out/series.mp4 is the same and runs 15 s a card
            (+-0.5 s); unasked, there is no out/series.mp4
  cards     3 or 4 cards in cards.json, each a 1080x1920 PNG still and a 15 +-0.5 s 1080x1920 H.264 story
  audio     every video carries AAC at 150 kbps or more; the film and the series (when made) sit at -14 LUFS +-1 LU; and with the
            reel's sound cues its effects stem sits music.FX_UNDER_BED_LU under the bed within 0.05 LU (both
            integrated, from music.json); the row names the two numbers and the cue and beat counts, and refuses
            nothing on count
  stop      the film's sound falls silent within RING s of the board's stop, where the ask lands, and stays silent to
            the end (silencedetect at SILENT dB)
  black     no black stretch of 0.4 s or more in any video (ffmpeg blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) in the film starting before the board's stop
            (more than SETTLE s before it),
            nor anywhere in the series when made: frames that repeat, as a stalled render's do; the grain moving under a held
            composition is change, and the still the reel holds from its stop to the end is the ending
  hook      the film and the series (when made) move within their first 30 frames
  render    the render failed no job and its checks found nothing (FONT_ERROR, IMAGE_ERROR, RENDER_ERROR in
            render-report.json)
  look      every card still wears the board's colors: its ground (the plates the words stand on) on at least
            GROUND of the frame and its ink on at least INK; with a look the person gave, those are its palette's
gate (adds):
  board     the rendered board passes storyboard.py's checks again against month.json (structure, the swap test,
            the monotony read, words, look, counts), and its sheets rendered with no finding
  timed     critic/timed.json holds the four reads made for this board; the row states each one's result
  text      no placeholder in the words on the cards and the reel, the caption, the run's brief or the review page
  register  the caption is in their register: their case, no '!' when they use none, 1 to 10 hashtags
  template  the run's template.json carries the style, the type, the palette, the axis rule, every card's devices and the reel
  research  taste.md carries its five headings and taste.json exists
  vote      vote.md and winner.json exist and the rendered board is the winner
  critic    the latest cut round in critic/ is for these files and filled in (after the first round, with what was
            fixed and a read of the new frames); the row states every rule's score against vote.BAR
  deliver   out/ holds out/cover.png, caption.md, review.html and the three looks (boards.png, looks/) beside the films and
            the cards, and nothing else; the review page names no critic, score or rule
"""
import argparse
import concurrent.futures as cf
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import music  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402
from compose import look  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|lorem|ipsum|\{\{|\}\}|\bXXX\b|PLACEHOLDER|undefined|\bNaN\b|\bNone\b|@handle\b|your_handle")
CARD_S = 15
SLACK = 0.5
# a color is on a frame when its pixels lie within NEAR of it on every channel over at least this share of the frame
NEAR = 32
GROUND, INK = 0.02, 0.002
BAD = ("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR")
HEADINGS = ("you are", "you like", "your style is", "your voice is", "avoid")
# words of the vote that stay in brief.md and never reach the person's page
TOLD = ("critic", "critics", "score", "scores", "bar", "r1", "r2", "r3", "r4", "r5", "r6", "r7")
# what out/ may hold: the deliverables and nothing a viewer could mistake for them
DELIVERABLE = re.compile(r"film\.mp4|series\.mp4|cover\.png|caption\.md|review\.html|boards\.png|looks/[1-3]-[a-z-]+\.png|cards/\d\d-story\.(mp4|png)")
# the film is silent from at most RING s after its stop (the last hit's ring, music.RING) to its end, read at SILENT dB
RING, SILENT = music.RING + 0.15, -50


def probe(p, spawn=subprocess.run):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
               "-of", "json", str(p)], capture_output=True, text=True)
    pr = json.loads(r.stdout or "{}")
    v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in pr.get("streams", []) if s.get("codec_type") == "audio"), None)
    return v, a, float(pr.get("format", {}).get("duration") or 0)


def shares(png, hexes):
    """{color: the share of the frame's pixels within NEAR of it on every channel}, read at full size, since a line of
    type is a few pixels wide; None when the file is not an image."""
    from PIL import Image, ImageChops, UnidentifiedImageError
    try:
        im = Image.open(png).convert("RGB")
    except (OSError, UnidentifiedImageError):
        return None
    out = {}
    for h in hexes:
        rgb = tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        near = [c.point(lambda v: 255 if v <= NEAR else 0) for c in ImageChops.difference(im, Image.new("RGB", im.size, rgb)).split()]
        mask = ImageChops.multiply(ImageChops.multiply(near[0], near[1]), near[2])
        out[h] = round(mask.histogram()[255] / (im.size[0] * im.size[1]), 4)
    return out


def frame_look(run, board, cards):
    """(pass, detail): every card still carries the board's ground on GROUND of its frame and its ink on INK."""
    colors = board["system"]["colors"]
    given = (board.get("look") or {}).get("given") or {}
    seen = {x["png"]: shares(run / x["png"], [colors["bg"], colors["ink"]]) for x in cards if (run / x["png"]).exists()}
    off = [f"{k}: not an image" if v is None else f"{k}: ground {v[colors['bg']]:.1%}, ink {v[colors['ink']]:.1%}" for k, v in seen.items()
           if v is None or v[colors["bg"]] < GROUND or v[colors["ink"]] < INK]
    said = (f"the palette of {given.get('source') or 'their look'}" if given.get("palette") else f"the colors from {look.source(board.get('look') or {})}")
    said += f": {colors['bg']} ground and {colors['ink']} ink on every card still"
    if off:
        return False, said + "; off: " + "; ".join(off[:3])
    return bool(seen), said + " (" + ", ".join(f"{Path(k).stem} {v[colors['bg']]:.1%}/{v[colors['ink']]:.1%}" for k, v in seen.items()) + ")"


def png_size(p):
    head = Path(p).read_bytes()[:24]
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


# the last frames of a closing page's eased build, a small line fading in, read as still to freezedetect: a still
# stretch starting within SETTLE s of the stop is the page settling into it
SETTLE = 0.15


def frozen(video, before=float("inf"), spawn=subprocess.run):
    r = studio.ff("-i", video, "-vf", "freezedetect=n=-80dB:d=1.0", "-an", "-f", "null", "-", spawn=spawn)
    starts = [float(ln.split(":")[-1]) for ln in r.stderr.splitlines() if "freeze_start" in ln]
    return [t for t in starts if t < before - SETTLE]


def held_from(board):
    """Where the reel holds its picture still to the end (its `stop` cue), in seconds; never, without one."""
    r = board.get("reel") or {}
    stop = next((c["at"] for c in r.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / r["bpm"] if stop is not None else float("inf")


def blacks(video, spawn=subprocess.run):
    r = studio.ff("-i", video, "-vf", "blackdetect=d=0.4:pix_th=0.10", "-an", "-f", "null", "-", spawn=spawn)
    return [ln.split("]")[-1].strip() for ln in r.stderr.splitlines() if "black_start" in ln]


def loudness(video, spawn=subprocess.run):
    r = studio.ff("-i", video, "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-", spawn=spawn)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def mixed(track, beats):
    """The reel's mix as music.json records it: a pass when it has no sound cues, or its effects stem sits
    music.FX_UNDER_BED_LU under its bed within 0.05 LU; and the words that say so."""
    cues = track.get("sound_cues") or 0
    under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
    said = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (the rule: {music.FX_UNDER_BED_LU})"
            if under is not None else "no effects stem measured")
    return not cues or (under is not None and abs(under - music.FX_UNDER_BED_LU) <= 0.05), f"{said}; {cues} sound cues over {beats} beats"


def silences(video, spawn=subprocess.run):
    """[(start, end or None)] of every stretch of the video's sound under SILENT dB for 0.2 s or more."""
    r = studio.ff("-i", video, "-af", f"silencedetect=n={SILENT}dB:d=0.2", "-vn", "-f", "null", "-", spawn=spawn)
    starts = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", r.stderr)]
    ends = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", r.stderr)]
    return [(s, ends[i] if i < len(ends) else None) for i, s in enumerate(starts)]


def stopped(quiet, stop, end):
    """(pass, words): the sound falls silent within RING s of the stop and stays silent to the end."""
    last = next(((s, e) for s, e in quiet if stop - 0.05 <= s <= stop + RING and (e is None or e >= end - 0.05)), None)
    if last:
        return True, f"the music stops on the ask at {stop:.2f} s; silent from {last[0]:.2f} s to the end at {end:.2f} s"
    return False, f"the music stops on the ask at {stop:.2f} s; no silence from there to the end at {end:.2f} s (silences: {quiet[:3]})"


def spec(v, secs, want):
    return ((v.get("width"), v.get("height")) == (1080, 1920) and v.get("codec_name") == "h264" and v.get("profile") == "High"
            and v.get("pix_fmt") == "yuv420p" and v.get("r_frame_rate") == "30/1" and abs(secs - want) <= SLACK)


def describe(v, secs):
    return f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} {v.get('r_frame_rate')}, {secs:.2f} s"


class Checks:
    """Checks, each a pass or a fail, and figures, measured and shown and never passed or failed."""

    def __init__(self):
        self.rows = []

    def add(self, name, ok, detail, **fig):
        self.rows.append({"check": name, "pass": bool(ok), "detail": detail, **({"figures": fig} if fig else {})})

    def figure(self, name, detail, values):
        self.rows.append({"check": name, "pass": None, "detail": detail, "figures": values})


def render_checks(run, c, spawn=subprocess.run):
    out = run / "out"
    board = _env.read_json(run / "film.json")
    cards = (_env.read_json(run / "cards.json") or {}).get("cards") or []
    series = bool(((board or {}).get("ask") or {}).get("series"))
    if not board or not (out / "film.mp4").exists() or series and not (out / "series.mp4").exists():
        c.add("film", False, f"film.json, out/film.mp4 or the out/series.mp4 they asked for is missing in {run}: run film.py render")
        return {}
    r = board["reel"]
    series_s = sum(studio.card_frames(board, x) for x in board["beats"]) / studio.FPS
    films = {"film": (out / "film.mp4", r["cuts"], r["frames"] / r["fps"])}
    if series:
        films["series"] = (out / "series.mp4", studio.cut_frames(board), series_s)
    else:
        c.add("series", not (out / "series.mp4").exists(), "not asked for, and not made" if not (out / "series.mp4").exists()
              else "out/series.mp4 is there, and the person did not ask for the cards as one video")
    pool = cf.ThreadPoolExecutor(16)
    jobs, videos = {}, {}
    for name, (mp4, planned, want) in films.items():
        v, a, secs = probe(mp4, spawn)
        c.add(name, spec(v, secs, want), describe(v, secs) + f" (wants {want:.2f} s), {mp4.stat().st_size / 1e6:.1f} MB, {mp4.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        jobs[name] = pool.submit(studio.measure, mp4, planned, run / "qa", spawn)
        videos[name] = (mp4, a)
    bad = []
    for x in cards:
        png, mp4 = run / x["png"], run / x["mp4"]
        sz = png_size(png) if png.exists() else None
        if sz != (1080, 1920):
            bad.append(f"{x['png']} " + (f"is {sz[0]}x{sz[1]}" if sz else "is missing"))
        if not mp4.exists():
            bad.append(f"{x['mp4']} is missing")
            continue
        v, a, secs = probe(mp4, spawn)
        if not spec(v, secs, CARD_S):
            bad.append(f"{x['mp4']}: {describe(v, secs)}")
        videos[f"card {x['n']:02d}"] = (mp4, a)
    c.add("cards", 3 <= len(cards) <= 4 and len(cards) == len(board["beats"]) and not bad,
          f"{len(cards)} cards, each a 1080x1920 still and a 15 s story" + (f"; {'; '.join(bad[:3])}" if bad else ""))
    asked = (board.get("ask") or {}).get("seconds")
    if asked:
        secs = probe(out / "film.mp4", spawn)[2]
        c.add("length", r["frames"] == round(float(asked) * studio.FPS) and abs(secs - float(asked)) <= 1 / studio.FPS + 1e-3,
              f"asked for {float(asked):g} s: the reel is {r['frames']} frames, the film runs {secs:.3f} s")
    c.add("look", *frame_look(run, board, cards))
    weak = [f"{k}: {(a or {}).get('codec_name')} {int((a or {}).get('bit_rate') or 0) // 1000} kbps"
            for k, (mp4, a) in videos.items() if not a or a.get("codec_name") != "aac" or int(a.get("bit_rate") or 0) < 150000]
    lufs = {k: pool.submit(loudness, videos[k][0], spawn=spawn) for k in films}
    black = {k: pool.submit(blacks, mp4, spawn) for k, (mp4, _) in videos.items()}
    held = held_from(board)
    froze = {"film": pool.submit(frozen, out / "film.mp4", held, spawn)}
    quiet = pool.submit(silences, out / "film.mp4", spawn) if held != float("inf") else None
    if series:
        froze["series"] = pool.submit(frozen, out / "series.mp4", spawn=spawn)
    figs = {k: f.result() for k, f in jobs.items()}
    lufs = {k: f.result() for k, f in lufs.items()}
    off = [k for k, lu in lufs.items() if lu is None or abs(lu + 14) > 1.0]
    mix_ok, mix = mixed(_env.read_json(run / "music.json") or {}, len(r["beats"]))
    c.add("audio", not weak and not off and mix_ok, f"AAC on all {len(videos)} videos; " + ", ".join(f"{k} {lu} LUFS" for k, lu in lufs.items()) + f"; {mix}"
          + (f"; {weak}" if weak else "") + (f"; loudness off -14 in {off}" if off else ""), lufs=lufs)
    if quiet:
        c.add("stop", *stopped(quiet.result(), held, r["frames"] / r["fps"]))
    bl = [f"{k}: {b}" for k, f in black.items() for b in f.result()]
    c.add("black", not bl, f"{len(bl)} black stretches of 0.4 s or more in {len(videos)} videos" + (f": {bl[0]}" if bl else ""))
    fz = {k: f.result() for k, f in froze.items()}
    c.add("frozen", not any(fz.values()), f"frozen stretches of 1.0 s or more: film {fz['film']} (before its stop at {held:.2f} s)"
          + (f", series {fz['series']}" if series else ""))
    c.add("hook", all(figs[k]["hook_ok"] for k in films), "; ".join(f"{k} moves at frame {figs[k]['hook_frame']}" for k in films)
          + f" (inside {studio.HOOK_FRAMES})")
    for k in films:
        m = figs[k]
        c.figure("cuts", f"{k}: {m['cuts']} cuts, {m['cuts_per_minute']} a minute", {x: m[x] for x in ("cuts", "cuts_per_minute", "planned_cuts", "extra_scene_cuts")})
        c.figure("still", f"{k}: seconds under 0.5: {m['seconds_under_half']}, longest run {m['longest_run_under_half']}",
                 {x: m[x] for x in ("luma", "seconds_under_half", "longest_run_under_half", "strip", "strip2")})
    rep = _env.read_json(run / "render-report.json") or {}
    found = [f for f in rep.get("findings", []) if f.get("text", "").startswith(BAD)]
    c.add("render", rep and not rep.get("failed") and not rep.get("exit") and not found,
          f"{rep.get('failed', '?')} failed jobs, {len(found)} findings" + (f": {found[0]['text'][:160]}" if found else ""))
    return figs


def gate_checks(run, c):
    out = run / "out"
    board = _env.read_json(run / "film.json") or {}
    month = _env.read_json(run / "month.json")
    if board and month:
        res = storyboard.check_board(board, month)
        sheets = ((_env.read_json(run / "storyboards" / "sheets.json") or {}).get("boards") or {}).get(board["style"]) or {}
        found = sheets.get("findings")
        bad = [r["check"] for r in res if not r["ok"]]
        c.add("board", not bad and found == [], "; ".join(f"{r['check']}: {r['detail']}" for r in res)
              + (f"; rest sheet: {sheets.get('stills')} stills, {len(found)} findings" if found is not None else "; no rest sheet: run storyboard.py sheets"))
    else:
        c.add("board", False, "film.json or month.json is missing")
    tm_ = _env.read_json(run / "critic" / "timed.json") or {}
    mine = bool(board) and tm_.get("hash") == studio.board_hash(board)
    word = lambda v: "pass" if v is True else "fail" if v is False else str(v)
    reads = "; ".join(f"{k} {word((v or {}).get('pass'))}" for k, v in (tm_.get("reads") or {}).items())
    c.add("timed", mine and tm_.get("pass") is not None,
          (f"the four reads of this board: {reads}" if mine else "critic/timed.json is not for this board")
          + ("" if not mine or tm_.get("pass") is not None else "; the reads are not made: run vote.py timed"))
    texts = [w for x in board.get("beats", []) for w in storyboard.card_words(x)] + storyboard.reel_words(board)
    texts += [p.read_text() for p in (out / "caption.md", run / "brief.md", out / "review.html") if p.exists()]
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    c.add("text", texts and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    taste = _env.read_json(run / "taste.json") or {}
    reg = taste.get("register") or {}
    cap = (out / "caption.md").read_text() if (out / "caption.md").exists() else ""
    body, tags = re.sub(r"#\w+", "", cap), re.findall(r"#\w+", cap)
    ok = cap and (not reg.get("lowercase") or body == body.lower()) and (reg.get("exclamations") or "!" not in cap) and 1 <= len(tags) <= 10
    c.add("register", ok, f"caption {len(cap.split())} words, {len(tags)} hashtags"
          + (", lowercase like theirs" if reg.get("lowercase") else "") + ("" if reg.get("exclamations") else ", no '!'"))
    t = _env.read_json(run / "template.json") or {}
    miss = [k for k in ("style", "type", "palette", "axis", "cards", "reel") if not t.get(k)]
    rows = t.get("cards") or []
    nodev = [r.get("role") for r in rows if not r.get("devices")]
    c.add("template", t and not miss and not nodev and len(rows) == len(board.get("beats", [])) and t.get("style") == board.get("style"),
          f"style {t.get('style')}, {len(rows)} cards with their devices" + (f"; missing {miss}" if miss else "")
          + (f"; no devices on {nodev}" if nodev else ""))
    tm = (run / "taste.md").read_text().lower() if (run / "taste.md").exists() else ""
    heads = [h for h in HEADINGS if h not in tm]
    c.add("research", tm and not heads and taste, "taste.md and taste.json" + (f"; taste.md is missing {heads}" if heads else ""))
    win = _env.read_json(run / "winner.json") or {}
    c.add("vote", (run / "vote.md").exists() and win.get("board") and win.get("board") == board.get("style"),
          f"winner {win.get('board')} ({win.get('name')}), rendered {board.get('style')}")
    rs = vote.rounds(run)
    if not rs:
        c.add("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rs[-1])
        bad = vote.round_problems(rs)
        same = last.get("film") == vote.fingerprint(run)
        said = vote.against_bar(vote.standing(last))[2] if not bad else bad[0]
        c.add("critic", same and not bad, f"round {len(rs)}: {said}" + ("" if same else "; the round is not for the current files"))
    missing = [f for f in ("cover.png", "caption.md", "review.html") if not (out / f).exists()]
    extra = sorted(str(f.relative_to(out)) for f in out.rglob("*") if f.is_file() and not DELIVERABLE.fullmatch(str(f.relative_to(out))))
    page = (out / "review.html").read_text().lower() if (out / "review.html").exists() else ""
    told = [w for w in TOLD if re.search(rf"\b{w}\b", page)]
    c.add("deliver", not missing and not extra and not told, "out/ holds the films, cover.png, the cards, caption.md and review.html"
          + (f"; missing {missing}" if missing else "") + (f"; not a deliverable: {extra[:5]}" if extra else "")
          + (f"; the review page names {told}, which belong in brief.md" if told else ""))


def report(c, path, gate):
    bad = [r for r in c.rows if r["pass"] is False]
    for r in c.rows:
        print(f"{'FIG ' if r['pass'] is None else 'PASS' if r['pass'] else 'FAIL'}  {r['check']:9s} {r['detail']}")
    _env.write_json(path, {"pass": not bad, "checks": c.rows})
    print(("GATE GREEN" if not bad else f"GATE RED ({len(bad)} failing)") if gate else ("CHECKS PASS" if not bad else f"{len(bad)} CHECKS FAIL"))
    return 0 if not bad else 1


def checks(run, gate, spawn=subprocess.run):
    """The render checks, and with `gate` the gate's too; every process they start goes through `spawn`."""
    # the record names the strips the measures write again, so it goes before the first of them; the other command's
    # record stays
    (run / "qa" / ("gate.json" if gate else "check.json")).unlink(missing_ok=True)
    c = Checks()
    render_checks(run, c, spawn)
    if gate:
        gate_checks(run, c)
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    run = _env.run()
    return report(checks(run, a.cmd == "gate"), run / "qa" / f"{a.cmd}.json", a.cmd == "gate")


if __name__ == "__main__":
    sys.exit(main())
