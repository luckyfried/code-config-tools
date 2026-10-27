// Instanced buildings: one box geometry, groups of at most 64 instances that cull by area, and a window texture
// painted on a canvas and offset per instance so no two towers light the same.
import * as THREE from "three";
import { FOG_GLSL } from "./palette.js";
import { FLOOR, PITCH } from "../game/gen.js";

const COLS = 16;
const ROWS = 32;
const GROUP = 64;

export function paintWindows(seedRng) {
  const cw = 32, ch = 16;
  const canvas = document.createElement("canvas");
  canvas.width = COLS * cw;
  canvas.height = ROWS * ch;
  const ctx = canvas.getContext("2d");
  const img = ctx.createImageData(canvas.width, canvas.height);
  const d = img.data;
  // Red is warm light, green is cool light, blue is the glass mask; every pixel is opaque so nothing premultiplies.
  for (let row = 0; row < ROWS; row++) {
    for (let col = 0; col < COLS; col++) {
      const lit = seedRng.next() < 0.42;
      const kind = seedRng.next();
      const level = 0.45 + seedRng.next() * 0.55;
      const blinds = seedRng.next() < 0.3;
      const tv = kind > 0.95;
      const warm = !lit ? 0 : kind < 0.68 ? level : tv ? level * 0.3 : level * 0.15;
      const cool = !lit ? 0 : kind < 0.68 ? level * 0.12 : level;
      const inset = seedRng.next() < 0.2 ? 9 : 6;
      for (let y = 0; y < ch; y++) {
        for (let x = 0; x < cw; x++) {
          const i = ((row * ch + y) * canvas.width + (col * cw + x)) * 4;
          const glass = x >= inset && x < cw - inset && y >= 4 && y < ch - 3;
          let shade = 1;
          if (glass && blinds && y % 3 === 0) shade = 0.55;
          if (glass) shade *= 0.75 + 0.25 * (y / ch);
          d[i] = glass ? Math.round(warm * shade * 255) : 0;
          d[i + 1] = glass ? Math.round(cool * shade * 255) : 0;
          d[i + 2] = glass ? 255 : 0;
          d[i + 3] = 255;
        }
      }
    }
  }
  ctx.putImageData(img, 0, 0);
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.NoColorSpace;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.anisotropy = 8;
  return texture;
}

