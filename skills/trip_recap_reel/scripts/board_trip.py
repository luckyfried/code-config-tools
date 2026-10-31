"""trip: the trip stop by stop, in one look. The hook is their first photograph under the trip's name and its dates; then
each later stop is a beat of its own, their photograph filling the frame, the place's name and their own caption set on
it, the camera moving through the photograph from where they stood to what it looks at; the closer is the look's own
(styles/<id>.json `closer`): a title card in their words with the bars closing, their closing line under projector
flicker, or the book closing on its cover. Every stop is a moment of theirs; nothing on screen is a count.

Everything about how a beat looks is the card's: its move and the cut into it are picked from the card's allowlists by
what the beat holds (its form, a portrait or a landscape, words or none, the peak, the people in it, a new city), never
by its place in the order, and never the same move twice running. A stop holds as long as its line takes to read, longer
at the peak, with someone in it, on a portrait, or in a new city, and shorter with no words; the board's tempo is the
middle of the card's music recipe, so every cut lands on a beat of the bed.

Times are in beats from the film's start, at the board's tempo."""
import json
import math
import re
from pathlib import Path

import sfx
import style
from board_parts import compass, km_between, mapped

CLOSER = 1.5  # bars of the closer: its words land in the first two beats and the card holds no longer than it reads
SAYS = 24  # the longest closing line, in characters, the closer sets at a size a phone reads (its display face at 110 px)
HOLD = 2.0  # seconds the picture holds still and silent at the end
SHORTEST, LONGEST = 4, 10  # beats a stop's span may run: one bar, and the most that never holds two bars silent
# the moves that set the beat's label themselves, where they set it, and the label they are given: a date stamp prints the
# stop's date, the others the place's name; the kit's own words leave out whatever the move already sets
SETS_LABEL = {"date-stamp": "bottom", "polaroid-drop": "bottom", "sticker-pop": "top",
              "long-fade-title": "middle"}
DATED = {"date-stamp"}
SETS_WORDS = {"long-fade-title"}
ANCHORS = ("top", "middle", "bottom")
MOST_IN_ONE = 0.7  # the share of a board's worded beats one anchor may hold
# the moves that take the frame and fly the photograph in before it lands (motion/system/moves/move/<id>.tsx), the
# seconds each flies; a beat with one holds that long and SETTLE more, so its words come on and read once it has landed
ARRIVES = {"picture-tunnel": 1.1, "exploded-layers": 1.15, "tilted-wall": 1.2}
SETTLE = 0.3
LONG_CUT = 2  # beats: a cut this long or longer is a long one
TITLE_AT = 1.0  # beats into the hook the trip's name comes on (motion/studio/words.tsx)


def bpm_of(c):
    """The board's tempo: the middle of its card's music recipe's tempo range."""
    book = json.loads((style.SKILL / "music" / "recipes.json").read_text())["recipes"]
    lo, hi = book[c["music"]]["tempo"]
    return round((lo + hi) / 2)


def onscreen(caption):
    """Their caption as the film sets it: the words, without the handles and hashtags the post carries for the feed."""
    words = re.sub(r"\s+", " ", re.sub(r"[@#][\w.]*\w", "", caption or ""))
    return re.sub(r" ([,;.!?])", r"\1", words).strip(" ,;")


def read_beats(caption, bpm):
    """Beats a line takes to read on screen (0.9 s and 0.3 s a word), three to six."""
    return min(6, max(3, round((0.9 + 0.3 * len(caption.split())) * bpm / 60)))


def legs_of(src):
    """Each stop's leg in from the stop before (km, or days when the trip has no coordinates) and its bearing."""
    st, on_map = src["stops"], mapped(src)
    out = [(0.0, None)]
    for a, b in zip(st, st[1:]):
        out.append(km_between(a, b) if on_map else (float(b["day"] - a["day"]), None))
    return out


def tags_of(src, i, peak):
    """What stop `i` holds, in the words a card's `fits` lists use."""
    s = src["stops"][i]
    words = onscreen(s.get("caption"))
    prev = src["stops"][i - 1] if i else None
    tags = {"clip" if s.get("clip") else "photo", "words" if words else "wordless"}
    if s["aspect"] > 1.15:
        tags.add("portrait")
    elif s["aspect"] < 0.87:
        tags.add("landscape")
    if i == peak:
        tags.add("peak")
    if "@" in (s.get("caption") or ""):
        tags.add("people")
    if prev is not None and s.get("city") and s.get("city") != prev.get("city"):
        tags.add("place")
    return tags


