#!/usr/bin/env python3
"""Movement 5: the generated clips the winning storyboard asks for, conformed, graded and placed; and the
generated stills that stand in for a post no library photo fits.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list [--board N]       # every clip: its prompt, length, source photo, the file to save
    python3 S/scripts/clips.py normalize [--board N] [--why "..."]
                                                      # conform what arrived; substitute what did not -> build/clips.json
    python3 S/scripts/clips.py stills [--board N]     # every stand-in still of every board (or of board N): conform
                                                      # build/stills/<id>.png from the image model, else paint one
                                                      # -> build/public/stills/<id>.jpg + build/stills.json

list writes build/clips/requests.json and prints one block per clip. The agent generates each clip with its
video model (image-to-video from the named photo when the model takes an image) and saves it as
build/clips/NN.mp4 (.mov and .webm are read too). A clip whose role is "their own reel" needs no generation:
it is cut from their footage.

A stand-in still is a post of the nine that no library photo fits (storyboard.py names each one, with its prompt
and its color). The agent makes each with its image model (4:5, 1080x1350) and saves it as build/stills/<id>.png
(.jpg and .webp are read too), then runs `clips.py stills`. A still that did not arrive is painted: late light
through a window falling across a plain wall in the slot's color, with film grain, so the grid still reads as one
palette. build/stills.json records each as generated or painted, and the plan says which posts they are.

normalize scales and crops each file to 1080x1920, conforms it to 30 fps, trims it to its beat (looping a
short file), applies the film's grade (build/grade.json, the same filter as the photos) and writes
build/public/clips/NN.mp4 with no audio, plus its frames in build/public/clips/NN/. A clip that did not arrive is substituted: the renderer animates the
named photo of theirs (parallax planes, light, dust) in its place. build/clips.json records every clip as
generated, their_reel or substituted, and brief.md lists them.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import grade  # noqa: E402

CLIPS = Path("build/clips")
OUT = grade.PUBLIC / "clips"
W, H, FPS = 1080, 1920, 30


def board_for(a):
    bid = a.board or (_env.read_json("build/winner.json") or {}).get("board")
    if not bid:
        sys.exit("no winner yet: run vote.py tally first (or pass --board N)")
    b = _env.read_json(f"build/storyboards/{bid}/storyboard.json")
    if not b:
        sys.exit(f"build/storyboards/{bid}/storyboard.json is missing")
    return b


def clip_seconds(b, c):
    """A clip runs for its whole beat."""
    return max(c.get("seconds") or 0, beat_seconds(b, c["beat"]) or 0)


def size_of(c):
    return (W, H)


def beat_seconds(b, beat_id):
    for bt in b["beats"]:
        if bt["id"] == beat_id:
            return bt["frames"] / FPS
    return None


def arrived(cid):
    for ext in (".mp4", ".mov", ".webm", ".m4v"):
        p = CLIPS / f"{cid}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def cmd_list(a):
    b = board_for(a)
    CLIPS.mkdir(parents=True, exist_ok=True)
    reqs = []
    for c in b.get("clips", []):
        secs = round(clip_seconds(b, c), 1)
        w, h = size_of(c)
        r = {"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": secs, "aspect": "9:16",
             "size": f"{w}x{h}", "save_as": str((CLIPS / f"{c['id']}.mp4").resolve())}
        if c.get("source"):
            r["their_footage"] = c["source"]
        else:
            r["prompt"] = c["prompt"]
            if c.get("image"):
                r["image"] = str((grade.PUBLIC / c["image"]).resolve())
        reqs.append(r)
    _env.write_json(CLIPS / "requests.json", {"board": b["id"], "clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s, {r['aspect']} -> {r['save_as']}")
        if r.get("their_footage"):
            print(f"  no generation: cut from their reel {r['their_footage']}")
        else:
            if r.get("image"):
                print(f"  image-to-video from: {r['image']}")
            print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> build/clips/requests.json")
    return 0


def conform(src, dst, secs, filt, size=(W, H), start=0.0):
    dst.parent.mkdir(parents=True, exist_ok=True)
    w, h = size
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},{filt},format=yuv420p"
    cmd = [_env.ffmpeg(), "-y", "-v", "error", "-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", str(src), "-t", f"{secs:.3f}",
           "-vf", vf, "-an", "-c:v", "libx264", "-profile:v", "high", "-crf", "16", "-preset", "fast", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        return False, r.stderr[-400:]
    return frames(dst), ""


def frames(clip):
    """The clip as one JPEG per frame beside it (clips/01/0001.jpg ...), the form the renderer reads.

    Each frame is a plain image request that retries on its own, so a render survives the browser dropping
    requests when the machine's network interfaces change (containers starting and stopping)."""
    d = clip.with_suffix("")
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-i", str(clip), "-q:v", "2", str(d / "%04d.jpg")],
                       capture_output=True, text=True)
    n = len(list(d.glob("*.jpg")))
    return n if r.returncode == 0 and n else False


