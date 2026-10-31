#!/usr/bin/env python3
"""Movement 2: the trip as stops, three storyboards built from them in three looks, checked, styleframed and timed.

USAGE (from the workspace root; S = this skill's folder; the files named below are in the run's folder, build/<run>/):
    python3 S/scripts/storyboard.py points            # points.json + points.png: the picked points of every stop's photograph
    python3 S/scripts/storyboard.py draft             # match the photographs, source.json, storyboards/1/ to 3/, checked;
                                                      # removes the vote, the pick, the timed films and the style sheets first
    python3 S/scripts/storyboard.py check [--board N] # re-solve the boards from their source and check them (exit 1 on a fault)
    python3 S/scripts/storyboard.py sheets [--board N]
                                                      # storyboards/N/frames/{hook,middle,closer}.png, storyboards/N/sheet.png
                                                      # and out/boards.png, the three looks side by side for the person
    python3 S/scripts/storyboard.py snap              # the picked board (winner.json) on the music's tempo: film.json,
                                                      # film-landscape.json, film-square.json (exit 1 when the monotony
                                                      # read refuses the cut)

The looks: a run drafts the trip in three looks, each a style card (styles/<id>.json; styles/catalog.md says each in a
sentence). By default they are cinematic-letterbox, analog-home-movie and scrapbook; taste.json `style` names the look
the person asked for, which becomes board 1, and boards 2 and 3 take the two of those three that differ most from it.
Every board is the same story (board_trip.py) told in its card: its faces, its palette rule's colors, its moves and
cuts chosen beat by beat from what each beat holds, its easing and finish, its music recipe's tempo, and its closer.

The stops (source.json, and the `source` of every board): one per place of the trip in route order (trip.json), each
with the photograph that shows it (picks.json; a place with only a clip takes the clip's poster), the day, date and
time of that post, their caption, the place's coordinates, the name on screen and the photograph's picked points.
taste.json `names` maps a place or a city as the data spells it to the name the film sets ({"Graca, Lisbon": "graça",
"Lisbon": "lisboa"}); without an entry the name is the place's first part in their case. taste.json `label` overrides
the trip's label ("lisbon week").

points: every stop's photograph's two points in fractions of it: near, where they stood, and far, what the photograph
  looks at (the camera moves through the photograph from near toward far, and its words sit away from far), and sees,
  what the photograph shows, what in it would move and its light, which its clip request is written from. near
  defaults to the middle of the lower ground, far to where its detail and skin tones are, and sees is empty; look at
  points.png and the photographs, correct points.json by eye and write every sees before draft: these points are the
  design's reason.

check re-solves each board from its source and its card (so an edit goes in the source) and refuses:
  swap       two neighboring stops whose beats come out the same with their photographs traded: the design does not
             answer its photographs
  structure  a span outside 1 to 4 bars, or a hook with nothing sounding in its first 30 frames
  look       a face not in the board's card, a move or cut outside the card's allowlist, a color the card's palette rule
             did not make, the same move on two beats running, every shot within 10 % of one length, or the words in
             one place (top, middle or bottom) on more than 70 % of the beats that carry words
  looks      two of the three boards whose cards share more than 2 of the 6 axes

snap times the picked board at the music's tempo (doubled or halved into the octave around the board's, from the track's
first downbeat) and reads the timed cut for monotony before anything renders: it refuses a span that holds more than
two bars with nothing sounding.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import board_trip  # noqa: E402
import film  # noqa: E402
import grade  # noqa: E402
import palette  # noqa: E402
import studio  # noqa: E402
import style  # noqa: E402

FPS = 30
BOARDS = Path("storyboards")
NUMBERS = ("1", "2", "3")
SHEET_GAP, SHEET_HEAD = 24, 170  # out/boards.png: the space around each look's row, and its heading over its frames
FORMATS = ("reel", "landscape", "square")
SAFE = json.loads((_env.SKILL / "design" / "safe-areas.json").read_text())
MONTHS = "jan feb mar apr may jun jul aug sep oct nov dec".split()
DAYS = "mon tue wed thu fri sat sun".split()
SPREAD = 0.1  # every shot within this share of one length is a template's rhythm


# ------------------------------------------------------------------ the stops
def jround(x):
    return int(math.floor(x + 0.5))


def say(text, taste):
    return text.lower() if (taste.get("register") or {}).get("lowercase") else text


def display(name, taste):
    names = taste.get("names") or {}
    if name in names:
        return names[name]
    return say(name.split(",")[0].strip(), taste)


def city_of(place, taste):
    parts = [p.strip() for p in place.split(",")]
    if len(parts) < 2:
        return None
    return (taste.get("names") or {}).get(parts[1]) or say(parts[1], taste)


def label_of(name, days, taste):
    if taste.get("label"):
        return taste["label"]
    name = say(name, taste)
    if name.split()[-1] in ("day", "weekend", "week", "trip", "holiday", "break") or " to " in name:
        return name
    if days <= 1:
        return f"a day in {name}"
    if days <= 3:
        return f"{name} weekend"
    return f"{name} week" if days <= 9 else f"{name} trip"


def range_of(a, b):
    if a.month == b.month:
        return f"{a.day} to {b.day} {MONTHS[b.month - 1]}"
    return f"{a.day} {MONTHS[a.month - 1]} to {b.day} {MONTHS[b.month - 1]}"


def stop_photos():
    """[(place, photo file in photos/, unix time of its post, caption)] in route order."""
    trip, picks = _env.read_json("trip.json") or {}, _env.read_json("picks.json") or {}
    if not trip or not picks:
        sys.exit("trip.json and picks.json are missing: run research.py first")
    by_place = {p["name"]: p for p in picks.get("places") or []}
    items = [it for d in trip.get("days") or [] for it in d.get("items") or []]
    src_of = picks.get("source_of") or {}
    out = []
    for pl in trip.get("places") or []:
        photos = (by_place.get(pl["name"]) or {}).get("photos") or []
        clip = next((c for c in picks.get("clips") or [] if c.get("place") == pl["name"] and c.get("poster")), None)
        if photos:
            ph = photos[0]
            media = src_of.get(ph)
            # the photograph's own post: its words and its time, never another post's
            it = next((i for i in items if media and media in (i.get("media") or [])), {})
            out.append((pl, ph, it.get("ts"), it.get("caption") or (picks.get("caption_of") or {}).get(ph, "")))
        elif clip:
            out.append((pl, clip["poster"], clip.get("ts"), clip.get("caption") or ""))
    return out


def clip_of(photo):
    """Their own clip whose poster is `photo`, if the stop is shown by one."""
    picks = _env.read_json("picks.json") or {}
    return next((c["file"] for c in picks.get("clips") or [] if c.get("poster") == photo and c.get("file")), None)


def public_name(photo):
    return f"matched/{Path(photo).name}"


def build_source():
    taste = _env.read_json("taste.json") or {}
    trip = _env.read_json("trip.json") or {}
    points = _env.read_json("points.json")
    if not points:
        sys.exit("points.json is missing: run storyboard.py points, look at points.png and correct points.json first")
    from PIL import Image
    start = dt.date.fromisoformat(trip["from"])
    stops = []
    for pl, ph, ts, cap in stop_photos():
        when = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc) if ts else None
        # the photograph's own date; the place's first day only when its post carries no time
        day = when.date().isoformat() if when else (pl.get("days") or [trip["from"]])[0]
        d = dt.date.fromisoformat(day)
        stem = Path(ph).stem
        if stem not in points:
            sys.exit(f"points.json has no entry for {stem} ({pl['name']}): run storyboard.py points again")
        with Image.open(Path("public") / public_name(ph)) as im:
            w, h = im.size
        with Image.open(ph) as im:
            long = max(im.size)
        p = {k: v for k, v in points[stem].items() if k in ("near", "far")}
        stops.append({"name": display(pl["name"], taste), "place": pl["name"], "city": city_of(pl["name"], taste), "photo": public_name(ph),
                      "aspect": round(h / w, 4), "long": long, "date": f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}",
                      "time": when.strftime("%H:%M") if when else "", "caption": say(cap or "", taste),
                      "day": (d - start).days + 1, "lat": pl.get("lat"), "lon": pl.get("lon"), "points": p,
                      "sees": points[stem].get("sees") or ""})
        if clip_of(ph):
            stops[-1]["clip"] = clip_of(ph)
    if len(stops) < 2:
        sys.exit(f"the trip has {len(stops)} stop with a photograph; a trip film needs two or more")
    first, last = (dt.date.fromisoformat(trip["from"]) + dt.timedelta(days=s["day"] - 1) for s in (stops[0], stops[-1]))
    name = (taste.get("trip") or {}).get("name") or trip.get("name") or "the trip"
    return {"stops": stops, "handle": taste.get("handle") or "you",
            "trip": {"name": name, "label": label_of(name, (last - first).days + 1, taste), "range": range_of(first, last), "year": first.year}}


def fmt_of(name):
    """A picture's size and rate, by the safe area's name."""
    return {"width": SAFE[name]["width"], "height": SAFE[name]["height"], "fps": FPS, "name": name}


def looks(taste):
    """The run's three looks, board 1's first: the look taste.json `style` names, or the default three."""
    return style.three((taste or {}).get("style"))


def make_board(n, look, source, taste):
    """Board `n`: the trip told in the look `look`, every color made by the card's palette rule from the photographs'
    swatches."""
    c = style.card(look)
    made = style.colors(c, palette.swatches_of(taste, _env.read_json("palette.json")))
    system = style.system(c, made["roles"])
    system["colors"]["swatches"] = [{"hex": h, "name": ""} for h in made["swatches"]]
    return dict({"id": n, "style": look, "look": c["name"], "sentence": style.sentence(look),
                 "name": f"{source['trip']['label']} · {c['name']}", "idea": board_trip.__doc__.split(". ")[0].strip() + ".",
                 "year": source["trip"]["year"], "format": fmt_of("reel"), "system": system, "palette": made["made"],
                 "source": source}, **board_trip.board(source, c))


# ------------------------------------------------------------------ points
def saliency(im):
    """A map of where a photograph's detail is, on a 64 px grid: edge energy, color, and skin tones three times over."""
    from PIL import ImageFilter
    sm = im.convert("RGB").resize((64, max(1, round(64 * im.size[1] / im.size[0]))))
    w, h = sm.size
    edges = sm.convert("L").filter(ImageFilter.FIND_EDGES).load()
    hsv = sm.convert("HSV").load()
    rgb = sm.load()
    vals = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = rgb[x, y]
            skin = r > 95 and g > 40 and b > 20 and r > g and r > b and r - g > 15 and max(r, g, b) - min(r, g, b) > 15
            vals[y][x] = edges[x, y] / 255 * (0.5 + hsv[x, y][1] / 255) + (1.5 if skin else 0)
    k = 4
    blur = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            ys, xs = range(max(0, y - k), min(h, y + k + 1)), range(max(0, x - k), min(w, x + k + 1))
            blur[y][x] = sum(vals[j][i] for j in ys for i in xs) / (len(ys) * len(xs))
    return blur, w, h


