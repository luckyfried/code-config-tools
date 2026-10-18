#!/usr/bin/env python3
"""Mockups without a photo shoot: phone frame, product-in-scene composite, three.js product render.

USAGE (from the workspace root):
  python3 S/scripts/mockup.py phone --screen build/screen.png [--color graphite|silver|sand] [--width 900]
                                    --out build/mock/phone.png
      -> transparent PNG of a modern phone (rounded body, island, soft shadow) with the screen image fitted
         (top-aligned crop, so a website/app screenshot shows its top). Drop it into a template image slot.
  python3 S/scripts/mockup.py scene --product build/photos/mug-cut.png [--bg build/photos/table.jpg | --bg "#F3EDE4"]
                                    --format 1080x1350|ig_feed_portrait [--scale 0.62] [--x 0.5] [--floor 0.82]
                                    --out build/mock/scene.jpg
      -> product (transparent PNG) standing on a background with a soft contact shadow.
  python3 S/scripts/mockup.py product3d --init build/product3d.html
      -> copies the three.js product template; edit its PARTS block to the product's silhouette.
  python3 S/scripts/mockup.py product3d --html build/product3d.html [--state lit|unlit] [--size 1080x1080]
                                    [--bg transparent|#hex] [--cam 3.2,2.4,4.2] --out build/mock/product-lit.png
      -> headless-Chromium render (software GL; ~10 s). Needs network once for three.js from jsDelivr.

A mockup shows the real thing (their app screen, their product shape). Never put a stock
device around somebody else's screen, and never invent product details.
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

_env.need("PIL")
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps  # noqa: E402

BODY = {"graphite": ((38, 38, 40), (70, 70, 74)), "silver": ((214, 214, 210), (240, 240, 236)),
        "sand": ((196, 176, 150), (226, 210, 186))}


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def parse_size(fmt):
    if "x" in fmt and fmt.replace("x", "").isdigit():
        w, h = fmt.split("x")
        return int(w), int(h)
    f = next((r for r in _env.formats() if r["key"] == fmt), None)
    if not f:
        sys.exit(f"unknown format '{fmt}'")
    return int(f["w"]), int(f["h"])


def rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def cmd_phone(a):
    SS = 2  # supersample for clean edges
    W = a.width * SS
    H = int(W * 2.05)
    pad = int(W * 0.12)  # room for shadow
    bezel = int(W * 0.035)
    R = int(W * 0.17)
    body_c, edge_c = BODY[a.color]
    canvas = Image.new("RGBA", (W + pad * 2, H + pad * 2), (0, 0, 0, 0))
    # shadow
    sh = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([pad + W * 0.04, pad + H * 0.03, pad + W * 0.96, pad + H * 1.01], radius=R, fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(W * 0.045))
    canvas.paste(Image.new("RGBA", canvas.size, (0, 0, 0, 255)), (0, 0), sh)
    # body with a subtle edge highlight
    body = Image.new("RGBA", (W, H), edge_c + (255,))
    inner = Image.new("RGBA", (W - 6 * SS, H - 6 * SS), body_c + (255,))
    body.paste(inner, (3 * SS, 3 * SS), rounded_mask(inner.size, R - 3 * SS))
    canvas.paste(body, (pad, pad), rounded_mask((W, H), R))
    # screen
    sw, shh = W - 2 * bezel, H - 2 * bezel
    scr = ImageOps.exif_transpose(Image.open(a.screen)).convert("RGB")
    scale = sw / scr.width
    scr = scr.resize((sw, max(shh, int(scr.height * scale))), Image.LANCZOS).crop((0, 0, sw, shh))
    canvas.paste(scr, (pad + bezel, pad + bezel), rounded_mask((sw, shh), R - bezel))
    # dynamic island
    d = ImageDraw.Draw(canvas)
    iw, ih = int(W * 0.29), int(W * 0.085)
    ix, iy = pad + (W - iw) // 2, pad + bezel + int(W * 0.03)
    d.rounded_rectangle([ix, iy, ix + iw, iy + ih], radius=ih // 2, fill=(8, 8, 8, 255))
    # side buttons
    for y0, ln in ((0.2, 0.06), (0.29, 0.1), (0.41, 0.1)):
        d.rounded_rectangle([pad - 3 * SS, pad + H * y0, pad + 1 * SS, pad + H * (y0 + ln)], radius=2 * SS, fill=edge_c + (255,))
    d.rounded_rectangle([pad + W - SS, pad + H * 0.3, pad + W + 3 * SS, pad + H * 0.43], radius=2 * SS, fill=edge_c + (255,))
    out = canvas.resize((canvas.width // SS, canvas.height // SS), Image.LANCZOS)
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(f"saved {dest.resolve()} {out.size[0]}x{out.size[1]} RGBA. Open it: the screen must be legible and theirs.")
    return 0


def cmd_scene(a):
    tw, th = parse_size(a.format)
    if a.bg.startswith("#"):
        bg = Image.new("RGB", (tw, th), hex_rgb(a.bg))
        # gentle floor/wall split so the product has somewhere to stand
        floor_y = int(th * a.floor)
        fl = Image.new("RGB", (tw, th - floor_y), tuple(max(0, int(c * 0.93)) for c in hex_rgb(a.bg)))
        bg.paste(fl, (0, floor_y))
        bg = bg.filter(ImageFilter.GaussianBlur(2))
    else:
        src = ImageOps.exif_transpose(Image.open(a.bg)).convert("RGB")
        bg = ImageOps.fit(src, (tw, th), Image.LANCZOS)
    prod = Image.open(a.product).convert("RGBA")
    bbox = prod.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if bbox:
        prod = prod.crop(bbox)
    target_h = int(th * a.scale)
    if prod.width * target_h / prod.height > tw * 0.86:
        target_h = int(tw * 0.86 * prod.height / prod.width)
    prod = prod.resize((max(1, int(prod.width * target_h / prod.height)), target_h), Image.LANCZOS)
    base_y = int(th * a.floor)
    px = int(tw * a.x - prod.width / 2)
    py = base_y - prod.height
    # contact shadow: squashed, blurred ellipse at the base + faint drop
    shadow = Image.new("L", (tw, th), 0)
    sd = ImageDraw.Draw(shadow)
    sw = int(prod.width * 0.92)
    sd.ellipse([px + (prod.width - sw) // 2, base_y - int(sw * 0.06), px + (prod.width + sw) // 2, base_y + int(sw * 0.06)], fill=150)
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(4, sw * 0.04)))
    drop = Image.new("L", (tw, th), 0)
    drop.paste(prod.getchannel("A").point(lambda v: int(v * 0.35)), (px + int(prod.width * 0.05), py + int(prod.height * 0.03)))
    drop = drop.filter(ImageFilter.GaussianBlur(max(6, prod.width * 0.05)))
    shadow = ImageChops.lighter(shadow, drop)
    bg = Image.composite(Image.new("RGB", (tw, th), (20, 16, 12)), bg, shadow)
    bg.paste(prod, (px, py), prod)
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    bg.save(dest, quality=92) if dest.suffix.lower() in (".jpg", ".jpeg") else bg.save(dest)
    print(f"saved {dest.resolve()} {tw}x{th}. Open it: does the product sit ON the surface (not float), at a believable size?")
    return 0


def cmd_product3d(a):
    tpl = Path(__file__).resolve().parent / "product3d.html"
    if a.init:
        dest = Path(a.init)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            print(f"{dest} exists; not overwriting")
        else:
            shutil.copy(tpl, dest)
            print(f"copied template to {dest}. Edit the PARTS block (lathe profiles = [radius, height] bottom to top;"
                  " colours in MAT) to match the product, then render with --html.")
        return 0
    if not a.html or not a.out:
        sys.exit("need --init PATH, or --html PATH --out PATH")
    chrome = _env.chromium()
    if not chrome:
        sys.exit("no Chromium/Chrome found (run setup.py). Fall back to a photo or type-only layout.")
    w, h = parse_size(a.size)
    from urllib.parse import quote
    url = (Path(a.html).resolve().as_uri() + f"?w={w}&h={h}&state={a.state}&bg={quote(a.bg)}"
           + (f"&cam={a.cam}" if a.cam else ""))
    dest = Path(a.out).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as prof:
        cmd = [chrome, "--headless=new", "--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
               "--hide-scrollbars", "--disable-gpu-sandbox", f"--user-data-dir={prof}", f"--window-size={w},{h}",
               "--virtual-time-budget=15000", f"--screenshot={dest}"]
        if a.bg == "transparent":
            cmd.append("--default-background-color=00000000")
        cmd.append(url)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            sys.exit("render timed out (120 s)")
    if not dest.exists():
        sys.exit(f"render failed: {r.stderr[-600:]}")
    im = Image.open(dest)
    if im.convert("RGB").getextrema() and all(lo == hi for lo, hi in im.convert("RGB").getextrema()):
        sys.exit("render is a flat colour: three.js probably didn't load (no network?) or WebGL failed. "
                 "Use a photo or a type-only layout instead.")
    print(f"saved {dest} {im.size[0]}x{im.size[1]} {im.mode}. Open it: silhouette right? same model in every image?")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("phone")
    s.add_argument("--screen", required=True)
    s.add_argument("--color", default="graphite", choices=list(BODY))
    s.add_argument("--width", type=int, default=900, help="phone body width in px")
    s.add_argument("--out", required=True)
    s = sub.add_parser("scene")
    s.add_argument("--product", required=True)
    s.add_argument("--bg", default="#F3EDE4", help="background photo path or #hex")
    s.add_argument("--format", required=True)
    s.add_argument("--scale", type=float, default=0.62, help="product height as share of frame height")
    s.add_argument("--x", type=float, default=0.5, help="horizontal centre 0-1")
    s.add_argument("--floor", type=float, default=0.82, help="where the product stands, 0-1 from top")
    s.add_argument("--out", required=True)
    s = sub.add_parser("product3d")
    s.add_argument("--init")
    s.add_argument("--html")
    s.add_argument("--state", default="lit", choices=["lit", "unlit"])
    s.add_argument("--size", default="1080x1080")
    s.add_argument("--bg", default="transparent")
    s.add_argument("--cam")
    s.add_argument("--out")
    a = ap.parse_args()
    sys.exit({"phone": cmd_phone, "scene": cmd_scene, "product3d": cmd_product3d}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
