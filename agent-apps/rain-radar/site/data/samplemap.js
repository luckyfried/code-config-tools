// The map the sample loop plays over, grown from the place name: a coast, a river through town, towns joined by
// roads, and the town's own street web. Two canvases the ground shader colors from the theme:
//   land:  red = a smooth field, land where it is above one half (the shader cuts the coast sharp at any zoom)
//   roads: red = streets, green = highways, blue = built-up ground

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return h >>> 0;
}

function makeNoise(seed) {
  const N = 256;
  const r = mulberry32(seed);
  const perm = new Uint8Array(N * 2);
  const vals = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    perm[i] = i;
    vals[i] = r();
  }
  for (let i = N - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [perm[i], perm[j]] = [perm[j], perm[i]];
  }
  for (let i = 0; i < N; i++) perm[N + i] = perm[i];
  const v = (x, y) => vals[perm[(perm[x & 255] + y) & 511]];
  const noise = (x, y) => {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const fx = x - xi;
    const fy = y - yi;
    const sx = fx * fx * (3 - 2 * fx);
    const sy = fy * fy * (3 - 2 * fy);
    const a = v(xi, yi);
    const b = v(xi + 1, yi);
    const c = v(xi, yi + 1);
    const d = v(xi + 1, yi + 1);
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  };
  return (x, y, oct = 5) => {
    let s = 0;
    let amp = 0.5;
    let f = 1;
    let norm = 0;
    for (let o = 0; o < oct; o++) {
      s += noise(x * f, y * f) * amp;
      norm += amp;
      amp *= 0.5;
      f *= 2.03;
    }
    return s / norm;
  };
}

