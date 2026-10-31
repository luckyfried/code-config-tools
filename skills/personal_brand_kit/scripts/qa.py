#!/usr/bin/env python3
"""Movement 5: the measured checks on the timed cut, and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the cut (cut.mp4, the reel as delivered) before the film renders: qa/check.json,
                                      # read by the critic
    python3 S/scripts/qa.py gate      # the film, what was asked for beside it and everything delivered; exit 0 only when all pass

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strips, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them

check holds the cut to:
  film      the board's size, H.264, yuv420p, 30 fps, 12-30 s
  black     no black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting before the closer: frames
            that repeat, as a stalled render's do; the film grain moving under a held composition is change, and the
            closer at rest from wherever it settles is the ending
  white     no frame over 0.97 mean luma: a frame that bright is a dropped frame or a shader that failed to
            compile, never a composition
  hook      the hook event lands inside the first 30 frames
  safe      no render job failed and no font or photograph failed to load (render/cut-report.json); a shader that
            failed to compile fails its attempt in the renderer, so a job that succeeded drew every frame
  bounds    storyboard.py found no bounds finding on the reel, the square or the wide board (film.json)
  subject   on every board, the hook's photograph is laid so its subject (studio.json's `subject`), and on a plain
            photograph the subject's ROOM, sits HELD or more of the frame inside each side
  brand     brand.json passes design/brand.schema.json, and its pillar shares sum to 1 within 0.01
  plan      out/plan.md carries 30 entries on 30 different dates, each naming a pillar and each with a caption
  audio     the cut's sound, which is the delivered reel's (film.py render copies the cut to out/film.mp4): the audio
            row the gate holds every film to, below

gate holds out/film.mp4 (reel), out/film-square.mp4 and out/film-wide.mp4 (render/film-report.json's `made`) to
film, black, frozen, white and safe, each at its own size; a render with no published report fails safe. It
holds the boards to bounds and subject, and adds:
  audio     with music, every film has an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU, and with sound
            cues the effects stem sits at least music.FX_UNDER_BED_LU under the bed (both integrated, from
            music.json); the row names the film's own loudness, the master's, the bed's and the effects', the gap,
            the cue and beat counts, where the film goes quiet against the board's stop, and where the bed came from,
            and refuses nothing on count or on the quiet
  cards     out/story.png is 1080x1920 (the reel's cover, the hook at rest) and out/post.png 1080x1080 (the square's peak moment)
  stills    when the render made them (--also stories): out/stills/ holds the stills out/stills.json names (one to
            ten, each 1080x1080, all different); when it did not, out/ holds no still or stills.json
  out       out/ holds the deliverables and nothing else: the films, the cards, the stills when asked for, the
            caption, the brand file, the plan and the review page
  text      no placeholder string in the film's words, the caption, the brief or the review page
  research  taste.md (you are / you like / your style / your voice / avoid) and taste.json
  boards    the three looks, each with its three boards, storyboard.md and sheet.png
  vote      vote.md and winner.json, the look picked by the person, or by their taste with its reason
  critic    the critics' verdict is for the cut the reel was made from, and ships it at the bar or spent its one fix
  deliver   out/caption.md, out/review.html, out/brand.json and out/plan.md, and brief.md (the run's notes) beside
            out/, the caption in their register
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
import brand as brandkit  # noqa: E402
import music  # noqa: E402
import storyboard  # noqa: E402

# code values (None, NaN, undefined) leak in their own case and as whole words; "none" and "banana" are English
PLACEHOLDER = re.compile(r"(?i:lorem|ipsum|placeholder|your_handle|@handle\b)|\{\{|\}\}|\b(?:TODO|TBD|XXX|undefined|NaN|None)\b")
CUT = Path("cut.mp4")
FILMS = {"reel": Path("out/film.mp4"), "square": Path("out/film-square.mp4"), "wide": Path("out/film-wide.mp4")}
SIZES = {"reel": (1080, 1920), "square": (1080, 1080), "wide": (1920, 1080)}
# the room a plain photograph's subject takes: a share of the photograph's width at each side of the subject, and of
# its height above and below it, which the frame keeps in view
ROOM = (0.04, 0.09)
# the share of the frame, from every side, the hook photograph's subject keeps inside
HELD = 0.1
ENTRY = re.compile(r"^- \*\*(\d{4}-\d{2}-\d{2})\*\* .*· pillar: (.+?)\s*$")
FINDINGS = ("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR")
WHITE = 0.97
# the level the film's sound falls under where it has stopped: the bed cut and the last hit rung out
QUIET = -50
MAX_STILLS = 10
# what every process QA starts goes through: subprocess.run, or the run.spawn of the command whose lock the gate runs
# under (deliver calls `gate(run)` in its own process)
spawn = subprocess.run


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
               "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(film, flt, key):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt, "-an", "-f", "null", "-"],
              capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def yavg(film, flt):
    """The mean luma (YAVG, 0-255) of every frame `flt` yields."""
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-v", "error", "-i", str(film), "-vf",
               flt + ",signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-", "-an", "-f", "null", "-"],
              capture_output=True, text=True)
    return [float(v) for v in re.findall(r"YAVG=([\d.]+)", r.stdout)]


def hook_subject(board, photos=None):
    """Where the hook's photograph puts its subject on `board`'s frame, as shares of its width and height: the
    subject's ROOM (x0, y0, x1, y1) on a plain photograph, its point (x, y) on any other; None when the hook lays no
    photograph or the photograph carries no subject. The crop is the film's: the photograph covers its box `zoom`
    times closer around its subject (motion/studio/Film.tsx)."""
    hook = next((b for b in (board or {}).get("beats") or [] if b["id"] == "hook"), None)
    p = (hook or {}).get("picture")
    if not p or not p.get("subject"):
        return None
    x0, y0, x1, y1 = p["box"]
    bw, bh = x1 - x0, y1 - y0
    su, sv = 1.0, 1.0
    if p["aspect"] > bh / bw:
        sv = (bh / bw) / p["aspect"]
    else:
        su = p["aspect"] / (bh / bw)
    su, sv = su / p["zoom"], sv / p["zoom"]
    sx, sy = p["subject"][:2]
    u0 = min(1 - su, max(0, sx - su / 2))
    t0 = min(1 - sv, max(0, sy - sv / 2))
    W, H = board["format"]["width"], board["format"]["height"]

    def at(u, v):
        return round((x0 + (u - u0) / su * bw) / W, 3), round((y0 + (v - t0) / sv * bh) / H, 3)
    if p.get("plain"):
        rx, ry = ROOM
        return at(sx - rx, sy - ry) + at(sx + rx, sy + ry)
    return at(sx, sy)


def subject_check(res, f):
    at = {fmt: hook_subject(_env.read_json(p)) for fmt, p in f["boards"].items()}
    out = [fmt for fmt, a in at.items() if a and not all(HELD <= v <= 1 - HELD for v in a)]
    res("subject", not out, "the hook's subject at " + "; ".join(f"{fmt} " + (" ".join(f"{v:.2f}" for v in a) if a else "unknown")
                                                              for fmt, a in at.items()) + f", inside {HELD} of each side")


def held_from(board):
    """Where the board holds its picture still to the end, in seconds: the closer's still, where the film stops its
    picture whether or not the music stops with it (a look that fades rings its music out over the held frame)."""
    still = ((board or {}).get("closer") or {}).get("still")
    return still * 60 / board["bpm"] if still is not None else float("inf")


def closer_from(board):
    """Where the closer starts, in seconds: the closer settles and holds still, so a frozen stretch that starts inside
    it is the closer at rest, however the film grain's refresh divides it."""
    at = ((board or {}).get("closer") or {}).get("at")
    return at * 60 / board["bpm"] if at is not None else float("inf")


