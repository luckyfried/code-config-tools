#!/usr/bin/env python3
"""Movement 5, last step: write out/caption.md, out/review.html and R/brief.md, then run the gate.

USAGE (from the workspace root; S = this skill's folder; R = the run folder, build/<run stamp>/):
    python3 S/scripts/deliver.py

caption.md is R/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from R/taste.json in their register (their case, their own hashtags, none when they use none). Either way the caption tags every person
in the film; a handle the agent's caption left out is added on a line of its own. brief.md, how the film was made, stays
in the run folder beside out/ and opens with the people: each one's stretch of the year, their moment (where and when the photograph of the two of them was taken, and the person's
caption of it), their best line and whose words it is, why they are in the film, and their story card; then who came
next.
It goes on to say where the material came from (every door tried, open or closed), what the run assumed, the vote,
the three looks and the panel's scores of each, which look was picked and by whom, where the music came from, how the
film was rendered, and the critics' scores of the timed cut against the bar, whichever way they went: the scores live in
brief.md and nowhere else. review.html is the film's cover, written for the person: it opens on the reel with its cover
image (out/cover.png) as the poster, links the square and wide films and shows the reel's story card (out/story.png),
and each person's story card when the person asked for them, then the caption, then the two looks that were not picked
(their sheets copied to out/looks/<style>.png) under "Prefer another look? Say 'make the second one'", then how it was
made in a few plain sentences. The page carries no score. out/ holds the deliverables and nothing else. The last line deliver prints on a green gate is the reel, R/out/film.mp4,
as a path from the workspace root (for example build/20261020T151200Z/out/film.mp4): the path the reply names.
Exit 0 only when qa.py gate passes; on a failed gate the last line names the failing checks and no film, the page carries a red banner naming what is wrong, and until
the gate has passed it carries one saying so; with no username in the data, the brief's title and the page leave the
handle out and the page says no username was found and where to put it. Every file is made beside its place and moved
in by rename. out/film.mp4 is the index of out/: deliver refuses without it, sets it aside while the caption moves in,
and puts it back after it, so a deliver stopped on the way leaves a set no later command
takes for delivered and film.py render makes it again. deliver holds the run's lock (studio.lock) from the moment it enters the run until its last
write, and runs the gate (qa.gate) in its own process under that lock, so every tool the gate starts holds it.
"""
import html
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import gather  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import studio  # noqa: E402
import style  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")


def esc(s):
    return html.escape("" if s is None else str(s))


def handles(taste):
    return [x["handle"] for x in taste.get("people") or [] if x.get("handle")]


def tagged(text, h):
    return re.search(r"@" + re.escape(h) + r"(?!\w|\.\w)", text) is not None


def caption(taste, win):
    reg = taste.get("register") or {}
    ppl = handles(taste)
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        text = own.read_text().strip()
        left = [h for h in ppl if not tagged(text, h)]
        if left:
            body, _, tags = text.rpartition("\n\n") if "\n\n" in text else (text, "", "")
            line = " ".join("@" + h for h in left)
            text = f"{body}\n{line}\n\n{tags}".strip() if tags else f"{text}\n{line}"
        return text + "\n"
    year = taste.get("year")
    lines = [f"the people who made my {year}", " ".join("@" + h for h in ppl), "thank you for every one of these"]
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    own = reg.get("hashtags") or []
    if not own:   # someone who never uses a hashtag gets none
        return f"{body}\n"
    tags = list(dict.fromkeys(own[:3] + ["#mypeople", f"#{year}recap"]))
    return f"{body}\n\n{' '.join(tags)}\n"


def people_rows(taste):
    res = {x["handle"]: x for x in (_env.read_json("research.json") or {}).get("people", [])}
    cards = {c["handle"]: c["file"] for c in (_env.read_json("cards.json") or {}).get("cards", [])}
    rows = ["| # | who | their stretch | where and when | the photograph | their best line | why |" + (" story card |" if cards else ""),
            "|---|---|---|---|---|---|---|" + ("---|" if cards else "")]
    for k, x in enumerate(taste.get("people") or [], 1):
        h = x["handle"]
        r = res.get(h) or {}
        line = (x.get("line") or r.get("line") or "-").replace("|", "/")
        src = x.get("line_from") or r.get("line_from")
        card = cards.get(h, "-")
        stamp = ", ".join(v for v in (x.get("where") or r.get("where"), x.get("when") or r.get("when")) if v)
        rows.append(f"| {k} | @{h} | {x.get('stretch') or r.get('stretch') or '-'} | {stamp or '-'} | {(x.get('what') or r.get('what') or '-').replace('|', '/')} | "
                    f"\"{line}\"{f' ({src})' if src else ''} | {(x.get('why') or r.get('why') or '').replace('|', '/')} |"
                    + (f" {card.removeprefix('out/')} |" if cards else ""))
    return rows


