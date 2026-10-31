#!/usr/bin/env python3
"""Movement 2: three storyboards of their month, one a look, composed by the board builder (scripts/compose) from the
run's month.json; their checks; and their sheets rendered by the studio compositions, with out/boards.png, the page
the person picks a look from.

USAGE (from the workspace root):
    python3 S/scripts/storyboard.py draft [--template FILE]
    python3 S/scripts/storyboard.py check
    python3 S/scripts/storyboard.py sheets

draft   writes three boards, one a style (compose/style.py: the trio editorial-quiet, scrapbook and swiss-grid, or the
        style the person named in taste.json `style`, else last month's template's, and the two of the trio that share
        the fewest axes with it), each storyboards/<style>/storyboard.json (what motion/studio renders: the system, the
        cards and their shots, and the reel with its beats, moves, sound cues and clips) and storyboard.md, and
        storyboards/boards.json, their order: the music brief from taste.json `music`
        with the Music and Mixed lines music.py make and film.py render fill in, the reel beat by beat (its span and
        the frame it cuts on, what its move reveals, what it carries across the cut, and every sound on it with the
        beat it lands on), then each card's idea, its shots with what each reveals, its sound cues and its words. The
        moments are the three or four the agent picked into taste.json `moments` (each a post's photograph, or its day
        when it has none, with the line it says on screen, one of them the peak), else the month as its captions tell
        it; the reel opens on the peak and walks through the others in date order, and there is one card a moment. taste.json `ask` goes onto the board: their counts on the cards (counting up from zero),
        the reel's length, and whether the series is made as one video; draft says what the reel runs against the
        length asked. A length outside 12 to 30 s is refused before anything is touched: draft prints
        "not delivered: this kit makes a reel of 12 to 30 s, and the ask is for N s. Ask for a length in that range."
        and exits 2, making nothing. Every close
        framing is worked out from the font files' own measures of the type it holds (compose/stories.py), so the
        camera holds every line wholly in view or wholly out of it. Each board's faces, moves, transitions, easing,
        finish, closer and music come from its style card; its colors are the card's palette rule over the swatches
        of their photographs. The look the person gave (compose/look.py: --template FILE, else template.json in the
        workspace, else last month's build/template.json) brings its palette, its font and its numbering, and draft
        names the font it sets when a style cannot set the one asked. A board in the style of last month's template
        is marked `follows`, so next month's series matches. A new draft starts a new vote: before its first file it
        removes winner.json, vote/scores.json, music.json, film.json, storyboards/check.json, storyboards/sheets.json,
        out/boards.png and the boards themselves, and it writes boards.json last.
check   the board gates for every board, written to storyboards/check.json; exits 1 when any fails, naming the board
        and the rule:
          styles      no two boards' styles share more than two of the six axes
          structure   3 or 4 cards, one a moment, each 15 s, every card's sound cues naming their event, and every line of type
                      wholly in or out of view wherever the camera holds, inside the safe area on a whole-frame hold
                      and clear of every other line (compose/stories.py bounds); the reel's beats run end to end from
                      its first frame to its last, and every sound cue sits on a beat, names its event, and the last
                      is the stop
          swap        every card and the reel change when their photographs and their words do (the month composed
                      again with each post's caption and photograph moved to the next post), and every moment's move in
                      the reel changes when the photographs move between posts: a card or a move that would look the
                      same for someone else's month or another photograph is a template
          monotony    the cards' timed cut has contrast: at least three shot lengths, no run of more than five equal
                      shots, the longest shot at least twice the shortest, and in every card a held shot at least 1.25
                      times the card's median shot
          words       every line set in its face's case
          style       every line in one of the card's two faces; every move and transition the card allows; no move
                      on two beats in a row; no color the palette rule did not make; the reel's beats not all within
                      10% of one length; the words not in one place on more than 70% of the reel's beats
          look        with a given look: the board's colors are its palette's, every card's title opens with its
                      numbering, and every line is set in its font (or the family named in its place); with none,
                      the colors are the ones read from the photographs
          counts      their numbers on screen only when asked, and then every count counts up over its hold
sheets  renders, for every board, every card shot at its rest frames (a beat in, the middle, the last frame) through
        motion/studio into storyboards/<style>/sheet.png, and every reel beat once its move has landed into
        storyboards/<style>/reel-sheet.png; and out/boards.png: each board's hook, a middle beat and its closer at half
        size, in board order, with the style's name and one plain sentence under each. storyboards/sheets.json
        carries the render's findings: a font or a photograph that did not load. Exits 1 on any finding. It refuses
        boards whose storyboards/check.json is missing or not green, before it renders anything.
"""
import argparse
import copy
import json
import shutil
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402
import compose  # noqa: E402
import studio  # noqa: E402
from compose import look, stories, style  # noqa: E402
from compose.month import SECONDS, OutOfRange  # noqa: E402
from compose.month import which  # noqa: E402

