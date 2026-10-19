#!/usr/bin/env python3
"""Movement 4: the film in both shapes and the card, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4 (1080x1920) + out/film-square.mp4 (1080x1080) + out/card.png (1080x1350)
    python3 S/scripts/film.py render --only film|square|card
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as stills under motion

The engine is the Remotion project in S/motion (setup.py installs it). One storyboard makes both films: render
draws the beats at 1080x1920 into build/film.silent.mp4 and again at 1080x1080 (the feed safe area, the type a
step smaller) into build/film-square.silent.mp4, both 30 fps H.264 high at CRF 18, then lays the mastered music
(build/music/master.wav from music.py, AAC 192 kbps) under each: out/film.mp4 and out/film-square.mp4. The card
is the board's "card" beat (its closer, held still) at 1080x1350: out/card.png. Every SAFE_BREACH (text that
left its safe box), FONT_ERROR and render error lands in build/render-report.json, which qa.py gate reads.
build/timeline.json carries each beat's start and length for qa.py and the frame extraction.
When setup.py reports engine "stills", render runs the stills route instead and build/engine.json says so.
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


def props_for(board):
    """The composition props: the board with every beat's clip reference resolved to a file or its substitute."""
    b = copy.deepcopy(board)
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    for bt in b["beats"]:
        bt["clip"] = clip_for(bt, clips)
        if bt["clip"] and bt["clip"].get("image") is None and bt.get("photos"):
            bt["clip"]["image"] = bt["photos"][0]
    if b.get("card"):
        b["card"]["clip"] = None
    for k in ("timeline", "clips", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds"):
        b.pop(k, None)
    return {"board": b}


SQUARE_TYPE = 0.84


def square_props(props):
    """The same beats for the 1:1 feed cut: a square frame, the feed safe area, the type scale a step down."""
    sq = copy.deepcopy(props)
    b = sq["board"]
    b["format"] = {**b["format"], "width": 1080, "height": 1080, "safe": "feed"}
    b["system"]["scale"] = {k: int(round(v * SQUARE_TYPE)) for k, v in b["system"]["scale"].items()}
    return sq


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or "build/.bundle").resolve() / "bt-bundle")}
    if concurrency:
        spec["concurrency"] = concurrency
    jf = Path("build/render") / f"{Path(report).stem}.jobs.json"
    _env.write_json(jf, spec)
    node = t["node"]
    env = dict(os.environ, PATH=f"{Path(node).parent}{os.pathsep}{os.environ.get('PATH', '')}")
    # cwd is the motion folder: Remotion keeps its browser in .remotion/ under the working directory, where setup.py put it
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


FILMS = {"film": ("build/film.silent.mp4", "out/film.mp4"), "square": ("build/film-square.silent.mp4", "out/film-square.mp4")}
CARD = "out/card.png"


