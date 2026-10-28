// Names on the sky: constellation names that settle in as their lines land, bright star names, planets, the Moon,
// a few named sights, and the compass points on the ground. Each is an HTML element placed through one custom
// property per frame. Every frame the line pieces, star dots, planets, and the Moon are projected to the screen and
// filed in coarse buckets, and each name takes the first spot around its object whose text keeps clear of all of
// them and of the names placed before it; a name with no clear spot waits.
import { apply, project, worldFromAltAz, DEG } from "../scene/astro.js";
import { greekName } from "./catalog.js";
import { MAX_CONSTELLATIONS } from "../scene/lines.js";

const COMPASS = [
  ["N", 0, true], ["NE", 45, false], ["E", 90, true], ["SE", 135, false],
  ["S", 180, true], ["SW", 225, false], ["W", 270, true], ["NW", 315, false],
];
export const COMPASS_ALT = -3.2;

const BUCKET = 32;

export function createLabels(root, catalog, lineData, starData) {
  // What a name must keep clear of: the line pieces, and the stars bright enough to read as dots.
  const lineAttr = lineData.geometry.attributes;
  const segStart = lineAttr.aStart.array, segEnd = lineAttr.aEnd.array, segCon = lineAttr.aCon.array;
  const segCount = segCon.length;
  // The pieces come grouped by figure; each figure's run, so a hidden figure is skipped whole.
  const runs = [];
  for (let i = 0; i < segCount; i += 1) {
    if (i === 0 || segCon[i] !== segCon[i - 1]) runs.push([segCon[i], i, i + 1]);
    else runs[runs.length - 1][2] = i + 1;
  }
  const dotIdx = [];
  for (let i = 0; i < starData.mags.length; i += 1) if (starData.mags[i] < 5.2) dotIdx.push(i);
  dotIdx.sort((a, b) => starData.mags[a] - starData.mags[b]);
  const dotStar = dotIdx.map((i) => catalog.stars[i]);
  const dotDir = new Float32Array(dotIdx.length * 3);
  const dotFlux = new Float32Array(dotIdx.length);
  dotIdx.forEach((i, j) => {
    dotDir.set(starData.vectors.subarray(i * 3, i * 3 + 3), j * 3);
    dotFlux[j] = Math.pow(10, -0.4 * starData.mags[i]);
  });

  const items = [];
  const make = (kind, text, extra = {}) => {
    const el = document.createElement("div");
    el.className = `label label--${kind}`;
    const inner = document.createElement("span");
    inner.className = "label__text";
    inner.textContent = text;
    el.appendChild(inner);
    root.appendChild(el);
    const item = { el, inner, kind, text, on: false, w: 40, h: 18, x: -999, y: -999, wx: 0, wy: 0, lastOn: -1e9, spot: -1, wait: 0, ...extra };
    items.push(item);
    return item;
  };

  for (const c of catalog.constellations) {
    make("con", c.name, { con: c.index, dir: c.label, priority: c.rank === 1 ? 30 : c.rank === 2 ? 50 : 70, rank: c.rank });
  }
  const named = catalog.stars.filter((s) => s.name && s.mag < 2.6).sort((a, b) => a.mag - b.mag);
  for (const s of named) {
    make("star", s.name, { dir: dirOf(s), mag: s.mag, star: s, priority: 40 + s.mag * 6 });
  }
  const lettered = catalog.stars.filter((s) => s.bayer && s.mag < 4.3).sort((a, b) => a.mag - b.mag);
  for (const s of lettered) {
    make("greek", s.bayer, { dir: dirOf(s), mag: s.mag, star: s, priority: 45 + s.mag * 6, title: greekName(s.bayer) });
  }
  for (const s of catalog.sights) {
    make("sight", s.name, { dir: s.dir, priority: 60, sight: s });
  }
  const planetItems = {};
  for (const name of ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]) {
    planetItems[name] = make("planet", name, { body: name, priority: 10, planet: name.toLowerCase() });
    planetItems[name].el.classList.add(`label--${name.toLowerCase()}`);
  }
  const moonItem = make("moon", "Moon", { body: "Moon", priority: 5 });
  const compass = COMPASS.map(([t, az, major]) => make(major ? "compass" : "compass-minor", t, { world: worldFromAltAz(COMPASS_ALT, az), ground: worldFromAltAz(0, az), lift: 0, priority: 0 }));
  const anchors = new Set(items.map((it) => it.star).filter(Boolean));
  const reticle = document.createElement("div");
  reticle.className = "reticle";
  reticle.innerHTML = '<span class="reticle__ring"></span>';
  root.appendChild(reticle);

  function measure() {
    for (const it of items) {
      it.w = it.inner.offsetWidth || it.w;
      it.h = it.inner.offsetHeight || it.h;
    }
  }

  const tmpW = [0, 0, 0];
  const tmpV = [0, 0, 0];
  const proj = { x: 0, y: 0, f: 0, visible: false };
  const placed = [];
  let order = items.slice().sort((a, b) => a.priority - b.priority);

  // Spots around a point object at gap g, as the top-left corner of the text: right first, then the sides and
  // corners. The Moon prefers below; a constellation name starts on its center and walks outward.
  const AROUND = [[1, 0], [-1, 0], [0.75, -0.75], [0.75, 0.75], [-0.75, -0.75], [-0.75, 0.75], [0, -1], [0, 1]];
  const MOON_AROUND = [[0, 1], [0, -1], [1, 0], [-1, 0], [0.75, 0.75], [-0.75, 0.75], [0.75, -0.75], [-0.75, -0.75]];
  const SPIRAL = [];
  for (let r = 0; r <= 7; r += 1) {
    for (let a = 0; a < (r === 0 ? 1 : 8 * r); a += 1) {
      const t = (a / (8 * r || 1)) * Math.PI * 2;
      SPIRAL.push([Math.round(Math.sin(t) * r * 100) / 100, Math.round(-Math.cos(t) * r * 100) / 100]);
    }
  }
  function spot(it, sx, sy, i, g) {
    if (it.kind === "con") {
      const [dx, dy] = SPIRAL[i];
      return [sx - it.w / 2 + dx * Math.max(it.w * 0.4, 22), sy - it.h / 2 + dy * it.h * 0.9];
    }
    const ring = it.kind === "moon" ? MOON_AROUND : AROUND;
    const [ux, uy] = ring[i % ring.length];
    if (i >= ring.length) g += 9;
    const x = ux > 0 ? sx + ux * g : ux < 0 ? sx + ux * g - it.w : sx - it.w / 2;
    const y = uy > 0 ? sy + uy * g : uy < 0 ? sy + uy * g - it.h : sy - it.h / 2;
    return [x, y];
  }

  // This frame's obstacles on screen: line pieces as segments, every dot as a disc with the air it needs. A disc
  // with an owner belongs to a name, which may sit beside it.
  let segs = new Float32Array(4 * 512), nSeg = 0;
  let dots = new Float32Array(4 * 1024), nDot = 0;
  let dotOwner = new Array(1024).fill(null);
  let cols = 0, rows = 0;
  let head = new Int32Array(0);
  let next = new Int32Array(4096), entry = new Int32Array(4096), nEntry = 0;
  let segSeen = new Uint32Array(512), dotSeen = new Uint32Array(1024), stamp = 0;
  let pad = 3.5;
  // Each figure's extent on screen this frame, so its name stays on it.
  const box = new Float32Array(MAX_CONSTELLATIONS * 4);
  // The rim's points on screen: a name never sits across it from its own object.
  const rimPts = new Float32Array(2 * 200);
  let nRim = 0;
  // The horizon a degree up, as a line no name crosses, so names stay in the sky.
  const RIM = [];
  for (let az = 0; az <= 360; az += 4) RIM.push(worldFromAltAz(1, az));

  function file(b, code) {
    if (nEntry === entry.length) {
      const e = new Int32Array(nEntry * 2); e.set(entry); entry = e;
      const n = new Int32Array(nEntry * 2); n.set(next); next = n;
    }
    entry[nEntry] = code;
    next[nEntry] = head[b];
    head[b] = nEntry++;
  }
  function fileBox(x0, y0, x1, y1, code) {
    const c0 = Math.max(0, Math.floor(x0 / BUCKET)), c1 = Math.min(cols - 1, Math.floor(x1 / BUCKET));
    const r0 = Math.max(0, Math.floor(y0 / BUCKET)), r1 = Math.min(rows - 1, Math.floor(y1 / BUCKET));
    for (let r = r0; r <= r1; r += 1) for (let c = c0; c <= c1; c += 1) file(r * cols + c, code);
  }
  function addSeg(x0, y0, x1, y1) {
    if (nSeg * 4 === segs.length) {
      const g = new Float32Array(segs.length * 2); g.set(segs); segs = g;
      segSeen = new Uint32Array(segs.length / 4);
    }
    const o = nSeg * 4;
    segs[o] = x0; segs[o + 1] = y0; segs[o + 2] = x1; segs[o + 3] = y1;
    fileBox(Math.min(x0, x1) - pad, Math.min(y0, y1) - pad, Math.max(x0, x1) + pad, Math.max(y0, y1) + pad, nSeg);
    nSeg += 1;
  }
  function addDot(x, y, r, owner, flux = 1e9) {
    if (nDot * 4 === dots.length) {
      const g = new Float32Array(dots.length * 2); g.set(dots); dots = g;
      dotSeen = new Uint32Array(dots.length / 4);
      dotOwner.length = dots.length / 4;
    }
    const o = nDot * 4;
    dots[o] = x; dots[o + 1] = y; dots[o + 2] = r; dots[o + 3] = flux;
    dotOwner[nDot] = owner;
    fileBox(x - r, y - r, x + r, y + r, -1 - nDot);
    nDot += 1;
  }

  // Liang-Barsky: does the segment enter the rectangle?
  let t0 = 0, t1 = 1;
  function edge(pv, qv) {
    if (pv === 0) return qv >= 0;
    const t = qv / pv;
    if (pv < 0) {
      if (t > t1) return false;
      if (t > t0) t0 = t;
    } else {
      if (t < t0) return false;
      if (t < t1) t1 = t;
    }
    return true;
  }
  function segInRect(x0, y0, x1, y1, rx0, ry0, rx1, ry1) {
    const dx = x1 - x0, dy = y1 - y0;
    t0 = 0;
    t1 = 1;
    return edge(-dx, x0 - rx0) && edge(dx, rx1 - x0) && edge(-dy, y0 - ry0) && edge(dy, ry1 - y0);
  }

  // Whether the way from an object to its name's center crosses the rim.
  function crossesRim(ax, ay, bx, by) {
    for (let i = 0; i + 1 < nRim; i += 1) {
      const x0 = rimPts[i * 2], y0 = rimPts[i * 2 + 1], x1 = rimPts[i * 2 + 2], y1 = rimPts[i * 2 + 3];
      if (x0 !== x0 || x1 !== x1) continue;
      const d1 = (x1 - x0) * (ay - y0) - (y1 - y0) * (ax - x0);
      const d2 = (x1 - x0) * (by - y0) - (y1 - y0) * (bx - x0);
      if ((d1 > 0) === (d2 > 0)) continue;
      const d3 = (bx - ax) * (y0 - ay) - (by - ay) * (x0 - ax);
      const d4 = (bx - ax) * (y1 - ay) - (by - ay) * (x1 - ax);
      if ((d3 > 0) !== (d4 > 0)) return true;
    }
    return false;
  }
  function onFigure(it, x, y) {
    const o = it.con * 4;
    const mx = x + it.w / 2, my = y + it.h / 2;
    return mx >= box[o] - 12 && mx <= box[o + 2] + 12 && my >= box[o + 1] - 12 && my <= box[o + 3] + 12;
  }

  // Whether text in this rectangle keeps clear of every line (by its width, glow, and air) and every dot.
  function clear(x, y, w, h, owner, minFlux) {
    stamp += 1;
    const rx0 = x - pad, ry0 = y - pad, rx1 = x + w + pad, ry1 = y + h + pad;
    const c0 = Math.max(0, Math.floor(rx0 / BUCKET)), c1 = Math.min(cols - 1, Math.floor(rx1 / BUCKET));
    const r0 = Math.max(0, Math.floor(ry0 / BUCKET)), r1 = Math.min(rows - 1, Math.floor(ry1 / BUCKET));
    for (let r = r0; r <= r1; r += 1) {
      for (let c = c0; c <= c1; c += 1) {
        for (let e = head[r * cols + c]; e >= 0; e = next[e]) {
          const code = entry[e];
          if (code >= 0) {
            if (segSeen[code] === stamp) continue;
            segSeen[code] = stamp;
            const o = code * 4;
            if (segInRect(segs[o], segs[o + 1], segs[o + 2], segs[o + 3], rx0, ry0, rx1, ry1)) return false;
          } else {
            const d = -1 - code;
            if (dotSeen[d] === stamp) continue;
            dotSeen[d] = stamp;
            if ((owner && dotOwner[d] === owner) || dots[d * 4 + 3] < minFlux) continue;
            const dx = dots[d * 4], dy = dots[d * 4 + 1], dr = dots[d * 4 + 2];
            const nx = Math.max(x, Math.min(dx, x + w)), ny = Math.max(y, Math.min(dy, y + h));
            if ((nx - dx) * (nx - dx) + (ny - dy) * (ny - dy) < dr * dr) return false;
          }
        }
      }
    }
    return true;
  }

  // Sky to screen in one matrix for the frame: the view times the sky rotation.
  const M = new Float64Array(9);
  function combine(view, sky) {
    for (let r = 0; r < 3; r += 1) {
      for (let c = 0; c < 3; c += 1) M[r * 3 + c] = view[r * 3] * sky[c] + view[r * 3 + 1] * sky[3 + c] + view[r * 3 + 2] * sky[6 + c];
    }
  }
  function toScreenXYZ(x, y, z, k, cx, cy, out) {
    const f = -(M[6] * x + M[7] * y + M[8] * z);
    if (f < -0.3) return false;
    const s = (2 * k) / (1 + f);
    out[0] = cx + (M[0] * x + M[1] * y + M[2] * z) * s;
    out[1] = cy - (M[3] * x + M[4] * y + M[5] * z) * s;
    return true;
  }
  function toScreen(dir, k, cx, cy, out) {
    return toScreenXYZ(dir[0], dir[1], dir[2], k, cx, cy, out);
  }

  function markSky(ctx) {
    const { sky, view, k, width, height, conAlpha, lineMaster, settings, magLimit, zoom, bodies, moonRadius, fov } = ctx;
    cols = Math.ceil(width / BUCKET) + 1;
    rows = Math.ceil(height / BUCKET) + 1;
    if (head.length !== cols * rows) head = new Int32Array(cols * rows);
    head.fill(-1);
    nEntry = 0;
    nSeg = 0;
    nDot = 0;
    const cx = width / 2, cy = height / 2;
    const a = [0, 0], b = [0, 0];
    combine(view, sky);
    if (settings.constellations !== "none") {
      // Half the line's width and glow, plus air.
      pad = settings.constellations === "art" ? 6 : 3.5;
      for (let i = 0; i < box.length; i += 4) { box[i] = box[i + 1] = Infinity; box[i + 2] = box[i + 3] = -Infinity; }
      for (const [con, from, to] of runs) {
        if (conAlpha[con] * (lineMaster ?? 1) < 0.04) continue;
        const ci = con * 4;
        for (let i = from; i < to; i += 1) {
          if (!toScreenXYZ(segStart[i * 3], segStart[i * 3 + 1], segStart[i * 3 + 2], k, cx, cy, a)) continue;
          if (!toScreenXYZ(segEnd[i * 3], segEnd[i * 3 + 1], segEnd[i * 3 + 2], k, cx, cy, b)) continue;
          if ((a[0] < 0 && b[0] < 0) || (a[1] < 0 && b[1] < 0) || (a[0] > width && b[0] > width) || (a[1] > height && b[1] > height)) continue;
          addSeg(a[0], a[1], b[0], b[1]);
          box[ci] = Math.min(box[ci], a[0], b[0]); box[ci + 1] = Math.min(box[ci + 1], a[1], b[1]);
          box[ci + 2] = Math.max(box[ci + 2], a[0], b[0]); box[ci + 3] = Math.max(box[ci + 3], a[1], b[1]);
        }
      }
    }
    const rim = [0, 0, 0];
    nRim = 0;
    let px = 0, py = 0, prev = false;
    for (const w of RIM) {
      apply(view, w, rim);
      project(rim, k, proj);
      const ok = proj.visible && proj.f > -0.3;
      const x = cx + proj.x, y = cy - proj.y;
      if (ok && prev) addSeg(px, py, x, y);
      if (ok) {
        if (nRim > 0 && !prev) { rimPts[nRim * 2] = NaN; rimPts[nRim * 2 + 1] = NaN; nRim += 1; }
        rimPts[nRim * 2] = x; rimPts[nRim * 2 + 1] = y; nRim += 1;
      }
      prev = ok;
      px = x;
      py = y;
    }
    // A star's dot as the star shader draws it, plus air.
    const limit = magLimit ?? 6.2;
    const z = zoom ?? 1;
    const gain = Math.pow(10, 0.4 * limit);
    for (let j = 0; j < dotFlux.length; j += 1) {
      const L = dotFlux[j] * gain;
      if (L < 3) break;
      if (!toScreenXYZ(dotDir[j * 3], dotDir[j * 3 + 1], dotDir[j * 3 + 2], k, cx, cy, a)) continue;
      if (a[0] < -8 || a[1] < -8 || a[0] > width + 8 || a[1] > height + 8) continue;
      addDot(a[0], a[1], dotRadius(L, z) + (anchors.has(dotStar[j]) ? 3 : 1.5), dotStar[j], L);
    }
    if (bodies) {
      for (const name of ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]) {
        const bd = bodies[name];
        if (!bd || !toScreen(bd.dir, k, cx, cy, a)) continue;
        addDot(a[0], a[1], (1.9 + 0.75 * Math.max(0, Math.min(6, 1.5 - bd.mag))) * z + 4, name);
      }
      if (bodies.Moon && toScreen(bodies.Moon.dir, k, cx, cy, a)) addDot(a[0], a[1], moonRadius + 8, "Moon");
    }
    for (const s of catalog.sights) {
      if (fov >= 95 || !toScreen(s.dir, k, cx, cy, a)) continue;
      addDot(a[0], a[1], sightRadius(s, k), s);
    }
  }

  function collides(x, y, w, h) {
    for (let i = 0; i < placed.length; i += 1) {
      const r = placed[i];
      if (x < r[0] + r[2] && x + w > r[0] && y < r[1] + r[3] && y + h > r[1]) return true;
    }
    return false;
  }

  // A compass point that falls under a panel stands above it with room to spare, as long as it stays on the ground
  // below the horizon; where the ground has no room it waits under the panel. It eases to a new height rather than
  // jumping when a panel comes or goes.
  function liftClear(it, x, y, blocks, k, cx, cy) {
    if (!blocks) return 0;
    let top = y;
    for (let pass = 0; pass < 3; pass += 1) {
      let moved = false;
      for (const b of blocks) {
        if (x - 4 < b[0] + b[2] && x + it.w + 4 > b[0] && top - 8 < b[1] + b[3] && top + it.h + 10 > b[1] && b[1] + b[3] > cy) {
          top = b[1] - it.h - 10;
          moved = true;
        }
      }
      if (!moved) break;
    }
    if (top === y) return 0;
    apply(ctxView, it.ground, tmpV);
    project(tmpV, k, proj);
    return proj.visible && top >= cy - proj.y + 2 ? top - y : 0;
  }
  let ctxView = null;

  function moveTo(it) {
    if (Math.abs(it.x - it.wx) > 0.3 || Math.abs(it.y - it.wy) > 0.3) {
      it.wx = it.x;
      it.wy = it.y;
      it.el.style.setProperty("--t", `translate(${it.x.toFixed(1)}px, ${it.y.toFixed(1)}px)`);
    }
  }

  // Between full placements, every name shown keeps its spot beside its object as the sky moves.
  let frame = 0;
  function follow(ctx) {
    const { sky, view, k, width, height, now } = ctx;
    const cx = width / 2, cy = height / 2;
    for (const it of items) {
      if (!it.on && now - it.lastOn >= 200) continue;
      const w = it.world || (it.src && apply(sky, it.src, tmpW));
      if (!w) continue;
      apply(view, w, tmpV);
      project(tmpV, k, proj);
      if (!proj.visible) continue;
      const sx = cx + proj.x, sy = cy - proj.y;
      if (it.kind === "compass" || it.kind === "compass-minor") {
        it.x = sx - it.w / 2;
        it.y = sy - it.h / 2 + it.lift;
      } else if (it.spot >= 0) {
        [it.x, it.y] = spot(it, sx, sy, it.spot, gapFor(it, ctx));
      } else continue;
      if (it.on) it.lastOn = now;
      moveTo(it);
    }
  }

  function aim(ctx) {
    const { view, k, width, height, selection } = ctx;
    const cx = width / 2, cy = height / 2;
    if (selection && selection.world) {
      apply(view, selection.world, tmpV);
      project(tmpV, k, proj);
      const show = proj.visible && proj.f > 0.05;
      reticle.classList.toggle("is-on", show);
      if (show) {
        reticle.style.setProperty("--t", `translate(${(cx + proj.x).toFixed(1)}px, ${(cy - proj.y).toFixed(1)}px)`);
        reticle.style.setProperty("--r", `${Math.max(14, selection.radius || 0) + 6}px`);
      }
    } else {
      reticle.classList.remove("is-on");
    }
  }

  return {
    measure,
    reticle,
    update(ctx) {
      const { sky, view, k, width, height, now, settings, conAlpha, bodies, fov, selection, safeTop, safeBottom, blocks, spinning } = ctx;
      frame += 1;
      if (frame % 2 === 0) {
        follow(ctx);
        aim(ctx);
        return;
      }
      placed.length = 0;
      ctxView = view;
      markSky(ctx);
      // Names already showing keep their places ahead of names arriving, so a settled name never gives way to a
      // newcomer; the compass, the Moon, and the planets always go first.
      order.sort(byStanding);
      if (blocks) for (const b of blocks) placed.push(b);
      const cx = width / 2, cy = height / 2;
      const labelsOn = settings.labels !== "none";
      const consOn = settings.constellations !== "none";
      const greek = settings.labels === "bayer";

      for (const it of order) {
        let want = false;
        let world = it.world;
        if (it.kind === "con") {
          want = labelsOn && consOn && conAlpha[it.con] > 0.35 && (it.rank <= 2 || fov < 62);
        } else if (it.kind === "star") {
          want = labelsOn && !greek && (it.mag < 1.6 || (it.mag < 2.1 && fov < 80) || fov < 45);
        } else if (it.kind === "greek") {
          want = labelsOn && greek && (it.mag < 3.2 || fov < 60);
        } else if (it.kind === "sight") {
          want = labelsOn && fov < 95;
        } else if (it.kind === "planet") {
          const b = bodies && bodies[it.body];
          want = labelsOn && !!b && b.mag < (it.body === "Uranus" || it.body === "Neptune" ? 6 : 9) && (it.body !== "Uranus" && it.body !== "Neptune" || fov < 50);
          if (b) world = apply(sky, b.dir, tmpW).slice();
        } else if (it.kind === "moon") {
          const b = bodies && bodies.Moon;
          want = labelsOn && !!b;
          if (b) world = apply(sky, b.dir, tmpW).slice();
        } else {
          want = true;
        }
        if (spinning && (it.kind === "con" || it.kind === "star" || it.kind === "greek" || it.kind === "sight")) want = false;
        it.src = it.kind === "planet" || it.kind === "moon" ? bodies && bodies[it.body] && bodies[it.body].dir : it.dir;
        if (!world) world = apply(sky, it.dir, tmpW);
        if (want && it.kind !== "compass" && it.kind !== "compass-minor") {
          const altMin = it.kind === "con" ? 4 * DEG : it.kind === "moon" || it.kind === "planet" ? -0.5 * DEG : 1.5 * DEG;
          if (world[1] < Math.sin(altMin)) want = false;
        }
        let sx = 0, sy = 0;
        if (want) {
          apply(view, world, tmpV);
          project(tmpV, k, proj);
          if (!proj.visible || proj.f < 0.05) want = false;
          sx = cx + proj.x;
          sy = cy - proj.y;
        }
        if (want) {
          const pointy = it.kind !== "compass" && it.kind !== "compass-minor";
          const owner = it.star || it.body || it.sight;
          const minFlux = it.kind === "con" ? 6 : 0;
          // Cheapest tests first: the screen's edges, the figure's extent, names already placed, then the sky.
          const free = (x, y) => !(x < 6 || y < safeTop || x + it.w > width - 6 || y + it.h > height - safeBottom)
            && (it.kind !== "con" || onFigure(it, x, y))
            && !collides(x - 4, y - 2, it.w + 8, it.h + 4)
            && (!pointy || (clear(x, y + 1, it.w, it.h - 2, owner, minFlux) && !crossesRim(sx, sy, x + it.w / 2, y + it.h / 2)));
          let found = -1, fx = 0, fy = 0, searched = false;
          if (it.kind === "compass" || it.kind === "compass-minor") {
            fx = sx - it.w / 2;
            fy = sy - it.h / 2;
            const lift = liftClear(it, fx, fy, blocks, k, cx, cy);
            it.lift = it.on ? it.lift + (lift - it.lift) * 0.25 : lift;
            if (free(fx, fy + lift)) found = 0;
            fy += it.lift;
          } else if (it.wait > 0) {
            // A name that found no clear spot tries again a few frames later.
            it.wait -= 1;
          } else {
            searched = true;
            const g = gapFor(it, ctx);
            const n = it.kind === "con" ? SPIRAL.length : AROUND.length * 2;
            // Keep the spot from the last frame while it stays clear, so names hold still as the sky turns.
            if (it.spot >= 0 && it.spot < n) {
              [fx, fy] = spot(it, sx, sy, it.spot, g);
              if (free(fx, fy)) found = it.spot;
            }
            for (let i = 0; found < 0 && i < n; i += 1) {
              [fx, fy] = spot(it, sx, sy, i, g);
              if (free(fx, fy)) found = i;
            }
          }
          if (found < 0) {
            want = false;
            if (searched) it.wait = it.on ? 24 : 6;
          } else {
            it.spot = found;
            placed.push([fx - 4, fy - 2, it.w + 8, it.h + 4]);
            it.x = fx;
            it.y = fy;
          }
        }
        if (want !== it.on) {
          it.on = want;
          it.el.classList.toggle("is-on", want);
          if (want) it.lastOn = now;
        }
        if (want || now - it.lastOn < 200) {
          if (want) it.lastOn = now;
          else if (it.spot >= 0 && world && it.kind !== "compass" && it.kind !== "compass-minor") {
            // A name on its way out keeps to its object while it fades.
            apply(view, world, tmpV);
            project(tmpV, k, proj);
            if (proj.visible) [it.x, it.y] = spot(it, cx + proj.x, cy - proj.y, it.spot, gapFor(it, ctx));
          }
          moveTo(it);
        }
      }
      aim(ctx);
    },
    resort() {
      order = items.slice().sort(byStanding);
    },
    planetItems,
    moonItem,
    compass,
  };
}

