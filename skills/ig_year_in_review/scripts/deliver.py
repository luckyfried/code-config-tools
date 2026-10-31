#!/usr/bin/env python3
"""Movement 6, last step: write out/caption.md, out/review.html and build/brief.md, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is build/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from build/taste.json in their register (their case, their length, their own hashtags). review.html is the film's
cover and the person's page: it opens on the film, its poster the hook's story card and the strip of the reel's frames
beside it (out/strip/, which film.py render makes), and shows the caption, the carousel, the story cards, the other two
looks (out/looks/, each look's sheet from storyboard.py sheets, numbered as in out/boards.png) with the line that picks
one, and how the film was made in plain words, on the look's ground in whichever of its two type colors (ink and paper)
reads on it. The page carries no score. out/ holds only what is posted, that page with its strip and the looks, and
out/boards.png.
brief.md is the working record and stays in build/: where the material came from (every door tried, open or closed),
the year month by month, what the run assumed, the three looks, the panel's scores of them and the pick, every clip and
whether it was generated or stood in for, where the music came from, how the film was rendered, and the critics' scores
of the cut against the bar (vote.BAR), with a line saying so when the delivered cut is under it.
deliver holds the run's lock (named deliver) from the moment it enters build/ through its last write, and runs the gate
(qa.py gate) in its own process under that lock, so every probe and detector the gate starts holds it. Exit 0 only
when the gate passes; on a failed gate the page carries a red banner naming what is wrong, and until the gate has
passed it carries one saying so. Every file reaches out/ whole, by rename. On a passing gate the last line printed
is the reel's path from the workspace root (out/film.mp4), the path the reply to the person names first; on a
failed gate it is "the gate failed: " and the failing checks' names, and no path.
"""
import html
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import palette  # noqa: E402
import qa  # noqa: E402
import style  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402

OUT = Path("../out")
ORDINAL = ("first", "second", "third")


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(taste, win):
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    places = taste.get("places") or []
    year = taste.get("year")
    lines = [f"{year}, month by month"]
    if len(places) >= 2:
        lines.append(", ".join(places[:-1]) + " and " + places[-1])
    lines.append("thank you for being here for all of it")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3] + ["#yearinreview"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    for cid, c in sorted(clips.items()):
        how = (f"made by the video model from {c.get('image')}" if c.get("status") == "generated"
               else f"stood in for ({c.get('why')}): the film makes {c.get('stand_in')}")
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def month_rows():
    rows = ["| month | the moment | their line |", "|---|---|---|"]
    board = _env.read_json(((_env.read_json("film.json") or {}).get("boards") or {}).get("reel", "")) or {}
    for m in (board.get("year") or {}).get("months") or []:
        rows.append(f"| {m['short']} | {m['scene'].replace('|', '/')} | {(m.get('text') or '').replace('|', '/')} |")
    return rows


def brief(lib, taste, win, clips, music, report, cuts):
    handle, year = lib.get("handle") or taste.get("handle"), lib.get("year") or taste.get("year")
    L = [f"# {'@' + handle + ', ' if handle else ''}{year} in review: how this was made", "", "## the year", ""] + month_rows()
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the three looks and the pick", ""]
    scored = _env.read_json("vote/scores.json") or {}
    for i, t in enumerate(looks()):
        tot = sum(sum((((scored.get("critics") or {}).get(c) or {}).get("boards") or {}).get(t, {}).get("scores", {}).get(k) or 0
                      for k in vote.CRITERIA) for c in vote.PANEL)
        L.append(f"- {i + 1}. {t}" + (f" (the panel: {tot} of {len(vote.PANEL) * len(vote.CRITERIA) * 5})" if tot else "")
                 + f": {style.sentence(t)}")
    L.append("")
    L.append(f"The film is look {win.get('board')}, " + ("the person's pick" if win.get("by") == "person" else "the panel's board")
             + (f": {win['why']}" if win.get("why") else "") + ("." if not win.get("why") or not win["why"].endswith(".") else ""))
    L += ["", "## the clips", ""]
    L += clip_rows(clips) if clips else ["The storyboard uses no clips."]
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    film = _env.read_json("film.json") or {}
    L += ["", "## how the film was made", "",
          f"- The {film.get('style')} storyboard, {film.get('seconds')} s, {len(film.get('cuts') or [])} cuts, rendered by the kit's "
          "studio in the browser at 1080x1920, 30 fps, H.264 with AAC sound; the carousel and story cards are the film's own frames at rest.",
          f"- Rendered{ {True: ' on the graphics card', False: ' on the processor'}.get(report.get('gpu'), '')} in {round(report.get('seconds') or 0)} s."]
    L += ["", "## the scores", "", f"The bar: a mean of {vote.BAR[0]} with no score under {vote.BAR[1]}.", ""]
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
        last = [v for e in (cuts[-1].get("critics") or {}).values()
                for v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).values() if isinstance(v, int)]
        if last:
            mean = round(sum(last) / len(last), 2)
            low = sorted({k for e in (cuts[-1].get("critics") or {}).values()
                          for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, int) and v < vote.BAR[1]})
            L.append(f"- Round {cuts[-1].get('round')}: mean {mean}, lowest {min(last)}. " + (
                "At the bar." if vote.at_bar(last) else "Under the bar: this is the best cut the one fix made, delivered as it is"
                + (f"; under {vote.BAR[1]} on " + ", ".join(low) if low else "") + "."))
    return "\n".join(L) + "\n"


