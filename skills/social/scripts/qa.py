#!/usr/bin/env python3
"""QA for the social pipeline: see every image, record a verdict, refuse to finish until all PASS.

USAGE (run from the workspace root):
  python3 S/scripts/qa.py check                 # auto-checks every out/*.png|jpg|mp4, writes safe-zone overlays,
                                                # contact sheet (build/qa/sheet.png, feed size), MP4 filmstrips,
                                                # and out/qa.json (verdicts survive only while the file is unchanged)
  python3 S/scripts/qa.py verdict out/p01-x-1080x1350.png PASS --seen "what the image actually shows" [--by critic|self] [--note ".."]
  python3 S/scripts/qa.py verdict out/p01-x-1080x1350.png FIX  --seen ".." --note "the exact fix"
  python3 S/scripts/qa.py round                 # critic: call once at the start of each critic round
  python3 S/scripts/qa.py gate                  # exit 0 only if the pipeline is complete and every current file has PASS
  python3 S/scripts/qa.py copy [out/copy.md]    # lint captions: AI tells, hashtags, weekdays, repeats, structure
  python3 S/scripts/qa.py palette brand.json    # contrast ratios + purple check
  python3 S/scripts/qa.py status                # which pipeline steps are done, what's missing

Options: --out DIR (default out), --qa DIR (default build/qa).
Rules: a verdict is tied to the file's sha256; re-rendering a file voids its verdict. --seen must describe
what is visibly in the image (words + picture), not intent. Self verdicts count only after 2 critic rounds.
"""
import argparse
import colorsys
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
VID_EXT = {".mp4", ".mov"}
MAX_ROUNDS = 2


# ------------------------------------------------------------------ helpers
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def media(out):
    return sorted(p for p in Path(out).glob("*") if p.suffix.lower() in IMG_EXT | VID_EXT and p.is_file())


def load_qa(out):
    f = Path(out) / "qa.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"rounds": 0, "files": {}}


def save_qa(out, q):
    (Path(out) / "qa.json").write_text(json.dumps(q, indent=2))


def video_info(p):
    ff = _env.ffmpeg()
    r = subprocess.run([ff, "-hide_banner", "-i", str(p)], capture_output=True, text=True)
    txt = r.stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    vline = next((l for l in txt.splitlines() if "Video:" in l), "")
    size = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", vline)
    pix = re.search(r"\b(yuv\w+|rgb\w+|nv12|gray)\b", vline)
    fps = re.search(r"([\d.]+) fps", vline)
    secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0
    return {"seconds": round(secs, 2), "codec": size.group(1) if size else "?",
            "w": int(size.group(2)) if size else 0, "h": int(size.group(3)) if size else 0,
            "pix_fmt": pix.group(1) if pix else "?", "fps": float(fps.group(1)) if fps else 0,
            "audio": "Audio:" in txt, "decodes": r.returncode in (0, 1) and bool(dur)}


def video_checks(p, info=None):
    """Platform requirements for Reels/TikTok/Stories video. Returns (issues, info)."""
    info = info or video_info(p)
    issues = []
    if not info["decodes"] or info["codec"] == "?":
        return [("BAD", "file does not decode as video")], info
    if (info["w"], info["h"]) != (1080, 1920):
        issues.append(("BAD", f"video is {info['w']}x{info['h']}; Reels/TikTok/Stories need 1080x1920"))
    if not 5.9 <= info["seconds"] <= 15.1:
        issues.append(("BAD", f"video is {info['seconds']}s; keep 6-15s"))
    if info["codec"] != "h264":
        issues.append(("BAD", f"codec {info['codec']}; use H.264 (plays everywhere)"))
    if info["pix_fmt"] != "yuv420p":
        issues.append(("BAD", f"pixel format {info['pix_fmt']}; phones need yuv420p"))
    if info["fps"] and not 23 <= info["fps"] <= 60:
        issues.append(("WARN", f"{info['fps']} fps; use 30"))
    if not info["audio"]:
        issues.append(("WARN", "no audio track; some apps reject videos without one (motion.py adds a silent track)"))
    mb = p.stat().st_size / 1e6
    if mb > 100:
        issues.append(("WARN", f"{mb:.0f} MB; re-encode smaller (Stories reject large files on slow uploads)"))
    elif mb < 0.02:
        issues.append(("WARN", f"{mb * 1000:.0f} KB: suspiciously small; open the filmstrip (blank or frozen?)"))
    return issues, info


def zones_for(name, w, h):
    """Rectangles (label, x, y, w, h) that text/logos must stay out of."""
    m = round(min(w, h) * 0.05)
    z = [("edge", 0, 0, w, m), ("edge", 0, h - m, w, m), ("edge", 0, 0, m, h), ("edge", w - m, 0, m, h)]
    fmt = _env.match_format(name, w, h)
    sz = (fmt or {}).get("safe_zone") or None
    if sz:
        t, b, l, r = (int(sz.get(k, 0) or 0) for k in ("top", "bottom", "left", "right"))
        lab = (fmt.get("label") or fmt["key"])
        if t:
            z.append((f"{lab}: top UI {t}px", 0, 0, w, t))
        if b:
            z.append((f"{lab}: bottom UI {b}px", 0, h - b, w, b))
        if l > m:
            z.append(("left UI", 0, 0, l, h))
        if r > m:
            z.append((f"right rail {r}px", w - r, 0, r, h))
    if (w, h) == (1500, 500):
        z.append(("profile photo", 0, 250, 420, 250))
    return z, fmt


