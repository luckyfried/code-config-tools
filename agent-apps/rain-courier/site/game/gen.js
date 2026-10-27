// The city plan from a seed: blocks, lots, buildings as stacks of boxes, balconies, roof pads, signs, and streetlights.
import { ImprovedNoise } from "three/addons/math/ImprovedNoise.js";
import { createRng, hashString } from "./rng.js";

export const BLOCK = 44;
export const STREET = 14;
export const PITCH = BLOCK + STREET;
export const FLOOR = 3.6;

// The words on the neon signs; vertical signs use the short ones.
export const SIGN_WORDS = [
  "HOTEL", "NOODLES", "24 HOURS", "KARAOKE", "PHARMACY", "BAR", "OPEN", "RAMEN", "LAUNDRY", "ARCADE",
  "TAXI", "CAFE", "DINER", "PARKING", "MOTEL", "TATTOO", "CINEMA", "DUMPLINGS", "RECORDS", "PAWN",
];
export const VERTICAL_WORDS = ["HOTEL", "BAR", "OPEN", "RAMEN", "CAFE", "TAXI", "MOTEL", "DINER", "PAWN", "ARCADE", "TATTOO"];
const NAMES = [
  "Halvorsen", "Marlowe", "Okafor", "Ibarra", "Kestrel", "Vance", "Takeda", "Moreau", "Lindqvist", "Achebe",
  "Castell", "Novak", "Reyes", "Sorensen", "Quill", "Harrow", "Tanaka", "Delacroix", "Brennan", "Oduya",
  "Varga", "Whitlock", "Esposito", "Nakamura", "Ferreira", "Calloway", "Dubois", "Kowalski", "Mbeki", "Rourke",
];

