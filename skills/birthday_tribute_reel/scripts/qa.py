#!/usr/bin/env python3
"""Movement 5: the measured checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder, B = the run's folder):
    python3 S/scripts/qa.py timed       # the cut, before the film renders (film.py render refuses without it)
    python3 S/scripts/qa.py check       # the films and stills the render made (run before the critics watch the cut)
    python3 S/scripts/qa.py gate        # timed, check and the run's records; exit 0 when no check fails

Each check passes (PASS), fails (FAIL) or stays open (OPEN): a read that could not be made, or a film the critics
scored below the bar once the one fix is spent. The last line is GREEN when every check passes, RED (n failing) when
any fails, and OPEN (the open checks) when none fails and one is open; an open film is delivered with the page saying
what is open, and it is never called green.

Two figures are printed and written beside the checks and are never a pass or a fail: the critic reads them with the
strip, and a held composition is quiet by design.
  cuts      the cuts, as planned and as the picture shows them, and cuts a minute
  still     each second's change (read at an eighth of the frame so film grain is not counted as motion): the
            seconds under 0.5 and the longest run of them
timed reads them from the preview, check from the rendered reel.

timed (from B/film.json, B/preview/preview.json and B/critic/timed.json, all for the same cut):
  board     the board at the film's tempo passes storyboard.py check (frame, subject, words, photos, length, hook)
  preview   B/preview/preview.json is for this cut
  reads     the critic's four reads of the timed cut (vote.py timed), for this cut, each with its words and naming the
            frames vote.py timed cut from this cut's preview; open when a read was not made (with the reason), and failed
            when one fails or names none of this cut's frames
check (the rendered out/):
  format    out/film.mp4 1080x1920, and out/film-square.mp4 1080x1080 and out/film-wide.mp4 1920x1080 when the render
            made them (film-report.json's `made`, from film.py render --also), and none of them in out/ when it did
            not: H.264, yuv420p, 30 fps, inside 20 to 60 s, the reel within 1 s of the cut's length (the one the person asked
            for, when they asked), the square and the wide the reel's length within 1 s
  audio     with music, an AAC track near 192 kbps at -14 LUFS integrated, within 1 LU, with sound cues the effects
            stem at least music.FX_UNDER_BED_LU - 1 LU under the bed (both integrated, from music.json), and with a
            stop cue the film quiet after it (mean volume from a tenth of a second past the stop to the end at most
            QUIET dB); the row names the two numbers, the cue and beat counts, each cue's kind and second, and where
            the music stops with the volume after it, and refuses nothing on count
  black     no black frame at all, not even one (blackdetect at FLASH: a photograph the page failed to load leaves its
            frames black, one or a few at a time, and no look in this kit cuts to black), and no white stretch of 0.4 s or
            more (blackdetect on the negated picture, pure white only: a tab that lost its graphics context draws white, and a
            look's paper, however light, is never read as one)
  frozen    no frozen stretch of 1.0 s or more (freezedetect at -80 dB) starting before the board's stop: frames
            that repeat, as a stalled render's do; the film grain moving under a held composition is change, and the
            still the board holds from its stop to the end is the ending
  safe      no render job failed, and no font or photograph failed to load (B/render/film-report.json)
  stills    when the render made them, out/stills/ holds the settled frame of every rest moment in every rendered
            format; when it did not, out/stills/ holds none
  posts     out/post.png (1080x1080, the closer laid out for the feed) and out/story.png (1080x1920, the hook), from
            this render
gate adds:
  text      no placeholder in the words, the caption, the brief or the review page
  shared    every photograph on screen is one the two share (picks.json "shared")
  research  B/taste.md (you are / you like / your style / your voice / avoid) and B/taste.json
  boards    the storyboard, with storyboard.md, storyboard.json, its three sheets and its type read
  vote      B/vote.md and B/winner.json
  board     the critics' swap test: no beat the panel named is unchanged in the board
  critic    the latest cut round in B/critic/ is for this film and complete as vote.py verdict counts it (every score
            whole, every paragraph 25 words or more naming the round's frames, the worst thing named), and at the bar (a
            mean of 4.5, no score under 4); below it the row fails in round 1 (fix once) and is open once the fix is spent
  deliver   out/ holds the deliverables and nothing else: the films and stills the render made, out/post.png,
            out/story.png, out/caption.md (in their register, naming the named one by @handle or first name) and
            out/review.html; brief.md is B/brief.md
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
import shared as shared_py  # noqa: E402
import studio  # noqa: E402

PLACEHOLDER = re.compile(r"\bTODO\b|\bTBD\b|\blorem\b|\bipsum\b|\{\{|\}\}|\bXXX\b|\bPLACEHOLDER\b|@handle\b|your_handle|\bundefined\b|\bNaN\b|\bNone\b")
FILM = Path("out/film.mp4")
POSTS = {"post": (Path("out/post.png"), (1080, 1080)), "story": (Path("out/story.png"), (1080, 1920))}
OPEN = "open"
FILMS = {"reel": (FILM, (1080, 1920)), "feed": (Path("out/film-square.mp4"), (1080, 1080)), "wide": (Path("out/film-wide.mp4"), (1920, 1080))}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def probe(p, run=None):
    r = (run.spawn if run else subprocess.run)([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def detect(film, flt, key, run=None):
    return [ln for ln in studio.ff(["-i", str(film), "-vf", flt, "-an", "-f", "null", "-"], run).splitlines() if key in ln]


def held_from(f):
    """Where the board holds its picture still to the end (its `stop` sound cue), in seconds; never, without one."""
    stop = next((c["at"] for c in f.get("sound") or [] if c["kind"] == "stop"), None)
    return stop * 60 / f["bpm"] if stop is not None else float("inf")


# the mean volume, dB, a film may keep after its stop cue: the music's tail is gone a tenth of a second after it
QUIET = -45
# the shortest black stretch the black check reads, seconds: under one frame at 30 fps, so a single black frame counts
FLASH = 0.03


def after(film, at, run=None):
    """The mean volume of the film's sound from `at` seconds to its end, in dB; None when nothing is measured."""
    m = re.findall(r"mean_volume:\s+(-?[\d.]+) dB", studio.ff(["-ss", f"{at:.3f}", "-i", str(film), "-vn", "-af", "volumedetect", "-f", "null", "-"], run))
    return float(m[-1]) if m else None


