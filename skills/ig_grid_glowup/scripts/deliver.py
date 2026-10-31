#!/usr/bin/env python3
"""The last step: write brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

brief.md, in the run folder beside out/, says where the photos came from (every door tried, open or closed), what the
run assumed, which of their photos each post is, the look picked and why, the panel's means for the three looks, where
the music came from, how the films were made, and the critic's score on each of the seven rules against the bar (a
mean of 4.5 and no rule under 4), with the verdict. review.html, in the film's own colors, is the film's cover: it
opens on the reel playing, with the landscape and square films beside it, then the posts, the Story card and the
captions, when to post them, their grid with the plan in place, the read of their grid beside the grid it numbers
(out/grid-before.png) when they have a feed, the other two looks (out/boards.png) with how to ask for one, and how it
was made in plain words. It carries no scores: they are in brief.md.
Exit 0 only when qa.py gate passes. deliver holds the run's lock (name "deliver") from the moment it enters the run
to its last write and runs the gate in its own process under that lock, so every probe the gate starts holds the
lock and no render changes out/ while it reads it. It removes out/review.html before its first write, then writes
the page with its last section saying "Not ready to post" before the gate runs; only a passing gate writes the page
without it, and on a failed gate that section names each failing check. Every file reaches out/ by a rename, so a
deliver that was stopped leaves no half-written file there and no page that looks delivered. On a passing gate its
last line is the reel's path from the project's root (build/<run>/out/film.mp4), the path the reply names first; on a
failed gate it is "not ready: the gate failed on" and the failing checks, and no path.
"""
import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")


def esc(s):
    return html.escape("" if s is None else str(s))


def nine_rows(plan):
    rows = ["| # | goes up | which photo | caption |", "|---|---|---|---|"]
    for s in plan.get("slots") or []:
        src = Path(s.get("source") or s.get("photo") or "").name
        what = f"your photo ({src})" + (f", titled \"{s['lesson']}\" on the cover" if s.get("lesson") else "")
        rows.append(f"| {s['n']} | {s.get('date', '-')} | {what} | {(s.get('caption') or '').replace('|', '/')} |")
    return rows


