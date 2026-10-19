#!/usr/bin/env python3
"""Movement 6: the measurable checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the film, the nine posts and the grid images only (run before the critics look)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes

The gate refuses:
  film      out/film.mp4 is not 1080x1920 H.264 high profile yuv420p at 30 fps, or runs outside 14.5-15.5 s
  audio     music was found but the film has no AAC track near 192 kbps, or its loudness is off -14 LUFS by more than 1 LU
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.5 s or more (ffmpeg freezedetect): nothing on screen may stand still that long
  safe      text that left its safe box or was cut off (SAFE_BREACH in build/render-report.json), a font that did
            not load, or a render job that failed
  posts     out/posts/01.png to 09.png are not nine 1080x1350 PNGs, or two of them are the same picture
  grid      out/grid-before.png (their real grid) or out/grid-after.png (the nine in place over it) is missing
  audit     out/audit.md is missing or names fewer than three findings about their grid
  plan      build/plan.json fails plan.py check (nine captions in order 1 to 9 on rising dates, in their register,
            none a copy of an old caption), or out/plan.md does not list the nine
  text      a placeholder string anywhere in the film's words, the posts' words, the audit, the plan, the brief or
            the review page
  research  build/taste.md (you are / you like / your style / your voice / avoid) or build/taste.json is missing
  boards    three grid directions, each with storyboard.md, storyboard.json, its style sheet sheet.png and six frames
  vote      build/vote.md and build/winner.json are missing
  clips     the film's storyboard lists clips and build/clips.json does not account for every one
  stills    a post that is a generated still has no picture behind it (build/stills.json, build/public/stills/)
  critic    the latest cut round in build/critic/ is not for this film, or scores below 4 with the one fix unspent
  deliver   out/review.html or out/brief.md is missing
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
import plan as plan_check  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|@handle\b|your_handle", re.I)
FILM = Path("out/film.mp4")
POSTS = Path("out/posts")
BEFORE = Path("out/grid-before.png")
AFTER = Path("out/grid-after.png")
LENGTH = (14.5, 15.5)


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
    check("posts", *posts_check())
    check("grid", BEFORE.exists() and AFTER.exists(), f"grid-before.png {'there' if BEFORE.exists() else 'missing'}, "
          f"grid-after.png {'at %dx%d' % png_size(AFTER) if AFTER.exists() else 'missing'}")
    return res


def posts_check():
    """The nine posts: 1080x1350 each, and nine different pictures (each post's whole frame, compared with every other)."""
    files = [POSTS / f"{n:02d}.png" for n in range(1, 10)]
    have = [f for f in files if f.exists()]
    if len(have) < 9:
        return False, f"{len(have)} of nine posts in out/posts/ (missing {[f.name for f in files if not f.exists()]})"
    sizes = {png_size(f) for f in have}
    _env.need("PIL")
    from PIL import Image
    cells = [list(Image.open(f).convert("L").resize((16, 20), Image.BILINEAR).tobytes()) for f in have]
    least = min(sum(abs(p - q) for p, q in zip(cells[i], cells[j])) / 320 for i in range(9) for j in range(i + 1, 9))
    return sizes == {(1080, 1350)} and least > 6, (f"nine posts at {', '.join('%dx%d' % z for z in sorted(sizes))}, "
                                                   f"least difference between two posts {least:.1f}")


def words_in(obj, acc):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("kicker", "headline", "line", "text", "meta", "label", "signoff", "name", "caption", "bio") and isinstance(v, str):
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
    texts = words_in({"beats": film.get("beats"), "posts": film.get("posts"), "profile": film.get("profile")}, [])
    for f in ("out/audit.md", "out/plan.md", "out/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    audit = Path("out/audit.md").read_text() if Path("out/audit.md").exists() else ""
    part = audit.split("## What your grid is doing", 1)[-1].split("\n## ", 1)[0] if audit else ""
    found = len(re.findall(r"^\d+\.\s+\S", part, re.M))
    check("audit", found >= 3, f"out/audit.md {'names %d findings' % found if audit else 'is missing'}")
    plan = _env.read_json("build/plan.json") or {}
    bad = plan_check.problems(plan) if plan else ["build/plan.json is missing"]
    md = Path("out/plan.md").read_text() if Path("out/plan.md").exists() else ""
    rows = [int(m) for m in re.findall(r"^\| (\d) \|", md, re.M)]
    check("plan", not bad and rows == list(range(1, 10)), f"{len(plan.get('slots') or [])} slots, out/plan.md lists {rows}"
          + (f"; {bad[0]}" + (f" (and {len(bad) - 1} more)" if len(bad) > 1 else "") if bad else ""))
    tm = Path("build/taste.md").read_text().lower() if Path("build/taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "avoid") if h not in tm]
    check("research", tm and not heads and Path("build/taste.json").exists(),
          "taste.md and taste.json" + (f"; taste.md is missing: {heads}" if heads else ""))
    boards = sorted(Path("build/storyboards").glob("*/storyboard.json"))
    full = [b.parent for b in boards if (b.parent / "storyboard.md").exists() and (b.parent / "sheet.png").exists()
            and len(list((b.parent / "frames").glob("0[1-6]-*.png"))) == 6]
    check("boards", len(boards) == 3 and len(full) == 3,
          f"{len(boards)} grid directions, {len(full)} with storyboard.md, sheet.png and six frames")
    win = _env.read_json("build/winner.json") or {}
    check("vote", Path("build/vote.md").exists() and win.get("board"), f"winner {win.get('board')} ({win.get('name')})")
    want = {c["id"] for c in film.get("clips", [])}
    got = set(((_env.read_json("build/clips.json") or {}).get("clips") or {}).keys())
    check("clips", want <= got, f"{len(want)} clips listed, {len(want & got)} accounted for" + (f"; missing {sorted(want - got)}" if want - got else ""))
    still_ids = [p.get("still_id") for p in film.get("posts", []) if p.get("still")]
    have = (_env.read_json("build/stills.json") or {}).get("stills", {})
    ok_stills = [i for i in still_ids if i in have and Path("build/public/stills", f"{i}.jpg").exists()]
    check("stills", len(ok_stills) == len(still_ids), f"{len(still_ids)} generated stills in the nine, {len(ok_stills)} with a picture"
          + (" (" + ", ".join(f"{i} {have[i].get('status')}" for i in ok_stills) + ")" if ok_stills else ""))
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
    check("deliver", Path("out/review.html").exists() and Path("out/brief.md").exists(),
          ("review.html" if Path("out/review.html").exists() else "review.html missing") + ", " +
          ("brief.md" if Path("out/brief.md").exists() else "brief.md missing"))
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
