#!/usr/bin/env python3
"""Movement 6, last step: write out/brand.json, out/caption.md and out/review.html, and the run's notes in brief.md
beside out/, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

brand.json is brand.json, copied as it stands. out/plan.md is written by brand.py plan and only checked here.
caption.md is caption.md when the agent wrote one in the person's voice, otherwise a short caption drafted from
brand.json in their register (their case, their own hashtags) to post with the film or the stills. brief.md, in the
run folder and never in out/, says where the material came from (every door tried, open or closed), what the run
assumed, what the read found (palette, type, pillars, cadence, voice, what to stop), what each beat of the film shows,
the three looks and the pick, where the music came from, how the film was rendered, and the critics' scores of the cut
against the bar, with what is left under it when the one fix was spent. review.html is the film's cover: it opens on
the reel with its cover (the story card) as the poster, then the square and wide films, the story card and the posted
image, the stills when they were asked for, the caption to copy, the other two looks with how to ask for one, how the
film was made in plain words, and the brand: the palette as color, the voice, what they like elsewhere and what to stop.
The page carries no score: the scores are in brief.md.
Exit 0 only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong. Every file
reaches out/ by rename of a finished file, and the page goes first with a banner saying the gate has not passed, so a
deliver stopped part way never leaves out/ reading as delivered; only a passing gate writes the page without it. On a
green gate its last line is the reel's path from the project's root (build/<run>/out/film.mp4), the path the reply
names first; on a failed gate it is "not ready: the gate failed on" and the failing checks, and no path.
"""
import contextlib
import html
import io
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import qa  # noqa: E402
import studio  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")
SIZES = {"film.mp4": "1080x1920", "film-square.mp4": "1080x1080", "film-wide.mp4": "1920x1080"}


