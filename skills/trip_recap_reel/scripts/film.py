#!/usr/bin/env python3
"""Movement 4: the trip film at 9:16 and at 16:9, and the five story cards, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4 (1080x1920) + out/film-16x9.mp4 (1920x1080)
                                                # + out/story-1.png .. out/story-5.png (1080x1920)
    python3 S/scripts/film.py render --only film|landscape|cards
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as stills under motion

The engine is the Remotion project in S/motion (setup.py installs it). Both films come from the one storyboard:
the same beats, frames and cuts, laid out for the frame they are in (the map and the words side by side at 16:9).
render writes the silent pictures to build/film.silent.mp4 and build/film-16x9.silent.mp4 (30 fps, H.264 high,
CRF 18), then lays the mastered music under each (build/music/master.wav from music.py, AAC 192 kbps) into
out/film.mp4 and out/film-16x9.mp4. The story cards are the board's five stories (the opener, three places, the
closer) as 1080x1920 stills. Every SAFE_BREACH (text that left its safe box), FONT_ERROR and render error lands in
build/render-report.json, which qa.py gate reads. build/timeline.json carries each beat's start and length for
qa.py and the frame extraction. When setup.py reports engine "stills", render runs the stills route instead and
build/engine.json says so.
"""
import argparse
import copy
import json
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


def clip_for(beat, clips):
    c = beat.get("clip")
    if not c:
        return None
    if isinstance(c, dict):
        return c
    got = clips.get(c) or {}
    return {"id": c, "file": got.get("file"), "frames": got.get("frames", 0),
            "image": got.get("image") or (beat.get("photos") or [None])[0], "status": got.get("status", "pending")}


def props_for(board, fmt="reel"):
    """The composition props: the board with every beat's clip reference resolved to a file or its substitute."""
    b = copy.deepcopy(board)
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    for bt in b["beats"]:
        bt["clip"] = clip_for(bt, clips)
        if bt["clip"] and bt["clip"].get("image") is None and bt.get("photos"):
            bt["clip"]["image"] = bt["photos"][0]
    for st in b.get("stories") or []:
        st["clip"] = None
    for k in ("timeline", "clips", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds"):
        b.pop(k, None)
    return {"board": b, "format": fmt}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "tr-bundle")}
    if concurrency:
        spec["concurrency"] = concurrency
    jf = Path("build/render") / f"{Path(report).stem}.jobs.json"
    _env.write_json(jf, spec)
    node = t["node"]
    env = dict(os.environ, PATH=f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}")
    # run from the motion folder so Remotion finds the browser setup.py put in motion/node_modules/.remotion
    r = subprocess.run([node, str(Path(t["motion"]) / "render.mjs"), str(jf.resolve())], env=env, cwd=t["motion"])
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


FILMS = (("film", "reel", "build/film.silent.mp4", "out/film.mp4"),
         ("landscape", "landscape", "build/film-16x9.silent.mp4", "out/film-16x9.mp4"))


def story_out(i):
    return Path(f"out/story-{i}.png")


def story_jobs(props):
    return [{"type": "still", "composition": "Card", "frame": 0, "scale": 1,
             "props": {"board": props["board"], "beat": st, "format": "story"}, "out": str(story_out(i).resolve())}
            for i, st in enumerate(props["board"].get("stories") or [], 1)]


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
    jobs, made = [], []
    for key, fmt, silent, out in FILMS:
        if a.only in (None, key):
            Path(out).unlink(missing_ok=True)
            jobs.append({"type": "video", "composition": "Film", "props": props_for(board, fmt), "out": str(Path(silent).resolve()),
                         "crf": 18, "preset": "medium"})
            made.append((silent, out))
    if a.only in (None, "cards"):
        for f in Path("out").glob("story-*.png"):
            f.unlink()
        jobs += story_jobs(props_for(board, "story"))
    t0 = time.time()
    rep = render_jobs(jobs, "build/render-report.json")
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "remotion", "node": _env.tools().get("node"),
                                          "seconds": round(time.time() - t0, 1), "jobs": len(jobs)})
    music, films = False, []
    for silent, out in made:
        if Path(silent).exists():
            music = mux(Path(silent), Path(out), secs)
            films.append(out)
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    film = f"; {secs:.1f} s{' with music' if music else ' (no music track)'} -> {', '.join(films)}" if films else ""
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {time.time() - t0:.1f} s{film}")
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
    for i, b in enumerate(tl["beats"], 1):
        # the settled moment of the beat's longest shot: past its entrance, before the next cut or transition
        edges = b.get("shots") or [0, b["frames"]]
        spans = [(edges[k], edges[k + 1]) for k in range(len(edges) - 1)]
        lo, hi = max(spans, key=lambda e: e[1] - e[0])
        lo = max(lo, b["transition"])
        grab((b["start"] + lo + (hi - lo) * 0.7) / FPS, out / f"{i:02d}-{b['id']}.png")
        if len(spans) >= 4:
            # a beat cut into many shots (a day's photos, a place's montage) also gets every shot
            sub = out / f"{i:02d}-{b['id']}"
            sub.mkdir(exist_ok=True)
            for k, (a_, z) in enumerate(spans, 1):
                grab((b["start"] + max(a_, b["transition"]) + (z - max(a_, b["transition"])) * 0.7) / FPS, sub / f"{k:02d}.png")
                shots += 1
    print(f"{len(tl['beats'])} frames -> {out}/" + (f", and {shots} shot frames in its beat folders" if shots else ""))
    return 0


