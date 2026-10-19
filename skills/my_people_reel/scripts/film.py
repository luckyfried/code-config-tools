#!/usr/bin/env python3
"""Movement 4: the film and one story card per person, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4 + out/people/NN-<handle>.png (1080x1920, one per person)
    python3 S/scripts/film.py render --only film|cards
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as stills under motion

The engine is the Remotion project in S/motion (setup.py installs it). render writes the silent picture to
build/film.silent.mp4 (1080x1920, 30 fps, H.264 high, CRF 18), then lays the mastered music under it
(build/music/master.wav from music.py, AAC 192 kbps) into out/film.mp4. Every SAFE_BREACH (text that left its
safe box), FONT_ERROR and render error lands in build/render-report.json, which qa.py gate reads.
build/timeline.json carries each beat's start and length for qa.py and the frame extraction.
build/cards.json names each person's card, its file and its photo, for qa.py and deliver.py.
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
    """The composition props: the board with every clip reference, a beat's or a tile's, resolved to a file or its substitute."""
    b = copy.deepcopy(board)
    clips = (_env.read_json("build/clips.json") or {}).get("clips", {})
    for bt in b["beats"]:
        bt["clip"] = clip_for(bt, clips)
        if bt["clip"] and bt["clip"].get("image") is None and bt.get("photos"):
            bt["clip"]["image"] = bt["photos"][0]
        for tl in (bt.get("data") or {}).get("tiles") or []:
            tl["clip"] = clip_for(tl, clips) if tl.get("clip") else None
            if tl["clip"] and tl["clip"].get("image") is None:
                tl["clip"]["image"] = tl.get("photo")
    for c in b.get("cards") or []:
        c["clip"] = None
    for k in ("timeline", "clips", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds"):
        b.pop(k, None)
    return {"board": b}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "mpr-bundle")}
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


def card_path(c):
    d = c.get("data") or {}
    return Path("out/people") / f"{int(d.get('rank') or 0):02d}-{d.get('handle') or c['id']}.png"


def card_jobs(props):
    return [{"type": "still", "composition": "Card", "frame": 0, "scale": 1,
             "props": {"board": props["board"], "beat": c, "format": "story"}, "out": str(card_path(c).resolve())}
            for c in props["board"].get("cards") or []]


def write_cards(board):
    """Each person's story card: rank, handle, file and the photo it is made from."""
    cards = [{"rank": (c.get("data") or {}).get("rank"), "handle": (c.get("data") or {}).get("handle"), "file": str(card_path(c)),
              "photo": (c.get("photos") or [None])[0], "line": (c.get("text") or {}).get("headline")} for c in board.get("cards") or []]
    _env.write_json("build/cards.json", {"size": [1080, 1920], "cards": cards})


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
    if a.only in (None, "cards"):
        Path("out/people").mkdir(parents=True, exist_ok=True)
        for f in Path("out/people").glob("*.png"):
            f.unlink()
        write_cards(board)
    props = props_for(board)
    jobs = []
    silent = Path("build/film.silent.mp4").resolve()
    if a.only in (None, "film"):
        jobs.append({"type": "video", "composition": "Film", "props": props, "out": str(silent), "crf": 18, "preset": "medium"})
    if a.only in (None, "cards"):
        jobs += card_jobs(props)
    t0 = time.time()
    rep = render_jobs(jobs, "build/render-report.json")
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    _env.write_json("build/engine.json", {"engine": "remotion", "node": _env.tools().get("node"),
                                          "seconds": round(time.time() - t0, 1), "jobs": len(jobs)})
    music = False
    if a.only in (None, "film") and silent.exists():
        Path("out").mkdir(exist_ok=True)
        music = mux(silent, Path("out/film.mp4"), secs)
    for f in rep.get("findings", []):
        print("finding:", f["text"][:400])
    film = f"; film {secs:.1f} s{' with music' if music else ' (no music track)'} -> out/film.mp4" if a.only in (None, "film") else ""
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
            # a beat cut into many shots (the wall assembling, the camera moving tile to tile) also gets every shot
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

    def wall(bt, w, h, top, side=None):
        """The party wall as 3x3, slot by slot, centered at the given top (filling the width unless a side is given)."""
        data = bt.get("data") or {}
        by = {t["rank"]: t for t in data.get("tiles", [])}
        gap = max(6, w // 120)
        side = side or min(w - 2 * gap, h - top - gap)
        tile = (side - 2 * gap) // 3
        x0 = (w - (3 * tile + 2 * gap)) // 2
        im = Image.new("RGB", (w, h), s["colors"]["bg"])
        for i, r in enumerate(data.get("order") or []):
            t = by.get(r)
            if t:
                im.paste(photo(t["photo"], tile, tile), (x0 + (i % 3) * (tile + gap), top + (i // 3) * (tile + gap)))
        return im

    def compose(bt, w, h, sf, fmt="reel"):
        sa = s["safe"].get(fmt) or safe
        bg = Image.new("RGB", (w, h), s["colors"]["bg"])
        t = dict(bt.get("text") or {})
        if bt["kind"] == "Grid":
            bg = wall(bt, w, h, int(h * 0.31))
        else:
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
        grid_top = bt["kind"] in ("Grid", "Leaderboard")
        if bt["kind"] == "Leaderboard":
            data = bt.get("data") or {}
            shown = set(data.get("shown") or [])
            rows = sorted(data.get("rows") or [], key=lambda r: r["rank"])
            y = int(h - sa["bottom"] * sf) - len(rows) * 102
            for r in rows:
                on = r["rank"] in shown
                color = s["colors"]["accent"] if r["rank"] == data.get("me") else s["colors"]["ink"] if on else s["colors"]["muted"]
                d.text((left, y), f"{r['rank']}", font=font("display", 64), fill=color)
                d.text((left + 100, y + 14), f"@{r['handle']}" if on else "·  ·  ·", font=font("text", 36), fill=color)
                y += 102
        blocks = []
        if t.get("kicker"):
            blocks.append(("text", str(t["kicker"]).upper(), int(s["scale"]["label"] * sf), s["colors"]["accent"]))
        if t.get("headline"):
            size = int((s["scale"]["h2"] if grid_top else s["scale"]["h1"]) * sf)
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
        if grid_top:
            y = int(sa["top"] * sf)
        else:
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
    parts = []
    for i, bt in enumerate(props["beats"]):
        im = compose(bt, W, H, 1)
        f = work / f"{i + 1:02d}-{bt['id']}.png"
        im.save(f)
        secs = bt["frames"] / FPS
        clip = work / f"{i + 1:02d}.mp4"
        z = "1+0.06*(1-pow(1-on/{n},3))".format(n=bt["frames"])
        subprocess.run([ff, "-y", "-v", "error", "-loop", "1", "-i", str(f), "-t", f"{secs:.3f}", "-vf",
                        f"scale={W * 2}:{H * 2},zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={bt['frames']}:s={W}x{H}:fps={FPS},format=yuv420p",
                        "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-r", str(FPS), str(clip)], check=True)
        parts.append((clip, secs, (bt.get("transition") or {}).get("frames", 0) / FPS))
    inputs, flt, last, offset = [], [], "0:v", 0
    for k, (clip, secs, tr) in enumerate(parts):
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
    write_cards(board)
    Path("out/people").mkdir(parents=True, exist_ok=True)
    for c in props.get("cards") or []:
        compose(c, 1080, 1920, 1, "story").save(card_path(c))
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: film {secs:.1f} s{' with music' if music else ''} -> out/film.mp4; {len(props.get('cards') or [])} cards -> out/people/")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["render", "frames", "stills"])
    ap.add_argument("--only", choices=["film", "cards"])
    ap.add_argument("--film", default="out/film.mp4")
    ap.add_argument("--out", default="build/frames")
    a = ap.parse_args()
    return {"render": cmd_render, "frames": cmd_frames, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
