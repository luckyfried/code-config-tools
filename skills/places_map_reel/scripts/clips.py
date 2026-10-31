#!/usr/bin/env python3
"""Movement 4, beside the cut: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/clips.py list                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize [--why "..."] # conform what arrived; the rest stand in -> clips.json

The storyboard (film.json's reel board) lists the clips an image-to-video model would make, one shot per stop: the
hook's world on the first, the texture between chapters where the trip leaps, and each other photograph brought to
life while its place holds. list writes clips/requests.json, each request one prompt written as a shot (the subject and
its light, or for a texture the place's material and its light, the camera move the beat's own move calls for, in camera words, or the one its photograph's line and focus call
for, the lens and height, the beat's seconds, a seamless loop), and prints one block per clip;
the agent generates each clip from the named photograph with its video model and saves it as clips/NN.mp4 in the run
(.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
public/clips/<normalize>/NN/0001.jpg onward, in a folder of that normalize's own. The film shows those frames on the
photograph's card while the clip's beat plays. A clip that did not arrive stands in: the film makes the camera or depth
move the storyboard names for it on the still photograph. clips.json records every clip as generated or stand-in, and
brief.md lists them.

A stop whose photograph in the cast is a clip they recorded (a video file in cast.json or in their set) needs nothing
generated: grade.py makes its photograph from the clip's strongest second (strongest()), the storyboard names the clip
as `their own clip` with its `source` and the second it plays `from`, list asks for nothing, and normalize conforms it
from that second for its beat's length, without its sound, as status `recorded`. It plays on the photograph's card,
so it arrives and moves as the photograph would have.
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
# the strongest second is read from the clip's frames at this rate and size, gray
READ_FPS, READ_W, READ_H = 10, 32, 32


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


def duration(src):
    """A clip's length in seconds (0.0 when it cannot be read)."""
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def strongest(src):
    """The second of a clip that moves most: the start of the whole second whose frames differ most from the frame before."""
    r = subprocess.run([_env.ffmpeg(), "-v", "error", "-i", str(src), "-an", "-vf",
                        f"fps={READ_FPS},scale={READ_W}:{READ_H},format=gray", "-f", "rawvideo", "-"], capture_output=True)
    n = READ_W * READ_H
    frames = [r.stdout[i:i + n] for i in range(0, len(r.stdout) - n + 1, n)]
    per = {}
    for k in range(1, len(frames)):
        moved = sum(abs(a - b) for a, b in zip(frames[k], frames[k - 1]))
        per[k // READ_FPS] = per.get(k // READ_FPS, 0) + moved
    return float(max(per, key=lambda s: (per[s], -s))) if per else 0.0


def recorded(src):
    """What grade.py records for a shot that is a clip they recorded: the clip, its strongest second and its length;
    {} for a photograph."""
    src = Path(src)
    if src.suffix.lower() not in EXTS:
        return {}
    return {"clip": str(src.resolve()), "clip_from": strongest(src), "clip_seconds": round(duration(src), 3)}


def frame_at(src, sec, dst):
    """The clip's frame at `sec` as a JPEG at `dst`."""
    subprocess.run([_env.ffmpeg(), "-y", "-v", "error", "-ss", f"{sec:.3f}", "-i", str(src), "-frames:v", "1", "-q:v", "2",
                    str(dst)], check=True, capture_output=True)
    return dst


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
    own = [c for c in b.get("clips") or [] if c.get("source")]
    for c in own:
        print(f"clip {c['id']} for {c['beat']}: their own recording, {c['seconds']} s from {c['from']:g} s of {c['source']}; nothing to generate")
    for c in b.get("clips") or []:
        if c.get("source"):
            continue
        w, h = size_of(c["image"])
        secs = round(max(c.get("seconds") or 0, win[c["beat"]][1] / FPS), 1)
        reqs.append({"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": secs, "size": f"{w}x{h}",
                     "image": str((PUBLIC / c["image"]).resolve()), "subject": c["subject"], "camera": c["camera"], "move": c["move"],
                     "prompt": prompt_of(c, secs), "save_as": str((CLIPS / f"{c['id']}.mp4").resolve()), "stand_in": c["stand_in"]})
    _env.write_json(CLIPS / "requests.json", {"clips": reqs})
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s at {r['size']} -> {r['save_as']}")
        print(f"  image-to-video from: {r['image']}")
        print(f"  prompt: {r['prompt']}")
    unread = [c["id"] for c in b.get("clips") or [] if not c.get("read") and not c.get("source")]
    if unread:
        print(f"clips {', '.join(unread)} have no `about` (`texture` for the texture between chapters) or `camera` in cast.json: their "
              "prompts name the place and the photograph's own light and lens; write them on the stop's first shot and run "
              "storyboard.py draft for a shot written from the photograph")
    print(f"{len(reqs)} clips -> clips/requests.json")
    return 0


def prompt_of(c, secs):
    """One clip's prompt, as a cinematographer writes a shot: the subject and its light, the camera's move, the lens and
    height, its length, and a loop that ends where it began (normalize loops every clip). Every sentence but the last is
    this shot's own; what the shot is for stays in the request's `role`, never a sentence pasted into each prompt."""
    return (f"{c['subject'][0].upper() + c['subject'][1:]}. {c['move'][0].upper() + c['move'][1:]}; {c['camera']}. "
            f"{secs:g} second{'' if secs == 1 else 's'}, a seamless loop that ends on its first frame, no text on screen.")


def conform(src, image, frames, dst, start=None):
    """The clip at the photograph's size, 30 fps, `frames` long, as one JPEG per frame in `dst`: a generated clip looped
    from its first frame; with `start`, a recorded one played once from that second, holding its last frame if it ends
    first."""
    w, h = size_of(image)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}"
    if start is None:
        head = ["-stream_loop", "-1", "-i", str(src)]
    else:
        head, vf = ["-ss", f"{start:.3f}", "-i", str(src)], vf + ",tpad=stop_mode=clone:stop=-1"
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", *head, "-an", "-frames:v", str(frames),
                        "-vf", vf, "-q:v", "2", str(dst / "%04d.jpg")], capture_output=True, text=True)
    n = len(list(dst.glob("*.jpg")))
    return (n, "") if r.returncode == 0 and n else (0, r.stderr[-300:])


