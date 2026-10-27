// One activity: the route flies in from its tile and draws itself at the recorded pace, then the facts, the pace
// strip, the elevation, and the splits.
import * as f from "./format.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const DRAW_MS = 2000;
const FLY_MS = 520;
const VIEW = 1140;

export function createDetail({ units, reduced, wide, onClose, onStep }) {
  const $ = (id) => document.getElementById(id);
  const root = $("detail");
  const scroller = $("detail-scroll");
  const box = $("route-box");
  const svg = $("route");
  const ghost = $("route-ghost");
  const line = $("route-line");
  const startDot = $("route-start");
  const head = $("route-head");
  const scrub = $("route-scrub");
  const strip = $("pace-strip");
  const ele = $("elevation");
  const eleArea = $("ele-area");
  const eleLine = $("ele-line");
  const cursor = $("ele-cursor");
  const readout = $("ele-readout");
  const cache = new Map();
  let current = null;
  let track = null;
  let geometry = null;
  let drawFrame = 0;
  let flight = null;
  let token = 0;
  let open = false;
  let lastFocus = null;

  $("close").addEventListener("click", () => onClose());
  $("prev").addEventListener("click", () => onStep(-1));
  $("next").addEventListener("click", () => onStep(1));

  function load(a) {
    if (!cache.has(a.id)) {
      cache.set(
        a.id,
        fetch(a.track)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
      );
    }
    return cache.get(a.id);
  }

  function sizeStroke() {
    const w = box.getBoundingClientRect().width;
    if (w > 0) svg.style.setProperty("--sw", `${((1.5 * VIEW) / w).toFixed(2)}px`);
  }
  new ResizeObserver(sizeStroke).observe(box);

  // ---------- the facts ----------

  function fact(label, value, unit) {
    const wrap = document.createElement("div");
    wrap.className = "fact";
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = value || "—";
    if (value && unit) {
      const small = document.createElement("small");
      small.textContent = unit;
      dd.append(small);
    }
    wrap.append(dt, dd);
    return wrap;
  }

  function renderFacts(a) {
    $("detail-name").textContent = a.name;
    $("detail-when").textContent = f.longDate(a.date, a.time);
    const p = f.pace(a.distance, a.duration, units, a.sport);
    const c = f.climb(a.gain, units);
    $("facts").replaceChildren(
      fact("Distance", f.distance(a.distance, units, 2), units),
      fact("Moving time", a.duration ? f.clock(a.duration) : ""),
      fact(a.sport === "ride" ? "Average speed" : "Average pace", p.value, p.unit),
      fact("Climb", c.value, c.unit),
    );
    $("pace-unit").textContent = units === "km" ? "kilometer" : "mile";
    const link = $("gpx-link");
    link.href = a.file;
    link.setAttribute("download", a.file.split("/").pop());
  }

  // ---------- the route ----------

  function setGhost(a) {
    ghost.setAttribute("points", a.points.map((p) => `${p[0]},${p[1]}`).join(" "));
    box.style.setProperty("--len", getComputedStyle(document.querySelector(`.tile[data-id="${CSS.escape(a.id)}"]`) ?? box).getPropertyValue("--len") || "0");
    const first = a.points[0];
    startDot.setAttribute("cx", first[0]);
    startDot.setAttribute("cy", first[1]);
  }

  function buildGeometry(t) {
    const n = t.x.length;
    const cum = new Float64Array(n);
    let d = "M" + t.x[0] + " " + t.y[0];
    for (let i = 1; i < n; i += 1) {
      cum[i] = cum[i - 1] + Math.hypot(t.x[i] - t.x[i - 1], t.y[i] - t.y[i - 1]);
      d += "L" + t.x[i] + " " + t.y[i];
    }
    return { d, cum, total: cum[n - 1] || 1 };
  }

  // Where the line has reached a fraction u of the way through the moving time, as an index and a blend.
  function atTime(u) {
    const t = track.t;
    const target = u * t[t.length - 1];
    let lo = 0;
    let hi = t.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (t[mid] < target) lo = mid + 1;
      else hi = mid;
    }
    const i = Math.max(1, lo);
    const span = t[i] - t[i - 1];
    return { i, k: span > 0 ? (target - t[i - 1]) / span : 1 };
  }

  function atLength(u) {
    const target = u * geometry.total;
    const cum = geometry.cum;
    let lo = 0;
    let hi = cum.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (cum[mid] < target) lo = mid + 1;
      else hi = mid;
    }
    const i = Math.max(1, lo);
    const span = cum[i] - cum[i - 1];
    return { i, k: span > 0 ? (target - cum[i - 1]) / span : 1 };
  }

  function placeHead(i, k) {
    const x = track.x[i - 1] + (track.x[i] - track.x[i - 1]) * k;
    const y = track.y[i - 1] + (track.y[i] - track.y[i - 1]) * k;
    head.setAttribute("cx", x.toFixed(1));
    head.setAttribute("cy", y.toFixed(1));
    return geometry.cum[i - 1] + (geometry.cum[i] - geometry.cum[i - 1]) * k;
  }

  function draw() {
    cancelAnimationFrame(drawFrame);
    line.setAttribute("d", geometry.d);
    line.style.setProperty("stroke-dasharray", `${geometry.total.toFixed(1)} ${(geometry.total + 10).toFixed(1)}`);
    if (reduced.matches) {
      line.style.setProperty("stroke-dashoffset", "0");
      head.classList.remove("is-on");
      return;
    }
    const timed = Array.isArray(track.t) && track.t[track.t.length - 1] > 0;
    head.classList.add("is-on");
    const begin = performance.now();
    const frame = (now) => {
      const u = Math.min(1, (now - begin) / DRAW_MS);
      // Timed tracks draw at the recorded pace, so fast stretches draw fast; untimed ones draw evenly.
      const at = timed ? atTime(u) : atLength(u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);
      const reached = placeHead(at.i, at.k);
      line.style.setProperty("stroke-dashoffset", (geometry.total - reached).toFixed(1));
      if (u < 1) drawFrame = requestAnimationFrame(frame);
      else {
        line.style.setProperty("stroke-dashoffset", "0");
        head.classList.remove("is-on");
      }
    };
    line.style.setProperty("stroke-dashoffset", geometry.total.toFixed(1));
    drawFrame = requestAnimationFrame(frame);
  }

  function clearRoute() {
    cancelAnimationFrame(drawFrame);
    line.setAttribute("d", "");
    head.classList.remove("is-on");
    scrub.classList.remove("is-on");
  }

  // ---------- the pace strip ----------

  // Each split's speed, and where it sits from slow (0) to fast (1) around the activity's own average.
  function speeds(a, splits) {
    const v = splits.map((s) => (s.t ? s.d / s.t : null));
    const ok = v.filter((x, i) => x !== null && !splits[i].flag && splits[i].d >= 0.3 * f.UNIT_M[units]);
    const mean = ok.reduce((s, x) => s + x, 0) / (ok.length || 1);
    const sd = Math.max(mean * 0.025, Math.sqrt(ok.reduce((s, x) => s + (x - mean) ** 2, 0) / (ok.length || 1)));
    const k = v.map((x) => (x === null ? null : Math.max(0, Math.min(1, 0.5 + (x - mean) / (3 * sd)))));
    return { v, k, min: Math.min(...ok), max: Math.max(...ok) };
  }

  // Slower than the activity's average leans to --pace-slow, faster to --pace-fast, the average sits at --pace-mid.
  function paceColor(el, k) {
    el.style.setProperty("--k1", Math.min(1, 2 * k).toFixed(3));
    el.style.setProperty("--k2", Math.max(0, 2 * k - 1).toFixed(3));
  }

  function renderStrip(a, t) {
    const splits = t.splits;
    const total = splits.reduce((s, x) => s + x.d, 0) || 1;
    const { v, k, min, max } = speeds(a, splits);
    strip.setAttribute("viewBox", `0 0 ${total} 10`);
    strip.replaceChildren();
    const defs = document.createElementNS(SVG_NS, "defs");
    const pattern = document.createElementNS(SVG_NS, "pattern");
    pattern.id = "gps-hatch";
    pattern.setAttribute("patternUnits", "userSpaceOnUse");
    pattern.setAttribute("width", String(total / 60));
    pattern.setAttribute("height", "10");
    const bg = document.createElementNS(SVG_NS, "rect");
    bg.setAttribute("class", "hatch-bg");
    bg.setAttribute("width", String(total / 60));
    bg.setAttribute("height", "10");
    const hatch = document.createElementNS(SVG_NS, "line");
    hatch.setAttribute("class", "hatch-line");
    hatch.setAttribute("x1", "0");
    hatch.setAttribute("y1", "10");
    hatch.setAttribute("x2", String(total / 60));
    hatch.setAttribute("y2", "0");
    hatch.setAttribute("vector-effect", "non-scaling-stroke");
    pattern.append(bg, hatch);
    defs.append(pattern);
    strip.append(defs);
    const gap = total * 0.004;
    let x = 0;
    splits.forEach((s, i) => {
      const r = document.createElementNS(SVG_NS, "rect");
      r.setAttribute("x", x.toFixed(1));
      r.setAttribute("y", "0");
      r.setAttribute("width", Math.max(0, s.d - (i < splits.length - 1 ? gap : 0)).toFixed(1));
      r.setAttribute("height", "10");
      r.style.setProperty("--i", String(i));
      if (s.flag) r.classList.add("is-flag");
      else if (v[i] === null) r.classList.add("is-blank");
      else paceColor(r, k[i]);
      x += s.d;
      strip.append(r);
    });
    const legend = $("pace-legend");
    if (Number.isFinite(min) && Number.isFinite(max)) {
      const slow = f.paceOnly(1000, 1000 / min, units, a.sport);
      const fast = f.paceOnly(1000, 1000 / max, units, a.sport);
      const ramp = document.createElement("span");
      ramp.className = "legend-ramp";
      legend.replaceChildren(document.createTextNode(slow), ramp, document.createTextNode(fast));
    } else {
      legend.textContent = "No times recorded";
    }
  }

  // ---------- the elevation ----------

  let eleScale = null;

  function renderElevation(t) {
    const e = t.e;
    const d = t.d;
    const W = 1000;
    const H = 100;
    ele.setAttribute("viewBox", `0 0 ${W} ${H}`);
    if (!e || e.every((v) => v === null)) {
      eleArea.setAttribute("d", "");
      eleLine.setAttribute("d", "");
      readout.textContent = "No elevation recorded";
      eleScale = null;
      return;
    }
    const vals = e.map((v, i) => (v === null ? e.slice(0, i).reverse().find((x) => x !== null) ?? 0 : v));
    let lo = Math.min(...vals);
    let hi = Math.max(...vals);
    if (hi - lo < 30) {
      const mid = (hi + lo) / 2;
      lo = mid - 15;
      hi = mid + 15;
    }
    const D = d[d.length - 1] || 1;
    const sx = (m) => (m / D) * W;
    const sy = (v) => H - 6 - ((v - lo) / (hi - lo)) * (H - 14);
    const step = Math.max(1, Math.floor(vals.length / 600));
    let path = "";
    for (let i = 0; i < vals.length; i += step) path += `${i ? "L" : "M"}${sx(d[i]).toFixed(1)} ${sy(vals[i]).toFixed(1)}`;
    path += `L${W} ${sy(vals[vals.length - 1]).toFixed(1)}`;
    eleLine.setAttribute("d", path);
    eleArea.setAttribute("d", `${path}L${W} ${H}L0 ${H}Z`);
    eleScale = { D, lo, hi, vals };
    const top = f.climb(hi, units);
    const bottom = f.climb(lo, units);
    readout.textContent = `${bottom.value} to ${top.value} ${top.unit}`;
    restingReadout = readout.textContent;
  }

  let restingReadout = "";

  function scrubTo(clientX) {
    if (!track || !eleScale) return;
    const r = ele.getBoundingClientRect();
    const u = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    const target = u * eleScale.D;
    const d = track.d;
    let lo = 0;
    let hi = d.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (d[mid] < target) lo = mid + 1;
      else hi = mid;
    }
    const i = lo;
    cursor.setAttribute("x1", String(u * 1000));
    cursor.setAttribute("x2", String(u * 1000));
    cursor.classList.add("is-on");
    scrub.setAttribute("cx", String(track.x[i]));
    scrub.setAttribute("cy", String(track.y[i]));
    scrub.classList.add("is-on");
    const c = f.climb(eleScale.vals[i], units);
    const v = track.v ? track.v[i] : null;
    const p = v ? f.pace(1000, 1000 / v, units, current.sport) : null;
    readout.textContent = `${f.distance(d[i], units, 1)} ${units}, ${c.value} ${c.unit}${p ? `, ${p.value} ${p.unit}` : ""}`;
  }

  function endScrub() {
    cursor.classList.remove("is-on");
    scrub.classList.remove("is-on");
    readout.textContent = restingReadout;
  }

  ele.addEventListener("pointerdown", (event) => {
    ele.setPointerCapture(event.pointerId);
    scrubTo(event.clientX);
  });
  ele.addEventListener("pointermove", (event) => {
    if (event.pointerType === "mouse" || ele.hasPointerCapture(event.pointerId)) scrubTo(event.clientX);
  });
  ele.addEventListener("pointerup", (event) => {
    if (event.pointerType !== "mouse") endScrub();
  });
  ele.addEventListener("pointercancel", endScrub);
  ele.addEventListener("pointerleave", (event) => {
    if (event.pointerType === "mouse") endScrub();
  });

  // ---------- the splits ----------

  function renderSplits(a, t) {
    const table = $("splits");
    const splits = t.splits;
    const { v, k, max } = speeds(a, splits);
    const ride = a.sport === "ride";
    const head = document.createElement("thead");
    head.innerHTML = `<tr><th scope="col">${units === "km" ? "Km" : "Mile"}</th><th scope="col">${ride ? "Speed" : "Pace"}</th><th scope="col" class="split-bar"><span class="visually-hidden"></span></th><th scope="col">Climb</th></tr>`;
    const body = document.createElement("tbody");
    const unitM = f.UNIT_M[units];
    let at = 0;
    splits.forEach((s, i) => {
      at += s.d;
      const tr = document.createElement("tr");
      if (s.flag) tr.classList.add("is-flag");
      const label = s.d < unitM * 0.995 ? (at / unitM).toFixed(2) : String(Math.round(at / unitM));
      const cells = [label, s.t ? f.paceOnly(s.d, s.t, units, a.sport) : "", "", ""];
      cells.forEach((text, c) => {
        const td = document.createElement("td");
        td.textContent = text;
        if (c === 1 && s.flag) {
          const note = document.createElement("span");
          note.className = "flag-note";
          note.textContent = "GPS jump";
          td.append(note);
        }
        if (c === 2) {
          td.className = "split-bar";
          const bar = document.createElement("span");
          if (v[i] !== null && max > 0) bar.style.setProperty("--w", Math.min(1, v[i] / max).toFixed(3));
          else bar.style.setProperty("--w", "0");
          paceColor(bar, k[i] ?? 0.5);
          td.append(bar);
        }
        if (c === 3) {
          const up = f.climb(s.up, units);
          const down = f.climb(s.down, units);
          td.textContent = `+${up.value} −${down.value}`;
        }
        tr.append(td);
      });
      body.append(tr);
    });
    table.replaceChildren(head, body);
    if (!t.t) {
      const foot = document.createElement("caption");
      foot.className = "splits-empty";
      foot.textContent = "This file has no times, so pace is blank.";
      table.prepend(foot);
    }
  }

  // ---------- open, fly, close ----------

  function flyFrom(fromSvg, a) {
    const first = fromSvg.getBoundingClientRect();
    const last = box.getBoundingClientRect();
    if (!first.width || !last.width) return Promise.resolve();
    const flyer = document.createElement("div");
    flyer.className = "flyer route-box";
    flyer.style.setProperty("--len", box.style.getPropertyValue("--len"));
    const clone = fromSvg.cloneNode(true);
    clone.setAttribute("class", "route");
    clone.setAttribute("viewBox", `-70 -70 ${VIEW} ${VIEW}`);
    const poly = clone.querySelector("polyline");
    poly.removeAttribute("pathLength");
    poly.setAttribute("class", "route-ghost flyer-line");
    clone.append();
    flyer.append(clone);
    document.body.append(flyer);
    flyer.style.setProperty("--fx", `${last.left}px`);
    flyer.style.setProperty("--fy", `${last.top}px`);
    flyer.style.setProperty("--fw", `${last.width}px`);
    const s = first.width / last.width;
    const tileSw = (1.5 * VIEW) / first.width;
    const boxSw = (1.5 * VIEW) / last.width;
    box.classList.add("is-hidden");
    const moving = flyer.animate(
      [
        { transform: `translate(${first.left - last.left}px, ${first.top - last.top}px) scale(${s})`, borderRadius: `${8 / s}px` },
        { transform: "none", borderRadius: "16px" },
      ],
      { duration: FLY_MS, easing: "cubic-bezier(0.23, 1, 0.32, 1)" },
    );
    poly.animate([{ strokeWidth: `${tileSw}px` }, { strokeWidth: `${boxSw}px` }], { duration: FLY_MS, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "forwards" });
    flight = moving;
    return moving.finished
      .catch(() => {})
      .then(() => {
        flyer.remove();
        box.classList.remove("is-hidden");
        if (flight === moving) flight = null;
      });
  }

  function show(a, { from = null, newer = false, older = false } = {}) {
    const mine = ++token;
    current = a;
    track = null;
    geometry = null;
    if (flight) flight.cancel();
    clearRoute();
    endScrub();
    $("prev").disabled = !newer;
    $("next").disabled = !older;
    renderFacts(a);
    setGhost(a);
    $("splits").replaceChildren();
    strip.replaceChildren();
    eleArea.setAttribute("d", "");
    eleLine.setAttribute("d", "");
    readout.textContent = "";
    const wasOpen = open;
    if (!wide.matches) {
      if (!open) lastFocus = document.activeElement;
      root.classList.add("is-open");
      root.setAttribute("aria-hidden", "false");
      root.setAttribute("role", "dialog");
      root.setAttribute("aria-modal", "true");
      document.body.classList.add("is-locked");
      if (!wasOpen) scroller.scrollTop = 0;
    } else {
      scroller.scrollTo({ top: 0 });
    }
    open = true;
    const loading = load(a);
    const flying = from && !reduced.matches && (wide.matches || !wasOpen) ? flyFrom(from, a) : Promise.resolve();
    if (!wide.matches && !wasOpen) $("close").focus({ preventScroll: true });
    loading.then((t) => {
      if (mine !== token || !t) return;
      track = t;
      geometry = buildGeometry(t);
      renderStrip(a, t);
      renderElevation(t);
      renderSplits(a, t);
      flying.then(() => {
        if (mine === token) draw();
      });
    });
  }

  function hide(toSvg) {
    if (!open || wide.matches) return;
    open = false;
    token += 1;
    clearRoute();
    root.classList.remove("is-open");
    root.setAttribute("aria-hidden", "true");
    root.removeAttribute("aria-modal");
    document.body.classList.remove("is-locked");
    if (lastFocus && lastFocus.isConnected && !toSvg) lastFocus.focus({ preventScroll: true });
  }

  function dock() {
    root.classList.remove("is-open");
    root.setAttribute("aria-hidden", "false");
    root.removeAttribute("role");
    root.removeAttribute("aria-modal");
    document.body.classList.remove("is-locked");
    open = Boolean(current);
  }

  function undock() {
    open = false;
    root.setAttribute("aria-hidden", "true");
  }

  return {
    show,
    hide,
    dock,
    undock,
    isOpen: () => open,
    prefetch: (a) => a && load(a),
  };
}
