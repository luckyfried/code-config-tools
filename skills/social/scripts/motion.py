#!/usr/bin/env python3
"""Short vertical video (Reels / TikTok / Stories): 6-15 s, 1080x1920, 30 fps, H.264 yuv420p + silent AAC,
burned-in captions. Colours come from brand.json (or the stills themselves); nothing is hardcoded.

USAGE (from the workspace root):
  Route A, slides (default):
  python3 S/scripts/motion.py slides build/frames/p01-1.png build/frames/p01-2.png out/p01-x-story-1080x1920.png \
      --seconds 8 [--transition auto|cut|fade|push] [--fade 0.25] [--zoom 1.0] [--bg auto|"#FFF4E2"] \
      [--brand brand.json] [--captions 'Tuesday.' '$2 tacos.' 'All day.' | --captions-file build/captions.json] \
      --out out/p01-x-story-1080x1920.mp4
    Each still gets equal time (the first a little less, so the hook lands fast).
    Transitions sit exactly on the beat:
      cut   hard cut (no double exposure). Right for type beats of the same layout.
      fade  short eased crossfade (--fade seconds, 0.1-0.5, default 0.25). For photo-to-photo.
      push  the next still slides up over the last one (eased, --fade seconds). No double exposure.
      auto  (default) cut between stills that share a background (same template = type beats), fade otherwise.
    --fade 0 forces cuts everywhere. --zoom 1.04 adds a slow camera push-in that runs once across the whole
    clip, so both sides of every transition are at the same scale (no ghosted, mis-sized double text). Off by
    default: a push-in enlarges everything, so text that sits right at a safe-zone edge drifts into the UI band.
    Non-9:16 stills are centred on a pad: --bg auto = brand.json palette.bg, else the still's own edge colour.

  Route B, animated HTML (CSS animations; no JS timers):
  python3 S/scripts/motion.py html build/anim.html --seconds 8 [--captions-file build/captions.json] --out out/p02-reel-1080x1920.mp4
    The page is loaded at 1080x1920, every animation is paused and seeked frame by frame, so motion is smooth
    and deterministic.

captions.json: [{"start": 0.0, "end": 2.5, "text": "Tuesday."}, ...]. Max 2 lines; 3-5 words a line. Cues never
overlap (a cue that runs into the next is cut at its start) and are hidden during fade/push transitions.
Captions sit inside the Reels/TikTok/Story safe area (above the bottom 420 px, clear of the top 250 px and the
right-side rail), at the calmest height across the stills so they don't sit on the stills' own text. The caption
band uses brand.json fg with bg-coloured text (or the stills' own dark/light colours if there is no brand.json).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat  # noqa: E402

W, H, FPS = 1080, 1920, 30
# Captions must clear every 9:16 UI at once (Story, Reels, TikTok): the strictest band of each side from
# formats.json, never less than the Reels bottom caption band (420 px).
_Z = [f.get("safe_zone") or {} for f in _env.formats() if (f["w"], f["h"]) == (W, H)]
SAFE_TOP = max([250] + [int(z.get("top") or 0) for z in _Z])
SAFE_BOTTOM = max([420] + [int(z.get("bottom") or 0) for z in _Z])
SAFE_SIDE = max([64] + [int(z.get("left") or 0) for z in _Z])
SAFE_RAIL = max([200] + [int(z.get("right") or 0) for z in _Z])


# ------------------------------------------------------------------ colour
def hex_rgb(h):
    h = str(h).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(rgb):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def load_brand(path):
    """brand.json from --brand, else ./brand.json, else out/brand.json. Returns the palette as RGB tuples."""
    cands = [Path(path)] if path else [Path("brand.json"), Path("out/brand.json")]
    for p in cands:
        if p.exists():
            try:
                pal = json.loads(p.read_text()).get("palette") or {}
                out = {}
                for k, v in pal.items():
                    try:
                        out[k] = hex_rgb(v)
                    except Exception:
                        pass
                if out:
                    return out, p
            except Exception as e:
                print(f"note: could not read {p}: {e}", file=sys.stderr)
    if path:
        sys.exit(f"--brand {path}: not found or has no palette")
    return {}, None


def edge_colour(im):
    """Median colour of the still's outer border: what a seamless pad looks like."""
    s = im.convert("RGB").resize((64, 114))
    px = s.load()
    pts = [px[x, y] for x in range(64) for y in (0, 1, 112, 113)] + [px[x, y] for y in range(114) for x in (0, 1, 62, 63)]
    return tuple(sorted(p[i] for p in pts)[len(pts) // 2] for i in range(3))


def dominant(im, k=6):
    q = im.convert("RGB").resize((96, 170)).quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 3 * k]
    counts = sorted(q.getcolors(), reverse=True)
    return [tuple(pal[3 * i:3 * i + 3]) for _, i in counts]


# ------------------------------------------------------------------ captions
def wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


class Captioner:
    PADX, PADY = 34, 22

    def __init__(self, cues, size, band, ink):
        self.cues = cues or []
        self.font = _env.pil_font(size, "bold")
        self.size = size
        self.band, self.ink = band, ink
        self.cache = {}
        self.y_top = None  # chosen later (calmest band); default: just above the bottom UI band
        d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        self.maxw = W - SAFE_SIDE - SAFE_RAIL - 2 * self.PADX
        self.box_h = 0
        for c in self.cues:
            lines = wrap(d, c["text"], self.font, self.maxw)
            if len(lines) > 2:
                print(f"warning: caption '{c['text'][:40]}' wraps to {len(lines)} lines; keep it to 2 (3-5 words a line)",
                      file=sys.stderr)
            self.box_h = max(self.box_h, int(self.size * 1.18) * len(lines) + 2 * self.PADY)
        self.lowest = H - SAFE_BOTTOM - self.box_h - 24

    def place(self, stills):
        """Pick one caption height for the whole clip: the band that covers the fewest stills' own text/detail
        (so a caption never sits on a headline), preferring the usual low position on ties."""
        if not self.cues or not stills:
            return
        bw = W - SAFE_SIDE - SAFE_RAIL
        ink = [s.convert("L").filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v > 40 else 0) for s in stills]
        best = None
        for y in range(SAFE_TOP + 10, self.lowest + 1, 16):
            fr = [ImageStat.Stat(e.crop((SAFE_SIDE - 16, y - 16, SAFE_SIDE + bw + 16, y + self.box_h + 16))).mean[0] / 255
                  for e in ink]
            hits = sum(1 for v in fr if v > 0.002)
            score = (hits, round(20 * sum(fr) / len(fr)), self.lowest - y)  # coarse busyness, then lowest
            if best is None or score < best[0]:
                best = (score, y)
        self.y_top = best[1]
        if best[0][0]:
            print(f"note: captions overlap artwork on {best[0][0]} of {len(stills)} stills (no clear band; placed at "
                  f"y={best[1]}). If the stills already carry the words, drop the captions.", file=sys.stderr)

    def layer(self, text):
        if text in self.cache:
            return self.cache[text]
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        lines = wrap(d, text, self.font, self.maxw)
        lh = int(self.size * 1.18)
        bw = int(max(d.textlength(l, font=self.font) for l in lines)) + 2 * self.PADX
        bh = lh * len(lines) + 2 * self.PADY
        x0 = SAFE_SIDE
        y0 = self.y_top if self.y_top is not None else self.lowest
        y0 += self.box_h - bh  # bottom-align short cues inside the chosen band
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=22, fill=self.band + (232,))
        for i, l in enumerate(lines):
            d.text((x0 + self.PADX, y0 + self.PADY + i * lh - int(self.size * 0.08)), l, font=self.font,
                   fill=self.ink + (255,))
        self.cache[text] = im
        return im

    def apply(self, frame, t, hidden=False):
        if hidden:
            return frame
        for c in self.cues:
            if c["start"] <= t < c["end"]:
                frame = frame.convert("RGBA")
                frame.alpha_composite(self.layer(c["text"]))
                return frame.convert("RGB")
        return frame


