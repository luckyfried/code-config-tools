// The two trays beside the board: each holds its side's discs on a grid of sixteen stacks, eight along the tray in
// two lines. Discs are dealt one per stack, along the line next to the player's card and then the other line, a level
// at a time, so the stacks spread over the whole tray as the count grows and rise evenly. Sixty-four discs make
// sixteen stacks of four. Wide screens put the trays left and right of the board; tall screens above and below it.
import { Group, Mesh, Shape, Path, ExtrudeGeometry, PlaneGeometry, Quaternion, Vector3, Color } from "three";
import { BLACK, WHITE } from "../game/reversi.js";
import { DISC_H, discQuaternion } from "./discs.js";
import { lacquerMaterial, feltMaterial } from "./materials.js";

export const TABLE_Y = -0.46;
const FLOOR = TABLE_Y + 0.07;
export const PER_STACK = 4;
const ALONG = 8;
const RIM = 0.1;
// Felt left between the stacks and the rim at the tray's near and far sides.
const NEAR = 0.18;
const FAR = 0.44;
// Grid steps. A step that runs away from the camera is wider: seen from the camera's tilt a four-high stack leans
// over the cell behind it, and these keep every stack's top clear of its neighbour's (64° tilt wide, 70° tall).
const WIDE_ALONG = 1.16;
const WIDE_CROSS = 1.0;
const TALL_ALONG = 1.02;
const TALL_CROSS = 1.12;

function rounded(shape, w, h, r) {
  const x = -w / 2;
  const y = -h / 2;
  shape.moveTo(x + r, y);
  shape.lineTo(x + w - r, y);
  shape.quadraticCurveTo(x + w, y, x + w, y + r);
  shape.lineTo(x + w, y + h - r);
  shape.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  shape.lineTo(x + r, y + h);
  shape.quadraticCurveTo(x, y + h, x, y + h - r);
  shape.lineTo(x, y + r);
  shape.quadraticCurveTo(x, y, x + r, y);
  return shape;
}

// Stable small offsets so a stack looks hand-built rather than machined.
function jitter(seed) {
  const s = Math.sin(seed * 12.9898) * 43758.5453;
  return s - Math.floor(s) - 0.5;
}

export function trayLayout(mode, cardsAbove = false) {
  if (mode === "wide") {
    // Eight cells along each tray from the near end, by the card, toward the far end; the line by the board first.
    // The far end keeps the wider margin: from the camera's tilt a stack's top leans toward the far rim.
    const w = 2 * RIM + WIDE_CROSS + 0.84 + 0.56;
    const d = 2 * RIM + (ALONG - 1) * WIDE_ALONG + 0.84 + NEAR + FAR;
    const cx = 4.5 + 0.55 + w / 2;
    const z0 = ((ALONG - 1) * WIDE_ALONG) / 2 + (FAR - NEAR) / 2;
    return {
      mode,
      // Cell 0 of line 0 sits at `start`; the next cell is `step` along the line, the second line `cross` over.
      start: { [BLACK]: { x: WIDE_CROSS / 2, z: z0 }, [WHITE]: { x: -WIDE_CROSS / 2, z: z0 } },
      step: { x: 0, z: -WIDE_ALONG },
      cross: { [BLACK]: { x: -WIDE_CROSS, z: 0 }, [WHITE]: { x: WIDE_CROSS, z: 0 } },
      size: { w, d },
      centers: { [BLACK]: new Vector3(-cx, 0, 0), [WHITE]: new Vector3(cx, 0, 0) },
      // The card sits just below each tray's near edge, clear of the stacks. On short screens, where the bottom strip
      // is the page's, it sits above the far edge instead, centered on the tray's inner rim so it reaches over the
      // open table behind the board rather than past the screen's side.
      cardsAbove,
      anchors: cardsAbove
        ? { [BLACK]: new Vector3(-cx + w / 2, 0, -d / 2 - 0.12), [WHITE]: new Vector3(cx - w / 2, 0, -d / 2 - 0.12) }
        : { [BLACK]: new Vector3(-cx, 0, d / 2 + 0.12), [WHITE]: new Vector3(cx, 0, d / 2 + 0.12) },
      below: { [BLACK]: !cardsAbove, [WHITE]: !cardsAbove },
      shakeAxis: new Vector3(0, 0, 1),
    };
  }
  // Tall screens: eight cells across the tray from left to right; the line by the card first.
  const w = 2 * RIM + (ALONG - 1) * TALL_ALONG + 0.84 + 0.36;
  const d = 2 * RIM + TALL_CROSS + 0.84 + NEAR + FAR;
  const cz = 4.5 + 0.45 + d / 2;
  const x0 = (-(ALONG - 1) * TALL_ALONG) / 2;
  const mid = (FAR - NEAR) / 2;
  return {
    mode,
    cardsAbove: false,
    start: { [BLACK]: { x: x0, z: mid + TALL_CROSS / 2 }, [WHITE]: { x: x0, z: mid - TALL_CROSS / 2 } },
    step: { x: TALL_ALONG, z: 0 },
    cross: { [BLACK]: { x: 0, z: -TALL_CROSS }, [WHITE]: { x: 0, z: TALL_CROSS } },
    size: { w, d },
    centers: { [BLACK]: new Vector3(0, 0, cz), [WHITE]: new Vector3(0, 0, -cz) },
    anchors: { [BLACK]: new Vector3(-2.6, 0, cz + d / 2 - 0.03), [WHITE]: new Vector3(-2.6, 0, -cz - d / 2 + 0.03) },
    below: { [BLACK]: true, [WHITE]: false },
    shakeAxis: new Vector3(1, 0, 0),
  };
}

