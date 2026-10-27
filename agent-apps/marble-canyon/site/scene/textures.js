// Textures painted at load: the sandstone normal map (layered tileable noise), the rock strata bands from the
// theme's palette, the track's polished-stone detail, the boost chevrons, the marble's inner swirl, and the
// soft round sprite the particles and the contact shadow use.
import { CanvasTexture, ClampToEdgeWrapping, LinearMipmapLinearFilter, NoColorSpace, RepeatWrapping, SRGBColorSpace } from "three";
import { createRng } from "../game/rng.js";

const canvas = (w, h) => {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
};

// Tileable value noise on a periodic lattice.
function tileNoise(size, period, rng) {
  const lattice = new Float32Array(period * period);
  for (let i = 0; i < lattice.length; i += 1) lattice[i] = rng();
  const out = new Float32Array(size * size);
  const scale = period / size;
  for (let y = 0; y < size; y += 1) {
    const fy = y * scale;
    const y0 = Math.floor(fy);
    const ty = fy - y0;
    const sy = ty * ty * (3 - 2 * ty);
    const r0 = (y0 % period) * period;
    const r1 = ((y0 + 1) % period) * period;
    for (let x = 0; x < size; x += 1) {
      const fx = x * scale;
      const x0 = Math.floor(fx);
      const tx = fx - x0;
      const sx = tx * tx * (3 - 2 * tx);
      const c0 = x0 % period;
      const c1 = (x0 + 1) % period;
      const a = lattice[r0 + c0] + (lattice[r0 + c1] - lattice[r0 + c0]) * sx;
      const b = lattice[r1 + c0] + (lattice[r1 + c1] - lattice[r1 + c0]) * sx;
      out[y * size + x] = a + (b - a) * sy;
    }
  }
  return out;
}

export function sandstoneNormal(size, seed = 7) {
  const rng = createRng(seed);
  const height = new Float32Array(size * size);
  const layers = [
    [4, 0.5],
    [8, 0.28],
    [16, 0.14],
    [32, 0.08],
    [64, 0.04],
  ];
  for (const [period, weight] of layers) {
    const n = tileNoise(size, period, rng);
    for (let i = 0; i < height.length; i += 1) height[i] += n[i] * weight;
  }
  // Wind-cut bedding: thin horizontal grooves that wander with the low octave.
  const bands = tileNoise(size, 6, rng);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const i = y * size + x;
      const v = (y / size) * 22 + bands[i] * 3;
      height[i] += Math.pow(Math.abs(Math.sin(v * Math.PI)), 6) * -0.12;
    }
  }
  const c = canvas(size, size);
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(size, size);
  const strength = 5.5;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const l = height[y * size + ((x - 1 + size) % size)];
      const r = height[y * size + ((x + 1) % size)];
      const u = height[((y - 1 + size) % size) * size + x];
      const d = height[((y + 1) % size) * size + x];
      let nx = (l - r) * strength;
      let ny = (u - d) * strength;
      let nz = 1;
      const len = Math.hypot(nx, ny, nz);
      nx /= len;
      ny /= len;
      nz /= len;
      const o = (y * size + x) * 4;
      img.data[o] = (nx * 0.5 + 0.5) * 255;
      img.data[o + 1] = (ny * 0.5 + 0.5) * 255;
      img.data[o + 2] = (nz * 0.5 + 0.5) * 255;
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const tex = new CanvasTexture(c);
  tex.wrapS = tex.wrapT = RepeatWrapping;
  tex.colorSpace = NoColorSpace;
  tex.anisotropy = 4;
  return tex;
}

// Rock strata: bands of the theme's five rock colors in a fixed sequence of thicknesses, read by height.
export class StrataTexture {
  constructor(seed = 11) {
    this.canvas = canvas(1024, 4);
    this.texture = new CanvasTexture(this.canvas);
    this.texture.wrapS = RepeatWrapping;
    this.texture.wrapT = ClampToEdgeWrapping;
    this.texture.colorSpace = SRGBColorSpace;
    this.texture.channel = 1;
    const rng = createRng(seed);
    this.bands = [];
    let x = 0;
    while (x < 1024) {
      const w = Math.round(rng.range(10, 70));
      this.bands.push({ x, w, tone: Math.floor(rng() * 5), shade: rng.range(-0.06, 0.06), line: rng() < 0.35 });
      x += w;
    }
  }

