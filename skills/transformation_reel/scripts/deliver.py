#!/usr/bin/env python3
"""Movement 5, last step: write caption.md and review.html beside the cut in RUN/cut/ and the making-of RUN/brief.md,
run the gate, and on a passing gate publish the cut to RUN/out/.

USAGE (from the workspace root; S = this skill's folder; RUN = build/<run stamp>/, named in build/RUN):
    python3 S/scripts/deliver.py

caption.md is RUN/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from RUN/taste.json and RUN/subject.json in their register (their case, their length, their own hashtags). Either
way it carries the span as the closer does, in their own words where they say it ("fourteen months in") and otherwise
as their first and latest dates, and the gate checks it. RUN/brief.md, the making-of beside the deliverables and never
in out/, opens with the timeline (the subject, the first post, the latest, the span and every milestone, and every
photograph the film shows, in order), then says where the material came from (every door tried, open or closed), what
the run assumed, the three looks and the one made, the length made and why when it is not the length they asked for
(storyboard.length_said), the posts whose line the film leaves off, the timing round, where the music came from, where
the film rendered, and every round of the critics on the cut, rule by rule against the bar (a mean of 4.5 and no rule
under 4), with the rules nobody could read named as not read. review.html is the page for the person, in the film's
own colors: the film with cover.png as its poster, the caption to copy, the story cards and the then/now card, the
square and 16:9 films when they asked for them, the other two looks (cut/looks/, each its opening, its busiest moment
and its ending) with how to ask for one, and how the film was made in plain words. The scores stay in brief.md.
A cut under the bar is delivered as the run's best, its scores stated in brief.md; the gate never refuses on a score.

RUN/out/ holds the deliverables only once the gate passes: deliver removes RUN/out/ first, writes caption.md and
review.html into RUN/cut/ and RUN/brief.md, runs qa.py gate, and on a pass publishes everything in RUN/cut/ to RUN/out/
in one rename, so out/ is never a set the gate refused. On a passing gate the last line printed is the reel's path from
the workspace root (RUN/out/film.mp4, for example build/20261026-014049/out/film.mp4), the path the reply to the person
names first; on a failed gate it is "not delivered: the gate failed on " and the failing checks' names, no path, and no
RUN/out/. deliver holds the run's lock (scripts/chunks.py, named deliver) from its first write to its last. The gate
runs inside deliver with that lock, so every probe and detector it starts holds it too; while another command holds
it, deliver exits nonzero and names that command.
"""
import html
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import chunks  # noqa: E402
import vote  # noqa: E402
import qa  # noqa: E402


def esc(s):
    return html.escape("" if s is None else str(s))


def plain(line):
    """One of their captions as a line of ours: no milestone prefix, no hashtags, no span of its own."""
    c = re.sub(r"^\s*milestone\s*[:\-–]\s*", "", re.sub(r"#\w+", "", line or ""), flags=re.I).strip()
    return "" if qa.SPAN.search(c) else c


