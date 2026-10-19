#!/usr/bin/env python3
"""Movement 5: the generated clips the winning storyboard asks for, conformed, graded and placed.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/clips.py list [--board N]       # every clip: its prompt, length, source photo, the file to save
    python3 S/scripts/clips.py normalize [--board N] [--why "..."]
                                                      # conform what arrived; substitute what did not -> build/clips.json

list writes build/clips/requests.json and prints one block per clip. The agent generates each clip with its
video model (image-to-video from the named photo when the model takes an image) and saves it as
build/clips/NN.mp4 (.mov and .webm are read too). A clip whose role is "their own reel" needs no generation:
it is cut from their footage. Every clip is vertical, the film's own frame.

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
    """A clip runs for its whole beat, or longer when the storyboard asks."""
    return max(c.get("seconds") or 0, beat_seconds(b, c["beat"]) or 0)


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
        r = {"id": c["id"], "beat": c["beat"], "role": c["role"], "seconds": secs, "aspect": "9:16",
             "size": f"{W}x{H}", "save_as": str((CLIPS / f"{c['id']}.mp4").resolve())}
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


def conform(src, dst, secs, filt, start=0.0):
    dst.parent.mkdir(parents=True, exist_ok=True)
    w, h = W, H
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
            ok, err = conform(src, OUT / f"{c['id']}.mp4", secs, g["filter"])
            rec.update({"status": "generated", "from": str(src), "frames": ok} if ok else {"status": "substituted", "why": f"could not read {src.name}: {err}"})
        elif c.get("source") and Path(c["source"]).exists():
            ok, err = conform(c["source"], OUT / f"{c['id']}.mp4", secs, g["filter"])
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["list", "normalize"])
    ap.add_argument("--board")
    ap.add_argument("--why", help="normalize: why the missing clips did not arrive (for example: no video model in this session)")
    a = ap.parse_args()
    return {"list": cmd_list, "normalize": cmd_normalize}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