  paint(colors) {
    const ctx = this.canvas.getContext("2d");
    for (const band of this.bands) {
      const c = colors[band.tone];
      const k = 1 + band.shade;
      ctx.fillStyle = `rgb(${Math.min(255, c.r * 255 * k)} ${Math.min(255, c.g * 255 * k)} ${Math.min(255, c.b * 255 * k)})`;
      ctx.fillRect(band.x, 0, band.w, 4);
      if (band.line) {
        ctx.fillStyle = `rgb(${c.r * 160} ${c.g * 160} ${c.b * 160})`;
        ctx.fillRect(band.x, 0, 2, 4);
      }
    }
    this.texture.needsUpdate = true;
  }
}

// The track's surface detail: near-white polished stone with seams every tile, multiplied by the theme color.
export function trackDetail(seed = 3) {
  const w = 256;
  const h = 256;
  const c = canvas(w, h);
  const ctx = c.getContext("2d");
  const rng = createRng(seed);
  const img = ctx.createImageData(w, h);
  const n = tileNoise(256, 16, rng);
  const fine = tileNoise(256, 64, rng);
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 1) {
      const i = y * w + x;
      let v = 0.9 + n[i] * 0.07 + fine[i] * 0.05;
      const edge = Math.min(x, w - 1 - x) / w;
      if (edge < 0.035) v *= 0.82 + edge * 4;
      if (y < 3) v *= 0.78;
      const o = i * 4;
      const g = Math.min(255, v * 255);
      img.data[o] = g;
      img.data[o + 1] = g;
      img.data[o + 2] = g;
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  const tex = new CanvasTexture(c);
  tex.wrapS = ClampToEdgeWrapping;
  tex.wrapT = RepeatWrapping;
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 8;
  tex.minFilter = LinearMipmapLinearFilter;
  return tex;
}

// Boost chevrons: bright arrows on a dark field, white so the material color tints them.
export function chevrons() {
  const c = canvas(128, 128);
  const ctx = c.getContext("2d");
  ctx.fillStyle = "rgb(40 40 40)";
  ctx.fillRect(0, 0, 128, 128);
  ctx.fillStyle = "rgb(255 255 255)";
  ctx.beginPath();
  ctx.moveTo(14, 96);
  ctx.lineTo(64, 40);
  ctx.lineTo(114, 96);
  ctx.lineTo(90, 96);
  ctx.lineTo(64, 68);
  ctx.lineTo(38, 96);
  ctx.closePath();
  ctx.fill();
  const tex = new CanvasTexture(c);
  tex.wrapS = ClampToEdgeWrapping;
  tex.wrapT = RepeatWrapping;
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

// The swirl inside the marble: ribbons of the chosen color with pale cores, on transparent ground.
export function swirl(hex) {
  const w = 512;
  const h = 256;
  const c = canvas(w, h);
  const ctx = c.getContext("2d");
  const ribbons = 3;
  for (let r = 0; r < ribbons; r += 1) {
    const phase = (r / ribbons) * w;
    for (let pass = 0; pass < 2; pass += 1) {
      ctx.beginPath();
      for (let x = -20; x <= w + 20; x += 8) {
        const y = h * 0.5 + Math.sin(((x + phase) / w) * Math.PI * 2) * h * 0.32;
        if (x === -20) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.lineCap = "round";
      ctx.strokeStyle = pass === 0 ? hex : "rgb(255 255 255 / 0.75)";
      ctx.lineWidth = pass === 0 ? 44 : 7;
      ctx.stroke();
    }
  }
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  tex.wrapS = RepeatWrapping;
  tex.anisotropy = 4;
  return tex;
}

// A soft round dot, white, for particles and the contact shadow.
export function softDot() {
  const c = canvas(64, 64);
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgb(255 255 255 / 1)");
  g.addColorStop(0.45, "rgb(255 255 255 / 0.55)");
  g.addColorStop(1, "rgb(255 255 255 / 0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  return tex;
}

// The marble's contact shadow as an alpha map: a grey falloff on black, since alpha maps read the green channel.
// Dense under the marble and gone well inside the square, so no edge of the quad ever shows.
export function contactBlob() {
  const c = canvas(128, 128);
  const ctx = c.getContext("2d");
  ctx.fillStyle = "rgb(0 0 0)";
  ctx.fillRect(0, 0, 128, 128);
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 60);
  for (let i = 0; i <= 12; i += 1) {
    const x = i / 12;
    const k = Math.max(0, Math.min(1, (x - 0.38) / 0.62));
    const v = Math.round(255 * (1 - k * k * (3 - 2 * k)) ** 1.6);
    g.addColorStop(x, `rgb(${v} ${v} ${v})`);
  }
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return new CanvasTexture(c);
}