def caption_colours(pal, stills):
    """Band + ink from brand.json (fg band, bg ink); fallback: the stills' own darkest/lightest colours."""
    if pal.get("fg") and pal.get("bg") and contrast(pal["fg"], pal["bg"]) >= 4.5:
        return pal["fg"], pal["bg"]
    if pal.get("fg"):
        fg = pal["fg"]
        ink = (255, 255, 255) if contrast(fg, (255, 255, 255)) >= contrast(fg, (0, 0, 0)) else (0, 0, 0)
        return fg, ink
    cols = [c for s in stills for c in dominant(s)]
    dark = min(cols, key=lum)
    light = max(cols, key=lum)
    if contrast(dark, light) < 4.5:
        light = (255, 255, 255) if lum(dark) < 0.4 else (0, 0, 0)
    return dark, light


def clean_cues(cues, total_s):
    cues = sorted((c for c in cues if str(c["text"]).strip()), key=lambda c: c["start"])
    out = []
    for i, c in enumerate(cues):
        s, e = max(0.0, c["start"]), min(total_s, c["end"])
        if i + 1 < len(cues) and e > cues[i + 1]["start"]:
            print(f"note: caption '{c['text'][:30]}' overlapped the next one; cut at {cues[i + 1]['start']:.2f}s",
                  file=sys.stderr)
            e = cues[i + 1]["start"]
        if e - s < 0.6:
            print(f"warning: caption '{c['text'][:30]}' is on screen {e - s:.2f}s; too short to read", file=sys.stderr)
        if e > s:
            out.append({"start": s, "end": e, "text": str(c["text"])})
    return out


