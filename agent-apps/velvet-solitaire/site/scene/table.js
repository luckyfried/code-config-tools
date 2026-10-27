// The table: a felt plane with a procedural fiber normal map and cloth sheen, the printed
// markings on it, a lacquered wood rail, one warm key light, a cool rim, and the studio
// environment the card lacquer reflects. Every color comes from the theme's tokens.

import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { SUIT_PATHS } from "../faces.js";

function seeded(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

// Smooth value noise on a wrapping grid, for mottling and wood grain.
function valueNoise(size, cells, seed) {
  const rand = seeded(seed);
  const grid = Array.from({ length: cells * cells }, () => rand());
  const at = (x, y) => grid[((y % cells) + cells) % cells * cells + (((x % cells) + cells) % cells)];
  const out = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const fx = (x / size) * cells;
      const fy = (y / size) * cells;
      const ix = Math.floor(fx);
      const iy = Math.floor(fy);
      let tx = fx - ix;
      let ty = fy - iy;
      tx = tx * tx * (3 - 2 * tx);
      ty = ty * ty * (3 - 2 * ty);
      const a = at(ix, iy) + (at(ix + 1, iy) - at(ix, iy)) * tx;
      const b = at(ix, iy + 1) + (at(ix + 1, iy + 1) - at(ix, iy + 1)) * tx;
      out[y * size + x] = a + (b - a) * ty;
    }
  }
  return out;
}

