"""The studio composition (motion/studio) as a function: storyboards in, films and settled frames out.

A run's public/ folder is what the composition reads: public/photos/ (picks.py writes it), and the kit's fonts and
grain, copied in here. Every render writes its jobs, its report and its log under render/ in the run; the report
lists any job that failed after three tries and any finding the composition logged (SAFE_BREACH, FONT_ERROR,
UNKNOWN_KIND, IMAGE_ERROR, RENDER_ERROR). With an NVIDIA device the render rasterizes and encodes on the card."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import _env
import clips

STUDIO = _env.SKILL / "motion" / "studio"
PUBLIC = Path("public")
RENDER = Path("render")


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


def video(board, out, scale=1.0):
    return {"type": "video", "composition": "Film", "props": props(board), "scale": scale, "out": str(Path(out).resolve())}


def render(jobs, name):
    """Runs the jobs in one bundle and one browser; returns the report, with the render's wall and CPU seconds."""
    tools = _env.tools()
    if not tools.get("node") or not tools.get("motion"):
        sys.exit(f"the studio engine is not installed (node or the motion packages): run python3 {_env.SKILL}/scripts/setup.py")
    RENDER.mkdir(exist_ok=True)
    spec = {"publicDir": str(public()), "report": str((RENDER / f"{name}-report.json").resolve()), "jobs": jobs,
            "bundleDir": str((RENDER / "bundle").resolve())}
    jf = RENDER / f"{name}-jobs.json"
    jf.write_text(json.dumps(spec))
    t0 = os.times()
    with open(RENDER / f"{name}.log", "w") as log:
        code = subprocess.run([tools["node"], str(STUDIO / "render.mjs"), str(jf.resolve())], cwd=STUDIO, stderr=log,
                              env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1")).returncode
    t1 = os.times()
    rep = _env.read_json(RENDER / f"{name}-report.json") or {"jobs": len(jobs), "failed": len(jobs), "findings": [], "seconds": 0}
    rep["exit"] = code
    rep["cpu_seconds"] = round((t1.children_user - t0.children_user) + (t1.children_system - t0.children_system), 1)
    rep["gpu"] = os.path.exists("/dev/nvidia0")
    _env.write_json(RENDER / f"{name}-report.json", rep)
    print(f"render {name}: {rep['jobs'] - rep['failed']} of {rep['jobs']} jobs in {rep.get('seconds', 0):.0f} s "
          f"({rep['cpu_seconds']} CPU-s, {'graphics card' if rep['gpu'] else 'CPU'}), {len(rep['findings'])} findings; log {RENDER / name}.log")
    return rep


def ff(args):
    return subprocess.run([_env.ffmpeg(), "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr


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


def luma_line(mp4):
    """Each second's change: the mean luma difference between the frame at the start of the second and the frame at
    its end, with the picture downscaled to LUMA_WIDTH px wide. Grain is new noise on every frame, so it neither
    survives the downscale nor adds up across the second; a move, however slow, does both. A locked frame under
    moving grain reads 0.25 or less, the slowest drift in the three tones over 1."""
    import re
    ya = [float(x) for x in re.findall(r"YAVG=([\d.]+)", ff(["-i", str(mp4), "-vf", f"fps=1,scale={LUMA_WIDTH}:-2:flags=area,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"]))]
    return [round(y, 2) for y in ya]


def measure(mp4, planned, hook_frame=None, strips=None):
    """Duration; the cuts, as the planned shot changes joined with the scene-score cuts (scene > 0.12 at 270x480) more
    than 0.2 s from every one of them, and per minute; the luma line (`luma_line`) and its quiet seconds (`under_half`); and the 1 and 2 fps strips in the folder `strips` (beside the file when it is None). All of it is figures: nothing here passes or fails."""
    import re
    mp4 = Path(mp4)
    secs = float(subprocess.run([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                                capture_output=True, text=True).stdout)
    scene = [float(x) for x in re.findall(r"pts_time:([\d.]+)", ff(["-i", str(mp4), "-vf", "scale=270:480,select='gt(scene,0.12)',showinfo", "-an", "-f", "null", "-"]))]
    cuts = sorted(planned)
    extra = [t for t in scene if t >= 0.2 and all(abs(t - c) > 0.2 for c in cuts)]
    allc = sorted(cuts + extra)
    luma = luma_line(mp4)
    out = {"file": str(mp4), "seconds": round(secs, 2), "frames": round(secs * 30), "planned_cuts": [round(c, 2) for c in cuts],
           "scene_cuts": [round(t, 2) for t in scene], "extra_scene_cuts": [round(t, 2) for t in extra], "cuts": len(allc),
           "cuts_per_minute": round(len(allc) / (secs / 60), 1), "hook_event_frame": hook_frame, "luma": luma,
           **under_half(luma)}
    d = Path(strips) if strips else mp4.parent
    n = max(1, int(secs))
    out["strip"] = str(d / (mp4.stem + "-strip.png"))
    out["strip2"] = str(d / (mp4.stem + "-strip2.png"))
    ff(["-y", "-i", str(mp4), "-vf", f"fps=1,scale=216:-2,tile={n}x1:padding=6:color=white", "-frames:v", "1", "-update", "1", out["strip"]])
    ff(["-y", "-i", str(mp4), "-vf", f"fps=2,scale=135:-2,tile={2 * n}x1:padding=4:color=white", "-frames:v", "1", "-update", "1", out["strip2"]])
    return out
