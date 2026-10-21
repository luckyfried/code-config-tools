"""calm: proofed to the line. Each post rises like dough in its own clear tub to its share of the top post's count,
smallest first and each rise as long as it is high; a strip of tape marks where it stopped. One scale at the wall's
left edge reads every tub."""
import math

from compose import fit_size, photo, system, text_width

BPM = 80
GAP = 22
# the beats the whole wall spends rising: each post's rise is its share of the top count times PER_FULL, so the nine
# together take about this long whatever their counts
RISE_TOTAL = 17.1
# every shot eases back this much over its length, so nothing is ever held still and nothing settles out of the frame
DRIFT = -0.04
# per format: the wall's top-left and tub size, the words' places in the wides, the hook's and the close-ups' framing
# (where the tub lands on the frame and how wide it is drawn) and the closer's tape
LAYOUT = {
    "reel": {"wall": (None, 452, 240), "handle": 316, "head": (392, 64), "hook": ([150, 600], 720, 330, 440, 84, 514),
             "close": ([30, 330], 960), "top": ([84, 966], 912, 400, 520, 574), "closer": (312, 392, 72)},
    "square": {"wall": (None, 214, 262), "handle": 74, "head": (150, 60), "hook": ([250, 372], 670, 74, 196, 76, 262),
               "close": ([60, 60], 960), "top": ([290, 390], 650, 150, 236, 282), "closer": (74, 150, 60)},
    "wide": {"wall": ("right", 92, 292), "handle": 440, "head": (520, 72), "hook": ([862, 60], 960, 400, 520, 92, 600),
             "close": ([480, 60], 960), "top": ([862, 60], 960, 520, 600, 654), "closer": (440, 520, 72)},
}


def sys_():
    return system("documentary", {"bg": "#ebe5db", "ink": "#3b3f45", "accent": "#a8552f", "accent2": "#e6d6a2", "muted": "#9a958c", "paper": "#f7f3ec"},
                  texture={"grain": 0.04}, hit={"damping": 16, "stiffness": 160, "mass": 0.8})


def geometry(b):
    """The tub's inner top, inner height and inner left and width, as the Tub component draws them."""
    x, y, w, h = b
    wall = max(6, w * 0.028)
    top = y + h * 0.045
    return top, y + h - wall - top, x + wall, w - 2 * wall


