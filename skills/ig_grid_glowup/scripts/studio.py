"""The studio composition (motion/studio) as a function: the board in, films and settled frames out.

The composition ships built, in motion/dist/, and render.py draws it in a headless Chromium. A run's public/
folder is what the composition reads: public/before/ and public/graded/ (storyboard.py draft writes them),
and the kit's fonts, copied in here on every staging. Every render writes its jobs, its report and its log
under render/ in the run; the report lists any job that failed after three tries and any finding the composition
logged (FONT_ERROR, IMAGE_ERROR, RENDER_ERROR). With an NVIDIA device the render rasterizes and encodes on the card.

A film renders in chunks kept in the run (scripts/chunks.py), so a render that was stopped resumes when the same
command runs again: the chunks already whole are kept and only the missing ones render. A command takes the run's lock
(`lock`) before its first write into the run, and every process it starts while it holds the lock goes through
run.spawn."""
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import _env
import chunks
import clips

DIST = _env.SKILL / "motion" / "dist"
RENDERER = _env.SKILL / "scripts" / "render.py"
PUBLIC = Path("public")
RENDER = Path("render")
# the built composition: a change to any file here is a new chunk key
SOURCES = (DIST,)


def public():
    """The run's public folder with the kit's fonts beside the photographs."""
    for name, src in (("fonts", _env.SKILL / "fonts"),):
        dst = PUBLIC / name
        if dst.is_symlink():
            dst.unlink()
        shutil.copytree(src, dst, dirs_exist_ok=True)
    return PUBLIC.resolve()


def props(board):
    """The composition's input: the board and the generated clips placed on its posts."""
    return {"board": board, "clips": clips.placed()}


def still(board, frame, out, scale=1.0):
    return {"type": "still", "composition": "Film", "props": props(board), "frame": int(frame), "scale": scale, "out": str(Path(out).resolve())}


def video(board, out, scale=1.0, frame_range=None):
    """A film job: `frames` is the film's length, the sum of its beats' frames, which is the composition's length."""
    job = {"type": "video", "composition": "Film", "props": props(board), "scale": scale,
           "frames": sum(int(b["frames"]) for b in board["beats"]), "out": str(Path(out).resolve())}
    if frame_range:
        job["frameRange"] = [int(frame_range[0]), int(frame_range[1])]
    return job


def lock(name):
    """The run's render lock, taken by a command before its first write into the run (chunks.lock). The tools are
    resolved first, so setup.py runs before the lock is held and every process under it starts through run.spawn."""
    _env.tools()
    return chunks.lock(RENDER, name)


def render(jobs, name, run=None):
    """Runs the jobs in one bundle and one browser through chunks.render, which keeps every whole chunk of a video job
    and joins each video whose chunks are all whole; `run` is the lock of a command that took it (lock), and without it
    the render takes its own. Returns the report in the caller's jobs, with the wall and CPU seconds. The renderer's
    own report is staging under a name of this command's; the command publishes the returned report (`publish`) once
    the set it speaks for is in place."""
    if run is None:
        with lock(name) as run:
            return render(jobs, name, run)
    tools = _env.tools()
    if not tools.get("chromium") or not tools.get("dist"):
        sys.exit(f"the film cannot render here: python3 {_env.SKILL}/scripts/setup.py says what is missing")
    pub = public()
    report = _env.part(RENDER / f"{name}-report.json").resolve()
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
        report.unlink(missing_ok=True)
        renderer.update(got)
        return got

    t0 = os.times()
    rep = chunks.render(run, jobs, pub, SOURCES, _env.ffmpeg(), _env.ffprobe(), invoke)
    t1 = os.times()
    rep.update(exit=renderer["exit"], gpu=rep.pop("card", None), cpu_seconds=round((t1.children_user - t0.children_user) + (t1.children_system - t0.children_system), 1))
    where = f" on the {'graphics card' if rep['gpu'] else 'CPU'} ({rep['gl']})" if rep.get("gl") else ""
    print(f"render {name}: {rep['jobs'] - rep['failed']} of {rep['jobs']} jobs in {rep['seconds']:.0f} s{where}, "
          f"{rep['cpu_seconds']} CPU-s, {len(rep['findings'])} findings; log {RENDER / name}.log")
    return rep


def publish(name, rep):
    """The report of a render (`render`) under the name its readers open, render/<name>-report.json."""
    _env.write_json(RENDER / f"{name}-report.json", rep)


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
    survives the downscale nor adds up across the second; a move, however slow, does both."""
    ya = [float(x) for x in re.findall(r"YAVG=([\d.]+)", ff(["-i", str(mp4), "-vf", f"fps=1,scale={LUMA_WIDTH}:-2:flags=area,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"], run))]
    return [round(y, 2) for y in ya]


def measure(mp4, planned, hook_frame=None, strips=None, run=None):
    """Duration; the cuts, as the planned shot changes joined with the scene-score cuts (scene > 0.12 at 270x480) more
    than 0.2 s from every one of them, and per minute; the luma line (`luma_line`) and its quiet seconds (`under_half`);
    and the 1, 2 and 12 fps strips in the folder `strips` (beside the file when it is None). All of it is figures: nothing
    here passes or fails. Under a command's lock (`run`) every probe starts through run.spawn."""
    mp4 = Path(mp4)
    secs = float((run.spawn if run else subprocess.run)([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                                capture_output=True, text=True).stdout)
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
    n = max(1, int(secs))
    out["strip"] = str(d / (mp4.stem + "-strip.png"))
    out["strip2"] = str(d / (mp4.stem + "-strip2.png"))
    ff(["-y", "-i", str(mp4), "-vf", f"fps=1,scale=216:-2,tile={n}x1:padding=6:color=white", "-frames:v", "1", "-update", "1", out["strip"]], run)
    ff(["-y", "-i", str(mp4), "-vf", f"fps=2,scale=135:-2,tile={2 * n}x1:padding=4:color=white", "-frames:v", "1", "-update", "1", out["strip2"]], run)
    # every frame at 12 a second, one second to a row: where a field is the stage or a beat holds past its words
    out["strip12"] = str(d / (mp4.stem + "-strip12.jpg"))
    ff(["-y", "-i", str(mp4), "-vf", f"fps=12,scale=-2:300,tile=12x{math.ceil(secs)}", "-frames:v", "1", "-update", "1", out["strip12"]], run)
    return out
