"""The bounds check: what a board's frames hold when each beat comes to rest, measured from the board alone.

Every beat is read as its layers set it: each photograph (Photo, and the grid's Slice tiles) a box on the frame, each
line of type the box its face draws it in, each shade the box it darkens. The check fails a board when, at rest:

- a line of type leaves the safe area (the format's, kept clear of the card's letterbox bars);
- two lines of one beat overlap;
- words that stand on the ground run onto a photograph, or words that stand on a photograph (`over`) have no shade
  under them;
- a line set in the display face is drawn smaller than its format's floor (story.FLOOR);
- a photograph's subject (its focus) falls outside the part of it the frame shows;
- a grid tile leaves the frame or meets another.

Run as `python3 bounds.py <board.json>...`: prints the findings and exits 1 when there are any."""
import json
import sys

import compose
import story


def inside(a, b, tol=0.5):
    return a[0] >= b[0] - tol and a[1] >= b[1] - tol and a[2] <= b[2] + tol and a[3] <= b[3] + tol


def meets(a, b, pad=0.0):
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad


def rect(b):
    return (b[0], b[1], b[0] + b[2], b[1] + b[3])


def check_beat(board, bt, frame):
    """The findings of one beat at rest."""
    S = board["system"]
    out = []
    say = lambda x: out.append(f"{bt['id']}: {x}")
    lines = [ln for L in bt["layers"] if L["kind"] == "Words" for ln in L["lines"] if ln.get("text")]
    boxes = [compose.text_box(S, ln, ink=True) for ln in lines]
    for ln, bx in zip(lines, boxes):
        if not inside(bx, frame.safe):
            say(f"\"{ln['text']}\" at [{bx[0]:.0f}, {bx[1]:.0f}, {bx[2]:.0f}, {bx[3]:.0f}] leaves the safe area {list(frame.safe)}")
        if ln["face"] == "display" and ln["size"] < story.FLOOR[frame.name] - 0.5:
            say(f"\"{ln['text']}\" is drawn at {ln['size']} px, under the {story.FLOOR[frame.name]} px floor")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if meets(boxes[i], boxes[j], 2):
                say(f"\"{lines[i]['text']}\" and \"{lines[j]['text']}\" overlap")
    photos = [L for L in bt["layers"] if L["kind"] in ("Photo", "Slice")]
    shades = [rect(L["box"]) for L in bt["layers"] if L["kind"] == "Shade"]
    for L in (L for L in bt["layers"] if L["kind"] == "Words"):
        for ln in L["lines"]:
            bx = compose.text_box(S, ln, ink=True)
            if L.get("over"):
                if not any(inside(bx, s, 1) for s in shades):
                    say(f"\"{ln['text']}\" stands on the photograph with no shade under it")
            elif bt["form"] != "wall":
                for p in photos:
                    if meets(bx, rect(p.get("window") or p["box"]), 2):
                        say(f"\"{ln['text']}\" runs onto the photograph at {[round(v) for v in p['box']]}")
    for p in photos:
        x, y, w, h = p["box"]
        u0, v0, u1, v1 = p["uv"]
        fx, fy = (p.get("focus") or [None, None])
        if fx is None:
            continue
        if not (u0 <= fx <= u1 and v0 <= fy <= v1):
            say(f"the subject of {p['photo']['file']} at {fx:.2f}, {fy:.2f} is cropped out of its box")
    if bt["form"] == "wall":
        tiles = [rect(p["box"]) for p in photos]
        for t in tiles:
            if not inside(t, (0, 0, frame.W, frame.H), 0.5):
                say(f"a grid tile at {[round(v) for v in t]} leaves the frame")
        for i in range(len(tiles)):
            for j in range(i + 1, len(tiles)):
                if meets(tiles[i], tiles[j]):
                    say("two grid tiles meet")
    return out


def check(board):
    """Every bounds finding of a board, one plain sentence each."""
    compose.use(board["style"])
    frame = compose.Frame(board["format"]["name"], board["system"]["finish"].get("bars", 0.0))
    out = []
    for bt in board["beats"]:
        out += check_beat(board, bt, frame)
    return out


def main(paths):
    bad = 0
    for p in paths:
        f = check(json.loads(open(p).read()))
        bad += len(f)
        print(f"{'PASS' if not f else 'FAIL'}  {p}: {len(f)} findings")
        for x in f:
            print("   ", x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
