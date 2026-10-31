#!/usr/bin/env python3
"""Movement 4, beside the render: the generated clips the storyboard asks for, conformed and placed on their cards.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list                       # every clip: its prompt, length, photo, the file to save
    python3 S/scripts/clips.py normalize [--why "..."]    # conform what arrived; the rest stand in -> clips.json

The winning look's storyboard (winner.json `board`, its storyboard.json `reel.clips`) lists the clips an image-to-video model would
make, each the shot the agent wrote for its photograph in taste.json (`moments[].shot`): its subject, the camera's
move, the lens, the camera's height and the light, in the vertical 1080x1920 frame, as long as its window of the film
(`at`, beats) and a seamless loop. The first is the hook's world (`use` hook), the others a still brought to life
(`use` still), and between two chapters a texture shot from the outgoing photograph's light (`use` texture). list
writes clips/requests.json and prints one block per clip; the agent generates each clip from the named photograph with
its video model and saves it as clips/NN.mp4 in the run (.mov, .webm and .m4v are read too).

normalize scales and crops each file to its photograph's size as the film stages it, so the film maps it onto the
card exactly where the photograph was, conforms it to 30 fps, trims it to its window (looping a short file) and writes
its frames as clips/frames-<stamp>/NN/0001.jpg onward, a folder of its own that clips.json names once every clip is
conformed, and every render copies the folder clips.json names into its public folder. The film shows those
frames on the photograph's card while the clip's window plays. A clip that did not arrive stands in: the film plays
the layered move the storyboard names for it on the still photograph. A moment the person recorded plays their own
clip (`use` their own clip, its `source` the recording): list asks for nothing, and normalize trims the recording from
its strongest second (the second whose samples move most and are sharpest, `strongest`) to its window, holding its
last frame when it runs short, with no sound. clips.json records every clip as generated, their own clip, or stand-in,
and brief.md lists them.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import film  # noqa: E402
from compose import photos  # noqa: E402

FPS = 30
# the film's frame, which every clip is asked for in
W, H = 1080, 1920
# what a shot names, as the agent wrote it for its photograph
SHOT = ("subject", "move", "lens", "height", "light")
EXTS = (".mp4", ".mov", ".webm", ".m4v")
# the clip a person recorded, which plays as it is (compose/reel.py `OWN`)
OWN = "their own clip"
# how a recording is read for its strongest second: samples a second, each SAMPLE px wide in grey, and the share of a
# sample's score its motion gives (the rest its sharpness)
RATE, SAMPLE, MOTION = 6, 48, 0.6


def reel(run):
    """The reel of the look that won the vote."""
    b = film.board_of(run)
    if not b.get("reel"):
        sys.exit(f"the {film.won(run)} storyboard has no reel: run storyboard.py draft first")
    return b["reel"]


def windows(r):
    """{clip id: (first frame, frames)} of every clip's window of the film."""
    f = lambda beat: round(beat * r["fps"] * 60 / r["bpm"])
    return {c["id"]: (f(c["at"][0]), f(c["at"][1]) - f(c["at"][0])) for c in r.get("clips") or []}


def arrived(run, cid):
    for ext in EXTS:
        p = run / "clips" / f"{cid}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def size_of(card):
    """The photograph's size as studio.public stages it (photos.LONG on its long side at most), even on both sides."""
    w, h = card["size"]
    k = min(1.0, photos.LONG / max(w, h))
    w, h = round(w * k), round(h * k)
    return w - w % 2, h - h % 2


def cards_of(r):
    return {c["key"]: c for c in r["cards"]}


def cmd_list(a):
    run = _env.run()
    r = reel(run)
    cards = cards_of(r)
    (run / "clips").mkdir(exist_ok=True)
    reqs = []
    for c in r.get("clips") or []:
        card = cards[c["beat"]]
        if c["use"] == OWN:
            print(f"clip {c['id']} for {c['beat']}: their own clip, {c['source']}, {c['seconds']} s from its strongest second; nothing to make")
            continue
        reqs.append({"id": c["id"], "beat": c["beat"], "use": c["use"], **{k: c[k] for k in SHOT},
                     "seconds": c["seconds"], "loop": c["loop"],
                     "size": f"{W}x{H}", "image": card["source"], "prompt": c["prompt"],
                     "save_as": str((run / "clips" / f"{c['id']}.mp4").resolve()), "stand_in": c["stand_in"]})
    _env.write_json(run / "clips" / "requests.json", {"clips": reqs})
    for q in reqs:
        print(f"clip {q['id']} for {q['beat']} ({q['use']}), {q['seconds']} s at {q['size']} -> {q['save_as']}")
        print("  " + "; ".join(f"{k}: {q[k] or '(not written)'}" for k in SHOT))
        print(f"  image-to-video from: {q['image']}")
        print(f"  prompt: {q['prompt']}")
    print(f"{len(reqs)} clips -> {run / 'clips' / 'requests.json'}")
    return 0