def length_of(tags, caption, bpm, hook, move=None):
    """Beats a stop's span runs, from what it holds; a move that flies the photograph in holds it at least until its
    words have read after the landing."""
    read = read_beats(caption, bpm)
    n = read + 1 + 2 * ("peak" in tags) + ("people" in tags or "portrait" in tags) + ("place" in tags) - ("wordless" in tags)
    return max(SHORTEST + hook, min(LONGEST, n + 2 * hook), landing(move, bpm) + read + 1 if move in ARRIVES else 0)


def landing(move, bpm):
    """Whole beats at `bpm` a move that flies the photograph in takes to land and settle; none for any other move."""
    return math.ceil((ARRIVES[move] + SETTLE) * bpm / 60) if move in ARRIVES else 0


def leaning(s, move):
    """Where the beat's words want to sit, from -1 (the top) to 1 (the bottom): away from what the photograph looks at,
    and away from the label its move sets; None when the move sets every word itself."""
    if move in SETS_WORDS:
        return None
    lean = (0.5 - s["points"]["far"][1]) * 2.5
    if SETS_LABEL.get(move) == "bottom":
        lean -= 1.5
    return max(-1.0, min(1.0, lean))


def anchors(leans, fixed):
    """Each beat's anchor from its leaning, then, while one anchor holds more than MOST_IN_ONE of the worded beats, the
    beat that leans least moved to the other end; `fixed` beats keep theirs."""
    out = [None if l is None else ("top" if l < 0 else "bottom") for l in leans]
    out = [fixed.get(i, a) for i, a in enumerate(out)]
    worded = [i for i, a in enumerate(out) if a]
    while worded:
        counts = {a: sum(out[i] == a for i in worded) for a in ANCHORS}
        most = max(counts, key=counts.get)
        if counts[most] <= MOST_IN_ONE * len(worded):
            break
        free = [i for i in worded if out[i] == most and i not in fixed and leans[i] is not None]
        if not free:
            break
        k = min(free, key=lambda i: abs(leans[i]))
        out[k] = "bottom" if most == "top" else "top"
        fixed = {**fixed, k: out[k]}
    return out


