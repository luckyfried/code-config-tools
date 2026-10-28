// The bookcase and where every book goes on it. Rows run along the whole wall; bays are the columns between
// uprights. A segment is one row of one bay: it holds a run of books, face-out books on easels, a flat stack,
// a bookend, and a small object, composed so a short library still reads as a styled shelf.
import * as THREE from "three";
import { hash, rng, stripCanvas, blobCanvas } from "./textures.js";
import { bookDims } from "./dims.js";

export { bookDims };
import { canvasTexture } from "./renderer.js";

export const CASE = {
  rows: 3,
  rowH: 0.28,
  board: 0.024,
  side: 0.032,
  divider: 0.022,
  depth: 0.27,
  bayW: 0.46,
  plinth: 0.075,
  crown: 0.05,
};

export function caseGeometry(bays) {
  const innerW = bays * CASE.bayW + (bays - 1) * CASE.divider;
  const outerW = innerW + CASE.side * 2;
  const floorY = (r) => CASE.plinth + CASE.board + (CASE.rows - 1 - r) * (CASE.rowH + CASE.board);
  const topY = CASE.plinth + CASE.rows * (CASE.rowH + CASE.board) + CASE.board;
  const bayX = (b) => -innerW / 2 + b * (CASE.bayW + CASE.divider);
  return { bays, innerW, outerW, floorY, topY, height: topY + CASE.crown, bayX, front: CASE.depth / 2 };
}

/** How tall a face-out book may stand inside a row: room above it for the bookmark tag and a clear gap. */
export const BOOKMARK_RISE = 0.04;
const FACE_ROOM = CASE.rowH - CASE.board * 0.5 - 0.014;

const DECOR_ORDER = ["plant", "frame", "vase", "candle", "stones", "plant", "vase", "frame", "candle"];

/**
 * Slots for `books` (already sorted) on a case of `bays` bays. Returns { geo, slots: Map(id -> slot), decor: [] }.
 * A slot is { kind: "stand" | "lean" | "flat" | "face", pos, quat, offset, row, seg }.
 */
