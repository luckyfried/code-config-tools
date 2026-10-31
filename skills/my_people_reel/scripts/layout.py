"""The board builder's ruler and set square: the formats, the photographs placed by their subject, the phrasing of a
line, and the type system the drive board carries.

- FORMATS: reel (1080x1920), square (1080x1080) and wide (1920x1080), each with its safe area from
  design/safe-areas.json. A Frame maps the reel's design into a format: type keeps its size and its place inside the
  safe area, and a photograph is covered again so its subject lands where the format leaves room for it.
- Photos: the cast's matched photographs (public/matched/<role>.jpg and aspects.json); cover() lays one into a box
  with its subject on a mark.
- phrasing(lines, width): the designer's breaks for a sentence, never leaving a hanging article at a line's end.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

DESIGN = _env.SKILL / "design"
FLOOR = 28
REEL_SAFE = (72, 270)
FORMATS = {k: v for k, v in json.loads((DESIGN / "safe-areas.json").read_text()).items() if k != "about"}
FACE_MARGIN = 0.04   # share of the visible picture kept clear on each side of a face, so a camera push never cuts it


def system_safe():
    """The safe areas as the composition reads them (system.safe[format])."""
    return {k: {e: v[e] for e in ("top", "bottom", "left", "right")} for k, v in FORMATS.items()}


HANGING = {"the", "a", "an", "and", "my", "your", "our", "their"}
OPENING = HANGING | {"but", "so", "of", "in", "on", "to", "with", "for", "at", "from"}


def hangs(lines):
    """How many lines before the last end on an article, a possessive or "and"."""
    return sum(1 for x in lines[:-1] if x.split()[-1].strip(",.;:!?").lower() in HANGING)


def phrasing(lines, width):
    """The break cost of a set's phrasing, px of rag: a line before the last that ends on an article, a possessive or
    "and" costs half a measure squared (a designer carries those words over to the noun or the clause they open), and a
    line after the first that opens a phrase (a conjunction, an article, a preposition) earns back a tenth of the
    measure, so among even rags the one that breaks between phrases wins, and a short line over a long one never does."""
    hang = hangs(lines)
    opens = sum(1 for x in lines[1:] if x.split()[0].lower() in OPENING)
    return hang * (width * 0.5) ** 2 - opens * width * 0.1


def _breaks(words, n):
    """Every way to break `words` into n lines, as lists of lines."""
    if n == 1:
        yield [" ".join(words)]
        return
    for i in range(1, len(words) - n + 2):
        for rest in _breaks(words[i:], n - 1):
            yield [" ".join(words[:i])] + rest


class Frame:
    """One delivery format. The reel is the designed frame; x() and y() carry a reel position inside its safe area to
    the same place inside this format's safe area, so a column of type keeps its size and its measure."""

    def __init__(self, kind="reel"):
        s = FORMATS[kind]
        self.kind, self.W, self.H = kind, s["width"], s["height"]
        self.left, self.top = s["left"], s["top"]
        self.right, self.bottom = s["width"] - s["right"], s["height"] - s["bottom"]

    @property
    def reel(self):
        return self.kind == "reel"

    def x(self, rx):
        return round(self.left + (rx - REEL_SAFE[0]))

    def y(self, ry):
        return round(self.top + (ry - REEL_SAFE[1]))

    def mark(self, p):
        """Where a full-frame photograph's subject lands: the reel mark, lowered with the frame's height; in the wide
        frame it moves into the right part, beside the column of type."""
        x, y = p
        if self.reel:
            return (x, y)
        return ((self.W - 1080 + x) if self.kind == "wide" else x, round(y * self.H / 1920))

    def panel(self, box):
        """A photograph that fills the reel's width under or over its type: in the square the same band of the frame
        under the type's new place (None when it no longer has room); in the wide the right part of the frame."""
        x, y, w, h = box
        if self.reel:
            return list(box)
        if self.kind == "wide":
            return [self.W - 880, 0, 880, self.H]
        top = self.y(y)
        h = min(h, self.H - top)
        return [0, top, self.W, h] if h >= 200 else None