def loudness(film):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"],
              capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def quiet_from(film):
    """Where the film's sound falls under QUIET dB and stays there to its end, in seconds; None when it never does. A
    silence that runs to the end of the stream is closed by ffmpeg at the stream's end, so the last silence counts when
    it has no end or ends at the film's end."""
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", f"silencedetect=n={QUIET}dB:d=0.3", "-vn", "-f", "null", "-"],
              capture_output=True, text=True)
    starts = re.findall(r"silence_start: (-?[\d.]+)", r.stderr)
    ends = re.findall(r"silence_end: (-?[\d.]+)", r.stderr)
    if not starts:
        return None
    end = float((probe(film).get("format") or {}).get("duration") or 0)
    return float(starts[-1]) if len(starts) > len(ends) or float(ends[-1]) >= end - 0.05 else None


def audio(res, film, f, board):
    """The audio row of one film, when music.json names music (see the docstring's gate rows)."""
    track = _env.read_json("music.json") or {}
    if not track.get("file"):
        return
    beats = len((_env.read_json(f["boards"]["reel"]) or {}).get("beats") or [])
    cues = track.get("sound_cues") or 0
    # the meter reads to a tenth of a LU, so the gap is compared at a tenth
    under = round(track["bed_lufs"] - track["fx_lufs"], 1) if "fx_lufs" in track else None
    mix = (f"master {track.get('master_lufs')} LUFS, bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, "
           f"{under:.1f} LU under (at least {music.FX_UNDER_BED_LU})" if under is not None else "no effects stem measured")
    a = next((s for s in probe(film).get("streams", []) if s.get("codec_type") == "audio"), None) if film.exists() else None
    lu = loudness(film) if a else None
    br = int((a or {}).get("bit_rate") or 0)
    held, stop = held_from(board), ""
    if a and held != float("inf"):
        quiet = quiet_from(film)
        stop = (f"; quiet under {QUIET} dB from {quiet:.2f} s to the end, the picture still from {held:.2f} s" if quiet is not None else
                f"; never quiet under {QUIET} dB before the end, the picture still from {held:.2f} s")
    res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
        and (not cues or (under is not None and under >= music.FX_UNDER_BED_LU)),
        f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated" if a else "no audio track")
        + f"; {mix}; {cues} sound cues over {beats} beats{stop}; the bed: {track.get('origin') or 'not named'}")


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


