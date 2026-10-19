#!/usr/bin/env python3
"""Movement 6, last step: write out/caption.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is build/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from build/taste.json and build/shared.json in their register (their case, their length, their own hashtags); it
always names the named one by @handle. brief.md opens with who the film is for and how they were found (the
person's words, the tags, the comments, the runner-up), the occasion and where it came from, what the two share
(the photos, the videos, the comments traded, the first and the latest photo, the eras), then every door tried,
open or closed, what the run assumed, the vote, every clip and whether it was generated, taken from their own
videos or substituted with an animated photo, where the music came from, which engine rendered the film, and the
critics' scores of the cut. review.html plays both films and shows the card, the caption, the three storyboards'
style sheets and the vote, with the runners-up.
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


def caption(taste, shared):
    own = Path("build/caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    who = shared.get("who") or {}
    occ = {**(shared.get("occasion") or {}), **{k: v for k, v in (taste.get("occasion") or {}).items() if v}}
    eras = [e["place"] for e in shared.get("eras", []) if e.get("place")]
    first = (shared.get("first") or {}).get("date")
    lines = [occ.get("title") or f"for @{who.get('handle')}"]
    if first:
        m = int(first.split("-")[1])
        since = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                 "november", "december"][m - 1]
        lines.append(f"from that first photo in {since} to now" + (f": {', '.join(eras[:-1])} and {eras[-1]}" if len(eras) >= 2 else ""))
    line = (taste.get("love_lines") or [x["line"] for x in shared.get("love_lines", [])] or [None])[0]
    if line:
        lines.append(line)
    lines.append(f"love you @{who.get('handle')}")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:2]))
    return f"{body}\n" + (f"\n{' '.join(tags)}\n" if tags else "")


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    said = {"generated": "made by the video model", "their_video": "the video the two of you shot, as it is",
            "substituted": "no generated clip arrived; an animated treatment of your photo stands in"}
    for cid, c in sorted(clips.items()):
        how = said.get(c.get("status"), c.get("status"))
        if c.get("status") == "substituted" and c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def who_rows(shared):
    who = shared.get("who") or {}
    occ = shared.get("occasion") or {}
    c = shared.get("counts") or {}
    f, l = shared.get("first") or {}, shared.get("latest") or {}
    L = [f"- For @{who.get('handle')} ({who.get('name') or who.get('first')}): {who.get('matched_by')}"
         + (f" (you said \"{who.get('words')}\")" if who.get("words") and who.get("words").lstrip("@") != who.get("handle") else "") + "."]
    n = who.get("named_one") or {}
    if n:
        L.append(f"- What the two of you share on Instagram: tagged together {n.get('tagged', 0)} times, mentioned "
                 f"{n.get('mentioned', 0)} times, {n.get('commented_on', 0)} comments of theirs on your posts.")
    ru = who.get("runner_up") or {}
    if ru:
        L.append(f"- The next closest was @{ru.get('handle')} (score {ru.get('shared_score')} against {n.get('shared_score')}); "
                 "the film is not about them.")
    if occ.get("label"):
        L.append(f"- The occasion: {occ['label']}" + (f", on {occ['date']}" if occ.get("date") else "") + (f" (from {occ['from']})" if occ.get("from") else "") + ".")
    L.append(f"- {c.get('photos', 0)} photos and {c.get('videos', 0)} videos with the two of you ({c.get('posts', 0)} of your posts, "
             f"{c.get('stories', 0)} stories, {c.get('their_posts_with_you', 0)} of their posts), {c.get('exchanges', 0)} comments traded.")
    if f:
        L.append(f"- The first photo together: {f.get('date')}, \"{f.get('caption')}\". The latest: {l.get('date')}, \"{l.get('caption')}\".")
    eras = shared.get("eras") or []
    if eras:
        L.append("- The chapters: " + "; ".join(f"{e['label']} ({e['span']}, {e['count']} photos)" if e["label"] != e["span"]
                                                else f"{e['label']} ({e['count']} photos)" for e in eras) + ".")
    feed = shared.get("feed") or {}
    if feed.get("handle"):
        L.append(f"- Their own feed was read from {feed.get('source') or 'a saved copy'}: {feed.get('posts', 0)} posts; its palette is in build/palette.json.")
    return L


def brief(lib, taste, shared, win, clips, music, engine, cuts):
    handle = lib.get("handle") or taste.get("handle")
    who = (shared.get("who") or {}).get("handle")
    occ = (shared.get("occasion") or {}).get("label")
    L = [f"# @{handle} for @{who}{', ' + occ if occ else ''}: how this was made", "", "## who it is for", ""] + who_rows(shared)
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in (lib.get("assumptions") or []) + (shared.get("assumptions") or [])]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("together", []))) + " (the colors the two of you share); avoid "
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
    L += ["", "## how the film was made", ""]
    if engine.get("engine") == "stills":
        L.append(f"- Rendered as stills with ffmpeg because the motion engine could not run here: {engine.get('why')}.")
    else:
        L.append("- Rendered with the kit's Remotion project from one storyboard: 1080x1920 and 1080x1080, 30 fps, H.264, AAC; "
                 "the card at 1080x1350.")
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


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:420px 336px;gap:18px;align-items:start}} .posts video{{width:100%}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.posts img,.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your tribute film, the same film square for the feed, a card and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, which clips were made and
which were stood in for, and where the music came from.</p></div></div>
<h2>The square film and the card</h2>{posts}
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
    shared = _env.read_json("build/shared.json") or {}
    win = _env.read_json("build/winner.json") or {}
    if not (lib and taste and win):
        sys.exit("build/library.json, build/taste.json or build/winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, shared)
    (OUT / "caption.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, shared, win, clips, music, engine, cuts))
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
    pal = (taste.get("palette") or {}).get("together") or []
    colors = (_env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle = lib.get("handle")
    who = (shared.get("who") or {}).get("handle")
    occ = (shared.get("occasion") or {}).get("label")
    posts = ("<div class='posts'>" + ("<video src='film-square.mp4' controls playsinline loop></video>" if (OUT / "film-square.mp4").exists() else "")
             + ("<a href='card.png'><img src='card.png' alt=''></a>" if (OUT / "card.png").exists() else "") + "</div>")

    def page(banner):
        return PAGE.format(title=esc(f"For @{who}" + (f" · {occ}" if occ else "") + f" · from @{handle}"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts, boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print("delivered: out/film.mp4, out/film-square.mp4, out/card.png, out/caption.md, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