def loudness(film, run=None):
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", studio.ff(["-i", str(film), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"], run))
    return float(m[-1]) if m else None


class Checks(list):
    """Checks, (name, passed, detail) with passed True, False or OPEN, and figures, (name, None, detail, values): a
    figure is measured and shown, never passed or failed."""

    def __call__(self, name, ok, detail):
        self.append((name, ok if ok == OPEN else bool(ok), detail))

    def figure(self, name, detail, values):
        self.append((name, None, detail, values))


def figures(res, m):
    """The cut's two figures from a measurement (`studio.measure`)."""
    res.figure("cuts", f"{m['cuts']} cuts, {m['cuts_per_minute']} a minute", {k: m[k] for k in ("cuts", "cuts_per_minute", "planned_cuts", "extra_scene_cuts")})
    res.figure("still", f"seconds under 0.5: {m['seconds_under_half']}, longest run {m['longest_run_under_half']}",
               {k: m[k] for k in ("luma", "seconds_under_half", "longest_run_under_half")})


def cut():
    f = _env.read_json(f"{_env.B}/film.json")
    if not f:
        sys.exit(f"{_env.B}/film.json is missing: run storyboard.py snap first")
    return f


def timed_checks():
    import compose
    import storyboard
    import vote
    res = Checks()
    f = cut()
    iss = storyboard.board_issues(f, compose.Ctx(), storyboard.allowed_photos(), f["bpm"])
    res("board", not iss, f"{len(iss)} issues at {f['bpm']} bpm, {f['seconds']} s, the hook event at frame {f['hook_frame']}"
        + (f": {iss[0]}" if iss else ""))
    pv = _env.read_json(f"{_env.B}/preview/preview.json") or {}
    if pv.get("hash") != f["hash"]:
        res("preview", False, "B/preview/preview.json is not for this cut: run film.py preview")
    else:
        res("preview", True, f"B/preview/preview.json, {pv['seconds']} s")
        figures(res, pv)
    ct = _env.read_json(f"{_env.B}/critic/timed.json") or {}
    if ct.get("hash") != f["hash"]:
        res("reads", False, "B/critic/timed.json is not for this cut: run vote.py timed and write the four reads")
    else:
        reads = ct.get("reads") or {}
        bad, open_ = vote.read_problems(ct)
        failed = [k for k in vote.READS if (reads.get(k) or {}).get("pass") is False]
        why = "; ".join(f"{k}: {reads[k]['read']}" for k in open_)
        res("reads", OPEN if open_ and not bad and not failed else not bad and not failed,
            f"failed: {', '.join(failed)}" if failed else f"not written: {', '.join(bad)}" if bad
            else f"not made: {why}" if open_ else "the critic's four reads pass, each naming this cut's frames")
    return res, f


