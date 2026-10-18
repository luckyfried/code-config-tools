#!/usr/bin/env python3
"""
USAGE (the pipeline's way: render the agent's own HTML design):
    python3 scripts/render.py --html build/html/p01.html --format ig_feed_portrait \
        --brand brand.json --out out/p01-name-1080x1350.png
        # batch entries use "html": "build/html/p01.html" instead of "template"
        # Authoring contract: references/html-authoring.md (fonts, brand vars, data-fit, safe zones, images)

    python3 scripts/render.py --template editorial/hero --format 1080x1350 \
        --data slide.json --brand brand.json --out out/x.png
        # LEGACY: fills a reference-library template. Kept only for the gallery builder;
        # the pipeline must not use it (qa.py gate rejects "template" jobs).

    python3 scripts/render.py --template editorial/hero --format ig_story --out out/x.png
        # --format accepts a formats.json key (e.g. ig_story) OR a literal WxH (e.g. 1080x1920)
        # --data/--brand are optional; manifest.json slot defaults + a built-in default
        # brand are used if omitted, so a bare render always produces something.

    python3 scripts/render.py --list
        # prints the full template catalog (family, layout, slots, formats, max_chars) as JSON

    python3 scripts/render.py --batch plan.json
        # plan.json: [{"template": "...", "format": "...", "data": {...}|"path.json",
        #              "brand": {...}|"path.json", "out": "out/x.png"}, ...]
        # Renders every entry in ONE browser session (fast: one Chromium launch for N images).

Renderer contract (Social toolkit v3 spec): template + format + data JSON + brand.json -> PNG.
- Fonts resolve locally (bundled OFL families in fonts/), no CDN at render time.
- Text auto-fits to its slot (shrink-to-fit via a binary-search font-size pass; never overflows;
  a last-resort line-clamp only applies to secondary copy, never the headline).
- Image slots accept a local path; object-fit + focal point (--object-position / data focal_x/y)
  are honored by the template CSS.
- Fails loudly (non-zero exit, no PNG written) if a safe-zone-checked element breaches the
  format's safe zone (formats.json), e.g. story/reel headline sitting under the UI chrome band.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
FORMATS_PATH = SKILL_DIR / "formats.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup as bootstrap  # noqa: E402
import _env  # noqa: E402  (stdlib only)

DEFAULT_BRAND = {
    "name": "Brand",
    "palette": {"bg": "#F1ECE1", "fg": "#1F2A24", "accent": "#B6862C", "accent2": "#5C6B3F"},
    "logo": None,
}

AUTOFIT_JS = r"""
(() => {
  const results = [];
  document.querySelectorAll('[data-autofit]').forEach(el => {
    const box = el.closest('[data-autofit-box]') || el.parentElement;
    const minRatio = parseFloat(el.getAttribute('data-autofit-min') || '0.38');
    const cs = getComputedStyle(el);
    const startPx = parseFloat(cs.fontSize);
    const minPx = startPx * minRatio;
    let px = startPx;
    const fits = () => el.scrollWidth <= box.clientWidth + 1 && el.scrollHeight <= box.clientHeight + 1;
    let guard = 0;
    while (!fits() && px > minPx && guard < 60) {
      px -= Math.max(0.5, px * 0.04);
      el.style.fontSize = px + 'px';
      guard++;
    }
    if (!fits() && el.hasAttribute('data-autofit-clamp')) {
      el.style.display = '-webkit-box';
      el.style.webkitBoxOrient = 'vertical';
      el.style.overflow = 'hidden';
      el.style.webkitLineClamp = el.getAttribute('data-autofit-clamp');
    }
    results.push({ id: el.getAttribute('data-slot') || el.className, startPx, finalPx: px, overflow: !fits() });
  });
  return results;
})();
"""

SAFE_ZONE_JS = r"""
(zone) => {
  const w = window.innerWidth, h = window.innerHeight;
  const bad = [];
  document.querySelectorAll('[data-safe-check]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const breaches = (r.top < zone.top) || (r.bottom > h - zone.bottom) ||
                      (r.left < zone.left) || (r.right > w - zone.right);
    if (breaches) {
      bad.push({ slot: el.getAttribute('data-slot') || el.className,
                 rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right } });
    }
  });
  return bad;
}
"""


def load_formats():
    return json.loads(FORMATS_PATH.read_text())


def resolve_format(spec, formats, out_name=""):
    """formats.json key -> its size + safe zone. A literal WxH is mapped to the formats.json entry of
    that size (file-name hints pick e.g. tiktok_cover over ig_story for '...-reel-...'), so a bare
    1080x1920 still gets the Story safe-zone check."""
    if spec in formats:
        f = formats[spec]
        return f["w"], f["h"], f.get("safe_zone"), spec
    if re.fullmatch(r"\d{2,5}x\d{2,5}", spec.lower()):
        w, h = (int(v) for v in spec.lower().split("x"))
        m = _env.match_format(out_name, w, h)
        if m:
            return w, h, m.get("safe_zone"), m["key"]
        return w, h, None, spec
    raise SystemExit(f"Unknown format '{spec}': not in formats.json and not a WxH form like 1080x1350")


def catalog():
    out = []
    for family_dir in sorted(TEMPLATES_DIR.iterdir()):
        if not family_dir.is_dir() or family_dir.name.startswith("_"):
            continue
        for layout_dir in sorted(family_dir.iterdir()):
            manifest = layout_dir / "manifest.json"
            if not manifest.exists():
                continue
            m = json.loads(manifest.read_text())
            out.append({"template": f"{family_dir.name}/{layout_dir.name}", **m})
    return out


def merge_brand(b):
    # Only the palette keys the brand actually sets become CSS overrides; every other key keeps the
    # template family's own default (filling them from DEFAULT_BRAND turned every family beige/green).
    b = dict(b or {})
    return {**DEFAULT_BRAND, **b, "palette": dict(b.get("palette") or {})}


def load_json_arg(val):
    """val may be a dict already, an inline JSON string, or a path to a .json file."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    p = Path(val)
    if p.exists():
        return json.loads(p.read_text())
    return json.loads(val)


