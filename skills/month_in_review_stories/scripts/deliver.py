#!/usr/bin/env python3
"""Movement 5, last step: write caption.md and review.html into the run's out/ and brief.md and template.json into the
run, run the gate, and on a green gate copy the run's out/ to the workspace's out/, its engine.json to build/engine.json
and its template.json to build/template.json.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is the run's caption.md when the agent wrote one in the person's voice, else a short caption drafted from
taste.json in their register (their case, no '!' when they use none, their own hashtags). brief.md opens with the
month's moments (each one's day, kind, place and their words), then lists the cards in posting order, where the material came
from (every door tried, open or closed), what the run assumed, the vote, where the music came from, the clips (made
or stood in for), which engine rendered the stories, and the critics' scores of the cut. template.json is what keeps
next month matching: the style, the type, the palette, the devices on each card, the reel's beats and the axis rule
(one card a moment, each in its post's cell of the wall of the month's posts); next month's storyboard.py draft reads it
from build/template.json. brief.md carries the vote: the three looks with their means, who picked the one rendered, and
the critics' scores of the cut against the bar (a cut under the bar is delivered as the best one, its scores stated
there and nowhere else). review.html is the person's page, written to them: it opens on the reel, large, with
out/cover.png for its poster, then the caption, the series when they asked for it as one video, every card animated
beside its still, the other two looks (out/looks/, each its hook, a middle beat and its closer) with "Prefer another
look? Say 'make the second one'", and how it was made in plain words; it carries no score and no rule. out/ holds the
films, the cover, the cards, the three looks (boards.png, looks/), caption.md and review.html, and nothing else: the
storyboards, brief.md and template.json stay in the build.
deliver holds the run's render lock (the one film.py render takes) from the moment it enters the run to its last write,
so the two never run at once. The gate runs in deliver's own process, and every process it starts goes through the
lock's spawn, so each holds the lock too.
Exit 0 only when qa.py gate passes, and the gate fails only on a measured check or a missing record, never on a score;
on a failed gate the last line names the failing checks and no film, the page carries a red banner naming what is wrong and nothing
is copied to the workspace's out/. Until the gate has passed the page carries a banner saying so, and every file moves
into out/ by rename, whole, so a deliver stopped partway never leaves out/ looking delivered. The workspace's out/
is never moved away: each file is renamed into it, whole, and its ready page is written last. delivered.json goes
first, before either out/ changes, and is written again only once the workspace's out/ stands. The last line a green
deliver prints is the delivered reel, the run's out/film.mp4, as a path from the workspace root (for example
build/20261026T005754Z/out/film.mp4): the path the reply names.
"""
import html
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402
from compose import look, month as month_words, style  # noqa: E402

DEVICES = {"bands": "their photograph on a band, the words on the ground", "rules": "the line", "strips": "a plate sized to the words",
           "bursts": "dust where the line lands"}


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(run, taste, n):
    own = run / "caption.md"
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    month = ((taste.get("month") or {}).get("name") or "this month").lower()
    lines = [f"my {month}, in {month_words.number(n)} stories", "which one was your favorite?"]
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    if not reg.get("exclamations"):
        body = body.replace("!", ".")
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#monthinreview", f"#{month}recap"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def template(board):
    """Next month's look and shape: the palette as a list and as its roles, the font, the numbering, the month, the
    type files, every card's devices and the reel; compose/look.py reads it back as a look."""
    s = board["system"]
    lk = board.get("look") or {}
    colors = {k: v for k, v in s["colors"].items() if k != "swatches"}
    return {"series": "month_in_review_stories", "style": board["style"], "bpm": board["bpm"], "month": board.get("month"),
            "palette": list(dict.fromkeys(colors[k] for k in ("bg", "ink", "accent", "accent2") if k in colors)),
            "colors": colors, "font": lk.get("font_used"), "numbering": lk.get("numbering"),
            "type": {k: s.get(k) for k in ("display", "text")},
            "finish": s.get("finish"),
            "cards": [{"n": i + 1, "role": c["id"], "title": c["idea"],
                       "devices": [v for k, v in DEVICES.items() if c.get(k)],
                       "shots": len(c["shots"]), "seconds": 15} for i, c in enumerate(board["beats"])],
            "reel": {"seconds": round(board["reel"]["frames"] / board["reel"]["fps"], 2), "beats": [b["key"] for b in board["reel"]["beats"]],
                     "idea": "the month's diary, each moment shown once: its peak moment opens, then each other moment in date order, "
                             "its photograph with their words beside it, set into its post's cell, until the camera pulls back "
                             "to the wall of every post with a photograph and the closing page comes over it"},
            "axis": "one card a moment, three or four of them, in date order; each moment sits in its post's cell of a wall that "
                    "holds every one of the month's posts with a photograph, each with its day beneath it",
            "format": board["format"]}