def put(files):
    """Each out/<name> as its text, or a copy of the file when it is a Path: every one made beside out/ first, then all
    moved in by rename."""
    stage = OUT.with_name("out.deliver")
    for name, x in files.items():
        (stage / name).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(x, Path):
            shutil.copyfile(x, stage / name)
        else:
            (stage / name).write_text(x)
    for name in files:
        (OUT / name).parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage / name, OUT / name)


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(brand, taste):
    own = Path("caption.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    reg = taste.get("register") or {}
    lines = ["one sentence, found in my photographs", brand.get("statement") or "", "what's yours?"]
    body = "\n".join(x for x in lines if x)
    body = body.lower() if reg.get("lowercase") else body[:1].upper() + body[1:]
    tags = list(dict.fromkeys((reg.get("hashtags") or [])[:3]))
    return body + ("\n\n" + " ".join(tags) if tags else "") + "\n"


def found_rows(brand):
    pct = lambda x: f"{round(100 * (x or 0))}%"
    pal = ", ".join(f"{c['name']} {c['hex']} ({c.get('role')}, {pct(c.get('share'))})" for c in brand.get("palette") or [])
    ty = brand.get("type") or {}
    cad = brand.get("cadence") or {}
    slots = ", ".join(f"{s['day']} {s['time']}" for s in cad.get("slots") or [])
    voice = brand.get("voice") or {}
    L = [f"- Statement: {brand.get('statement')}",
         f"- Palette: {pal}.",
         *([f"- Type: {ty.get('display')} for headlines, {ty.get('text')} for text" + (f": {ty['why']}." if ty.get('why') else ".")]
           if ty.get("display") else []),
         "- Compositions: " + ", ".join(brand.get("compositions") or []) + ".",
         "- Pillars: " + ", ".join(f"{p['name']} {pct(p.get('share'))}" for p in brand.get("pillars") or []) + ".",
         f"- Cadence: {cad.get('per_week')} posts a week; best slots {slots} ({cad.get('timezone')}).",
         f"- Voice: {voice.get('case')}, about {voice.get('avg_words')} words a caption; "
         + ", ".join(d["name"] for d in voice.get("devices") or []) + "."]
    asp = brand.get("aspire") or {}
    if asp:
        L.append("- What you like elsewhere: " + ", ".join(asp.get("subjects") or []) + ".")
    for s in brand.get("stop") or []:
        L.append(f"- Stop: {s.get('line')}, because {s.get('why')}.")
    return L


def film_rows(board):
    """What the film shows, beat by beat: its words and the photograph under them (the reel's board)."""
    L = ["", "## what the film shows", ""]
    faces = compose.card(board["style"])["faces"] if (board or {}).get("style") else {}
    if faces:
        L += [f"Set in {faces['display']['family']} for the lines and {faces['text']['family']} for the labels, the look's two faces.", ""]
    for x in (board or {}).get("beats") or []:
        words = x.get("say") or x.get("words") or ""
        pic = (x.get("picture") or {}).get("file")
        what = {"hook": "the hook", "ask": "the ask", "closer": "the sign-off"}.get(x["id"], f"moment {x['id'][1:]}")
        L.append(f"- {what}, {x['frames'] / 30:.1f} s: " + (f"\"{words}\"" if words else (board.get("signoff") or "the closer"))
                 + (f" over {pic}" if pic else "") + ".")
    return L + ["", "The shares and counts are in brand.json; the film shows none of them."]


def looks_rows(win):
    data = _env.read_json("vote/scores.json") or {}
    L = []
    for letter in storyboard.letters():
        b = _env.read_json(storyboard.BOARDS / letter / "board-reel.json") or {}
        vs = [v for c in (data.get("critics") or {}).values() for v in (((c.get("boards") or {}).get(letter) or {}).get("scores") or {}).values()
              if isinstance(v, int)]
        score = f", the critics' mean {sum(vs) / len(vs):.2f} of 5" if vs else ""
        L.append(f"- {letter.upper()}, {b.get('name')}{score}" + (" (the film)" if letter == win.get("board") else "")
                 + f". storyboards/{letter}/storyboard.md has its beats.")
    L.append(f"- Picked by {'their taste' if win.get('by') == 'taste' else 'the person'}" + (f": {win['why']}" if win.get("why") else "") + ".")
    return L


def brief(lib, taste, brand, win, music, render, film, cut, cuts, board):
    handle = brand.get("handle") or lib.get("handle")
    L = [f"# @{handle}, personal brand kit: how this was made", "", "## what the read found", ""] + found_rows(brand)
    L += film_rows(board)
    L += ["", "out/brand.json holds this; out/plan.md is the next 30 days.", "", "## where your material came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. It avoids " + (", ".join(taste.get("avoid") or []) or "nothing named") + ".", "",
          "## the three looks", ""] + looks_rows(win)
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; {film.get('tempo')}; a sound where a line lands, mixed under the music and mastered "
                 f"to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film is silent. Add a sound when you post.")
    L += ["", "## how the film was made", "",
          f"- {film.get('name')}, {film.get('seconds')} s at {film.get('bpm')} bpm, {(cut.get('measured') or {}).get('cuts')} cuts, rendered by the "
          "kit's studio composition at 30 fps, H.264: "
          + ", ".join(f"out/{n} ({size})" for n, size in SIZES.items() if (OUT / n).exists())
          + ". Each format is laid out for its own frame, not cropped from another."]
    L.append("- out/story.png is the reel's cover, the hook as it settles; out/post.png is the square's peak moment with its line, the image to post.")
    if (OUT / "stills.json").exists():
        L.append("- out/stills/ holds every beat of the square film at rest, in the film's order, for a carousel.")
    for k, r in (render or {}).items():
        L.append(f"- {k}: {r.get('seconds')} s wall, {r.get('cpu_seconds')} CPU-seconds{' on the graphics card' if r.get('gpu') else ''}.")
    L += ["", "## the critics on the cut", "", f"The bar: a mean of {vote.BAR_MEAN} over every score and no score under {vote.BAR_MIN}.", ""]
    if not cuts:
        L.append("- Not scored yet.")
    for c in cuts:
        for who, sc in vote.scores_of(c).items():
            L.append(f"- Round {c.get('round')}, {vote.CUT_PANEL.get(who, who)}: " + ", ".join(f"{k} {v}" for k, v in sc.items()) + ".")
        if all(isinstance(v, int) for sc in vote.scores_of(c).values() for v in sc.values()):
            mean, low = vote.at_bar(c)
            L.append(f"- Round {c.get('round')}: mean {mean:.2f}, lowest {low}, " + ("at the bar." if mean >= vote.BAR_MEAN and low >= vote.BAR_MIN else "under the bar."))
        if c.get("fixed"):
            L.append(f"- Fixed before round {c.get('round')}: {c['fixed']}")
    v = _env.read_json("critic/verdict.json") or {}
    if v.get("verdict") == "spent":
        L.append(f"- The one fix was spent in round {v.get('round')}, so this is the best cut, delivered under the bar. "
                 f"What holds it under: {v.get('what')}")
    return "\n".join(L) + "\n"


