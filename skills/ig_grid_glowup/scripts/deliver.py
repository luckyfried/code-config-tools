#!/usr/bin/env python3
"""Movement 6, last step: write out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

brief.md says where the material came from (every door tried, open or closed), what the run assumed, what each of
the nine is made from (their photo, a type post, a color tile, or a generated still and whether the image model made
it or the kit painted it), the three directions and the vote, every clip and how it arrived, where the music came
from, which engine rendered the film, and the critics' scores. review.html shows the audit, their grid with the nine in place, the nine posts with
the plan, the film, the three directions' style sheets and the vote, with the runners-up.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong.
"""
import html
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


def what_it_is(p, stills):
    if p.get("still"):
        st = (stills.get(p.get("still_id") or "") or {}).get("status")
        return ("a still made by the image model in your palette" if st == "generated"
                else "a still the kit painted in your palette (no image model answered)")
    if p.get("kind") == "type":
        return "your own words set as a post"
    if p.get("kind") == "color":
        return "a color tile with your line on it"
    src = Path(p.get("source") or "").name
    return f"your photo ({src})" if src else "your photo"


def nine_rows(film, plan, stills):
    caps = {s["n"]: s for s in plan.get("slots") or []}
    rows = ["| # | goes up | what it is | caption |", "|---|---|---|---|"]
    for p in sorted(film.get("posts") or [], key=lambda p: p["n"]):
        s = caps.get(p["n"]) or {}
        rows.append(f"| {p['n']} | {s.get('date', '-')} | {what_it_is(p, stills)} | {(s.get('caption') or '').replace('|', '/')} |")
    return rows


def brief(lib, taste, win, film, plan, clips, stills, music, engine, cuts):
    handle = lib.get("handle") or taste.get("handle")
    L = [f"# @{handle}, grid glow-up: how this was made", "",
         "`audit.md` is the read of your last 30 posts as a grid. `posts/` holds the next nine, `plan.md` says when to "
         "post each and what to write, `grid-after.png` shows them in place over your grid, and `film.mp4` is the "
         "before and after.", "", "## the nine", ""] + nine_rows(film, plan, stills)
    n_st = [p for p in film.get("posts") or [] if p.get("still")]
    if n_st:
        L += ["", f"{len(n_st)} of the nine {'is a generated still' if len(n_st) == 1 else 'are generated stills'}, because "
              "your library had no photo that fit that spot; the plan says which, so you can swap in your own."]
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "", "## the three directions and the vote", ""]
    tot = win.get("totals") or {}
    for i in win.get("order") or []:
        sb = _env.read_json(f"build/storyboards/{i}/storyboard.json") or {}
        mark = "won" if i == win.get("board") else "runner-up"
        L.append(f"- {i}, {sb.get('name')} ({mark}, {tot.get(i)} of {len(vote.PANEL) * len(vote.CRITERIA) * 5}): {sb.get('idea')}")
    if win.get("tie_broken_by_person"):
        L.append("- The top two tied; the critic speaking for you broke the tie.")
    L += ["", "Say \"do the second one\" to have the runner-up made instead.", "", "## the clips", ""]
    L += clip_rows(clips) if clips else ["The winning direction uses no clips."]
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
    L += ["", "## how it was made", ""]
    if engine.get("engine") == "stills":
        L.append(f"- Rendered as stills with ffmpeg because the motion engine could not run here: {engine.get('why')}.")
    else:
        L.append("- The nine posts, the grid and the film were rendered with the kit's Remotion project: posts at "
                 "1080x1350, the film at 1080x1920, 30 fps, H.264, AAC.")
    L += ["", "## the critics on the finished nine and the film", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        for who, e in (c.get("critics") or {}).items():
            s = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in s.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts:
        low = [k for e in (cuts[-1].get("critics") or {}).values()
               for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, int) and v < 4]
        if low:
            L.append("- Still below 4 after the one fix: " + ", ".join(sorted(set(low))) + ".")
    return "\n".join(L) + "\n"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:44px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:420px 1fr;gap:36px;align-items:start}}
