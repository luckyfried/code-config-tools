#!/usr/bin/env python3
"""Movement 6, last step: write out/captions.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py                  # every piece
    python3 S/scripts/deliver.py feed captions    # only the pieces the person asked for: film, cover, feed, captions,
                                                  # and for a launch stories and countdown (any of them, in any order)

captions.md has one section per piece: the film, the feed post and the share caption (one to three sentences, postable
as it is), and for a launch story 1, story 2, story 3 and the countdown. It is captions.md when the agent wrote one in
the person's voice (the same sections), otherwise drafted from taste.json in their register (their case and their own
hashtags), the share caption from the plan's share line; every section names the subject. brief.md opens with the
subject as given (its name, what it is, the date for a launch, where its pictures came from) and the plan, then their
hooks ranked by response (comments and saves), what their best-answered posts share, where the subject's colors meet
theirs, every door tried, what the run assumed, the vote, every clip and how it arrived, the music, the engine and the
critics' scores of the cut; where the person asked for a length the film could not run, one line saying the length
made and why, which deliver also prints before the reel's path. review.html opens on the reel, the cover its poster,
then the captions, the cover, the feed post and for a launch the three stories and the countdown card, then the two
looks not made, with how to ask for one. out/ holds
the deliverables and nothing else; the storyboards and the vote stay in the run folder. Where the person asked for only
some pieces, the gate runs on the whole set as always, and then out/ keeps the asked pieces and brief.md, the rest
moving to the run folder.
Exit 0 only when qa.py's gate passes; on a failed gate the page carries a red banner naming what is wrong. deliver
holds the run's lock (render/render.lock, as "deliver") from the moment it enters the run to its last write, removes
out/review.html before it writes anything into out/, and writes the page as not ready until the gate has passed. On a
passing gate the last line printed is the reel's path from the workspace root (build/<run>/out/film.mp4), or the
first asked piece's path when only some were asked, the path the reply to the person names first; on a failed gate it is "the gate failed: " and the failing checks' names, and
no path.
"""
import html
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import chunks  # noqa: E402
import qa  # noqa: E402
import storyboard  # noqa: E402
import vote  # noqa: E402

OUT = Path("out")
SECTIONS = ("film", "feed post", "share")
LAUNCH_SECTIONS = ("story 1", "story 2", "story 3", "countdown")
STILLS = (("cover.png", "cover"), ("feed.png", "feed post"), ("story-1.png", "story 1"), ("story-2.png", "story 2"),
          ("story-3.png", "story 3"), ("countdown.png", "countdown"))
# the pieces a person can ask for, and their files in out/
PIECES = {"film": ("film.mp4",), "cover": ("cover.png",), "stories": ("story-1.png", "story-2.png", "story-3.png"),
          "countdown": ("countdown.png",), "feed": ("feed.png",), "captions": ("captions.md",)}


def esc(s):
    return html.escape("" if s is None else str(s))


def subject_of(lib, taste):
    return {**(taste.get("subject") or {}), **(lib.get("subject") or {})}


def sections_for(subj):
    """The caption sections a run carries: the film, the feed post and the share caption, and a launch's stories and
    countdown."""
    return SECTIONS + (LAUNCH_SECTIONS if subj.get("launch", True) else ())


def drafts(taste, subj, opener=None):
    """The captions in their register, each naming the subject; the film's caption opens on the film's hook. The share
    caption is the plan's share line, else the subject's name and its first fact. A launch's captions carry its date;
    anything else's carry the plan's punchline where it has one."""
    subject = subj.get("name") or "it"
    launch = subj.get("launch", True)
    plan = taste.get("plan") or {}
    label = subj.get("date_label") or "soon"
    punch = (plan.get("punchline") or "").strip().rstrip(".")
    fact = next((f.strip().rstrip(".") for f in subj.get("facts") or [] if f.strip()), "")
    days = subj.get("days_to_go")
    opener = opener or (f"{subject} is almost here" if launch else punch or f"this one is for {subject}")
    reg = taste.get("register") or {}
    tags = list(dict.fromkeys(reg["hashtags"][:2] + ["#" + re.sub(r"\W", "", subject.lower())]
                              + (["#launchday"] if launch else []))) if reg.get("hashtags") else []
    tail = f"\n\n{' '.join(tags)}" if tags else ""
    share = (plan.get("share") or "").strip() or (f"{subject}: {fact}." if fact else f"Meet {subject}.")
    if subject.lower() not in share.lower():
        share = f"{subject}. {share}"
    if launch:
        count = f"{days} days until {subject}" if isinstance(days, int) and days > 0 else f"{subject} is out now"
        c = {
            "film": f"{opener}\n{subject}, out {label}." + tail,
            "story 1": f"something's coming. {subject}, {label}.",
            "story 2": f"closer. {subject} is nearly ready.",
            "story 3": f"meet {subject}. out {label}.",
            "countdown": f"{count}. {label}, set a reminder.",
            "feed post": f"{subject} is out {label}.\n{opener}" + tail,
        }
    else:
        c = {
            "film": f"{opener}\n{subject}." + (f" {fact}." if fact and fact.lower() not in opener.lower() else "") + tail,
            "feed post": f"{subject}." + (f" {punch}." if punch else f" {fact}." if fact else "") + tail,
        }
    c["share"] = share
    if reg.get("lowercase"):
        c = {k: v.lower() for k, v in c.items()}
    else:
        c = {k: v[:1].upper() + v[1:] for k, v in c.items()}
    return c