export function createCityMaterial(shared, windowTexture) {
  return new THREE.ShaderMaterial({
    uniforms: {
      ...shared,
      uWindows: { value: windowTexture },
      uBuilding: { value: new THREE.Color() },
      uBuildingLight: { value: new THREE.Color() },
      uRoof: { value: new THREE.Color() },
      uWarm: { value: new THREE.Color() },
      uCool: { value: new THREE.Color() },
      uSign: { value: new THREE.Color() },
      uWindowLit: { value: 1 },
    },
    vertexShader: /* glsl */ `
      attribute vec4 aWin;
      attribute float aKind;
      varying vec3 vWorld;
      varying vec3 vNormal;
      varying vec3 vLocal;
      varying vec3 vSize;
      varying vec4 vWin;
      varying float vKind;
      void main() {
        vec4 world = modelMatrix * instanceMatrix * vec4(position, 1.0);
        vWorld = world.xyz;
        vNormal = normalize(mat3(instanceMatrix) * normal);
        vLocal = position;
        vSize = vec3(length(instanceMatrix[0].xyz), length(instanceMatrix[1].xyz), length(instanceMatrix[2].xyz));
        vWin = aWin;
        vKind = aKind;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uWindows;
      uniform vec3 uBuilding;
      uniform vec3 uBuildingLight;
      uniform vec3 uRoof;
      uniform vec3 uWarm;
      uniform vec3 uCool;
      uniform vec3 uSign;
      uniform vec3 uSkyTop;
      uniform vec3 uSkyHorizon;
      uniform float uWindowLit;
      uniform float uTime;
      uniform float uGlow;
      varying vec3 vWorld;
      varying vec3 vNormal;
      varying vec3 vLocal;
      varying vec3 vSize;
      varying vec4 vWin;
      varying float vKind;
      ${FOG_GLSL}
      float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vnoise(vec2 p) {
        vec2 i = floor(p), f = fract(p);
        f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
      }
      void main() {
        vec3 n = normalize(vNormal);
        vec3 view = normalize(vWorld - cameraPosition);
        float fres = pow(1.0 - max(dot(-view, n), 0.0), 3.0);
        vec3 sky = mix(uSkyHorizon, uSkyTop, 0.35);
        float streetGlow = 1.0 - smoothstep(0.0, 46.0, vWorld.y);
        vec3 wall = uBuilding * (0.75 + 0.25 * vWin.w);
        wall += uBuildingLight * 0.22 * smoothstep(-1.0, 1.0, n.x * 0.6 + n.z * 0.8);
        wall += uFogNear * 0.18 * streetGlow;
        vec3 color;
        if (n.y > 0.5) {
          // Roof: dark membrane with wet sheen and a lit parapet edge.
          vec2 edge = abs(vLocal.xz) * 2.0;
          float rim = smoothstep(1.0 - 0.9 / max(min(vSize.x, vSize.z), 1.0), 1.0, max(edge.x, edge.y));
          float puddle = smoothstep(0.5, 0.7, vnoise(vWorld.xz * 0.35) * 0.7 + vnoise(vWorld.xz * 1.1) * 0.3);
          color = uRoof + sky * (0.06 + 0.18 * puddle) + uBuildingLight * rim * 0.35;
        } else if (n.y < -0.5) {
          color = uRoof * 0.5;
        } else if (vKind > 0.5) {
          // Roof units, spires, balconies, and sign frames: plain panels with horizontal seams.
          float seam = step(0.92, fract(vWorld.y * 0.8));
          color = wall * (0.8 - 0.25 * seam) + sky * fres * 0.25;
          if (vKind > 1.5 && vKind < 2.5) color += uWarm * 0.25 * smoothstep(0.6, 1.0, vLocal.y);
        } else {
          float u = abs(n.x) > 0.5 ? vWorld.z * sign(n.x) : -vWorld.x * sign(n.z);
          vec2 cell = vec2(u / 1.8, vWorld.y / ${FLOOR.toFixed(1)});
          vec2 uv = cell / vec2(${COLS.toFixed(1)}, ${ROWS.toFixed(1)}) + vWin.xy;
          vec3 tex = texture2D(uWindows, uv).rgb;
          float glass = tex.b;
          vec3 lit = (uWarm * tex.r + uCool * tex.g) * vWin.z * uWindowLit * 2.4;
          // Street-level shopfronts: a continuous lit band on the ground floor.
          float shop = step(vWorld.y, ${FLOOR.toFixed(1)}) * step(0.35, vWorld.y);
          vec2 shopCell = vec2(u / 3.2, vWorld.y / ${FLOOR.toFixed(1)});
          float shopGlass = shop * step(0.12, fract(shopCell.x)) * step(fract(shopCell.x), 0.94) * step(0.12, fract(shopCell.y)) * step(fract(shopCell.y), 0.86);
          float shopKind = hash(floor(vec2(shopCell.x * 0.33, 0.0) + vWin.xy * 91.0));
          vec3 shopLight = mix(uWarm, uSign, step(0.72, shopKind)) * (0.8 + 0.6 * shopKind) * uGlow;
          vec3 glassColor = sky * (0.12 + 0.55 * fres) + lit;
          color = mix(wall, glassColor, glass * (1.0 - shop));
          color = mix(color, shopLight * 1.8, shopGlass);
          // Corner rims keep each tower's silhouette readable against the fog.
          vec2 e = abs(vLocal.xz) * 2.0;
          float corner = smoothstep(0.985, 1.0, max(abs(n.x) > 0.5 ? e.y : e.x, 0.0));
          color += uBuildingLight * corner * 0.5;
        }
        color += uFlashColor * uFlash * 0.35 * (0.4 + 0.6 * max(n.y, 0.0) + 0.3 * fres);
        color = applyFog(color, vWorld, cameraPosition);
        gl_FragColor = vec4(color, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
}

export function updateCityPalette(material, palette) {
  const u = material.uniforms;
  u.uBuilding.value.copy(palette.building);
  u.uBuildingLight.value.copy(palette.buildingLight);
  u.uRoof.value.copy(palette.roof);
  u.uWarm.value.copy(palette.windowWarm);
  u.uCool.value.copy(palette.windowCool);
  u.uSign.value.copy(palette.sign1);
  u.uWindowLit.value = palette.windowLit;
}

// Boxes sorted into areas two blocks square, then cut into groups of 64: each group is one InstancedMesh whose
// bounding sphere lets the renderer skip it when it is off screen.
export function buildCity(plan, material) {
  const base = new THREE.BoxGeometry(1, 1, 1);
  base.translate(0, 0.5, 0);
  const area = PITCH * 2;
  const order = plan.boxes.map((b, i) => i).sort((a, b) => {
    const A = plan.boxes[a], B = plan.boxes[b];
    const ka = Math.floor((A.x + plan.halfX) / area) * 100 + Math.floor((A.z + plan.halfZ) / area);
    const kb = Math.floor((B.x + plan.halfX) / area) * 100 + Math.floor((B.z + plan.halfZ) / area);
    return ka - kb || A.x - B.x || A.z - B.z;
  });
  const group = new THREE.Group();
  group.name = "city";
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const p = new THREE.Vector3();
  const s = new THREE.Vector3();
  let start = 0;
  while (start < order.length) {
    // Keep each group inside one area so its bounding sphere stays tight.
    const first = plan.boxes[order[start]];
    const key = Math.floor((first.x + plan.halfX) / area) * 100 + Math.floor((first.z + plan.halfZ) / area);
    let end = start;
    while (end < order.length && end - start < GROUP) {
      const b = plan.boxes[order[end]];
      const k = Math.floor((b.x + plan.halfX) / area) * 100 + Math.floor((b.z + plan.halfZ) / area);
      if (k !== key) break;
      end++;
    }
    const count = end - start;
    const geometry = base.clone();
    const win = new Float32Array(count * 4);
    const kind = new Float32Array(count);
    const mesh = new THREE.InstancedMesh(geometry, material, count);
    for (let k = 0; k < count; k++) {
      const b = plan.boxes[order[start + k]];
      p.set(b.x, b.y0, b.z);
      s.set(b.w, b.y1 - b.y0, b.d);
      mesh.setMatrixAt(k, m.compose(p, q, s));
      win.set([b.ox, b.oy, b.lit, b.tint], k * 4);
      kind[k] = b.windows ? 0 : b.balcony ? 2 : 1;
    }
    geometry.setAttribute("aWin", new THREE.InstancedBufferAttribute(win, 4));
    geometry.setAttribute("aKind", new THREE.InstancedBufferAttribute(kind, 1));
    mesh.instanceMatrix.needsUpdate = true;
    mesh.computeBoundingSphere();
    mesh.computeBoundingBox();
    mesh.matrixAutoUpdate = false;
    group.add(mesh);
    start = end;
  }
  return group;
}
