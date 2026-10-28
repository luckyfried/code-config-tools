// The authors river: a streamgraph of commits per author per month, the top eight in their own colors and everyone
// else as one neutral band, Catmull-Rom smoothed, drawn in with a left-to-right sweep. A phone gets stacked bars.
import {
  DATA, svg, el, catmullRom, authorColor, shortName, monthShort, monthLong, fmt, plural, isPhone, calm,
  tween, ease, showTip, hideTip, escapeHtml, monoWidth,
} from "./util.js";

let uid = 0;

/** Layers in drawing order, bottom to top: the biggest in the middle, the neutral band on the outside. */
function layers() {
  const top = DATA.river.map((values, k) => ({
    key: k,
    name: DATA.authors[k].n,
    label: shortName(DATA.authors[k].n),
    color: authorColor(k),
    values,
    total: values.reduce((a, b) => a + b, 0),
  }));
  const sorted = [...top].sort((a, b) => b.total - a.total);
  const inside = [];
  sorted.forEach((layer, k) => (k % 2 === 0 ? inside.push(layer) : inside.unshift(layer)));
  const rest = { key: "rest", name: "Everyone else", label: "Everyone else", color: "var(--cat-rest)", values: DATA.rest, total: DATA.rest.reduce((a, b) => a + b, 0), rest: true };
  return rest.total > 0 ? [rest, ...inside] : inside;
}