def captions(taste, subj, opener=None):
    own = Path("captions.md")
    if own.exists() and own.read_text().strip():
        return own.read_text().strip() + "\n"
    c = drafts(taste, subj, opener)
    return "\n".join(f"## {k}\n\n{c[k]}\n" for k in sections_for(subj))


def sections(text):
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", ln)
        if m:
            cur = m.group(1).strip().lower()
            out[cur] = []
        elif cur is not None:
            out[cur].append(ln)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def clip_rows(clips):
    rows = ["| clip | beat | what it is | how it arrived |", "|---|---|---|---|"]
    for cid, c in sorted(clips.items()):
        how = c["status"] if c.get("status") in ("generated", "footage") else f"stand-in: {c.get('stand_in')}"
        if c.get("why"):
            how += f" ({c['why']})"
        rows.append(f"| {cid} | {c.get('beat')} | {c.get('role')} | {how} |")
    return rows


def count(v):
    return len(v) if isinstance(v, list) else (v or 0)


def hook_rows():
    r = _env.read_json("research.json") or {}
    rows = ["| # | posted | comments | saves | response | opener | style |", "|---|---|---|---|---|---|---|"]
    for h in r.get("hooks") or []:
        rows.append(f"| {h['rank']} | {h.get('date')} ({h.get('kind')}) | {h.get('comments', '-')} | {h.get('saves', '-')} | "
                    f"{h.get('response')} | {str(h.get('hook') or '').replace('|', '/')} | {h.get('style')} |")
    return rows


