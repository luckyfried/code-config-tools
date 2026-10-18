#!/usr/bin/env python3
"""Build out/index.html: the one page the user opens. Posts grouped with their files, each caption
with a copy button, the posting plan, what was assumed, image credits and the QA status.

USAGE (from the workspace root):
  python3 S/scripts/deliver.py [--out out] [--title "Taqueria El Sol: Taco Tuesday"]

Runs the QA gate first. If the gate fails, the page is still written (so nothing is lost) but carries a
red "not finished" banner listing the failures, and the script exits 1. Fix and re-run until it exits 0.
Self-contained HTML: relative links to the files beside it, no external fonts or scripts.
"""
import argparse
import contextlib
import html
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402

E = html.escape
FALLBACK_ACCENT = "#C2410C"  # rust; never purple


def md_inline(s):
    s = E(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"https?://[^\s<]+", _link, s)
    return s


def _link(m):
    """Linkify a URL, keeping balanced parentheses (Commons file names have them) but not a trailing ')' or '.'."""
    u, tail = m.group(0), ""
    while u and (u[-1] in ".,;:" or (u[-1] == ")" and u.count("(") < u.count(")"))):
        tail = u[-1] + tail
        u = u[:-1]
    return f'<a href="{u}">{u}</a>{tail}'


def md_block(text):
    """Tiny markdown: bullets, tables, paragraphs, ### headings. Enough for brief/credits sections."""
    out, para, lines = [], [], text.strip().splitlines()
    i = 0

    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.strip().startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                h = "".join(f"<th>{md_inline(c)}</th>" for c in rows[0])
                b = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
                out.append(f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>')
            continue
        m = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)", ln)
        if m:
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*(?:[-*]|\d+\.)\s+", lines[i]):
                items.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in items) + "</ul>")
            continue
        m = re.match(r"^#{3,4}\s+(.*)", ln)
        if m:
            flush()
            out.append(f"<h4>{md_inline(m.group(1))}</h4>")
        elif not ln.strip():
            flush()
        elif not ln.startswith("#"):
            para.append(ln.strip())
        i += 1
    flush()
    return "\n".join(out)


def gate_result(out):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = qa.cmd_gate(argparse.Namespace(out=str(out), qa="build/qa"))
        except SystemExit as e:
            code = e.code or 1
    lines = [l.strip()[2:] for l in buf.getvalue().splitlines() if l.strip().startswith("- ")]
    return code, lines


def accent_from_brand(out):
    try:
        b = json.loads((out / "brand.json").read_text())
        acc = (b.get("palette") or {}).get("accent")
        name = b.get("name")
        if acc and re.fullmatch(r"#[0-9a-fA-F]{6}", acc) and not qa.is_purple(acc):
            # too light to use as link/button colour on white? fall back
            if qa.contrast(acc, "#FFFFFF") >= 3:
                return acc, name
        return FALLBACK_ACCENT, name
    except Exception:
        return FALLBACK_ACCENT, None


def plan_by_post(copy_text):
    """Posting-plan rows grouped by post number: {1: ["Tuesday 2026-10-20 10:30 · Instagram feed", ...]}."""
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in qa.section(copy_text, "Posting plan").splitlines()
            if l.strip().startswith("|")]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r if c)]
    if len(rows) < 2:
        return {}
    head = [h.lower() for h in rows[0]]
    col = {k: head.index(k) for k in ("#", "date", "day", "time", "platform") if k in head}
    out = {}
    for r in rows[1:]:
        try:
            n = int(re.sub(r"\D", "", r[col["#"]]) or 0)
        except (KeyError, IndexError):
            continue
        parts = [r[col[k]] for k in ("day", "date", "time") if k in col and col[k] < len(r)]
        plat = r[col["platform"]] if "platform" in col and col["platform"] < len(r) else ""
        out.setdefault(n, []).append(" ".join(p for p in parts if p) + (f" · {plat}" if plat else ""))
    return out


def plan_table(copy_text):
    sec = qa.section(copy_text, "Posting plan")
    return md_block(sec) if sec else ""


def file_card(p, alt, verdict):
    name = p.name
    size = p.stat().st_size
    kb = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size // 1024} KB"
    dims = re.search(r"(\d{3,4})x(\d{3,4})", name)
    dim = f"{dims.group(1)}x{dims.group(2)}" if dims else ""
    if p.suffix.lower() in qa.VID_EXT:
        media = f'<video src="{E(name)}" controls autoplay muted playsinline loop preload="auto"></video>'
    else:
        media = f'<a href="{E(name)}" target="_blank"><img src="{E(name)}" alt="{E(alt or "")}" loading="lazy"></a>'
    tag = ""
    if verdict:
        tag = f'<span class="v {"ok" if verdict == "PASS" else "bad"}">{"checked" if verdict == "PASS" else "needs fix"}</span>'
    alt_html = f'<p class="alt"><b>Alt text</b> {E(alt)} <button class="cp sm" data-t="{E(alt)}">Copy</button></p>' if alt else ""
    return (f'<figure class="f">{media}<figcaption><a class="dl" href="{E(name)}" download>{E(name)}</a>'
            f'<span class="meta">{dim} · {kb}</span>{tag}{alt_html}</figcaption></figure>')


