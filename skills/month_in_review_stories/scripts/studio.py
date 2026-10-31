"""The studio renderer and the measures taken of what it renders (stdlib only).

- shots(board), cut_frames(board), rest_frames(n, pulse): the series' timing in frames, the same arithmetic as
  motion/studio/story (a card is its shots end to end). The storyboard's sheets show each shot's rest frames.
- reel_rest_frames(board): one frame in each of the reel's beats where its move has settled, for the storyboard's reel
  sheet.
- props(board, run): the compositions' input, the board and the generated clips placed on the reel's cards.
- lock(work, name), render(jobs, work, name): the run's render lock, and one run of scripts/render.py (the built
  composition in motion/dist/, drawn in a headless Chromium and encoded with ffmpeg) over still and video jobs through scripts/chunks.py; returns its report, whose `findings` carry
  every FONT_ERROR and IMAGE_ERROR line the compositions printed and any RENDER_ERROR of the run. Every video job
  carries its length as `frames` and renders in chunks kept in work/chunks/<name>/<key>/ (chunks.CHUNK_FRAMES each, or
  one per video on an NVIDIA card), so a render that is cut off resumes on the next call with the same jobs: only
  the chunks that are not whole render again, and a job's out is its chunks joined once all of them are whole.
- findings(report), lines(found): the findings parsed, and each distinct one as one line.
- measure(mp4, planned, strips), under_half(luma), hook_frame(mp4): the figures the critic reads beside the strips,
  from one decode of the file; ff, duration, hook_frame and measure start their processes through `spawn`, which is
  the held lock's under one. Nothing here passes or fails but the hook: a held composition is quiet by design.
"""
import contextlib
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import chunks  # noqa: E402
from compose import photos  # noqa: E402

FPS = 30
DIST = _env.SKILL / "motion" / "dist"
RENDERER = _env.SKILL / "scripts" / "render.py"
# the built composition a chunk is drawn by: a change to any file in it makes every chunk new
SOURCES = (DIST,)
# the first event (a frame whose luma moves by 1.0 or more from the frame before) lands inside this many frames
HOOK_FRAMES = 30
HOOK_STEP = 1.0
# the width the luma line reads the picture at: an eighth of the frame, where film grain averages out and a move does not
LUMA_WIDTH = 135


def pulse(board):
    return FPS * 60 / board["bpm"]


def jround(x):
    """x to the nearest frame as the compositions round it (Math.round: a half goes up), so a frame named here is the
    frame the browser draws as that shot's."""
    return math.floor(x + 0.5)


def card_frames(board, card):
    return card.get("frames") or jround(card["bars"] * 4 * pulse(board))


def shots(board):
    """Every shot of every card: card index and id, shot index, first frame and end frame (film frames), length."""
    p, out, start = pulse(board), [], 0
    for ci, c in enumerate(board["beats"]):
        n = card_frames(board, c)
        ss = c.get("shots") or [{"beats": n / p}]
        acc = 0
        for si, s in enumerate(ss):
            a = jround(acc * p)
            acc += s["beats"]
            e = n if si == len(ss) - 1 else min(n, jround(acc * p))
            out.append({"card": ci, "id": c["id"], "shot": si, "a": start + a, "e": start + e, "len": e - a, "local": a})
        start += n
    return out


def cut_frames(board):
    """Every planned cut: each card boundary and each shot boundary inside a card."""
    return [s["a"] for s in shots(board) if s["a"] > 0]


