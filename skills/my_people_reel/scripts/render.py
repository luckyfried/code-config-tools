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
compresses at its fastest setting. ffmpeg encodes the frames to yuv420p at the composition's size and frame rate, with
h264_nvenc on the NVIDIA card, with h264_videotoolbox on a Mac whose ffmpeg has it, and with libx264 otherwise: the
encoder is tried once per process on one frame, a machine whose card or driver refuses that frame encodes with
libx264, and a film the card's encoder refuses (one smaller than its smallest frame) is encoded again with libx264.
With the NVIDIA device the browser draws on the card through ANGLE on Vulkan, otherwise on the CPU through ANGLE on
SwiftShader. A browser draws and captures its pages one at a time, so a film runs one page in each of several
browsers (half the cores, up to 8), all taking the next frame from one queue.

A frame that is not ready in 30 s stops the render, naming the frame and what it still waited for. Any other failure
(a browser that stops answering, a lost graphics context, a render that comes out one flat color) costs one attempt,
and attempts 2 and 3 run in a fresh browser. A video job whose `frames` differs from the composition's is refused.
An `out` ending in `.part.mp4` is a chunk (scripts/chunks.py): once it passes its checks its findings are written
beside it as `.part.findings.json`. The jobs file's report lists every job that failed and every FONT_ERROR and
IMAGE_ERROR line the composition logged.

