// Procedural textures painted from the theme's tokens: the table under the board, the board's face with its grid,
// and the soft glow the legal dots and the last move use. Painted once per theme, never per frame.
import { CanvasTexture, SRGBColorSpace, RepeatWrapping } from "three";

function canvas(size) {
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  return c;
}

function hexToRgb(hex) {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((x) => x + x).join("") : h.slice(0, 6), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// A small seeded generator, so a theme paints the same grain every time.
function seeded(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function texture(c, srgb = true) {
  const t = new CanvasTexture(c);
  if (srgb) t.colorSpace = SRGBColorSpace;
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

/** Fine grain laid over a canvas: `kind` picks speckle (stone), fiber (felt), cells (leather), or streaks (glass). */
function grain(ctx, size, kind, strength, rand) {
  const img = ctx.getImageData(0, 0, size, size);
  const d = img.data;
  const fiber = new Float32Array(size);
  for (let y = 0; y < size; y += 1) {
    let run = 0;
    for (let x = 0; x < size; x += 1) {
      let n;
      if (kind === "felt") {
        run = run * 0.82 + (rand() - 0.5) * 0.9;
        fiber[x] = fiber[x] * 0.6 + run * 0.4;
        n = fiber[x] * 1.2 + (rand() - 0.5) * 0.5;
      } else if (kind === "leather") {
        const cx = Math.sin(x * 0.09 + Math.sin(y * 0.05) * 2) * Math.sin(y * 0.083 + Math.sin(x * 0.04) * 2);
        n = Math.abs(cx) < 0.12 ? -0.9 : (rand() - 0.5) * 0.4;
      } else if (kind === "glass") {
        n = (rand() - 0.5) * 0.25 + Math.sin((x + y) * 0.012) * 0.15;
      } else {
        n = (rand() - 0.5) * 0.9 + (rand() < 0.01 ? -1.2 : 0);
      }
      const i = (y * size + x) * 4;
      const v = n * strength;
      d[i] = Math.max(0, Math.min(255, d[i] + v));
      d[i + 1] = Math.max(0, Math.min(255, d[i + 1] + v));
      d[i + 2] = Math.max(0, Math.min(255, d[i + 2] + v));
    }
  }
  ctx.putImageData(img, 0, 0);
}

/** The table: a pool of light under the board falling off to the room's edge, with the surface's grain. */
export function paintTable(tokens, size) {
  const c = canvas(size);
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(size / 2, size / 2, size * 0.04, size / 2, size / 2, size * 0.42);
  g.addColorStop(0, tokens.table);
  g.addColorStop(0.55, tokens.table);
  g.addColorStop(1, tokens.tableEdge);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const kind = tokens.tableTexture;
  grain(ctx, size, kind, kind === "glass" ? 6 : kind === "felt" ? 9 : kind === "leather" ? 3.5 : 7, seeded(11));
  return texture(c);
}

function gridPath(ctx, size, inset) {
  const cell = (size - inset * 2) / 8;
  ctx.beginPath();
  for (let k = 0; k <= 8; k += 1) {
    const p = inset + k * cell;
    ctx.moveTo(p, inset);
    ctx.lineTo(p, size - inset);
    ctx.moveTo(inset, p);
    ctx.lineTo(size - inset, p);
  }
  return cell;
}

function stars(ctx, size, inset, radius) {
  const cell = (size - inset * 2) / 8;
  for (const [r, col] of [[2, 2], [2, 6], [6, 2], [6, 6]]) {
    ctx.beginPath();
    ctx.arc(inset + col * cell, inset + r * cell, radius, 0, Math.PI * 2);
    ctx.fill();
  }
}

/** The board's face: lacquer, oiled walnut, or black glass, with grooved grid lines and the four star points. */
export function paintBoard(tokens, size) {
  const c = canvas(size);
  const ctx = c.getContext("2d");
  const rand = seeded(29);
  const kind = tokens.boardTexture;
  const g = ctx.createRadialGradient(size * 0.42, size * 0.38, size * 0.05, size / 2, size / 2, size * 0.75);
  g.addColorStop(0, tokens.board);
  g.addColorStop(1, tokens.board2);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  if (kind === "wood") {
    const [r, gg, b] = hexToRgb(tokens.board2);
    for (let k = 0; k < 260; k += 1) {
      const y0 = rand() * size;
      const amp = 4 + rand() * 14;
      const freq = 0.002 + rand() * 0.004;
      const phase = rand() * 10;
      ctx.strokeStyle = `rgba(${r},${gg},${b},${0.08 + rand() * 0.22})`;
      ctx.lineWidth = 0.6 + rand() * (size / 512) * 2.2;
      ctx.beginPath();
      for (let x = 0; x <= size; x += size / 64) {
        const y = y0 + Math.sin(x * freq + phase) * amp + Math.sin(x * freq * 3.1 + phase) * amp * 0.25;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    grain(ctx, size, "stone", 5, rand);
  } else if (kind === "glass") {
    grain(ctx, size, "glass", 3, rand);
  }
  const inset = size * 0.0;
  const lw = Math.max(3, size / 230);
  // A groove: the dark cut, then a faint lit lip just below it.
  if (kind !== "glass") {
    ctx.strokeStyle = tokens.lineHi;
    ctx.globalAlpha = 0.55;
    ctx.lineWidth = lw * 0.7;
    ctx.save();
    ctx.translate(lw * 0.6, lw * 0.6);
    gridPath(ctx, size, inset);
    ctx.stroke();
    ctx.restore();
    ctx.globalAlpha = 1;
  }
  ctx.strokeStyle = tokens.line;
  ctx.lineWidth = kind === "glass" ? lw * 0.8 : lw;
  gridPath(ctx, size, inset);
  ctx.stroke();
  ctx.fillStyle = tokens.line;
  stars(ctx, size, inset, lw * 2.6);
  return texture(c);
}

/** Neon's lit lines: the grid alone on black, for the board's emissive map. */
export function paintBoardGlow(tokens, size) {
  const c = canvas(size);
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, size, size);
  const lw = Math.max(3, size / 230);
  ctx.strokeStyle = tokens.line;
  ctx.shadowColor = tokens.line;
  ctx.shadowBlur = lw * 4;
  ctx.lineWidth = lw * 0.8;
  gridPath(ctx, size, 0);
  ctx.stroke();
  ctx.fillStyle = tokens.line;
  stars(ctx, size, 0, lw * 2.4);
  return texture(c);
}

/** A soft round glow with a bright center dot, white, tinted by the material. */
export function paintGlow(size = 256, dot = 0.13) {
  const c = canvas(size);
  const ctx = c.getContext("2d");
  const h = size / 2;
  const g = ctx.createRadialGradient(h, h, 0, h, h, h);
  g.addColorStop(0, "rgba(255,255,255,0.55)");
  g.addColorStop(0.35, "rgba(255,255,255,0.22)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  if (dot > 0) {
    ctx.fillStyle = "rgba(255,255,255,1)";
    ctx.beginPath();
    ctx.arc(h, h, size * dot * 0.5, 0, Math.PI * 2);
    ctx.fill();
  }
  return texture(c, false);
}

/** A rounded square outline: the keyboard cursor. */
export function paintCursor(size = 256) {
  const c = canvas(size);
  const ctx = c.getContext("2d");
  const lw = size * 0.05;
  const r = size * 0.14;
  const m = lw;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = lw;
  ctx.beginPath();
  ctx.roundRect(m, m, size - 2 * m, size - 2 * m, r);
  ctx.stroke();
  return texture(c, false);
}

export { RepeatWrapping };