def brief(lib, taste, win, plan, music, done, cuts, films):
    handle = lib.get("handle") or taste.get("handle")
    m = len(plan.get("slots") or [])
    shown = ("shows them in place over your grid, and `film.mp4` is the before and after" if lib.get("grid")
             else "shows how your profile will look with them, and `film.mp4` is the film of them landing there,")
    L = [f"# @{handle}, grid glow-up: how this was made", "",
         "Everything to post is in `out/`; `out/review.html` opens it. "
         + ("`audit.md`, here beside it, is the read of your last 30 posts as a grid. " if lib.get("grid") else "")
         + f"`out/posts/` holds the next {vote_num(m)}, `out/caption.txt` has what to write under each and under the reel, "
         + "`out/story.png` is the Story that sends people to the new grid, `out/grid-after.png` "
         + shown + " for Reels" + (", with " + " and ".join(f"`{n}`" for n in films[1:]) + " for anywhere else" if len(films) > 1 else "") + ".",
         "", "## the posts", ""] + nine_rows(plan)
    if m < 9:
        L += ["", f"Your photos that never had a post of their own gave {vote_num(m)} that fit the grid, so the plan and "
              "the film have that many."]
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "", "## the film", ""]
    L.append(f"- Look {win.get('board')}, {(win.get('name') or win.get('style') or '').lower()}, picked by "
             + ("you" if win.get("by") == "person" else "your taste") + f": {win.get('reason')}")
    L.append(f"- The other looks, {' and '.join(win.get('others') or [])}, are in `out/boards.png`; ask for one and the film is made again in it.")
    if Path("vote.md").exists():
        L.append("- The panel's read of the three looks is in `vote.md`.")
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- Mastered to {music.get('master_lufs', -14)} LUFS; "
                 + ("the cuts land on its beats." if music.get("on_cut_tempo") else
                    f"it plays at its own {music.get('bpm')} bpm, too far from the film's tempo to follow its beats."))
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how it was made", "",
          "- One storyboard, laid out afresh for each shape (tall, wide and square), at 30 fps, H.264 with AAC sound."
          + (f" {done.get('render_seconds')} s for the {len(done.get('formats') or [])} films." if done else ""),
          f"- The posts are 1080x1350, laid out in the look's own type and colors; the grid shows each one's middle 3:4."]
    L += ["", "## the critic on the finished film, rule by rule", "",
          f"The bar: a mean of {vote.MEAN} over the seven rules and no rule under {vote.FLOOR}; each rule's score is the "
          "lower of the two critics'.", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        for who, e in (c.get("critics") or {}).items():
            sc = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in sc.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    said = verdict()
    if said:
        L += ["", "| rule | score | against the bar |", "|---|---|---|"]
        L += [f"| {vote.CRITERIA[k]} | {v} | {'at or over 4' if v >= vote.FLOOR else 'under 4'} |" for k, v in said[2].items()]
        L += ["", f"Mean {sum(said[2].values()) / len(said[2]):.2f} against {vote.MEAN}. {said[1]}."]
    return "\n".join(L) + "\n"


def verdict():
    """vote.py verdict on the latest cut round: (word, message, scores), or None when no round is complete."""
    rs = vote.rounds()
    return vote.decide(rs) if rs else None


def vote_num(m):
    return ["no posts", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][m]


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:44px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.films{{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}}
video{{border-radius:12px;background:#000;display:block}} .reel{{width:360px}} .landscape{{width:560px}} .square{{width:315px}}
.side{{display:flex;flex-direction:column;gap:18px}}
.nine{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;max-width:520px}}
.nine img{{width:100%;display:block}}
.pair{{display:grid;grid-template-columns:520px 240px;gap:36px;align-items:start}} .pair img{{width:100%;border-radius:12px;display:block}}
.top{{display:grid;grid-template-columns:420px 1fr;gap:36px;align-items:start}}
.top img{{width:100%;border-radius:12px;display:block}}
.boards{{width:100%;border-radius:12px;display:block}}
.audit{{background:rgba(127,127,127,.1);padding:4px 22px 14px;border-radius:12px}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left;vertical-align:top}}
a{{color:inherit}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">{sub}</p>
<div class="films">{films}</div>
<h2>Your next posts</h2><p>As they will sit on your profile, newest at the top left, with the Story that sends people
to them. Each post is a 1080x1350 file in <a href="posts/">posts/</a>; <a href="caption.txt">caption.txt</a> has what
to write under each, and under the reel.</p><div class="pair"><div class="nine">{nine}</div>
<a href="story.png"><img src="story.png" alt="The Story card"></a></div>
<h2>When to post them</h2>{plan}
<div class="top"><a href="grid-after.png"><img src="grid-after.png" alt="Your profile with the next posts in place"></a><div>
{read}</div></div>
<h2>Prefer another look?</h2><p>This film is look {letter}, {look}. All three looks are below, each as its first
frame, a held post and its ending. Say "make the second one" or name a letter, and the film, the posts and the grid are
made again in that look.</p><a href="boards.png"><img class="boards" src="boards.png" alt="The three looks"></a>
<h2>How it was made</h2>{made}
{ready}
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
    _env.enter_run()
    # the gate reads pictures with Pillow: its re-exec happens here, before the lock, since an exec drops the lock's file
    _env.need("PIL")
    with studio.lock("deliver") as run:
        return delivered(run)


def delivered(run):
    """Everything deliver writes, under the run's lock `run`."""
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win.get("board")):
        sys.exit("library.json, taste.json or winner.json is missing; run the earlier steps first")
    plan = _env.read_json("plan.json") or {}
    music = _env.read_json("music.json") or {}
    done = _env.read_json("render/film.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    _env.unready()
    names = [n for n in ("film.mp4", "film-landscape.mp4", "film-square.mp4") if (OUT / n).exists()]
    _env.write_text("brief.md", brief(lib, taste, win, plan, music, done, cuts, names))
    m = len(plan.get("slots") or [])
    nine = "".join(f"<a href='posts/{n:02d}.png'><img src='posts/{n:02d}.png' loading='lazy' alt='post {n}'></a>" for n in range(m, 0, -1))
    video = {name: f"<video class='{fmt}' src='{name}' controls playsinline loop muted{' autoplay' if fmt == 'reel' else ''}></video>"
             for fmt, name in (("reel", "film.mp4"), ("landscape", "film-landscape.mp4"), ("square", "film-square.mp4")) if (OUT / name).exists()}
    films = video.get("film.mp4", "") + "<div class='side'>" + "".join(v for n, v in video.items() if n != "film.mp4") + "</div>"
    plan_md = Path("plan.md").read_text().splitlines() if Path("plan.md").exists() else []
    audit_md = Path("audit.md").read_text() if Path("audit.md").exists() else ""
    colors = ((_env.read_json("board.json") or {}).get("boards") or {}).get("reel", {}).get("system", {}).get("colors") or {}
    bg, ink, accent = colors.get("bg", "#160e09"), colors.get("paper", "#f4ead8"), colors.get("accent", "#e0a040")
    handle = lib.get("handle")
    if lib.get("grid"):
        sub = "Your grid's glow-up film, your next posts and when to post them, over the grid you have now."
        if Path("grid-before.png").exists():
            tmp = _env.part(OUT / "grid-before.png")
            tmp.write_bytes(Path("grid-before.png").read_bytes())
            os.replace(tmp, OUT / "grid-before.png")
        read = ('<h2 style="margin-top:0">Your grid, read</h2><p>The numbers are the posts as they sit on your grid now, '
                'counted from the top left.</p><a href="grid-before.png"><img src="grid-before.png" alt="Your grid now, numbered"></a>'
                '<div class="audit">' + (audit_html(audit_md) if audit_md else "<p>audit.md is missing.</p>") + '</div>')
    else:
        sub = "The film of your next posts landing on your profile, the posts, and when to post them."
        read = '<h2 style="margin-top:0">Your profile, next</h2><p>How your profile will look once the new posts are up.</p>'

    sound = ("The music was made for this look, at its tempo, with each cut landing on a beat and the sound stopping as "
             "the last line lands. " if music.get("file") else "The film is silent; add a sound when you post. ")
    made = (f"<p>Your photos were read for their light, color and what they show, and {vote_num(m)} that never had a post "
            "of their own were placed so the grid alternates quiet and busy pictures. Three looks were drawn from the same "
            "story, and " + ("you picked this one. " if win.get("by") == "person" else "this one was picked for you. ") + sound + "The film was made in three shapes from one storyboard, "
            "and every frame was checked for words that run out of place before it reached you.</p>")

    def page(ready):
        return PAGE.format(title=esc(f"@{handle} · your grid, glowed up"), bg=bg, ink=ink, accent=accent, sub=sub, read=read,
                           nine=nine, films=films, plan=md_table(plan_md), letter=esc(win.get("board")),
                           look=esc((win.get("name") or win.get("style") or "").lower()), made=made, ready=ready)

    _env.write_text(OUT / "review.html", page("<h2>Not ready to post</h2><p>The last checks have not run yet: run deliver.py.</p>"))
    res, board = qa.gate_checks(run)
    if qa.report(res, "qa/gate.json", board, "GATE") != 0:
        # the person's page names what is not ready in plain words; the film's scores stay in brief.md
        items = "".join(f"<li>{esc(name)} " + ("the finished film is still being reviewed" if name == "critic" else esc(detail)) + "</li>"
                        for name, ok, detail, *_ in res if ok is False)
        _env.write_text(OUT / "review.html", page(f"<h2>Not ready to post</h2><ul>{items}</ul>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        print("not ready: the gate failed on " + ", ".join(dict.fromkeys(name for name, ok, *_ in res if ok is False)))
        return 1
    _env.write_text(OUT / "review.html", page(""))
    print("delivered: " + ", ".join(f"out/{n}" for n in names) + f", out/posts/01..{m:02d}.png, out/story.png, out/caption.txt, "
          "out/grid-after.png, out/review.html; beside out/: brief.md" + (", audit.md, grid-before.png" if lib.get("grid") else ""))
    print(Path(os.path.relpath(Path.cwd().resolve() / OUT / "film.mp4", _env.HOME)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