MONOTONY = {"lengths": 3, "run": 5, "range": 2.0, "held": 1.25}


def boards_dir(run):
    return run / "storyboards"


def order(run):
    """The boards' styles in board order, as draft wrote them (storyboards/boards.json)."""
    return (_env.read_json(boards_dir(run) / "boards.json") or {}).get("order") or []


def load_boards(run):
    d = boards_dir(run)
    out = {}
    for t in order(run):
        b = _env.read_json(d / t / "storyboard.json")
        if b:
            out[t] = b
    return out


def card_words(card):
    """Every line of type the card draws."""
    return [x["text"] for x in card.get("lines", [])]


def reel_words(board):
    """Every line of type the reel draws: each moment's, the closer's words, the day under each of its photographs, and
    the style's closing page (the month's line, the handle, the sign-off)."""
    r = board.get("reel") or {}
    rows = [x for c in r.get("cards", []) for x in c.get("lines", [])]
    cl = r.get("closer") or {}
    rows += cl.get("lines", []) + [t["label"] for t in cl.get("tiles", [])]
    page = [(r.get("look") or {}).get(k) for k in ("title", "handle", "signoff")] if cl.get("page") else []
    return [x["text"] for x in rows] + [x for x in page if x]


def numbers(x):
    """Every number in a card (positions, sizes, scales, camera views), strings left out."""
    if isinstance(x, bool):
        return []
    if isinstance(x, (int, float)):
        return [round(x, 1)]
    if isinstance(x, dict):
        return [n for k in sorted(x) for n in numbers(x[k])]
    if isinstance(x, list):
        return [n for v in x for n in numbers(v)]
    return []


def picked(month, board):
    """Their month with the board's moments, what the person asked for and the look they gave."""
    return dict(month, moments=board.get("moments") or month.get("moments"), ask=board.get("ask") or month.get("ask"),
                look=(board.get("look") or {}).get("given") or month.get("look"))


def swapped(month, k=1):
    """Their month with each post given the caption and the photograph of the post k on (the last ones the first's), the
    moments staying on their posts and saying the captions those posts now carry."""
    v = copy.deepcopy(month)
    ps = v["posts"]
    at = [which(ps, x) for x in v.get("moments") or []]
    turned = [(p.get("caption"), p.get("photo")) for p in ps[k:] + ps[:k]]
    for p, (cap, photo) in zip(ps, turned):
        p["caption"], p["photo"] = cap, photo
    for x, i in zip(v.get("moments") or [], at):
        if i is not None:
            x["photo"], x["day"], x["line"] = ps[i]["photo"], ps[i]["day"], ps[i]["caption"]
    return v


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def swap_test(board, month, build=None):
    """[(card id, changed)] for every card of board, and ("reel", changed) for the reel, against the same style composed
    from the swapped month."""
    build = build or (lambda m: compose.board(board["style"], m))
    o = build(swapped(picked(month, board)))
    other = {c["id"]: c for c in o["beats"]}
    out = [(c["id"], c["id"] in other and not same(c, other[c["id"]])) for c in board["beats"]]
    if board.get("reel"):
        out.append(("reel", not same(board["reel"]["cards"], (o.get("reel") or {}).get("cards"))))
    return out


