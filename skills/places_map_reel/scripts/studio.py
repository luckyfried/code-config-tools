"""The studio composition (motion/studio) as a function: boards in, films and settled frames out.

A run's public/ folder is what the composition reads: public/photos/ (storyboard.py grades them in), and the kit's
fonts and grain, copied in here on every staging. Every render writes its jobs, its report and its log under render/
in the run; the report lists any job that failed after three tries and any finding the composition logged
(FONT_ERROR, IMAGE_ERROR, RENDER_ERROR). With an NVIDIA device the render rasterizes and encodes on the card.

A film renders in chunks kept in the run under render/chunks/<name>/<key>/ (scripts/chunks.py), where the key names
the job, the run's public folder and the composition's source, so an interrupted render resumes when the same command
runs again: chunks that probe whole are kept, only the missing ones render, and the film is joined from them. With an
NVIDIA card a film is one chunk, which renders in seconds; otherwise a chunk is chunks.CHUNK_FRAMES frames.
One render at a time runs in a run, under render/render.lock (chunks.lock)."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import _env
import chunks
import clips

STUDIO = _env.SKILL / "motion" / "studio"
PUBLIC = Path("public")
RENDER = Path("render")
FAULTS = ("FONT_ERROR", "IMAGE_ERROR", "RENDER_ERROR")
RENDERER = _env.SKILL / "scripts" / "render.py"
# the built composition: a change to it gives every film a new chunk folder
SOURCES = (_env.SKILL / "motion" / "dist",)


def public():
    """The run's public folder with the kit's fonts and grain beside the photographs."""
    for name, src in (("fonts", _env.SKILL / "fonts"), ("fx", _env.SKILL / "motion" / "public" / "fx")):
        shutil.copytree(src, PUBLIC / name, dirs_exist_ok=True)
    return PUBLIC.resolve()


def props(board):
    """The composition's input: the board and the generated clips placed on its cards."""
    return {"board": board, "clips": clips.placed()}


def still(board, frame, out, scale=1.0):
    return {"type": "still", "composition": "Film", "props": props(board), "frame": int(frame), "scale": scale, "out": str(Path(out).resolve())}


def video(board, out, frames, scale=1.0):
    """A film of `frames` frames, the length the cut gives it (film.json); render.py refuses one the composition
    does not run to."""
    return {"type": "video", "composition": "Film", "props": props(board), "frames": int(frames), "scale": scale,
            "out": str(Path(out).resolve())}


def faults(rep):
    """The findings of a render report that refuse a film, and the failed jobs."""
    bad = [f["text"] for f in rep.get("findings", []) if f["text"].startswith(FAULTS)]
    return bad + [f"{rep['failed']} render jobs failed"] * bool(rep.get("failed"))


def lock(name):
    """The run's render lock, taken by a command before its first write into the run (chunks.lock). The tools resolve
    first, since setup.py runs outside run.spawn and under the lock only run.spawn starts a process."""
    _env.tools()
    return chunks.lock(RENDER, name)