.top img{{width:100%;border-radius:12px;display:block}}
video{{width:340px;border-radius:16px;background:#000;display:block}}
.nine{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;max-width:520px}}
.nine img{{width:100%;display:block}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
.audit{{background:rgba(127,127,127,.1);padding:4px 22px 14px;border-radius:12px}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left;vertical-align:top}}
a{{color:inherit}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">What your grid is doing, your next nine posts, when to post them, and a before and after film.</p>
{banner}
<div class="top"><a href="grid-after.png"><img src="grid-after.png" alt="Your profile with the next nine in place"></a><div>
<h2 style="margin-top:0">Your grid, read</h2><div class="audit">{audit}</div>
<p><a href="audit.md">audit.md</a> has the whole read; <a href="grid-before.png">grid-before.png</a> numbers your
grid as it is now.</p></div></div>
<h2>Your next nine</h2><p>As they will sit on your profile, newest at the top left. Each is a 1080x1350 file in
<a href="posts/">posts/</a>.</p><div class="nine">{nine}</div>
<h2>When to post them</h2>{plan}<p><a href="plan.md">plan.md</a> has the same plan to copy from.</p>
<h2>Before and after</h2><video src="film.mp4" controls playsinline loop></video>
<h2>The three directions</h2><div class="sheets">{boards}</div>
<h2>The vote</h2>{table}<p>{runners}</p>
<p><a href="brief.md">brief.md</a> says where everything came from, which stills and clips were made, and where the
music came from.</p>
</main></body></html>
"""


def md_table(lines):
    rows = [ln for ln in lines if ln.startswith("|") and not ln.startswith("|---")]
    return "<table>" + "".join("<tr>" + "".join(f"<td>{esc(c.strip().strip('*').strip('`'))}</td>" for c in r.strip("|").split("|"))
                               + "</tr>" for r in rows) + "</table>"


def audit_html(md):
    part = md.split("## What your grid is doing", 1)[-1].split("\n## ", 1)[0]
    items = [ln.split(".", 1)[1].strip() for ln in part.splitlines() if ln[:1].isdigit() and "." in ln]
    out = []
    for it in items:
        bold = it.split("**")
        out.append("<li>" + "".join(f"<b>{esc(x)}</b>" if k % 2 else esc(x) for k, x in enumerate(bold)) + "</li>")
    return "<ol>" + "".join(out) + "</ol>"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    lib = _env.read_json("build/library.json") or {}
    taste = _env.read_json("build/taste.json") or {}
    win = _env.read_json("build/winner.json") or {}
    if not (lib and taste and win):
        sys.exit("build/library.json, build/taste.json or build/winner.json is missing; run the earlier movements first")
    film = _env.read_json("build/film.json") or {}
    plan = _env.read_json("build/plan.json") or {}
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    stills = (_env.read_json("build/stills.json") or {}).get("stills") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    (OUT / "brief.md").write_text(brief(lib, taste, win, film, plan, clips, stills, music, engine, cuts))
    sheets = OUT / "directions"
    sheets.mkdir(exist_ok=True)
    cells = []
    for i in sorted(win.get("totals") or {}):
        src = Path(f"build/storyboards/{i}/sheet.png")
        sb = _env.read_json(f"build/storyboards/{i}/storyboard.json") or {}
        if src.exists():
            shutil.copyfile(src, sheets / f"{i}.png")
        cls = "board win" if i == win.get("board") else "board"
        cells.append(f"<div class='{cls}'><a href='directions/{i}.png'><img src='directions/{i}.png' alt=''></a>"
                     f"<h3>{esc(i)}. {esc(sb.get('name'))} · {esc(win['totals'][i])}</h3><p>{esc(sb.get('idea'))}</p></div>")
    md = Path("build/vote.md").read_text().splitlines() if Path("build/vote.md").exists() else []
    head = [ln for ln in md if ln.startswith("|")]
    stop = next((k for k, ln in enumerate(head) if ln.startswith("| total")), len(head) - 1)
    table = md_table(head[:stop + 1])
    names = {i: (_env.read_json(f"build/storyboards/{i}/storyboard.json") or {}).get("name") for i in win.get("order") or []}
    runners = ("Runners-up: " + ", ".join(f"{esc(i)}. {esc(names[i])}" for i in (win.get("order") or [])[1:])
               + ". Want a different take? Say \"do the second one\" and that direction is made instead.")
    nine = "".join(f"<a href='posts/{n:02d}.png'><img src='posts/{n:02d}.png' loading='lazy' alt='post {n}'></a>" for n in range(9, 0, -1))
    plan_md = Path("out/plan.md").read_text().splitlines() if Path("out/plan.md").exists() else []
    audit_md = Path("out/audit.md").read_text() if Path("out/audit.md").exists() else ""
    colors = (_env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("paper", "#f4efe8"), colors.get("ink", "#1d1a17"), colors.get("accent", "#a5482a")
    handle = lib.get("handle")

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · your grid, glowed up"), banner=banner, bg=bg, ink=ink, accent=accent,
                           audit=audit_html(audit_md) if audit_md else "<p>audit.md is missing.</p>", nine=nine,
                           plan=md_table(plan_md), boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print("delivered: out/audit.md, out/grid-before.png, out/posts/01..09.png, out/grid-after.png, out/plan.md, "
          "out/film.mp4, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