def ranking_notes(taste):
    r = _env.read_json("research.json") or {}
    ppl = handles(taste)
    L = []
    if r.get("ranked_by"):
        L.append(f"They are the people found from {r['ranked_by']}.")
    nxt = [x for x in r.get("next") or [] if x["handle"] not in ppl][:3]
    if nxt:
        L.append("Who came next: " + ", ".join(f"@{x['handle']}" for x in nxt) + ".")
    return L


def brief(lib, taste, win, music, engine, cuts):
    handle, year = lib.get("handle") or taste.get("handle"), lib.get("year") or taste.get("year")
    L = [f"# @{handle}, my people of {year}: how this was made" if handle else f"# My people of {year}: how this was made",
         "", "## my people", ""] + people_rows(taste)
    notes = ranking_notes(taste)
    if notes:
        L += [""] + notes
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the three looks and the panel", ""]
    tot = (_env.read_json("vote/order.json") or {}).get("totals") or {}
    idea = (_env.read_json(storyboard.sb_path(win.get("board"))) or {}).get("idea") if win.get("board") else None
    if idea:
        L += [f"One story, drawn three ways: {idea}.", ""]
    for letter, i in zip("ABC", storyboard.looks()):
        score = f", {tot[i]} of {len(vote.PANEL) * len(vote.CRITERIA) * 5} from the panel" if i in tot else ""
        L.append(f"- {letter}. {style.card(i)['name']} ({i}{score}): {style.sentence(i)}")
    who = "picked by their taste" if win.get("by") == "taste" else "picked by them"
    L.append(f"- Made in {win.get('look') or win.get('board')}, {who}" + (f": {win['why']}" if win.get("why") else "."))
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", ""]
    on = {True: " on the graphics card", False: " on the processor"}.get((engine.get("render") or {}).get("gpu"), "")
    films = ["film.mp4 (1080x1920)"] + [w for f, w in (("film-square.mp4", "film-square.mp4 (1080x1080)"), ("film-wide.mp4", "film-wide.mp4 (1920x1080)"))
                                        if (OUT / f).exists()]
    L.append(f"- Drawn frame by frame in a browser with no window{on} and encoded with ffmpeg: " + (", ".join(films[:-1]) + " and " + films[-1] if len(films) > 1 else films[0])
             + ", 30 fps, H.264 High, AAC" + ("; each person's story card is the settled frame of the beat that names them."
                                               if any((OUT / "people").glob("*.png")) else "."))
    L += ["", "## the critics on the timed cut", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        cr = c.get("critics") or {}
        for who, e in cr.items():
            s = ((e.get("boards") or {}).get("film") or {}).get("scores") or {}
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in s.items()) + ".")
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    if cuts and not vote.problems(cuts[-1], vote.CUT_PANEL, ["film"]):
        L.append(f"- Round {cuts[-1].get('round')} against the bar: " + vote.told(*vote.standing(cuts[-1])) + ".")
    return "\n".join(L) + "\n"


def how_made(win, music, engine, taste):
    """How the film was made, in a few plain sentences for the person."""
    n = len(taste.get("people") or [])
    L = [f"Your photos and the words you and your people traded this year chose the {n} people in the film and the "
         "moment of each one.",
         f"Three looks were drawn up from your storyboard; this one is {win.get('look') or win.get('board')}"
         + (f", chosen because {win['why'][:1].lower() + win['why'][1:]}" if win.get("why") else ", the one you picked") + "."]
    if music.get("file"):
        L.append(f"The music was written for this look at {music.get('bpm')} beats a minute, and every cut lands on its beat.")
    else:
        L.append("The film is silent; add a sound when you post.")
    L.append("Each moment moves the way its photograph and its words ask, and the last frame brings everyone together.")
    return "<p>" + " ".join(esc(x) for x in L) + "</p>"


