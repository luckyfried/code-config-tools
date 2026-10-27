// The school: the flock simulation behind every fish in the tank, the instanced meshes it drives, and the soft
// shadow each fish throws on the sand.
import * as THREE from "three";
import { createFlock, addFish, stepFlock } from "../sim/boids.js";
import { speciesMesh } from "./fish.js";
import { sandHeight } from "./floor.js";

const TAU = Math.PI * 2;
const MAX = 60;

export function createSchool(catalog, quality) {
  const group = new THREE.Group();
  const kinds = catalog.species;
  const kindOf = new Map(kinds.map((s, i) => [s.id, i]));
  const env = {
    bounds: null,
    species: kinds.map((s) => ({ speed: s.speed, school: s.school, depthY: 3 })),
    time: 0, slow: 1, food: null, foodAlive: null, foodCount: 0, onEat: null,
  };
  const scaleBoost = quality.phone ? 1.12 : 1;
  let flock = createFlock(MAX);
  let ids = [];
  let look = []; // per fish: yaw, pitch, roll, bend, phase, grow
  const meshes = new Map();

  const shadowMat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: new THREE.Color(0x000000) } },
    transparent: true,
    depthWrite: false,
    vertexShader: /* glsl */ `
      attribute float iAlpha;
      varying float vA;
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vA = iAlpha;
        gl_Position = projectionMatrix * viewMatrix * modelMatrix * instanceMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying float vA;
      varying vec2 vUv;
      void main() {
        float d = length(vUv - 0.5) * 2.0;
        float a = smoothstep(1.0, 0.0, d);
        gl_FragColor = vec4(uColor, a * a * vA);
        #include <colorspace_fragment>
      }
    `,
  });
  const shadowGeo = new THREE.PlaneGeometry(1, 1);
  shadowGeo.rotateX(-Math.PI / 2);
  const shadowAlpha = new THREE.InstancedBufferAttribute(new Float32Array(MAX), 1);
  shadowAlpha.setUsage(THREE.DynamicDrawUsage);
  shadowGeo.setAttribute("iAlpha", shadowAlpha);
  const shadows = new THREE.InstancedMesh(shadowGeo, shadowMat, MAX);
  shadows.frustumCulled = false;
  shadows.renderOrder = -4;
  shadows.count = 0;
  group.add(shadows);

  function meshFor(spec) {
    let m = meshes.get(spec.id);
    if (!m) {
      m = speciesMesh(spec, MAX);
      meshes.set(spec.id, m);
      group.add(m);
    }
    return m;
  }

  function setBounds(bounds) {
    env.bounds = bounds;
    kinds.forEach((s, i) => { env.species[i].depthY = bounds.y0 + (bounds.y1 - bounds.y0) * s.depth; });
  }

  let seedN = 1;
  const rnd = () => ((seedN = (seedN * 16807) % 2147483647) / 2147483647);

  // Matches the flock to the person's fish list, keeping every fish that stays where it is. Fish that are new swim
  // in from the surface; on the first load they start spread through the water, each species near its own kind.
  function sync(fishList, { entering = true } = {}) {
    const b = env.bounds;
    const old = new Map(ids.map((id, i) => [id, i]));
    const next = createFlock(MAX);
    const nextLook = [];
    const centers = new Map();
    const list = fishList.slice(0, quality.maxFish);
    for (const f of list) {
      const spec = kinds[kindOf.get(f.sp)];
      if (!spec) continue;
      const k = kindOf.get(f.sp);
      const size = spec.size * (f.g || 1) * scaleBoost;
      const i = old.get(f.id);
      if (i !== undefined) {
        const j = addFish(next, k, size, flock.pos[i * 3], flock.pos[i * 3 + 1], flock.pos[i * 3 + 2], flock.seed[i]);
        next.vel.set(flock.vel.subarray(i * 3, i * 3 + 3), j * 3);
        nextLook.push({ ...look[i], grow: f.g || 1 });
        continue;
      }
      let x, y, z;
      if (entering) {
        x = b.x0 + (b.x1 - b.x0) * (0.2 + rnd() * 0.6);
        y = b.y1;
        z = b.z0 + (b.z1 - b.z0) * rnd();
      } else {
        if (!centers.has(k)) {
          centers.set(k, [b.x0 + (b.x1 - b.x0) * (0.15 + rnd() * 0.7), env.species[k].depthY, b.z0 + (b.z1 - b.z0) * (0.3 + rnd() * 0.4)]);
        }
        const c = centers.get(k);
        const spread = spec.school > 0.6 ? 1.2 : 3.2;
        x = THREE.MathUtils.clamp(c[0] + (rnd() - 0.5) * spread * 2, b.x0, b.x1);
        y = THREE.MathUtils.clamp(c[1] + (rnd() - 0.5) * spread, b.y0, b.y1);
        z = THREE.MathUtils.clamp(c[2] + (rnd() - 0.5) * spread, b.z0, b.z1);
      }
      const seed = (f.id * 0.6180339) % 1;
      const j = addFish(next, k, size, x, y, z, seed);
      const dir = seed > 0.5 ? 1 : -1;
      next.vel.set([dir * spec.speed * 0.6, entering ? -0.5 : 0, 0.1 * (rnd() - 0.5)], j * 3);
      nextLook.push({ yaw: dir > 0 ? Math.PI / 2 : -Math.PI / 2, pitch: 0, roll: 0, bend: 0, phase: seed * TAU, grow: f.g || 1 });
    }
    flock = next;
    ids = list.filter((f) => kindOf.has(f.sp)).map((f) => f.id);
    look = nextLook;
    for (const m of meshes.values()) m.count = 0;
  }

  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler(0, 0, 0, "YXZ");
  const p = new THREE.Vector3();
  const s = new THREE.Vector3();
  const counts = new Map();
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

  function update(dt, time, mood, food, hungryOf, eaten) {
    env.time = time;
    env.slow = mood.slow;
    env.food = food.pos;
    env.foodAlive = food.alive;
    env.foodCount = food.count;
    env.onEat = (i, k) => eaten.push(ids[i], k);
    for (let i = 0; i < flock.count; i++) flock.hungry[i] = hungryOf(ids[i]) ? 1 : 0;
    stepFlock(flock, dt, env);

    counts.clear();
    const shadowDay = 0.16 + 0.26 * mood.day + 0.14 * mood.lamp;
    for (let i = 0; i < flock.count; i++) {
      const spec = kinds[flock.kind[i]];
      const L = look[i];
      const vx = flock.vel[i * 3], vy = flock.vel[i * 3 + 1], vz = flock.vel[i * 3 + 2];
      const speed = Math.hypot(vx, vy, vz) || 1e-4;
      const yawT = Math.atan2(vx, vz);
      const k = Math.min(1, dt * 5);
      const dYaw = wrap(yawT - L.yaw) * k;
      L.yaw = wrap(L.yaw + dYaw);
      const yawRate = dt > 0 ? dYaw / dt : 0;
      L.bend += (THREE.MathUtils.clamp(yawRate * 0.11, -0.3, 0.3) - L.bend) * Math.min(1, dt * 6);
      L.pitch += (-Math.asin(THREE.MathUtils.clamp(vy / speed, -1, 1)) * 0.75 - L.pitch) * k;
      L.roll += (THREE.MathUtils.clamp(-yawRate * 0.12, -0.35, 0.35) - L.roll) * k;
      const eating = flock.eating[i] > 0 ? 1.6 : 1;
      L.phase = (L.phase + dt * TAU * spec.freq * (0.5 + 0.9 * speed / (spec.speed * 1.2)) * eating) % (TAU * 1000);
      const mesh = meshFor(spec);
      const slot = counts.get(spec.id) || 0;
      counts.set(spec.id, slot + 1);
      p.set(flock.pos[i * 3], flock.pos[i * 3 + 1], flock.pos[i * 3 + 2]);
      e.set(L.pitch, L.yaw, L.roll);
      q.setFromEuler(e);
      const size = flock.size[i];
      s.setScalar(size);
      m4.compose(p, q, s);
      mesh.setMatrixAt(slot, m4);
      const sw = mesh.geometry.attributes.iSwim;
      sw.array[slot * 3] = L.phase;
      sw.array[slot * 3 + 1] = L.bend;
      sw.array[slot * 3 + 2] = flock.seed[i];
      // shadow
      const ground = Math.max(sandHeight(p.x, p.z), sandHeight(p.x + Math.sin(L.yaw) * size * 0.5, p.z + Math.cos(L.yaw) * size * 0.5)) + 0.04;
      const lift = THREE.MathUtils.clamp((p.y - ground) / 7, 0, 1);
      e.set(0, L.yaw, 0);
      q.setFromEuler(e);
      p.y = ground;
      const spread = 1 + lift * 1.2;
      s.set(size * spec.body.height * 2.4 * spread, 1, size * 1.15 * spread);
      m4.compose(p, q, s);
      shadows.setMatrixAt(i, m4);
      shadowAlpha.array[i] = shadowDay * (1 - lift * 0.75);
    }
    for (const [id, mesh] of meshes) {
      mesh.count = counts.get(id) || 0;
      if (mesh.count) {
        mesh.instanceMatrix.needsUpdate = true;
        mesh.geometry.attributes.iSwim.needsUpdate = true;
      }
    }
    shadows.count = flock.count;
    shadows.instanceMatrix.needsUpdate = true;
    shadowAlpha.needsUpdate = true;
    shadowMat.uniforms.uColor.value.copy(mood.deep).multiplyScalar(0.25);
  }

  function positionOf(id, out) {
    const i = ids.indexOf(id);
    if (i < 0) return null;
    return out.set(flock.pos[i * 3], flock.pos[i * 3 + 1], flock.pos[i * 3 + 2]);
  }

  function sizeOf(id) {
    const i = ids.indexOf(id);
    return i < 0 ? 0 : flock.size[i];
  }

  function regrow(fishList) {
    for (const f of fishList) {
      const i = ids.indexOf(f.id);
      if (i >= 0) flock.size[i] = kinds[flock.kind[i]].size * (f.g || 1) * scaleBoost;
    }
  }

  return { group, sync, update, setBounds, positionOf, sizeOf, regrow, count: () => flock.count, ids: () => ids };
}
