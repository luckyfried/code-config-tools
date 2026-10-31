"""A run's video jobs render in chunks that a render run again keeps, under one lock per run.

    with chunks.lock(render_dir, name) as run:      # before the command's first write into the run
        report = chunks.render(run, jobs, public_dir, sources, ffmpeg, ffprobe, invoke)

A video job (`"type": "video"`, `frames`, an optional `frameRange` [first, last], `out`) is planned as chunks: one
over its whole range with the NVIDIA device (GPU), CHUNK_FRAMES frames each without. The chunks live in
render_dir/chunks/<name>/<key>/, where the key is the job without its `out`, the files of `public_dir` and the files of
every folder in `sources`, each by relative path and content digest. A chunk that probes whole (ffprobe counts its
frames) is kept; the others are pending. Every other job is pending as it is.

Every process a command starts while it holds the lock goes through `run.spawn(argv, **kwargs)`, subprocess.run
with the run's lock handed to the child, so the lock lasts while any of them lives. The kit's `invoke(pending, spawn)`
renders the pending jobs its own way, starting its processes through `spawn`, which is `run.spawn`, and returns the
renderer's report (`findings`, each `{"job": out, "text": ...}`, `gl`, and `card`), or `unreported(pending, exit, log)`
when the renderer wrote none. A pending chunk's `out` is
`<a>-<b>.part.mp4`; once it passes the renderer's checks the renderer writes that attempt's findings for it, a list that
may be empty, to `<a>-<b>.part.findings.json` and renames nothing. After invoke returns, a chunk with that file and its
frames is published by rename, the findings first, over whatever stood there; a pair a killed command left is
published the same way when the next render plans. Nothing published is ever unlinked, and the only files removed
under the chunk folders are `.part` files. Each video whose chunks are all whole is joined into
its `out` by rename once the join holds its frames.

The report covers the caller's jobs: `jobs`, `failed`, `findings` (stills' and render errors from the renderer's
report, every whole chunk's from the file beside it), `seconds`, `chunks` (kept, rendered, to_go), and the renderer's
`gl` (the browser's graphics backend) and `card` (whether it drew on a graphics card), both None when this render drew
nothing."""
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

CHUNK_FRAMES = 60
GPU = os.path.exists("/dev/nvidia0")
# the Windows CreateFile flags the lock uses, which _winapi does not export; sharing is checked before CREATE_ALWAYS
# truncates, so a refused open never empties the holder's note
FILE_SHARE_READ, CREATE_ALWAYS = 1, 2


class Run:
    def __init__(self, render_dir, name, held):
        self.render_dir, self.name, self.held = render_dir, name, held

    def spawn(self, argv, **kwargs):
        """subprocess.run with the run's lock handed to the child."""
        if os.name == "nt":
            kwargs["startupinfo"] = subprocess.STARTUPINFO(lpAttributeList={"handle_list": [self.held]})
        else:
            kwargs["pass_fds"] = (self.held.fileno(),)
        return subprocess.run(argv, **kwargs)


@contextlib.contextmanager
def lock(render_dir, name):
    """The run's one render lock, render_dir/render.lock: a second taker exits nonzero naming the holder and its log.
    A flock on POSIX, on Windows an open that no other process may write to; every child started through `run.spawn`
    inherits it, so the lock lasts while any of them lives."""
    render_dir = Path(render_dir).resolve()
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / "render.lock"
    note = f"{name}\t{render_dir / f'{name}.log'}\n"
    if os.name == "nt":
        import _winapi
        try:
            held = _winapi.CreateFile(str(path), _winapi.GENERIC_READ | _winapi.GENERIC_WRITE, FILE_SHARE_READ, 0,
                                      CREATE_ALWAYS, 0, 0)
        except OSError as e:
            if getattr(e, "winerror", None) != 32:
                raise
            _busy(path.read_text(encoding="utf-8"), path)
        os.set_handle_inheritable(held, True)
        _winapi.WriteFile(held, note.encode("utf-8"))
    else:
        import fcntl
        held = open(path, "a+", encoding="utf-8")
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            held.seek(0)
            text = held.read()
            held.close()
            _busy(text, path)
        held.seek(0)
        held.truncate()
        held.write(note)
        held.flush()
    try:
        yield Run(render_dir, name, held)
    finally:
        if os.name == "nt":
            import _winapi
            _winapi.CloseHandle(held)
        else:
            held.close()


