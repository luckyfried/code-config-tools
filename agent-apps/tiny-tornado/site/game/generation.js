// The town, grown from the seed: two crossing roads, a town center of houses and the water tower, and farms in the
// four quarters (barn, silo, farmhouse, fenced pasture with cows, a hay field, a windbreak, and a parked truck), with
// crop fields between them. Farm 0 is the showcase: the storm is born in its pasture with the barn just ahead.
// North is -z; the camera watches from the south.

export function seedRandom(text) {
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  let a = h1 >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const ROAD_WIDTH = 7;
export const TOWN_EDGE = 132;
const SLOTS_X = [-44, 44, -106, 106];
const SLOTS_Z = [38, -40, 98, -100];
const CROPS = ["cropA", "cropB", "cropC", "cropD"];

export function generateTown(seed) {
  const rnd = seedRandom(String(seed).toLowerCase());
  const pick = (list) => list[Math.floor(rnd() * list.length)];
  const range = (a, b) => a + (b - a) * rnd();
  const props = [];
  const fields = [];
  const pastures = [];
  const yards = [];
  const lawns = [];
  const lanes = [];
  const add = (type, x, z, rot = 0, extra = {}) => props.push({ type, x, z, rot, ...extra });

  const slots = [];
  for (const x of SLOTS_X) for (const z of SLOTS_Z) slots.push({ x, z });
  const showcase = slots.find((s) => s.x === -44 && s.z === 38);
  const others = slots.filter((s) => s !== showcase);
  for (let i = others.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [others[i], others[j]] = [others[j], others[i]];
  }
  const farmSlots = [showcase, ...others.slice(0, 7)];
  const fieldSlots = others.slice(7);

  farmSlots.forEach((slot, index) => {
    const cx = slot.x + (index === 0 ? 0 : range(-3, 3));
    const cz = slot.z + (index === 0 ? 0 : range(-2, 2));
    const m = index === 0 ? 1 : rnd() < 0.5 ? -1 : 1;
    yards.push({ x0: cx - 9, z0: cz - 17, x1: cx + 9, z1: cz - 1 });
    add("barn", cx, cz - 9, 0, { farm: index });
    add("silo", cx + m * 5.8, cz - 12.2, 0, { farm: index });
    add("house", cx - m * 14, cz - 10, m > 0 ? 0.08 : -0.08, { farm: index });
    lawns.push({ x0: cx - m * 14 - 5, z0: cz - 15, x1: cx - m * 14 + 5, z1: cz - 4 });
    add("truck", cx - m * 5.8, cz - 2.4, Math.PI / 2 + range(-0.2, 0.2), { farm: index });

    const px0 = cx - 15;
    const px1 = cx + 15;
    const pz0 = cz + 0.5;
    const pz1 = cz + 19;
    pastures.push({ x0: px0, z0: pz0, x1: px1, z1: pz1 });
    const fenceRun = (ax, az, bx, bz, gapAt) => {
      const len = Math.hypot(bx - ax, bz - az);
      const n = Math.round(len / 2.1);
      const rot = Math.atan2(-(bz - az), bx - ax);
      for (let k = 0; k < n; k++) {
        if (gapAt !== undefined && k === gapAt) continue;
        const t = (k + 0.5) / n;
        add("fence", ax + (bx - ax) * t, az + (bz - az) * t, rot, { farm: index });
      }
    };
    fenceRun(px0, pz0, px1, pz0, 7);
    fenceRun(px0, pz1, px1, pz1);
    fenceRun(px0, pz0, px0, pz1);
    fenceRun(px1, pz0, px1, pz1);
    const cows = index === 0 ? 7 : 4 + Math.floor(rnd() * 4);
    for (let k = 0; k < cows; k++) {
      const showSpot = index === 0 && k < 3;
      const x = showSpot ? cx + [-5, 2.5, 7][k] : range(px0 + 2.5, px1 - 2.5);
      const z = showSpot ? cz + [5.5, 3.5, 8][k] : range(pz0 + 2.5, pz1 - 2.5);
      add("cow", x, z, range(0, Math.PI * 2), { farm: index });
    }

    const hx0 = m > 0 ? cx + 17 : cx - 31;
    fields.push({ x0: hx0, z0: cz - 18, x1: hx0 + 14, z1: cz + 19, kind: "cropA", rows: "z" });
    const bales = index === 0 ? 7 : 4 + Math.floor(rnd() * 4);
    for (let k = 0; k < bales; k++) add("hay", range(hx0 + 2, hx0 + 12), range(cz - 15, cz + 16), range(0, Math.PI), { farm: index });
    if (index === 0) {
      add("hay", cx - 9, cz + 6, 0.4, { farm: index });
      add("hay", cx + 11, cz + 13, 1.3, { farm: index });
    }

    for (let x = cx - 22; x <= cx + 22; x += 3.4 + rnd() * 1.4) {
      if (Math.abs(x - (cx - m * 14)) < 3) continue;
      add(rnd() < 0.7 ? "treePine" : "treeRound", x, cz - 21 - rnd() * 1.6, range(0, 6.28), { farm: index, scale: range(0.85, 1.25) });
    }
    for (let k = 0; k < 3; k++) add("treeRound", cx - m * (14 + range(-5, 5)), cz - 2.5 - rnd() * 1.5, range(0, 6.28), { farm: index, scale: range(0.9, 1.3) });

    const fx0 = m > 0 ? cx - 31 : cx + 17;
    fields.push({ x0: fx0, z0: cz - 18, x1: fx0 + 14, z1: cz + 19, kind: pick(["cropB", "cropC", "cropD"]), rows: "x" });

    const toRoadZ = Math.abs(cz) > Math.abs(cx) * 0.4 ? 0 : null;
    if (toRoadZ === 0 && Math.abs(cz) < 60) lanes.push({ x0: cx - 1.6, z0: Math.min(cz - 9, 0), x1: cx + 1.6, z1: Math.max(cz - 9, 0) });
    else lanes.push({ x0: Math.min(cx, 0), z0: cz - 1.6 - 9, x1: Math.max(cx, 0), z1: cz + 1.6 - 9 });
  });

  for (const slot of fieldSlots) {
    for (let k = 0; k < 3; k++) {
      const x0 = slot.x - 32 + k * 21.3;
      fields.push({ x0: x0 + 0.8, z0: slot.z - 20, x1: x0 + 20.5, z1: slot.z + 20, kind: pick(CROPS), rows: rnd() < 0.5 ? "x" : "z" });
    }
    for (let x = slot.x - 30; x <= slot.x + 30; x += 4 + rnd() * 3) {
      add(rnd() < 0.5 ? "treePine" : "treeRound", x, slot.z - 22, range(0, 6.28), { scale: range(0.8, 1.2) });
    }
  }

  // The town center: houses facing the two roads, lawns, yard trees, and parked cars on the shoulders.
  const housesAt = [];
  for (const x of [-25, -17, -9, 9, 17, 25]) {
    housesAt.push({ x, z: -10, rot: 0 });
    housesAt.push({ x, z: 10, rot: Math.PI });
  }
  for (const z of [-25, -17, 17, 25]) {
    housesAt.push({ x: -10, z, rot: -Math.PI / 2 });
    housesAt.push({ x: 10, z, rot: Math.PI / 2 });
  }
  for (const h of housesAt) {
    if (h.x > 13 && h.z < -13) continue;
    add(rnd() < 0.5 ? "house" : "houseB", h.x + range(-0.6, 0.6), h.z, h.rot + range(-0.05, 0.05));
    lawns.push({ x0: h.x - 4, z0: h.z - 4, x1: h.x + 4, z1: h.z + 4 });
    if (rnd() < 0.7) add("treeRound", h.x + range(-3.5, 3.5), h.z + Math.sign(h.z || 1) * 3.6, range(0, 6.28), { scale: range(0.8, 1.1) });
  }
  const tower = { x: 19, z: -21 };
  lawns.push({ x0: 13, z0: -27, x1: 26, z1: -14 });
  for (let k = 0; k < 7; k++) {
    const side = rnd() < 0.5 ? -1 : 1;
    const along = range(14, 40) * (rnd() < 0.5 ? -1 : 1);
    if (rnd() < 0.5) add("car", along, side * 5, side > 0 ? 0 : Math.PI, { parked: true });
    else add("car", side * 5, along, side > 0 ? Math.PI / 2 : -Math.PI / 2, { parked: true });
  }

  // Cars driving the roads, on the right-hand lane, wrapping at the town's edge.
  const movers = [];
  for (let k = 0; k < 5; k++) {
    const axis = k % 2 === 0 ? "x" : "z";
    const dir = rnd() < 0.5 ? 1 : -1;
    movers.push({ axis, dir, at: range(-TOWN_EDGE, TOWN_EDGE), lane: dir * 1.75, speed: range(9, 13) });
    add(k === 3 ? "truck" : "car", 0, 0, 0, { mover: movers.length - 1 });
  }

  const farm0 = farmSlots[0];
  return {
    props,
    fields,
    pastures,
    yards,
    lawns,
    lanes,
    tower,
    movers,
    farmCount: farmSlots.length,
    attractStart: { x: farm0.x - 4, z: farm0.z + 13 },
    playStart: { x: farm0.x + 2, z: farm0.z + 30 },
  };
}