export function sampleMap(placeName, sizes = { land: 512, roads: 2048 }) {
  const seed = hashString(placeName || "place");
  const rnd = mulberry32(seed ^ 0x9e3779b9);
  const fbm = makeNoise(seed);
  const ang = rnd() * Math.PI * 2;
  const dir = [Math.cos(ang), Math.sin(ang)]; // toward the inland side
  const coastAt = 0.2 + rnd() * 0.06;

  const lakes = [];
  for (let i = 0; i < 3; i++) {
    lakes.push([0.5 + dir[0] * (0.15 + rnd() * 0.25) + (rnd() - 0.5) * 0.4, 0.5 + dir[1] * (0.15 + rnd() * 0.25) + (rnd() - 0.5) * 0.4, 0.012 + rnd() * 0.02]);
  }

  // f(x, y) in uv-like canvas units (x east, y south), land where f > 0.5
  const field = (x, y) => {
    const g = (x - 0.5) * dir[0] + (y - 0.5) * dir[1];
    let f = 0.5 + (g + coastAt) * 1.25 + (fbm(x * 4.2 + 11, y * 4.2 + 3) - 0.5) * 0.85;
    const dc = (x - 0.5) ** 2 + (y - 0.5) ** 2;
    f += 0.22 * Math.exp(-dc / 0.012);
    for (const [lx, ly, lr] of lakes) {
      const d = ((x - lx) ** 2 + (y - ly) ** 2) / (lr * lr);
      f -= 0.45 * Math.exp(-d * 2) * (0.7 + 0.6 * fbm(x * 30, y * 30, 2));
    }
    return f;
  };

  // land field
  const LS = sizes.land;
  const land = document.createElement("canvas");
  land.width = land.height = LS;
  const lctx = land.getContext("2d");
  const img = lctx.createImageData(LS, LS);
  for (let j = 0; j < LS; j++) {
    for (let i = 0; i < LS; i++) {
      const f = field(i / LS, j / LS);
      const k = (j * LS + i) * 4;
      img.data[k] = Math.max(0, Math.min(255, f * 255));
      img.data[k + 3] = 255;
    }
  }
  lctx.putImageData(img, 0, 0);

  // the river: from inland, through town, to the sea
  const river = [];
  const src = [0.5 + dir[0] * 0.48 + -dir[1] * (rnd() - 0.5) * 0.5, 0.5 + dir[1] * 0.48 + dir[0] * (rnd() - 0.5) * 0.5];
  const mouth = [0.5 - dir[0] * (coastAt + 0.12), 0.5 - dir[1] * (coastAt + 0.12)];
  const via = [0.5 + -dir[1] * 0.025, 0.5 + dir[0] * 0.025];
  const ctrl = [src, [(src[0] + via[0]) / 2 + (rnd() - 0.5) * 0.12, (src[1] + via[1]) / 2 + (rnd() - 0.5) * 0.12], via, mouth];
  for (let s = 0; s < ctrl.length - 1; s++) {
    const [a, b] = [ctrl[s], ctrl[s + 1]];
    for (let t = 0; t < 1; t += 0.02) {
      const x = a[0] + (b[0] - a[0]) * t;
      const y = a[1] + (b[1] - a[1]) * t;
      const m = (fbm(x * 9 + 40, y * 9 + 40, 3) - 0.5) * 0.08;
      river.push([x + -dir[1] * m, y + dir[0] * m]);
    }
  }
  river.push(mouth);
  lctx.lineCap = "round";
  lctx.lineJoin = "round";
  lctx.strokeStyle = "rgb(0,0,0)";
  for (let i = 1; i < river.length; i++) {
    lctx.lineWidth = 0.9 + (i / river.length) * 1.6;
    lctx.beginPath();
    lctx.moveTo(river[i - 1][0] * LS, river[i - 1][1] * LS);
    lctx.lineTo(river[i][0] * LS, river[i][1] * LS);
    lctx.stroke();
  }
  // the land test for road points: the field alone, ignoring the river
  const onLand = (x, y) => x > 0 && y > 0 && x < 1 && y < 1 && field(x, y) > 0.5;

  // towns
  const towns = [{ x: 0.5, y: 0.5, size: 1 }];
  for (let tries = 0; tries < 1800 && towns.length < 64; tries++) {
    const x = 0.04 + rnd() * 0.92;
    const y = 0.04 + rnd() * 0.92;
    if (!onLand(x, y) || field(x, y) < 0.56) continue;
    if (towns.some((t) => Math.hypot(t.x - x, t.y - y) < 0.052)) continue;
    towns.push({ x, y, size: 0.12 + rnd() ** 2 * 0.45 });
  }

  const RS = sizes.roads;
  const roads = document.createElement("canvas");
  roads.width = roads.height = RS;
  const ctx = roads.getContext("2d");
  ctx.fillStyle = "rgb(0,0,0)";
  ctx.fillRect(0, 0, RS, RS);
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // built-up ground
  for (const t of towns) {
    const blobs = t.size === 1 ? 9 : 2;
    for (let b = 0; b < blobs; b++) {
      const ox = t.size === 1 ? (rnd() - 0.5) * 0.07 : (rnd() - 0.5) * 0.008;
      const oy = t.size === 1 ? (rnd() - 0.5) * 0.07 : (rnd() - 0.5) * 0.008;
      const r = (t.size === 1 ? 0.03 + rnd() * 0.025 : 0.006 + t.size * 0.02) * RS;
      const gx = (t.x + ox) * RS;
      const gy = (t.y + oy) * RS;
      const grad = ctx.createRadialGradient(gx, gy, 0, gx, gy, r);
      grad.addColorStop(0, "rgba(0,0,150,1)");
      grad.addColorStop(0.6, "rgba(0,0,70,1)");
      grad.addColorStop(1, "rgba(0,0,0,1)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(gx, gy, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // a bent road between two points; stops where it would run out to sea
  const bend = (a, b, amount) => {
    let pts = [a, b];
    for (let level = 0; level < 5; level++) {
      const next = [pts[0]];
      for (let i = 1; i < pts.length; i++) {
        const p = pts[i - 1];
        const q = pts[i];
        const dx = q[0] - p[0];
        const dy = q[1] - p[1];
        const off = (rnd() - 0.5) * amount * 0.5 ** level;
        next.push([(p[0] + q[0]) / 2 - dy * off, (p[1] + q[1]) / 2 + dx * off], q);
      }
      pts = next;
    }
    const out = [];
    let wet = 0;
    for (const p of pts) {
      wet = onLand(p[0], p[1]) ? 0 : wet + 1;
      if (wet > 2) break;
      out.push(p);
    }
    return out;
  };
  const stroke = (pts, width, style) => {
    if (pts.length < 2) return;
    ctx.strokeStyle = style;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(pts[0][0] * RS, pts[0][1] * RS);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0] * RS, pts[i][1] * RS);
    ctx.stroke();
  };

  // section lanes across the farmland, on a grid that turns a little from square to square
  {
    const step = 0.026;
    const tilt = rnd() * 0.5 - 0.25;
    ctx.beginPath();
    for (let gy = -0.1; gy < 1.1; gy += step) {
      for (let gx = -0.1; gx < 1.1; gx += step) {
        if (rnd() < 0.45) continue;
        const a = tilt + (fbm(gx * 3 + 7, gy * 3 + 7, 2) - 0.5) * 0.6 + (rnd() < 0.5 ? 0 : Math.PI / 2);
        const x0 = gx * RS;
        const y0 = gy * RS;
        const x1 = x0 + Math.cos(a) * step * RS;
        const y1 = y0 + Math.sin(a) * step * RS;
        if (onLand(gx, gy) && onLand(x1 / RS, y1 / RS)) {
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
        }
      }
    }
    ctx.strokeStyle = "rgba(55,0,0,1)";
    ctx.lineWidth = 0.9;
    ctx.stroke();
  }

  // the street web inside each built-up area
  for (const t of towns) {
    const radius = (t.size === 1 ? 0.075 : 0.008 + t.size * 0.022) * RS;
    const spacing = t.size === 1 ? 7 : 6;
    const rot = rnd() * Math.PI;
    for (let pass = 0; pass < 2; pass++) {
      const a = rot + pass * (Math.PI / 2 + (rnd() - 0.5) * 0.25);
      const ca = Math.cos(a);
      const sa = Math.sin(a);
      ctx.beginPath();
      for (let o = -radius; o <= radius; o += spacing * (0.7 + rnd() * 0.6)) {
        const half = Math.sqrt(Math.max(0, radius * radius - o * o));
        let s = -half;
        while (s < half) {
          const len = 6 + rnd() * 40;
          if (rnd() > 0.28) {
            const e = Math.min(half, s + len);
            const x0 = t.x * RS + ca * s - sa * o;
            const y0 = t.y * RS + sa * s + ca * o;
            const x1 = t.x * RS + ca * e - sa * o;
            const y1 = t.y * RS + sa * e + ca * o;
            if (onLand(x0 / RS, y0 / RS)) {
              ctx.moveTo(x0, y0);
              ctx.lineTo(x1, y1);
            }
          }
          s += len;
        }
      }
      ctx.strokeStyle = t.size === 1 ? "rgba(120,0,0,1)" : "rgba(90,0,0,1)";
      ctx.lineWidth = 0.9;
      ctx.stroke();
    }
  }

  // country roads: every town to its nearest neighbors
  for (let i = 0; i < towns.length; i++) {
    const near = towns
      .map((t, j) => ({ j, d: Math.hypot(t.x - towns[i].x, t.y - towns[i].y) }))
      .filter((n) => n.j !== i)
      .sort((p, q) => p.d - q.d)
      .slice(0, 3);
    for (const n of near) {
      if (n.j < i && near.length > 1) continue;
      stroke(bend([towns[i].x, towns[i].y], [towns[n.j].x, towns[n.j].y], 0.5), 1.6, "rgba(150,0,0,1)");
    }
  }

  // highways from the town outward, through the bigger towns, and a ring
  const big = towns.slice(1).sort((p, q) => q.size - p.size).slice(0, 7);
  for (const t of big) {
    const far = [0.5 + (t.x - 0.5) * 3, 0.5 + (t.y - 0.5) * 3];
    stroke(bend([0.5, 0.5], [t.x, t.y], 0.35).concat(bend([t.x, t.y], far, 0.3).slice(1)), 3.2, "rgba(0,210,0,1)");
  }
  const ring = [];
  const rr = 0.045 + rnd() * 0.01;
  for (let k = 0; k <= 64; k++) {
    const a = (k / 64) * Math.PI * 2;
    const w = 1 + (fbm(Math.cos(a) * 2 + 5, Math.sin(a) * 2 + 5, 2) - 0.5) * 0.5;
    ring.push([0.5 + Math.cos(a) * rr * w, 0.5 + Math.sin(a) * rr * w]);
  }
  stroke(ring.filter((p) => onLand(p[0], p[1])), 2.6, "rgba(0,170,0,1)");

  // arterials across town
  for (let k = 0; k < 10; k++) {
    const a = rnd() * Math.PI;
    const r = 0.06 + rnd() * 0.04;
    const p = [0.5 + Math.cos(a) * r, 0.5 + Math.sin(a) * r];
    const q = [0.5 - Math.cos(a) * r * (0.6 + rnd() * 0.6), 0.5 - Math.sin(a) * r * (0.6 + rnd() * 0.6)];
    stroke(bend(p, q, 0.25), 1.5, "rgba(200,0,0,1)");
  }

  return { land, roads };
}