def _busy(text, path):
    holder, _, log = (text.splitlines() or [""])[0].partition("\t")
    sys.exit(f"a render named {holder or 'another'} is already running in this run; its log is {log or path}")


def unreported(pending, code, log):
    """The report of a renderer that exited `code` and wrote none: one RENDER_ERROR per pending job naming the exit and
    the last lines of the renderer's log `log`, where a THREE. line stays only when it reads as an error."""
    lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines() if Path(log).is_file() else []
    kept = [s.strip() for s in lines if s.strip() and ("THREE." not in s or re.search(r"error|fail|lost", s, re.I))]
    text = f"RENDER_ERROR the renderer exited {code} with no report; its last lines: {' | '.join(kept)[-600:] or 'none'}"
    return {"findings": [{"job": j["out"], "text": text} for j in pending], "gl": None}


def _plan(job):
    first, last = job.get("frameRange") or (0, job["frames"] - 1)
    size = last - first + 1 if GPU else CHUNK_FRAMES
    return [(a, min(a + size - 1, last)) for a in range(first, last + 1, size)]


def _tree(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and "node_modules" not in rel.parts:
            h.update(f"{rel.as_posix()}\0".encode() + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def _key(job, shared):
    j = json.dumps({k: v for k, v in job.items() if k != "out"}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{j}\0{shared}".encode()).hexdigest()[:16]


def _frames(run, ffprobe, mp4):
    """The video packets ffprobe reads from the file's index, or -1 when it reads none. A count, not a decode: the
    renderer decoded the chunk in its checks, and every file is synced to disk before its rename publishes it."""
    if not Path(mp4).exists():
        return -1
    r = run.spawn([ffprobe, "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                   "stream=nb_read_packets", "-of", "default=noprint_wrappers=1:nokey=1", str(mp4)], capture_output=True, text=True)
    return int(r.stdout.strip()) if r.stdout.strip().isdigit() else -1


def _synced(path):
    fd = os.open(path, os.O_RDWR | getattr(os, "O_BINARY", 0))  # Windows syncs only a handle open for writing
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def _checked(marker):
    try:
        found = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(found, list)


def _publish(run, ffprobe, part):
    """Publishes the chunk `<a>-<b>.part.mp4` when the renderer's findings file beside it parses and it holds its
    frames: both are synced and renamed, the findings first. Returns the published chunk, None when the renderer never
    checked it, or the RENDER_ERROR text of a chunk short of its frames."""
    stem = part.name[:-len(".part.mp4")]
    marker = part.with_name(f"{stem}.part.findings.json")
    if not _checked(marker):
        return None
    a, b = (int(x) for x in stem.split("-"))
    n = _frames(run, ffprobe, part)
    if n != b - a + 1:
        return f"RENDER_ERROR chunk {stem} holds {n} frames of {b - a + 1}"
    os.replace(_synced(marker), part.with_name(f"{stem}.findings.json"))
    os.replace(_synced(part), part.with_name(f"{stem}.mp4"))
    return part.with_name(f"{stem}.mp4")


def render(run, jobs, public_dir, sources, ffmpeg, ffprobe, invoke):
    t0 = time.monotonic()
    # every path is made absolute here, so a renderer started in another folder writes where the run reads
    jobs = [{**j, "out": str(Path(j["out"]).resolve())} for j in jobs]
    shared = _tree(Path(public_dir).resolve()) + "".join(_tree(Path(s).resolve()) for s in sources)
    pending, videos, whole = [], [], set()
    for job in jobs:
        if job["type"] != "video":
            pending.append(job)
            continue
        d = run.render_dir / "chunks" / run.name / _key(job, shared)
        d.mkdir(parents=True, exist_ok=True)
        # a chunk that passed its checks before its command was killed is published now, the same way as after invoke
        for part in d.glob("*.part.mp4"):
            _publish(run, ffprobe, part)
        for part in d.glob("*.part.*"):
            part.unlink()
        parts = []
        for a, b in _plan(job):
            done = d / f"{a}-{b}.mp4"
            if _frames(run, ffprobe, done) == b - a + 1:
                whole.add(done)
            else:
                pending.append({**job, "frameRange": [a, b], "out": str(d / f"{a}-{b}.part.mp4")})
            parts.append((done, b - a + 1))
        videos.append((job, d, parts))
    kept = len(whole)
    report = invoke(pending, run.spawn) if pending else {"findings": []}
    stills = [j for j in pending if j["type"] != "video"]
    findings, refused, published = [], set(), set()
    for j in pending:
        if j["type"] != "video":
            continue
        done = _publish(run, ffprobe, Path(j["out"]))
        if isinstance(done, str):
            findings.append({"job": j["out"], "text": done})
        elif done:
            published.add(j["out"])
            whole.add(done)
    for f in report.get("findings") or []:
        if f["job"] not in published:
            findings.append(f)
            if f["text"].startswith("RENDER_ERROR"):
                refused.add(f["job"])
    failed = sum(1 for j in stills if j["out"] in refused)
    for job, d, parts in videos:
        for done, _ in parts:
            found = done.with_suffix(".findings.json")
            if done in whole and found.exists():
                findings += json.loads(found.read_text(encoding="utf-8"))
        if not all(done in whole for done, _ in parts) or not _join(run, job, d, parts, ffmpeg, ffprobe, findings):
            failed += 1
    to_go = sum(len(parts) for _, _, parts in videos) - len(whole)
    if videos:
        print(f"render {run.name}: {kept} chunks kept, {len(whole) - kept} rendered, {to_go} to go")
    return {"jobs": len(jobs), "failed": failed, "findings": findings, "seconds": round(time.monotonic() - t0, 1),
            "chunks": {"kept": kept, "rendered": len(whole) - kept, "to_go": to_go}, "gl": report.get("gl"),
            "card": report.get("card")}


def _join(run, job, d, parts, ffmpeg, ffprobe, findings):
    out = Path(job["out"])
    first, last = job.get("frameRange") or (0, job["frames"] - 1)
    listing = d / "chunks.part.txt"
    quote = lambda p: p.resolve().as_posix().replace("'", "'\\''")
    listing.write_text("".join(f"file '{quote(p)}'\n" for p, _ in parts), encoding="utf-8")
    tmp = out.with_name(f"{out.stem}.join{out.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    # a join a killed command left behind is never counted as this one's
    tmp.unlink(missing_ok=True)
    rate = run.spawn([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of",
                      "csv=p=0", str(parts[0][0])], capture_output=True, text=True).stdout.strip()
    # the concat demuxer places each chunk in whole microseconds, so the join's clock ticks once a frame to keep every
    # frame on its own tick
    r = run.spawn([ffmpeg, "-hide_banner", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", "-video_track_timescale", rate.split("/")[0] or "30", str(tmp)],
                  capture_output=True, text=True)
    listing.unlink()
    n = _frames(run, ffprobe, tmp) if r.returncode == 0 else -1
    if n != last - first + 1:
        tmp.unlink(missing_ok=True)
        text = f"RENDER_ERROR join {out.name}: ffmpeg exited {r.returncode}, {max(n, 0)} frames of {last - first + 1}; ffmpeg: {r.stderr.strip()[-600:] or 'no error'}"
        findings.append({"job": job["out"], "text": text})
        print(text)
        return False
    os.replace(_synced(tmp), out)
    return True