ORDINAL = ("first", "second", "third")


def thumb(path, width=200):
    """A frame as an inline JPEG, so the page carries the other looks without a file of its own in out/."""
    import base64
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def other_looks(win):
    """The two looks the film was not made in, each as its hook, a middle beat and its closer."""
    letters = storyboard.letters()
    rest = [l for l in letters if l != win.get("board")]
    if not rest:
        return ""
    cards = []
    for l in rest:
        b = _env.read_json(storyboard.BOARDS / l / "board-reel.json") or {}
        frames = [storyboard.BOARDS / l / "frames" / f"{k}.png" for k in ("hook", "middle", "closer")]
        imgs = "".join(f"<img src='{thumb(f)}' alt=''>" for f in frames if f.exists())
        cards.append(f"<figure><div class='strip'>{imgs}</div><figcaption>The {ORDINAL[letters.index(l)]} look: {esc(b.get('name'))}"
                     "</figcaption></figure>")
    ask = ORDINAL[letters.index(rest[0])]
    return (f"<h2>Prefer another look? Say 'make the {ask} one'</h2><p>The same story in the two other looks. Say which, and the film "
            "is made again in it: its own music, its own cut, the same words and photographs.</p>"
            f"<div class='looks'>{''.join(cards)}</div>")


def made_how(lib, taste, brand, film, music, board):
    """How the film was made, in plain words, without a number the person did not give."""
    sysm = (board or {}).get("system") or {}
    shows = [x for x in (board or {}).get("beats") or [] if (x.get("picture") or {}).get("file")]
    L = [f"Everything in it is yours: the opening line is in your own words, the photographs are {len(shows)} of your own posts, "
         "and the question at the end is the kind you ask in your captions.",
         f"The look is {esc(film.get('name'))}: {esc(sysm.get('display', {}).get('family'))} for the big words and "
         f"{esc(sysm.get('text', {}).get('family'))} for the small ones, in your own colors.",
         ("The music was made for this film, " + esc(music.get("origin")).rstrip(".") + "." if music.get("file") else
          "The film is silent; add a sound when you post.")]
    if taste.get("avoid"):
        L.append("It keeps clear of what you said you avoid: " + esc(", ".join(taste["avoid"])) + ".")
    return "<h2>How it was made</h2>" + "".join(f"<p>{x}</p>" for x in L)


def swatches(colors):
    return "<div class='sw'>" + "".join(f"<span><i style='background:{esc(c['hex'])}'></i>{esc(c['name'])}</span>" for c in colors) + "</div>"


def the_brand(brand):
    voice = brand.get("voice") or {}
    devices = [d["name"] for d in voice.get("devices") or []][:4]
    asp = brand.get("aspire") or {}
    out = ["<h2>Your brand</h2>", f"<p class='stmt'>{esc(brand.get('statement'))}</p>", "<h3>Your palette</h3>", swatches(brand.get("palette") or []),
           "<h3>Your voice</h3>",
           f"<p>{esc(voice.get('case') or 'your own case')}, about {round(voice.get('avg_words') or 0)} words a caption"
           + (", with " + esc(", ".join(devices)) if devices else "") + ".</p>"]
    if asp:
        out += ["<h3>What you like elsewhere</h3>", swatches(asp.get("palette") or []),
                f"<p>{esc(', '.join(asp.get('subjects') or []))}.</p>"]
    if brand.get("stop"):
        out += ["<h3>What to stop</h3><ul>"] + [f"<li>{esc(s.get('line'))}: {esc(s.get('why'))}.</li>" for s in brand["stop"]] + ["</ul>"]
    return "".join(out)


def gallery(paths, cls):
    return f"<div class='{cls}'>" + "".join(f"<a href='{esc(p)}'><img src='{esc(p)}' loading='lazy' alt=''></a>" for p in paths) + "</div>"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:420px 1fr;gap:36px;align-items:start}}
