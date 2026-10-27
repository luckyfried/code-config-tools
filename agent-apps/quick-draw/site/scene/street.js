// Main Street: two rows of false-front buildings with porches, posts, windows, and painted shop signs, the
// two-story saloon with its balcony, and the saloon's canvas banner across the street with the town's name.
import * as THREE from "three";
import { box, cylinder, xf, seeded } from "./kit.js";

const FACADE = 8.5;
export const BANNER_Y = 7.6;

/** Where a building's local (u outward from its facade, y, z) lands in the world on side s (-1 left, +1 right). */
const X = (s, u) => s * (FACADE + u);

function signPlane(w, h, rect) {
  const g = new THREE.PlaneGeometry(w, h);
  const uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i += 1) {
    uv.setXY(i, rect.u0 + uv.getX(i) * (rect.u1 - rect.u0), rect.v0 + uv.getY(i) * (rect.v1 - rect.v0));
  }
  return g;
}

/** The lots on each side of the street, near to far. */
function plan() {
  return [
    // left side (s = -1)
    { s: -1, z0: 17, len: 11, stories: 1, top: "stepped", paint: "paint-2", sign: "GUNSMITH", lantern: true },
    { s: -1, z0: 4.6, len: 15, stories: 2, top: "flat", paint: "paint-3", sign: "HOTEL", balcony: true, lantern: true, anchor: true },
    { s: -1, z0: -12.4, len: 8, stories: 1, top: "flat", paint: "paint-4", sign: "BARBER" },
    { s: -1, z0: -22.6, len: 11, stories: 2, top: "stepped", paint: "paint-5", sign: "BANK", stone: true },
    { s: -1, z0: -36, len: 9, stories: 1, top: "flat", paint: "wood", sign: "ASSAY OFFICE", lantern: true },
    { s: -1, z0: -47, len: 8, stories: 1, top: "stepped", paint: "paint-1", sign: "TELEGRAPH" },
    { s: -1, z0: -58, len: 10, stories: 1, top: "flat", paint: "paint-2", sign: "DRY GOODS" },
    { s: -1, z0: -71, len: 14, kind: "barn", paint: "paint-1" },
    { s: -1, z0: -92, len: 9, stories: 1, top: "flat", paint: "wood" },
    // right side (s = +1)
    { s: 1, z0: 16, len: 12, stories: 1, top: "flat", paint: "paint-4", sign: "GENERAL STORE", lantern: true },
    { s: 1, z0: 2, len: 16, stories: 2, kind: "saloon", paint: "paint-1", sign: "SALOON", balcony: true, lantern: true },
    { s: 1, z0: -16.4, len: 9, stories: 1, top: "stepped", paint: "paint-3", sign: "SHERIFF", lantern: true },
    { s: 1, z0: -27, len: 8, stories: 1, top: "flat", paint: "paint-2", sign: "UNDERTAKER" },
    { s: 1, z0: -37, len: 12, stories: 2, top: "flat", paint: "wood", sign: "LIVERY" },
    { s: 1, z0: -52, len: 9, stories: 1, top: "stepped", paint: "paint-5" },
    { s: 1, z0: -64, len: 10, stories: 1, top: "flat", paint: "paint-4" },
    { s: 1, z0: -78, len: 8, stories: 1, top: "flat", paint: "wood" },
  ];
}