def auto_checks(p, im):
    """Pixel-level checks that need no judgment. Returns list of (level, msg)."""
    from PIL import ImageStat
    issues = []
    w, h = im.size
    fmt = _env.match_format(p.name, w, h)
    if not fmt:
        issues.append(("BAD", f"{w}x{h} is not a known platform size (formats.json)"))
    m = re.search(r"(\d{3,4})x(\d{3,4})", p.name)
    if m and (int(m.group(1)), int(m.group(2))) != (w, h):
        issues.append(("BAD", f"file name says {m.group(1)}x{m.group(2)} but image is {w}x{h}"))
    small = im.convert("L").resize((max(1, w // 8), max(1, h // 8)))
    sd = ImageStat.Stat(small).stddev[0]
    if sd < 3:
        issues.append(("BAD", "image is almost a single flat colour (failed render?)"))
    # Empty bands: consecutive rows with almost no variation.
    sw, sh = small.size
    px = small.load()
    run = best = 0
    for y in range(sh):
        row = [px[x, y] for x in range(sw)]
        if max(row) - min(row) < 6:
            run += 1
            best = max(best, run)
        else:
            run = 0
    if sh and best / sh > 0.30:
        issues.append(("WARN", f"empty band covers {round(100 * best / sh)}% of the height: intended (sticker space)? otherwise fill or tighten"))
    size_mb = p.stat().st_size / 1e6
    if size_mb > 8:
        issues.append(("WARN", f"{size_mb:.1f} MB: Instagram rejects images over 8 MB; export as high-quality JPEG"))
    return issues, fmt


def vertical_video_zones(w=1080, h=1920):
    """One set of no-text bands that clears Story, Reels and TikTok UI at once (what motion.py captions obey)."""
    zs = [f.get("safe_zone") or {} for f in _env.formats() if (f["w"], f["h"]) == (w, h)]
    t = max([250] + [int(z.get("top") or 0) for z in zs])
    b = max([420] + [int(z.get("bottom") or 0) for z in zs])
    l = max([64] + [int(z.get("left") or 0) for z in zs])
    r = max([200] + [int(z.get("right") or 0) for z in zs])
    return [(f"top UI {t}px", 0, 0, w, t), (f"Reels/TikTok caption + buttons {b}px", 0, h - b, w, b),
            ("left", 0, 0, l, h), (f"right rail {r}px", w - r, 0, r, h)]


def draw_zones(im, name, zones=None):
    """The image with its platform's no-text zones shaded (safe-zone overlay)."""
    from PIL import Image, ImageDraw
    w, h = im.size
    ov = im.convert("RGBA")
    layer = Image.new("RGBA", ov.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if zones is None:
        zones, _ = zones_for(name, w, h)
    lab_font = _env.pil_font(max(22, w // 36), "bold")
    for label, x, y, zw, zh in zones:
        if label == "edge":  # margin: thin dashed guide only
            for i in range(0, max(zw, zh), 24):
                if zw > zh:
                    d.line([x + i, y + zh - 1 if y == 0 else y, x + i + 12, y + zh - 1 if y == 0 else y], fill=(255, 64, 0, 200), width=2)
                else:
                    d.line([x + zw - 1 if x == 0 else x, y + i, x + zw - 1 if x == 0 else x, y + i + 12], fill=(255, 64, 0, 200), width=2)
            continue
        d.rectangle([x, y, x + zw - 1, y + zh - 1], fill=(255, 64, 0, 70), outline=(255, 64, 0, 230), width=3)
        if zw >= 300 and zh >= 40:  # label only the wide bands, centred, so labels never collide
            tw = d.textlength(label, font=lab_font)
            d.text((x + (zw - tw) / 2, y + zh / 2 - lab_font.size / 2), label, fill=(255, 255, 255, 255),
                   font=lab_font, stroke_width=4, stroke_fill=(150, 30, 0, 255))
    return Image.alpha_composite(ov, layer).convert("RGB")


def video_overlay(p, info, dest):
    """Safe-zone overlay for a 9:16 video: frames at 25%, 55% and the end, side by side, zones shaded,
    so burned-in captions can be checked against the Story/Reels/TikTok UI bands."""
    from PIL import Image
    if (info.get("w"), info.get("h")) != (1080, 1920) or not info.get("seconds"):
        return None
    frames = []
    for frac in (0.25, 0.55, 0.97):
        r = subprocess.run([_env.ffmpeg(), "-loglevel", "error", "-ss", f"{info['seconds'] * frac:.2f}", "-i", str(p),
                            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
        if len(r.stdout) >= 1080 * 1920 * 3:
            fr = Image.frombytes("RGB", (1080, 1920), r.stdout[:1080 * 1920 * 3])
            # captions must clear the strictest 9:16 UI (Story, Reels and TikTok at once)
            ov = draw_zones(fr, p.name, vertical_video_zones())
            frames.append(ov.resize((540, 960)))
    if not frames:
        return None
    sheet = Image.new("RGB", (len(frames) * 552 - 12, 960), (255, 255, 255))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * 552, 0))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    return dest


# ------------------------------------------------------------------ check
def cmd_check(a):
    _env.need("PIL")
    from PIL import Image, ImageDraw
    out, qa_dir = Path(a.out), Path(a.qa)
    (qa_dir / "overlays").mkdir(parents=True, exist_ok=True)
    for old in list((qa_dir / "overlays").glob("*.png")) + list(qa_dir.glob("*-strip.png")):
        old.unlink()  # overlays/strips of files that were renamed or deleted must not linger
    q = load_qa(out)
    files = media(out)
    if not files:
        sys.exit(f"No images or videos in {out}/. Render first.")
    cells, n_bad = [], 0
    seen_names = set()
    for p in files:
        seen_names.add(p.name)
        digest = sha(p)
        entry = q["files"].get(p.name, {})
        if entry.get("sha") != digest:
            entry = {"verdicts": entry.get("verdicts", [])}  # keep history, sha change voids them
        entry["sha"] = digest
        if p.suffix.lower() in VID_EXT:
            issues, info = video_checks(p)
            strip = qa_dir / f"{p.stem}-strip.png"
            n = 6
            fps = n / max(info["seconds"], 1)
            subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-i", str(p), "-vf",
                            f"fps={fps:.4f},scale=240:-2,tile={n}x1:padding=8:color=white", "-frames:v", "1", str(strip)],
                           check=False)
            ov_path = video_overlay(p, info, qa_dir / "overlays" / f"{p.stem}-video.png")
            entry.update(kind="video", w=info["w"], h=info["h"], seconds=info["seconds"], overlay=str(ov_path or strip),
                         strip=str(strip))
            if strip.exists():
                cells.append((p.name, strip, "video"))
        else:
            im = Image.open(p)
            im.load()
            issues, fmt = auto_checks(p, im)
            w, h = im.size
            ov = draw_zones(im, p.name)
            ov_path = qa_dir / "overlays" / f"{p.stem}.png"
            ov.save(ov_path)
            entry.update(kind="image", w=w, h=h, format=(fmt or {}).get("key"), overlay=str(ov_path))
            cells.append((p.name, p, "image"))
        entry["auto"] = [{"level": l, "msg": m} for l, m in issues]
        n_bad += sum(1 for l, _ in issues if l == "BAD")
        q["files"][p.name] = entry
    for gone in [k for k in q["files"] if k not in seen_names]:
        del q["files"][gone]
    save_qa(out, q)
    cells.sort(key=lambda c: c[2] == "video")  # images pack 4 to a row; each video filmstrip takes a full row
    sheet = make_sheet(cells, qa_dir / "sheet.png", q)
    print(f"{'file':<48} {'size':<10} auto-checks")
    for p in files:
        e = q["files"][p.name]
        flags = "; ".join(f"{i['level']}: {i['msg']}" for i in e["auto"]) or "ok"
        print(f"{p.name:<48} {str(e.get('w'))+'x'+str(e.get('h')):<10} {flags}")
    print(f"\nContact sheet (phone feed size): {sheet}")
    print(f"Overlays: {qa_dir/'overlays'}/<name>.png (videos: <name>-video.png)   Filmstrips: {qa_dir}/<name>-strip.png")
    print("NEXT: open the sheet, then EVERY file (image + its overlay; filmstrip for videos), then record a verdict for each:")
    print("  python3 <S>/scripts/qa.py verdict out/<file> PASS|FIX --seen \"<what is visibly there>\" [--note \"<fix>\"]")
    return 1 if n_bad else 0


def make_sheet(cells, dest, q):
    from PIL import Image, ImageDraw
    cw, pad, label_h = 360, 18, 44
    cols = 4
    thumbs = []
    for name, path, kind in cells:
        im = Image.open(path).convert("RGB")
        tw = cw if kind == "image" else cw * cols + pad * (cols - 1)  # a video's filmstrip gets a full row
        th = round(im.height * tw / im.width)
        thumbs.append((name, im.resize((tw, th), Image.LANCZOS), kind))
    # simple row packing
    rows, row, roww = [], [], 0
    for t in thumbs:
        span = 1 if t[2] == "image" else cols
        if roww + span > cols:
            rows.append(row)
            row, roww = [], 0
        row.append(t)
        roww += span
    if row:
        rows.append(row)
    W = cols * (cw + pad) + pad
    H = pad + sum(max(t[1].height for t in r) + label_h + pad for r in rows)
    sheet = Image.new("RGB", (W, max(H, 100)), (236, 233, 228))
    d = ImageDraw.Draw(sheet)
    f = _env.pil_font(15, "text")
    y = pad
    for r in rows:
        x = pad
        for name, im, kind in r:
            sheet.paste(im, (x, y))
            e = q["files"].get(name, {})
            v = (e.get("verdicts") or [{}])[-1] if e.get("verdicts") and e["verdicts"][-1].get("sha") == e.get("sha") else {}
            tag = v.get("verdict", "no verdict")
            d.text((x, y + im.height + 6), f"{name}", fill=(20, 20, 20), font=f)
            d.text((x, y + im.height + 24), f"{e.get('w')}x{e.get('h')}  [{tag}]", fill=(90, 90, 90), font=f)
            x += im.width + pad
        y += max(t[1].height for t in r) + label_h + pad
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    return dest


# ------------------------------------------------------------------ verdicts
def cmd_verdict(a):
    out = Path(a.out)
    p = Path(a.file)
    if not p.exists():
        p = out / Path(a.file).name
    if not p.exists():
        sys.exit(f"No such file: {a.file}")
    v = a.verdict.upper()
    if v not in ("PASS", "FIX"):
        sys.exit("verdict must be PASS or FIX")
    seen = (a.seen or "").strip()
    if len(seen) < 15:
        sys.exit("--seen is required: describe what is VISIBLY in the file (the words and the picture), at least a full phrase.")
    if v == "FIX" and not (a.note or "").strip():
        sys.exit("A FIX needs --note with the specific change to make.")
    q = load_qa(out)
    if a.by == "critic" and q.get("rounds", 0) == 0:
        q["rounds"] = 1
        print("(no 'qa.py round' yet: started critic round 1)")
    e = q["files"].setdefault(p.name, {"verdicts": []})
    digest = sha(p)
    if e.get("sha") and e["sha"] != digest:
        e["auto"] = []  # stale; gate re-runs checks
    e["sha"] = digest
    e.setdefault("verdicts", []).append({"by": a.by, "verdict": v, "seen": seen, "note": a.note or "",
                                         "sha": digest, "round": q.get("rounds", 0),
                                         "at": dt.datetime.now().isoformat(timespec="seconds")})
    save_qa(out, q)
    print(f"{p.name}: {v} by {a.by} (round {q.get('rounds', 0)})")


def cmd_round(a):
    q = load_qa(a.out)
    q["rounds"] = q.get("rounds", 0) + 1
    save_qa(a.out, q)
    print(f"critic round {q['rounds']} started (max {MAX_ROUNDS} revision rounds; after that, fix and self-verify)")


def current_verdict(e, rounds):
    """The verdict that counts for the file's current bytes, or None."""
    cur = [v for v in e.get("verdicts", []) if v.get("sha") == e.get("sha")]
    critic = [v for v in cur if v["by"] == "critic"]
    selfv = [v for v in cur if v["by"] != "critic"]
    if critic and (not selfv or critic[-1]["at"] >= selfv[-1]["at"]):
        return critic[-1]
    if selfv and rounds >= MAX_ROUNDS:
        return selfv[-1]
    if critic:
        return critic[-1]
    return None


# ------------------------------------------------------------------ brief / status
STEP_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(\d)\b(.*)$", re.M)


def brief_state(out):
    f = Path(out) / "brief.md"
    if not f.exists():
        return None, {}
    t = f.read_text()
    steps = {int(m.group(2)): m.group(1).lower() == "x" for m in STEP_RE.finditer(t)}
    return t, steps


def section(text, title):
    m = re.search(rf"^##\s+{title}\b.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1).strip() if m else ""


def brief_problems(out):
    t, steps = brief_state(out)
    probs = []
    if t is None:
        return ["out/brief.md missing (step 0)"], steps
    if not steps:
        probs.append("out/brief.md has no pipeline checklist (copy it from SKILL.md)")
    concepts = section(t, "Concepts")
    n_ideas = len(re.findall(r"^###\s+C\d", t, re.M)) or len(re.findall(r"^\s*(?:\d+\.|[-*])\s+\S", concepts, re.M))
    if n_ideas < 3:
        probs.append(f"brief has {n_ideas} concepts; step 2 needs 3-5 (### C1 ... headings)")
    pick = section(t, "Pick")
    if len(pick.split()) < 20:
        probs.append("brief has no '## Pick' with a written rationale (20+ words)")
    if "|" not in section(t, "Plan"):
        probs.append("brief has no '## Plan' table (file | format | job / design idea | headline | image shows ...)")
    if not section(t, "Assumptions"):
        probs.append("brief has no '## Assumptions'")
    return probs, steps


def cmd_status(a):
    out = Path(a.out)
    probs, steps = brief_problems(out)
    names = ["scope", "brand", "concept", "copy", "visuals", "motion", "critic", "deliver"]
    for i, n in enumerate(names):
        print(f"[{'x' if steps.get(i) else ' '}] {i} {n}")
    print(f"brand.json: {'yes' if Path('brand.json').exists() else 'no'}   out/brand.json: {'yes' if (out/'brand.json').exists() else 'no'}")
    print(f"out/copy.md: {'yes' if (out/'copy.md').exists() else 'no'}   files in out/: {len(media(out))}")
    q = load_qa(out)
    pend = [p.name for p in media(out) if not (q["files"].get(p.name) and q["files"][p.name].get("sha") == sha(p)
                                                and current_verdict(q["files"][p.name], q.get("rounds", 0)))]
    print(f"critic rounds: {q.get('rounds', 0)}   files without a current verdict: {len(pend)}")
    for p in probs:
        print("  -", p)


# ------------------------------------------------------------------ copy lint
BANNED = [
    r"say goodbye to", r"reimagined", r"\bunlock(s|ed|ing)?\b", r"\belevate[sd]?\b", r"next level",
    r"here'?s the thing", r"game[- ]?changer", r"look no further", r"\bindulge\b", r"treat yourself",
    r"mouth-?watering", r"delectable", r"\bnestled\b", r"\bboasts\b", r"whether you'?re .{1,40} or ",
    r"let that sink in", r"read that again", r"\bagree\?", r"\bthoughts\?", r"tag a friend",
    r"don'?t miss out", r"get yours today", r"join thousands", r"stop scrolling",
    r"what nobody tells you", r"we'?re (so )?(excited|thrilled) to (announce|share)", r"i'?ll be honest",
    r"in today'?s fast[- ]paced", r"\bdelve\b", r"\btapestry\b", r"\bsymphony of\b", r"\bunleash",
    r"\bseamless(ly)?\b", r"\bembark\b",
]
TELLS = [
    (r"\b(it'?s|this is|that'?s|we'?re)\s+not\s+[^.!?\n]{1,50}[,;.]\s*(it'?s|this is|that'?s|we'?re)\b", "contrast reveal ('it's not X, it's Y')"),
    (r"\bnot because\b[^.]{1,60}\.\s*because\b", "contrast reveal ('not because X. because Y')"),
    (r"\bno\s+\w+(\s+\w+)?[,.]\s+no\s+\w+(\s+\w+)?[,.]\s+(and\s+)?no\s+\w+", "negation list ('no X, no Y, no Z')"),
    (r"(^|[.!]\s+)(the|our|your|my)\s+\w+(\s+\w+)?\?\s+\S", "self-answered question ('The result? ...')"),
    (r"\b(the best part|the secret|the catch|the twist|the kicker|the result|here'?s the deal)\s*:", "colon reveal"),
]
CAPS = {"instagram": 5, "tiktok": 5, "facebook": 2, "x": 2, "twitter": 2, "linkedin": 3, "pinterest": 2, "threads": 1}
FOLD = {"instagram": 125, "tiktok": 150, "linkedin": 210, "facebook": 140, "pinterest": 100}
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
DAYS = {d: i for i, d in enumerate(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])}
WD = r"(mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?"
MO = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"


def resolve_year(month, day, year=None):
    today = dt.date.today()
    if year:
        return dt.date(int(year), month, day)
    for y in (today.year, today.year + 1):
        try:
            d = dt.date(y, month, day)
        except ValueError:
            continue
        if d >= today - dt.timedelta(days=60):
            return d
    return dt.date(today.year, month, day)


def weekday_errors(text, where):
    errs = []
    pats = [
        (rf"\b{WD},?\s+{MO}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?", ("wd", "mo", "d", "y")),
        (rf"\b{MO}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\s*[,(]?\s*{WD}\b", ("mo", "d", "y", "wd")),
        (rf"\b{WD},?\s+(\d{{1,2}})/(\d{{1,2}})(?:/(\d{{2,4}}))?", ("wd", "mon", "d", "y")),
        (rf"\b(\d{{4}})-(\d{{2}})-(\d{{2}})\s*[|,(]?\s*{WD}\b", ("y", "mon", "d", "wd")),
        (rf"\b{WD},?\s+(\d{{1,2}})\s+{MO}(?:\s+(\d{{4}}))?", ("wd", "d", "mo", "y")),
    ]
    for pat, order in pats:
        for m in re.finditer(pat, text, re.I):
            g = dict(zip(order, m.groups()))
            try:
                month = MONTHS[g["mo"][:3].lower()] if "mo" in g else int(g["mon"])
                y = g.get("y")
                if y and len(y) == 2:
                    y = "20" + y
                d = resolve_year(month, int(g["d"]), y)
            except Exception:
                continue
            said = DAYS[g["wd"][:3].lower()]
            if d.weekday() != said:
                errs.append(f"{where}: '{m.group(0).strip()}' but {d.isoformat()} is a {d.strftime('%A')}")
    return errs


def parse_copy(text):
    posts = []
    for m in re.finditer(r"^##\s+Post\s+(\d+)\s*[:.\-]?\s*(.*?)$(.*?)(?=^##\s|\Z)", text, re.M | re.S):
        body = m.group(3)
        files = []
        fm = re.search(r"^Files?:\s*(.+)$", body, re.M)
        if fm:
            files = [x.strip().strip("`") for x in re.split(r"[,;]", fm.group(1)) if x.strip()]
        alts = {}
        for am in re.finditer(r"^Alt:\s*([^|]+?)\s*\|\s*(.+)$", body, re.M):
            alts[am.group(1).strip().strip("`")] = am.group(2).strip()
        caps = {}
        for cm in re.finditer(r"^###\s+(.+?)\s*$(.*?)(?=^###\s|\Z)", body, re.M | re.S):
            caps[cm.group(1).strip()] = cm.group(2).strip()
        extra = {}
        for em in re.finditer(r"^(Story sticker|Sticker|Note|Notes|Credit|Link):\s*(.+)$", body, re.M):
            extra[em.group(1)] = em.group(2).strip()
        posts.append({"n": int(m.group(1)), "title": m.group(2).strip(), "files": files, "alts": alts,
                      "captions": caps, "extra": extra})
    return posts


def platform_key(name):
    n = name.lower()
    for k in ("instagram", "tiktok", "facebook", "linkedin", "pinterest", "threads", "twitter"):
        if k in n:
            return k
    if re.search(r"\bx\b", n):
        return "x"
    return None


def lint_copy(path, out, strict_files=False):
    errs, warns = [], []
    p = Path(path)
    if not p.exists():
        return [f"{path} missing (step 3)"], []
    text = p.read_text()
    if not re.search(r"^##\s+Posting plan", text, re.M | re.I):
        errs.append("no '## Posting plan' table")
    posts = parse_copy(text)
    if not posts:
        errs.append("no '## Post N: title' sections")
    errs += weekday_errors(text, "copy.md")
    # weekdays in image data too: the picture must not carry a wrong date
    for jf in sorted(Path("build/data").glob("*.json")) if Path("build/data").exists() else []:
        try:
            errs += weekday_errors(jf.read_text(), str(jf))
        except Exception:
            pass
    plan = section(text, "Posting plan")
    for row in plan.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        iso = next((c for c in cells if re.fullmatch(r"\d{4}-\d{2}-\d{2}", c)), None)
        day = next((c for c in cells if re.fullmatch(WD, c, re.I)), None)
        if iso and day:
            d = dt.date.fromisoformat(iso)
            if d.weekday() != DAYS[day[:3].lower()]:
                errs.append(f"posting plan: {iso} is a {d.strftime('%A')}, table says {day}")
    all_caps = []
    openings = {}
    for post in posts:
        tag = f"Post {post['n']}"
        if not post["files"]:
            errs.append(f"{tag}: no 'Files:' line")
        for f in post["files"]:
            if Path(f).suffix.lower() in IMG_EXT and f not in post["alts"]:
                warns.append(f"{tag}: no 'Alt: {f} | ...' line")
            if strict_files and not (Path(out) / f).exists():
                errs.append(f"{tag}: Files lists {f} but out/{f} does not exist")
        if not post["captions"]:
            errs.append(f"{tag}: no '### Platform' caption sections")
        for plat, cap in post["captions"].items():
            where = f"{tag} / {plat}"
            all_caps.append((post["n"], plat, cap))
            if "—" in cap or re.search(r"\s–\s", cap):
                errs.append(f"{where}: em/en dash; use a full stop, comma or line break")
            low = cap.lower()
            for b in BANNED:
                mm = re.search(b, low)
                if mm:
                    errs.append(f"{where}: stock/AI phrase '{mm.group(0)}'")
            for pat, label in TELLS:
                mm = re.search(pat, cap, re.I | re.M)
                if mm:
                    errs.append(f"{where}: {label}: '{mm.group(0)[:60]}'")
            lines = [l for l in cap.splitlines() if l.strip()]
            emoji_lead = sum(1 for l in lines if re.match(r"^\s*[☀-➿\U0001F300-\U0001FAFF]", l))
            if emoji_lead >= 3:
                errs.append(f"{where}: emoji used as bullets ({emoji_lead} lines start with an emoji)")
            body_lines = [l for l in lines if not l.strip().startswith("#")]
            if len(body_lines) >= 6 and sum(1 for l in body_lines if len(l.split()) <= 8) / len(body_lines) > 0.8:
                warns.append(f"{where}: reads as broetry (one short line after another); write paragraphs")
            if cap.count("!") > 3:
                warns.append(f"{where}: {cap.count('!')} exclamation marks")
            k = platform_key(plat)
            tags = re.findall(r"(?<![\w&])#\w+", cap)
            if k and k in CAPS and len(tags) > CAPS[k]:
                errs.append(f"{where}: {len(tags)} hashtags, cap is {CAPS[k]}")
            first = body_lines[0].strip() if body_lines else ""
            if k in FOLD and len(first) > FOLD[k]:
                warns.append(f"{where}: first line is {len(first)} chars; the hook must land before ~{FOLD[k]}")
            if re.match(r"^(happy \w+day|exciting news|we'?re (so )?excited|attention|hey (guys|everyone))", first, re.I):
                warns.append(f"{where}: weak opener '{first[:30]}'; lead with the point")
            op = " ".join(re.findall(r"[a-z0-9$']+", first.lower())[:3])
            if op:
                openings.setdefault(op, set()).add(post["n"])
    for op, ns in openings.items():
        if len(ns) >= 2:
            warns.append(f"captions in posts {sorted(ns)} all open with '{op}...'; vary the openings")
    # repeated terms block: the same sentence in 3+ captions
    sent_count = {}
    for n, plat, cap in all_caps:
        for s in set(re.split(r"(?<=[.!?])\s+|\n", cap)):
            s2 = re.sub(r"\s+", " ", s.strip().lower())
            if len(s2.split()) >= 5 and not s2.startswith("#"):
                sent_count.setdefault(s2, set()).add((n, plat))
    for s, where in sent_count.items():
        if len(where) >= 3:
            warns.append(f"the sentence '{s[:70]}' appears in {len(where)} captions; state terms once, then refer back")
    errs += credit_problems(Path(out), all_caps)
    tz = re.findall(r"\b\d{1,2}(:\d\d)?\s*(am|pm)\s*(pt|pst|pdt|et|est|edt|ct|mt)\b", text, re.I)
    if len(tz) > 3:
        warns.append(f"a deadline with time zone appears {len(tz)} times; full terms belong in 2-3 places only")
    return errs, warns


def credit_problems(out, all_caps):
    """CC BY / BY-SA images listed in out/credits.md must be credited in a caption (licence condition)."""
    f = Path(out) / "credits.md"
    if not f.exists():
        return []
    text = " ".join(c for _, _, c in all_caps).lower()
    errs = []
    for line in f.read_text().splitlines():
        if "credit required" not in line:
            continue
        m = re.match(r'^-\s*`([^`]+)`:\s*".*?"\s+by\s+(.+?),\s+(CC BY[^,(]*)', line)
        if not m:
            continue
        name, creator, lic = m.group(1), m.group(2).strip(), m.group(3).strip()
        if creator.lower() in ("unknown", "") :
            continue
        if creator.lower() not in text:
            errs.append(f"credits.md: {name} is {lic} by {creator}; put 'Photo: {creator} / {lic}' in the caption of the "
                        "post that uses it (or, if it isn't used, delete its line from out/credits.md)")
    return errs


def cmd_copy(a):
    errs, warns = lint_copy(a.file or Path(a.out) / "copy.md", a.out)
    for e in errs:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    print(f"\n{len(errs)} errors, {len(warns)} warnings" + ("" if errs else ". Copy lint passes."))
    return 1 if errs else 0


# ------------------------------------------------------------------ palette
def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lum(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(hex_rgb(a)), lum(hex_rgb(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def is_purple(hx):
    r, g, b = hex_rgb(hx)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    deg = h * 360
    return s > 0.18 and 0.12 < l < 0.92 and 255 <= deg <= 335


def palette_problems(brand):
    pal = brand.get("palette") or {}
    probs, notes = [], []
    if not isinstance(pal, dict) or not pal:
        return ["brand.json has no palette object"], notes
    if len(pal) > 4:
        probs.append(f"{len(pal)} palette colours; max 4")
    for k, v in pal.items():
        try:
            if is_purple(v):
                probs.append(f"{k} {v} is purple/violet/magenta: not allowed")
        except Exception:
            probs.append(f"{k} {v!r} is not a hex colour")
    bg, fg = pal.get("bg"), pal.get("fg") or pal.get("ink") or pal.get("text")
    try:
        if bg and fg:
            c = contrast(bg, fg)
            notes.append(f"fg on bg {c:.1f}:1")
            if c < 7:
                probs.append(f"fg on bg is {c:.1f}:1; need 7:1 for small text on phones")
        for k in ("accent", "accent2"):
            if bg and pal.get(k):
                c = contrast(bg, pal[k])
                notes.append(f"{k} on bg {c:.1f}:1")
                if c < 3:
                    notes.append(f"  {k} under 3:1 on bg: use it for shapes/blocks, not for text on bg")
    except Exception as e:
        probs.append(f"contrast check failed: {e}")
    return probs, notes


def cmd_palette(a):
    brand = json.loads(Path(a.brand).read_text())
    probs, notes = palette_problems(brand)
    for n in notes:
        print(n)
    for p in probs:
        print("ERROR", p)
    print("palette ok" if not probs else f"{len(probs)} palette problems")
    return 1 if probs else 0


# ------------------------------------------------------------------ gate
BUTTON_STRONG = re.compile(r"^\s*(order|shop|buy|book|sign up|subscribe|register|claim|download|click|tap|learn more|get started|get yours|reserve)\b", re.I)
BUTTON_SOFT = re.compile(r"^\s*(see|get|join|visit|try|start|discover|explore|view|grab|call)\b.*\b(now|more|here|today|menu|online)\s*[.!]?\s*$", re.I)


def looks_like_button(t):
    return len(t.split()) <= 4 and bool(BUTTON_STRONG.match(t) or BUTTON_SOFT.match(t))


def plan_problems(plan_path="build/plan.json"):
    """Every render job must be an agent-written `html` job (never a library `template` fill): the HTML exists,
    has no unfilled {{tokens}}, its images exist, and any visible CTA text is a fact line, not a button."""
    p = Path(plan_path)
    if not p.exists():
        return [], []
    errs, warns = [], []
    try:
        jobs = json.loads(p.read_text())
    except Exception as e:
        return [f"{plan_path} unreadable: {e}"], []
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs") or jobs.get("renders") or []
    htmls = []
    for j in jobs:
        outp = Path(j.get("out", "?")).name
        if j.get("template") and not j.get("html"):
            errs.append(f"{outp}: rendered from the library template '{j['template']}'. The library is reference only: "
                        "design an original HTML file and render it with 'html' (pipeline/4-visuals.md)")
            continue
        hp = Path(str(j.get("html", "")))
        if not hp.is_file():
            errs.append(f"{outp}: html file '{hp}' not found")
            continue
        htmls.append(hp)
        src = hp.read_text()
        data = j.get("data") if isinstance(j.get("data"), dict) else {}
        for tok in sorted(set(re.findall(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}", src))):
            if tok not in ("fonts_css", "brand_css") and tok not in data:
                errs.append(f"{outp}: {hp.name} has an unfilled {{{{{tok}}}}} token")
        if re.search(r"https?://(?!www\.w3\.org)", src):
            errs.append(f"{outp}: {hp.name} references a remote URL; only bundled fonts and local files render")
        for u in re.findall(r"""(?:src=|url\()\s*["']?(/[^"')\s>]+)""", src):
            if not Path(u).exists() and not u.startswith("//"):
                errs.append(f"{outp}: {hp.name} uses an image that does not exist: {u}")
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", src, flags=re.S | re.I)
        for t in re.findall(r">([^<>]{2,60})<", text):
            if looks_like_button(t.strip()):
                errs.append(f"{outp}: text '{t.strip()}' reads like a button; use a fact line ('Tuesdays · all day', 'link in bio')")
        if re.search(r"font-family:[^;}]*\b(Arial|Helvetica|Times|Georgia|Verdana|system-ui)\b", src, re.I):
            warns.append(f"{outp}: {hp.name} names a system font; use the bundled families (references/html-authoring.md)")
    if len(htmls) >= 2:
        if not Path("build/design-system.css").is_file():
            errs.append("a set of 2+ posts needs build/design-system.css (the shared type, colour, grid and motif; step 4 section 0)")
        else:
            linked = sum(1 for h in htmls if "design-system.css" in h.read_text())
            if linked < len(htmls):
                warns.append(f"only {linked}/{len(htmls)} post HTML files link design-system.css")
    return errs, warns


def study_problems():
    """Step 4 requires the reference examples to have been pulled and the notes written."""
    errs = []
    log = Path("build/library-log.json")
    try:
        n = len(json.loads(log.read_text())) if log.is_file() else 0
    except Exception:
        n = 0
    if n == 0:
        errs.append("no reference examples were pulled: run scripts/library.py find <job> --family <style_family> for each post (step 4b)")
    notes = Path("build/design-notes.md")
    if not notes.is_file() or len(notes.read_text().split()) < 40:
        errs.append("build/design-notes.md missing or empty: per post, the job, the examples studied and the principle borrowed (step 4a-b)")
    return errs


def cmd_gate(a):
    _env.need("PIL")
    from PIL import Image
    out = Path(a.out)
    fails = []
    probs, steps = brief_problems(out)
    fails += probs
    for i, n in enumerate(["scope", "brand", "concept", "copy", "visuals", "motion", "critic"]):
        if i == 6:
            continue  # the gate is part of step 6
        if not steps.get(i):
            fails.append(f"brief checklist: step {i} ({n}) not ticked")
    if not (out / "brand.json").exists():
        fails.append("out/brand.json missing (step 1)")
    else:
        try:
            pp, _ = palette_problems(json.loads((out / "brand.json").read_text()))
            fails += [f"brand.json: {p}" for p in pp if "purple" in p or "max 4" in p]
        except Exception as e:
            fails.append(f"out/brand.json unreadable: {e}")
    errs, _ = lint_copy(out / "copy.md", out, strict_files=True)
    fails += [f"copy: {e}" for e in errs]
    perrs, _ = plan_problems()
    fails += [f"plan: {e}" for e in perrs]
    if Path("build/plan.json").exists() or media(out):
        fails += [f"study: {e}" for e in study_problems()]
    q = load_qa(out)
    rounds = q.get("rounds", 0)
    if rounds == 0:
        fails.append("the critic never ran (no 'qa.py round'); step 6 spawns it")
    files = media(out)
    if not files:
        fails.append("no images in out/")
    seen_by = {}
    listed = set()
    if (out / "copy.md").exists():
        for post in parse_copy((out / "copy.md").read_text()):
            listed |= set(post["files"])
    for p in files:
        e = q["files"].get(p.name)
        if not e:
            fails.append(f"{p.name}: never checked (run qa.py check)")
            continue
        cur = sha(p)
        if e.get("sha") != cur:
            e = dict(e, sha=cur)
        if p.suffix.lower() in IMG_EXT:
            im = Image.open(p)
            issues, _ = auto_checks(p, im)
        else:
            issues, _ = video_checks(p)
        for lvl, msg in issues:
            if lvl == "BAD":
                fails.append(f"{p.name}: {msg}")
        v = current_verdict(e, rounds)
        if not v:
            stale = any(x.get("sha") != cur for x in e.get("verdicts", []))
            early_self = any(x.get("sha") == cur and x["by"] != "critic" for x in e.get("verdicts", []))
            fails.append(f"{p.name}: no verdict for the current file"
                         + (" (self verdicts count only after 2 critic rounds: run qa.py round and spawn the critic)"
                            if early_self else " (changed since its last verdict: open it again)" if stale else ""))
        elif v["verdict"] != "PASS":
            fails.append(f"{p.name}: {v['by']} says FIX: {v['note']}")
        else:
            seen_by.setdefault(re.sub(r"\W+", " ", v.get("seen", "").lower()).strip(), []).append(p.name)
        if listed and p.name not in listed:
            fails.append(f"{p.name}: in out/ but not in any post's Files: line (add it or delete it)")
    for desc, names in seen_by.items():
        if len(names) > 1:
            fails.append(f"{', '.join(names)}: identical --seen text ('{desc[:50]}'); open each file and describe what "
                         "is visibly in that one")
    if fails:
        print("GATE FAILED")
        for f in fails:
            print("  -", f)
        return 1
    print(f"GATE PASSED: {len(files)} files, all PASS for their current version; {rounds} critic round(s).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out", default="out")
    common.add_argument("--qa", default="build/qa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", parents=[common])
    v = sub.add_parser("verdict", parents=[common])
    v.add_argument("file")
    v.add_argument("verdict")
    v.add_argument("--seen", required=True)
    v.add_argument("--note", default="")
    v.add_argument("--by", default="self", choices=["critic", "self"])
    sub.add_parser("round", parents=[common])
    sub.add_parser("gate", parents=[common])
    c = sub.add_parser("copy", parents=[common])
    c.add_argument("file", nargs="?")
    pl = sub.add_parser("palette", parents=[common])
    pl.add_argument("brand", nargs="?", default="brand.json")
    sub.add_parser("status", parents=[common])
    a = ap.parse_args()
    fn = {"check": cmd_check, "verdict": cmd_verdict, "round": cmd_round, "gate": cmd_gate,
          "copy": cmd_copy, "palette": cmd_palette, "status": cmd_status}[a.cmd]
    sys.exit(fn(a) or 0)


if __name__ == "__main__":
    main()
