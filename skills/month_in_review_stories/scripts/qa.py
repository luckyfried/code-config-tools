#!/usr/bin/env python3
"""Movement 6: the measurable checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the film and the cards only (run before the critics watch the cut)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes

The gate refuses:
  film      out/film.mp4 is not 1080x1920 H.264 high profile yuv420p at 30 fps, or runs outside 15 +-0.5 s
  cards     build/cards.json does not list three to five cards, a static card is not a 1080x1920 PNG, or an
            animated card is not 1080x1920 H.264 yuv420p at 30 fps running 15 +-0.5 s
  audio     music was found but the film or a card has no AAC track near 192 kbps, or the film's loudness is off
            -14 LUFS by more than 1 LU
  black     a black stretch of 0.4 s or more in the film or a card (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.5 s or more in the film or a card (ffmpeg freezedetect)
  safe      text that left its safe box or was cut off (SAFE_BREACH in build/render-report.json), a font that did
            not load, or a render job that failed
  text      a placeholder string anywhere in the words on screen, the caption, the brief or the review page
  template  out/template.json does not parse, or does not name every card (number, role, title, both files)
  research  build/taste.md (this month against your year / you are / you like / your style / your voice / avoid)
            or build/taste.json is missing
  boards    three storyboards, each with storyboard.md, storyboard.json and six style-sheet frames
  vote      build/vote.md and build/winner.json are missing
  clips     the storyboard lists clips and build/clips.json does not account for every one
  critic    the latest cut round in build/critic/ is not for these files, or scores below 4 with the one fix unspent
  deliver   out/caption.md, out/review.html or out/brief.md is missing, or the caption is not in their register
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import vote  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|@handle\b|your_handle", re.I)
FILM = Path("out/film.mp4")
LENGTH = (14.5, 15.5)


def probe(p):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,profile,width,height,pix_fmt,r_frame_rate,bit_rate:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    return json.loads(r.stdout or "{}")


def png_size(p):
    with open(p, "rb") as f:
        head = f.read(24)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def detect(video):
    """Black stretches of 0.4 s or more and frozen stretches of 1.5 s or more, in one decode."""
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(video), "-vf",
                        "blackdetect=d=0.4:pix_th=0.10,freezedetect=n=-60dB:d=1.5", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    lines = r.stderr.splitlines()
    return [ln for ln in lines if "black_start" in ln], [ln for ln in lines if "freeze_start" in ln]


def loudness(video):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def streams(p):
    pr = probe(p)
    v = next((s for s in pr.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in pr.get("streams", []) if s.get("codec_type") == "audio"), None)
    return v, a, float(pr.get("format", {}).get("duration") or 0)


def video_ok(v, secs, high=False):
    return (v.get("width"), v.get("height")) == (1080, 1920) and v.get("codec_name") == "h264" and v.get("pix_fmt") == "yuv420p" \
        and v.get("r_frame_rate") == "30/1" and LENGTH[0] <= secs <= LENGTH[1] and (not high or v.get("profile") == "High")


def describe(v, secs):
    return f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} {v.get('r_frame_rate')} fps, {secs:.2f} s"


def cards_listed():
    return (_env.read_json("build/cards.json") or {}).get("cards") or []


def film_checks():
    res = []
    def check(name, ok, detail):
        res.append((name, bool(ok), detail))
    if not FILM.exists():
        check("film", False, "out/film.mp4 is missing")
        return res
    v, a, secs = streams(FILM)
    check("film", video_ok(v, secs, high=True), describe(v, secs))
    cards = cards_listed()
    bad, seen = [], []
    for c in cards:
        st, an = Path(c["static"]), Path(c["animated"])
        sz = png_size(st) if st.exists() else None
        if sz != (1080, 1920):
            bad.append(f"{st} {'at %dx%d' % sz if sz else 'is missing'}")
        if not an.exists():
            bad.append(f"{an} is missing")
            continue
        cv, ca, cs = streams(an)
        seen.append(f"{c['id']} {cs:.2f} s")
        if not video_ok(cv, cs):
            bad.append(f"{an}: {describe(cv, cs)}")
    check("cards", 3 <= len(cards) <= 5 and not bad, f"{len(cards)} cards, each a 1080x1920 PNG and a 15 s H.264 story ({', '.join(seen)})"
          + (f"; {bad[0]}" + (f" and {len(bad) - 1} more" if len(bad) > 1 else "") if bad else ""))
    videos = [FILM] + [Path(c["animated"]) for c in cards if Path(c["animated"]).exists()]
    music = (_env.read_json("build/music.json") or {}).get("file")
    if music:
        silent = [str(p) for p in videos if not streams(p)[1]]
        lu = loudness(FILM) if a else None
        br = int((a or {}).get("bit_rate") or 0)
        check("audio", a and a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0 and not silent,
              f"film {(a or {}).get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated; {len(videos) - 1 - len(silent)} of {len(videos) - 1} cards carry the music"
              + (f"; no audio in {silent}" if silent else ""))
    else:
        check("audio", True, "no music was found; no audio track is required")
    blacks, frozen = [], []
    for p in videos:
        b, f = detect(p)
        blacks += [f"{p.name}: {ln[-70:]}" for ln in b]
        frozen += [f"{p.name}: {ln[-50:]}" for ln in f]
    check("black", not blacks, f"{len(blacks)} black stretches of 0.4 s or more in {len(videos)} videos" + (f": {blacks[0]}" if blacks else ""))
    check("frozen", not frozen, f"{len(frozen)} frozen stretches of 1.5 s or more in {len(videos)} videos" + (f": {frozen[0]}" if frozen else ""))
    rep = _env.read_json("build/render-report.json") or {}
    bad = [f["text"][:160] for f in rep.get("findings", []) if f["text"].startswith(("SAFE_BREACH", "FONT_ERROR", "RENDER_ERROR", "UNKNOWN_KIND"))]
    check("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, "
          f"{len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    return res


def template_check():
    p = Path("out/template.json")
    if not p.exists():
        return False, "out/template.json is missing"
    try:
        t = json.loads(p.read_text())
    except ValueError as e:
        return False, f"out/template.json does not parse: {e}"
    cards = cards_listed()
    rows = {r.get("n"): r for r in t.get("cards") or []}
    miss = [c["id"] for c in cards if not (rows.get(c["n"]) or {}).get("role") == c["role"] or not (rows.get(c["n"]) or {}).get("title")
            or not (rows.get(c["n"]) or {}).get("static") or not (rows.get(c["n"]) or {}).get("animated")]
    keys = [k for k in ("structure", "type", "palette", "series_mark") if not t.get(k)]
    return not miss and not keys and len(rows) == len(cards), (f"{len(rows)} cards named of {len(cards)}" + (f"; not named: {miss}" if miss else "")
                                                                + (f"; missing {keys}" if keys else ""))


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("kicker", "headline", "line", "text", "meta", "label", "signoff", "name") and isinstance(v, str):
                acc.append(v)
            else:
                words_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            words_in(v, acc)
    return acc


def gate_checks():
    res = film_checks()
    def check(name, ok, detail):
        res.append((name, bool(ok), detail))
    film = _env.read_json("build/film.json") or {}
    texts = words_in({"film": film.get("film"), "cards": film.get("cards")}, [])
    for f in ("out/caption.md", "out/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    check("template", *template_check())
    tm = Path("build/taste.md").read_text().lower() if Path("build/taste.md").exists() else ""
    heads = [h for h in ("this month against your year", "you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    check("research", tm and not heads and Path("build/taste.json").exists(),
          "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    boards = sorted(Path("build/storyboards").glob("*/storyboard.json"))
    full = [b.parent for b in boards if (b.parent / "storyboard.md").exists() and len(list((b.parent / "frames").glob("0[1-6].png"))) == 6]
    check("boards", len(boards) == 3 and len(full) == 3, f"{len(boards)} storyboards, {len(full)} with storyboard.md and six frames")
    win = _env.read_json("build/winner.json") or {}
    check("vote", Path("build/vote.md").exists() and win.get("board"), f"winner {win.get('board')} ({win.get('name')})")
    want = {c["id"] for c in film.get("clips", [])}
    got = set(((_env.read_json("build/clips.json") or {}).get("clips") or {}).keys())
    check("clips", want <= got, f"{len(want)} clips listed, {len(want & got)} accounted for" + (f"; missing {sorted(want - got)}" if want - got else ""))
    rounds = sorted(Path("build/critic").glob("cut-*.json"), key=lambda p: int(p.stem.split("-")[1]))
    if not rounds:
        check("critic", False, "no cut round in build/critic/: run vote.py cut and fill it in")
    else:
        last = _env.read_json(rounds[-1])
        sc = [v for c in last.get("critics", {}).values() for e in c.get("boards", {}).values() for v in (e.get("scores") or {}).values()]
        same = FILM.exists() and last.get("film") == vote.fingerprint()
        done = sc and all(isinstance(x, int) for x in sc)
        ok = same and done and (min(sc) >= 4 or len(rounds) >= 2)
        check("critic", ok, f"round {len(rounds)}, lowest {min(sc) if done else '?'}" + ("" if same else "; the round is not for the current film and cards"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("build/taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    check("deliver", reg and Path("out/review.html").exists() and Path("out/brief.md").exists(),
          f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "") +
          ("" if Path("out/review.html").exists() else "; review.html missing") + ("" if Path("out/brief.md").exists() else "; brief.md missing"))
    return res


def report(res, path):
    bad = [r for r in res if not r[1]]
    for name, ok, detail in res:
        print(f"{'PASS' if ok else 'FAIL'}  {name:9s} {detail}")
    _env.write_json(path, {"pass": not bad, "checks": [{"check": n, "pass": o, "detail": d} for n, o, d in res]})
    print("GATE " + ("GREEN" if not bad else f"RED ({len(bad)} failing)") if path.endswith("gate.json") else
          ("CHECKS PASS" if not bad else f"{len(bad)} CHECKS FAIL"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "gate"])
    a = ap.parse_args()
    if a.cmd == "check":
        return report(film_checks(), "build/qa/check.json")
    return report(gate_checks(), "build/qa/gate.json")


if __name__ == "__main__":
    sys.exit(main())
