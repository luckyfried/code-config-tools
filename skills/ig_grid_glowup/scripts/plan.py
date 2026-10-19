#!/usr/bin/env python3
"""Movement 5: the posting plan for the winning direction's nine, with a caption in their voice for each and a date.

USAGE (from the workspace root; S = this skill's folder):
    python3 S/scripts/plan.py draft    # build/plan.json + out/plan.md from build/winner.json and the board's nine
    python3 S/scripts/plan.py check    # validates build/plan.json and rewrites out/plan.md; exit 0 only when it holds

draft puts the nine in posting order (post 1 goes up first and ends at the bottom right of the nine; post 9 lands at
the top left), dates them from their own cadence (research.json: the weekday and hour they post most, and the median
gap between their last 30 posts, kept between one and seven days), and gives each a draft caption: the words that
came with that photo, else the nearest post's, plus two of their usual hashtags in turn. A slot filled by a generated
still, a type post or a color tile carries a note saying so.
The drafts are a starting point. Write each caption fresh in their voice (build/taste.md: their register, length,
lowercase or not, emoji or not) by editing the "caption" fields of build/plan.json, then run check. check refuses a
plan without nine slots in order 1 to 9 on rising dates, a caption that is empty, a placeholder, too long, out of
their register, a repeat of another slot, or word for word the caption of a post already on their grid.
"""
import argparse
import datetime as dt
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

PLACEHOLDER = re.compile(r"TODO|TBD|lorem|ipsum|\{\{|\}\}|XXX|PLACEHOLDER|undefined|NaN|\bNone\b|caption here", re.I)
TAG = re.compile(r"#\w+")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAX_WORDS = 40


def plain(text):
    return re.sub(r"\s+", " ", TAG.sub("", text or "")).strip().lower()


def winner_board():
    win = _env.read_json("build/winner.json") or {}
    if not win.get("board"):
        sys.exit("no winner: run vote.py tally first")
    b = _env.read_json(f"build/storyboards/{win['board']}/storyboard.json")
    if not b:
        sys.exit(f"build/storyboards/{win['board']}/storyboard.json is missing")
    return b


def cadence():
    cad = (_env.read_json("build/research.json") or {}).get("cadence") or {}
    ts = sorted(c["ts"] for c in (_env.read_json("build/grid.json") or {}).get("cells", []) if c.get("ts"))
    gaps = [(b - a) / 86400 for a, b in zip(ts, ts[1:])]
    gap = min(7, max(1, round(statistics.median(gaps)))) if gaps else 3
    last = dt.datetime.fromtimestamp(ts[-1], dt.timezone.utc).date() if ts else dt.date.today()
    weekday = cad.get("top_weekday") if cad.get("top_weekday") in DAYS else None
    hour = cad.get("top_hour_utc") if isinstance(cad.get("top_hour_utc"), int) else 18
    return {"weekday": weekday, "hour_utc": hour, "gap_days": gap, "after": str(max(last, dt.date.today()))}


def dates(cad):
    day = dt.date.fromisoformat(cad["after"]) + dt.timedelta(days=1)
    if cad["weekday"]:
        while DAYS[day.weekday()] != cad["weekday"]:
            day += dt.timedelta(days=1)
    return [day + dt.timedelta(days=cad["gap_days"] * i) for i in range(9)]


def note_for(p):
    if p.get("still"):
        return ("a generated still in your palette stands in here, because your library had no photo for this spot; "
                "swap in your own shot of the same light and color if you have one")
    if p["kind"] == "type":
        return "your own words set as a post: this is the quiet beat between photos"
    if p["kind"] == "color":
        return "a color tile with your line on it, in the middle of the nine"
    return ""


def cmd_draft(a):
    b = winner_board()
    cad = cadence()
    tags = [t for t in ((_env.read_json("build/taste.json") or {}).get("register") or {}).get("hashtags", []) if t.startswith("#")][:3]
    slots = []
    for k, (p, day) in enumerate(zip(sorted(b["posts"], key=lambda p: p["n"]), dates(cad))):
        cap = re.sub(r"\s+", " ", TAG.sub("", p.get("caption") or "")).strip()
        slots.append({"n": p["n"], "date": str(day), "weekday": DAYS[day.weekday()], "time_utc": f"{cad['hour_utc']:02d}:00",
                      "file": f"posts/{p['n']:02d}.png", "kind": p["kind"], "still": bool(p.get("still")),
                      "grid_spot": grid_spot(p["n"]), "caption": cap, "note": note_for(p),
                      "hashtags": list(dict.fromkeys(tags[(k + j) % len(tags)] for j in range(2))) if tags else []})
    plan = {"board": b["id"], "name": b["name"], "handle": b.get("handle"), "cadence": cad, "drafted": True, "slots": slots}
    _env.write_json("build/plan.json", plan)
    write_md(plan)
    print(f"plan for direction {b['id']} ({b['name']}): nine posts from {slots[0]['date']} to {slots[-1]['date']}, every "
          f"{cad['gap_days']} day(s) at {cad['hour_utc']:02d}:00 UTC -> build/plan.json, out/plan.md. Now write each caption "
          "fresh in their voice in build/plan.json and run plan.py check")
    return 0


