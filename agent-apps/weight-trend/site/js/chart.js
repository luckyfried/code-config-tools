// The chart, drawn by hand in SVG: faint daily weigh-ins, the smoothed trend with its shadow and the gradient under it,
// the dashed goal, and the marker where the trend meets the goal. It opens by drawing the trend from the first weigh-in
// to today, then running the forecast dash on to the goal, where the marker lands. The marker keeps its last position,
// so after a new weigh-in it eases from where it was to where it now lands.

import { fromKg } from "./store.js";
import * as fmt from "./format.js";

const NS = "http://www.w3.org/2000/svg";
const EASE_MOVE = "cubic-bezier(0.77, 0, 0.175, 1)";
const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const AHEAD = { 90: 120, 365: 240, all: 365 };
const INTRO = { delay: 300, draw: 1000, forecast: 460, land: 300 };
const easeInOut = (t) => (t < 0.5 ? 4 * t ** 3 : 1 - (-2 * t + 2) ** 3 / 2);
const easeOut = (t) => 1 - (1 - t) ** 3;
let uid = 0;

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const r1 = (n) => Math.round(n * 10) / 10;

function node(name, attrs, parent) {
  const el = document.createElementNS(NS, name);
  if (attrs) for (const key in attrs) el.setAttribute(key, attrs[key]);
  if (parent) parent.appendChild(el);
  return el;
}

function niceStep(span, target) {
  const raw = span / target;
  return [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100].find((s) => s >= raw) || 200;
}

