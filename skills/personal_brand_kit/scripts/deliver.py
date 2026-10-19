#!/usr/bin/env python3
"""Movement 6, last step: write out/brand.json, out/caption.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

brand.json is build/brand.json, copied as it stands (the system the ten cards show). out/plan.md is written by
brand.py plan and only checked here. caption.md is build/caption.md when the agent wrote one in the person's voice,
otherwise a short caption drafted from build/brand.json in their register (their case, their own hashtags) to post
with the film or the cards. brief.md says where the material came from (every door tried, open or closed), what the
run assumed, what the read found (palette, type, pillars, cadence, voice, what to stop), the vote, every clip and
whether it was generated, taken from their own reels or substituted with an animated photo, where the music came from,
which engine rendered the film, and the critics' scores of the cut. review.html plays the film and shows the ten
cards, the caption, the three storyboards' style sheets and the vote, with the runners-up.
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


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(brand, taste):
    own = Path("build/caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    lines = ["my style, in ten cards", brand.get("statement") or "", "which card is most you?"]
    body = "\n".join(x for x in lines if x)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3]))
    return body + ("\n\n" + " ".join(tags) if tags else "") + "\n"


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    said = {"generated": "made by the video model", "their_reel": "taken from one of your own reels",
            "substituted": "no generated clip arrived; an animated treatment of your photo stands in"}
    for cid, c in sorted(clips.items()):
        how = said.get(c.get("status"), c.get("status"))
        if c.get("status") == "substituted" and c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def found_rows(brand):
    pct = lambda x: f"{round(100 * (x or 0))}%"
    pal = ", ".join(f"{c['name']} {c['hex']} ({c.get('role')}, {pct(c.get('share'))})" for c in brand.get("palette") or [])
    ty = brand.get("type") or {}
    cad = brand.get("cadence") or {}
    slots = ", ".join(f"{s['day']} {s['time']}" for s in cad.get("slots") or [])
    voice = brand.get("voice") or {}
    L = [f"- Statement: {brand.get('statement')}",
         f"- Palette: {pal}.",
         f"- Type: {ty.get('display')} for headlines, {ty.get('text')} for text. {ty.get('why') or ''}".rstrip(),
         "- Compositions: " + ", ".join(f"{c['name']} {pct(c.get('share'))}" for c in brand.get("compositions") or []) + ".",
         "- Pillars: " + ", ".join(f"{p['name']} {pct(p.get('share'))}" for p in brand.get("pillars") or []) + ".",
         f"- Cadence: {cad.get('per_week')} posts a week; best slots {slots} ({cad.get('timezone')}).",
         f"- Voice: {voice.get('case')}, about {voice.get('avg_words')} words a caption; "
         + ", ".join(d["name"] for d in voice.get("devices") or []) + "."]
    asp = brand.get("aspire") or {}
    if asp:
        L.append("- What you like elsewhere: " + ", ".join(asp.get("subjects") or []) + ".")
    for s in brand.get("stop") or []:
        L.append(f"- Stop: {s.get('line')}, because {s.get('why')}.")
    return L


def brief(lib, taste, brand, win, clips, music, engine, cuts):
    handle = brand.get("handle") or lib.get("handle")
    L = [f"# @{handle}, personal brand kit: how this was made", "", "## what the read found", ""] + found_rows(brand)
    L += ["", "The ten cards in out/cards show this; out/brand.json holds it; out/plan.md is the next 30 days.",
          "", "## where your material came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. It avoids " + (", ".join(taste.get("avoid") or []) or "nothing named") + ".", "",
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
        L += ["", f"{len(subs)} of {len(clips)} clips were substituted with an animated treatment of one of your photos, "
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
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.posts img,.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your style guide in ten cards, a film that reveals it, your brand file and the next 30 days.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, which clips were made and
which were stood in for, and where the music came from. <a href="plan.md">plan.md</a> is the next 30 days, and
<a href="brand.json">brand.json</a> holds the whole system.</p></div></div>
<h2>The ten cards</h2>{posts}
<h2>The three storyboards</h2><div class="sheets">{boards}</div>
<h2>The vote</h2>{table}<p>{runners}</p>
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    lib = _env.read_json("build/library.json") or {}
    taste = _env.read_json("build/taste.json") or {}
    brand = _env.read_json("build/brand.json") or {}
    win = _env.read_json("build/winner.json") or {}
    if not (lib and taste and brand and win):
        sys.exit("build/library.json, build/taste.json, build/brand.json or build/winner.json is missing; "
                 "run the earlier movements first")
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    shutil.copyfile("build/brand.json", OUT / "brand.json")
    cap = caption(brand, taste)
    (OUT / "caption.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, brand, win, clips, music, engine, cuts))
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
    pal = brand.get("palette") or []
    colors = (_env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle = brand.get("handle") or lib.get("handle")
    posts = gallery(sorted(f"cards/{p.name}" for p in (OUT / "cards").glob("*.png")), "posts")

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · personal brand kit"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts, boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print("delivered: out/film.mp4, out/cards/ (10), out/brand.json, out/plan.md, out/caption.md, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
