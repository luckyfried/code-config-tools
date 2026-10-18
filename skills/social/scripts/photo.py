#!/usr/bin/env python3
"""User-photo prep: inspect, contact-sheet, smart-crop to a format, light grade, cutout.

USAGE (from the workspace root):
  python3 S/scripts/photo.py info in/*                     # size, orientation, sharpness, brightness, verdict per photo
  python3 S/scripts/photo.py sheet in/ --out build/in-sheet.jpg   # numbered contact sheet of every image (READ IT)
  python3 S/scripts/photo.py fit in/IMG_1.jpg --format 1080x1350|ig_story [--focus auto|0.4,0.6|center]
                                 [--grade warm|neutral|cool|none] [--out build/photos/p01.jpg]
      -> cropped + resized photo, prints the focal point used (pass it to templates as focal_x/focal_y)
  python3 S/scripts/photo.py cutout in/mug.jpg --out build/photos/mug-cut.png
      -> transparent PNG. Uses rembg if it can be installed; otherwise keys out a plain, even
         background sampled from the edges (fine for product-on-white/table shots; says so if it isn't).

Grades are deliberately light: a small warmth/contrast nudge so a set looks consistent. Never
heavy filters. Use the same grade on every photo in a set.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}


def open_img(p):
    p = Path(p)
    if p.suffix.lower() in (".heic", ".heif"):
        try:
            import pillow_heif  # type: ignore
            pillow_heif.register_heif_opener()
        except ImportError:
            try:
                _env.need("pillow_heif")
                import pillow_heif  # type: ignore
                pillow_heif.register_heif_opener()
            except Exception:
                sys.exit(f"{p.name}: HEIC needs pillow-heif (pip install pillow-heif) or convert it first "
                         "(macOS: sips -s format jpeg in.heic --out in.jpg)")
    im = Image.open(p)
    im = ImageOps.exif_transpose(im)  # phone photos: respect rotation
    return im


def list_images(args):
    out = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in EXTS)
        elif p.suffix.lower() in EXTS and p.exists():
            out.append(p)
    return out


def sharpness(im):
    g = im.convert("L")
    g.thumbnail((800, 800))
    lap = g.filter(ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128))
    return ImageStat.Stat(lap).var[0]


def describe(p):
    im = open_img(p)
    w, h = im.size
    rgb = im.convert("RGB")
    st = ImageStat.Stat(rgb.convert("L"))
    bright = st.mean[0]
    contrast = st.stddev[0]
    sharp = sharpness(rgb)
    orient = "portrait" if h > w * 1.05 else "landscape" if w > h * 1.05 else "square"
    notes = []
    if min(w, h) < 1080:
        notes.append(f"small (short side {min(w, h)}px): fine for a half-frame slot, soft if full-bleed")
    if sharp < 60:
        notes.append("blurry/soft")
    if bright < 60:
        notes.append("dark: try --grade warm or pick another")
    if bright > 215:
        notes.append("very bright/washed")
    if contrast < 30:
        notes.append("flat/low contrast")
    verdict = "USE" if not notes else ("WEAK" if len(notes) == 1 and "small" in notes[0] else "CHECK")
    return {"file": str(p), "w": w, "h": h, "orientation": orient, "sharpness": round(sharp),
            "brightness": round(bright), "contrast": round(contrast), "verdict": verdict, "notes": notes}


def cmd_info(a):
    files = list_images(a.files)
    if not files:
        print("no images found")
        return 0
    for p in files:
        try:
            d = describe(p)
        except SystemExit:
            raise
        except Exception as e:
            print(f"{Path(p).name}: unreadable ({e})")
            continue
        print(f"{Path(p).name}: {d['w']}x{d['h']} {d['orientation']}, sharpness {d['sharpness']}, "
              f"brightness {d['brightness']}, contrast {d['contrast']} -> {d['verdict']}"
              + (f" ({'; '.join(d['notes'])})" if d["notes"] else ""))
    print("\nNumbers are hints. Open the photos (or `photo.py sheet`) and judge what they SHOW.")
    return 0


def cmd_sheet(a):
    files = list_images(a.files)
    if not files:
        print("no images found")
        return 0
    cw, ch, pad, lab, cols = 320, 320, 14, 40, 4
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + lab + pad) + pad), (238, 235, 230))
    d = ImageDraw.Draw(sheet)
    fb, ft = _env.pil_font(26, "bold"), _env.pil_font(14, "text")
    for k, p in enumerate(files):
        x = pad + (k % cols) * (cw + pad)
        y = pad + (k // cols) * (ch + lab + pad)
        try:
            im = open_img(p).convert("RGB")
            size = im.size
            im.thumbnail((cw, ch))
            sheet.paste(im, (x + (cw - im.width) // 2, y + (ch - im.height) // 2))
        except Exception:
            size = ("?", "?")
            d.text((x + 10, y + ch // 2), "unreadable", fill=(120, 120, 120), font=ft)
        d.rectangle([x, y, x + 44, y + 36], fill=(20, 20, 20))
        d.text((x + 8, y + 3), str(k + 1), fill=(255, 255, 255), font=fb)
        d.text((x, y + ch + 4), f"{Path(p).name[:34]}  {size[0]}x{size[1]}", fill=(30, 30, 30), font=ft)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    print(f"sheet: {out}  ({len(files)} images). Read it.")
    return 0


def parse_size(fmt):
    if "x" in fmt and fmt.replace("x", "").isdigit():
        w, h = fmt.split("x")
        return int(w), int(h)
    f = next((r for r in _env.formats() if r["key"] == fmt), None)
    if not f:
        sys.exit(f"unknown format '{fmt}'. Use WxH or a key from formats.json")
    return int(f["w"]), int(f["h"])


def saliency(im):
    """Cheap saliency map: local detail (edges) + colour saturation + mild centre bias. Returns (map, w, h)."""
    small = im.convert("RGB").copy()
    small.thumbnail((160, 160))
    w, h = small.size
    edges = small.convert("L").filter(ImageFilter.FIND_EDGES).filter(ImageFilter.BoxBlur(3))
    sat = small.convert("HSV").split()[1].filter(ImageFilter.BoxBlur(3))
    e, s = edges.load(), sat.load()
    m = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            dx, dy = (x / w - 0.5) * 2, (y / h - 0.5) * 2
            centre = 1.0 - 0.35 * min(1.0, (dx * dx + dy * dy) ** 0.5)
            border = x < 3 or y < 3 or x >= w - 3 or y >= h - 3  # FIND_EDGES rings the frame
            m[y][x] = 0.0 if border else (0.6 * e[x, y] + 0.4 * s[x, y]) * centre
    return m, w, h


def best_window(m, w, h, cw, ch):
    """Slide a cw x ch window over the map, return the top-left with the most energy (integral image)."""
    ii = [[0.0] * (w + 1) for _ in range(h + 1)]
    for y in range(h):
        row = 0.0
        for x in range(w):
            row += m[y][x]
            ii[y + 1][x + 1] = ii[y][x + 1] + row
    best, bx, by = -1, 0, 0
    step = max(1, min(w, h) // 60)
    for y in range(0, h - ch + 1, step):
        for x in range(0, w - cw + 1, step):
            v = ii[y + ch][x + cw] - ii[y][x + cw] - ii[y + ch][x] + ii[y][x]
            if v > best:
                best, bx, by = v, x, y
    return bx, by


def focal_point(im):
    m, w, h = saliency(im)
    tot = sum(sum(r) for r in m) or 1
    fx = sum(m[y][x] * x for y in range(h) for x in range(w)) / tot / w
    fy = sum(m[y][x] * y for y in range(h) for x in range(w)) / tot / h
    return fx, fy, m, w, h


def grade(im, kind):
    if kind in (None, "none"):
        return im
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(1.05 if kind != "neutral" else 1.02)
    if kind in ("warm", "cool"):
        r, g, b = im.split()
        if kind == "warm":
            r = r.point(lambda v: min(255, int(v * 1.035 + 2)))
            b = b.point(lambda v: int(v * 0.965))
        else:
            b = b.point(lambda v: min(255, int(v * 1.03 + 2)))
            r = r.point(lambda v: int(v * 0.97))
        im = Image.merge("RGB", (r, g, b))
    return im


def cmd_fit(a):
    tw, th = parse_size(a.format)
    im = open_img(a.file).convert("RGB")
    W, H = im.size
    target = tw / th
    if W / H > target:
        cw, ch = int(H * target), H
    else:
        cw, ch = W, int(W / target)
    if a.focus == "center":
        fx, fy = 0.5, 0.5
        x0, y0 = (W - cw) // 2, (H - ch) // 2
    elif a.focus == "auto":
        fx, fy, m, mw, mh = focal_point(im)
        sx, sy = mw / W, mh / H
        ww, wh = max(1, round(cw * sx)), max(1, round(ch * sy))
        wx, wy = best_window(m, mw, mh, ww, wh)
        # centre the crop on the energy centroid inside the best window (subject centred, not edge-hugging)
        tot = sum(m[y][x] for y in range(wy, min(mh, wy + wh)) for x in range(wx, min(mw, wx + ww))) or 0
        if tot:
            fx = sum(m[y][x] * x for y in range(wy, min(mh, wy + wh)) for x in range(wx, min(mw, wx + ww))) / tot / mw
            fy = sum(m[y][x] * y for y in range(wy, min(mh, wy + wh)) for x in range(wx, min(mw, wx + ww))) / tot / mh
        x0 = int(min(max(fx * W - cw / 2, 0), W - cw))
        y0 = int(min(max(fy * H - ch / 2, 0), H - ch))
    else:
        try:
            fx, fy = (float(v) for v in a.focus.split(","))
        except ValueError:
            sys.exit("--focus must be auto, center, or x,y between 0 and 1 (e.g. 0.4,0.6)")
        x0 = int(min(max(fx * W - cw / 2, 0), W - cw))
        y0 = int(min(max(fy * H - ch / 2, 0), H - ch))
    crop = im.crop((x0, y0, x0 + cw, y0 + ch))
    upscale = tw / cw
    out = crop.resize((tw, th), Image.LANCZOS)
    if upscale > 1.05:
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    out = grade(out, a.grade)
    dest = Path(a.out or f"build/photos/{Path(a.file).stem}-{tw}x{th}.jpg")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() == ".png":
        out.save(dest)
    else:
        out.save(dest, quality=92)
    # focal point relative to the cropped frame, for templates' focal_x/focal_y
    rfx = min(1, max(0, (fx * W - x0) / cw))
    rfy = min(1, max(0, (fy * H - y0) / ch))
    print(f"saved {dest.resolve()}  crop {cw}x{ch} at ({x0},{y0}) -> {tw}x{th}"
          + (f"  UPSCALED x{upscale:.2f}: may look soft at full bleed" if upscale > 1.3 else ""))
    print(f"focal_x {rfx:.2f}  focal_y {rfy:.2f}   (open the result: is the subject whole and not cut at an edge?)")
    return 0


def cmd_cutout(a):
    src = open_img(a.file).convert("RGBA")
    dest = Path(a.out or f"build/photos/{Path(a.file).stem}-cut.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not a.no_rembg:
        try:
            import os
            os.environ.setdefault("TQDM_DISABLE", "1")  # no progress-bar spam in the agent's context
            _env.need("rembg", "onnxruntime")
            from rembg import new_session, remove  # type: ignore
            model = os.environ.get("SOCIAL_REMBG_MODEL", "bria-rmbg")
            home = Path(os.environ.get("U2NET_HOME") or Path.home() / ".rembg")
            if not any(home.rglob(f"{model}*.onnx")) and not any((Path.home() / ".u2net").glob(f"{model}*.onnx")):
                print(f"first cutout: downloading the free '{model}' model once (bria is ~1 GB; 1-3 min). "
                      "Set SOCIAL_REMBG_MODEL=u2net for a 170 MB, rougher one.", file=sys.stderr)
            out = remove(src, session=new_session(model))
            bbox = out.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
            if bbox:
                out = out.crop(bbox)
            out.save(dest)
            print(f"saved {dest.resolve()} (rembg). Open it: check edges, hands, and thin parts.")
            return 0
        except Exception as e:
            print(f"rembg unavailable ({str(e)[:80]}); using plain-background key", file=sys.stderr)
    rgb = src.convert("RGB")
    W, H = rgb.size
    px = rgb.load()
    edge = [px[x, 0] for x in range(0, W, max(1, W // 50))] + [px[x, H - 1] for x in range(0, W, max(1, W // 50))] \
        + [px[0, y] for y in range(0, H, max(1, H // 50))] + [px[W - 1, y] for y in range(0, H, max(1, H // 50))]
    bg = tuple(sorted(c[i] for c in edge)[len(edge) // 2] for i in range(3))
    spread = sum(sum(abs(c[i] - bg[i]) for i in range(3)) for c in edge) / len(edge)
    if spread > 45:
        print(f"background is not plain (edge spread {spread:.0f}); a key cutout would look bad. "
              "Use the photo uncut in a hero layout instead, or install rembg.", file=sys.stderr)
        return 2
    tol = max(28, spread * 2.2)
    diff = Image.new("L", (W, H))
    dp = diff.load()
    for y in range(H):
        for x in range(W):
            c = px[x, y]
            d = abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2])
            dp[x, y] = 0 if d < tol else min(255, int((d - tol) * 4))
    # keep only what's connected to the subject: fill background from the edges
    mask = diff.point(lambda v: 255 if v > 0 else 0)
    flood = mask.copy()
    for seed in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        if flood.getpixel(seed) == 0:
            ImageDraw.floodfill(flood, seed, 128)
    alpha = flood.point(lambda v: 0 if v == 128 else 255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    out = src.copy()
    out.putalpha(alpha)
    bbox = alpha.point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        out = out.crop(bbox)
    out.save(dest)
    print(f"saved {dest.resolve()} (plain-background key, bg {bg}). Open it: background enclosed by the product (inside a handle or loop) stays opaque, and halos or holes mean use the photo uncut.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("info")
    s.add_argument("files", nargs="+")
    s = sub.add_parser("sheet")
    s.add_argument("files", nargs="+")
    s.add_argument("--out", default="build/in-sheet.jpg")
    s = sub.add_parser("fit")
    s.add_argument("file")
    s.add_argument("--format", required=True)
    s.add_argument("--focus", default="auto")
    s.add_argument("--grade", default="none", choices=["warm", "neutral", "cool", "none"])
    s.add_argument("--out")
    s = sub.add_parser("cutout")
    s.add_argument("file")
    s.add_argument("--out")
    s.add_argument("--no-rembg", action="store_true", help="skip rembg, use the plain-background key")
    a = ap.parse_args()
    sys.exit({"info": cmd_info, "sheet": cmd_sheet, "fit": cmd_fit, "cutout": cmd_cutout}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