def brief(lib, taste, win, clips, music, engine, cuts, length=None):
    subj = subject_of(lib, taste)
    research = _env.read_json("research.json") or {}
    subject, label = subj.get("name"), subj.get("date_label") or subj.get("date") or "no date given"
    launch = subj.get("launch", True)
    plan = taste.get("plan") or {}
    L = [f"# {subject}, a hype reel: how this was made", "", "## the subject, as you gave it", "",
         f"- Subject: {subject}" + (f", a {subj['kind']}" if subj.get("kind") else "") + "."]
    if launch:
        L.append(f"- A launch on {label}" + (f" ({subj['date']}, {subj['days_to_go']} days from the latest post)" if subj.get("date") and subj.get("days_to_go") is not None else "") + ".")
    else:
        L.append("- Not a launch, so the reel, the cover, the feed post and the share caption are made, with no teaser stories or countdown.")
    if subj.get("handle"):
        L.append(f"- Handle on the closer: {subj['handle']}.")
    L += [
         f"- Assets: {subj.get('assets') or 'none given; the subject beats use your own feed'}"
         + (f" ({count(subj.get('stills'))} stills, {count(subj.get('footage'))} clip{'' if count(subj.get('footage')) == 1 else 's'})" if subj.get("assets") else "") + "."]
    asks = (("what", "What it is"), ("for", "Who it is for"), ("apart", "What sets it apart"), ("claim", "The best true claim"),
            ("hook", "The hook"), ("punchline", "The punchline"), ("share", "The share caption"), ("tone", "The tone"))
    if any(plan.get(k) for k, _ in asks):
        L += ["", "## the plan", ""] + [f"- {name}: {plan[k]}" for k, name in asks if plan.get(k)]
    said = taste.get("said") or {}
    for k in ("subject", "audience"):
        if said.get(k):
            L.append(f"- In your words, the {k}: {said[k]}")
    about = subj.get("posts_about_it") or []
    if about:
        L.append(f"- Already in your feed: {len(about)} posts about {subject}.")
    L += ["", "## your hooks, ranked by response", "", "Response is comments plus saves per post. This is for you; the film "
          "never shows it.", ""] + hook_rows()
    shared = research.get("response_shared") or []
    if shared:
        L += ["", "## what your best-answered posts share", ""] + [f"- {x}" for x in shared]
    meet = (research.get("palette") or {}).get("meet") or []
    if meet:
        L += ["", "## where the subject's colors meet yours", "", "| subject | yours | between | reads |", "|---|---|---|---|"]
        L += [f"| {m['subject_name']} {m['subject']} | {m['theirs_name']} {m['theirs']} | {m['between']} | {m['reads']} |" for m in meet]
    L += ["", "## where your material came from", ""]
    for door, state in (lib.get("doors") or {}).items():
        L.append(f"- {door.replace('_', ' ')}: {state}")
    L += ["", "## what this run assumed", ""] + [f"- {a}" for a in lib.get("assumptions") or []]
    L += ["", "## what it learned about you", "",
          "taste.md has the whole read. In short: " + ", ".join(taste.get("pillars") or []) + "; palette "
          + ", ".join(dict.fromkeys(c["name"] for c in (taste.get("palette") or {}).get("year", []))) + "; avoid "
          + ", ".join(taste.get("avoid") or []) + ".", "",
          "## the storyboards and the vote", ""]
    tot = win.get("totals") or {}
    for i in win.get("order") or []:
        sb = _env.read_json(f"storyboards/{i}/storyboard.json") or {}
        score = f" ({tot[i]} of {len(vote.PANEL) * len(vote.CRITERIA) * 5})" if i in tot else ""
        L.append(f"- {i}, {sb.get('name')}{score}: {storyboard.LOOKS.get(sb.get('style')) or sb.get('idea')}")
    if win.get("picked_by"):
        L.append(f"- Look {win.get('board')} was picked by {win['picked_by']}" + (f": {win['why']}" if win.get("why") else "."))
    L += ["", "## your photographs in the film", ""]
    sb = _env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}
    for e in sb.get("cast") or []:
        said = f"\"{e['line']}\"" if e.get("line") else "no words of yours"
        L.append(f"- {e['part']}: your photograph {Path(e['id']).name}" + (f" of {e['date']}" if e.get("date") else "")
                 + f", with {said} on screen" + (f", chosen as {e['rule']}." if e.get("rule") else "."))
    r = sb.get("reveal") or {}
    if r.get("line"):
        L.append(f"- The reveal says \"{r['line']}\" and the subject grows out of " + (f"your photograph {Path(r['photo']).name}." if r.get("photo") else "the frame."))
    if not sb.get("cast"):
        L.append("- No photograph of yours: the film is made from the subject alone.")
    L += ["", "## the clips", ""]
    L += clip_rows(clips) if clips else ["The board asks for no clip."]
    L += ["", "## music", ""]
    if music.get("file"):
        L.append(f"- {music.get('origin')}.")
        L.append(f"- {music.get('bpm')} bpm; the cuts land on its beats; mastered to {music.get('master_lufs', -14)} LUFS.")
    else:
        L.append("- No music was found, so the film carries its sound effects alone. Add a sound when you post.")
    L += ["", "## how the film was made", ""]
    where = {True: " on the graphics card", False: " on the CPU"}.get(engine.get("card"), "")
    L.append(f"- Rendered by the kit's studio composition{where}: 1080x1920, 30 fps, H.264 High"
             + ", AAC, with a sound on every cut, photograph and title over the music."
             + " The cover is the reveal at rest and is also the film's first frame; the feed post"
             + (", the stories and the countdown card are" if launch else " is") + " the same film at rest, laid for its size.")
    if length:
        L.append(f"- {length}")
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
        bar, mean, least = vote.at_bar(last)
        if bar:
            L.append(f"- At the bar: mean {mean} of {vote.BAR} needed, lowest {least[0]}.")
        else:
            L.append(f"- Under the bar after the one fix: mean {mean} of {vote.BAR} needed, lowest {least[0]} ({least[1]}). "
                     "This is the best cut the run made.")
        if low:
            L.append("- Still below 4: " + ", ".join(sorted({k for _, k in low})) + ".")
    return "\n".join(L) + "\n"


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{title}</title><style>
body{{margin:0;background:{bg};color:{ink};font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:36px 24px 72px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{margin:40px 0 12px;font-size:20px}} .sub{{opacity:.7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.top{{display:grid;grid-template-columns:auto 1fr;gap:40px;align-items:start}}
video{{height:min(86vh,860px);aspect-ratio:9/16;border-radius:18px;background:#000;display:block}}
.posts{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;align-items:start}} .posts figure{{margin:0}} .posts figcaption{{font-size:13px;opacity:.75;margin-top:6px}}
.posts img{{width:100%;border-radius:8px;display:block}}
.looks{{display:grid;grid-template-columns:repeat(2,1fr);gap:28px}} .looks figure{{margin:0}} .looks .row{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.looks img{{width:100%;border-radius:6px;display:block}} .looks figcaption{{margin-top:8px}}
pre{{white-space:pre-wrap;background:rgba(127,127,127,.12);padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
table{{border-collapse:collapse}} td,th{{padding:6px 12px;border-bottom:1px solid rgba(127,127,127,.3);text-align:left}}
button{{background:{accent};color:{bg};border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
</style></head><body><main>
{banner}
<div class="top"><video src="film.mp4" poster="cover.png" controls playsinline loop></video><div>
<h1>{title}</h1><p class="sub">{made}</p>
<h2>Captions</h2>{caption}
<h2>How it was made</h2><p><a href="brief.md">brief.md</a> says where everything came from, which of your photographs plays
each part and why, and where the music came from.</p></div></div>
<h2>{stills}</h2>{posts}
{looks}
</main></body></html>
"""


def scored(cut):
    """A cut round whose every score was filled in; an unfilled round never reaches the brief."""
    sc = [v for e in (cut.get("critics") or {}).values() for b in (e.get("boards") or {}).values() for v in (b.get("scores") or {}).values()]
    return bool(sc) and all(isinstance(v, int) for v in sc)


def caption_html(cap):
    out = []
    for i, (k, v) in enumerate(sections(cap).items()):
        out.append(f"<h3>{esc(k)}</h3><pre id='cap{i}'>{esc(v)}</pre><button onclick=\"navigator.clipboard.writeText("
                   f"document.getElementById('cap{i}').innerText);this.textContent='Copied'\">Copy</button>")
    return "".join(out)


ORDINAL = {"1": "first", "2": "second", "3": "third"}


def looks_html(win):
    """The two looks not made, three of each one's beats at rest, so the person can ask for another."""
    figs, said = [], []
    for i in win.get("order") or []:
        sb = _env.read_json(f"storyboards/{i}/storyboard.json") or {}
        frames = sorted(Path(f"storyboards/{i}/frames").glob("*.png"))
        if i == str(win.get("board")) or not sb.get("beats") or len(frames) != len(sb["beats"]):
            continue
        imgs = "".join(f"<img src='../{frames[k].as_posix()}' loading='lazy' alt=''>" for k in storyboard.look_beats(sb))
        said.append(ORDINAL.get(i, i))
        figs.append(f"<figure><div class='row'>{imgs}</div><figcaption><b>The {ORDINAL.get(i, i)} look, {esc(sb.get('name') or '')}.</b> "
                    f"{esc(storyboard.LOOKS.get(sb.get('style'), ''))}</figcaption></figure>")
    if not figs:
        return ""
    ask = f"make the {said[0]} one" + (f"\" or \"make the {said[1]} one" if len(said) > 1 else "")
    return (f"<h2>Prefer another look?</h2><p>Say \"{ask}\" and the film is made again in that look, from the same "
            "photographs and words.</p><div class='looks'>" + "".join(figs) + "</div>")


def posts_html():
    return "<div class='posts'>" + "".join(
        f"<figure><a href='{f}'><img src='{f}' loading='lazy' alt=''></a><figcaption>{esc(name)}</figcaption></figure>"
        for f, name in STILLS if (OUT / f).exists()) + "</div>"


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    asked = sys.argv[1:]
    wrong = [a for a in asked if a not in PIECES]
    if wrong:
        sys.exit(f"deliver: no piece called {', '.join(wrong)}; the pieces are {', '.join(PIECES)}")
    _env.enter_run()
    film = _env.read_json("film.json") or {}
    only = [a for a in asked if a in ("stories", "countdown")]
    if only and not film.get("launch", True):
        sys.exit(f"deliver: there is no {' and no '.join(only)} for this reel, since it is not a launch (no date was "
                 "given); the pieces it has are film, cover, feed and captions")
    # the tools resolve before the lock, so nothing under it starts a process except through run.spawn
    _env.need("PIL")
    _env.tools()
    with chunks.lock("render", "deliver") as run:
        return deliver(run, asked)


def keep_only(asked):
    """out/ keeps the asked pieces and brief.md; every other file moves to the run folder. The kept files, in the order asked."""
    kept = [f for a in asked for f in PIECES[a]]
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name not in kept and f.name != "brief.md":
            os.replace(f, f.name)
    return kept


def deliver(run, asked=()):
    lib = _env.read_json("library.json") or {}
    taste = _env.read_json("taste.json") or {}
    win = _env.read_json("winner.json") or {}
    if not (lib and taste and win):
        sys.exit("library.json, taste.json or winner.json is missing; run the earlier movements first")
    clips = (_env.read_json("clips.json") or {}).get("clips") or {}
    music = _env.read_json("music.json") or {}
    engine = _env.read_json("engine.json") or {}
    cuts = [c for c in (_env.read_json(p) for p in vote.rounds()) if scored(c)]
    subj = subject_of(lib, taste)
    # the page that reads as delivered goes before anything in out/ changes
    OUT.mkdir(exist_ok=True)
    (OUT / "review.html").unlink(missing_ok=True)
    won = _env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}
    cap = captions(taste, subj, (won.get("hook") or {}).get("line"))
    _env.write_text(OUT / "captions.md", cap)
    length = storyboard.length_said((_env.read_json("film.json") or {}).get("seconds") or 0, storyboard.asked(taste))
    _env.write_text(OUT / "brief.md", brief(lib, taste, win, clips, music, engine, cuts, length))
    pal = (taste.get("palette") or {}).get("year") or []
    colors = (_env.read_json(f"storyboards/{win.get('board')}/storyboard.json") or {}).get("system", {}).get("colors", {})
    bg, ink, accent = colors.get("bg", "#141212"), colors.get("ink", "#f4efe8"), colors.get("accent", pal[0]["hex"] if pal else "#e6b26d")
    launch = subj.get("launch", True)
    title = f"{subj.get('name')} · " + (f"{subj.get('date_label') or 'soon'}" if launch else "Hype reel")
    made = ("Your hype reel, its cover, three teaser stories, a countdown card, a feed post and a caption for each, ready to post."
            if launch else "Your hype reel, its cover, a feed post, their captions and a share caption, ready to post.")
    stills = "The cover, the feed post, the stories and the countdown card" if launch else "The cover and the feed post"

    def page(banner):
        return PAGE.format(title=esc(title), banner=banner, caption=caption_html(cap), bg=bg, ink=ink, made=esc(made),
                           stills=esc(stills), accent=accent, posts=posts_html(), looks=looks_html(win))

    # the page says the run is not ready until the gate passes, so a deliver killed before its gate ends never leaves
    # a page that reads as delivered
    _env.write_text(OUT / "review.html", page("<div class='banner'><b>Not ready to post.</b> The checks have not passed yet: "
                                              "run deliver.py again.</div>"))
    res = qa.gate_checks(run.spawn)
    if qa.report(res, "qa/gate.json", gate=True) != 0:
        items = "".join(f"<li>{esc(name)} {esc(detail)}</li>" for name, ok, detail in res if ok is False)
        _env.write_text(OUT / "review.html", page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        # the last line names what failed and no film, so a reply copied from it never points at an unready reel
        print("the gate failed: " + ", ".join(r[0] for r in res if r[1] is False))
        return 1
    _env.write_text(OUT / "review.html", page(""))
    if asked:
        kept = keep_only(asked)
        print("delivered: " + ", ".join(f"out/{f}" for f in kept + ["brief.md"]) + "; the rest is in the run folder")
        print(Path(os.path.relpath(Path.cwd() / OUT / kept[0], _env.ROOT)).as_posix())
        return 0
    made = ["film.mp4", "cover.png"] + (["story-1.png", "story-2.png", "story-3.png", "countdown.png"] if launch else []) + \
        ["feed.png", "captions.md", "review.html", "brief.md"]
    print("delivered: " + ", ".join(f"out/{f}" for f in made))
    if length:
        print(length)
    print(Path(os.path.relpath(Path.cwd() / OUT / "film.mp4", _env.ROOT)).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
