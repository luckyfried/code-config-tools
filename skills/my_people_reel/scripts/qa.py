#!/usr/bin/env python3
"""Movement 5: the measured checks on the timed cut, and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/qa.py check     # the timed cut (R/render/cut.mp4) and its board, before the film renders -> R/qa/check.json
    python3 S/scripts/qa.py gate      # the check, the finished film in every format made and everything delivered -> R/qa/gate.json

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strip, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts per minute
  still     the luma line (each second's change, read at an eighth of the frame so film grain is not counted as
            motion): the seconds under 0.5 and the longest run of them

check refuses:
  film      the cut is not 1080x1920 H.264 High yuv420p at 30 fps, or runs outside 8 to 30 s (4 s more for
            each person after the fifth)
  audio     music was found but the cut has no AAC track near 192 kbps, or its loudness is off -14 LUFS by more than 1 LU,
            or with sound cues the effects stem sits less than music.FX_UNDER_BED_LU - 1 LU under the bed (both
            integrated, from music.json); the row names the two numbers and the cue and beat counts, and refuses
            nothing on count
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting over 0.15 s before the board's
            stop: frames that repeat, as a stalled render's do; the still the board holds from its stop to the end is
            the ending, and the last 0.15 s before it is the closer's ease coming to rest (three frames) and the stop's
            place inside its frame
  hook      the first event lands after frame 30
  board     the film's storyboard, laid out in all three formats, fails storyboard.py check (the safe area, the 28 px
            cap-height floor, a tag outside the safe area or into the type, a line that is not the person's own)
  safe      a failed render job, or FONT_ERROR, RENDER_ERROR or IMAGE_ERROR in R/render/cut-report.json
  people    a person of the film appears in no beat
The gate adds:
  formats   out/film.mp4 is not the checked cut, or out/film-square.mp4 (1080x1080) or out/film-wide.mp4 (1920x1080), when
            the render made it (engine.json's `made`, from film.py render --also), is missing, off format, or a
            different length; black and frozen on each; either of them in out/ when the render did not make it
  cards     when the render made story cards, a person has no out/people/NN-<handle>.png at 1080x1920, or two stills
            are the same image; when it did not, a story card in out/people/
  text      a placeholder string in the film's words, the caption, R/brief.md or the review page
  research  R/taste.md (you are / you like / your style / your voice / avoid) or R/taste.json is missing
  boards    the three looks' storyboards, each with storyboard.md, storyboard.json and its sheet, and out/boards.png
  vote      R/vote.md or R/winner.json (the picked look) is missing
  scored    the latest round in R/critic/ is not for this cut or not filled in; beside it, the critic figure states
            the round's scores against the bar (vote.py), whichever way they went, and never passes or fails
  deliver   out/caption.md, out/review.html, out/cover.png or out/story.png is missing, out/ holds anything but the
            deliverables (the films, cover.png, story.png, caption.md, review.html, people/, boards.png and looks/), the caption is not in
            their register, or it does not tag every person
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

# a value that leaked into the words (Python's None in its own case; the word "none" is English), and a stand-in for the
# person's username
PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|(?-i:\bNone\b)|@handle\b|your_handle"
                         r"|@(?:you|me)(?![\w.])", re.I)
CUT = Path("render/cut.mp4")
CARDS = Path("out/people")
OUT = Path("out")
# everything out/ may hold: the films, the posted image, the reel's story card, the caption, the review page and the
# people's story cards
DELIVERABLES = {"film.mp4", "film-square.mp4", "film-wide.mp4", "cover.png", "story.png", "caption.md", "review.html", "people", "boards.png", "looks"}
LENGTH = (8, 30)
# the seconds a cut may run past 30 for each person after the fifth: the longest beat a person's words take
PAST_FIVE = 4
SIZES = {"out/film.mp4": (1080, 1920), "out/film-square.mp4": (1080, 1080), "out/film-wide.mp4": (1920, 1080)}
KINDS = {"reel": "out/film.mp4", "square": "out/film-square.mp4", "wide": "out/film-wide.mp4"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


_run = None  # the lock of the command the gate runs inside (deliver), or None when qa.py runs on its own


def spawn(argv):
    """A tool's run, its output captured; inside a command's lock every process starts through its run.spawn."""
    return (_run.spawn if _run else subprocess.run)(argv, capture_output=True, text=True)


def probe(p):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)])
    return json.loads(r.stdout or "{}")


def video_of(p):
    pr = probe(p)
    v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in pr.get("streams", []) if s.get("codec_type") == "audio"), None)
    return v, a, float(pr.get("format", {}).get("duration") or 0)


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def ffmpeg_lines(film, args, key):
    r = spawn([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(film), *args, "-f", "null", "-"])
    return [ln for ln in r.stderr.splitlines() if key in ln]


def loudness(film):
    m = [re.findall(r"I:\s+(-?[\d.]+) LUFS", ln) for ln in ffmpeg_lines(film, ["-af", "ebur128=framelog=quiet", "-vn"], "I:")]
    m = [x for xs in m for x in xs]
    return float(m[-1]) if m else None


def held_from():
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    board = _env.read_json("render/board-reel.json") or {}
    stop = next((c["at"] for c in board.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / board["bpm"] if stop is not None else float("inf")


def frozen_in(film, held):
    return [ln for ln in ffmpeg_lines(film, ["-vf", "freezedetect=n=-80dB:d=1.0", "-an"], "freeze_start")
            if float(ln.split(":")[-1]) < held - 0.15]


class Checks(list):
    """Checks, (name, passed, detail), and figures, (name, None, detail, values): a figure is measured and shown,
    never passed or failed."""

    def __call__(self, name, ok, detail):
        self.append((name, bool(ok), detail))

    def figure(self, name, detail, values):
        self.append((name, None, detail, values))


def figures(res, m):
    """The cut's two figures from its measurement (`studio.measure`, carried in render/cut.json)."""
    res.figure("cuts", f"{m['cuts']} cuts, {m['cuts_per_minute']} a minute", {k: m[k] for k in ("cuts", "cuts_per_minute", "planned_cuts", "extra_scene_cuts")})
    res.figure("still", f"seconds under 0.5: {m['seconds_under_half']}, longest run {m['longest_run_under_half']}",
               {k: m[k] for k in ("luma", "seconds_under_half", "longest_run_under_half")})