export function createRiver(container, { tall = false, onFocus } = {}) {
  const months = DATA.months;
  const stack = layers();
  const totals = months.map((_, i) => stack.reduce((sum, layer) => sum + layer.values[i], 0));
  const id = `river-${(uid += 1)}`;
  let played = false;
  let progress = calm() ? 1 : 0;
  let live = null;
  let sweepTo = null;
  let highlighted = null;

  const svgNode = svg("svg", { role: "img" }, "river-svg");
  svgNode.dataset.total = totals.reduce((a, b) => a + b, 0);
  svgNode.setAttribute("aria-label", `Commits per author per month, ${fmt(DATA.commits)} in all`);
  const legend = el("ul", "river-legend");
  const plot = el("div", "river-plot");
  plot.append(svgNode);
  container.replaceChildren(legend, plot);

  for (const layer of [...stack].reverse()) {
    const item = el("li", `legend-item${layer.rest ? " is-rest" : ""}`);
    item.dataset.key = layer.key;
    const dot = el("span", "legend-dot");
    dot.style.setProperty("--c", layer.color);
    item.append(dot, el("span", "legend-name", layer.label), el("span", "legend-count", fmt(layer.total)));
    item.addEventListener("pointerenter", () => highlight(layer.key));
    item.addEventListener("pointerleave", () => highlight(null));
    legend.append(item);
  }

  function highlight(key) {
    highlighted = key;
    svgNode.classList.toggle("is-focusing", key !== null);
    for (const node of svgNode.querySelectorAll("[data-key]")) node.classList.toggle("is-on", String(node.dataset.key) === String(key));
    for (const node of legend.children) node.classList.toggle("is-on", String(node.dataset.key) === String(key));
    onFocus?.(key);
  }

  function drawStream(full, h, gutter = 0) {
    // A gutter on the right holds the names of wide bands too thin to carry their own.
    const w = full - gutter;
    const padTop = 10;
    const axis = 26;
    const plotH = h - padTop - axis;
    const max = Math.max(...totals, 1);
    const scale = (plotH * 0.94) / max;
    const mid = padTop + plotH / 2;
    const step = w / months.length;
    const xs = months.map((_, i) => (i + 0.5) * step);
    const xsAll = [0, ...xs, w];
    const pad = (arr) => [arr[0], ...arr, arr[arr.length - 1]];
    const base = pad(totals.map((t) => mid - (t * scale) / 2));

    const defs = svg("defs");
    const clip = svg("clipPath", { id: `${id}-clip` });
    const clipRect = svg("rect", { x: 0, y: 0, width: (progress * full).toFixed(1), height: h });
    clip.append(clipRect);
    defs.append(clip);

    const gGrid = svg("g", {}, "river-grid");
    months.forEach((key, i) => {
      gGrid.append(svg("line", { x1: xs[i], x2: xs[i], y1: padTop, y2: padTop + plotH }, "grid-line"));
      const label = i === 0 || key.endsWith("-01") ? `${monthShort(key)}${key.endsWith("-01") ? ` ${key.slice(0, 4)}` : ""}` : monthShort(key);
      if (step < monoWidth(label, 11) + 6 && label.length > 3) {
        const t = svg("text", { x: xs[i], y: h - 8 }, "axis-label");
        t.textContent = monthShort(key);
        gGrid.append(t);
      } else {
        const t = svg("text", { x: xs[i], y: h - 8 }, "axis-label");
        t.textContent = label;
        gGrid.append(t);
      }
    });

    const gLayers = svg("g", { "clip-path": `url(#${id}-clip)` }, "river-layers");
    const bounds = [];
    let lower = base.slice();
    for (const layer of stack) {
      const vals = pad(layer.values);
      const upper = lower.map((y, i) => y + vals[i] * scale);
      const top = xsAll.map((x, i) => [x, upper[i]]);
      const bottom = xsAll.map((x, i) => [x, lower[i]]).reverse();
      const d = `${catmullRom(top)}${catmullRom(bottom, false)}Z`;
      const path = svg("path", { d, "data-key": layer.key }, `river-layer${layer.rest ? " is-rest" : ""}`);
      path.style.setProperty("--c", layer.color);
      gLayers.append(path);
      bounds.push({ layer, lower: lower.slice(1, -1), upper: upper.slice(1, -1) });
      lower = upper;
    }

    // Names inside the streams, the widest first, where a stream is thick enough to hold one; a name steps down a
    // size before it gives up.
    const gNames = svg("g", { "clip-path": `url(#${id}-clip)` }, "river-names");
    const placed = [];
    const nameSize = tall ? 13 : 12;
    // The band's edges at any x, read between the month points.
    const at = (arr, px) => {
      const f = Math.max(0, Math.min(months.length - 1, px / step - 0.5));
      const i0 = Math.floor(f);
      const i1 = Math.min(months.length - 1, i0 + 1);
      return arr[i0] + (arr[i1] - arr[i0]) * (f - i0);
    };
    const named = new Set();
    const spots = [];
    for (let x = step / 2; x <= w - step / 2 + 0.1; x += step / 4) spots.push(x);
    for (const { layer, lower: lo, upper: up } of [...bounds].sort((a, b) => b.layer.total - a.layer.total)) {
      const text = layer.label;
      let box = null;
      let x = 0;
      let y = 0;
      let size = nameSize;
      for (const fs of [nameSize, nameSize - 1.5]) {
        const tw = text.length * fs * 0.56 + 8;
        const half = fs / 2 + 1.5;
        const thick = (px) => at(up, px) - at(lo, px);
        // The thickest spots first; the first where the whole name sits inside the band wins.
        const order = spots.filter((px) => thick(px) >= fs + 3).sort((a, b) => thick(b) - thick(a));
        for (const sx of order) {
          const cx = Math.min(Math.max(sx, tw / 2 + 4), w - tw / 2 - 4);
          const cy = (at(lo, cx) + at(up, cx)) / 2;
          const holds = [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1].every((f) => {
            const px = cx - tw / 2 + f * tw;
            return at(lo, px) <= cy - half && at(up, px) >= cy + half;
          });
          if (!holds) continue;
          const b = [cx - tw / 2, cy - half, cx + tw / 2, cy + half];
          if (placed.some((p) => !(b[2] < p[0] || b[0] > p[2] || b[3] < p[1] || b[1] > p[3]))) continue;
          box = b;
          x = cx;
          y = cy;
          size = fs;
          break;
        }
        if (box) break;
      }
      if (!box) continue;
      named.add(layer.key);
      placed.push(box);
      const t = svg("text", { x: x.toFixed(1), y: (y + size * 0.36).toFixed(1), "data-key": layer.key }, `river-name${layer.rest ? " is-rest" : ""}`);
      t.style.setProperty("--fs", `${size}px`);
      t.textContent = text;
      gNames.append(t);
    }

    const widest = bounds.filter((b) => !b.layer.rest).sort((a, b) => b.layer.total - a.layer.total).slice(0, 3);
    const unnamed = widest.filter((b) => !named.has(b.layer.key));
    if (unnamed.length && !gutter && !tall) {
      drawStream(full, h, Math.ceil(Math.max(...widest.map((b) => monoWidth(b.layer.label, 12))) + 18));
      return;
    }
    if (gutter) {
      const ends = unnamed
        .map((b) => ({ layer: b.layer, band: (b.lower[months.length - 1] + b.upper[months.length - 1]) / 2 }))
        .sort((a, b) => a.band - b.band);
      ends.forEach((e, k) => {
        e.y = Math.max(e.band, k ? ends[k - 1].y + 15 : padTop + 6);
      });
      for (let k = ends.length - 1; k >= 0; k -= 1) ends[k].y = Math.min(ends[k].y, k < ends.length - 1 ? ends[k + 1].y - 15 : padTop + plotH - 6);
      for (const e of ends) {
        const g = svg("g", { "data-key": e.layer.key }, "river-end");
        g.style.setProperty("--c", e.layer.color);
        g.append(svg("path", { d: `M${(w + 1).toFixed(1)},${e.band.toFixed(1)} L${(w + 5).toFixed(1)},${e.y.toFixed(1)} L${(w + 9).toFixed(1)},${e.y.toFixed(1)}` }, "river-end-line"));
        const t = svg("text", { x: (w + 12).toFixed(1), y: (e.y + 4).toFixed(1) }, "river-end-name");
        t.textContent = e.layer.label;
        g.append(t);
        gNames.append(g);
      }
    }

    const edge = svg("line", { x1: 0, x2: 0, y1: padTop, y2: padTop + plotH }, "river-edge");
    const hover = svg("line", { x1: 0, x2: 0, y1: padTop, y2: padTop + plotH }, "river-hover");
    svgNode.replaceChildren(defs, gGrid, gLayers, gNames, edge, hover);

    live = { clipRect, edge, w: full };
    if (progress >= 1) edge.classList.add("is-done");
    // The sweep reads whatever drawing is current, so a redraw mid-sweep carries on from where it was.
    sweepTo = () =>
      tween({
        duration: 1350,
        delay: 120,
        easing: ease.inOut,
        update: (t) => {
          progress = t;
          const x = (t * live.w).toFixed(1);
          live.clipRect.setAttribute("width", x);
          live.edge.setAttribute("x1", x);
          live.edge.setAttribute("x2", x);
          live.edge.style.setProperty("--o", t < 1 ? Math.min(1, t * 6, (1 - t) * 6) : 0);
        },
      }).then(() => live.edge.classList.add("is-done"));

    svgNode.onpointermove = (event) => {
      const r = svgNode.getBoundingClientRect();
      const x = event.clientX - r.left;
      const y = event.clientY - r.top;
      const i = Math.max(0, Math.min(months.length - 1, Math.floor(x / step)));
      hover.setAttribute("x1", xs[i]);
      hover.setAttribute("x2", xs[i]);
      hover.classList.add("is-on");
      const hit = bounds.find((b) => y >= b.lower[i] - 1 && y <= b.upper[i] + 1 && b.layer.values[i] > 0);
      if (!hit) {
        showTip(`<strong>${monthLong(months[i])}</strong><span>${plural(totals[i], "commit")}</span>`, event.clientX, event.clientY);
        if (highlighted !== null) highlight(null);
        return;
      }
      if (highlighted !== hit.layer.key) highlight(hit.layer.key);
      const share = totals[i] ? Math.round((hit.layer.values[i] / totals[i]) * 100) : 0;
      showTip(
        `<strong>${escapeHtml(hit.layer.name)}</strong><span>${monthLong(months[i])}</span><span>${plural(hit.layer.values[i], "commit")}, ${share}% of the month</span>`,
        event.clientX,
        event.clientY,
      );
    };
    svgNode.onpointerleave = () => {
      hover.classList.remove("is-on");
      hideTip();
      highlight(null);
    };
  }

  function drawBars(w, h) {
    const axis = 22;
    const plotH = h - axis - 6;
    const max = Math.max(...totals, 1);
    const step = w / months.length;
    const bw = Math.max(6, step * 0.62);
    const gBars = svg("g", {}, "river-bars");
    const gAxis = svg("g", {}, "river-grid");
    months.forEach((key, i) => {
      const g = svg("g", { "data-month": key }, "bar-stack");
      g.style.setProperty("--d", `${i * 45}ms`);
      let y = 6 + plotH;
      for (const layer of stack) {
        const v = layer.values[i];
        if (!v) continue;
        const bh = (v / max) * plotH;
        y -= bh;
        const rect = svg("rect", { x: (i * step + (step - bw) / 2).toFixed(1), y: y.toFixed(1), width: bw.toFixed(1), height: Math.max(0.5, bh - 1).toFixed(1), "data-key": layer.key }, `bar-seg${layer.rest ? " is-rest" : ""}`);
        rect.style.setProperty("--c", layer.color);
        g.append(rect);
      }
      gBars.append(g);
      const t = svg("text", { x: (i * step + step / 2).toFixed(1), y: h - 5 }, "axis-label");
      t.textContent = step >= 24 ? monthShort(key) : monthShort(key)[0];
      gAxis.append(t);
    });
    svgNode.replaceChildren(gAxis, gBars);
    svgNode.onpointermove = null;
    svgNode.onpointerleave = null;
    svgNode.onclick = (event) => {
      const r = svgNode.getBoundingClientRect();
      const i = Math.max(0, Math.min(months.length - 1, Math.floor((event.clientX - r.left) / step)));
      const lines = stack.filter((l) => l.values[i]).sort((a, b) => b.values[i] - a.values[i]).slice(0, 4)
        .map((l) => `<span>${escapeHtml(l.label)}: ${fmt(l.values[i])}</span>`).join("");
      showTip(`<strong>${monthLong(months[i])}, ${plural(totals[i], "commit")}</strong>${lines}`, event.clientX, event.clientY);
      window.setTimeout(hideTip, 2600);
    };
  }

  function render(w, h) {
    if (w < 40 || h < 40) return;
    svgNode.setAttribute("width", Math.round(w));
    svgNode.setAttribute("height", Math.round(h));
    svgNode.setAttribute("viewBox", `0 0 ${Math.round(w)} ${Math.round(h)}`);
    svgNode.classList.toggle("is-bars", isPhone());
    if (isPhone()) drawBars(w, h);
    else drawStream(w, h);
  }

  return {
    render,
    play() {
      if (played) return;
      played = true;
      if (calm() || isPhone()) {
        svgNode.classList.add("is-growing");
        progress = 1;
        if (live) {
          live.clipRect.setAttribute("width", live.w);
          live.edge.classList.add("is-done");
        }
        return;
      }
      const go = () => (live ? sweepTo() : requestAnimationFrame(go));
      go();
    },
    highlight,
    legend,
    plot,
    svg: svgNode,
    stack,
  };
}
