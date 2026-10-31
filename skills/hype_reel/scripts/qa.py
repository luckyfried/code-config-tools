#!/usr/bin/env python3
"""The measurable checks of the cut and the film, and the gate that refuses delivery.

USAGE (in a run; S = this skill's folder):
    python3 S/scripts/qa.py check [--film F]  # the picture's checks (--film: the silent cut F against the cut's report
                                              # render/cut-report.json into qa/cut.json, as film.py cut runs them;
                                              # with no --film, out/film.mp4 against render-report.json into qa/check.json)
    python3 S/scripts/qa.py gate              # everything below on out/; exit 0 only when every check passes

The checks of a picture:
  film      it is not 1080x1920 H.264 High yuv420p at 30 fps, or runs outside 15-25 s
  audio     (out/film.mp4 only) music was found but the film has no AAC track near 192 kbps, or its loudness is off
            -14 LUFS by more than 1 LU, or with sound cues the effects stem sits less than music.FX_UNDER_BED_LU - 1 LU
            under the bed (both integrated, from music.json); the row names the two numbers and the cue and beat
            counts, and refuses nothing on count
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting more than SETTLE musical beats (or
            SETTLE_SECONDS, the longer) before the board's stop: the picture the board holds from its stop cue to the
            end is the ending, the closer eases into it over its last beat, and a board with no stop cue holds nothing
  frame0    frame 0 is a flat field: the first frame (read at 270x480 gray, inside the card's letterbox bars) shows
            neither a picture nor words
  hook      nothing arrives in the first 30 frames: the hook event is the first frame whose mean luma differs from the
            first frame's by 6 or more (of 255, read at 108x192), and it must come before frame 30
  board     any finding of storyboard.py check on film.json: a line outside the safe area or its box, a picture not
            in public/ or shown as the subject when it is not one of its own stills or clips, the subject's own
            pictures under half the time before the closer, a launch's closer without its date, no stop, a length
            outside the kit's
  safe      a FONT_ERROR, IMAGE_ERROR or RENDER_ERROR (among them a lost graphics context or a shader that failed to
            validate, whose frames come out white) or a failed job in render-report.json
The figures of a picture, measured and shown to the critic, never passed or failed:
  cuts      the cuts and the cuts a minute: every beat boundary of film.json joined with every ffmpeg scene change
            scoring over 0.12 (read at 270x480) more than 0.2 s from another cut
  still     each second's change (its first frame against its last, box-downscaled to 135x240 gray, mean absolute
            difference), the seconds under 0.5 and the longest run of them; a held composition is quiet by design
The gate adds:
  made      out/film.mp4 is not the render of the current film.json's cut (engine.json, cut.json)
  cover     out/cover.png is not 1080x1920, or frame 0 of out/film.mp4 is not the cover (mean difference over 6 of 255
            at 108x192 gray)
  stories   (a launch only) out/story-1.png, story-2.png and story-3.png are not all 1080x1920, or two of them are the
            same picture
  countdown (a launch only) out/countdown.png is not 1080x1920
  feed      out/feed.png is not 1080x1350
  text      a placeholder string anywhere in the film's words, the captions, the brief or the review page
  captions  out/captions.md lacks a section for the film, the feed post or the share caption (and for a launch each
            story and the countdown), a section does not name the subject, or the share caption is not one to three
            sentences
  research  taste.md (you are / you like / your style / your voice / the subject / avoid) or taste.json is missing
  boards    three storyboards (the three looks), each with storyboard.md, storyboard.json, a frame of every beat at
            rest, and sheet.png, and out/boards.png
  vote      winner.json is missing, or the panel's winner fails the swap test (a board the person or the agent
            picked carries its picker instead)
  clips     a clip the board asks for is not accounted for in clips.json as generated or standing in
  critic    the latest cut round in critic/ is not for this film.json, is not filled in, fails one of its reads
            (vote.READS), or is under the bar (vote.at_bar) with the one fix unspent
  deliver   out/captions.md, out/review.html or out/brief.md is missing, or the captions are not in their register
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
import music  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|(?-i:\bNaN\b|\bNone\b)|@handle\b|your_handle", re.I)
OUT_FILM = Path("out/film.mp4")
STORIES = [Path(f"out/story-{i}.png") for i in (1, 2, 3)]
COUNTDOWN = Path("out/countdown.png")
COVER = Path("out/cover.png")
FEED = Path("out/feed.png")
CAPTIONS = Path("out/captions.md")
SECTIONS = ("film", "feed post", "share")
LAUNCH_SECTIONS = ("story 1", "story 2", "story 3", "countdown")
LENGTH = (15, 25)
# the most a frame 0 may differ from the cover (of 255, at 108x192 gray) and still be the cover
COVER_DIFF = 6.0
STILL = 0.5
SCENE = 0.12
HOOK_FRAMES, HOOK_LUMA = 30, 6.0
FLAT = 8.0
# how long before the stop a picture may come to rest: a closer eases into its hold over its last beat, and the
# shared ease out moves under a pixel for about its last 0.6 s, so the allowance is a musical beat or 0.6 s, the longer
SETTLE = 1
SETTLE_SECONDS = 0.6
MEASURES = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p, spawn):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
               "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(film, flt, key, spawn):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf", flt, "-an", "-f", "null", "-"],
              capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def loudness(film, spawn):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"],
              capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def still_figure(film, spawn):
    """Each second's change: its first frame against its last, both box-downscaled to 135x240 gray, by mean absolute
    difference. Grain moves single pixels and averages out in the box; a move, however slow, does not. A figure the
    critic reads beside the strips: the seconds under STILL and the longest run of them."""
    w, h = 135, 240
    r = spawn([_env.ffmpeg(), "-v", "error", "-i", str(film), "-vf", f"scale={w}:{h}:flags=area,format=gray", "-an",
               "-f", "rawvideo", "-"], capture_output=True)
    n = len(r.stdout) // (w * h)
    frame = lambda i: r.stdout[i * w * h:(i + 1) * w * h]
    per = []
    for i in range(0, n - 1, 30):
        a, b = frame(i), frame(min(i + 29, n - 1))
        per.append(round(sum(abs(x - y) for x, y in zip(a, b)) / (w * h), 2))
    low = [i for i, x in enumerate(per) if x < STILL]
    run, longest = 0, 0
    for x in per:
        run = run + 1 if x < STILL else 0
        longest = max(longest, run)
    MEASURES["still"] = {"per_second": per, "seconds_under_half": low, "longest_run_under_half": longest}
    return f"seconds under {STILL}: {low}, longest run {longest}"


def cuts_figure(film, board, secs, spawn):
    """The cuts: the planned ones (beat boundaries) joined with every scene change more than 0.2 s from another cut."""
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), "-vf",
               f"scale=270:480,select='gt(scene,{SCENE})',showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True)
    scene = [float(m) for m in re.findall(r"pts_time:\s*([\d.]+)", r.stderr)]
    planned = [t["start"] / 30 for t in board.get("timeline") or [] if t["start"]]
    cuts = sorted(planned)
    for t in scene:
        if t >= 0.2 and all(abs(t - c) > 0.2 for c in cuts):
            cuts.append(t)
            cuts.sort()
    per_min = round(len(cuts) / (secs / 60), 1) if secs else 0.0
    MEASURES["cuts"] = {"cuts": len(cuts), "cuts_per_minute": per_min, "planned_cuts": len(planned), "scene_cuts": len(scene),
                        "at": [round(c, 2) for c in cuts], "duration": round(secs, 2)}
    return f"{len(cuts)} cuts ({len(planned)} planned), {per_min} a minute"


def held_from(board):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    stop = next((c["at"] for c in board.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / board["bpm"] if stop is not None else float("inf")


def hook_check(film, spawn):
    """The first frame that differs visibly from the first: the hook arriving."""
    _env.need("PIL")
    from PIL import Image, ImageChops, ImageStat
    r = spawn([_env.ffmpeg(), "-v", "error", "-i", str(film), "-vf", "scale=108:192:flags=area,format=gray",
               "-frames:v", str(HOOK_FRAMES + 15), "-f", "rawvideo", "-"], capture_output=True)
    n = 108 * 192
    frames = [Image.frombytes("L", (108, 192), r.stdout[i:i + n]) for i in range(0, len(r.stdout) - n + 1, n)]
    at = next((i for i, f in enumerate(frames) if ImageStat.Stat(ImageChops.difference(f, frames[0])).mean[0] >= HOOK_LUMA), None)
    MEASURES["hook_frame"] = at
    return at is not None and at < HOOK_FRAMES, (f"the hook arrives at frame {at}" if at is not None else
                                                 f"nothing arrives in the first {len(frames)} frames") + f", within {HOOK_FRAMES}"


def frame0_check(film, bars, spawn):
    """Frame 0 shows the hook: inside the letterbox bars (`bars`, a share of the height at each edge) the first frame is
    not one flat field."""
    _env.need("PIL")
    from PIL import Image
    r = spawn([_env.ffmpeg(), "-v", "error", "-i", str(film), "-vf", "scale=270:480:flags=area,format=gray",
               "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True)
    if len(r.stdout) < 270 * 480:
        return False, "frame 0 could not be read"
    sd = spread(Image.frombytes("L", (270, 480), r.stdout[:270 * 480]), bars)
    return sd >= FLAT, f"frame 0 varies by {sd:.1f} (of 255) inside the bars, a flat field under {FLAT}"


def spread(im, bars):
    """How far a gray frame varies inside its letterbox bars (`bars`, a share of the height at each edge)."""
    from PIL import ImageStat
    k = round(bars * im.height) + 2
    return ImageStat.Stat(im.crop((0, k, im.width, im.height - k))).stddev[0]


def board_checks(board, check):
    """storyboard.py's checks on film.json."""
    import storyboard
    found = storyboard.board_issues("film", board)
    check("board", not found, f"{len(found)} findings on film.json" + (f": {found[0]}" if found else ""))