export function layoutShelf(books, bays) {
  const geo = caseGeometry(bays);
  const S = CASE.rows * bays;
  const items = books.map((b) => {
    const dims = bookDims(b);
    const kind = b.status === "reading" ? "face" : "stand";
    return { b, dims, kind, w: kind === "face" ? dims.d + 0.04 : dims.t + 0.003 };
  });
  const total = items.reduce((s, it) => s + it.w, 0);
  const target = total / S;
  const segs = Array.from({ length: S }, () => []);
  let seg = 0;
  let acc = 0;
  items.forEach((it, i) => {
    const left = items.length - i;
    const segsLeft = S - seg - 1;
    if (acc > 0 && seg < S - 1 && (acc + it.w > target * 1.15 || left <= segsLeft)) {
      seg += 1;
      acc = 0;
    }
    segs[seg].push(it);
    acc += it.w;
  });

  const slots = new Map();
  const decor = [];
  const front = geo.front - 0.022;
  const Q = (x, y, z, order = "XYZ") => new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, order));

  segs.forEach((list, s) => {
    const row = Math.floor(s / bays);
    const bay = s % bays;
    const x0 = geo.bayX(bay);
    const y = geo.floorY(row);
    const mirror = s % 2 === 1;
    const X = (u) => (mirror ? x0 + CASE.bayW - u : x0 + u);
    const dir = mirror ? -1 : 1;
    const r = rng(hash(`seg-${s}`));
    let u = 0.014;

    const faces = list.filter((it) => it.kind === "face");
    let stands = list.filter((it) => it.kind !== "face");
    let flats = [];
    if (stands.length >= 4 && s % 3 === 2) {
      flats = stands.slice(-2).filter((it) => it.dims.h < CASE.bayW * 0.5);
      stands = stands.slice(0, stands.length - flats.length);
    }

    for (const it of faces) {
      const { d, h, t } = it.dims;
      const cx = X(u + 0.012 + d / 2);
      const faceZ = CASE.depth / 2 - 0.085;
      // A tall book leans back further on its easel and, past a comfortable lean, stands a little smaller, so its
      // bookmark tag always stands whole above its front edge and clear below the board above.
      const stand = (th) => h * Math.cos(th) + (t / 2) * Math.sin(th) + BOOKMARK_RISE * Math.cos(th);
      let tilt = 0.2;
      while (tilt < 0.5 && 0.012 + stand(tilt) > FACE_ROOM) tilt += 0.02;
      const scale = Math.min(1, (FACE_ROOM - 0.012) / stand(tilt));
      slots.set(it.b.id, {
        kind: "face",
        row,
        seg: s,
        pos: new THREE.Vector3(cx, y + 0.012, faceZ),
        quat: new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -tilt).multiply(Q(0, -Math.PI / 2, 0)),
        offset: new THREE.Vector3(0, h / 2, 0),
        tilt,
        scale,
      });
      decor.push({ type: "easel", x: cx, y, z: faceZ, w: d * scale, t: t * scale, tilt, row, seg: s });
      u += d + 0.04;
    }

    const leanIt = stands.length >= 3 && s % 3 === 0 ? stands[stands.length - 1] : null;
    let prev = null;
    for (const it of stands) {
      const { t, h } = it.dims;
      if (it === leanIt && prev) {
        const theta = 0.2;
        const contact = Math.min(prev.h, h * Math.cos(theta));
        const uEdge = prev.uEnd + contact * Math.tan(theta);
        slots.set(it.b.id, {
          kind: "lean",
          row,
          seg: s,
          pos: new THREE.Vector3(X(uEdge), y, front),
          quat: Q(0, 0, theta * dir),
          offset: new THREE.Vector3((t / 2) * dir, h / 2, -it.dims.d / 2),
        });
        u = uEdge + t * Math.cos(theta) + h * Math.sin(theta) * 0.15 + 0.012;
        prev = null;
        continue;
      }
      const gap = 0.001 + r() * 0.003;
      const cx = u + t / 2;
      slots.set(it.b.id, {
        kind: "stand",
        row,
        seg: s,
        pos: new THREE.Vector3(X(cx), y, front - r() * 0.006),
        quat: Q(0, (r() - 0.5) * 0.04, 0),
        offset: new THREE.Vector3(0, h / 2, -it.dims.d / 2),
      });
      prev = { uEnd: u + t, h };
      u += t + gap;
    }
    if (stands.length && !leanIt) {
      decor.push({ type: "bookend", x: X(u + 0.004), y, dir, row, seg: s });
      u += 0.03;
    }

    if (flats.length) {
      const hmax = Math.max(...flats.map((it) => it.dims.h));
      const cu = u + 0.02 + hmax / 2;
      let stack = 0;
      flats
        .slice()
        .sort((a, b) => b.dims.h - a.dims.h)
        .forEach((it) => {
          const { t, h } = it.dims;
          slots.set(it.b.id, {
            kind: "flat",
            row,
            seg: s,
            pos: new THREE.Vector3(X(cu) + h / 2, y + stack + t / 2, front - 0.004),
            quat: Q(0, 0, Math.PI / 2 + (r() - 0.5) * 0.03),
            offset: new THREE.Vector3(0, h / 2, -it.dims.d / 2),
          });
          stack += t;
        });
      decor.push({ type: "stones", x: X(cu), y: y + stack, row, seg: s, small: true });
      u = cu + hmax / 2 + 0.01;
    }

    const free = CASE.bayW - u;
    if (free > 0.1) {
      const type = DECOR_ORDER[s % DECOR_ORDER.length];
      const room = Math.min(free - 0.02, 0.2);
      decor.push({ type, x: X(CASE.bayW - Math.max(0.06, Math.min(free / 2, room / 2 + 0.03))), y, room, row, seg: s });
    }
  });

  return { geo, slots, decor };
}