def caption_block(platform, text):
    n = len(text)
    first = text.strip().splitlines()[0] if text.strip() else ""
    return (f'<div class="cap"><div class="caph"><b>{E(platform)}</b><span class="meta">{n} characters</span>'
            f'<button class="cp" data-t="{E(text)}">Copy caption</button></div>'
            f'<pre>{E(text)}</pre></div>') if text else ""


CSS = """
:root{--a:%(accent)s;--ink:#1d1b18;--mute:#6b665e;--line:#e6e1d8;--bg:#faf8f4;--card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 80px}
header h1{font-size:30px;line-height:1.15;margin:0 0 6px}header p{color:var(--mute);margin:0}
.bar{height:6px;background:var(--a);border-radius:3px;width:72px;margin:0 0 18px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 8px}nav a{font-size:14px;color:var(--ink);text-decoration:none;border:1px solid var(--line);background:#fff;padding:5px 12px;border-radius:999px}
nav a:hover{border-color:var(--a)}
section{margin-top:36px}h2{font-size:21px;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:18px;margin:0 0 4px}h4{margin:14px 0 4px;font-size:15px}
.post{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0}
.post .when{color:var(--mute);font-size:14px;margin-bottom:12px}
.files{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;align-items:start}
.f{margin:0}.f img,.f video{width:100%%;display:block;border-radius:8px;border:1px solid var(--line);background:#eee}
figcaption{font-size:13px;margin-top:6px;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}
.dl{color:var(--ink);font-weight:600;word-break:break-all}.meta{color:var(--mute);font-size:13px}
.v{font-size:12px;padding:1px 8px;border-radius:999px}.v.ok{background:#e3f1e6;color:#1f6b35}.v.bad{background:#fde2dd;color:#a3260f}
.alt{flex-basis:100%%;margin:4px 0 0;color:var(--mute)}.alt b{color:var(--ink);font-weight:600;margin-right:4px}
.caps{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin-top:16px}
.cap{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#fdfcfa}
.caph{display:flex;gap:10px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--line);background:#f6f3ee}
.caph .cp{margin-left:auto}
pre{white-space:pre-wrap;word-wrap:break-word;font-size:15px;line-height:1.5;font-family:inherit;margin:0;padding:12px}
.cp{font-weight:600;font-size:13px;line-height:1;font-family:inherit;border:0;background:var(--a);color:#fff;padding:8px 12px;border-radius:7px;cursor:pointer}
.cp.sm{padding:4px 8px;font-size:12px;background:#fff;color:var(--ink);border:1px solid var(--line)}
.cp.done{background:#1f6b35;color:#fff}
.extra{margin-top:12px;font-size:14px}.extra b{margin-right:6px}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%%;font-size:14px;background:#fff}th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:#f6f3ee}
.warn{background:#fdecea;border:2px solid #b42318;color:#7a1a10;border-radius:12px;padding:16px 20px;margin:20px 0}
.warn h2{border:0;color:#b42318;margin:0 0 6px;padding:0}
.ok-note{color:#1f6b35;font-size:14px}
code{background:#f1ede6;padding:1px 5px;border-radius:4px;font-size:90%%}
a{color:var(--a)}
"""

