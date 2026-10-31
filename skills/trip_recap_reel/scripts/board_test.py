"""The three boards and their checks, from the Lisbon fixture, and a second person's trip.

usage: TMPDIR=<scratch> python3 scripts/board_test.py

Lays the Lisbon fixture out twice in scratch workspaces under $TMPDIR (with coordinates, and without them, the trip a
phone with location off shares), runs gather, research, storyboard.py points, draft and check the way a person's
agent does, and asserts:
  - the three boards (cinematic letterbox, analog home movie, scrapbook) are each clean and no two looks share more
    than two of the six axes; each board's five story cards are distinct: five stops spread over a trip of five stops
    or more, the first and the last among them, else each stop and the closer;
  - nothing on a board or in its storyboard.md is a count: no running total, no ticks, no count column;
  - the person they were with reaches the research (taste.json people) and the drafted caption;
  - the trip without coordinates states no distance anywhere on a board;
  - a second person (the italy fixture, sentence case, two posts on one day) gets their own places in their own case,
    each photograph's own caption, a title and dates from their days, and legs from their coordinates, with nothing
    of the Lisbon fixture on a board, a drafted caption with no hashtag (they use none), and a brief that says their
    shared posts are all from the trip instead of comparing against an empty everyday;
then breaks a board the ways the checks exist for, and asserts each check names it:
  - two neighboring stops given the same photograph shape and points (the swap test: the design does not answer them);
  - a span of five bars, and a hook with nothing sounding in its first 30 frames;
  - a move outside the card, one move on two beats running, and every shot one length;
  - every span one length, and a span that holds more than two bars with nothing sounding (the monotony read);
and times each board to tracks from 80 to 140 bpm, and asserts every cut sits on one of the track's beats.
"""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(HERE))
FAILED = []


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILED.append(what)


