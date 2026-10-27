// The thirty-day chart: words per minute as a line with a gradient fill, accuracy as a dotted line on its own scale,
// drawn in screen pixels so the labels stay sharp. It draws across from the left when it first shows, and a finished
// drill draws only the new stretch of line out to its point.

const NS = "http://www.w3.org/2000/svg";
let charts = 0;

function el(name, attrs, parent) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, String(v));
  if (parent) parent.appendChild(node);
  return node;
}

const r1 = (n) => Math.round(n * 10) / 10;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const short = (d) => `${MONTHS[d.getMonth()]} ${d.getDate()}`;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const FULL_MS = 1300;
const GROW_MS = 900;

/** How many leading days `before` and `after` share with the same words per minute. */
function sharedDays(before, after) {
  let n = 0;
  while (n < before.length && n < after.length && before[n].key === after[n].key && before[n].wpm === after[n].wpm) n += 1;
  return n;
}

/** A smooth path through points that never overshoots between them (monotone cubic). */
function smooth(points) {
  if (points.length < 2) return points.length ? `M${points[0][0]},${points[0][1]}` : "";
  const n = points.length;
  const slopes = [];
  for (let i = 0; i < n - 1; i += 1) slopes.push((points[i + 1][1] - points[i][1]) / (points[i + 1][0] - points[i][0]));
  const tangents = [slopes[0]];
  for (let i = 1; i < n - 1; i += 1) tangents.push(slopes[i - 1] * slopes[i] <= 0 ? 0 : (slopes[i - 1] + slopes[i]) / 2);
  tangents.push(slopes[n - 2]);
  let d = `M${r1(points[0][0])},${r1(points[0][1])}`;
  for (let i = 0; i < n - 1; i += 1) {
    const [x0, y0] = points[i];
    const [x1, y1] = points[i + 1];
    const h = (x1 - x0) / 3;
    d += ` C${r1(x0 + h)},${r1(y0 + tangents[i] * h)} ${r1(x1 - h)},${r1(y1 - tangents[i + 1] * h)} ${r1(x1)},${r1(y1)}`;
  }
  return d;
}

export class Chart {
  constructor(host, options = {}) {
    this.host = host;
    this.big = Boolean(options.big);
    this.days = [];
    this.size = "";
    this.draw = null;
    if ("ResizeObserver" in window) {
      new ResizeObserver(() => this.resize()).observe(host);
    }
  }

  /**
   * Shows `days`. `draw` is "full" (across from the left), "grow" (only the stretch that changed since the days
   * shown before), "held" (full, waiting for `play()`), or "none".
   */
  setDays(days, { draw = "none" } = {}) {
    const keep = draw === "grow" ? sharedDays(this.days, days) : 0;
    this.days = days;
    this.shown = false;
    this.draw = draw === "none" || reduced.matches ? null : { at: draw === "held" ? Infinity : performance.now(), keep };
    this.render();
  }

  /** Starts a held draw `delay` ms from now. */
  play(delay = 0) {
    if (!this.draw || this.draw.at !== Infinity) return;
    this.draw.at = performance.now() + delay;
    this.render();
  }

  resize() {
    const size = `${this.host.clientWidth}x${this.host.clientHeight}`;
    if (size === this.size) return;
    this.render();
  }

  render() {
    const width = this.host.clientWidth;
    const height = this.host.clientHeight;
    if (!width || !height || !this.days.length) return;
    this.size = `${width}x${height}`;
    const id = `ch${(charts += 1)}`;
    const big = this.big;
    const left = big ? 40 : 30;
    const right = big ? 46 : 38;
    const top = big ? 22 : 16;
    const bottom = 26;
    const w = width - left - right;
    const h = height - top - bottom;

    const withWpm = this.days.map((d, i) => ({ ...d, i })).filter((d) => d.wpm != null);
    const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img" });
    if (!withWpm.length) {
      svg.setAttribute("aria-label", "No drills in the last 30 days yet");
      this.host.replaceChildren(svg);
      return;
    }
    const wpms = withWpm.map((d) => d.wpm);
    let lo = Math.floor((Math.min(...wpms) - 4) / 10) * 10;
    let hi = Math.ceil((Math.max(...wpms) + 4) / 10) * 10;
    if (hi - lo < 20) hi = lo + 20;
    lo = Math.max(0, lo);
    const accs = withWpm.map((d) => d.accuracy);
    const accLo = Math.max(0, Math.min(0.9, Math.floor(Math.min(...accs) * 20) / 20));
    const x = (i) => left + (i / 29) * w;
    const y = (v) => top + h - ((v - lo) / (hi - lo)) * h;
    const ya = (v) => top + h - ((v - accLo) / (1 - accLo)) * h;

    const last = withWpm[withWpm.length - 1];
    svg.setAttribute("aria-label", `Words per minute over the last 30 days, latest ${Math.round(last.wpm)}`);
    const defs = el("defs", {}, svg);
    const grad = el("linearGradient", { id: `${id}-fill`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: 0, class: "grad-a" }, grad);
    el("stop", { offset: 1, class: "grad-b" }, grad);
    const clip = el("clipPath", { id: `${id}-clip` }, defs);
    const reveal = el("rect", { x: left - 6, y: 0, width: w + 12, height, class: "reveal" }, clip);

    const grid = el("g", { class: "grid" }, svg);
    const axis = el("g", { class: "axis" }, svg);
    // The finest round step that keeps the labels at least 22 px apart.
    const step = [10, 20, 25, 50, 100, 200, 250, 500, 1000].find((n) => (n / (hi - lo)) * h >= 22 && n >= (hi - lo > 40 || h < 120 ? 20 : 10)) || hi - lo;
    for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) {
      const ty = y(v);
      el("line", { x1: left, x2: left + w, y1: r1(ty), y2: r1(ty) }, grid);
      if (v > lo || big) {
        const label = el("text", { x: left - 8, y: r1(ty + 4), "text-anchor": "end" }, axis);
        label.textContent = Math.round(v);
      }
    }
    const accAxis = el("g", { class: "acc-axis" }, axis);
    [accLo, (accLo + 1) / 2, 1].forEach((v, idx) => {
      if (!big && idx === 1) return;
      const label = el("text", { x: left + w + 8, y: r1(ya(v) + 4), "text-anchor": "start" }, accAxis);
      label.textContent = `${Math.round(v * 100)}%`;
    });
    const first = el("text", { x: left, y: height - 6, "text-anchor": "start" }, axis);
    first.textContent = short(this.days[0].date);
    if (big) {
      const mid = el("text", { x: r1(x(15)), y: height - 6, "text-anchor": "middle" }, axis);
      mid.textContent = short(this.days[15].date);
    }
    const end = el("text", { x: left + w, y: height - 6, "text-anchor": "end" }, axis);
    end.textContent = "Today";

