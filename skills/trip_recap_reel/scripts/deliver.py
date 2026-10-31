#!/usr/bin/env python3
"""Movement 6, last step: write out/caption.md and out/review.html, and brief.md beside out/, then run the gate.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/deliver.py

caption.md is caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from taste.json in their register (their case, their length, their own hashtags). brief.md, in the run's folder and
not in out/, says where the material came from (every door tried, open or closed), what the run assumed, the vote,
every clip and whether it was generated, taken from their own clips or substituted with an animated photo, where the
music came from, how the film was made, and every score of the boards and of the cut against the bar (a mean of 4.5
with no criterion under 4), saying plainly when the delivered cut is under it; it opens with the trip: its dates, its
days, its places one per line with their city, the people on it, and how their travel style differs from their
everyday one. out/ holds the deliverables and nothing else: the films, the cover, the story cards, the caption, the
boards (out/boards.png) and review.html. review.html is the film's page, on the board's paper in its ink: the trip's
title, the film (9:16) with the cover as its poster, the caption to copy, the cover to post with, the 16:9 and square
films and the five story cards when the person asked for them, the two other looks (their rows of out/boards.png)
with "Prefer another look? Say 'make the second one'", and how it was made in plain words; it carries no score and
links to nothing outside out/. A storyboard, a vote table or an earlier brief left in out/ is taken away.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong, and until
the gate has passed it carries one saying so. deliver holds the run's render lock from entering the run to its last
write, so a render running in the run refuses it, and no render changes out/ while it writes. On a green gate its
last line is the reel's path from the project's root (build/<run>/out/film.mp4), the path the reply names first;
on a failed gate it is "not ready: the gate failed on" and the failing checks, and no path.
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
import studio  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")
SIZES = {"reel": "1080x1920", "landscape": "1920x1080", "square": "1080x1080"}
# the formats beyond the reel: their file, their heading on the page, their class
EXTRAS = (("film-16x9.mp4", "The same film, wide", "wide"), ("film-square.mp4", "The same film, square", "square"))


def esc(s):
    return html.escape("" if s is None else str(s))


MONTHS = "january february march april may june july august september october november december".split()


def range_line(lo, hi):
    import datetime as dt
    try:
        a, b = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
    except (TypeError, ValueError):
        return ""
    if a == b:
        return f"{MONTHS[a.month - 1]} {a.day}"
    if a.month == b.month:
        return f"{MONTHS[a.month - 1]} {a.day} to {b.day}"
    return f"{MONTHS[a.month - 1]} {a.day} to {MONTHS[b.month - 1]} {b.day}"


def and_list(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1] if xs else ""


def trip_tags():
    """The hashtags they used on the trip's own posts, most used first."""
    from collections import Counter
    trip = _env.read_json("trip.json") or {}
    c = Counter(t.lower() for d in trip.get("days") or [] for cap in d.get("captions") or [] for t in re.findall(r"#\w+", cap or ""))
    return [t for t, _ in c.most_common(6)]


def their_tags(register):
    """The hashtags a caption may carry: the trip's own, then the ones they use most; none for a person who uses none."""
    return list(dict.fromkeys(trip_tags()[:4] + [h.lower() for h in register.get("hashtags") or []][:2]))


def local(place, city):
    """A place as the caption names it: the trip's own city left off ("Alfama, Lisbon" on a Lisbon trip is Alfama)."""
    head, _, tail = (place or "").rpartition(", ")
    return head if head and city and tail.strip().lower() == city.strip().lower() else place