Chromium is found in this order: CHROME_PATH; Playwright's Chromium (PLAYWRIGHT_BROWSERS_PATH, ~/.cache/ms-playwright,
~/Library/Caches/ms-playwright; the newest revision first, a full build before a headless shell); chromium,
chromium-browser, google-chrome, google-chrome-stable on PATH; the macOS applications; a Remotion headless shell
already on disk under motion/node_modules.
"""
import argparse
import atexit
import base64
import collections
import hashlib
import http.server
import inspect
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
GPU = os.path.exists("/dev/nvidia0")
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
ENCODERS = {
    # spatial adaptive quantization keeps the grain in a dark dissolve, which the card's encoder flattens into patches
    # without it: under the ceiling a lower cq buys nothing there
    "h264_nvenc": ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "18", "-b:v", "0", *CEILING,
                   "-spatial-aq", "1", "-profile:v", "high"],
    "h264_videotoolbox": ["-c:v", "h264_videotoolbox", "-q:v", "65", "-allow_sw", "0", *CEILING, "-profile:v", "high"],
    "libx264": ["-c:v", "libx264", "-preset", "medium", "-crf", "18", *CEILING],
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
    for kind, names in (("chromium-*", ("*/chrome", "*/chrome.exe", "*/*.app/Contents/MacOS/*")),
                        ("chromium_headless_shell-*", ("*/chrome-headless-shell", "*/headless_shell", "*/chrome-headless-shell.exe"))):
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


def private_dir(parent, prefix):
    """A new folder only this user can open, under `parent`."""
    Path(parent).mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=parent))


def headless(exe):
    """A headless shell takes the plain flag; a full Chromium takes the new headless mode, as open-browser.js does."""
    return "--headless" if "headless" in Path(exe).name else "--headless=new"


def browser_env(runtime):
    """The browser's environment: its own runtime folder, and no accessibility bridge to the desktop's bus."""
    return dict(os.environ, XDG_RUNTIME_DIR=str(runtime), NO_AT_BRIDGE="1")


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
        self.ws, self.on_event, self.next, self.replies, self.ignored = ws, on_event, 0, {}, set()

    def send(self, method, params=None, session=None):
        self.next += 1
        msg = {"id": self.next, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
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
window.__vs_seek = async (f, comp) => {
  await window.__vs_ready(`frame ${f}`);
  window.remotion_setFrame(f, comp, 1);
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


class Browser:
    """One headless Chromium with its own profile and runtime folder, and its DevTools connection."""

    def __init__(self, exe, gl):
        self.root = private_dir(cache() / "browser", "chromium-")
        (self.root / "run").mkdir(mode=0o700)
        self.log_path = self.root / "stderr.log"
        self.findings, self.lost, self.errors, self.crashed = collections.defaultdict(list), {}, {}, None
        # @remotion/renderer's open-browser.js: its flags, and its two graphics backends this renderer uses
        angle = (["--use-angle=vulkan", "--use-vulkan=native", "--disable-vulkan-fallback-to-gl-for-testing",
                  "--disable-vulkan-surface", "--enable-gpu", "--enable-features=Vulkan,UseSkiaRenderer"]
                 if gl == "vulkan" else ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
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
                                         env=browser_env(self.root / "run"), start_new_session=True,
                                         preexec_fn=_die_with_parent)
        LIVE.add(self)
        url, until = None, time.monotonic() + 30
        while not url:
            m = re.search(r"DevTools listening on (ws://\S+)", self.log_path.read_text(errors="replace"))
            if m:
                url = m.group(1)
            elif self.proc.poll() is not None or time.monotonic() > until:
                tail = self.log_path.read_text(errors="replace")[-800:]
                self.close()
                raise Failed(f"the browser did not start ({exe}): {tail.strip() or 'no output'}")
            else:
                time.sleep(0.05)
        self.cdp = Cdp(WebSocket(url, 30), self.event)
        self.sessions = {}

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
    """In the browser's process before it starts, on Linux: the kernel kills it when this process dies, even by a
    signal that runs no handler."""
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


def encoder(ffmpeg):
    """The encoder this process encodes films with through `ffmpeg`: the card's (h264_nvenc with the NVIDIA device, or
    h264_videotoolbox on a Mac) when that ffmpeg lists it and it encodes one frame, otherwise libx264."""
    if ffmpeg not in CHOSEN:
        CHOSEN[ffmpeg] = _probe(ffmpeg)
    return CHOSEN[ffmpeg]


def _probe(ffmpeg):
    want = "h264_nvenc" if GPU else "h264_videotoolbox" if sys.platform == "darwin" else None
    if not want:
        return "libx264"
    try:
        listed = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=30).stdout
        if not re.search(rf"\s{want}\s", listed):
            return "libx264"
        r = subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "color=gray:s=256x256:r=30",
                            "-frames:v", "1", "-pix_fmt", "yuv420p", *ENCODERS[want], "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "libx264"
    return want if r.returncode == 0 else "libx264"


def encode(ffmpeg, codec, fps, first, total, frames, out):
    """The PNG frames in `frames` as the film `out`, BT.709 tagged, faststart."""
    return subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-y", "-framerate", str(fps), "-start_number", str(first),
                           "-i", str(frames / "%06d.png"), "-frames:v", str(total),
                           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", *ENCODERS[codec],
                           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                           "-color_range", "tv", "-movflags", "+faststart", str(out)], capture_output=True, text=True)


# ------------------------------------------------------------------------------------------------------------ render

class Renderer:
    """One browser and its pages. A film job also runs on `browsers - 1` more of them (the crew), each with its own
    pages, all taking the next frame from one queue: a browser draws and captures its pages one at a time, so browsers
    render side by side where a second page in the same browser waits its turn."""

    def __init__(self, url, chromium_exe, ffmpeg, gl, tabs, browsers=1):
        self.url, self.exe, self.ffmpeg, self.gl, self.tabs, self.browsers = url, chromium_exe, ffmpeg, gl, tabs, browsers
        self.browser, self.pool, self.chosen, self.crew, self.encoder = None, None, {}, [], "libx264"

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

    def film(self, job, comp, a, z, write, progress):
        """Frames a..z of a film job across this browser and its crew, each member a thread taking the next frame from
        one queue. The first failure empties the queue, so every member stops at its next frame, and is raised once
        all of them have; a frame that never got ready is raised before any other failure."""
        total = z - a + 1
        while len(self.crew) < min(self.browsers, total) - 1:
            self.crew.append(Renderer(self.url, self.exe, self.ffmpeg, self.gl, self.tabs))
        members = [self] + self.crew[:max(0, min(self.browsers, total) - 1)]
        queue, errors = collections.deque(range(a, z + 1)), []

        def work(m, k):
            try:
                if m.browser is None:
                    m.browser = Browser(m.exe, m.gl)
                m.browser.findings.pop(job["out"], None)
                m.browser.lost.pop(job["out"], None)
                mine = comp if m is self else m.select(job)
                if mine["durationInFrames"] != comp["durationInFrames"]:
                    raise Failed("two browsers calculated the composition differently")
                m.frames(job, comp, m.pages(job, comp, min(m.tabs, total), a + k * m.tabs, False), queue, write, progress)
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
        """One attempt at a job; returns its findings and the frames it rendered."""
        b = self.browser
        b.findings.pop(job["out"], None)
        b.lost.pop(job["out"], None)
        b.errors.pop(job["out"], None)
        comp = self.select(job)
        members = [self]
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        if job["type"] == "video":
            n = comp["durationInFrames"]
            if job.get("frames") is not None and job["frames"] != n:
                raise Refused(f"the job plans {job['frames']} frames and the composition has {n}")
            a, z = job.get("frameRange") or (0, n - 1)
            if not (0 <= a <= z < n):
                raise Refused(f"frameRange [{a}, {z}] is outside the composition's {n} frames")
            total = z - a + 1
            folder = private_dir(cache() / "frames", f"{out.stem}-")
            try:
                done, last, counting = [0], [-1], threading.Lock()

                def write(f, png):
                    (folder / f"{f:06d}.png").write_bytes(png)

                def progress():
                    with counting:
                        done[0] += 1
                        p = done[0] * 10 // total
                        if p == last[0]:
                            return
                        last[0] = p
                    print(f"render {out.name} {p * 10}% ({time.monotonic() - t0:.0f} s)", file=sys.stderr, flush=True)

                members = self.film(job, comp, a, z, write, progress)
                r = encode(self.ffmpeg, self.encoder, comp["fps"], a, total, folder, out)
                if r.returncode != 0 and self.encoder != "libx264":
                    why = (r.stderr.strip().splitlines() or ["no output"])[-1][:200]
                    print(f"encoding {out.name} with libx264: {self.encoder} refused it ({why})", file=sys.stderr, flush=True)
                    r = encode(self.ffmpeg, "libx264", comp["fps"], a, total, folder, out)
                if r.returncode != 0:
                    raise Failed(f"ffmpeg could not encode {out.name}: {r.stderr.strip()[-600:]}")
            finally:
                shutil.rmtree(folder, ignore_errors=True)
        else:
            frame, total = min(int(job.get("frame") or 0), comp["durationInFrames"] - 1), 1
            pages = self.pages(job, comp, 1, frame, True)
            self.frames(job, comp, pages, [frame], lambda f, png: out.write_bytes(png), lambda: None)
        for m in members:
            if job["out"] in m.browser.lost:
                raise Failed(f"the browser lost its graphics context: {m.browser.lost[job['out']]}")
            if job["out"] in m.browser.errors:
                raise Failed(f"{out.name}: the page threw an error: {m.browser.errors[job['out']]}")
        refuse_blank(self.ffmpeg, out, job["type"] == "video")
        own = [{"job": job["out"], "text": t}
               for t in dict.fromkeys(t for m in members for t in m.browser.findings.get(job["out"], []))]
        if job["out"].endswith(".part.mp4"):
            Path(job["out"][:-len(".mp4")] + ".findings.json").write_text(json.dumps(own))
        return own, total


def render_jobs(jobs, public, dist=DIST, ffmpeg=None, chromium=None, gl="auto", tabs=None, browsers=None):
    """Renders the jobs in one browser, each film across it and its crew; returns the report: seconds, jobs, failed,
    retries, gl, card, encoder (None when no job is a film), frames, findings, timings."""
    t_start = time.monotonic()
    exe = chromium or globals()["chromium"]()
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("no Chromium was found: set CHROME_PATH to one, or install Chromium or Google Chrome")
    if not (Path(dist) / "index.html").is_file():
        raise SystemExit(f"the composition bundle is missing ({dist}): this kit ships motion/dist, so restore the kit folder")
    gl = ("vulkan" if GPU else "swiftshader") if gl == "auto" else gl
    # a browser draws and captures its pages one at a time, on the card and on the CPU alike, so a film runs one page
    # in each of several browsers, each kept busy by about two cores
    tabs = tabs or 1
    browsers = browsers or max(1, min(8, (os.cpu_count() or 1) // 2))
    server, url = serve(dist, public)
    r = Renderer(url, exe, ffmpeg, gl, tabs, browsers)
    codec = encoder(ffmpeg) if any(job["type"] == "video" for job in jobs) else None
    if codec:
        r.encoder = codec
        print(f"encoding with {codec}{'' if codec == 'libx264' else ' on the card'}", file=sys.stderr, flush=True)
    findings, timings, failed, retries, frames = [], [], 0, 0, 0
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
                    own, n = r.run(job, t0)
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
                timings.append({"out": job["out"], "seconds": round(time.monotonic() - t0, 2), "frames": n})
    finally:
        r.close()
        server.shutdown()
        server.server_close()
    seconds = round(time.monotonic() - t_start, 2)
    print(f"rendered {len(jobs) - failed} of {len(jobs)} jobs in {seconds:.1f} s on {gl}", file=sys.stderr, flush=True)
    return {"seconds": seconds, "jobs": len(jobs), "failed": failed, "retries": retries, "gl": gl,
            "card": gl == "vulkan" and GPU, "encoder": codec, "frames": frames, "findings": findings, "timings": timings}


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
    ap.add_argument("--gl", choices=["auto", "vulkan", "swiftshader"], default="auto",
                    help="the browser's graphics backend (auto: Vulkan on an NVIDIA card, SwiftShader on the CPU otherwise)")
    ap.add_argument("--tabs", type=int, help="pages in each browser (default 1)")
    ap.add_argument("--browsers", type=int, help="browsers a film renders in side by side (default half the cores, up to 8)")
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
    print(f"wrote {out} ({rep['frames']} frames in {rep['seconds']:.1f} s, {rep['frames'] / max(rep['seconds'], 0.01):.1f} frames a second, {rep['gl']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
