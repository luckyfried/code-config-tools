// Ghost ships built from primitives: a tapered hull, masts, yards, and tattered sails in one geometry, dark against
// the fog with lanterns that glow. Held in the beam, a ship warms, then dissolves along a noise threshold with a
// glowing edge, sails first, hull last.
import * as THREE from "three";
import { NOISE } from "./glsl.js";
import { merge, paint, softSprite } from "./geometry.js";

const PART_HULL = 0.42;
const PART_MAST = 0.2;
const PART_SAIL = 0.0;

function withPart(geometry, part) {
  const g = geometry.index ? geometry.toNonIndexed() : geometry;
  const n = g.attributes.position.count;
  // The part rides in the color attribute's red channel: its burn offset, so sails go first and the hull last.
  const colors = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) colors[i * 3] = part;
  g.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return g;
}

function hull() {
  const g = new THREE.BoxGeometry(2.8, 2.2, 11, 4, 3, 12);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    let x = p.getX(i);
    let y = p.getY(i);
    const z = p.getZ(i);
    const t = z / 5.5;
    const bow = t > 0 ? 1 - Math.pow(t, 2.2) * 0.92 : 1 - Math.pow(-t, 3) * 0.45;
    const keel = 0.45 + 0.55 * ((y + 1.1) / 2.2);
    x *= bow * keel;
    if (y > 0) y += 0.55 * t * t + (t < -0.6 ? (-t - 0.6) * 1.6 : 0);
    p.setXYZ(i, x, y, z);
  }
  g.computeVertexNormals();
  return g;
}

function sail(width, height, billow, seed) {
  const g = new THREE.PlaneGeometry(width, height, 6, 6);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i);
    const y = p.getY(i);
    const u = x / width + 0.5;
    const v = y / height + 0.5;
    const bulge = Math.sin(u * Math.PI) * Math.sin(v * Math.PI * 0.9 + 0.2) * billow;
    const sag = v < 0.18 ? Math.sin(u * Math.PI * 3 + seed) * 0.25 : 0;
    p.setXYZ(i, x, y - sag, bulge);
  }
  g.computeVertexNormals();
  return g;
}

function buildShipGeometry(seed) {
  const parts = [];
  parts.push(withPart(hull(), PART_HULL));
  const cabin = new THREE.BoxGeometry(2.2, 1.3, 2.6);
  cabin.translate(0, 1.9, -3.4);
  parts.push(withPart(cabin, PART_HULL));
  const masts = [
    [1.6, 10.5, 3.6, 4.6],
    [-1.9, 8.6, 3.0, 3.8],
  ];
  masts.forEach(([z, h, w, sh], i) => {
    const mast = new THREE.CylinderGeometry(0.1, 0.16, h, 6);
    mast.translate(0, 1 + h / 2, z);
    parts.push(withPart(mast, PART_MAST));
    for (const [y, yw] of [[h * 0.92, w * 0.85], [h * 0.55, w]]) {
      const yard = new THREE.CylinderGeometry(0.07, 0.07, yw * 1.05, 5);
      yard.rotateZ(Math.PI / 2);
      yard.translate(0, 1 + y, z);
      parts.push(withPart(yard, PART_MAST));
    }
    const upper = sail(w * 0.82, sh * 0.62, 0.45, seed + i);
    upper.translate(0, 1 + h * 0.92 - sh * 0.33, z + 0.15);
    parts.push(withPart(upper, PART_SAIL));
    const lower = sail(w, sh * 0.85, 0.6, seed + i + 4);
    lower.translate(0, 1 + h * 0.55 - sh * 0.45, z + 0.2);
    parts.push(withPart(lower, PART_SAIL));
  });
  const bowsprit = new THREE.CylinderGeometry(0.06, 0.1, 4.2, 5);
  bowsprit.rotateX(Math.PI / 2 - 0.35);
  bowsprit.translate(0, 1.8, 6.6);
  parts.push(withPart(bowsprit, PART_MAST));
  const jib = new THREE.BufferGeometry();
  jib.setAttribute("position", new THREE.Float32BufferAttribute([0, 2.0, 8.2, 0, 10.5, 1.8, 0, 1.6, 2.4], 3));
  jib.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, 1, 1, 1, 0], 2));
  jib.computeVertexNormals();
  parts.push(withPart(jib, PART_SAIL));
  return merge(parts);
}

