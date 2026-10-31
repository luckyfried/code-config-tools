"""The year's storyboard, drafted from an export the way a run drafts it: gather, research, the moments curated, the
photographs read, then the draft. Research drafts the moments from the posts (the month's photograph, the date, their
line, the people, the place), never from counts; picks.py takes each month's photograph from its moment, else the post
with the most to say, never by its likes. The draft refuses a month whose photograph has not been read, lays the
months out in calendar order whatever order picks.json lists them in, names each photograph by its scene, sets every
month's words in paper on one ink plate, lays the wall on the first month's photograph, runs the months two quick and
one held over and over with the peak longest, flashes the hook's months alike, says each month's own line under its
name over its line inside the type area (picks.py finds a line with room above it for them, and a line without that
room is a finding), closes on the year's rows, all alike, with no count anywhere, and ends on the sign-off landing on
the stop and two seconds of silence.

The film's camera, from motion/studio/year/camera.ts bundled with the kit's own esbuild and run over the drafted board
frame by frame, as the pose the kit sets: while it holds on a month the picture is inside that month's own photograph,
each month's in turn in calendar order, and between two months inside a month's field, never the wall; it draws back
off each month and pushes into the next past its mark; a month's words stay inside the type area through its hold; the
year on the wall shows only while it is wholly in the picture, and never under an open month's photograph.

    python3 -I -m unittest discover -s S/tests
"""
import calendar
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "scripts"))
import music  # noqa: E402
import style  # noqa: E402
import year as yr  # noqa: E402
LOOK = style.TRIO[0]  # the board these tests read: the trio's first look
ENV = dict(os.environ, CSC_DISABLE_KEYCHAIN="1")
# (month, posts, light of the photograph 0-255): June posted most, May bright, December a night photograph
YEAR = [(1, 5, 120), (2, 6, 110), (3, 7, 130), (4, 6, 100), (5, 8, 235), (6, 14, 140), (7, 9, 125), (8, 7, 115),
        (9, 6, 105), (10, 8, 120), (11, 7, 150), (12, 6, 25)]


def photo(path, light, k):
    """A photograph with a horizon: sky above, ground below, a mean light near `light`, and its subject (a sun) high in
    the sky, clear of the words that stand on the horizon."""
    im = Image.new("RGB", (1200, 1500), (light, light, min(255, light + 10)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 900, 1200, 1500], fill=(max(0, light - 20), max(0, light - 30), max(0, light - 40)))
    d.ellipse([200 + 40 * k, 120, 500 + 40 * k, 420], fill=(min(255, light + 20), max(0, light - 40), max(0, light - 60)))
    im.save(path, quality=90)


MOTION = KIT / "motion"
# every frame of the board under its camera, as the kit's pose sets it: the year's heading and each month's open
# photograph as rectangles of the picture (x and y from -1 to 1 across it), how much of the heading shows, the piece
# frames that fill the picture, and the months whose field fills it
CAMERA = """import * as THREE from 'three';
import {readFileSync} from 'node:fs';
import {planOf, liftOf, layerOf} from %(plan)s;
import * as camera from %(camera)s;
import {REACH, FIELD} from %(month)s;
const board = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const headingBox = JSON.parse(process.argv[3]);
const plan = planOf(board);
const cam = new THREE.PerspectiveCamera();
const rectOf = (pose, pts, z) => {
  const fwd = new THREE.Vector3(...pose.target).sub(new THREE.Vector3(...pose.position)).normalize();
  cam.position.set(...pose.position);
  cam.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -pose.roll));
  cam.lookAt(...pose.target);
  cam.fov = pose.fov;
  cam.aspect = plan.W / plan.H;
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld();
  const v = pts.map(([x, y]) => new THREE.Vector3(x - plan.W / 2, plan.H / 2 - y, z).project(cam));
  return [Math.min(...v.map((p) => p.x)), Math.min(...v.map((p) => p.y)), Math.max(...v.map((p) => p.x)), Math.max(...v.map((p) => p.y))];
};
const corners = ([x0, y0, x1, y1]) => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
// a month's piece frame on the wall, which its photograph covers
const frameOf = (m) => [m.T.o[0], m.T.o[1], m.T.o[0] + m.T.s * plan.W, m.T.o[1] + m.T.s * plan.H];
// the photograph as its halves draw it, on the layer T: its place in the piece frame, reaching no more than REACH past
// the frame
const printOf = (m, T) => {
  const [px, py, pw, ph] = m.place, s = T.s, [ox, oy] = T.o;
  const r = [Math.max(px, -REACH * plan.W), Math.max(py, -REACH * plan.H), Math.min(px + pw, (1 + REACH) * plan.W), Math.min(py + ph, (1 + REACH) * plan.H)];
  return [ox + s * r[0], oy + s * r[1], ox + s * r[2], oy + s * r[3]];
};
// a month's field, FIELD times its piece frame about the frame's middle
const fieldOf = (m) => {
  const [x0, y0, x1, y1] = frameOf(m), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  return [cx - FIELD * (cx - x0), cy - FIELD * (cy - y0), cx + FIELD * (cx - x0), cy + FIELD * (cy - y0)];
};
const fills = (r) => r[0] <= -1 + 1e-6 && r[1] <= -1 + 1e-6 && r[2] >= 1 - 1e-6 && r[3] >= 1 - 1e-6;
const still = Math.round(plan.closer.still * plan.pulse);
const out = [];
for (let f = 0; f < plan.frames; f++) {
  const t = Math.min(f, still) / plan.pulse;
  const shot = camera.shotAt(plan, t);
  const pose = shot.pose;
  const open = plan.months.filter((m) => t >= m.at.pull[0] && t <= m.at.slide[0] + m.at.slide[1]).map((m) => {
    const s = m.T.s, [ox, oy] = m.T.o;
    const box = [ox - s * REACH * plan.W, oy - s * REACH * plan.H, ox + s * (1 + REACH) * plan.W, oy + s * (1 + REACH) * plan.H];
    return {id: m.id, rect: rectOf(pose, corners(box), liftOf(m))};
  });
  const inside = plan.months.filter((m) => fills(rectOf(pose, corners(frameOf(m)), liftOf(m)))).map((m) => m.id);
  // the half over the line on the near layer reaches the picture's top and sides, the half under it on the far one its
  // foot and sides
  const print = plan.months.filter((m) => {
    const layer = layerOf(plan, m, t);
    const near = rectOf(pose, corners(printOf(m, layer.T)), layer.z), far = rectOf(pose, corners(printOf(m, m.T)), liftOf(m));
    return near[0] <= -1 + 1e-6 && near[2] >= 1 - 1e-6 && near[3] >= 1 - 1e-6 && far[0] <= -1 + 1e-6 && far[2] >= 1 - 1e-6 && far[1] <= -1 + 1e-6;
  }).map((m) => m.id);
  const field = plan.months.filter((m) => fills(rectOf(pose, corners(fieldOf(m)), liftOf(m) - 1))).map((m) => m.id);
  out.push({f, t, heading: rectOf(pose, corners(headingBox), 1), seen: t < plan.hook.slam[0] ? 0 : camera.headingSeen ? camera.headingSeen(plan, t) : 1, open, inside, print, field});
}
console.log(JSON.stringify(out));
"""