def caption(taste, win):
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    t = taste.get("trip") or {}
    places = taste.get("places") or []
    people = [f"@{p.lstrip('@')}" for p in taste.get("people") or []]
    lines = [", ".join(x for x in (t.get("name"), range_line(t.get("from"), t.get("to"))) if x)]
    if len(places) >= 2:
        lines.append(and_list(dict.fromkeys(local(x, t.get("name")) for x in places)))
    if people:
        lines.append(f"with {and_list(people)}")
    body = "\n".join(x for x in lines if x)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = their_tags(reg)[:6]
    return f"{body}\n\n{' '.join(tags)}\n" if tags else f"{body}\n"


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    said = {"generated": "made by the video model", "their_reel": "taken from one of your own clips",
            "substituted": "no generated clip arrived; an animated treatment of your photo stands in"}
    for cid, c in sorted(clips.items()):
        how = said.get(c.get("status"), c.get("status"))
        if c.get("status") == "substituted" and c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def trip_lines(taste):
    """The trip as the brief opens on it: the dates, each day and its places, the people, travel against everyday."""
    r = _env.read_json("research.json") or {}
    trip = _env.read_json("trip.json") or {}
    film = _env.read_json("film.json") or {}
    t = film.get("trip") or taste.get("trip") or {}
    places = t.get("places") or taste.get("places") or [p["name"] for p in trip.get("places") or []]
    L = [f"- When: {t.get('from')} to {t.get('to')}, {t.get('days') or trip.get('days_count')} days "
         f"({trip.get('chosen_by') or 'the trip you named'}; found by {trip.get('found_by') or 'dates'})."]
    stops = film.get("stops") or []
    L.append("- Places, in the order of the trip:")
    L += [f"  - {s['name']}, {s['city']}" if s.get("city") and s["city"] != s["name"] else f"  - {s['name']}"
          for s in stops] or [f"  - {p}" for p in places]
    rows = ["", "| day | places | its line |", "|---|---|---|"]
    for d in r.get("days") or []:
        rows.append(f"| {d.get('label') or d.get('date')} | {', '.join(d.get('places') or []) or '-'} | {(d.get('line') or '').replace('|', '/')} |")
    people = r.get("people") or []
    L.append("- With: " + (", ".join(f"@{p['handle']} ({p['items']} posts on {p['days']} days)" for p in people) if people else "no one tagged") + ".")
    tv = r.get("travel_vs_everyday") or {}
    if not (tv.get("palette_everyday")):
        L.append("- Every day: the posts you shared are all from the trip, so the film's look is the trip's own.")
    else:
        def pair(k):
            v = tv.get(k) or {}
            return f"{v.get('trip')} on the trip against {v.get('everyday')} every day"
        L.append(f"- Traveling you shoot {', '.join(tv.get('palette_trip') or [])}; every day you shoot "
                 f"{', '.join(tv.get('palette_everyday') or [])}. Brightness {pair('brightness')}; saturation "
                 f"{pair('saturation')}; caption length in words {pair('caption_words')}; posts a day {pair('posts_per_day')}.")
    return L + rows


