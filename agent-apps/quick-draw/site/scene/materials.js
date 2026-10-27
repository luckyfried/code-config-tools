// One named material per look, and the canvas textures they paint with: weathered siding, wood grain,
// the shop-sign atlas, and the saloon's canvas banner with the town's name.
import * as THREE from "three";
import { seeded } from "./kit.js";

function canvas(w, h) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

function texture(c, { repeat = true, color = true, aniso = 4 } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  if (color) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = aniso;
  t.needsUpdate = true;
  return t;
}

/** Horizontal siding, 1 m square: five boards with seams, grain, butt joints, nail heads, and weathering. */
function sidingCanvas() {
  const S = 512;
  const c = canvas(S, S);
  const g = c.getContext("2d");
  const rnd = seeded(7);
  const boards = 5;
  const bh = S / boards;
  for (let b = 0; b < boards; b += 1) {
    const y = b * bh;
    let x = 0;
    while (x < S) {
      const len = S * (0.35 + rnd() * 0.65);
      const tone = 196 + Math.floor(rnd() * 50);
      g.fillStyle = `rgb(${tone},${tone},${tone})`;
      g.fillRect(x, y, len, bh);
      // grain: long thin streaks
      for (let k = 0; k < 26; k += 1) {
        const gy = y + 3 + rnd() * (bh - 6);
        const a = 0.05 + rnd() * 0.12;
        g.strokeStyle = `rgba(40,30,20,${a})`;
        g.lineWidth = 0.6 + rnd() * 1.4;
        g.beginPath();
        g.moveTo(x, gy);
        const segs = 6;
        for (let s = 1; s <= segs; s += 1) g.lineTo(x + (len * s) / segs, gy + (rnd() - 0.5) * 3);
        g.stroke();
      }
      // knots
      if (rnd() < 0.55) {
        const kx = x + rnd() * len;
        const ky = y + bh * (0.3 + rnd() * 0.4);
        const kg = g.createRadialGradient(kx, ky, 0, kx, ky, 7 + rnd() * 6);
        kg.addColorStop(0, "rgba(50,32,20,0.55)");
        kg.addColorStop(1, "rgba(50,32,20,0)");
        g.fillStyle = kg;
        g.fillRect(kx - 16, ky - 16, 32, 32);
      }
      // butt joint and nails
      g.fillStyle = "rgba(25,18,12,0.7)";
      g.fillRect(x + len - 2, y, 2, bh);
      g.fillStyle = "rgba(30,24,20,0.8)";
      g.fillRect(x + len - 9, y + bh * 0.3, 3, 3);
      g.fillRect(x + len - 9, y + bh * 0.68, 3, 3);
      x += len;
    }
    // seam: a dark shadow line under each board's lip and a light edge on top
    g.fillStyle = "rgba(20,14,10,0.85)";
    g.fillRect(0, y + bh - 4, S, 4);
    g.fillStyle = "rgba(255,255,255,0.25)";
    g.fillRect(0, y, S, 2);
  }
  // weathering blotches
  for (let k = 0; k < 40; k += 1) {
    const x = rnd() * S;
    const y = rnd() * S;
    const r = 20 + rnd() * 70;
    const wg = g.createRadialGradient(x, y, 0, x, y, r);
    const dark = rnd() < 0.6;
    wg.addColorStop(0, dark ? "rgba(60,40,25,0.16)" : "rgba(255,250,240,0.14)");
    wg.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = wg;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  return c;
}

/** Fine wood grain and grime for posts, rails, barrels, and props. */
function grainCanvas() {
  const S = 256;
  const c = canvas(S, S);
  const g = c.getContext("2d");
  const rnd = seeded(11);
  g.fillStyle = "rgb(222,222,222)";
  g.fillRect(0, 0, S, S);
  for (let k = 0; k < 140; k += 1) {
    const x = rnd() * S;
    g.strokeStyle = `rgba(50,36,24,${0.04 + rnd() * 0.12})`;
    g.lineWidth = 0.5 + rnd() * 1.5;
    g.beginPath();
    g.moveTo(x, 0);
    for (let y = 0; y <= S; y += 32) g.lineTo(x + Math.sin(y * 0.05 + k) * 2, y);
    g.stroke();
  }
  for (let k = 0; k < 30; k += 1) {
    const x = rnd() * S;
    const y = rnd() * S;
    const r = 10 + rnd() * 40;
    const wg = g.createRadialGradient(x, y, 0, x, y, r);
    wg.addColorStop(0, "rgba(40,28,18,0.14)");
    wg.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = wg;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  return c;
}

/** Corrugated tin: vertical ribs with rust streaks. */
function tinCanvas() {
  const S = 256;
  const c = canvas(S, S);
  const g = c.getContext("2d");
  const rnd = seeded(5);
  for (let x = 0; x < S; x += 1) {
    const v = 170 + Math.round(Math.sin((x / S) * Math.PI * 2 * 12) * 40);
    g.fillStyle = `rgb(${v},${v},${v})`;
    g.fillRect(x, 0, 1, S);
  }
  for (let k = 0; k < 30; k += 1) {
    const x = rnd() * S;
    const len = 30 + rnd() * 160;
    const grad = g.createLinearGradient(0, 0, 0, len);
    grad.addColorStop(0, "rgba(120,60,20,0.45)");
    grad.addColorStop(1, "rgba(120,60,20,0)");
    g.fillStyle = grad;
    g.fillRect(x, 0, 2 + rnd() * 6, len);
  }
  return c;
}

const SIGNS = [
  "GENERAL STORE", "BANK", "SHERIFF", "HOTEL", "BARBER", "ASSAY OFFICE",
  "LIVERY", "DRY GOODS", "TELEGRAPH", "UNDERTAKER", "GUNSMITH", "SALOON",
];

/** Twelve painted shop signs in one atlas, each 1024 by 192; signRect(name) gives its UV rectangle. */
function signAtlas(colors) {
  const W = 2048;
  const H = 1152;
  const c = canvas(W, H);
  const g = c.getContext("2d");
  const rnd = seeded(23);
  const cols = 2;
  const sw = W / cols;
  const sh = H / 6;
  const rects = {};
  SIGNS.forEach((name, i) => {
    const x = (i % cols) * sw;
    const y = Math.floor(i / cols) * sh;
    const board = colors.boards[i % colors.boards.length];
    g.fillStyle = board;
    g.fillRect(x, y, sw, sh);
    // board planks
    for (let p = 1; p < 3; p += 1) {
      g.fillStyle = "rgba(0,0,0,0.25)";
      g.fillRect(x, y + (sh * p) / 3 - 2, sw, 3);
    }
    // painted border
    g.strokeStyle = colors.ink[i % colors.ink.length];
    g.lineWidth = 10;
    g.strokeRect(x + 22, y + 20, sw - 44, sh - 40);
    g.lineWidth = 3;
    g.strokeRect(x + 38, y + 34, sw - 76, sh - 68);
    // lettering
    const ink = colors.ink[i % colors.ink.length];
    const size = name.length > 10 ? 92 : 112;
    g.font = `${size}px Rye, Bitter, Georgia, serif`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillStyle = "rgba(0,0,0,0.35)";
    g.fillText(name, x + sw / 2 + 4, y + sh / 2 + 10);
    g.fillStyle = ink;
    g.fillText(name, x + sw / 2, y + sh / 2 + 6);
    // sun-bleach and wear
    for (let k = 0; k < 60; k += 1) {
      const wx = x + rnd() * sw;
      const wy = y + rnd() * sh;
      g.fillStyle = `rgba(${rnd() < 0.5 ? "255,240,220" : "40,25,15"},${0.05 + rnd() * 0.12})`;
      g.fillRect(wx, wy, 4 + rnd() * 50, 1 + rnd() * 3);
    }
    const eps = 2;
    rects[name] = { u0: (x + eps) / W, v0: 1 - (y + sh - eps) / H, u1: (x + sw - eps) / W, v1: 1 - (y + eps) / H };
  });
  return { canvas: c, rects };
}

/** The saloon's canvas banner: the town's name in big painted letters on stretched, weathered canvas. */
export function bannerCanvas(town, line, colors) {
  const W = 2048;
  const H = 400;
  const c = canvas(W, H);
  const g = c.getContext("2d");
  const rnd = seeded(31);
  g.fillStyle = colors.canvas;
  g.fillRect(0, 0, W, H);
  // weave
  for (let y = 0; y < H; y += 3) {
    g.fillStyle = `rgba(80,60,40,${0.03 + rnd() * 0.05})`;
    g.fillRect(0, y, W, 1);
  }
  for (let x = 0; x < W; x += 3) {
    g.fillStyle = `rgba(80,60,40,${0.02 + rnd() * 0.04})`;
    g.fillRect(x, 0, 1, H);
  }
  // hem and grommets
  g.fillStyle = "rgba(60,40,25,0.35)";
  g.fillRect(0, 0, W, 14);
  g.fillRect(0, H - 14, W, 14);
  for (let x = 40; x < W; x += 245) {
    g.fillStyle = "rgba(40,30,20,0.85)";
    g.beginPath();
    g.arc(x, 24, 9, 0, Math.PI * 2);
    g.fill();
  }
  // lettering, fit to width
  const name = town.toUpperCase();
  let size = 230;
  g.font = `${size}px Rye, Bitter, Georgia, serif`;
  while (g.measureText(name).width > W - 160 && size > 60) {
    size -= 6;
    g.font = `${size}px Rye, Bitter, Georgia, serif`;
  }
  g.textAlign = "center";
  g.textBaseline = "alphabetic";
  const base = H * 0.66;
  g.fillStyle = colors.shadow;
  g.fillText(name, W / 2 + 7, base + 7);
  g.fillStyle = colors.letter;
  g.fillText(name, W / 2, base);
  g.font = `64px Bitter, Georgia, serif`;
  g.fillStyle = colors.line;
  g.fillText(line, W / 2, H - 46);
  // dust and stains
  for (let k = 0; k < 50; k += 1) {
    const x = rnd() * W;
    const y = rnd() * H;
    const r = 30 + rnd() * 120;
    const sg = g.createRadialGradient(x, y, 0, x, y, r);
    sg.addColorStop(0, `rgba(120,80,40,${0.05 + rnd() * 0.1})`);
    sg.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = sg;
    g.fillRect(x - r, y - r, r * 2, r * 2);
  }
  return c;
}

/** A soft round sprite for dust, smoke, and glows. */
export function softDot(size = 64, hard = 0) {
  const c = canvas(size, size);
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(Math.min(0.9, 0.2 + hard), "rgba(255,255,255,0.55)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  return texture(c, { repeat: false, color: false, aniso: 1 });
}

export function createMaterials(tokens) {
  const siding = texture(sidingCanvas());
  const sidingBump = texture(sidingCanvas(), { color: false });
  const grain = texture(grainCanvas());
  const tin = texture(tinCanvas());
  const atlas = signAtlas({
    boards: ["#e8dcc0", "#2b2420", "#6e2a20", "#e4d2a6", "#30403c", "#c8a466"],
    ink: ["#2a1a10", "#ecdcb4", "#f2e2be", "#6e1e14", "#efe0bc", "#2a1a10"],
  });
  const signs = texture(atlas.canvas, { repeat: false, aniso: 8 });

  const lantern = tokens.lantern.clone();
  const lanternOn = tokens.lanternOn;

  const materials = {
    wood: new THREE.MeshStandardMaterial({ vertexColors: true, map: siding, bumpMap: sidingBump, bumpScale: 1.2, roughness: 0.92, envMapIntensity: 0.5 }),
    plain: new THREE.MeshStandardMaterial({ vertexColors: true, map: grain, roughness: 0.86, envMapIntensity: 0.5 }),
    tin: new THREE.MeshStandardMaterial({ vertexColors: true, map: tin, roughness: 0.55, metalness: 0.35, envMapIntensity: 0.8, side: THREE.DoubleSide }),
    metal: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.38, metalness: 0.75, envMapIntensity: 1.1 }),
    glass: new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.12,
      metalness: 0.1,
      envMapIntensity: 1.4,
      emissive: lantern.clone().multiplyScalar(0.55 * lanternOn),
    }),
    glow: new THREE.MeshBasicMaterial({ vertexColors: true, color: lantern.clone().multiplyScalar(0.6 + 3.2 * lanternOn) }),
    signs: new THREE.MeshStandardMaterial({ map: signs, roughness: 0.85, envMapIntensity: 0.4 }),
    cloth: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, side: THREE.DoubleSide, envMapIntensity: 0.4 }),
  };
  return { materials, signRect: (name) => atlas.rects[name], textures: { siding, grain, tin, signs } };
}

/** Recolors the materials that read tokens directly when the scheme changes. */
export function retintMaterials(materials, tokens) {
  materials.glass.emissive.copy(tokens.lantern).multiplyScalar(0.55 * tokens.lanternOn);
  materials.glow.color.copy(tokens.lantern).multiplyScalar(0.6 + 3.2 * tokens.lanternOn);
}
