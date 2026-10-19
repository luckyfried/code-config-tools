#!/usr/bin/env python3
"""Movement 6, last step: write out/captions.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

captions.md has one section per piece: the film, story 1, story 2, story 3, the countdown and the feed post. It is
build/captions.md when the agent wrote one in the person's voice (same six sections), otherwise drafted from
build/taste.json in their register (their case, their best hook style, their own hashtags); every section names the
product. brief.md opens with the launch as given (the product, the date, where the assets came from), then their
hooks ranked by response (comments and saves), what their best-answered posts share, where the product's colors meet
theirs, every door tried, what the run assumed, the vote, every clip and how it arrived, the music, the engine and the
critics' scores of the cut. review.html plays the film and shows the three stories, the countdown card, the feed
post, the captions, the three storyboards' style sheets and the vote, with the runners-up.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong.
"""
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")
HERE = Path(__file__).resolve().parent
SECTIONS = ("film", "story 1", "story 2", "story 3", "countdown", "feed post")
STILLS = (("story-1.png", "story 1"), ("story-2.png", "story 2"), ("story-3.png", "story 3"),
          ("countdown.png", "countdown"), ("feed.png", "feed post"))


def esc(s):
    return html.escape("" if s is None else str(s))


def launch_of(lib, taste):
    return {**(taste.get("launch") or {}), **(lib.get("launch") or {})}


def drafts(taste, launch):
    """The six captions in their register, each naming the product."""
    product = launch.get("product") or "it"
    label = launch.get("date_label") or "soon"
    days = launch.get("days_to_go")
    style = (taste.get("best_hook") or {}).get("style")
    opener = {"question": f"what would you do first with {product}?",
              "confession": f"confession: {product} has been my secret for a while",
              "list": f"three things about {product}: it's new, it's mine, it's out {label}"}.get(style, f"{product} is almost here")
    reg = taste.get("register") or {}
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:2] + ["#" + re.sub(r"\W", "", product.lower()), "#launchday"]))
    count = f"{days} days until {product}" if isinstance(days, int) and days > 0 else f"{product} is out now"
    c = {
        "film": f"{opener}\n{product}, out {label}.\n\n{' '.join(tags)}",
        "story 1": f"something's coming. {product}, {label}.",
        "story 2": f"closer. {product} is nearly ready.",
        "story 3": f"meet {product}. out {label}.",
        "countdown": f"{count}. {label}, set a reminder.",
        "feed post": f"{product} is out {label}.\n{opener}\n\n{' '.join(tags)}",
    }
    if reg.get("lowercase"):
        c = {k: v.lower() for k, v in c.items()}
    else:
        c = {k: v[:1].upper() + v[1:] for k, v in c.items()}
    return c


