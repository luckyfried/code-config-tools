#!/usr/bin/env python3
"""Movement 4, beside the cut: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list --run R                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize --run R [--why "..."] # conform what arrived; the rest stand in -> clips.json

The storyboard (film.json's reel board) lists the clips an image-to-video model would make: the wall's world under
the hook, each photograph brought to life under its moment beat, the texture under the ribbon. list writes
clips/requests.json and prints one block per clip, each prompt ending with its beat's length and asking for a
seamless loop, since normalize loops a short file; the agent generates each clip from the named photograph with its
video model and saves it as clips/NN.mp4 in the run (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
public/clips/NN.TAG/0001.jpg onward, in a folder named for that normalize. The film shows those frames on the
photograph's card while the clip's beat plays. A clip that did not arrive stands in: the film makes the camera or
depth move the storyboard names for it on the still photograph. clips.json records every clip as generated or
stand-in, and brief.md lists them.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CLIPS = Path("clips")
PUBLIC = Path("public")
FPS = 30
EXTS = (".mp4", ".mov", ".webm", ".m4v")


def board():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return _env.read_json(f["boards"]["reel"])


def windows(b):
    """Each beat's first frame and length in frames."""
    at, out = 0, {}
    for bt in b["beats"]:
        out[bt["id"]] = (at, bt["frames"])
        at += bt["frames"]
    return out


def arrived(cid):
    for ext in EXTS:
        p = CLIPS / f"{cid}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def size_of(image):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(PUBLIC / image)], capture_output=True, text=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w - w % 2, h - h % 2


def cmd_list(a):
    b = board()
    win = windows(b)
    CLIPS.mkdir(exist_ok=True)
    reqs = []
    for c in b.get("clips") or []:
        w, h = size_of(c["image"])
        secs = round(max(c.get("seconds") or 0, win[c["beat"]][1] / FPS), 1)
        reqs.append({"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": secs, "size": f"{w}x{h}",
                     "image": str((PUBLIC / c["image"]).resolve()), "prompt": f"{c['prompt']}, {secs:g} seconds, a seamless loop that ends on its first frame",
                     "save_as": str((CLIPS / f"{c['id']}.mp4").resolve()), "stand_in": c["stand_in"]})
    _env.write_json(CLIPS / "requests.json", {"clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s at {r['size']} -> {r['save_as']}")
        print(f"  image-to-video from: {r['image']}")
        print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> clips/requests.json")
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
    b = board()
    win = windows(b)
    out = {}
    # the frames go into folders of this normalize's own, clips.json moves in naming them, and only then do the folders
    # it no longer names go, so clips.json never names a folder that is missing or half written
    tag = f"{time.time_ns():x}"
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        src = arrived(c["id"])
        name = f"{c['id']}.{tag}"
        got, err = conform(src, c["image"], n, PUBLIC / "clips" / name) if src else (0, "")
        if got:
            rec.update(status="generated", source=str(src), dir=f"clips/{name}", frames=got)
        else:
            rec.update(status="stand-in", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"generated, {got} frames -> public/clips/{name}/" if got
                                                    else f"stand-in ({rec['why']}): {c['stand_in']}"))
    _env.write_json("clips.json", {"clips": out})
    named = {Path(r["dir"]).name for r in out.values() if r.get("dir")}
    for old in (PUBLIC / "clips").glob("*"):
        if old.name not in named:
            shutil.rmtree(old, ignore_errors=True)
    g = sum(1 for r in out.values() if r["status"] == "generated")
    print(f"clips: {g} generated, {len(out) - g} stand-in -> clips.json")
    return 0


def placed():
    """The generated clips the film shows, for the composition's props: where each starts and its frames."""
    return [{"id": k, "image": r["image"], "from": r["from_frame"], "frames": r["frames"], "dir": r["dir"]}
            for k, r in ((_env.read_json("clips.json") or {}).get("clips") or {}).items() if r.get("status") == "generated"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
