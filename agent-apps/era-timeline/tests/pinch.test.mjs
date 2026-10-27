// Replays a recorded two-finger pinch and a timeline's lanes through the page's own modules:
//   node --test tests/pinch.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { pinch, timeAt, zoomAt, flight } from "../site/js/camera.js";
import { layoutLanes, countOverlaps } from "../site/js/lanes.js";

// Pointer positions sampled from a pinch-out on a phone held upright (time runs down, so y is the time axis),
// one sample a frame, as the page applies them after its one-frame debounce.
const RECORDED = [
  { a: { x: 180, y: 400 }, b: { x: 200, y: 480 } },
  { a: { x: 179, y: 392 }, b: { x: 201, y: 489 } },
  { a: { x: 177, y: 380 }, b: { x: 203, y: 502 } },
  { a: { x: 175, y: 366 }, b: { x: 206, y: 518 } },
  { a: { x: 172, y: 351 }, b: { x: 209, y: 535 } },
  { a: { x: 170, y: 340 }, b: { x: 211, y: 548 } },
];

const YEAR = 365.2425 * 86400000;
const start = { cam: { t0: Date.UTC(1850, 0, 1), k: (176 * YEAR) / 700 }, a: RECORDED[0].a, b: RECORDED[0].b };
const distance = ({ a, b }) => Math.hypot(a.x - b.x, a.y - b.y);
const middle = ({ a, b }) => (a.y + b.y) / 2;

test("a recorded pinch zooms by the ratio of the two-pointer distances", () => {
  for (const frame of RECORDED) {
    const cam = pinch(start, frame.a, frame.b, "y");
    const ratio = distance(RECORDED[0]) / distance(frame);
    assert.ok(Math.abs(cam.k / start.cam.k - ratio) < 1e-9);
  }
});

test("the time under the fingers stays under the fingers", () => {
  const held = timeAt(start.cam, middle(RECORDED[0]));
  for (const frame of RECORDED) {
    const cam = pinch(start, frame.a, frame.b, "y");
    assert.ok(Math.abs(timeAt(cam, middle(frame)) - held) < 1000, "within a second of the starting time");
  }
});

test("zooming in keeps the time under the cursor", () => {
  const cam = { t0: 0, k: 1000 };
  const next = zoomAt(cam, 300, 2);
  assert.equal(timeAt(next, 300), timeAt(cam, 300));
  assert.equal(next.k, 500);
});

test("a flight starts at the first camera and ends at the second", () => {
  const a = { t0: 0, k: 1000 };
  const b = { t0: 5e8, k: 40 };
  const path = flight(a, b, 1200);
  const first = path(0);
  assert.ok(Math.abs(first.t0 - a.t0) < 1e-3 && Math.abs(first.k - a.k) < 1e-9);
  assert.deepEqual(path(1), b);
});

test("greedy lanes never overlap and gather the overflow into badges", () => {
  const items = Array.from({ length: 40 }, (_, i) => ({ id: `e${i}`, at: 100 + (i % 10) * 9, size: 160 }));
  const layout = layoutLanes(items, { mode: "rows", rows: 6, lead: 14, gap: 6, badge: 34 });
  const boxes = [...layout.placed.values()].map((p) => ({ x: p.from, y: p.lane * 40, w: p.size, h: 30 }));
  assert.equal(countOverlaps(boxes), 0);
  assert.ok(layout.placed.size <= 6);
  const hidden = layout.clusters.reduce((n, c) => n + c.ids.length, 0);
  assert.equal(layout.placed.size + hidden, items.length);
});

test("a pin folds into a badge only when no row has room, sliding the flags already there", () => {
  // The 1930s on a desktop: a flag led forward from its pin leaves a few pixels too few for the next pin's flag,
  // and the only row is free once the first flag hangs back from its pin.
  const items = [
    { id: "sailing", at: 511, size: 183 },
    { id: "ruth", at: 693, size: 210 },
  ];
  const layout = layoutLanes(items, { mode: "rows", rows: 1, lead: 14, gap: 6, badge: 34, start: 10, slide: true });
  assert.equal(layout.placed.size, 2);
  assert.equal(layout.clusters.length, 0);
  const [a, b] = ["sailing", "ruth"].map((id) => layout.placed.get(id));
  assert.ok(a.from + a.size + 12 <= b.from, "the two flags keep their gap");
  assert.ok(a.from + 14 <= 511 && 511 <= a.from + a.size - 14 && b.from + 14 <= 693 && 693 <= b.from + b.size - 14, "each flag stays over its pin");
});

test("down the phone, a flag goes next to the axis when the flags there can slide to let it in", () => {
  const items = [
    { id: "bakery", at: 410, size: 200, thick: 50 },
    { id: "ruth", at: 460, size: 220, thick: 50 },
    { id: "marries", at: 520, size: 200, thick: 50, first: true },
  ];
  const layout = layoutLanes(items, { mode: "pack", thick: 32, gap: 5, from: 120, to: 385, minSize: Infinity, badge: 44, slide: 12 });
  assert.equal(layout.placed.size, 3);
  const boxes = items.map((it) => ({ ...layout.placed.get(it.id), thick: it.thick })).map((p) => ({ x: p.lane, y: p.from, w: p.size, h: p.thick }));
  assert.equal(countOverlaps(boxes), 0);
});