def grid_spot(n):
    slot = 9 - n
    return f"row {slot // 3 + 1}, {['left', 'middle', 'right'][slot % 3]}"


def problems(plan):
    bad = []
    slots = plan.get("slots") or []
    if [s.get("n") for s in slots] != list(range(1, 10)):
        bad.append(f"the plan needs nine slots in posting order 1 to 9 (got {[s.get('n') for s in slots]})")
    days = [s.get("date") or "" for s in slots]
    if any(not x for x in days) or days != sorted(days) or len(set(days)) != len(days):
        bad.append("every slot needs its own date, rising from post 1 to post 9")
    reg = (_env.read_json("build/taste.json") or {}).get("register") or {}
    old = {plain(c.get("caption")) for c in (_env.read_json("build/grid.json") or {}).get("cells", []) if c.get("caption")}
    seen = set()
    for s in slots:
        cap = (s.get("caption") or "").strip()
        body = plain(cap)
        where = f"post {s.get('n')}"
        if not body:
            bad.append(f"{where}: the caption is empty")
            continue
        if PLACEHOLDER.search(cap):
            bad.append(f"{where}: the caption carries a placeholder")
        if len(body.split()) > MAX_WORDS:
            bad.append(f"{where}: the caption runs {len(body.split())} words; keep it under {MAX_WORDS}")
        if reg.get("lowercase") and TAG.sub("", cap) != TAG.sub("", cap).lower():
            bad.append(f"{where}: they write in lowercase; this caption has capitals")
        named = [d.lower() for d in DAYS if re.search(rf"\b{d.lower()}", body)]
        if named and (s.get("weekday") or "").lower() not in named:
            bad.append(f"{where}: the caption says {named[0]} but the post goes up on a {s.get('weekday')}")
        if body in seen:
            bad.append(f"{where}: the same caption as another slot")
        if body in old:
            bad.append(f"{where}: word for word the caption of a post already on their grid; write a new line in their voice")
        seen.add(body)
    return bad


def cmd_check(a):
    plan = _env.read_json("build/plan.json")
    if not plan:
        sys.exit("build/plan.json is missing: run plan.py draft")
    bad = problems(plan)
    if bad:
        print("the plan does not hold yet:")
        for x in bad:
            print("  -", x)
        return 1
    plan["drafted"] = False
    _env.write_json("build/plan.json", plan)
    write_md(plan)
    print(f"plan ok: nine captions in order, {plan['slots'][0]['date']} to {plan['slots'][-1]['date']} -> out/plan.md")
    return 0


def write_md(plan):
    cad = plan["cadence"]
    stills = [s["n"] for s in plan["slots"] if s.get("still")]
    lines = [f"# Your next nine: {plan['name']}", "",
             ("Post them in this order, one a day" if cad["gap_days"] == 1 else f"Post them in this order, one every {cad['gap_days']} days") + (f", starting on a {cad['weekday']}" if cad.get("weekday") else "")
             + f", around {cad['hour_utc']:02d}:00 UTC, the hour you post most. "
             "Post 1 goes up first and ends at the bottom right of the nine; post 9 goes up last and lands at the top "
             "left. `grid-after.png` shows how your profile will look when all nine are up.", ""]
    if stills:
        lines += [f"Post{'s' if len(stills) > 1 else ''} {', '.join(map(str, stills))} {'use' if len(stills) > 1 else 'uses'} "
                  "a generated still in your palette, because your library had no photo that fit that spot. Swap in your "
                  "own shot of the same light and color if you have one.", ""]
    lines += ["| # | date | file | where it lands | caption |", "|---|---|---|---|---|"]
    for s in plan["slots"]:
        cap = (s["caption"] + (" " + " ".join(s["hashtags"]) if s.get("hashtags") else "")).replace("|", "/")
        lines.append(f"| {s['n']} | {s['weekday'][:3]} {s['date']}, {s['time_utc']} UTC | `{s['file']}` | {s['grid_spot']} | {cap} |")
    notes = [s for s in plan["slots"] if s.get("note")]
    if notes:
        lines += ["", "## notes", ""] + [f"- Post {s['n']}: {s['note']}." for s in notes]
    lines.append("")
    Path("out").mkdir(exist_ok=True)
    Path("out/plan.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["draft", "check"])
    a = ap.parse_args()
    return {"draft": cmd_draft, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