def peaks(blur, w, h, n=1, apart=0.18):
    cells = sorted(((blur[y][x], (x + 0.5) / w, (y + 0.5) / h) for y in range(h) for x in range(w)), reverse=True)
    out = []
    for v, u, t in cells:
        if all(math.hypot(u - a, t - b) > apart for a, b in out) and 0.06 < u < 0.94 and 0.06 < t < 0.94:
            out.append((round(u, 3), round(t, 3)))
        if len(out) == n:
            break
    return out or [(0.5, 0.5)]


def default_points(path):
    from PIL import Image
    with Image.open(path) as im:
        blur, w, h = saliency(im)
    sx, sy = peaks(blur, w, h)[0]
    return {"near": [0.5, 0.86], "far": [sx, sy], "sees": ""}


def cmd_points(a):
    from PIL import Image, ImageDraw
    have = _env.read_json("points.json") or {}
    rows = stop_photos()
    if len(rows) < 2:
        sys.exit(f"the trip has {len(rows)} place with a photograph; a trip film needs two or more: name the places with "
                 "research.py --place, or hand over photographs that carry where they were taken")
    out = {}
    for pl, ph, _, cap in rows:
        stem = Path(ph).stem
        out[stem] = have.get(stem) or {"place": pl["name"], "caption": cap, **default_points(ph)}
    _env.write_json("points.json", out)
    tiles = []
    for pl, ph, _, _ in rows:
        p = out[Path(ph).stem]
        im = Image.open(ph).convert("RGB")
        im.thumbnail((640, 640))
        w, h = im.size
        d = ImageDraw.Draw(im)
        f = _env.pil_font(18, "text")
        for key, col in (("near", (255, 255, 255)), ("far", (255, 120, 255))):
            u, v = p[key]
            d.ellipse([u * w - 10, v * h - 10, u * w + 10, v * h + 10], outline=col, width=4)
            d.text((u * w + 12, v * h + 4), key, fill=col, font=f)
        d.rectangle([0, 0, w, 30], fill=(0, 0, 0))
        d.text((8, 5), f"{Path(ph).stem} · {pl['name']}", fill=(255, 255, 255), font=f)
        tiles.append(im)
    W = sum(t.size[0] for t in tiles) + 12 * (len(tiles) + 1)
    H = max(t.size[1] for t in tiles) + 24
    sheet = Image.new("RGB", (W, H), (30, 30, 30))
    x = 12
    for t in tiles:
        sheet.paste(t, (x, 12))
        x += t.size[0] + 12
    sheet.save("points.png")
    kept = sum(1 for s in out if s in have)
    print(f"points.json: {len(out)} photographs ({kept} kept as you set them, {len(out) - kept} from the default rule); "
          f"look at points.png and the photographs, correct points.json by eye and write what each one sees before draft")
    return 0