def picture(res, film, fmt, board, report):
    """The checks a rendered film is held to by its picture and its render report."""
    if not film.exists():
        res("film", False, f"{film} is missing")
        return
    p = probe(film)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    secs = float(p.get("format", {}).get("duration") or 0)
    lo, hi = storyboard.LENGTH
    ok = (v.get("width"), v.get("height")) == SIZES[fmt] and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
        and v.get("r_frame_rate") == "30/1" and lo <= secs <= hi
    res("film", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                    f"{v.get('r_frame_rate')} fps, {secs:.2f} s of {lo}-{hi}, {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
    black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start")
    res("black", not black, f"{film}: {len(black)} black stretches of 0.4 s or more")
    held, closing = held_from(board), closer_from(board)
    frozen = [float(ln.split(":")[-1]) for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "lavfi.freezedetect.freeze_start")]
    frozen = [at for at in frozen if at < min(closing, held - 0.04)]
    res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more before the closer at {min(closing, held):.2f} s"
        + (f" (from {frozen[0]:.2f} s)" if frozen else ""))
    lum = [max(0.0, min(1.0, (y - 16) / 219)) for y in yavg(film, "scale=108:-2:flags=area")]
    white = [i for i, y in enumerate(lum) if y > WHITE]
    res("white", lum and not white, f"{film}: brightest frame {max(lum) if lum else 0:.3f} mean luma, limit {WHITE}"
        + (f"; {len(white)} frames over it from frame {white[0]}" if white else ""))
    rep = _env.read_json(report) or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(FINDINGS)]
    res("safe", rep and not rep.get("failed") and not bad, f"{report}: {rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, "
        f"{len(bad)} findings" + (f": {bad[0]}" if bad else ""))