video{{width:420px;border-radius:16px;background:#000;display:block}}
.formats{{display:grid;grid-template-columns:1fr 1.78fr;gap:18px;align-items:start}} .formats video{{width:100%}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}}
.posts img{{width:100%;border-radius:8px;display:block}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
.looks{{display:grid;grid-template-columns:1fr 1fr;gap:24px}} .strip{{display:flex;gap:8px}} .strip img{{width:32%;border-radius:8px}}
figure{{margin:0}} figcaption{{margin-top:8px;opacity:.8}} h3{{margin:22px 0 8px;font-size:16px}} .stmt{{font-size:20px}}
.sw{{display:flex;flex-wrap:wrap;gap:14px}} .sw span{{display:flex;align-items:center;gap:8px}}
.sw i{{display:inline-block;width:44px;height:44px;border-radius:8px;border:1px solid rgba(127,127,127,.35)}}
</style></head><body><main>
{banner}
<div class="top"><video src="film.mp4" poster="story.png" controls playsinline loop></video><div>
<h1>{title}</h1><p class="sub">Your statement, found in your own photographs, in three shapes, with its story card, the
image to post{also}, your brand file and the next 30 days.</p>
<h2>Caption</h2><pre id="cap">{caption}</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<p><a href="brand.json">brand.json</a> holds your whole brand system, and <a href="plan.md">plan.md</a> is the next 30 days.</p></div></div>
<h2>Square and wide</h2><div class="formats"><video src="film-square.mp4" poster="post.png" controls playsinline loop></video>
<video src="film-wide.mp4" controls playsinline loop></video></div>
<h2>The cover and the image to post</h2><div class="posts"><a href="story.png"><img src="story.png" alt=""></a><a href="post.png"><img src="post.png" alt=""></a></div>
{extras}{looks}{how}{brand}</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    _env.enter()
    # the run's lock from here to the last write, so no render changes out/ while the page and the gate are made
    with studio.lock("deliver") as run:
        return deliver(run)


def deliver(run):
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    brand = _env.read_json("brand.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and brand and win):
        sys.exit("library.json, taste.json, brand.json or winner.json is missing; "
                 "run the earlier movements first")
    music = _env.read_json("music.json") or {}
    render = _env.read_json("render.json") or {}
    film = _env.read_json("film.json") or {}
    cut = _env.read_json("cut.json") or {}
    cuts = [_env.read_json(p) for p in vote.rounds()]
    cap = caption(brand, taste)
    pal = brand.get("palette") or []
    board = _env.read_json(film["boards"]["reel"]) if film.get("boards") else {}
    colors = (board or {}).get("system", {}).get("colors", {})
    bg, ink = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8")
    accent = colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    handle = brand.get("handle") or lib.get("handle")
    # the stills only when the render made them, as the person asked for them
    stills = [s["file"] for s in (_env.read_json(OUT / "stills.json") or {}).get("stills", [])]
    extras = ("<h2>The stills</h2>" + gallery(stills, "posts")) if stills else ""
    also = ", the stills" if stills else ""
    made = list(SIZES) + ["story.png", "post.png"] + (["stills/"] if stills else [])

    looks, how, mine = other_looks(win), made_how(lib, taste, brand, film, music, board), the_brand(brand)

    def page(banner):
        return PAGE.format(title=esc(f"@{handle} · personal brand kit"), banner=banner, caption=esc(cap), bg=bg, ink=ink, accent=accent,
                           also=also, extras=extras, looks=looks, how=how, brand=mine)

    put({"review.html": page("<div class='banner'><b>Not ready to post.</b> The gate has not passed yet.</div>")})
    put({"brand.json": Path("brand.json"), "caption.md": cap})
    _env.write_text("brief.md", brief(lib, taste, brand, win, music, render, film, cut, cuts, board))
    # the gate runs in this process under this lock, so every probe it starts holds the lock too
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        failed = qa.gate(run)
    print(said.getvalue().strip())
    if failed:
        items = "".join(f"<li>{esc(ln[6:])}</li>" for ln in said.getvalue().splitlines() if ln.startswith("FAIL "))
        put({"review.html": page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>")})
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        print("not ready: the gate failed on " + ", ".join(dict.fromkeys(ln.split()[1] for ln in said.getvalue().splitlines() if ln.startswith("FAIL "))))
        return 1
    put({"review.html": page("")})
    print("delivered: " + ", ".join(f"out/{n}" for n in made + ["brand.json", "plan.md", "caption.md", "review.html"]) + "; the run's notes in brief.md")
    print(Path(os.path.relpath(Path.cwd() / OUT / "film.mp4", _env.ROOT)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
