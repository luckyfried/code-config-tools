#!/usr/bin/env python3
"""Movement 5, last step: write out/caption.md, out/review.html and B/brief.md, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is B/caption.md (B = the run's folder, build/<run stamp>/) when the agent wrote one in the person's
voice, otherwise a short caption drafted from B/taste.json and B/shared.json in their register (their case, their length, their own hashtags); it
always names the named one by @handle (by the name the person calls them when no account is theirs).

review.html is the person's page: the reel opening on its story card (out/story.png), the caption to copy, the posted
image (out/post.png) and the story card, the square and wide films and the stills when the person asked for them, the
other two looks (their frames from storyboard.py sheets, copied to out/looks/) with the sentence "Prefer another look?
Say 'make the second one'", and how the film was made, in plain words. It names no check, carries no score, and never
says who judged it.

B/brief.md, the run's record (never in out/), opens with who the film is for and how they were found (the person's
words, the tags, the comments, the runner-up), the occasion and where it came from, the film's length and where it
came from, what the two share, then every door tried, open or closed, what the run assumed, the three looks and how
this one was picked, the clips the storyboard asked for and which a video model made, where the music came from, how
the film was rendered, and the critics' scores of the cut against the bar (a mean of 4.5, none under 4). A film under
the bar once its one fix is spent is delivered as the best cut, and its scores are in brief.md and nowhere else.

deliver holds the run's lock (named deliver) from the moment it enters the run through its last write, and runs the
gate (qa.py gate) in its own process under that lock, so every probe and detector the gate starts holds it. It prints
each assumption research recorded about who the film is for and what it shows (`assumed: ...`), for the reply. Exit 0
when no check of qa.py gate fails; on a failed gate the last line is "not delivered: the gate failed on <checks>",
naming no film, brief.md lists what the gate found, and the page says it is not ready to post. A delivered run is
marked delivered (B/delivered.json) with its deliverables kept in B/out/, so a later script never writes into it again
(except `vote.py pick`, which makes another look in the same run), and the last line deliver prints is that run's
reel, B/out/film.mp4, as a path from the workspace root (for example build/20261020T151200Z/out/film.mp4): the path
the reply names. The line before it names the other two looks in the page's order, so "the second one" is known.
"""
import html
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import qa  # noqa: E402
import shared as shared_py  # noqa: E402
import studio  # noqa: E402
import vote  # noqa: E402
import compose  # noqa: E402

OUT = Path("out")


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(taste, shared):
    own = Path(f"{_env.B}/caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    who = shared.get("who") or {}
    occ = {**(shared.get("occasion") or {}), **{k: v for k, v in (taste.get("occasion") or {}).items() if v}}
    eras = [e["place"] for e in shared.get("eras", []) if e.get("place")]
    first = (shared.get("first") or {}).get("date")
    lines = [occ.get("title") or f"for {shared_py.called(who)}"]
    if first:
        m = int(first.split("-")[1])
        since = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
                 "november", "december"][m - 1]
        lines.append(f"from that first photo in {since} to now" + (f": {', '.join(eras[:-1])} and {eras[-1]}" if len(eras) >= 2 else ""))
    line = (taste.get("love_lines") or [x["line"] for x in shared.get("love_lines", [])] or [None])[0]
    if line:
        lines.append(line)
    lines.append(f"love you {shared_py.called(who)}")
    body = "\n".join(lines)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:2]))
    return f"{body}\n" + (f"\n{' '.join(tags)}\n" if tags else "")