def moment_rows(run, board, taste):
    """One row a moment: its day, what happened as the agent named it in taste.json, its photograph, its place and the
    line it says on screen."""
    posts = {p["photo"]: p for p in (_env.read_json(run / "month.json") or {}).get("posts") or [] if p.get("photo")}
    what = {m.get("photo"): m.get("what") for m in taste.get("moments") or []}
    rows = ["| day | the moment | photograph | where | on screen |", "|---|---|---|---|---|"]

    def cell(v):
        return (v or "").replace("|", "/")

    for x in board.get("moments") or []:
        p = posts.get(x.get("photo")) or {}
        rows.append(f"| {x['day']}{' (the peak)' if x.get('peak') else ''} | {cell(what.get(x.get('photo')) or p.get('type'))} | "
                    f"{Path(x.get('photo') or '').name} | {cell(p.get('place'))} | {cell(x.get('line')) or '(no words)'} |")
    return rows


def clip_rows(run):
    out = []
    for k, x in ((_env.read_json(run / "clips.json") or {}).get("clips") or {}).items():
        out.append(f"- clip {k} ({x['beat']}): " + ("made by the video model" if x["status"] == "generated" else
                                                     f"stood in for ({x.get('why')}): {x.get('stand_in')}"))
    return out or ["- None: the cards are type, because no photographs or clips came with these posts."]


def opener(board):
    """The handle a title opens with, when their data carries one."""
    return f"{board['handle']}, " if board.get("handle") else ""


def brief(run, lib, taste, win, board, cards, music, engine, cuts):
    mo = lib.get("month") or {}
    lk = board.get("look") or {}
    L = [f"# {opener(board)}{mo.get('name', '').lower()} {mo.get('year', '')} in review: how this was made", "",
         "## the look", "", f"- From {look.source(lk, 'your')}: " + ", ".join(f"{k} {v}" for k, v in (lk.get("colors") or {}).items())
         + f"; type in {lk.get('font_used')}" + (f", numbered {lk.get('numbering')}" if lk.get("given") else "") + ".",
         *([f"- {lk['font_note'][0].upper()}{lk['font_note'][1:]}."] if lk.get("font_note") else []), "",
         "## the month's moments", ""] + moment_rows(run, board, taste)
    L += ["", f"## the series: {len(cards)} story cards, post them in this order", "", "| card | idea | animated | still |", "|---|---|---|---|"]
    idea = {b["id"]: b["idea"] for b in board["beats"]}
    for c in cards:
        L.append(f"| {c['n']:02d} | {idea.get(c['id'], c['id'])} | {c['mp4'][4:]} | {c['png'][4:]} |")
    secs = board["reel"]["frames"] / board["reel"]["fps"]
    series = bool((board.get("ask") or {}).get("series"))
    L += ["", f"film.mp4 is the reel, {secs:.0f} s: your month's diary, each moment with your words beside it, then the "
          "wall of your month's posts and the closing page. " + ("series.mp4 is all the cards in one film. " if series else "")
          + "Every card is 15 s at 1080x1920 with a still. build/template.json keeps the look, type, palette and devices, so next month's series matches.", "",
          "## where your month came from", ""]
    L += [f"- {door.replace('_', ' ')}: {state}" for door, state in (lib.get("doors") or {}).items()]
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## the three looks and the vote", ""]
    means = win.get("means") or {}
    L += [f"- {i + 1}. {s}: a mean of {means.get(s)} of 5 over the rules the panel read" + (" (rendered)" if s == board["style"] else "")
          for i, s in enumerate(win.get("order") or [board["style"]])]
    L.append(f"- {board['style']} ({board.get('name')}) was picked by {win.get('picked_by') or 'the panel'}.")
    if win.get("follows"):
        L.append(f"- {win['follows']} follows last month's template, so the series matches.")
    L += ["", "## music", "",
          f"- {music.get('origin')}.", "- The reel's sounds sit under the music, one where each beat lands; the picture and the "
          "music stop together; every video is brought to -14 LUFS.", "", "## clips", ""] + clip_rows(run) + ["",
          "## how the stories were made", "",
          f"- Drawn by the kit's compositions ({engine.get('compositions')}) in a headless browser: "
          "1080x1920, 30 fps, H.264, AAC; the reel, " + ("the series, " if series else "") + "every card and every still from one storyboard.", "",
          "## the critics on the finished stories", ""]
    for c in cuts:
        for who, e in (c.get("critics") or {}).items():
            s = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in s.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts:
        try:
            sc = vote.standing(cuts[-1])
            ok, mean, said = vote.against_bar(sc)
            L.append(f"- At the bar: {said}." if ok else f"- Delivered as the best cut, {short_of(sc, mean)}: {said}.")
        except (KeyError, TypeError):
            L.append("- The latest round is not complete.")
    else:
        L.append("- Not scored yet.")
    return "\n".join(L) + "\n"