def board(src, c):
    """The board's own parts in the look `c`: the route of stops with their times, the beats with their moves, cuts, words
    and anchors, what the film sounds, the clips."""
    bpm = bpm_of(c)
    st = src["stops"]
    legs = legs_of(src)
    on_map = mapped(src)
    peak = max(range(1, len(st)), key=lambda i: (legs[i][0], -i)) if len(st) > 1 else None
    beats, stops, t = [], [], 0.0
    used_m, used_t, prev, prev_cut = {}, {}, None, None
    # a look that ends on their closing line takes it from the last stop that has one; a line short enough to read on a
    # phone is said once, as the last thing on screen, and that stop plays wordless, and a longer line plays whole on its
    # stop while the closer holds its last phrase, the way a film comes back to the line it just said
    lines = [i for i, s in enumerate(st) if i and onscreen(s.get("caption"))]
    last = lines[-1] if c["closer"] == "closing-flicker" and lines else None
    echo = last_phrase(onscreen(st[last].get("caption"))) if last is not None else ""
    held = last if last is not None and not echo else None
    for i, s in enumerate(st):
        tags = tags_of(src, i, peak)
        form = "title" if i == 0 else ("clip" if s.get("clip") else "photo")
        caption = "" if i == held else onscreen(s.get("caption"))
        # the hook opens on a move the card makes for its title; a later beat's form counts as one more thing it holds, so what
        # is in the photograph decides its move and its cut; their own clip plays where the photograph would have been,
        # so it takes the move and the cut the photograph would have taken
        # a stop whose card stands the photograph in a box of its own never takes a move that lays a print or a margin of
        # its own over the page: that print would sit inside the card's print and its paper would cover the card's line
        moves = c["moves"] if i == 0 or full_frame(c) else [m for m in c["moves"] if m["id"] not in WINDOWED] or c["moves"]
        seen = (tags - {"clip"}) | {"photo"}
        opens = [m for m in moves if "title" in m["fits"]] or moves
        ahead = {m["id"] for m in moves if m.get("once") and "photo" in m["fits"]} if peak is not None and i < peak else set()
        move = style.pick(opens, tags, form, used_m, prev, ahead) if i == 0 else style.pick(moves, seen, "", used_m, prev, ahead)
        # a long cut never follows a long cut: a stop between two plays half of each over its picture and holds longest
        short = [x for x in c["transitions"] if cut_beats(x["id"]) < LONG_CUT] if cut_beats(prev_cut) >= LONG_CUT else []
        cut = None if i == 0 else style.pick(short or c["transitions"], seen, "", used_t, None)
        n = length_of(tags, caption, bpm, i == 0, move)
        km, brg = legs[i]
        stops.append({"name": s["name"], "place": s["place"], "city": s.get("city"), "photo": s["photo"], "aspect": s["aspect"],
                      "long": s.get("long"), "near": s["points"]["near"], "far": s["points"]["far"], "caption": caption,
                      "date": s["date"], "leg": round(km, 2),
                      "compass": compass(brg) if brg is not None and on_map else None, "clip": bool(s.get("clip")),
                      "at": t, "end": t + n})
        label = s["date"] if move in DATED else s["name"]
        beats.append({"id": "hook" if i == 0 else f"stop-{i + 1}", "form": form, "bars": n / 4, "move": move, "transition": cut,
                      "fly": ARRIVES.get(move, 0.0), "tags": sorted(tags), "words": caption, "label": label, "peak": i == peak,
                      "stops": [i]})
        prev, prev_cut, t = move, cut, t + n
    closing = style.pick(c["transitions"], {"closer"}, "closer", used_t, None)
    # a stop's line reads between the cut into its beat and the cut out of it, each of which plays half its length over
    # the beat, so a stop holds those halves, a flown-in photograph's landing and settle, the label's lead and the line's
    # fade on top of the time its line takes to read
    # fade on top of the time its line takes to read; the peak holds at least as long as any other stop after the hook
    cuts = [b["transition"] for b in beats[1:]] + [closing]
    for i, b in enumerate(beats):
        if i and b["words"]:
            landed = (b["fly"] + SETTLE) * bpm / 60 if b["fly"] else 0.0
            need = (max(0.25, cut_beats(b["transition"]) / 2, landed) + 0.5 + read_beats(b["words"], bpm)
                    + max(0.5, cut_beats(cuts[i]) / 2) + 0.6)
            b["bars"] = max(b["bars"], math.ceil(need) / 4)
    if peak is not None:
        beats[peak]["bars"] = max(b["bars"] for b in beats[1:])
    t = 0
    for st_i, b in zip(stops, beats):
        st_i["at"], st_i["end"] = t, t + 4 * b["bars"]
        t = st_i["end"]
    leans = [leaning(s, b["move"]) if b["words"] or b["form"] == "title" else None for s, b in zip(st, beats)]
    fixed = {0: "middle"} if c["closer"] == "title-card" else {}
    for b, a in zip(beats, anchors(leans, fixed)):
        b["anchor"] = a
    beats.append({"id": "closer", "form": "closer", "bars": CLOSER, "move": None,
                  "transition": closing, "tags": ["closer"],
                  "words": "", "label": "", "peak": False, "anchor": None, "stops": list(range(len(st)))})
    trip = src["trip"]
    signoff = echo or (onscreen(st[held].get("caption")) if held is not None else f"{trip['range']} {trip['year']}")
    handle = src.get("handle") or ""
    r = {"title": trip["label"], "kicker": f"{trip['range']} {trip['year']}", "stops": stops, "mapped": on_map,
         "closer": closer_of(t, bpm), "signoff": signoff or trip["label"],
         "handle": "" if handle in ("", "you") else (handle if handle.startswith("@") else f"@{handle}")}
    out = {"bpm": bpm, "route": r, "beats": describe(r, beats, c), "clips": clips(r, src, bpm)}
    return dict(out, sound=sound(out))


CUTS = Path(__file__).resolve().parents[1] / "motion" / "system" / "moves" / "cut"


def cut_beats(cut):
    """The beats a cut plays, as its file in the film's system (motion/system/moves/cut/<id>.tsx) gives them; none for
    no cut."""
    if not cut:
        return 0.0
    m = re.search(r"beats:\s*([\d.]+)", (CUTS / f"{cut}.tsx").read_text())
    return float(m.group(1)) if m else 0.0


# the moves that lay the picture on a page through a print or a margin of their own (motion/system/moves/move/<id>.tsx);
# page-drift's margin stands wide of a card's print and its line, so it can drift a pasted print
WINDOWED = {"polaroid-drop", "tape-slap"}


