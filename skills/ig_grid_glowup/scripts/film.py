#!/usr/bin/env python3
"""Movement 4: the nine designed posts, the grid after, and the before->after film, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/posts/01..09.png (1080x1350) + out/grid-after.png + out/film.mp4
    python3 S/scripts/film.py render --only film|posts
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json drawn with Pillow

The engine is the Remotion project in S/motion (setup.py installs it). out/posts/NN.png is post NN of the plan
(post 01 goes up first). out/grid-after.png is their profile with the nine in place over the real grid.
render writes the silent picture to build/film.silent.mp4 (1080x1920, 30 fps, H.264 high, CRF 18), then lays the
mastered music under it (build/music/master.wav from music.py, AAC 192 kbps) into out/film.mp4. Every SAFE_BREACH
(text that left its safe box), FONT_ERROR and render error lands in build/render-report.json, which qa.py gate
reads. build/timeline.json carries each beat's start and length for qa.py and the frame extraction.
When setup.py reports engine "stills", render runs the stills route instead and build/engine.json says so.
"""
import argparse
import copy
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

FPS = 30
PUBLIC = Path("build/public")
POSTS = Path("out/posts")
AFTER = Path("out/grid-after.png")
SHEET_ROWS = 7


def clip_for(beat, clips):
    c = beat.get("clip")
    if not c:
        return None
    if isinstance(c, dict):
        return c
    got = clips.get(c) or {}
    return {"id": c, "file": got.get("file"), "frames": got.get("frames", 0),
            "image": got.get("image") or (beat.get("photos") or [None])[0], "status": got.get("status", "pending")}


def props_for(board):
    """The composition props: the board with every clip id resolved to its file and frame count, or its substitute."""
    b = copy.deepcopy(board)
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    for bt in b["beats"]:
        bt["clip"] = clip_for(bt, clips)
        if bt["clip"] and bt["clip"].get("image") is None and bt.get("photos"):
            bt["clip"]["image"] = bt["photos"][0]
    for k in ("timeline", "clips", "stills", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds"):
        b.pop(k, None)
    return {"board": b}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "gg-bundle")}
    if concurrency:
        spec["concurrency"] = concurrency
    jf = Path("build/render") / f"{Path(report).stem}.jobs.json"
    _env.write_json(jf, spec)
    node = t["node"]
    env = dict(os.environ, PATH=f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}")
    r = subprocess.run([node, str(Path(t["motion"]) / "render.mjs"), str(jf.resolve())], env=env)
    rep = _env.read_json(report) or {"failed": len(jobs), "findings": [{"text": f"render.mjs exited {r.returncode}"}]}
    return rep


def timeline(beats):
    out, start = [], 0
    for i, b in enumerate(beats):
        t = (b.get("transition") or {}).get("frames", 0) if i else 0
        start = start - t if i else 0
        out.append({"id": b["id"], "kind": b["kind"], "start": start, "frames": b["frames"], "transition": t,
                    "start_s": round(start / FPS, 3), "seconds": round(b["frames"] / FPS, 3),
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]]})
        start += b["frames"]
    return out


def post_jobs(props):
    jobs = []
    for p in props["board"]["posts"]:
        jobs.append({"type": "still", "composition": "Post", "frame": 0, "scale": 1, "props": {**props, "post": p},
                     "out": str((POSTS / f"{p['n']:02d}.png").resolve())})
    jobs.append({"type": "still", "composition": "Sheet", "frame": 0, "scale": 1, "props": {**props, "rows": SHEET_ROWS},
                 "out": str(AFTER.resolve())})
    return jobs


def write_nine(board):
    """Which file each of the nine is and what it was made from, for qa.py and the brief."""
    stills = (_env.read_json("build/stills.json") or {}).get("stills", {})
    rows = []
    for p in sorted(board["posts"], key=lambda p: p["n"]):
        rows.append({"n": p["n"], "file": str(POSTS / f"{p['n']:02d}.png"), "kind": p["kind"], "photo": p.get("photo"),
                     "source": p.get("source"), "still": bool(p.get("still")),
                     "still_status": (stills.get(p.get("still_id") or "") or {}).get("status") if p.get("still") else None,
                     "slot": 9 - p["n"]})
    _env.write_json("build/nine.json", {"size": [1080, 1350], "posts": rows, "grid_after": str(AFTER)})