/** The felt's fiber normal map: thousands of short crossing fibers turned into a tangent-space normal map. */
function feltNormalMap() {
  const size = 512;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, size, size);
  const rand = seeded(7);
  ctx.lineCap = "round";
  for (let i = 0; i < 9000; i += 1) {
    const x = rand() * size;
    const y = rand() * size;
    const a = rand() * Math.PI * 2;
    const len = 3 + rand() * 9;
    ctx.strokeStyle = `rgba(255,255,255,${0.05 + rand() * 0.12})`;
    ctx.lineWidth = 0.6 + rand() * 0.9;
    for (const ox of [-size, 0, size]) {
      for (const oy of [-size, 0, size]) {
        if (x + ox < -12 || x + ox > size + 12 || y + oy < -12 || y + oy > size + 12) continue;
        ctx.beginPath();
        ctx.moveTo(x + ox, y + oy);
        ctx.quadraticCurveTo(x + ox + Math.cos(a + 0.6) * len * 0.5, y + oy + Math.sin(a + 0.6) * len * 0.5, x + ox + Math.cos(a) * len, y + oy + Math.sin(a) * len);
        ctx.stroke();
      }
    }
  }
  const src = ctx.getImageData(0, 0, size, size).data;
  const fine = valueNoise(size, 96, 11);
  const h = new Float32Array(size * size);
  for (let i = 0; i < h.length; i += 1) h[i] = src[i * 4] / 255 + fine[i] * 0.35;
  const out = ctx.createImageData(size, size);
  const H = (x, y) => h[((y + size) % size) * size + ((x + size) % size)];
  const strength = 2.2;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = (H(x + 1, y) - H(x - 1, y)) * strength;
      const dy = (H(x, y + 1) - H(x, y - 1)) * strength;
      const len = Math.hypot(dx, dy, 1);
      const o = (y * size + x) * 4;
      out.data[o] = ((-dx / len) * 0.5 + 0.5) * 255;
      out.data[o + 1] = ((dy / len) * 0.5 + 0.5) * 255;
      out.data[o + 2] = ((1 / len) * 0.5 + 0.5) * 255;
      out.data[o + 3] = 255;
    }
  }
  ctx.putImageData(out, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

/** Low, soft mottling so the baize is never one flat color. */
function feltMottle() {
  const size = 256;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  const a = valueNoise(size, 6, 3);
  const b = valueNoise(size, 22, 5);
  const img = ctx.createImageData(size, size);
  for (let i = 0; i < a.length; i += 1) {
    const v = 0.9 + a[i] * 0.07 + b[i] * 0.03;
    img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v * 255;
    img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** Wood grain running along the rail, drawn in the theme's two wood tones. */
function woodCanvas(light, dark) {
  const w = 1024;
  const h = 256;
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");
  const n = valueNoise(256, 8, 19);
  const fine = valueNoise(256, 64, 23);
  const L = new THREE.Color(light);
  const D = new THREE.Color(dark);
  const img = ctx.createImageData(w, h);
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      const nx = Math.floor((x / w) * 256) % 256;
      const ny = Math.floor((y / h) * 256) % 256;
      const warp = n[ny * 256 + nx] * 9;
      const ring = Math.sin((y / h) * 46 + warp * 2.2 + Math.sin(x / 140) * 0.8);
      const streak = fine[ny * 256 + ((nx * 3) % 256)] * 0.35;
      let t = Math.pow(Math.abs(ring), 3.5) * 0.75 + streak * 0.6;
      t = Math.min(1, t);
      const o = (y * w + x) * 4;
      img.data[o] = (L.r + (D.r - L.r) * t) * 255;
      img.data[o + 1] = (L.g + (D.g - L.g) * t) * 255;
      img.data[o + 2] = (L.b + (D.b - L.b) * t) * 255;
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return c;
}

/** Loads the studio environment the card lacquer and the rail reflect. */
export async function loadEnvironment(renderer, url) {
  const hdr = await new HDRLoader().loadAsync(url);
  hdr.mapping = THREE.EquirectangularReflectionMapping;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromEquirectangular(hdr).texture;
  hdr.dispose();
  pmrem.dispose();
  return env;
}

export function createTable() {
  const group = new THREE.Group();
  const normalMap = feltNormalMap();
  const mottle = feltMottle();
  const felt = new THREE.MeshPhysicalMaterial({
    color: 0x1d5b3f,
    map: mottle,
    normalMap,
    normalScale: new THREE.Vector2(0.55, 0.55),
    roughness: 0.92,
    metalness: 0,
    sheen: 1,
    sheenRoughness: 0.42,
    sheenColor: new THREE.Color(0x6fc497),
    envMapIntensity: 0.25,
  });
  const feltMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), felt);
  feltMesh.renderOrder = 0;
  group.add(feltMesh);

  // The printed markings: pile outlines and the table's rule line, in foil or ink.
  const printCanvas = document.createElement("canvas");
  const printTexture = new THREE.CanvasTexture(printCanvas);
  printTexture.colorSpace = THREE.SRGBColorSpace;
  const printMaterial = new THREE.MeshPhysicalMaterial({
    map: printTexture,
    transparent: true,
    depthWrite: false,
    roughness: 0.4,
    metalness: 0.55,
    envMapIntensity: 1,
  });
  const printMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), printMaterial);
  printMesh.position.z = 0.05;
  printMesh.renderOrder = 0.5;
  group.add(printMesh);

  // The lamp on the cloth: a warm pool where the key falls, the cloth darkening toward the
  // edges and the rail, and a broad sheen raking across the nap. Drawn over the felt and its
  // print as premultiplied light (added) and shade (laid over), so an orthographic still shows it.
  const poolMaterial = new THREE.ShaderMaterial({
    uniforms: {
      uWarm: { value: new THREE.Color() },
      uDeep: { value: new THREE.Color() },
      uSheen: { value: new THREE.Color() },
      uCenter: { value: new THREE.Vector2() },
      uRadius: { value: new THREE.Vector2(1, 1) },
      uPool: { value: 0.1 },
      uFall: { value: 0.6 },
      uSheenPower: { value: 0.1 },
      uNap: { value: normalMap },
      uNapRepeat: { value: new THREE.Vector2(1, 1) },
    },
    vertexShader: `
varying vec2 vPos;
varying vec2 vUv;
void main() {
  vUv = uv;
  vPos = (modelMatrix * vec4(position, 1.0)).xy;
  gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
}`,
    fragmentShader: `
uniform vec3 uWarm;
uniform vec3 uDeep;
uniform vec3 uSheen;
uniform vec2 uCenter;
uniform vec2 uRadius;
uniform float uPool;
uniform float uFall;
uniform float uSheenPower;
uniform sampler2D uNap;
uniform vec2 uNapRepeat;
varying vec2 vPos;
varying vec2 vUv;
void main() {
  vec2 d = (vPos - uCenter) / uRadius;
  float r = length(d);
  float pool = exp(-r * r * 2.2);
  float fall = smoothstep(0.3, 1.3, r);
  vec3 n = texture2D(uNap, vUv * uNapRepeat).xyz - 0.5;
  float nap = clamp(0.55 + length(n.xy) * 3.2, 0.0, 1.6);
  float across = dot(d, vec2(0.78, -0.62)) + 0.18;
  float band = exp(-across * across * 5.0) * (1.0 - fall * 0.85);
  vec3 add = uWarm * pool * uPool + uSheen * band * nap * uSheenPower;
  float shade = fall * uFall;
  gl_FragColor = vec4(add * (1.0 - shade) + uDeep * shade, shade);
}`,
    transparent: true,
    depthWrite: false,
    toneMapped: false,
    blending: THREE.CustomBlending,
    blendSrc: THREE.OneFactor,
    blendDst: THREE.OneMinusSrcAlphaFactor,
  });
  const poolMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), poolMaterial);
  poolMesh.position.z = 0.08;
  poolMesh.renderOrder = 0.75;
  group.add(poolMesh);

  const woodMaterial = new THREE.MeshPhysicalMaterial({ roughness: 0.5, clearcoat: 0.85, clearcoatRoughness: 0.18, envMapIntensity: 1.4 });
  const woodMaterialV = woodMaterial.clone();
  const rails = [];

  const key = new THREE.SpotLight(0xffe2b8, 3, 0, Math.PI / 4, 1, 0);
  const rim = new THREE.DirectionalLight(0x9cc4ff, 0.6);
  const ambient = new THREE.HemisphereLight(0xfff4e0, 0x203028, 0.6);
  group.add(key, key.target, rim, rim.target, ambient);

  const table = {
    group,
    felt,
    feltMesh,
    printCanvas,
    printTexture,
    printMaterial,
    printMesh,
    poolMaterial,
    poolMesh,
    key,
    rim,
    ambient,
    rails,
    woodMaterial,
    woodMaterialV,
  };
  return table;
}

