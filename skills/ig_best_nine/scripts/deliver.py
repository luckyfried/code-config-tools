#!/usr/bin/env python3
"""Movement 6, last step: write the run's out/caption.md, out/review.html and the run's brief.md, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py --run R

caption.md is the run's caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from taste.json in their register (their case, their length, their own hashtags). review.html is the person's page:
it plays the reel (and the square and wide films when they asked for them), shows the best-nine image to post, the
story card when it was asked for and the caption, then the other two looks with the line that makes one of them, and
how the film was made in plain words. It names no rule and no score. out/ holds those and nothing else.
brief.md stays in the run folder, beside out/: the nine with their numbers and why each worked, every door tried,
what the run assumed, the three looks and who picked the one made and why, the panel's totals, which look the review
page calls the first and the second, where the music came from, how the film was rendered, the clips, and the critics'
scores of the cut against the bar (mean 4.5 or more, no criterion under 4), saying when the cut was delivered under it.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong, and until
the gate has passed it carries one saying so. On a passing gate it prints the ranking for the reply (what ranked the
nine, or that they are the most recent and why, the nine first to ninth, and the one the reel ends on), and the last
line printed is the reel's path from the workspace root (build/<run>/out/film.mp4), the path the reply to the person
names first; on a failed gate the last line is "not delivered: the gate failed on " and the failing checks' names,
and no path.
"""
import argparse
import html
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402
import story  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")


def idea(style):
    """The look in one plain sentence (styles/catalog.md)."""
    return storyboard.sentence(style)


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


def clip(caption, most=80):
    """A caption on one line, cut at the last whole word inside `most` characters, with an ellipsis when it was cut."""
    said = " ".join((caption or "").split())
    if len(said) <= most:
        return said
    return said[:most].rsplit(" ", 1)[0].rstrip(",.:;") + "…"


def ranking():
    """The lines the reply carries about the nine: what ranked them (or that they are the most recent, and why), each
    first to ninth by its day and its caption, and the order the reel and the grid show them in."""
    st = _env.read_json("stats.json") or {}
    top = st.get("top_nine") or []
    if not top:
        return []
    by = st.get("top_ranked_by")
    out = ["the nine are the most recent posts, newest first, because the file carries no likes, comments or saves:" if by == "recent"
           else f"the nine, first to ninth, ranked by {by}:"]
    out += [f"{t['rank']}. {t.get('date_label') or t.get('date')}, {clip(t.get('caption')) or 'a photograph without a caption'}" for t in top]
    last = story.film_order(storyboard.Run().posts)[-1]
    return out + [f"the reel shows them one by one and ends on {last['date']}, {clip(last['caption']) or 'a photograph without a caption'}, "
                  "the one the film builds to; the closing grid holds all nine"]


def nine_rows():
    st = _env.read_json("stats.json") or {}
    # the agent's own reasons in taste.json, else the ones research drafted
    why = {x["rank"]: x["why"] for src in ("research.json", "taste.json") for x in (_env.read_json(src) or {}).get("nine") or [] if x.get("why")}
    rows = [f"Ranked by {st.get('top_ranked_by')}.", "", "| # | posted | likes | comments | saves | why it worked |", "|---|---|---|---|---|---|"]
    for t in st.get("top_nine") or []:
        w = why.get(t["rank"]) or ""
        likes, comments, saves = ("-" if t.get(k) is None else t[k] for k in ("likes", "comments", "saves"))
        rows.append(f"| {t['rank']} | {t.get('date_label') or t.get('date')} ({t.get('kind')}) | {likes} | {comments} | {saves} | "
                    f"{w.replace('|', '/')} |")
    ten = st.get("tenth") or {}
    if ten.get("likes") is not None:
        rows += ["", f"The tenth had {ten['likes']} likes, {ten.get('gap')} fewer than the ninth."]
    return rows


