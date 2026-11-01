#!/usr/bin/env python3
"""Renders the studio composition with python3, ffmpeg and a Chromium: nothing else is installed or downloaded.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/render.py --run R --board reel --out film.mp4 [--scale 0.5]   # one board's film, with the music and its effects
    python3 S/scripts/render.py --run R --board reel --still 120 --out cover.png     # one frame of it
    python3 S/scripts/render.py --jobs JOBS.json                                     # what studio.render runs

--board is a profile of the run's film.json `boards` or a board file. The film goes through studio.render's jobs
and checks, without its chunks: film.py preview and render are the commands that keep chunks and stage the outputs.

How it renders. motion/dist/ is the composition built into static files (scripts/dev/build_motion.py makes it). It
is served on a loopback port with the run's public/ folder at /public/, where the composition reads its photographs,
fonts and grain. The Chromium starts headless with a profile and a runtime folder of its own under the cache
(~/.cache/code-config/<kit>/, or under XDG_CACHE_HOME when that is set) and is driven over the DevTools protocol by a
WebSocket client written here. Each job selects the composition with its props, steps every frame and waits for the
composition's ready signal before the screenshot (a frame is never taken on a timer), a lossless PNG that Chromium
compresses at its fastest setting. A frame is set inside a click, so React commits it before that signal can read
true (PRELUDE). Each frame goes into ffmpeg's input as it arrives, in frame order (a frame that
arrives ahead of its turn goes in from its file on disk once the frames before it are in), and is kept on disk for the
frames cache. ffmpeg encodes them to yuv420p at the composition's size and frame rate, with h264_nvenc on the NVIDIA
card, with h264_videotoolbox on a Mac whose ffmpeg has it, and with libx264 otherwise: the encoder is tried once per
process on one frame at each film's size, a size the card or driver refuses (one smaller than the card's smallest
frame) encodes with libx264, and a film the card's encoder fails partway renders again on the next attempt with
libx264.
With the NVIDIA device the browser draws on the card through ANGLE on Vulkan. Without it the browser draws on the
CPU: through ANGLE on Vulkan on Mesa's lavapipe (the mesa-vulkan-drivers package) when the machine has it, otherwise
through ANGLE on SwiftShader, Chromium's own. lavapipe draws a frame for about a quarter of SwiftShader's CPU time,
and its frames are as near the card's or nearer; a render on SwiftShader says so once. A browser draws and captures
its pages one at a time, so a film runs one page in each of several browsers, all taking the next frame from one
queue: PER_BROWSER gives the cores each browser keeps busy, and the pool is that share of the cores this process may
use (its CPU affinity, lowered to its cgroup's CPU quota), up to 8, and no larger than the memory left holds
(MemAvailable, lowered to what its cgroup has left under memory.max) at BROWSER_BYTES each, with one share kept for
ffmpeg and this process. lavapipe and SwiftShader draw each frame on a thread for each of those cores already. Every
browser is started from the thread that renders the jobs and serves every job of the process.

VS_GPU=0 renders as a machine without the card does (the browser draws on the CPU, libx264 encodes), on a machine
that has one. VS_TIMING=1 writes <film>.timing.json beside each film: the seconds each frame spent in each stage and
the film's marks (Timing).

A frame that is not ready in 30 s stops the render, naming the frame and what it still waited for. Any other failure
(a browser that stops answering, a lost graphics context, a render that comes out one flat color) costs one attempt,
and attempts 2 and 3 run in a fresh browser. A video job whose `frames` differs from the composition's is refused.

The frames cache. A film's frames are kept in the cache's frames/ folder, each under its key: the hash of what decides
that frame's pixels (frame_keys: the props that reach the frame, the composition's size and length, the scale, the
frame number, and by content the bundle, the public folder, the browser and this file). A render paints only the
frames whose keys it does not find there and takes the others from the cache, in frame order, into the same ffmpeg
input. A frame's key takes every beat before it whole (a wall gathers the photographs before it) and a later beat
without its words, so a render after an edit to one beat's words paints from the beat before it, or from AHEAD seconds
before it, to the end of the film, and a render with no edit paints none. A film's painted frames enter the cache once
it passes its checks with no finding, and the cache keeps its newest frames (by when each was last painted or reused)
under FRAMES_CAP bytes. Until then they wait in a staging folder the render holds locked; a render removes every
staging folder no render holds, such as the one a killed render leaves.

An `out` ending in `.part.mp4` is a chunk (scripts/chunks.py): once it passes its checks its findings are written
beside it as `.part.findings.json`. The jobs file's report lists every job that failed and every FONT_ERROR and
IMAGE_ERROR line the composition logged.

Chromium is found in this order: CHROME_PATH; Playwright's Chromium (PLAYWRIGHT_BROWSERS_PATH, ~/.cache/ms-playwright,
~/Library/Caches/ms-playwright; a headless shell before a full build, the newest revision first); chromium,
chromium-browser, google-chrome, google-chrome-stable on PATH; the macOS applications; a Remotion headless shell
already on disk under motion/node_modules. The headless shell is first because it composites each frame on the card,
where a full build in its new headless mode composites in software and takes about twice the time per frame.
"""
import argparse
import atexit
import base64
import bisect
import collections
import contextlib
import hashlib
import http.server
import inspect
import itertools
import json
import os
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
DIST = KIT / "motion" / "dist"
# a frame that is not ready this long after it was asked for stops the render; the composition's own delayRender
# timeout is 2 s shorter, so its message, naming what it waited for, usually arrives first
READY_MS = 30_000
# VS_GPU=0 renders as a machine without the NVIDIA card does
GPU = os.path.exists("/dev/nvidia0") and os.environ.get("VS_GPU") != "0"
TIMING = os.environ.get("VS_TIMING") == "1"
# a film's memory share for each of its browsers and one more for ffmpeg and this process, at the peak of 1080 by 1920
# on the CPU: the tree measured about 500 MB and 440 MB a browser on SwiftShader, and about 530 MB and 600 to 710 MB a
# browser on lavapipe, the lit three.js kits the most (about 300 MB a browser on the card)
BROWSER_BYTES = 768 << 20
# the usable cores one browser keeps busy with each graphics backend, measured on 1080 by 1920 films
PER_BROWSER = {"vulkan": 2, "lavapipe": 2, "swiftshader": 4}
CGROUP, SELF_CGROUP, MEMINFO = Path("/sys/fs/cgroup"), Path("/proc/self/cgroup"), Path("/proc/meminfo")
# where the Vulkan loader finds drivers; lavapipe's is lvp_icd*.json
VULKAN_DRIVERS = (Path("/usr/share/vulkan/icd.d"), Path("/etc/vulkan/icd.d"), Path("/usr/local/share/vulkan/icd.d"))
GL_LOST = re.compile(r"Context Lost|context could not be created|Error creating WebGL context|Shader Error", re.I)
FINDING = re.compile(r"^(FONT_ERROR|IMAGE_ERROR)")
MAC_APPS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"))
REMOTION_SHELLS = KIT / "motion" / "node_modules" / ".remotion" / "chrome-headless-shell"
# each encoder setting aims at constant quality under one ceiling, 12 Mbit/s over a 24 Mbit buffer: every platform the
# reel is posted to encodes it again, so bits above that buy nothing a viewer sees
CEILING = ["-maxrate", "12M", "-bufsize", "24M"]
# A beat that starts within AHEAD seconds of a frame, or right after the frame's own beat, reaches that frame whole:
# a photograph slides in, a card's words rise and the camera travels toward the next beat before it starts.
AHEAD = 2.0
# The keys whose strings are words a person reads, in every kit's board: a beat later than that reaches a frame
# without them, and without its lines of text (a dict with a typeface named in `face`), since its words show only near
# its own time.
WORDS = frozenset({"text", "words", "label", "say", "said", "caption", "title", "signoff", "handle", "idea", "scene",
                   "shows", "held", "carries", "reveals", "what"})