export function buildStreet(kit, tokens, signRect) {
  const rnd = seeded(41);
  const lanterns = [];
  const occluders = [];
  const C = (name) => (name === "wood" ? tokens.wood : tokens[name.replace(/-(\d)/, "$1").replace(/-([a-z])/g, (_, c) => c.toUpperCase())]);
  const trim = tokens.trim;
  const woodLight = tokens.woodLight;
  const wood = tokens.wood;
  const dark = tokens.wood.clone().multiplyScalar(0.45);
  const glass = tokens.window;

  for (const lot of plan()) {
    const { s, z0, len } = lot;
    const zc = z0 - len / 2;
    const paint = C(lot.paint).clone().offsetHSL(0, (rnd() - 0.5) * 0.04, (rnd() - 0.5) * 0.04);
    if (lot.kind === "barn") {
      barn(kit, s, zc, len, paint, trim, wood, dark);
      continue;
    }
    const twoStory = lot.stories === 2;
    const h = twoStory ? 7.4 : 4.4;
    const front = h + (lot.top === "stepped" ? 1.4 : 2.0) + (twoStory ? 0.4 : 0);
    const depth = 11 + rnd() * 3;

    // body behind the false front, and a stovepipe
    kit.add("wood", box(depth, h, len - 0.2), paint.clone().multiplyScalar(0.82), xf(X(s, depth / 2), h / 2, zc));
    if (rnd() < 0.6) {
      kit.add("metal", cylinder(0.12, 0.12, 1.6, 8), dark, xf(X(s, depth * (0.4 + rnd() * 0.4)), h + 0.8, zc + (rnd() - 0.5) * len * 0.5));
    }

    // the false front, with its top
    const wallTop = lot.top === "stepped" ? front - 1.0 : front;
    kit.add("wood", box(0.24, wallTop, len), paint, xf(X(s, -0.12), wallTop / 2, zc));
    if (lot.top === "stepped") {
      const w2 = len * 0.52;
      kit.add("wood", box(0.24, 1.0, w2), paint, xf(X(s, -0.12), wallTop + 0.5, zc));
      kit.add("wood", box(0.42, 0.22, w2 + 0.3), trim, xf(X(s, -0.2), front + 0.08, zc));
      kit.add("wood", box(0.36, 0.16, len + 0.2), trim, xf(X(s, -0.2), wallTop + 0.05, zc));
    } else {
      kit.add("wood", box(0.46, 0.26, len + 0.34), trim, xf(X(s, -0.22), front + 0.1, zc));
      kit.add("wood", box(0.3, 0.12, len + 0.1), trim, xf(X(s, -0.18), front - 0.24, zc));
      const brackets = Math.floor(len / 0.9);
      for (let i = 0; i <= brackets; i += 1) {
        const bz = z0 - 0.2 - (i * (len - 0.4)) / brackets;
        kit.add("wood", box(0.24, 0.3, 0.1), trim, xf(X(s, -0.3), front - 0.15, bz));
      }
    }
    // corner boards
    for (const end of [z0 - 0.06, z0 - len + 0.06]) {
      kit.add("wood", box(0.3, wallTop, 0.16), trim, xf(X(s, -0.16), wallTop / 2, end));
    }

    // porch: deck, posts, beam, and roof (a flat balcony floor on two-story buildings that have one)
    const porch = 2.4;
    const deckH = 0.34;
    kit.add("wood", box(porch, deckH, len), woodLight, xf(X(s, -porch / 2), deckH / 2, zc));
    kit.add("wood", box(0.12, 0.12, len), dark, xf(X(s, -porch + 0.06), deckH + 0.01, zc));
    const postCount = Math.max(2, Math.round(len / 2.8));
    const postH = 3.0;
    for (let i = 0; i <= postCount; i += 1) {
      const pz = z0 - 0.25 - (i * (len - 0.5)) / postCount;
      kit.add("plain", box(0.16, postH, 0.16), woodLight, xf(X(s, -porch + 0.22), deckH + postH / 2, pz));
      kit.add("plain", box(0.26, 0.14, 0.26), woodLight, xf(X(s, -porch + 0.22), deckH + 0.07, pz));
      if (lot.lantern && i === 1) {
        const lx = X(s, -porch + 0.5);
        const ly = deckH + postH - 0.75;
        kit.add("metal", box(0.22, 0.05, 0.22), dark, xf(lx, ly + 0.19, pz));
        kit.add("glow", box(0.15, 0.24, 0.15), new THREE.Color(1, 1, 1), xf(lx, ly, pz));
        kit.add("metal", box(0.2, 0.04, 0.2), dark, xf(lx, ly - 0.14, pz));
        kit.add("metal", box(0.03, 0.4, 0.03), dark, xf(lx, ly + 0.4, pz));
        lanterns.push(new THREE.Vector3(lx, ly, pz));
      }
    }
    const beamY = deckH + postH;
    kit.add("plain", box(0.2, 0.22, len), woodLight, xf(X(s, -porch + 0.22), beamY + 0.11, zc));
    if (lot.balcony) {
      balcony(kit, s, z0, len, zc, porch, beamY, trim, woodLight, dark);
    } else {
      const slope = Math.atan2(0.42, porch);
      const roofColor = rnd() < 0.5 ? new THREE.Color(0.62, 0.6, 0.58) : woodLight.clone().multiplyScalar(0.8);
      kit.add(rnd() < 0.5 ? "tin" : "wood", box(porch + 0.5, 0.08, len + 0.3), roofColor, xf(X(s, -porch / 2 + 0.05), beamY + 0.42, zc, 0, 0, s * slope));
    }

    // a hitching rail in front of some porches
    if (rnd() < 0.55) {
      const hz = zc + (rnd() - 0.5) * (len - 4);
      for (const dz of [-1.4, 1.4]) kit.add("plain", box(0.14, 1.1, 0.14), wood, xf(X(s, -porch - 1.1), 0.55, hz + dz));
      kit.add("plain", cylinder(0.05, 0.05, 3.1, 6), wood, xf(X(s, -porch - 1.1), 1.02, hz, Math.PI / 2, 0, 0));
    }

    // ground-floor door and windows
    const doorZ = zc + (lot.kind === "saloon" ? 0 : (rnd() - 0.5) * len * 0.3);
    if (lot.kind === "saloon") {
      saloonDoors(kit, s, doorZ, deckH, trim, woodLight, glass);
    } else {
      doorway(kit, s, doorZ, deckH, trim, dark);
    }
    const winW = 1.25;
    for (const side of [-1, 1]) {
      const wz = doorZ + side * (len * 0.28 + 0.5);
      if (Math.abs(wz - zc) > len / 2 - 0.9) continue;
      windowPane(kit, s, wz, deckH + 1.55, winW, 1.6, trim, glass, lot.kind === "saloon");
    }
    if (twoStory) {
      const upper = Math.max(2, Math.floor(len / 3.2));
      for (let i = 0; i < upper; i += 1) {
        const wz = z0 - (len * (i + 0.5)) / upper;
        windowPane(kit, s, wz, 5.35, 0.95, 1.4, trim, glass, lot.kind === "saloon");
      }
    }

    // the shop sign on the false front
    if (lot.sign && signRect(lot.sign)) {
      const sw = Math.min(len * 0.78, lot.kind === "saloon" ? 9.5 : 6.4);
      const sh = sw / 5.33;
      const signY = lot.kind === "saloon" ? front - sh / 2 - 0.45 : Math.max(beamY + 0.75 + sh / 2, front - 0.55 - sh / 2);
      const g = signPlane(sw, sh, signRect(lot.sign));
      kit.add("signs", g, new THREE.Color(1, 1, 1), xf(X(s, -0.27), signY, zc, 0, -s * Math.PI / 2, 0));
      kit.add("wood", box(0.1, sh + 0.16, sw + 0.16), dark, xf(X(s, -0.22), signY, zc));
    }

    // barrels and crates on the boardwalk
    const clutter = Math.floor(rnd() * 3);
    for (let i = 0; i < clutter; i += 1) {
      const cz = z0 - 0.8 - rnd() * (len - 1.6);
      if (Math.abs(cz - doorZ) < 1.4) continue;
      if (rnd() < 0.5) barrel(kit, X(s, -0.6 - rnd() * 0.6), deckH, cz, woodLight, dark);
      else kit.add("plain", box(0.62, 0.62, 0.62), woodLight.clone().multiplyScalar(0.9), xf(X(s, -0.7), deckH + 0.31, cz, 0, rnd(), 0));
    }
    occluders.push({ s, z0, len, front });
  }

  // a few loose barrels and a water trough in the street's edges
  barrel(kit, X(-1, -3.3), 0, 6.4, woodLight, dark);
  barrel(kit, X(-1, -3.0), 0, 5.6, woodLight.clone().multiplyScalar(0.85), dark);
  kit.add("plain", box(0.7, 0.55, 2.4), wood, xf(X(1, -3.5), 0.28, -19.5));
  kit.add("glass", box(0.56, 0.05, 2.26), tokens.skyMid.clone().multiplyScalar(0.5), xf(X(1, -3.5), 0.5, -19.5));

  return { lanterns, occluders };
}