def short_of(sc, mean):
    """Why a round is not at the bar, in words: the rules under it or the mean under it, and the rules nobody in the
    session could read."""
    under = [k for k, v in sc.items() if v != vote.NOT_READ and v < vote.BAR["least"]]
    unread = [k for k, v in sc.items() if v == vote.NOT_READ]
    why = ([f"under the bar on {', '.join(under)}"] if under
           else [f"the mean {mean:.2f} under {vote.BAR['mean']}"] if mean < vote.BAR["mean"] else [])
    return "; ".join(why + ([f"{', '.join(unread)} not read in the session"] if unread else []))


def looks(run, win, board, out):
    """The other two looks as the page shows them: out/looks/<n>-<style>.png, each its hook, a middle beat and its
    closer side by side, from the stills storyboard.py sheets made; [(n, style, file)]."""
    from PIL import Image
    shown = []
    d = out / "looks"
    shutil.rmtree(d, ignore_errors=True)
    for n, s in enumerate(win.get("order") or [], 1):
        stills = [run / "storyboards" / s / "boards" / f"{k}.png" for k in ("hook", "middle", "closer")]
        if s == board["style"] or not all(f.exists() for f in stills):
            continue
        ims = [Image.open(f).convert("RGB") for f in stills]
        w, h = ims[0].size
        strip = Image.new("RGB", (3 * w + 2 * 12, h), "white")
        for i, im in enumerate(ims):
            strip.paste(im, (i * (w + 12), 0))
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{n}-{s}.png"
        strip.save(f)
        shown.append((n, s, f"looks/{f.name}"))
    return shown


ORDINAL = {1: "first", 2: "second", 3: "third"}


