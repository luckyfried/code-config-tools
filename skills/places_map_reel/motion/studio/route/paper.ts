// The film's one paper: a tiling sheet of fine grain, short fibres and a light mottle, drawn from a fixed sequence so
// every render draws the same. The land, the sea, a card's strip and the closer's strip all take it, so the map is the
// same stock as the paper the names stand on.
import * as THREE from 'three';

/** Wall px one tile of the paper spans. */
export const SHEET = 420;

let sheet: THREE.Texture | null = null;

const make = () => {
  const N = 512;
  const cv = document.createElement('canvas');
  cv.width = N;
  cv.height = N;
  const g = cv.getContext('2d')!;
  g.fillStyle = 'rgb(236,236,236)';
  g.fillRect(0, 0, N, N);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  // the mottle: soft discs of light and shade, each drawn with its wrapped copies so the tile has no seam
  for (let k = 0; k < 60; k++) {
    const x = rnd() * N, y = rnd() * N, r = 60 + rnd() * 160;
    const c = rnd() > 0.5 ? '255,255,255' : '150,150,150';
    const a = 0.02 + rnd() * 0.025;
    for (const ox of [-N, 0, N]) for (const oy of [-N, 0, N]) {
      const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
      gr.addColorStop(0, `rgba(${c},${a})`);
      gr.addColorStop(1, `rgba(${c},0)`);
      g.fillStyle = gr;
      g.fillRect(x + ox - r, y + oy - r, 2 * r, 2 * r);
    }
  }
  // the fibres: short thin strokes at every angle, a little lighter or darker than the sheet
  g.lineCap = 'round';
  for (let k = 0; k < 1400; k++) {
    const x = rnd() * N, y = rnd() * N, len = 5 + rnd() * 26, a = rnd() * Math.PI * 2, bend = (rnd() - 0.5) * 8;
    g.strokeStyle = rnd() > 0.45 ? `rgba(120,110,100,${0.05 + rnd() * 0.07})` : `rgba(255,255,255,${0.08 + rnd() * 0.1})`;
    g.lineWidth = 0.5 + rnd() * 0.9;
    for (const ox of [-N, 0, N]) for (const oy of [-N, 0, N]) {
      const x0 = x + ox, y0 = y + oy, x1 = x0 + Math.cos(a) * len, y1 = y0 + Math.sin(a) * len;
      g.beginPath();
      g.moveTo(x0, y0);
      g.quadraticCurveTo((x0 + x1) / 2 - Math.sin(a) * bend, (y0 + y1) / 2 + Math.cos(a) * bend, x1, y1);
      g.stroke();
    }
  }
  // the grain: every texel a little lighter or darker
  const img = g.getImageData(0, 0, N, N);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = (rnd() + rnd() - 1) * 14;
    img.data[i] += v;
    img.data[i + 1] += v;
    img.data[i + 2] += v;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
};

/** The paper, tiled `rx` by `ry` times across a surface's texture coordinates. */
export const paper = (rx = 1, ry = rx) => {
  sheet ??= make();
  const t = sheet.clone();
  t.repeat.set(rx, ry);
  t.needsUpdate = true;
  return t;
};
