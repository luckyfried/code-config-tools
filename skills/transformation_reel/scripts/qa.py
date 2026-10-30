#!/usr/bin/env python3
"""Movement 5: the film's figures, and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/qa.py check     # the rendered cut in RUN/cut/: RUN/qa/check.json and RUN/qa/strip.png (2 fps)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes -> RUN/qa/gate.json

film.py render runs the check itself once the cut is in RUN/cut/, so RUN/qa/check.json always describes the cut there;
check.json and gate.json name the cut they measured (`film`, the digest of RUN/cut/film.mp4).

The figures are measured and shown, never passed or failed: the critic reads them beside the strips (film.py draft
writes the same ones for the timing round, on the timed cut), and a held composition is quiet by design.
  cuts       the planned moves (each beat boundary: the camera leaves the card it held) joined with every scene
             change ffmpeg scores over 0.12, one cut where the two fall within 0.2 s, and cuts per minute
  still      for every second, the mean absolute difference between its first and its last frame, both box-scaled to
             1/8 of the frame's size so grain does not count; the seconds under 0.5 and the lowest second
  sound      the board's sound cues, the last one before the stop, and the stop

The gate refuses:
  film      the reel, or a format the render made (the square and the 16:9 only when the person asked for them), is
            missing, is not its size (1080x1920, 1080x1080, 1920x1080), H.264 High yuv420p at 30 fps, is not the
            board's length, or runs past 60 s; or cut/ holds a film the render did not make (nobody asked for it)
  audio     music was found but a film has no AAC track near 192 kbps, or its loudness is off -14 LUFS by more than 1 LU,
            or, with sound cues, the effects stem sits less than music.FX_UNDER_BED_LU (8) LU under the bed (both
            integrated, from RUN/music.json); the row names the two numbers and the cue and beat counts, and refuses
            nothing on count
  hook      no event inside the first 30 frames (day one's photograph landing, and frames 0 and 30 the same)
  black     a black stretch of 0.4 s or more
  frozen    a frozen stretch (freezedetect at -80 dB) with 1.0 s or more of it before the board's stop: frames that
            repeat, as a stalled render's do; the picture the board holds from its stop to the end is the ending
  render    a render job that failed, a font or a photograph that did not load (FONT_ERROR, IMAGE_ERROR)
  rules     any of storyboard.py check's rules broken by the board as rendered, in any format
  cards     the cover or one of the three story cards is missing or not 1080x1920; the then/now card is not 1080x1080
            or its halves are one picture
  order     the film's photographs not in date order from day one to the latest, or one that is not a dated post
            (the film may leave ordinary posts out; it never leaves out day one or the latest)
  research  RUN/taste.md (you are / you like / your style / your voice / avoid) or RUN/taste.json is missing
  boards    one of the run's three looks (storyboard.styles_of) without its storyboard and sheet, out/boards.png (or
            cut/boards.png once delivered) missing, or a finding in RUN/storyboards/check.json
  vote      RUN/vote.md or RUN/winner.json missing, or the look made was not chosen and its styleframes failed the swap test
  timing    no passing timing round (vote.py timing) for the rendered board
  critic    the latest cut round is not for this cut, is a ballot the vote refuses, or its verdict is FIX ONCE (a rule under
            the bar has a lever and the one fix is not taken); the row states every rule's score against the bar and
            the rules nobody read, and never refuses on a score
  text      a placeholder in the film's words, the caption, the brief or the review page
  deliver   cut/caption.md, cut/review.html or RUN/brief.md is missing, or the caption is not in their register
  span      the caption names a span they never said, or leaves out the one they did ("fourteen months in")
"""
import argparse
import hashlib
import json
import operator
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PLACEHOLDER = re.compile(r"(?i:TODO|TBD|lorem|ipsum|XXX|PLACEHOLDER|@handle\b|your_handle)|\{\{|\}\}|\bundefined\b|\bNaN\b|\bNone\b")
LONGEST = 60
SIZES = {"reel": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}
FILES = {"reel": "film.mp4", "square": "film-square.mp4", "landscape": "film-16x9.mp4"}
NUMBER = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                                     "sixteen seventeen eighteen nineteen twenty".split())}
SPAN = re.compile(r"\b(\d+|an?|" + "|".join(NUMBER) + r")[\s-]+(weeks?|months?|years?)\b(?!\s+ago)", re.I)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def start(run):
    """How a measurement starts its process: through the lock's run.spawn when the caller holds the run's lock `run`
    (chunks.lock), else subprocess.run."""
    return run.spawn if run else subprocess.run