def made_how(board, music, cards):
    """How it was made, in plain words, to the person."""
    c = style.card(board["style"])
    recipe = music.get("recipe")
    said = [f"Made from your own posts: {len(board.get('moments') or [])} moments of your month, in your words, one story card each.",
            f"The look is {c['name'].lower()}: {style.sentence(board['style'])[0].lower()}{style.sentence(board['style'])[1:]}"]
    if recipe:
        said.append(f"The music was written for this film, at {music.get('bpm'):g} beats a minute, and every cut lands on its beat.")
    elif music.get("origin"):
        said.append("The music is the track you gave, and every cut lands on a beat of the film.")
    said.append(f"The reel, the {len(cards)} cards and the cover were drawn from your photographs.")
    return " ".join(said)


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1240px;margin:0 auto;padding:36px 24px 72px}}
.cover{{display:grid;grid-template-columns:minmax(320px,460px) 1fr;gap:36px;align-items:start}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
video{{width:100%;border-radius:14px;background:#000;display:block}}
.cards{{display:grid;grid-template-columns:repeat({ncards},1fr);gap:16px}}
.card h3{{margin:8px 0 6px;font-size:15px}} .look img{{width:100%;border-radius:10px;display:block}} .card img{{width:100%;border-radius:10px;display:block;margin-top:8px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
{banner}
<div class="cover"><video src="film.mp4" poster="cover.png" controls playsinline></video>
<div><h1>{title}</h1><p class="sub">Your month as a reel, a series of stories, each animated and still, and a caption, ready to post.</p>
<h2>Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<p><a href="cover.png">The cover</a></p></div></div>
{series}
<h2>The cards</h2><p>Post them in order. Each card comes animated and still.</p><div class="cards">{cards}</div>
{looks}
<h2>How it was made</h2><p>{how}</p>
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    run = _env.run()
    # the run's lock, the one film.py render takes, is held from here through the last write, and the gate runs under it
    with studio.lock(run / "render", "deliver") as hold:
        return deliver(run, hold)


def deliver(run, hold):
    # delivered.json vouches for the out/ folders below, so it goes before either changes and comes back once both stand
    (run / "delivered.json").unlink(missing_ok=True)
    lib, taste, win = (_env.read_json(run / f) or {} for f in ("library.json", "taste.json", "winner.json"))
    board = _env.read_json(run / "film.json") or {}
    cards = (_env.read_json(run / "cards.json") or {}).get("cards") or []
    if not (lib and taste and win and board and cards):
        sys.exit(f"library.json, taste.json, winner.json, film.json or cards.json is missing in {run}; run the earlier movements first")
    music, engine = _env.read_json(run / "music.json") or {}, _env.read_json(run / "engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds(run)]
    out = run / "out"
    cap = caption(run, taste, len(cards))
    written = brief(run, lib, taste, win, board, cards, music, engine, cuts)
    colors = board["system"]["colors"]
    series = bool((board.get("ask") or {}).get("series"))
    mo = lib.get("month") or {}
    idea = {b["id"]: b["idea"] for b in board["beats"]}
    html_cards = "".join(f"<div class='card'><h3>{c['n']:02d} · {esc(idea.get(c['id'], c['id']))}</h3>"
                         f"<video src='{esc(c['mp4'][4:])}' controls playsinline loop muted></video>"
                         f"<a href='{esc(c['png'][4:])}'><img src='{esc(c['png'][4:])}' alt='' loading='lazy'></a></div>" for c in cards)

    def page(banner):
        return PAGE.format(title=esc(f"{opener(board).replace(', ', ' · ')}{mo.get('name', '').lower()} {mo.get('year', '')} in review"), banner=banner,
                           caption=esc(cap), bg=colors.get("bg", "#141212"), ink=colors.get("ink", "#f4efe8"),
                           accent=colors.get("accent", "#e6b26d"), cards=html_cards, ncards=len(cards), looks=html_looks,
                           how=esc(made_how(board, music, cards)),
                           series='<h2>The series</h2><div class="cards"><video src="series.mp4" controls playsinline loop></video></div>'
                           if series else "")

    # the page says it is not ready until the gate passes, and only a green gate replaces it
    out.mkdir(parents=True, exist_ok=True)
    others = looks(run, win, board, out)
    html_looks = ("<h2>Other looks</h2><p>Prefer another look? Say 'make the second one'.</p><div class='cards'>"
                  + "".join(f"<div class='look'><h3>The {ORDINAL[n]} one: {esc(style.card(s)['name'])}</h3>"
                            f"<img src='{esc(f)}' alt='' loading='lazy'></div>" for n, s, f in others) + "</div>") if others else ""
    _env.write_text(out / "review.html", page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>"))
    _env.write_text(out / "caption.md", cap)
    _env.write_text(run / "brief.md", written)
    _env.write_json(run / "template.json", template(board))
    shutil.rmtree(out / "storyboards", ignore_errors=True)
    c = qa.checks(run, True, hold.spawn)
    if qa.report(c, run / "qa" / "gate.json", True) != 0:
        items = "".join(f"<li>{esc(r['check'])}: {esc(r['detail'])}</li>" for r in c.rows if r["pass"] is False)
        _env.write_text(out / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        # the last line names what failed and no film, so a reply read from it never points at an unready film
        print(f"not delivered: the gate failed on {', '.join(r['check'] for r in c.rows if r['pass'] is False)}")
        return 1
    _env.write_text(out / "review.html", page(""))
    # the workspace's out/ stays: its ready page goes first, every file moves into it by rename, whole, the files the
    # run does not carry go, and the ready page comes back last
    ws_out = Path("out")
    (ws_out / "review.html").unlink(missing_ok=True)
    files = [f.relative_to(out) for f in sorted(out.rglob("*")) if f.is_file() and f.name != "review.html"]
    for rel in files:
        dst = ws_out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(f".{dst.name}.part")
        shutil.copyfile(out / rel, tmp)
        os.replace(tmp, dst)
    for f in [f for f in ws_out.rglob("*") if f.is_file() and f.relative_to(ws_out) not in files]:
        f.unlink()
    _env.write_text(ws_out / "review.html", (out / "review.html").read_text())
    _env.write_text(Path("build") / "engine.json", (run / "engine.json").read_text())
    _env.write_text(Path("build") / "template.json", (run / "template.json").read_text())
    _env.write_json(run / "delivered.json", {"run": run.name, "out": str(ws_out.resolve())})
    print(f"delivered: film.mp4, {len(cards)} cards (animated and still), {'series.mp4, ' if series else ''}caption.md and review.html in out/ "
          f"(the build, with brief.md, stays in {run}; next month's look is build/template.json)")
    if (board.get("look") or {}).get("font_note"):
        print(f"the type: {board['look']['font_note']}")
    print(os.path.relpath(run / "out" / "film.mp4"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