def render(jobs, name, run=None):
    """Runs the jobs in one bundle and one browser through chunks.render, which keeps every whole chunk of a film and
    joins each film whose chunks are all whole; `run` is the lock of a command that took it (lock), and without it the
    render takes its own. Returns the report in the caller's jobs, with the render's wall and CPU seconds, and leaves it
    at render/<name>-report.part.json, a working copy no check reads: the command that moves the render's outputs onto
    their names publishes the report once they are all there."""
    if run is None:
        with lock(name) as run:
            return render(jobs, name, run)
    tools = _env.tools()
    if not tools.get("chromium") or not tools.get("dist"):
        sys.exit(f"the film cannot render here: python3 {_env.SKILL}/scripts/setup.py says what is missing")
    pub = public()
    report = (RENDER / f"{name}-report.part.json").resolve()
    renderer = {"exit": 0}

    def invoke(pending, spawn):
        jf = RENDER / f"{name}-jobs.json"
        jf.write_text(json.dumps({"publicDir": str(pub), "report": str(report), "jobs": pending,
                                  "ffmpeg": _env.ffmpeg(), "chromium": tools["chromium"]}))
        report.unlink(missing_ok=True)
        with open(RENDER / f"{name}.log", "w") as log:
            renderer["exit"] = spawn([sys.executable, str(RENDERER), "--jobs", str(jf.resolve())], stderr=log,
                                     env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1")).returncode
        got = _env.read_json(report) or chunks.unreported(pending, renderer["exit"], RENDER / f"{name}.log")
        renderer.update(got)
        return got

    t0 = os.times()
    rep = chunks.render(run, jobs, pub, SOURCES, _env.ffmpeg(), _env.ffprobe(), invoke)
    t1 = os.times()
    rep.update(exit=renderer["exit"], render_seconds=renderer.get("seconds", 0), bundle_seconds=renderer.get("bundle_seconds", 0),
               gpu=rep.pop("card", None),
               cpu_seconds=round((t1.children_user - t0.children_user) + (t1.children_system - t0.children_system), 1))
    _env.write_json(report, rep)
    where = f" on the {'graphics card' if rep['gpu'] else 'CPU'} ({rep['gl']})" if rep.get("gl") else ""
    print(f"render {name}: {rep['jobs'] - rep['failed']} of {rep['jobs']} jobs in {rep['seconds']:.0f} s{where}, "
          f"{rep['cpu_seconds']} CPU-s, {len(rep['findings'])} findings; log {RENDER / name}.log")
    return rep


def ff(args, run=None):
    """ffmpeg's stderr; under a command's lock (`run`) the process starts through run.spawn and holds the lock."""
    return (run.spawn if run else subprocess.run)([_env.ffmpeg(), "-hide_banner", "-nostats", *args], capture_output=True,
                                                  text=True).stderr


def under_half(luma):
    """The quiet seconds of a luma line (each second's change, `luma_line`): which seconds read under 0.5, and the
    longest run of them. Figures the critic reads beside the strip; a held composition is quiet by design."""
    low = [i + 1 for i, y in enumerate(luma) if y < 0.5]
    run_, longest = 0, 0
    for y in luma:
        run_ = run_ + 1 if y < 0.5 else 0
        longest = max(longest, run_)
    return {"seconds_under_half": low, "longest_run_under_half": longest}


# the width the luma line reads the picture at: an eighth of the reel, where film grain averages out and a move does not
LUMA_WIDTH = 135


def luma_line(mp4, run=None):
    """Each second's change: the mean luma difference between the frame at the start of the second and the frame at
    its end, with the picture downscaled to LUMA_WIDTH px wide. Grain is new noise on every frame, so it neither
    survives the downscale nor adds up across the second; a move, however slow, does both. A locked frame under
    moving grain reads 0.25 or less."""
    ya = [float(x) for x in re.findall(r"YAVG=([\d.]+)", ff(["-i", str(mp4), "-vf", f"fps=1,scale={LUMA_WIDTH}:-2:flags=area,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"], run))]
    return [round(y, 2) for y in ya]


def strip12(mp4, out, run=None):
    """The film at 12 frames a second, 300 px tall, tiled 12 across and 3 down per image: every frame a move spends,
    the ones the 1 and 2 fps strips skip. One image per three seconds, named <stem>-strip12-NN.jpg."""
    mp4, out = Path(mp4), Path(out)
    for f in out.glob(f"{mp4.stem}-strip12-*.jpg"):
        f.unlink()
    ff(["-y", "-i", str(mp4), "-vf", "fps=12,scale=-2:300,tile=12x3", "-q:v", "3", str(out / f"{mp4.stem}-strip12-%02d.jpg")], run)
    return sorted(str(p) for p in out.glob(f"{mp4.stem}-strip12-*.jpg"))


def measure(mp4, planned, hook_frame=None, strips=None, run=None):
    """Duration; the cuts, as the planned shot changes joined with the scene-score cuts (scene > 0.12 at 270x480) more
    than 0.2 s from every one of them, and per minute; the luma line (`luma_line`) and its quiet seconds (`under_half`);
    and the 1, 2 and 12 fps strips in the folder `strips` (beside the file when it is None). All of it is figures:
    nothing here passes or fails. Under a command's lock (`run`) every process starts through run.spawn."""
    mp4 = Path(mp4)
    secs = float((run.spawn if run else subprocess.run)([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of",
                                                         "csv=p=0", str(mp4)], capture_output=True, text=True).stdout)
    scene = [float(x) for x in re.findall(r"pts_time:([\d.]+)", ff(["-i", str(mp4), "-vf", "scale=270:480,select='gt(scene,0.12)',showinfo", "-an", "-f", "null", "-"], run))]
    cuts = sorted(planned)
    extra = [t for t in scene if t >= 0.2 and all(abs(t - c) > 0.2 for c in cuts)]
    allc = sorted(cuts + extra)
    luma = luma_line(mp4, run)
    out = {"file": str(mp4), "seconds": round(secs, 2), "frames": round(secs * 30), "planned_cuts": [round(c, 2) for c in cuts],
           "scene_cuts": [round(t, 2) for t in scene], "extra_scene_cuts": [round(t, 2) for t in extra], "cuts": len(allc),
           "cuts_per_minute": round(len(allc) / (secs / 60), 1), "hook_event_frame": hook_frame, "luma": luma,
           **under_half(luma)}
    d = Path(strips) if strips else mp4.parent
    d.mkdir(parents=True, exist_ok=True)
    n = max(1, int(secs))
    out["strip"] = str(d / (mp4.stem + "-strip.png"))
    out["strip2"] = str(d / (mp4.stem + "-strip2.png"))
    ff(["-y", "-i", str(mp4), "-vf", f"fps=1,scale=216:-2,tile={n}x1:padding=6:color=white", "-frames:v", "1", "-update", "1", out["strip"]], run)
    ff(["-y", "-i", str(mp4), "-vf", f"fps=2,scale=135:-2,tile={2 * n}x1:padding=4:color=white", "-frames:v", "1", "-update", "1", out["strip2"]], run)
    out["strip12"] = strip12(mp4, d, run)
    return out
