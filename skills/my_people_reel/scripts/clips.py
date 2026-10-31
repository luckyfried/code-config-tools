#!/usr/bin/env python3
"""Movement 4, beside the cut: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list --run R                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize --run R [--why "..."] # conform what arrived; the rest stand in -> clips.json

The reel's board (render/board-reel.json, laid out by film.py cut) lists the clips an image-to-video model would make:
the group photograph swaying under the hook and each person's photograph brought to life under their beat, each lit
in the words its own photograph's light measures (board_drive.light_of). list writes
clips/requests.json and prints one block per clip; the agent generates each clip from the named photograph with its
video model and saves it as clips/NN.mp4 in the run (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
public/clips/NN-<digest>/0001.jpg onward. The film shows those frames on the photograph's card while the clip's beat plays. A
clip that did not arrive stands in: the film makes the camera or depth move the storyboard names for it on the
still photograph. clips.json records every clip as generated or stand-in, and brief.md lists them.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

CLIPS = Path("clips")
PUBLIC = Path("public")
FPS = 30
EXTS = (".mp4", ".mov", ".webm", ".m4v")


def board():
    b = _env.read_json("render/board-reel.json")
    if not b:
        sys.exit("render/board-reel.json is missing: run film.py cut first")
    return b


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
                     "image": str((PUBLIC / c["image"]).resolve()), "prompt": c["prompt"],
                     "save_as": str((CLIPS / f"{c['id']}.mp4").resolve()), "stand_in": c["stand_in"]})
    _env.write_json(CLIPS / "requests.json", {"clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s at {r['size']} -> {r['save_as']}")
        print(f"  image-to-video from: {r['image']}")
        print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> clips/requests.json")
    return 0


def conform(cid, src, image, frames):
    """The clip at the photograph's size, 30 fps, `frames` long, as one JPEG per frame in public/clips/<id>-<digest>/,
    the digest naming the file and the conform; returns (frames, error, folder). The folder is made under its part
    name and moved in whole, so a folder of that name is always finished and is kept."""
    w, h = size_of(image)
    name = f"{cid}-{hashlib.sha256(Path(src).read_bytes() + f'|{frames}|{w}x{h}|{FPS}'.encode()).hexdigest()[:12]}"
    dst = PUBLIC / "clips" / name
    if dst.exists():
        return len(list(dst.glob("*.jpg"))), "", name
    tmp = _env.part(dst)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}"
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-frames:v", str(frames),
                        "-vf", vf, "-q:v", "2", str(tmp / "%04d.jpg")], capture_output=True, text=True)
    n = len(list(tmp.glob("*.jpg")))
    if r.returncode or not n:
        shutil.rmtree(tmp, ignore_errors=True)
        return 0, r.stderr[-300:], None
    os.replace(tmp, dst)
    return n, "", name


def cmd_normalize(a):
    b = board()
    win = windows(b)
    out = {}
    # clips.json names the folders the film shows: the new ones are made beside the old under new names, clips.json
    # is written, and only then do the folders it no longer names go
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        src = arrived(c["id"])
        got, err, name = conform(c["id"], src, c["image"], n) if src else (0, "", None)
        if got:
            rec.update(status="generated", source=str(src), dir=f"clips/{name}", frames=got)
        else:
            rec.update(status="stand-in", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"generated, {got} frames -> public/{rec['dir']}/" if got
                                                    else f"stand-in ({rec['why']}): {c['stand_in']}"))
    _env.write_json("clips.json", {"clips": out})
    named = {Path(r["dir"]).name for r in out.values() if r.get("dir")}
    for old in sorted((PUBLIC / "clips").iterdir()) if (PUBLIC / "clips").exists() else []:
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
    a = ap.parse_args()
    _env.enter_run()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
