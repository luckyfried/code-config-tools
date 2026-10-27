// The chart, drawn as SVG by hand: assets stacked above the zero line, debts mirrored below,
// net worth as a bold line across both, a milestone flag where the line crosses each value.
const NS = "http://www.w3.org/2000/svg";

function el(name, attrs, parent) {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, String(value));
  if (parent) parent.appendChild(node);
  return node;
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** A round step near `raw`: 1, 2, 2.5, or 5 times a power of ten. */
function niceStep(raw) {
  if (!(raw > 0)) return 1;
  const power = 10 ** Math.floor(Math.log10(raw));
  const unit = raw / power;
  const step = unit <= 1 ? 1 : unit <= 2 ? 2 : unit <= 2.5 ? 2.5 : unit <= 5 ? 5 : 10;
  return step * power;
}

const fmtPath = (pts) => pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");

export function createChart({ svg, plot, model, fmt }) {
  const { points, assets, debts, milestones } = model;
  const n = points.length;
  let geo = null;
  let reveal = 1;
  let cursor = Math.max(0, n - 1);
  const nodes = {};
  const flags = [];
  const uid = `nw${Math.random().toString(36).slice(2, 7)}`;

  /** Where everything goes at the plot's current size, the left margin at least `minLeft` wide. */
  function measure(minLeft = 0) {
    const width = Math.max(240, plot.clientWidth);
    const height = Math.max(160, plot.clientHeight);
    const compact = width < 560;
    const margin = { left: Math.max(compact ? 52 : 64, minLeft), right: compact ? 16 : 24, top: compact ? 34 : 48, bottom: 40 };
    const W = width - margin.left - margin.right;
    const H = height - margin.top - margin.bottom;

    const first = n > 0 ? points[0].idx : 0;
    const last = n > 1 ? points[n - 1].idx : first + 1;
    const x0 = n > 1 ? first : first - 0.2;
    const x1 = last;
    const xOf = (idx) => margin.left + ((idx - x0) / (x1 - x0)) * W;

    const maxA = Math.max(0, ...points.map((p) => p.assets));
    const maxD = Math.max(0, ...points.map((p) => p.debts));
    const share = maxA + maxD > 0 ? maxA / (maxA + maxD) : 0.75;
    const rows = Math.max(2, Math.round(H / (compact ? 40 : 64)));
    let split;
    let topV;
    let botV;
    let stepA;
    let stepD;
    let ownScale = false;
    if (maxD === 0 || maxA === 0) {
      split = maxD === 0 ? 0.86 : 0.14;
      stepA = stepD = niceStep(Math.max(maxA, maxD, 1) / Math.max(1, rows - 1));
      topV = Math.max(stepA, maxA * 1.06);
      botV = Math.max(stepD, maxD * 1.06);
      ownScale = true;
    } else if (share >= 0.28 && share <= 0.85) {
      stepA = stepD = niceStep((maxA + maxD) / rows);
      topV = maxA * 1.06;
      botV = maxD * 1.06;
      split = topV / (topV + botV);
    } else {
      // One side dwarfs the other (a mortgage, say): each side gets its own scale and says so.
      split = share < 0.28 ? 0.55 : 0.8;
      ownScale = true;
      const rowsA = Math.max(1, Math.round(rows * split));
      const rowsD = Math.max(1, rows - rowsA);
      stepA = niceStep(maxA / rowsA);
      stepD = niceStep(maxD / rowsD);
      topV = maxA * 1.06;
      botV = maxD * 1.06;
    }
    const zeroY = margin.top + split * H;
    const kA = (split * H) / topV;
    const kD = ((1 - split) * H) / botV;
    const yOf = (v) => (v >= 0 ? zeroY - v * kA : zeroY + -v * kD);
    return { width, height, compact, margin, W, H, xOf, yOf, zeroY, topV, botV, stepA, stepD, ownScale, maxA, maxD, x0, x1, first, last };
  }

  /** The x of a fractional point index: point 2.5 sits halfway between the third and fourth snapshot. */
  function xAt(pos) {
    if (n === 0) return geo.margin.left;
    const i = clamp(Math.floor(pos), 0, n - 1);
    const j = Math.min(n - 1, i + 1);
    const t = pos - i;
    return geo.xOf(points[i].idx + (points[j].idx - points[i].idx) * t);
  }

  function netAt(pos) {
    const i = clamp(Math.floor(pos), 0, n - 1);
    const j = Math.min(n - 1, i + 1);
    const t = clamp(pos - i, 0, 1);
    return points[i].net + (points[j].net - points[i].net) * t;
  }

  /** The fractional point index under an x in plot pixels. */
  function posAt(x) {
    if (n <= 1) return 0;
    for (let i = 0; i < n - 1; i += 1) {
      const a = geo.xOf(points[i].idx);
      const b = geo.xOf(points[i + 1].idx);
      if (x <= b || i === n - 2) return clamp(i + (x - a) / (b - a), 0, n - 1);
    }
    return n - 1;
  }

  function bandPaths(list, sign) {
    const out = [];
    const xs = n > 1 ? points.map((p) => [geo.xOf(p.idx)]) : null;
    let below = points.map(() => 0);
    for (const account of list) {
      const above = points.map((p, k) => below[k] + p.balances[account.id]);
      let top;
      let bottom;
      if (n > 1) {
        top = points.map((p, k) => [xs[k][0], geo.yOf(sign * above[k])]);
        bottom = points.map((p, k) => [xs[k][0], geo.yOf(sign * below[k])]).reverse();
      } else {
        const cx = geo.xOf(points[0].idx);
        const half = 14;
        top = [[cx - half, geo.yOf(sign * above[0])], [cx + half, geo.yOf(sign * above[0])]];
        bottom = [[cx + half, geo.yOf(sign * below[0])], [cx - half, geo.yOf(sign * below[0])]];
      }
      out.push({ account, fill: `${fmtPath([...top, ...bottom])} Z`, edge: fmtPath(top) });
      below = above;
    }
    return out;
  }

  /** Each milestone at the first month whose net worth reaches it. */
  function crossings() {
    const found = [];
    for (const milestone of milestones) {
      for (let i = 0; i < n - 1; i += 1) {
        const a = points[i].net;
        const b = points[i + 1].net;
        if (a < milestone.value && b >= milestone.value) {
          found.push({ ...milestone, at: i + 1 });
          break;
        }
      }
    }
    return found.sort((p, q) => p.at - q.at);
  }

  /** The values the scale labels, top to bottom, at `g`'s steps. */
  function axisValues(g) {
    const values = [0];
    for (let v = g.stepA; v <= g.topV + 1e-6; v += g.stepA) values.push(v);
    for (let v = g.stepD; v <= g.botV + 1e-6; v += g.stepD) values.push(-v);
    return values;
  }

  /** The widest scale label in pixels, so the left margin holds every label inside the plot. */
  function axisWidth(g) {
    const probe = el("text", { class: "axis-value" }, svg);
    let widest = 0;
    for (const v of axisValues(g)) {
      probe.textContent = fmt.compact(v);
      widest = Math.max(widest, probe.getComputedTextLength ? probe.getComputedTextLength() : probe.textContent.length * 7);
    }
    probe.remove();
    return widest;
  }

  function render() {
    svg.textContent = "";
    geo = measure();
    const needed = Math.ceil(axisWidth(geo)) + 12;
    if (needed > geo.margin.left) geo = measure(needed);
    const { width, height, margin, W, H, zeroY, compact } = geo;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.textContent = "";
    flags.length = 0;

    const defs = el("defs", {}, svg);
    const clip = el("clipPath", { id: `${uid}-clip` }, defs);
    nodes.clipRect = el("rect", { x: 0, y: 0, width: 0, height }, clip);

    // Grid and scale.
    const grid = el("g", { class: "grid" }, svg);
    const labels = el("g", { class: "axis" }, svg);
    for (let v = geo.stepA; v <= geo.topV + 1e-6; v += geo.stepA) {
      const y = Math.round(geo.yOf(v)) + 0.5;
      el("line", { class: "grid-line", x1: margin.left, x2: margin.left + W, y1: y, y2: y }, grid);
      el("text", { class: "axis-value", x: margin.left - 10, y: y + 4, "text-anchor": "end" }, labels).textContent = fmt.compact(v);
    }
    for (let v = geo.stepD; v <= geo.botV + 1e-6; v += geo.stepD) {
      const y = Math.round(geo.yOf(-v)) + 0.5;
      el("line", { class: "grid-line", x1: margin.left, x2: margin.left + W, y1: y, y2: y }, grid);
      el("text", { class: "axis-value", x: margin.left - 10, y: y + 4, "text-anchor": "end" }, labels).textContent = fmt.compact(-v);
    }
    el("text", { class: "axis-value", x: margin.left - 10, y: zeroY + 4, "text-anchor": "end" }, labels).textContent = fmt.compact(0);

    // Layers: each account a band, filled with its color fading toward the zero line.
    const plotted = el("g", { "clip-path": `url(#${uid}-clip)` }, svg);
    const drawSide = (list, sign) => {
      bandPaths(list, sign).forEach(({ account, fill, edge }, k) => {
        const id = `${uid}-g-${sign > 0 ? "a" : "d"}${k}`;
        const grad = el("linearGradient", { id, gradientUnits: "userSpaceOnUse", x1: 0, x2: 0, y1: sign > 0 ? margin.top : margin.top + H, y2: zeroY }, defs);
        grad.style.setProperty("--layer", account.color);
        el("stop", { offset: 0, class: "grad-near" }, grad);
        el("stop", { offset: 1, class: "grad-far" }, grad);
        el("path", { d: fill, fill: `url(#${id})`, class: "layer" }, plotted);
        const line = el("path", { d: edge, class: "layer-edge" }, plotted);
        line.style.setProperty("--layer", account.color);
      });
    };
    drawSide(assets, 1);
    drawSide(debts, -1);

    el("line", { class: "zero-line", x1: margin.left, x2: margin.left + W, y1: Math.round(zeroY) + 0.5, y2: Math.round(zeroY) + 0.5 }, svg);

    // The key, above the plot: what sits above the line and what sits below it.
    const key = el("g", { class: "key" }, svg);
    let kx = margin.left;
    const keyY = compact ? 13 : 17;
    const keyItem = (label, color, note) => {
      const swatch = el("rect", { class: "key-swatch", x: kx, y: keyY - 9, width: 10, height: 10, rx: 3 }, key);
      swatch.style.setProperty("--layer", color);
      const text = el("text", { class: "axis-name", x: kx + 16, y: keyY }, key);
      text.textContent = label;
      if (note) el("tspan", { class: "axis-name-note" }, text).textContent = note;
      kx += 16 + (text.getComputedTextLength ? text.getComputedTextLength() : label.length * 7) + 18;
    };
    keyItem("Assets", "var(--asset-1)", "");
    keyItem("Debts", "var(--debt-1)", geo.ownScale && geo.maxA > 0 && geo.maxD > 0 ? ", own scale" : "");
    keyItem("Net worth", "var(--color-line)", "");

    // Months: one tick per snapshot, labels thinned to what fits from the latest back, the first always
    // labelled, and a year under the first label of each year.
    const months = el("g", { class: "months" }, svg);
    const baseY = margin.top + H;
    const spacing = n > 1 ? W / Math.max(1, geo.last - geo.first) : W;
    const every = Math.max(1, Math.ceil((compact ? 40 : 52) / spacing));
    let yearShown = null;
    const tickIdx = n > 1 ? points.map((p) => p.idx) : [points[0]?.idx ?? 0, (points[0]?.idx ?? 0) + 1];
    tickIdx.forEach((idx, k) => {
      const x = Math.round(geo.xOf(idx)) + 0.5;
      el("line", { class: "month-tick", x1: x, x2: x, y1: baseY, y2: baseY + 5 }, months);
      const fromEnd = n > 1 ? n - 1 - k : 0;
      const firstOff = (n - 1) % every !== 0;
      const labelled = n <= 1 || k === 0 || (fromEnd % every === 0 && !(firstOff && k < every));
      if (!labelled) return;
      const anchor = n > 1 && k === 0 ? "start" : k === tickIdx.length - 1 ? "end" : "middle";
      const label = el("text", { class: `month-label${n <= 1 && k === 1 ? " is-next" : ""}`, x, y: baseY + 18, "text-anchor": anchor }, months);
      label.textContent = fmt.monthShort(idx);
      const year = Math.floor(idx / 12);
      if (year !== yearShown) {
        el("text", { class: "month-year", x, y: baseY + 33, "text-anchor": anchor }, months).textContent = fmt.year(idx);
        yearShown = year;
      }
    });

    // Net worth: the bold line and one point a month.
    const linePts = n > 1 ? points.map((p) => [geo.xOf(p.idx), geo.yOf(p.net)]) : [];
    if (n > 1) el("path", { class: "net-line", d: fmtPath(linePts) }, plotted);
    points.forEach((p) => el("circle", { class: "net-point", cx: geo.xOf(p.idx), cy: geo.yOf(p.net), r: geo.compact ? 2.5 : 3.25 }, plotted));

    // Milestone flags: one marker on the month's own point, and a pill set where it touches neither the
    // net worth line, its points, nor another pill.
    const flagLayer = el("g", { class: "flags" }, svg);
    const PILL_H = 22;
    const CLEAR = 6;
    const segs = n > 1 ? linePts.slice(1).map((q, k) => [linePts[k], q]) : points.map((p) => [[geo.xOf(p.idx), geo.yOf(p.net)], [geo.xOf(p.idx), geo.yOf(p.net)]]);
    const segHits = ([[ax, ay], [bx, by]], r) => {
      // Liang-Barsky: does the segment from a to b pass through rectangle r?
      let t0 = 0;
      let t1 = 1;
      const dx = bx - ax;
      const dy = by - ay;
      const edges = [[-dx, ax - r.x0], [dx, r.x1 - ax], [-dy, ay - r.y0], [dy, r.y1 - ay]];
      for (const [pp, qq] of edges) {
        if (pp === 0) {
          if (qq < 0) return false;
        } else {
          const t = qq / pp;
          if (pp < 0) t0 = Math.max(t0, t);
          else t1 = Math.min(t1, t);
          if (t0 > t1) return false;
        }
      }
      return true;
    };
    const placed = [];
    const topLimit = keyY + 6;
    const bottomLimit = baseY - 2;
    for (const crossing of crossings()) {
      const point = points[crossing.at];
      const cx = geo.xOf(point.idx);
      const cy = geo.yOf(point.net);
      const g = el("g", { class: "flag" }, flagLayer);
      const pole = el("line", { class: "flag-pole", x1: cx, x2: cx, y1: cy, y2: cy }, g);
      const pill = el("rect", { class: "flag-pill", rx: 11, height: PILL_H }, g);
      const text = el("text", { class: "flag-text", "text-anchor": "middle" }, g);
      text.textContent = crossing.label;
      el("circle", { class: "flag-mark", cx, cy, r: 4.5 }, g);
      const tw = text.getComputedTextLength ? text.getComputedTextLength() : crossing.label.length * 7;
      const pw = tw + 20;
      const lift0 = compact ? 14 : 20;
      const lefts = [cx - pw / 2, cx - pw + 16, cx - 16].map((x) => clamp(x, margin.left - 4, margin.left + W - pw + 4));
      const cost = (px, top) => {
        const r = { x0: px - CLEAR, x1: px + pw + CLEAR, y0: top - CLEAR, y1: top + PILL_H + CLEAR };
        let hits = segs.filter((seg) => segHits(seg, r)).length;
        for (const other of placed) {
          if (px < other.x + other.w + 4 && px + pw + 4 > other.x && top < other.y + PILL_H + 4 && top + PILL_H + 4 > other.y) hits += 10;
        }
        if (top < topLimit || top + PILL_H > bottomLimit) hits += 100;
        return hits;
      };
      let best = null;
      for (const up of [true, false]) {
        for (const lift of [lift0, lift0 + 12, lift0 + 26, lift0 + 44, lift0 + 66]) {
          const top = up ? cy - lift - PILL_H : cy + lift;
          for (const px of lefts) {
            const c = cost(px, top);
            if (!best || c < best.c) best = { c, px, top, up };
          }
          if (best.c === 0) break;
        }
        if (best.c === 0) break;
      }
      const { px, top, up } = best;
      pole.setAttribute("y2", String(up ? top + PILL_H : top));
      pill.setAttribute("x", String(px));
      pill.setAttribute("y", String(top));
      pill.setAttribute("width", String(pw));
      text.setAttribute("x", String(px + pw / 2));
      text.setAttribute("y", String(top + 15));
      placed.push({ x: px, y: top, w: pw });
      flags.push({ node: g, x: cx });
    }

    // The month cursor.
    const cursorG = el("g", { class: "cursor" }, svg);
    nodes.cursorLine = el("line", { class: "cursor-line", y1: margin.top - 4, y2: baseY }, cursorG);
    nodes.cursorHalo = el("circle", { class: "cursor-halo", r: geo.compact ? 11 : 14 }, cursorG);
    nodes.cursorDot = el("circle", { class: "cursor-dot", r: geo.compact ? 5 : 6 }, cursorG);

    applyReveal();
    applyCursor();
  }

  function applyReveal() {
    if (!geo) return;
    const edge = geo.margin.left + reveal * geo.W;
    nodes.clipRect.setAttribute("width", String(Math.max(0, reveal >= 1 ? geo.width : edge + 4)));
    for (const flag of flags) {
      if (flag.x <= edge + 0.5 && !flag.node.classList.contains("is-down")) flag.node.classList.add("is-down");
    }
  }

  function applyCursor() {
    if (!geo || n === 0) return;
    const x = xAt(cursor);
    const y = geo.yOf(netAt(cursor));
    nodes.cursorLine.setAttribute("x1", String(x));
    nodes.cursorLine.setAttribute("x2", String(x));
    nodes.cursorDot.setAttribute("cx", String(x));
    nodes.cursorDot.setAttribute("cy", String(y));
    nodes.cursorHalo.setAttribute("cx", String(x));
    nodes.cursorHalo.setAttribute("cy", String(y));
  }

  return {
    render,
    /** Each snapshot's x as a share of the plot's width, for the scrubber's ticks. */
    ticks: () => points.map((p) => (geo.xOf(p.idx) - geo.margin.left) / geo.W),
    margins: () => ({ left: geo.margin.left, right: geo.margin.right }),
    posAtShare: (share) => posAt(geo.margin.left + share * geo.W),
    shareAtPos: (pos) => (xAt(pos) - geo.margin.left) / geo.W,
    posAtClientX: (clientX) => posAt(clientX - svg.getBoundingClientRect().left),
    setReveal(p) {
      reveal = clamp(p, 0, 1);
      applyReveal();
    },
    setCursor(pos) {
      cursor = clamp(pos, 0, Math.max(0, n - 1));
      applyCursor();
    },
  };
}