/** Where living disc number `slot` of tray `color` rests, from the tray's center: the stack's x and z and its level. */
export function stackSpot(layout, color, slot, out) {
  const cells = 2 * ALONG;
  const c = slot % cells;
  const line = Math.floor(c / ALONG);
  const cell = c % ALONG;
  const start = layout.start[color];
  const cross = layout.cross[color];
  out.x = start.x + layout.step.x * cell + cross.x * line;
  out.z = start.z + layout.step.z * cell + cross.z * line;
  out.level = Math.min(PER_STACK - 1, Math.floor(slot / cells));
  return out;
}

export function createTrays() {
  const group = new Group();
  const wallMaterial = lacquerMaterial();
  const floorMaterial = feltMaterial();
  const meshes = {};
  let layout = null;

  function build(mode, cardsAbove) {
    layout = trayLayout(mode, cardsAbove);
    for (const key of Object.keys(meshes)) {
      group.remove(meshes[key]);
      meshes[key].traverse((o) => o.geometry && o.geometry.dispose());
    }
    for (const color of [BLACK, WHITE]) {
      const { w, d } = layout.size;
      const tray = new Group();
      const outer = rounded(new Shape(), w, d, 0.22);
      const hole = new Path();
      const iw = w - 2 * RIM;
      const id = d - 2 * RIM;
      hole.moveTo(-iw / 2, -id / 2);
      hole.lineTo(-iw / 2, id / 2);
      hole.lineTo(iw / 2, id / 2);
      hole.lineTo(iw / 2, -id / 2);
      hole.lineTo(-iw / 2, -id / 2);
      outer.holes.push(hole);
      const wall = new Mesh(
        new ExtrudeGeometry(outer, { depth: 0.16, bevelEnabled: true, bevelThickness: 0.025, bevelSize: 0.025, bevelSegments: 2, curveSegments: 6 }),
        wallMaterial,
      );
      wall.rotation.x = -Math.PI / 2;
      wall.position.y = TABLE_Y;
      wall.castShadow = true;
      wall.receiveShadow = true;
      const floor = new Mesh(new PlaneGeometry(iw + 0.02, id + 0.02), floorMaterial);
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = FLOOR - 0.001;
      floor.receiveShadow = true;
      tray.add(wall, floor);
      tray.position.copy(layout.centers[color]);
      meshes[color] = tray;
      group.add(tray);
    }
    return layout;
  }

  const qa = new Quaternion();
  const tilt = new Quaternion();
  const tiltAxis = new Vector3();
  const spot = {};

  /**
   * Places tray `color`'s discs into `pool` from instance `offset`, reading the stacks from `table`. A disc's place is
   * its rank among the discs in the tray now, so discs still to come never leave gaps and the stacks stay packed.
   */
  function sync(table, now, pool, offset, color) {
    const center = layout.centers[color];
    const shake = table.shakeOffset(color, now);
    const sx = layout.shakeAxis.x * shake;
    const sz = layout.shakeAxis.z * shake;
    meshes[color].position.set(center.x + sx, 0, center.z + sz);
    const stack = table.trays[color];
    const pose = {};
    let slot = 0;
    for (let j = 0; j < stack.length && slot < 64; j += 1) {
      table.trayPose(color, j, now, pose);
      if (!pose.visible) continue;
      stackSpot(layout, color, slot, spot);
      const x = center.x + sx + spot.x + jitter(slot * 3 + color) * 0.03;
      const z = center.z + sz + spot.z + jitter(slot * 7 + color) * 0.03;
      const y = FLOOR + DISC_H + spot.level * DISC_H * 2 + pose.lift;
      discQuaternion(color, 0, 1, 0, qa);
      tiltAxis.set(jitter(slot + 1), 0, jitter(slot + 2)).normalize();
      tilt.setFromAxisAngle(tiltAxis, 0.02);
      qa.premultiply(tilt);
      pool.set(offset + slot, x, y, z, qa, pose.scale);
      slot += 1;
    }
    for (; slot < 64; slot += 1) pool.hide(offset + slot);
  }

  function applyTokens(tokens) {
    wallMaterial.color = new Color(tokens.tray);
    floorMaterial.color = new Color(tokens.trayFloor);
  }

  return { group, build, sync, applyTokens, get layout() { return layout; } };
}
