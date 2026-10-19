#!/usr/bin/env python3
"""Movement 6: the measurable checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the film, the people in it and their story cards only (run before the critics watch the cut)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes

The gate refuses:
  film      out/film.mp4 is not 1080x1920 H.264 high profile yuv420p at 30 fps, or runs outside 30-60 s
  audio     music was found but the film has no AAC track near 192 kbps, or its loudness is off -14 LUFS by more than 1 LU
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.5 s or more (ffmpeg freezedetect): nothing on screen may stand still that long
  safe      text that left its safe box or was cut off (SAFE_BREACH in build/render-report.json), a font that did
            not load, or a render job that failed
  text      a placeholder string anywhere in the film's words, the caption, the brief or the review page
  cards     a person in build/taste.json has no out/people/NN-<handle>.png at 1080x1920, or two cards are the same image
  people    a person in build/taste.json appears in no beat of the film (a board row, a portrait, or a wall tile)
  research  build/taste.md (you are / you like / your style / your voice / avoid) or build/taste.json is missing
  boards    three storyboards, each with storyboard.md, storyboard.json and six style-sheet frames
  vote      build/vote.md and build/winner.json are missing
  clips     the film's storyboard lists clips and build/clips.json does not account for every one
  critic    the latest cut round in build/critic/ is not for this film, or scores below 4 with the one fix unspent
  deliver   out/caption.md, out/review.html or out/brief.md is missing, the caption is not in their register, or it
            does not tag every person
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

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|@handle\b|your_handle", re.I)
FILM = Path("out/film.mp4")
CARDS = Path("out/people")
LENGTH = (30, 60)


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


def detect(flt, key):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(FILM), "-vf", flt, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [ln for ln in r.stderr.splitlines() if key in ln]


def loudness():
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", "-i", str(FILM), "-af", "ebur128=framelog=quiet", "-vn", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def film_checks():
    res = []
    def check(name, ok, detail):
        res.append((name, bool(ok), detail))
    if not FILM.exists():
        check("film", False, "out/film.mp4 is missing")
        return res
    p = probe(FILM)
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
    secs = float(p.get("format", {}).get("duration") or 0)
    ok = (v.get("width"), v.get("height")) == (1080, 1920) and v.get("codec_name") == "h264" and v.get("profile") == "High" \
        and v.get("pix_fmt") == "yuv420p" and v.get("r_frame_rate") == "30/1" and LENGTH[0] <= secs <= LENGTH[1]
    check("film", ok, f"{v.get('width')}x{v.get('height')} {v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} "
                      f"{v.get('r_frame_rate')} fps, {secs:.1f} s")
    music = (_env.read_json("build/music.json") or {}).get("file")
    if music:
        if not a:
            check("audio", False, "music was found but the film has no audio track")
        else:
            lu = loudness()
            br = int(a.get("bit_rate") or 0)
            check("audio", a.get("codec_name") == "aac" and br >= 150000 and lu is not None and abs(lu + 14) <= 1.0,
                  f"{a.get('codec_name')} {br // 1000} kbps, {lu} LUFS integrated")
    else:
        check("audio", True, "no music was found; no audio track is required" + (" (the film has one)" if a else ""))
    black = detect("blackdetect=d=0.4:pix_th=0.10", "black_start")
    check("black", not black, f"{len(black)} black stretches of 0.4 s or more" + (f": {black[0][-80:]}" if black else ""))
    frozen = detect("freezedetect=n=-60dB:d=1.5", "freeze_start")
    check("frozen", not frozen, f"{len(frozen)} frozen stretches of 1.5 s or more" + (f": {frozen[0][-60:]}" if frozen else ""))
    rep = _env.read_json("build/render-report.json") or {}
    bad = [f["text"][:160] for f in rep.get("findings", []) if f["text"].startswith(("SAFE_BREACH", "FONT_ERROR", "RENDER_ERROR", "UNKNOWN_KIND"))]
    check("safe", rep and not rep.get("failed") and not bad, f"{rep.get('jobs', 0)} render jobs, {rep.get('failed', '?')} failed, "
          f"{len(bad)} findings" + (f": {bad[0]}" if bad else ""))
    check("cards", *cards_check())
    check("people", *people_check())
    return res


def the_people():
    """The people of the film and the brief, in rank order: build/taste.json (the agent's edit), else build/people.json."""
    ppl = (_env.read_json("build/taste.json") or {}).get("people") or (_env.read_json("build/people.json") or {}).get("people") or []
    return [x["handle"] for x in ppl if x.get("handle")]


def cards_check():
    """One story card per person: out/people/NN-<handle>.png at 1080x1920, every card a different image."""
    ppl = the_people()
    if not ppl:
        return False, "no people in build/taste.json"
    have = {f.stem.split("-", 1)[1]: f for f in CARDS.glob("[0-9][0-9]-*.png")} if CARDS.exists() else {}
    missing = [h for h in ppl if h not in have]
    wrong = [h for h in ppl if h in have and png_size(have[h]) != (1080, 1920)]
    same = len({sha(have[h]) for h in ppl if h in have}) < len([h for h in ppl if h in have])
    ok = not missing and not wrong and not same
    return ok, (f"{len(ppl) - len(missing)} of {len(ppl)} cards in out/people/ at 1080x1920"
                + (f"; missing {missing}" if missing else "") + (f"; wrong size {wrong}" if wrong else "")
                + ("; two cards are the same image" if same else ""))


def people_in(bt):
    data = bt.get("data") or {}
    out = set()
    if bt.get("kind") == "Leaderboard":
        shown = set(data.get("shown") or [])
        out |= {r["handle"] for r in data.get("rows", []) if r.get("rank") in shown}
    if bt.get("kind") == "Portrait" and data.get("handle"):
        out.add(data["handle"])
    for t in data.get("tiles", []):
        out |= set(t.get("people") or [])
    return out


def people_check():
    """Every person is on screen in at least one beat of the film."""
    ppl = the_people()
    beats = (_env.read_json("build/film.json") or {}).get("beats") or []
    seen = set().union(*(people_in(b) for b in beats)) if beats else set()
    gone = [h for h in ppl if h not in seen]
    return bool(ppl) and not gone, f"{len(ppl) - len(gone)} of {len(ppl)} people appear in a beat of {len(beats)}" + (
        f"; in no beat: {gone}" if gone else "")


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
    texts = words_in({"beats": film.get("beats"), "cards": film.get("cards")}, [])
    for f in ("out/caption.md", "out/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("build/taste.md").read_text().lower() if Path("build/taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
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
        same = FILM.exists() and last.get("film") == sha(FILM)
        done = sc and all(isinstance(x, int) for x in sc)
        ok = same and done and (min(sc) >= 4 or len(rounds) >= 2)
        check("critic", ok, f"round {len(rounds)}, lowest {min(sc) if done else '?'}" + ("" if same else "; the round is not for the current out/film.mp4"))
    cap = Path("out/caption.md").read_text() if Path("out/caption.md").exists() else ""
    lower = (_env.read_json("build/taste.json") or {}).get("register", {}).get("lowercase")
    body = re.sub(r"#\w+", "", cap)
    tags = re.findall(r"#\w+", cap)
    reg = cap and (not lower or body == body.lower()) and 1 <= len(tags) <= 10
    untagged = [h for h in the_people() if not re.search(r"@" + re.escape(h) + r"(?!\w|\.\w)", cap)]
    check("deliver", reg and not untagged and Path("out/review.html").exists() and Path("out/brief.md").exists(),
          f"caption {len(cap.split())} words, {len(tags)} hashtags" + (", lowercase like theirs" if lower else "") +
          (f", tags all {len(the_people())} people" if not untagged else f"; caption does not tag {untagged}") +
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
