#!/usr/bin/env python3
"""Movement 4, beside the cut: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/clips.py list                    # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize [--why "..."] # conform what arrived -> RUN/clips.json (film.py render runs it too)

The storyboard (RUN/film.json's board) lists the six shots an image-to-video model would make, each written the way a
cinematographer asks for one (subject, lens, light, camera move, length and a seamless loop): the hook's world (day
one's place, alive), the stills brought to life (the first milestone, the peak and the latest), and the texture
between chapters (the two busiest ordinary posts). film.py draft writes them to RUN/clips/requests.json; list writes
the same file and prints one block per clip; the agent generates each clip from the named photograph with its video
model and saves it as RUN/clips/<id>.mp4 (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's own size, so the film maps it onto the card exactly where
the photograph was, conforms it to 30 fps, trims it to its beat (looping a short file) and writes its frames as
RUN/public/clips/<normalize stamp>/<id>/0001.jpg onward, the folder clips.json names; the folders of earlier
normalizes go once clips.json names the new one. The film shows those frames on the photograph's card while the clip's beat plays.
Where no clip arrived, the photograph itself plays the beat, with the camera or depth move the storyboard names for it;
that is a still photograph, never called a clip. clips.json records each request as generated or as the photograph,
with why, and brief.md lists them. film.py render runs normalize first, so every clip saved before the render is in
the film.
"""
import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

FPS = 30
EXTS = (".mp4", ".mov", ".webm", ".m4v")


def board():
    import storyboard
    f = _env.read_json(_env.b("film.json"))
    if not f:
        sys.exit("RUN/film.json is missing: run storyboard.py snap first")
    return storyboard.lay_out(f["board"])


def windows(b):
    """Each beat's first frame and length in frames."""
    at, out = 0, {}
    for bt in b["beats"]:
        out[bt["id"]] = (at, bt["frames"])
        at += bt["frames"]
    return out


def arrived(cid):
    for ext in EXTS:
        p = _env.b("clips", f"{cid}{ext}")
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def size_of(image):
    r = subprocess.run([_env.ffprobe(), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(_env.b("public", image))], capture_output=True, text=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w - w % 2, h - h % 2


def write_requests(b):
    """RUN/clips/requests.json: every shot the board `b` asks for, at its photograph's size, as long as its beat (the
    seconds its prompt says), with the file to save it as. Returns the requests."""
    _env.b("clips").mkdir(parents=True, exist_ok=True)
    reqs = []
    for c in b.get("clips") or []:
        w, h = size_of(c["image"])
        reqs.append({"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": c["seconds"], "size": f"{w}x{h}",
                     "image": str(_env.b("public", c["image"]).resolve()), "lens": c["lens"], "light": c["light"], "move": c["move"],
                     "loop": c["loop"], "prompt": c["prompt"], "save_as": str(_env.b("clips", f"{c['id']}.mp4").resolve()), "stand_in": c["stand_in"]})
    _env.write_json(_env.b("clips", "requests.json"), {"clips": reqs})
    return reqs


def cmd_list(a):
    reqs = write_requests(board())
    for r in reqs:
        print(f"clip {r['id']} for {r['beat']} ({r['role']}), {r['seconds']} s at {r['size']} -> {r['save_as']}")
        print(f"  image-to-video from: {r['image']}")
        print(f"  prompt: {r['prompt']}")
    print(f"{len(reqs)} clips -> {_env.b('clips', 'requests.json')}")
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


def normalize(b, why=None):
    """Conform every clip the board `b` asks for that arrived, record the rest as their photographs, write
    RUN/clips.json, and return the number generated."""
    win = windows(b)
    out = {}
    # the frames go to a folder of this normalize's own; once clips.json names it, every folder it does not name goes,
    # so clips.json never names a folder that is gone or half made
    fresh = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    for c in b.get("clips") or []:
        at, n = win[c["beat"]]
        rec = {"beat": c["beat"], "role": c["role"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        src = arrived(c["id"])
        got, err = conform(src, c["image"], n, _env.b("public", "clips", fresh, c["id"])) if src else (0, "")
        if got:
            rec.update(status="generated", source=str(src), dir=f"clips/{fresh}/{c['id']}", frames=got)
        else:
            rec.update(status="photograph", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (why or f"no file at clips/{c['id']}.mp4"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"generated, {got} frames -> public/clips/{fresh}/{c['id']}/" if got
                                                    else f"none ({rec['why']}); the photograph plays the beat: {c['stand_in']}"))
    _env.write_json(_env.b("clips.json"), {"clips": out})
    for old in _env.b("public", "clips").glob("*"):
        if old.name != fresh:
            shutil.rmtree(old, ignore_errors=True)
    g = sum(1 for r in out.values() if r["status"] == "generated")
    print(f"clips: {g} of {len(out)} generated; the other beats play their photographs -> {_env.b('clips.json')}")
    return g


def cmd_normalize(a):
    normalize(board(), a.why)
    return 0


def placed():
    """The generated clips the film shows, for the composition's props: where each starts and its frames."""
    return [{"id": k, "image": r["image"], "from": r["from_frame"], "frames": r["frames"], "dir": r["dir"]}
            for k, r in ((_env.read_json(_env.b("clips.json")) or {}).get("clips") or {}).items() if r.get("status") == "generated"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    _env.open_run()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