def mux(silent, out, seconds):
    ff = _env.ffmpeg()
    master = Path("build/music/master.wav")
    if master.exists():
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-i", str(master), "-map", "0:v", "-map", "1:a",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{seconds:.3f}",
               "-movflags", "+faststart", str(out)]
    else:
        cmd = [ff, "-y", "-v", "error", "-i", str(silent), "-c:v", "copy", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return master.exists()


def cmd_render(a):
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    if _env.tools().get("engine") != "remotion":
        return cmd_stills(a)
    Path("out").mkdir(exist_ok=True)
    props = props_for(board)
    jobs = []
    silent = Path("build/film.silent.mp4").resolve()
    if a.only in (None, "posts"):
        shutil.rmtree(POSTS, ignore_errors=True)
        AFTER.unlink(missing_ok=True)
        write_nine(board)
        jobs += post_jobs(props)
    if a.only in (None, "film"):
        jobs.append({"type": "video", "composition": "Film", "props": props, "out": str(silent), "crf": 18, "preset": "medium"})
    t0 = time.time()
    rep = render_jobs(jobs, "build/render-report.json")
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "remotion", "node": _env.tools().get("node"),
                                          "seconds": round(time.time() - t0, 1), "jobs": len(jobs)})
    music = False
    if a.only in (None, "film") and silent.exists():
        music = mux(silent, Path("out/film.mp4"), secs)
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    film = f"; film {secs:.2f} s{' with music' if music else ' (no music track)'} -> out/film.mp4" if a.only in (None, "film") else ""
    posts = "; out/posts/01..09.png, out/grid-after.png" if a.only in (None, "posts") else ""
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {time.time() - t0:.1f} s{posts}{film}")
    return 1 if rep.get("failed") else 0


def cmd_frames(a):
    tl = _env.read_json("build/timeline.json")
    film = Path(a.film)
    if not tl or not film.exists():
        sys.exit("out/film.mp4 and build/timeline.json are needed: run film.py render first")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*.png"):
        f.unlink()
    for d in out.glob("*/"):
        shutil.rmtree(d, ignore_errors=True)
    ff = _env.ffmpeg()

    def grab(t, dst):
        subprocess.run([ff, "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", str(film), "-frames:v", "1", str(dst)], check=True)

    shots = 0
    beats = tl["beats"]
    for i, b in enumerate(beats, 1):
        # the settled moment of the beat: the last shot of a many-shot beat (the nine all landed), else its longest
        # shot, never inside the transition in or the next beat's transition out
        edges = b.get("shots") or [0, b["frames"]]
        end = b["frames"] - (beats[i]["transition"] if i < len(beats) else 0)
        spans = [(edges[k], min(edges[k + 1], end)) for k in range(len(edges) - 1)]
        spans = [(lo, hi) if hi > lo else (lo, edges[k + 1]) for k, (lo, hi) in enumerate(spans)]
        lo, hi = spans[-1] if len(spans) >= 4 else max(spans, key=lambda e: e[1] - e[0])
        lo = max(lo, b["transition"])
        grab((b["start"] + lo + (hi - lo) * 0.7) / FPS, out / f"{i:02d}-{b['id']}.png")
        if len(spans) >= 3:
            sub = out / f"{i:02d}-{b['id']}"
            sub.mkdir(exist_ok=True)
            for k, (a_, z) in enumerate(spans, 1):
                grab((b["start"] + max(a_, b["transition"]) + (z - max(a_, b["transition"])) * 0.7) / FPS, sub / f"{k:02d}.png")
                shots += 1
    print(f"{len(tl['beats'])} frames -> {out}/" + (f", and {shots} shot frames in its beat folders" if shots else ""))
    return 0