# each month's hold under its camera: a point of its photograph a quarter in from its left and three quarters down, on
# its far layer and on its near one, projected from just after the near layer has stood off to just before the camera
# leaves; how far each moved and how far the near one moved against the far one, in frame px
PARALLAX = """import * as THREE from 'three';
import {readFileSync} from 'node:fs';
import {planOf, layerOf, liftOf, onWall, world} from %(plan)s;
import * as camera from %(camera)s;
const plan = planOf(JSON.parse(readFileSync(process.argv[2], 'utf8')));
const cam = new THREE.PerspectiveCamera();
const seen = (t, T, z, p) => {
  const pose = camera.poseOf(plan, camera.framingAt(plan, t).framing);
  const fwd = new THREE.Vector3(...pose.target).sub(new THREE.Vector3(...pose.position)).normalize();
  cam.position.set(...pose.position);
  cam.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -pose.roll));
  cam.lookAt(...pose.target);
  cam.fov = pose.fov;
  cam.aspect = plan.W / plan.H;
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld();
  const v = world(plan, onWall(T, p), z).project(cam);
  return [v.x * plan.W / 2, -v.y * plan.H / 2];
};
const d = (a, b) => [b[0] - a[0], b[1] - a[1]];
console.log(JSON.stringify(plan.months.map((m) => {
  const p = [m.place[0] + 0.25 * m.place[2], m.place[1] + 0.75 * m.place[3]];
  const t0 = m.at.open[0] + 0.7, t1 = m.at.pull[0] - 0.6;
  const n0 = layerOf(plan, m, t0), n1 = layerOf(plan, m, t1);
  const far = d(seen(t0, m.T, liftOf(m), p), seen(t1, m.T, liftOf(m), p));
  const near = d(seen(t0, n0.T, n0.z, p), seen(t1, n1.T, n1.z, p));
  return {id: m.id, move: m.move, far, near, rel: d(far, near)};
})));
"""

# from each month the camera leaves for the next: its framing's height as it holds, the most it draws back to before
# the next month's photograph opens, the least on its push into the next month, and the next month's mark
DRAWBACK = """import {readFileSync} from 'node:fs';
import {planOf} from %(plan)s;
import * as camera from %(camera)s;
import {openingOf} from %(month)s;
const plan = planOf(JSON.parse(readFileSync(process.argv[2], 'utf8')));
const h = (t) => camera.framingAt(plan, t).framing.h;
const range = (t0, t1) => Array.from({length: 61}, (_, k) => h(t0 + ((t1 - t0) * k) / 60));
console.log(JSON.stringify(plan.months.slice(0, -1).map((m, i) => {
  const next = plan.months[i + 1];
  const mark = camera.stationOf(plan, next).h;
  if (camera.jumpsInto(plan, i + 1)) {
    const a = next.start - camera.ANTICIPATE;
    return {id: m.id, jump: true, held: h(a - 0.01), back: h(next.start - 0.01), push: h(next.start + 0.01), mark,
            landed: h(next.start + camera.SETTLE + 0.01)};
  }
  const [o0] = openingOf(plan, i + 1);
  return {id: m.id, jump: false, held: h(m.at.pull[0] - 0.01), back: Math.max(...range(m.at.pull[0], o0)),
          push: Math.min(...range(o0, next.at.arrive)), mark, landed: h(next.at.arrive + 0.01)};
})));
"""

# each month's photograph in the hook's window near the end of its flash: the wall y its focus lands on, the window's
# top, and the lowest wall y the camera shows then
HOOKFOCUS = """import {readFileSync} from 'node:fs';
import {planOf} from %(plan)s;
import {framingAt} from %(camera)s;
import {hookUv} from %(hook)s;
const plan = planOf(JSON.parse(readFileSync(process.argv[2], 'utf8')));
const [, y0, , y1] = plan.hook.window;
const fl = plan.hook.flash;
console.log(JSON.stringify(plan.months.map((m, k) => {
  const i = plan.hook.order.indexOf(k);
  const t = fl[i] + 0.9 * (fl[i + 1] - fl[i]);
  const {uv: [a, b], foot} = hookUv(plan, m, t, 0.9);
  const f = framingAt(plan, t).framing;
  // texture v runs up the photograph: its top is 1 - a[1], its foot 1 - b[1]
  return {id: m.id, t, focus: y0 + ((m.focus[1] - (1 - a[1])) / (a[1] - b[1])) * (foot - y0), top: y0,
          seen: Math.min(y1, f.c[1] + f.h / 2), foot};
})));
"""

# each month's words (boxes of the piece frame, given per month) on its near layer through the camera, frame by frame
# from the moment they stand whole to the camera leaving the month: the least and most x and y they reach, frame px
HOLDWORDS = """import * as THREE from 'three';
import {readFileSync} from 'node:fs';
import {planOf, layerOf, onWall, world} from %(plan)s;
import * as camera from %(camera)s;
const plan = planOf(JSON.parse(readFileSync(process.argv[2], 'utf8')));
const boxes = JSON.parse(process.argv[3]);
const whole = JSON.parse(process.argv[4]);
const cam = new THREE.PerspectiveCamera();
console.log(JSON.stringify(plan.months.map((m) => {
  let r = [Infinity, Infinity, -Infinity, -Infinity];
  for (let t = whole[m.id]; t < m.at.pull[0]; t += 1 / plan.pulse) {
    const pose = camera.poseOf(plan, camera.framingAt(plan, t).framing);
    const fwd = new THREE.Vector3(...pose.target).sub(new THREE.Vector3(...pose.position)).normalize();
    cam.position.set(...pose.position);
    cam.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -pose.roll));
    cam.lookAt(...pose.target);
    cam.fov = pose.fov;
    cam.aspect = plan.W / plan.H;
    cam.updateProjectionMatrix();
    cam.updateMatrixWorld();
    const layer = layerOf(plan, m, t);
    for (const [x0, y0, x1, y1] of boxes[m.id]) {
      for (const p of [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]) {
        const v = world(plan, onWall(layer.T, p), layer.z).project(cam);
        const px = [(v.x + 1) * plan.W / 2, (1 - v.y) * plan.H / 2];
        r = [Math.min(r[0], px[0]), Math.min(r[1], px[1]), Math.max(r[2], px[0]), Math.max(r[3], px[1])];
      }
    }
  }
  return {id: m.id, reach: r};
})));
"""

# the reel's type area [x0, y0, x1, y1], and the farthest a month's nearest word stands off its line, px
AREA = [72, 270, 930, 1250]


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


# the least contrast type holds over the worst tenth of the photograph under it, and the smallest a row's month and the
# sign-off are set (design/standards.md)
CONTRAST, LABEL_LEAST, SIGNOFF_LEAST = 4.5, 48, 72


