// Canvas painters: each book's spine, cover, back, and page edges in one atlas; the open book's two pages; wood,
// plaster, beadboard, contact shadows, the window light, and the soft sprites. Plain canvas 2D, no Three.js here,
// so the flat fallback shelf paints with the same hands.
export const SERIF = '"Fraunces", "Iowan Old Style", Georgia, serif';
export const SANS = '"Instrument Sans", "Segoe UI", system-ui, sans-serif';

export function hash(text) {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function toRgb(hex) {
  const h = hex.replace("#", "").trim();
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6);
  const n = parseInt(full, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function toHex([r, g, b]) {
  const c = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

export function mix(a, b, t) {
  const x = toRgb(a);
  const y = toRgb(b);
  return toHex([x[0] + (y[0] - x[0]) * t, x[1] + (y[1] - x[1]) * t, x[2] + (y[2] - x[2]) * t]);
}

export function luminance(hex) {
  const [r, g, b] = toRgb(hex).map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export const shade = (hex, t) => (t < 0 ? mix(hex, "#000000", -t) : mix(hex, "#ffffff", t));
const isDark = (hex) => luminance(hex) < 0.22;

/** The color a cover is mostly made of: the fullest bin of a small sample, averaged. */
export function dominantColor(image) {
  try {
    const w = 24;
    const h = 36;
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(image, 0, 0, w, h);
    const { data } = ctx.getImageData(0, 0, w, h);
    const bins = new Map();
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const key = ((r >> 5) << 6) | ((g >> 5) << 3) | (b >> 5);
      const bin = bins.get(key) || { n: 0, r: 0, g: 0, b: 0 };
      bin.n += 1;
      bin.r += r;
      bin.g += g;
      bin.b += b;
      bins.set(key, bin);
    }
    let best = null;
    for (const bin of bins.values()) if (!best || bin.n > best.n) best = bin;
    return toHex([best.r / best.n, best.g / best.n, best.b / best.n]);
  } catch {
    return null;
  }
}

function wrapLines(ctx, text, maxWidth) {
  const words = text.split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width <= maxWidth || !line) line = test;
    else {
      lines.push(line);
      line = word;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function cloth(ctx, x, y, w, h, seed, strength) {
  const r = rng(seed);
  ctx.save();
  ctx.globalAlpha = strength;
  for (let i = 0; i < 70; i += 1) {
    ctx.fillStyle = r() > 0.5 ? "#ffffff" : "#000000";
    ctx.fillRect(x + r() * w, y, 1 + r() * 1.5, h);
  }
  for (let i = 0; i < 40; i += 1) {
    ctx.fillStyle = r() > 0.5 ? "#ffffff" : "#000000";
    ctx.fillRect(x, y + r() * h, w, 1);
  }
  ctx.restore();
}

/** The atlas layout for a book of thickness t, height h, depth d on an A x A canvas. */
export function atlasLayout(dims, A) {
  const pad = Math.round(A * 0.008);
  const strips = Math.round(A * 0.07);
  let sw = Math.round((A * dims.t) / dims.h);
  let cw = Math.round((A * dims.d) / dims.h);
  const room = A - strips - pad * 3;
  if (cw + sw > room) {
    sw = Math.min(sw, Math.round(room * 0.32));
    cw = room - sw;
  }
  const spineX = cw + pad;
  const backX = spineX + sw + pad;
  const backW = Math.round(strips * 0.35);
  const edgeX = backX + backW + pad;
  return {
    A,
    cover: { x: 0, y: 0, w: cw, h: A },
    spine: { x: spineX, y: 0, w: sw, h: A },
    back: { x: backX, y: 0, w: backW, h: A },
    edge: { x: edgeX, y: 0, w: A - edgeX, h: A },
  };
}

function drawImageCover(ctx, img, r) {
  const ir = img.width / img.height;
  const rr = r.w / r.h;
  let sw = img.width;
  let sh = img.height;
  let sx = 0;
  let sy = 0;
  if (ir > rr) {
    sw = img.height * rr;
    sx = (img.width - sw) / 2;
  } else {
    sh = img.width / rr;
    sy = (img.height - sh) / 2;
  }
  ctx.drawImage(img, sx, sy, sw, sh, r.x, r.y, r.w, r.h);
}

function fitFont(ctx, text, family, weight, size, maxWidth, minSize = 0) {
  let s = size;
  ctx.font = `${weight} ${s}px ${family}`;
  const w = ctx.measureText(text).width;
  if (w > maxWidth) s = Math.max(minSize, (s * maxWidth) / w);
  ctx.font = `${weight} ${s}px ${family}`;
  return s;
}

/** A cover in the theme's colors for a book with no cover image anywhere. */
export function paintGeneratedCover(ctx, r, book, color, palette) {
  const seed = hash(book.id);
  const style = seed % 3;
  const dark = isDark(color);
  const ink = dark ? mix(palette.paper, "#ffffff", 0.2) : "#1b1914";
  const soft = dark ? shade(color, 0.16) : shade(color, -0.12);
  const u = r.w / 100;
  ctx.save();
  ctx.beginPath();
  ctx.rect(r.x, r.y, r.w, r.h);
  ctx.clip();
  ctx.fillStyle = color;
  ctx.fillRect(r.x, r.y, r.w, r.h);
  cloth(ctx, r.x, r.y, r.w, r.h, seed, 0.035);
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  const cx = r.x + r.w / 2;
  if (style === 0) {
    const band = mix(palette.paper, color, 0.08);
    ctx.fillStyle = band;
    ctx.fillRect(r.x, r.y + r.h * 0.33, r.w, r.h * 0.34);
    ctx.fillStyle = shade(color, -0.25);
    ctx.fillRect(r.x, r.y + r.h * 0.33, r.w, 3);
    ctx.fillRect(r.x, r.y + r.h * 0.67 - 3, r.w, 3);
    ctx.fillStyle = "#1b1914";
    ctx.font = `560 ${12 * u}px ${SERIF}`;
    const lines = wrapLines(ctx, book.title, r.w * 0.82).slice(0, 3);
    const size = Math.min(12 * u, (r.h * 0.26) / (lines.length * 1.12));
    ctx.font = `560 ${size}px ${SERIF}`;
    const top = r.y + r.h * 0.5 - (lines.length * size * 1.1) / 2 + size * 0.85;
    lines.forEach((line, i) => ctx.fillText(line, cx, top + i * size * 1.1));
    ctx.fillStyle = ink;
    fitFont(ctx, book.author, SANS, 600, 4.6 * u, r.w * 0.8, 3 * u);
    ctx.fillText(book.author, cx, r.y + r.h * 0.86);
  } else if (style === 1) {
    ctx.fillStyle = soft;
    ctx.beginPath();
    ctx.arc(r.x + r.w * 0.62, r.y + r.h * 0.6, r.w * 0.42, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.5;
    ctx.lineWidth = Math.max(1, u * 0.4);
    ctx.beginPath();
    ctx.arc(r.x + r.w * 0.62, r.y + r.h * 0.6, r.w * 0.3, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.textAlign = "left";
    ctx.fillStyle = ink;
    ctx.font = `600 ${13 * u}px ${SERIF}`;
    const lines = wrapLines(ctx, book.title, r.w * 0.82).slice(0, 4);
    const size = Math.min(13 * u, (r.h * 0.3) / (lines.length * 1.08));
    ctx.font = `600 ${size}px ${SERIF}`;
    lines.forEach((line, i) => ctx.fillText(line, r.x + r.w * 0.09, r.y + r.h * 0.1 + size * (0.9 + i * 1.06)));
    ctx.font = `italic 400 ${5.4 * u}px ${SERIF}`;
    ctx.fillText(book.author, r.x + r.w * 0.09, r.y + r.h * 0.93);
  } else {
    ctx.strokeStyle = ink;
    ctx.globalAlpha = 0.75;
    ctx.lineWidth = Math.max(1, u * 0.35);
    ctx.strokeRect(r.x + r.w * 0.07, r.y + r.w * 0.07, r.w * 0.86, r.h - r.w * 0.14);
    ctx.strokeRect(r.x + r.w * 0.09, r.y + r.w * 0.09, r.w * 0.82, r.h - r.w * 0.18);
    ctx.globalAlpha = 1;
    ctx.fillStyle = ink;
    ctx.font = `italic 500 ${11 * u}px ${SERIF}`;
    const lines = wrapLines(ctx, book.title, r.w * 0.7).slice(0, 4);
    const size = Math.min(11 * u, (r.h * 0.3) / (lines.length * 1.1));
    ctx.font = `italic 500 ${size}px ${SERIF}`;
    const top = r.y + r.h * 0.4 - (lines.length * size * 1.1) / 2 + size * 0.8;
    lines.forEach((line, i) => ctx.fillText(line, cx, top + i * size * 1.1));
    const oy = top + lines.length * size * 1.1 + 3 * u;
    ctx.beginPath();
    ctx.moveTo(cx - 3 * u, oy);
    ctx.lineTo(cx, oy - 1.6 * u);
    ctx.lineTo(cx + 3 * u, oy);
    ctx.lineTo(cx, oy + 1.6 * u);
    ctx.closePath();
    ctx.fill();
    fitFont(ctx, book.author, SANS, 600, 4.4 * u, r.w * 0.7, 3 * u);
    ctx.fillText(book.author, cx, r.y + r.h * 0.84);
  }
  ctx.restore();
}

/** The spine: a cloth-colored strip with rounded shading, the title set vertically in the serif, and the author. */
export function paintSpine(ctx, r, book, color) {
  const seed = hash(`${book.id}:spine`);
  const style = seed % 4;
  const dark = isDark(color);
  const ink = dark ? "#f2e9d6" : "#1c1914";
  const gilt = dark ? "#d9b46c" : shade(color, -0.55);
  ctx.save();
  ctx.beginPath();
  ctx.rect(r.x, r.y, r.w, r.h);
  ctx.clip();
  ctx.fillStyle = color;
  ctx.fillRect(r.x, r.y, r.w, r.h);
  cloth(ctx, r.x, r.y, r.w, r.h, seed, 0.03);

  const u = r.h / 100;
  let titleTop = r.y + u * 9;
  let titleBottom = r.y + u * 70;
  const authorTop = r.y + u * 74;
  const authorBottom = r.y + u * 92;

  if (style === 0) {
    ctx.fillStyle = gilt;
    [5, 6.4, 93.6, 95].forEach((p) => ctx.fillRect(r.x, r.y + p * u, r.w, u * 0.45));
  } else if (style === 1) {
    const label = mix("#f4ecd8", color, 0.06);
    ctx.fillStyle = label;
    ctx.fillRect(r.x + r.w * 0.12, r.y + u * 12, r.w * 0.76, u * 54);
    ctx.strokeStyle = shade(color, -0.3);
    ctx.lineWidth = Math.max(1, r.w * 0.02);
    ctx.strokeRect(r.x + r.w * 0.16, r.y + u * 13.2, r.w * 0.68, u * 51.6);
    titleTop = r.y + u * 15;
    titleBottom = r.y + u * 63;
  } else if (style === 2) {
    ctx.fillStyle = shade(color, dark ? 0.2 : -0.2);
    ctx.fillRect(r.x, r.y, r.w, u * 7);
    ctx.fillRect(r.x, r.y + u * 93, r.w, u * 7);
  } else {
    ctx.fillStyle = gilt;
    ctx.fillRect(r.x, r.y + u * 71, r.w, u * 0.5);
  }

  // Title, top to bottom.
  const along = titleBottom - titleTop;
  const across = r.w * (style === 1 ? 0.6 : 0.74);
  const titleInk = style === 1 ? "#1c1914" : ink;
  ctx.save();
  ctx.translate(r.x + r.w / 2, titleTop);
  ctx.rotate(Math.PI / 2);
  ctx.fillStyle = titleInk;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  let size = Math.min(across * 0.82, u * 7.5);
  ctx.font = `620 ${size}px ${SERIF}`;
  let width = ctx.measureText(book.title).width;
  const lines = [];
  if (width > along && across > size * 1.9) {
    const words = book.title.split(/\s+/);
    let split = 1;
    let bestDiff = Infinity;
    for (let i = 1; i < words.length; i += 1) {
      const a = ctx.measureText(words.slice(0, i).join(" ")).width;
      const b = ctx.measureText(words.slice(i).join(" ")).width;
      if (Math.abs(a - b) < bestDiff) {
        bestDiff = Math.abs(a - b);
        split = i;
      }
    }
    if (words.length > 1) {
      lines.push(words.slice(0, split).join(" "), words.slice(split).join(" "));
      size = Math.min(size, (across * 0.9) / 2.15);
      ctx.font = `620 ${size}px ${SERIF}`;
      width = Math.max(...lines.map((l) => ctx.measureText(l).width));
    }
  }
  if (!lines.length) lines.push(book.title);
  if (width > along) {
    size *= along / width;
    ctx.font = `620 ${size}px ${SERIF}`;
  }
  const gap = size * 1.08;
  lines.forEach((line, i) => ctx.fillText(line, along / 2, (i - (lines.length - 1) / 2) * gap));
  ctx.restore();

  // Author surname, smaller, also top to bottom.
  const name = book.author.split(/\s+/).filter(Boolean).pop() || "";
  if (name) {
    ctx.save();
    ctx.translate(r.x + r.w / 2, authorTop);
    ctx.rotate(Math.PI / 2);
    ctx.fillStyle = ink;
    ctx.globalAlpha = 0.88;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const len = authorBottom - authorTop;
    fitFont(ctx, name.toUpperCase(), SANS, 600, Math.min(r.w * 0.36, u * 3.4), len, u * 1.2);
    ctx.fillText(name.toUpperCase(), len / 2, 0);
    ctx.restore();
  }

  // Rounded spine: darker at both edges, a soft highlight off center.
  const g = ctx.createLinearGradient(r.x, 0, r.x + r.w, 0);
  g.addColorStop(0, "rgba(0,0,0,0.42)");
  g.addColorStop(0.16, "rgba(0,0,0,0.08)");
  g.addColorStop(0.38, "rgba(255,255,255,0.10)");
  g.addColorStop(0.6, "rgba(255,255,255,0.02)");
  g.addColorStop(0.86, "rgba(0,0,0,0.12)");
  g.addColorStop(1, "rgba(0,0,0,0.45)");
  ctx.fillStyle = g;
  ctx.fillRect(r.x, r.y, r.w, r.h);
  // Wear at the head and tail.
  const v = ctx.createLinearGradient(0, r.y, 0, r.y + r.h);
  v.addColorStop(0, "rgba(0,0,0,0.25)");
  v.addColorStop(0.02, "rgba(0,0,0,0)");
  v.addColorStop(0.98, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(0,0,0,0.3)");
  ctx.fillStyle = v;
  ctx.fillRect(r.x, r.y, r.w, r.h);
  ctx.restore();
}

function paintEdges(ctx, r, paper, seed) {
  const rand = rng(seed);
  ctx.fillStyle = paper;
  ctx.fillRect(r.x, r.y, r.w, r.h);
  for (let x = 0; x < r.w; x += 2) {
    ctx.fillStyle = `rgba(80,60,30,${0.05 + rand() * 0.1})`;
    ctx.fillRect(r.x + x, r.y, 1, r.h);
  }
  const g = ctx.createLinearGradient(r.x, 0, r.x + r.w, 0);
  g.addColorStop(0, "rgba(60,40,20,0.35)");
  g.addColorStop(0.08, "rgba(60,40,20,0)");
  g.addColorStop(0.92, "rgba(60,40,20,0)");
  g.addColorStop(1, "rgba(60,40,20,0.35)");
  ctx.fillStyle = g;
  ctx.fillRect(r.x, r.y, r.w, r.h);
}

/** Paints the whole atlas for one book. `look`: { color, image, palette }. */
export function paintAtlas(canvas, book, layout, look) {
  const ctx = canvas.getContext("2d");
  const { color, image, palette } = look;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (image) {
    drawImageCover(ctx, image, layout.cover);
    // A hint of board at the hinge.
    const g = ctx.createLinearGradient(0, 0, layout.cover.w * 0.06, 0);
    g.addColorStop(0, "rgba(0,0,0,0.22)");
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, layout.cover.w * 0.06, layout.cover.h);
  } else {
    paintGeneratedCover(ctx, layout.cover, book, color, palette);
  }
  paintSpine(ctx, layout.spine, book, color);
  ctx.fillStyle = shade(color, -0.08);
  ctx.fillRect(layout.back.x, layout.back.y, layout.back.w, layout.back.h);
  paintEdges(ctx, layout.edge, palette.paper, hash(book.id));
}

/** A small cover for lists and cards, from the atlas when there is one. */
export function paintThumb(canvas, source, layout) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(source, layout.cover.x, layout.cover.y, layout.cover.w, layout.cover.h, 0, 0, canvas.width, canvas.height);
}

function star(ctx, cx, cy, r) {
  ctx.beginPath();
  for (let i = 0; i < 10; i += 1) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const rr = i % 2 === 0 ? r : r * 0.45;
    ctx.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
  }
  ctx.closePath();
}

function pageGround(ctx, W, H, paper, gutterOnRight) {
  ctx.fillStyle = paper;
  ctx.fillRect(0, 0, W, H);
  const r = rng(91);
  ctx.globalAlpha = 0.035;
  for (let i = 0; i < 260; i += 1) {
    ctx.fillStyle = r() > 0.5 ? "#7a6a50" : "#ffffff";
    ctx.fillRect(r() * W, r() * H, 1 + r() * 2, 1 + r() * 2);
  }
  ctx.globalAlpha = 1;
  const gx = gutterOnRight ? W : 0;
  const g = ctx.createLinearGradient(gx, 0, gutterOnRight ? W * 0.82 : W * 0.18, 0);
  g.addColorStop(0, "rgba(70,50,25,0.30)");
  g.addColorStop(0.35, "rgba(70,50,25,0.08)");
  g.addColorStop(1, "rgba(70,50,25,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  const o = ctx.createLinearGradient(gutterOnRight ? 0 : W, 0, gutterOnRight ? W * 0.06 : W * 0.94, 0);
  o.addColorStop(0, "rgba(70,50,25,0.10)");
  o.addColorStop(1, "rgba(70,50,25,0)");
  ctx.fillStyle = o;
  ctx.fillRect(0, 0, W, H);
}

/**
 * The left page: the ex libris, the title, the author, the rating, and where the reader is.
 * `text` holds the words the page shows; `scale` is canvas pixels per CSS pixel at the book's open size.
 */
export function paintLeftPage(canvas, book, text, palette, scale) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  pageGround(ctx, W, H, palette.paper, true);
  const ink = palette.ink;
  const accent = palette.pageAccent;
  const cx = W * 0.48;
  const span = W * 0.8;
  // Type sizes: readable at the open size where there is room, always inside the page.
  const u = Math.min(Math.max(scale, H / 900), H / 400);
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";

  let y = H * 0.1;
  ctx.fillStyle = ink;
  ctx.globalAlpha = 0.62;
  fitFont(ctx, text.exLibris, SERIF, "italic 400", 12 * u, span, 8 * u);
  ctx.fillText(text.exLibris, cx, y);
  ctx.globalAlpha = 1;

  let size = Math.min(W * 0.13, 30 * u);
  ctx.font = `560 ${size}px ${SERIF}`;
  let lines = wrapLines(ctx, book.title, span * 0.92);
  if (lines.length > 3) {
    size *= 0.78;
    ctx.font = `560 ${size}px ${SERIF}`;
    lines = wrapLines(ctx, book.title, span * 0.92).slice(0, 4);
  }
  y += size * 1.9;
  lines.forEach((line, i) => ctx.fillText(line, cx, y + i * size * 1.08));
  y += (lines.length - 1) * size * 1.08;
  const authorSize = fitFont(ctx, book.author, SERIF, "italic 400", 16 * u, span, 9 * u);
  y += authorSize * 1.6;
  ctx.globalAlpha = 0.8;
  ctx.fillText(book.author, cx, y);
  ctx.globalAlpha = 1;

  y += authorSize * 1.9;
  ctx.fillStyle = accent;
  const d = 4 * u;
  ctx.beginPath();
  ctx.moveTo(cx - d * 1.6, y);
  ctx.lineTo(cx, y - d);
  ctx.lineTo(cx + d * 1.6, y);
  ctx.lineTo(cx, y + d);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(cx - W * 0.22, y - 0.75, W * 0.15, 1.5);
  ctx.fillRect(cx + W * 0.07, y - 0.75, W * 0.15, 1.5);

  const sr = Math.min(9 * u, span / 14);
  y += sr * 3.2;
  for (let i = 0; i < 5; i += 1) {
    star(ctx, cx + (i - 2) * sr * 2.5, y, sr);
    if (i < book.rating) {
      ctx.fillStyle = accent;
      ctx.fill();
    } else {
      ctx.strokeStyle = ink;
      ctx.globalAlpha = 0.3;
      ctx.lineWidth = Math.max(1, u);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
  }

  ctx.fillStyle = ink;
  const statusSize = fitFont(ctx, text.status, SANS, 500, 14 * u, span, 8 * u);
  y += sr + statusSize * 2.2;
  ctx.fillText(text.status, cx, y);
  if (book.status === "reading" && book.pages) {
    y += statusSize * 0.9;
    const bw = W * 0.56;
    const bh = Math.max(3, 3.5 * u);
    ctx.fillStyle = "rgba(60,45,25,0.16)";
    ctx.fillRect(cx - bw / 2, y, bw, bh);
    ctx.fillStyle = accent;
    ctx.fillRect(cx - bw / 2, y, (bw * book.page) / book.pages, bh);
    y += bh;
  }
  ctx.fillStyle = ink;
  ctx.globalAlpha = 0.66;
  text.facts.forEach((fact) => {
    const fs = fitFont(ctx, fact, SANS, 400, 12 * u, span, 7 * u);
    y += fs * 1.8;
    ctx.fillText(fact, cx, y);
  });
  ctx.globalAlpha = 1;
}

/** The right page: the person's note, set like a page of a book, with a drop initial. */
export function paintRightPage(canvas, book, text, palette, scale) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  pageGround(ctx, W, H, palette.paper, false);
  const ink = palette.ink;
  const unit = Math.min(Math.max(scale, H / 900), H / 560);
  const left = W * 0.13;
  const width = W * 0.75;
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.fillStyle = palette.pageAccent;
  ctx.font = `italic 500 ${Math.max(14 * unit, H * 0.024)}px ${SERIF}`;
  ctx.fillText(text.noteHead, left, H * 0.1);

  const note = book.note || text.noNote;
  let size = Math.max(17 * unit, H * 0.03);
  const maxSize = H * 0.05;
  if (note.length < 120) size = Math.min(maxSize, size * 1.25);
  const body = note;
  ctx.fillStyle = ink;
  let lineH = size * 1.42;
  const fits = () => {
    ctx.font = `400 ${size}px ${SERIF}`;
    lineH = size * 1.42;
    const first = wrapLines(ctx, body, width - size * 2.4);
    return first.length * lineH < H * 0.66;
  };
  while (!fits() && size > 10 * unit) size *= 0.92;

  const top = H * 0.18;
  if (book.note) {
    const capSize = lineH * 2 + size * 0.7;
    ctx.font = `500 ${capSize}px ${SERIF}`;
    ctx.fillStyle = palette.pageAccent;
    const cap = body.charAt(0);
    ctx.fillText(cap, left, top + capSize * 0.74);
    const capW = ctx.measureText(cap).width + size * 0.35;
    ctx.fillStyle = ink;
    ctx.font = `400 ${size}px ${SERIF}`;
    const rest = body.slice(1);
    const words = rest.split(/\s+/).filter(Boolean);
    const lines = [];
    let line = "";
    let lineIndex = 0;
    const limit = () => (lineIndex < 2 ? width - capW : width);
    let firstWordJoin = !/^\s/.test(rest);
    for (const word of words) {
      const test = line ? `${line} ${word}` : word;
      if (ctx.measureText(test).width <= limit() || !line) line = test;
      else {
        lines.push(line);
        lineIndex += 1;
        line = word;
      }
    }
    if (line) lines.push(line);
    lines.forEach((l, i) => {
      const x = i < 2 ? left + capW : left;
      const text2 = i === 0 && firstWordJoin ? l : l;
      ctx.fillText(text2, x, top + size + i * lineH);
    });
    firstWordJoin = false;
    const endY = top + size + (lines.length - 1) * lineH;
    ctx.font = `italic 400 ${size * 0.9}px ${SERIF}`;
    ctx.globalAlpha = 0.7;
    ctx.textAlign = "right";
    ctx.fillText(text.signature, left + width, endY + lineH * 1.6);
    ctx.globalAlpha = 1;
  } else {
    ctx.font = `italic 400 ${size}px ${SERIF}`;
    ctx.globalAlpha = 0.55;
    wrapLines(ctx, body, width).forEach((l, i) => ctx.fillText(l, left, top + size + i * lineH));
    ctx.globalAlpha = 1;
  }
  ctx.textAlign = "center";
  ctx.globalAlpha = 0.5;
  ctx.font = `400 ${Math.max(12 * unit, H * 0.02)}px ${SERIF}`;
  ctx.fillText("1", W * 0.52, H * 0.94);
  ctx.globalAlpha = 1;
}

/** A paper bookmark card with how far the reader is, set in the part that stands above the book. */
export function paintBookmark(canvas, book, palette) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;
  const shown = H * 0.44;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = palette.pageAccent;
  ctx.beginPath();
  ctx.moveTo(0, H);
  ctx.lineTo(0, W * 0.14);
  ctx.quadraticCurveTo(0, 0, W * 0.14, 0);
  ctx.lineTo(W * 0.86, 0);
  ctx.quadraticCurveTo(W, 0, W, W * 0.14);
  ctx.lineTo(W, H);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,0.14)";
  ctx.fillRect(0, W * 0.1, W * 0.07, H);
  ctx.fillStyle = palette.paper;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const pct = book.pages ? Math.round((book.page / book.pages) * 100) : 0;
  const label = `${pct}%`;
  let size = W * 0.42;
  ctx.font = `640 ${size}px ${SERIF}`;
  const fit = ctx.measureText(label).width;
  if (fit > W * 0.84) size *= (W * 0.84) / fit;
  ctx.font = `640 ${size}px ${SERIF}`;
  ctx.fillText(label, W / 2, shown * 0.54);
}

export function woodCanvas(base, grain, seed, kind) {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 256;
  const ctx = c.getContext("2d");
  const r = rng(seed);
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, c.width, c.height);
  if (kind === "lacquer") {
    ctx.globalAlpha = 0.04;
    for (let i = 0; i < 60; i += 1) {
      ctx.fillStyle = r() > 0.5 ? "#000000" : "#ffffff";
      ctx.fillRect(0, r() * c.height, c.width, 1 + r() * 2);
    }
    ctx.globalAlpha = 1;
    return c;
  }
  if (kind === "steel") {
    for (let i = 0; i < 400; i += 1) {
      ctx.fillStyle = r() > 0.5 ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.08)";
      ctx.fillRect(r() * c.width, r() * c.height, 80 + r() * 400, 1);
    }
    return c;
  }
  for (let i = 0; i < 120; i += 1) {
    const y0 = r() * c.height;
    const amp = 2 + r() * 10;
    const len = 120 + r() * 300;
    ctx.strokeStyle = grain;
    ctx.globalAlpha = 0.08 + r() * 0.16;
    ctx.lineWidth = 0.6 + r() * 2.2;
    ctx.beginPath();
    for (let x = 0; x <= c.width; x += 16) {
      const y = y0 + Math.sin((x / len) * Math.PI * 2 + i) * amp + Math.sin(x * 0.013 + i * 3) * amp * 0.4;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = grain;
  for (let i = 0; i < 900; i += 1) ctx.fillRect(r() * c.width, r() * c.height, 2 + r() * 6, 1);
  ctx.globalAlpha = 1;
  return c;
}

export function plasterCanvas(seed) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  const r = rng(seed);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 900; i += 1) {
    const v = 236 + Math.floor(r() * 19);
    ctx.fillStyle = `rgb(${v},${v},${v})`;
    ctx.globalAlpha = 0.35;
    ctx.beginPath();
    ctx.arc(r() * 256, r() * 256, 3 + r() * 9, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  ctx.filter = "blur(3px)";
  ctx.drawImage(c, 0, 0);
  ctx.filter = "none";
  ctx.globalAlpha = 1;
  return c;
}

export function beadboardCanvas() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 64;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, 512, 64);
  for (let x = 0; x < 512; x += 64) {
    const g = ctx.createLinearGradient(x, 0, x + 64, 0);
    g.addColorStop(0, "rgb(170,170,170)");
    g.addColorStop(0.04, "rgb(250,250,250)");
    g.addColorStop(0.5, "rgb(238,238,238)");
    g.addColorStop(0.96, "rgb(225,225,225)");
    g.addColorStop(1, "rgb(150,150,150)");
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, 64, 64);
  }
  return c;
}