def run(ws, *args):
    r = subprocess.run([sys.executable, str(HERE / args[0]), *args[1:]], cwd=ws, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        sys.exit(f"{args[0]} {' '.join(args[1:])} exited {r.returncode}")
    return r.stdout


def workspace(root, trip, coords=True, *research):
    ws = root / (trip if coords else f"{trip}-no-coordinates")
    subprocess.run([sys.executable, str(KIT / "evals/fixtures/make_trip.py"), str(ws), "--trip", trip,
                    *([] if coords else ["--no-coordinates"])], check=True, capture_output=True)
    run(ws, "gather.py", "--door", "handed=open: the posts the person handed over")
    run(ws, "research.py", *research)
    R = ws / "build" / (ws / "build/RUN").read_text().strip()
    if trip == "lisbon":
        t = json.loads((R / "taste.json").read_text())
        t["names"] = {"Graca, Lisbon": "graça", "Belem, Lisbon": "belém", "Lisbon": "lisboa"}
        (R / "taste.json").write_text(json.dumps(t))
    (R / "taste.md").write_text("**You are** a traveler.\n\n**You like** slow light.\n\n**Your style is** muted.\n\n"
                                "**Your voice is** plain.\n\n**Avoid** stock footage.\n")
    run(ws, "storyboard.py", "points")
    run(ws, "storyboard.py", "draft")
    return ws, R


def person_cases(b, ws, R):
    """Every name, caption and date on screen is the person's own: computed from their posts, nothing else."""
    import math
    import deliver
    posts = json.loads((ws / "pulled/items.json").read_text())["posts"]
    r = b["route"]
    ok([s["name"] for s in r["stops"]] == [p["place"] for p in posts],
       f"italy: the stops are the posts' places in their own case ({', '.join(s['name'] for s in r['stops'])})")
    caps = [p["caption"] for p in posts]
    if b["system"]["closer"] == "closing-flicker":
        held = max(i for i, c in enumerate(caps) if i and c)
        ok(r["signoff"] == caps[held], f"italy {b['style']}: the closing line is the last stop's own line ({r['signoff']!r})")
        caps[held] = ""
    ok([s["caption"] for s in r["stops"]] == caps,
       f"italy {b['style']}: each photograph carries its own post's caption, two posts on one day included")
    ok(r["title"] == "Bolzano to Lago di Campotosto" and r["kicker"] == "2 to 5 jun 2026",
       f"italy: the title and dates come from the route and the posts' days ({r['title']}; {r['kicker']})")
    def gc(a, c):
        (la1, lo1), (la2, lo2) = (map(math.radians, x) for x in (a, c))
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 2 * 6371.0088 * math.asin(math.sqrt(h))
    want = [gc(posts[i - 1]["geo"], p["geo"]) if i else 0.0 for i, p in enumerate(posts)]
    ok(all(abs(s["leg"] - w) < 0.6 for s, w in zip(r["stops"], want)),
       f"italy: the map's legs are the distances between the posts' coordinates ({', '.join(str(round(s['leg'])) for s in r['stops'])} km)")
    text = json.dumps(b, ensure_ascii=False).lower()
    ok(not re.search(r"mara|lisbo|alfama|gra[cç]a|bel[eé]m|sintra|bairro|\bsep\b", text),
       "italy: nothing from the lisbon fixture reaches the board")
    here = os.getcwd()
    os.chdir(R)
    try:
        taste = json.loads((R / "taste.json").read_text())
        cap = deliver.caption(taste, {})
        lines = "\n".join(deliver.trip_lines(taste))
    finally:
        os.chdir(here)
    ok("#" not in cap, f"italy: a person who uses no hashtags gets a caption with none ({cap.strip()!r})")
    ok([d["places"] for d in json.loads((R / "trip.json").read_text())["days"]][2] == [],
       "italy: the day with no posts names no place")
    ok(not re.search(r"\bNone\b", lines) and "posts you shared are all from the trip" in lines,
       "italy: with no posts from other days the brief says so and prints no empty comparison")


LOOKS = ("1", "2", "3")


def board(R, n="1"):
    return json.loads((R / f"storyboards/{n}/storyboard.json").read_text())


def with_cases(R):
    """The person they were with, read from their captions, reaches the research and the drafted caption."""
    import deliver
    taste = json.loads((R / "taste.json").read_text())
    ok(taste.get("people") == ["ines.draws"], f"lisbon: the person tagged on three days is the trip's people ({taste.get('people')})")
    ok([m["with"] for m in taste.get("moments") or []] == [["ines.draws"], [], [], ["ines.draws"], ["ines.draws"]] and
       all(set(m) == {"date", "place", "with", "line"} for m in taste["moments"]),
       "lisbon: each moment is a place's line with who is in it, nothing counted")
    here = os.getcwd()
    os.chdir(R)
    try:
        cap = deliver.caption(taste, {})
    finally:
        os.chdir(here)
    ok("with @ines.draws" in cap, f"lisbon: the drafted caption names who they were with ({cap.strip()!r})")
    ok(cap.lower().count("lisbon") == 1 and "alfama, graça, belém, sintra and bairro alto" in cap.lower(),
       f"lisbon: the drafted caption names the trip's city once and each place without it ({cap.strip()!r})")


def clean(ws, R, label):
    """Each of the three boards clean, the looks apart, its story cards distinct and nothing on it a count."""
    import storyboard
    out = run(ws, "storyboard.py", "check")
    lines = [ln for ln in out.splitlines() if ln.startswith("board ")]
    ok(len(lines) == 3 and all("no faults" in ln for ln in lines), f"{label}: " + ("; ".join(lines) or "no board lines"))
    ok(not any(ln.startswith("looks:") for ln in out.splitlines()), f"{label}: no two looks share more than two axes")
    boards = [board(R, n) for n in LOOKS]
    for n, b in zip(LOOKS, boards):
        st = storyboard.film_of(b, {}, "reel")["stories"]
        k = len(b["route"]["stops"])
        ends = (st[0], st[-1]) == ("hook", f"stop-{k}") if k >= 5 else st[-1] == "closer"
        ok(len(set(st)) == len(st) == 5 and ends, f"{label} board {n}: five distinct story cards ({', '.join(st)})")
        said = json.dumps({x: v for x, v in b.items() if x != "source"}, ensure_ascii=False) + (R / f"storyboards/{n}/storyboard.md").read_text()
        ok(not re.search(r"\b(count|total|ticks|unit)\b", said), f"{label} board {n}: nothing on the board or in storyboard.md is a count")
    return boards


def says(issues, pattern, what):
    hit = next((s for s in issues if re.search(pattern, s)), None)
    ok(hit is not None, f"{what}: " + (hit or "; ".join(issues[:2]) or "no fault found"))


def check_cases(b):
    import board_trip
    import storyboard
    sw = copy.deepcopy(b)
    a, c = sw["source"]["stops"][2], sw["source"]["stops"][3]
    c["aspect"], c["long"], c["points"], c["clip"] = a["aspect"], a.get("long"), copy.deepcopy(a["points"]), a.get("clip")
    says(storyboard.check_board(sw)[1], r"^swap: .* come out the same", "swap: two neighboring stops with one shape and one set of points are refused")
    real = board_trip.board
    def five(src, card):
        out = real(src, card)
        out["beats"][1]["bars"] = 5
        return out
    def quiet(src, card):
        out = real(src, card)
        out["sound"] = [x for x in out["sound"] if x["at"] * 30 * 60 / out["bpm"] > 30]
        return out
    for broken, pattern, what in ((five, r"^structure: stop-2 runs 5 bars", "structure: a span of five bars is refused"),
                                  (quiet, r"hook has nothing sounding", "structure: a hook with nothing in its first 30 frames is refused")):
        board_trip.board = broken
        try:
            says(storyboard.check_board(b)[1], pattern, what)
        finally:
            board_trip.board = real
    beats = copy.deepcopy(storyboard.solve(b)["beats"])
    beats[2]["move"] = "spin-zoom"
    says(storyboard.look_findings(b, beats), r"spin-zoom", "look: a move outside the card is refused")
    beats = copy.deepcopy(storyboard.solve(b)["beats"])
    beats[2]["move"] = beats[1]["move"]
    says(storyboard.look_findings(b, beats), re.escape(beats[1]["move"]), "look: one move on two beats running is refused")
    beats = copy.deepcopy(storyboard.solve(b)["beats"])
    for x in beats:
        x["bars"] = 2
    says(storyboard.look_findings(b, beats), r"every shot runs within", "look: every shot one length is refused")
    f = storyboard.film_of(b, {}, "reel")
    flat = copy.deepcopy(f)
    for x in flat["beats"]:
        x["frames"], x["bars"] = 120, 2
    says(storyboard.monotony(flat), r"every shot runs within", "monotony: every span one length is refused")
    gap = copy.deepcopy(f)
    gap["beats"][1]["bars"] = 3
    start = 4 * gap["beats"][0]["bars"]
    gap["sound"] = [x for x in gap["sound"] if not start < x["at"] < start + 12]
    says(storyboard.monotony(gap), r"stop-2 holds .* with nothing sounding", "monotony: a span with nothing sounding is refused")
    ok(board_trip.km(0) == "0" and board_trip.km(0.3) == "1" and board_trip.km(2.6) == "3",
       f"leg: 0 km is written {board_trip.km(0)}, 0.3 km {board_trip.km(0.3)}, 2.6 km {board_trip.km(2.6)}")
    r0 = storyboard.solve(b)["route"]["stops"][0]
    ok(r0["leg"] == 0 and r0["compass"] is None, "leg: the first stop has no leg")
    for n in (2, 3):
        short = copy.deepcopy(b)
        short["source"]["stops"] = short["source"]["stops"][:n]
        sf = storyboard.film_of(dict(short, **storyboard.solve(short)), {}, "reel")
        at = [sf["rests"][k] for k in sf["stories"]]
        ok(len(set(sf["stories"])) == 5 and sf["stories"][-1] == "closer" and at == sorted(at) and len(set(at)) == 5,
           f"stories: a trip of {n} stops gives five cards at five moments in film order ({', '.join(sf['stories'])})")


def tempo_cases(b):
    import storyboard
    for bpm in (80, 100, 120, 140):
        f = storyboard.film_of(b, {"bpm": bpm, "downbeats": [0.25]}, "reel")
        beat = 60.0 / f["bpm"] * storyboard.FPS
        whole = all(abs(x["frames"] / beat - round(x["frames"] / beat)) < 0.2 for x in f["beats"])
        ok((bpm % f["bpm"] == 0 or f["bpm"] % bpm == 0) and whole and f["music_offset"] == 0.25,
           f"tempo: {b['style']} on a {bpm} bpm track cuts at {f['bpm']:g} bpm, {f['seconds']:.1f} s, every cut on its beats")


def main():
    base = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix="board-test-") as root:
        root = Path(root)
        ws, R = workspace(root, "lisbon", True, "--place", "lisbon")
        boards = clean(ws, R, "lisbon")
        with_cases(R)
        for b in boards:
            check_cases(b)
            tempo_cases(b)
        ws2, R2 = workspace(root, "lisbon", False, "--place", "lisbon")
        for n, b2 in zip(LOOKS, clean(ws2, R2, "lisbon without coordinates")):
            text = json.dumps({k: v for k, v in b2.items() if k != "source"}, ensure_ascii=False) + (R2 / f"storyboards/{n}/storyboard.md").read_text()
            ok(not re.search(r"\bkm\b", text) and not b2["route"]["mapped"], f"lisbon without coordinates: board {n} states no distance")
        ws3, R3 = workspace(root, "italy", True, "--from", "2026-06-02", "--to", "2026-06-05")
        for b3 in clean(ws3, R3, "italy"):
            person_cases(b3, ws3, R3)
    print(f"{'FAILED' if FAILED else 'passed'}: {len(FAILED)} failing")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