def brand_css_vars(brand, data=None):
    pal = brand.get("palette", {})
    lines = [f"--{k}: {v};" for k, v in pal.items()]
    focal = focal_css(data or {})
    if focal:
        lines.append(f"--focal: {focal};")
    fonts = brand.get("fonts", {})
    for k, v in fonts.items():
        # font-family values need quoting unless already quoted or a generic keyword/comma-list.
        vv = str(v).strip()
        if vv and vv[0] not in "\"'" and "," not in vv and " " in vv:
            vv = f"'{vv}'"
        lines.append(f"--font-{k}: {vv};")
    return "\n".join(lines)


def focal_css(data):
    """data focal_x/focal_y (0-1) or focal ('30% 40%', 'center', 'top') -> CSS object-position."""
    fx, fy = data.get("focal_x"), data.get("focal_y")
    if fx is not None or fy is not None:
        try:
            fx = 0.5 if fx is None else min(1.0, max(0.0, float(fx)))
            fy = 0.5 if fy is None else min(1.0, max(0.0, float(fy)))
            return f"{fx * 100:.1f}% {fy * 100:.1f}%"
        except (TypeError, ValueError):
            pass
    f = data.get("focal")
    if isinstance(f, str) and re.fullmatch(r"[a-z0-9.% ]{1,40}", f.strip().lower()):
        return f.strip()
    return None


def image_src(val):
    """Local paths (absolute, or relative to the workspace/cwd) -> file:// URIs, so spaces, '#' and
    relative paths all work even though the page renders from the template's own folder."""
    v = str(val).strip()
    if not v or re.match(r"^(https?|data|file):", v, re.I):
        return v
    p = Path(v).expanduser()
    if not p.is_absolute():
        cand = Path.cwd() / p
        if cand.exists():
            p = cand
        else:
            return v  # template-relative default (e.g. ../../_shared/placeholder/x.svg)
    if not p.exists():
        print(f"WARNING: image not found: {v}", file=sys.stderr)
    return p.resolve().as_uri()