def cmd_normalize(a):
    b = board_for(a)
    g = grade.ensure_recipe()
    out = {}
    for f in OUT.glob("*.mp4") if OUT.exists() else []:
        f.unlink()
        shutil.rmtree(f.with_suffix(""), ignore_errors=True)
    for c in b.get("clips", []):
        secs = (clip_seconds(b, c) or 4) + 0.6
        rec = {"beat": c["beat"], "role": c["role"], "prompt": c.get("prompt"), "image": c.get("image"), "file": None}
        src = arrived(c["id"])
        if src:
            ok, err = conform(src, OUT / f"{c['id']}.mp4", secs, g["filter"], size_of(c))
            rec.update({"status": "generated", "from": str(src), "frames": ok} if ok else {"status": "substituted", "why": f"could not read {src.name}: {err}"})
        elif c.get("source") and Path(c["source"]).exists():
            ok, err = conform(c["source"], OUT / f"{c['id']}.mp4", secs, g["filter"], size_of(c))
            rec.update({"status": "their_reel", "from": c["source"], "frames": ok} if ok else {"status": "substituted", "why": f"could not read their reel: {err}"})
        else:
            rec.update({"status": "substituted", "why": a.why or "the video model did not produce it"})
        if rec["status"] in ("generated", "their_reel"):
            rec["file"] = f"clips/{c['id']}.mp4"
        elif not rec["image"]:
            beat = next((x for x in b["beats"] if x["id"] == c["beat"]), {})
            rec["image"] = (beat.get("photos") or [None])[0]
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): {rec['status']}" + (f", {rec.get('why')}" if rec.get("why") else "") +
              (f" -> build/public/{rec['file']}" if rec["file"] else f", animated from their photo {rec['image']}"))
    _env.write_json("build/clips.json", {"board": b["id"], "clips": out})
    n = {s: sum(1 for r in out.values() if r["status"] == s) for s in ("generated", "their_reel", "substituted")}
    print(f"clips: {n['generated']} generated, {n['their_reel']} from their reels, {n['substituted']} substituted -> build/clips.json")
    return 0


STILLS = Path("build/stills")
STILL_OUT = grade.PUBLIC / "stills"
PW, PH = 1080, 1350


def paint_still(color, seed, path):
    """Late light through a window across a plain wall in one color: a quiet frame that sits in the palette."""
    _env.need("PIL")
    import random
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    rnd = random.Random(seed)
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    W, H = PW, PH
    base = Image.new("RGB", (W, H), (r, g, b))
    shade = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(shade)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=int(70 * (y / H) ** 1.4))
    dark = Image.new("RGB", (W, H), (int(r * 0.55), int(g * 0.52), int(b * 0.5)))
    im = Image.composite(dark, base, shade)
    light = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(light)
    x0, slant = rnd.randint(-200, 120), rnd.uniform(0.35, 0.6)
    panes = [(0.0, 0.46), (0.52, 1.0)]
    for top, bot in panes:
        for k in range(2):
            ya, yb = 160 + top * 760, 160 + bot * 760
            xa = x0 + k * 330
            d.polygon([(xa, ya), (xa + 310, ya), (xa + 310 + slant * (yb - ya), yb), (xa + slant * (yb - ya), yb)], fill=255)
    light = light.filter(ImageFilter.GaussianBlur(30))
    warm = Image.new("RGB", (W, H), tuple(int(c + (w - c) * 0.42) for c, w in zip((r, g, b), (255, 238, 205))))
    im = Image.composite(warm, im, light.point(lambda v: int(v * 0.85)))
    noise = Image.effect_noise((W, H), 22).convert("RGB")
    im = ImageChops.add(ImageChops.multiply(im, Image.new("RGB", (W, H), (236, 236, 236))), ImageChops.multiply(noise, Image.new("RGB", (W, H), (20, 20, 20))))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=92)


def still_arrived(sid):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = STILLS / f"{sid}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def make_stills(stills):
    """Each stand-in as build/public/stills/<id>.jpg: the image model's file cropped to 4:5 and graded, else painted."""
    rec = (_env.read_json("build/stills.json") or {}).get("stills", {})
    g = grade.ensure_recipe()
    for st in stills:
        dst = STILL_OUT / f"{st['id']}.jpg"
        src = still_arrived(st["id"])
        if src:
            dst.parent.mkdir(parents=True, exist_ok=True)
            vf = f"scale={PW}:{PH}:force_original_aspect_ratio=increase,crop={PW}:{PH},{g['filter']}"
            r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-i", str(src), "-vf", vf, "-q:v", "2", str(dst)], capture_output=True, text=True)
            if r.returncode == 0:
                rec[st["id"]] = {"n": st["n"], "status": "generated", "from": str(src), "prompt": st["prompt"], "file": f"stills/{st['id']}.jpg"}
                continue
        paint_still(st["color"], st["id"], dst)
        rec[st["id"]] = {"n": st["n"], "status": "painted", "color": st["color"], "prompt": st["prompt"], "file": f"stills/{st['id']}.jpg",
                         "why": "no image model file at build/stills/" + st["id"] + ".png"}
    _env.write_json("build/stills.json", {"stills": rec})
    return rec


def cmd_stills(a):
    boards = [board_for(a)] if a.board else [_env.read_json(f) for f in sorted(Path("build/storyboards").glob("*/storyboard.json"))]
    todo = [st for b in boards for st in b.get("stills", [])]
    for st in todo:
        print(f"still {st['id']} (post {st['n']}), 4:5 1080x1350 -> save as {(STILLS / (st['id'] + '.png')).resolve()}")
        print(f"  prompt: {st['prompt']}")
    rec = make_stills(todo)
    n = {s: sum(1 for st in todo if rec[st["id"]]["status"] == s) for s in ("generated", "painted")}
    print(f"stills: {n['generated']} generated, {n['painted']} painted in their palette -> build/public/stills/, build/stills.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize", "stills"])
    ap.add_argument("--board")
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    return {"list": cmd_list, "normalize": cmd_normalize, "stills": cmd_stills}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