# ------------------------------------------------------------------ the stills route (no node)
def cmd_stills(a):
    """The posts, the grid after and the film drawn with Pillow: each beat one composed still under an eased push."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    c = s["colors"]
    font = lambda kind, size: ImageFont.truetype(str(_env.SKILL / s[kind]["file"]), size)
    CW, CH, GAP, TOP = 358, 448, 3, 120

    def photo(p, w, h):
        return ImageOps.fit(Image.open(PUBLIC / p).convert("RGB"), (w, h), Image.LANCZOS)

    def wrap(text, f, width):
        lines, cur = [], ""
        for w in str(text).split():
            nxt = (cur + " " + w).strip()
            if f.getlength(nxt) <= width or not cur:
                cur = nxt
            else:
                lines.append(cur)
                cur = w
        return lines + [cur] if cur else lines

    def post_image(p):
        if p["kind"] == "photo" and p.get("photo"):
            im = photo(p["photo"], 1080, 1350)
            if p.get("tint"):
                im = Image.blend(im, Image.new("RGB", im.size, p["tint"]), 0.16)
            return im
        fill = p.get("bg") or p.get("tint") or c["bg"]
        im = Image.new("RGB", (1080, 1350), fill)
        d = ImageDraw.Draw(im)
        r, g, b = (int(fill.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        ink = c["ink"] if (0.299 * r + 0.587 * g + 0.114 * b) < 140 else c["bg"]
        size = 150
        f = font("display", size)
        lines = wrap((p.get("text") or {}).get("headline") or "", f, 888)
        while len(lines) > 4 and size > 60:
            size -= 10
            f = font("display", size)
            lines = wrap((p.get("text") or {}).get("headline") or "", f, 888)
        y = 1350 - 230 - len(lines) * int(size * 1.05)
        for ln in lines:
            d.text((96, y), ln, font=f, fill=ink)
            y += int(size * 1.05)
        if (p.get("text") or {}).get("kicker"):
            d.text((96, 96), str(p["text"]["kicker"]).upper(), font=font("text", 34), fill=ink)
        d.text((96, 1350 - 96 - 30), f"@{board['handle']}", font=font("text", 30), fill=ink)
        return im

    def profile(with_posts, rows=None):
        cells = board["grid"]
        shift = 9 if with_posts else 0
        total = rows * 3 if rows else shift + len(cells)
        H = TOP + -(-total // 3) * (CH + GAP)
        im = Image.new("RGB", (1080, H), "#ffffff")
        d = ImageDraw.Draw(im)
        d.text((40, 40), board["handle"], font=font("text", 46), fill="#0a0a0a")
        for cell in cells:
            slot = cell["pos"] + shift
            if slot >= total or not cell.get("photo"):
                continue
            im.paste(photo(cell["photo"], CW, CH), ((slot % 3) * (CW + GAP), TOP + (slot // 3) * (CH + GAP)))
        if with_posts:
            for p in board["posts"]:
                slot = 9 - p["n"]
                im.paste(post_image(p).resize((CW, CH), Image.LANCZOS), ((slot % 3) * (CW + GAP), TOP + (slot // 3) * (CH + GAP)))
        return im

    POSTS.mkdir(parents=True, exist_ok=True)
    write_nine(board)
    for p in board["posts"]:
        post_image(p).save(POSTS / f"{p['n']:02d}.png")
    profile(True, SHEET_ROWS).save(AFTER)
    W, H = board["format"]["width"], board["format"]["height"]

    def frame_for(bt):
        bg = Image.new("RGB", (W, H), c["bg"])
        mode = (bt.get("data") or {}).get("mode")
        if bt["kind"] == "Feed" and mode in ("before", "after", "end"):
            pr = profile(mode != "before", 5 if mode == "end" else None)
            k = 0.86 if mode != "end" else 0.7
            pr = pr.resize((int(1080 * k), int(pr.height * k)), Image.LANCZOS).crop((0, 0, int(1080 * k), H - 600))
            bg.paste(pr, ((W - pr.width) // 2, 600))
        elif bt["kind"] == "Feed" and mode == "posts":
            p = next((x for x in board["posts"] if x["n"] == (bt["data"].get("show") or [9])[0]), board["posts"][0])
            im = post_image(p).resize((900, 1125), Image.LANCZOS)
            bg.paste(im, (90, 560))
        else:
            ph = (bt.get("photos") or [None])[0]
            if ph:
                bg.paste(photo(ph, W, H))
        d = ImageDraw.Draw(bg)
        t = bt.get("text") or {}
        y = 170
        for key, kind, size in (("kicker", "text", 40), ("headline", "display", 92), ("line", "text", 44)):
            if t.get(key):
                f = font(kind, size)
                for ln in wrap(t[key], f, W - 2 * 90):
                    d.text((90, y), ln, font=f, fill=c["ink"] if mode != "posts" else c["ink"])
                    y += int(size * 1.1)
                y += 14
        return bg

    ff = _env.ffmpeg()
    work = Path("build/stills-route")
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, bt in enumerate(board["beats"]):
        f = work / f"{i + 1:02d}-{bt['id']}.png"
        frame_for(bt).save(f)
        secs = bt["frames"] / FPS
        clip = work / f"{i + 1:02d}.mp4"
        z = "1+0.05*(1-pow(1-on/{n},3))".format(n=bt["frames"])
        subprocess.run([ff, "-y", "-v", "error", "-loop", "1", "-i", str(f), "-t", f"{secs:.3f}", "-vf",
                        f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={bt['frames']}:s={W}x{H}:fps={FPS},format=yuv420p",
                        "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-r", str(FPS), str(clip)], check=True)
        parts.append((clip, secs, (bt.get("transition") or {}).get("frames", 0) / FPS))
    inputs, flt, last = [], [], "0:v"
    for clip, _, _ in parts:
        inputs += ["-i", str(clip)]
    offset = parts[0][1]
    for k in range(1, len(parts)):
        tr = max(0.1, parts[k][2])
        offset -= tr
        flt.append(f"[{last}][{k}:v]xfade=transition=fade:duration={tr:.3f}:offset={offset:.3f}[v{k}]")
        last = f"v{k}"
        offset += parts[k][1]
    silent = Path("build/film.silent.mp4")
    subprocess.run([ff, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(flt), "-map", f"[{last}]",
                    "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)], check=True)
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    Path("out").mkdir(exist_ok=True)
    music = mux(silent, Path("out/film.mp4"), secs)
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: film {secs:.2f} s{' with music' if music else ''} -> out/film.mp4; out/posts/01..09.png, out/grid-after.png")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "frames", "stills"])
    ap.add_argument("--only", choices=["film", "posts"])
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="build/frames")
    a = ap.parse_args()
    return {"render": cmd_render, "frames": cmd_frames, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