export function generateCity({ seed, cityName, blocksX = 9, blocksZ = 9 }) {
  const rng = createRng(`city:${seed}`);
  const noise = new ImprovedNoise();
  const nz0 = (hashString(String(seed)) % 1000) / 7.3;
  const halfX = (blocksX * PITCH) / 2;
  const halfZ = (blocksZ * PITCH) / 2;
  const downtown = { x: rng.range(-0.15, 0.15) * halfX * 2, z: rng.range(-0.15, 0.15) * halfZ * 2 };
  const reach = Math.max(halfX, halfZ) * 0.95;

  const boxes = [];
  const buildings = [];
  const balconies = [];
  const pads = [];
  const signs = [];
  const aviation = [];
  const names = NAMES.slice();
  for (let i = names.length - 1; i > 0; i--) {
    const j = Math.floor(rng.next() * (i + 1));
    [names[i], names[j]] = [names[j], names[i]];
  }
  let nameAt = 0;
  const nextName = () => names[nameAt++ % names.length];

  const addBox = (b) => {
    boxes.push({
      x: b.x, z: b.z, w: b.w, d: b.d, y0: b.y0 ?? 0, y1: b.y1,
      windows: b.windows !== false, tint: b.tint ?? rng.range(0.85, 1.15),
      lit: b.lit ?? rng.range(0.55, 1), ox: rng.next(), oy: rng.next(), solid: b.solid !== false,
    });
    return boxes.length - 1;
  };

  for (let bx = 0; bx < blocksX; bx++) {
    for (let bz = 0; bz < blocksZ; bz++) {
      const x0 = -halfX + bx * PITCH + STREET / 2;
      const z0 = -halfZ + bz * PITCH + STREET / 2;
      const cx = x0 + BLOCK / 2;
      const cz = z0 + BLOCK / 2;
      const dist = Math.hypot(cx - downtown.x, cz - downtown.z) / reach;
      const core = Math.max(0, 1 - dist * 1.15);
      const plaza = core < 0.2 && rng.chance(0.06);
      if (plaza) continue;

      const splitsX = cuts(rng, BLOCK - 2, core > 0.6 ? rng.int(1, 2) : rng.int(2, 3));
      const splitsZ = cuts(rng, BLOCK - 2, core > 0.6 ? rng.int(1, 2) : rng.int(2, 3));
      for (let ix = 0; ix < splitsX.length; ix++) {
        for (let iz = 0; iz < splitsZ.length; iz++) {
          const [ax, aw] = splitsX[ix];
          const [az, ad] = splitsZ[iz];
          const gap = rng.range(1.2, 2.6);
          const lot = {
            x: x0 + 1 + ax + aw / 2, z: z0 + 1 + az + ad / 2,
            w: aw - gap, d: ad - gap,
            edgeX: ix === 0 ? -1 : ix === splitsX.length - 1 ? 1 : 0,
            edgeZ: iz === 0 ? -1 : iz === splitsZ.length - 1 ? 1 : 0,
          };
          if (lot.w < 7 || lot.d < 7) continue;
          const n = noise.noise(lot.x * 0.012 + nz0, lot.z * 0.012, 0.5) * 0.5 + 0.5;
          const r = rng.next();
          let h = 9 + 16 * rng.next() + core * core * (34 + 96 * r * r) + n * 14;
          h = Math.round(Math.min(150, Math.max(9, h)) / FLOOR) * FLOOR;
          buildBuilding(lot, h, core);
        }
      }
    }
  }

  function buildBuilding(lot, h, core) {
    const building = { boxes: [], top: null, x: lot.x, z: lot.z, h, name: nextName() };
    const tint = rng.range(0.8, 1.2);
    const lit = rng.range(0.5, 1);
    const shapeRoll = rng.next();
    let topBox;
    const add = (b) => {
      const i = addBox({ tint, lit, ...b });
      building.boxes.push(i);
      return i;
    };
    if (h > 66 && shapeRoll < 0.45) {
      const w = lot.w * 0.86, d = lot.d * 0.86;
      add({ x: lot.x, z: lot.z, w: lot.w, d: lot.d, y1: FLOOR * 2 + 0.6 });
      topBox = add({ x: lot.x, z: lot.z, w, d, y1: h });
      add({ x: lot.x, z: lot.z, w: w * 0.7, d: d * 0.7, y0: h, y1: h + 3.4, windows: false });
      const spire = rng.range(10, 22);
      add({ x: lot.x, z: lot.z, w: 0.9, d: 0.9, y0: h + 3.4, y1: h + 3.4 + spire, windows: false, solid: true });
      aviation.push({ x: lot.x, y: h + 3.4 + spire + 0.6, z: lot.z });
    } else if (h > 40 && shapeRoll < 0.8) {
      add({ x: lot.x, z: lot.z, w: lot.w, d: lot.d, y1: Math.round((h * 0.55) / FLOOR) * FLOOR });
      add({ x: lot.x, z: lot.z, w: lot.w * 0.76, d: lot.d * 0.76, y1: Math.round((h * 0.8) / FLOOR) * FLOOR });
      topBox = add({ x: lot.x, z: lot.z, w: lot.w * 0.52, d: lot.d * 0.52, y1: h });
      if (h > 80) aviation.push({ x: lot.x, y: h + 0.8, z: lot.z });
    } else if (shapeRoll < 0.3 && lot.w > 14 && Math.abs(lot.w - lot.d) > 2) {
      const alongX = lot.w > lot.d;
      const share = rng.range(0.4, 0.6);
      const len = alongX ? lot.w : lot.d;
      const a = len * share, b = len - a;
      const hb = Math.max(FLOOR * 3, Math.round((h * rng.range(0.45, 0.7)) / FLOOR) * FLOOR);
      if (alongX) {
        topBox = add({ x: lot.x - len / 2 + a / 2, z: lot.z, w: a, d: lot.d, y1: h });
        add({ x: lot.x + len / 2 - b / 2, z: lot.z, w: b, d: lot.d, y1: hb });
      } else {
        topBox = add({ x: lot.x, z: lot.z - len / 2 + a / 2, w: lot.w, d: a, y1: h });
        add({ x: lot.x, z: lot.z + len / 2 - b / 2, w: lot.w, d: b, y1: hb });
      }
    } else {
      topBox = add({ x: lot.x, z: lot.z, w: lot.w, d: lot.d, y1: h });
    }
    const t = boxes[topBox];
    building.top = topBox;
    // Roof furniture sits at the corners so the middle of a roof stays clear for a pad.
    const units = rng.int(1, 3);
    for (let u = 0; u < units; u++) {
      const sx = rng.chance(0.5) ? 1 : -1, sz = rng.chance(0.5) ? 1 : -1;
      const uw = rng.range(2, 3.6), ud = rng.range(2, 3.6), uh = rng.range(1.6, 3.4);
      if (t.w < uw * 2 + 6 || t.d < ud * 2 + 6) break;
      add({ x: t.x + sx * (t.w / 2 - uw / 2 - 0.8), z: t.z + sz * (t.d / 2 - ud / 2 - 0.8), w: uw, d: ud, y0: t.y1, y1: t.y1 + uh, windows: false });
    }
    if (t.w >= 9 && t.d >= 9) pads.push({ x: t.x, y: t.y1, z: t.z, w: t.w, d: t.d, name: `${building.name} roof`, building: buildings.length });

    // A balcony on a street-facing facade at a lit floor.
    const base = boxes[building.boxes[0]];
    const baseTop = base.y1;
    if (baseTop >= FLOOR * 5 && (lot.edgeX !== 0 || lot.edgeZ !== 0) && rng.chance(0.7)) {
      const onX = lot.edgeX !== 0 && (lot.edgeZ === 0 || rng.chance(0.5));
      const nx = onX ? lot.edgeX : 0;
      const nzz = onX ? 0 : lot.edgeZ;
      const floor = rng.int(3, Math.min(11, Math.floor(baseTop / FLOOR) - 2));
      const y = floor * FLOOR;
      const span = (onX ? base.d : base.w) / 2 - 3;
      const along = rng.range(-span, span);
      const fx = onX ? base.x + nx * (base.w / 2) : base.x + along;
      const fz = onX ? base.z + along : base.z + nzz * (base.d / 2);
      balconies.push({ x: fx, y, z: fz, nx, nz: nzz, floor: floor + 1, name: `${building.name} House`, building: buildings.length });
      boxes.push({
        x: fx + nx * 0.8, z: fz + nzz * 0.8, w: onX ? 1.6 : 3.4, d: onX ? 3.4 : 1.6, y0: y - 0.25, y1: y + 1.1,
        windows: false, tint: 1, lit: 0, ox: 0, oy: 0, solid: true, balcony: true,
      });
    }

    // Facade signs on the street sides of the lower floors.
    const signCount = core > 0.3 ? rng.int(1, 3) : rng.int(0, 2);
    for (let s = 0; s < signCount; s++) {
      const useX = lot.edgeX !== 0 && (lot.edgeZ === 0 || rng.chance(0.5));
      const nx = useX ? lot.edgeX : 0;
      const nzz = useX ? 0 : lot.edgeZ || (rng.chance(0.5) ? 1 : -1);
      const face = boxes[building.boxes[0]];
      const vertical = rng.chance(0.55);
      const word = vertical ? rng.pick(VERTICAL_WORDS) : rng.pick(SIGN_WORDS);
      const sw = vertical ? rng.range(1.5, 2.1) : Math.min(rng.range(5, 9), (useX ? face.d : face.w) - 2);
      const sh = vertical ? sw * (720 / 124) : sw * (124 / 512);
      if (sw < 1.2 || (vertical && face.y1 < sh + 6)) continue;
      const y = vertical ? rng.range(4 + sh / 2, Math.max(4 + sh / 2, Math.min(face.y1 - sh / 2 - 1, 24))) : rng.range(4, Math.min(face.y1 - 2, 18));
      const span = (useX ? face.d : face.w) / 2 - sw / 2 - 0.5;
      if (span < 0) continue;
      const along = rng.range(-span, span);
      signs.push({
        x: useX ? face.x + nx * (face.w / 2 + 0.22) : face.x + along,
        y,
        z: useX ? face.z + along : face.z + nzz * (face.d / 2 + 0.22),
        nx, nz: nzz, w: sw, h: sh, text: word, vertical, color: rng.int(0, 2), flicker: rng.chance(0.18) ? rng.next() : -1,
      });
    }
    buildings.push(building);
  }

  // The city's name on rooftop billboards over the tallest blocks, each facing out over a street.
  const byHeight = buildings.map((b, i) => i).sort((a, b) => buildings[b].h - buildings[a].h);
  let named = 0;
  for (const i of byHeight) {
    if (named >= 9) break;
    const b = buildings[i];
    const t = boxes[b.top];
    if (t.y1 < 28 || t.w < 14) continue;
    const facing = Math.abs(t.x - downtown.x) > Math.abs(t.z - downtown.z) ? [Math.sign(t.x - downtown.x) || 1, 0] : [0, Math.sign(t.z - downtown.z) || 1];
    const along = facing[0] !== 0 ? t.d : t.w;
    const w = Math.min(along - 1.5, 24);
    const h = w * (420 / 2048);
    const ex = facing[0] * (t.w / 2 - 1.2);
    const ez = facing[1] * (t.d / 2 - 1.2);
    signs.push({ x: t.x + ex, y: t.y1 + 1.6 + h / 2, z: t.z + ez, nx: facing[0], nz: facing[1], w, h, text: cityName, vertical: false, color: named % 2, flicker: -1, big: true });
    // Back to back, so the name reads from both sides of the roof.
    signs.push({ x: t.x + ex - facing[0] * 0.8, y: t.y1 + 1.6 + h / 2, z: t.z + ez - facing[1] * 0.8, nx: -facing[0], nz: -facing[1], w, h, text: cityName, vertical: false, color: (named + 1) % 2, flicker: -1, big: true });
    boxes.push({ x: t.x + ex - facing[0] * 0.4, z: t.z + ez - facing[1] * 0.4, w: facing[0] ? 0.5 : w, d: facing[0] ? w : 0.5, y0: t.y1, y1: t.y1 + 1.6 + h, windows: false, tint: 0.6, lit: 0, ox: 0, oy: 0, solid: true, frame: true });
    named++;
  }

  // Streetlights in rows along both kerbs of every street.
  const lamps = [];
  const spacing = 19;
  for (let i = 0; i <= blocksX; i++) {
    const sx = -halfX + i * PITCH;
    for (let z = -halfZ + 8; z < halfZ - 4; z += spacing) {
      if (nearCrossing(z, halfZ)) continue;
      lamps.push({ x: sx - STREET / 2 + 0.8, z, ax: 1, az: 0 });
      lamps.push({ x: sx + STREET / 2 - 0.8, z: z + spacing / 2, ax: -1, az: 0 });
    }
  }
  for (let j = 0; j <= blocksZ; j++) {
    const sz = -halfZ + j * PITCH;
    for (let x = -halfX + 8; x < halfX - 4; x += spacing) {
      if (nearCrossing(x, halfX)) continue;
      lamps.push({ x, z: sz - STREET / 2 + 0.8, ax: 0, az: 1 });
      lamps.push({ x: x + spacing / 2, z: sz + STREET / 2 - 0.8, ax: 0, az: -1 });
    }
  }

  return {
    seed, cityName, blocksX, blocksZ, halfX, halfZ, downtown,
    boxes, buildings, balconies, pads, signs, lamps, aviation,
    grid: buildGrid(boxes, halfX, halfZ),
  };
}