def ff(*args, run=None):
    return start(run)([_env.ffmpeg(), "-hide_banner", "-nostats", *args], capture_output=True, text=True)


def probe(p, run=None):
    r = start(run)([_env.ffprobe(), "-v", "error", "-show_entries",
                    "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration", "-of", "json", str(p)],
                   capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def yavg(video, flt, run=None):
    r = ff("-i", str(video), "-vf", flt + ",format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-",
           run=run)
    return [float(v) for v in re.findall(r"YAVG=([\d.]+)", r.stderr)]


def hook_ok(m):
    """An event inside the first 30 frames: the first beat's first entrance at frame 30 or sooner (frame 0 counts), and
    frames 0 and 30 differing by more than 1.0 at 1/8."""
    return m.get("hook_frame") is not None and m["hook_frame"] <= 30 and (m.get("hook_difference") or 0) > 1.0


def rest_line(video, fps, frames, w, h, run=None):
    """The difference between the first and the last frame of every second, box-scaled to `w` by `h`, as the mean
    absolute difference of their RGB values; a trailing part-second of two or more frames is compared the same way."""
    pick = f"eq(mod(n\\,{fps})\\,0)+eq(mod(n\\,{fps})\\,{fps - 1})+eq(n\\,{frames - 1})"
    r = start(run)([_env.ffmpeg(), "-v", "error", "-i", str(video), "-vf", f"select='{pick}',scale={w}:{h}:flags=area", "-fps_mode", "passthrough",
                    "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    n = w * h * 3
    fr = [r.stdout[i:i + n] for i in range(0, len(r.stdout) - n + 1, n)]
    return [round(sum(map(abs, map(operator.sub, fr[i], fr[i + 1]))) / n, 2) for i in range(0, len(fr) - 1, 2)]


def sound_of(board):
    """The board's sound: its cues, the last cue before the stop and the stop, in seconds."""
    k = 60 / board["bpm"]
    cues = [c for c in board["sound"] if c["kind"] != "stop"]
    stop = next(c["at"] for c in board["sound"] if c["kind"] == "stop")
    return {"cues": len(cues), "last": round(max(c["at"] for c in cues) * k, 2), "stop": round(stop * k, 2)}


def measure(video, tl, board, run=None):
    """The cut's figures (see the module's notes) and its hook; `run` is the run's lock when the caller holds it."""
    p = probe(video, run)
    secs = float(p.get("format", {}).get("duration") or 0)
    w, h = tl.get("width", 1080), tl.get("height", 1920)
    eighth = f"scale={w // 8}:{h // 8}:flags=area"
    r = ff("-i", str(video), "-vf", "scale=270:-2,select='gt(scene,0.12)',showinfo", "-an", "-f", "null", "-", run=run)
    scene = [float(x) for x in re.findall(r"pts_time:\s*([\d.]+)", r.stderr)]
    planned = sorted(c / tl["fps"] for c in tl["cuts"])
    extra = [t for t in scene if all(abs(t - c) > 0.2 for c in planned)]
    line = rest_line(video, tl["fps"], round(secs * tl["fps"]), w // 8, h // 8, run)
    low = min(range(len(line)), key=line.__getitem__) if line else None
    hook = yavg(video, f"select='eq(n\\,0)+eq(n\\,30)',{eighth}", run)
    n = len(planned) + len(extra)
    return {"style": tl["style"], "duration": round(secs, 2), "board_seconds": tl["seconds"], "cuts": n, "planned_cuts": len(planned),
            "extra_scene_cuts": [round(t, 2) for t in extra], "cuts_per_minute": round(n / (secs / 60), 1) if secs else 0,
            "rest_line": line, "still_seconds": [i + 1 for i, v in enumerate(line) if v < 0.5],
            "lowest_second": [low + 1, line[low]] if line else None, "hook_frame": tl.get("hook_frame"),
            "hook_difference": round(hook[-1], 2) if hook else None, "sound": sound_of(board)}


def summary(m):
    """The figures in one line."""
    s = m["sound"]
    return (f"{m['duration']} s, {m['cuts']} cuts ({m['cuts_per_minute']} a minute), seconds under 0.5 {m['still_seconds'] or 'none'}, "
            f"lowest second {m['lowest_second']}, first event at frame {m['hook_frame']}; {s['cues']} sound cues, "
            f"the last at {s['last']} s, the stop at {s['stop']} s")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def loudness(film, run=None):
    r = ff("-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-", run=run)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


class Checks(list):
    def add(self, name, ok, detail):
        self.append((name, bool(ok), detail))


def made():
    """The formats the last render made (RUN/render/report.json's `made`); the reel alone when the report names none."""
    m = (_env.read_json(_env.b("render", "report.json")) or {}).get("made") or {}
    return set(m.get("formats") or ["reel"]) | {"reel"}


def film_checks(res, run=None):
    import music
    import storyboard
    tl = _env.read_json(_env.b("timeline.json"))
    film = _env.read_json(_env.b("film.json")) or {}
    if not tl or not film:
        res.add("film", False, "RUN/timeline.json or RUN/film.json is missing: run film.py render first")
        return None
    style = film["board"]
    board = storyboard.lay_out(style)
    track = _env.read_json(_env.b("music.json")) or {}
    bad, audio = [], []
    formats = made()
    for fmt, name in FILES.items():
        f = _env.cut(name)
        if fmt not in formats:
            if f.exists():
                bad.append(f"cut/{name} is in cut/, and the render did not make it (nobody asked for it)")
            continue
        if not f.exists():
            bad.append(f"cut/{name} is missing")
            continue
        p = probe(f, run)
        v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
        a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        if (v.get("width"), v.get("height")) != SIZES[fmt] or v.get("codec_name") != "h264" or v.get("profile") != "High" or v.get("pix_fmt") != "yuv420p" \
                or v.get("r_frame_rate") != "30/1" or secs > LONGEST or abs(secs - tl["seconds"]) > 0.5:
            bad.append(f"cut/{name} is {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} {v.get('r_frame_rate')}, {secs:.1f} s")
        if track.get("file"):
            lu = loudness(f, run) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            if not a or a.get("codec_name") != "aac" or br < 150000 or lu is None or abs(lu + 14) > 1.0:
                audio.append(f"cut/{name}: {(a or {}).get('codec_name')} {br // 1000} kbps, {lu} LUFS")
    res.add("film", not bad, ", ".join(f"{f} {(n := _env.cut(FILES[f]).stat().st_size) / 1e6:.1f} MB, {n * 8e-6 / tl['seconds']:.1f} Mbit/s"
                                       for f in FILES if f in formats and _env.cut(FILES[f]).exists()) + f", {tl['seconds']:.1f} s each" + (f"; {'; '.join(bad)}" if bad else ""))
    if track.get("file"):
        cues = sound_of(board)["cues"]
        under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
        mixed = not cues or (under is not None and under >= music.FX_UNDER_BED_LU)
        said = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU})"
                if under is not None else "no effects stem measured") + f"; {cues} sound cues over {len(board['beats'])} beats"
        res.add("audio", not audio and mixed, "music under every film at -14 LUFS; " + said + (f"; {'; '.join(audio)}" if audio else ""))
    else:
        res.add("audio", True, "no music was found; no audio track is required")
    reel = _env.cut("film.mp4")
    if not reel.exists():
        return None
    m = measure(reel, tl, board, run)
    print(f"      figures   {summary(m)}")
    res.add("hook", hook_ok(m),
            f"first event at frame {m['hook_frame']}; frames 0 and 30 differ by {m['hook_difference']} at 1/8")
    black = [ln for ln in ff("-i", str(reel), "-vf", "blackdetect=d=0.4:pix_th=0.10", "-an", "-f", "null", "-", run=run).stderr.splitlines() if "black_start" in ln]
    res.add("black", not black, f"{len(black)} black stretches of 0.4 s or more")
    held = m["sound"]["stop"]
    said = ff("-i", str(reel), "-vf", "freezedetect=n=-80dB:d=1.0", "-an", "-f", "null", "-", run=run).stderr
    frozen = [float(x) for x in re.findall(r"freeze_start:\s*([\d.]+)", said)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([\d.]+)", said)]
    # a stretch counts for what of it stands before the stop: a closer that settles less than a second before the
    # stop and holds on into the ending is the ending, not a stall
    early = [t for k, t in enumerate(frozen) if min(ends[k] if k < len(ends) else held, held) - t >= 0.96]
    res.add("frozen", not early, f"{len(early)} frozen stretches of 1.0 s or more before the stop at {held} s" + (f" (from {early[0]} s)" if early else "")
            + (f"; the ending holds from {frozen[-1]} s" if frozen and not early else ""))
    rep = _env.read_json(_env.b("render", "report.json")) or {}
    found = [f["text"][:160] for f in rep.get("findings", []) if f["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res.add("render", rep and not rep.get("failed") and not found, f"{rep.get('jobs', 0)} jobs" + (f" on the {rep['device']}" if rep.get("device") else "") + f", {rep.get('failed', '?')} failed, "
            f"{len(found)} findings" + (f": {found[0]}" if found else ""))
    rows = storyboard.measured()
    rules = []
    storyboard.compose.use(style)  # the film's type is measured in the picked look's faces
    for fmt in FILES:
        b = storyboard.lay_out(style, fmt)
        rules += [f"{fmt}: {x}" for x in storyboard.check_board(b, rows, b["facts"])]
    res.add("rules", not rules, "type floor, safe lines, crop, numbers and the first event in three formats" + (f"; {len(rules)} findings: {rules[0]}" if rules else ""))
    res.add("cards", *cards_check())
    res.add("order", *order_check(board, rows))
    _env.write_json(_env.b("qa", "numbers.json"), m)
    strip = _env.b("qa", "strip.png")
    rows_n = -(-int(m["duration"] * 2) // 10)
    # the strip of this reel reaches its name whole, or the strip of another reel goes
    tmp = strip.with_name(".strip.part.png")
    r = ff("-v", "error", "-y", "-i", str(reel), "-vf", f"fps=2,scale=144:256:flags=area,tile=10x{rows_n}:padding=4:color=black", "-frames:v", "1", str(tmp), run=run)
    if r.returncode == 0 and tmp.exists():
        os.replace(tmp, strip)
    else:
        tmp.unlink(missing_ok=True)
        strip.unlink(missing_ok=True)
    return m


def cards_check():
    _env.need("PIL")
    from PIL import Image
    stories = [_env.cut("stories", n) for n in ("01-hook.png", "02-dense.png", "03-closer.png")]
    tn = _env.cut("then-now.png")
    cover = _env.cut("cover.png")
    miss = [str(p.name) for p in stories + [tn, cover] if not p.exists()]
    if miss:
        return False, f"missing: {', '.join(miss)}"
    sizes = [png_size(p) for p in stories]
    if png_size(cover) != (1080, 1920):
        return False, f"cover.png is {png_size(cover)}, not 1080x1920"
    im = Image.open(tn).convert("L")
    w, h = im.size
    a, b = [list(x.resize((24, 24), Image.BILINEAR).tobytes()) for x in (im.crop((0, 0, w // 2, h)), im.crop((w // 2, 0, w, h)))]
    diff = sum(abs(p - q) for p, q in zip(a, b)) / len(a)
    ok = all(s == (1080, 1920) for s in sizes) and (w, h) == (1080, 1080) and diff > 4
    return ok, f"three story cards at {sorted(set(sizes))}, cover.png 1080x1920, then-now.png {w}x{h}, its halves differ by {diff:.1f}"


def order_check(board, rows):
    """The cards in date order from day one to the latest, each a dated post (the film may leave ordinary posts out)."""
    cards = board["film"]["cards"]
    dates = [c["date"] for c in cards]
    ids = {r["id"] for r in rows}
    stray = [c["id"] for c in cards if c["id"] not in ids]
    ok = not stray and dates == sorted(dates) and dates[0] == rows[0]["date"] and dates[-1] == rows[-1]["date"]
    return ok, (f"{len(cards)} of {len(rows)} photographs from {dates[0]} to {dates[-1]}" + ("" if dates == sorted(dates) else "; out of date order")
                + (f"; not a dated post: {', '.join(stray)}" if stray else ""))


def spans(text):
    """Each span the text names ("fourteen months", "2 years"), in figures, so "fourteen months" and "14 months" match."""
    return [re.sub(r"\b(" + "|".join(NUMBER) + r")\b", lambda m: str(NUMBER[m.group(1)]), m.group(0).lower()).replace("-", " ")
            for m in SPAN.finditer(text or "")]


def span_check(cap, facts):
    """The caption carries the span the way the closer does: in their own words where they say it, and otherwise not at
    all (their dates carry it), so a span they never said never reaches the post."""
    own, named = spans((facts or {}).get("said")), spans(cap)
    other = [x for x in named if x not in own]
    ok = not other and (not own or own[0] in named)
    return ok, (f"they say {own[0]!r}" if own else "they never say the span") + f"; the caption says {named or 'no span'}" + (f"; names another: {other}" if other else "")


def gate_checks(res, run=None):
    import storyboard
    m = film_checks(res, run)
    film = _env.read_json(_env.b("film.json")) or {}
    board = storyboard.lay_out(film["board"]) if film.get("board") else None
    tm = _env.b("taste.md").read_text().lower() if _env.b("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res.add("research", tm and not heads and _env.b("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    sb = _env.b("storyboards")
    chk = _env.read_json(sb / "check.json") or {}
    found = sum(len(v) for by in chk.values() for v in by.values())
    # a board's sheet is written after the last of its styleframes, so it is their completion
    looks = storyboard.styles_of(_env.read_json(_env.b("taste.json")) or {})
    full = [t for t in looks if (sb / t / "storyboard.json").exists() and (sb / t / "sheet.png").exists()]
    shown = _env.out("boards.png").exists() or _env.cut("boards.png").exists()
    res.add("boards", len(full) == len(looks) and shown and chk and not found,
            f"{len(full)} of {len(looks)} looks with storyboard.json and its sheet; boards.png {'there' if shown else 'missing'}; "
            f"{found} findings in check.json")
    win = _env.read_json(_env.b("winner.json")) or {}
    swap = (win.get("swap") or {}).get(win.get("board"), {})
    res.add("vote", _env.b("vote.md").exists() and win.get("board") and (win.get("chosen") or (swap and all(swap.values()))),
            f"the look {win.get('board')}, " + (f"chosen ({win['chosen']})" if win.get("chosen") else "recommended by the vote")
            + f"; swap test {swap or 'not answered'}")
    timing = _env.read_json(_env.b("critic", "timing.json")) or {}
    import film as filmpy
    res.add("timing", board and timing.get("pass") and timing.get("board_sha") == filmpy.board_sha(board),
            f"timing round {'passed' if timing.get('pass') else 'not passed'}" + "".join(f"; {k} not read in this session" for k in timing.get("unread") or [])
            + ("" if not board or timing.get("board_sha") == filmpy.board_sha(board) else " (for another board)"))
    import vote
    rounds = vote.rounds()
    reel = _env.cut("film.mp4")
    if not rounds:
        res.add("critic", False, "no cut round in RUN/critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        same = reel.exists() and last.get("film") == sha(reel)
        bad = vote.problems(last, vote.CUT_PANEL, ["film"])
        what, rule, why = vote.outcome(rounds) if not bad else (None, None, None)
        res.add("critic", same and not bad and what != "FIX ONCE",
                f"round {len(rounds)}, " + (bad[0] if bad else f"{vote.scores_line(last)}; {what}: "
                                            + (f"{rule} has a lever, take the one fix ({why})" if what == "FIX ONCE" else why))
                + ("" if same else "; the round is not for the current cut/film.mp4"))
    texts = storyboard.words_of(board) if board else []
    for f in (_env.cut("caption.md"), _env.b("brief.md"), _env.cut("review.html")):
        if f.exists():
            texts.append(f.read_text())
    hits = sorted({x.group(0) for t in texts for x in PLACEHOLDER.finditer(t)})
    res.add("text", texts and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    cap = _env.cut("caption.md").read_text() if _env.cut("caption.md").exists() else ""
    lower = (_env.read_json(_env.b("taste.json")) or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    res.add("deliver", reg and _env.cut("review.html").exists() and _env.b("brief.md").exists(),
            f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "")
            + ("" if _env.cut("review.html").exists() else "; review.html missing") + ("" if _env.b("brief.md").exists() else "; RUN/brief.md missing"))
    res.add("span", *span_check(cap, (board or {}).get("facts")))
    return m


def report(res, name, m=None):
    bad = [r for r in res if not r[1]]
    for n, ok, detail in res:
        print(f"{'PASS' if ok else 'FAIL'}  {n:9s} {detail}")
    reel = _env.cut("film.mp4")
    _env.write_json(_env.b("qa", name), {"pass": not bad, "film": sha(reel) if reel.exists() else None, "numbers": m,
                                         "checks": [{"check": n, "pass": o, "detail": d} for n, o, d in res]})
    print(("GATE " + ("GREEN" if not bad else f"RED ({len(bad)} failing)")) if name == "gate.json" else ("CHECKS PASS" if not bad else f"{len(bad)} CHECKS FAIL"))
    print(f"-> {_env.b('qa', name)}")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    res = Checks()
    if a.cmd == "check":
        m = film_checks(res)
        return report(res, "check.json", m)
    m = gate_checks(res)
    return report(res, "gate.json", m)


if __name__ == "__main__":
    sys.exit(main())
