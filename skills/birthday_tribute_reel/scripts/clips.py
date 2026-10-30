#!/usr/bin/env python3
"""Movement 4, beside the cut: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize [--why "..."] # conform what arrived; record the rest as not made -> B/clips.json

The storyboard (B/film.json, laid out for the reel) lists the clips an image-to-video model would make, one for each
use a generated shot has: the hook's world, texture between chapters and a still brought to life. Each request is in
the shape motion/system/standards.md gives one: its use, its subject and what moves in it (the beat's "shot", as the
agent saw the photograph), the camera's move, the lens feel and the camera's height, the light, its duration and a
seamless loop, with the part of the photograph its card's frame shows, and its prompt says all of it. list writes
B/clips/requests.json and prints one block per clip; the agent generates each clip from the named photograph with its
video model and saves it as B/clips/NN.mp4 (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
B/public/clips/<stamp>/NN/0001.jpg onward. The film shows those frames on the photograph's card while the clip's beat plays. A
clip that did not arrive is not made: the film shows the still photograph on its card, moved as every card is, and
nothing calls it a clip. B/clips.json records every clip as generated or not made, and brief.md lists them. Each normalize
writes its frames into a folder of its own, B/public/clips/<stamp>/NN/, then clips.json names them, and only then do the
folders of earlier normalizes go, so clips.json always names frames that are whole.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

FPS = 30
EXTS = (".mp4", ".mov", ".webm", ".m4v")
# what a request names beside its prompt: the shot as the agent saw it and as the board measured it
SHOT = ("subject", "move", "lens", "light", "loop", "frame")


def board():
    import compose
    f = _env.read_json(f"{_env.B}/film.json")
    if not f:
        sys.exit(f"{_env.B}/film.json is missing: run storyboard.py snap first")
    return compose.lay(f, "reel", f["bpm"])


def windows(b):
    """Each beat's first frame and length in frames."""
    at, out = 0, {}
    for bt in b["beats"]:
        out[bt["id"]] = (at, bt["frames"])
        at += bt["frames"]
    return out


def arrived(cid):
    for ext in EXTS:
        p = (Path(_env.B) / "clips") / f"{cid}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def size_of(image):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str((Path(_env.B) / "public") / image)], capture_output=True, text=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w - w % 2, h - h % 2


def cmd_list(a):
    b = board()
    win = windows(b)
    (Path(_env.B) / "clips").mkdir(exist_ok=True)
    reqs = []
    for c in b.get("clips") or []:
        w, h = size_of(c["image"])
        secs = round(max(c.get("duration") or 0, win[c["beat"]][1] / FPS), 1)
        reqs.append({"id": c["id"], "beat": c["beat"], "use": c["use"], "duration": secs, "size": f"{w}x{h}",
                     **{k: c[k] for k in SHOT if k in c},
                     "image": str(((Path(_env.B) / "public") / c["image"]).resolve()), "prompt": c["prompt"],
                     "save_as": str(((Path(_env.B) / "clips") / f"{c['id']}.mp4").resolve())})
    _env.write_json((Path(_env.B) / "clips") / "requests.json", {"clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['use']}), {r['duration']} s at {r['size']} -> {r['save_as']}")
        print(f"  image-to-video from: {r['image']}")
        print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> {_env.B}/clips/requests.json")
    return 0


def conform(src, image, frames, dst):
    """The clip at the photograph's size, 30 fps, `frames` long, as one JPEG per frame in `dst`."""
    w, h = size_of(image)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}"
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-frames:v", str(frames),
                        "-vf", vf, "-q:v", "2", str(dst / "%04d.jpg")], capture_output=True, text=True)
    n = len(list(dst.glob("*.jpg")))
    return (n, "") if r.returncode == 0 and n else (0, r.stderr[-300:])


def cmd_normalize(a):
    import datetime
    import os
    b = board()
    win = windows(b)
    out = {}
    root = Path(_env.B) / "public" / "clips"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + f"-{os.getpid()}"
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "use": c["use"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        src = arrived(c["id"])
        got, err = conform(src, c["image"], n, root / stamp / c["id"]) if src else (0, "")
        if got:
            rec.update(status="generated", source=str(src), dir=f"clips/{stamp}/{c['id']}", frames=got)
        else:
            rec.update(status="not made",
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"generated, {got} frames -> public/clips/{stamp}/{c['id']}/" if got
                                                    else f"not made ({rec['why']}); the film shows the photograph still"))
    _env.write_json(f"{_env.B}/clips.json", {"clips": out})
    for old in root.iterdir() if root.exists() else ():
        if old.name != stamp:
            shutil.rmtree(old)
    g = sum(1 for r in out.values() if r["status"] == "generated")
    print(f"clips: {g} generated, {len(out) - g} not made -> {_env.B}/clips.json")
    return 0


def placed():
    """The generated clips the film shows, for the composition's props: where each starts and its frames."""
    return [{"id": k, "image": r["image"], "from": r["from_frame"], "frames": r["frames"], "dir": r["dir"]}
            for k, r in ((_env.read_json(f"{_env.B}/clips.json") or {}).get("clips") or {}).items() if r.get("status") == "generated"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
