#!/usr/bin/env python3
"""Steps 7 and 8: measurable checks, the critic's scores, and the gate that refuses delivery.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/qa.py story     # lints build/story.json: every chapter has its words, no placeholder text,
                                      # lengths that fit, and every number is one of the real numbers
    python3 S/scripts/qa.py check     # probes the video, pulls one frame per chapter to build/qa/frames/NN.png,
                                      # writes build/qa/sheet.jpg (all chapters + the carousel) for the critic
    python3 S/scripts/qa.py score --scores '{"numbers":5,"two_seconds":4,"photos":5,"palette":4,"type":4,"ending":4}' \
        --worst "what is weakest, in one sentence" [--fixed "what was changed"]
                                      # records one critic round in build/critic.json, tied to the current files
    python3 S/scripts/qa.py gate      # every check below; exit 0 only when all pass

The gate: the MP4 is 1080x1920 H.264 yuv420p at 24 fps, 45-60 s, no audio track unless --music was used, and it
is the file motion.py built from the current layers; every chapter is 4-8 s and carries one caption; the carousel
is 10 PNGs at 1080x1350 that render.py checked (safe area, fit, fonts) and that are unchanged since; the counts in
build/stats.json match build/data.json; the story lint passes; out/caption.md is one paragraph plus 3-10
hashtags; out/review.html and out/brief.md exist; the critic's latest round scores every criterion 4 or better
on exactly these files.
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

CRITERIA = {
    "numbers": "the numbers are theirs and correct",
    "two_seconds": "every card reads in two seconds",
    "photos": "their photos carry the video",
    "palette": "the palette is theirs",
    "type": "type and spacing are consistent across cards",
    "ending": "the ending makes a person want to post it",
}
LIMITS = {"kicker": 30, "headline": 34, "line": 64, "quiet": 34}
PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|\[[^\]]*\]|XXX|<[^>]+>|@handle\b|your_handle|PLACEHOLDER", re.I)
BUILD, OUT = Path("build"), Path("out")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def video_info(p):
    r = subprocess.run([_env.ffmpeg(), "-hide_banner", "-i", str(p)], capture_output=True, text=True)
    txt = r.stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", txt)
    vline = next((ln for ln in txt.splitlines() if "Video:" in ln), "")
    size = re.search(r"Video: (\w+).*?, (\d{2,5})x(\d{2,5})", vline)
    pix = re.search(r"\b(yuv\w+|rgb\w+|nv12|gray)\b", vline)
    fps = re.search(r"([\d.]+) fps", vline)
    secs = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0
    return {"seconds": round(secs, 2), "codec": size.group(1) if size else "?",
            "w": int(size.group(2)) if size else 0, "h": int(size.group(3)) if size else 0,
            "pix_fmt": pix.group(1) if pix else "?", "fps": float(fps.group(1)) if fps else 0,
            "audio": "Audio:" in txt}


def png_size(p):
    import struct
    with open(p, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)


def ints_in(obj, acc):
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        acc.add(int(obj))
        if isinstance(obj, float) and obj < 1:
            acc.add(round(obj * 100))
    elif isinstance(obj, str):
        acc.update(int(m.replace(",", "")) for m in re.findall(r"\d[\d,]*", obj) if m.replace(",", "").isdigit())
    elif isinstance(obj, dict):
        for v in obj.values():
            ints_in(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            ints_in(v, acc)
    return acc


def story_issues():
    story = _env.read_json(BUILD / "story.json")
    stats = _env.read_json(BUILD / "stats.json")
    if not story or not stats:
        return ["build/story.json or build/stats.json is missing"], []
    issues, notes = [], []
    allowed = ints_in(stats, set()) | ints_in((_env.read_json(BUILD / "palette.json") or {}).get("year"), set())
    allowed |= {stats["year"], stats["year"] + 1, 1, 2, 3, 5}
    accounts = {stats.get("handle", "")} | {p["account"] for p in stats.get("people") or []} | \
               {p["account"] for p in stats.get("loved") or []}
    cuts = _env.read_json(BUILD / "cuts.json") or {}
    need = cuts.get("chapters") or ["opener", "numbers", "top", "months", "palette", "closer"]
    for key in need + ["cover", "share"]:
        sec = story.get(key)
        if not isinstance(sec, dict):
            issues.append(f"story.json has no '{key}' section")
            continue
        for f in ("kicker", "headline", "line"):
            if key in need and f == "line" and not str(sec.get(f, "")).strip():
                issues.append(f"{key}.line is empty: every chapter carries one caption")
            if key in need and f == "headline" and key not in ("top",) and not str(sec.get(f, "")).strip():
                issues.append(f"{key}.headline is empty")
    texts = []
    for key, sec in story.items():
        if isinstance(sec, dict):
            for f, v in sec.items():
                if isinstance(v, str):
                    texts.append((f"{key}.{f}", v))
                    if f in LIMITS and len(v) > LIMITS[f]:
                        issues.append(f"{key}.{f} is {len(v)} characters; keep it to {LIMITS[f]} so it reads in two seconds")
    texts.append(("caption", str(story.get("caption", ""))))
    for where, v in texts:
        if PLACEHOLDER.search(v):
            issues.append(f"{where} has placeholder text: '{v[:50]}'")
        for m in re.findall(r"(?<![#\w])\d[\d,]*(?:\.\d+)?", v):
            n = m.replace(",", "")
            if "." in n or int(n) not in allowed:
                issues.append(f"{where} says {m}, which is not one of the real numbers in build/stats.json")
        for acct in re.findall(r"@([A-Za-z0-9._]+)", v):
            if acct.rstrip(".") not in accounts:
                issues.append(f"{where} names @{acct}, who is not in their data")
    tags = story.get("hashtags") or []
    if not 3 <= len(tags) <= 10 or any(not re.fullmatch(r"#[\w]+", t) for t in tags):
        issues.append(f"hashtags: give 3-10, each like #word (now {tags})")
    if "\n\n" in str(story.get("caption", "")).strip() or not str(story.get("caption", "")).strip():
        issues.append("caption must be one paragraph")
    if story.get("drafted"):
        notes.append("story.json is still the draft from the numbers; rewrite the lines in their voice and remove \"drafted\"")
    return issues, notes


def cmd_story(a):
    issues, notes = story_issues()
    for n in notes:
        print(f"NOTE {n}")
    for i in issues:
        print(f"FAIL {i}")
    print("story: PASS" if not issues else f"story: {len(issues)} problem(s)")
    return 1 if issues else 0


def carousel_files(plan):
    return [OUT / f"{plan['handle']}-{plan['year']}-carousel-{n:02d}.png" for n in range(1, (plan.get("carousel") or 10) + 1)]


def digest():
    tl = _env.read_json(BUILD / "timeline.json") or {}
    plan = _env.read_json(BUILD / "cuts.json") or {}
    parts = []
    if tl.get("mp4") and Path(tl["mp4"]).exists():
        parts.append(sha(tl["mp4"]))
    parts += [sha(p) for p in carousel_files(plan) if p.exists()] if plan else []
    if (BUILD / "story.json").exists():
        parts.append(sha(BUILD / "story.json"))
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def cmd_check(a):
    tl = _env.read_json(BUILD / "timeline.json")
    plan = _env.read_json(BUILD / "cuts.json")
    if not tl or not plan:
        sys.exit("build/timeline.json is missing; run motion.py first")
    from PIL import Image
    info = video_info(tl["mp4"])
    print(f"video: {info['w']}x{info['h']} {info['codec']} {info['pix_fmt']} {info['fps']:g} fps {info['seconds']} s "
          f"audio={'yes' if info['audio'] else 'no'}")
    fd = BUILD / "qa" / "frames"
    fd.mkdir(parents=True, exist_ok=True)
    for old in fd.glob("*.png"):
        old.unlink()
    frames = []
    for ch in tl["chapters"]:
        t = ch["start"] + min(3.0, (ch["end"] - ch["start"]) * 0.6)
        p = fd / f"{ch['chapter']:02d}.png"
        subprocess.run([_env.ffmpeg(), "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", tl["mp4"], "-frames:v", "1",
                        str(p)], check=True)
        frames.append(p)
        print(f"  chapter {ch['chapter']} {ch['name']:8s} {ch['start']:5.1f}-{ch['end']:5.1f}s  frame {p}")
    cards = [p for p in carousel_files(plan) if p.exists()]
    tw, th = 270, 480
    cols = max(len(frames), 5)
    cw = cols * tw // 5
    sheet = Image.new("RGB", (cols * tw, th + 2 * int(cw * 1350 / 1080)), (240, 238, 234))
    for i, p in enumerate(frames):
        sheet.paste(Image.open(p).convert("RGB").resize((tw, th)), (i * tw, 0))
    for i, p in enumerate(cards[:10]):
        im = Image.open(p).convert("RGB").resize((cw, int(cw * 1350 / 1080)))
        sheet.paste(im, ((i % 5) * cw, th + (i // 5) * im.height))
    sheet.save(BUILD / "qa" / "sheet.jpg", quality=88)
    print(f"sheet: {BUILD / 'qa' / 'sheet.jpg'} (video frames on top, carousel below); open it and judge by eye")
    issues, _ = gate_checks(final=False)
    for i in issues:
        print(f"FAIL {i}")
    print("check: PASS" if not issues else f"check: {len(issues)} problem(s)")
    return 1 if issues else 0


def cmd_score(a):
    try:
        scores = json.loads(a.scores)
    except Exception:
        sys.exit("--scores must be JSON like '{\"numbers\":5,...}'")
    missing = [k for k in CRITERIA if k not in scores]
    bad = [k for k, v in scores.items() if k not in CRITERIA or not isinstance(v, int) or not 1 <= v <= 5]
    if missing or bad:
        sys.exit(f"scores need every criterion as an integer 1-5: {list(CRITERIA)} (missing {missing}, invalid {bad})")
    rec = _env.read_json(BUILD / "critic.json", {"rounds": []})
    rnd = {"round": len(rec["rounds"]) + 1, "scores": scores, "worst": a.worst or "", "fixed": a.fixed or "",
           "digest": digest()}
    rec["rounds"].append(rnd)
    _env.write_json(BUILD / "critic.json", rec)
    low = [k for k, v in scores.items() if v < 4]
    print(f"critic round {rnd['round']}: " + ", ".join(f"{k} {v}" for k, v in scores.items()))
    if low:
        print(f"below 4: {low}. Fix the worst one ({a.worst or low[0]}) once, rebuild, and score again."
              if rnd["round"] < 2 else f"below 4 after the fix round: {low}. The gate will refuse delivery.")
    else:
        print("every criterion is 4 or better")
    return 0


def gate_checks(final=True):
    issues = []
    plan = _env.read_json(BUILD / "cuts.json")
    tl = _env.read_json(BUILD / "timeline.json")
    report = _env.read_json(BUILD / "render-report.json", {}) or {}
    if not plan or not tl:
        return ["build/cuts.json or build/timeline.json is missing (run cards.py build, render.py, motion.py)"], {}
    mp4 = Path(tl["mp4"])
    want = OUT / f"{plan['handle']}-{plan['year']}-year-in-review.mp4"
    if not mp4.exists():
        issues.append(f"{mp4} is missing")
        info = {}
    else:
        if mp4.resolve() != want.resolve():
            issues.append(f"video is at {mp4}; it belongs at {want}")
        info = video_info(mp4)
        if (info["w"], info["h"]) != (1080, 1920):
            issues.append(f"video is {info['w']}x{info['h']}, needs 1080x1920")
        if info["codec"] != "h264" or info["pix_fmt"] != "yuv420p":
            issues.append(f"video is {info['codec']} {info['pix_fmt']}, needs h264 yuv420p")
        if abs(info["fps"] - 24) > 0.01:
            issues.append(f"video is {info['fps']} fps, needs 24")
        if not 45 <= info["seconds"] <= 60:
            issues.append(f"video is {info['seconds']} s, needs 45-60")
        if info["audio"] and not tl.get("music"):
            issues.append("video has an audio track but no --music was given")
        if sha(mp4) != tl.get("mp4_sha"):
            issues.append("the video changed after motion.py wrote it; rerun motion.py")
    chapters, cues = tl.get("chapters") or [], tl.get("cues") or []
    for ch in chapters:
        d = ch["end"] - ch["start"]
        if not 3.99 <= d <= 8.01:
            issues.append(f"chapter {ch['chapter']} ({ch['name']}) is {d:.1f} s; chapters are 4-8 s")
        if sum(1 for c in cues if c.get("chapter") == ch["chapter"] and c["text"].strip()) != 1:
            issues.append(f"chapter {ch['chapter']} ({ch['name']}) needs exactly one caption")
    if len(chapters) < 6:
        issues.append(f"only {len(chapters)} chapters")
    for path, s in (tl.get("layers") or {}).items():
        r = report.get(path)
        if not Path(path).exists() or not r or r.get("sha") != s or sha(path) != s:
            issues.append(f"{path} changed or was not checked by render.py; rerun render.py and motion.py")
            break
    cards = carousel_files(plan)
    if len(cards) != 10:
        issues.append(f"carousel has {len(cards)} cards, needs 10")
    for p in cards:
        r = report.get(str(p))
        if not p.exists():
            issues.append(f"{p} is missing")
        elif png_size(p) != (1080, 1350):
            issues.append(f"{p} is {png_size(p)}, needs 1080x1350")
        elif not r or r.get("sha") != sha(p) or not r.get("checked"):
            issues.append(f"{p} changed after render.py checked it; rerun render.py")
    data, stats = _env.read_json(BUILD / "data.json") or {}, _env.read_json(BUILD / "stats.json") or {}
    c = stats.get("counts") or {}
    for key, src in (("posts", "posts"), ("reels", "reels"), ("stories", "stories"), ("likes_given", "likes"),
                     ("comments_written", "comments")):
        if key in c and c[key] != len(data.get(src) or []):
            issues.append(f"stats says {c[key]} {key} but the data has {len(data.get(src) or [])}; rerun stats.py")
    s_issues, _ = story_issues()
    issues += [f"story: {i}" for i in s_issues]
    if final:
        cap = OUT / "caption.md"
        if not cap.exists():
            issues.append("out/caption.md is missing")
        else:
            txt = cap.read_text().strip()
            paras = [p for p in re.split(r"\n\s*\n", txt) if p.strip() and not p.strip().startswith("#")]
            tags = re.findall(r"(?<!\w)#\w+", txt)
            if len(paras) != 1:
                issues.append(f"out/caption.md has {len(paras)} paragraphs; it is one paragraph plus hashtags")
            if not 3 <= len(tags) <= 10:
                issues.append(f"out/caption.md has {len(tags)} hashtags; give 3-10")
            if PLACEHOLDER.search(txt):
                issues.append("out/caption.md has placeholder text")
        for f in ("review.html", "brief.md"):
            if not (OUT / f).exists():
                issues.append(f"out/{f} is missing")
        rec = _env.read_json(BUILD / "critic.json", {"rounds": []})
        if not rec["rounds"]:
            issues.append("the critic has not scored this video (qa.py score)")
        else:
            last = rec["rounds"][-1]
            low = {k: v for k, v in last["scores"].items() if v < 4}
            if low:
                issues.append(f"critic scored below 4: {low}")
            if last.get("digest") != digest():
                issues.append("the files changed after the critic's last score; look again and score again")
    return issues, info


def cmd_gate(a):
    issues, info = gate_checks(final=True)
    out = {"pass": not issues, "issues": issues, "video": info, "digest": digest()}
    _env.write_json(BUILD / "qa" / "gate.json", out)
    for i in issues:
        print(f"FAIL {i}")
    print("GATE: PASS" if not issues else f"GATE: FAIL ({len(issues)} problem(s))")
    return 0 if not issues else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("story", help="lint build/story.json")
    sub.add_parser("check", help="probe the video, pull one frame per chapter, write the contact sheet")
    s = sub.add_parser("score", help="record one critic round")
    s.add_argument("--scores", required=True)
    s.add_argument("--worst", default="")
    s.add_argument("--fixed", default="")
    sub.add_parser("gate", help="every check; exit 0 only when all pass")
    a = ap.parse_args()
    if a.cmd == "check":
        _env.need("PIL")
    sys.exit({"story": cmd_story, "check": cmd_check, "score": cmd_score, "gate": cmd_gate}[a.cmd](a))


if __name__ == "__main__":
    main()