JS = """
function cp(t,b){const done=()=>{const o=b.textContent;b.textContent='Copied';b.classList.add('done');setTimeout(()=>{b.textContent=o;b.classList.remove('done')},1400)};
 if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(t).then(done,()=>fb(t,done))}else{fb(t,done)}}
function fb(t,done){const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();
 try{document.execCommand('copy');done()}catch(e){prompt('Copy this:',t)}document.body.removeChild(a)}
document.addEventListener('click',e=>{const b=e.target.closest('.cp');if(b)cp(b.dataset.t,b)});
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="out")
    ap.add_argument("--title")
    a = ap.parse_args()
    out = Path(a.out)
    if not out.exists():
        sys.exit("no out/ directory")
    copy_text = (out / "copy.md").read_text() if (out / "copy.md").exists() else ""
    brief = (out / "brief.md").read_text() if (out / "brief.md").exists() else ""
    posts = qa.parse_copy(copy_text) if copy_text else []
    accent, bname = accent_from_brand(out)
    code, fails = gate_result(out)
    q = qa.load_qa(out)
    rounds = q.get("rounds", 0)

    def verdict_for(p):
        e = q.get("files", {}).get(p.name)
        if not e:
            return None
        e = dict(e)
        if e.get("sha") != qa.sha(p):
            return None
        v = qa.current_verdict(e, rounds)
        return v["verdict"] if v else None

    title_m = re.match(r"^#\s+(?:Copy:\s*)?(.+)$", copy_text, re.M)
    title = a.title or (title_m.group(1).strip() if title_m else (bname or "Your social posts"))
    files = qa.media(out)
    by_name = {p.name: p for p in files}
    used = set()
    nav, body = [], []

    if code != 0:
        body.append('<div class="warn"><h2>Not finished yet</h2><p>These checks did not pass:</p><ul>'
                    + "".join(f"<li>{E(f)}</li>" for f in fails[:40]) + "</ul></div>")

    plan = plan_table(copy_text)
    if plan:
        nav.append('<a href="#plan">Posting plan</a>')
        body.append(f'<section id="plan"><h2>Posting plan</h2>{plan}</section>')

    when = plan_by_post(copy_text)
    body.append('<section id="posts"><h2>Posts</h2>')
    for post in posts:
        pid = f"post{post['n']}"
        nav.append(f'<a href="#{pid}">Post {post["n"]}</a>')
        cards = []
        for fn in post["files"]:
            p = by_name.get(fn)
            if not p:
                cards.append(f'<figure class="f"><figcaption><b>{E(fn)}</b> missing</figcaption></figure>')
                continue
            used.add(fn)
            cards.append(file_card(p, post["alts"].get(fn), verdict_for(p)))
        caps = "".join(caption_block(k, v) for k, v in post["captions"].items())
        extra = "".join(f'<div class="extra"><b>{E(k)}:</b>{md_inline(v)}</div>' for k, v in post["extra"].items())
        w = "".join(f"<div>{E(x)}</div>" for x in when.get(post["n"], []))
        body.append(f'<article class="post" id="{pid}"><h3>Post {post["n"]}: {E(post["title"])}</h3>'
                    + (f'<div class="when">{w}</div>' if w else "") +
                    f'<div class="files">{"".join(cards)}</div><div class="caps">{caps}</div>{extra}</article>')
    loose = [p for p in files if p.name not in used]
    if loose:
        body.append('<article class="post"><h3>Other files</h3><div class="files">'
                    + "".join(file_card(p, None, verdict_for(p)) for p in loose) + "</div></article>")
    body.append("</section>")

    pick = qa.section(brief, "Pick")
    idea = qa.section(brief, "Idea")
    if pick or idea:
        nav.append('<a href="#idea">The idea</a>')
        body.append(f'<section id="idea"><h2>The idea</h2>{md_block(idea) if idea else ""}{md_block(pick)}</section>')
    assum = qa.section(brief, "Assumptions")
    if assum:
        nav.append('<a href="#assumptions">What I assumed</a>')
        body.append(f'<section id="assumptions"><h2>What I assumed (change any of these)</h2>{md_block(assum)}</section>')
    cred = (out / "credits.md").read_text() if (out / "credits.md").exists() else ""
    if cred.strip():
        nav.append('<a href="#credits">Image credits</a>')
        body.append(f'<section id="credits"><h2>Image credits</h2>{md_block(re.sub(r"^# .*$", "", cred, flags=re.M))}</section>')
    nav.append('<a href="#qa">Checks</a>')
    status = (f'<p class="ok-note">Every file was opened and checked ({rounds} review round{"s" if rounds != 1 else ""}).</p>'
              if code == 0 else f"<p>{len(fails)} open item(s); see the banner at the top.</p>")
    extras = [n for n in ("brief.md", "copy.md", "brand.json", "credits.md") if (out / n).exists()]
    status += "<p>Source files: " + ", ".join(f'<a href="{n}">{n}</a>' for n in extras) + "</p>"
    body.append(f'<section id="qa"><h2>Checks</h2>{status}</section>')

    sub = f"{len(posts)} post{'s' if len(posts) != 1 else ''} · {len(files)} file{'s' if len(files) != 1 else ''}"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><style>{CSS % {"accent": accent}}</style></head><body><div class="wrap">
<header><div class="bar"></div><h1>{E(title)}</h1><p>{sub}. Tap a picture to open it full size; use Copy to grab a caption.</p></header>
<nav>{''.join(nav)}</nav>
{''.join(body)}
</div><script>{JS}</script></body></html>"""
    (out / "index.html").write_text(page)
    print(f"wrote {(out / 'index.html').resolve()}")
    if code != 0:
        print(f"GATE FAILED ({len(fails)} item(s)); the page shows a 'Not finished' banner. Fix, then re-run:")
        for f in fails:
            print("  -", f)
        return 1
    print("gate passed; deliverable ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