// Where a point of the ship sits in the burn: sails first, then masts, then the hull, and within each part from the
// top down, broken into large ragged fronts by low-frequency noise.
const BURN_VALUE = /* glsl */ `
float shipBurnValue(vec3 p, float part) {
  float n = lkNoise(p * 0.42 + vec3(3.1, 0.0, 7.7)) * 0.7 + lkNoise(p * 1.25) * 0.3;
  float fromTop = clamp(1.0 - p.y / 12.0, 0.0, 1.0);
  return n * 0.34 + fromTop * 0.2 + part;
}
`;

const dissolveShader = (shader, u) => {
  Object.assign(shader.uniforms, u);
  shader.vertexShader = shader.vertexShader
    .replace(
      "#include <common>",
      `#include <common>
      varying vec3 vShipLocal;
      varying float vPart;`,
    )
    .replace(
      "#include <begin_vertex>",
      `#include <begin_vertex>
      vShipLocal = position;
      vPart = color.r;`,
    );
  shader.fragmentShader = shader.fragmentShader
    .replace(
      "#include <common>",
      `#include <common>
      uniform float uBurn, uHeat, uRim;
      uniform vec3 uEdge, uRimColor, uHull;
      varying vec3 vShipLocal;
      varying float vPart;
      ${NOISE}
      ${BURN_VALUE}`,
    )
    .replace(
      "#include <clipping_planes_fragment>",
      `#include <clipping_planes_fragment>
      float shipValue = shipBurnValue(vShipLocal, vPart);
      float burnLevel = uBurn * 1.06;
      if (shipValue < burnLevel) discard;
      float burnGap = shipValue - burnLevel;
      float burnOn = step(0.001, uBurn);
      float burnEdge = (1.0 - smoothstep(0.0, 0.022, burnGap)) * burnOn;
      float burnChar = (1.0 - smoothstep(0.02, 0.14, burnGap)) * burnOn;`,
    )
    .replace("#include <color_fragment>", "diffuseColor.rgb = uHull * (vPart < 0.05 ? 1.35 : 1.0) * (1.0 - uHeat * 0.5) * (1.0 - burnChar * 0.85);")
    .replace(
      "#include <emissivemap_fragment>",
      `#include <emissivemap_fragment>
      vec3 shipView = normalize(vViewPosition);
      float shipRim = pow(1.0 - abs(dot(normalize(vNormal), shipView)), 2.5);
      totalEmissiveRadiance += uRimColor * shipRim * uRim;
      totalEmissiveRadiance += uEdge * (burnEdge * 9.0 + burnChar * 0.35);`,
    );
};

const depthShader = (shader, u) => {
  Object.assign(shader.uniforms, u);
  shader.vertexShader = shader.vertexShader
    .replace(
      "#include <common>",
      `#include <common>
      attribute vec3 color;
      varying vec3 vShipLocal;
      varying float vPart;`,
    )
    .replace(
      "#include <begin_vertex>",
      `#include <begin_vertex>
      vShipLocal = position;
      vPart = color.r;`,
    );
  shader.fragmentShader = shader.fragmentShader
    .replace(
      "#include <common>",
      `#include <common>
      uniform float uBurn;
      varying vec3 vShipLocal;
      varying float vPart;
      ${NOISE}
      ${BURN_VALUE}`,
    )
    .replace(
      "#include <clipping_planes_fragment>",
      `#include <clipping_planes_fragment>
      if (shipBurnValue(vShipLocal, vPart) < uBurn * 1.06) discard;`,
    );
};

