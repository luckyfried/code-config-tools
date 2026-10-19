#!/usr/bin/env python3
"""Movement 4: the film and the ten guide cards, rendered from build/film.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/film.py render            # out/film.mp4 (1080x1920) + out/cards/01-palette.png .. 10-week.png (1080x1350)
    python3 S/scripts/film.py render --only film|cards
    python3 S/scripts/film.py frames            # one frame per beat of out/film.mp4 into build/frames/NN-<beat>.png
                                                # (and every shot of a many-shot beat into build/frames/NN-<beat>/)
    python3 S/scripts/film.py stills            # the stills route (no node): the same film.json as stills under motion

The engine is the Remotion project in S/motion (setup.py installs it). render writes the silent picture to
build/film.silent.mp4 (1080x1920, 30 fps, H.264 high, CRF 18), then lays the mastered music under it
(build/music/master.wav from music.py, AAC 192 kbps) into out/film.mp4. Every SAFE_BREACH (text that left its
safe box or a card's body), FONT_ERROR and render error lands in build/render-report.json, which qa.py gate reads,
and so does every color name a card shows (its guide list). build/cards.json names the ten card files.
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
    for k in ("timeline", "clips", "idea", "music", "structure", "tone", "clip_use", "direction", "seconds", "field"):
        b.pop(k, None)
    return {"board": b}


def render_jobs(jobs, report, concurrency=None):
    t = _env.tools()
    if t.get("engine") != "remotion":
        sys.exit("the motion engine is not installed (setup.py reports engine 'stills'); run film.py stills")
    spec = {"publicDir": str(PUBLIC.resolve()), "report": str(Path(report).resolve()), "jobs": jobs,
            "bundleDir": str(Path(os.environ.get("TMPDIR") or Path("build/.bundle").resolve()) / "pb-bundle")}
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


CARDS = Path("out/cards")


def card_jobs(board, props):
    return [{"type": "still", "composition": "Card", "frame": 0, "scale": 1, "props": {"board": props["board"], "card": c["n"]},
             "out": str((CARDS / f"{c['id']}.png").resolve())} for c in board.get("cards", [])]


def write_cards(board):
    """The ten card files in order, with what each shows, for qa.py and deliver.py."""
    _env.write_json("build/cards.json", {"size": [1080, 1350], "cards": [
        {"n": c["n"], "kind": c["kind"], "file": str(CARDS / f"{c['id']}.png"), "title": c.get("title"),
         "colors": [x["name"] for x in c.get("colors", [])]} for c in board.get("cards", [])]})


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
        shutil.rmtree(CARDS, ignore_errors=True)
        CARDS.mkdir(parents=True)
        write_cards(board)
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
            # a beat cut into many shots (the swipe, the camera moving panel to panel) also gets every shot
            sub = out / f"{i:02d}-{b['id']}"
            sub.mkdir(exist_ok=True)
            for k, (a_, z) in enumerate(spans, 1):
                grab((b["start"] + max(a_, b["transition"]) + (z - max(a_, b["transition"])) * 0.7) / FPS, sub / f"{k:02d}.png")
                shots += 1
    print(f"{len(tl['beats'])} frames -> {out}/" + (f", and {shots} shot frames in its beat folders" if shots else ""))
    return 0


# ------------------------------------------------------------------ the stills route (no node)
def cmd_stills(a):
    """Each beat as one composed still under an eased push, cut with crossfades; each card as a plain text card."""
    _env.need("PIL")
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    board = _env.read_json("build/film.json")
    if not board:
        sys.exit("build/film.json is missing: run storyboard.py snap first")
    s = board["system"]
    c = s["colors"]
    W, H = board["format"]["width"], board["format"]["height"]
    fonts = {k: str(_env.SKILL / s[k]["file"]) for k in ("display", "text")}

    def font(kind, size):
        return ImageFont.truetype(fonts[kind], size)

    def wrap(d, text, f, width):
        words, lines, cur = str(text).split(), [], ""
        for wd in words:
            nxt = (cur + " " + wd).strip()
            if f.getlength(nxt) <= width or not cur:
                cur = nxt
            else:
                lines.append(cur)
                cur = wd
        return lines + ([cur] if cur else [])

    def card_lines(card):
        k = card["kind"]
        if k in ("palette", "aspire"):
            return [f"{x['name']}  {x.get('label') or x['hex']}" for x in card.get("colors", [])] + [card.get("line") or ""]
        if k == "type":
            return [f"display: {card.get('display')}", f"text: {card.get('text')}", card.get("sample") or "", card.get("why") or ""]
        if k == "compositions":
            return [f"{h['name']}  {h.get('label') or ''}" for h in card.get("habits", [])]
        if k == "voice":
            return [f"{d['label']} {d['name']}" for d in card.get("devices", [])] + [x.replace("\n", " / ") for x in card.get("examples", [])]
        if k == "pillars":
            return [f"{p['name']}  {p['label']}" for p in card.get("pillars", [])]
        if k == "cadence":
            return [f"{d['day']} {d['time']}" for d in card.get("days", []) if d.get("time")] + [card.get("line") or ""]
        if k == "stop":
            return [x["line"] for x in card.get("items", [])]
        if k == "statement":
            return [card.get("statement") or "", card.get("handle") or ""]
        return [f"{d['day']} {d['date'][8:]}  {d['pillar']}: {d['caption']}" for d in card.get("days", [])]

    def draw_card(card):
        im = Image.new("RGB", (1080, 1350), c["card"])
        d = ImageDraw.Draw(im)
        d.text((80, 80), f"{card['n']:02d} / {len(board['cards'])}", font=font("text", 26), fill=c["cardAccent"])
        d.text((80, 150), card["title"], font=font("display", 90), fill=c["cardInk"])
        y = 330
        for ln in card_lines(card):
            f = font("text", 32)
            for row in wrap(d, ln, f, 920):
                if y > 1180:
                    break
                d.text((80, y), row, font=f, fill=c["cardInk"])
                y += 44
            y += 18
        for i, sw in enumerate(c["swatches"]):
            w = 920 // max(1, len(c["swatches"]))
            d.rectangle((80 + i * w, 1276, 80 + (i + 1) * w - 8, 1286), fill=sw["hex"])
        return im

    def photo(p, w, h):
        return ImageOps.fit(Image.open(PUBLIC / p).convert("RGB"), (w, h), Image.LANCZOS)

    def compose(bt):
        bg = Image.new("RGB", (W, H), c["bg"])
        ph = list(bt.get("photos") or [])
        if bt.get("clip") and isinstance(bt["clip"], dict) and bt["clip"].get("image"):
            ph = [bt["clip"]["image"]] + ph
        if ph:
            bg = Image.blend(photo(ph[0], W, H), bg, 0.75 if bt["kind"] in ("Reveal", "Swipe", "Poster") else 0.3)
        data = bt.get("data") or {}
        ns = [data["card"]] if data.get("card") else list(data.get("cards") or [])
        if ns:
            card = next(x for x in board["cards"] if x["n"] == ns[0])
            im = draw_card(card).resize((734, 918), Image.LANCZOS)
            bg.paste(im, (134, 330))
            return bg
        d = ImageDraw.Draw(bg)
        t = bt.get("text") or {}
        y = H - 670 - 300
        for key, kind, size, color in (("kicker", "text", 28, c["accent"]), ("headline", "display", 96, c["ink"]), ("line", "text", 40, c["ink"])):
            if t.get(key):
                for row in wrap(d, t[key], font(kind, size), W - 222):
                    d.text((72, y), row, font=font(kind, size), fill=color)
                    y += int(size * 1.1)
        return bg

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
        trn = max(0.1, parts[k][2])
        offset -= trn
        flt.append(f"[{last}][{k}:v]xfade=transition=fade:duration={trn:.3f}:offset={offset:.3f}[v{k}]")
        last = f"v{k}"
        offset += parts[k][1]
    silent = Path("build/film.silent.mp4")
    subprocess.run([ff, "-y", "-v", "error", *inputs, *(["-filter_complex", ";".join(flt), "-map", f"[{last}]"] if flt else []),
                    "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(silent)], check=True)
    tl = timeline(board["beats"])
    secs = (tl[-1]["start"] + tl[-1]["frames"]) / FPS
    _env.write_json("build/timeline.json", {"fps": FPS, "seconds": secs, "beats": tl})
    Path("out").mkdir(exist_ok=True)
    music = mux(silent, Path("out/film.mp4"), secs)
    shutil.rmtree(CARDS, ignore_errors=True)
    CARDS.mkdir(parents=True)
    for card in board["cards"]:
        draw_card(card).save(CARDS / f"{card['id']}.png")
    write_cards(board)
    guide = [{"job": str(CARDS / f"{x['id']}.png"), "text": "GUIDE_COLORS " + json.dumps({"card": x["id"], "names": [y["name"] for y in x.get("colors", [])]})}
             for x in board["cards"]]
    _env.write_json("build/engine.json", {"engine": "stills", "why": "node could not be installed on this machine"})
    _env.write_json("build/render-report.json", {"failed": 0, "findings": [], "guide": guide, "engine": "stills"})
    print(f"stills route: film {secs:.1f} s{' with music' if music else ''} -> out/film.mp4; {len(board['cards'])} cards -> {CARDS}/")
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