def film_checks(film, audio, spawn=subprocess.run, report="render-report.json"):
    """The checks of a picture and of `report`, its render report. A command that holds the run's lock passes its
    run.spawn, so every ffprobe and ffmpeg these start keeps the lock."""
    res = []

    def check(name, ok, detail):
        res.append((name, bool(ok), detail))

    def figure(name, detail):
        res.append((name, None, detail))
    board = _env.read_json("film.json") or {}
    if not film.exists() or not board:
        check("film", False, f"{film} or film.json is missing")
        return res
    p = probe(film, spawn)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
    secs = float(p.get("format", {}).get("duration") or 0)
    ok = (v.get("width"), v.get("height")) == (1080, 1920) and v.get("codec_name") == "h264" and v.get("profile") == "High" \
        and v.get("pix_fmt") == "yuv420p" and v.get("r_frame_rate") == "30/1" and LENGTH[0] <= secs <= LENGTH[1]
    check("film", ok, f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                      f"{v.get('r_frame_rate')} fps, {secs:.1f} s, {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
    if audio:
        track = _env.read_json("music.json") or {}
        if track.get("file") and not a:
            check("audio", False, "music was found but the film has no audio track")
        elif track.get("file"):
            lu = loudness(film, spawn)
            br = int(a.get("bit_rate") or 0)
            cues = track.get("sound_cues") or 0
            under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
            mix = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU - 1})"
                   if under is not None else "no effects stem measured")
            check("audio", a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                  and (not cues or (under is not None and under >= music.FX_UNDER_BED_LU - 1)),
                  f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated; {mix}; {cues} sound cues over "
                  f"{len(board.get('beats') or [])} beats")
        else:
            check("audio", True, "no music was found; the film carries its sound effects alone")
    black = detect(film, "blackdetect=d=0.4:pix_th=0.10", "black_start", spawn)
    check("black", not black, f"{len(black)} black stretches of 0.4 s or more" + (f": {black[0][-80:]}" if black else ""))
    held = held_from(board)
    rest = held - max(SETTLE * 60 / board["bpm"], SETTLE_SECONDS) if held != float("inf") else held
    frozen = [ln for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start", spawn) if float(ln.split(":")[-1]) < rest]
    check("frozen", not frozen, f"{len(frozen)} frozen stretches of 1.0 s or more before the stop"
          + (f" at {held:.2f} s" if held != float("inf") else " (the board has no stop)") + (f": {frozen[0][-40:]}" if frozen else ""))
    check("frame0", *frame0_check(film, (board["system"].get("finish") or {}).get("bars", 0), spawn))
    check("hook", *hook_check(film, spawn))
    figure("cuts", cuts_figure(film, board, secs, spawn))
    figure("still", still_figure(film, spawn))
    board_checks(board, check)
    rep = _env.read_json(report) or {}
    bad = [f["text"][:160] for f in rep.get("findings", []) if f["text"].startswith(("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR"))]
    check("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, "
          f"{len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    return res


def stories_check():
    """The three teaser stories: 1080x1920 each, and three different pictures."""
    miss = [str(f) for f in STORIES if not f.exists()]
    if miss:
        return False, f"missing {miss}"
    sizes = [png_size(f) for f in STORIES]
    _env.need("PIL")
    from PIL import Image
    small = [list(Image.open(f).convert("L").resize((24, 42), Image.BILINEAR).tobytes()) for f in STORIES]
    diffs = [sum(abs(p - q) for p, q in zip(small[i], small[j])) / len(small[i]) for i in range(3) for j in range(i + 1, 3)]
    ok = all(sz == (1080, 1920) for sz in sizes) and min(diffs) > 4
    return ok, f"sizes {['%dx%d' % sz for sz in sizes]}, least difference between two stories {min(diffs):.1f}"


def sections(text):
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip().lower()
            out[cur] = ""
        elif cur:
            out[cur] += ln + "\n"
    return out


def share_sentences(text):
    """The sentences of the share caption, its hashtags aside."""
    body = re.sub(r"#\w+", "", text).strip()
    return [x for x in re.split(r"(?<=[.!?])\s+", body) if x.strip()]


def captions_check(subject, launch=True):
    if not CAPTIONS.exists():
        return False, "out/captions.md is missing"
    sec = sections(CAPTIONS.read_text())
    want = SECTIONS + (LAUNCH_SECTIONS if launch else ())
    miss = [k for k in want if k not in sec]
    unnamed = [k for k in want if k in sec and subject.lower() not in sec[k].lower()]
    n = len(share_sentences(sec.get("share", "")))
    return not miss and not unnamed and subject and 1 <= n <= 3, (
        f"{len(sec)} sections" + (f"; missing {miss}" if miss else "") +
        (f"; not naming {subject}: {unnamed}" if unnamed else f"; every one names {subject}") +
        f"; the share caption is {n} sentences" + ("" if 1 <= n <= 3 else ", not one to three"))


def cover_check(film, spawn):
    """The cover is 1080x1920 and is the film's frame 0."""
    if not COVER.exists():
        return False, f"{COVER} is missing"
    if png_size(COVER) != (1080, 1920):
        return False, f"{COVER} is %dx%d, not 1080x1920" % png_size(COVER)
    _env.need("PIL")
    from PIL import Image, ImageChops, ImageStat
    r = spawn([_env.ffmpeg(), "-v", "error", "-i", str(film), "-vf", "scale=108:192:flags=area,format=gray",
               "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True)
    if len(r.stdout) < 108 * 192:
        return False, "frame 0 could not be read"
    first = Image.frombytes("L", (108, 192), r.stdout[:108 * 192])
    cover = Image.open(COVER).convert("L").resize((108, 192), Image.BOX)
    d = ImageStat.Stat(ImageChops.difference(first, cover)).mean[0]
    return d <= COVER_DIFF, f"frame 0 differs from the cover by {d:.1f} (of 255), at most {COVER_DIFF}"


def in_register(sec, subject, register):
    """The captions read like theirs: their case, and one to ten hashtags on the film and the feed post when their own
    captions carry hashtags (taste.json register.hashtags), none when that list is empty. Returns whether they do, the
    hashtag counts of the film and the feed post, and the reason when they do not."""
    name = re.compile(re.escape(subject), re.I) if subject else None
    bodies = [re.sub(r"#\w+", "", name.sub("", v) if name else v) for v in sec.values()]
    tags = [len(re.findall(r"#\w+", sec.get(k, ""))) for k in ("film", "feed post")]
    tagged = bool(register.get("hashtags"))
    why = ("captions.md has no sections" if not sec else
           "they write in lowercase, so every section is lowercase except the subject's name"
           if register.get("lowercase") and any(b != b.lower() for b in bodies) else
           "their own captions carry hashtags, so the film and the feed post carry one to ten"
           if tagged and not all(1 <= n <= 10 for n in tags) else
           "their own captions carry no hashtags (taste.json register.hashtags is empty), so the film and the feed post carry none"
           if not tagged and any(tags) else "")
    return not why, tags, why


def words_of(film):
    """Every line of type the film and its stills show."""
    return [ln["text"] for b in (film.get("beats") or []) + ((film.get("feed") or {}).get("beats") or [])
            for ln in b.get("lines") or []] + [film.get(k) or "" for k in ("title", "signoff", "handle")]


def critic_check(h):
    import vote
    rs = vote.rounds()
    if not rs:
        return False, "no cut round in critic/: run vote.py cut and fill it in"
    last = _env.read_json(rs[-1])
    bad = vote.problems(last, vote.CUT_PANEL, ["film"], swap=False)
    if last.get("film") != h:
        return False, f"round {len(rs)} is not for the current film.json"
    if bad:
        return False, f"round {len(rs)} is not filled in: {bad[0]}"
    bar, mean, low = vote.at_bar(last)
    failed = [k for k in vote.READS if not last["reads"][k]["pass"]]
    ok = not failed and (bar or len(rs) >= 2)
    return ok, f"round {len(rs)}, mean {mean}, lowest {low[0]} ({low[1]}), " + ("at the bar, " if bar else "under the bar, ") + (f"fails {', '.join(failed)}: {last['reads'][failed[0]]['why'][:120]}" if failed
                                                    else f"every read passes ({', '.join(vote.READS)})")


def gate_checks(spawn=subprocess.run):
    res = film_checks(OUT_FILM, audio=True, spawn=spawn)

    def check(name, ok, detail):
        res.append((name, bool(ok), detail))
    h = sha("film.json") if Path("film.json").exists() else None
    eng, cut = _env.read_json("engine.json") or {}, _env.read_json("cut.json") or {}
    check("made", h and eng.get("film") == h and cut.get("film") == h,
          "out/film.mp4 is the render of the current film.json's cut" if h and eng.get("film") == h == cut.get("film")
          else "out/film.mp4 is not from the current film.json: run film.py cut, the critics, then film.py render")
    film = _env.read_json("film.json") or {}
    launch = film.get("launch", True)
    check("cover", *cover_check(OUT_FILM, spawn))
    if launch:
        check("stories", *stories_check())
    for name, f, want in ((("countdown", COUNTDOWN, (1080, 1920)),) if launch else ()) + (("feed", FEED, (1080, 1350)),):
        sz = png_size(f) if f.exists() else None
        check(name, sz == want, f"{f} {'at %dx%d' % sz if sz else 'is missing'}")
    film = _env.read_json("film.json") or {}
    texts = words_of(film)
    for f in ("out/captions.md", "out/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [x for x in ("you are", "you like", "your style", "your voice", "the subject", "avoid") if x not in tm]
    subj = (_env.read_json("library.json") or {}).get("subject") or {}
    subject = subj.get("name") or film.get("subject") or ""
    check("captions", *captions_check(subject, launch))
    check("research", tm and not heads and Path("taste.json").exists(),
          "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    boards = sorted(Path("storyboards").glob("*/storyboard.json"))

    def full(f):
        b = _env.read_json(f) or {}
        d = f.parent
        frames = list((d / "frames").glob("[0-9][0-9]-*.png"))
        return (d / "storyboard.md").exists() and (d / "sheet.png").exists() and len(frames) == len(b.get("beats") or [])
    whole = [f for f in boards if full(f)]
    looks = Path("out/boards.png").exists()
    check("boards", len(boards) == 3 and len(whole) == 3 and looks,
          f"{len(boards)} storyboards, {len(whole)} with storyboard.md, a frame of every beat and sheet.png"
          + ("" if looks else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    swap = (win.get("swap") or {}).get(str(win.get("board")))
    by = win.get("picked_by")
    check("vote", win.get("board") and (by or (Path("vote.md").exists() and swap)),
          f"board {win.get('board')} ({win.get('name')})" + (f" picked by {by}" if by else ", the panel's winner" if swap
                                                             else ", which does not pass the swap test"))
    want = {c["id"] for c in film.get("clips", [])}
    got = ((_env.read_json("clips.json") or {}).get("clips") or {})
    gen = sum(1 for k in want if (got.get(k) or {}).get("status") in ("generated", "footage"))
    miss = sorted(want - set(got))
    check("clips", not miss, f"{len(want)} clips, {gen} generated or footage, {len(want) - gen - len(miss)} standing in"
          + (f"; not accounted for {miss}: run clips.py normalize" if miss else ""))
    check("critic", *critic_check(h))
    sec = sections(CAPTIONS.read_text()) if CAPTIONS.exists() else {}
    register = (_env.read_json("taste.json") or {}).get("register") or {}
    lower = register.get("lowercase")
    reg, tags, why = in_register(sec, subject, register)
    check("deliver", reg and Path("out/review.html").exists() and Path("out/brief.md").exists(),
          f"captions {sum(len(v.split()) for v in sec.values())} words, hashtags film {tags[0]} feed {tags[1]}" +
          (", lowercase like theirs" if lower else "") + (f"; {why}" if why else "") +
          ("" if Path("out/review.html").exists() else "; review.html missing") + ("" if Path("out/brief.md").exists() else "; brief.md missing"))
    return res


def report(res, path, gate=False):
    bad = [r for r in res if r[1] is False]
    for name, ok, detail in res:
        print(f"{'FIG ' if ok is None else 'PASS' if ok else 'FAIL'}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, **MEASURES, "checks": [{"check": n, "pass": o, "detail": d} for n, o, d in res if o is not None],
                           "figures": [{"figure": n, "detail": d} for n, o, d in res if o is None]})
    print(("GATE " + ("GREEN" if not bad else f"RED ({len(bad)} failing)")) if gate else
          ("CHECKS PASS" if not bad else f"{len(bad)} CHECKS FAIL"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    ap.add_argument("--film", help="check: the silent cut to check against render/cut-report.json (default: out/film.mp4)")
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "check":
        film = Path(a.film) if a.film else OUT_FILM
        if a.film:
            return report(film_checks(film, audio=False, report="render/cut-report.json"), "qa/cut.json")
        return report(film_checks(film, audio=True), "qa/check.json")
    return report(gate_checks(), "qa/gate.json", gate=True)


if __name__ == "__main__":
    sys.exit(main())
