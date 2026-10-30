#!/usr/bin/env python3
"""Movement 5, last step: write out/caption.md, out/review.html and brief.md, then run the gate.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/deliver.py

caption.md is caption.md in the run's folder when the agent wrote one in the person's voice, otherwise a short
caption drafted from taste.json in their register (their case, their length, their own hashtags). Either way the
caption states the count of places from places.json ("11 places"); a caption of theirs that states none gets one
line with the count on top. brief.md opens with the places table (every place in visit order, its dates, visits,
posts and where it was found), then the photographs each visit shows and where each came from,
where the material came from (every door tried, open or closed), what the run assumed, the look and who picked it,
where the music came from, how the film was rendered, and the critics' scores of the cut against the bar (a cut
under the bar is still the delivered cut, and brief.md says so); it is the run's record and sits in the run's
folder, beside out/, never in it. review.html is the film's page for the person: the reel with the story card as its
cover, the caption to copy, the posted image and the story card, the 16:9 and square films, the two looks not
picked (cut from out/boards.png) with how to ask for one, and how it was made in plain words. It carries no score.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong. The page
carries a banner saying the gate has not passed until the gate passes, so a deliver cut short never leaves a page that
looks ready, and every file reaches out/ by a rename. On a passing gate its last line is the reel's path from the
project's root (build/<run>/out/film.mp4), the path the reply names first; on a
failed gate it is "not ready: the gate failed on" and the failing checks, and no path.
"""
import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import look  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(taste, places):
    """Their caption, or one drafted in their register; both state the count of places."""
    reg = taste.get("register") or {}
    year, n = taste.get("year"), len(places)
    head = f"{year} in {n} places"
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        text = own.read_text().strip()
        if not qa.caption_counts(text):
            text = (head.lower() if reg.get("lowercase") else head) + "\n" + text
        return text + "\n"
    names = [p["name"] for p in places]
    lines = [head]
    if len(names) >= 2:
        lines.append(", ".join(names[:-1]) + " and " + names[-1])
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#travelmap", f"#{year}inplaces"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def place_rows(pl):
    """The places table: one row per place in visit order."""
    rows = ["| # | place | country | when | visits | photos | found by |", "|---|---|---|---|---|---|---|"]
    for i, p in enumerate(pl.get("places") or [], 1):
        when = p.get("first") if p.get("first") == p.get("last") else f"{p.get('first')} to {p.get('last')}"
        rows.append(f"| {i} | {p['name']} | {p.get('country') or ''} | {when} | {p.get('visits', 1)} | {p.get('rows', 0)} | "
                    f"{(p.get('source') or '').replace('|', '/')} |")
    return rows


def title(handle, year, n):
    """The brief's and the review page's title: their handle, the year and the count of places; no handle, no handle."""
    return (f"@{handle} · " if handle else "") + f"{year} in {n} places"