def who_rows(shared):
    who = shared.get("who") or {}
    occ = shared.get("occasion") or {}
    c = shared.get("counts") or {}
    f, l = shared.get("first") or {}, shared.get("latest") or {}
    L = [f"- For {shared_py.called(who)} ({who.get('name') or who.get('first')}): {who.get('matched_by')}"
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
        L.append(f"- Their own feed was read from {feed.get('source') or 'a saved copy'}: {feed.get('posts', 0)} posts; its palette is in {_env.B}/palette.json.")
    return L


def brief(lib, taste, shared, win, music, film, cuts):
    handle = lib.get("handle") or taste.get("handle")
    who = shared_py.called(shared.get("who") or {})
    occ = (shared.get("occasion") or {}).get("label")
    L = [f"# @{handle} for {who}{', ' + occ if occ else ''}: how this was made", "", "## who it is for", ""] + who_rows(shared)
    if film.get("length"):
        L.append(f"- The film runs {film['length']:g} s: {film.get('length_from') or 'the board'}; each card holds as long as its photograph asks.")
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in (lib.get("assumptions") or []) + (shared.get("assumptions") or [])]
    L += ["", "## what it learned about you", "",
          f"{_env.B}/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("together", []))) + " (the colors the two of you share); avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the three looks", ""]
    i = str(win.get("board"))
    most = len(vote.PANEL) * len(vote.CRITERIA) * 5
    for n in looks_order(win, all_looks=True):
        sb = _env.read_json(f"{_env.B}/storyboards/{n}/storyboard.json") or {}
        total = (win.get("totals") or {}).get(n)
        L.append(f"- {n}, {compose.name_of(sb.get('style'))[0] if sb.get('style') else sb.get('name')}"
                 + (f", {total} of {most} from the critics" if total is not None else "") + (" (this film)" if n == i else "")
                 + f": {sb.get('idea')}")
    L.append(f"- Picked by {win.get('picked_by') or 'the vote'}" + (f": {win['reason']}" if win.get("reason") else "") + ".")
    L.append(f"- The boards side by side: {_env.B}/out/boards.png (out/boards.png until delivered); this storyboard's sheet: {_env.B}/storyboards/{i}/sheet.png.")
    cl = (_env.read_json(f"{_env.B}/clips.json") or {}).get("clips") or {}
    if cl:
        L += ["", "## the clips", ""]
        for k, c in cl.items():
            if c.get("status") == "generated":
                L.append(f"- {k} ({c['beat']}, {c['use']}): made by a video model from {c['image']}, {c['frames']} frames.")
            else:
                L.append(f"- {k} ({c['beat']}, {c['use']}): requested and not made ({c.get('why')}); the film shows the "
                         f"photograph still, with the camera moving over it.")
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm, the film timed at {film.get('bpm') or music.get('bpm')} bpm so the opening hit, the close's fall and its punch land on its beats; "
                 f"mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", ""]
    shapes = ["1080x1920 for Reels"] + [w for f, w in (("film-square.mp4", "1080x1080 for the feed"), ("film-wide.mp4", "1920x1080 for a wide screen"))
                                         if (OUT / f).exists()]
    L.append("- Every picture in it is one of your own photographs" + (" or a clip a video model made from one" if made_clips() else "")
             + ", set in motion by the kit's motion studio from one storyboard, laid out "
             + ("for each shape: " + ", ".join(shapes) if len(shapes) > 1 else "at " + shapes[0]) + ".")
    if any((OUT / "stills").glob("*.png")):
        L.append("- The stills are the settled frames of the opening, the fullest moment and the close, in each shape.")
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
        sc = last_scores(cuts)
        if sc:
            L.append(f"- Round {cuts[-1].get('round')} against the bar: {vote.against_bar(sc)}.")
        low = sorted({k for e in (cuts[-1].get("critics") or {}).values()
                      for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, int) and v < vote.FLOOR})
        if low:
            L.append(f"- Under {vote.FLOOR}: " + ", ".join(low) + ".")
        if sc and not vote.at_bar(sc):
            L.append("- This is the best cut, delivered under the bar; these scores are here and not on the page.")
    return "\n".join(L) + "\n"


def made_clips():
    return sum(1 for c in ((_env.read_json(f"{_env.B}/clips.json") or {}).get("clips") or {}).values() if c.get("status") == "generated")


def looks_order(win, all_looks=False):
    """The boards in the vote's order; without `all_looks`, the two that are not this film, in the order the page shows them."""
    order = [str(n) for n in win.get("order") or []] or sorted(p.parent.name for p in Path(f"{_env.B}/storyboards").glob("*/storyboard.json"))
    here = str(win.get("board"))
    return order if all_looks else [n for n in order if n != here]


