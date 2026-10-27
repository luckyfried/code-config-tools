// The cubes and their motion. A move's trace slides every cube in 90 ms (inside the 110 ms a swipe is given) with a
// lean into the motion; a pair that meets squashes into itself, the cube it makes pops 15% wider and settles while it
// flashes past the bloom threshold and throws six sparks off its struck side; the new cube drops a short way into its
// own cell and bounces, landing by the time the slide ends. Every cube keeps its number on its top face in every
// frame: of a pair that meets, the one sliding in dips under the other, so the face in front is never crossed.
// Each lit cube spills a soft pool of its own light onto the tray round its foot, which is what makes the board glow.
// Reduced motion: cubes cross-fade in 100 ms, with no flash and no lean.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { glowTexture, poolTexture } from "./fx.js";
import { cubeMaterial, haloMaterial, labelMaterial, poolMaterial, tuneCube } from "./materials.js";
import { stepOf } from "./tokens.js";
import { CUBE, cellX, cellZ } from "./tray.js";

export const SLIDE = 0.09;
const LEAN = THREE.MathUtils.degToRad(6);
const DROP_FROM = 0.3;
const DROP_TIME = 0.06;
const DROP_AFTER = 0.045; // seconds into a slide when the new cube starts down: its cell is clear by then
const DIVE = 0.14; // how far the cube sliding into a merge dips under the one it meets
const FLASH_POWER = 0.6;
const FLASH_TIME = 0.24;
const HERO_GLOW = 0.55;
const WHITE = new THREE.Color(1, 1, 1);
const heroAt = new THREE.Vector3();

const easeOut = (u) => 1 - (1 - u) ** 3;
const easeInOut = (u) => (u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2);
const clamp01 = (u) => Math.min(1, Math.max(0, u));
/** An underdamped spring's settle from `from` to `to` after t seconds. */
function spring(t, from, to, hz = 5, zeta = 0.42) {
  const w = 2 * Math.PI * hz;
  const wd = w * Math.sqrt(1 - zeta * zeta);
  const e = Math.exp(-zeta * w * t);
  return to + (from - to) * e * (Math.cos(wd * t) + ((zeta * w) / wd) * Math.sin(wd * t));
}

const heightOf = (step) => 0.66 + step * 0.0125;