function nearCrossing(v, half) {
  const k = (v + half) / PITCH;
  const off = Math.abs(k - Math.round(k)) * PITCH;
  return off < STREET / 2 + 1.5;
}

function cuts(rng, length, parts) {
  const out = [];
  let at = 0;
  for (let i = 0; i < parts; i++) {
    const left = length - at;
    const size = i === parts - 1 ? left : Math.max(10, Math.min(left - 10 * (parts - i - 1), (length / parts) * rng.range(0.7, 1.3)));
    out.push([at, size]);
    at += size;
  }
  return out;
}

// A uniform grid over the city so the flight only tests the boxes near the drone.
export const CELL = 16;
function buildGrid(boxes, halfX, halfZ) {
  const nx = Math.ceil((halfX * 2 + 40) / CELL);
  const nz = Math.ceil((halfZ * 2 + 40) / CELL);
  const ox = -halfX - 20, oz = -halfZ - 20;
  const cells = Array.from({ length: nx * nz }, () => []);
  boxes.forEach((b, i) => {
    if (!b.solid) return;
    const x0 = Math.max(0, Math.floor((b.x - b.w / 2 - ox) / CELL));
    const x1 = Math.min(nx - 1, Math.floor((b.x + b.w / 2 - ox) / CELL));
    const z0 = Math.max(0, Math.floor((b.z - b.d / 2 - oz) / CELL));
    const z1 = Math.min(nz - 1, Math.floor((b.z + b.d / 2 - oz) / CELL));
    for (let x = x0; x <= x1; x++) for (let z = z0; z <= z1; z++) cells[x * nz + z].push(i);
  });
  let stamp = 1;
  const seen = new Uint32Array(boxes.length);
  return {
    // Calls visit(index) once for every solid box whose cell touches the square around (x, z).
    query(x, z, r, visit) {
      stamp++;
      const x0 = Math.max(0, Math.floor((x - r - ox) / CELL));
      const x1 = Math.min(nx - 1, Math.floor((x + r - ox) / CELL));
      const z0 = Math.max(0, Math.floor((z - r - oz) / CELL));
      const z1 = Math.min(nz - 1, Math.floor((z + r - oz) / CELL));
      for (let cx = x0; cx <= x1; cx++) {
        for (let cz = z0; cz <= z1; cz++) {
          const list = cells[cx * nz + cz];
          for (let k = 0; k < list.length; k++) {
            const i = list[k];
            if (seen[i] === stamp) continue;
            seen[i] = stamp;
            visit(i);
          }
        }
      }
    },
  };
}