def fill_template(html_src, slots, defaults, max_chars, brand):
    data = {**defaults, **slots}
    out = html_src.replace("/*{brand_css}*/", brand_css_vars(brand, data))
    for key, val in data.items():
        token = "{{%s}}" % key
        if token not in out:
            continue
        if key.startswith("image"):
            out = out.replace(token, html.escape(image_src(val), quote=True))
        else:
            text = "" if val is None else str(val)
            cap = max_chars.get(key)
            if cap and len(text) > cap:
                print(f"WARNING: '{key}' is {len(text)} chars (max {cap}); it was cut to end in '…'. "
                      "Rewrite it shorter.", file=sys.stderr)
                text = text[: cap - 1].rstrip() + "…"
            out = out.replace(token, html.escape(text))
    # Strip any unreplaced slot tokens so a missing optional slot doesn't show literal braces.
    out = re.sub(r"\{\{[a-zA-Z0-9_]+\}\}", "", out)
    return out


def render_one(page, template, fmt_spec, data, brand, out_path, formats):
    family, layout = template.split("/")
    layout_dir = TEMPLATES_DIR / family / layout
    manifest = json.loads((layout_dir / "manifest.json").read_text())
    html_src = (layout_dir / "index.html").read_text()
    w, h, safe_zone, fmt_name = resolve_format(fmt_spec, formats, out_path.name)
    if manifest.get("formats") and fmt_name in formats and fmt_name not in manifest["formats"]:
        print(f"WARNING: {template} manifest does not list format '{fmt_name}' (rendering anyway)", file=sys.stderr)
    missing = [k for k in manifest.get("slots", []) if k != "focal" and k not in data]
    if missing:
        print(f"WARNING: {out_path.name}: slots not set {missing}; the template's demo text/picture shows there. "
              "Set each one (\"\" for blank).", file=sys.stderr)

    filled = fill_template(html_src, data, manifest.get("defaults", {}), manifest.get("max_chars", {}), brand)

    # Render from a temp file (the skill folder may be read-only); <base> keeps the template's
    # relative URLs (fonts, textures, placeholders) resolving against its own folder.
    base = f'<base href="{layout_dir.resolve().as_uri()}/">'
    filled = re.sub(r"(<head[^>]*>)", r"\1" + base, filled, count=1, flags=re.I) if re.search(r"<head[^>]*>", filled, re.I) \
        else base + filled
    tmp_path = Path(tempfile.gettempdir()) / f"social_render_{uuid.uuid4().hex}.html"
    tmp_path.write_text(filled)
    try:
        page.set_viewport_size({"width": w, "height": h})
        page.goto(tmp_path.resolve().as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_timeout(60)
        page.evaluate(AUTOFIT_JS)
        page.wait_for_timeout(30)
        if safe_zone:
            bad = page.evaluate(SAFE_ZONE_JS, safe_zone)
            if bad:
                raise RuntimeError(
                    f"SAFE ZONE BREACH in {template} @ {fmt_name}: {json.dumps(bad)}"
                )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        part = out_path.with_name(f".{out_path.stem}.partial{out_path.suffix}")
        page.screenshot(path=str(part))
        part.replace(out_path)  # atomic: never a half-written PNG
    except Exception:
        # A failed re-render must not leave the previous version looking current.
        if out_path.exists():
            out_path.unlink()
            print(f"removed the previous {out_path} (this render failed)", file=sys.stderr)
        raise
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------- agent-written HTML mode
FAMILY_FONTS = {  # used only when brand.json sets no fonts
    "editorial": ("Playfair Display", "Inter"), "bold_type": ("Archivo", "Archivo"),
    "warm_craft": ("Fraunces", "Work Sans"), "clean_modern": ("Inter", "Inter"),
    "playful_pop": ("Fraunces", "Manrope"), "quiet_luxury": ("Fraunces", "Manrope"),
}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "system-ui", "inherit", "initial", "ui-sans-serif"}
MIN_EDGE = 30  # px of air kept between text and the canvas edge on formats with no platform safe zone


def fonts_css():
    """@font-face rules for every bundled family, as absolute file:// URLs (no network, works from any folder)."""
    fonts_dir = SKILL_DIR / "fonts"
    src = (TEMPLATES_DIR / "bold_type" / "offer" / "index.html").read_text()
    rules = []
    for m in re.finditer(r"@font-face\s*\{([^}]*)\}", src):
        body = m.group(1)
        u = re.search(r"url\('\.\./\.\./\.\./fonts/([^']+)'\)", body)
        if not u:
            continue
        uri = (fonts_dir / u.group(1)).resolve().as_uri()
        rules.append("@font-face{" + body.replace(u.group(0), f"url('{uri}')").strip() + ";font-display:block}")
    return "\n".join(rules)