def card_job(props):
    c = props["board"].get("card") or props["board"]["beats"][-1]
    return {"type": "still", "composition": "Card", "frame": 0, "scale": 1,
            "props": {"board": props["board"], "beat": c, "format": "portrait"}, "out": str(Path(CARD).resolve())}


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
    want = [a.only] if a.only else ["film", "square", "card"]
    jobs = []
    for k in ("film", "square"):
        if k in want:
            silent, out = FILMS[k]
            Path(out).unlink(missing_ok=True)
            jobs.append({"type": "video", "composition": "Film", "props": props if k == "film" else square_props(props),
                         "out": str(Path(silent).resolve()), "crf": 18, "preset": "medium"})
    if "card" in want:
        Path(CARD).unlink(missing_ok=True)
        jobs.append(card_job(props))
    t0 = time.time()
    rep = render_jobs(jobs, "build/render-report.json")
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "remotion", "node": _env.tools().get("node"),
                                          "seconds": round(time.time() - t0, 1), "jobs": len(jobs)})
    made = []
    for k in ("film", "square"):
        silent, out = FILMS[k]
        if k in want and Path(silent).exists():
            music = mux(Path(silent), Path(out), secs)
            made.append(f"{out}{' with music' if music else ' (no music track)'}")
    if "card" in want and Path(CARD).exists():
        made.append(CARD)
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    print(f"rendered {len(jobs) - rep.get('failed', 0)} of {len(jobs)} jobs in {time.time() - t0:.1f} s; {secs:.1f} s -> {', '.join(made)}")
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
            # a beat cut into many shots also gets every shot
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
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    W, H = board["format"]["width"], board["format"]["height"]
    safe = s["safe"]["reel"]
    fonts = {k: str(_env.SKILL / s[k]["file"]) for k in ("display", "text")}
    from PIL import ImageFont

    def font(kind, size):
        return ImageFont.truetype(fonts[kind], size)

    def photo(p, w, h):
        im = Image.open(PUBLIC / p).convert("RGB")
        return ImageOps.fit(im, (w, h), Image.LANCZOS)

    def compose(bt, w, h, sf, fmt="reel"):
        sa = s["safe"].get(fmt) or safe
        bg = Image.new("RGB", (w, h), s["colors"]["bg"])
        t = dict(bt.get("text") or {})
        if bt["kind"] == "Exchange":
            t["line"] = " / ".join(x["text"] for x in (bt.get("data") or {}).get("lines", []))
        if bt["kind"] == "KineticType" and not t.get("headline"):
            t["headline"] = " ".join(r["text"] for r in (bt.get("data") or {}).get("rows", []))
        ph = (bt.get("photos") or [])
        if bt.get("clip") and isinstance(bt["clip"], dict) and bt["clip"].get("image"):
            ph = [bt["clip"]["image"]] + ph
        if ph:
            bg.paste(photo(ph[0], w, h))
            shade = Image.new("L", (1, 256))
            for y in range(256):
                shade.putpixel((0, y), int(max(0, (y - 90) / 166) * 200))
            bg = Image.composite(Image.new("RGB", (w, h), s["colors"]["bg"]), bg, shade.resize((w, h)))
        d = ImageDraw.Draw(bg)
        left, maxw = int(sa["left"] * sf), int(w - (sa["left"] + sa["right"]) * sf)
        blocks = []
        if t.get("kicker"):
            blocks.append(("text", str(t["kicker"]).upper(), int(s["scale"]["label"] * sf), s["colors"]["accent"]))
        if t.get("headline"):
            size = int(s["scale"]["h1"] * sf)
            while size > 20 and font("display", size).getlength(str(t["headline"])) > maxw * 1.9:
                size -= 4
            blocks.append(("display", t["headline"], size, s["colors"]["ink"]))
        if t.get("line"):
            blocks.append(("text", t["line"], int(s["scale"]["body"] * sf), s["colors"]["ink"]))
        laid = []
        for kind, text, size, color in blocks:
            f = font(kind, size)
            words, lines, cur = str(text).split(), [], ""
            for wd in words:
                nxt = (cur + " " + wd).strip()
                if f.getlength(nxt) <= maxw or not cur:
                    cur = nxt
                else:
                    lines.append(cur)
                    cur = wd
            lines.append(cur)
            laid.append((f, lines, size, color))
        height = sum(len(ln) * int(sz * 1.08) + int(sz * 0.4) for _, ln, sz, _ in laid)
        y = int(h - sa["bottom"] * sf) - height
        for f, lines, size, color in laid:
            for ln in lines:
                d.text((left, y), ln, font=f, fill=color)
                y += int(size * 1.08)
            y += int(size * 0.4)
        return bg

    ff = _env.ffmpeg()
    work = Path("build/stills")
    work.mkdir(parents=True, exist_ok=True)
    props = props_for(board)["board"]
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    Path("out").mkdir(exist_ok=True)
    music = False
    for key, (w, h, fmt, sf) in {"film": (W, H, "reel", 1), "square": (1080, 1080, "feed", SQUARE_TYPE)}.items():
        parts = []
        for i, bt in enumerate(props["beats"]):
            f = work / f"{key}-{i + 1:02d}-{bt['id']}.png"
            compose(bt, w, h, sf, fmt).save(f)
            clip = work / f"{key}-{i + 1:02d}.mp4"
            z = "1+0.06*(1-pow(1-on/{n},3))".format(n=bt["frames"])
            subprocess.run([ff, "-y", "-v", "error", "-loop", "1", "-i", str(f), "-t", f"{bt['frames'] / FPS:.3f}", "-vf",
                            f"scale={w * 2}:{h * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={bt['frames']}:s={w}x{h}:fps={FPS},format=yuv420p",
                            "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-r", str(FPS), str(clip)], check=True)
            parts.append((clip, bt["frames"] / FPS, (bt.get("transition") or {}).get("frames", 0) / FPS))
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
        silent, out = FILMS[key]
        subprocess.run([ff, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(flt), "-map", f"[{last}]",
                        "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), silent], check=True)
        music = mux(Path(silent), Path(out), secs)
    compose(props.get("card") or props["beats"][-1], 1080, 1350, 1, "portrait").save(CARD)
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: {secs:.1f} s{' with music' if music else ''} -> out/film.mp4, out/film-square.mp4, {CARD}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "frames", "stills"])
    ap.add_argument("--only", choices=["film", "square", "card"])
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="build/frames")
    a = ap.parse_args()
    return {"render": cmd_render, "frames": cmd_frames, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