# A 1080 by 1920 frame of photographs is up to about 3.4 MB, so the cache holds at least 3,000 of them: the longest film
# a kit makes (60 s, 1,800 frames) and the frames its next edit paints.
FRAMES_CAP = 10 * 2 ** 30
ENCODERS = {
    # spatial adaptive quantization keeps the grain in a dark dissolve, which the card's encoder flattens into patches
    # without it: under the ceiling a lower cq buys nothing there
    "h264_nvenc": ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", *CEILING,
                   "-spatial-aq", "1", "-profile:v", "high"],
    "h264_videotoolbox": ["-c:v", "h264_videotoolbox", "-q:v", "65", "-allow_sw", "0", *CEILING, "-profile:v", "high"],
    # veryfast holds SSIM against the frames within 0.001 of medium at this crf and ceiling, for half the CPU
    "libx264": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", *CEILING],
}


class Failed(Exception):
    """A job's attempt failed; the next attempt runs in a fresh browser."""


class Refused(Failed):
    """The job cannot render as asked; no attempt runs again."""


class Stopped(Failed):
    """A frame never got ready: the render stops."""


def cache():
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return root / "code-config" / KIT.name


def _executable(p):
    return p.is_file() and os.access(p, os.X_OK)


def _revision(p, root):
    m = re.search(r"-(\d+)$", p.relative_to(root).parts[0])
    return int(m.group(1)) if m else 0


def chromium():
    """The Chromium a render starts, in the order the module docstring gives, or None."""
    forced = os.environ.get("CHROME_PATH")
    if forced and _executable(Path(forced)):
        return forced
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), Path.home() / ".cache" / "ms-playwright",
             Path.home() / "Library" / "Caches" / "ms-playwright"]
    for kind, names in (("chromium_headless_shell-*", ("*/chrome-headless-shell", "*/headless_shell", "*/chrome-headless-shell.exe")),
                        ("chromium-*", ("*/chrome", "*/chrome.exe", "*/*.app/Contents/MacOS/*"))):
        for root in (Path(r) for r in roots if r):
            hits = [p for n in names for p in root.glob(f"{kind}/{n}") if _executable(p)] if root.is_dir() else []
            if hits:
                return str(max(hits, key=lambda p: _revision(p, root)))
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        if shutil.which(name):
            return shutil.which(name)
    for p in MAC_APPS:
        if _executable(Path(p)):
            return p
    hits = sorted(p for p in REMOTION_SHELLS.glob("*/*/chrome-headless-shell*") if _executable(p)) if REMOTION_SHELLS.is_dir() else []
    return str(hits[-1]) if hits else None


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def _tree(root):
    """The digest of every file under `root`, by relative path and content."""
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        if p.is_file():
            h.update(f"{p.relative_to(root).as_posix()}\0".encode() + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def frame_inputs(dist, public, exe, gl):
    """What reaches every frame besides its props: the bundle and the public folder by content, the browser and its
    graphics, and this file."""
    try:
        st = os.stat(exe)
        browser = [exe, st.st_size, st.st_mtime_ns]
    except OSError:
        browser = [exe]
    own = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return _sha(_canon([_tree(dist), _tree(public), browser, gl, own]))


def _line(x):
    """A line of text: a dict that names the typeface it is set in. A photograph's `face` is the box its face is in, a
    list, so a photograph is never a line."""
    return isinstance(x, dict) and isinstance(x.get("face"), str)


def _words(k, v):
    return k in WORDS and (isinstance(v, str) or (isinstance(v, list) and bool(v) and all(isinstance(w, str) for w in v)))


def _wordless(x):
    """`x` without its words: every WORDS string or list of strings, and every line of text."""
    if isinstance(x, dict):
        return {k: _wordless(v) for k, v in x.items() if not _line(v) and not _words(k, v)}
    if isinstance(x, list):
        return [_wordless(v) for v in x if not _line(v)]
    return x


def frame_keys(job, comp, frames, inputs):
    """The key of each of `frames` of a film job, the hash of what decides its pixels. A board whose beats' `frames`
    add up to the composition's length is the film's timeline: frame f takes whole every beat up to the one after its
    own and every beat that starts within AHEAD seconds of it, and every later beat without its words, since a later
    beat can show its photograph early (a title that flashes every photograph) but its words only near its own time.
    The rest of the props, the composition's size, rate and length, the scale, the frame number and `inputs`
    (frame_inputs) reach every frame. Props with no such timeline reach every frame whole."""
    props = job["props"]
    head = _canon([inputs, comp["id"], comp["width"], comp["height"], comp["fps"], comp["durationInFrames"],
                   job.get("scale") or 1])
    board = props.get("board") if isinstance(props, dict) else None
    beats = board.get("beats") if isinstance(board, dict) else None
    lengths = [b.get("frames") if isinstance(b, dict) else None for b in beats] if isinstance(beats, list) else []
    if not lengths or not all(type(n) is int and n > 0 for n in lengths) or sum(lengths) != comp["durationInFrames"]:
        whole = _sha(head + _canon(props))
        return {f: _sha(f"{whole}\0{f}") for f in frames}
    common = head + _canon({**props, "board": {**board, "beats": len(beats)}})
    whole = [_sha(_canon(b)) for b in beats]
    bare = [_sha(_canon(_wordless(b))) for b in beats]
    starts = list(itertools.accumulate(lengths, initial=0))
    slices, keys = {}, {}
    for f in frames:
        own = bisect.bisect_right(starts, f) - 1
        near = bisect.bisect_right(starts, f + AHEAD * comp["fps"], 0, len(beats)) - 1
        live = min(len(beats) - 1, max(own + 1, near))
        if live not in slices:
            slices[live] = _sha(common + "".join(whole[:live + 1]) + "".join(bare[live + 1:]))
        keys[f] = _sha(f"{slices[live]}\0{f}")
    return keys


def trim(folder, cap):
    """Removes the frames cache's oldest frames, by when each was last painted or reused, until `folder` holds `cap`
    bytes of them or fewer. A render's own folder of painted frames is left alone."""
    found = []
    try:
        for e in os.scandir(folder):
            if e.name.endswith(".png") and e.is_file():
                with contextlib.suppress(FileNotFoundError):
                    st = e.stat()
                    found.append((st.st_mtime_ns, st.st_size, e.path))
    except FileNotFoundError:
        return
    total = sum(size for _, size, _ in found)
    for _, size, path in sorted(found):
        if total <= cap:
            return
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
        total -= size


def private_dir(parent, prefix):
    """A new folder only this user can open, under `parent`."""
    Path(parent).mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


def stage(store, stem):
    """A new private folder under the frames cache for a render's painted frames, and the open file that locks it for
    the render's life. Every staging folder no render holds is removed first: a lock ends with its process however that
    process ends, a kill included. A folder made in the last minute is left alone, for the render between making it and
    locking it."""
    import fcntl
    Path(store).mkdir(parents=True, exist_ok=True)
    for e in os.scandir(store):
        with contextlib.suppress(OSError):
            if not e.is_dir(follow_symlinks=False) or time.time() - e.stat().st_mtime < 60:
                continue
            fd = os.open(e.path, os.O_RDONLY)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                shutil.rmtree(e.path, ignore_errors=True)
            finally:
                os.close(fd)
    folder = private_dir(store, f"{stem}-")
    hold = os.open(folder, os.O_RDONLY)
    fcntl.flock(hold, fcntl.LOCK_EX)
    return folder, hold


def headless(exe):
    """A headless shell takes the plain flag; a full Chromium takes the new headless mode, as open-browser.js does."""
    return "--headless" if "headless" in Path(exe).name else "--headless=new"


def browser_env(runtime, gl=None):
    """The browser's environment: its own runtime folder, and no accessibility bridge to the desktop's bus. On lavapipe
    the Vulkan loader sees lavapipe's driver alone (VK_DRIVER_FILES, and VK_ICD_FILENAMES for a loader older than
    1.3.234), and lavapipe draws on a thread for each usable core."""
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), NO_AT_BRIDGE="1")
    if gl == "lavapipe":
        env.update(VK_DRIVER_FILES=lavapipe(), VK_ICD_FILENAMES=lavapipe(), LP_NUM_THREADS=str(usable_cores()))
    return env


