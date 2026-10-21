#!/usr/bin/env python3
"""Movement 6, last step: write the run's out/caption.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py --run R

caption.md is the run's caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from taste.json in their register (their case, their length, their own hashtags). brief.md says where the material
came from (every door tried, open or closed), what the run assumed, the vote and its swap test, where the music came
from, how the film was rendered, which clips were generated and which stood in, and the critics' scores of the cut; it opens with the nine, each with its numbers
and why it worked. review.html plays the three films and shows the best-nine image, the story card, the caption, the
storyboard's sheet and the vote.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong.
"""
import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")
HERE = Path(__file__).resolve().parent


def idea(tone):
    """The tone's idea: the first paragraph of its builder's docstring, without the leading "tone: " name."""
    para = " ".join(storyboard.tone_module(tone).__doc__.strip().split("\n\n")[0].split())
    return para.split(": ", 1)[1] if para.startswith(f"{tone}: ") else para


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(taste, win):
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    places = taste.get("places") or []
    year = taste.get("year")
    lines = [f"my best nine of {year}, the ones you loved most"]
    if len(places) >= 2:
        lines.append(", ".join(places[:-1]) + " and " + places[-1])
    lines.append("which one is your favorite?")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#bestnine", f"#bestnine{year}"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def nine_rows():
    st = _env.read_json("stats.json") or {}
    why = {x["rank"]: x for x in (_env.read_json("research.json") or {}).get("nine", [])}
    rows = ["| # | posted | likes | comments | why it worked |", "|---|---|---|---|---|"]
    for t in st.get("top_nine") or []:
        w = (why.get(t["rank"]) or {}).get("why") or ""
        rows.append(f"| {t['rank']} | {t.get('date_label') or t.get('date')} ({t.get('kind')}) | {t.get('likes', '-')} | "
                    f"{t.get('comments', '-')} | {w.replace('|', '/')} |")
    ten = st.get("tenth") or {}
    if ten.get("likes") is not None:
        rows += ["", f"The tenth had {ten['likes']} likes, {ten.get('gap')} fewer than the ninth."]
    return rows


def brief(lib, taste, win, music, film, report, cuts):
    handle, year = lib.get("handle") or taste.get("handle"), lib.get("year") or taste.get("year")
    L = [f"# @{handle}, best nine of {year}: how this was made", "", "## the nine", ""] + nine_rows()
    ph = lib.get("photos") or {}
    L += ["", "## where your photos came from", ""]
    if ph.get("folder"):
        L.append(f"- The photographs: {ph['folder']} ({ph.get('from')}).")
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md in this run has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the storyboards and the vote", ""]
    tot = win.get("totals") or {}
    for t in win.get("order") or []:
        swap = "passes the swap test" if (win.get("swap") or {}).get(t) else "fails the swap test"
        L.append(f"- {t} ({tot.get(t)} of {len(vote.PANEL) * len(vote.CRITERIA) * 5}, {swap}): {idea(t)}")
    if win.get("tie_broken_by_person"):
        L.append("- The top two tied; the critic speaking for you broke the tie.")
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {film.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", "",
          f"- The {film.get('tone')} storyboard, {film.get('seconds')} s, {len(film.get('cuts') or [])} cuts, rendered with the "
          "kit's Remotion studio at 30 fps in three shapes: 1080x1920 for reels and stories, 1080x1080 for the feed, "
          "1920x1080 for anywhere wide. Each shape is laid out on its own; nothing is scaled to fit.",
          f"- Rendered on {'the graphics card' if report.get('gpu') else 'the processor'} in {round(report.get('seconds') or 0)} s."]
    cl = (_env.read_json("clips.json") or {}).get("clips") or {}
    if cl:
        L += ["", "## the generated clips", ""]
        for k, c in cl.items():
            if c.get("status") == "generated":
                L.append(f"- {k}, {c['role']} ({c['beat']}): generated from {c['image']}, {c['frames']} frames, from {c['source']}.")
            else:
                L.append(f"- {k}, {c['role']} ({c['beat']}): stand-in, {c.get('why')}; the film makes {c.get('stand_in')}.")
    L += ["", "## the critics on the finished film", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        for who, e in (c.get("critics") or {}).items():
            sc = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in sc.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts:
        low = [k for e in (cuts[-1].get("critics") or {}).values()
               for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, int) and v < 4]
        if low:
            L.append("- Still below 4 after the one fix: " + ", ".join(sorted(set(low))) + ".")
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
.shapes{{display:grid;grid-template-columns:360px 1fr;gap:18px;align-items:start}} .shapes video{{width:100%}}
.posts{{display:grid;grid-template-columns:420px 236px;gap:18px;align-items:start}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.posts img,.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your best-nine film, the best-nine image, a story card and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, how the storyboard was
picked, and where the music came from.</p></div></div>
<h2>The same film for the feed and for wide screens</h2><div class="shapes"><video src="film-square.mp4" controls playsinline loop></video><video src="film-wide.mp4" controls playsinline loop></video></div>
<h2>The best-nine image and the story card</h2>{posts}
<h2>The storyboard</h2><div class="sheets">{boards}</div>
<h2>The vote</h2>{table}
</main></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _env.run_arg(ap)
    where = _env.enter_run(ap.parse_args().run)
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    film = _env.read_json("film.json") or {}
    if not (lib and taste and win and film):
        sys.exit("library.json, taste.json, winner.json or film.json is missing in the run; run the earlier movements first")
    music = _env.read_json("music.json") or {}
    report = _env.read_json("render/film-report.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, win)
    (OUT / "caption.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, win, music, film, report, cuts))
    sheets = OUT / "storyboards"
    sheets.mkdir(exist_ok=True)
    cells = []
    for t in sorted(win.get("totals") or {}):
        src = storyboard.BOARDS / t / "sheet.png"
        if src.exists():
            shutil.copyfile(src, sheets / f"{t}.png")
        cls = "board win" if t == win.get("board") else "board"
        cells.append(f"<div class='{cls}'><a href='storyboards/{t}.png'><img src='storyboards/{t}.png' alt=''></a>"
                     f"<h3>{esc(t)} · {esc(win['totals'][t])}</h3><p>{esc(idea(t))}</p></div>")
    md = Path("vote.md").read_text() if Path("vote.md").exists() else ""
    rows = [ln for ln in md.splitlines() if ln.startswith("|") and not ln.startswith("|---")]
    rows = rows[:rows.index(next((r for r in rows if r.startswith("| total")), rows[-1])) + 1] if rows else []
    table = "<table>" + "".join("<tr>" + "".join(f"<td>{esc(c.strip().strip('*'))}</td>" for c in r.strip('|').split('|')) + "</tr>"
                                for r in rows) + "</table>"
    colors = (_env.read_json(storyboard.BOARDS / film.get("tone", win["board"]) / "board-reel.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", "#e6b26d")
    handle, year = lib.get("handle"), lib.get("year")
    posts = gallery([p for p in ("best-nine.png", "story.png") if (OUT / p).exists()], "posts")

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · best nine {year}"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts, boards="".join(cells), table=table)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate", "--run", str(where)], capture_output=True, text=True,
                       cwd=_env.WORKSPACE)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print(f"delivered to {where / 'out'}: film.mp4, film-square.mp4, film-wide.mp4, best-nine.png, story.png, caption.md, "
          "review.html, brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