    const pts = withWpm.map((d) => [x(d.i), y(d.wpm)]);
    const line = smooth(pts);
    const area = `${line} L${r1(pts[pts.length - 1][0])},${top + h} L${r1(pts[0][0])},${top + h} Z`;
    const plot = el("g", { "clip-path": `url(#${id}-clip)` }, svg);
    el("path", { d: area, fill: `url(#${id}-fill)`, class: "area" }, plot);
    const accPts = withWpm.map((d) => [x(d.i), ya(d.accuracy)]);
    el("path", { d: smooth(accPts), class: "acc", pathLength: 1 }, plot);
    const wpmPath = el("path", { d: line, class: "wpm", pathLength: 1 }, svg);

    const dots = el("g", {}, svg);
    let lastDot = null;
    withWpm.forEach((d, n) => {
      const isLast = n === withWpm.length - 1;
      if (!big && !isLast && !d.touch) return;
      const dot = el("circle", { cx: r1(x(d.i)), cy: r1(y(d.wpm)), r: isLast ? 4.5 : big ? 3.5 : 3, class: "dot" }, dots);
      if (isLast) {
        dot.classList.add("is-last");
        lastDot = dot;
      }
      if (d.touch) dot.classList.add("is-touch");
    });
    const tag = el("text", { x: r1(x(last.i) - 8), y: r1(y(last.wpm) - 12), "text-anchor": "end", class: "tag" }, svg);
    tag.textContent = `${Math.round(last.wpm)} wpm`;

    this.host.replaceChildren(svg);
    // A chart set while its view was hidden draws when it first shows.
    if (this.draw && !this.shown && this.draw.at < performance.now()) this.draw.at = performance.now();
    this.shown = true;
    if (this.draw) this.animate({ svg, pts, wpmPath, reveal, dots, lastDot, tag, withWpm, left });
  }

  /** Runs the draw from where it stands now, so a resize partway through carries on rather than starting over. */
  animate({ svg, pts, wpmPath, reveal, dots, lastDot, tag, withWpm, left }) {
    const kept = withWpm.filter((d) => d.i < this.draw.keep).length;
    if (kept >= pts.length) {
      this.draw = null;
      return;
    }
    const grow = kept >= 2;
    const duration = grow ? GROW_MS : FULL_MS;
    const wait = this.draw.at - performance.now();
    if (wait < -(duration + 400)) {
      this.draw = null;
      return;
    }
    let from = 0;
    let fromScale = 0;
    if (grow) {
      const part = el("path", { d: smooth(pts.slice(0, kept)) }, svg);
      from = Math.min(1, part.getTotalLength() / Math.max(1, wpmPath.getTotalLength()));
      part.remove();
      const span = Number(reveal.getAttribute("width"));
      fromScale = Math.min(1, (pts[kept - 1][0] - (left - 6)) / span);
    }
    const easing = getComputedStyle(document.documentElement).getPropertyValue("--ease-in-out").trim() || "ease-in-out";
    const timing = { duration, delay: wait === Infinity ? 1e9 : wait, easing, fill: "backwards" };
    wpmPath.animate(
      [
        { strokeDasharray: "1 1", strokeDashoffset: 1 - from },
        { strokeDasharray: "1 1", strokeDashoffset: 0 },
      ],
      timing,
    );
    reveal.animate([{ transform: `scaleX(${fromScale})` }, { transform: "scaleX(1)" }], timing);
    const popAt = timing.delay + duration - 120;
    const pop = { duration: 320, delay: popAt, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)", fill: "backwards" };
    const popIn = [
      { opacity: 0, transform: "scale(0.3)" },
      { opacity: 1, transform: "scale(1)" },
    ];
    const popping = grow ? [lastDot] : [...dots.children];
    popping.forEach((dot) => dot?.animate(popIn, pop));
    tag.animate([{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "translateY(0)" }], { ...pop, delay: popAt + 60 });
  }
}