def plan_check():
    p = Path("out/plan.md")
    if not p.exists():
        return False, "out/plan.md is missing: run brand.py plan"
    b = the_brand() or {}
    lines = p.read_text().splitlines()
    names = {x.get("name") for x in b.get("pillars", [])}
    entries, bad, bare = [], [], 0
    for i, ln in enumerate(lines):
        m = ENTRY.match(ln)
        if not m:
            continue
        entries.append(m.group(1))
        if m.group(2) not in names:
            bad.append(f"{m.group(1)} {m.group(2)!r}")
        cap = [x for x in lines[i + 1:i + 12] if x.startswith("  >")]
        if not any(x[3:].strip() for x in cap):
            bare += 1
    ok = len(entries) == 30 and len(set(entries)) == 30 and not bad and not bare
    return ok, (f"{len(entries)} dated entries, {len(set(entries))} dates, {bare} without a caption" +
                (f"; pillars not in brand.json: {bad[:3]}" if bad else ""))


def the_brand():
    return _env.read_json("out/brand.json" if Path("out/brand.json").exists() else "brand.json")


def project(res):
    b = the_brand()
    errs = brandkit.check(b) if b else ["brand.json is missing: run brand.py system"]
    res("brand", not errs, f"brand.json valid, pillar shares sum to {sum(p.get('share', 0) for p in (b or {}).get('pillars', [])):.3f}"
        if not errs else f"{len(errs)} errors: {errs[0]}")
    res("plan", *plan_check())


def check_checks():
    res, f = Checks(), cut()
    if not CUT.exists():
        sys.exit("cut.mp4 is missing: run film.py cut first")
    reel = _env.read_json(f["boards"]["reel"])
    picture(res, CUT, "reel", reel, "render/cut-report.json")
    res("hook", f["hook_frame"] <= storyboard.HOOK_FRAMES, f"the hook event at frame {f['hook_frame']} (inside {storyboard.HOOK_FRAMES})")
    res("bounds", not f["findings"], f"{len(f['findings'])} findings on the three boards" + (f": {f['findings'][0]}" if f["findings"] else ""))
    subject_check(res, f)
    project(res)
    audio(res, CUT, f, reel)
    m = (_env.read_json("cut.json") or {}).get("measured") or {}
    if (_env.read_json("cut.json") or {}).get("sha") == sha(CUT) and m:
        figures(res, m)
    else:
        res("cut", False, "cut.json is not for this cut.mp4: run film.py cut")
    return res, f


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("text", "label", "caption") and isinstance(v, str):
                acc.append(v)
            else:
                words_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            words_in(v, acc)
    return acc


CARDS = {"out/story.png": (1080, 1920), "out/post.png": (1080, 1080)}
# what out/ delivers: the films, the cards, the caption, the brand file, the plan, the review page, and the stills
# with their list when the person asked for them
DELIVERED = {"film.mp4", "film-square.mp4", "film-wide.mp4", "story.png", "post.png", "caption.md", "brand.json", "plan.md",
             "review.html", "stills.json", "boards.png"}


def delivered(p):
    rel = Path(p).relative_to("out")
    return rel.as_posix() in DELIVERED or (rel.parent.as_posix() == "stills" and rel.suffix == ".png")


def made():
    """What the last render made (render/film-report.json's `made`): the formats and whether the story card and stills;
    every format when the report names none."""
    m = (_env.read_json("render/film-report.json") or {}).get("made") or {}
    return set(m.get("formats") or FILMS) | {"reel"}, bool(m.get("stories"))