def bundled_family_names():
    return set(re.findall(r"font-family:\s*'([^']+)'", fonts_css()))


def html_brand_css(brand, w, h, safe_zone):
    pal = brand.get("palette", {})
    fam = brand.get("style_family")
    dflt_d, dflt_b = FAMILY_FONTS.get(fam, ("Fraunces", "Inter"))
    fonts = brand.get("fonts") or {}
    q = lambda v: "'%s'" % str(v).strip().strip("'\"")
    z = safe_zone or {"top": MIN_EDGE, "bottom": MIN_EDGE, "left": MIN_EDGE, "right": MIN_EDGE}
    lines = [f"--{k}: {v};" for k, v in pal.items()]
    lines += [f"--font-display: {q(fonts.get('display') or dflt_d)}, serif;",
              f"--font-body: {q(fonts.get('body') or dflt_b)}, sans-serif;",
              f"--brand-name: \"{str(brand.get('name', '')).replace(chr(34), '')}\";",
              f"--w: {w}px; --h: {h}px;",
              f"--safe-top: {z['top']}px; --safe-bottom: {z['bottom']}px; "
              f"--safe-left: {z['left']}px; --safe-right: {z['right']}px;"]
    return ":root{\n" + "\n".join(lines) + "\n}"


HTML_AUTOFIT_JS = r"""
() => {
  const res = [];
  document.querySelectorAll('[data-fit]').forEach(el => {
    const boxEl = el.closest('[data-fit-box]') || el;
    const minR = parseFloat(el.getAttribute('data-fit-min') || '0.4');
    const start = parseFloat(getComputedStyle(el).fontSize);
    let px = start, guard = 0;
    const over = () => el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1 ||
      (boxEl !== el && (el.getBoundingClientRect().height > boxEl.clientHeight + 1 || el.scrollWidth > boxEl.clientWidth + 1));
    while (over() && px > start * minR && guard < 120) {
      px -= Math.max(0.5, px * 0.03); el.style.fontSize = px + 'px'; guard++;
    }
    res.push({ el: (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + (el.className || '').toString().split(' ')[0]),
               text: (el.textContent || '').trim().slice(0, 30), start, final: px, overflow: over() });
  });
  return res;
}
"""

HTML_CHECK_JS = r"""
(cfg) => {
  const W = innerWidth, H = innerHeight, z = cfg.zone, bad = [], small = [], fonts = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    if (!n.textContent.trim()) continue;
    const p = n.parentElement;
    if (!p || p.closest('script,style,[data-safe-ignore]')) continue;
    const cs = getComputedStyle(p);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) continue;
    const bleed = !!p.closest('[data-bleed]');
    fonts.add(cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, ''));
    const fs = parseFloat(cs.fontSize);
    if (fs < cfg.minFont) small.push({ text: n.textContent.trim().slice(0, 30), px: fs });
    const range = document.createRange(); range.selectNodeContents(n);
    for (const r of range.getClientRects()) {
      if (r.width < 1 || r.height < 1) continue;
      const off = r.left < -1 || r.top < -1 || r.right > W + 1 || r.bottom > H + 1;
      const inBand = r.top < z.top || r.bottom > H - z.bottom || r.left < z.left || r.right > W - z.right;
      if ((off && !bleed) || (inBand && !bleed)) {
        bad.push({ text: n.textContent.trim().slice(0, 40), why: off ? 'outside the canvas' : 'inside the keep-clear band',
                   top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) });
        break;
      }
    }
  }
  return { bad, small, fonts: [...fonts], sw: document.documentElement.scrollWidth, sh: document.documentElement.scrollHeight, W, H };
}
"""