function doorway(kit, s, z, deckH, trim, dark) {
  kit.add("wood", box(0.1, 2.4, 1.3), dark, xf(X(s, -0.26), deckH + 1.2, z));
  kit.add("wood", box(0.14, 0.16, 1.6), trim, xf(X(s, -0.3), deckH + 2.48, z));
  for (const dz of [-0.72, 0.72]) kit.add("wood", box(0.14, 2.5, 0.14), trim, xf(X(s, -0.3), deckH + 1.25, z + dz));
}

function saloonDoors(kit, s, z, deckH, trim, woodLight, glass) {
  // a lit doorway behind the batwing doors
  kit.add("glass", box(0.06, 2.6, 1.9), glass.clone().multiplyScalar(1.4), xf(X(s, -0.2), deckH + 1.3, z));
  kit.add("wood", box(0.16, 0.2, 2.3), trim, xf(X(s, -0.3), deckH + 2.7, z));
  for (const dz of [-1.05, 1.05]) kit.add("wood", box(0.16, 2.7, 0.18), trim, xf(X(s, -0.3), deckH + 1.35, z + dz));
  for (const dz of [-0.47, 0.47]) {
    kit.add("wood", box(0.06, 1.05, 0.86), woodLight, xf(X(s, -0.36), deckH + 1.2, z + dz));
    for (let k = -2; k <= 2; k += 1) kit.add("wood", box(0.08, 0.7, 0.05), woodLight.clone().multiplyScalar(0.7), xf(X(s, -0.4), deckH + 1.2, z + dz + k * 0.15));
  }
}

