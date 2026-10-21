#!/usr/bin/env python3
"""Movement 2: the storyboard of the nine, laid out for the reel, the square and the wide.
Also the step that cuts the storyboard to the music.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft  --run R             # storyboards/<tone>/board-{reel,square,wide}.json + storyboard.md
    python3 S/scripts/storyboard.py check  --run R             # the bounds check, the length and the hook, every board
    python3 S/scripts/storyboard.py sheets --run R             # storyboards/<tone>/sheet.png: the hook, the densest beat and the closer at rest
    python3 S/scripts/storyboard.py snap   --run R             # the storyboard at the music's tempo -> film.json

The kit has one tone (scripts/tones/):
  drive  the cut                      each photograph is cut along its own line, its count standing on the edge
Each board is the storyboard the studio composition (motion/studio) renders: the rank order, the layout (the cuts
and their edges), and every photograph by its focus and crop from picks.json. One storyboard gives all three formats: the layout is solved again for each frame, never
scaled to fit. Each board names its rests (the hook, the densest beat, an ordinary count beat and the
closer), the settled frames the sheets and the stills are taken from.

The words are the person's: taste.json `words.<tone>` replaces any default below, in their case and voice.
check fails a board on any bounds finding (type outside the safe area, cut by the frame or run onto a photograph; a
slice too thin to read; a bar over a count; a count under its floor), a length outside the band, or a hook
event after frame 30. storyboard.md states each board's cuts and cuts per minute as figures for the critics.
"""
import argparse
import calendar
import datetime as dt
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import bounds  # noqa: E402
import compose  # noqa: E402

TONES = ("drive",)
BOARDS = Path("storyboards")
FPS = compose.FPS
HOOK_FRAMES = 30
LENGTH = (15, 30)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨️‍]")
STOP = {"and", "i", "the", "a", "an", "to", "of", "be", "will", "not", "in", "on", "at", "with", "for", "is", "it", "my",
        "but", "so", "just", "then", "that", "this", "all", "you", "we", "or", "by", "from", "like"}


def words_default(year):
    nxt = f"see you in {year + 1}"
    return {"drive": {"total": "likes on my nine.", "head": "my nine, cut to size.", "promise": nxt, "ask": "share yours"}}


def tone_module(tone):
    return importlib.import_module(f"tones.{tone}")


def length_band(n):
    """The film's length band: 15-30 s for nine posts; fewer posts make a shorter film, so the floor scales with them."""
    return (round(LENGTH[0] * min(9, n) / 9, 2), LENGTH[1])


def board_for(tone, posts, fmt, words, handle, year, bpm=None):
    """The board for `posts` (rank order) in format `fmt`, and its plan: {board, scenes, cuts, hook_frame, rests,
    seconds}. Rests map hook, dense and closer to the frame each comes to rest at."""
    m = tone_module(tone)
    bpm = bpm or m.BPM
    fr = compose.Frame(fmt)
    r = m.build(posts, fr, words, handle, year, bpm)
    beats = compose.shots(r["scenes"], r["end"], bpm, r["drift"])
    b = compose.board({"tone": tone, "handle": handle, "year": year, "bpm": bpm, "system": r["system"]}, fr, beats)
    for key in ("sound", "clips"):
        if r.get(key):
            b[key] = r[key]
    starts, f = {}, 0
    for beat in beats:
        starts[beat["id"]] = (f, beat["frames"])
        f += beat["frames"]
    # a rest is its shot's last frames, or as many beats into the shot as the tone's rest_at names for it
    at = r.get("rest_at") or {}
    rests = {k: starts[v][0] + (round(at[k] * compose.pulse_of(bpm)) if k in at else starts[v][1] - 2)
             for k, v in r["rests"].items() if v in starts}
    return {"board": b, "scenes": r["scenes"], "cuts": compose.cuts_of(r["scenes"], beats), "hook_frame": round(r["hook"] * compose.pulse_of(bpm)),
            "rests": rests, "rest_beats": r["rests"], "seconds": round(f / FPS, 2), "frames": f}


def short(cap, limit=60):
    """A caption's lead line for the screen: no hashtags or emoji, cut at a clause or a word, never on a function word."""
    c = EMOJI.sub("", re.sub(r"#\w+", "", cap or "")).strip()
    c = re.sub(r"\s+", " ", c)
    for sep in (". ", ": ", "; ", " - "):
        if sep in c and len(c.split(sep)[0]) >= 14:
            c = c.split(sep)[0]
            break
    if len(c) > limit and ", " in c[:limit] and len(c[:limit].rsplit(", ", 1)[0]) >= 14:
        c = c[:limit].rsplit(", ", 1)[0]
    if len(c) > limit:
        c = c[:limit].rsplit(" ", 1)[0]
    w = c.split()
    while len(w) > 3 and w[-1].lower().strip(",.") in STOP:
        w.pop()
    return " ".join(w).strip(" ,;:-")