/** Sizes the felt and the print to the view (in table units) and aims the lights at the card area. */
export function fitTable(table, view) {
  const { width, height, cx, cy, areaW, areaH } = view;
  table.feltMesh.scale.set(width * 1.3, height * 1.6, 1);
  table.feltMesh.position.set(cx, cy, 0);
  const rep = Math.max(width, height) / 150;
  table.felt.normalMap.repeat.set((width * 1.3) / 150, (height * 1.6) / 150);
  table.felt.map.repeat.set(rep * 0.35, rep * 0.35 * ((height * 1.6) / (width * 1.3)));
  table.printMesh.scale.set(width, height, 1);
  table.printMesh.position.set(view.printX, view.printY, 0.05);
  table.poolMesh.scale.set(width * 1.3, height * 1.6, 1);
  table.poolMesh.position.set(cx, cy, 0.08);
  const pu = table.poolMaterial.uniforms;
  pu.uNapRepeat.value.copy(table.felt.normalMap.repeat);
  pu.uCenter.value.set(view.areaX - areaW * 0.06, view.areaY + areaH * 0.1);
  pu.uRadius.value.set(areaW * 0.6, areaH * 0.62);
  const span = Math.max(areaW, areaH);
  // The key hangs above and left of the table, placed so its mirror spot on a flat card falls
  // just past the top edge: a card lifted and tilted toward it catches the light.
  const lampHeight = span * 1.15;
  const hotY = view.areaY + areaH * 0.5 + span * 0.05;
  table.key.position.set(view.areaX - areaW * 0.12, hotY + lampHeight * Math.tan((14 * Math.PI) / 180), lampHeight);
  table.key.target.position.set(view.areaX + areaW * 0.04, view.areaY - areaH * 0.05, 0);
  table.rim.position.set(view.areaX + areaW * 0.6, view.areaY - areaH * 1.2, span * 0.35);
  table.rim.target.position.set(view.areaX, view.areaY, 0);
  table.span = span;
}

/** Applies the theme's palette and light to the felt, the print, the rail, and the lights. */
export function paintTable(table, tok) {
  table.felt.color.set(tok.color("--felt"));
  table.felt.sheenColor.set(tok.color("--felt-sheen"));
  table.felt.sheenRoughness = tok.number("--felt-sheen-roughness", 0.42);
  table.printMaterial.metalness = tok.number("--print-metal", 0.55);
  // The pool's colors go straight onto the drawn frame, so they stay in display (sRGB) values.
  const pu = table.poolMaterial.uniforms;
  // Warm in every theme, even under a cool key: the lamp's pool is tungsten.
  pu.uWarm.value.set(tok.color("--light-key")).lerp(new THREE.Color(0xffc98a), 0.5).convertLinearToSRGB();
  pu.uDeep.value.set(tok.color("--felt-deep")).convertLinearToSRGB();
  pu.uSheen.value.set(tok.color("--felt-sheen")).convertLinearToSRGB();
  pu.uPool.value = tok.number("--felt-pool-power", 0.12);
  pu.uFall.value = tok.number("--felt-falloff", 0.6);
  pu.uSheenPower.value = tok.number("--felt-sheen-power", 0.1);
  table.key.color.set(tok.color("--light-key"));
  table.key.intensity = tok.number("--light-key-power", 3);
  table.key.angle = tok.number("--light-pool", 0.6) * 0.62;
  table.key.penumbra = 1;
  table.rim.color.set(tok.color("--light-rim"));
  table.rim.intensity = tok.number("--light-rim-power", 0.6);
  table.ambient.color.set(tok.color("--light-sky"));
  table.ambient.groundColor.set(tok.color("--light-ground"));
  table.ambient.intensity = tok.number("--light-ambient-power", 0.6);
  const canvas = woodCanvas(tok.color("--rail-wood"), tok.color("--rail-grain"));
  for (const [mat, vertical] of [[table.woodMaterial, false], [table.woodMaterialV, true]]) {
    if (mat.map) mat.map.dispose();
    const t = new THREE.CanvasTexture(canvas);
    t.colorSpace = THREE.SRGBColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    if (vertical) {
      t.center.set(0.5, 0.5);
      t.rotation = Math.PI / 2;
    }
    mat.map = t;
    mat.needsUpdate = true;
  }
}