def looks():
    return (_env.read_json("storyboards/boards.json") or {}).get("order") or []


def other_looks(won):
    """out/looks/: each look but the film's, its sheet numbered as in out/boards.png, and the page's block for them."""
    d = OUT / "looks"
    order = looks()
    shown = []
    for i, s in enumerate(order):
        src = Path("storyboards") / s / "sheet.png"
        if s != won and src.exists():
            d.mkdir(parents=True, exist_ok=True)
            dst = d / f"{i + 1}-{s}.png"
            tmp = dst.with_name(f".{dst.name}.part")
            tmp.write_bytes(src.read_bytes())
            os.replace(tmp, dst)
            shown.append((i, s, f"looks/{dst.name}"))
    keep = {Path(x[2]).name for x in shown}
    for p in d.glob("*.png") if d.is_dir() else []:
        if p.name not in keep:
            p.unlink()
    if not shown:
        return ""
    cards = "".join(f"<figure><img src='{esc(src)}' alt=''><figcaption><b>{i + 1}. {esc(style.card(s)['name'])}</b><br>"
                    f"{esc(style.sentence(s))}</figcaption></figure>" for i, s, src in shown)
    return (f"<div class='looks'>{cards}</div><p>Prefer another look? Say 'make the {ORDINAL[shown[0][0]]} one'.</p>")


def how_made(lib, win, film, music):
    """How the film was made, in plain words for the person."""
    n = len(((_env.read_json(film.get("boards", {}).get("reel", "")) or {}).get("year") or {}).get("months") or [])
    s = win.get("board")
    said = [f"We went through your {lib.get('year') or ''} posts and photos and took one photograph for each month you "
            "posted" + (f", {n} in all," if n else "") + " with your own words from them.",
            f"Three looks were drawn for them, and this film is {style.card(s)['name']}: {style.sentence(s)}"
            if s else "Three looks were drawn for them.",
            ("You picked it." if win.get("by") == "person" else f"It was picked to fit your taste: {win['why']}" if win.get("why")
             else "It was picked to fit your taste."),
            (f"The music was written for this look, {round(music['bpm'])} beats a minute, and every cut lands on a beat."
             if music.get("bpm") else "The film has no music; add a sound when you post."),
            f"The film runs {film['seconds']:g} seconds, and every card is a frame of it." if film.get("seconds") else ""]
    return "<p>" + " ".join(esc(x) for x in said if x) + "</p>"


