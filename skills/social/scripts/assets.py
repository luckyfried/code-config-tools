#!/usr/bin/env python3
"""Free, keyless image search + download: Openverse and Wikimedia Commons, licence recorded.

USAGE (from the workspace root):
  python3 S/scripts/assets.py search "street tacos plate" [--orientation portrait|landscape|square|any]
                                     [--n 12] [--min-short 640] [--source all|openverse|commons] [--cc0-only]
      -> numbered contact sheet build/assets/<slug>-sheet.jpg (READ IT before choosing) + build/assets/<slug>.json
  python3 S/scripts/assets.py get <slug>:<number> [--out build/assets]
      -> downloads the full image, appends licence + attribution to out/credits.md, prints the credit line
  python3 S/scripts/assets.py credits      # print out/credits.md

Only licences that allow commercial use and modification are returned: CC0, Public Domain Mark,
CC BY, CC BY-SA. (No NC, no ND.) CC BY / BY-SA need the credit line in the caption.
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

UA = "SocialToolkit/3.0 (open-source social media skill; keyless Openverse/Commons search)"
ASSETS = Path("build/assets")


def fetch(url, timeout=25, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        return data if binary else json.loads(data.decode("utf-8", "replace"))


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "q"


def norm_license(code, version=""):
    c = (code or "").lower().replace("_", "-").strip()
    if c in ("cc0", "cc-zero") or "cc0" in c:
        return "CC0", False
    if c in ("pdm", "pd") or "public domain" in c or c.startswith("pd-") or c == "pd":
        return "Public Domain", False
    if "nc" in c.split("-") or "-nc" in c or " nc" in c or "nd" in c.split("-") or "-nd" in c:
        return None, None
    if c.startswith("cc-by-sa") or c.startswith("by-sa") or "by-sa" in c:
        return f"CC BY-SA {version}".strip(), True
    if c.startswith("cc-by") or c.startswith("by") or c == "cc by":
        return f"CC BY {version}".strip(), True
    return None, None


def search_openverse(q, n):
    url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
        "q": q, "license": "cc0,pdm,by,by-sa", "page_size": min(20, max(n * 2, 10)), "mature": "false"})
    out = []
    for r in fetch(url).get("results", []):
        lic, need_credit = norm_license(r.get("license"), r.get("license_version") or "")
        if not lic:
            continue
        out.append({
            "source": "Openverse/" + (r.get("source") or r.get("provider") or "?"),
            "title": r.get("title") or "Untitled",
            "creator": r.get("creator") or "Unknown",
            "license": lic, "credit_required": need_credit,
            "license_url": r.get("license_url") or "",
            "page": r.get("foreign_landing_url") or "",
            "url": r.get("url"),
            "thumb": r.get("thumbnail") or r.get("url"),
            "w": r.get("width") or 0, "h": r.get("height") or 0,
        })
    return out


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search_commons(q, n):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": f"{q} filetype:bitmap", "gsrlimit": min(40, max(n * 3, 15)),
        "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1920})
    data = fetch(url)
    out = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        if not str(ii.get("mime", "")).startswith("image/") or ii.get("mime") in ("image/svg+xml", "image/gif"):
            continue
        md = ii.get("extmetadata", {})
        short = (md.get("LicenseShortName", {}) or {}).get("value", "")
        ver = ""
        m = re.search(r"(\d\.\d)", short)
        if m:
            ver = m.group(1)
        code = short.lower().replace(" ", "-")
        lic, need_credit = norm_license(code, ver)
        if not lic:
            continue
        full = ii.get("thumburl") or ii.get("url")
        thumb = re.sub(r"/\d+px-", "/500px-", ii["thumburl"]) if ii.get("thumburl") and "/thumb/" in ii["thumburl"] else full
        title = strip_html((md.get("ObjectName", {}) or {}).get("value")) or page.get("title", "").replace("File:", "")
        out.append({
            "source": "Wikimedia Commons",
            "title": title[:120],
            "creator": strip_html((md.get("Artist", {}) or {}).get("value"))[:120] or "Unknown",
            "license": lic, "credit_required": need_credit,
            "license_url": (md.get("LicenseUrl", {}) or {}).get("value", ""),
            "page": ii.get("descriptionurl") or "",
            "url": full, "thumb": thumb,
            "w": ii.get("width") or 0, "h": ii.get("height") or 0,
        })
    return out


def orient_ok(c, o):
    w, h = c["w"] or 1, c["h"] or 1
    r = h / w
    return {"portrait": r > 1.05, "landscape": r < 0.95, "square": 0.85 <= r <= 1.18}.get(o, True)


def cmd_search(a):
    _env.need("PIL")
    from PIL import Image, ImageDraw
    import io
    q = a.query
    from concurrent.futures import ThreadPoolExecutor
    cands, errors = [], []
    jobs = {k: f for k, f in (("openverse", search_openverse), ("commons", search_commons)) if a.source in ("all", k)}
    with ThreadPoolExecutor(2) as ex:
        futs = {k: ex.submit(f, q, a.n) for k, f in jobs.items()}
        for k, fu in futs.items():
            try:
                cands += fu.result()
            except Exception as e:
                errors.append(f"{k}: {e}")
    for e in errors:
        print("note:", e, file=sys.stderr)
    if a.source == "all":  # Commons metadata is richer than Openverse's copy of it
        cands = [c for c in cands if c["source"].lower() != "openverse/wikimedia"]
    cands = [c for c in cands if min(c["w"], c["h"]) >= a.min_short or not (c["w"] and c["h"])]
    if a.orientation != "any":
        cands = [c for c in cands if orient_ok(c, a.orientation)]
    if a.cc0_only:
        cands = [c for c in cands if not c["credit_required"]]
    cands.sort(key=lambda c: (c["credit_required"], -(min(c["w"], c["h"]) or 0)))
    # the same photo often comes back twice (Commons + its Flickr original): keep the first (largest/freest)
    seen_titles, uniq = set(), []
    for c in cands:
        t = re.sub(r"\s*\(\d{6,}\)\s*$", "", c["title"].lower())  # Commons appends the Flickr id
        t = re.sub(r"\.(jpe?g|png|webp|tiff?)$", "", t)
        t = re.sub(r"[^a-z0-9]+", " ", t).strip()[:60]
        if t and t != "untitled" and len(t) > 6 and t in seen_titles:
            continue
        seen_titles.add(t)
        uniq.append(c)
    cands = uniq
    # interleave sources so one provider doesn't crowd out the other
    by = {}
    for c in cands:
        by.setdefault(c["source"].split("/")[0], []).append(c)
    mixed = []
    while any(by.values()) and len(mixed) < a.n:
        for k in list(by):
            if by[k] and len(mixed) < a.n:
                mixed.append(by[k].pop(0))
    if not mixed:
        print(f"No usable CC images for '{q}'. Try simpler words (e.g. 'tacos' not 'authentic street tacos'),"
              " --orientation any, or go type-only.")
        return 1
    slug = slugify(q)
    ASSETS.mkdir(parents=True, exist_ok=True)
    def load(c):
        err = None
        for u in dict.fromkeys([c["thumb"], c["url"]]):
            try:
                im = Image.open(io.BytesIO(fetch(u, timeout=20, binary=True))).convert("RGB")
                im.thumbnail((600, 600))
                return im
            except Exception as e:
                err = str(e)
        c["thumb_error"] = err
        return None
    for i, c in enumerate(mixed, 1):
        c["n"] = i
    with ThreadPoolExecutor(8) as ex:
        thumbs = list(zip(mixed, ex.map(load, mixed)))
    (ASSETS / f"{slug}.json").write_text(json.dumps({"query": q, "results": mixed}, indent=2))
    # contact sheet: 4 columns, 300px cells
    cw, ch, pad, lab = 300, 300, 14, 54
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + lab + pad) + pad), (238, 235, 230))
    d = ImageDraw.Draw(sheet)
    fb, ft = _env.pil_font(30, "bold"), _env.pil_font(14, "text")
    for k, (c, im) in enumerate(thumbs):
        x = pad + (k % cols) * (cw + pad)
        y = pad + (k // cols) * (ch + lab + pad)
        if im:
            im.thumbnail((cw, ch))
            sheet.paste(im, (x + (cw - im.width) // 2, y + (ch - im.height) // 2))
        else:
            d.rectangle([x, y, x + cw, y + ch], outline=(150, 150, 150))
            d.text((x + 10, y + ch // 2), "thumbnail failed", fill=(120, 120, 120), font=ft)
        d.rectangle([x, y, x + 52, y + 42], fill=(20, 20, 20))
        d.text((x + 8, y + 4), str(c["n"]), fill=(255, 255, 255), font=fb)
        small = min(c["w"], c["h"]) < 1080 if (c["w"] and c["h"]) else False
        d.text((x, y + ch + 4), f"{c['w']}x{c['h']}  {c['license']}" + ("  SMALL" if small else ""),
               fill=(160, 40, 20) if small else (30, 30, 30), font=ft)
        d.text((x, y + ch + 22), c["source"][:40], fill=(90, 90, 90), font=ft)
    sp = ASSETS / f"{slug}-sheet.jpg"
    sheet.save(sp, quality=88)
    for c in mixed:
        print(f"{slug}:{c['n']:<3} {c['w']}x{c['h']:<6} {c['license']:<14} {c['source']:<28} {c['title'][:50]}")
    print(f"\nSheet: {sp}\nREAD THE SHEET before choosing. Reject blurry, watermarked, cluttered, dated or wrong-subject images."
          f"\nThen: python3 <S>/scripts/assets.py get {slug}:<number>")
    return 0


def credits_line(c):
    return (f"\"{c['title']}\" by {c['creator']}, {c['license']}"
            + (f" ({c['license_url']})" if c.get("license_url") else "")
            + f", via {c['source']}" + (f": {c['page']}" if c.get("page") else ""))


def cmd_get(a):
    try:
        slug, num = a.ref.rsplit(":", 1)
        num = int(num)
    except ValueError:
        sys.exit("Use <slug>:<number>, as printed by search (e.g. street-tacos-plate:3)")
    meta = ASSETS / f"{slug}.json"
    if not meta.exists():
        sys.exit(f"No search results saved for '{slug}'. Run search first.")
    c = next((r for r in json.loads(meta.read_text())["results"] if r["n"] == num), None)
    if not c:
        sys.exit(f"No result {num} for {slug}")
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    ext = Path(urllib.parse.urlparse(c["url"]).path).suffix.lower()
    ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"
    dest = outdir / f"{slug}-{num}{ext}"
    data = None
    for u in (c["url"], c["thumb"]):
        try:
            data = fetch(u, timeout=60, binary=True)
            if len(data) > 5000:
                break
        except Exception as e:
            print(f"note: download failed from {u[:80]}: {e}", file=sys.stderr)
    if not data:
        sys.exit("Download failed from every URL. Pick another number.")
    dest.write_bytes(data)
    line = credits_line(c)
    cred = Path("out/credits.md")
    cred.parent.mkdir(exist_ok=True)
    if not cred.exists():
        cred.write_text("# Image credits\n\nFree-licence images used in this set. CC BY / BY-SA images need the credit in the caption.\n\n")
    # one line per downloaded file name (a re-search can reuse a name for a different picture)
    keep = [l for l in cred.read_text().splitlines() if not l.startswith(f"- `{dest.name}`:")]
    keep.append(f"- `{dest.name}`: {line}" + ("  **(credit required in caption)**" if c["credit_required"] else ""))
    cred.write_text("\n".join(keep) + "\n")
    print(f"saved {dest}  ({len(data)//1024} KB)")
    print(f"licence: {c['license']}{'  -> put this credit in the caption: Photo: ' + c['creator'] + ' / ' + c['license'] if c['credit_required'] else '  (no credit required; credited in out/credits.md anyway)'}")
    print(f"absolute path for render data: {dest.resolve()}")
    return 0


def cmd_credits(a):
    p = Path("out/credits.md")
    print(p.read_text() if p.exists() else "no out/credits.md yet")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--n", type=int, default=12)
    s.add_argument("--orientation", default="any", choices=["any", "portrait", "landscape", "square"])
    s.add_argument("--min-short", type=int, default=640,
                   help="minimum short side in px (Openverse/Flickr files top out at 1024 px wide)")
    s.add_argument("--source", default="all", choices=["all", "openverse", "commons"])
    s.add_argument("--cc0-only", action="store_true")
    g = sub.add_parser("get")
    g.add_argument("ref")
    g.add_argument("--out", default=str(ASSETS))
    sub.add_parser("credits")
    a = ap.parse_args()
    sys.exit({"search": cmd_search, "get": cmd_get, "credits": cmd_credits}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
