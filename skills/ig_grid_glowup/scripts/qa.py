#!/usr/bin/env python3
"""The measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the board and the rendered films, posts and grid images (before the critics watch)
    python3 S/scripts/qa.py gate      # check and the run's records; exit 0 only when every check passes

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strip, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them
check reads them from the rendered reel.

board (board.json, the board storyboard.py pick made):
  bounds    each page's words inside the type area and the page's line box at a cap height of 40 px or more, off
            the photograph where the card sets them beside it, and the closer's header inside the type area, in every
            format
  length    the reel runs inside the length band: 15-30 s for nine posts, the floor scaled down for fewer
  hook      the hook event (the frame landing on the first post that breaks the grid) lands inside the first 30 frames
check (the rendered out/, for the formats render/film.json names; qa/check.json names the reel it measured):
  format    out/film.mp4 1080x1920, out/film-landscape.mp4 1920x1080 and out/film-square.mp4 1080x1080: H.264, yuv420p,
            30 fps, inside the length band
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU, and the effects stem
            music.py master measured sitting FX_UNDER_BED_LU - 1 LU or more under the bed; the row prints both
            loudness numbers, the cue and beat counts, the second each cue falls on, and the second the music stops
            as the ask lands, and refuses nothing on the count
  black     no black frame anywhere, not even one between two pictures (blackdetect, one frame long)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting before the board's stop: frames
            that repeat, as a stalled render's do; the still the board holds from its stop to the end is the ending
  cards     every held post's page with words read from the film's own frames over its hold (three frames, from its
            last word in to the frame before its words leave): its caption's ink, in the caption's color, found and
            inside the format's safe width; every held post whose photograph came with words shows them on its page
  safe      no render job failed and no font or image that failed to load (render/film-report.json); a page whose
            graphics context was lost or whose shaders failed is an attempt the renderer runs again
  swap      the critic's swap test on the nine as placed passes (critic/swap.json)
  posts     out/posts/ holds one 1080x1350 PNG per post of the plan, no two the same picture
  out       out/ holds the deliverables and nothing else: the three films, posts/, story.png (1080x1920), caption.txt
            (every post's caption), grid-after.png and review.html
  grid      grid-before.png (their grid now) and out/grid-after.png (the plan in place over it), when they have a feed;
            with none (an empty grid) there is no grid before and no row
gate adds:
  text      no placeholder in the board's words, the plan, the audit, the brief, the caption or the review page
  audit     audit.md names three or more findings about their grid, when they have a feed; with none there is
            nothing to audit and no row
  plan      plan.json passes plan.py check, and plan.md lists every post in order
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  stills    the three boards' sheets (storyboards/<L>/sheet.png), out/boards.png and the storyboard of the board picked
  pick      winner.json names this board, who picked it and why
  critic    the latest cut round in critic/ is for this film and complete as vote.py verdict takes it (whole scores and
            full paragraphs on the seven rules), and its verdict is SHIP or DELIVER: a FIX ONCE not yet made is red;
            DELIVER is green here, and brief.md states every score against the bar
  deliver   out/review.html and brief.md
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
import drive  # noqa: E402
import plan as plan_check  # noqa: E402
import storyboard as SB  # noqa: E402
import studio  # noqa: E402
import music  # noqa: E402
import vote  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILMS = {"reel": (Path("out/film.mp4"), (1080, 1920)), "landscape": (Path("out/film-landscape.mp4"), (1920, 1080)),
         "square": (Path("out/film-square.mp4"), (1080, 1080))}
POSTS = Path("out/posts")
BEFORE = Path("grid-before.png")
AFTER = Path("out/grid-after.png")
STORY = Path("out/story.png")
CAPTION = Path("out/caption.txt")
# everything out/ may hold: the deliverables
OUT = {*(f.name for f, _ in FILMS.values()), "posts", STORY.name, CAPTION.name, AFTER.name, "grid-before.png", "boards.png", "review.html"}


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


def held_from(board):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    reel = board["boards"]["reel"]
    stop = next((c["at"] for c in reel.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / reel["bpm"] if stop is not None else float("inf")


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


def board_of():
    board = _env.read_json("board.json")
    if not board:
        sys.exit("board.json is missing: run storyboard.py draft, sheets and pick first")
    return board


def board_checks():
    res = Checks()
    board = board_of()
    n = len(board["nine"])
    bad = board["check"]["faults"]
    res("bounds", board["check"]["pass"], f"{len(bad)} faults" + (f": {bad[0]}" if bad else " in every format"))
    lo, hi = SB.length_band(n)
    res("length", lo <= board["seconds"] <= hi, f"{board['seconds']} s, band {lo}-{hi} s")
    res("hook", board["hook_frame"] <= SB.HOOK_FRAMES, f"the hook event at frame {board['hook_frame']}")
    return res, board


def mix(track, reel):
    """The mix music.py master measured (music.json `track`): whether the effects sit far enough under the bed, and the
    line that says where they sit, how many cues play over the reel board's beats, the second each cue falls on, and
    where the music stops: on the stop cue, as the ask lands, with the picture held in silence after it."""
    cues = track.get("sound_cues") or 0
    under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track and "bed_lufs" in track else None
    said = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU - 1})"
            if under is not None else "no effects stem measured")
    sec = lambda c: c["at"] * 60 / reel["bpm"]
    sound = reel.get("sound") or []
    placed = ", ".join(f"{c['kind']} {sec(c):.2f} s" for c in sound)
    stop = next((c for c in sound if c["kind"] == "stop"), None)
    ends = (f"the music stops at {sec(stop):.2f} s as the ask lands and the profile holds in silence to "
            f"{reel['seconds']:.2f} s" if stop else "no stop cue: the music tails out over the last seconds")
    return ((not cues or (under is not None and under >= music.FX_UNDER_BED_LU - 1)),
            f"{said}; {cues} sound cues over {len(reel.get('beats') or [])} beats at {placed or 'none'}; {ends}")


def film_checks(run=None):
    """The rendered films, posts and grid images; under a command's lock (`run`) every probe starts through run.spawn."""
    res = Checks()
    board = board_of()
    lo, hi = SB.length_band(len(board["nine"]))
    done = _env.read_json("render/film.json") or {}
    if done.get("hash") != board["hash"]:
        res("format", False, "render/film.json is not for this board: run film.py render")
        return res, board, None
    with_music = done.get("music")
    placed, mixed = mix(_env.read_json("music.json") or {}, board["boards"]["reel"])
    held = held_from(board)
    measured = None
    for fmt in done["formats"]:
        film, size = FILMS[fmt]
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film, run)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        ok = (v.get("width"), v.get("height")) == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and lo <= secs <= hi
        res("format", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s, {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        if with_music:
            lu = loudness(film, run) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0 and placed,
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated" if a else "no audio track") + f"; {mixed}")
        black = detect(film, "blackdetect=d=0.01:pix_th=0.10", "black_start", run)
        res("black", not black, f"{film}: {len(black)} black stretches of a frame or more"
            + (f" (the first {black[0].split('black_start:')[-1].split()[0]} s)" if black else ""))
        frozen = [ln for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start", run) if float(ln.split(":")[-1]) < held - 0.04]
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more before the stop at {held:.2f} s"
            + (f" ({frozen[0][-40:]})" if frozen else ""))
        bad, n, widest = cards_check(board["boards"][fmt], fmt, film, run)
        bad += [f"{k} came with words and its page shows none" for k in words_lost(board["boards"][fmt], board["nine"])]
        res("cards", not bad, f"{film}: " + ("; ".join(bad[:3]) + (f" (and {len(bad) - 3} more)" if len(bad) > 3 else "") if bad else
                                             f"{n} held page frames, caption inside the safe width: "
                                             + ", ".join(f"{k} x {v[0]} to {v[1]}" for k, v in widest.items()) if n else
                                             "no photograph of the posts came with words, so no card to measure"))
        if fmt == "reel":
            Path("qa").mkdir(exist_ok=True)
            measured = studio.measure(film, board["cuts_at"], board["hook_frame"], strips="qa", run=run)
            _env.write_json("qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json("render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad,
        f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    sw = _env.read_json("critic/swap.json") or {}
    res("swap", sw.get("pass"), f"{len(sw.get('swap') or {})} photographs placed by detail" + "".join(f"; {o['at']}: {o['text']}" for o in sw.get("objections", []))
        if sw else "critic/swap.json is missing: run film.py render")
    res("posts", *posts_check(len(board["nine"])))
    res("out", *out_check(board, done["formats"]))
    if board.get("before"):
        res("grid", BEFORE.exists() and AFTER.exists(), f"grid-before.png {'there' if BEFORE.exists() else 'missing'}, "
            f"grid-after.png {'at %dx%d' % png_size(AFTER) if AFTER.exists() else 'missing'}")
    return res, board, measured


def hold_reads(times, pg):
    """The beats a held page is read on: its last word in, the middle of its hold and the frame before its words
    leave."""
    lock = sum(times["close"])
    t0 = max(lock + 0.35, drive.page_landed(pg) or lock)
    t1 = pg["sink"] - 1 / drive.PULSE
    return sorted({round(t0, 3), round((t0 + t1) / 2, 3), round(t1, 3)} if t1 > t0 else {round(t1, 3)})


def card_frames(fb, fmt, film, out=Path("qa/cards"), run=None):
    """Each held post's page read from the rendered film over its hold, from its last word in to the frame before its
    words leave: on three frames, the left and right edges of the ink of its caption in the caption's own color, read
    along the rows its lines stand on, px. Returns [(post, frame, {caption})]."""
    _env.need("PIL")
    from PIL import Image
    W, H = fb["format"]["width"], fb["format"]["height"]
    holds = []
    for b in fb["beats"]:
        pg = b["layers"][0].get("page") if b["id"].startswith("post-") else None
        if not pg or not pg["lines"]:
            continue
        for t in hold_reads(b["layers"][0]["times"], pg):
            holds.append((b["id"], round(t * drive.PULSE), t, pg))
    if not holds:
        return []
    out.mkdir(parents=True, exist_ok=True)
    ns = sorted({n for _, n, _, _ in holds})
    for old in out.glob(f"{fmt}-*.png"):
        old.unlink()
    (run.spawn if run else subprocess.run)([_env.ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(film), "-vf",
                                            "select='" + "+".join(f"eq(n,{n})" for n in ns) + "'", "-vsync", "0",
                                            str(out / f"{fmt}-%02d.png")], check=True)
    shots = {n: Image.open(out / f"{fmt}-{i + 1:02d}.png").convert("RGB") for i, n in enumerate(ns)}
    found = []
    for name, n, t, pg in holds:
        px = shots[n].load()
        ink = [int(pg["color"][i:i + 2], 16) for i in (1, 3, 5)]
        # the caption's ink: a column holds it where two or more px of the line's rows stand within 60 of the
        # caption's color, from 40 px outside the line box to 40 px past it
        cols = set()
        for ln in pg["lines"]:
            cap = ln["size"] * drive.CAP["display"]
            rows = [round(ln["y"] - cap + cap * j / 8) for j in range(9)]
            for x in range(max(0, round(pg["box"][0] - 40)), min(W, round(pg["box"][2] + 40))):
                hits = sum(1 for y in rows if 0 <= y < H and sum(abs(px[x, y][c] - ink[c]) for c in range(3)) < 60)
                if hits >= 2:
                    cols.add(x)
        found.append((name, n, {"caption": (min(cols), max(cols)) if cols else None}))
    return found


def words_lost(fb, nine):
    """The pages that lost their line: each held post whose photograph came with words and whose page shows none."""
    came = {f"post-{p['n']}" for p in nine if p.get("caption")}
    lost = {b["id"] for b in fb["beats"] if b["id"].startswith("post-") and b["layers"][0].get("full")
            and not (b["layers"][0].get("page") or {}).get("lines")}
    return sorted(came & lost, key=lambda k: int(k.split("-")[1]))


def cards_check(fb, fmt, film, run=None):
    """Every held page frame of one format's film: its caption found, inside the safe width."""
    safe = fb["system"]["safe"][fmt]
    W = fb["format"]["width"]
    lo, hi = safe["left"] - 1, W - safe["right"] + 1
    seen = card_frames(fb, fmt, film, run=run)
    bad = [f"{name} at frame {n}: " + (f"no {what} ink found on the page" if e is None else
                                        f"the {what} runs {e[0]} to {e[1]}, the safe width {safe['left']} to {W - safe['right']}")
           for name, n, s in seen for what, e in s.items() if e is None or e[0] < lo or e[1] > hi]
    # the widest the caption runs over the frames it was found on; one found on none (a frame that came out black or
    # bare) has no width, and its frames are already named in `bad`
    spans = [s["caption"] for _, _, s in seen if s.get("caption")]
    widest = {"caption": (min(e[0] for e in spans), max(e[1] for e in spans))} if spans else {}
    return bad, len(seen), widest


def posts_check(m):
    files = [POSTS / f"{n:02d}.png" for n in range(1, m + 1)]
    have = [f for f in files if f.exists()]
    if len(have) < m or m == 0:
        return False, f"{len(have)} of {m} posts in out/posts/ (missing {[f.name for f in files if not f.exists()]})"
    sizes = {png_size(f) for f in have}
    _env.need("PIL")
    from PIL import Image
    cells = [list(Image.open(f).convert("L").resize((16, 20), Image.BILINEAR).tobytes()) for f in have]
    least = min((sum(abs(p - q) for p, q in zip(cells[i], cells[j])) / 320 for i in range(m) for j in range(i + 1, m)), default=99)
    return sizes == {(1080, 1350)} and least > 6, (f"{m} posts at {', '.join('%dx%d' % z for z in sorted(sizes))}, "
                                                   f"least difference between two posts {least:.1f}")


def out_check(board, formats):
    """out/ holds every deliverable of this render and nothing else."""
    extra = sorted(p.name for p in Path("out").iterdir() if p.name not in OUT) if Path("out").exists() else []
    need = [FILMS[f][0] for f in formats] + [STORY, CAPTION, AFTER]
    missing = [str(f) for f in need if not f.exists()]
    if STORY.exists() and png_size(STORY) != (1080, 1920):
        missing.append(f"{STORY} at 1080x1920 (it is {'%dx%d' % png_size(STORY)})")
    text = CAPTION.read_text() if CAPTION.exists() else ""
    # caption.txt carries each post's caption as the plan wrote it (the film's page carries the words the photograph
    # came with)
    slots = (_env.read_json("plan.json") or {}).get("slots") or []
    unsaid = [s["n"] for s in slots if (s.get("caption") or "").strip() and s["caption"].strip() not in text]
    ok = not extra and not missing and not unsaid
    return ok, (f"out/ holds {', '.join(sorted(p.name for p in Path('out').iterdir())) if Path('out').exists() else 'nothing'}"
                + (f"; not a deliverable: {extra}" if extra else "") + (f"; missing: {missing}" if missing else "")
                + (f"; caption.txt lacks the caption of posts {unsaid}" if unsaid else ""))


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("text", "caption", "lesson", "handle") and isinstance(v, str):
                acc.append(v)
            else:
                words_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            words_in(v, acc)
    return acc


def gate_checks(run=None):
    """board, check and the run's records; deliver calls it under its lock (`run`), so every probe holds the lock."""
    tres, board = board_checks()
    fres, board, _ = film_checks(run)
    res = Checks(tres + fres)
    texts = words_in({"boards": board["boards"], "nine": board["nine"], "handle": board.get("handle")}, [])
    for f in ("audit.md", "plan.md", "brief.md", "out/caption.txt", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    if board.get("before"):
        audit = Path("audit.md").read_text() if Path("audit.md").exists() else ""
        part = audit.split("## What your grid is doing", 1)[-1].split("\n## ", 1)[0] if audit else ""
        found = len(re.findall(r"^\d+\.\s+\S", part, re.M))
        res("audit", found >= 3, f"audit.md {'names %d findings' % found if audit else 'is missing'}")
    plan = _env.read_json("plan.json") or {}
    bad = plan_check.problems(plan) if plan else ["plan.json is missing"]
    md = Path("plan.md").read_text() if Path("plan.md").exists() else ""
    listed = [int(m) for m in re.findall(r"^\| (\d) \|", md, re.M)]
    m = len(plan.get("slots") or [])
    res("plan", not bad and m and listed == list(range(1, m + 1)), f"{m} posts, plan.md lists {listed}"
        + (f"; {bad[0]}" + (f" (and {len(bad) - 1} more)" if len(bad) > 1 else "") if bad else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    want = [Path("storyboards") / L / "sheet.png" for L in SB.LETTERS] + [Path("out/boards.png"), Path("storyboard.md")]
    gone = [str(p) for p in want if not p.exists()]
    res("stills", not gone, "the three sheets, out/boards.png and storyboard.md" if not gone else f"missing {gone}: run storyboard.py sheets and pick")
    win = _env.read_json("winner.json") or {}
    res("pick", win.get("board") == board["letter"] and win.get("hash") == board["hash"] and (win.get("reason") or "").strip(),
        f"board {win.get('board')} ({win.get('style')}), picked by {win.get('by')}: {(win.get('reason') or '').strip()[:120]}")
    rounds = sorted(Path("critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    film = FILMS["reel"][0]
    if not rounds:
        res("critic", False, "no cut round in critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        same = film.exists() and last.get("film") == sha(film)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"])
        got = None if bad else vote.decide(rounds)
        res("critic", same and got and got[0] != "FIX", f"round {len(rounds)}: " + (bad[0] if bad else got[1])
            + ("" if same else "; the round is not for the current out/film.mp4"))
    res("deliver", Path("out/review.html").exists() and Path("brief.md").exists(),
        ("out/review.html" if Path("out/review.html").exists() else "out/review.html missing") + ", "
        + ("brief.md" if Path("brief.md").exists() else "brief.md missing"))
    return res, board


def report(res, path, board, label):
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    Path(path).parent.mkdir(exist_ok=True)
    reel = FILMS["reel"][0]
    _env.write_json(path, {"pass": not bad, "hash": board["hash"], "film": sha(reel) if reel.exists() else None,
                           "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(f"{label} " + ("GREEN" if not bad else f"RED ({len(bad)} failing)") + f" -> {path}")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "check":
        res, board, _ = film_checks()
        return report(res, "qa/check.json", board, "CHECKS")
    res, board = gate_checks()
    return report(res, "qa/gate.json", board, "GATE")


if __name__ == "__main__":
    sys.exit(main())