class Run:
    """The run's nine as the posts the tones lay out, with the handle, the year and the words."""

    def __init__(self):
        self.stats = _env.read_json("stats.json")
        self.picks = _env.read_json("picks.json")
        if not self.stats or not self.picks:
            sys.exit("stats.json or picks.json is missing: run research.py first")
        self.taste = _env.read_json("taste.json") or {}
        self.year = int(self.stats["year"])
        self.handle = "@" + (self.stats.get("handle") or "you").lstrip("@")
        self.lower = bool((self.taste.get("register") or {}).get("lowercase", True))
        info = {n["rank"]: n for n in self.picks["nine"]}
        self.posts = []
        for t in self.stats["top_nine"]:
            n = info.get(t["rank"])
            if not n or t.get("likes") is None:
                continue
            d = dt.date.fromisoformat(t["date"])
            cap = short(t.get("caption") or "") or f"{calendar.month_name[d.month].lower()} {d.day}"
            self.posts.append({"rank": len(self.posts) + 1, "caption": cap.lower() if self.lower else cap, "likes": t["likes"],
                               "date": f"{d.day} {calendar.month_abbr[d.month].lower()}", "doy": d.timetuple().tm_yday,
                               "file": n["file"], "aspect": n["aspect"], "focus": n["focus"], "crop": n["crop"], "line": n.get("line")})
        if not self.posts:
            sys.exit("none of the nine has a photograph and a like count: the storyboards need at least one")

    def words(self, tone):
        w = dict(words_default(self.year)[tone])
        w.update((self.taste.get("words") or {}).get(tone) or {})
        return w

    def plan(self, tone, fmt, bpm=None):
        return board_for(tone, [dict(p) for p in self.posts], fmt, self.words(tone), self.handle, self.year, bpm)


def board_hash(boards):
    return hashlib.sha256(json.dumps(boards, sort_keys=True).encode()).hexdigest()[:16]


def write_tone(run, tone, bpm=None):
    """The tone's three boards and its storyboard.md; returns the plans by format."""
    d = BOARDS / tone
    d.mkdir(parents=True, exist_ok=True)
    plans = {fmt: run.plan(tone, fmt, bpm) for fmt in compose.FORMATS}
    for fmt, p in plans.items():
        _env.write_json(d / f"board-{fmt}.json", p["board"])
    _env.write_json(d / "plan.json", {fmt: {k: v for k, v in p.items() if k not in ("board", "scenes")} for fmt, p in plans.items()})
    reel = plans["reel"]
    lines = [f"# {tone}: {tone_module(tone).__doc__.strip().splitlines()[0]}", "",
             f"{len(run.posts)} posts, {reel['board']['bpm']} bpm, {reel['seconds']} s, {len(reel['cuts'])} cuts "
             f"({len(reel['cuts']) / (reel['seconds'] / 60):.1f} a minute), the hook at frame {reel['hook_frame']}.", "",
             "| shot | starts | seconds | words |", "|---|---|---|---|"]
    f = 0
    for sc, beat in zip(reel["scenes"], reel["board"]["beats"]):
        said = [ln["text"] for L in beat["layers"] if L["kind"] == "Words" for ln in L["lines"]]
        held = f" (held: {sc['held']})" if sc.get("held") else ""
        lines.append(f"| {beat['id']}{' (continues)' if sc.get('same') else ''}{held} | {f / FPS:.2f} s | {beat['frames'] / FPS:.2f} | {' / '.join(said)[:90]} |")
        f += beat["frames"]
    if any(sc.get("reveals") for sc in reel["scenes"]):
        lines += ["", "What each move reveals, and what it carries across the cut:", "", "| shot | reveals | carries |", "|---|---|---|"]
        lines += [f"| {sc['id']} | {sc['reveals']} | {sc['carries']} |" for sc in reel["scenes"] if sc.get("reveals")]
    b = reel["board"]
    if b.get("sound"):
        sec = 60 / b["bpm"]
        lines += ["", f"Sound, placed at named beats (music.py synthesises each and mixes it under the bed; {len(b['sound'])} cues):", "",
                  "| at | beat | cue | what |", "|---|---|---|---|"]
        lines += [f"| {c['at'] * sec:.2f} s | {c['beat']} | {c['kind']} | {c['what']} |" for c in b["sound"]]
    if b.get("clips"):
        lines += ["", "Generated clips (clips.py list asks the video model for them; clips.py normalize places what arrives):", "",
                  "| clip | beat | role | seconds | prompt | in its place until it arrives |", "|---|---|---|---|---|---|"]
        lines += [f"| {c['id']} | {c['beat']} | {c['role']} | {c['seconds']} | {c['prompt']} | {c['stand_in']} |" for c in b["clips"]]
    lines += ["", "Rests (the sheet and the stills): " + ", ".join(f"{k} {reel['rest_beats'][k]} at frame {v}" for k, v in reel["rests"].items()), "",
              "The words, from taste.json `words." + tone + "` over the defaults: " + json.dumps(run.words(tone), ensure_ascii=False), "",
              "The photographs (focus and square crop from picks.json):", ""]
    lines += [f"- {p['rank']}. {p['likes']} likes, {p['date']}, \"{p['caption']}\": {p['file']} focus {p['focus']} crop {p['crop']}" for p in run.posts]
    (d / "storyboard.md").write_text("\n".join(lines) + "\n")
    return plans