class Wall:
    def __init__(self, S, posts, frame):
        self.S, self.posts, self.f = S, posts, frame
        L = LAYOUT[frame.name]
        self.L = L
        _, y0, s = L["wall"]
        self.top = max(p["likes"] for p in posts)
        self.ticks = [str(self.top // 4 * q) for q in (1, 2, 3, 4)]
        self.label = round(34 * s / 240)
        lw = max(text_width(S, {"text": t, "size": self.label, "face": "text", "weight": 600}) for t in self.ticks)
        self.s, self.Y0, self.lw = s, y0, lw
        self.rows = math.ceil(len(posts) / 3)
        if L["wall"][0] == "right":
            self.X0 = frame.W - frame.right - 3 * s - 2 * GAP
        else:
            self.X0 = int(frame.left + lw + 7) + 30
        self.scale_x = self.X0 - 30
        self.per = min(6.0, max(1.5, round(RISE_TOTAL * self.top / sum(p["likes"] for p in posts) * 4) / 4))
        self.tape_size, self.tape_h = round(40 * s / 240), round(52 * s / 240)

    def box(self, rank):
        c, r = (rank - 1) % 3, (rank - 1) // 3
        return [self.X0 + c * (self.s + GAP), self.Y0 + r * (self.s + GAP), self.s, self.s]

    def rise(self, p):
        return p["likes"] / self.top * self.per

    def tub(self, p, at, **kw):
        b = self.box(p["rank"])
        top, ih, ix, iw = geometry(b)
        level = p["likes"] / self.top
        ty = top + ih * (1 - level)
        tx = ix + iw * 0.4
        return {"kind": "Tub", "at": round(at, 4), "box": b, "photo": photo(p, wall=True), "level": round(level, 4), "beatsPerFull": self.per,
                "rank": p["rank"], "tickLabels": [], "tapeX": round(tx, 1), "tapeW": round(iw * 0.66, 1), "tapeRot": -1.5, "tapeH": self.tape_h,
                "tape": [{"text": str(p["likes"]), "x": round(tx + 12, 1), "y": round(ty - self.tape_h / 2 + 3 + self.tape_size * 0.36, 1),
                          "size": self.tape_size, "face": "text", "weight": 700, "tracking": 0.02, "name": f"count-{p['rank']}"}], **kw}

    def scale(self, at=-4):
        """The tubs' graduations read once per row, at the wall's left edge, at the size the hook's close-up shows them."""
        rows = []
        for r in range(self.rows):
            top, ih, _, _ = geometry(self.box(1 + 3 * r))
            rows.append({"bottom": round(top + ih, 1), "top": round(top, 1)})
        return {"kind": "Scale", "at": at, "x": self.scale_x, "size": self.label, "labels": self.ticks, "rows": rows}


def words(at, lines, **kw):
    return {"kind": "Words", "at": at, "lines": lines, **kw}


def fitted(S, line, room):
    return dict(line, size=fit_size(S, line, room))


def tape_caption(S, f, p, x, y, size=30):
    """The post's caption and its date on one strip of tape, sized to its words and kept inside the safe area."""
    room = f.W - f.right - x
    while True:
        cap = {"text": p["caption"], "size": size, "face": "text", "weight": 600, "tracking": 0}
        cw = text_width(S, cap) if p.get("caption") else 0
        dw = text_width(S, dict(cap, text=p["date"]))
        w = 20 + cw + (24 if cw else 0) + dw + 20
        if w <= room or size <= 20:
            break
        size -= 1
    lines = []
    if cw:
        lines.append(dict(cap, x=x + 20, y=round(y + size * 0.36)))
    lines.append(dict(cap, text=p["date"], x=round(x + 20 + cw + (24 if cw else 0)), y=round(y + size * 0.36), color="accent"))
    return {"kind": "Tape", "at": 0.6, "fixed": True, "x": x, "y": y, "w": round(w), "h": round(size * 1.8), "rot": -1, "seed": 5, "lines": lines}


def view_for(Wl, rank, to, width):
    return {"scale": round(width / Wl.s, 3), "at": Wl.box(rank)[:2], "to": list(to)}


def build(posts, frame, words_, handle, year, bpm=BPM):
    """The calm storyboard for `posts` (rank order) in `frame`. The hook is the smallest post's tub rising, close; then
    wides and close-ups that each hold whole rises, two rises to a wide and one to a close-up, smallest first. A close-up
    is an insert of one tub: it draws that tub alone, so no neighbour's glass, ticks or tape is cut by the frame. The
    top post's long rise starts close and finishes in the wide, and the closer proofs every tub to the top."""
    S = sys_()
    f = frame
    Wl = Wall(S, posts, f)
    L = Wl.L
    asc = sorted(posts, key=lambda q: (q["likes"], -q["rank"]))
    first, top = asc[0], asc[-1]
    middle = asc[1:-1] if len(asc) > 1 else []
    left = f.left + (24 if f.name == "wide" else 24)
    x = f.left + 24
    # in the wide the words stand left of the scale, whose labels end at its x
    room_w = (Wl.scale_x - Wl.lw - 24 - x) if f.name == "wide" else (f.W - f.right - x)

    def handle_line(y, size=26, weight=500):
        return {"text": f"{handle} · {year}", "x": x, "y": y, "size": size, "face": "text", "weight": weight}

    def head(text, y, size):
        return fitted(S, {"text": text, "x": x, "y": y, "size": size, "face": "display", "weight": 600}, room_w)

    rises = {first["rank"]: -0.15}
    plan, ids = [], set()

    def name(stem):
        n, k = stem, 2
        while n in ids:
            n, k = f"{stem}-{k}", k + 1
        ids.add(n)
        return n

    t = 3.0
    i, wide_turn = 0, True
    while i < len(middle):
        take = middle[i:i + (2 if wide_turn else 1)]
        i += len(take)
        r = t + 0.25
        for p in take:
            rises[p["rank"]] = round(r, 4)
            r += Wl.rise(p) + 0.25
        end = r - 0.25 + (0.875 if wide_turn else 1.5)
        nxt = round(end * 4) / 4
        if wide_turn:
            plan.append({"id": name(f"wide-{take[-1]['likes']}"), "t": t})
        else:
            p = take[0]
            plan.append({"id": name(f"close-{p['likes']}"), "t": t, "view": view_for(Wl, p["rank"], *L["close"]), "only": p})
        t, wide_turn = nxt, not wide_turn
    if top is not first:
        rises[top["rank"]] = t
        top_at = t
        closer_at = max(t + Wl.rise(top) + 0.75, t + 3.75)
    else:
        top_at = None
        closer_at = max(t, Wl.rise(first) + 1.0)
    full = closer_at + 0.25
    end = closer_at + 5.75

    T = {p["rank"]: Wl.tub(p, rises[p["rank"]]) for p in posts}
    n = len(posts)
    Tf = [Wl.tub(p, rises[p["rank"]], fullAt=round(full + 0.15 * (n - p["rank"]), 4), fullBeats=2.5) for p in posts]
    W = [Wl.scale()] + [T[p["rank"]] for p in posts]
    hy, hd = L["handle"], L["head"]
    proofed = words(-4, [handle_line(hy), head(words_["head"], *hd)])

    hto, hwidth, h_handle, h_head, h_size, h_tape = L["hook"]
    hook_tape = tape_caption(S, f, first, x, h_tape)
    # the hook's tub is framed so its count, once pressed on, lands under the caption's tape and inside the frame: a
    # tall first rise lowers the tub, and shrinks it when lowering alone would push it off the frame
    b = Wl.box(first["rank"])
    top_, ih, _, _ = geometry(b)
    rel = (top_ + ih * (1 - first["likes"] / Wl.top) - Wl.tape_h - 8 - b[1]) / Wl.s
    limit = f.top + 10 if f.name == "wide" else h_tape + hook_tape["h"] / 2 + 14
    to_y = hto[1]
    if to_y + rel * hwidth < limit:
        to_y = limit - rel * hwidth
        if to_y + hwidth > f.H - 14:
            hwidth = (f.H - 14 - limit) / (1 - rel)
            to_y = limit - rel * hwidth
    hook_view = view_for(Wl, first["rank"], [hto[0], round(to_y)], hwidth)
    hook_layers = [T[first["rank"]], words(-2, [handle_line(h_handle)]), words(0.1, [head(words_["head"], h_head, h_size)], beats=0.7),
                   hook_tape]
    scenes = [{"id": "hook", "t": 0, "view": hook_view, "layers": hook_layers}]
    for sc in plan:
        only = sc.pop("only", None)
        scenes.append({**sc, "layers": [T[only["rank"]]] if only else W + [proofed]})
    if top_at is not None:
        tto, twidth, t_head, t_cap, t_date = L["top"]
        cap = [{"text": top["date"], "x": x, "y": t_date, "size": 32, "face": "text", "weight": 600, "color": "accent"}]
        if top.get("caption"):
            cap.insert(0, fitted(S, {"text": top["caption"], "x": x, "y": t_cap, "size": 40, "face": "text", "weight": 500}, room_w))
        scenes.append({"id": name(f"close-{top['likes']}"), "t": top_at, "view": view_for(Wl, top["rank"], tto, twidth), "layers": [
            T[top["rank"]], words(-4, [handle_line(hy), head(words_["top"], t_head, hd[1])]),
            words(top_at + 0.4, cap, beats=0.5, step=0.2)]})
        scenes.append({"id": "wide-dense", "t": top_at + 2.25, "layers": W + [words(-4, [handle_line(hy), head(words_["top"], *hd)])]})
    c_handle, c_head, c_size = L["closer"]
    ask = {"text": words_["ask"], "size": 26, "face": "text", "weight": 700, "tracking": 0.01}
    tw = round(text_width(S, ask) + 40)
    if f.name == "wide":
        tx, ty = x, c_head + 80
    else:
        tx, ty = f.W - f.right - tw, c_handle
    extra = closer_at + 0.2
    closer = [words(extra, [{"text": handle, "x": x, "y": c_handle, "size": 28, "face": "text", "weight": 600}, head(words_["promise"], c_head, c_size)],
                    beats=0.5, step=0.25),
              {"kind": "Tape", "at": round(extra + 2.2, 4), "x": tx, "y": ty, "w": tw, "h": 52, "rot": -2, "seed": 2,
               "lines": [dict(ask, x=tx + 20, y=round(ty + 9))]}]
    scenes.append({"id": "wide-closer", "t": closer_at, "same": True, "layers": [Wl.scale()] + Tf + closer})
    tape_at = -0.15 + Wl.rise(first) + 0.25
    hook = round(tape_at if tape_at <= 1.3 else 0.8, 3)
    return {"system": S, "scenes": scenes, "end": end, "hook": hook, "rests": {"hook": "hook", "dense": "wide-dense" if top_at is not None else "wide-closer",
            "closer": "wide-closer"}, "drift": DRIFT}