def page_colors(colors):
    """The page's ground and its text: the look's bg, and of its two type colors (ink and paper) the one with
    the most contrast on it, so the text is never the ground's own color."""
    bg = colors.get("bg", "#141212")
    type_colors = [c for c in (colors.get("ink"), colors.get("paper")) if c] or ["#f4efe8"]
    return bg, max(type_colors, key=lambda c: palette.contrast(palette.hex_rgb(c), palette.hex_rgb(bg)))


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{text};font:16px/1.55 system-ui,sans-serif}} a{{color:inherit}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.strip{{display:grid;grid-template-columns:repeat(8,1fr);gap:8px;margin-top:28px}}
.strip img{{width:100%;aspect-ratio:9/16;border-radius:6px;display:block}}
@media (max-width:720px){{ .top{{grid-template-columns:1fr}} video{{width:100%}} .strip{{grid-template-columns:repeat(4,1fr)}} }}
.carousel{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
.stories{{display:grid;grid-template-columns:repeat(3,minmax(0,220px));gap:12px}}
.carousel img,.stories img{{width:100%;border-radius:8px;display:block}}
.looks{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}} .looks figure{{margin:0}}
.looks img{{width:100%;border-radius:8px;display:block}} .looks figcaption{{margin-top:8px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your film, ten carousel cards, three story cards and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" poster="stories/01-hook.png" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
{strip}</div></div>
<h2>Carousel</h2>{carousel}
<h2>Story cards</h2>{stories}
<h2>The other two looks</h2>{looks}
<h2>How it was made</h2>{made}
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter_build()
    with studio.lock("deliver") as run:
        return _deliver(run)


def _deliver(run):
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win):
        sys.exit("build/library.json, build/taste.json or build/winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("clips.json") or {}).get("clips") or {}
    music = _env.read_json("music.json") or {}
    report = _env.read_json("render/film-report.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, win)
    written = brief(lib, taste, win, clips, music, report, cuts)
    film = _env.read_json("film.json") or {}
    other = other_looks(win.get("board"))
    made = how_made(lib, win, film, music)
    pal = (taste.get("palette") or {}).get("year") or []
    board = _env.read_json(((_env.read_json("film.json") or {}).get("boards") or {}).get("reel", "")) or {}
    colors = (board.get("year") or {}).get("colors") or {}
    bg, text = page_colors(colors)
    accent = colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle, year = lib.get("handle"), lib.get("year")
    carousel = gallery([f"carousel/{p.name}" for p in sorted((OUT / "carousel").glob("*.png"))], "carousel")
    stories = gallery([f"stories/{p.name}" for p in sorted((OUT / "stories").glob("*.png"))], "stories")
    frames = [f"strip/{p.name}" for p in sorted((OUT / "strip").glob("*.jpg"))]
    strip = gallery(frames, "strip") if frames else ""

    def page(banner):
        return PAGE.format(title=esc(f"{'@' + handle + ' · ' if handle else ''}{year} in review"), banner=banner, caption=esc(cap), bg=bg, text=text,
                           accent=accent, strip=strip, carousel=carousel, stories=stories, looks=other, made=made)

    # the page says it is not ready until the gate passes, so a deliver stopped partway never leaves out/ looking
    # delivered; every file moves in by rename, whole
    _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>"))
    _env.write_text(OUT / "caption.md", cap)
    _env.write_text(Path("brief.md"), written)
    (OUT / "brief.md").unlink(missing_ok=True)
    res, f = qa.gate_checks(run)
    if qa.report(res, "qa/gate.json", f, "GATE") == 0:
        _env.write_text(OUT / "review.html", page(""))
    else:
        items = "".join(f"<li>{esc(name)}: {esc(detail)}</li>" for name, ok, detail, *_ in res if ok is False)
        _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        # the last line names what failed and no film, so a reply copied from it never points at an unready reel
        print("the gate failed: " + ", ".join(r[0] for r in res if r[1] is False))
        return 1
    print(f"delivered: out/film.mp4, out/carousel/ (10), out/stories/ (3), out/strip/ ({len(frames)}), out/looks/, out/caption.md, "
          "out/review.html; the record of the run is build/brief.md")
    print(Path(os.path.relpath((OUT / "film.mp4").resolve(), _env.WORKSPACE.resolve())).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