def brief(lib, taste, win, music, film, report, cuts):
    handle, year = lib.get("handle") or taste.get("handle"), lib.get("year") or taste.get("year")
    L = [f"# {'@' + handle + ', ' if handle else ''}best nine of {year}: how this was made", "",
         "Open [out/review.html](out/review.html): it plays the film and shows everything to post with it, on one page.", "",
         "## the nine", ""] + nine_rows()
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
          "## the three looks and the one made", ""]
    looks = win.get("looks") or vote.looks()
    tot = win.get("totals") or {}
    for x, t in zip("ABC", looks):
        score = f", the panel's total {tot[t]} of {len(vote.PANEL) * len(vote.CRITERIA) * 5}" if t in tot else ""
        L.append(f"- {x}. {vote.name_of(t)} ({t}{score}): {idea(t)}")
    who = {"the person": "you picked it", "taste": "picked by your taste, since nothing could be asked",
           "the panel": "the panel's pick"}.get(win.get("picked_by"), "picked")
    L.append(f"- Made in {vote.name_of(win['board'])}: {who}" + (f". {win['why']}" if win.get("why") else "") + ".")
    others = [t for t in looks if t != win["board"]]
    if others:
        L.append("- The review page shows the other two: " + ", ".join(f"the {n} one is {vote.name_of(t)} ({t})" for n, t in zip(("first", "second"), others))
                 + f". \"Make the second one\" is vote.py pick --board {others[-1]}, then the sequence from music.py find in this run.")
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {film.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", "",
          f"- The {film.get('style')} look's storyboard, {film.get('seconds')} s, {len(film.get('cuts') or [])} cuts, rendered by "
          f"the kit's studio at 30 fps at {sizes(report)}. Each shape is laid out on its own; nothing is scaled to fit.",
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
        for who_, e in (c.get("critics") or {}).items():
            sc = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who_, who_)}: " + ", ".join(f"{k} {v}" for k, v in sc.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts and not vote.problems(cuts[-1], vote.CUT_PANEL, ["film"]):
        mean, worst, ship = vote.at_bar(cuts[-1])
        L.append(f"- Mean {mean} of 5 against the bar of {vote.BAR}, lowest {worst[0]} ({worst[1]}): "
                 + ("at the bar." if ship else "under the bar after the one fix; this is the best cut, delivered with these scores."))
    return "\n".join(L) + "\n"