def full_frame(c):
    """Whether the card stands a stop's photograph over the whole frame (its picture box is the frame)."""
    pic = c["photo"]["picture"]
    return pic["show"] and list(pic["box"]) == [0, 0, 1, 1]


def last_phrase(line):
    """The phrase the closer holds of a closing line too long to read whole on a phone: its last clause, when that clause
    reads; empty when the whole line reads or no clause of it does, and the closer says the whole line."""
    if len(line) <= SAYS:
        return ""
    tail = re.split(r"[,;:.!?\u2014\u2013]\s*|\s+-\s+", line.rstrip(" ,;:.!?"))[-1].strip()
    return tail if 0 < len(tail) <= SAYS and tail != line else ""


def closer_of(at, bpm):
    """The closer from beat `at` at `bpm`: it runs CLOSER bars and holds still and silent for its last HOLD seconds."""
    return {"at": at, "still": round(at + CLOSER * 4 - HOLD * bpm / 60, 3)}


def km(x):
    """A leg's length as the storyboard writes it: whole kilometers, never under one once there is any."""
    return f"{max(1, round(x)) if x > 0 else 0}"


CLOSERS = {"title-card": "a title card: the trip's name centered in the display face's capitals over its dates, the bars closing on it",
           "closing-flicker": "their closing line on the dark of a projector screen, flickering with the lamp as the roll runs out",
           "book-cover": "the book closing: the cover slides over the page, the trip's name written on it over its dates"}


def describe(r, beats, c):
    """What each beat shows, in plain words, for storyboard.md."""
    st = r["stops"]
    for b in beats:
        if b["form"] == "closer":
            b["shows"] = CLOSERS.get(c["closer"], c["closer"])
            continue
        s = st[b["stops"][0]]
        said = f"their line \"{s['caption']}\"" if s["caption"] else "no words, as they posted it"
        if b["id"] == "hook":
            b["shows"] = f"{s['name']}, their first photograph, under \"{r['title']}\" and its dates, then {said}"
        else:
            way = f", {km(s['leg'])} km {s['compass']} of the last stop" if s["compass"] else ""
            where = "filling the frame" if full_frame(c) else "pasted on the page"
            b["shows"] = (f"{s['name']}{way}: their {'own clip' if s['clip'] else 'photograph'} {where}, the camera "
                          f"moving from where they stood to what it looks at, {said}")
    return beats


def fx_board(b):
    """The board as the shared effects read it (sfx.py): each beat's form, move and cut, where it starts, where its
    picture lands, and the words on it, in beats from the film's start at the board's tempo."""
    r, out, at = b["route"], [], 0.0
    for x in b["beats"]:
        end = at + 4 * x["bars"]
        kind = {"title": "Title", "closer": "Closer"}.get(x["form"], "Photo")
        layer = {"kind": kind, "at": {"arrive": at + (x.get("fly") or 0.0) * b["bpm"] / 60, "end": end}}
        if kind == "Title":
            # the trip's name comes on TITLE_AT beats in and lands on an impact
            layer.update(title={"text": r["title"]}, slam=[at + TITLE_AT, 0])
        elif kind == "Closer":
            layer["signoff"] = {"text": r["signoff"]}
        else:
            layer.update(label=x.get("label") or "", text=x.get("words") or "")
        out.append({"id": x["id"], "form": x["form"], "move": x.get("move"), "transition": x.get("transition"), "start": at,
                    "layers": [layer]})
        at = end
    return {"id": b.get("id") or r["title"], "bpm": b["bpm"], "beats": out}


SOUNDS = {"air": "a soft air into {name}", "sweep": "the cut to {name} sweeps past", "bright": "the cut to {name}, the film's one bright sweep",
          "shutter": "{name}'s photograph lands", "pop": "the mark lands on {name}", "riser": "the build into the closer"}


def sound(b):
    """What the film sounds, each where something lands (`at` in beats), for storyboard.md and the checks: the shared
    effects (sfx.py) the film is mixed with as it renders, each on the nearest quarter beat; then the stop, where the
    music cuts and the picture holds silent. The hook's title lands on an impact and the closer opens on one."""
    fb, sec = fx_board(b), 60 / b["bpm"]
    names = {x["id"]: (b["route"]["stops"][x["stops"][0]]["name"] if x["form"] != "closer" else "the closer") for x in b["beats"]}
    out = []
    for t, kind in sfx.events(fb)[0]:
        at = round(t / sec, 3)
        beat = [x["id"] for x in fb["beats"] if x["start"] <= at + 1e-6][-1]
        what = ("the trip's name lands" if beat == "hook" else "the closer opens") if kind == "impact" else SOUNDS[kind]
        out.append({"kind": kind, "at": at, "beat": beat, "what": what.format(name=names[beat])})
    out.append({"kind": "stop", "at": b["route"]["closer"]["still"], "beat": "closer", "what": "the picture and the music stop together"})
    return sorted(out, key=lambda x: x["at"])