def trimmed(row):
    """A cast entry with its point, tip, face and heads moved from the whole photograph into the part its `trim`
    keeps (the part cast.py match writes)."""
    if not row.get("trim"):
        return row
    u0, v0, u1, v1 = row["trim"]
    u = lambda x: round(min(1.0, max(0.0, (x - u0) / (u1 - u0))), 4)
    v = lambda y: round(min(1.0, max(0.0, (y - v0) / (v1 - v0))), 4)
    out = dict(row)
    for k in ("point", "tip"):
        if row.get(k):
            out[k] = [u(row[k][0]), v(row[k][1])]
    if row.get("face"):
        f = row["face"]
        out["face"] = [u(f[0]), v(f[1]), u(f[2]), v(f[3])]
    if row.get("heads"):
        out["heads"] = {h: [u(x), v(y)] for h, (x, y) in row["heads"].items()}
    return out


def banded(row, band):
    """A cast entry (a person's photograph, or the group's) with its point, tip, face and heads moved from its
    photograph into the band [v0, v1] the photograph spans in its framed picture."""
    v0, v1 = band
    v = lambda y: round(v0 + y * (v1 - v0), 4)
    out = dict(row)
    for k in ("point", "tip"):
        if row.get(k):
            out[k] = [row[k][0], v(row[k][1])]
    if row.get("face"):
        f = row["face"]
        out["face"] = [f[0], v(f[1]), f[2], v(f[3])]
    if row.get("heads"):
        out["heads"] = {h: [u, v(y)] for h, (u, y) in row["heads"].items()}
    return out


