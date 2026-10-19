#!/usr/bin/env python3
"""Movement 4: the film and the map poster, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4 (1080x1920) + out/poster.png (1080x1350)
    python3 S/scripts/film.py render --only film|cards
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as stills under motion

The engine is the Remotion project in S/motion (setup.py installs it). render writes the silent picture to
build/film.silent.mp4 (1080x1920, 30 fps, H.264 high, CRF 18), then lays the mastered music under it
(build/music/master.wav from music.py, AAC 192 kbps) into out/film.mp4. Every SAFE_BREACH (text that left its
safe box), FONT_ERROR and render error lands in build/render-report.json, which qa.py gate reads.
build/timeline.json carries each beat's start, length and the places it shows (focus) for qa.py and the frame
extraction.
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
    if b.get("poster"):
        b["poster"]["clip"] = None
    for k in ("timeline", "clips", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds"):
        b.pop(k, None)
    return {"board": b}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "pm-bundle")}
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
                    "shots": [0] + list((b.get("data") or {}).get("cuts") or []) + [b["frames"]],
                    "focus": list((b.get("data") or {}).get("focus") or [])})
        start += b["frames"]
    return out


CARDS = (("poster", "poster", "out/poster.png"),)


def card_jobs(board, props):
    jobs = []
    for key, fmt, out in CARDS:
        c = props["board"].get(key)
        if c:
            jobs.append({"type": "still", "composition": "Card", "frame": 0, "scale": 1,
                         "props": {"board": props["board"], "beat": c, "format": fmt},
                         "out": str(Path(out).resolve())})
    return jobs


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
        for _, _, f in CARDS:
            Path(f).unlink(missing_ok=True)
    props = props_for(board)
    jobs = []
    silent = Path("build/film.silent.mp4").resolve()
    if a.only in (None, "film"):
        jobs.append({"type": "video", "composition": "Film", "props": props, "out": str(silent), "crf": 18, "preset": "medium"})
    if a.only in (None, "cards"):
        jobs += card_jobs(board, props)
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
    """Each beat as one composed still under an eased push, cut with crossfades: the map beats and the poster drawn
    from the same coordinates and land shapes, the stamps as photos in their shapes. Same film.json, same out/ names."""
    _env.need("PIL")
    import re
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    c, m = s["colors"], s["map"]
    W, H = board["format"]["width"], board["format"]["height"]
    fonts = {k: str(_env.SKILL / s[k]["file"]) for k in ("display", "text")}
    land = _env.read_json(PUBLIC / board["map"]["land"]) or {"paths": []}
    rings = []
    for d in land["paths"]:
        for sub in re.findall(r"M[^M]*", d):
            pts = [(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+)[ ,](-?[\d.]+)", sub)]
            if len(pts) > 2:
                rings.append(pts)
    pins = {p["id"]: p for p in board["map"]["pins"]}
    legs = board["map"]["legs"]

    def font(kind, size):
        return ImageFont.truetype(fonts[kind], size)

    def photo(p, w, h):
        return ImageOps.fit(Image.open(PUBLIC / p).convert("RGB"), (w, h), Image.LANCZOS)

    def proj(cam, w, h, x, y):
        k = w / cam[2]
        return (w / 2 + (x - cam[0]) * k, h / 2 + (y - cam[1]) * k)

    def draw_map(cam, w, h, upto=None, ids=None, labels=None, size=30, night=False, route_w=6):
        """The map at one camera: sea, land, the route's legs up to `upto` (all when None) and the pins in `ids`."""
        sea = c["bg"] if night else m["sea"]
        im = Image.new("RGB", (w, h), sea)
        d = ImageDraw.Draw(im)
        for r in rings:
            d.polygon([proj(cam, w, h, x, y) for x, y in r], fill=m["land"], outline=m["coast"])
        for i, lg in enumerate(legs if upto is None else legs[:upto]):
            if ids is not None and (lg["from"] not in ids or lg["to"] not in ids):
                continue
            pts = [proj(cam, w, h, x, y) for x, y in lg["arc"]]
            if lg["far"]:
                for q in pts[::2]:
                    d.ellipse([q[0] - route_w / 2, q[1] - route_w / 2, q[0] + route_w / 2, q[1] + route_w / 2], fill=m["route"])
            else:
                d.line(pts, fill=m["route"], width=route_w, joint="curve")
        f = font("text", size)
        for pid in (ids if ids is not None else list(pins)):
            p = pins.get(pid)
            if not p:
                continue
            x, y = proj(cam, w, h, p["x"], p["y"])
            r = 9
            d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=m["halo"])
            d.ellipse([x - r, y - r, x + r, y + r], fill=m["pin"])
            if labels is not None:
                side = labels.get(pid, "right")
                g = size * 0.55
                anchor, at = {"right": ("lm", (x + g, y)), "left": ("rm", (x - g, y)),
                              "above": ("mb", (x, y - g)), "below": ("mt", (x, y + g))}[side]
                d.text(at, p["name"], font=f, fill=m["label"], anchor=anchor, stroke_width=3, stroke_fill=m["halo"])
        return im

    def text_block(im, t, sa, top=None, hero="h1"):
        d = ImageDraw.Draw(im)
        w, h = im.size
        left, maxw = sa["left"], w - sa["left"] - sa["right"]
        blocks = []
        if t.get("kicker"):
            blocks.append(("text", str(t["kicker"]).upper(), s["scale"]["label"], c["accent"]))
        if t.get("headline"):
            size = s["scale"][hero]
            while size > 20 and font("display", size).getlength(str(t["headline"])) > maxw * 1.9:
                size -= 4
            blocks.append(("display", t["headline"], size, c["ink"]))
        if t.get("line"):
            blocks.append(("text", t["line"], s["scale"]["body"], c["ink"]))
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
        y = top if top is not None else h - sa["bottom"] - height
        for f, lines, size, color in laid:
            for ln in lines:
                d.text((left, y), ln, font=f, fill=color, stroke_width=2, stroke_fill=c["bg"])
                y += int(size * 1.08)
            y += int(size * 0.4)
        return im

    def shade(im):
        w, h = im.size
        ramp = Image.new("L", (1, 256))
        for y in range(256):
            ramp.putpixel((0, y), int(max(0, (y - 90) / 166) * 200))
        return Image.composite(Image.new("RGB", (w, h), c["bg"]), im, ramp.resize((w, h)))

    def poster(bt, fmt):
        w, h = (1080, 1350) if fmt == "poster" else (W, H)
        sa = s["safe"][fmt]
        L = bt["data"]["layout"][fmt]
        night = bool(bt["data"].get("night"))
        im = Image.new("RGB", (w, h), c["bg"])
        rx, ry, rw, rh = L["rect"]
        far = set((L.get("inset") or {}).get("ids") or [])
        near = [pid for pid in pins if pid not in far]
        im.paste(draw_map(L["cam"], rw, rh, ids=near, labels=L["labels"], size=L["size"], night=night), (rx, ry))
        ins = L.get("inset")
        if ins:
            ix, iy, iw, ih = ins["rect"]
            box = draw_map(ins["cam"], iw, ih, ids=ins["ids"], labels=L["labels"], size=round(L["size"] * 0.85), night=night)
            ImageDraw.Draw(box).rectangle([0, 0, iw - 1, ih - 1], outline=m["label"], width=3)
            km = pins[ins["ids"][0]].get("km_from_home") if len(ins["ids"]) == 1 else None
            if km:
                ImageDraw.Draw(box).text((14, ih - 12), f"{km:,} km from home", font=font("text", round(L["size"] * 0.7)),
                                         fill=m["label"], anchor="ls", stroke_width=2, stroke_fill=m["halo"])
            im.paste(box, (rx + ix, ry + iy))
        t = bt.get("text") or {}
        if fmt == "poster":
            text_block(im, {"kicker": t.get("kicker"), "headline": t.get("headline")}, sa, top=sa["top"], hero="h2")
            text_block(im, {"line": t.get("line")}, sa)
        else:
            text_block(im, t, sa, top=ry + rh + 20, hero="h2")
        return im

    def stamp(bt):
        im = Image.new("RGB", (W, H), c["paper"])
        sa = s["safe"]["reel"]
        st = (bt["data"].get("stamp") or {})
        page = bt["data"].get("page") or []
        if bt["data"].get("mode") == "page":
            cols = 2 if len(page) <= 4 else 3 if len(page) <= 9 else 4
            cell = (W - 80) // cols
            for i, q in enumerate(page):
                if q.get("photos"):
                    tile = photo(q["photos"][0], cell - 30, cell - 30)
                    im.paste(tile, (40 + (i % cols) * cell + 15, 150 + (i // cols) * cell + 15))
            return text_block(im, bt.get("text") or {}, sa)
        if st.get("photos"):
            size = 640
            tile = photo(st["photos"][0], size, size)
            mask = Image.new("L", (size, size), 0)
            md = ImageDraw.Draw(mask)
            if st.get("shape") in ("circle", "oval"):
                md.ellipse([0, 0, size - 1, size - 1], fill=255)
            else:
                md.rectangle([0, 0, size - 1, size - 1], fill=255)
            x0, y0 = (W - size) // 2, sa["top"]
            im.paste(tile, (x0, y0), mask)
            ImageDraw.Draw(im).text((W // 2, y0 + size - 50), st.get("name", ""), font=font("display", 44), fill=c["paper"],
                                    anchor="mm", stroke_width=3, stroke_fill=c["ink"])
        return text_block(im, bt.get("text") or {}, sa)

    def compose(bt):
        k = bt["kind"]
        dt = bt.get("data") or {}
        sa = s["safe"]["reel"]
        if k == "Poster":
            return poster(bt, "reel")
        if k == "Stamp":
            return stamp(bt)
        if k == "MapJourney":
            upto = (dt.get("done") or 0) + len(dt.get("legs") or [])
            seen = set()
            for lg in legs[:upto]:
                seen |= {lg["from"], lg["to"]}
            seen = seen or set(board["map"]["route"][:1])
            im = draw_map(dt.get("cam1") or dt.get("cam0"), W, H, upto=upto, ids=list(seen) if upto else list(pins),
                          labels=(dt.get("labels") or {}) if dt.get("mode") == "overview" else None, size=30)
            card = dt.get("card") or {}
            if card.get("photo"):
                ph = photo(card["photo"], 400, 400)
                frame = Image.new("RGB", (430, 500), c["paper"])
                frame.paste(ph, (15, 15))
                x = W - sa["right"] - 430 + 30 if card.get("side") == "right" else sa["left"] - 10
                im.paste(frame, (x, sa["top"] + 20))
            return text_block(shade(im), bt.get("text") or {}, sa)
        im = Image.new("RGB", (W, H), c["bg"])
        ph = list(bt.get("photos") or [])
        if isinstance(bt.get("clip"), dict) and bt["clip"].get("image"):
            ph = [bt["clip"]["image"]] + ph
        if ph:
            im = shade(photo(ph[0], W, H))
        return text_block(im, bt.get("text") or {}, sa)

    ff = _env.ffmpeg()
    work = Path("build/stills")
    work.mkdir(parents=True, exist_ok=True)
    props = props_for(board)["board"]
    parts = []
    for i, bt in enumerate(props["beats"]):
        f = work / f"{i + 1:02d}-{bt['id']}.png"
        compose(bt).save(f)
        secs = bt["frames"] / FPS
        clip = work / f"{i + 1:02d}.mp4"
        z = "1+0.06*(1-pow(1-on/{n},3))".format(n=bt["frames"])
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
    subprocess.run([ff, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(flt) or "null", "-map", f"[{last}]" if flt else "0:v",
                    "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)], check=True)
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    Path("out").mkdir(exist_ok=True)
    music = mux(silent, Path("out/film.mp4"), secs)
    for key, fmt, out in CARDS:
        if props.get(key):
            poster(props[key], fmt).save(out)
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "engine": "stills"})
    print(f"stills route: film {secs:.1f} s{' with music' if music else ''} -> out/film.mp4; out/poster.png")
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