def others(win):
    """The two looks that were not picked: each look's reel sheet copied into out/looks/, with the words that pick it."""
    looks = list(storyboard.looks())
    rest = [(n, t) for n, t in zip(("first", "second", "third"), looks) if t != win.get("board")]
    shelf = OUT / "looks"
    shelf.mkdir(exist_ok=True)
    for old in shelf.glob("*.png"):
        if old.stem not in dict((t, 1) for _, t in rest):
            old.unlink()
    tiles = []
    for n, t in rest:
        src = storyboard.sb_path(t).parent / "sheet.png"
        if not src.exists():
            continue
        dst = shelf / f"{t}.png"
        _env.part(dst).write_bytes(src.read_bytes())
        os.replace(_env.part(dst), dst)
        tiles.append(f"<figure><a href='looks/{esc(t)}.png'><img src='looks/{esc(t)}.png' loading='lazy' alt=''></a>"
                     f"<figcaption><b>The {n} look, {esc(style.card(t)['name'])}.</b> {esc(style.sentence(t))}</figcaption></figure>")
    if not tiles:
        return ""
    say = next(n for n, _ in rest)
    return (f"<h2>Prefer another look? Say 'make the {say} one'</h2>"
            "<p>The same people and the same moments, made again in that look, music and all.</p>"
            f"<div class='looks'>{''.join(tiles)}</div>\n")


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:420px 1fr;gap:40px;align-items:start}}
video{{width:420px;border-radius:16px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}}
.posts img,.story img{{width:100%;border-radius:8px;display:block}}
.story{{width:240px}}
.looks{{display:grid;grid-template-columns:1fr 1fr;gap:24px}} .looks img{{width:100%;border-radius:8px;display:block}}
figure{{margin:0}} figcaption{{margin-top:8px;opacity:.85}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your film of your people and a caption that tags them all.</p>
{banner}
<div class="top"><video src="film.mp4" poster="cover.png" controls playsinline loop></video><div>
{films}<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2>{made}</div></div>
{posts}{others}
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter_run()
    with studio.lock("deliver") as run:
        return deliver(run)


def deliver(run):
    # out/film.mp4 is the index of out/: film.py render moves it in after the stills and cards.json
    reel = OUT / "film.mp4"
    if not (reel.exists() and Path("cards.json").exists()):
        sys.exit("out/film.mp4 or cards.json is missing: run film.py render, then deliver.py")
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win):
        sys.exit("library.json, taste.json or winner.json is missing from the run folder; run the earlier movements first")
    music = _env.read_json("music.json") or {}
    engine = _env.read_json("engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, win)
    # how it was made stays in the run, beside out/
    _env.write_text("brief.md", brief(lib, taste, win, music, engine, cuts))
    pal = (taste.get("palette") or {}).get("year") or []
    colors = (_env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle, year = lib.get("handle"), lib.get("year")
    # the square and wide films and the story cards only when the render made them, as the person asked for them
    extra = [f"<a href=\"{f}\">{f}</a> ({w})" for f, w in (("film-square.mp4", "for the feed"), ("film-wide.mp4", "for anywhere wide"))
             if (OUT / f).exists()]
    films = f"<p>{' and '.join(extra)} {'are' if len(extra) > 1 else 'is'} the same film.</p>\n" if extra else ""
    cards = sorted((OUT / "people").glob("*.png"))
    posts = "<h2>The story card, to share the reel to your story</h2>" + gallery(["story.png"], "story") + "\n"
    posts += "<h2>The story cards, one per person</h2>" + gallery([f"people/{f.name}" for f in cards], "posts") + "\n" if cards else ""

    # with no username in the data the film is signed with the year alone, and every page says where the username goes
    unsigned = "" if handle else f"<p>{esc(gather.NO_HANDLE)}</p>"

    shelf = others(win)

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · my people {year}" if handle else f"my people {year}"), banner=banner,
                           caption=esc(cap), bg=bg, ink=ink, accent=accent, films=films, posts=posts, made=how_made(win, music, engine, taste),
                           others=shelf)

    # the page says it is not ready until the gate passes, so a deliver stopped partway never leaves out/ looking
    # delivered; it goes first, before anything in out/ moves
    _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.{unsigned}</div>"))
    # out/film.mp4 stands aside while the caption changes and comes back after it: a deliver stopped on the way leaves
    # no out/film.mp4, which the gate and the next deliver refuse
    os.replace(reel, _env.part(reel))
    dest = OUT / "caption.md"
    _env.part(dest).write_text(cap)
    os.replace(_env.part(dest), dest)
    os.replace(_env.part(reel), reel)
    failing = qa.gate(run)
    if not failing:
        _env.write_text(OUT / "review.html", page(f"<div class='banner'>{unsigned}</div>" if unsigned else ""))
    else:
        items = "".join(f"<li>{esc(f'{name:9s} {detail}')}</li>" for name, detail in failing)
        _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul>{unsigned}</div>"))
        # the last line names what failed and no film, so a reply read from it never points at an unready film
        print(f"not delivered: the gate failed on {', '.join(name for name, _ in failing)}; fix what it names and run deliver.py again")
        return 1
    made = [f"out/{n}" for n in ("film.mp4", "film-square.mp4", "film-wide.mp4", "cover.png", "story.png") if (OUT / n).exists()]
    made += [f"{len(cards)} story cards in out/people/"] if cards else []
    print("delivered: " + ", ".join(made + ["out/caption.md", "out/review.html"]) + "; how it was made: brief.md")
    print(os.path.relpath(Path.cwd() / reel, _env.WORKSPACE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