function windowPane(kit, s, z, y, w, h, trim, glass, warm) {
  kit.add("glass", box(0.05, h, w), warm ? glass.clone().multiplyScalar(1.3) : glass, xf(X(s, -0.26), y, z));
  kit.add("wood", box(0.12, 0.12, w + 0.3), trim, xf(X(s, -0.3), y + h / 2 + 0.06, z));
  kit.add("wood", box(0.16, 0.1, w + 0.4), trim, xf(X(s, -0.32), y - h / 2 - 0.05, z));
  for (const dz of [-w / 2 - 0.06, w / 2 + 0.06]) kit.add("wood", box(0.12, h + 0.2, 0.12), trim, xf(X(s, -0.3), y, z + dz));
  kit.add("wood", box(0.08, h, 0.05), trim, xf(X(s, -0.3), y, z));
  kit.add("wood", box(0.08, 0.05, w), trim, xf(X(s, -0.3), y + h * 0.1, z));
  // shutters
  for (const dz of [-w / 2 - 0.42, w / 2 + 0.42]) kit.add("wood", box(0.06, h, w * 0.5), trim.clone().multiplyScalar(0.62), xf(X(s, -0.29), y, z + dz));
}

function balcony(kit, s, z0, len, zc, porch, beamY, trim, woodLight, dark) {
  const floorY = beamY + 0.24;
  kit.add("wood", box(porch + 0.2, 0.16, len + 0.2), woodLight, xf(X(s, -porch / 2), floorY, zc));
  const railH = 1.05;
  kit.add("wood", box(0.14, 0.1, len), trim, xf(X(s, -porch + 0.22), floorY + railH, zc));
  kit.add("wood", box(0.1, 0.08, len), trim, xf(X(s, -porch + 0.22), floorY + 0.2, zc));
  const balusters = Math.floor(len / 0.24);
  for (let i = 0; i < balusters; i += 1) {
    kit.add("wood", box(0.05, railH - 0.2, 0.05), trim, xf(X(s, -porch + 0.22), floorY + 0.6, z0 - 0.12 - (i * (len - 0.24)) / balusters));
  }
  const posts = Math.max(2, Math.round(len / 2.8));
  for (let i = 0; i <= posts; i += 1) {
    const pz = z0 - 0.25 - (i * (len - 0.5)) / posts;
    kit.add("wood", box(0.14, 2.6, 0.14), woodLight, xf(X(s, -porch + 0.22), floorY + 1.3, pz));
  }
  const slope = Math.atan2(0.4, porch);
  kit.add("tin", box(porch + 0.5, 0.08, len + 0.3), new THREE.Color(0.55, 0.52, 0.5), xf(X(s, -porch / 2 + 0.05), floorY + 2.75, zc, 0, 0, s * slope));
}

function barrel(kit, x, y, z, color, dark) {
  kit.add("plain", cylinder(0.27, 0.27, 0.86, 12), color, xf(x, y + 0.43, z));
  for (const hy of [0.16, 0.7]) kit.add("metal", cylinder(0.285, 0.285, 0.05, 12), dark, xf(x, y + hy, z));
}