/** A soft dark strip: opaque at the top of the canvas, clear at the bottom. */
export function stripCanvas() {
  const c = document.createElement("canvas");
  c.width = 4;
  c.height = 128;
  const ctx = c.getContext("2d");
  const g = ctx.createLinearGradient(0, 0, 0, 128);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.25, "rgba(255,255,255,0.55)");
  g.addColorStop(0.6, "rgba(255,255,255,0.15)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 4, 128);
  return c;
}

export function blobCanvas() {
  const c = document.createElement("canvas");
  c.width = 64;
  c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.5, "rgba(255,255,255,0.5)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return c;
}

/** Sun through a window with four panes and a glazing bar, blurred, for the key light in daylight themes. */
export function windowCanvas() {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, 512, 512);
  ctx.filter = "blur(10px)";
  ctx.fillStyle = "#ffffff";
  const panes = [
    [70, 60, 170, 180],
    [272, 60, 170, 180],
    [70, 272, 170, 180],
    [272, 272, 170, 180],
  ];
  for (const [x, y, w, h] of panes) ctx.fillRect(x, y, w, h);
  ctx.filter = "none";
  const v = ctx.createRadialGradient(256, 256, 60, 256, 256, 300);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(0,0,0,0.85)");
  ctx.fillStyle = v;
  ctx.fillRect(0, 0, 512, 512);
  return c;
}