def how_made(win, music, film, shared):
    """How the film was made, in plain words for the person: the photos, the look, the music, the clips, the pick."""
    sb = _env.read_json(f"{_env.B}/storyboards/{win.get('board')}/storyboard.json") or {}
    name, sentence = compose.name_of(sb["style"]) if sb.get("style") else (sb.get("name"), "")
    photos = len({bt["post"] for bt in film.get("beats") or [] if bt.get("post")})
    c = shared.get("counts") or {}
    L = [f"It is made from {photos} of the {c.get('photos') or photos} photographs of the two of you"
         + (f", in the order you lived them" if shared.get("eras") else "") + "."]
    L.append(f"The look is {name}" + (f": {sentence[:1].lower() + sentence[1:].rstrip('.')}" if sentence else "") + ".")
    if music.get("recipe"):
        L.append(f"The music was written for this film in the same look, at {round(float(music.get('bpm') or 0))} beats a minute, and the cuts land on its beats.")
    elif music.get("file"):
        L.append("The music is the track you chose, and the cuts land on its beats.")
    else:
        L.append("It has no music yet; add a sound when you post.")
    n = made_clips()
    if n:
        L.append(f"{n} of its moments move because a video model brought the photograph to life.")
    L.append("Three looks were drafted from the same photographs; " + ("you picked this one." if win.get("picked_by") not in (None, "the vote", "taste")
                                                                       else "this one was picked as the strongest of the three."))
    return " ".join(L)


