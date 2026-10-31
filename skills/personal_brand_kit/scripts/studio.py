"""The studio composition as a function: storyboards in, films and settled frames out.

The composition ships built, in motion/dist/, and render.py draws it in a headless Chromium. A run's public/ folder is
what the composition reads: public/studio/ (material.py writes it), and the kit's fonts, copied in here on every
render. Every render writes its jobs, its report and its log under render/ in the run; the report lists any job that
failed after three tries and any finding the composition logged (FONT_ERROR, IMAGE_ERROR). With an NVIDIA device the
browser draws on the card.

A video job renders in chunks kept under render/chunks/<name>/<key>/, where the key names the job, the public folder's
files and the built composition, so an interrupted render resumes by running the same command again: chunks that
probe whole are kept, only the missing ones render, and the film is joined from them (chunks.render). With an NVIDIA
card a job is one chunk; otherwise a chunk is chunks.CHUNK_FRAMES frames. One render runs in a run at a time,
under the run's render lock (chunks.lock)."""
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import _env
import chunks

DIST = _env.SKILL / "motion" / "dist"
RENDERER = _env.SKILL / "scripts" / "render.py"
PUBLIC = Path("public")
RENDER = Path("render")
# the built composition: a new build gives every video job a new chunk folder
SOURCES = (DIST,)


def public():
    """The run's public folder with the kit's fonts beside the photographs."""
    shutil.copytree(_env.SKILL / "fonts", PUBLIC / "fonts", dirs_exist_ok=True)
    return PUBLIC.resolve()


def props(board):
    """The composition's input: the board."""
    return {"board": board}


def still(board, frame, out, scale=1.0):
    return {"type": "still", "composition": "Film", "props": props(board), "frame": int(frame), "scale": scale, "out": str(Path(out).resolve())}


def video(board, out, scale=1.0):
    """A film job; `frames` is the board's length, the sum of its beats, which the composition runs to."""
    return {"type": "video", "composition": "Film", "props": props(board), "scale": scale,
            "frames": sum(b["frames"] for b in board["beats"]), "out": str(Path(out).resolve())}


def lock(name):
    """The run's render lock, taken by a command before its first write into the run (chunks.lock). The tools resolve
    first, so setup.py never runs under the lock and every process under it starts through run.spawn."""
    _env.tools()
    return chunks.lock(RENDER, name)


def report_of(name):
    """The render's report QA reads as proof of what the render made: render/<name>-report.json. The render writes it
    beside that name (_env.part), and the command publishes it (publish_report) once the last file it certifies is in
    place, so the name never holds a report for files that are not."""
    return RENDER / f"{name}-report.json"


def publish_report(name):
    os.replace(_env.part(report_of(name)), report_of(name))


def render(jobs, name, run=None):
    """Runs the jobs in one bundle and one browser through chunks.render, which keeps every whole chunk of a video job
    and joins each video whose chunks are all whole; `run` is the lock of a command that took it (lock), and without it
    the render takes its own. Returns the report in the caller's jobs, with the wall and CPU seconds, written beside
    report_of(name) for the command to publish."""
    if run is None:
        with lock(name) as run:
            return render(jobs, name, run)
    tools = _env.tools()
    if not tools.get("chromium") or not tools.get("dist"):
        sys.exit(f"the film cannot render here: python3 {_env.SKILL}/scripts/setup.py says what is missing")
    pub = public()
    report = _env.part(report_of(name)).resolve()
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
    rep.update(exit=renderer["exit"], render_seconds=renderer.get("seconds", 0), gpu=rep.pop("card", None),
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
    moving grain reads 0.25 or less, the slowest push in a film over 1."""
    import re
    ya = [float(x) for x in re.findall(r"YAVG=([\d.]+)", ff(["-i", str(mp4), "-vf", f"fps=1,scale={LUMA_WIDTH}:-2:flags=area,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"], run))]
    return [round(y, 2) for y in ya]


def measure(mp4, planned, hook_frame=None, strips=None, run=None):
    """Duration; the cuts, as the planned shot changes joined with the scene-score cuts (scene > 0.12 at 270x480) more
    than 0.2 s from every one of them, and per minute; the luma line (`luma_line`) and its quiet seconds (`under_half`); and the strips in the folder `strips`: one frame a second in a row, and every frame at 12 a second, a row a second, for reading the film frame by frame (beside the file when it is None). All of it is figures: nothing here passes or fails.
    Under a command's lock (`run`) every process starts through run.spawn."""
    import re
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
    n = max(1, int(secs))
    rows = max(1, math.ceil(secs))
    out["strip"] = str(d / (mp4.stem + "-strip.png"))
    out["strip12"] = str(d / (mp4.stem + "-strip12.jpg"))
    ff(["-y", "-i", str(mp4), "-vf", f"fps=1,scale=216:-2,tile={n}x1:padding=6:color=white", "-frames:v", "1", "-update", "1", out["strip"]], run)
    ff(["-y", "-i", str(mp4), "-vf", f"fps=12,scale=-2:300,tile=12x{rows}:padding=2:color=white", "-frames:v", "1", "-update", "1", out["strip12"]], run)
    return out