def the_people():
    """The people of the film, in its order."""
    f = _env.read_json("film.json") or {}
    if f.get("storyboard"):
        return list(f["storyboard"].get("people") or [])
    ppl = (_env.read_json("taste.json") or {}).get("people") or (_env.read_json("people.json") or {}).get("people") or []
    return [x["handle"] for x in ppl if x.get("handle")]


def longest():
    """The longest the cut may run: 30 s, and PAST_FIVE more for each person of the film after the fifth."""
    return LENGTH[1] + PAST_FIVE * max(0, len(the_people()) - 5)


def people_check():
    ppl = the_people()
    beats = ((_env.read_json("film.json") or {}).get("storyboard") or {}).get("beats") or []
    seen = {b.get("person") for b in beats}
    gone = [h for h in ppl if h not in seen]
    return bool(ppl) and not gone, f"{len(ppl) - len(gone)} of {len(ppl)} people appear in a beat of {len(beats)}" + (f"; in no beat: {gone}" if gone else "")


def cut_checks():
    """The checks on the timed cut and its board, with its figures."""
    import boards
    import storyboard
    res = Checks()
    cut = _env.read_json("render/cut.json") or {}
    film = _env.read_json("film.json") or {}
    if not CUT.exists() or not cut or not film:
        res("film", False, "render/cut.mp4 is missing: run storyboard.py snap and film.py cut first")
        return res, {}
    v, a, secs = video_of(CUT)
    ok = (v.get("width"), v.get("height")) == (1080, 1920) and v.get("codec_name") == "h264" and v.get("profile") == "High" \
        and v.get("pix_fmt") == "yuv420p" and v.get("r_frame_rate") == "30/1" and LENGTH[0] <= secs <= longest() + 0.1
    res("film", ok, f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} {v.get('r_frame_rate')} fps, {secs:.1f} s, {CUT.stat().st_size / 1e6:.1f} MB, {CUT.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
    track = _env.read_json("music.json") or {}
    if track.get("file"):
        if not a:
            res("audio", False, "music was found but the cut has no audio track")
        else:
            lu, br = loudness(CUT), int(a.get("bit_rate") or 0)
            cues = track.get("sound_cues") or 0
            beats = len((_env.read_json("render/board-reel.json") or {}).get("beats") or [])
            under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
            mix = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU - 1})"
                   if under is not None else "no effects stem measured")
            res("audio", a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                and (not cues or (under is not None and under >= music.FX_UNDER_BED_LU - 1)),
                f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated; {mix}; {cues} sound cues over {beats} beats")
    else:
        res("audio", True, "no music was found; no audio track is required")
    black = ffmpeg_lines(CUT, ["-vf", "blackdetect=d=0.4:pix_th=0.10", "-an"], "black_start")
    res("black", not black, f"{len(black)} black stretches of 0.4 s or more" + (f": {black[0][-80:]}" if black else ""))
    held = held_from()
    frozen = frozen_in(CUT, held)
    res("frozen", not frozen, f"{len(frozen)} frozen stretches of 1.0 s or more before the stop at {held:.2f} s" + (f": {frozen[0][-40:]}" if frozen else ""))
    res("hook", cut["hook_frame"] <= storyboard.HOOK, f"the first event at frame {cut['hook_frame']}")
    ctx = boards.Ctx()
    ps = storyboard.problems(film["storyboard"], ctx, film["bpm"])
    res("board", not ps, f"{len(ps)} problems on 9:16, 1:1 and 16:9" + (f"; {ps[0][0]}: {ps[0][1]}" if ps else ""))
    rep = _env.read_json("render/cut-report.json") or {}
    bad = [f["text"][:160] for f in rep.get("findings", []) if f["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    res("people", *people_check())
    m = cut.get("measure") or {}
    if m:
        figures(res, m)
    fig = {"cut": sha(CUT), "style": film["style"], "duration": round(secs, 2), "frames": cut["frames"], "held_from": round(held, 2) if held != float("inf") else None,
           "hook_frame": cut["hook_frame"], "board_problems": [f"{w}: {m_}" for w, m_ in ps], "roles": cut.get("roles")}
    return res, fig


def made():
    """What the last render made (engine.json's `made`): the formats and whether the story cards; the reel alone when
    engine.json names nothing."""
    m = (_env.read_json("engine.json") or {}).get("made") or {}
    return set(m.get("formats") or ["reel"]) | {"reel"}, bool(m.get("stories"))


def cards_check():
    if not made()[1]:
        extra = sorted(f.name for f in CARDS.glob("*.png")) if CARDS.exists() else []
        return not extra, "no story card for each person asked for" + (f", and out/people/ holds {', '.join(extra[:3])}" if extra else ", none in out/people/")
    ppl = the_people()
    if not ppl:
        return False, "no people in the film"
    have = {f.stem.split("-", 1)[1]: f for f in CARDS.glob("[0-9][0-9]-*.png")} if CARDS.exists() else {}
    missing = [h for h in ppl if h not in have]
    wrong = [h for h in ppl if h in have and png_size(have[h]) != (1080, 1920)]
    same = len({sha(have[h]) for h in ppl if h in have}) < len([h for h in ppl if h in have])
    return not missing and not wrong and not same, (f"{len(ppl) - len(missing)} of {len(ppl)} stills in out/people/ at 1080x1920"
                                                    + (f"; missing {missing}" if missing else "") + (f"; wrong size {wrong}" if wrong else "")
                                                    + ("; two stills are the same image" if same else ""))


def formats_check(seconds):
    bad = []
    if not Path("out/film.mp4").exists() or not CUT.exists() or sha("out/film.mp4") != sha(CUT):
        bad.append("out/film.mp4 is not the checked cut")
    held = held_from()
    formats = made()[0]
    for kind, f in KINDS.items():
        size = SIZES[f]
        if kind not in formats:
            if Path(f).exists():
                bad.append(f"{f} is in out/, and the render did not make it (nobody asked for it)")
            continue
        if not Path(f).exists():
            bad.append(f"{f} is missing")
            continue
        v, _, secs = video_of(f)
        if (v.get("width"), v.get("height")) != size or v.get("profile") != "High" or v.get("r_frame_rate") != "30/1" or abs(secs - seconds) > 0.5:
            bad.append(f"{f} is {v.get('width')}x{v.get('height')} {v.get('profile')} {v.get('r_frame_rate')}, {secs:.1f} s")
        if f != "out/film.mp4":
            if ffmpeg_lines(f, ["-vf", "blackdetect=d=0.4:pix_th=0.10", "-an"], "black_start"):
                bad.append(f"{f} has a black stretch")
            if frozen_in(f, held):
                bad.append(f"{f} freezes before the stop")
    names = {"reel": "9:16", "square": "1:1", "wide": "16:9"}
    return not bad, (", ".join(names[k] for k in KINDS if k in formats) + " at 30 fps, H.264 High, one length") if not bad else "; ".join(bad)


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("lines", "text", "handle", "details", "line") and isinstance(v, (str, list)):
                acc += [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)]
            else:
                words_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            words_in(v, acc)
    return acc


def gate_checks():
    import boards
    import vote
    res, fig = cut_checks()
    check = res
    check("formats", *formats_check(fig.get("duration", 0)))
    check("cards", *cards_check())
    texts = words_in(_env.read_json("render/board-reel.json") or {}, [])
    for f in ("out/caption.md", "brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", texts and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("taste.md").read_text().lower() if Path("taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    check("research", tm and not heads and Path("taste.json").exists(), "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    sbs = sorted(Path("storyboards").glob("*/storyboard.json"))
    full = [b.parent for b in sbs if (b.parent / "storyboard.md").exists() and (b.parent / "sheet.png").exists()]
    import storyboard
    n = len(storyboard.looks())
    check("boards", len(sbs) == n and len(full) == n and Path("out/boards.png").exists(),
          f"{len(sbs)} of {n} storyboards, {len(full)} with storyboard.md and a sheet"
          + ("" if Path("out/boards.png").exists() else "; out/boards.png is missing"))
    win = _env.read_json("winner.json") or {}
    check("vote", Path("vote.md").exists() and win.get("board"), f"picked {win.get('board')} ({win.get('name')}) by {win.get('by')}")
    ok, why = vote.scored(fig.get("cut"))
    check("scored", ok, why.split(", ")[0] + " is for this cut and complete" if ok else why)
    if ok:
        s, mean, least = vote.standing(_env.read_json(vote.rounds()[-1]))
        check.figure("critic", why, {"mean": mean, "least": least, "at_bar": vote.at_bar(mean, least)})
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    register = (_env.read_json("taste.json") or {}).get("register", {})
    lower = register.get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    # their hashtags, or none when they never use one
    reg = cap and (not lower or body == body.lower()) and (1 <= len(tags) <= 10 if register.get("hashtags") else not tags)
    untagged = [h for h in the_people() if not re.search(r"@" + re.escape(h) + r"(?!\w|\.\w)", cap)]
    missing = [f for f in ("review.html", "cover.png", "story.png") if not (OUT / f).exists()]
    stray = sorted(f.name for f in OUT.iterdir() if f.name not in DELIVERABLES) if OUT.exists() else []
    check("deliver", reg and not untagged and not missing and not stray,
          f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "") +
          (f", tags all {len(the_people())} people" if not untagged else f"; caption does not tag {untagged}") +
          "".join(f"; {f} missing" for f in missing) + (f"; out/ also holds {', '.join(stray)}, which is not a deliverable" if stray else ""))
    return res, fig


def report(res, fig, path):
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, **fig, "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(("GATE " + ("GREEN" if not bad else f"RED ({len(bad)} failing)")) if path.endswith("gate.json") else
          ("CHECKS PASS" if not bad else f"{len(bad)} CHECKS FAIL"))
    return 0 if not bad else 1


def gate(run=None):
    """The gate, printed and written to qa/gate.json; returns the failing checks as (name, detail). deliver.py calls it
    inside its own lock (`run`), so every process the gate starts holds that lock."""
    global _run
    _run = run
    res, fig = gate_checks()
    report(res, fig, "qa/gate.json")
    return [(r[0], r[2]) for r in res if r[1] is False]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    _env.enter_run()
    if a.cmd == "check":
        return report(*cut_checks(), "qa/check.json")
    return 1 if gate() else 0


if __name__ == "__main__":
    sys.exit(main())