export function createCubes({ parent, labels, sparks, flares, lights }) {
  const geos = new Map();
  const labelGeo = new THREE.PlaneGeometry(0.66, 0.66).rotateX(-Math.PI / 2);
  const poolGeo = new THREE.PlaneGeometry(CUBE * 2.1, CUBE * 2.1).rotateX(-Math.PI / 2);
  const cubes = new Map();
  let tokens = null;
  let size = 4;
  let reduced = false;
  let dim = 0;
  let hero = null;
  let flashOn = true;
  let haloGain = 1; // the halos carry more of the glow where there is no bloom pass
  const dying = new Set();
  const spare = [];

  function geometry(step) {
    if (!geos.has(step)) {
      const h = heightOf(step);
      geos.set(step, new RoundedBoxGeometry(CUBE, h, CUBE, 4, 0.12).translate(0, h / 2, 0));
    }
    return geos.get(step);
  }

  /** A cube's meshes and materials. Cubes that leave the board are kept and dressed again, never rebuilt mid-move. */
  function build() {
    const root = new THREE.Group();
    const pivot = new THREE.Group();
    root.add(pivot);
    const mat = cubeMaterial(tokens, 0);
    // Drawn in layers: the glow (halo and pool), then every cube's body, then the faces, so no glow ever lies over a
    // cube and a face is only ever hidden by a cube in front of it.
    const body = new THREE.Mesh(geometry(0), mat);
    body.renderOrder = 2;
    const labelMat = labelMaterial(labels.texture(2));
    const label = new THREE.Mesh(labelGeo, labelMat);
    label.renderOrder = 3;
    pivot.add(body, label);
    // The light a high cube throws round itself: hidden behind the cube in the middle, so it rims it.
    const haloMat = haloMaterial(glowTexture());
    const halo = new THREE.Sprite(haloMat);
    halo.renderOrder = 1;
    root.add(halo);
    const poolMat = poolMaterial(poolTexture());
    const pool = new THREE.Mesh(poolGeo, poolMat);
    pool.renderOrder = 1;
    root.add(pool);
    return { root, pivot, body, label, mat, labelMat, halo, haloMat, pool, poolMat };
  }

  function make(tile) {
    const step = stepOf(tile.value);
    const parts = spare.pop() ?? build();
    const { root, pivot, body, label, mat, labelMat, halo, pool } = parts;
    tuneCube(mat, tokens, step);
    if (tile.value > 4096) mat.color.copy(tokens.beyond);
    mat.opacity = 1;
    body.geometry = geometry(step);
    labelMat.map = labels.texture(tile.value);
    labelMat.opacity = 1;
    label.position.y = heightOf(step) + 0.004;
    label.visible = true;
    halo.position.y = heightOf(step) * 0.45;
    pool.position.y = 0.006;
    pivot.scale.set(1, 1, 1);
    pivot.rotation.set(0, 0, 0);
    root.visible = true;
    root.renderOrder = 0;
    parent.add(root);
    const cube = {
      ...parts,
      id: tile.id,
      value: tile.value,
      step,
      r: tile.r,
      c: tile.c,
      x: cellX(tile.c, size),
      z: cellZ(tile.r, size),
      slide: null, // { fx, fz, tx, tz, t, dir }
      squash: null, // { t, dir }
      pop: null, // { t }
      drop: null, // { t, delay }
      nudge: null, // { t, dir }
      sink: null, // { t, delay }
      rise: null, // { t, down }
      fade: null, // { t, from, to, delay, dur }
      leader: null, // the cube this one slides into, which it dips under
      into: null, // the id of the cube a merging pair becomes
      flash: 0,
      gone: false,
      dieAt: Infinity,
      age: 0,
    };
    root.position.set(cube.x, 0, cube.z);
    cubes.set(tile.id, cube);
    return cube;
  }

  function remove(cube) {
    // A cube leaves once: its meshes go back to the spares, and a second removal would hand them to two cubes.
    if (cube.gone) return;
    cube.gone = true;
    cube.root.removeFromParent();
    const { root, pivot, body, label, mat, labelMat, halo, haloMat, pool, poolMat } = cube;
    spare.push({ root, pivot, body, label, mat, labelMat, halo, haloMat, pool, poolMat });
    cubes.delete(cube.id);
    dying.delete(cube);
  }

  /**
   * Where the winning cube hangs: the open cell nearest the middle of the board, best with the cell behind it open too
   * (so nothing behind is covered), and nearer the front on a tie. A full board keeps it over its own cell.
   */
  function openCell(cube) {
    const taken = new Set();
    for (const c of cubes.values()) if (!c.gone && !dying.has(c) && c !== cube) taken.add(`${c.r},${c.c}`);
    const mid = (size - 1) / 2;
    let best = [cube.r, cube.c];
    let bestScore = Infinity;
    for (let r = 0; r < size; r += 1) {
      for (let c = 0; c < size; c += 1) {
        if (taken.has(`${r},${c}`)) continue;
        const behind = r > 0 && taken.has(`${r - 1},${c}`) ? 1.5 : 0;
        const score = Math.hypot(r - mid, c - mid) + behind - r * 0.01;
        if (score < bestScore) {
          bestScore = score;
          best = [r, c];
        }
      }
    }
    return best;
  }

  function dropSpares() {
    for (const parts of spare.splice(0)) {
      parts.mat.dispose();
      parts.labelMat.dispose();
      parts.haloMat.dispose();
      parts.poolMat.dispose();
    }
  }

  function setOpacity(cube, a) {
    cube.mat.opacity = a;
    cube.labelMat.opacity = a;
  }

  function finish(cube) {
    if (cube.slide) {
      cube.x = cube.slide.tx;
      cube.z = cube.slide.tz;
      cube.slide = null;
    }
    cube.squash = null;
    cube.pop = null;
    cube.drop = null;
    cube.root.visible = true;
    cube.nudge = null;
    if (cube.fade) {
      setOpacity(cube, cube.fade.to);
      cube.fade = null;
    }
    cube.age = 10;
  }

  function lookFor(cube) {
    const look = tokens.cubes[cube.step];
    const isHero = cube === hero;
    const k = isHero ? 1 : 1 - 0.62 * dim;
    const base = cube.value > 4096 ? tokens.beyond : look.color;
    cube.mat.color.copy(base).multiplyScalar(k);
    // The flash is a short, hot pulse of the cube's own glow, just past the bloom threshold, never a white-out.
    const flash = flashOn ? cube.flash ** 1.6 : 0;
    const heat = cube.value > 4096 ? tokens.beyond : look.heat;
    cube.mat.emissive.copy(heat).lerp(WHITE, flash * 0.12);
    const glow = tokens.glowPower * look.glow;
    // A cube that already glows needs less flash to read as one, and more would bloom over its own number.
    const pulse = flash * FLASH_POWER * (1 - 0.75 * look.glow);
    cube.mat.emissiveIntensity = isHero ? Math.max(HERO_GLOW * (flashOn ? 1 : 0.6), glow) + pulse : glow * (1 - 0.88 * dim) + pulse;
    cube.labelMat.color.setScalar(isHero ? 1 : 1 - 0.45 * dim);
    const seen = cube.root.visible ? cube.mat.opacity : 0;
    // The halo: added light round a high cube on an evening stage; on a pale stage, a warm haze laid over the room.
    const halo = isHero ? 0 : haloGain * tokens.haloPower * (tokens.haloOver ? look.glow ** 1.3 : Math.max(0, look.glow - 0.15)) * (1 - 0.9 * dim) * seen;
    cube.halo.visible = halo > 0.004;
    if (cube.halo.visible) {
      cube.haloMat.blending = tokens.haloOver ? THREE.NormalBlending : THREE.AdditiveBlending;
      cube.haloMat.color.copy(heat).multiplyScalar(tokens.haloOver ? 1 : halo);
      cube.haloMat.opacity = tokens.haloOver ? Math.min(0.9, halo) : 1;
      cube.halo.scale.setScalar(CUBE * (tokens.haloOver ? 2.8 + 1.6 * look.glow : (1.7 + 1.1 * look.glow) * (haloGain > 1 ? 1.3 : 1)));
    }
    // The pool: the cube's light spilled on the dark tray round its foot, climbing with the ramp and with a flash.
    const pool = isHero ? 0 : tokens.poolPower * (look.glow + flash * 0.9) * (1 - 0.85 * dim) * seen;
    cube.pool.visible = pool > 0.01;
    if (cube.pool.visible) cube.poolMat.color.copy(heat).multiplyScalar(pool);
  }

  return {
    configure(next) {
      tokens = next.tokens ?? tokens;
      if (next.size !== undefined) size = next.size;
      if (next.reduced !== undefined) reduced = next.reduced;
      if (next.flash !== undefined) flashOn = next.flash;
      if (next.bloom !== undefined) haloGain = next.bloom ? 1 : 1.6;
    },
    /** Rebuilds the materials and faces after a theme or label change. */
    restyle() {
      dropSpares();
      for (const cube of cubes.values()) {
        tuneCube(cube.mat, tokens, cube.step);
        cube.labelMat.map = labels.texture(cube.value);
      }
    },
    get count() {
      return cubes.size;
    },
    /** Puts exactly the board's cubes on the tray; `intro` drops them in one after another. */
    sync(board, { intro = false } = {}) {
      flares.release();
      for (const cube of [...cubes.values()]) remove(cube);
      const order = [...board.tiles].sort((a, b) => a.r + a.c - (b.r + b.c));
      order.forEach((tile, i) => {
        const cube = make(tile);
        if (intro) {
          if (reduced) cube.fade = { t: 0, from: 0, to: 1, delay: i * 0.02, dur: 0.1 };
          else cube.drop = { t: 0, delay: i * 0.03, intro: true };
          if (reduced) setOpacity(cube, 0);
          else cube.root.visible = false;
        }
      });
    },
    /** Shows every part of every cube for the compile pass; `false` hides the glows again. */
    warm(on) {
      for (const cube of cubes.values()) {
        cube.root.visible = true;
        cube.halo.visible = on;
        cube.pool.visible = on;
      }
    },
    snap() {
      for (const cube of [...dying]) remove(cube);
      for (const cube of cubes.values()) finish(cube);
    },
    /** Animates one move: the trace, its merges, and the cube that appears after it. */
    play(result, spawned, dir) {
      this.snap();
      const made = new Map(result.merges.map((m) => [m.id, m]));
      const leaders = new Map(result.merges.map((m) => [m.from[1], m.from[0]]));
      for (const e of result.trace) {
        const cube = cubes.get(e.id);
        if (!cube) continue;
        const tx = cellX(e.to[1], size);
        const tz = cellZ(e.to[0], size);
        const moves = tx !== cube.x || tz !== cube.z;
        if (reduced) {
          if (moves || e.into) cube.fade = { t: 0, from: 1, to: 0, delay: 0, dur: 0.05, jump: e.into ? null : [tx, tz] };
        } else if (moves) {
          cube.slide = { fx: cube.x, fz: cube.z, tx, tz, t: 0, dir };
        }
        cube.r = e.to[0];
        cube.c = e.to[1];
        if (e.into) {
          cube.into = e.into;
          cube.leader = leaders.has(e.id) ? cubes.get(leaders.get(e.id)) ?? null : null;
          if (!reduced) cube.squash = { t: -SLIDE, dir };
          cube.dieAt = reduced ? 0.05 : SLIDE + 0.04;
          cube.age = 0;
          dying.add(cube);
        }
      }
      for (const m of made.values()) {
        const cube = make(m);
        cube.age = 0;
        if (reduced) {
          setOpacity(cube, 0);
          cube.fade = { t: 0, from: 0, to: 1, delay: 0.05, dur: 0.05 };
        } else {
          cube.root.visible = false;
          cube.pop = { t: -SLIDE - 0.04, dir };
        }
      }
      if (spawned) {
        const cube = make(spawned);
        if (reduced) {
          setOpacity(cube, 0);
          cube.fade = { t: 0, from: 0, to: 1, delay: 0.05, dur: 0.05 };
        } else {
          cube.root.visible = false;
          cube.drop = { t: 0, delay: DROP_AFTER };
        }
      }
    },
    /** Nothing moved: every cube shoves toward the wall and springs back. */
    bump(dir) {
      if (reduced) return;
      for (const cube of cubes.values()) cube.nudge = { t: 0, dir };
    },
    /** Sinks every cube into the tray, from the middle out; resolves when they are gone. */
    clear() {
      this.snap();
      const all = [...cubes.values()];
      if (all.length === 0) return Promise.resolve();
      all.forEach((cube) => {
        const d = Math.hypot(cube.x, cube.z);
        if (reduced) cube.fade = { t: 0, from: 1, to: 0, delay: 0, dur: 0.1 };
        else cube.sink = { t: 0, delay: d * 0.04 };
      });
      return new Promise((resolve) => setTimeout(() => {
        for (const cube of [...cubes.values()]) remove(cube);
        resolve();
      }, reduced ? 140 : 520));
    },
    /** The 2048 moment: the winning cube rises and turns once at full glow while the rest dim. */
    celebrate(id) {
      this.snap();
      hero = cubes.get(id) ?? null;
      if (hero) {
        const [tr, tc] = openCell(hero);
        // Pulled a little toward the middle, so its corners stay inside the rim as it turns.
        hero.rise = { t: 0, down: false, tx: cellX(tc, size) * 0.9, tz: cellZ(tr, size) * 0.9 };
        hero.flash = 1;
        hero.root.renderOrder = 2;
      }
    },
    settle() {
      flares.release();
      if (hero?.rise) hero.rise = { t: 0, down: true, from: hero.root.position.clone(), scale: hero.pivot.scale.x };
      setTimeout(() => {
        hero = null;
      }, 500);
    },
    heroPosition(out) {
      if (!hero) return null;
      return hero.root.getWorldPosition(out);
    },
    setDim(value) {
      dim = value;
    },
    get busy() {
      for (const cube of cubes.values()) if (cube.slide || cube.squash || cube.drop || cube.fade || cube.pop) return true;
      return false;
    },
    update(dt) {
      for (const cube of [...cubes.values()]) {
        if (cube.gone) continue;
        cube.age += dt;
        if (cube.age >= cube.dieAt) {
          remove(cube);
          continue;
        }
        let x = cube.x;
        let z = cube.z;
        let y = 0;
        let sx = 1;
        let sy = 1;
        let sz = 1;
        let lean = 0;
        let leanDir = null;

        if (cube.slide) {
          const s = cube.slide;
          s.t += dt;
          const u = clamp01(s.t / SLIDE);
          const e = easeOut(u);
          x = s.fx + (s.tx - s.fx) * e;
          z = s.fz + (s.tz - s.fz) * e;
          leanDir = s.dir;
          if (u < 1) lean = LEAN * Math.sin(Math.PI * Math.min(1, u * 1.15));
          else {
            const after = s.t - SLIDE;
            lean = -LEAN * 0.3 * Math.exp(-after / 0.05) * Math.sin((2 * Math.PI * after) / 0.14);
            if (after > 0.22) {
              cube.x = s.tx;
              cube.z = s.tz;
              cube.slide = null;
            }
          }
        }

        if (cube.squash) {
          const q = cube.squash;
          q.t += dt;
          if (q.t > 0) {
            const u = clamp01(q.t / 0.045);
            const along = 1 - 0.3 * u;
            const across = 1 + 0.12 * u;
            if (q.dir === "left" || q.dir === "right") {
              sx = along;
              sz = across;
            } else {
              sz = along;
              sx = across;
            }
            sy = 1 - 0.08 * u;
          }
        }

        if (cube.leader) {
          // The cube sliding into a merge dips under the one it meets as they close, so the two top faces never
          // cross: the one in front keeps its number whole, and the other's shows until the front one covers it.
          const lp = cube.leader.gone ? null : cube.leader.root.position;
          const d = lp ? Math.hypot(x - lp.x, z - lp.z) : 0;
          y -= DIVE * (1 - clamp01(d / CUBE));
        }

        if (cube.pop) {
          const p = cube.pop;
          p.t += dt;
          if (p.t < 0) {
            cube.root.visible = false;
          } else {
            if (!cube.root.visible) {
              cube.root.visible = true;
              cube.flash = 1;
              // The pair it was made from goes in the same frame, so its face is the only one in the cell.
              for (const d of [...dying]) if (d.into === cube.id) remove(d);
              const look = tokens.cubes[cube.step];
              if (flashOn) {
                // The borrowed light is for the neighbors; a cube that glows by itself gets less, so its face never whites out.
                lights.flash(cube.x, cube.z, look.color, (2.2 + cube.step * 0.25) * (1 - 0.7 * look.glow));
                flares.flare(cube.x, 0.14, cube.z, look.heat, 0.8 + cube.step * 0.03, 0.3 + 0.7 * Math.min(1, cube.step / 8));
              }
              sparks.puff(cube.x, cube.z, p.dir, look.heat, tokens.sparkPower, heightOf(cube.step));
            }
            // 15% wider at the peak but only 6% taller, so the popped cube never rises over the face behind it.
            const s = p.t < 0.06 ? 1 + 0.15 * easeOut(p.t / 0.06) : spring(p.t - 0.06, 1.15, 1, 6, 0.5);
            sx *= s;
            sy *= 1 + (s - 1) * 0.4;
            sz *= s;
            if (p.t > 0.5) cube.pop = null;
          }
        }

        if (cube.drop) {
          // A short fall straight down into its own cell, a squash on landing, and a quick settle.
          const d = cube.drop;
          d.t += dt;
          const t = d.t - d.delay;
          if (t < 0) cube.root.visible = false;
          else {
            cube.root.visible = true;
            if (t < DROP_TIME) {
              const u = t / DROP_TIME;
              y = DROP_FROM * (1 - u * u);
              const grow = d.intro ? 0.8 + 0.2 * u : 1;
              sy *= 1.05 * grow;
              sx *= 0.97 * grow;
              sz *= 0.97 * grow;
            } else {
              const after = t - DROP_TIME;
              const squash = spring(after, -0.12, 0, 7, 0.45);
              sy *= 1 + squash;
              sx *= 1 - squash * 0.45;
              sz *= 1 - squash * 0.45;
              if (after > 0.32) cube.drop = null;
            }
          }
        }

        if (cube.nudge) {
          const n = cube.nudge;
          n.t += dt;
          const amount = n.t < 0.05 ? 0.07 * easeOut(n.t / 0.05) : spring(n.t - 0.05, 0.07, 0, 6, 0.4);
          const dx = n.dir === "left" ? -1 : n.dir === "right" ? 1 : 0;
          const dz = n.dir === "up" ? -1 : n.dir === "down" ? 1 : 0;
          x += dx * amount;
          z += dz * amount;
          leanDir = n.dir;
          lean = amount * 1.6;
          if (n.t > 0.6) cube.nudge = null;
        }

        if (cube.sink) {
          const s = cube.sink;
          s.t += dt;
          const u = clamp01((s.t - s.delay) / 0.3);
          y -= heightOf(cube.step) * 1.08 * easeInOut(u);
          sx *= 1 - 0.08 * u;
          sz *= 1 - 0.08 * u;
        }

        if (cube.rise) {
          // The winning cube lifts off its cell and floats to the open cell nearest the middle, turns once, and holds
          // there at full glow: over an empty socket, so it covers no number and stays inside the stage on a phone.
          const r = cube.rise;
          r.t += dt;
          if (!r.down) {
            const e = easeInOut(clamp01(r.t / 0.8));
            x += (r.tx - x) * e;
            z += (r.tz - z) * e;
            y += 0.42 * e + (r.t > 0.8 ? Math.sin((r.t - 0.8) * 2.2) * 0.03 : 0);
            const s = 1 + 0.03 * e;
            sx *= s;
            sy *= s;
            sz *= s;
            cube.pivot.rotation.y = Math.PI * 2 * easeInOut(clamp01((r.t - 0.15) / 1.35));
            cube.flash = Math.max(0.12, cube.flash - dt / 0.8);
            if (flashOn) flares.hold(heroAt.set(x, y + heightOf(cube.step) * 0.6, z - 0.25), tokens.cubes[cube.step].color);
          } else {
            flares.release();
            const e = easeInOut(clamp01(r.t / 0.45));
            const from = r.from ?? new THREE.Vector3(x, 0, z);
            x = from.x + (x - from.x) * e;
            z = from.z + (z - from.z) * e;
            y += from.y * (1 - e);
            const s = (r.scale ?? 1) + (1 - (r.scale ?? 1)) * e;
            sx *= s;
            sy *= s;
            sz *= s;
            cube.pivot.rotation.y *= 1 - e;
            if (e >= 1) {
              cube.rise = null;
              cube.pivot.rotation.y = 0;
              cube.root.renderOrder = 0;
            }
          }
        }

        if (cube.fade) {
          const f = cube.fade;
          f.t += dt;
          const u = clamp01((f.t - f.delay) / f.dur);
          setOpacity(cube, f.from + (f.to - f.from) * u);
          if (u >= 1) {
            if (f.jump) {
              cube.x = f.jump[0];
              cube.z = f.jump[1];
              x = cube.x;
              z = cube.z;
              cube.fade = { t: 0, from: 0, to: 1, delay: 0, dur: 0.05 };
            } else cube.fade = null;
          }
        }

        cube.root.position.set(x, y, z);
        cube.pool.position.y = 0.006 - y;
        cube.pivot.scale.set(sx, sy, sz);
        cube.pivot.rotation.x = 0;
        cube.pivot.rotation.z = 0;
        if (leanDir && lean) {
          if (leanDir === "right") cube.pivot.rotation.z = -lean;
          else if (leanDir === "left") cube.pivot.rotation.z = lean;
          else if (leanDir === "down") cube.pivot.rotation.x = lean;
          else cube.pivot.rotation.x = -lean;
        }
        if (cube.flash > 0 && cube !== hero) cube.flash = Math.max(0, cube.flash - dt / FLASH_TIME);
        lookFor(cube);
      }
    },
  };
}