# ------------------------------------------------------------------ the stills route (no node)
def cmd_stills(a):
    """Each beat as one composed still under an eased push, cut with crossfades. Same film.json, same out/ names."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    fonts = {k: str(_env.SKILL / s[k]["file"]) for k in ("display", "text")}

    def font(kind, size):
        return ImageFont.truetype(fonts[kind], size)

    def photo(p, w, h):
        im = Image.open(PUBLIC / p).convert("RGB")
        return ImageOps.fit(im, (w, h), Image.LANCZOS)

    def route(d, pts, box, width):
        """Their coordinates as a line across the box (equirectangular, fitted), a dot and a name at each place."""
        import math
        if not pts:
            return
        lat0 = sum(p["lat"] for p in pts) / len(pts)
        kx = math.cos(math.radians(lat0))
        xs, ys = [p["lon"] * kx for p in pts], [-p["lat"] for p in pts]
        span = max(max(xs) - min(xs), max(ys) - min(ys), 0.02)
        k = min(box[2], box[3]) * 0.72 / span
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        xy = [(box[0] + box[2] / 2 + (x - cx) * k, box[1] + box[3] / 2 + (y - cy) * k) for x, y in zip(xs, ys)]
        if len(xy) > 1:
            d.line(xy, fill=s["colors"]["accent"], width=width, joint="curve")
        named = set()
        f = font("text", int(s["scale"]["label"]))
        for (x, y), p in zip(xy, pts):
            r = width * 1.3
            d.ellipse((x - r, y - r, x + r, y + r), fill=s["colors"]["accent"])
            if p.get("place") and p["place"] not in named:
                named.add(p["place"])
                d.text((x + r * 2, y), p["place"], font=f, fill=s["colors"]["ink"], anchor="lm")

    def compose(bt, w, h, fmt):
        sa = s["safe"].get(fmt) or s["safe"]["reel"]
        wide = w > h
        paper = bt["kind"] == "Postcard"
        bg = Image.new("RGB", (w, h), s["colors"]["paper" if paper else "bg"])
        t = dict(bt.get("text") or {})
        data = bt.get("data") or {}
        ph = list(bt.get("photos") or [])
        if bt.get("clip") and isinstance(bt["clip"], dict) and bt["clip"].get("image"):
            ph = [bt["clip"]["image"]] + ph
        d = ImageDraw.Draw(bg)
        left, right = sa["left"], w - sa["right"]
        if paper and ph:
            pw = int((right - left) * (0.52 if wide else 1.0))
            phh = int(pw * 0.72) if wide else min(600, int(pw * 0.74))
            top = sa["top"] + ((h - sa["top"] - sa["bottom"]) - phh) // 2 if wide else max(110, sa["top"] - 140)
            d.rectangle((left - 18, top - 18, left + pw + 18, top + phh + 18), fill="#fbf8f1")
            bg.paste(photo(ph[0], pw, phh), (left, top))
            if wide:
                left = left + pw + 70
        elif bt["kind"] in ("Route", "Closer") and data.get("points"):
            if bt["kind"] == "Closer" and ph:
                bg = Image.blend(photo(ph[0], w, h), Image.new("RGB", (w, h), s["colors"]["bg"]), 0.75)
                d = ImageDraw.Draw(bg)
            box = (sa["left"], sa["top"], (right - left) * 0.58, h - sa["top"] - sa["bottom"]) if wide else \
                (sa["left"], sa["top"], right - left, max(320, h - sa["top"] - sa["bottom"] - 360))
            route(d, data["points"], box, 8)
            if wide:
                left = int(sa["left"] + (right - sa["left"]) * 0.63)
        elif ph:
            bg.paste(photo(ph[0], w, h))
            shade = Image.new("L", (1, 256))
            for y in range(256):
                shade.putpixel((0, y), int(max(0, (y - 90) / 166) * 200))
            bg = Image.composite(Image.new("RGB", (w, h), s["colors"]["bg"]), bg, shade.resize((w, h)))
            d = ImageDraw.Draw(bg)
        ink = s["colors"]["bg"] if paper else s["colors"]["ink"]
        maxw = right - left
        blocks = []
        if t.get("kicker"):
            blocks.append(("text", str(t["kicker"]).upper(), int(s["scale"]["label"]), s["colors"]["accent"]))
        if t.get("headline"):
            size = int(s["scale"]["h2" if paper else "h1"])
            while size > 20 and font("display", size).getlength(str(t["headline"])) > maxw * 2.6:
                size -= 4
            blocks.append(("display", t["headline"], size, ink))
        if t.get("line"):
            blocks.append(("text", t["line"], int(s["scale"]["body"]), ink))
        laid = []
        for kind, text, size, color in blocks:
            f = font(kind, size)
            lines, cur = [], ""
            for wd in str(text).split():
                nxt = (cur + " " + wd).strip()
                if f.getlength(nxt) <= maxw or not cur:
                    cur = nxt
                else:
                    lines.append(cur)
                    cur = wd
            lines.append(cur)
            laid.append((f, lines, size, color))
        height = sum(len(ln) * int(sz * 1.08) + int(sz * 0.4) for _, ln, sz, _ in laid)
        y = h - sa["bottom"] - height
        if paper and not wide:
            y = min(y, max(110, sa["top"] - 140) + 650)
        for f, lines, size, color in laid:
            for ln in lines:
                d.text((left, y), ln, font=f, fill=color)
                y += int(size * 1.08)
            y += int(size * 0.4)
        return bg

    ff = _env.ffmpeg()
    work = Path("build/stills")
    work.mkdir(parents=True, exist_ok=True)
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    Path("out").mkdir(exist_ok=True)
    music = False

    def film(props, W, H, fmt, silent, out):
        parts = []
        for i, bt in enumerate(props["beats"]):
            f = work / f"{fmt}-{i + 1:02d}-{bt['id']}.png"
            compose(bt, W, H, fmt).save(f)
            n = bt["frames"]
            clip = work / f"{fmt}-{i + 1:02d}.mp4"
            z = "1+0.06*(1-pow(1-on/{n},3))".format(n=n)
            subprocess.run([ff, "-y", "-v", "error", "-loop", "1", "-i", str(f), "-t", f"{n / FPS:.3f}", "-vf",
                            f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},format=yuv420p",
                            "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-r", str(FPS), str(clip)], check=True)
            parts.append((clip, n / FPS, (bt.get("transition") or {}).get("frames", 0) / FPS))
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
        subprocess.run([ff, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(flt) or "null", "-map", f"[{last}]" if flt else "0:v",
                        "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)], check=True)
        return mux(Path(silent), Path(out), secs)

    props = props_for(board)["board"]
    for key, fmt, silent, out in FILMS:
        W, H = (1920, 1080) if fmt == "landscape" else (1080, 1920)
        music = film(props, W, H, fmt, silent, out)
    for f in Path("out").glob("story-*.png"):
        f.unlink()
    for i, st in enumerate(props.get("stories") or [], 1):
        compose(st, 1080, 1920, "story").save(story_out(i))
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: {secs:.1f} s{' with music' if music else ''} -> out/film.mp4, out/film-16x9.mp4; "
          f"{len(props.get('stories') or [])} story cards -> out/story-N.png")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "frames", "stills"])
    ap.add_argument("--only", choices=["film", "landscape", "cards"])
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="build/frames")
    a = ap.parse_args()
    return {"render": cmd_render, "frames": cmd_frames, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