def luminance(rgb):
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in rgb)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def held(path, place, boxes, color, plate, grade, dim=1.0):
    """The contrast type in `color` holds over the worst tenth of the photograph's pixels under its boxes, laid at
    `place` (px of the frame) and drawn at `dim` of its light, with the plate ({color, alpha}, or None) blended over
    them in linear light in its own color, channel by channel, counted here pixel by pixel, both as the film's `grade`
    leaves them (each pixel taken as a gray of its luminance)."""
    im = Image.open(path).convert("RGB")
    px = im.load()
    x, y, a, b = place
    lin = lambda h: [luminance([int(h[i:i + 2], 16)] * 3) for i in (1, 3, 5)]
    ink = yr.graded(lin(color), grade)
    over, alpha = (lin(plate["color"]), plate["alpha"]) if plate else ([0.0] * 3, 0.0)
    out = []
    for bx in boxes:
        i0, i1 = (max(0, min(im.width, int((v - x) / a * im.width))) for v in (bx[0], bx[2]))
        j0, j1 = (max(0, min(im.height, int((v - y) / b * im.height))) for v in (bx[1], bx[3]))
        for i in range(i0, i1, 2):
            for j in range(j0, j1, 2):
                v = dim * luminance(px[i, j])
                under = yr.graded([alpha * o + (1 - alpha) * v for o in over], grade)
                out.append((max(ink, under) + 0.05) / (min(ink, under) + 0.05))
    out.sort()
    return out[len(out) // 10]


def run(ws, *args):
    return subprocess.run([sys.executable, *args], cwd=ws, capture_output=True, text=True, env=ENV)


class Year(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        root = Path(cls.tmp.name)
        # a copy of the fixture's make_export.py with this year's photographs beside it, where it reads them
        fixture = root / "fixture"
        photos = fixture / "photos"
        photos.mkdir(parents=True)
        shutil.copyfile(KIT / "evals/fixtures/make_export.py", fixture / "make_export.py")
        months = []
        for m, posts, light in YEAR:
            photo(photos / f"p{m:02d}.jpg", light, m)
            months.append({"month": m, "photo": f"p{m:02d}.jpg", "posts": posts, "likes": 200 + 10 * m,
                           "caption": f"the horizon in month {m}. porto @friend.m{m}", "more": ["the sky", "the ground"]})
        book = root / "book.json"
        book.write_text(json.dumps({"handle": "test.year", "name": "Test Year", "year": 2026, "exported": "2026-12-30", "months": months}))
        cls.ws = root / "ws"
        cls.ws.mkdir()
        S = KIT / "scripts"
        steps = [[str(fixture / "make_export.py"), str(book), str(cls.ws)],
                 [str(S / "gather.py"), "--door", "instagram_account=closed: none in the test", "--door", "browser=closed: none in the test"],
                 [str(S / "research.py")]]
        for s in steps:
            r = run(cls.ws, *s)
            assert r.returncode == 0, (s, r.stdout[-800:], r.stderr[-800:])
        b = cls.ws / "build"
        (b / "taste.md").write_text((b / "taste.draft.md").read_text())
        cls.research = json.loads((b / "research.json").read_text())
        # the moments curated: September the story's peak, March in words of their own
        taste = json.loads((b / "taste.json").read_text())
        cls.drafted = [dict(mo) for mo in taste["moments"]]
        for mo in taste["moments"]:
            mo["peak"] = mo.get("month") == "September"
            if mo.get("month") == "March":
                mo["line"] = "we climbed it twice"
        (b / "taste.json").write_text(json.dumps(taste))
        cls.unread = run(cls.ws, str(S / "storyboard.py"), "draft")
        picks = b / "picks.json"
        p = json.loads(picks.read_text())
        for m in p["months"]:
            m["scene"] = "a horizon with a sun over the ground"
            m["line"] = [0, 0.6, 1, 0.6]
        p["months"][9]["line"] = [0, 0.35, 1, 0.65]  # a steep line, which turns its words out past the safe area unless they slide along it
        p["months"][0]["line"] = [0, 0.61, 1, 0.61]  # the lowest line fits takes for this photograph laid on its focus
        # picks.json lists the months out of calendar order
        cls.files = {m["month"]: m["file"] for m in p["months"]}
        p["months"] = [p["months"][k] for k in (8, 2, 11, 0, 5, 9, 3, 7, 1, 10, 6, 4)]
        picks.write_text(json.dumps(p))
        cls.draft = run(cls.ws, str(S / "storyboard.py"), "draft")
        board = json.loads((b / f"storyboards/{LOOK}/board-reel.json").read_text()) if cls.draft.returncode == 0 else {}
        cls.year, cls.bpm = board.get("year"), board.get("bpm")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_snap_cuts_only_a_board_that_won_the_vote(self):
        r = run(self.ws, str(KIT / "scripts/storyboard.py"), "snap")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vote.py ballot", r.stderr)
        self.assertNotEqual(run(self.ws, str(KIT / "scripts/storyboard.py"), "snap", "--board", LOOK).returncode, 0)
        self.assertFalse((self.ws / "build/film.json").exists())

    def test_a_new_draft_starts_a_new_vote(self):
        b = self.ws / "build"
        (b / "vote").mkdir(exist_ok=True)
        (b / "winner.json").write_text(json.dumps({"board": LOOK, "swap_passed": True}))
        (b / "vote/scores.json").write_text("{}")
        r = run(self.ws, str(KIT / "scripts/storyboard.py"), "draft")
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        self.assertFalse((b / "winner.json").exists())
        self.assertFalse((b / "vote/scores.json").exists())

    def test_a_month_whose_photograph_is_unread_is_refused(self):
        self.assertNotEqual(self.unread.returncode, 0)
        self.assertIn("no scene for", self.unread.stderr + self.unread.stdout)

    def test_the_draft_has_no_findings(self):
        self.assertEqual(self.draft.returncode, 0, self.draft.stderr[-800:])
        self.assertIn("0 findings", self.draft.stdout)

    def test_every_months_words_take_the_cards_color_on_a_plate_that_holds_their_contrast(self):
        spec = style.card(LOOK)["photo"]["line"]
        for m in self.year["months"]:
            self.assertEqual({w["color"] for w in m["said"]}, {spec["color"]}, m["id"])
            self.assertTrue(all(t["contrast"] >= CONTRAST for t in [m["name"], *m["said"]]), m["id"])
            self.assertIn(m["plate"]["color"], ("bg", "ink", "paper"), m["id"])
            self.assertGreaterEqual(m["plate"]["alpha"], spec["scrim"], m["id"])

    def test_their_whole_line_stands_within_a_second_of_the_month_and_holds_a_second_before_the_pull(self):
        # the last word stands whole LAND beats after its beat: words.tsx rises it from 0.05 before, over 0.2
        beat = 60 / self.bpm
        for m in self.year["months"]:
            whole = sum(m["at"]["say"]) + yr.LAND
            self.assertLessEqual((whole - m["start"]) * beat, 1.0, m["id"])
            self.assertGreaterEqual((m["at"]["pull"][0] - whole) * beat, 1.0, m["id"])

    def test_research_drafts_each_months_moment_from_its_post_never_from_counts(self):
        moments = self.research["moments"]
        self.assertEqual([mo["month"] for mo in moments], [calendar.month_name[m] for m, _, _ in YEAR])
        for mo, (m, _, _) in zip(moments, YEAR):
            self.assertEqual(set(mo), {"month", "date", "photo", "line", "people", "place"})
            self.assertEqual((mo["line"], mo["people"], mo["place"]), (f"the horizon in month {m}.", [f"friend.m{m}"], "porto"))
            self.assertTrue(mo["date"].startswith(f"2026-{m:02d}-"))
        self.assertEqual(self.drafted, moments)

    def test_the_months_run_two_quick_and_one_held_and_the_peak_holds_longest(self):
        ms = self.year["months"]
        self.assertEqual([m["id"] for m in ms if m["peak"]], ["m09"])
        self.assertEqual([m["beats"] for m in ms], [yr.month_beats(i, m["peak"]) for i, m in enumerate(ms)])
        rest = [m["beats"] for m in ms if not m["peak"]]
        self.assertGreater(next(m["beats"] for m in ms if m["peak"]), max(rest))
        for a, b, c in zip(ms, ms[1:], ms[2:]):
            self.assertFalse(a["beats"] == b["beats"] == c["beats"], (a["id"], b["id"], c["id"]))

    def test_the_hooks_window_opens_on_the_looks_lead_and_flashes_every_month_once(self):
        h = self.year["hook"]
        self.assertEqual(sorted(h["order"]), list(range(len(self.year["months"]))))
        self.assertEqual(h["order"][0], yr.leads(self.year["months"], h["window"])[0])
        self.assertNotEqual(h["order"][0], 0)

    def test_each_look_leads_with_its_own_photograph_and_a_read_focus_first(self):
        window = [64, 455, 1016, 2147]
        months = [{"size": [720, 1080], "focus": [0.5, 0.5]} for _ in range(6)]
        months[4] = {"size": [720, 1080], "focus": [0.5, 0.3], "read": True}
        months[2] = {"size": [1080, 720], "focus": [0.9, 0.5]}
        got = yr.leads(months, window)
        self.assertEqual(got[0], 4)
        self.assertEqual(got[-1], 0)
        self.assertEqual(got.index(2), len(got) - 2)
        self.assertEqual(len(set(got[:3])), 3)

    def test_a_boxed_photographs_line_never_crosses_its_subject(self):
        pic, subject = [60, 660, 1020, 1560], [426, 822, 750, 1398]
        crossing = yr.boxed_line([922.8, 1037.1], pic, subject)
        self.assertEqual(crossing[0], crossing[1])
        self.assertTrue(crossing[0] <= subject[1] - yr.LINE_CLEAR or crossing[0] >= subject[3] + yr.LINE_CLEAR, crossing)
        self.assertTrue(pic[1] < crossing[0] < pic[3])
        self.assertEqual(crossing[0], subject[1] - yr.LINE_CLEAR)
        low = yr.boxed_line([1250.0, 1350.0], pic, subject)
        self.assertEqual(low, [subject[3] + yr.LINE_CLEAR] * 2)
        clear = yr.boxed_line([700.0, 760.0], [60, 660, 1020, 1560], [426, 1000, 750, 1500])
        self.assertEqual(clear, [792.0, 852.0])
        whole = yr.boxed_line([1100.0, 1100.0], pic, [426, 600, 750, 1600])
        self.assertEqual(whole, [round(pic[3] - yr.LINE_IN[0] * 900, 1)] * 2)

    def test_the_hooks_months_flash_alike(self):
        f = self.year["hook"]["flash"]
        lengths = [b - a for a, b in zip(f, f[1:])]
        self.assertEqual(len(lengths), 12)
        self.assertLess(max(lengths) - min(lengths), 0.002)

    def test_each_month_says_its_name_and_its_own_line_and_no_count(self):
        for m in self.year["months"]:
            want = "we climbed it twice" if m["id"] == "m03" else f"the horizon in month {m['month']}."
            style.use(LOOK)
            self.assertEqual((m["name"]["text"], m["text"], " ".join(w["text"] for w in m["said"])),
                             (style.cased(m["short"], m["name"]["face"]), want, style.cased(want, m["said"][0]["face"])))
            self.assertTrue({"posts", "count", "word", "note", "busiest"}.isdisjoint(m), sorted(m))
            self.assertTrue(all(w.get("rotate") == m["name"].get("rotate") for w in m["said"]))

    def test_a_sound_lands_where_a_beat_lands_and_nowhere_else(self):
        board = json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text())
        cues = board["sound"]
        self.assertLessEqual(len(cues), len(board["beats"]) + 4)
        self.assertEqual({c["kind"] for c in cues}, {"hit", "riser", "impact", "stop"})
        peak = next(m for m in self.year["months"] if m["peak"])
        self.assertEqual([(c["kind"], c["beat"]) for c in cues if c["kind"] in ("riser", "impact")],
                         [("impact", "hook"), ("riser", peak["id"]), ("impact", peak["id"]), ("impact", "closer")])
        # every month but the peak lands on a hit, and the card's closer takes the frame on one
        self.assertEqual([c["beat"] for c in cues if c["kind"] == "hit"], [m["id"] for m in self.year["months"] if not m["peak"]] + ["closer"])

    def test_the_closer_is_the_years_rows_alike_with_no_count_and_no_total(self):
        rows = self.year["rows"]
        self.assertEqual(len({(r["x0"], r["x1"]) for r in rows}), 1)
        self.assertEqual(rows[0]["x1"], 1080 - 150)
        self.assertTrue(all({"count", "tab"}.isdisjoint(r) for r in rows))
        self.assertTrue({"total", "total_line", "total_word", "top"}.isdisjoint(self.year), sorted(self.year))
        self.assertTrue({"big", "word", "ink", "box"}.isdisjoint(self.year["hook"]), sorted(self.year["hook"]))
        md = (self.ws / f"build/storyboards/{LOOK}/storyboard.md").read_text()
        self.assertNotIn("posts", md)
        self.assertIn("| beat | starts | seconds | form | move | cut | the moment | on screen |", md)

    def test_each_photograph_is_named_by_its_scene_never_by_its_posts_caption(self):
        self.assertTrue(all(m["scene"] == "a horizon with a sun over the ground" and "caption" not in m for m in self.year["months"]))

    def taste_palette(self):
        return json.loads((self.ws / "build/taste.json").read_text())["palette"]["year"]

    def test_one_grade_for_the_whole_film_the_cards_turned_by_their_palette(self):
        card = style.card(LOOK)["finish"]["grade"]
        self.assertEqual(yr.grade([], card), {k: card[k] for k in ("lift", "gamma", "gain", "saturation")})
        g = yr.grade([{"hex": "#1c2640", "share": 0.5}, {"hex": "#f4e6c8", "share": 0.3}, {"hex": "#c03020", "share": 0.2}], card)
        lift = [g["lift"][i] - card["lift"][i] for i in range(3)]
        gain = [g["gain"][i] / card["gain"][i] for i in range(3)]
        self.assertGreater(lift[2], lift[0], "their darkest is blue, so the shadows lift toward blue")
        self.assertGreater(gain[0], gain[2], "their lightest is cream, so the highlights go warm")
        self.assertTrue(0 < max(lift) <= 0.08 and min(gain) >= 0.5 and max(gain) <= 1, g)
        self.assertNotEqual(yr.grade(self.taste_palette(), card), yr.grade([], card), "the palette reaches the grade")
        self.assertEqual(self.year["grade"], yr.grade(self.taste_palette(), card, self.year["colors"]))

    def test_the_peak_holds_ten_beats_the_others_five_or_seven_and_the_hook_five(self):
        ms = self.year["months"]
        self.assertEqual(ms[0]["start"], 5.0)
        self.assertEqual({m["beats"] for m in ms if not m["peak"]}, {5.0, 7.0})
        self.assertEqual([m["beats"] for m in ms if m["peak"]], [10.0])

    def test_each_months_move_is_the_cards_picked_for_what_it_shows_and_never_twice_running(self):
        card = style.card(LOOK)
        ms = self.year["months"]
        self.assertTrue({m["move"] for m in ms} <= {mv["id"] for mv in card["moves"]}, {m["move"] for m in ms})
        self.assertTrue({m["transition"] for m in ms} <= {t["id"] for t in card["transitions"]}, {m["transition"] for m in ms})
        for a, b in zip(ms, ms[1:]):
            self.assertNotEqual(a["move"], b["move"], (a["id"], b["id"]))
        # the peak takes the move the card fits to a peak
        self.assertIn(next(m for m in ms if m["peak"])["move"], [mv["id"] for mv in card["moves"] if "peak" in mv["fits"]])

    def test_their_line_is_set_in_the_cards_line_face_under_its_label_inside_the_type_area(self):
        photo = style.card(LOOK)["photo"]
        for m in self.year["months"]:
            self.assertEqual((m["name"]["face"], m["name"]["size"] <= photo["label"]["size"]), (photo["label"]["face"], True), m["id"])
            self.assertTrue(all(w["face"] == photo["line"]["face"] and w["size"] <= photo["line"]["size"] for w in m["said"]), m["id"])
            name = style.box_of(m["name"])
            self.assertTrue(all(name[3] < style.box_of(w)[1] for w in m["said"]), f"{m['id']}'s name stands under its line")
            x0, y0, x1, y1 = m["box"]
            self.assertTrue(AREA[0] - 1 <= x0 and x1 <= AREA[2] + 1 and AREA[1] - 1 <= y0 and y1 <= AREA[3] + 1, (m["id"], m["box"]))

    def test_each_cards_photograph_stands_in_its_own_box(self):
        got = {c: yr.picture_box(style.card(c)["photo"]) for c in style.TRIO}
        analog, kinetic, swiss = (got[c] for c in style.TRIO)
        self.assertTrue(analog[0] < 0 and analog[2] > yr.W, analog)
        self.assertTrue(kinetic[0] < 0 and kinetic[2] > yr.W, kinetic)
        bx = style.card(style.TRIO[2])["photo"]["picture"]["box"]
        self.assertEqual([round(v) for v in swiss], [round(bx[0] * yr.W), round(bx[1] * yr.H), round((bx[0] + bx[2]) * yr.W), round((bx[1] + bx[3]) * yr.H)])
        self.assertEqual(style.system(style.card(LOOK), {}, {})["photo"], style.card(LOOK)["photo"])

    def test_a_landscape_photograph_takes_the_cards_landscape_box_and_its_line_stays_in_the_line_box(self):
        import storyboard
        swiss = style.TRIO[2]
        photo_ = style.card(swiss)["photo"]
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            b = Path(tmp) / "build"
            shutil.copytree(self.ws / "build", b, ignore=shutil.ignore_patterns("render", "storyboards"))
            picks = json.loads((b / "picks.json").read_text())
            wide = next(m for m in picks["months"] if m["month"] == 4)
            Image.open(b / "public" / wide["file"]).resize((1800, 1200)).save(b / "public" / "wide.jpg", quality=90)
            wide["file"], wide["size"] = "wide.jpg", [1800, 1200]
            (b / "picks.json").write_text(json.dumps(picks))
            here = os.getcwd()
            os.chdir(b)
            try:
                p = storyboard.board_for(swiss, storyboard.Run())
            finally:
                os.chdir(here)
        m = next(m for m in p["board"]["year"]["months"] if m["month"] == 4)
        bx = photo_["landscape"]["box"]
        self.assertEqual([round(v) for v in m["picture"]], [round(bx[0] * yr.W), round(bx[1] * yr.H), round((bx[0] + bx[2]) * yr.W), round((bx[1] + bx[3]) * yr.H)])
        cell = yr.area_box(photo_["landscape"]["line"])
        for ln in [m["name"], *m["said"]]:
            x0, y0, x1, y1 = style.box_of(ln)
            self.assertTrue(cell[0] - 0.5 <= x0 and x1 <= cell[2] + 0.5, (ln["text"], [x0, x1], cell))
            self.assertGreaterEqual(ln["size"], 32, ln["text"])
        self.assertEqual([f for f in storyboard.findings(p) if f.startswith("m04") and "line box" in f], [])

    def test_a_card_that_stands_its_photographs_in_a_box_keeps_its_own_grade(self):
        # its moves cut mats and cells in the card's ground over the graded film, so the ground stays the card's
        import storyboard
        boxed = style.TRIO[2]
        here = os.getcwd()
        os.chdir(self.ws / "build")
        try:
            p = storyboard.board_for(boxed, storyboard.Run())
        finally:
            os.chdir(here)
        card = style.card(boxed)["finish"]["grade"]
        self.assertNotEqual(yr.grade(self.taste_palette(), card), yr.grade([], card), "the palette would turn this card's grade")
        self.assertEqual(p["board"]["year"]["grade"], yr.grade([], card))

    def test_a_full_frame_cards_words_stand_clear_of_their_moves_bands_on_a_scrim_from_the_nearer_edge(self):
        import storyboard
        kinetic = style.TRIO[1]
        here = os.getcwd()
        os.chdir(self.ws / "build")
        try:
            p = storyboard.board_for(kinetic, storyboard.Run())
        finally:
            os.chdir(here)
        months = p["board"]["year"]["months"]
        self.assertTrue(any(m["move"] in yr.MOVE_BANDS for m in months), [m["move"] for m in months])
        for m in months:
            b = m["box"]
            for top, tall in yr.MOVE_BANDS.get(m["move"], []):
                self.assertTrue(b[3] <= top * yr.H or b[1] >= (top + tall) * yr.H, (m["id"], m["move"], b))
            plate = m["plate"]["box"]
            # the scrim runs past the frame's sides and stops short of the frame's far edge, so the photograph shows there
            self.assertTrue(plate[0] < 0 and plate[2] > yr.W, (m["id"], plate))
            self.assertTrue(plate[1] < 0 or plate[3] > yr.H, (m["id"], plate))
            self.assertFalse(plate[1] < 0 and plate[3] > yr.H, (m["id"], plate))

    def test_a_boxed_cards_words_stand_clear_of_the_rule_its_move_draws_over_the_picture(self):
        import storyboard
        swiss = style.TRIO[2]
        here = os.getcwd()
        os.chdir(self.ws / "build")
        try:
            p = storyboard.board_for(swiss, storyboard.Run())
        finally:
            os.chdir(here)
        ruled = [m for m in p["board"]["year"]["months"] if m["move"] in yr.PICTURE_BANDS and m["picture"]]
        self.assertTrue(ruled, [m["move"] for m in p["board"]["year"]["months"]])
        for m in ruled:
            for top, foot in yr.PICTURE_BANDS[m["move"]](m["picture"]):
                self.assertTrue(m["box"][3] <= top or m["box"][1] >= foot, (m["id"], m["move"], m["box"], m["picture"]))

    def test_each_clip_request_is_one_shot_the_length_of_its_beat(self):
        # the hook's world, each month's still brought to life, and the closer's texture, each one prompt of its own
        clips = json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text())["clips"]
        ms = self.year["months"]
        self.assertEqual([c["beat"] for c in clips], ["hook", *[m["id"] for m in ms], "closer"])
        self.assertAlmostEqual(clips[0]["seconds"], ms[0]["start"] * 60 / self.bpm, delta=0.06)
        for c, m in zip(clips[1:], ms):
            self.assertAlmostEqual(c["seconds"], m["beats"] * 60 / self.bpm, delta=0.06)
            self.assertIn("two layers", c["stand_in"])
        for c in clips:
            for part in ("Camera:", "Lens:", "Light:", f"{c['seconds']} seconds", "seamless loop"):
                self.assertIn(part, c["prompt"], c["id"])
            self.assertNotIn("exactly as in the image", c["prompt"], c["id"])
            self.assertNotIn("the horizon in month", c["prompt"], c["id"])
        for c, m in zip(clips[1:], ms):
            self.assertTrue(c["prompt"].startswith(m["scene"]), c["id"])

    def test_the_hook_card_is_the_year_over_its_open_window(self):
        h = self.year["hook"]
        rests = json.loads((self.ws / f"build/storyboards/{LOOK}/plan.json").read_text())["reel"]["rests"]
        self.assertEqual(rests["hook"], round(h["rest"] * 30 * 60 / self.bpm))
        self.assertTrue(h["flash"][0] + 0.2 <= h["rest"] < h["dive"][0], h)
        self.assertEqual(self.frames()[rests["hook"]]["seen"], 1)

    def test_the_wall_lies_on_the_first_months_photograph(self):
        self.assertEqual(self.year["ground"]["month"], "m01")

    def test_the_months_lie_in_calendar_order_whatever_order_picks_lists_them(self):
        months = self.year["months"]
        self.assertEqual([m["id"] for m in months], [f"m{k:02d}" for k in range(1, 13)])
        self.assertEqual([m["file"] for m in months], [self.files[k] for k in range(1, 13)])
        starts = [m["start"] for m in months]
        self.assertEqual(starts, sorted(starts))

    def test_each_months_own_photograph_fills_the_picture_in_calendar_order(self):
        # from the camera's arrival on the first month to its pull back from the last, the picture lies inside the
        # photograph of the month it holds on while it holds (its halves, which run up to REACH past the piece frame
        # as the photograph allows), and at the hold's middle inside its piece frame; as it draws back off a month and pushes into the next,
        # the print comes whole into the picture on a field, the month's own or the next one's opening over it; no
        # frame is the wall
        months = self.year["months"]
        span = [fr for fr in self.frames() if months[0]["at"]["arrive"] <= fr["t"] <= months[-1]["at"]["pull"][0]]
        self.assertTrue(span)
        out = []
        for fr in span:
            i = max(k for k, m in enumerate(months) if m["start"] <= fr["t"])
            m = months[i]
            if m["at"]["arrive"] <= fr["t"] < m["at"]["pull"][0]:
                if m["id"] not in fr["print"]:
                    out.append((fr["f"], m["id"], "held", fr["print"]))
            else:
                near = {months[k]["id"] for k in (i - 1, i, i + 1) if 0 <= k < len(months)}
                if not near & set(fr["field"]):
                    out.append((fr["f"], m["id"], "between", fr["field"]))
        self.assertEqual(out, [], "frames where the picture is not the month's own photograph or a month's field")
        for m in months:
            mid = (m["at"]["arrive"] + m["at"]["pull"][0]) / 2
            fr = min(self.frames(), key=lambda fr: abs(fr["t"] - mid))
            self.assertIn(m["id"], fr["inside"], m["id"])
        for m, n in zip(months, months[1:]):
            self.assertLess(m["at"]["pull"][0], n["start"], f"{n['id']} does not open over {m['id']} before it starts")
            # month.tsx opens the next month's field twice as fast as its print, so it covers the month from halfway
            # through the print's opening, and the month closes under it
            self.assertGreaterEqual(m["at"]["fold"][0], n["at"]["card"][0] + n["at"]["card"][1] / 2, f"{m['id']} closes before {n['id']}'s field covers it")

    def heading(self):
        """The year's heading at rest on the wall."""
        import storyboard
        return style.box_of(self.year["title"])

    def bundle(self, script, board, *args):
        """`script` bundled with the kit's own esbuild against motion/studio/year and run over a board: its output."""
        esbuild = MOTION / "node_modules/.bin/esbuild"
        if not esbuild.exists():
            self.skipTest("motion/node_modules is not installed")
        y = MOTION / "studio/year"
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            entry, bundle, path = Path(tmp) / "entry.mjs", Path(tmp) / "bundle.mjs", Path(tmp) / "board.json"
            entry.write_text(script % {k: json.dumps(str(y / f)) for k, f in (("plan", "plan.ts"), ("camera", "camera.ts"), ("month", "month.tsx"), ("hook", "hook.tsx"),
                                                                               ("motion", "../../system/three/motion.ts"),
                                                                               ("stage", "../../system/three/Stage.tsx"))})
            path.write_text(json.dumps(board))
            r = subprocess.run([str(esbuild), str(entry), "--bundle", "--platform=node", "--format=esm", "--log-level=error",
                                f"--outfile={bundle}"], cwd=MOTION, capture_output=True, text=True,
                               env=dict(ENV, NODE_PATH=str(MOTION / "node_modules")))
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
            r = subprocess.run(["node", str(bundle), str(path), *args], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr[-800:])
        return json.loads(r.stdout)

    def camera(self, board, heading):
        """A board's frames under its camera, from CAMERA run over it."""
        return self.bundle(CAMERA, board, json.dumps(heading))

    def frames(self):
        """The drafted board's frames under its camera."""
        if getattr(type(self), "_frames", None) is None:
            type(self)._frames = self.camera(json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text()), self.heading())
        return type(self)._frames

    def test_the_years_heading_is_never_under_an_open_photograph_while_it_shows(self):
        hidden = [(fr["f"], m["id"]) for fr in self.frames() for m in fr["open"] if fr["seen"] > 0 and overlap(fr["heading"], m["rect"])]
        self.assertEqual(hidden, [], "frames where an open month's photograph covers the year's heading")

    def test_the_years_heading_shows_only_while_it_is_wholly_in_the_picture(self):
        cut = [fr["f"] for fr in self.frames() if fr["seen"] > 0 and not (-1 <= fr["heading"][0] and -1 <= fr["heading"][1]
                                                                           and fr["heading"][2] <= 1 and fr["heading"][3] <= 1)]
        self.assertEqual(cut, [], "frames where the picture's edge cuts the year's heading while it shows")

    def test_the_heading_is_drawn_whole_or_not_at_all(self):
        part = [fr["f"] for fr in self.frames() if 0 < fr["seen"] < 1]
        self.assertEqual(part, [], "frames where the year's heading shows through, neither whole nor gone")

    def test_the_year_shows_as_it_slams_in_when_its_heading_runs_wide(self):
        # a heading reaching x 900, inside the type area: the hook frames all of it
        board = json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text())
        board["year"]["heading"][2] = 900
        s0, s1 = board["year"]["hook"]["slam"]
        slam = [fr for fr in self.camera(board, board["year"]["heading"]) if s0 <= fr["t"] <= s0 + s1]
        self.assertTrue(slam)
        self.assertEqual([fr["f"] for fr in slam if fr["seen"] < 1], [], "frames of the slam where the year does not show")

    def test_every_hold_moves_its_near_layer_against_its_far_one(self):
        # a point of the month's photograph on its near layer (the foreground under the line, and the words) and the same
        # point on its far layer (the sky over it), projected through the camera across the month's hold: the near one
        # moves against the far one by more than a few px, and the way it moves turns from one month to the next
        got = self.bundle(PARALLAX, json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text()))
        import math
        for g in got:
            self.assertGreater(math.hypot(*g["rel"]), 12, g)
        for a, b in zip(got, got[1:]):
            cos = (a["rel"][0] * b["rel"][0] + a["rel"][1] * b["rel"][1]) / (math.hypot(*a["rel"]) * math.hypot(*b["rel"]))
            self.assertLess(cos, 0.87, (a, b))

    def test_the_camera_gathers_before_each_cut_and_settles_on_the_next_months_mark(self):
        # the anticipation: the camera gathers itself before the cut, drawing back off the month (the whole print onto
        # its field where the cut dissolves, a little where it jumps); the overshoot: the next month comes in tighter
        # than its mark and settles on it
        got = self.bundle(DRAWBACK, json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text()))
        self.assertEqual(len(got), 11)
        for g in got:
            self.assertGreater(g["back"], (1.02 if g["jump"] else 1.3) * g["held"], g)
            self.assertLess(g["push"], (0.97 if g["jump"] else 0.995) * g["mark"], g)
            self.assertAlmostEqual(g["landed"] / g["mark"], 1, delta=0.03 if g["jump"] else 0.1, msg=g)

    def test_each_photograph_in_the_hooks_window_shows_its_subject_in_the_part_of_the_window_the_picture_shows(self):
        # the hook's picture holds the year over its window and shows the window's top part, then dives in: each month's
        # photograph flashing through it covers the part of the window the camera shows and has its focus in that part's
        # middle half, never a corner of the photograph's sky
        got = self.bundle(HOOKFOCUS, json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text()))
        self.assertEqual(len(got), 12)
        for g in got:
            part = g["seen"] - g["top"]
            self.assertGreater(part, 200, g)
            self.assertGreaterEqual(g["foot"], g["seen"], g)
            self.assertGreaterEqual(g["focus"], g["top"] + 0.25 * part, g)
            self.assertLessEqual(g["focus"], g["top"] + 0.75 * part, g)

    def test_a_months_words_stay_inside_the_type_area_through_its_hold(self):
        # from the moment the line stands whole to the camera leaving the month, the name and their line, moved by the
        # month's own camera on the near layer, never leave the reel's type area
        import storyboard
        whole = {m["id"]: sum(m["at"]["say"]) + yr.LAND for m in self.year["months"]}
        boxes = {m["id"]: [style.box_of(ln) for ln in [m["name"], *m["said"]]] for m in self.year["months"]}
        got = self.bundle(HOLDWORDS, json.loads((self.ws / f"build/storyboards/{LOOK}/board-reel.json").read_text()),
                          json.dumps(boxes), json.dumps(whole))
        out = [g for g in got if not (AREA[0] - 1 <= g["reach"][0] and g["reach"][2] <= AREA[2] + 1 and AREA[1] - 1 <= g["reach"][1] and g["reach"][3] <= AREA[3] + 1)]
        self.assertEqual(out, [], "months whose words leave the type area during their hold")

    def test_a_bright_band_sits_in_the_years_rows_like_the_rest(self):
        # a white slit is dimmed to the light the year's rows carry, never under BAND_LEAST of its own; a dark one keeps
        # all of its light
        import shutil
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "public").mkdir()
        Image.new("RGB", (1080, 1920), (250, 250, 250)).save(root / "public/white.png")
        Image.new("RGB", (1080, 1920), (40, 40, 40)).save(root / "public/dark.png")
        Image.new("RGB", (1080, 1920), (190, 190, 190)).save(root / "public/light.png")
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(root)
        place, ln, band = [0, 0, 1080, 1920], [960, 960], [100, 0, 1000, 60]
        white = yr.band_gain("white.png", place, ln, band)
        self.assertEqual(white, yr.BAND_LEAST)
        self.assertEqual(yr.band_gain("dark.png", place, ln, band), 1.0)
        light = yr.band_gain("light.png", place, ln, band)
        self.assertTrue(yr.BAND_LEAST < light < 1.0, light)
        self.assertAlmostEqual(light * yr.light_mean("light.png", place, [0, 930, 1080, 990]), yr.BAND_LIGHT, delta=0.01)
        for m in self.year["months"]:
            self.assertTrue(yr.BAND_LEAST <= m["gain"] <= 1.0, m["id"])

    def test_the_effects_sit_at_least_eight_lu_under_the_music(self):
        # the mix aims past the gate's floor, so a measured mix lands on it or over it
        self.assertEqual(music.FX_LEAST_LU, 8)
        self.assertGreater(music.FX_UNDER_BED_LU, music.FX_LEAST_LU)

    def board(self):
        d = self.ws / f"build/storyboards/{LOOK}"
        return dict(json.loads((d / "plan.json").read_text())["reel"], board=json.loads((d / "board-reel.json").read_text()))

    def test_a_months_words_past_the_cards_line_box_are_a_finding(self):
        import storyboard
        p = self.board()
        m = p["board"]["year"]["months"][3]
        m["said"][-1]["x"] += 900
        found = [f for f in storyboard.findings(p) if f.startswith("m04")]
        self.assertTrue(any("runs past the card's line box" in f for f in found), found)

    def test_picks_finds_a_line_the_photograph_shows(self):
        import picks
        im = Image.new("RGB", (1200, 1500), (200, 200, 205))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 1200, 300], fill=(20, 20, 30))      # a hard edge high in the photograph, at v 0.2
        d.rectangle([0, 750, 1200, 1500], fill=(150, 150, 150))  # a softer one in the middle, at v 0.5
        self.assertAlmostEqual(picks.line_of(im)[1], 0.2, delta=0.03)
        ln = picks.line_of(im, lambda ln: yr.shown(im.size, [0.5, 0.5], ln))
        self.assertTrue(yr.shown(im.size, [0.5, 0.5], ln))

    def test_a_line_too_low_to_reach_leaves_the_photograph_at_its_cover_and_is_refused(self):
        # a 1200x1500 photograph, its subject in the middle, its line at v 0.85: lifting that line into the words' room
        # would take a photograph about 4467 px tall, with the subject above the picture
        import storyboard
        size, focus, ln = (1200, 1500), [0.5, 0.5], [0, 0.85, 1, 0.85]
        x, y, a, b = yr.cover(size, focus, 1080, 1920)
        self.assertAlmostEqual(b, 1920 * 1.06, delta=1)
        self.assertTrue(0 <= y + focus[1] * b <= 1920, f"the subject at y {y + focus[1] * b:.0f}")
        self.assertFalse(yr.shown(size, focus, ln))

    def february(self, size, focus, line):
        """The first look's board for the year, february's photograph a gray one of `size` with this focus and line."""
        import shutil
        import storyboard
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        b = Path(tmp.name) / "build"
        shutil.copytree(self.ws / "build", b, ignore=shutil.ignore_patterns("render", "storyboards"))
        Image.new("RGB", tuple(size), (120, 120, 125)).save(b / "public/photos/feb.jpg")
        p = json.loads((b / "picks.json").read_text())
        next(m for m in p["months"] if m["month"] == 2).update(file="photos/feb.jpg", size=list(size), focus=focus, line=line)
        (b / "picks.json").write_text(json.dumps(p))
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(b)
        return storyboard.board_for(LOOK, storyboard.Run())

    def test_a_months_words_move_off_a_subject_low_in_the_frame(self):
        # february's subject sits low in the frame, where the card's line box stands its words: they move
        # up or down the type area until they are clear of it
        p = self.february((1200, 1500), [0.5, 0.6], [0, 0.4, 1, 0.4])
        m = next(m for m in p["board"]["year"]["months"] if m["id"] == "m02")
        cell = yr.area_box(style.card(LOOK)["photo"]["line"]["box"])
        s, b = m["subject"], m["box"]
        self.assertTrue(s[1] < cell[3] and s[3] > cell[1], (s, cell))
        self.assertEqual(m["on_subject"], 0)
        self.assertTrue(b[3] <= s[1] or b[1] >= s[3], (b, s))

    def busy(self):
        """The first look's board drafted from a copy of the year, January's and September's photographs a black and white
        checkerboard, so the wall's ground is one whichever month it lies on, and the board's colors."""
        import shutil
        import storyboard
        if getattr(type(self), "_busy", None) is None:
            tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
            self.addClassCleanup(tmp.cleanup)
            b = Path(tmp.name) / "build"
            shutil.copytree(self.ws / "build", b, ignore=shutil.ignore_patterns("render", "storyboards"))
            im = Image.new("RGB", (1200, 1500), (255, 255, 255))
            d = ImageDraw.Draw(im)
            for i in range(0, 1200, 24):
                for j in range(0, 1500, 24):
                    if (i // 24 + j // 24) % 2:
                        d.rectangle([i, j, i + 23, j + 23], fill=(0, 0, 0))
            im.save(b / "public/photos/busy.png")
            p = json.loads((b / "picks.json").read_text())
            for m in p["months"]:
                if m["month"] in (1, 9):
                    m.update(file="photos/busy.png", size=[1200, 1500])
            (b / "picks.json").write_text(json.dumps(p))
            here = os.getcwd()
            os.chdir(b)
            try:
                type(self)._busy = (b, storyboard.board_for(LOOK, storyboard.Run()))
            finally:
                os.chdir(here)
        return type(self)._busy

    def test_a_months_words_hold_their_contrast_over_a_busy_photograph(self):
        import storyboard
        b, p = self.busy()
        y = p["board"]["year"]
        self.assertNotEqual(y["grade"]["lift"], [0, 0, 0], "the contrast is measured through a grade that moves the picture")
        for m in y["months"]:
            if m["file"] != "photos/busy.png":
                continue
            ln = m["name"]
            worst = held(b / "public" / m["file"], m["place"], [style.box_of(t) for t in [ln, *m["said"]]],
                         y["colors"][ln["color"]], {"color": y["colors"][m["plate"]["color"]], "alpha": m["plate"]["alpha"]},
                         y["grade"])
            self.assertGreaterEqual(worst, CONTRAST, f"{m['id']}'s words hold {worst:.2f}:1 over the checkerboard")

    def test_the_walls_type_holds_its_contrast_over_a_busy_ground(self):
        import storyboard
        b, p = self.busy()
        y = p["board"]["year"]
        ground = next(m for m in y["months"] if m["id"] == y["ground"]["month"])
        self.assertEqual(ground["file"], "photos/busy.png")
        x0, y0, x1, y1 = y["ground"]["box"]
        gx, gy, gw, gh = yr.cover(ground["size"], ground["focus"], x1 - x0, y1 - y0, 1.0)
        place = [gx + x0, gy + y0, gw, gh]
        plates = {s["of"]: s for s in y["plates"]}
        groups = {"title": [y["title"]], "handle": [y["handle"]] if y["handle"] else [], "labels": [r["label"] for r in y["rows"]],
                  "signoff": [y["signoff"]]}
        for of, lines in groups.items():
            if not lines:
                continue
            pl = plates.get(of)
            worst = held(b / "public" / ground["file"], place, [style.box_of(t) for t in lines], y["colors"][lines[0]["color"]],
                         pl and {"color": y["colors"][pl["color"]], "alpha": pl["alpha"]}, y["grade"], y["dim"])
            self.assertGreaterEqual(worst, CONTRAST, f"the wall's {of} holds {worst:.2f}:1 over the checkerboard")

    def test_a_card_that_lays_no_photograph_full_frame_lays_the_wall_flat_in_its_ground(self):
        import shutil
        import storyboard
        self.assertIsNone(self.year["ground"]["flat"], "a full-frame card lays the wall on the first month's photograph")
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            b = Path(tmp) / "build"
            shutil.copytree(self.ws / "build", b, ignore=shutil.ignore_patterns("render", "storyboards"))
            here = os.getcwd()
            os.chdir(b)
            try:
                for look in style.TRIO:
                    p = storyboard.board_for(look, storyboard.Run())
                    y, photo = p["board"]["year"], style.card(look)["photo"]
                    pb = yr.picture_box(photo)
                    if pb is not None and pb[2] - pb[0] > yr.W:
                        continue
                    self.assertEqual(y["ground"]["flat"], photo["ground"], look)
                    ground = yr._lum(y["colors"][photo["ground"]])
                    plates = {s["of"]: s for s in y["plates"]}
                    for of, ln in (("title", y["title"]), ("signoff", y["signoff"])):
                        pl = plates[of]
                        held_ = yr.holds(y["colors"][ln["color"]], y["colors"][pl["color"]], pl["alpha"],
                                         {"dark": ground, "bright": ground}, y["grade"])
                        self.assertGreaterEqual(held_, CONTRAST, f"{look}'s {of} on its flat ground")
                    self.assertNotIn("hook", [c["beat"] for c in yr.clips(y, p["board"]["bpm"])], look)
            finally:
                os.chdir(here)

    def test_the_closers_names_and_sign_off_are_never_under_their_smallest_sizes(self):
        for r in self.year["rows"]:
            self.assertGreaterEqual(r["label"]["size"], LABEL_LEAST, r["label"]["text"])
        self.assertGreaterEqual(self.year["signoff"]["size"], SIGNOFF_LEAST)
        # every row's name stands in the column left of the bands, so none lies on a band
        import storyboard
        for r in self.year["rows"]:
            self.assertLessEqual(style.box_of(r["label"])[2], r["band"][0], r["label"]["text"])

    def test_every_rows_photograph_ends_at_the_spine(self):
        # the spine the dot draws down the rows' ends is the year's right edge: each row's photograph runs from its name
        # to the spine and no further, so the rows and the spine read as one figure
        for r in self.year["rows"]:
            self.assertEqual(r["band"][2], r["x1"], r["label"]["text"])

    def test_type_under_its_contrast_or_its_smallest_size_is_a_finding(self):
        import storyboard
        p = self.board()
        y = p["board"]["year"]
        y["months"][3]["name"]["contrast"] = 2.1
        y["rows"][5]["label"]["size"] = 40
        y["signoff"]["size"] = 60
        found = storyboard.findings(p)
        self.assertTrue(any(f.startswith("m04") and "2.1:1" in f for f in found), found)
        self.assertTrue(any(f.startswith("wall row") and "40 px" in f for f in found), found)
        self.assertTrue(any(f.startswith("wall sign-off") and "60 px" in f for f in found), found)

    def test_the_closer_lands_the_sign_off_on_the_stop_and_holds_two_seconds(self):
        c = self.year["closer"]
        beat = 60 / self.bpm
        self.assertAlmostEqual((c["end"] - c["still"]) * beat - music.RING, 2.0, delta=0.05)
        self.assertLess(c["hops"][-1], c["still"])
        self.assertEqual(len(c["hops"]), 12)


class Selection(unittest.TestCase):
    """picks.py takes each month's photograph for its moment: the photograph taste.json's moment names, else the post
    with the most to say, never the post with the most likes or comments."""

    def test_a_months_photograph_is_its_moments_never_its_most_liked(self):
        import _env
        import picks
        from unittest import mock
        tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(d)
        for name in ("loved.png", "walk.png", "long.png", "named.png"):
            Image.new("RGB", (40, 30), (120, 90, 60)).save(d / name)
        (d / "other").mkdir()
        Image.new("RGB", (40, 30), (120, 90, 60)).save(d / "other" / "named.png")
        march, may = 1678000000, 1683500000
        _env.write_json("build/library.json", {"year": 2023, "stories": [], "posts": [
            {"media": [str(d / "loved.png")], "ts": march, "caption": "sky", "likes": 900, "comments": 80},
            {"media": [str(d / "walk.png")], "ts": march + 60, "caption": "the long walk up to the castle. sintra @marta.sousa",
             "likes": 3, "comments": 0},
            {"media": [str(d / "long.png")], "ts": may, "caption": "a caption that runs on and on about the light"},
            {"media": [str(d / "other" / "named.png")], "ts": may + 30, "caption": "the same name in another folder"},
            {"media": [str(d / "named.png")], "ts": may + 60, "caption": "mum's birthday."}]})
        _env.write_json("build/taste.json", {"moments": [{"month": "May", "photo": str(d / "named.png"), "line": "mum's birthday."}]})
        with mock.patch.object(picks, "analyse", lambda m: {}), mock.patch.object(picks, "line_of", lambda *a: [0, 0.8, 1, 0.8]), mock.patch.object(picks, "sheet", lambda *a: None), \
                mock.patch.object(sys, "argv", ["picks.py"]), mock.patch("sys.stdout"):
            picks.main()
        got = {m["month"]: m for m in _env.read_json("build/picks.json")["months"]}
        self.assertEqual({n: m["src"] for n, m in got.items()}, {3: str(d / "walk.png"), 5: str(d / "named.png")})
        self.assertEqual((got[3]["said"], got[3]["people"], got[3]["place"]), ("the long walk up to the castle.", ["marta.sousa"], "sintra"))


if __name__ == "__main__":
    unittest.main()