def png_size(path):
    import struct
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def render_html_one(page, html_path, fmt_spec, data, brand, out_path, formats, fonts_blob, bundled):
    html_path = Path(html_path).expanduser()
    if not html_path.exists():
        raise RuntimeError(f"html file not found: {html_path}")
    src = html_path.read_text()
    w, h, safe_zone, fmt_name = resolve_format(fmt_spec, formats, out_path.name)
    brand_blob = html_brand_css(brand, w, h, safe_zone)
    for key, val in (data or {}).items():
        tok = "{{%s}}" % key
        if tok in src:
            src = src.replace(tok, html.escape("" if val is None else str(val)))
    inject = ""
    for tok, blob, ident in (("{{fonts_css}}", fonts_blob, "social-fonts"), ("{{brand_css}}", brand_blob, "social-brand")):
        if tok in src:
            src = src.replace(tok, blob)
        else:
            inject += f'<style id="{ident}">\n{blob}\n</style>\n'
    left = sorted(set(re.findall(r"\{\{\s*[A-Za-z0-9_]+\s*\}\}", src)))
    if left:
        raise RuntimeError(f"unfilled tokens in {html_path.name}: {left} (write the real text, or pass them in the entry's data)")
    if re.search(r"<head[^>]*>", src, re.I):
        src = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + "\n" + inject, src, count=1, flags=re.I)
    else:
        src = "<!doctype html><html><head><meta charset='utf-8'>" + inject + "</head><body>" + src + "</body></html>"

    # Render from a hidden sibling of the source so relative <link>/<img> paths resolve as the author expects.
    tmp_path = html_path.with_name(f".render-{uuid.uuid4().hex[:8]}-{html_path.name}")
    try:
        tmp_path.write_text(src)
    except OSError:
        tmp_path = Path(tempfile.gettempdir()) / f"social_render_{uuid.uuid4().hex}.html"
        tmp_path.write_text(src)
    remote = []
    handler = lambda route: (remote.append(route.request.url), route.abort())
    page.route(re.compile(r"^https?://"), handler)
    try:
        page.set_viewport_size({"width": w, "height": h})
        page.goto(tmp_path.resolve().as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        page.wait_for_timeout(80)
        if remote:
            raise RuntimeError(f"{html_path.name} loads from the network ({remote[:3]}); only bundled fonts and local files are allowed")
        fits = page.evaluate(HTML_AUTOFIT_JS)
        page.wait_for_timeout(30)
        for f in fits:
            ratio = f["final"] / f["start"] if f["start"] else 1
            if f["overflow"]:
                raise RuntimeError(f"TEXT OVERFLOW in {html_path.name}: data-fit '{f['text']}' still does not fit its box at "
                                   f"{f['final']:.0f}px ({ratio:.0%} of {f['start']:.0f}px). Shorten the words or enlarge the box.")
            if ratio < 0.6:
                print(f"WARNING: {html_path.name}: '{f['text']}' shrank to {ratio:.0%} of its size; shorten it or give it more room.",
                      file=sys.stderr)
        z = safe_zone or {}
        zone = {"top": z.get("top", MIN_EDGE), "bottom": z.get("bottom", MIN_EDGE),
                "left": z.get("left", MIN_EDGE), "right": z.get("right", MIN_EDGE)}
        chk = page.evaluate(HTML_CHECK_JS, {"zone": zone, "minFont": 22})
        if chk["bad"]:
            where = f"the {fmt_name} safe zone {zone}" if safe_zone else f"the {MIN_EDGE}px edge margin"
            raise RuntimeError(f"SAFE ZONE BREACH in {html_path.name} @ {fmt_name}: text outside {where}: "
                               + json.dumps(chk["bad"][:4]) + ". Move it in, shorten it, or mark deliberate cropped "
                               "display type with data-bleed.")
        if chk["small"]:
            print(f"WARNING: {html_path.name}: text under 22px will not read on a phone: "
                  + ", ".join(f"'{s['text']}' {s['px']:.0f}px" for s in chk["small"][:3]), file=sys.stderr)
        odd = [f for f in chk["fonts"] if f not in bundled and f.lower() not in GENERIC_FONTS]
        if odd:
            print(f"WARNING: {html_path.name}: font(s) {odd} are not bundled; they fall back to a system font. "
                  f"Use: {sorted(bundled)}", file=sys.stderr)
        if chk["sw"] > w + 1 or chk["sh"] > h + 1:
            print(f"WARNING: {html_path.name}: content is {chk['sw']}x{chk['sh']}, bigger than the {w}x{h} canvas "
                  "(set html,body{overflow:hidden} and size the canvas to var(--w) x var(--h)).", file=sys.stderr)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        part = out_path.with_name(f".{out_path.stem}.partial{out_path.suffix}")
        page.screenshot(path=str(part), clip={"x": 0, "y": 0, "width": w, "height": h})
        got = png_size(part)
        if got != (w, h):
            part.unlink(missing_ok=True)
            raise RuntimeError(f"output is {got[0]}x{got[1]}, not {w}x{h}")
        part.replace(out_path)
        shrunk = [f"{f['text']!r} {f['start']:.0f}->{f['final']:.0f}px" for f in fits if f["final"] < f["start"] - 0.5]
        if shrunk:
            print("  data-fit:", "; ".join(shrunk[:4]), file=sys.stderr)
    except Exception:
        if out_path.exists():
            out_path.unlink()
            print(f"removed the previous {out_path} (this render failed)", file=sys.stderr)
        raise
    finally:
        page.unroute(re.compile(r"^https?://"), handler)
        tmp_path.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="render this agent-written HTML file (the pipeline's mode)")
    ap.add_argument("--template", help="LEGACY: a reference-library template (gallery builder only)")
    ap.add_argument("--format")
    ap.add_argument("--data")
    ap.add_argument("--brand")
    ap.add_argument("--out")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--batch")
    args = ap.parse_args()

    if args.list:
        print(json.dumps(catalog(), indent=2))
        return 0

    resolved = bootstrap.ensure_venv()
    bootstrap.ensure_packages(resolved)
    chromium, _kind = bootstrap.ensure_chromium(resolved)
    if not chromium:
        print("ERROR: no Chromium available after setup.py bootstrap", file=sys.stderr)
        return 2

    # We're invoked with system python but deps live in the venv; re-exec into the venv
    # python the first time so `import playwright` works regardless of caller's interpreter.
    venv_py = str(bootstrap.venv_python())
    if sys.executable != venv_py and Path(venv_py).exists():
        os_exec_args = [venv_py, __file__] + sys.argv[1:]
        import os
        os.execv(venv_py, os_exec_args)

    from playwright.sync_api import sync_playwright

    formats = load_formats()

    jobs = []
    if args.batch:
        plan = load_json_arg(args.batch)
        for entry in plan:
            jobs.append({
                "html": entry.get("html"),
                "template": entry.get("template"),
                "format": entry["format"],
                "data": load_json_arg(entry.get("data")),
                "brand": merge_brand(load_json_arg(entry.get("brand"))),
                "out": Path(entry["out"]),
            })
    else:
        if not ((args.html or args.template) and args.format and args.out):
            ap.error("--html (or legacy --template), --format and --out are required (or use --list / --batch)")
        jobs.append({
            "html": args.html,
            "template": args.template,
            "format": args.format,
            "data": load_json_arg(args.data),
            "brand": merge_brand(load_json_arg(args.brand)),
            "out": Path(args.out),
        })

    t0 = time.time()
    ok, failed = 0, []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium, headless=True)
        page = browser.new_page()
        fonts_blob, bundled = fonts_css(), bundled_family_names()
        for j in jobs:
            name = str(j["html"] or j["template"])
            try:
                if j["html"]:
                    render_html_one(page, j["html"], j["format"], j["data"], j["brand"], j["out"], formats, fonts_blob, bundled)
                else:
                    render_one(page, j["template"], j["format"], j["data"], j["brand"], j["out"], formats)
                ok += 1
                print(f"OK  {Path(name).name:<28} {j['format']:<14} -> {j['out']}", flush=True)
            except Exception as e:
                failed.append((name, j["format"], str(e)))
                print(f"FAIL {Path(name).name:<28} {j['format']:<14} {e}", file=sys.stderr)
        browser.close()
    dt = time.time() - t0
    print(f"\n{ok}/{len(jobs)} rendered in {dt:.1f}s ({dt / max(len(jobs),1)*1000:.0f}ms/image avg)", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