/** Rebuilds the rail blocks under the page's rail panels: rects in table units { x, y, w, h }. */
export function setRails(table, rects) {
  for (const r of table.rails) {
    table.group.remove(r);
    r.geometry.dispose();
  }
  table.rails.length = 0;
  for (const rect of rects) {
    const depth = 44;
    const vertical = rect.h > rect.w;
    const geo = new RoundedBoxGeometry(rect.w, rect.h, depth, 4, Math.min(10, rect.w / 2.2, rect.h / 2.2));
    const mesh = new THREE.Mesh(geo, vertical ? table.woodMaterialV : table.woodMaterial);
    mesh.position.set(rect.x, rect.y, depth / 2 - 6);
    const tex = mesh.material.map;
    if (tex) tex.repeat.set(vertical ? Math.max(1, rect.h / 400) : Math.max(1, rect.w / 400), 1);
    mesh.renderOrder = 0;
    table.group.add(mesh);
    table.rails.push(mesh);
  }
}

/**
 * Paints the felt's printed markings for a layout: an outline for every pile, a ring on
 * the stock, an A on each foundation, and the rule line arched across the bottom.
 */
export function paintPrint(table, layout, view, tok, { title, rule, stockState }) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const c = table.printCanvas;
  c.width = Math.round(view.pxW * ratio);
  c.height = Math.round(view.pxH * ratio);
  const ctx = c.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, view.pxW, view.pxH);
  const ink = tok.color("--felt-print");
  const w = layout.cardW;
  const h = layout.cardH;
  ctx.strokeStyle = ink;
  ctx.fillStyle = ink;
  const outline = (pile, alpha) => {
    const a = layout.anchors[pile];
    ctx.globalAlpha = alpha;
    ctx.lineWidth = Math.max(1, w * 0.022);
    ctx.beginPath();
    ctx.roundRect(a.x - w / 2 + 1, a.y - h / 2 + 1, w - 2, h - 2, w * 0.07);
    ctx.stroke();
  };
  for (const p of ["stock", "waste", "f0", "f1", "f2", "f3", "t0", "t1", "t2", "t3", "t4", "t5", "t6"]) outline(p, p === "waste" ? 0.32 : 0.5);
  ctx.globalAlpha = 0.5;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const display = tok.raw("--font-display");
  for (let f = 0; f < 4; f += 1) {
    const a = layout.anchors[`f${f}`];
    ctx.font = `italic 400 ${h * 0.42}px ${display}`;
    ctx.fillText("A", a.x, a.y + h * 0.02);
  }
  for (let t = 0; t < 7; t += 1) {
    const a = layout.anchors[`t${t}`];
    ctx.globalAlpha = 0.28;
    ctx.font = `italic 400 ${h * 0.3}px ${display}`;
    ctx.fillText("K", a.x, a.y + h * 0.02);
  }
  // The stock's ring: a circle to turn the waste over again, a bar when the passes are spent.
  const s = layout.anchors.stock;
  ctx.globalAlpha = 0.55;
  ctx.lineWidth = Math.max(1.5, w * 0.05);
  ctx.beginPath();
  ctx.arc(s.x, s.y, w * 0.24, -Math.PI * 0.35, Math.PI * 1.45);
  ctx.stroke();
  if (stockState === "spent") {
    ctx.beginPath();
    ctx.moveTo(s.x - w * 0.24, s.y + w * 0.24);
    ctx.lineTo(s.x + w * 0.24, s.y - w * 0.24);
    ctx.stroke();
  } else {
    const ang = Math.PI * 1.45;
    const ex = s.x + Math.cos(ang) * w * 0.24;
    const ey = s.y + Math.sin(ang) * w * 0.24;
    ctx.beginPath();
    ctx.moveTo(ex + w * 0.1, ey - w * 0.02);
    ctx.lineTo(ex, ey);
    ctx.lineTo(ex + w * 0.03, ey + w * 0.1);
    ctx.stroke();
  }

  // The table's seal, printed where a casino prints its name: a ring with the four suits,
  // the title arched over it and the rule under it, centered in the open felt between the
  // dealt columns and the button that deals a visitor in. Play covers it as the columns grow.
  const area = layout.area;
  const cx = area.x + area.w / 2;
  const openTop = layout.tabTop + h + 6 * layout.downGap + h * 0.08;
  const clear = layout.compact ? 64 : area.h < 560 ? 80 : 64;
  const openBottom = layout.bottom - clear;
  const openH = openBottom - openTop;
  const mid = (openTop + openBottom) / 2;
  const R = Math.min(area.w * (layout.compact ? 0.21 : 0.08), openH / 2.75);
  const pipAt = (suit, x, y, size) => {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(size / 100, size / 100);
    ctx.translate(-50, -50);
    ctx.fill(new Path2D(SUIT_PATHS[suit]));
    ctx.restore();
  };
  const done = () => {
    ctx.globalAlpha = 1;
    table.printTexture.needsUpdate = true;
  };
  if (openH < 26) return done();
  if (R < 40) {
    // A short table (a phone on its side): the seal prints as one line, the title between the suits.
    const size = Math.min(openH * 0.62, area.w * 0.045, 30);
    ctx.font = `italic 400 ${size}px ${display}`;
    const tw = ctx.measureText(title).width;
    const pip = size * 0.62;
    const step = pip * 1.25;
    ctx.globalAlpha = 0.6;
    ctx.fillText(title, cx, mid);
    ctx.globalAlpha = 0.5;
    const edge = tw / 2 + size * 0.55;
    pipAt(0, cx - edge - step * 1.5, mid, pip);
    pipAt(1, cx - edge - step * 0.5, mid, pip);
    pipAt(2, cx + edge + step * 0.5, mid, pip);
    pipAt(3, cx + edge + step * 1.5, mid, pip);
    ctx.globalAlpha = 0.42;
    ctx.lineWidth = Math.max(1, size * 0.05);
    const lineW = tw / 2 + size * 0.55 + step * 2;
    for (const dy of [-size * 0.82, size * 0.82]) {
      ctx.beginPath();
      ctx.moveTo(cx - lineW, mid + dy);
      ctx.lineTo(cx + lineW, mid + dy);
      ctx.stroke();
    }
    return done();
  }
  // The title arches higher over the ring than the rule hangs under it, so the ring sits a touch low.
  const cy = mid + R * 0.08;
  ctx.globalAlpha = 0.42;
  ctx.lineWidth = Math.max(1.5, R * 0.035);
  ctx.beginPath();
  ctx.arc(cx, cy, R, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = Math.max(1, R * 0.014);
  ctx.beginPath();
  ctx.arc(cx, cy, R * 0.86, 0, Math.PI * 2);
  ctx.stroke();
  ctx.globalAlpha = 0.5;
  const pip = R * 0.34;
  for (const [suit, dx, dy] of [[0, 0, -0.36], [1, 0.36, 0], [2, 0, 0.36], [3, -0.36, 0]]) pipAt(suit, cx + dx * R, cy + dy * R, pip);
  const around = (text, font, radius, top, spacing, alpha) => {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.font = font;
    ctx.textBaseline = top ? "alphabetic" : "top";
    const chars = [...text];
    const widths = chars.map((ch) => ctx.measureText(ch).width + spacing);
    const total = widths.reduce((sum, v) => sum + v, 0);
    if (total / radius > Math.PI * 1.4) {
      ctx.restore();
      return;
    }
    let ang = -total / 2 / radius;
    for (let i = 0; i < chars.length; i += 1) {
      const a = ang + widths[i] / 2 / radius;
      ctx.save();
      if (top) {
        ctx.translate(cx + Math.sin(a) * radius, cy - Math.cos(a) * radius);
        ctx.rotate(a);
      } else {
        ctx.translate(cx + Math.sin(a) * radius, cy + Math.cos(a) * radius);
        ctx.rotate(-a);
      }
      ctx.fillText(chars[i], 0, 0);
      ctx.restore();
      ang += widths[i] / radius;
    }
    ctx.restore();
  };
  const titleSize = Math.max(13, R * 0.3);
  const ruleSize = Math.max(9, R * 0.135);
  around(title, `italic 400 ${titleSize}px ${display}`, R * 1.12, true, titleSize * 0.02, 0.6);
  around(rule, `400 ${ruleSize}px ${display}`, R * 1.1, false, ruleSize * 0.12, 0.55);
  done();
}
