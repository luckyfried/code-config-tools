// What the storm can lift and what happens to it: anything inside the funnel's reach that the storm is big enough for
// eases into orbit along a spiral (squashing and stretching as it leaves the ground, spinning up), climbs the funnel,
// and is flung out on an arc that bounces where it lands. Cows land legs-up. Cars throw sparks. Barns and houses come
// apart into planks that join the orbit. Driving cars move along the roads until the storm takes them.
import * as THREE from "three";
import { MeshSurfaceSampler } from "three/addons/math/MeshSurfaceSampler.js";
import { PLANKS } from "../scene/town.js";
import { TOWN_EDGE } from "./generation.js";

// Mass in tons, the storm level that can lift it, its footprint radius, and the words for the damage report.
export const KINDS = {
  fence: { mass: 0.1, level: 1, r: 1.0, word: "fence", words: "fences" },
  hay: { mass: 0.3, level: 1, r: 0.7, word: "hay bale", words: "hay bales" },
  cow: { mass: 0.7, level: 2, r: 0.9, word: "cow", words: "cows" },
  treeRound: { mass: 1.2, level: 2, r: 1.0, word: "tree", words: "trees", group: "tree" },
  treePine: { mass: 1.2, level: 2, r: 1.0, word: "tree", words: "trees", group: "tree" },
  car: { mass: 1.4, level: 3, r: 1.3, word: "car", words: "cars" },
  truck: { mass: 2.2, level: 3, r: 1.5, word: "truck", words: "trucks" },
  silo: { mass: 6, level: 4, r: 1.6, word: "silo", words: "silos" },
  house: { mass: 18, level: 4, r: 2.6, word: "house", words: "houses", group: "house" },
  houseB: { mass: 18, level: 4, r: 2.6, word: "house", words: "houses", group: "house" },
  barn: { mass: 25, level: 4, r: 3.6, word: "barn", words: "barns" },
};
export const LEVEL_MASS = [0, 2, 8, 20];

export function levelFor(mass) {
  let level = 1;
  for (let i = 1; i < LEVEL_MASS.length; i++) if (mass >= LEVEL_MASS[i]) level = i + 1;
  return level;
}

// 0 for a fresh storm, 1 for one that has eaten a farm or two; it grows fastest early.
export function growthFor(mass) {
  return Math.min(1, Math.pow(mass / 70, 0.55));
}

const CELL = 10;
const GRAVITY = 20;