def photo_swap(board, month):
    """[(moment key, changed)]: each moment's move in the reel (where its photograph sits and how the camera frames it)
    against the reel composed with every photograph moved to the next post. None when fewer than two posts carry a
    photograph."""
    v = copy.deepcopy(picked(month, board))
    has = [p for p in v["posts"] if p.get("photo")]
    if len(has) < 2:
        return None
    pics = [p["photo"] for p in has]
    moved = dict(zip(pics, pics[1:] + pics[:1]))
    for p in has:
        p["photo"] = moved[p["photo"]]
    for x in v.get("moments") or []:
        x["photo"] = moved.get(x["photo"], x["photo"])
    other = {c["key"]: c for c in compose.board(board["style"], v)["reel"]["cards"]}
    mine = board["reel"]["cards"]
    return [(c["key"], numbers([c["T"], c["place"]]) != numbers([other[c["key"]]["T"], other[c["key"]]["place"]])) for c in mine if c.get("file")]


def reel_structure(board):
    """What is wrong with the reel's plan: beats that do not run end to end, a cue off every beat or naming no event,
    a last cue that is not the stop, a frame count that is not its end."""
    r = board.get("reel") or {}
    if not r:
        return ["no reel"]
    bad, bs = [], r.get("beats") or []
    if not bs or bs[0]["from"] != 0 or abs(bs[-1]["to"] - r["end"]) > 1e-6:
        bad.append("the beats do not run from the first frame to the end")
    bad += [f"{a['key']} ends at {a['to']}, {b['key']} starts at {b['from']}" for a, b in zip(bs, bs[1:]) if abs(a["to"] - b["from"]) > 1e-6]
    bad += [f"{b['key']} says nothing it reveals or carries" for b in bs if not b.get("reveals") or not b.get("carries")]
    keys = {b["key"] for b in bs}
    bad += [f"{c['kind']} at {c['at']} sits on no beat or names no event" for c in r.get("sound") or [] if c.get("beat") not in keys or not c.get("what")]
    last = max(r.get("sound") or [{"kind": None, "at": 0}], key=lambda c: (c["at"], c["kind"] == "stop"))
    if last["kind"] != "stop":
        bad.append("the last sound cue is not the stop")
    if r.get("frames") != round(r["end"] * r["fps"] * 60 / r["bpm"]):
        bad.append(f"{r.get('frames')} frames for an end at beat {r['end']}")
    return bad


