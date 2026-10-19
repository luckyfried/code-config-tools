#!/usr/bin/env python3
"""Movement 6: the measurable checks and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py check     # the film and the four still formats only (run before the critics watch the cut)
    python3 S/scripts/qa.py gate      # everything below; exit 0 only when every check passes

The gate refuses:
  film      out/film.mp4 is not 1080x1920 H.264 high profile yuv420p at 30 fps, or runs outside 15-30 s
  audio     music was found but the film has no AAC track near 192 kbps, or its loudness is off -14 LUFS by more than 1 LU
  black     a black stretch of 0.4 s or more (ffmpeg blackdetect)
  frozen    a frozen stretch of 1.5 s or more (ffmpeg freezedetect): nothing on screen may stand still that long
  safe      text that left its safe box or was cut off (SAFE_BREACH in build/render-report.json), a font that did
            not load, or a render job that failed
  text      a placeholder string anywhere in the film's words, the captions, the brief or the review page
  stories   out/story-1.png, story-2.png and story-3.png are not all 1080x1920, or two of them are the same picture
            (tease, tease harder and reveal must each show more than the one before)
  countdown out/countdown.png is not 1080x1920
  feed      out/feed.png is not 1080x1350
  date      the countdown card's beat does not carry the date the person gave (build/library.json launch.date) and
            its label, or the film has no date beat carrying it
  product   a product beat (film or card) shows a picture that is not from the product's own assets, when it has any
  captions  out/captions.md lacks a section for the film, each story, the countdown or the feed post, or a section
            does not name the product
  research  build/taste.md (you are / you like / your style / your voice / the launch / avoid) or build/taste.json is missing
  boards    three storyboards, each with storyboard.md, storyboard.json and six style-sheet frames
  vote      build/vote.md and build/winner.json are missing
  clips     the film's storyboard lists clips and build/clips.json does not account for every one
  critic    the latest cut round in build/critic/ is not for this film, or scores below 4 with the one fix unspent
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
import grade  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|@handle\b|your_handle", re.I)
FILM = Path("out/film.mp4")
STORIES = [Path(f"out/story-{i}.png") for i in (1, 2, 3)]
COUNTDOWN = Path("out/countdown.png")
FEED = Path("out/feed.png")
CAPTIONS = Path("out/captions.md")
SECTIONS = ("film", "story 1", "story 2", "story 3", "countdown", "feed post")
LENGTH = (15, 30)


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
    check("stories", *stories_check())
    for name, f, want in (("countdown", COUNTDOWN, (1080, 1920)), ("feed", FEED, (1080, 1350))):
        sz = png_size(f) if f.exists() else None
        check(name, sz == want, f"{f} {'at %dx%d' % sz if sz else 'is missing'}")
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


def date_check(film, launch):
    want = launch.get("date")
    if not want:
        return True, "no date was given; the cards say soon"
    label = str(launch.get("date_label") or "").lower()
    cd = film.get("countdown") or {}
    data, text = cd.get("data") or {}, " ".join(str(v) for v in (cd.get("text") or {}).values()).lower()
    beat = [b for b in film.get("beats", []) if b["kind"] == "DateCard" and (b.get("data") or {}).get("date") == want]
    ok = data.get("date") == want and label in text and beat
    return ok, (f"countdown card carries {data.get('date')} ({'label in its words' if label in text else 'label missing'}), "
                f"want {want}; {len(beat)} film date beats carry it")


def product_check(film):
    picks = _env.read_json("build/picks.json") or {}
    own = {grade.graded_name(e["photo"]) for e in picks.get("product") or [] if e.get("own")}
    own |= {grade.graded_name(e["poster"]) for e in picks.get("footage") or []}
    if not own:
        return True, "the product has no assets of its own; product beats use their feed"
    beats = [*film.get("beats", []), *(film.get("stories") or []), film.get("countdown") or {}, film.get("feed") or {}]
    prod = [b for b in beats if (b.get("data") or {}).get("product")]
    bad = [b["id"] for b in prod if not set(b.get("photos") or []) <= own]
    return not bad and prod, f"{len(prod)} product beats, {len(prod) - len(bad)} on the product's own assets" + (f"; not: {bad}" if bad else "")


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


def captions_check(product):
    if not CAPTIONS.exists():
        return False, "out/captions.md is missing"
    sec = sections(CAPTIONS.read_text())
    miss = [k for k in SECTIONS if k not in sec]
    unnamed = [k for k in SECTIONS if k in sec and product.lower() not in sec[k].lower()]
    return not miss and not unnamed and product, (f"{len(sec)} sections" + (f"; missing {miss}" if miss else "") +
                                                 (f"; not naming {product}: {unnamed}" if unnamed else f"; every one names {product}"))


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
    texts = words_in({"beats": film.get("beats"), "stories": film.get("stories"), "countdown": film.get("countdown"),
                      "feed": film.get("feed")}, [])
    for f in ("out/captions.md", "out/brief.md", "out/review.html"):
        if Path(f).exists():
            texts.append(Path(f).read_text())
    hits = sorted({m.group(0) for t in texts for m in PLACEHOLDER.finditer(t)})
    check("text", film and not hits, f"{len(texts)} texts scanned" + (f"; placeholders: {hits}" if hits else ""))
    tm = Path("build/taste.md").read_text().lower() if Path("build/taste.md").exists() else ""
    heads = [h for h in ("you are", "you like", "your style", "your voice", "the launch", "avoid") if h not in tm]
    launch = (_env.read_json("build/library.json") or {}).get("launch") or {}
    product = launch.get("product") or film.get("product") or ""
    check("date", *date_check(film, launch))
    check("product", *product_check(film))
    check("captions", *captions_check(product))
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
    sec = sections(CAPTIONS.read_text()) if CAPTIONS.exists() else {}
    lower = (_env.read_json("build/taste.json") or {}).get("register", {}).get("lowercase")
    name = re.compile(re.escape(product), re.I) if product else None
    bodies = [re.sub(r"#\w+", "", name.sub("", v) if name else v) for v in sec.values()]
    tags = [len(re.findall(r"#\w+", sec.get(k, ""))) for k in ("film", "feed post")]
    reg = sec and (not lower or all(b == b.lower() for b in bodies)) and all(1 <= n <= 10 for n in tags)
    check("deliver", reg and Path("out/review.html").exists() and Path("out/brief.md").exists(),
          f"captions {sum(len(v.split()) for v in sec.values())} words, hashtags film {tags[0]} feed {tags[1]}" +
          (", lowercase like theirs" if lower else "") +
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
