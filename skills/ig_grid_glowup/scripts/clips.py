#!/usr/bin/env python3
"""Beside the cut: the generated clips the storyboard asks for, conformed and placed on their posts.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize [--why "..."] # conform what arrived; the rest stand in -> clips.json

The storyboard (board.json's reel board) lists the clips an image-to-video model would make, each a shot written from
the plan: the hook's world (clip 00, under the hook), a still brought to life on each post the frame holds, and the
texture between chapters on each post it passes; each names its subject, lens, height and light, the camera move its
beat makes, its seconds, and a seamless loop. list writes clips/requests.json and prints one block per clip; with a
video model the agent generates each clip from the named photograph and saves it as clips/NN.mp4 in the run (.mov,
.webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the post exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
public/clips/NN-<key>/0001.jpg onward, the key a digest of the file and its size and length; a folder gets its name only
when its frames are whole, and a folder already there is used as it is. The film shows those frames on the photograph
while the clip's beat plays. A clip that did not arrive stands in: the film makes the camera or depth move the
storyboard names for it on the still photograph. clips.json records every clip as generated or stand-in and names
the folders the film reads; the folders it does not name go after it is written, so a normalize that was stopped
leaves the clips.json before it and every folder that one names.

A post made from a clip they recorded (role "their own clip") asks nothing of a video model: list leaves it out of
the requests, and normalize conforms the recording itself as one shot the length of its beat, from the second the
board names (its strongest), in the grade of its photograph, holding its first frame for the frames the board names
(while a trailer move lands its photograph) and its last frame when the recording ends first. Frames carry no sound.
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
    b = _env.read_json("board.json")
    if not b or "boards" not in b:
        sys.exit("board.json is missing: run storyboard.py draft, sheets and pick first")
    return b["boards"]["reel"]


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
    own = [c for c in b.get("clips") or [] if c["role"] == "their own clip"]
    for c in b.get("clips") or []:
        if c in own:
            continue
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
    for c in own:
        print(f"clip {c['id']} for {c['beat']} is their own clip, {Path(c['source']).name} from {c['from']:.2f} s: nothing to make")
    print(f"{len(reqs)} clips -> clips/requests.json")
    return 0


def conform(src, image, frames, cid, start=None, hold=0):
    """The clip at the photograph's size, 30 fps, `frames` long, as one JPEG per frame in public/clips/<cid>-<key>/.
    A generated clip loops when it is short of its beat. A recording (`start` given) is read from `start` seconds in
    the grade of its photograph, opens on its first frame held for `hold` frames, and keeps its last frame when it ends
    first. Returns the frame count, ffmpeg's error, and the folder relative to public/."""
    w, h = size_of(image)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}"
    if start is None:
        head = ["-stream_loop", "-1", "-i", str(src)]
    else:
        grade = ((_env.read_json("grade.json") or {}).get("photos") or {}).get(Path(image).name)
        head = ["-ss", f"{start:.3f}", "-i", str(src), "-an"]
        vf += (f",{grade}" if grade else "") + f",tpad=start={int(hold)}:start_mode=clone:stop=-1:stop_mode=clone"
    key = hashlib.sha256(Path(src).read_bytes() + f"{w}x{h}:{frames}:{vf}".encode()).hexdigest()[:12]
    dst = PUBLIC / "clips" / f"{cid}-{key}"
    rel = f"clips/{dst.name}"
    if dst.is_dir():
        return len(list(dst.glob("*.jpg"))), "", rel
    tmp = _env.part(dst)
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", *head, "-frames:v", str(frames),
                        "-vf", vf, "-q:v", "2", str(tmp / "%04d.jpg")], capture_output=True, text=True)
    n = len(list(tmp.glob("*.jpg")))
    if r.returncode == 0 and n:
        os.replace(tmp, dst)
        return n, "", rel
    shutil.rmtree(tmp, ignore_errors=True)
    return 0, r.stderr[-300:], None


def cmd_normalize(a):
    b = board()
    win = windows(b)
    out = {}
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        own = c["role"] == "their own clip"
        src = Path(c["source"]) if own else arrived(c["id"])
        if own and not src.is_file():
            src = None
        got, err, rel = ((conform(src, c["image"], n, c["id"], c["from"], c.get("hold") or 0) if own
                          else conform(src, c["image"], n, c["id"])) if src else (0, "", None))
        if got:
            rec.update(status="recorded" if own else "generated", source=str(src), dir=rel, frames=got)
        else:
            rec.update(status="stand-in", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"{rec['status']}, {got} frames -> public/{rel}/" if got
                                                    else f"stand-in ({rec['why']}): {c['stand_in']}"))
    _env.write_json("clips.json", {"clips": out})
    named = {r["dir"] for r in out.values() if r.get("dir")}
    for d in (PUBLIC / "clips").iterdir() if (PUBLIC / "clips").is_dir() else []:
        if f"clips/{d.name}" not in named:
            shutil.rmtree(d)
    g = sum(1 for r in out.values() if r["status"] == "generated")
    o = sum(1 for r in out.values() if r["status"] == "recorded")
    print(f"clips: {g} generated, " + (f"{o} their own, " if o else "") + f"{len(out) - g - o} stand-in -> clips.json")
    return 0


def placed():
    """The clips the film shows (generated, and their own recordings), for the composition's props: where each starts
    and its frames."""
    return [{"id": k, "image": r["image"], "from": r["from_frame"], "frames": r["frames"], "dir": r["dir"]}
            for k, r in ((_env.read_json("clips.json") or {}).get("clips") or {}).items() if r.get("status") in ("generated", "recorded")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    _env.enter_run()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