def sizes(report):
    """The films the render made, in words: the reel, and the square and wide ones when the person asked for them."""
    of = {"reel": "1080x1920 for reels", "square": "1080x1080 for the feed", "wide": "1920x1080 for anywhere wide"}
    got = [of[f] for f in of if f in set((report.get("made") or {}).get("formats") or ["reel"])]
    return got[0] if len(got) == 1 else ", ".join(got[:-1]) + " and " + got[-1]


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
.posts img,.looks img{{width:100%;border-radius:8px;display:block}}
.looks{{display:grid;grid-template-columns:1fr 1fr;gap:24px}} .looks p{{margin:8px 0 0}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your best-nine film, the best-nine image and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p>{how}</p></div></div>
{films}
<h2>{stills}</h2>{posts}
{looks}
</main></body></html>
"""


def how(win, music, film, report):
    """How the film was made, in plain words for the person."""
    st = _env.read_json("stats.json") or {}
    by = st.get("top_ranked_by")
    nine = ("These are your nine most recent posts, because your download carries no likes, comments or saves." if by == "recent"
            else f"These are your nine most-loved posts of the year, ranked by {by}.")
    track = ("The music is the track you chose." if music.get("file") and not music.get("recipe") else
             "The music was composed for this film on real instruments, and every cut lands on its beat." if music.get("file") else
             "The film is silent; add a sound when you post.")
    return " ".join([nine, f"The film shows them one by one in the {vote.name_of(win['board'])} look ({idea(win['board'])[:1].lower() + idea(win['board'])[1:].rstrip('.')})"
                     .rstrip(".") + ", and ends on all nine as the grid you post.", track,
                     f"It runs {round(film.get('seconds') or 0)} seconds, and each shape is laid out on its own, never stretched to fit."])


def others_html(win):
    """The other two looks, each its sheet and its name, and the line that makes one of them."""
    looks = win.get("looks") or vote.looks()
    others = [t for t in looks if t != win["board"]]
    if not others:
        return ""
    cells = "".join(f"<div><img src='../storyboards/{esc(t)}/sheet.png' alt=''><p><b>{n}. {esc(vote.name_of(t))}</b>: {esc(idea(t))}</p></div>"
                    for n, t in zip(("1", "2"), others))
    return (f"<h2>The other two looks</h2><div class='looks'>{cells}</div>"
            f"<p>{esc('Prefer another look? Say ')}<b>{esc(chr(39) + 'make the second one' + chr(39))}</b>{esc(' and that one is made for you.')}</p>")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _env.run_arg(ap)
    where = _env.enter_run(ap.parse_args().run)
    # the run's lock from the first read to the last write: a film render never moves files into out/ while the page
    # and the gate read them
    with studio.lock("deliver") as run:
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
        written = brief(lib, taste, win, music, film, report, cuts)
        colors = (_env.read_json(storyboard.BOARDS / win["board"] / "board-reel.json") or {})["system"]["colors"]
        bg, ink, accent = colors["bg"], colors["ink"], colors["accent"]
        handle, year = lib.get("handle"), lib.get("year")
        # the story card and the other films only when the render made them, as the person asked for them
        shown = [p for p in ("best-nine.png", "story.png") if (OUT / p).exists()]
        posts = gallery(shown, "posts")
        stills = "The best-nine image and the story card" if "story.png" in shown else "The best-nine image"
        extra = "".join(f"<video src='{f}' controls playsinline loop></video>" for f in ("film-square.mp4", "film-wide.mp4") if (OUT / f).exists())
        films = f"<h2>The same film for the feed and for wide screens</h2><div class='shapes'>{extra}</div>" if extra else ""

        def page(banner):
            return PAGE.format(title=esc(f"{'@' + handle + ' · ' if handle else ''}best nine {year}"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                               accent=accent, posts=posts, films=films, stills=stills, how=esc(how(win, music, film, report)),
                               looks=others_html(win))

        # the page says it is not ready until the gate passes, so a deliver stopped partway never leaves out/ looking
        # delivered; every file moves in by rename, whole
        _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>"))
        # out/ is only what is posted and its page; the brief, with the scores, stays in the run beside it
        shutil.rmtree(OUT / "storyboards", ignore_errors=True)
        (OUT / "brief.md").unlink(missing_ok=True)
        _env.write_text(OUT / "caption.md", cap)
        _env.write_text("brief.md", written)
        # the gate runs here, so every process it starts holds this lock through run.spawn
        res, cut = qa.gate_checks(run)
        if qa.report(res, "qa/gate.json", cut, "GATE") == 0:
            _env.write_text(OUT / "review.html", page(""))
        else:
            items = "".join(f"<li>{esc(f'{name} {detail}')}</li>" for name, ok, detail, *_ in res if ok is False)
            _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
            print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
            # the last line names what failed and no film, so a reply copied from it never points at an unready reel
            print("not delivered: the gate failed on " + ", ".join(r[0] for r in res if r[1] is False))
            return 1
        made = [n for n in ("film.mp4", "film-square.mp4", "film-wide.mp4", "best-nine.png", "story.png") if (OUT / n).exists()]
        for line in ranking():
            print(line)
        print(f"delivered to {where / 'out'}: " + ", ".join(made + ["caption.md", "review.html"]) + f"; the brief is {where / 'brief.md'}")
        print(Path(os.path.relpath(where / OUT / "film.mp4", _env.WORKSPACE.resolve())).as_posix())
        return 0


if __name__ == "__main__":
    sys.exit(main())