def cmd_normalize(a):
    b = board()
    win = windows(b)
    out = {}
    # clips.json names the frames the film shows, so this normalize writes its frames under a folder of its own, then
    # clips.json, and only then removes the folders before it
    tag = f"{time.time_ns():x}"
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "from_frame": at}
        own = c.get("source")
        src = Path(own) if own and Path(own).is_file() else None if own else arrived(c["id"])
        got, err = conform(src, c["image"], n, PUBLIC / "clips" / tag / c["id"], c.get("from") if own else None) if src else (0, "")
        if got:
            rec.update(status="recorded" if own else "generated", source=str(src), dir=f"clips/{tag}/{c['id']}", frames=got)
        elif own:
            rec.update(status="stand-in", stand_in="the photograph made from the clip holds its place",
                       why=f"could not read {Path(own).name}: {err}" if src else f"{own} is not there")
        else:
            rec.update(status="stand-in", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"{rec['status']}, {got} frames -> public/clips/{tag}/{c['id']}/" if got
                                                    else f"stand-in ({rec['why']}): {c['stand_in']}"))
    _env.write_json("clips.json", {"clips": out})
    for old in (PUBLIC / "clips").glob("*"):
        if old.name != tag:
            shutil.rmtree(old) if old.is_dir() else old.unlink()
    g = sum(1 for r in out.values() if r["status"] == "generated")
    o = sum(1 for r in out.values() if r["status"] == "recorded")
    print(f"clips: {g} generated, {o} their own, {len(out) - g - o} stand-in -> clips.json")
    return 0


def placed():
    """The clips the film shows, generated and their own, for the composition's props: where each starts and its frames."""
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