function smoothPath(pts) {
  if (!pts.length) return "";
  let d = `M${r1(pts[0][0])},${r1(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i += 1) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const c1x = Math.min(p2[0], Math.max(p1[0], p1[0] + (p2[0] - p0[0]) / 6));
    const c2x = Math.min(p2[0], Math.max(p1[0], p2[0] - (p3[0] - p1[0]) / 6));
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += `C${r1(c1x)},${r1(c1y)} ${r1(c2x)},${r1(c2y)} ${r1(p2[0])},${r1(p2[1])}`;
  }
  return d;
}

function monthTicks(startDay, endDay, maxTicks) {
  const ticks = [];
  const first = fmtDate(startDay);
  let y = first.getFullYear();
  let m = first.getMonth() + 1;
  for (;;) {
    const day = Math.round(Date.UTC(y, m, 1) / 86400000);
    if (day > endDay) break;
    ticks.push(day);
    m += 1;
    if (m > 11) {
      m = 0;
      y += 1;
    }
  }
  const every = Math.max(1, Math.ceil(ticks.length / maxTicks));
  return ticks.filter((_, i) => i % every === 0);
}

function fmtDate(day) {
  const d = new Date(day * 86400000);
  return new Date(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

function weekTicks(startDay, endDay, maxTicks) {
  const ticks = [];
  let d = startDay;
  while (fmtDate(d).getDay() !== 1) d += 1;
  const step = Math.max(7, Math.ceil((endDay - startDay) / maxTicks / 7) * 7);
  for (; d <= endDay; d += step) ticks.push(d);
  return ticks;
}

export function createChart(host, { span = 90 } = {}) {
  const id = `wt${(uid += 1)}`;
  const svg = node("svg", { class: "chart-svg", role: "img" }, host);
  let model = null;
  let markerAt = null;
  let size = { w: 0, h: 0 };
  let introRaf = 0;

  new ResizeObserver(() => {
    const w = host.clientWidth;
    const h = host.clientHeight;
    if (!w || !h || (w === size.w && h === size.h)) return;
    size = { w, h };
    if (model) draw(model, {});
  }).observe(host);

  function setSpan(next) {
    span = next;
    markerAt = null;
    if (model) draw(model, { intro: true });
  }

  function draw(next, { intro = false, ease = false } = {}) {
    model = next;
    cancelAnimationFrame(introRaf);
    const W = host.clientWidth;
    const H = host.clientHeight;
    if (!W || !H) return;
    size = { w: W, h: H };
    const motion = !reducedMotion();
    const { points, goalKg, units, proj, showProjection, today } = model;
    const narrow = W < 520;
    const pad = { l: narrow ? 38 : 48, r: narrow ? 10 : 20, t: 22, b: 30 };
    const pw = W - pad.l - pad.r;
    const ph = H - pad.t - pad.b;

    // The axis starts two days before the first weigh-in, so a short history spreads across the chart.
    const spanStart = span === "all" ? today - 29 : today - span + 1;
    const startDay = points.length ? Math.max(span === "all" ? -Infinity : spanStart, points[0].day - 2) : spanStart;
    let endDay = today + (narrow ? 3 : 2);
    const crossing = proj.state === "toward" && showProjection ? Math.ceil(proj.day) : null;
    // The future gets at most half again the history's width, so the weigh-ins never shrink to a sliver.
    const reach = Math.min(AHEAD[span], Math.max(28, Math.round((today - startDay) * 1.5)));
    const markerShown = crossing !== null && crossing - today <= reach;
    if (markerShown) endDay = Math.max(endDay, crossing + Math.max(4, Math.round((crossing - startDay) * 0.05)));

    const firstIn = points.findIndex((p) => p.day >= startDay);
    const shown = firstIn < 0 ? [] : points.slice(Math.max(0, firstIn - 1));
    const inside = firstIn < 0 ? [] : points.slice(firstIn);

    const goal = fromKg(goalKg, units);
    let lo = goal;
    let hi = goal;
    for (const p of inside) {
      const v = fromKg(p.value, units);
      const t = fromKg(p.trend, units);
      lo = Math.min(lo, v, t);
      hi = Math.max(hi, v, t);
    }
    const spread = hi - lo;
    const margin = Math.max(units === "lb" ? 1.5 : 0.7, spread * 0.1);
    lo -= margin;
    hi += margin;
    const step = niceStep(hi - lo, ph < 220 ? 4 : ph < 360 ? 5 : 6);
    lo = Math.floor(lo / step) * step;
    hi = Math.ceil(hi / step) * step;

    const x = (day) => pad.l + ((day - startDay) / (endDay - startDay)) * pw;
    const y = (kg) => pad.t + ((hi - fromKg(kg, units)) / (hi - lo)) * ph;

    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);

    const defs = node("defs", null, svg);
    const grad = node("linearGradient", { id: `${id}-area`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    node("stop", { offset: "0", class: "area-top" }, grad);
    node("stop", { offset: "1", class: "area-bottom" }, grad);
    const plotClip = node("clipPath", { id: `${id}-plot` }, defs);
    node("rect", { x: pad.l, y: 0, width: pw, height: H }, plotClip);
    const revealClip = node("clipPath", { id: `${id}-reveal` }, defs);
    const lastX = inside.length ? x(inside[inside.length - 1].day) : pad.l;
    const revealWidth = Math.max(1, lastX - pad.l + 16);
    const revealRect = node("rect", { x: pad.l - 8, y: 0, width: revealWidth, height: H }, revealClip);
    const foreClip = node("clipPath", { id: `${id}-fore` }, defs);
    const foreRect = node("rect", { x: 0, y: 0, width: W, height: H }, foreClip);

    const todayX = x(today);
    node("rect", { class: "future", x: todayX, y: pad.t, width: Math.max(0, pad.l + pw - todayX), height: ph }, svg);

    const grid = node("g", null, svg);
    const decimals = step < 1 ? 1 : 0;
    for (let v = lo; v <= hi + step / 2; v += step) {
      const gy = pad.t + ((hi - v) / (hi - lo)) * ph;
      node("line", { class: "grid-line", x1: pad.l, x2: pad.l + pw, y1: Math.round(gy) + 0.5, y2: Math.round(gy) + 0.5 }, grid);
      const label = node("text", { class: "axis-label", x: pad.l - 8, y: gy + 4, "text-anchor": "end" }, grid);
      label.textContent = fmt.plain(v, decimals);
    }
    const ticks = endDay - startDay > 70 ? monthTicks(startDay, endDay, Math.max(3, Math.floor(pw / 90))) : weekTicks(startDay, endDay, Math.max(3, Math.floor(pw / 90)));
    const longSpan = endDay - startDay > 400;
    for (const t of ticks) {
      const tx = x(t);
      if (tx < pad.l + 12 || tx > pad.l + pw - 12) continue;
      const label = node("text", { class: "axis-label", x: tx, y: H - 8, "text-anchor": "middle" }, grid);
      label.textContent = longSpan ? fmt.day(t, "monthYear") : endDay - startDay > 70 ? fmt.day(t, "month") : fmt.day(t);
    }

    node("line", { class: "today-line", x1: todayX, x2: todayX, y1: pad.t, y2: pad.t + ph }, svg);
    const todayLabel = node("text", { class: "today-label", x: todayX, y: pad.t - 8, "text-anchor": "middle" }, svg);
    todayLabel.textContent = "Today";

    const gy = y(goalKg);
    const goalLine = node("line", { class: "goal-line", x1: pad.l, x2: pad.l + pw, y1: gy, y2: gy }, svg);

    const plot = node("g", { "clip-path": `url(#${id}-plot)` }, svg);
    const revealed = node("g", { "clip-path": `url(#${id}-reveal)` }, plot);
    const trendPts = shown.map((p) => [x(p.day), y(p.trend)]);
    const linePath = smoothPath(trendPts);
    if (trendPts.length > 1) {
      const bottom = pad.t + ph;
      const area = `${linePath}L${r1(trendPts[trendPts.length - 1][0])},${bottom}L${r1(trendPts[0][0])},${bottom}Z`;
      node("path", { class: "trend-area", d: area, fill: `url(#${id}-area)` }, revealed);
    }

    const dots = node("g", null, revealed);
    const radius = pw / Math.max(1, endDay - startDay) > 5 ? 3.2 : 2.2;
    for (const p of inside) {
      const px = x(p.day);
      const py = y(p.value);
      const ty = y(p.trend);
      if (Math.abs(py - ty) > radius + 1) node("line", { class: "stem", x1: px, x2: px, y1: py, y2: ty }, dots);
    }
    for (const p of inside) {
      const isToday = p.day === today;
      node("circle", { class: isToday ? "point point-today" : "point", cx: r1(x(p.day)), cy: r1(y(p.value)), r: isToday ? 5 : radius }, dots);
    }

    const line = trendPts.length > 1 ? node("path", { class: "trend-line", d: linePath }, plot) : null;

    let head = null;
    if (inside.length) {
      const last = inside[inside.length - 1];
      head = node("circle", { class: "trend-head", cx: r1(x(last.day)), cy: r1(y(last.trend)), r: 5.5 }, svg);
    }

    const goalTag = node("g", { class: "goal-tag" }, svg);
    const goalText = node("text", { x: pad.l + 18, y: 0 }, goalTag);
    goalText.textContent = `Goal ${fmt.weight(goalKg, units)}`;
    const gw = goalText.getComputedTextLength() + 20;
    const tagY = gy - pad.t > 34 ? gy - 30 : gy + 8;
    node("rect", { x: pad.l + 8, y: tagY, width: gw, height: 22, rx: 11 }, goalTag).after(goalText);
    goalText.setAttribute("y", tagY + 15);

    let guide = null;
    let marker = null;
    let target = null;
    if (markerShown && inside.length) {
      const last = inside[inside.length - 1];
      const fx = x(last.day);
      const fy = y(last.trend);
      target = { x: x(proj.day), y: gy };
      guide = node("path", { class: "projection", d: `M${r1(fx)},${r1(fy)}L${r1(target.x)},${r1(target.y)}`, "clip-path": `url(#${id}-fore)` }, svg);
      marker = node("g", { class: "marker" }, svg);
      node("circle", { class: "marker-halo", r: 15 }, marker);
      node("circle", { class: "marker-dot", r: 7 }, marker);
      const tag = node("g", { class: "marker-tag" }, marker);
      const text = node("text", { y: -24, "text-anchor": "middle" }, tag);
      text.textContent = fmt.day(Math.round(proj.day));
      const tw = text.getComputedTextLength() + 18;
      let tx = -tw / 2;
      if (target.x + tw / 2 > pad.l + pw + pad.r - 2) tx = pad.l + pw + pad.r - 2 - target.x - tw;
      const above = target.y - pad.t > 44;
      const ty = above ? -40 : 18;
      node("rect", { x: tx, y: ty, width: tw, height: 24, rx: 12 }, tag).after(text);
      text.setAttribute("x", tx + tw / 2);
      text.setAttribute("y", ty + 16);
      marker.setAttribute("transform", `translate(${r1(target.x)},${r1(target.y)})`);
    } else if (crossing !== null && inside.length) {
      // The crossing lies past the chart's edge: the dotted line heads toward it and leaves at the edge.
      const last = inside[inside.length - 1];
      const edgeDay = endDay;
      const edgeTrend = last.trend + (proj.week / 7) * (edgeDay - last.day);
      guide = node("path", { class: "projection", d: `M${r1(x(last.day))},${r1(y(last.trend))}L${r1(x(edgeDay))},${r1(y(edgeTrend))}`, "clip-path": `url(#${id}-fore)` }, svg);
    }

    if (!inside.length) {
      const empty = node("text", { class: "chart-empty", x: pad.l + pw / 2, y: pad.t + ph / 2 - (gy > pad.t + ph / 2 - 30 && gy < pad.t + ph / 2 + 30 ? 40 : 0), "text-anchor": "middle" }, svg);
      empty.textContent = "Log your first weigh-in to start the line.";
    }

    svg.setAttribute("aria-label", describe(model, inside, markerShown));

    if (motion && intro && line) {
      const end = guide ? guide.getPointAtLength(guide.getTotalLength()) : null;
      playIntro({ line, revealRect, foreRect, head, guide, end, marker, goalLine, goalTag, H, left: pad.l - 8, revealWidth });
    } else if (motion && ease && marker) {
      if (markerAt) {
        moveMarker(marker, markerAt, target, { duration: 700, delay: 0 });
        guide.animate([{ opacity: 0 }, { opacity: 0 }, { opacity: 0.75 }], { duration: 900, easing: EASE_OUT });
      } else {
        marker.animate([{ opacity: 0, transform: `translate(${target.x}px, ${target.y}px) scale(0.6)` }, { opacity: 1, transform: `translate(${target.x}px, ${target.y}px) scale(1)` }], { duration: 400, easing: EASE_OUT });
      }
    }
    markerAt = target;
  }

  // The opening: the trend draws from the first weigh-in to today with its head as the pen, the weigh-ins and the
  // gradient fill in behind it, then the forecast dash runs on from today to the goal and the marker lands there.
  function playIntro({ line, revealRect, foreRect, head, guide, end, marker, goalLine, goalTag, H, left, revealWidth }) {
    const total = line.getTotalLength();
    const headAt = head ? { x: head.getAttribute("cx"), y: head.getAttribute("cy") } : null;
    const from = headAt ? { x: Number(headAt.x), y: Number(headAt.y) } : null;
    const markerTo = marker ? marker.getAttribute("transform") : null;
    const tag = marker ? marker.querySelector(".marker-tag") : null;
    const halo = marker ? marker.querySelector(".marker-halo") : null;

    line.setAttribute("stroke-dasharray", `${total} ${total}`);
    line.setAttribute("stroke-dashoffset", total);
    revealRect.setAttribute("width", 0);
    if (guide) foreRect.setAttribute("width", 0);
    if (marker) marker.setAttribute("opacity", 0);
    if (head) head.classList.add("trend-head-pen");
    goalLine.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, easing: EASE_OUT, fill: "backwards" });
    goalTag.animate([{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "none" }], { duration: 420, delay: 240, easing: EASE_OUT, fill: "backwards" });

    const start = performance.now() + INTRO.delay;
    const foreStart = start + INTRO.draw;
    const foreEnd = foreStart + (guide ? INTRO.forecast : 0);
    let landed = false;
    const frame = (now) => {
      const a = Math.min(1, Math.max(0, (now - start) / INTRO.draw));
      const len = total * easeInOut(a);
      const tip = line.getPointAtLength(len);
      line.setAttribute("stroke-dashoffset", r1(total - len));
      revealRect.setAttribute("width", a >= 1 ? revealWidth : Math.max(0, r1(tip.x - left)));
      if (head) {
        head.setAttribute("cx", r1(tip.x));
        head.setAttribute("cy", r1(tip.y));
        head.setAttribute("opacity", now < start ? 0 : 1);
      }
      if (a >= 1) {
        line.removeAttribute("stroke-dasharray");
        line.removeAttribute("stroke-dashoffset");
        if (head) {
          head.setAttribute("cx", headAt.x);
          head.setAttribute("cy", headAt.y);
          head.classList.remove("trend-head-pen");
        }
      }
      if (guide && now >= foreStart) {
        const b = easeOut(Math.min(1, (now - foreStart) / INTRO.forecast));
        foreRect.setAttribute("x", r1(from.x - 4));
        foreRect.setAttribute("width", r1((end.x - from.x + 8) * b));
        if (marker) {
          marker.setAttribute("opacity", 1);
          marker.setAttribute("transform", `translate(${r1(from.x + (end.x - from.x) * b)},${r1(from.y + (end.y - from.y) * b)})`);
          if (tag) tag.setAttribute("opacity", 0);
        }
      }
      if (now >= foreEnd && a >= 1) {
        if (guide) {
          foreRect.setAttribute("x", 0);
          foreRect.setAttribute("width", host.clientWidth);
        }
        if (marker && !landed) {
          landed = true;
          marker.setAttribute("transform", markerTo);
          if (tag) {
            tag.removeAttribute("opacity");
            tag.animate([{ opacity: 0, transform: "translateY(6px) scale(0.9)" }, { opacity: 1, transform: "none" }], { duration: INTRO.land, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" });
          }
          if (halo) halo.animate([{ transform: "scale(0.3)", opacity: 0.6 }, { transform: "scale(1.6)", opacity: 0 }, { transform: "scale(1)", opacity: 0.18 }], { duration: INTRO.land * 2, easing: EASE_OUT });
        }
        return;
      }
      introRaf = requestAnimationFrame(frame);
    };
    introRaf = requestAnimationFrame(frame);
  }

  function moveMarker(marker, from, to, { duration, delay, fade = false }) {
    const frames = [
      { transform: `translate(${from.x}px, ${from.y}px)`, opacity: fade ? 0 : 1 },
      { transform: `translate(${to.x}px, ${to.y}px)`, opacity: 1 },
    ];
    if (fade) frames.splice(1, 0, { transform: `translate(${from.x + (to.x - from.x) * 0.12}px, ${from.y + (to.y - from.y) * 0.12}px)`, opacity: 1, offset: 0.2 });
    marker.animate(frames, { duration, delay, easing: EASE_MOVE, fill: "backwards" });
  }

  return { draw, setSpan };
}

function describe({ goalKg, units, proj }, inside, markerShown) {
  if (!inside.length) return `No weigh-ins yet. Goal ${fmt.weight(goalKg, units)}.`;
  const last = inside[inside.length - 1];
  let text = `${inside.length} weigh-ins. Trend ${fmt.weight(last.trend, units)}, goal ${fmt.weight(goalKg, units)}.`;
  if (markerShown) text += ` The trend reaches the goal on ${fmt.day(Math.round(proj.day), "long")}.`;
  return text;
}