export function createLift({ town, meshes, funnel, sparks, events }) {
  const items = [];
  const grid = new Map();
  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const qSpin = new THREE.Quaternion();
  const e = new THREE.Euler();
  const v = new THREE.Vector3();
  const sc = new THREE.Vector3();
  const axisP = new THREE.Vector3();
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  const active = [];
  const touched = new Set();

  // Sample points on the barn and house walls once, for where their planks start.
  const samples = {};
  for (const type of ["barn", "house", "houseB"]) {
    if (!meshes.geometries[type]) continue;
    const sampler = new MeshSurfaceSampler(new THREE.Mesh(meshes.geometries[type])).build();
    const pts = [];
    for (let i = 0; i < 48; i++) {
      const p = new THREE.Vector3();
      sampler.sample(p);
      pts.push(p);
    }
    samples[type] = pts;
  }
  const plankColors = {};
  let nextPlank = 0;

  const indexOf = {};
  for (const p of town.props) {
    const kind = KINDS[p.type];
    const index = indexOf[p.type] || 0;
    indexOf[p.type] = index + 1;
    items.push({
      ...p,
      kind,
      mesh: meshes.meshes[p.type],
      index,
      scale: p.scale || 1,
      state: "stand",
      home: { x: p.x, z: p.z, rot: p.rot },
      moverHome: p.mover,
    });
  }

  function cellKey(x, z) {
    return `${Math.floor(x / CELL)},${Math.floor(z / CELL)}`;
  }
  function rebuildGrid() {
    grid.clear();
    for (const it of items) {
      if (it.mover !== undefined || it.state !== "stand") continue;
      const k = cellKey(it.x, it.z);
      if (!grid.has(k)) grid.set(k, []);
      grid.get(k).push(it);
    }
  }

  function writeStanding(it) {
    q.setFromEuler(e.set(0, it.rot, 0));
    m4.compose(v.set(it.x, 0, it.z), q, sc.setScalar(it.scale));
    it.mesh.setMatrixAt(it.index, m4);
    touched.add(it.mesh);
  }
  function setStand(it, value) {
    const a = it.mesh.geometry.getAttribute("aStand");
    a.array[it.index] = value;
    a.needsUpdate = true;
  }

  function startLift(it, now, level) {
    it.state = "rise";
    it.t = 0;
    it.rise = 0.7 + Math.min(1.4, it.kind.mass * 0.05);
    it.orbitFor = 2.6 + Math.random() * 2.2 + Math.min(2, it.kind.mass * 0.05);
    it.hMax = Math.min(0.92, 0.42 + Math.random() * 0.45 - it.kind.mass * 0.004);
    it.h0 = 0.04 + Math.random() * 0.08;
    const fp = funnel.shape.uFunnelPos.value;
    it.r0 = Math.hypot(it.x - fp.x, it.z - fp.z);
    it.a = Math.atan2(it.z - fp.z, it.x - fp.x);
    it.y0 = it.y0 || 0;
    it.spinAxis = new THREE.Vector3(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
    it.spin = 0;
    it.spinRate = 2 + Math.random() * 4 - Math.min(1.5, it.kind.mass * 0.06);
    it.base = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, it.rot, 0));
    it.pos = new THREE.Vector3(it.x, it.y0, it.z);
    it.vel = new THREE.Vector3();
    it.bounces = 0;
    if (it.mesh !== meshes.planks) setStand(it, 0);
    active.push(it);
    if (it.plank) return;
    if (it.mover !== undefined) it.mover = undefined;
    events.lifted(it, level);
  }

  function breakApart(it, now, level) {
    it.state = "gone";
    it.mesh.setMatrixAt(it.index, zero);
    touched.add(it.mesh);
    setStand(it, 0);
    events.lifted(it, level);
    const pts = samples[it.type] || [];
    const n = it.type === "barn" ? 40 : 26;
    const cos = Math.cos(it.rot);
    const sin = Math.sin(it.rot);
    const palette = plankColors[it.type] || [new THREE.Color(1, 1, 1)];
    for (let k = 0; k < n; k++) {
      const p = pts[k % pts.length];
      const index = nextPlank;
      nextPlank = (nextPlank + 1) % PLANKS;
      const plank = {
        type: "plank",
        plank: true,
        kind: { mass: 0, level: 1, r: 0.5 },
        mesh: meshes.planks,
        index,
        scale: 0.8 + Math.random() * 0.6,
        x: it.x + p.x * cos + p.z * sin,
        z: it.z - p.x * sin + p.z * cos,
        y0: p.y,
        rot: it.rot + (Math.random() - 0.5) * 0.6,
      };
      meshes.planks.setColorAt(index, palette[k % palette.length]);
      meshes.planks.instanceColor.needsUpdate = true;
      const old = active.findIndex((a) => a.plank && a.index === index);
      if (old >= 0) active.splice(old, 1);
      startLift(plank, now, level);
      plank.rise = 0.35 + Math.random() * 0.9 + (p.y / 8) * 0.4;
      plank.spinRate = 4 + Math.random() * 6;
    }
    sparks.emit(it.x, 2, it.z, 30, 7);
  }

  const api = {
    items,
    active,
    setPlankColors(tokens) {
      const c = tokens.colors;
      plankColors.barn = [c.propBarn, c.propBarn, c.propTrim, c.propRoof, c.propBarn, c.propWood];
      plankColors.house = [c.propHouse, c.propHouse, c.propRoof, c.propTrim, c.propWood];
      plankColors.houseB = [c.propHouseB, c.propHouseB, c.propRoof, c.propTrim, c.propWood];
    },
    // Put every prop back where the town was generated, standing.
    reset() {
      active.length = 0;
      for (const it of items) {
        it.state = "stand";
        it.x = it.home.x;
        it.z = it.home.z;
        it.rot = it.home.rot;
        it.y0 = 0;
        it.mover = it.moverHome;
        writeStanding(it);
        setStand(it, 1);
      }
      for (let i = 0; i < PLANKS; i++) meshes.planks.setMatrixAt(i, zero);
      touched.add(meshes.planks);
      nextPlank = 0;
      rebuildGrid();
      api.flush();
    },
    // Cars on the roads.
    drive(dt) {
      for (const it of items) {
        if (it.mover === undefined || it.state !== "stand") continue;
        const mv = town.movers[it.mover];
        mv.at += mv.dir * mv.speed * dt;
        if (mv.at > TOWN_EDGE + 40) mv.at = -TOWN_EDGE - 40;
        if (mv.at < -TOWN_EDGE - 40) mv.at = TOWN_EDGE + 40;
        if (mv.axis === "x") {
          it.x = mv.at;
          it.z = mv.lane;
          it.rot = mv.dir > 0 ? 0 : Math.PI;
        } else {
          it.x = -mv.lane;
          it.z = mv.at;
          it.rot = mv.dir > 0 ? -Math.PI / 2 : Math.PI / 2;
        }
        writeStanding(it);
      }
    },
    // Take everything inside the reach that this level can lift.
    grab(now, level, reach) {
      const fp = funnel.shape.uFunnelPos.value;
      const span = Math.ceil((reach + 4) / CELL);
      const cx = Math.floor(fp.x / CELL);
      const cz = Math.floor(fp.z / CELL);
      for (let gx = cx - span; gx <= cx + span; gx++) {
        for (let gz = cz - span; gz <= cz + span; gz++) {
          const list = grid.get(`${gx},${gz}`);
          if (!list) continue;
          for (const it of list) {
            if (it.state !== "stand" || it.kind.level > level) continue;
            const d = Math.hypot(it.x - fp.x, it.z - fp.z);
            if (d > reach + it.kind.r * 0.6) continue;
            if (it.type === "barn" || it.type === "house" || it.type === "houseB") breakApart(it, now, level);
            else startLift(it, now, level);
          }
        }
      }
      for (const it of items) {
        if (it.mover === undefined || it.state !== "stand" || it.kind.level > level) continue;
        if (Math.hypot(it.x - fp.x, it.z - fp.z) <= reach + it.kind.r * 0.6) startLift(it, now, level);
      }
    },
    update(dt, boost) {
      for (let i = active.length - 1; i >= 0; i--) {
        const it = active[i];
        it.t += dt;
        if (it.state === "rise" || it.state === "orbit") {
          let h;
          let r;
          let squash = 0;
          let rise = 1;
          if (it.state === "rise") {
            const k = Math.min(1, it.t / it.rise);
            const ease = k * k * (3 - 2 * k);
            rise = ease;
            h = it.h0 * ease;
            const rOrbit = funnel.radius(h) * 1.15 + it.kind.r * 0.4;
            r = it.r0 + (rOrbit - it.r0) * ease;
            squash = Math.sin(k * Math.PI);
            it.spin += it.spinRate * ease * dt;
            if (k >= 1) {
              it.state = "orbit";
              it.t = 0;
            }
          } else {
            const k = Math.min(1, it.t / it.orbitFor);
            h = it.h0 + (it.hMax - it.h0) * (k * (2 - k));
            r = funnel.radius(h) * 1.15 + it.kind.r * 0.4;
            it.spin += it.spinRate * dt;
            if (k >= 1) {
              it.state = "fling";
              const w = (3.2 - 1.8 * h) * (1 + boost);
              const tangential = w * r;
              it.vel.set(-Math.sin(it.a) * tangential + Math.cos(it.a) * 7, 3 + Math.random() * 5, Math.cos(it.a) * tangential + Math.sin(it.a) * 7);
              it.vel.multiplyScalar(0.55);
            }
          }
          const w = (3.2 - 1.8 * h) * (1 + boost) * (0.4 + 0.6 * rise);
          it.a += w * dt;
          funnel.axis(h, axisP);
          const fp = funnel.shape.uFunnelPos.value;
          const cx = fp.x + (axisP.x - fp.x) * rise;
          const cz = fp.z + (axisP.z - fp.z) * rise;
          it.pos.set(cx + Math.cos(it.a) * r, it.y0 * (1 - rise) + axisP.y, cz + Math.sin(it.a) * r);
          qSpin.setFromAxisAngle(it.spinAxis, it.spin);
          q.copy(qSpin).multiply(it.base);
          const stretch = 1 + squash * 0.35;
          sc.set(it.scale / Math.sqrt(stretch), it.scale * stretch, it.scale / Math.sqrt(stretch));
          m4.compose(it.pos, q, sc);
          it.mesh.setMatrixAt(it.index, m4);
          touched.add(it.mesh);
          if ((it.type === "car" || it.type === "truck") && Math.random() < 0.5) sparks.emit(it.pos.x, it.pos.y, it.pos.z, 2, 2.5);
        } else if (it.state === "fling") {
          it.vel.y -= GRAVITY * dt;
          it.pos.addScaledVector(it.vel, dt);
          it.spin += it.spinRate * dt;
          const rest = it.type === "cow" ? 1.45 : it.plank ? 0.06 : 0.25;
          if (it.pos.y <= rest && it.vel.y < 0) {
            it.pos.y = rest;
            it.bounces++;
            if (!it.plank) events.landed(it);
            if (it.bounces >= 3 || Math.abs(it.vel.y) < 2) {
              it.state = "rest";
              const flip = it.type === "cow" ? Math.PI : it.plank ? 0 : Math.PI / 2;
              q.setFromEuler(e.set(flip, Math.random() * Math.PI * 2, it.type === "cow" ? 0 : (Math.random() - 0.5) * 0.4));
              sc.setScalar(it.scale);
              m4.compose(it.pos, q, sc);
              it.mesh.setMatrixAt(it.index, m4);
              touched.add(it.mesh);
              active.splice(i, 1);
              continue;
            }
            it.vel.y *= -0.38;
            it.vel.x *= 0.6;
            it.vel.z *= 0.6;
            it.spinRate *= 0.6;
            if (it.type === "car" || it.type === "truck") sparks.emit(it.pos.x, 0.3, it.pos.z, 14, 5);
          }
          qSpin.setFromAxisAngle(it.spinAxis, it.spin);
          q.copy(qSpin).multiply(it.base);
          sc.setScalar(it.scale);
          m4.compose(it.pos, q, sc);
          it.mesh.setMatrixAt(it.index, m4);
          touched.add(it.mesh);
        }
      }
    },
    flush() {
      for (const mesh of touched) mesh.instanceMatrix.needsUpdate = true;
      touched.clear();
    },
    nearest(from, level, maxD) {
      let best = null;
      let bestScore = Infinity;
      for (const it of items) {
        if (it.state !== "stand" || it.kind.level > level) continue;
        const d = Math.hypot(it.x - from.x, it.z - from.z);
        if (d > maxD) continue;
        const score = d - it.kind.mass * 1.5 - (it.kind.level === level ? 10 : 0);
        if (score < bestScore) {
          bestScore = score;
          best = it;
        }
      }
      return best;
    },
  };
  return api;
}
