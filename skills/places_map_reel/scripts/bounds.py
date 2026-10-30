"""The bounds check of a drive board, in px of its own format: what a still of the board would show wrong, found from
the board's numbers before anything renders.

check(board) returns one plain sentence per finding:
  photo   a stop's photograph enlarged past ENLARGE of its own pixels (board_drive.placed() never asks for more)
  safe    a line of type, as the studio lays it (its anchor, its rotation about its pivot, the ink of its glyphs), outside
          the format's type-safe area: every card's name and line, the hook's title and handle, each as the camera
          holds it at the end of its hold (pushed in to HOLD_END of the frame)
  floor   a line of type under FLOOR of the frame's short side (32.4 px on a 1080 px side)
  window  a pin the closer's map window does not hold: the whole route stays in sight as the closer lands
"""
import board_drive as bd

FLOOR = 0.03
# the studio rasterizes a rotated line's corner up to a pixel off its pivot's column
SLACK = 1.5


def frame_of(board):
    f = board["format"]
    sa = bd.SAFE[f["name"]]
    W, H = f["width"], f["height"]
    return W, H, (sa["left"], sa["top"], W - sa["right"], H - sa["bottom"])


def face_of(ln):
    """The face a set line stands in: its file and tracking, its words already in the case they are set in."""
    return {"file": ln["file"], "tracking": ln.get("tracking", 0), "case": "as set"}


def ink(ln, text=None):
    """The four corners of a line's ink in frame px, as the studio lays it."""
    import math
    text = text or ln["text"]
    size = ln["size"]
    w = bd.width(text, size, face_of(ln))
    box = bd.font(face_of(ln)).getbbox(text, anchor="ls")
    x0 = ln["x"] - (w if ln.get("anchor") == "end" else w / 2 if ln.get("anchor") == "middle" else 0)
    pts = [(x0, ln["y"] + box[1] / 1000 * size), (x0 + w, ln["y"] + box[1] / 1000 * size),
           (x0 + w, ln["y"] + box[3] / 1000 * size), (x0, ln["y"] + box[3] / 1000 * size)]
    a = math.radians(ln.get("rotate") or 0.0)
    if a:
        px, py = ln.get("pivot") or (ln["x"], ln["y"])
        c, s = math.cos(a), math.sin(a)
        pts = [(px + (x - px) * c - (y - py) * s, py + (x - px) * s + (y - py) * c) for x, y in pts]
    return pts


def lines_of(board):
    """Every line of type the board sets, with where it stands and the push it stands under: (where, line, text to
    measure, the share of the frame the camera holds at the end of the line's hold)."""
    rt = board["route"]
    out = []
    for c in rt["cards"]:
        out += [(f"{c['id']} {ln.get('name', 'line')}", ln, None, bd.HOLD_END) for ln in c["lines"]]
    out += [("hook kicker", ln, None, bd.HOLD_END) for ln in rt["hook"]["kicker"]]
    return out


def box(ln):
    """A line's ink as a box (x0, y0, x1, y1) in frame px."""
    pts = ink(ln)
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check(board):
    W, H, safe = frame_of(board)
    rt = board["route"]
    out = []
    for c in rt["cards"]:
        if c.get("scale", 1.0) > bd.ENLARGE + 1e-4:
            out.append(f"photo: {c['id']} ({c['name']}) is enlarged {c['scale']:g}x past its own pixels")
    for where, ln, text, push in lines_of(board):
        pts = [(W / 2 + (x - W / 2) / push, H / 2 + (y - H / 2) / push) for x, y in ink(ln, text)]
        if min(p[0] for p in pts) < safe[0] - SLACK or max(p[0] for p in pts) > safe[2] + SLACK or \
                min(p[1] for p in pts) < safe[1] - SLACK or max(p[1] for p in pts) > safe[3] + SLACK:
            out.append(f"safe: {where} \"{ln['text']}\" leaves the type-safe area")
        if ln["size"] < FLOOR * min(W, H) - 0.05:
            out.append(f"floor: {where} \"{ln['text']}\" is set at {ln['size']} px, under {FLOOR * min(W, H):.1f}")
    wx, wy, ww, wh = rt["closer"]["window"]
    for c in rt["cards"]:
        px, py = c["pin"]
        if not (wx <= px <= wx + ww and wy <= py <= wy + wh):
            out.append(f"window: {c['name']}'s pin stands outside the closer's map window")
    return out