/** A plain soft pool of light for the key light at night. */
export function poolCanvas() {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
  g.addColorStop(0, "#ffffff");
  g.addColorStop(0.55, "#d8d8d8");
  g.addColorStop(1, "#000000");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  return c;
}

export function glowCanvas() {
  const c = document.createElement("canvas");
  c.width = 128;
  c.height = 128;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.18, "rgba(255,255,255,0.55)");
  g.addColorStop(0.5, "rgba(255,255,255,0.12)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return c;
}

/** A wash of lamplight on the wall: an upright ellipse, brightest at its middle (the shade), fading to nothing at every edge. */
export function scallopCanvas() {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 512;
  const ctx = c.getContext("2d");
  ctx.setTransform(1, 0, 0, 2, 0, 0);
  const g = ctx.createRadialGradient(128, 128, 2, 128, 128, 126);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.25, "rgba(255,255,255,0.5)");
  g.addColorStop(0.6, "rgba(255,255,255,0.12)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  return c;
}

/** A small framed print for the shelf: an arch and a sun in the theme's book colors. */
export function printCanvas(palette, seed) {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 320;
  const ctx = c.getContext("2d");
  const r = rng(seed);
  const cols = palette.books;
  ctx.fillStyle = mix(palette.paper, "#ffffff", 0.3);
  ctx.fillRect(0, 0, 256, 320);
  ctx.fillStyle = cols[Math.floor(r() * cols.length)];
  ctx.beginPath();
  ctx.moveTo(48, 270);
  ctx.lineTo(48, 150);
  ctx.arc(128, 150, 80, Math.PI, 0);
  ctx.lineTo(208, 270);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = cols[(Math.floor(r() * cols.length) + 2) % cols.length];
  ctx.beginPath();
  ctx.arc(150, 120, 30, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = shade(cols[0], -0.2);
  ctx.fillRect(48, 228, 160, 42);
  return c;
}