function standing(it) {
  if (it.kind === "compass" || it.kind === "compass-minor" || it.kind === "moon" || it.kind === "planet") return 0;
  return it.on ? 1 : 2;
}

function byStanding(a, b) {
  return standing(a) - standing(b) || a.priority - b.priority;
}

function sightRadius(s, k) {
  // The Pleiades and the Orion Nebula spread over about a degree; the name sits outside that.
  return Math.max(9, k * DEG * (s.name === "Pleiades" ? 1.1 : 0.7));
}

function gapFor(it, ctx) {
  const z = ctx.zoom ?? 1;
  if (it.kind === "moon") return ctx.moonRadius + 8;
  if (it.kind === "sight") return sightRadius(it.sight, ctx.k);
  if (it.kind === "planet") {
    const b = ctx.bodies && ctx.bodies[it.body];
    return (1.9 + 0.75 * Math.max(0, Math.min(6, 1.5 - (b ? b.mag : 0)))) * z + 6;
  }
  const L = Math.pow(10, -0.4 * ((it.mag ?? 3) - (ctx.magLimit ?? 6.2)));
  return dotRadius(L, z) + 5;
}

// How far a star's dot reaches on screen: the star shader's core, about three quarters of its nominal radius, and
// the halo of the brightest.
function dotRadius(L, z) {
  const r = (0.72 + 0.5 * Math.log2(1 + L)) * z;
  return L > 25 ? r * 1.1 : Math.max(1.2, r * 0.75);
}

function dirOf(s) {
  const ra = s.ra * DEG, dec = s.dec * DEG;
  return [Math.cos(dec) * Math.cos(ra), Math.cos(dec) * Math.sin(ra), Math.sin(dec)];
}