def captions(taste, launch):
    own = Path("build/captions.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    c = drafts(taste, launch)
    return "\n".join(f"## {k}\n\n{c[k]}\n" for k in SECTIONS)


def sections(text):
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip().lower()
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    said = {"generated": "made by the video model", "their_footage": "cut from the footage you supplied",
            "substituted": "no generated clip arrived; an animated treatment of a still stands in"}
    for cid, c in sorted(clips.items()):
        how = said.get(c.get("status"), c.get("status"))
        if c.get("status") == "substituted" and c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def count(v):
    return len(v) if isinstance(v, list) else (v or 0)


def hook_rows():
    r = _env.read_json("build/research.json") or {}
    rows = ["| # | posted | comments | saves | response | opener | style |", "|---|---|---|---|---|---|---|"]
    for h in r.get("hooks") or []:
        rows.append(f"| {h['rank']} | {h.get('date')} ({h.get('kind')}) | {h.get('comments', '-')} | {h.get('saves', '-')} | "
                    f"{h.get('response')} | {str(h.get('hook') or '').replace('|', '/')} | {h.get('style')} |")
    return rows


def brief(lib, taste, win, clips, music, engine, cuts):
    launch = launch_of(lib, taste)
    research = _env.read_json("build/research.json") or {}
    product, label = launch.get("product"), launch.get("date_label") or launch.get("date") or "no date given"
    L = [f"# {product}, launching {label}: how this was made", "", "## the launch, as you gave it", "",
         f"- Product: {product}.", f"- Date: {label}" + (f" ({launch['date']}, {launch['days_to_go']} days from the latest post)" if launch.get("date") and launch.get("days_to_go") is not None else "") + ".",
         f"- Assets: {launch.get('assets') or 'none given; the product beats use your own feed'}"
         + (f" ({count(launch.get('stills'))} stills, {count(launch.get('footage'))} clip{'' if count(launch.get('footage')) == 1 else 's'})" if launch.get("assets") else "") + "."]
    said = taste.get("said") or {}
    for k in ("product", "audience"):
        if said.get(k):
            L.append(f"- In your words, the {k}: {said[k]}")
    about = launch.get("posts_about_it") or []
    if about:
        L.append(f"- Already in your feed: {len(about)} posts about {product}.")
    L += ["", "## your hooks, ranked by response", "", "Response is comments plus saves per post.", ""] + hook_rows()
    best = taste.get("best_hook") or {}
    if best.get("hook"):
        L += ["", f"Your best opener: \"{best['hook']}\" ({best.get('style')}, response {best.get('response')}). The hype cut "
              "storyboard opens on it, and the drafted captions open in its style."]
    shared = research.get("response_shared") or []
    if shared:
        L += ["", "## what your best-answered posts share", ""] + [f"- {x}" for x in shared]
    meet = (research.get("palette") or {}).get("meet") or []
    if meet:
        L += ["", "## where the product's colors meet yours", "", "| product | yours | between | reads |", "|---|---|---|---|"]
        L += [f"| {m['product_name']} {m['product']} | {m['theirs_name']} {m['theirs']} | {m['between']} | {m['reads']} |" for m in meet]
    L += ["", "## where your material came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the storyboards and the vote", ""]
    tot = win.get("totals") or {}
    for i in win.get("order") or []:
        sb = _env.read_json(f"build/storyboards/{i}/storyboard.json") or {}
        mark = "won" if i == win.get("board") else "runner-up"
        L.append(f"- {i}, {sb.get('name')} ({mark}, {tot.get(i)} of {len(vote.PANEL) * len(vote.CRITERIA) * 5}): {sb.get('idea')}")
    if win.get("tie_broken_by_person"):
        L.append("- The top two tied; the critic speaking for you broke the tie.")
    L += ["", "Say \"do the second one\" to have the runner-up made instead.", "", "## the clips", ""]
    L += clip_rows(clips) if clips else ["The winning storyboard uses no clips."]
    subs = [c for c in clips.values() if c.get("status") == "substituted"]
    if subs:
        L += ["", f"{len(subs)} of {len(clips)} clips were substituted with an animated treatment of a product still or one of your photos, "
              "so no beat is missing."]
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", ""]
    if engine.get("engine") == "stills":
        L.append(f"- Rendered as stills with ffmpeg because the motion engine could not run here: {engine.get('why')}.")
    else:
        L.append("- Rendered with the kit's Remotion project: 1080x1920, 30 fps, H.264, AAC.")
    L += ["", "## the critics on the finished film", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        cr = c.get("critics") or {}
        for who, e in cr.items():
            s = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in s.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts:
        last = cuts[-1]
        low = [(v, k) for e in (last.get("critics") or {}).values()
               for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, int) and v < 4]
        if low:
            L.append("- Still below 4 after the one fix: " + ", ".join(sorted({k for _, k in low})) + ".")
    return "\n".join(L) + "\n"


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}} .posts figure{{margin:0}} .posts figcaption{{font-size:13px;opacity:.75;margin-top:6px}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.posts img,.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your reveal film, three teaser stories, a countdown card, a feed post and a caption for each, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Captions</h2>{caption}
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, which clips were made and
which were stood in for, and where the music came from.</p></div></div>
<h2>The stories, the countdown card and the feed post</h2>{posts}
<h2>The three storyboards</h2><div class="sheets">{boards}</div>
<h2>The vote</h2>{table}<p>{runners}</p>
</main></body></html>
"""


def scored(cut):
    """A cut round whose every score was filled in; an unfilled round never reaches the brief."""
    sc = [v for e in (cut.get("critics") or {}).values() for b in (e.get("boards") or {}).values() for v in (b.get("scores") or {}).values()]
    return bool(sc) and all(isinstance(v, int) for v in sc)


def caption_html(cap):
    out = []
    for i, (k, v) in enumerate(sections(cap).items()):
        out.append(f"<h3>{esc(k)}</h3><pre id='cap{i}'>{esc(v)}</pre><button onclick=\"navigator.clipboard.writeText("
                   f"document.getElementById('cap{i}').innerText);this.textContent='Copied'\">Copy</button>")
    return "".join(out)


def posts_html():
    return "<div class='posts'>" + "".join(
        f"<figure><a href='{f}'><img src='{f}' loading='lazy' alt=''></a><figcaption>{esc(name)}</figcaption></figure>"
        for f, name in STILLS if (OUT / f).exists()) + "</div>"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    lib = _env.read_json("build/library.json") or {}
    taste = _env.read_json("build/taste.json") or {}
    win = _env.read_json("build/winner.json") or {}
    if not (lib and taste and win):
        sys.exit("build/library.json, build/taste.json or build/winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [c for c in (_env.read_json(p) for p in vote.rounds()) if scored(c)]
    launch = launch_of(lib, taste)
    OUT.mkdir(exist_ok=True)
    cap = captions(taste, launch)
    (OUT / "captions.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, win, clips, music, engine, cuts))
    sheets = OUT / "storyboards"
    sheets.mkdir(exist_ok=True)
    cells = []
    for i in sorted(win.get("totals") or {}):
        src = Path(f"build/storyboards/{i}/sheet.png")
        sb = _env.read_json(f"build/storyboards/{i}/storyboard.json") or {}
        if src.exists():
            shutil.copyfile(src, sheets / f"{i}.png")
        cls = "board win" if i == win.get("board") else "board"
        cells.append(f"<div class='{cls}'><a href='storyboards/{i}.png'><img src='storyboards/{i}.png' alt=''></a>"
                     f"<h3>{esc(i)}. {esc(sb.get('name'))} · {esc(win['totals'][i])}</h3><p>{esc(sb.get('idea'))}</p></div>")
    md = Path("build/vote.md").read_text() if Path("build/vote.md").exists() else ""
    rows = [ln for ln in md.splitlines() if ln.startswith("|") and not ln.startswith("|---")]
    rows = rows[:rows.index(next((r for r in rows if r.startswith("| total")), rows[-1])) + 1] if rows else []
    table = "<table>" + "".join("<tr>" + "".join(f"<td>{esc(c.strip().strip('*'))}</td>" for c in r.strip('|').split('|')) + "</tr>"
                                for r in rows) + "</table>"
    names = {i: (_env.read_json(f"build/storyboards/{i}/storyboard.json") or {}).get("name") for i in win.get("order") or []}
    runners = ("Runners-up: " + ", ".join(f"{esc(i)}. {esc(names[i])}" for i in (win.get("order") or [])[1:])
               + ". Want a different take? Say \"do the second one\" and that storyboard is made instead.")
    pal = (taste.get("palette") or {}).get("year") or []
    colors = (_env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    title = f"{launch.get('product')} · {launch.get('date_label') or 'launch'}"

    def page(banner):
        return PAGE.format(title=esc(title), banner=banner, caption=caption_html(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts_html(), boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print("delivered: out/film.mp4, out/story-1.png, out/story-2.png, out/story-3.png, out/countdown.png, out/feed.png, "
          "out/captions.md, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