def strongest(src, seconds):
    """Where a recording's shot of `seconds` starts: at its strongest second (the one-second run of samples that move
    most and are sharpest), moved earlier as far as the shot needs to end inside the recording; 0.0 when it cannot be
    read."""
    h = SAMPLE * 2
    r = subprocess.run([_env.ffmpeg(), "-v", "error", "-i", str(src), "-an", "-vf",
                        f"fps={RATE},scale={SAMPLE}:{h}:force_original_aspect_ratio=increase,crop={SAMPLE}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    n = SAMPLE * h
    frames = [r.stdout[i:i + n] for i in range(0, len(r.stdout) - n + 1, n)] if r.returncode == 0 else []
    if len(frames) < 2:
        return 0.0
    move = [0.0] + [sum(abs(a - b) for a, b in zip(f, g)) / n for f, g in zip(frames[1:], frames)]
    sharp = [sum(abs(f[i] - f[i + 1]) for i in range(n - 1) if (i + 1) % SAMPLE) / n for f in frames]
    top = lambda xs: max(xs) or 1.0
    score = [MOTION * m / top(move) + (1 - MOTION) * s / top(sharp) for m, s in zip(move, sharp)]
    run = min(RATE, len(score))
    best = max(range(len(score) - run + 1), key=lambda i: (sum(score[i:i + run]), -i))
    return round(max(0.0, min(best / RATE, len(frames) / RATE - seconds)), 3)


def conform(src, size, frames, dst, start=None):
    """The clip at `size`, 30 fps, `frames` long, as one JPEG per frame in `dst`: looped when it runs short, or, for a
    recording of the person's own (`start`, the second its shot starts), from `start`, its last frame held."""
    w, h = size
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={FPS}"
    head = ["-stream_loop", "-1", "-i", str(src)] if start is None else ["-ss", f"{start:.3f}", "-i", str(src)]
    if start is not None:
        vf += ",tpad=stop=-1:stop_mode=clone"
    r = subprocess.run([_env.ffmpeg(), "-y", "-v", "error", *head, "-an", "-frames:v", str(frames),
                        "-vf", vf, "-q:v", "2", str(dst / "%04d.jpg")], capture_output=True, text=True)
    n = len(list(dst.glob("*.jpg")))
    return (n, "") if r.returncode == 0 and n else (0, r.stderr[-300:])


def cmd_normalize(a):
    run = _env.writable_run()
    r = reel(run)
    win, cards = windows(r), cards_of(r)
    # the frames go to a folder of their own that clips.json then names; the folders it does not name go after it
    name = f"frames-{time.time_ns()}"
    frames_dir = run / "clips" / name
    out = {}
    for c in r.get("clips") or []:
        card = cards[c["beat"]]
        at, n = win[c["id"]]
        rec = {"beat": c["beat"], "use": c["use"], "image": c["image"], "prompt": c["prompt"], "from_frame": at}
        if c["use"] == OWN:
            start = strongest(c["source"], n / FPS)
            got, err = conform(c["source"], size_of(card), n, frames_dir / c["id"], start=start)
            if got:
                rec.update(status=OWN, source=c["source"], from_second=start, dir=f"clips/{c['id']}", frames=got)
            else:
                rec.update(status="stand-in", stand_in=c["stand_in"], why=f"could not read {Path(c['source']).name}: {err}")
            out[c["id"]] = rec
            print(f"clip {c['id']} ({c['beat']}): " + (f"their own clip from {start} s, {got} frames -> clips/{name}/{c['id']}/" if got
                                                        else f"stand-in ({rec['why']}): {c['stand_in']}"))
            continue
        src = arrived(run, c["id"])
        got, err = conform(src, size_of(card), n, frames_dir / c["id"]) if src else (0, "")
        if got:
            rec.update(status="generated", source=str(src), dir=f"clips/{c['id']}", frames=got)
        else:
            rec.update(status="stand-in", stand_in=c["stand_in"],
                       why=f"could not read {src.name}: {err}" if src else (a.why or "the video model did not produce it"))
        out[c["id"]] = rec
        print(f"clip {c['id']} ({c['beat']}): " + (f"generated, {got} frames -> clips/{name}/{c['id']}/" if got
                                                    else f"stand-in ({rec['why']}): {c['stand_in']}"))
    _env.write_json(run / "clips.json", {"frames": f"clips/{name}", "clips": out})
    for old in (run / "clips").glob("frames*"):
        if old.name != name:
            shutil.rmtree(old)
    g = sum(1 for x in out.values() if x["status"] == "generated")
    o = sum(1 for x in out.values() if x["status"] == OWN)
    print(f"clips: {g} generated, {o} their own, {len(out) - g - o} stand-in -> {run / 'clips.json'}")
    return 0


def frames(run):
    """The folder of conformed frames clips.json names, or None."""
    name = (_env.read_json(Path(run) / "clips.json") or {}).get("frames")
    return Path(run) / name if name else None


def placed(run):
    """The clips the film shows, generated and the person's own, for the composition's props: where each starts and its
    frames."""
    return [{"id": k, "image": x["image"], "from": x["from_frame"], "frames": x["frames"], "dir": x["dir"]}
            for k, x in ((_env.read_json(Path(run) / "clips.json") or {}).get("clips") or {}).items() if x.get("status") in ("generated", OWN)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