def last_scores(cuts):
    return [v for e in (cuts[-1].get("critics") or {}).values()
            for v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).values() if isinstance(v, int)] if cuts else []


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:380px 1fr;gap:18px;align-items:start}} .posts video{{width:100%}}
.stills{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;align-items:start}} .stills img{{width:100%;border-radius:6px}}
.posts img{{width:100%;border-radius:8px;display:block}}
.looks{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}} .looks img{{width:100%;border-radius:8px;display:block}}
.looks h3{{margin:10px 0 2px;font-size:17px}} .looks p{{margin:0;opacity:.8;font-size:14px}} .ask{{margin:22px 0 0;font-size:17px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your tribute film for Reels, the post, the story card and a caption.</p>
{banner}
<div class="top"><video src="film.mp4" poster="story.png" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>The post and the story card</h2><div class="posts"><a href="post.png"><img src="post.png" alt="the post"></a>
<a href="story.png"><img src="story.png" alt="the story card" style="max-width:260px"></a></div>
</div></div>
{posts}{stills}
<h2>How it was made</h2><p>{how}</p>
{looks}
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.run_dir()
    with studio.lock("deliver") as run:
        return _deliver(run)


def _deliver(run):
    lib = _env.read_json(f"{_env.B}/library.json") or {}
    taste = _env.read_json(f"{_env.B}/taste.json") or {}
    shared = _env.read_json(f"{_env.B}/shared.json") or {}
    win = _env.read_json(f"{_env.B}/winner.json") or {}
    if not (lib and taste and win):
        sys.exit(f"{_env.B}/library.json, {_env.B}/taste.json or {_env.B}/winner.json is missing; run the earlier movements first")
    music = _env.read_json(f"{_env.B}/music.json") or {}
    film = _env.read_json(f"{_env.B}/film.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, shared)
    written = brief(lib, taste, shared, win, music, film, cuts)
    colors = (_env.read_json(f"{_env.B}/storyboards/{win.get('board')}/storyboard.json") or {}).get("colors") or {}
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("paper", "#f4efe8"), colors.get("accent", "#e6b26d")
    others = looks_order(win)
    shutil.rmtree(OUT / "looks", ignore_errors=True)
    cells = []
    for k, n in zip(("second", "third"), others):
        sb = _env.read_json(f"{_env.B}/storyboards/{n}/storyboard.json") or {}
        name, sentence = compose.name_of(sb["style"]) if sb.get("style") else (sb.get("name"), "")
        src = Path(f"{_env.B}/storyboards/{n}/look.png")
        if src.exists():
            (OUT / "looks").mkdir(exist_ok=True)
            tmp = OUT / "looks" / f".{n}.png.part"
            shutil.copyfile(src, tmp)
            os.replace(tmp, OUT / "looks" / f"{n}.png")
        img = f"<a href='looks/{esc(n)}.png'><img src='looks/{esc(n)}.png' alt=''></a>" if src.exists() else ""
        cells.append(f"<div>{img}<h3>The {k} look: {esc(name)}</h3><p>{esc(sentence)}</p></div>")
    looks = (f"<h2>The other two looks</h2><div class='looks'>{''.join(cells)}</div>"
             f"<p class='ask'>Prefer another look? Say 'make the second one'.</p>") if cells else ""
    how = how_made(win, music, film, shared)
    handle = lib.get("handle")
    who = shared_py.called(shared.get("who") or {})
    occ = (shared.get("occasion") or {}).get("label")
    # the square and wide films and the stills only when the render made them, as the person asked for them
    extra = "".join(f"<video src='{f}' controls playsinline loop></video>" for f in ("film-square.mp4", "film-wide.mp4") if (OUT / f).exists())
    posts = f"<h2>For the feed or a screen</h2><div class='posts'>{extra}</div>" if extra else ""
    shots = "".join(f"<a href='stills/{p.name}'><img src='stills/{p.name}' alt=''></a>" for p in sorted((OUT / "stills").glob("*.png")))
    stills = f"<h2>Stills</h2><div class='stills'>{shots}</div>" if shots else ""

    def page(banner):
        return PAGE.format(title=esc(f"For {who}" + (f" · {occ}" if occ else "") + f" · from @{handle}"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts, stills=stills, how=esc(how), looks=looks)

    # the page says it is not ready until the gate passes, so a deliver stopped partway never leaves out/ looking
    # delivered; every file moves in by rename, whole
    _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>"))
    # the run's record lives in B, never beside the deliverables
    (OUT / "brief.md").unlink(missing_ok=True)
    shutil.rmtree(OUT / "storyboards", ignore_errors=True)
    _env.write_text(OUT / "caption.md", cap)
    _env.write_text(f"{_env.B}/brief.md", written)
    for a in shared.get("assumptions") or []:
        print(f"assumed: {a}")
    res, f = qa.gate_checks(run)
    passed = qa.report(res, f"{_env.B}/qa/gate.json", f, "GATE") == 0
    found = [f"- {name}: {detail}" for name, ok, detail, *_ in res if ok is False or ok == qa.OPEN]
    if found:
        _env.write_text(f"{_env.B}/brief.md", written + "\n## what the gate found\n\n" + "\n".join(found) + "\n")
    if passed:
        _env.write_text(OUT / "review.html", page(""))
    else:
        _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> This film is still being made.</div>"))
        # the last line names what failed and no film, so a reply read from it never points at an unready film
        print(f"not delivered: the gate failed on {', '.join(name for name, ok, *_ in res if ok is False)}")
        return 1
    shutil.rmtree(f"{_env.B}/out", ignore_errors=True)
    shutil.copytree(OUT, f"{_env.B}/out")
    _env.write_json(f"{_env.B}/delivered.json", {"run": Path(_env.B).name, "out": sorted(str(p) for p in OUT.rglob("*") if p.is_file())})
    made = [n for n in ("film.mp4", "film-square.mp4", "film-wide.mp4", "stills/", "post.png", "story.png") if (OUT / n).exists()]
    print("delivered: " + ", ".join(f"out/{n}" for n in made + ["caption.md", "review.html"]) + f"; the record: {_env.B}/brief.md")
    names = [compose.name_of((_env.read_json(f"{_env.B}/storyboards/{n}/storyboard.json") or {}).get("style") or "")[0] for n in others]
    print("other looks: " + ", ".join(f"the {k} one is storyboard {n} ({nm})" for k, n, nm in zip(("second", "third"), others, names)))
    print(os.path.relpath(Path(_env.B) / "out" / "film.mp4"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