# ---------------------------------------------------------------------------------------------------------- WebSocket

class WebSocket:
    """A client of RFC 6455 enough for the DevTools protocol: text messages out, masked; text messages in, whole,
    across the three length forms and continuation frames; a ping answered with its pong; a close ends the socket."""
    GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, url, timeout):
        u = urllib.parse.urlsplit(url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        key = base64.b64encode(os.urandom(16))
        self.sock.sendall(b"GET " + (u.path or "/").encode() + b" HTTP/1.1\r\nHost: " + f"{u.hostname}:{u.port}".encode()
                          + b"\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key
                          + b"\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.buf = bytearray()
        while b"\r\n\r\n" not in self.buf:
            self._fill()
        head, _, rest = bytes(self.buf).partition(b"\r\n\r\n")
        self.buf = bytearray(rest)
        lines = head.split(b"\r\n")
        headers = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(b":") for ln in lines[1:])}
        want = base64.b64encode(hashlib.sha1(key + self.GUID).digest())
        if b" 101 " not in lines[0] + b" " or headers.get(b"sec-websocket-accept") != want:
            self.sock.close()
            raise ConnectionError(f"the browser refused the DevTools connection: {lines[0].decode(errors='replace')}")

    def settimeout(self, seconds):
        self.sock.settimeout(seconds)

    def _fill(self):
        data = self.sock.recv(1 << 20)
        if not data:
            raise ConnectionError("the browser closed the DevTools connection")
        self.buf += data

    def _take(self, n):
        while len(self.buf) < n:
            self._fill()
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def _send(self, op, payload):
        n = len(payload)
        head = bytes([0x80 | op])
        head += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        whole = (mask * (n // 4 + 1))[:n]
        masked = (int.from_bytes(payload, "little") ^ int.from_bytes(whole, "little")).to_bytes(n, "little") if n else b""
        self.sock.sendall(head + mask + masked)

    def send(self, text):
        self._send(0x1, text.encode())

    def recv(self):
        parts = []
        while True:
            b0, b1 = self._take(2)
            n = b1 & 0x7F
            n = struct.unpack(">H", self._take(2))[0] if n == 126 else struct.unpack(">Q", self._take(8))[0] if n == 127 else n
            mask = self._take(4) if b1 & 0x80 else None
            data = self._take(n)
            if mask:
                whole = (mask * (n // 4 + 1))[:n]
                data = (int.from_bytes(data, "little") ^ int.from_bytes(whole, "little")).to_bytes(n, "little")
            op = b0 & 0x0F
            if op == 0x9:
                self._send(0xA, data)
            elif op == 0x8:
                raise ConnectionError("the browser closed the DevTools connection")
            elif op in (0x0, 0x1, 0x2):
                parts.append(data)
                if b0 & 0x80:
                    return b"".join(parts).decode()

    def close(self):
        try:
            self._send(0x8, b"")
        except OSError:
            pass
        self.sock.close()


# --------------------------------------------------------------------------------------------------------- DevTools

class Cdp:
    """The DevTools protocol over one WebSocket, with flat sessions: `send` returns the message id, `reply` waits for
    it, and every event goes to `on_event` as it arrives."""

    def __init__(self, ws, on_event):
        self.ws, self.on_event, self.next, self.replies, self.ignored, self.asked = ws, on_event, 0, {}, set(), {}

    def send(self, method, params=None, session=None):
        self.next += 1
        msg = {"id": self.next, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        if TIMING:
            stage = ("shot" if method == "Page.captureScreenshot" else
                     "seek" if str((params or {}).get("expression", "")).startswith("window.__vs_seek(") else None)
            if stage:
                self.asked[self.next] = (stage, time.monotonic())
        self.ws.send(json.dumps(msg))
        return self.next

    def pump(self, until):
        """Reads one message, waiting until the monotonic time `until` at most."""
        left = until - time.monotonic()
        if left <= 0:
            raise TimeoutError
        self.ws.settimeout(left)
        try:
            msg = json.loads(self.ws.recv())
        except socket.timeout:
            raise TimeoutError from None
        if "id" in msg:
            asked, clock = self.asked.pop(msg["id"], None), Timing.now
            if asked and clock:
                clock.stages[asked[0]].append(time.monotonic() - asked[1])
            if msg["id"] in self.ignored:
                self.ignored.discard(msg["id"])
            else:
                self.replies[msg["id"]] = msg
        else:
            self.on_event(msg)

    def first(self, ids, seconds):
        """The first reply among `ids` to arrive: (id, message)."""
        until = time.monotonic() + seconds
        while True:
            for i in ids:
                if i in self.replies:
                    return i, self.replies.pop(i)
            self.pump(until)

    def call(self, method, params=None, session=None, seconds=30):
        try:
            _, msg = self.first([self.send(method, params, session)], seconds)
        except TimeoutError:
            raise Failed(f"the browser did not answer {method} in {seconds} s") from None
        if "error" in msg:
            raise Failed(f"{method}: {msg['error'].get('message')} {msg['error'].get('data') or ''}".strip())
        return msg.get("result") or {}

    def evaluate(self, expression, session, seconds=30):
        r = self.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True}, session, seconds)
        return value(r)


def value(result):
    """A Runtime.evaluate result's value, or the page's error as Failed."""
    if "exceptionDetails" in result:
        d = result["exceptionDetails"]
        text = (d.get("exception") or {}).get("description") or d.get("text") or "the page threw"
        first = (text.splitlines() or [""])[0]
        raise Failed((first[len("Error: "):] if first.startswith("Error: ") else first)[:1500])
    return (result.get("result") or {}).get("value")


# Set before the bundle's own scripts run in every page, as @remotion/renderer's set-props-and-env.js sets them, and
# the seek that renderer's seek-to-frame.js runs: wait for ready, set the frame, wait for ready, wait for the fonts.
# The frame is set inside a click dispatched on a target of the seek's own. React gives an update made during a click
# its synchronous lane, so the composition renders frame f, commits it and runs its effects in the microtask after the
# call, and every hold it takes for frame f is open before the animation frame on which remotion_setFrame ends its own
# hold. An update made outside an event waits for a scheduler task, and on a starved page that animation frame comes
# first: ready reads true while the page still shows the frame before, and the screenshot is of that frame.
PRELUDE = r"""
window.remotion_puppeteerTimeout = %(timeout)d;
window.remotion_isMainTab = %(main)s;
window.remotion_mediaCacheSizeInBytes = null;
window.remotion_initialMemoryAvailable = %(memory)d;
window.remotion_sampleRate = 48000;
if (window.process === undefined) window.process = {};
if (window.process.env === undefined) window.process.env = {};
window.process.env.NODE_ENV = 'production';
window.remotion_broadcastChannel = new BroadcastChannel('remotion-video-frame-extraction');
window.remotion_inputProps = %(props)s;
window.remotion_initialFrame = %(frame)d;
window.remotion_attempt = 1;
window.remotion_proxyPort = null;
window.remotion_audioEnabled = false;
window.remotion_videoEnabled = true;
window.remotion_logLevel = 'info';
window.alert = (m) => { window.remotion_cancelledError = new Error(`alert(${m ?? ''}) was called; a headless browser cannot show it`).stack; };
window.confirm = (m) => { window.remotion_cancelledError = new Error(`confirm(${m ?? ''}) was called; a headless browser cannot show it`).stack; return false; };
window.__vs_ready = (what) => new Promise((resolve, reject) => {
  const until = performance.now() + %(timeout)d;
  const tick = () => {
    if (window.remotion_renderReady === true) return resolve(true);
    if (window.remotion_cancelledError !== undefined) return reject(new Error(`STOP ${what}: the composition cancelled the render: ${String(window.remotion_cancelledError).split('\n')[0]}`));
    if (performance.now() > until) {
      const open = Object.values(window.remotion_delayRenderTimeouts || {}).map((h) => h.label || '(no label)');
      return reject(new Error(`STOP ${what} did not get ready in %(seconds)d s; it was waiting for: ${open.join(', ') || 'nothing it named'}`));
    }
    requestAnimationFrame(tick);
  };
  tick();
});
window.__vs_clicks = new EventTarget();
window.__vs_seek = async (f, comp) => {
  await window.__vs_ready(`frame ${f}`);
  let thrown;
  window.__vs_clicks.addEventListener('click', () => {
    try { window.remotion_setFrame(f, comp, 1); } catch (e) { thrown = e; }
  }, {once: true});
  window.__vs_clicks.dispatchEvent(new Event('click'));
  if (thrown !== undefined) throw thrown;
  await window.__vs_ready(`frame ${f}`);
  await document.fonts.ready;
  return true;
};
"""


def memory():
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return 4 << 30


def _cgroups():
    """This process's cgroup v2 folder and every folder above it, nearest first; none off Linux."""
    try:
        rel = next(ln[3:].strip() for ln in SELF_CGROUP.read_text().splitlines() if ln.startswith("0::"))
    except (OSError, StopIteration):
        return []
    d = CGROUP / rel.lstrip("/")
    return [d, *d.parents[:len(d.relative_to(CGROUP).parts)]]


def usable_cores():
    """The cores this process may use: its CPU affinity, lowered to the CPU quota (cpu.max, rounded up) of its cgroup
    or of any cgroup above it."""
    try:
        n = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        n = os.cpu_count() or 1
    for d in _cgroups():
        try:
            quota, period = (d / "cpu.max").read_text().split()[:2]
            if quota != "max":
                n = min(n, max(1, -(-int(quota) // int(period))))
        except (OSError, ValueError):
            continue
    return n


def usable_memory():
    """The bytes this process can still take: the machine's MemAvailable, lowered to what its cgroup or any cgroup
    above it has left under memory.max."""
    try:
        left = next(int(ln.split()[1]) << 10 for ln in MEMINFO.read_text().splitlines()
                    if ln.startswith("MemAvailable:"))
    except (OSError, StopIteration, ValueError, IndexError):
        left = memory()
    for d in _cgroups():
        try:
            limit = (d / "memory.max").read_text().strip()
            if limit != "max":
                left = min(left, int(limit) - int((d / "memory.current").read_text()))
        except (OSError, ValueError):
            continue
    return max(0, left)


def pool_size(gl):
    """The browsers a film renders in side by side with `gl`, at least one: one for every PER_BROWSER[gl] usable cores,
    up to 8, and no more than the usable memory holds at BROWSER_BYTES each after one share for ffmpeg and this process."""
    return max(1, min(8, usable_cores() // PER_BROWSER[gl], usable_memory() // BROWSER_BYTES - 1))


def lavapipe():
    """This machine's lavapipe driver files (Mesa's Vulkan on the CPU), joined as the Vulkan loader reads a list, or
    an empty string."""
    return os.pathsep.join(str(p) for d in VULKAN_DRIVERS if d.is_dir() for p in sorted(d.glob("lvp_icd*.json")))


def backend(gl):
    """The graphics backend a render draws with for `gl`: auto is Vulkan on the NVIDIA card, otherwise lavapipe when
    the machine has it and SwiftShader when not. lavapipe on a machine without it is refused, and SwiftShader on Linux
    says once that lavapipe would draw faster."""
    gl = ("vulkan" if GPU else "lavapipe" if lavapipe() else "swiftshader") if gl == "auto" else gl
    if gl == "lavapipe" and not lavapipe():
        raise SystemExit("lavapipe is not on this machine: install Mesa's Vulkan drivers (mesa-vulkan-drivers), or "
                         "leave --gl at auto")
    if gl == "swiftshader" and sys.platform.startswith("linux") and not lavapipe():
        print("drawing on the CPU with SwiftShader: with Mesa's lavapipe installed (mesa-vulkan-drivers) each frame "
              "takes about a quarter of the CPU time", file=sys.stderr, flush=True)
    return gl


class Browser:
    """One headless Chromium with its own profile and runtime folder, and its DevTools connection."""

    def __init__(self, exe, gl, wait=True):
        """Starts the browser; with `wait=False` the wait for its DevTools is left to `ready`."""
        self.root = private_dir(cache() / "browser", "chromium-")
        (self.root / "run").mkdir(mode=0o700)
        self.log_path = self.root / "stderr.log"
        self.findings, self.lost, self.errors, self.crashed = collections.defaultdict(list), {}, {}, None
        # @remotion/renderer's open-browser.js: its flags, and its two graphics backends: Vulkan (the card's, or
        # lavapipe's on the CPU) and SwiftShader
        angle = (["--use-angle=vulkan", "--use-vulkan=native", "--disable-vulkan-fallback-to-gl-for-testing",
                  "--disable-vulkan-surface", "--enable-gpu", "--enable-features=Vulkan,UseSkiaRenderer"]
                 if gl in ("vulkan", "lavapipe") else ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        args = [exe, headless(exe), "--remote-debugging-port=0", f"--user-data-dir={self.root / 'profile'}", "about:blank",
                "--no-sandbox", "--disable-setuid-sandbox", "--no-first-run", "--no-default-browser-check", "--no-zygote",
                "--disable-background-networking", "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows", "--disable-renderer-backgrounding", "--disable-breakpad",
                "--disable-component-update", "--disable-default-apps", "--disable-dev-shm-usage", "--disable-extensions",
                "--disable-hang-monitor", "--disable-ipc-flooding-protection", "--disable-popup-blocking", "--disable-sync",
                "--disable-features=Translate,BackForwardCache,IntensiveWakeUpThrottling,LocalNetworkAccessChecks",
                "--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars", "--mute-audio",
                "--ignore-gpu-blocklist", "--force-gpu-mem-available-mb=4096", "--password-store=basic",
                "--use-mock-keychain", "--no-proxy-server", "--metrics-recording-only", *angle]
        with open(self.log_path, "wb") as log:
            self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=log,
                                         env=browser_env(self.root / "run", gl), start_new_session=True,
                                         preexec_fn=_die_with_parent)
        LIVE.add(self)
        self.exe, self.until, self.cdp, self.sessions = exe, time.monotonic() + 30, None, {}
        if wait:
            self.ready()

    def ready(self):
        """Waits for the browser's DevTools, up to 30 s from its start, and connects to it; a browser already
        connected returns at once."""
        url = None
        while self.cdp is None and not url:
            m = re.search(r"DevTools listening on (ws://\S+)", self.log_path.read_text(errors="replace"))
            if m:
                url = m.group(1)
            elif self.proc.poll() is not None or time.monotonic() > self.until:
                tail = self.log_path.read_text(errors="replace")[-800:]
                self.close()
                raise Failed(f"the browser did not start ({self.exe}): {tail.strip() or 'no output'}")
            else:
                time.sleep(0.05)
        if url:
            self.cdp = Cdp(WebSocket(url, 30), self.event)

    def event(self, msg):
        method, p = msg.get("method"), msg.get("params") or {}
        job = self.sessions.get(msg.get("sessionId"))
        if method == "Runtime.consoleAPICalled":
            text = " ".join(str(a["value"]) if "value" in a else a.get("description", "") for a in p.get("args") or [])
        elif method == "Log.entryAdded":
            entry = p.get("entry") or {}
            text = entry.get("text", "")
            # a photograph or a font the page could not load leaves its place in the frame empty: the render fails
            if entry.get("source") == "network" and entry.get("level") == "error" and "favicon.ico" not in (entry.get("url") or ""):
                text = f"{text} {entry.get('url') or ''}".strip()
                print(f"page error: {text[:300]}", file=sys.stderr)
                if job is not None:
                    self.errors.setdefault(job, text[:300])
                return
        elif method == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails") or {}
            text = ((d.get("exception") or {}).get("description") or d.get("text") or "").splitlines()[0:1]
            text = text[0] if text else ""
            print(f"page error: {text[:300]}", file=sys.stderr)
            if job is not None:
                self.errors.setdefault(job, text[:300])
            return
        elif method in ("Inspector.targetCrashed", "Target.targetCrashed"):
            self.crashed = "the browser's page crashed"
            return
        elif method == "Target.detachedFromTarget" and p.get("sessionId") in self.sessions:
            self.crashed = "the browser closed a page it was rendering"
            return
        else:
            return
        if job is None:
            return
        if GL_LOST.search(text):
            self.lost.setdefault(job, text[:300])
        # each page writes the line, and Chrome reports a console line in both domains: a finding is listed once
        if FINDING.search(text) and text not in self.findings[job]:
            self.findings[job].append(text)
            print(text[:300], file=sys.stderr)

    def tab(self, job, url, props, frame, main):
        """A page attached as a flat session, the prelude set, the bundle loaded at `url`."""
        # a window of its own: a headless page that shares a window with a newer one is hidden, and a hidden page runs
        # no animation frames, so its composition would never get ready
        target = self.cdp.call("Target.createTarget", {"url": "about:blank", "newWindow": True})["targetId"]
        session = self.cdp.call("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        self.sessions[session] = job
        for m in ("Runtime.enable", "Page.enable", "Log.enable"):
            self.cdp.call(m, session=session)
        self.cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": PRELUDE % {
            "timeout": READY_MS, "seconds": READY_MS // 1000, "main": "true" if main else "false", "memory": memory(),
            "props": json.dumps(json.dumps(props)), "frame": frame}}, session)
        self.cdp.call("Page.navigate", {"url": url}, session)
        self.cdp.evaluate("new Promise((r) => document.readyState === 'complete' ? r(true) : addEventListener('load', () => r(true)))", session)
        if self.cdp.evaluate("typeof window.getStaticCompositions", session) == "undefined":
            raise Refused(f"{url} is not a composition bundle (window.getStaticCompositions is missing)")
        site = self.cdp.evaluate("window.siteVersion", session)
        if site != "11":
            raise Refused(f"the bundle's site version is {site}, and this renderer speaks version 11: rebuild motion/dist")
        return {"target": target, "session": session}

    def close_tab(self, tab):
        self.sessions.pop(tab["session"], None)
        try:
            self.cdp.call("Target.closeTarget", {"targetId": tab["target"]}, seconds=5)
        except (Failed, OSError):
            pass

    def close(self):
        """Ends the browser and every process it started (its own process group), then removes its folder."""
        LIVE.discard(self)
        if getattr(self, "cdp", None):
            try:
                self.cdp.send("Browser.close")
            except OSError:
                pass
        try:
            self.proc.wait(3)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, AttributeError):
            pass
        self.proc.wait()
        if getattr(self, "cdp", None):
            self.cdp.ws.close()
        shutil.rmtree(self.root, ignore_errors=True)


# every browser still open when this process ends, by any path: an exception, a stop signal, or the end of a test
LIVE = set()
atexit.register(lambda: [b.close() for b in list(LIVE)])


def _die_with_parent():
    """In the browser's process before it starts, on Linux: the kernel kills it when the thread that started it ends,
    and so when this process dies, even by a signal that runs no handler."""
    if sys.platform.startswith("linux"):
        import ctypes
        ctypes.CDLL(None).prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG


# ----------------------------------------------------------------------------------------------------------- serving

def serve(dist, public):
    """dist at / and the run's public folder at /public/ on a loopback port; returns (server, base url)."""
    dist, public = Path(dist).resolve(), Path(public).resolve()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
            root, rest = (public, path[len("/public/"):]) if path.startswith("/public/") else (dist, path.lstrip("/"))
            target = (root / rest).resolve()
            return str(target if target == root or root in target.parents else root / "missing")

        def log_message(self, *args):
            pass

    class Server(http.server.ThreadingHTTPServer):
        # every page of every chunk asks for its photographs at once; a short listen queue refuses some of them
        request_queue_size = 256
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/index.html"


# ------------------------------------------------------------------------------------------------------------ checks

def _flat(rgb):
    n = len(rgb) // 3
    for c in range(3):
        ch = rgb[c::3]
        mean = sum(ch) / n
        if sum(x * x for x in ch) / n - mean * mean >= 1:
            return False
    return True


def refuse_blank(ffmpeg, out, video):
    """Raises Failed when any frame is one flat color (a video's every frame, a still's one frame), naming the first
    such frame and its time, or when the output does not decode: each frame is decoded at 64 x 64 and is flat when no
    color channel's standard deviation reaches 1."""
    out = Path(out)
    side = 64
    rgb = subprocess.run([ffmpeg, "-v", "error", "-i", str(out), "-vf", f"scale={side}:{side}:flags=area", "-pix_fmt", "rgb24",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    k = side * side * 3
    if len(rgb) < k:
        raise Failed(f"blank render: no frame of {out.name} decodes")
    fps = 0.0
    if video:
        r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(out)], capture_output=True, text=True)
        m = re.search(r"([\d.]+) fps", r.stderr)
        fps = float(m.group(1)) if m else 0.0
    for n in range(len(rgb) // k):
        if _flat(rgb[n * k:(n + 1) * k]):
            at = f" (frame {n}, {n / fps:.3f} s)" if video and fps else ""
            raise Failed(f"blank render: a frame of {out.name} is one flat color{at}")


# ------------------------------------------------------------------------------------------------------------ encode

CHOSEN = {}


def encoder(ffmpeg, size=(256, 256)):
    """The encoder this process encodes films of `size` (width, height) with through `ffmpeg`: the card's (h264_nvenc
    with the NVIDIA device, or h264_videotoolbox on a Mac) when that ffmpeg lists it and it encodes one frame of that
    size, otherwise libx264."""
    if (ffmpeg, size) not in CHOSEN:
        CHOSEN[ffmpeg, size] = _probe(ffmpeg, size)
    return CHOSEN[ffmpeg, size]


def _probe(ffmpeg, size):
    want = "h264_nvenc" if GPU else "h264_videotoolbox" if sys.platform == "darwin" else None
    if not want:
        return "libx264"
    try:
        listed = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30).stdout
        if not re.search(rf"\s{want}\s", listed):
            return "libx264"
        r = subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-f", "lavfi", "-i", f"color=gray:s={size[0]}x{size[1]}:r=30",
                            "-frames:v", "1", "-pix_fmt", "yuv420p", *ENCODERS[want], "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "libx264"
    return want if r.returncode == 0 else "libx264"


class Encoding:
    """ffmpeg encoding the film `out` from PNG frames written into its input in frame order from `first`, BT.709
    tagged, faststart. Every painted frame is kept in `folder`, where the frames cache takes it once the film passes
    its checks: a frame that arrives ahead of its turn goes in from there once every frame before it is in, and a frame
    in `kept` (frame to its file in the frames cache) goes in from its file at its turn. `write` is called from every
    browser's thread."""

    def __init__(self, ffmpeg, codec, fps, first, total, folder, out, kept=None):
        self.next, self.folder, self.kept, self.early = first, folder, kept or {}, set()
        self.lock, self.err = threading.Lock(), tempfile.TemporaryFile()
        self.proc = subprocess.Popen([ffmpeg, "-hide_banner", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(fps),
                                      "-c:v", "png", "-i", "-", "-frames:v", str(total),
                                      "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", *ENCODERS[codec],
                                      *(["-threads", str(usable_cores())] if codec == "libx264" else []),
                                      "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                                      "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", str(out)],
                                     stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.err)

    def write(self, f, png):
        (self.folder / f"{f:06d}.png").write_bytes(png)
        with self.lock:
            if f == self.next:
                self._put(png)
            else:
                self.early.add(f)
            self._drain()

    def flush(self):
        """Puts in the kept frames that are next in line."""
        with self.lock:
            self._drain()

    def _put(self, png):
        try:
            self.proc.stdin.write(png)
        except BrokenPipeError:
            raise Failed(f"ffmpeg stopped taking frames at frame {self.next}: {self.close()[1][-600:]}") from None
        self.next += 1

    def _drain(self):
        while True:
            if self.next in self.early:
                self.early.discard(self.next)
                self._put((self.folder / f"{self.next:06d}.png").read_bytes())
            elif self.next in self.kept:
                try:
                    png = self.kept[self.next].read_bytes()
                except OSError:
                    raise Failed(f"frame {self.next} left the frames cache before it went in") from None
                self._put(png)
            else:
                return

    def close(self):
        """ffmpeg's return code and its error output once every frame is in."""
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        rc = self.proc.wait()
        self.err.seek(0)
        return rc, self.err.read().decode(errors="replace").strip()

    def kill(self):
        self.proc.kill()
        self.close()


# ------------------------------------------------------------------------------------------------------------ timing

class Timing:
    """A film's stage times under VS_TIMING=1, written to <film>.timing.json beside it once it passes its checks. The
    stages, in seconds a frame: seek (the frame asked for until the composition is ready: its draw, three.js included),
    shot (Page.captureScreenshot until its reply is in: the browser composites the frame, reads it back and compresses
    it to PNG) and write (the PNG into ffmpeg's input and the frames folder). The marks, in seconds since the attempt
    began: first and frames (the first and the last frame in), encoded (ffmpeg done) and checked (the film's checks
    done). Every browser's connection adds its replies to the attempt being timed, Timing.now."""

    now = None

    def __init__(self, out, codec, gl):
        self.out, self.codec, self.gl, self.t0 = Path(out), codec, gl, time.monotonic()
        self.stages, self.marks, self.sizes = {"seek": [], "shot": [], "write": []}, {}, []
        Timing.now = self

    def wrap(self, write):
        def timed(f, png):
            t = time.monotonic()
            write(f, png)
            self.stages["write"].append(time.monotonic() - t)
            self.sizes.append(len(png))
            self.marks.setdefault("first", round(t - self.t0, 3))
        return timed

    def mark(self, name):
        self.marks[name] = round(time.monotonic() - self.t0, 3)

    def save(self, browsers):
        def summary(xs):
            xs = sorted(xs)
            return {"n": len(xs), "mean_ms": round(1000 * sum(xs) / len(xs), 2), "p50_ms": round(1000 * xs[len(xs) // 2], 2),
                    "p90_ms": round(1000 * xs[int(len(xs) * 0.9)], 2), "sum_s": round(sum(xs), 3)} if xs else {"n": 0}
        Timing.now = None
        self.out.with_suffix(".timing.json").write_text(json.dumps({
            "out": str(self.out), "frames": len(self.sizes), "browsers": browsers, "gl": self.gl, "encoder": self.codec,
            "cores": usable_cores(), "seconds": self.marks, "stages": {k: summary(v) for k, v in self.stages.items()},
            "png_mean_bytes": round(sum(self.sizes) / len(self.sizes)) if self.sizes else 0}, indent=1))


# ------------------------------------------------------------------------------------------------------------ render

class Renderer:
    """One browser and its pages. A film job also runs on `browsers - 1` more of them (the crew), each with its own
    pages, all taking the next frame from one queue: a browser draws and captures its pages one at a time, so browsers
    render side by side where a second page in the same browser waits its turn."""

    def __init__(self, url, chromium_exe, ffmpeg, gl, tabs, browsers=1):
        self.url, self.exe, self.ffmpeg, self.gl, self.tabs, self.browsers = url, chromium_exe, ffmpeg, gl, tabs, browsers
        self.browser, self.pool, self.chosen, self.crew, self.encoder = None, None, {}, [], "libx264"
        self.inputs = ""

    def fresh(self):
        self.close()
        self.browser = Browser(self.exe, self.gl)

    def close(self):
        for m in self.crew:
            m.close()
        if self.browser:
            self.browser.close()
        self.browser, self.pool, self.chosen, self.crew = None, None, {}, []

    def select(self, job):
        """The composition with the job's props, as @remotion/renderer's select-composition.js selects it: a page in
        evaluation mode, ready, then remotion_calculateComposition. Kept for the browser's life, per props."""
        key = json.dumps([job["composition"], job["props"]], sort_keys=True)
        if key not in self.chosen:
            tab = self.browser.tab(job["out"], self.url, job["props"], 0, True)
            try:
                b = self.browser.cdp
                b.evaluate("window.remotion_setBundleMode({type: 'evaluation'})", tab["session"])
                b.evaluate("window.__vs_ready('the composition')", tab["session"], READY_MS / 1000 + 5)
                self.chosen[key] = b.evaluate(f"window.remotion_calculateComposition({json.dumps(job['composition'])})",
                                              tab["session"], READY_MS / 1000 + 5)
            finally:
                self.browser.close_tab(tab)
        return self.chosen[key]

    def pages(self, job, comp, n, first, still):
        """`n` pages in composition mode at the job's scale (make-page.js), kept while the next job shares their props,
        scale and background."""
        key = json.dumps([comp, job["scale"] if "scale" in job else 1, still], sort_keys=True)
        if self.pool and self.pool[0] == key and len(self.pool[1]) >= n:
            for t in self.pool[1]:
                self.browser.sessions[t["session"]] = job["out"]
            return self.pool[1][:n]
        if self.pool:
            for t in self.pool[1]:
                self.browser.close_tab(t)
        b, made = self.browser, []
        for i in range(n):
            t = b.tab(job["out"], self.url, job["props"], first + i, i == 0)
            s = t["session"]
            b.cdp.call("Emulation.setDeviceMetricsOverride", {
                "width": comp["width"], "height": comp["height"], "deviceScaleFactor": job.get("scale") or 1,
                "mobile": False, "screenOrientation": {"angle": 0, "type": "portraitPrimary"}}, s)
            # take-frame.js: a PNG still keeps the page's transparency, and a film frame is drawn on black
            if still:
                b.cdp.call("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}}, s)
            mode = {"type": "composition", "compositionName": comp["id"],
                    "serializedResolvedPropsWithSchema": comp["serializedResolvedPropsWithCustomSchema"],
                    "compositionDurationInFrames": comp["durationInFrames"], "compositionFps": comp["fps"],
                    "compositionHeight": comp["height"], "compositionWidth": comp["width"],
                    "compositionDefaultCodec": comp.get("defaultCodec"), "compositionDefaultOutName": comp.get("defaultOutName"),
                    "compositionDefaultVideoImageFormat": comp.get("defaultVideoImageFormat"),
                    "compositionDefaultPixelFormat": comp.get("defaultPixelFormat"),
                    "compositionDefaultProResProfile": comp.get("defaultProResProfile"),
                    "compositionDefaultSampleRate": comp.get("defaultSampleRate")}
            b.cdp.evaluate(f"window.remotion_setBundleMode({json.dumps(mode)}); "
                           f"document.body.style.background = {json.dumps('transparent' if still else 'black')}; true", s)
            made.append(t)
        self.pool = (key, made)
        return made

    def frames(self, job, comp, pages, todo, write, progress):
        """Every frame of `todo` across the pages: each page seeks (wait for ready, set the frame, wait for ready, the
        fonts) and is screenshot (screenshot-task.js) on its own, so the pages work side by side over one connection."""
        b, cdp = self.browser, self.browser.cdp
        queue, inflight = todo if isinstance(todo, collections.deque) else collections.deque(todo), {}
        comp_id = json.dumps(comp["id"])
        clip = {"x": 0, "y": 0, "width": comp["width"], "height": comp["height"], "scale": 1}

        def start(page):
            if queue:
                f = queue.popleft()
                i = cdp.send("Runtime.evaluate", {"expression": f"window.__vs_seek({f}, {comp_id})", "awaitPromise": True,
                                                  "returnByValue": True}, page["session"])
                inflight[i] = (page, "seek", f)

        for page in pages:
            start(page)
        while inflight:
            try:
                i, msg = cdp.first(list(inflight), READY_MS / 1000 + 5)
            except TimeoutError:
                f = min(f for _, _, f in inflight.values())
                raise Failed(f"the browser stopped answering at frame {f}") from None
            page, stage, f = inflight.pop(i)
            if b.crashed:
                raise Failed(f"{b.crashed} at frame {f}")
            if job["out"] in b.lost:
                raise Failed(f"the browser lost its graphics context at frame {f}: {b.lost[job['out']]}")
            if job["out"] in b.errors:
                raise Failed(f"{Path(job['out']).name}: the page threw an error by frame {f}: {b.errors[job['out']]}")
            if "error" in msg:
                raise Failed(f"frame {f}: {msg['error'].get('message')}")
            if stage == "seek":
                try:
                    value(msg.get("result") or {})
                except Failed as e:
                    text = str(e)
                    if "STOP " in text:
                        raise Stopped(text[text.index("STOP ") + 5:]) from None
                    raise Failed(f"frame {f}: {text}") from None
                cdp.ignored.add(cdp.send("Target.activateTarget", {"targetId": page["target"]}))
                # optimizeForSpeed: still a lossless PNG, compressed at Chromium's fastest setting; a Chromium that does
                # not know the key ignores it
                i = cdp.send("Page.captureScreenshot", {"format": "png", "clip": clip, "captureBeyondViewport": True,
                                                        "optimizeForSpeed": True, "fromSurface": True}, page["session"])
                inflight[i] = (page, "shot", f)
            else:
                write(f, base64.b64decode(msg["result"]["data"]))
                progress()
                start(page)

    def film(self, job, comp, todo, write, progress):
        """The frames `todo` of a film job across this browser and its crew, each member a thread taking the next frame
        from one queue. The first failure empties the queue, so every member stops at its next frame, and is raised
        once all of them have; a frame that never got ready is raised before any other failure."""
        total = len(todo)
        while len(self.crew) < min(self.browsers, total) - 1:
            self.crew.append(Renderer(self.url, self.exe, self.ffmpeg, self.gl, self.tabs))
        members = [self] + self.crew[:max(0, min(self.browsers, total) - 1)]
        queue, errors = collections.deque(todo), []
        # a browser ends with the thread that started it (_die_with_parent): the crew's start here, in the thread that
        # renders every job, so they serve the jobs after this one; each waits for its DevTools in its own thread, while
        # the others render
        for m in members:
            if m.browser is None:
                m.browser = Browser(m.exe, m.gl, wait=False)

        def work(m, k):
            try:
                try:
                    m.browser.ready()
                except Failed:
                    m.browser = None
                    raise
                m.browser.findings.pop(job["out"], None)
                m.browser.lost.pop(job["out"], None)
                mine = comp if m is self else m.select(job)
                if mine["durationInFrames"] != comp["durationInFrames"]:
                    raise Failed("two browsers calculated the composition differently")
                m.frames(job, comp, m.pages(job, comp, min(m.tabs, total), todo[min(k * m.tabs, total - 1)], False), queue, write, progress)
            except BaseException as e:
                errors.append(e)
                queue.clear()

        if len(members) == 1:
            work(self, 0)
        else:
            threads = [threading.Thread(target=work, args=(m, k), daemon=True) for k, m in enumerate(members)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        if errors:
            raise next((e for e in errors if isinstance(e, Stopped)), errors[0])
        return members

    def run(self, job, t0):
        """One attempt at a job; returns its findings, the frames it rendered and the frames it painted."""
        b = self.browser
        b.findings.pop(job["out"], None)
        b.lost.pop(job["out"], None)
        b.errors.pop(job["out"], None)
        comp = self.select(job)
        members, folder, hold, clock = [self], None, None, None
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if job["type"] == "video":
                n = comp["durationInFrames"]
                if job.get("frames") is not None and job["frames"] != n:
                    raise Refused(f"the job plans {job['frames']} frames and the composition has {n}")
                a, z = job.get("frameRange") or (0, n - 1)
                if not (0 <= a <= z < n):
                    raise Refused(f"frameRange [{a}, {z}] is outside the composition's {n} frames")
                total = z - a + 1
                store = cache() / "frames"
                keys, kept = frame_keys(job, comp, range(a, z + 1), self.inputs), {}
                for f, k in keys.items():
                    # a reused frame is marked as just used, so the cap removes it last
                    with contextlib.suppress(OSError):
                        os.utime(store / f"{k}.png")
                        kept[f] = store / f"{k}.png"
                todo = [f for f in range(a, z + 1) if f not in kept]
                painted = len(todo)
                folder, hold = stage(store, out.stem)
                scale = job.get("scale") or 1
                codec = self.encoder if self.encoder == "libx264" else encoder(self.ffmpeg, (round(comp["width"] * scale),
                                                                                             round(comp["height"] * scale)))
                if kept:
                    print(f"render {out.name}: {len(kept)} of {total} frames from the frames cache, {painted} to paint",
                          file=sys.stderr, flush=True)
                pipe = Encoding(self.ffmpeg, codec, comp["fps"], a, total, folder, out, kept)
                clock = Timing(out, codec, self.gl) if TIMING else None
                done, last, counting = [0], [-1], threading.Lock()

                def progress():
                    with counting:
                        done[0] += 1
                        p = done[0] * 10 // painted
                        if p == last[0]:
                            return
                        last[0] = p
                    print(f"render {out.name} {p * 10}% ({time.monotonic() - t0:.0f} s)", file=sys.stderr, flush=True)

                try:
                    pipe.flush()
                    if todo:
                        members = self.film(job, comp, todo, clock.wrap(pipe.write) if clock else pipe.write, progress)
                except BaseException:
                    pipe.kill()
                    out.unlink(missing_ok=True)
                    raise
                if clock:
                    clock.mark("frames")
                rc, err = pipe.close()
                if clock:
                    clock.mark("encoded")
                if rc != 0:
                    out.unlink(missing_ok=True)
                    if codec != "libx264":
                        # the next attempt renders the film again for libx264
                        self.encoder = "libx264"
                    raise Failed(f"ffmpeg could not encode {out.name} with {codec}: {err[-600:]}")
            else:
                frame, total, painted = min(int(job.get("frame") or 0), comp["durationInFrames"] - 1), 1, 1
                pages = self.pages(job, comp, 1, frame, True)
                self.frames(job, comp, pages, [frame], lambda f, png: out.write_bytes(png), lambda: None)
            for m in members:
                if job["out"] in m.browser.lost:
                    raise Failed(f"the browser lost its graphics context: {m.browser.lost[job['out']]}")
                if job["out"] in m.browser.errors:
                    raise Failed(f"{out.name}: the page threw an error: {m.browser.errors[job['out']]}")
            refuse_blank(self.ffmpeg, out, job["type"] == "video")
            if clock:
                clock.mark("checked")
                clock.save(len(members))
            own = [{"job": job["out"], "text": t}
                   for t in dict.fromkeys(t for m in members for t in m.browser.findings.get(job["out"], []))]
            if job["out"].endswith(".part.mp4"):
                Path(job["out"][:-len(".mp4")] + ".findings.json").write_text(json.dumps(own))
            # a film whose composition logged a finding keeps none of its frames, so the next render paints them again
            if folder and not own:
                for f in todo:
                    os.replace(folder / f"{f:06d}.png", store / f"{keys[f]}.png")
                trim(store, FRAMES_CAP)
        finally:
            if folder:
                shutil.rmtree(folder, ignore_errors=True)
                os.close(hold)
        return own, total, painted


def render_jobs(jobs, public, dist=DIST, ffmpeg=None, chromium=None, gl="auto", tabs=None, browsers=None):
    """Renders the jobs in one browser, each film across it and its crew; returns the report: seconds, jobs, failed,
    retries, gl, card, encoder (None when no job is a film), frames, painted (the frames not taken from the frames
    cache), findings, timings."""
    t_start = time.monotonic()
    exe = chromium or globals()["chromium"]()
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("no Chromium was found: set CHROME_PATH to one, or install Chromium or Google Chrome")
    if not (Path(dist) / "index.html").is_file():
        raise SystemExit(f"the composition bundle is missing ({dist}): this kit ships motion/dist, so restore the kit folder")
    gl = backend(gl)
    # a browser draws and captures its pages one at a time, on the card and on the CPU alike, so a film runs one page
    # in each of several browsers (pool_size)
    tabs = tabs or 1
    browsers = browsers or pool_size(gl)
    server, url = serve(dist, public)
    r = Renderer(url, exe, ffmpeg, gl, tabs, browsers)
    r.inputs = frame_inputs(dist, public, exe, gl)
    codec = encoder(ffmpeg) if any(job["type"] == "video" for job in jobs) else None
    if codec:
        r.encoder = codec
        print(f"encoding with {codec}{'' if codec == 'libx264' else ' on the card'}", file=sys.stderr, flush=True)
    findings, timings, failed, retries, frames, painted = [], [], 0, 0, 0, 0
    stopped = None
    try:
        for job in jobs:
            t0 = time.monotonic()
            if stopped:
                failed += 1
                findings.append({"job": job["out"], "text": f"RENDER_ERROR not rendered: {stopped}"})
                continue
            error = None
            for attempt in (1, 2, 3):
                try:
                    if attempt > 1 or r.browser is None:
                        if attempt > 1:
                            retries += 1
                            print(f"retrying {Path(job['out']).name} (attempt {attempt} of 3): {str(error)[:200]}", file=sys.stderr, flush=True)
                        r.fresh()
                    own, n, drawn = r.run(job, t0)
                    findings += own
                    error = None
                    break
                except (Refused, Stopped) as e:
                    error = e
                    break
                except (Failed, OSError, KeyError) as e:
                    error = e
            if error:
                failed += 1
                findings.append({"job": job["out"], "text": f"RENDER_ERROR {error}"})
                print(f"failed {job['out']}: {error}", file=sys.stderr, flush=True)
                if isinstance(error, Stopped):
                    stopped = f"an earlier job stopped: {error}"
            else:
                frames += n
                painted += drawn
                timings.append({"out": job["out"], "seconds": round(time.monotonic() - t0, 2), "frames": n, "painted": drawn})
    finally:
        r.close()
        server.shutdown()
        server.server_close()
    seconds = round(time.monotonic() - t_start, 2)
    print(f"rendered {len(jobs) - failed} of {len(jobs)} jobs in {seconds:.1f} s on {gl}", file=sys.stderr, flush=True)
    return {"seconds": seconds, "jobs": len(jobs), "failed": failed, "retries": retries, "gl": gl,
            "card": gl == "vulkan" and GPU, "encoder": codec, "frames": frames, "painted": painted, "findings": findings,
            "timings": timings}


def _stop(signum, frame):
    raise SystemExit(128 + signum)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", help="a jobs file as studio.render writes it")
    ap.add_argument("--run", help="the run folder (default: this folder)")
    ap.add_argument("--board", help="a profile in the run's film.json boards, or a board file")
    ap.add_argument("--out", help="the film (.mp4) or, with --still, the frame (.png)")
    ap.add_argument("--scale", type=float, default=1.0, help="the size against the board's (0.5 is half)")
    ap.add_argument("--still", type=int, help="render this frame alone, as a PNG")
    ap.add_argument("--gl", choices=["auto", "vulkan", "lavapipe", "swiftshader"], default="auto",
                    help="the browser's graphics backend (auto: Vulkan on an NVIDIA card; otherwise on the CPU, lavapipe "
                    "when the machine has it, SwiftShader when not)")
    ap.add_argument("--tabs", type=int, help="pages in each browser (default 1)")
    ap.add_argument("--browsers", type=int, help="browsers a film renders in side by side (default: one for "
                    "every PER_BROWSER usable cores of the graphics backend, up to 8, as many as the memory holds)")
    a = ap.parse_args()
    # a stop from the machine or a person ends the render at once; the browser is closed on the way out
    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _stop)
    if a.jobs:
        spec = json.loads(Path(a.jobs).read_text())
        rep = render_jobs(spec["jobs"], spec["publicDir"], ffmpeg=spec.get("ffmpeg"), chromium=spec.get("chromium"),
                          gl=spec.get("gl") or a.gl, tabs=a.tabs, browsers=a.browsers)
        if spec.get("report"):
            Path(spec["report"]).write_text(json.dumps(rep, indent=2))
        return 1 if rep["failed"] else 0
    if not (a.board and a.out):
        ap.error("give --jobs, or --board and --out")
    sys.path.insert(0, str(KIT / "scripts"))
    import types
    import _env
    import film
    import studio
    out = (_env.WORKSPACE / a.out).resolve()
    if a.run:
        _env.enter_run(a.run)
    boards = (_env.read_json("film.json") or {}).get("boards") or {}
    board = _env.read_json(boards.get(a.board) or a.board)
    if not board:
        sys.exit(f"no board {a.board}: name a profile in film.json `boards` or a board file")
    pub = studio.public()
    if a.still is not None:
        job = studio.still(board, a.still, out, a.scale)
        rep = render_jobs([job], pub, ffmpeg=_env.ffmpeg(), gl=a.gl, tabs=a.tabs, browsers=a.browsers)
    else:
        silent = private_dir(cache() / "films", "film-") / "silent.mp4"
        job = {**studio.video(board, silent, 0, a.scale), "frames": None}
        try:
            rep = render_jobs([job], pub, ffmpeg=_env.ffmpeg(), gl=a.gl, tabs=a.tabs, browsers=a.browsers)
            if not rep["failed"]:
                fps = board.get("fps") or (board.get("format") or {}).get("fps") or 30
                # a kit whose film.py has not taken the sound effects yet lays the music alone
                takes = "board" in inspect.signature(film.mux).parameters
                film.mux(types.SimpleNamespace(spawn=subprocess.run), silent, out, rep["frames"] / fps, **({"board": board} if takes else {}))
        finally:
            shutil.rmtree(silent.parent, ignore_errors=True)
    for f in rep["findings"]:
        print(f["text"][:300], file=sys.stderr)
    if rep["failed"]:
        return 1
    print(f"wrote {out} ({rep['frames']} frames, {rep['painted']} painted, in {rep['seconds']:.1f} s, "
          f"{rep['frames'] / max(rep['seconds'], 0.01):.1f} frames a second, {rep['gl']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