class Photos:
    """The cast's matched photographs for one run (public/matched/), each named by its role. aspects.json gives each
    picture's height over its width; a framed photograph (cast.py match) also gives its band, and `cast` here is the
    run's cast with every point of a framed photograph moved into its band, so a place on the picture is a place on
    the photograph."""

    def __init__(self, cast, public):
        self.public = Path(public)
        index = self.public / "matched" / "aspects.json"
        if not index.exists():
            sys.exit("public/matched/aspects.json is missing: run cast.py match")
        got = json.loads(index.read_text())
        self.aspect = {r: x["aspect"] if isinstance(x, dict) else x for r, x in got.items()}
        self.band = {r: x["band"] for r, x in got.items() if isinstance(x, dict)}
        people = {h: [trimmed(r) for r in rows] for h, rows in cast.get("people", {}).items()}
        self.cast = {**cast, "people": {h: [banded(r, self.band[f"{h}-{i}"]) if f"{h}-{i}" in self.band else r for i, r in enumerate(rows)]
                                        for h, rows in people.items()}}
        if cast.get("group"):
            self.cast["group"] = trimmed(cast["group"])
            if "group" in self.band:
                self.cast["group"] = banded(self.cast["group"], self.band["group"])
        self._light = {}

    def framed(self, role):
        """True when the role's photograph lies whole across its picture: a crop never enlarges it past filling."""
        return role in self.band

    def light(self, shot, part=(0.0, 0.0, 1.0, 1.0)):
        """Mean lightness (0 to 1) of the part of a placed Shot's visible picture given as fractions of its box."""
        key = (shot["file"], tuple(shot["crop"]), tuple(shot["box"]), part)
        if key not in self._light:
            from PIL import Image, ImageStat
            im = Image.open(self.public / shot["file"]).convert("L")
            W, H = im.size
            x, y, w, h = shot["box"]
            cx, cy, cw = shot["crop"]
            img_w = w / cw
            u0, u1 = cx + part[0] * w / img_w, cx + part[2] * w / img_w
            v0, v1 = cy + part[1] * h / (img_w * shot["aspect"]), cy + part[3] * h / (img_w * shot["aspect"])
            box = (int(max(0, u0) * W), int(max(0, v0) * H), int(min(1, u1) * W), int(min(1, v1) * H))
            self._light[key] = ImageStat.Stat(im.crop(box)).mean[0] / 255 if box[2] > box[0] and box[3] > box[1] else 0.5
        return self._light[key]

    def role(self, handle, i=0):
        """The role name of a person's i-th photograph, falling back to the last one they have."""
        ph = self.cast["people"].get(handle) or []
        if not ph:
            return None
        return f"{handle}-{min(i, len(ph) - 1)}"

    def info(self, role):
        if role == "group":
            return self.cast["group"]
        h, _, i = role.rpartition("-")
        return self.cast["people"][h][int(i)]

    def point(self, role):
        return tuple(self.info(role)["point"])

    def close(self, role, use):
        """(zoom, (tx, ty)): how much closer than the widest fill the photograph sits for a use (full, bar, frame,
        slice) and where its point lands, as fractions of the box."""
        c = (self.info(role).get("close") or {}).get(use)
        if c is None:
            return 1.0, (0.5, 0.5)
        if isinstance(c, (int, float)):
            return float(c), (0.5, 0.5)
        return float(c[0]), (tuple(c[1:3]) if len(c) >= 3 else (0.5, 0.5))

    def face(self, role):
        return self.info(role).get("face")

    def face_width(self, role, h):
        """The widest box `h` px tall that a crop of `role` fills with the face the cast names whole inside it, with the
        margin a crop keeps around a face (no limit for a photograph with no face named)."""
        face = self.face(role)
        if not face:
            return float("inf")
        return (1 - 2 * FACE_MARGIN) * h / (max(face[3] - face[1], 1e-6) * self.aspect[role])

    def tip(self, role):
        return tuple(self.info(role).get("tip") or self.point(role))

    def place(self, role, box, use="full", zoom=None, scale=1.0):
        """A Shot of `role` in `box` with the use's own closeness (times `scale`) and its point on the use's mark."""
        z, (tx, ty) = self.close(role, use)
        return self.cover(role, box, (tx * box[2], ty * box[3]), (zoom or z) * scale)

    def full(self, role, F, use="full", zoom=None, scale=1.0):
        """A Shot of `role` filling the whole frame of format F, its point on the use's mark carried into the format."""
        z, (tx, ty) = self.close(role, use)
        return self.cover(role, [0, 0, F.W, F.H], F.mark((tx * 1080, ty * 1920)), (zoom or z) * scale)

    def cover(self, role, box, to, zoom=1.0, at=None):
        """A Shot of `role` filling `box` [x, y, w, h] px, `zoom` times closer than the widest crop that fills it, with
        source point `at` (the role's own point when unset) landing on box point `to` (px inside the box), as near as the
        source's edges allow. A face the cast names is never cut: the zoom comes back until the face fits the box with
        a margin (never wider than the widest fill), and the crop moves until the whole face is inside."""
        x, y, w, h = box
        a = self.aspect[role]
        at = at or self.point(role)
        base = min(1.0, a * w / h)
        face = self.face(role)
        if face:
            fw, fh = face[2] - face[0], (face[3] - face[1])
            zoom = max(1.0, min(zoom, (1 - 2 * FACE_MARGIN) * base / max(fw, 1e-6),
                                (1 - 2 * FACE_MARGIN) * h * base / max(fh * w * a, 1e-6)))
        cw = base / zoom
        img_w = w / cw
        img_h = img_w * a
        ch = h / img_h
        cx = at[0] - to[0] / img_w
        cy = at[1] - to[1] / img_h
        if face:
            mx, my = FACE_MARGIN * cw, FACE_MARGIN * ch
            cx = min(max(cx, face[2] + mx - cw), face[0] - mx)
            cy = min(max(cy, face[3] + my - ch), face[1] - my)
        cx = min(max(cx, 0), 1 - cw)
        cy = min(max(cy, 0), 1 - ch)
        return {"kind": "Shot", "file": f"matched/{role}.jpg", "aspect": a, "box": [round(v) for v in box],
                "crop": [round(cx, 4), round(cy, 4), round(cw, 4)], "role": role}

    def frame_crop(self, role, fw, fh, zoom=1.0, to=(0.5, 0.5), at=None):
        a = self.aspect[role]
        at = at or self.point(role)
        cw = min(1.0, a * fw / fh) / zoom
        img_w = fw / cw
        ch = fh / (img_w * a)
        cx = min(max(at[0] - to[0] * fw / img_w, 0), 1 - cw)
        cy = min(max(at[1] - to[1] * fh / (img_w * a), 0), 1 - ch)
        return {"file": f"matched/{role}.jpg", "aspect": a, "crop": [round(cx, 4), round(cy, 4), round(cw, 4)], "role": role}