MOVES = {
    "push": "pushes in at a slow walking pace toward the {where} of the frame{drift}, {tilt}, steady as a gimbal",
    "track": "tracks sideways at walking pace{side}, the near ground sliding past faster than the {where} of the frame, level",
    "rise": "starts low over the near ground and cranes up slowly, {tilt}, until the {where} of the frame stands clear",
    "arc": "arcs slowly around the {where} of the frame at eye height, holding it centered while the background turns behind it",
}


def move_of(s, after, first=None):
    """The camera move for a clip of the photograph: the one its points suggest (a far point high in the frame rises to
    it, one off to a side tracks toward it, one deep in the frame pushes in, else an arc), `first` ahead of them when
    given, and never the move of the clip before it."""
    (nu, nv), (fu, fv) = s["near"], s["far"]
    pick = "rise" if fv < 0.4 else "track" if abs(fu - nu) > 0.12 else "push" if nv - fv > 0.12 else "arc"
    order = ([first] if first else []) + [pick] + list(MOVES)
    return next(m for m in order if m != after)


def where_of(s):
    """Where in the photograph's frame what it looks at (its far point) sits, in words."""
    fu, fv = s["far"]
    return (("upper" if fv < 0.4 else "lower" if fv > 0.66 else "middle") + " " +
            ("left" if fu < 0.36 else "right" if fu > 0.64 else "center"))


def shot(s, sees, secs, move, lens):
    """A clip request as a cinematographer writes a shot: what the photograph shows, what moves in it and its light
    (`sees`, written by eye at the points step), the camera's move toward what it looks at, its lens feel, the length,
    and a loop."""
    (nu, nv), (fu, fv) = s["near"], s["far"]
    words = {"where": where_of(s),
             "drift": ", drifting right" if fu - nu > 0.12 else ", drifting left" if fu - nu < -0.12 else "",
             "side": " to the right" if fu >= nu else " to the left",
             "tilt": "tilting up a touch as it goes" if fv < 0.4 else "looking down a touch" if fv > 0.66 else "level"}
    return (f"{sees.rstrip('. ')}. The camera starts at eye height where the photographer stood and "
            f"{MOVES[move].format(**words)}; {lens}. One continuous {secs} second shot with no cut, the light and every "
            "moving thing settling back to the first frame at the end so it loops seamlessly. Nothing added that is not "
            "in the photograph: no text, captions or logos.")


def clips(r, src, bpm):
    """The clips an image-to-video model would make: every photograph brought to life over its beat (a stop shown by
    their own clip needs none), each with a camera move unlike the clip before it. `stand_in` says what the film does
    with the still photograph when no clip has arrived. A clip's `window` is the beats it plays over."""
    pulse = 30 * 60 / bpm
    secs = lambda a, b: round((round(b * pulse) - round(max(0.0, a) * pulse)) / 30, 1)
    st = r["stops"]
    out, last = [], None
    for i, (s, raw) in enumerate(zip(st, src["stops"])):
        sees = raw.get("sees") or f"The scene at {raw.get('place') or s['name']}"
        win = [round(s["at"], 3), round(s["end"], 3)]
        c = {"id": f"{i:02d}", "beat": "hook" if i == 0 else f"stop-{i + 1}", "image": s["photo"], "window": win, "seconds": secs(*win)}
        if raw.get("clip"):
            c.update(role="their own clip", source=raw["clip"], prompt=None, stand_in=None)
            last = None
        else:
            last = move_of(s, last, "rise" if i == 0 else None)
            lens = ("a 24 mm wide lens feel, deep focus, the whole place open around its subject" if i == 0 else
                    "a 28 mm wide lens feel, deep focus from the near ground to the far end" if s["aspect"] < 1 else
                    "a 35 mm lens feel, the subject sharp and the far background a little soft")
            c.update(role="the hook's world" if i == 0 else "the photograph brought to life", move=last,
                     prompt=shot(s, sees, c["seconds"], last, lens),
                     stand_in="the camera moves through the still photograph from where they stood to what it looks at")
        out.append(c)
    return out
