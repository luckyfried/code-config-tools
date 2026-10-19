#!/usr/bin/env python3
"""Movement 6, last step: write out/caption.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is build/caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted
from build/taste.json in their register (their case, their length, their own hashtags). brief.md says where the
material came from (every door tried, open or closed), what the run assumed, the vote, every clip and whether it was
generated, taken from their own clips or substituted with an animated photo, where the music came from, which
engine rendered the film, and the critics' scores of the cut; it opens with the trip: its dates, its days, its
places, the people on it, and how their travel style differs from their everyday one. review.html plays both films
and shows the five story cards, the caption, the three storyboards' style sheets and the vote, with the runners-up.
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
    trip = _env.read_json("build/trip.json") or {}
    c = Counter(t.lower() for d in trip.get("days") or [] for cap in d.get("captions") or [] for t in re.findall(r"#\w+", cap or ""))
    return [t for t, _ in c.most_common(6)]


def caption(taste, win):
    own = Path("build/caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    t = taste.get("trip") or {}
    places = taste.get("places") or []
    people = [f"@{p.lstrip('@')}" for p in taste.get("people") or []]
    lines = [", ".join(x for x in (t.get("name"), range_line(t.get("from"), t.get("to"))) if x)]
    if len(places) >= 2:
        lines.append(and_list(places))
    if people:
        lines.append(f"with {and_list(people)}")
    body = "\n".join(x for x in lines if x)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys(trip_tags()[:4] + [h.lower() for h in reg.get("hashtags") or []][:2] + ["#travelrecap"]))[:7]
    return f"{body}\n\n{' '.join(tags)}\n"


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
    r = _env.read_json("build/research.json") or {}
    trip = _env.read_json("build/trip.json") or {}
    film = _env.read_json("build/film.json") or {}
    t = film.get("trip") or taste.get("trip") or {}
    places = t.get("places") or taste.get("places") or [p["name"] for p in trip.get("places") or []]
    L = [f"- When: {t.get('from')} to {t.get('to')}, {t.get('days') or trip.get('days_count')} days "
         f"({trip.get('chosen_by') or 'the trip you named'}; found by {trip.get('found_by') or 'dates'})."]
    L.append(f"- Places, in the order of the route: {', '.join(places)}.")
    rows = ["", "| day | places | its line |", "|---|---|---|"]
    for d in r.get("days") or []:
        rows.append(f"| {d.get('label') or d.get('date')} | {', '.join(d.get('places') or []) or '-'} | {(d.get('line') or '').replace('|', '/')} |")
    people = r.get("people") or []
    L.append("- With: " + (", ".join(f"@{p['handle']} ({p['items']} posts on {p['days']} days)" for p in people) if people else "no one tagged") + ".")
    tv = r.get("travel_vs_everyday") or {}
    if tv:
        def pair(k):
            v = tv.get(k) or {}
            return f"{v.get('trip')} on the trip against {v.get('everyday')} every day"
        L.append(f"- Traveling you shoot {', '.join(tv.get('palette_trip') or [])}; every day you shoot "
                 f"{', '.join(tv.get('palette_everyday') or [])}. Brightness {pair('brightness')}; saturation "
                 f"{pair('saturation')}; caption length in words {pair('caption_words')}; posts a day {pair('posts_per_day')}.")
    return L + rows


def brief(lib, taste, win, clips, music, engine, cuts):
    handle = lib.get("handle") or taste.get("handle")
    t = taste.get("trip") or {}
    L = [f"# @{handle}, {t.get('name')}: how this trip recap was made", "", "## the trip", ""] + trip_lines(taste)
    L += ["", "## where your photos came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "build/taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("trip", []))) + "; avoid "
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
        L.append("- Rendered with the kit's Remotion project from one storyboard: 1080x1920 and 1920x1080, 30 fps, H.264, AAC; "
                 "the route map is drawn from your own coordinates, with no map tiles fetched from anywhere.")
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


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:380px 1fr;gap:36px;align-items:start}}
video{{width:380px;border-radius:16px;background:#000;display:block}} video.wide{{width:100%;max-width:960px}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}}
.sheets{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.posts img,.sheets img{{width:100%;border-radius:8px;display:block}}
.board h3{{margin:10px 0 2px;font-size:17px}} .board p{{margin:0;opacity:.8;font-size:14px}}
.win{{outline:3px solid {accent};outline-offset:6px;border-radius:10px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your trip as a film for Reels, the same film for a wide screen, five story cards and a caption, ready to post.</p>
{banner}
<div class="top"><video src="film.mp4" controls playsinline loop></video><div>
<h2 style="margin-top:0">Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, which clips were made and
which were stood in for, and where the music came from.</p></div></div>
<h2>The same film, wide</h2><video class="wide" src="film-16x9.mp4" controls playsinline loop></video>
<h2>The five story cards</h2>{posts}
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
    win = _env.read_json("build/winner.json") or {}
    if not (lib and taste and win):
        sys.exit("build/library.json, build/taste.json or build/winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("build/clips.json") or {}).get("clips") or {}
    music = _env.read_json("build/music.json") or {}
    engine = _env.read_json("build/engine.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    OUT.mkdir(exist_ok=True)
    cap = caption(taste, win)
    (OUT / "caption.md").write_text(cap)
    (OUT / "brief.md").write_text(brief(lib, taste, win, clips, music, engine, cuts))
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
    pal = (taste.get("palette") or {}).get("trip") or []
    colors = (_env.read_json(f"build/storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle, name = lib.get("handle") or taste.get("handle"), (taste.get("trip") or {}).get("name")
    posts = gallery([p for p in (f"story-{i}.png" for i in range(1, 6)) if (OUT / p).exists()], "posts")

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · {name}"), banner=banner, caption=esc(cap), bg=bg, ink=ink,
                           accent=accent, posts=posts, boards="".join(cells), table=table, runners=runners)

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print("delivered: out/film.mp4, out/film-16x9.mp4, out/story-1.png .. out/story-5.png, out/caption.md, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
