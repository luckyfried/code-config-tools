// Food pellets that sink and wait on the sand, and pearls that fish drop: they sink, settle, and glint until a tap
// or the sweep gathers them.
import * as THREE from "three";
import { patchMaterial } from "./shading.js";
import { sandHeight } from "./floor.js";

const FOOD = 48;
const PEARLS = 48;
const FOOD_LIFE = 14;

export function createItems(pal, quality) {
  const group = new THREE.Group();

  // food
  const food = { pos: new Float32Array(FOOD * 3), alive: new Uint8Array(FOOD), count: FOOD };
  const foodVel = new Float32Array(FOOD);
  const foodAge = new Float32Array(FOOD);
  const foodSeed = new Float32Array(FOOD);
  const foodMat = patchMaterial(new THREE.MeshStandardMaterial({ color: pal.food, roughness: 0.6, emissive: pal.food, emissiveIntensity: 0.15 }), { caustic: 0.6, key: "food" });
  const foodMesh = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), foodMat, FOOD);
  foodMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  foodMesh.frustumCulled = false;
  foodMesh.count = 0;
  group.add(foodMesh);
  let foodNext = 0;

  // pearls
  const pearl = {
    pos: new Float32Array(PEARLS * 3), state: new Uint8Array(PEARLS), // 0 none, 1 sinking, 2 resting
    age: new Float32Array(PEARLS), vy: new Float32Array(PEARLS), value: new Uint16Array(PEARLS), ground: new Float32Array(PEARLS),
  };
  const pearlMat = new THREE.MeshStandardMaterial({ color: pal.pearl, roughness: 0.12, metalness: 0.25, envMapIntensity: 1.8, emissive: pal.pearl, emissiveIntensity: 0.12 });
  const pearlMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 16, 12), pearlMat, PEARLS);
  pearlMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  pearlMesh.frustumCulled = false;
  pearlMesh.count = 0;
  group.add(pearlMesh);

  // glints: camera-facing four-point stars over each resting pearl
  const quad = new THREE.PlaneGeometry(1, 1);
  const gGeo = new THREE.InstancedBufferGeometry();
  gGeo.index = quad.index;
  gGeo.setAttribute("position", quad.attributes.position);
  gGeo.setAttribute("uv", quad.attributes.uv);
  const gCenter = new THREE.InstancedBufferAttribute(new Float32Array(PEARLS * 3), 3);
  const gData = new THREE.InstancedBufferAttribute(new Float32Array(PEARLS * 2), 2);
  gCenter.setUsage(THREE.DynamicDrawUsage);
  gData.setUsage(THREE.DynamicDrawUsage);
  gGeo.setAttribute("iCenter", gCenter);
  gGeo.setAttribute("iData", gData);
  gGeo.instanceCount = 0;
  const gMat = new THREE.ShaderMaterial({
    uniforms: { uColor: { value: pal.pearl.clone() }, uTime: { value: 0 }, uScale: { value: 1 } },
    transparent: true,
    depthWrite: false,
    depthTest: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      attribute vec3 iCenter;
      attribute vec2 iData;
      uniform float uTime, uScale;
      varying vec2 vUv;
      varying float vA;
      void main() {
        vUv = uv - 0.5;
        float tw = 0.65 + 0.35 * sin(uTime * 3.0 + iData.x * 17.0);
        vA = iData.y * tw;
        vec4 mv = modelViewMatrix * vec4(iCenter, 1.0);
        float s = uScale * (0.55 + 0.25 * tw);
        float a = uTime * 0.6 + iData.x * 6.0;
        mat2 r = mat2(cos(a), -sin(a), sin(a), cos(a));
        mv.xy += r * position.xy * s;
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      varying vec2 vUv;
      varying float vA;
      void main() {
        vec2 p = abs(vUv) * 2.0;
        float star = max(smoothstep(0.08, 0.0, p.x * p.y * 3.0 + p.y * 0.04 + p.x * 0.04) * smoothstep(1.0, 0.0, p.x + p.y * 0.2),
                         smoothstep(0.08, 0.0, p.x * p.y * 3.0 + p.x * 0.04 + p.y * 0.04) * smoothstep(1.0, 0.0, p.y + p.x * 0.2));
        float core = smoothstep(0.35, 0.0, length(p));
        float a = (star * 0.9 + core * 0.8) * vA;
        gl_FragColor = vec4(uColor * a * 3.2, 1.0);
        #include <colorspace_fragment>
      }
    `,
  });
  const glints = new THREE.Mesh(gGeo, gMat);
  glints.frustumCulled = false;
  glints.renderOrder = 30;
  group.add(glints);

  const m4 = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const v = new THREE.Vector3();
  const s = new THREE.Vector3();

  function dropFood(x, y, z, n) {
    for (let k = 0; k < n; k++) {
      const i = foodNext++ % FOOD;
      food.pos[i * 3] = x + (Math.random() - 0.5) * 0.9;
      food.pos[i * 3 + 1] = y + (Math.random() - 0.5) * 0.3;
      food.pos[i * 3 + 2] = z + (Math.random() - 0.5) * 0.7;
      food.alive[i] = 1;
      foodVel[i] = 0.38 + Math.random() * 0.2;
      foodAge[i] = 0;
      foodSeed[i] = Math.random() * 10;
    }
  }

  function dropPearl(x, y, z, value) {
    for (let i = 0; i < PEARLS; i++) {
      if (pearl.state[i]) continue;
      pearl.pos.set([x, y, z], i * 3);
      pearl.state[i] = 1;
      pearl.age[i] = 0;
      pearl.vy[i] = 0.2;
      pearl.value[i] = value;
      pearl.ground[i] = sandHeight(x, z) + 0.08;
      return i;
    }
    return -1;
  }

  // landed: pearls that touched the sand this frame (each gets a chime)
  function update(dt, time, landed) {
    let n = 0;
    for (let i = 0; i < FOOD; i++) {
      if (!food.alive[i]) continue;
      foodAge[i] += dt;
      const ground = sandHeight(food.pos[i * 3], food.pos[i * 3 + 2]) + 0.05;
      const y = food.pos[i * 3 + 1];
      if (y > ground) {
        food.pos[i * 3 + 1] = Math.max(ground, y - foodVel[i] * dt);
        food.pos[i * 3] += Math.sin(time * 2.2 + foodSeed[i]) * 0.12 * dt;
      }
      if (foodAge[i] > FOOD_LIFE) { food.alive[i] = 0; continue; }
      const fade = Math.min(1, (FOOD_LIFE - foodAge[i]) / 1.5);
      v.set(food.pos[i * 3], food.pos[i * 3 + 1], food.pos[i * 3 + 2]);
      s.setScalar(0.055 * fade * (quality.phone ? 1.25 : 1));
      q.identity();
      m4.compose(v, q, s);
      foodMesh.setMatrixAt(n++, m4);
    }
    foodMesh.count = n;
    foodMesh.instanceMatrix.needsUpdate = true;

    let p = 0;
    let g = 0;
    for (let i = 0; i < PEARLS; i++) {
      const st = pearl.state[i];
      if (!st) continue;
      pearl.age[i] += dt;
      if (st === 1) {
        pearl.vy[i] = Math.min(1.1, pearl.vy[i] + dt * 1.2);
        const y = pearl.pos[i * 3 + 1] - pearl.vy[i] * dt;
        if (y <= pearl.ground[i]) {
          pearl.pos[i * 3 + 1] = pearl.ground[i];
          pearl.state[i] = 2;
          pearl.age[i] = 0;
          landed.push(i);
        } else pearl.pos[i * 3 + 1] = y;
      }
      const size = 0.065 * (quality.phone ? 1.3 : 1);
      v.set(pearl.pos[i * 3], pearl.pos[i * 3 + 1], pearl.pos[i * 3 + 2]);
      s.setScalar(size);
      m4.compose(v, q.identity(), s);
      pearlMesh.setMatrixAt(p++, m4);
      if (pearl.state[i] === 2) {
        gCenter.setXYZ(g, v.x, v.y + size * 0.4, v.z + 0.05);
        gData.setXY(g, i * 0.37, Math.min(1, pearl.age[i] * 2.5));
        g++;
      }
    }
    pearlMesh.count = p;
    pearlMesh.instanceMatrix.needsUpdate = true;
    gGeo.instanceCount = g;
    gCenter.needsUpdate = true;
    gData.needsUpdate = true;
    gMat.uniforms.uTime.value = time;
    gMat.uniforms.uScale.value = quality.phone ? 0.9 : 0.75;
  }

  function take(i) {
    const value = pearl.value[i];
    pearl.state[i] = 0;
    return value;
  }

  function resting(minAge = 0) {
    const out = [];
    for (let i = 0; i < PEARLS; i++) if (pearl.state[i] === 2 && pearl.age[i] >= minAge) out.push(i);
    return out;
  }

  function positionOf(i, out) {
    return out.set(pearl.pos[i * 3], pearl.pos[i * 3 + 1], pearl.pos[i * 3 + 2]);
  }

  function hasFood() {
    for (let i = 0; i < FOOD; i++) if (food.alive[i]) return true;
    return false;
  }

  return { group, food, dropFood, dropPearl, update, take, resting, positionOf, hasFood, pearlState: pearl.state };
}
