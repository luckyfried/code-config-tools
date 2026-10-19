#!/usr/bin/env python3
"""Movement 6, last step: write out/caption.md, out/brief.md, out/template.json and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is build/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from build/taste.json in their register (their case, their length, their own hashtags). brief.md opens with the
month against their year and the three that hit, each with its numbers and why it worked, then lists the cards,
where the material came from (every door tried, open or closed), what the run assumed, the vote, every clip and
whether it was generated, taken from their own reels or substituted with an animated photo, where the music came
from, which engine rendered the stories, and the critics' scores of the cut. template.json is the series as a
template (structure, card roles and titles, type, palette, texture, motion, the series mark), which next month's
storyboard.py draft reads so the series matches. review.html plays the film and every animated card beside its
static version, and shows the caption, the three storyboards' style sheets and the vote, with the runners-up.
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


def caption(taste, board):
    own = Path("build/caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    month = (taste.get("month") or {}).get("name") or "this month"
    n = len(board.get("cards") or [])
    head = (taste.get("change") or {}).get("headline") or []
    lines = [f"{month} in {n} stories"]
    if head:
        lines.append("; ".join(head[:2]))
    lines.append("which one was your favorite?")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#monthinreview", f"#{month.lower()}recap"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def clip_rows(clips):
    rows = ["| clip | where it plays | what it is | how it arrived |", "|---|---|---|---|"]
    said = {"generated": "made by the video model", "their_reel": "taken from one of your own reels",
            "substituted": "no generated clip arrived; an animated treatment of your photo stands in"}
    for cid, c in sorted(clips.items()):
        how = said.get(c.get("status"), c.get("status"))
        if c.get("status") == "substituted" and c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {', '.join(c.get('beats') or [c.get('beat')])} | {c.get('role')} | {how} |")
    return rows


def moment_rows():
    st = _env.read_json("build/stats.json") or {}
    why = {x["rank"]: x for x in (_env.read_json("build/research.json") or {}).get("moments", [])}
    rows = ["| # | posted | likes | comments | against your usual | why it worked |", "|---|---|---|---|---|---|"]
    for t in st.get("top_three") or []:
        w = (why.get(t["rank"]) or {}).get("why") or ""
        rows.append(f"| {t['rank']} | {t.get('date_label') or t.get('date')} ({t.get('kind')}) | {t.get('likes', '-')} | "
                    f"{t.get('comments', '-')} | {t.get('times_usual', '-')}x | {w.replace('|', '/')} |")
    ag = st.get("against") or {}
    if ag.get("year_best_likes") is not None:
        rows += ["", f"The best post of the rest of the year had {ag['year_best_likes']} likes ({ag.get('year_best_date')})."]
    return rows


def card_rows(board):
    rows = ["| card | idea | animated | static |", "|---|---|---|---|"]
    for c in board.get("cards") or []:
        rows.append(f"| {c['n']:02d} | {c['title']} | cards/{c['id']}.mp4 | cards/{c['id']}.png |")
    return rows


def brief(lib, taste, win, board, clips, music, engine, cuts):
    handle = lib.get("handle") or taste.get("handle")
    month = (lib.get("month") or {}).get("name") or ""
    year = (lib.get("month") or {}).get("year") or lib.get("year")
    L = [f"# @{handle}, {month} {year} in review: how this was made", "", "## this month against your year", ""]
    L += [f"- {h}" for h in (taste.get("change") or {}).get("headline") or []]
    L += ["", "## the three that hit", ""] + moment_rows()
    L += ["", f"## the series: {len(board.get('cards') or [])} story cards", ""] + card_rows(board)
    L += ["", "Every card is 15 s at 1080x1920 with a static version; the film carries the whole month in 15 s.",
          "out/template.json keeps the structure, type, palette and card roles, so next month's series matches."]
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; this month's palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("month", []))) + "; avoid "
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
        L += ["", f"{len(subs)} of {len(clips)} clips were substituted with an animated treatment of one of your photos, "
              "so no beat is missing."]
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the stories were made", ""]
    if engine.get("engine") == "stills":
        L.append(f"- Rendered as stills with ffmpeg because the motion engine could not run here: {engine.get('why')}.")
    else:
        L.append("- Rendered with the kit's Remotion project (shipped in the kit's motion/ folder): 1080x1920, 30 fps, H.264, AAC; "
                 "the film and every animated card from one storyboard, each static card from the same storyboard's still beat.")
    L += ["", "## the critics on the finished stories", ""]
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


def template(board, lib):
    """The series as a template: next month's draft follows its direction and its card roles."""
    s = board.get("system") or {}
    pick = {k: s.get(k) for k in ("display", "text", "scale")}
    used = sorted({(b.get("transition") or {}).get("preset") for _, bs in sets(board) for b in bs if b.get("transition")})
    return {"series": "month_in_review_stories", "handle": board.get("handle"), "month": board.get("month"),
            "board": {k: board.get(k) for k in ("id", "name", "axis", "direction")},
            "structure": board.get("structure"),
            "cards": [{"n": c["n"], "role": c["role"], "title": c["title"], "kinds": [b["kind"] for b in c["beats"]],
                       "seconds": 15, "still": c["still"]["kind"], "static": f"out/cards/{c['id']}.png",
                       "animated": f"out/cards/{c['id']}.mp4"} for c in board.get("cards") or []],
            "type": pick, "palette": {**(s.get("colors") or {}), "from": "this month's photos"},
            "texture": s.get("texture"), "ease": s.get("ease"), "transitions": used, "direction": s.get("direction"),
            "series_mark": {"text": "MONTH YEAR on the left, NN / NN on the right with the number in the accent",
                            "segments": "one per card; the current one fills over the card", "height": 92},
            "music": {k: (board.get("music") or {}).get(k) for k in ("direction", "bpm", "mood")},
            "film": {"seconds": 15, "kinds": [b["kind"] for b in board["film"]["beats"]]},
            "safe": (s.get("safe") or {}).get("story")}


