#!/usr/bin/env python3
"""Movement 5, beside the cut: the clips the storyboard asks for, conformed and placed on their photographs' cards.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/clips.py list                  # every clip: its prompt, length, photograph, the file to save
    python3 S/scripts/clips.py normalize [--why ...] # conform what arrived and their own clips; the rest stand in -> clips.json

The storyboard (film.json) lists one clip per photograph, over the stretch the camera walks it (the hook's world on
the first, the photograph brought to life on the rest, an image-to-video model's clip), or, where the stop is shown by a
clip they shot on the trip, that clip (its role is "their own clip" and it needs no generation); and one texture
between chapters, played on the print the longest leg leaves while that leg is drawn. Each clip's `window` is the
beats it plays over. list writes clips/requests.json and prints one block per
clip; the agent generates each clip from the named photograph with its video model and saves it as clips/NN.mp4 in
the run (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its stretch (looping a short file) and writes its frames as
public/clips/NN-<digest>/0001.jpg onward, graded and matched like the photograph it plays on. The film shows those frames on the
photograph's card while the camera is on it. A clip that did not arrive stands in: the film walks the still photograph instead, the move
the storyboard names for it. clips.json records every clip as generated, their_reel (cut from their own clip) or
stand-in, and brief.md lists them.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import grade  # noqa: E402

CLIPS = Path("clips")
PUBLIC = Path("public")
FPS = 30
EXTS = (".mp4", ".mov", ".webm", ".m4v")


def film():
    f = _env.read_json("film.json")
    if not f:
        sys.exit("film.json is missing: run storyboard.py snap first")
    return f


def window(f, c):
    """The frames a clip plays over: its `window`, in beats from the film's start, at the film's tempo."""
    b0, b1 = c["window"]
    pulse = FPS * 60 / f["bpm"]
    a = round(max(0.0, b0) * pulse)
    return a, round(b1 * pulse) - a


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
    f = film()
    CLIPS.mkdir(exist_ok=True)
    reqs = []
    for c in f.get("clips") or []:
        w, h = size_of(c["image"])
        _, n = window(f, c)
        r = {"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": round(max(c.get("seconds") or 0, n / FPS), 1),
             "size": f"{w}x{h}", "save_as": str((CLIPS / f"{c['id']}.mp4").resolve())}
        if c.get("source"):
            r["their_footage"] = c["source"]
        else:
            r.update(image=str((PUBLIC / c["image"]).resolve()), prompt=c["prompt"], stand_in=c["stand_in"])
        reqs.append(r)
    _env.write_json(CLIPS / "requests.json", {"clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s at {r['size']} -> {r['save_as']}")
        if r.get("their_footage"):
            print(f"  no generation: cut from their own clip {r['their_footage']}")
        else:
            print(f"  image-to-video from: {r['image']}")
            print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> clips/requests.json")
    return 0


def conform(cid, src, image, frames, filt):
    """The clip at the photograph's size, 30 fps, `frames` long, graded, and matched the way its photograph was
    (grade.py match), as one JPEG per frame in a folder of public/clips/ named by the clip and a digest of what its
    frames are made from. The folder is made under a temporary
    name and moved in whole, so a folder at its name is complete, and the same clip normalized again keeps it.
    Returns the folder, its frame count and ffmpeg's error."""
    w, h = size_of(image)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS},{filt}"
    op = grade.match_of(image)
    digest = hashlib.sha256(Path(src).read_bytes() + json.dumps([vf, frames, op]).encode()).hexdigest()[:12]
    dst = PUBLIC / "clips" / f"{cid}-{digest}"
    if not dst.exists():
        tmp = dst.with_name(f".{dst.name}.part")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-frames:v", str(frames),
                            "-vf", vf, "-q:v", "2", str(tmp / "%04d.jpg")], capture_output=True, text=True)
        if r.returncode or not any(tmp.glob("*.jpg")):
            shutil.rmtree(tmp, ignore_errors=True)
            return None, 0, r.stderr[-300:]
        if op:
            from PIL import Image
            for f in tmp.glob("*.jpg"):
                grade.apply_match(Image.open(f), op).save(f, quality=94)
        os.replace(tmp, dst)
    return dst, len(list(dst.glob("*.jpg"))), ""


def cmd_normalize(a):
    """clips.json names the folders the film reads: the new folders are made first, then clips.json, and only then do
    the folders it no longer names go, so a normalize stopped at any point leaves clips.json naming whole folders."""
    f = film()
    g = grade.ensure_recipe()
    out = {}
    for c in f.get("clips") or []:
        at, n = window(f, c)
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "prompt": c.get("prompt"), "from_frame": at}
        src = arrived(c["id"])
        theirs = c.get("source") and Path(c["source"]).exists()
        dst, got, err = (conform(c["id"], src or c["source"], c["image"], n, g["filter"]) if src or theirs else (None, 0, ""))
        if got:
            rec.update(status="generated" if src else "their_reel", source=str(src or c["source"]),
                       dir=dst.relative_to(PUBLIC).as_posix(), frames=got)
        else:
            rec.update(status="stand-in", stand_in=c.get("stand_in") or "the camera walks their still photograph",
                       why=f"could not read {Path(src or c['source']).name}: {err}" if src or theirs else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"{rec['status']}, {got} frames -> public/{rec['dir']}/" if got
                                                    else f"stand-in ({rec['why']}): {rec['stand_in']}"))
    _env.write_json("clips.json", {"clips": out})
    kept = {r["dir"] for r in out.values() if r.get("dir")}
    for old in (PUBLIC / "clips").glob("*") if (PUBLIC / "clips").is_dir() else ():
        if old.relative_to(PUBLIC).as_posix() not in kept:
            shutil.rmtree(old, ignore_errors=True)
    n = {s: sum(1 for r in out.values() if r["status"] == s) for s in ("generated", "their_reel", "stand-in")}
    print(f"clips: {n['generated']} generated, {n['their_reel']} from their own clips, {n['stand-in']} stand-in -> clips.json")
    return 0


def placed():
    """The clips the film shows, for the composition's props: the photograph each plays on, where it starts, its frames."""
    return [{"id": k, "image": r["image"], "from": r["from_frame"], "frames": r["frames"], "dir": r["dir"]}
            for k, r in ((_env.read_json("clips.json") or {}).get("clips") or {}).items() if r.get("status") in ("generated", "their_reel")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    _env.enter_run()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
