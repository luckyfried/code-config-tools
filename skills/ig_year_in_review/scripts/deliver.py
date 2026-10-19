#!/usr/bin/env python3
"""Step 8: write out/caption.md, out/brief.md and out/review.html, then run the gate.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/deliver.py

caption.md is the caption paragraph from build/story.json plus its hashtags. brief.md lists every assumption the
run made (where the data came from, the year, the handle, how the top posts were ranked, what was missing, the
critic's scores). review.html is one page that plays the video and shows the ten cards and the caption. Exit 0
only when qa.py gate passes; on a failed gate the page carries a red banner naming what is wrong.
"""
import html
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

BUILD, OUT = Path("build"), Path("out")
HERE = Path(__file__).resolve().parent


def esc(s):
    return html.escape("" if s is None else str(s))


def caption(story):
    tags = " ".join(story.get("hashtags") or [])
    return f"{str(story.get('caption', '')).strip()}\n\n{tags}\n"


def brief(data, stats, pal, story, plan, tl, critic):
    lines = [f"# {stats.get('handle') or 'Your'} year in review, {stats['year']}: what this run assumed", ""]
    for a in data.get("assumptions") or []:
        lines.append(f"- {a}")
    found = data.get("found") or {}
    if found:
        have = [k for k, v in found.items() if v]
        miss = [k for k, v in found.items() if not v]
        lines.append(f"- Found in the data: {', '.join(have) or 'nothing'}.")
        if miss:
            lines.append(f"- Not in the data, so left out: {', '.join(miss)}.")
    by = stats.get("top_ranked_by")
    lines.append({"likes": "- Top posts are ranked by likes, then comments, from the export's own post insights.",
                  "comments": "- The export has no like counts per post, so top posts are ranked by comments received.",
                  }.get(by, "- The data has no likes or comments per post, so the three posts shown are the best photos "
                            "spread across the year."))
    b, q = stats.get("busiest") or {}, stats.get("quietest") or {}
    if b:
        lines.append(f"- Busiest month is the one with the most posts ({b.get('name')}, {b.get('posts')}); quietest is "
                     f"the fewest among months with any activity ({q.get('name')}, {q.get('posts')}).")
    if stats.get("people"):
        lines.append("- Your people are the accounts you commented on plus the accounts you tagged in captions.")
    if stats.get("loved"):
        lines.append("- What you loved counts the posts you liked, by account.")
    if pal.get("year"):
        lines.append("- The palette is the five most common colors across the year's photos, named plainly: "
                     + ", ".join(f"{c['name']} {c['hex']}" for c in pal["year"]) + ".")
    chapters = plan.get("chapters") or []
    skipped = [c for c in ["opener", "numbers", "top", "months", "people", "loved", "palette", "closer"] if c not in chapters]
    if skipped:
        lines.append(f"- Chapters left out because the data has nothing for them: {', '.join(skipped)}.")
    lines.append(f"- The video is {tl.get('seconds')} s, {len(tl.get('chapters') or [])} chapters, 24 fps, "
                 + ("with the music file you gave." if tl.get("music") else "with no sound (add your own music when you "
                    "post, or rerun with --music <file>)."))
    lines.append("- The words on the cards are written in your own style, read from your captions"
                 + (f" ({'all lowercase' if (stats.get('register') or {}).get('lowercase_share', 0) >= 0.6 else 'sentence case'})."))
    if critic.get("rounds"):
        last = critic["rounds"][-1]
        lines.append(f"- Self-review, round {last['round']}: " + ", ".join(f"{k} {v}/5" for k, v in last["scores"].items())
                     + (f". Fixed: {last['fixed']}" if last.get("fixed") else "") + ".")
    lines += ["", "Nothing was sent anywhere: every file was made on this computer from your own download."]
    return "\n".join(lines) + "\n"


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>
body{{margin:0;background:#141212;color:#f4efe8;font:16px/1.5 system-ui,sans-serif}}
main{{max-width:1180px;margin:0 auto;padding:32px 24px 64px}}
h1{{font-size:28px;margin:0 0 4px}} .sub{{color:#b9b1a7;margin:0 0 24px}}
.banner{{background:#b3261e;color:#fff;padding:14px 18px;border-radius:10px;margin-bottom:20px}}
.ok{{background:#1f5f3a}}
.top{{display:grid;grid-template-columns:360px 1fr;gap:32px;align-items:start}}
video{{width:360px;border-radius:14px;background:#000}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:32px}}
.cards a img{{width:100%;border-radius:8px;display:block}}
pre{{white-space:pre-wrap;background:#221f1e;padding:16px;border-radius:10px;font:15px/1.5 system-ui,sans-serif}}
button{{background:{accent};color:#141212;border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer}}
.files li{{margin:2px 0}}
</style></head><body><main>
<h1>{title}</h1><p class="sub">Your video, your ten carousel cards and a caption, ready to post.</p>
{banner}
<div class="top"><video src="{mp4}" controls playsinline loop muted></video><div>
<h2>Caption</h2><pre id="cap">{caption}</pre><button onclick="navigator.clipboard.writeText(document.getElementById('cap').innerText);this.textContent='Copied'">Copy caption</button>
<h2>Files</h2><ul class="files">{files}</ul>
<h2>What this run assumed</h2><pre>{brief}</pre></div></div>
<h2>Carousel</h2><div class="cards">{cards}</div>
</main></body></html>
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    data = _env.read_json(BUILD / "data.json") or {}
    stats = _env.read_json(BUILD / "stats.json")
    story = _env.read_json(BUILD / "story.json")
    plan = _env.read_json(BUILD / "cuts.json")
    tl = _env.read_json(BUILD / "timeline.json") or {}
    if not (stats and story and plan):
        sys.exit("build/stats.json, build/story.json or build/cuts.json is missing; run the earlier steps first")
    pal = _env.read_json(BUILD / "palette.json") or {}
    critic = _env.read_json(BUILD / "critic.json", {"rounds": []})
    OUT.mkdir(exist_ok=True)
    (OUT / "caption.md").write_text(caption(story))
    br = brief(data, stats, pal, story, plan, tl, critic)
    (OUT / "brief.md").write_text(br)
    handle, year = plan["handle"], plan["year"]
    mp4 = f"{handle}-{year}-year-in-review.mp4"
    cards = [f"{handle}-{year}-carousel-{n:02d}.png" for n in range(1, 11)]

    def page(banner):
        files = [mp4] + cards + ["caption.md", "brief.md"]
        return PAGE.format(title=esc(f"@{handle} · {year} year in review"), banner=banner, mp4=esc(mp4),
                           caption=esc(caption(story)), brief=esc(br), accent=(pal.get("roles") or {}).get("accent", "#e6b26d"),
                           files="".join(f"<li><a href='{esc(f)}'>{esc(f)}</a></li>" for f in files if (OUT / f).exists()),
                           cards="".join(f"<a href='{esc(c)}'><img src='{esc(c)}' loading='lazy'></a>" for c in cards))

    (OUT / "review.html").write_text(page(""))
    g = subprocess.run([sys.executable, str(HERE / "qa.py"), "gate"], capture_output=True, text=True)
    print(g.stdout.strip())
    if g.returncode != 0:
        items = "".join(f"<li>{esc(ln[5:])}</li>" for ln in g.stdout.splitlines() if ln.startswith("FAIL "))
        (OUT / "review.html").write_text(page(f"<div class='banner'><b>Not ready to post.</b><ul>{items}</ul></div>"))
        print("deliver: the gate failed; fix what it names and run deliver.py again", file=sys.stderr)
        return 1
    print(f"delivered: out/{mp4}, out/{cards[0]} .. out/{cards[-1]}, out/caption.md, out/review.html, out/brief.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