def caption(taste, sub, fx):
    own = _env.b("caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    span = sub.get("span") or {}
    words = sub.get("named") or sub.get("subject") or taste.get("subject")
    then = next((x for x in [plain(sub.get("first", {}).get("caption"))] + [plain(x) for x in (sub.get("voice") or {}).get("early", {}).get("lines", [])] if x), "")
    now = next((x for x in [plain(c.get("line")) for c in sub.get("changed") or []] if x), "")
    own = qa.SPAN.search(fx.get("said") or "")
    lines = [(f"{own.group(0)} of {words}" if own else words) + (f", {span.get('from')} to {span.get('to')}" if span.get("from") else "")]
    if then and now:
        lines.append(f"then: {then.split('. ')[0]}. now: {now.split('. ')[0]}")
    lines.append("swipe for the first and the latest side by side")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#progress", "#thenandnow"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def timeline_rows(fx, sub, board):
    """The timeline the builder computed, beside the photographs the film shows."""
    L = [f"Subject: {sub.get('subject')} ({'named by you' if sub.get('named') else 'found from your posts'}: "
         f"{', '.join(sub.get('terms') or [])}), {fx.get('count')} dated posts.",
         f"First post: {fx.get('first')}. Latest: {fx.get('latest')}."
         + (f" The span in their words: \"{fx['said']}\"." if fx.get("said") else ""), "",
         "| milestone | date | post | how it was found |", "|---|---|---|---|"]
    for m in sub.get("milestones") or []:
        said = re.sub(r"^\s*milestone\s*[:\-–]\s*", "", m.get("label") or "", flags=re.I).replace("|", "/")
        L.append(f"| {said} | {m.get('date')} | {m.get('id')} | {m.get('why')} |")
    L += ["", "The film's photographs, in order:", "", "| # | post | date | in the film | photograph |", "|---|---|---|---|---|"]
    for n, c in enumerate(((board or {}).get("film") or {}).get("cards") or [], 1):
        L.append(f"| {n} | {c['id']} | {c['date']} | {KIND.get(c['kind'], c['kind'])} | {Path(c['file']).name} |")
    return L


KIND = {"hook": "day one", "ordinary": "a run", "milestone": "a milestone", "latest": "the latest"}


def brief(lib, taste, sub, board, win, film, music, render, timing, cuts):
    import storyboard
    fx = board.get("facts") or {}
    handle = (lib.get("handle") or taste.get("handle") or "").lstrip("@")
    L = [f"# {'@' + handle + ', ' if handle else ''}{sub.get('subject')}: how this was made", "", "## the timeline", ""]
    unsaid = ((board or {}).get("film") or {}).get("unsaid") or []
    L += timeline_rows(fx, sub, board)
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("subject", []))) + "; "
          + ((taste.get("progress_style") or {}).get("why") or "") + "; your voice: " + ((sub.get("voice") or {}).get("summary") or "")
          + "; avoid " + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the three looks", ""]
    i, most = win.get("board"), len(vote.PANEL) * len(vote.CRITERIA) * 5
    for n, b in enumerate(storyboard.load_boards()):
        tot = (win.get("totals") or {}).get(b["style"])
        L.append(f"- {'ABC'[n] if n < 3 else n + 1}. {b.get('title')} ({b['style']})" + (f", {tot} of {most} on the boards" if tot is not None else "")
                 + (", recommended" if b["style"] == win.get("recommended") else "") + (", made" if b["style"] == i else "") + f": {b.get('idea')}.")
    chosen = win.get("chosen")
    L.append("- The look made was " + (f"chosen by you." if chosen in (None, "you") else f"picked from your taste: {chosen}."))
    L += ["", "## the timed cut", ""]
    said = storyboard.length_said(film.get("seconds") or 0, storyboard.asked(taste), len(board["film"]["cards"]))
    if said:
        L.append(f"- {said}")
    if unsaid:
        L.append(f"- {storyboard.unsaid_said(unsaid)}")
    read = (timing or {}).get("read") or {}
    if timing:
        L.append(f"- {qa.summary(timing.get('figures') or {})}.")
        L += [f"- {k}: {read.get(k)}" for k in vote.READS]
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {film.get('note')}; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", "",
          "- Rendered on this computer" + (f" ({render['device']})" if render.get("device") else "") + f": {sizes(render)}, 30 frames a second."]
    L += ["", "## the critics on the cut", "",
          f"The bar every film is held to: a mean of {vote.BAR} over the seven rules, and no rule under {vote.FLOOR}. "
          "A round's score on a rule is the lower of its critics' scores.", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        by, unread, mean = vote.standing(c)
        L += [f"### round {c.get('round')}", "", "| rule | score | " + " | ".join(vote.CUT_PANEL[w] for w in vote.CUT_PANEL) + " |",
              "|---|---|" + "---|" * len(vote.CUT_PANEL)]
        for k, rule in vote.CRITERIA.items():
            per = [(((c.get("critics") or {}).get(w) or {}).get("boards", {}).get("film", {}).get("scores") or {}).get(k) for w in vote.CUT_PANEL]
            L.append(f"| {rule} | {by.get(k, 'not read')} | " + " | ".join("not read" if v is None else str(v) for v in per) + " |")
        L += ["", f"Mean {mean} against the bar of {vote.BAR}" + (", every rule read at " + str(vote.FLOOR) + " or more" if not vote.short(by, mean) else
                                                                 "; under the bar on " + ", ".join(vote.short(by, mean))) + "."]
        if unread:
            L.append("Not read in this session: " + ", ".join(unread) + " (nobody could hear the film); it is not scored as a pass.")
        if c.get("fixed"):
            L.append(f"Fixed before round {c.get('round')}: {c['fixed']}")
        L.append("")
    return "\n".join(L) + "\n"


def sizes(render):
    """The films the render made, in words: the reel's size, and the square and 16:9 ones when the person asked for them."""
    of = {"reel": "1080x1920", "square": "1080x1080", "landscape": "1920x1080"}
    got = [of[f] for f in of if f in set((render.get("made") or {}).get("formats") or ["reel"])]
    return got[0] if len(got) == 1 else ", ".join(got[:-1]) + " and " + got[-1]


def put(path, text):
    """`text` at `path`, written beside it and renamed onto it, so the file is either the old one or the new one whole."""
    with _env.whole(path) as tmp:
        tmp.write_text(text)


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:repeat(3,220px) 420px;gap:18px;align-items:start}}
.posts img{{width:100%;border-radius:8px;display:block}}
.looks{{display:grid;gap:22px}} .looks figure{{margin:0}} .looks img{{width:100%;max-width:900px;border-radius:8px;display:block}}
.looks figcaption{{margin-top:8px;opacity:.8}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<div class="top"><video src="film.mp4" poster="cover.png" controls playsinline loop autoplay muted></video><div>
<h1>{title}</h1><p class="sub">Your transformation film, the then/now card and a caption.</p>
<h2>Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
{films}</div></div>
<h2>The story cards and the then/now card</h2>{posts}
<h2>The other two looks</h2>{looks}
<h2>How it was made</h2>{made}
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.need("PIL")
    _env.tools()
    with chunks.lock(_env.b("render"), "deliver") as run:
        return deliver(run)


def contrast(a, b):
    """The contrast ratio of two hex colors (WCAG): 1 for the same color, 21 for black on white."""
    import palette
    return palette.contrast(palette.hex_rgb(a), palette.hex_rgb(b))


PAGE_CONTRAST = 7.0


def page_colors(colors):
    """The review page's background, text and accent from the film's colors: its ground under its paper, the words'
    color for the accent; with the darker of ground and ink under the paper when the ground does not read under it,
    and a plain dark, warm white and yellow when neither reads under PAGE_CONTRAST to one."""
    import compose
    for bg in (colors["ground"], colors["ink"], colors.get("shade") or colors["ink"]):
        ink = colors["paper"]
        accent = colors["words"] if contrast(bg, colors["words"]) >= 4.5 else ink
        if contrast(bg, ink) >= PAGE_CONTRAST:
            return bg, ink, accent
    return compose.NEUTRAL[0], compose.NEUTRAL[1], compose.NEUTRAL[3]


ORDINAL = ("first", "second", "third", "fourth", "fifth", "sixth")


def looks(cut, made):
    """The other looks for the review page: each look's opening, busiest moment and ending side by side in
    cut/looks/<n>-<style>.png (n its place among the three, as boards.png numbers them), with its name and sentence."""
    import storyboard
    from PIL import Image
    d = cut / "looks"
    shutil.rmtree(d, ignore_errors=True)
    out, shown = [], []
    for n, b in enumerate(storyboard.load_boards()):
        if b["style"] == made:
            continue
        fr = storyboard.boards_dir() / b["style"] / "frames"
        ims = [Image.open(fr / f"{k}.png").convert("RGB") for k in storyboard.SHOWN if (fr / f"{k}.png").exists()]
        if not ims:
            continue
        w, h = ims[0].width // 3, ims[0].height // 3
        strip = Image.new("RGB", (w * len(ims) + 16 * (len(ims) - 1), h), (12, 12, 12))
        for i, im in enumerate(ims):
            strip.paste(im.resize((w, h), Image.LANCZOS), (i * (w + 16), 0))
        name = f"looks/{n + 1}-{b['style']}.png"
        d.mkdir(parents=True, exist_ok=True)
        strip.save(cut / name)
        shown.append(n)
        out.append(f"<figure><img src='{esc(name)}' alt=''><figcaption>The {ORDINAL[n]} one: <b>{esc(b.get('title'))}</b>. "
                   f"{esc(b.get('look_said'))}</figcaption></figure>")
    # the way to ask names one of the looks shown, never the one made
    ask = (f"<p>Prefer another look? Say \"make the {ORDINAL[shown[0]]} one\" and the film is made again in that look, "
           "with its own type, colors and music.</p>") if shown else ""
    return "<div class='looks'>" + "".join(out) + "</div>" + ask


def made_said(sub, fx, board, music, clips):
    """How the film was made, for the person, in plain words."""
    f = board["film"]
    n = len(f["cards"])
    said = [f"The film walks your posts about {sub.get('subject')} from the first, {fx.get('first')}, to the latest, "
            f"{fx.get('latest')}: {n} of your photographs in the order you posted them, each with your own words on it, "
            "and every photograph stays on the wall the film ends on."]
    g = sum(1 for r in (clips.get("clips") or {}).values() if r.get("status") == "generated")
    if g:
        said.append(f"{g} of those moments move as short clips made from your own photographs.")
    if music.get("board"):
        said.append(f"The music was composed for this look on this computer, at {board.get('bpm')} beats a minute, and the cuts land on its beats.")
    elif music.get("file"):
        said.append("The music is the track you gave it, and the cuts land on its beats.")
    else:
        said.append("The film is silent: add a sound when you post.")
    said.append("Nothing you posted left this computer.")
    return "".join(f"<p>{esc(s)}</p>" for s in said)


def publish(cut, out):
    """Everything in `cut` at `out` in one rename: linked (copied where a link is refused) into a folder beside `out`,
    which then takes its name, so `out` is never a part of the set."""
    part = out.with_name(".out.part")
    shutil.rmtree(part, ignore_errors=True)
    for src in sorted(cut.rglob("*")):
        dst = part / src.relative_to(cut)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    shutil.rmtree(out, ignore_errors=True)
    os.replace(part, out)


def deliver(run):
    """Everything deliver writes, under the run's lock `run` (chunks.lock). The gate runs in this process with the
    same `run`, so every process it starts goes through run.spawn and holds the lock."""
    import storyboard
    lib = _env.read_json(_env.b("library.json")) or {}
    taste = _env.read_json(_env.b("taste.json")) or {}
    sub = _env.read_json(_env.b("subject.json")) or {}
    film = _env.read_json(_env.b("film.json")) or {}
    win = _env.read_json(_env.b("winner.json")) or {}
    if not (lib and taste and sub and win and film):
        sys.exit("RUN/library.json, taste.json, subject.json, winner.json or film.json is missing; run the earlier movements first")
    CUT, OUT = _env.cut(), _env.out()
    if not (CUT / "film.mp4").exists():
        sys.exit("RUN/cut/film.mp4 is missing: run film.py render first")
    # boards.png, the three looks the person chose from, travels with the cut; out/ is only ever a set the gate passed,
    # so the last one goes before anything is written
    if (OUT / "boards.png").exists():
        shutil.copy2(OUT / "boards.png", CUT / "boards.png")
    shutil.rmtree(OUT, ignore_errors=True)
    board = storyboard.lay_out(film["board"])
    fx = board["facts"]
    music = _env.read_json(_env.b("music.json")) or {}
    render = _env.read_json(_env.b("render", "report.json")) or {}
    timing = _env.read_json(_env.b("critic", "timing.json")) or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    cap = caption(taste, sub, fx)
    put(CUT / "caption.md", cap)
    put(_env.b("brief.md"), brief(lib, taste, sub, board, win, film, music, render, timing, cuts))
    bg, ink, accent = page_colors(board["film"]["colors"])
    handle = (lib.get("handle") or "").lstrip("@")
    shown = ["stories/01-hook.png", "stories/02-dense.png", "stories/03-closer.png", "then-now.png"]
    posts = gallery(shown, "posts")
    extra = [f"<a href='{f}'>{f}</a>" for f in ("film-square.mp4", "film-16x9.mp4") if (CUT / f).exists()]
    films = f"<p>The {' and '.join(extra)} {'are' if len(extra) > 1 else 'is'} the same film for the feed or a wide screen.</p>" if extra else ""
    clips = _env.read_json(_env.b("clips.json")) or {}
    put(CUT / "review.html", PAGE.format(title=esc(f"{'@' + handle + ' · ' if handle else ''}{sub.get('subject')}"), caption=esc(cap),
                                         bg=bg, ink=ink, accent=accent, posts=posts, films=films,
                                         looks=looks(CUT, film["board"]), made=made_said(sub, fx, board, music, clips)))
    res = qa.Checks()
    if qa.report(res, "gate.json", qa.gate_checks(res, run)) != 0:
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        # the last line names what failed and no film, so a reply copied from it never points at an unready reel
        print("not delivered: the gate failed on " + ", ".join(r[0] for r in res if r[1] is False))
        return 1
    publish(CUT, OUT)
    made = [n for n in ("film.mp4", "film-square.mp4", "film-16x9.mp4", "cover.png", "stories/", "then-now.png") if (OUT / n).exists()]
    print(f"delivered: {OUT}/ " + ", ".join(made + ["caption.md", "review.html"]) + f"; the making-of: {_env.b('brief.md')}")
    print(Path(os.path.relpath(OUT / "film.mp4")).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