def made():
    """What the last render made (film-report.json's `made`): the formats and whether the stills; the reel alone when
    the report names nothing."""
    m = (_env.read_json(f"{_env.B}/render/film-report.json") or {}).get("made") or {}
    return set(m.get("formats") or ["reel"]) | {"reel"}, bool(m.get("stories"))


def film_checks(run=None):
    """The rendered out/; under a command's lock (`run`, deliver's) every process starts through run.spawn."""
    import compose
    import music
    res = Checks()
    f = cut()
    formats, stills = made()
    lo, hi = compose.LENGTH
    track = _env.read_json(f"{_env.B}/music.json") or {}
    held = held_from(f)
    measured, reel_secs = None, None
    for fmt, (film, size) in FILMS.items():
        if fmt not in formats:
            if film.exists():
                res("format", False, f"{film} is in out/, and the render did not make it (nobody asked for it)")
            continue
        if not film.exists():
            res("format", False, f"{film} is missing")
            continue
        p = probe(film, run)
        v = next((x for x in p.get("streams", []) if x.get("codec_type") == "video"), {})
        a = next((x for x in p.get("streams", []) if x.get("codec_type") == "audio"), None)
        secs = float(p.get("format", {}).get("duration") or 0)
        reel_secs = secs if fmt == "reel" else reel_secs
        want = f.get("length") if fmt == "reel" else secs if reel_secs is None else reel_secs
        ok = (v.get("width"), v.get("height")) == size and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
            and v.get("r_frame_rate") == "30/1" and lo <= secs <= hi and want is not None and abs(secs - want) <= 1.0
        res("format", ok, f"{film}: {v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                          f"{v.get('r_frame_rate')} fps, {secs:.2f} s" + (f" of {want:g} s" if want is not None else ", and the cut names no length")
                          + f", {film.stat().st_size / 1e6:.1f} MB, {film.stat().st_size * 8e-6 / max(secs, 0.001):.1f} Mbit/s")
        if track.get("file"):
            lu = loudness(film, run) if a else None
            br = int((a or {}).get("bit_rate") or 0)
            cues = track.get("sound_cues") or 0
            under = track["bed_lufs"] - track["fx_lufs"] if "fx_lufs" in track else None
            mix = (f"bed {track['bed_lufs']} LUFS, effects {track['fx_lufs']} LUFS, {under:.1f} LU under (at least {music.FX_UNDER_BED_LU - 1})"
                   if under is not None else "no effects stem measured")
            where = ", ".join(f"{c['kind']} {c['at'] * 60 / f['bpm']:.2f} s" for c in f.get("sound") or [] if c["kind"] != "stop")
            quiet = after(film, held + 0.1, run) if a and held + 0.1 < secs else None
            stop = (f"the music stops at {held:.2f} s, {quiet} dB mean after it (at most {QUIET})" if quiet is not None
                    else "no stop cue inside the film")
            res("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0
                and (not cues or (under is not None and under >= music.FX_UNDER_BED_LU - 1)) and (quiet is None or quiet <= QUIET),
                f"{film}: " + (f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated" if a else "no audio track")
                + f"; {mix}; {cues} sound cues over {len(f.get('beats') or [])} beats, at {where or 'none'}; {stop}")
        black = detect(film, f"blackdetect=d={FLASH}:pix_th=0.10", "black_start", run)
        white = detect(film, "negate,blackdetect=d=0.4:pix_th=0.01", "black_start", run)
        res("black", not black and not white, f"{film}: {len(black)} black frames or stretches and {len(white)} white stretches of 0.4 s or more")
        frozen = [ln for ln in detect(film, "freezedetect=n=-80dB:d=1.0", "freeze_start", run) if float(ln.split(":")[-1]) < held - 0.04]
        res("frozen", not frozen, f"{film}: {len(frozen)} frozen stretches of 1.0 s or more" + (f" ({frozen[0][-40:]})" if frozen else ""))
        if fmt == "reel":
            measured = studio.measure(film, f["cuts"], f["hook_frame"], strips=Path(_env.B) / "qa", run=run)
            _env.write_json(f"{_env.B}/qa/film.check.json", measured)
            figures(res, measured)
    rep = _env.read_json(f"{_env.B}/render/film-report.json") or {}
    bad = [x["text"][:160] for x in rep.get("findings", []) if x["text"].startswith(("FONT_ERROR", "RENDER_ERROR", "IMAGE_ERROR"))]
    res("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, {len(bad)} findings"
        + (f": {bad[0]}" if bad else ""))
    have = {p.name for p in Path("out/stills").glob("*.png")}
    if stills:
        want = [f"{fmt}-{bid}.png" for fmt in FILMS if fmt in formats for bid in f.get("rest") or []]
        miss = [w for w in want if w not in have]
        res("stills", want and not miss, f"{len(want) - len(miss)} of {len(want)} rest stills in out/stills/" + (f"; missing {miss[:3]}" if miss else ""))
    else:
        res("stills", not have, "no stills asked for" + (f", and out/stills/ holds {', '.join(sorted(have)[:3])}" if have else ", none in out/"))
    for name, (png, size) in POSTS.items():
        got = None
        if png.exists():
            v = next((x for x in probe(png, run).get("streams", []) if x.get("codec_type") == "video"), {})
            got = (v.get("width"), v.get("height"))
        res("posts", got == size and (rep.get("made") or {}).get("posts"),
            f"{png}: " + (f"{got[0]}x{got[1]}" if got else "missing") + f" (wanted {size[0]}x{size[1]}, from this render)")
    return res, f, measured


def shared_check(film):
    """Every photograph on screen is one of the two."""
    import grade
    allowed = {grade.graded_name(x) for x in (_env.read_json(f"{_env.B}/picks.json") or {}).get("shared", [])}
    used = {r["file"] for r in (film.get("photos") or {}).values()}
    bad = sorted(used - allowed)
    who = shared_py.called((_env.read_json(f"{_env.B}/shared.json") or {}).get("who") or {})
    return bool(allowed) and bool(used) and not bad, (f"{len(used)} photographs on screen, all of them with {who}" if not bad
                                                      else f"{len(bad)} photographs not shared with {who}: {bad[:3]}")


def words_in(film):
    import compose
    if not film:
        return []
    fl = compose.lay(film, "reel", film["bpm"])["film"]
    lines = [l for c in fl["cards"] for l in [*c["head"], *c["lines"]]] + [fl["closer"]["big"], fl["closer"]["last"], *fl["closer"]["lines"]]
    return [l["text"] for l in lines if isinstance(l.get("text"), str)]


def gate_checks(run=None):
    """deliver calls it in its own process with its lock (`run`)."""
    import compose
    res, film = timed_checks()
    more, _, _ = film_checks(run)
    res += more
    check = res
    texts = words_in(film)
    for f in ("out/caption.md", f"{_env.B}/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path(f"{_env.B}/taste.md").read_text().lower() if Path(f"{_env.B}/taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    check("research", tm and not heads and Path(f"{_env.B}/taste.json").exists(),
          "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    boards = sorted(Path(f"{_env.B}/storyboards").glob("*/storyboard.json"))
    parts = ("storyboard.md", "sheet.png", "sheet-feed.png", "sheet-wide.png", "type.json", "look.png")
    full = [b.parent for b in boards if all((b.parent / x).exists() for x in parts)]
    n = len(compose.TRIO)
    check("boards", len(boards) == n and len(full) == n, f"{len(boards)} storyboards for {n} looks, {len(full)} with storyboard.md, three sheets, its look and a type read")
    win = _env.read_json(f"{_env.B}/winner.json") or {}
    check("vote", Path(f"{_env.B}/vote.md").exists() and win.get("board"), f"winner {win.get('board')} ({win.get('name')})")
    import storyboard
    winner = _env.read_json(storyboard.boards_dir() / str(win.get("board")) / "storyboard.json") if win.get("board") else None
    left = storyboard.unswapped(winner, win) if winner else []
    check("board", winner and not left, f"board {win.get('board')}: swap test named {len(win.get('swap') or {})}, still unchanged {len(left)}")
    check("shared", *shared_check(film))
    import vote
    rounds = vote.rounds()
    if not rounds:
        check("critic", False, f"no cut round in {_env.B}/critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        bad = vote.problems(last, vote.CUT_PANEL, ["film"], frames=last.get("frames") or rounds[-1].with_suffix(""))
        sc = [last["critics"][c]["boards"]["film"]["scores"][k] for c in vote.CUT_PANEL for k in vote.CRITERIA] if not bad else []
        same = FILM.exists() and last.get("film") == sha(FILM)
        below = bool(sc) and not vote.at_bar(sc)
        ok = same and not bad and (OPEN if below and len(rounds) >= 2 else not below)
        check("critic", ok, f"round {len(rounds)}, " + (vote.against_bar(sc) if not bad else f"not complete: {bad[0]}")
              + ("" if same else "; the round is not for the current out/film.mp4")
              + ("; the one fix is spent" if below and len(rounds) >= 2 else "; fix the worst thing once (vote.py verdict)" if below else ""))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json(f"{_env.B}/taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and len(tags) <= 10
    who = (_env.read_json(f"{_env.B}/shared.json") or {}).get("who") or {}
    names = [n.lower() for n in (f"@{who.get('handle')}" if who.get("handle") else None, who.get("first")) if n]
    named = any(re.search(r"(?<![\w.@])" + re.escape(n) + r"(?![\w])", cap.lower()) for n in names)
    formats, stills = made()
    want = ({"caption.md", "review.html", "post.png", "story.png"} | {FILMS[x][0].name for x in formats} | ({"stills"} if stills else set())
            | {n for n in ("looks", "boards.png") if Path("out", n).exists()})
    have = {p.name for p in Path("out").iterdir()} if Path("out").exists() else set()
    check("deliver", reg and named and not want - have and not have - want,
          f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "") +
          (f", names {names[0]}" if named else f"; the caption does not name {' or '.join(names) or 'the named one'}") +
          (f"; out/ is missing {', '.join(sorted(want - have))}" if want - have else "") +
          (f"; out/ holds {', '.join(sorted(have - want))}, which is not a deliverable" if have - want else "; out/ holds the deliverables only"))
    return res, film


def summary(res):
    """GREEN, RED (n failing) or OPEN (the open checks)."""
    bad = [r for r in res if r[1] is False]
    opened = list(dict.fromkeys(r[0] for r in res if r[1] == OPEN))
    return "GREEN" if not bad and not opened else f"RED ({len(bad)} failing)" if bad else f"OPEN ({', '.join(opened)})"


def report(res, path, f, label):
    """Exit 0 when no check fails (green or open), else 1."""
    bad = [r for r in res if r[1] is False]
    for name, ok, detail, *_ in res:
        print(f"{'' if ok is None else 'OPEN' if ok == OPEN else 'PASS' if ok else 'FAIL':4s}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, "green": summary(res) == "GREEN", "open": [r[0] for r in res if r[1] == OPEN],
                           "hash": f.get("hash"), "film": str(FILM.resolve()),
                           "checks": [{"check": r[0], "pass": r[1], "detail": r[2]} for r in res if r[1] is not None],
                           "figures": {r[0]: dict(r[3], detail=r[2]) for r in res if r[1] is None}})
    print(f"{label} {summary(res)}")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["timed", "check", "gate"])
    a = ap.parse_args()
    if a.cmd == "timed":
        res, f = timed_checks()
        return report(res, f"{_env.B}/qa/timed.json", f, "TIMED")
    if a.cmd == "check":
        res, f, _ = film_checks()
        return report(res, f"{_env.B}/qa/check.json", f, "CHECKS")
    res, f = gate_checks()
    return report(res, f"{_env.B}/qa/gate.json", f, "GATE")


if __name__ == "__main__":
    sys.exit(main())
