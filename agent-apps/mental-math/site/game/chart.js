// The thirty-day curve and the score ring, drawn in SVG and eased with the Web Animations API.

import { reduced, EASE_OUT } from "./motion.js";

const NS = "http://www.w3.org/2000/svg";
let gradientId = 0;

const el = (name, attrs = {}) => {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
};

const fmt = new Intl.NumberFormat("en-US");
const dayFmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });

function niceMax(value) {
  if (value <= 0) return 100;
  const mag = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    if (step * mag >= value) return step * mag;
  }
  return 10 * mag;
}

// A monotone cubic through the points, so the line never overshoots a day's score.
function smoothPath(pts) {
  if (pts.length === 1) return `M${pts[0][0]},${pts[0][1]}`;
  const n = pts.length;
  const dx = [];
  const m = [];
  for (let i = 0; i < n - 1; i += 1) {
    dx.push(pts[i + 1][0] - pts[i][0]);
    m.push((pts[i + 1][1] - pts[i][1]) / (dx[i] || 1));
  }
  const t = [m[0]];
  for (let i = 1; i < n - 1; i += 1) t.push(m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2);
  t.push(m[n - 2]);
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < n - 1; i += 1) {
    const h = dx[i] / 3;
    d += ` C${pts[i][0] + h},${pts[i][1] + t[i] * h} ${pts[i + 1][0] - h},${pts[i + 1][1] - t[i + 1] * h} ${pts[i + 1][0]},${pts[i + 1][1]}`;
  }
  return d;
}