def load_cues(a, slide_times=None):
    if getattr(a, "captions_file", None):
        cues = json.loads(Path(a.captions_file).read_text())
        return [{"start": float(c["start"]), "end": float(c["end"]), "text": str(c["text"])} for c in cues]
    if getattr(a, "captions", None):
        if not slide_times:
            sys.exit("--captions (one per slide) only works with `slides`; use --captions-file for html")
        caps = a.captions
        if len(caps) != len(slide_times):
            print(f"note: {len(caps)} captions for {len(slide_times)} slides; extra ignored / missing left blank",
                  file=sys.stderr)
        return [{"start": s, "end": e, "text": c} for (s, e), c in zip(slide_times, caps) if c.strip()]
    return []


# ------------------------------------------------------------------ encode
def open_ffmpeg(out, seconds):
    ff = _env.ffmpeg()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ff, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-t", f"{seconds:.3f}", "-shortest", "-r", str(FPS),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def finish(proc, out):
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    mb = Path(out).stat().st_size / 1e6
    print(f"saved {Path(out).resolve()}  ({mb:.1f} MB; run qa.py check, then open build/qa/<name>-strip.png)")


# ------------------------------------------------------------------ slides
def strip_colour(im, side):
    """Median colour of a thin strip along one side of the image."""
    w, h = im.size
    box = {"top": (0, 0, w, max(1, h // 40)), "bottom": (0, h - max(1, h // 40), w, h),
           "left": (0, 0, max(1, w // 40), h), "right": (w - max(1, w // 40), 0, w, h)}[side]
    return tuple(int(v) for v in ImageStat.Stat(im.crop(box).convert("RGB")).median)


def has_alpha(im):
    return im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)


def fit_frame(path, pad, alpha_pad=None):
    """-> (1080x1920 RGB frame, was_padded). pad: RGB tuple (brand bg), or None = extend the still's own edge
    colours (top strip above, bottom strip below). Transparent stills sit on alpha_pad (the set's background)."""
    im = ImageOps.exif_transpose(Image.open(path))
    if has_alpha(im):
        im = im.convert("RGBA")
        pad = pad or alpha_pad or (245, 242, 236)  # cutouts: pad bands match the colour they sit on
        flat = Image.new("RGB", im.size, pad)
        flat.paste(im, (0, 0), im)
        im = flat
    im = im.convert("RGB")
    if abs(im.width / im.height - W / H) < 0.01:
        return im.resize((W, H), Image.LANCZOS), False
    s = min(W / im.width, H / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    x0, y0 = (W - im.width) // 2, (H - im.height) // 2
    canvas = Image.new("RGB", (W, H), pad or (0, 0, 0))
    if pad is None:  # seamless: each pad band continues the edge it touches
        d = ImageDraw.Draw(canvas)
        if y0 > 0:
            d.rectangle([0, 0, W, y0], fill=strip_colour(im, "top"))
            d.rectangle([0, y0 + im.height, W, H], fill=strip_colour(im, "bottom"))
        if x0 > 0:
            d.rectangle([0, 0, x0, H], fill=strip_colour(im, "left"))
            d.rectangle([x0 + im.width, 0, W, H], fill=strip_colour(im, "right"))
    canvas.paste(im, (x0, y0))
    return canvas, True


def push_in(base, z):
    if z <= 1.0005:
        return base
    cw, ch = W / z, H / z
    x0, y0 = (W - cw) / 2, (H - ch) / 2
    return base.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def beats_of_one_layout(a, b):
    """True when two stills are the same design with a few elements added/changed (kinetic type beats):
    most pixels identical. A crossfade there shows two ghosted headlines, so those get a hard cut."""
    ga, gb = (s.convert("L").resize((108, 192)) for s in (a, b))
    pa, pb = ga.load(), gb.load()
    changed = sum(1 for y in range(192) for x in range(108) if abs(pa[x, y] - pb[x, y]) > 24)
    return changed / (108 * 192) < 0.30


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)  # smoothstep: brief 50/50 moment, no lingering double exposure


def cmd_slides(a):
    if not 6 <= a.seconds <= 15:
        sys.exit("--seconds must be 6-15")
    pal, brand_path = load_brand(a.brand)
    if a.bg and a.bg != "auto":
        pad = hex_rgb(a.bg)
        if pal.get("bg") and dist(pad, pal["bg"]) > 30:
            print(f"warning: --bg {a.bg} is not brand.json's bg (#{'%02X%02X%02X' % pal['bg']}); the pad will not "
                  "match the posts. Leave --bg out (auto) unless that is deliberate.", file=sys.stderr)
    else:
        pad = pal.get("bg")  # None -> each still's own edge colour
    alpha_pad = None
    if pad is None:  # transparent stills (cutouts) sit on the set's own background, not on their own colour
        opaque = [Image.open(p) for p in a.stills]
        opaque = [edge_colour(o) for o in opaque if not has_alpha(o)]
        alpha_pad = max(opaque, key=opaque.count) if opaque else None
    fitted = [fit_frame(p, pad, alpha_pad) for p in a.stills]
    stills = [f[0] for f in fitted]
    if any(f[1] for f in fitted):
        src = f"brand.json bg from {brand_path}" if pad and not (a.bg and a.bg != "auto") else (
            a.bg if a.bg and a.bg != "auto" else "each still's own edge colours (no brand.json found)")
        print(f"note: non-9:16 stills padded with {src}", file=sys.stderr)
    n = len(stills)
    total = int(round(a.seconds * FPS))
    if n == 1:
        bounds = [(0, total)]
    else:
        first = int(total / n * 0.8)  # hook slide a touch shorter
        rest = (total - first) / (n - 1)
        edges = [0, first] + [int(first + rest * i) for i in range(1, n)]
        edges[-1] = total
        bounds = list(zip(edges[:-1], edges[1:]))
    if min(e - s for s, e in bounds) < FPS * 1.2:
        print("warning: some slides are on screen under 1.2 s; use fewer stills or more --seconds", file=sys.stderr)

    # transitions, one per boundary, centred on the beat
    dur = 0 if a.fade is not None and a.fade <= 0 else min(0.5, max(0.1, a.fade if a.fade is not None else 0.25))
    kinds = []
    for i in range(n - 1):
        k = a.transition
        if dur == 0:
            k = "cut"
        elif k == "auto":
            k = "cut" if beats_of_one_layout(stills[i], stills[i + 1]) else "fade"
        kinds.append(k)
    half = int(round(dur * FPS / 2))
    windows = []  # (start_frame, end_frame, i, kind) for non-cut transitions
    for i, k in enumerate(kinds):
        if k != "cut":
            b = bounds[i][1]
            windows.append((b - half, b + half, i, k))
    print("transitions: " + (", ".join(f"{i + 1}->{i + 2} {k}" for i, k in enumerate(kinds)) or "none")
          + (f" ({dur:.2f}s, eased)" if any(k != "cut" for k in kinds) else ""), file=sys.stderr)

    slide_times = [(s / FPS, e / FPS) for s, e in bounds]
    pal_band, pal_ink = caption_colours(pal, stills)
    cap = Captioner(clean_cues(load_cues(a, slide_times), a.seconds), a.caption_size, pal_band, pal_ink)
    cap.place(stills)
    proc = open_ffmpeg(a.out, a.seconds)

    for f in range(total):
        z = 1 + (a.zoom - 1) * f / max(1, total - 1)  # one continuous camera move for the whole clip
        win = next((w for w in windows if w[0] <= f < w[1]), None)
        if win:
            s0, s1, i, k = win
            t = ease((f - s0 + 0.5) / (s1 - s0))
            out_fr, in_fr = push_in(stills[i], z), push_in(stills[i + 1], z)
            if k == "fade":
                fr = Image.blend(out_fr, in_fr, t)
            else:  # push: the next still slides up and the last one leaves upward
                off = int(round(t * H))
                fr = Image.new("RGB", (W, H))
                fr.paste(out_fr, (0, -off))
                fr.paste(in_fr, (0, H - off))
            fr = cap.apply(fr, f / FPS, hidden=True)
        else:
            i = next(k for k, (s, e) in enumerate(bounds) if s <= f < e)
            fr = cap.apply(push_in(stills[i], z), f / FPS)
        proc.stdin.write(fr.tobytes())
    finish(proc, a.out)
    return 0


# ------------------------------------------------------------------ html
def cmd_html(a):
    if not 6 <= a.seconds <= 15:
        sys.exit("--seconds must be 6-15")
    _env.need("playwright")
    from playwright.sync_api import sync_playwright  # type: ignore
    import io
    pal, _ = load_brand(a.brand)
    total = int(round(a.seconds * FPS))
    cues = clean_cues(load_cues(a), a.seconds)
    proc = None
    with sync_playwright() as pw:
        kw = {"args": ["--no-sandbox", "--hide-scrollbars"]}
        exe = _env.tools().get("chromium")
        if exe:
            kw["executable_path"] = exe
        browser = pw.chromium.launch(**kw)
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto(Path(a.html).resolve().as_uri(), wait_until="load", timeout=30000)
        page.evaluate("document.fonts ? document.fonts.ready.then(()=>true) : true")
        page.wait_for_timeout(300)
        if page.evaluate("document.getAnimations().length") == 0:
            print("warning: the page has no CSS animations/transitions; the video will be a still", file=sys.stderr)

        def grab(t_ms):
            page.evaluate("t => { for (const an of document.getAnimations()) { an.pause(); an.currentTime = t; } }", t_ms)
            fr = Image.open(io.BytesIO(page.screenshot(type="png", full_page=False))).convert("RGB")
            return fr if fr.size == (W, H) else fr.resize((W, H))

        samples = [grab(total / FPS * 1000 * k / 4) for k in range(4)]
        cap = Captioner(cues, a.caption_size, *caption_colours(pal, samples))
        cap.place(samples)
        proc = open_ffmpeg(a.out, a.seconds)
        for f in range(total):
            proc.stdin.write(cap.apply(grab(f / FPS * 1000), f / FPS).tobytes())
        browser.close()
    finish(proc, a.out)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--seconds", type=float, default=8)
    common.add_argument("--captions-file")
    common.add_argument("--caption-size", type=int, default=68)
    common.add_argument("--brand", help="brand.json (default: ./brand.json, else out/brand.json)")
    common.add_argument("--out", required=True)
    s = sub.add_parser("slides", parents=[common])
    s.add_argument("stills", nargs="+")
    s.add_argument("--bg", default="auto", help="pad colour for non-9:16 stills: auto (brand bg / still edge) or #hex")
    s.add_argument("--zoom", type=float, default=1.0,
                   help="slow push-in across the whole clip, e.g. 1.04 for photo slides; 1.0 (default) = off")
    s.add_argument("--transition", default="auto", choices=["auto", "cut", "fade", "push"])
    s.add_argument("--fade", type=float, default=None, help="transition length in s (0.1-0.5, default 0.25); 0 = cuts")
    s.add_argument("--captions", nargs="+")
    s = sub.add_parser("html", parents=[common])
    s.add_argument("html")
    a = ap.parse_args()
    if a.out and not str(a.out).lower().endswith(".mp4"):
        sys.exit("--out must be an .mp4")
    sys.exit({"slides": cmd_slides, "html": cmd_html}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