def brief(lib, taste, pl, win, music, engine, cuts, photos):
    handle, year = lib.get("handle") or taste.get("handle"), lib.get("year") or taste.get("year")
    n = len(pl.get("places") or [])
    L = [f"# {title(handle, year, n)}: how this was made", "", "## the places", ""] + place_rows(pl)
    L += ["", "## the photographs", "", "| visit | photograph | from |", "|---|---|---|"]
    L += [f"| {r['place']} {r['n']} | {r['file']} | {r.get('source', '')} |" for r in photos]
    L += ["", f"{n} places, in the order they were visited."]
    if pl.get("unplaced"):
        L.append(f"{pl['unplaced']} posts and stories name no place and carry no geotag, so they are on no place.")
    for m in pl.get("mentioned") or []:
        L.append(f"- Named but not placed: {m.get('name') if isinstance(m, dict) else m}.")
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in (lib.get("assumptions") or []) + (pl.get("assumptions") or [])]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("travel") or (taste.get("palette") or {}).get("year", [])))
          + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the look", ""]
    st = win.get("board")
    by = (f"picked by taste: {win['why']}" if win.get("by") == "taste" and win.get("why") else
          "picked by you" if win.get("by") == "person" else "the vote's pick")
    L.append(f"- {st}, {look.sentence(st)} ({by}; the swap test {'passed' if win.get('swap_passed') else 'not passed'}).")
    others = [s for s in storyboard.styles() if s != st]
    L.append(f"- Not picked: {', '.join(others)}; out/boards.png shows all three.")
    L += ["", "## the music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    cut = _env.read_json("film.json") or {}
    L += ["", "## how the film was made", ""]
    if cut.get("seconds"):
        L.append(f"- It runs {storyboard.length_said(cut['seconds'], taste.get('seconds'), len((board_of(st).get('route') or {}).get('cards') or []))}.")
    L += ["- Rendered with the kit's Remotion project at 1080x1920, 1920x1080 and 1080x1080, 30 fps, H.264, "
          f"{'on the graphics card' if engine.get('card') else 'on the processor'}, in {engine.get('seconds')} s."]
    L += ["", "## the critics on the finished film", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        cr = c.get("critics") or {}
        for who, e in cr.items():
            s = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {'unread' if v is None else v}" for k, v in s.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    v = _env.read_json("verdict.json") or {}
    if v.get("verdict") == "ship":
        L.append(f"- At the bar: mean {v.get('mean')}, lowest {v.get('worst')} (the bar is a mean of {vote.MEAN} and no rule under {vote.BAR}).")
    elif v:
        L.append(f"- Under the bar: mean {v.get('mean')}, lowest {v.get('worst')} (the bar is a mean of {vote.MEAN} and no rule under "
                 f"{vote.BAR}). This is the best cut the run made, delivered with these scores.")
    return "\n".join(L) + "\n"


def board_of(style):
    return _env.read_json(f"storyboards/{style}/board-reel.json") or {}


def looks_html(st):
    """The two looks not picked, each cut from out/boards.png (the three sheets stacked, first to third), with the words
    a person answers with."""
    styles = list(storyboard.styles())
    if st not in styles or not (OUT / "boards.png").exists():
        return ""
    from PIL import Image
    n = len(styles)
    w, h = Image.open(OUT / "boards.png").size
    say = [f"'make the {storyboard.LOOKS[i].split()[0].lower()} one'" for i, s in enumerate(styles) if s != st]
    tiles = "".join(f"<figure><div class='look' style='aspect-ratio:{w} / {h / n:.1f}'><img src='boards.png' alt='{esc(storyboard.LOOKS[i])}' "
                    f"style='transform:translateY(-{100 * i / n:.4f}%)'></div><figcaption>{esc(storyboard.LOOKS[i])}: "
                    f"{esc(look.sentence(s))}</figcaption></figure>" for i, s in enumerate(styles) if s != st)
    return (f"<h2>Prefer another look?</h2><p>Say {' or '.join(say)} and the film is made again in that look.</p>"
            f"<div class='looks'>{tiles}</div>")


def made_html(pl, photos, music, cut, st, taste):
    """How the film was made, in plain words."""
    n = len(pl.get("places") or [])
    said = [f"The {n} places come from your own posts and their geotags, in the order you went.",
            f"Every photograph is one of yours, one for each stop ({len({p['file'] for p in photos})} in all).",
            f"The look: {esc(look.sentence(st))}"]
    said.append(f"The music is {esc(music['origin'])}, and every cut lands on its beat." if music.get("file")
                else "There is no music on it; add a sound when you post.")
    if cut.get("seconds"):
        said.append(f"It runs {esc(storyboard.length_said(cut['seconds'], taste.get('seconds'), len((board_of(st).get('route') or {}).get('cards') or [])))}.")
    return "<h2>How it was made</h2><p>" + " ".join(said) + "</p>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.cards{{display:flex;gap:14px;align-items:start}} .cards a{{display:block}}
.cards img{{height:300px;border-radius:8px;display:block}}
.films{{display:flex;gap:18px;align-items:start}} .films video{{width:auto;max-width:560px;max-height:420px}}
.looks{{display:flex;gap:18px}} .looks figure{{margin:0;flex:1}} figcaption{{opacity:.75;margin-top:8px}}
.look{{overflow:hidden;border-radius:10px}} .look img{{width:100%;display:block}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your year in places as a film and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" poster="story.png" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>To post and to share</h2><div class="cards">{cards}</div></div></div>
<h2>For a feed or a screen</h2><div class="films">{films}</div>
{looks}
{made}
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter_run()
    _env.need("PIL")
    # the lock holds while deliver writes out/, so no render changes the films under its page, and the gate runs in
    # this process, every check's process started through run.spawn
    with studio.lock("deliver") as run:
        return deliver(run)


def deliver(run):
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win):
        sys.exit("library.json, taste.json or winner.json is missing; run the earlier movements first")
    music = _env.read_json("music.json") or {}
    engine = _env.read_json("engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    pl = _env.read_json("places.json") or {}
    if not pl.get("places"):
        sys.exit("places.json is missing or has no places; run research.py first")
    photos = (_env.read_json("public/photos.json") or {}).get("photos") or []
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, pl["places"])
    _env.write_text(OUT / "review.html",
                    PAGE.format(title="", banner="<div class='banner'><b>Not ready to post.</b> qa.py gate has not passed.</div>",
                                caption="", bg="#141212", ink="#f4efe8", accent="#e6b26d", cards="", films="", looks="", made=""))
    _env.write_text(OUT / "caption.md", cap)
    _env.write_text(Path("brief.md"), brief(lib, taste, pl, win, music, engine, cuts, photos))
    pal = (taste.get("palette") or {}).get("travel") or (taste.get("palette") or {}).get("year") or []
    colors = (board_of(win.get("board")).get("system") or {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle, year = lib.get("handle"), lib.get("year")
    cards = "".join(f"<a href='{n}'><img src='{n}' alt='{a}'></a>" for n, a in (("post.png", "the posted image"), ("story.png", "the story card")))
    films = ("<video src='film-16x9.mp4' controls playsinline loop preload='metadata'></video>"
             "<video src='film-square.mp4' poster='post.png' controls playsinline loop></video>")

    def page(banner):
        return PAGE.format(title=esc(title(handle, year, len(pl["places"]))), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, cards=cards, films=films, looks=looks_html(win.get("board")),
                           made=made_html(pl, photos, music, _env.read_json("film.json") or {}, win.get("board"), taste))

    res, f = qa.gate_checks(run)
    if qa.report(res, "qa/gate.json", f, "GATE"):
        items = "".join(f"<li>{esc(name)} {esc(detail)}</li>" for name, ok, detail, *_ in res if ok is False)
        _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        print("not ready: the gate failed on " + ", ".join(dict.fromkeys(name for name, ok, *_ in res if ok is False)))
        return 1
    _env.write_text(OUT / "review.html", page(""))
    print("delivered: " + ", ".join(f"out/{n}" for n in sorted(qa.DELIVERED)) + "; the record is brief.md")
    print(Path(os.path.relpath(Path.cwd().resolve() / OUT / "film.mp4", _env.HOME)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