/** A curve that redraws itself on resize. `draw(points, how)` with how "draw", "slide-left", "slide-right", or "none". */
export function createCurve(container) {
  let points = [];
  let svg = null;
  const id = `curve-grad-${(gradientId += 1)}`;

  function render(how) {
    const w = Math.round(container.clientWidth);
    const h = Math.round(container.clientHeight);
    if (!w || !h) return;
    container.textContent = "";
    if (!points.length) {
      const empty = document.createElement("div");
      empty.className = "curve-empty";
      empty.textContent = "Your first drill draws the first point.";
      container.append(empty);
      svg = null;
      return;
    }
    // Under 100 px tall (the phone panel) the curve is a sparkline: no axes or labels, the ring beside it holds the score.
    const compact = h < 100;
    const padL = compact ? 4 : 6;
    const padR = compact ? 10 : 44;
    const padT = compact ? 10 : 28;
    const padB = compact ? 4 : 26;
    const scores = points.map((p) => p.score);
    const max = compact ? Math.max(...scores) : niceMax(Math.max(...scores) * 1.08);
    // The sparkline spans its own range so the month's climb fills the height.
    const lo = compact && points.length > 1 ? Math.min(...scores) * 0.9 : 0;
    const x = (day) => padL + (day / 29) * (w - padL - padR);
    const y = (score) => padT + (1 - (score - lo) / (max - lo || 1)) * (h - padT - padB);

    svg = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": label(points) });
    const defs = el("defs");
    const grad = el("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 });
    grad.append(el("stop", { offset: 0, class: "curve-stop-top" }), el("stop", { offset: 1, class: "curve-stop-bottom" }));
    defs.append(grad);
    svg.append(defs);

    for (const f of compact ? [] : [0.5, 1]) {
      svg.append(el("line", { class: "curve-grid", x1: padL, x2: w - padR, y1: y(max * f), y2: y(max * f) }));
      const t = el("text", { class: "curve-label", x: w - padR + 8, y: y(max * f) + 4 });
      t.textContent = fmt.format(max * f);
      svg.append(t);
    }
    svg.append(el("line", { class: "curve-base", x1: padL, x2: w - padR, y1: h - padB, y2: h - padB }));
    const now = new Date();
    for (const [day, anchor] of compact ? [] : [[0, "start"], [15, "middle"], [29, "end"]]) {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (29 - day));
      const t = el("text", { class: "curve-label", x: x(day), y: h - 6, "text-anchor": anchor });
      t.textContent = day === 29 ? "Today" : dayFmt.format(d);
      svg.append(t);
    }

    const pts = points.map((p) => [x(p.day), y(p.score)]);
    const line = smoothPath(pts);
    const group = el("g", { class: "curve-plot" });
    const fill = el("path", {
      class: "curve-fill",
      fill: `url(#${id})`,
      d: `${line} L${pts[pts.length - 1][0]},${h - padB} L${pts[0][0]},${h - padB} Z`,
    });
    const stroke = el("path", { class: "curve-line", d: line, pathLength: 1 });
    group.append(fill, stroke);
    if (pts.length === 1) {
      const [px, py] = pts[0];
      group.append(el("line", { class: "curve-drop", x1: px, x2: px, y1: py, y2: h - padB }));
      group.append(el("circle", { class: "curve-halo", cx: px, cy: py, r: compact ? 10 : 18 }));
    }
    const dots = el("g");
    pts.forEach(([px, py], i) => {
      const last = i === pts.length - 1;
      if (compact && !last) return;
      dots.append(el("circle", { class: last ? "curve-dot curve-dot-last" : "curve-dot", cx: px, cy: py, r: last ? (compact ? 4.5 : 6) : 3.5 }));
    });
    group.append(dots);
    const lastPt = pts[pts.length - 1];
    const value = el("text", {
      class: "curve-value",
      x: Math.min(lastPt[0], w - padR - 4),
      y: Math.max(14, lastPt[1] - 14),
      "text-anchor": lastPt[0] > w * 0.7 ? "end" : "middle",
    });
    value.textContent = fmt.format(points[points.length - 1].score);
    if (!compact) group.append(value);
    svg.append(group);
    container.append(svg);

    if (reduced() || how === "none") return;
    if (how === "draw") {
      stroke.animate([{ strokeDasharray: "1 1", strokeDashoffset: 1 }, { strokeDasharray: "1 1", strokeDashoffset: 0 }], {
        duration: 1100,
        easing: EASE_OUT,
      });
      fill.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 700, delay: 350, easing: EASE_OUT, fill: "backwards" });
      dots.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 400, delay: 700, easing: EASE_OUT, fill: "backwards" });
      value.animate([{ opacity: 0, transform: "translateY(6px)" }, { opacity: 1, transform: "none" }], {
        duration: 400,
        delay: 900,
        easing: EASE_OUT,
        fill: "backwards",
      });
    } else if (how === "slide-left" || how === "slide-right") {
      const from = how === "slide-left" ? 36 : -36;
      group.animate([{ opacity: 0, transform: `translateX(${from}px)` }, { opacity: 1, transform: "none" }], {
        duration: 360,
        easing: EASE_OUT,
      });
    }
  }

  const observer = new ResizeObserver(() => render("none"));
  observer.observe(container);

  return {
    draw(next, how = "draw") {
      points = next;
      render(how);
    },
  };
}

function label(points) {
  const last = points[points.length - 1];
  return `${points.length} days in the last thirty; the latest ${fmt.format(last.score)} points.`;
}

/** Eases a ring to `fraction` (0..1) and counts `target` up into `numberEl`. */
export function fillRing(arc, fraction, numberEl, target, { duration = 1100, delay = 0 } = {}) {
  const end = 100 - Math.max(0, Math.min(1, fraction)) * 100;
  if (reduced()) {
    arc.style.setProperty("stroke-dashoffset", String(end));
    if (numberEl) numberEl.textContent = fmt.format(target);
    return;
  }
  arc.style.setProperty("stroke-dashoffset", String(end));
  arc.animate([{ strokeDashoffset: 100 }, { strokeDashoffset: end }], { duration, delay, easing: EASE_OUT, fill: "backwards" });
  if (!numberEl) return;
  const start = performance.now() + delay;
  numberEl.textContent = "0";
  const tick = (now) => {
    const t = Math.min(1, Math.max(0, (now - start) / duration));
    const eased = 1 - (1 - t) ** 4;
    numberEl.textContent = fmt.format(Math.round(target * eased));
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

export { fmt };