def monotony(board):
    lengths = [s["beats"] for c in board["beats"] for s in c["shots"]]
    run = best = 1
    for a, b in zip(lengths, lengths[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    flat = [c["id"] for c in board["beats"] if max(s["beats"] for s in c["shots"]) < MONOTONY["held"] * statistics.median(s["beats"] for s in c["shots"])]
    out = {"lengths": len(set(lengths)), "run": best, "range": round(max(lengths) / min(lengths), 2), "flat_cards": flat}
    out["ok"] = out["lengths"] >= MONOTONY["lengths"] and best <= MONOTONY["run"] and out["range"] >= MONOTONY["range"] and not flat
    return out


def check_board(board, month):
    res = []
    add = lambda name, ok, detail: res.append({"check": name, "ok": bool(ok), "detail": detail})
    cards = board["beats"]
    bad_len = [c["id"] for c in cards if studio.card_frames(board, c) != 450]
    mute = [f"{c['id']} {x['kind']} at {x['at']}" for c in cards for x in c.get("sound", []) if not x.get("what")]
    framed = [x for c in cards for x in stories.bounds(c)]
    reel_bad = reel_structure(board)
    add("structure", 3 <= len(cards) <= 4 and len(cards) == len(board.get("moments") or []) and not bad_len and not mute and not framed and not reel_bad,
        f"{len(cards)} cards ({', '.join(c['id'] for c in cards)}); the reel {(board.get('reel') or {}).get('frames')} frames in "
        f"{len((board.get('reel') or {}).get('beats') or [])} beats with {len((board.get('reel') or {}).get('sound') or [])} sound cues"
        + (f"; not 15 s: {bad_len}" if bad_len else "") + (f"; cues naming no event: {mute[:3]}" if mute else "")
        + (f"; framing: {'; '.join(framed[:3])}" if framed else "; every line wholly in or out of view where the camera holds")
        + (f"; the reel: {'; '.join(reel_bad[:3])}" if reel_bad else ""))
    try:
        sw = swap_test(board, month)
        unchanged = [cid for cid, changed in sw if not changed]
        ph = photo_swap(board, month) if board.get("reel") else None
        still = [k for k, changed in ph or [] if not changed]
        add("swap", not unchanged and not still, ("every card and the reel change with their photographs and words" if not unchanged else
                                                  f"the same for another month's photographs and words: {unchanged}")
            + ("; no photographs to swap" if ph is None else "; every post's move changes with its photograph" if not still else
               f"; the same move under another photograph: {still}"))
    except ValueError as e:
        add("swap", False, f"the board builder could not compose the swapped month: {e}")
    mo = monotony(board)
    add("monotony", mo["ok"], f"{mo['lengths']} shot lengths, longest run of equal shots {mo['run']}, longest {mo['range']}x the shortest"
        + (f"; no held shot in {mo['flat_cards']}" if mo["flat_cards"] else ""))
    c = style.card(board["style"])
    faces = {f["file"]: f for f in c["faces"].values()}
    rows = all_lines(board)
    off = [x["text"] for x in rows if x.get("file") in faces and x["text"] != style.cased(x["text"], faces[x["file"]])]
    add("words", not off, f"{len(rows)} lines, each in its face's case" if not off else f"not in their face's case: {off[:5]}")
    tl = tells(board, c)
    add("style", not tl, f"in {c['name'].lower()}: its faces, its moves and transitions, its palette rule" if not tl else "; ".join(tl[:4]))
    lk = look_check(board)
    add("look", not lk["bad"], lk["detail"])
    ct = count_check(board)
    add("counts", not ct, "their numbers only as asked, every count counting up over its hold" if not ct else "; ".join(ct[:3]))
    return res


def tells(board, card):
    """What on a board a template would show, or its card does not allow: a line in a face not the card's, a move or
    transition outside its allowlist, one move on two beats in a row, a color the palette rule did not make, reel
    beats all within 10% of one length, words in one place on more than 70% of the reel's beats."""
    bad = []
    files = {f["file"] for f in card["faces"].values()}
    off = sorted({str(x.get("file")) for x in all_lines(board) if x.get("file") not in files})
    bad += [f"a line set in {f}, not one of the card's faces" for f in off]
    tl = (board.get("reel") or {}).get("timeline") or {}
    beats = tl.get("beats") or []
    moves, cuts = style.ids(card, "moves"), style.ids(card, "transitions")
    bad += [f"{b['id']}'s move {b['move']} is not the card's" for b in beats if b.get("move") not in moves]
    bad += [f"{b['id']}'s transition {b['transition']} is not the card's" for b in beats[1:] if b.get("transition") not in cuts]
    bad += [f"{a['id']} and {b['id']} both move by {a['move']}" for a, b in zip(beats, beats[1:]) if a.get("move") == b.get("move")]
    made = set((board.get("look") or {}).get("made") or []) | set(style.hexes_in([card.get("finish") or {}, card.get("photo") or {}]))
    rest = {k: v for k, v in board.items() if k != "look"}
    stray = sorted(set(style.hexes_in(rest)) - {h.lower() for h in made})
    bad += [f"{h} is neither a color the palette rule made nor the card's finish or photo layout" for h in stray]
    # the cuts and the end in beats from the film's start (the first beat's move may start before it), spans in seconds
    at = [max(0.0, x) for x in tl.get("cuts") or []]
    reel_ = board.get("reel") or {}
    end, sec = reel_.get("end", 0), 60 / reel_.get("bpm", 60)
    spans = [(b - a) * sec for a, b in zip(at, at[1:] + [end])]
    if len(spans) > 2:
        mid = statistics.median(spans)
        if all(abs(s - mid) <= 0.1 * mid for s in spans):
            bad.append(f"the reel's {len(spans)} beats all run within 10% of {mid:.2f} s")
    places = [place_of(c) for c in (board.get("reel") or {}).get("cards") or [] if c.get("lines")]
    if len(places) > 2:
        top = max(set(places), key=places.count)
        if places.count(top) > 0.7 * len(places):
            bad.append(f"the words sit {top} on {places.count(top)} of the reel's {len(places)} beats")
    return bad


def place_of(card):
    """Where a reel beat's words sit on the frame: the third of its height their first line is in, and its anchor (the
    hook the first beat opens on stands above its band and is not its words)."""
    ln = next((x for x in card["lines"] if x.get("name") != "hook"), card["lines"][0])
    third = ("in the top third", "in the middle", "in the bottom third")[min(2, int(3 * ln["y"] / compose.H))]
    return f"{third}, {ln.get('anchor', 'start')}"


def styles_check(boards):
    """Pairs of boards whose styles share more than two of the six axes."""
    ids = list(boards)
    return [f"{a} and {b} share {', '.join(sorted(style.shared_axes(a, b)))}" for i, a in enumerate(ids) for b in ids[i + 1:]
            if len(style.shared_axes(a, b)) > 2]


def all_lines(board):
    r = board.get("reel") or {}
    rows = [x for c in board["beats"] for x in c.get("lines", [])]
    rows += [x for c in r.get("cards", []) for x in c.get("lines", [])] + (r.get("closer") or {}).get("lines", [])
    return rows + [t["label"] for t in (r.get("closer") or {}).get("tiles", [])]


def look_check(board):
    """What on the board does not wear the look it was given: colors off its palette, a card title not in its
    numbering; with no look, colors that are not the ones read from the photographs or the kit's own. A line in a face
    the card does not set is the style check's (`tells`)."""
    from compose import look
    lk = board.get("look") or {}
    given = lk.get("given")
    bad = []
    colors = board["system"]["colors"]
    if (board.get("reel") or {}).get("colors") != colors:
        bad.append("the reel and the cards are in different colors")
    if given and given.get("palette"):
        want = look.roles_of(given)
        bad += [f"{k} is {colors.get(k)}, the look's is {v}" for k, v in want.items() if colors.get(k) != v]
    if given:
        n = len(board["beats"])
        for i, c in enumerate(board["beats"]):
            want = look.numbered(given.get("numbering") or look.NUMBERING, i + 1, n)
            if not c["lines"] or not c["lines"][0]["text"].startswith(want + " "):
                bad.append(f"{c['id']} is not numbered {want}")
    elif (lk.get("theme") or {}).get("from") not in ("photographs", "kit"):
        bad.append("no look was given, and the colors were not read from the photographs")
    detail = (f"from {look.source(lk)}: {colors.get('bg')} ground, {colors.get('ink')} ink, {colors.get('accent')} accent, type in {lk.get('font_used')}"
              + (f", numbered {lk.get('numbering')}" if given else "") + (f"; {lk['font_note']}" if lk.get("font_note") else ""))
    return {"bad": bad, "detail": "; ".join(bad) if bad else detail}


def count_check(board):
    """Count lines shown unasked, and count lines that stand still."""
    rows = [x for x in all_lines(board) if x.get("name") == "count"]
    if not (board.get("ask") or {}).get("counts"):
        return [f"'{x['text']}' is shown, and their numbers were not asked for" for x in rows]
    return [f"'{x['text']}' stands still" for x in rows if not (x.get("tally") or {}).get("beats")]


def write_md(board, path, brief=None):
    lk = board.get("look") or {}
    L = [f"# {board['name']}", "", f"in the {board['style']} style, music at {board['music']['bpm']} bpm, cut on a {board['bpm']} pulse, " + (f"signed {board['handle']}" if board.get("handle") else "no handle in their data, so no card carries one")
         + (" (follows last month's template)" if board.get("follows") else ""), "",
         f"The look: from {(lk.get('given') or {}).get('source') or 'their photographs'}, colors " + json.dumps(lk.get("colors"))
         + f", type in {lk.get('font_used')}" + (f" ({lk['font_note']})" if lk.get("font_note") else "") + ".", "",
         "The music brief (taste.json `music`): " + json.dumps(brief, ensure_ascii=False) + ".",
         "Music: not made yet; music.py make writes its origin here.",
         "Mixed: not yet; film.py render writes the bed's and the effects' loudness and the cue count here.", ""]
    r = board.get("reel")
    if r:
        f = lambda beat: round(beat * r["fps"] * 60 / r["bpm"])
        L += [f"## the reel: {r['frames']} frames, {r['frames'] / r['fps']:.1f} s, {len(r['beats'])} beats, one camera, "
              f"{len(r['sound'])} sound cues, one where each beat lands", "",
              "Each beat: its span in beats and frames, what its move reveals, what it carries across the cut, and every sound on it.", ""]
        cards = {c["key"]: c for c in r["cards"]}
        for b in r["beats"]:
            L += [f"### {b['key']}: beats {b['from']:g}-{b['to']:g}, frames {f(b['from'])}-{f(b['to'])}",
                  f"- reveals: {b['reveals']}", f"- carries: {b['carries']}"]
            if b["key"] in cards:
                c = cards[b["key"]]
                L += [f"- photograph: {c.get('source') or 'none'}", "- on screen: " + " / ".join(x["text"] for x in c["lines"])]
            L += [f"- sound at {c['at']:g} (frame {f(c['at'])}): {c['kind']}, {c['what']}" for c in r["sound"] if c.get("beat") == b["key"]]
            L += [f"- clip {c['id']}, {c['seconds']} s: {c['prompt']}; until one arrives, {c['stand_in']}" for c in r.get("clips", []) if c["beat"] == b["key"]]
            L.append("")
    L += [f"## the series: {len(board['beats'])} cards of 15 s", ""]
    for i, c in enumerate(board["beats"]):
        L += [f"### {i + 1:02d} {c['idea']}", f"- {len(c['shots'])} shots: " + ", ".join(f"{s['beats']:g}" for s in c["shots"]) + " beats"]
        at = 0
        for j, s in enumerate(c["shots"]):
            L.append(f"- shot {j + 1}, beats {at:g}-{at + s['beats']:g}: {s['reveals']}")
            at += s["beats"]
        L += [f"- sound at {x['at']:g}: {x['kind']}, {x['what']}" for x in c.get("sound", [])]
        L += ["- words: " + " / ".join(dict.fromkeys(card_words(c))), ""]
    _env.write_text(path, "\n".join(L))


def draft(a):
    run = _env.writable_run()
    month = _env.read_json(run / "month.json")
    if not month:
        sys.exit(f"{run / 'month.json'} is missing: run research.py first")
    if not (run / "taste.md").exists():
        sys.exit(f"{run / 'taste.md'} is missing: write it from taste.draft.md first (pipeline/1-research.md)")
    taste = _env.read_json(run / "taste.json") or {}
    month["moments"], month["ask"] = taste.get("moments") or [], taste.get("ask") or {}
    # every moment with a photograph is shot as the agent wrote it from that photograph, never from a template
    unshot = [str(x.get("day")) for x in month["moments"]
              if x.get("photo") and not all(str((x.get("shot") or {}).get(k) or "").strip() for k in ("subject", "move"))]
    if unshot:
        sys.exit(f"taste.json `moments`: the moment on day {', '.join(unshot)} has no shot subject or move: write each "
                 "moment's shot from looking at its photograph (pipeline/1-research.md)")
    drafted_from = studio.taste_hash(run)
    secs = month["ask"].get("seconds")
    if secs is not None and not SECONDS[0] <= float(secs) <= SECONDS[1]:
        print(OutOfRange(secs))
        return 2
    month["look"] = look.find(a.template)
    tpl = _env.read_json(a.template or "build/template.json") or {}
    follows = tpl.get("style") if tpl.get("style") in style.styles() else None
    named = taste.get("style") or follows
    try:
        trio = compose.trio(named)
    except ValueError as e:
        sys.exit(f"taste.json `style`: {e} (styles/catalog.md maps a look in their words to a style id)")
    d = boards_dir(run)
    # everything that stood on the old board goes before the first new file: the vote and the music made for its winner,
    # its checks and sheets, the record of the board the film rendered, and the board itself, so a draft cut off
    # partway leaves a run every later step refuses until the board is drafted again
    stale = [d / "boards.json", run / "winner.json", run / "vote" / "scores.json", run / "music.json", run / "film.json",
             d / "check.json", d / "sheets.json", run / "out" / "boards.png", *sorted(d.glob("*/storyboard.json"))]
    for old in stale:
        if old.exists():
            old.unlink()
            print(f"{old}: removed; the new board goes to its checks and a new ballot (check, sheets, vote.py ballot, then tally)")
    for t in trio:
        try:
            b = compose.board(t, month)
        except ValueError as e:
            sys.exit(f"{e}: fix taste.json `moments` (pipeline/1-research.md)")
        if t == follows:
            b["follows"] = True
        b["taste"] = drafted_from
        (d / t).mkdir(parents=True, exist_ok=True)
        write_md(b, d / t / "storyboard.md", (_env.read_json(run / "taste.json") or {}).get("music"))
        # the board's json goes last: it is what every later step reads
        _env.write_json(d / t / "storyboard.json", b)
        print(f"{t}: {b['bpm']} bpm, {len(b['beats'])} cards ({', '.join(c['id'] for c in b['beats'])}), {sum(len(c['shots']) for c in b['beats'])} shots"
              + (", follows last month's template" if t == follows else ""))
        lk = b["look"]
        print(f"  the look: from {look.source(lk)}, {lk['colors']['bg']} ground, "
              f"{lk['colors']['ink']} ink, {lk['colors']['accent']} accent, type in {lk['font_used']}"
              + (f", numbered {lk['numbering']}" if lk["given"] else "") + (f"; {lk['font_note']}" if lk["font_note"] else ""))
        r, ask = b["reel"], month["ask"]
        print(f"  the reel runs {r['frames'] / r['fps']:.2f} s ({r['frames']} frames)" + (f"; asked for {ask['seconds']} s" if ask.get("seconds") else "")
              + ("; their counts are on the cards" if b["ask"]["counts"] else "; the ask is for their numbers, and the data carries none, so no figure is shown"
                 if ask.get("counts") else "") + ("; the series is made as one video" if b["ask"]["series"] else ""))
    _env.write_json(d / "boards.json", {"order": list(trio), "named": named})
    print(f"wrote three boards: {', '.join(f'{d}/{t}/storyboard.json' for t in trio)}; order in {d / 'boards.json'}")
    return 0


def check(a):
    run = _env.run()
    month = _env.read_json(run / "month.json")
    boards = load_boards(run)
    if not boards or not month:
        sys.exit("no storyboards in this run: run storyboard.py draft first")
    out, ok = {}, len(boards) == 3
    if not ok:
        print(f"FAIL boards    {len(boards)} boards; draft writes three")
    pairs = styles_check(boards)
    ok &= not pairs
    print(f"{'ok  ' if not pairs else 'FAIL'} styles    " + ("; ".join(pairs) if pairs else f"{', '.join(boards)}: no two share more than two axes"))
    for t, b in boards.items():
        res = check_board(b, month)
        out[t] = {"ok": all(r["ok"] for r in res), "checks": res}
        ok &= out[t]["ok"]
        for r in res:
            print(f"{t:<16} {'ok  ' if r['ok'] else 'FAIL'} {r['check']:<9} {r['detail']}")
    _env.write_json(boards_dir(run) / "check.json", {"ok": ok, "styles": pairs, "boards": out, "monotony_ranges": MONOTONY})
    return 0 if ok else 1


def sheet(pngs, out, cols=12):
    from PIL import Image
    ims = [Image.open(p) for p in pngs]
    w, h = ims[0].size
    rows = -(-len(ims) // cols)
    s = Image.new("RGB", (cols * (w + 4), rows * (h + 4)), "black")
    for i, im in enumerate(ims):
        s.paste(im.convert("RGB"), ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    s.save(out)


def picks_of(board):
    """{hook, middle, closer: frame} of a board's reel: its first beat landed, its middle beat landed, its closer still."""
    rest = studio.reel_rest_frames(board)
    keys = [k for k in rest if k != "closer"]
    return {"hook": rest[keys[0]], "middle": rest[keys[len(keys) // 2]], "closer": rest["closer"]}


def boards_page(boards, stills, out):
    """out/boards.png: a row a board, its hook, middle beat and closer, the style's name and its sentence under them."""
    from PIL import Image, ImageDraw, ImageFont
    rows = [[Image.open(stills[t][k]).convert("RGB") for k in ("hook", "middle", "closer")] for t in boards]
    w, h = rows[0][0].size
    gap, under = 24, 150
    page = Image.new("RGB", (3 * w + 4 * gap, len(rows) * (h + under) + gap), "#f4f2ee")
    draw = ImageDraw.Draw(page)
    for i, (t, ims) in enumerate(zip(boards, rows)):
        y = gap + i * (h + under)
        for j, im in enumerate(ims):
            page.paste(im, (gap + j * (w + gap), y))
        # each look's name in its own display face and its sentence in its own text face
        c = style.card(t)
        face = lambda kind, size: ImageFont.truetype(str(_env.SKILL / c["faces"][kind]["file"]), size)
        draw.text((gap, y + h + 18), f"{i + 1}. {c['name']}", fill="#14161c", font=face("display", 46))
        words, said, ty = style.sentence(t).split(), "", y + h + 82
        for word in words:
            if said and draw.textlength(f"{said} {word}", font=face("text", 26)) > page.width - 2 * gap:
                draw.text((gap, ty), said, fill="#4a4d55", font=face("text", 26))
                said, ty = word, ty + 34
            else:
                said = f"{said} {word}".strip()
        draw.text((gap, ty), said, fill="#4a4d55", font=face("text", 26))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    page.save(out)


def sheets(a):
    _env.need("PIL")
    run = _env.run()
    boards = load_boards(run)
    if not boards:
        sys.exit("no storyboard in this run: run storyboard.py draft first")
    jobs, d = [], boards_dir(run)
    # draft removes check.json, so a green one is this board's
    if not (_env.read_json(d / "check.json") or {}).get("ok"):
        sys.exit("the board has not passed its check: run storyboard.py check first and fix what it fails")
    # the run's lock is held from the command's first write, the stills it clears, to its last
    with studio.lock(d / "render", "sheets") as hold:
        # sheets.json certifies the stills, so it goes before the first of them changes and comes back once they are made
        (d / "sheets.json").unlink(missing_ok=True)
        for t, b in boards.items():
            for k in ("rest", "reel"):
                shutil.rmtree(d / t / k, ignore_errors=True)
            jobs += studio.rest_jobs(b, d / t / "rest")
            if b.get("reel"):
                jobs += [{"type": "still", "composition": "Reel", "props": studio.props(b, run), "frame": fr, "scale": 0.25,
                          "out": str((d / t / "reel" / f"{k}-{fr:04d}.png").resolve())} for k, fr in studio.reel_rest_frames(b).items()]
        picks = {t: picks_of(b) for t, b in boards.items()}
        stills = {t: {k: str((d / t / "boards" / f"{k}.png").resolve()) for k in picks[t]} for t in boards}
        for t, b in boards.items():
            shutil.rmtree(d / t / "boards", ignore_errors=True)
            jobs += [{"type": "still", "composition": "Reel", "props": studio.props(b, run), "frame": fr, "scale": 0.5,
                      "out": stills[t][k]} for k, fr in picks[t].items()]
        first = next(iter(boards.values()))
        rep = studio.render(jobs, d / "render", "sheets", board=first, run=run, hold=hold)
        found = studio.findings(rep)
        out, ok = {}, not rep.get("failed")
        for t in boards:
            here = [str((d / t / x).resolve()) for x in ("rest", "reel", "boards")]
            mine = [f for f in found if any(f.get("job", "").startswith(h) for h in here)]
            pngs = {h: [Path(j["out"]) for j in jobs if j["out"].startswith(h) and Path(j["out"]).exists()] for h in here}
            if pngs[here[0]]:
                sheet(pngs[here[0]], d / t / "sheet.png")
            if pngs[here[1]]:
                sheet(pngs[here[1]], d / t / "reel-sheet.png", cols=6)
            out[t] = {"stills": len(pngs[here[0]]), "reel_stills": len(pngs[here[1]]), "findings": studio.lines(mine)}
            ok &= not mine
            print(f"{t}: {len(pngs[here[0]])} rest stills -> {d / t / 'sheet.png'}, {len(pngs[here[1]])} reel beats -> "
                  f"{d / t / 'reel-sheet.png'}, {len(mine)} findings")
            for x in out[t]["findings"]:
                print("  " + x)
        if all(Path(f).exists() for s in stills.values() for f in s.values()):
            boards_page(list(boards), stills, run / "out" / "boards.png")
            print(f"the three looks -> {run / 'out' / 'boards.png'}")
        else:
            ok = False
            print("out/boards.png is not made: a board's hook, middle or closer still did not render")
        _env.write_json(d / "sheets.json", {"ok": ok, "failed": rep.get("failed"), "boards": out,
                                            "page": str(run / "out" / "boards.png")})
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("draft")
    p.add_argument("--template")
    sub.add_parser("check")
    sub.add_parser("sheets")
    a = ap.parse_args()
    return {"draft": draft, "check": check, "sheets": sheets}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