function barn(kit, s, zc, len, paint, trim, wood, dark) {
  const depth = 14;
  const w = len;
  const wallH = 5.2;
  const peak = 8.6;
  const shape = new THREE.Shape();
  shape.moveTo(-w / 2, 0);
  shape.lineTo(w / 2, 0);
  shape.lineTo(w / 2, wallH);
  shape.lineTo(w * 0.28, wallH + 2.2);
  shape.lineTo(0, peak);
  shape.lineTo(-w * 0.28, wallH + 2.2);
  shape.lineTo(-w / 2, wallH);
  shape.lineTo(-w / 2, 0);
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  const uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i += 1) uv.setXY(i, uv.getX(i), uv.getY(i));
  // the shape is drawn in the x-y plane and extruded along +z; turn it so its face looks at the street
  kit.add("wood", g, paint, xf(X(s, 0), 0, zc, 0, s * Math.PI / 2, 0));
  // big doors with the white X braces
  const dz = zc;
  kit.add("wood", box(0.12, 3.6, 3.6), paint.clone().multiplyScalar(0.8), xf(X(s, -0.06), 1.8, dz));
  for (const sign of [-1, 1]) {
    kit.add("wood", box(0.14, 0.16, 4.9), trim, xf(X(s, -0.14), 1.8, dz, sign * 0.79, 0, 0));
  }
  kit.add("wood", box(0.16, 0.18, 3.9), trim, xf(X(s, -0.14), 3.62, dz));
  kit.add("wood", box(0.16, 3.7, 0.18), trim, xf(X(s, -0.14), 1.8, dz - 1.86));
  kit.add("wood", box(0.16, 3.7, 0.18), trim, xf(X(s, -0.14), 1.8, dz + 1.86));
  // hay door
  kit.add("wood", box(0.12, 1.4, 1.4), dark, xf(X(s, -0.08), 6.0, dz));
  kit.add("plain", box(1.6, 0.18, 0.18), wood, xf(X(s, -0.8), 7.2, dz));
}

/** The saloon's canvas banner across the street, sagging on its ropes and moving in the wind. */
export function createBanner(texture, tokens) {
  const width = 11.2;
  const height = 2.2;
  const geometry = new THREE.PlaneGeometry(width, height, 32, 6);
  const uniforms = { uTime: { value: 0 }, uWind: { value: 1 } };
  // lit from the porch lanterns as well as the sky, so the town's name reads in every light
  const material = new THREE.MeshStandardMaterial({
    map: texture,
    roughness: 0.95,
    side: THREE.DoubleSide,
    envMapIntensity: 0.45,
    emissive: tokens.lantern.clone().lerp(new THREE.Color(1, 1, 1), 0.5),
    emissiveMap: texture,
    emissiveIntensity: 0.1 + 0.32 * tokens.lanternOn,
  });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uTime;\nuniform float uWind;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        float ex = position.x / ${(width / 2).toFixed(2)};
        float hold = 1.0 - ex * ex;
        transformed.y -= hold * 0.32;
        float ripple = sin(position.x * 0.9 + uTime * 2.1) * 0.06 + sin(position.x * 2.3 - uTime * 3.4 + position.y * 1.5) * 0.025;
        transformed.z += (hold * 0.22 * sin(uTime * 0.9) + ripple) * uWind * (0.4 + 0.6 * hold);`,
      );
  };
  material.customProgramCacheKey = () => "quick-draw-banner";
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "banner";
  mesh.position.set(0, BANNER_Y, -8.6);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return { mesh, uniforms };
}

/** Ropes from the banner's corners to the two facades. */
export function bannerRopes(kit, tokens) {
  const rope = tokens.wood.clone().multiplyScalar(0.6);
  const y = BANNER_Y;
  const z = -8.6;
  for (const s of [-1, 1]) {
    for (const dy of [0.95, -0.95]) {
      const x0 = s * 5.6;
      const x1 = s * (FACADE - 0.3);
      const y0 = y + dy - (dy > 0 ? 0 : 0.32 * 0);
      const y1 = y + dy * 0.8 + 0.5;
      const len = Math.hypot(x1 - x0, y1 - y0);
      const g = cylinder(0.018, 0.018, len, 5);
      const ang = Math.atan2(y1 - y0, x1 - x0);
      kit.add("plain", g, rope, xf((x0 + x1) / 2, (y0 + y1) / 2, z, 0, 0, ang - Math.PI / 2));
    }
  }
}

export { FACADE };