def rest_frames(n, p):
    """A beat in, the middle and the last frame of a shot of n frames."""
    return sorted({min(n - 1, jround(p)), n // 2, n - 1})


def rest_jobs(board, out, scale=0.25, cards=None):
    """Still jobs at every rest frame of every shot (of the named cards), into out/<card>-s<shot>-<frame>.png."""
    jobs = []
    for s in shots(board):
        if cards and s["id"] not in cards:
            continue
        for f in rest_frames(s["len"], pulse(board)):
            jobs.append({"type": "still", "composition": "Film", "props": {"board": board}, "frame": s["a"] + f, "scale": scale,
                         "out": str(Path(out).resolve() / f"{s['id']}-s{s['shot']}-{s['local'] + f:04d}.png")})
    return jobs


def reel_rest_frames(board):
    """{beat key: frame}: each moment as its line lands above its subject (and before the camera leaves for the next
    photograph, 0.6 beats ahead of the cut), the closer at its still."""
    r = board["reel"]
    f = lambda beat: round(beat * r["fps"] * 60 / r["bpm"])
    out = {}
    for c in r["cards"]:
        out[c["key"]] = f(min(c["rise"][0] + c["rise"][1] + 0.15, c["leave"] - 0.65))
    out["closer"] = min(r["frames"] - 1, f(r["closer"]["still"]) + 2)
    return out


def props(board, run=None):
    """The compositions' input: the board, and the generated clips placed on the reel's cards (clips.json in `run`)."""
    import clips
    return {"board": board, "clips": clips.placed(run) if run else []}


def public(work, board=None, run=None):
    """work/public, the folder the browser reads: the kit's fonts, copied over on every staging, the reel's
    photographs (its moments' and the closer's other posts') at the size the film draws them, in the set's one grade
    (the reel's `grade`: the month's photographs' median lightness and median cast), and the run's conformed clips
    (clips.py normalize)."""
    pub = Path(work).resolve() / "public"
    shutil.copytree(_env.SKILL / "fonts", pub / "fonts", dirs_exist_ok=True)
    r = (board or {}).get("reel") or {}
    grade = r.get("grade") or {}
    for c in r.get("cards", []) + (r.get("closer") or {}).get("tiles", []):
        if c.get("source"):
            photos.stage(c["source"], pub / c["file"], grade.get("target"), grade.get("cast"))
    import clips
    frames = clips.frames(run) if run else None
    if frames and frames.is_dir():
        shutil.copytree(frames, pub / "clips", dirs_exist_ok=True)
    return pub


def lock(work, name):
    """The run's one render lock in the work folder (chunks.lock): the command takes it before its first write and hands
    it to render, and every process it starts while holding it goes through its `spawn`; the tools are resolved first
    (setup.py), so that probe runs before the lock."""
    _env.tools()
    return chunks.lock(work, name)


def render(jobs, work, name, board=None, run=None, hold=None):
    """Runs the jobs through render.py over work/public (staged with `board`'s photographs and `run`'s clips), each
    video as the chunks of it still to render (chunks.render); returns the report in the caller's jobs (failed,
    findings, exit, timings, chunks). The renderer's own report stays in work/<name>-report.json. `hold` is the work
    folder's lock when the caller has taken it; otherwise render takes it."""
    work = Path(work).resolve()
    tools = _env.tools()
    if not tools.get("chromium") or not tools.get("dist"):
        sys.exit(f"the film cannot render here: python3 {_env.SKILL}/scripts/setup.py says what is missing")
    with contextlib.ExitStack() as stack:
        hold = hold or stack.enter_context(lock(work, name))
        pub = public(work, board, run)
        jf, report, log = work / f"{name}-jobs.json", work / f"{name}-report.json", work / f"{name}.log"
        got = {"exit": 0, "timings": []}

        def invoke(pending, spawn):
            jf.write_text(json.dumps({"publicDir": str(pub), "report": str(report), "jobs": pending,
                                      "ffmpeg": _env.ffmpeg(), "chromium": tools["chromium"]}))
            report.unlink(missing_ok=True)
            with open(log, "w") as f:
                got["exit"] = spawn([sys.executable, str(RENDERER), "--jobs", str(jf)], stdout=f, stderr=f,
                                    env=dict(os.environ, CSC_DISABLE_KEYCHAIN="1")).returncode
            rep = _env.read_json(report) or chunks.unreported(pending, got["exit"], log)
            got["timings"] = rep.get("timings", [])
            return rep

        rep = chunks.render(hold, jobs, pub, SOURCES, _env.ffmpeg(), _env.ffprobe(), invoke)
    return {**rep, **got}


def findings(report):
    return [{"kind": f["text"].split(" ", 1)[0], "job": f.get("job"), "text": f["text"]} for f in report.get("findings", [])]


def lines(found):
    """Each distinct finding once, in the order first found."""
    return list(dict.fromkeys(f["text"][:200] for f in found))


def ff(*args, spawn=subprocess.run):
    return spawn([_env.ffmpeg(), "-hide_banner", "-nostats", *map(str, args)], capture_output=True, text=True)


def duration(mp4, spawn=subprocess.run):
    r = spawn([_env.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def under_half(luma):
    """The quiet seconds of a luma line: which seconds read under 0.5, and the longest run of them."""
    low = [i + 1 for i, y in enumerate(luma) if y < 0.5]
    run_, longest = 0, 0
    for y in luma:
        run_ = run_ + 1 if y < 0.5 else 0
        longest = max(longest, run_)
    return {"seconds_under_half": low, "longest_run_under_half": longest}


def hook_frame(mp4, spawn=subprocess.run):
    """The first frame whose luma moves by HOOK_STEP or more from the frame before (None when none does in 2 s)."""
    r = ff("-t", 2.2, "-i", mp4, "-vf", f"trim=end_frame={2 * FPS},tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
           "-an", "-f", "null", "-", spawn=spawn)
    v = [float(x) for x in re.findall(r"YAVG=([\d.]+)", r.stderr)]
    return next((i + 1 for i, x in enumerate(v) if x >= HOOK_STEP), None)


def measure(mp4, planned, strips=None, spawn=subprocess.run):
    """The figures of one film, from one decode of it: duration; the cuts, as the planned cuts (film frames) joined with
    the scene-score cuts (scene > 0.12 at 270x480) more than 0.2 s from every one of them, and per minute; the hook
    frame; the luma line (each second's change: the mean luma difference between the frame at the start of the second
    and the frame at its end, downscaled to LUMA_WIDTH px wide, where moving grain cancels and a move, however slow,
    adds up, so a locked frame under moving grain reads 0.25 or less) and its quiet seconds; and the 1 and 2 fps strips
    in the folder `strips` (beside the file when None)."""
    mp4 = Path(mp4)
    secs = duration(mp4, spawn)
    d = Path(strips) if strips else mp4.parent
    d.mkdir(parents=True, exist_ok=True)
    strip, strip2 = d / f"{mp4.stem}-strip.png", d / f"{mp4.stem}-strip2.png"
    k = max(1, int(secs))
    graph = ("[0:v]split=4[s][l][a][b];"
             "[s]scale=270:480,select='gt(scene,0.12)',showinfo[so];"
             f"[l]fps=1,scale={LUMA_WIDTH}:-2:flags=area,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG[lo];"
             f"[a]fps=1,scale=216:-2,tile={min(k, 10)}x{-(-k // 10)}:padding=4:color=black[ao];"
             f"[b]fps=2,scale=135:-2,tile={min(2 * k, 12)}x{-(-2 * k // 12)}:padding=4:color=black[bo]")
    r = ff("-y", "-i", mp4, "-filter_complex", graph, "-map", "[so]", "-f", "null", "-", "-map", "[lo]", "-f", "null", "-",
           "-map", "[ao]", "-frames:v", "1", "-update", "1", strip, "-map", "[bo]", "-frames:v", "1", "-update", "1", strip2,
           spawn=spawn)
    scene = [float(m) for m in re.findall(r"showinfo.*?pts_time:\s*([\d.]+)", r.stderr)]
    luma = [round(float(y), 2) for y in re.findall(r"YAVG=([\d.]+)", r.stderr)]
    cuts = sorted(f / FPS for f in planned)
    extra = [t for t in scene if t >= 0.2 and all(abs(t - c) > 0.2 for c in cuts)]
    n = len(cuts) + len(extra)
    hook = hook_frame(mp4, spawn)
    return {"file": str(mp4), "seconds": round(secs, 2), "frames": round(secs * FPS), "planned_cuts": [round(c, 2) for c in cuts],
            "scene_cuts": [round(t, 2) for t in scene], "extra_scene_cuts": [round(t, 2) for t in extra], "cuts": n,
            "cuts_per_minute": round(n / (secs / 60), 1) if secs else 0, "hook_frame": hook,
            "hook_ok": hook is not None and hook < HOOK_FRAMES, "luma": luma, **under_half(luma),
            "strip": str(strip), "strip2": str(strip2)}


def board_hash(board):
    """The board's identity: the timed read, the preview and the render name the board they are for by it."""
    return hashlib.sha256(json.dumps(board, sort_keys=True).encode()).hexdigest()[:16]


def taste_hash(run):
    """The identity of the run's taste.json as it stands: the board records the one it was drafted from, and the render
    refuses a board drafted from another, so every change to the taste reaches the film."""
    f = Path(run) / "taste.json"
    return hashlib.sha256(f.read_bytes()).hexdigest()[:16] if f.exists() else None