# ------------------------------------------------------------------ draft and check
def solve(board, src=None):
    """The board's own parts solved again from its source (or `src`) in its card."""
    return board_trip.board(src or board["source"], style.card(board["style"]))


def look_findings(board, beats, frames=None):
    """What breaks the board's look: a face not in its card, a move or cut outside the card's allowlist, a color the
    card's palette rule did not make, the same move on two beats running, every shot within SPREAD of one length (in
    frames when timed, else in bars), and the words in one place on more than MOST_IN_ONE of the beats that carry words."""
    c, s, out = style.card(board["style"]), board["system"], []
    for k in ("display", "text"):
        if (s[k]["family"], s[k]["file"]) != (c["faces"][k]["family"], c["faces"][k]["file"]):
            out.append(f"look: the {k} face {s[k]['family']} is not the {k} face of {c['id']} ({c['faces'][k]['family']})")
    moves, cuts = style.ids(c, "moves"), style.ids(c, "transitions")
    for b in beats:
        if b["form"] != "closer" and b.get("move") not in moves:
            out.append(f"look: {b['id']} moves by {b.get('move')!r}, which is not a move of {c['id']} ({', '.join(moves)})")
        if b.get("transition") is not None and b["transition"] not in cuts:
            out.append(f"look: {b['id']} is cut to by {b['transition']!r}, which is not a transition of {c['id']} ({', '.join(cuts)})")
    made = set(board.get("palette") or [])
    shown = {v.lower() for k, v in s["colors"].items() if k != "swatches"} | {w["hex"].lower() for w in s["colors"].get("swatches") or []}
    for h in sorted(shown - made):
        out.append(f"look: it shows {h}, a color the {c['palette']['rule']} palette rule of {c['id']} did not make")
    for x, y in zip(beats, beats[1:]):
        if x.get("move") and x.get("move") == y.get("move"):
            out.append(f"look: {x['id']} and {y['id']} both move by {x['move']}; two beats running move differently")
    shots = [b for b in beats if b["form"] != "closer"]
    lengths = sorted(frames[b["id"]] if frames else b["bars"] for b in shots)
    if len(lengths) >= 3:
        mid = lengths[len(lengths) // 2]
        if all(abs(x - mid) <= SPREAD * mid for x in lengths):
            out.append(f"look: every shot runs within {round(SPREAD * 100)} % of {mid:g} {'frames' if frames else 'bars'}; the cut has no rhythm")
    worded = [b["anchor"] for b in shots if b.get("anchor")]
    if len(worded) >= 3:
        top = max(set(worded), key=worded.count)
        if worded.count(top) > board_trip.MOST_IN_ONE * len(worded):
            out.append(f"look: the words sit at the {top} of the frame on {worded.count(top)} of the {len(worded)} beats that carry "
                       "words; move them with what each beat shows")
    return out


def check_board(board):
    """The board re-solved from its source: the swap test (neighboring stops trade photographs, with their shape and
    points, and two beats whose moves, places for the words, lengths and camera come out the same are a template), a
    span outside 1 to 4 bars, a first span with nothing sounding in its first 30 frames, and the look's findings."""
    out = []
    src = board["source"]
    base = solve(board)
    keys = ("move", "transition", "anchor", "bars")
    strip = lambda r, bs, k: ([{x: v for x, v in s.items() if x not in ("photo", "name", "caption", "date", "place", "city")} for s in r["stops"][k:k + 2]],
                              [{x: b.get(x) for x in keys} for b in bs[k:k + 2]])
    for k in range(len(src["stops"]) - 1):
        sw = copy.deepcopy(src)
        a, b = sw["stops"][k], sw["stops"][k + 1]
        for key in ("photo", "aspect", "long", "points", "clip"):
            a[key], b[key] = b.get(key), a.get(key)
        alt = solve(board, sw)
        if strip(alt["route"], alt["beats"], k) == strip(base["route"], base["beats"], k):
            out.append(f"swap: {src['stops'][k]['name']} and {src['stops'][k + 1]['name']} come out the same with their "
                       "photographs traded: correct their points in points.json")
    for b in base["beats"]:
        if not 1 <= b["bars"] <= 4:
            out.append(f"structure: {b['id']} runs {b['bars']:g} bars; a span is 1 to 4 bars")
    pulse = FPS * 60 / base["bpm"]
    if not any(c["at"] * pulse <= 30 for c in base["sound"]):
        out.append("structure: the hook has nothing sounding in its first 30 frames")
    return base["beats"], out + look_findings(board, base["beats"])


def across(boards):
    """What the boards break together: two looks too close to tell apart."""
    return [f"looks: {t}" for t in style.too_close([b["style"] for b in boards])]


def write_md(board, path):
    """storyboard.md for a board: drafted, at the board's own tempo; for the cut film.json (music.py master writes it), at
    the music's tempo and the film's length, with the music's origin and loudness from music.json."""
    r = board["route"]
    m = _env.read_json("music.json") or {}
    mixed = (f"bed {m['bed_lufs']} LUFS, effects {m['fx_lufs']} LUFS, {m['bed_lufs'] - m['fx_lufs']:.1f} LU under; "
             f"{len(board['sound'])} sound cues over {len(board['beats'])} beats" if "fx_lufs" in m and board.get("seconds")
             else "not yet; music.py master writes the bed's and the effects' loudness here")
    L = [f"# {board['name']}", "", f"The look: {board['look']} ({board['style']}). {board['sentence']}", "", board["idea"], "",
         f"Music: {m.get('origin') or 'none yet (music.py make)'}.", f"Mixed: {mixed}.", "",
         f"{len(board['beats'])} beats on {sum(b['bars'] for b in board['beats']):g} bars at {board['bpm']:g} bpm"
         + (f", {board['seconds']:.1f} s" if board.get("seconds") else "")
         + f"; {len(r['stops'])} stops, {r['stops'][0]['name']} to {r['stops'][-1]['name']}.", "",
         "| beat | bars | move | cut into it | words at | what it shows |", "|---|---|---|---|---|---|"]
    for b in board["beats"]:
        L.append(f"| {b['id']} | {b['bars']:g} | {b.get('move') or board['system']['closer']} | {b.get('transition') or '-'} | "
                 f"{b.get('anchor') or '-'} | {b['shows']} |")
    L += ["", "## the sound", "", "| beat | kind | what it sounds |", "|---|---|---|"]
    for c in board["sound"]:
        L.append(f"| {c['at']:g} | {c['kind']} | {c['what']} |")
    L += ["", "## the clips", "", "| clip | beat | role | prompt, or their own clip | without it |", "|---|---|---|---|---|"]
    for c in board["clips"]:
        L.append(f"| {c['id']} | {c['beat']} | {c['role']} | {c.get('prompt') or c.get('source')} | {c.get('stand_in') or '-'} |")
    L += ["", "## the stops", "", "| stop | city | date | photograph | leg | their line |", "|---|---|---|---|---|---|"]
    for s in r["stops"]:
        leg = f"{board_trip.km(s['leg'])} km {s['compass']}" if s["compass"] else "-"
        L.append(f"| {s['name']} | {s.get('city') or '-'} | {s['date']} | {s['photo']} | {leg} | {s['caption']} |")
    _env.write_text(path, "\n".join(L) + "\n")


def load_boards(only=None):
    out = []
    for n in NUMBERS:
        if only and str(only) != n:
            continue
        b = _env.read_json(BOARDS / n / "storyboard.json")
        if b:
            out.append(b)
    if not out:
        sys.exit("no storyboards: run storyboard.py draft first")
    return out


def report(board, issues):
    print(f"board {board['id']} ({board['style']}): {len(board['beats'])} beats on {sum(b['bars'] for b in board['beats']):g} bars "
          f"at {board['bpm']} bpm, moves {', '.join(b['move'] for b in board['beats'] if b.get('move'))}; "
          + ("no faults" if not issues else f"{len(issues)} faults"))
    for t in issues:
        print("   ", t)


def cmd_draft(a):
    taste = _env.read_json("taste.json")
    if not taste:
        sys.exit("taste.json is missing: run research.py and write the taste profile first")
    if not Path("taste.md").exists():
        sys.exit("taste.md is missing: write the taste profile (movement 1) before storyboards")
    if not _env.read_json("points.json"):
        sys.exit("points.json is missing: run storyboard.py points, look at points.png and correct points.json first")
    # the vote judged the boards it was shown, so boards drafted again are voted and picked again
    for old in (Path("winner.json"), Path("vote/scores.json")):
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new draft goes to a new ballot (vote.py ballot, then tally)")
    # the render report vouches for out/ as the films of one cut, so it goes first; then the timed films, the sheets and
    # the boards themselves, which describe the draft this one replaces, go before the first photograph is matched
    # again; each board's storyboard.json comes back after its storyboard.md, and only snap and sheets write the films
    # and the sheets back
    for old in ([studio.RENDER / "film-report.json", Path("out/boards.png")] + [Path(name) for name, _ in film.FILMS.values()]
                + [BOARDS / n / x for n in NUMBERS for x in ("sheet.png", "storyboard.json")]):
        old.unlink(missing_ok=True)
    files = [ph for _, ph, _, _ in stop_photos()]
    grade.grade_photos(files)
    grade.match_photos([Path(f).name for f in files])
    studio.public()
    source = build_source()
    _env.write_json("source.json", source)
    bad, boards = 0, []
    for n, look in zip(NUMBERS, looks(taste)):
        b = make_board(n, look, source, taste)
        b["beats"], issues = check_board(b)
        d = BOARDS / n
        d.mkdir(parents=True, exist_ok=True)
        write_md(b, d / "storyboard.md")
        _env.write_json(d / "storyboard.json", b)
        report(b, issues)
        bad += bool(issues)
        boards.append(b)
    both = across(boards)
    for t in both:
        print("   ", t)
    print(f"wrote source.json and storyboards/1, 2, 3 ({len(source['stops'])} stops; "
          f"{', '.join(b['style'] for b in boards)}); next: storyboard.py sheets")
    return 1 if bad or both else 0


def cmd_check(a):
    bad, boards = 0, load_boards(a.board)
    for b in boards:
        b["beats"], issues = check_board(b)
        write_md(b, BOARDS / str(b["id"]) / "storyboard.md")
        _env.write_json(BOARDS / str(b["id"]) / "storyboard.json", b)
        report(b, issues)
        bad += bool(issues)
    both = across(boards) if not a.board else []
    for t in both:
        print("   ", t)
    return 1 if bad or both else 0


# ------------------------------------------------------------------ timing
def timeline(board):
    """Each timed span's start and length in frames; a span's start is its cut."""
    out, start = [], 0
    for b in board["beats"]:
        out.append({"id": b["id"], "bars": b.get("bars"), "start": start, "frames": b["frames"], "transition": b.get("transition"),
                    "start_s": round(start / FPS, 3), "seconds": round(b["frames"] / FPS, 3), "cuts": []})
        start += b["frames"]
    return out


def tempo_of(board, music):
    """The film's tempo and where its first downbeat is in the track: the track's own, doubled or halved into the
    octave around the board's tempo so a span's bar is one of the track's bars, two of them or half of one; the
    board's when there is no beat grid."""
    down = music.get("downbeats") or []
    if not down or not music.get("bpm"):
        return float(board["bpm"]), 0.0
    bpm, lo = float(music["bpm"]), board["bpm"] / math.sqrt(2)
    while bpm < lo:
        bpm *= 2
    while bpm >= 2 * lo:
        bpm /= 2
    return bpm, float(down[0])


def film_of(board, music, fmt):
    """The board at the music's tempo in one format: each span's frames from its bars, the cuts, the frames the stills
    are taken at, and the board's sound cues for music.py."""
    out = copy.deepcopy(board)
    out.pop("source", None)
    bpm, offset = tempo_of(board, music or {})
    pulse = FPS * 60 / bpm
    out.update(bpm=round(bpm, 3), music_offset=round(offset, 3), format=fmt_of(fmt))
    at = 0.0
    for b in out["beats"]:
        b["at"], b["end"] = 4 * at, 4 * (at + b["bars"])
        b["frames"] = jround((at + b["bars"]) * 4 * pulse) - jround(at * 4 * pulse)
        b["pulse"] = round(pulse, 4)
        at += b["bars"]
    out["seconds"] = round(sum(b["frames"] for b in out["beats"]) / FPS, 3)
    out["timeline"] = timeline(out)
    out["cuts"] = [round(t["start_s"], 3) for t in out["timeline"][1:]]
    r = out["route"]
    # the closer's held still is HOLD seconds at the tempo the film plays at, and its cues move with it
    r["closer"] = board_trip.closer_of(r["closer"]["at"], bpm)
    out["sound"] = board_trip.sound(r, out["beats"])
    rest = lambda beat: jround(beat * pulse)
    shots = [b for b in out["beats"] if b["form"] != "closer"]
    out["rests"] = dict({b["id"]: rest(b["end"] - 0.7) for b in shots},
                        **{f"{b['id']}-open": rest(b["at"] + min(3.4, 0.6 * (b["end"] - b["at"]))) for b in shots},
                        closer=rest(r["closer"]["still"]) + 2)
    n = len(shots)
    if n >= 5:
        # a card for each of five stops spread over the trip, its first and its last among them; the cover is the closer
        out["stories"] = [shots[i]["id"] for i in sorted({round(k * (n - 1) / 4) for k in range(5)})]
    else:
        # a shorter trip takes each stop, the moment each one's words have just landed as well, and the closer
        picks = [b["id"] for b in shots] + [f"{b['id']}-open" for b in reversed(shots)][:max(0, 4 - n)]
        out["stories"] = sorted(picks, key=lambda k: out["rests"][k]) + ["closer"]
    out["stops"] = [{k: s[k] for k in ("name", "place", "city", "date", "caption")} for s in board["source"]["stops"]]
    out["music"] = {k: music.get(k) for k in ("file", "bpm", "origin") if (music or {}).get(k)}
    return out


def monotony(film):
    """The monotony read of a timed cut: a span that holds more than two bars with nothing sounding (a cue sounds where
    something lands), and every shot within SPREAD of one length."""
    out = [t for t in look_findings(film, film["beats"], {b["id"]: b["frames"] for b in film["beats"]}) if "no rhythm" in t]
    start = 0.0
    for b in film["beats"]:
        end = start + 4 * b["bars"]
        ev = sorted({start, end} | {c["at"] for c in film["sound"] if start <= c["at"] <= end})
        gap = max((y - x for x, y in zip(ev, ev[1:])), default=0)
        if gap > 8:
            out.append(f"{b['id']} holds {gap * 60 / film['bpm']:.1f} s ({gap:g} musical beats) with nothing sounding")
        start = end
    return out


def film_hash():
    return hashlib.sha256(Path("film.json").read_bytes()).hexdigest()[:16]


def cmd_snap(a):
    if a.board:
        sys.exit("snap takes no --board: it times the picked board, from winner.json (vote.py pick --board N picks another)")
    bid = (_env.read_json("winner.json") or {}).get("board")
    if not bid:
        sys.exit("no board picked: run vote.py ballot, fill it in, vote.py tally, then vote.py pick")
    board = _env.read_json(BOARDS / str(bid) / "storyboard.json")
    if not board:
        sys.exit(f"storyboards/{bid}/storyboard.json is missing")
    music = _env.read_json("music.json") or {}
    if not music.get("downbeats"):
        print("no downbeats in music.json (run music.py make); cutting on the board's tempo")
    _, issues = check_board(board)
    if issues:
        report(board, issues)
        sys.exit("the board has faults: fix its source and run storyboard.py check")
    films = {fmt: film_of(board, music, fmt) for fmt in FORMATS}
    read = monotony(films["reel"])
    if read:
        print("the monotony read refuses the timed cut:")
        for t in read:
            print("   ", t)
        return 1
    # the render report vouches for out/ as the films of the cut snap replaces, so it goes first, and only a render of
    # this cut writes it back; film.json certifies the other two formats: it goes before they change and comes back
    # after them, so a snap stopped between two writes leaves no film.json, which every reader refuses
    (studio.RENDER / "film-report.json").unlink(missing_ok=True)
    Path("film.json").unlink(missing_ok=True)
    for fmt, name in (("landscape", "film-landscape.json"), ("square", "film-square.json"), ("reel", "film.json")):
        _env.write_json(name, films[fmt])
    studio.public()
    f = films["reel"]
    print(f"board {bid} ({board['style']}): {len(f['beats'])} spans on {sum(x['bars'] for x in f['beats']):g} bars at {f['bpm']:g} bpm, "
          f"{len(f['sound'])} sound cues, the stop at {f['route']['closer']['still'] * 60 / f['bpm']:.2f} s; {f['seconds']:.1f} s "
          f"-> film.json ({film_hash()}), film-landscape.json, film-square.json")
    return 0


# ------------------------------------------------------------------ sheets
ROLES = ("hook", "middle", "closer")


def sheet_frames(b):
    """The board's three styleframes, timed at its own tempo: the hook and the middle stop the moment their words have
    landed (the look at its fullest, before the cut out of the beat starts), and the closer's still."""
    tb = film_of(b, {}, "reel")
    shots = [x["id"] for x in tb["beats"] if x["form"] != "closer"]
    mid = shots[len(shots) // 2] if len(shots) > 1 else shots[0]
    return tb, (("hook", tb["rests"]["hook-open"]), ("middle", tb["rests"][f"{mid}-open"]), ("closer", tb["rests"]["closer"]))


def wrap(draw, text, font, width):
    """`text` broken into lines no wider than `width` px in `font`."""
    lines, line = [], ""
    for w in text.split():
        if line and draw.textlength(f"{line} {w}", font=font) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return lines + [line] if line else lines


def save(im, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(_env.part(dst), "PNG")
    os.replace(_env.part(dst), dst)


def boards_png(boards, frames):
    """out/boards.png: one row a look, its name in its own display face and its sentence in its text face over its hook,
    middle and closer at half size, so the person picks a look from the pictures."""
    from PIL import Image, ImageDraw
    w, h = frames[boards[0]["id"]][0].size
    gap, head = SHEET_GAP, SHEET_HEAD
    W = 3 * w + 4 * gap
    sheet = Image.new("RGB", (W, len(boards) * (h + head + gap) + gap), "#151515")
    dr = ImageDraw.Draw(sheet)
    y = gap
    for i, b in enumerate(boards):
        name = _env.pil_font(58, "display", b["style"])
        text = _env.pil_font(30, "text", b["style"])
        dr.text((gap, y + 6), f"{i + 1}  {b['look']}", fill="#f3efe6", font=name)
        for k, ln in enumerate(wrap(dr, b["sentence"], text, W - 2 * gap)[:2]):
            dr.text((gap, y + 86 + 36 * k), ln, fill="#c9c2b4", font=text)
        for j, im in enumerate(frames[b["id"]]):
            sheet.paste(im.convert("RGB"), (gap + j * (w + gap), y + head))
        y += h + head + gap
    save(sheet, Path("out/boards.png"))


def cmd_sheets(a, run):
    from PIL import Image, ImageDraw
    boards = load_boards(a.board)
    jobs, want = [], []
    for b in boards:
        (BOARDS / str(b["id"]) / "sheet.png").unlink(missing_ok=True)
        tb, frames = sheet_frames(b)
        d = BOARDS / str(b["id"]) / "frames"
        d.mkdir(parents=True, exist_ok=True)
        for role, fr in frames:
            out = (d / f"{role}.png").resolve()
            jobs.append(studio.still(tb, fr, out, scale=0.5))
            want.append((b, role, fr, out))
    Path("out/boards.png").unlink(missing_ok=True)
    rep = studio.render(jobs, "sheets", run)
    got = {}
    for b in boards:
        mine = [(role, fr, out) for bb, role, fr, out in want if bb is b]
        ims = [Image.open(out) for _, _, out in mine if out.exists()]
        if len(ims) != 3:
            print(f"board {b['id']}: {len(ims)} of 3 styleframes rendered")
            continue
        got[b["id"]] = ims
        w, h = ims[0].size
        sheet = Image.new("RGB", (3 * w + 80, h + 120), "#181818")
        dr = ImageDraw.Draw(sheet)
        dr.text((20, 18), f"{b['id']}  {b['name']}", fill="#f0f0f0", font=_env.pil_font(30, "display", b["style"]))
        for j, ((role, fr, _), im) in enumerate(zip(mine, ims)):
            sheet.paste(im.convert("RGB"), (20 + j * (w + 20), 80))
            dr.text((20 + j * (w + 20), 80 + h + 8), f"{role}: frame {fr}", fill="#c8c8c8", font=_env.pil_font(22, "text", b["style"]))
        save(sheet, BOARDS / str(b["id"]) / "sheet.png")
        print(f"board {b['id']} ({b['style']}): storyboards/{b['id']}/sheet.png")
    if not a.board and len(got) == len(boards) == 3:
        boards_png(boards, got)
        print("out/boards.png: the three looks, each by its hook, its middle and its closer; show it to the person to pick one")
    bad = film.faults(rep)
    for t in dict.fromkeys(bad):
        print("fault:", t[:400])
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["points", "draft", "check", "sheets", "snap"])
    ap.add_argument("--board", help="check and sheets: the one board to read (snap takes the picked board)")
    a = ap.parse_args()
    _env.enter_run()
    _env.need("PIL")
    if a.cmd == "sheets":
        # the render lock is taken before the styleframes' folders are made, so a refused sheets changes nothing;
        # setup.py's tool probe runs before it, since no process outside run.spawn starts under the lock
        _env.tools()
        with studio.lock("sheets") as run:
            return cmd_sheets(a, run)
    return {"points": cmd_points, "draft": cmd_draft, "check": cmd_check, "snap": cmd_snap}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