def findings(tone, plans, n):
    out = []
    lo, hi = length_band(n)
    for fmt, p in plans.items():
        out += [f"{fmt}: {x}" for x in bounds.check(p["board"])]
        if not lo <= p["seconds"] <= hi:
            out.append(f"{fmt}: {p['seconds']} s is outside {lo}-{hi} s")
        if p["hook_frame"] > HOOK_FRAMES:
            out.append(f"{fmt}: the hook event lands at frame {p['hook_frame']}, after frame {HOOK_FRAMES}")
    return out


def load_plans(tone):
    d = BOARDS / tone
    if not (d / "board-reel.json").exists():
        sys.exit(f"{d}/board-reel.json is missing: run storyboard.py draft")
    meta = _env.read_json(d / "plan.json")
    return {fmt: dict(meta[fmt], board=_env.read_json(d / f"board-{fmt}.json")) for fmt in compose.FORMATS}


def cmd_draft(a, run):
    for tone in TONES:
        plans = write_tone(run, tone)
        bad = findings(tone, plans, len(run.posts))
        r = plans["reel"]
        print(f"{tone}: {r['seconds']} s, {len(r['cuts'])} cuts, hook at frame {r['hook_frame']}, {len(bad)} findings -> {BOARDS / tone}/")
        for x in bad[:8]:
            print("   ", x)
    return 0


def cmd_check(a, run):
    bad = 0
    n = len(run.posts)
    for tone in TONES:
        f = findings(tone, load_plans(tone), n)
        bad += len(f)
        print(f"{'PASS' if not f else 'FAIL'}  {tone}: {len(f)} findings")
        for x in f[:20]:
            print("   ", x)
    return 1 if bad else 0


def cmd_sheets(a, run):
    import studio
    _env.need("PIL")
    from PIL import Image
    jobs = []
    for tone in TONES:
        p = load_plans(tone)["reel"]
        for k in ("hook", "dense", "closer"):
            jobs.append(studio.still(p["board"], p["rests"][k], BOARDS / tone / "frames" / f"{k}.png", scale=0.5))
    rep = studio.render(jobs, "sheets")
    for tone in TONES:
        ims = [Image.open(BOARDS / tone / "frames" / f"{k}.png") for k in ("hook", "dense", "closer")]
        w, h = ims[0].size
        sheet = Image.new("RGB", (3 * w + 4 * 12, h + 24), "white")
        for i, im in enumerate(ims):
            sheet.paste(im.convert("RGB"), (12 + i * (w + 12), 12))
        sheet.save(BOARDS / tone / "sheet.png")
        print(f"{tone}: {BOARDS / tone / 'sheet.png'} (the hook, the densest beat and the closer, each at rest)")
    return 1 if rep["failed"] else 0


def cmd_snap(a, run):
    tone = TONES[0]
    music = _env.read_json("music.json") or {}
    base = tone_module(tone).BPM
    lo, hi = length_band(len(run.posts))
    bpm, why = base, f"the {tone} tempo, {base} bpm (no music tempo)"
    if music.get("bpm"):
        best = None
        for k in (0.5, 1, 2):
            cand = round(music["bpm"] * k, 2)
            p = run.plan(tone, "reel", cand)
            if lo <= p["seconds"] <= hi and (best is None or abs(cand - base) < abs(best - base)):
                best = cand
        if best:
            bpm, why = best, f"the music's {music['bpm']} bpm" + (f" at {best / music['bpm']:g}x" if best != music["bpm"] else "")
    plans = write_tone(run, tone, bpm)
    bad = findings(tone, plans, len(run.posts))
    boards = {fmt: str(BOARDS / tone / f"board-{fmt}.json") for fmt in compose.FORMATS}
    reel = plans["reel"]
    downs = music.get("downbeats") or []
    film = {"tone": tone, "bpm": bpm, "tempo": why, "seconds": reel["seconds"], "frames": reel["frames"],
            "music_start": downs[0] if downs else 0.0, "hook_frame": reel["hook_frame"], "cuts": reel["cuts"],
            "rests": {fmt: p["rests"] for fmt, p in plans.items()}, "boards": boards, "findings": bad,
            "hash": board_hash({fmt: p["board"] for fmt, p in plans.items()})}
    _env.write_json("film.json", film)
    print(f"{tone} at {bpm} bpm ({why}): {reel['seconds']} s, {len(reel['cuts'])} cuts, hook at frame {reel['hook_frame']}, "
          f"{len(bad)} findings -> film.json")
    for x in bad[:10]:
        print("   ", x)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check", "sheets", "snap"])
    _env.run_arg(ap)
    a = ap.parse_args()
    _env.enter_run(a.run)
    run = Run()
    return {"draft": cmd_draft, "check": cmd_check, "sheets": cmd_sheets, "snap": cmd_snap}[a.cmd](a, run)


if __name__ == "__main__":
    sys.exit(main())