export function createShips(tokens, tier, count) {
  const group = new THREE.Group();
  const geometries = [buildShipGeometry(1), buildShipGeometry(5), buildShipGeometry(9)];
  const flat = !tier.post;
  const ships = [];
  for (let i = 0; i < count; i++) {
    const u = {
      uBurn: { value: 0 },
      uHeat: { value: 0 },
      uRim: { value: (tokens.dark ? 0.55 : 0.2) * (flat ? 1.6 : 1) },
      uEdge: { value: tokens.burnEdge.clone() },
      uRimColor: { value: tokens.shipRim.clone() },
      uHull: { value: tokens.ship.clone() },
    };
    const material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.85,
      metalness: 0,
      side: THREE.DoubleSide,
      emissive: new THREE.Color(0, 0, 0),
    });
    material.onBeforeCompile = (shader) => dissolveShader(shader, u);
    material.customProgramCacheKey = () => "lk-ship";
    const mesh = new THREE.Mesh(geometries[i % geometries.length], material);
    mesh.castShadow = tier.shadow > 0;
    mesh.visible = false;
    if (tier.shadow > 0) {
      const depth = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, side: THREE.DoubleSide });
      depth.onBeforeCompile = (shader) => depthShader(shader, u);
      depth.customProgramCacheKey = () => "lk-ship-depth";
      mesh.customDepthMaterial = depth;
    }
    const scale = 0.85 + ((i * 37) % 10) / 30;
    mesh.scale.setScalar(scale);
    group.add(mesh);
    ships.push({ mesh, uniforms: u, scale });
  }

  // Lanterns for every ship in one draw: a stern lantern and a masthead lantern each.
  const lanternCount = count * 2;
  const lanternPos = new Float32Array(lanternCount * 3);
  const lanternGlow = new Float32Array(lanternCount);
  const lanternGeo = new THREE.BufferGeometry();
  lanternGeo.setAttribute("position", new THREE.BufferAttribute(lanternPos, 3));
  lanternGeo.setAttribute("aGlow", new THREE.BufferAttribute(lanternGlow, 1));
  const lanternMat = new THREE.ShaderMaterial({
    uniforms: {
      uMap: { value: softSprite(64, 0.12) },
      uColor: { value: tokens.lantern.clone().multiplyScalar(flat ? 3 : 2.2) },
      uScale: { value: 1 },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      attribute float aGlow;
      varying float vGlow;
      uniform float uScale;
      void main() {
        vGlow = aGlow;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = clamp(2.4 * uScale / -mv.z, 2.0, 110.0) * step(0.001, aGlow);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform vec3 uColor;
      varying float vGlow;
      void main() {
        float a = texture2D(uMap, gl_PointCoord).a;
        gl_FragColor = vec4(uColor * a * vGlow, 1.0);
      }
    `,
  });
  const lanterns = new THREE.Points(lanternGeo, lanternMat);
  lanterns.frustumCulled = false;
  group.add(lanterns);

  // Embers for every ship in one draw: sparks lift off a burning ship's sails and rigging, rise, drift downwind, and
  // cool from white-hot to the burn color as they fade.
  const EMBERS = 260;
  const emberPos = new Float32Array(EMBERS * 3);
  const emberLife = new Float32Array(EMBERS);
  const emberVel = new Float32Array(EMBERS * 3);
  const emberAge = new Float32Array(EMBERS).fill(1);
  const emberSpan = new Float32Array(EMBERS).fill(1);
  const emberGeo = new THREE.BufferGeometry();
  emberGeo.setAttribute("position", new THREE.BufferAttribute(emberPos, 3));
  emberGeo.setAttribute("aLife", new THREE.BufferAttribute(emberLife, 1));
  const emberMat = new THREE.ShaderMaterial({
    uniforms: {
      uMap: { value: softSprite(32, 0.2) },
      uColor: { value: tokens.burnEdge.clone().multiplyScalar(flat ? 3.2 : 2.6) },
      uScale: { value: 1 },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      attribute float aLife;
      varying float vLife;
      uniform float uScale;
      void main() {
        vLife = aLife;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = clamp(0.5 * uScale * (0.4 + aLife) / -mv.z, 1.5, 24.0) * step(0.001, aLife);
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform vec3 uColor;
      varying float vLife;
      void main() {
        float a = texture2D(uMap, gl_PointCoord).a;
        vec3 hot = mix(uColor, vec3(2.4, 2.1, 1.6), smoothstep(0.6, 1.0, vLife));
        gl_FragColor = vec4(hot * a * vLife, 1.0);
      }
    `,
  });
  const embers = new THREE.Points(emberGeo, emberMat);
  embers.frustumCulled = false;
  group.add(embers);
  let emberNext = 0;
  const emberCarry = new Float32Array(count);
  const local = new THREE.Vector3();

  const stern = new THREE.Vector3(0, 3.0, -4.9);
  const masthead = new THREE.Vector3(0, 12.1, 1.6);
  const tmp = new THREE.Vector3();
  return {
    group,
    ships,
    lanterns: lanternMat,
    setPixelScale(s) {
      lanternMat.uniforms.uScale.value = s;
      emberMat.uniforms.uScale.value = s;
    },
    updateEmbers(states, dt) {
      for (let i = 0; i < count; i++) {
        const s = states[i];
        if (!s.active || s.burn <= 0.01 || s.burn >= 0.98 || s.wrecked) continue;
        emberCarry[i] += dt * (30 + s.heat * 40 + (s.turned ? 50 : 0));
        const m = ships[i].mesh;
        // The burn front starts at the mastheads and works down to the hull.
        const front = Math.max(1.5, 12 - s.burn * 12);
        while (emberCarry[i] >= 1) {
          emberCarry[i] -= 1;
          const k = emberNext;
          emberNext = (emberNext + 1) % EMBERS;
          const mast = Math.random() < 0.55 ? 1.6 : -1.9;
          local.set((Math.random() - 0.5) * 3.4, front + (Math.random() - 0.3) * 2.4, mast + (Math.random() - 0.5) * 1.6);
          local.applyMatrix4(m.matrixWorld);
          emberPos[k * 3] = local.x;
          emberPos[k * 3 + 1] = local.y;
          emberPos[k * 3 + 2] = local.z;
          emberVel[k * 3] = (Math.random() - 0.5) * 1.6 + 1.2;
          emberVel[k * 3 + 1] = 2.2 + Math.random() * 2.8;
          emberVel[k * 3 + 2] = (Math.random() - 0.5) * 1.6;
          emberAge[k] = 0;
          emberSpan[k] = 0.9 + Math.random() * 1.1;
        }
      }
      for (let k = 0; k < EMBERS; k++) {
        if (emberAge[k] >= emberSpan[k]) {
          emberLife[k] = 0;
          continue;
        }
        emberAge[k] += dt;
        emberVel[k * 3 + 1] *= 1 - dt * 0.6;
        emberPos[k * 3] += emberVel[k * 3] * dt;
        emberPos[k * 3 + 1] += emberVel[k * 3 + 1] * dt;
        emberPos[k * 3 + 2] += emberVel[k * 3 + 2] * dt;
        emberLife[k] = Math.max(0, 1 - emberAge[k] / emberSpan[k]);
      }
      emberGeo.attributes.position.needsUpdate = true;
      emberGeo.attributes.aLife.needsUpdate = true;
    },
    syncLanterns(states) {
      for (let i = 0; i < count; i++) {
        const s = states[i];
        const m = ships[i].mesh;
        const consumed = Math.min(1, Math.max(0, (s.burn - 0.62) / 0.3));
        const glow = s.active ? (1 + s.heat * 0.8 + Math.min(1, s.burn * 4) * 1.6) * (1 - consumed) * s.fade : 0;
        tmp.copy(stern).applyMatrix4(m.matrixWorld);
        lanternPos[i * 6] = tmp.x;
        lanternPos[i * 6 + 1] = tmp.y;
        lanternPos[i * 6 + 2] = tmp.z;
        tmp.copy(masthead).applyMatrix4(m.matrixWorld);
        lanternPos[i * 6 + 3] = tmp.x;
        lanternPos[i * 6 + 4] = tmp.y;
        lanternPos[i * 6 + 5] = tmp.z;
        lanternGlow[i * 2] = glow;
        lanternGlow[i * 2 + 1] = glow * (1 - Math.min(1, Math.max(0, s.burn - 0.12) * 4)) * 0.8;
      }
      lanternGeo.attributes.position.needsUpdate = true;
      lanternGeo.attributes.aGlow.needsUpdate = true;
    },
  };
}