def brief(lib, taste, win, clips, music, cuts):
    handle = lib.get("handle") or taste.get("handle")
    t = taste.get("trip") or {}
    L = [f"# @{handle}, {t.get('name')}: how this trip recap was made", "", "## the trip", ""] + trip_lines(taste)
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("trip", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the three looks and the vote", "",
          f"The bar: a mean of {vote.BAR} or more, with no criterion under {vote.FLOOR}.", ""]
    res = win.get("scores") or {}
    for i in win.get("order") or []:
        sb = _env.read_json(f"storyboards/{i}/storyboard.json") or {}
        r = res.get(i) or {}
        crit = ", ".join(f"{k} {v:.2f}" for k, v in (r.get("criteria") or {}).items())
        L.append(f"- {i}, {sb.get('look')}: mean {r.get('mean', 0):.2f} ({crit}); "
                 + ("clears the bar." if r.get("clears") else "under the bar."))
    L.append(f"- The film is board {win.get('board')}, {win.get('name')}, picked by {win.get('by')}"
             + (f": {win['why']}" if win.get("why") else "") + ".")
    L += ["", "## the clips", ""]
    L += clip_rows(clips) if clips else ["The storyboard uses no clips."]
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
    formats, _ = qa.made()
    sizes = ", ".join(size for fmt, size in SIZES.items() if fmt in formats)
    look = (_env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}).get("look")
    L.append(f"- Drawn from one storyboard in the {look} look, every photograph your own: {sizes}, 30 fps, H.264, AAC.")
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
        vals = cut_scores(cuts[-1])
        if vals:
            mean = sum(vals.values()) / len(vals)
            low = sorted({k.split(" / ")[1] for k, v in vals.items() if v < vote.FLOOR})
            met = mean >= vote.BAR and not low
            L.append(f"- Against the bar: a mean of {vote.down(mean):.2f} against {vote.BAR}"
                     + (f"; under {vote.FLOOR}: {', '.join(low)}" if low else f", none under {vote.FLOOR}") + ". "
                     + ("The film clears the bar." if met else "The film is under the bar; this is the best cut, delivered as it is."))
    return "\n".join(L) + "\n"


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:17px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:40px 24px 72px}}
h1{{font-size:44px;line-height:1.1;margin:0 0 6px;letter-spacing:-.01em}} h2{{margin:44px 0 12px;font-size:21px}}
.sub{{margin:0 0 28px;opacity:.75}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:40px;align-items:start}}
video{{width:380px;border-radius:16px;background:{ink};display:block}} video.wide{{width:100%;max-width:960px}} video.square{{width:540px}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}}
.cover{{width:220px}} .posts img,.cover img{{width:100%;border-radius:8px;display:block}}
pre{{white-space:pre-wrap;background:rgba(0,0,0,.06);padding:16px;border-radius:10px;font:16px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:#fff;border:0;border-radius:8px;padding:9px 16px;font-weight:700;cursor:pointer}}
.looks{{display:grid;grid-template-columns:1fr;gap:22px;max-width:960px}} .row{{overflow:hidden;border-radius:10px;aspect-ratio:{row_ratio}}}
.row img{{width:100%;display:block}} .ask{{font-weight:700}} a{{color:{ink}}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your trip as a film for Reels{also} and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" poster="cover.png" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>Cover</h2><p>Choose this picture as the reel's cover when you post it.</p><div class="cover">{cover}</div>
</div></div>
{extras}
{looks}
<h2>How it was made</h2>{made}
</main></body></html>
"""


ORDINALS = ("first", "second", "third")


def cut_scores(cut):
    """A cut round's scores of the film, keyed "critic / criterion"."""
    return {f"{who} / {k}": v for who, e in (cut.get("critics") or {}).items()
            for k, v in (((e.get("boards") or {}).get("film") or {}).get("scores") or {}).items() if isinstance(v, (int, float))}


def other_looks(win):
    """The page's other looks: each a row of out/boards.png (the rows are storyboard.SHEET_GAP apart, each
    storyboard.SHEET_HEAD over its frames), with the words that ask for it; empty without out/boards.png."""
    import storyboard
    from PIL import Image
    sheet = OUT / "boards.png"
    order = [b["id"] for b in storyboard.load_boards()] if sheet.exists() else []
    if not order:
        return "", "1/1"
    W, H = Image.open(sheet).size
    gap = storyboard.SHEET_GAP
    row = (H - gap) / len(order)
    cells, first = [], None
    for k, n in enumerate(order):
        if n == str(win.get("board")):
            continue
        b = _env.read_json(f"storyboards/{n}/storyboard.json") or {}
        first = first or ORDINALS[k]
        top = -(k * row + gap / 2) / W * 100
        cells.append(f"<div><p class='ask'>{esc(b.get('look'))}: say \u201cmake the {ORDINALS[k]} one\u201d.</p>"
                     f"<div class='row'><img src='boards.png' alt='{esc(b.get('look'))}' style='margin-top:{top:.3f}%'></div></div>")
    ask = (f"<h2>The other looks</h2><p>Prefer another look? Say \u201cmake the {first} one\u201d, and the film is made "
           "again in it, music and all.</p>")
    return ask + "<div class='looks'>" + "".join(cells) + "</div>", f"{W}/{row:.0f}"


def made_lines(win, music):
    """How the film was made, in plain words for the person."""
    b = _env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}
    stops = len((b.get("route") or {}).get("stops") or [])
    said = [f"Your {stops} places, in the order you went, cut in the {b.get('look')} look: {b.get('sentence') or ''}".strip()]
    if music.get("file"):
        said.append("The music was made for this look, and every cut lands on its beat." if music.get("recipe") else
                    "The cuts land on the beat of the track you chose.")
    said.append("Every picture is one of your own photographs or clips.")
    return "".join(f"<p>{esc(x)}</p>" for x in said)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter_run()
    # the gate's tools resolve before the lock (setup.py's probe, a re-exec for PIL); then the lock is held from here
    # through the last write, so no render changes out/ while deliver writes it, and the gate runs here with the same
    # lock, every ffprobe and ffmpeg it starts going through run.spawn
    _env.need("PIL")
    _env.ffmpeg(), _env.ffprobe()
    with studio.lock("deliver") as run:
        return deliver(run)


def deliver(run):
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win):
        sys.exit("library.json, taste.json or winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("clips.json") or {}).get("clips") or {}
    music = _env.read_json("music.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, win)
    written = brief(lib, taste, win, clips, music, cuts)
    colors = (_env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    # the page is the film's own: the board's paper with its ink on it
    bg, ink, accent = colors["paper"], colors["ink"], colors["accent"]
    handle, name = lib.get("handle") or taste.get("handle"), (taste.get("trip") or {}).get("name")
    # the other formats and the story cards only when the render made them, as the person asked for them
    shapes = [(f, h, k) for f, h, k in EXTRAS if (OUT / f).exists()]
    stories = [p for p in (f"story-{i}.png" for i in range(1, 6)) if (OUT / p).exists()]
    extras = "".join(f"<h2>{h}</h2><video class='{k}' src='{f}' controls playsinline loop></video>" for f, h, k in shapes)
    extras += "<h2>The five story cards</h2>" + gallery(stories, "posts") if stories else ""
    also = [("the same film for a wide screen" if k == "wide" else "the same film for a square feed") for _, _, k in shapes]
    also += ["five story cards"] if stories else []

    looks, ratio = other_looks(win)

    def page(banner):
        return PAGE.format(title=esc(name or f"@{handle}"), banner=banner, caption=esc(cap), bg=bg, ink=ink, accent=accent,
                           also="".join(f", {a}" for a in also), extras=extras, looks=looks, row_ratio=ratio,
                           made=made_lines(win, music), cover=gallery(["cover.png"], "one") if (OUT / "cover.png").exists() else "")

    # the page says it is not ready until the gate passes, so a deliver stopped partway never leaves out/ looking
    # delivered; every file here can be opened without the page, so each moves in whole
    _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>"))
    shutil.rmtree(OUT / "storyboards", ignore_errors=True)
    (OUT / "brief.md").unlink(missing_ok=True)
    _env.write_text(OUT / "caption.md", cap)
    _env.write_text(Path("brief.md"), written)
    res = qa.gate_checks(run)
    if qa.report(res, "qa/gate.json", "GATE") == 0:
        _env.write_text(OUT / "review.html", page(""))
    else:
        items = "".join(f"<li>{esc(name)}  {esc(detail)}</li>" for name, ok, detail, *_ in res if ok is False)
        _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        print("not ready: the gate failed on " + ", ".join(dict.fromkeys(name for name, ok, *_ in res if ok is False)))
        return 1
    made = ["film.mp4", "cover.png"] + [f for f, _, _ in shapes] + (["story-1.png .. out/story-5.png"] if stories else [])
    print("delivered: " + ", ".join(f"out/{n}" for n in made + ["caption.md", "review.html"]) + "; brief.md beside out/")
    print(Path(os.path.relpath(Path.cwd().resolve() / OUT / "film.mp4", _env.HOME)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