def sets(board):
    return [("film", board["film"]["beats"])] + [(c["id"], c["beats"]) for c in board.get("cards") or []]


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1240px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:340px 1fr;gap:36px;align-items:start}}
video{{width:100%;border-radius:14px;background:#000;display:block}}
.cards{{display:grid;grid-template-columns:repeat({ncards},1fr);gap:16px}}
.card h3{{margin:8px 0 6px;font-size:15px}} .card img{{width:100%;border-radius:10px;display:block;margin-top:8px}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}} .sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your month as a numbered series of stories, each animated and still, a 15 second story film and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says how this month compares with your year, where everything
came from, which clips were made and which were stood in for, and where the music came from.
<a href="template.json">template.json</a> keeps the series' look so next month matches.</p></div></div>
<h2>The series</h2><p>Post them in order. Each card comes animated and still.</p><div class="cards">{cards}</div>
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
    win = _env.read_json("build/winner.json") or {}
    board = _env.read_json("build/film.json") or {}
    if not (lib and taste and win and board):
        sys.exit("build/library.json, build/taste.json, build/winner.json or build/film.json is missing; run the earlier movements first")
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, board)
    (OUT / "caption.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, win, board, clips, music, engine, cuts))
    _env.write_json(OUT / "template.json", template(board, lib))
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
    colors = (board.get("system") or {}).get("colors") or {}
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", "#e6b26d")
    month = board.get("month") or {}
    cards = "".join(f"<div class='card'><h3>{c['n']:02d} · {esc(c['title'])}</h3>"
                    f"<video src='cards/{esc(c['id'])}.mp4' controls playsinline loop muted></video>"
                    f"<a href='cards/{esc(c['id'])}.png'><img src='cards/{esc(c['id'])}.png' alt='' loading='lazy'></a></div>"
                    for c in board.get("cards") or [])

    def page(banner):
        return PAGE.format(title=esc(f"@{board.get('handle')} · {month.get('name', '')} {month.get('year', '')} in review"), banner=banner,
                           caption=esc(cap), bg=bg, ink=ink, accent=accent, cards=cards, ncards=max(3, len(board.get("cards") or [])),
                           boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print(f"delivered: out/film.mp4, {len(board.get('cards') or [])} cards in out/cards/ (animated and static), out/caption.md, "
          "out/template.json, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