/** The bookcase meshes for a case geometry, with baked contact strips under and behind each row. */
export function buildCase(geo, mats, room, tokens, renderer) {
  const group = new THREE.Group();
  const { board, post } = mats;
  const add = (geometry, material, x, y, z, cast = true) => {
    const m = new THREE.Mesh(geometry, material);
    m.position.set(x, y, z);
    m.castShadow = cast;
    m.receiveShadow = true;
    group.add(m);
    return m;
  };
  const D = CASE.depth;
  const H = geo.topY;
  add(new THREE.BoxGeometry(CASE.side, H + 0.02, D + 0.012), post, -geo.outerW / 2 + CASE.side / 2, (H + 0.02) / 2, 0.006);
  add(new THREE.BoxGeometry(CASE.side, H + 0.02, D + 0.012), post, geo.outerW / 2 - CASE.side / 2, (H + 0.02) / 2, 0.006);
  for (let r = 0; r <= CASE.rows; r += 1) {
    const yTop = r < CASE.rows ? geo.floorY(r) : geo.topY;
    add(new THREE.BoxGeometry(geo.innerW, CASE.board, D), board, 0, yTop - CASE.board / 2, 0);
    // A thicker front lip reads as solid timber.
    add(new THREE.BoxGeometry(geo.innerW, CASE.board * 1.5, 0.014), board, 0, yTop - CASE.board * 0.75, D / 2 + 0.002);
  }
  for (let b = 1; b < geo.bays; b += 1) {
    const x = geo.bayX(b) - CASE.divider / 2;
    for (let r = 0; r < CASE.rows; r += 1) {
      const y0 = geo.floorY(r);
      add(new THREE.BoxGeometry(CASE.divider, CASE.rowH, D - 0.004), post, x, y0 + CASE.rowH / 2, -0.002);
    }
  }
  add(new THREE.BoxGeometry(geo.outerW + 0.05, CASE.crown, D + 0.05), board, 0, H + CASE.crown / 2, 0.02);
  add(new THREE.BoxGeometry(geo.outerW - 0.03, CASE.plinth, D - 0.03), post, 0, CASE.plinth / 2, -0.01);

  const backPanel = new THREE.Mesh(new THREE.PlaneGeometry(geo.innerW, H - CASE.plinth), room.back);
  backPanel.position.set(0, CASE.plinth + (H - CASE.plinth) / 2, -D / 2 + 0.002);
  backPanel.receiveShadow = true;
  group.add(backPanel);
  backPanel.material.map.repeat.set(geo.innerW * 9, 1);

  // Baked contact shadows: on each board, at the foot of the back panel, and under each board on the back panel.
  const stripTex = canvasTexture(stripCanvas(), renderer, { srgb: false });
  const stripMat = new THREE.MeshBasicMaterial({
    color: tokens.shadow,
    alphaMap: stripTex,
    transparent: true,
    opacity: tokens.shadowPower,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });
  for (let r = 0; r < CASE.rows; r += 1) {
    const y0 = geo.floorY(r);
    const floorStrip = new THREE.Mesh(new THREE.PlaneGeometry(geo.innerW, D), stripMat);
    floorStrip.rotation.x = -Math.PI / 2;
    floorStrip.position.set(0, y0 + 0.0008, 0);
    group.add(floorStrip);
    const backFoot = new THREE.Mesh(new THREE.PlaneGeometry(geo.innerW, 0.08), stripMat);
    backFoot.rotation.z = Math.PI;
    backFoot.position.set(0, y0 + 0.04, -D / 2 + 0.003);
    group.add(backFoot);
    const backHead = new THREE.Mesh(new THREE.PlaneGeometry(geo.innerW, 0.06), stripMat);
    backHead.position.set(0, y0 + CASE.rowH - 0.03, -D / 2 + 0.003);
    group.add(backHead);
  }
  const softMat = new THREE.MeshBasicMaterial({ color: tokens.shadow, alphaMap: canvasTexture(blobCanvas(), renderer, { srgb: false }), transparent: true, opacity: tokens.shadowPower, depthWrite: false });
  const floorShadow = new THREE.Mesh(new THREE.PlaneGeometry(geo.outerW + 0.5, 0.7), softMat);
  floorShadow.rotation.x = -Math.PI / 2;
  floorShadow.position.set(0, 0.002, -D / 2 + 0.1);
  group.add(floorShadow);
  return { group, stripMat, softMat };
}