def gate_checks():
    res, f = Checks(), cut()
    formats, stories = made()
    if not Path("render/film-report.json").exists():
        res("safe", False, "render/film-report.json is missing: film.py render has not finished")
    for fmt, film in FILMS.items():
        if fmt not in formats:
            if film.exists():
                res("film", False, f"{film} is in out/, and the render did not make it (nobody asked for it)")
            continue
        board = _env.read_json(f["boards"][fmt])
        picture(res, film, fmt, board, "render/cut-report.json" if fmt == "reel" else "render/film-report.json")
        if film.exists():
            audio(res, film, f, board)
    cards = {p: png_size(p) if Path(p).exists() else None for p in CARDS}
    res("cards", cards == CARDS, ", ".join(f"{p} " + ("at %dx%d" % z if z else "missing") for p, z in cards.items()))
    if stories:
        st = (_env.read_json("out/stills.json") or {}).get("stills") or []
        files = [Path("out") / s["file"] for s in st]
        have = [p for p in files if p.exists()]
        sizes = {png_size(p) for p in have}
        stray = sorted(p.name for p in Path("out/stills").glob("*.png") if p not in files) if Path("out/stills").exists() else []
        res("stills", files and len(have) == len(files) <= MAX_STILLS and sizes == {(1080, 1080)} and len({sha(p) for p in have}) == len(have)
            and not stray, f"{len(have)} of {len(files)} stills at {', '.join('%dx%d' % z for z in sizes) or '-'}" + (f"; stray {stray}" if stray else ""))
    else:
        extra = [p.name for p in (Path("out/stills.json"),) if p.exists()] + sorted(f"stills/{p.name}" for p in Path("out/stills").glob("*.png"))
        res("stills", not extra, "no stills asked for" + (f", and out/ holds {', '.join(extra)}" if extra else ", none in out/"))
    other = sorted(p.relative_to("out").as_posix() for p in Path("out").rglob("*") if p.is_file() and not delivered(p))
    res("out", not other, "out/ holds the deliverables only" + (f"; and {', '.join(other)}" if other else ""))
    res("bounds", not f["findings"], f"{len(f['findings'])} findings on the three boards")
    subject_check(res, f)
    project(res)
    texts = words_in([_env.read_json(p) for p in f["boards"].values()], [])
    for p in ("out/caption.md", "brief.md", "out/review.html", "out/plan.md"):
        if Path(p).exists():
            texts.append(Path(p).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    res("text", not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    res("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    looks = storyboard.letters()
    full = [t for t in looks if all((storyboard.BOARDS / t / x).exists() for x in
                                    ("board-reel.json", "board-square.json", "board-wide.json", "storyboard.md", "sheet.png"))]
    res("boards", len(looks) == 3 and len(full) == 3 and Path("out/boards.png").exists(),
        f"{len(full)} of 3 looks with three boards, storyboard.md and sheet.png" + ("" if Path("out/boards.png").exists() else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    picked = win.get("board") in looks and (win.get("by") == "person" or bool(win.get("why")))
    res("vote", Path("vote.md").exists() and picked,
        f"look {win.get('board')} picked by {win.get('by')}" + ("" if picked else ", without a pick (or a reason when picked by taste)"))
    v = _env.read_json("critic/verdict.json") or {}
    same = CUT.exists() and v.get("film") == sha(CUT)
    res("critic", same and v.get("verdict") in ("ship", "spent"), f"round {v.get('round')}, {v.get('verdict')}"
        + ("" if same else "; the verdict is not for the current cut"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    need = ("out/review.html", "brief.md", "out/brand.json", "out/plan.md")
    res("deliver", reg and all(Path(p).exists() for p in need), f"caption {len(cap.split())} words, {len(tags)} hashtags"
        + (", lowercase like theirs" if lower else "") + "".join(f"; {p} missing" for p in need if not Path(p).exists()))
    return res, f


def report(res, path, f, label, extra=None):
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, "hash": f["hash"], **(extra or {}),
                           "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(f"{label} " + ("GREEN" if not bad else f"RED ({len(bad)} failing)"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    _env.enter()
    if a.cmd == "check":
        res, f = check_checks()
        return report(res, "qa/check.json", f, "CHECKS", {"film": sha(CUT)})
    return gate()


def gate(run=None):
    """The gate's checks, printed and written to qa/gate.json; 0 when they pass. Under a command's lock (`run`) every
    process a check starts goes through run.spawn."""
    global spawn
    spawn = run.spawn if run else subprocess.run
    res, f = gate_checks()
    return report(res, "qa/gate.json", f, "GATE", {"film": sha(CUT) if CUT.exists() else None})


if __name__ == "__main__":
    sys.exit(main())
