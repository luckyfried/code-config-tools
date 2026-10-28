// The commit heat map: one cell per day in the window, a five-step ramp from the theme, the busiest day called
// out, and the release strip drawn on the same time axis underneath.
import { DATA, dayDate, weekday, svg, el, setVars, monoWidth, fmt, plural, isPhone, calm, clamp, monthShort, monthLong, monthDate, shortDay, START_MS } from "./util.js";

// The busiest-day pill has a lane of its own over the month names, so it never covers one.
const CALL_H = 24;
const MONTH_H = 22;
const CELLS_TOP = CALL_H + MONTH_H;
const TAG_GAP = 12;
const TAG_ROW0 = 21;
const TAG_ROW = 15;
const TAG_PAD = 5;
const TAG_SIZE = 11;
const DAY_COL = 34;

export function levelsFor(days) {
  const nonzero = days.filter((c) => c > 0).sort((a, b) => a - b);
  const q = (p) => nonzero[Math.min(nonzero.length - 1, Math.floor(p * nonzero.length))] || 1;
  const cuts = [];
  for (const p of [0.2, 0.45, 0.7, 0.9]) {
    const v = q(p);
    cuts.push(Math.max(v, (cuts[cuts.length - 1] || 0) + 1));
  }
  const level = (c) => {
    if (c <= 0) return 0;
    let k = 1;
    for (const cut of cuts) if (c > cut) k += 1;
    return Math.min(k, 5);
  };
  const ranges = [];
  let lo = 1;
  cuts.forEach((cut) => {
    ranges.push([lo, cut]);
    lo = cut + 1;
  });
  ranges.push([lo, null]);
  return { level, ranges };
}

export function createHeatmap(panel, { onHover, onLeave, onPick }) {
  const days = DATA.days;
  const n = days.length;
  const first = weekday(dayDate(0));
  const cols = Math.floor((first + n - 1) / 7) + 1;
  const colOf = (i) => Math.floor((first + i) / 7);
  const rowOf = (i) => (first + i) % 7;
  const { level, ranges } = levelsFor(days);
  const tagDays = new Map(DATA.tags.map(([name, day]) => [day, name]));
  const major = (name) => /^v?\d+\.\d+\.0$/.test(name);

  // Release names, each starting at its tick (or ending there, at the right edge). Placed right to left, each takes
  // the first row where it touches no other name and its leader crosses none above it, and no name crosses a leader.
  function tagLabels(width, pitch = px) {
    const placed = [];
    const ticks = DATA.tags.map(([name, day]) => ({ name, day, x: colOf(day) * pitch + ((rowOf(day) + 0.5) / 7) * pitch }));
    const fits = (t, x0, x1, row) =>
      placed.every((p) => {
        if (p.row === row && !(x1 + 10 < p.x0 || x0 - 10 > p.x1)) return false;
        if (p.row < row && t.x > p.x0 - 4 && t.x < p.x1 + 4) return false;
        if (p.row > row && p.x > x0 - 4 && p.x < x1 + 4) return false;
        return true;
      });
    const rowFor = (t, x0, x1) => {
      for (let row = 0; row < 6; row += 1) if (fits(t, x0, x1, row)) return row;
      return 6;
    };
    for (const t of [...ticks].sort((a, b) => b.x - a.x)) {
      const w = monoWidth(t.name, TAG_SIZE) + TAG_PAD;
      // A name hangs right of its tick; it hangs left where that keeps it higher and covers no other tick.
      const right = t.x + w + 6 <= width ? { x0: t.x - 1, x1: t.x + w, flip: false } : null;
      // A phone scrolls the strip, so its names all hang one way and none waits beyond the edge of the window.
      const left = (!isPhone() || !right) && t.x - w >= 0 && !ticks.some((o) => o !== t && o.x < t.x && o.x > t.x - w - 14) ? { x0: t.x - w, x1: t.x + 1, flip: true } : null;
      const options = [right, left].filter(Boolean).map((o) => ({ ...o, row: rowFor(t, o.x0, o.x1) }));
      if (!options.length) options.push({ x0: t.x - w, x1: t.x + 1, flip: true, row: rowFor(t, t.x - w, t.x + 1) });
      const best = options.reduce((a, b) => (b.row < a.row ? b : a));
      Object.assign(t, best);
      placed.push(t);
    }
    return ticks;
  }
  const tagRows = (width, pitch) => Math.max(1, ...tagLabels(width, pitch).map((t) => t.row + 1));
  const tagLane = (rows) => 9 + TAG_ROW0 + (rows - 1) * TAG_ROW + 6;

  const host = panel.querySelector(".heat");
  host.replaceChildren();
  const daysSvg = svg("svg", { "aria-hidden": "true" }, "heat-days");
  const scroller = el("div", "heat-scroll");
  scroller.tabIndex = 0;
  scroller.setAttribute("role", "group");
  scroller.setAttribute(
    "aria-label",
    `Commits per day, ${fmt(n)} days. Arrow keys move between days; the card below names each day's commits.`,
  );
  const inner = el("div", "heat-inner");
  const map = svg("svg", { role: "img", "aria-label": `Heat map of ${fmt(DATA.commits)} commits` }, "heat-svg");
  const callout = el("div", "callout");
  callout.setAttribute("aria-hidden", "true");
  const snaps = el("div", "heat-snaps");
  snaps.setAttribute("aria-hidden", "true");
  inner.append(map, callout, snaps);
  scroller.append(inner);
  host.append(daysSvg, scroller);

  // Where the map scrolls, a bar over it holds the whole window: every month in its ramp step, the weeks in view
  // framed, and a step either way.
  const range = el("div", "heat-range");
  range.hidden = true;
  const chevron = (d) => {
    const icon = svg("svg", { viewBox: "0 0 24 24", "aria-hidden": "true" }, "icon");
    icon.append(svg("path", { d }));
    return icon;
  };
  const back = el("button", "range-step");
  back.type = "button";
  back.setAttribute("aria-label", "Earlier weeks");
  back.append(chevron("M14.5 6l-6 6 6 6"));
  const next = el("button", "range-step");
  next.type = "button";
  next.setAttribute("aria-label", "Later weeks");
  next.append(chevron("M9.5 6l6 6-6 6"));
  const track = el("div", "range-track");
  const view = el("span", "range-view");
  view.setAttribute("aria-hidden", "true");
  const monthTotals = DATA.months.map((_, i) => DATA.river.reduce((sum, r) => sum + r[i], 0) + DATA.rest[i]);
  const monthMax = Math.max(1, ...monthTotals);
  const monthSpans = DATA.months.map((key, k) => {
    const from = clamp(Math.round((monthDate(key).getTime() - START_MS) / 86400000), 0, n - 1);
    const d = monthDate(key);
    const to = clamp(Math.round((Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1) - START_MS) / 86400000) - 1, 0, n - 1);
    const button = el("button", `range-month lv${1 + Math.min(4, Math.floor((monthTotals[k] / monthMax) * 4.999))}`);
    button.type = "button";
    button.setAttribute("aria-label", `${monthLong(key)}, ${plural(monthTotals[k], "commit")}`);
    button.append(el("span", "range-cell"), el("span", "range-letter", monthShort(key)[0]));
    const c0 = colOf(from);
    const c1 = colOf(to) + 1;
    setVars(button, { "--l": `${((c0 / cols) * 100).toFixed(3)}%`, "--w": `${(((c1 - c0) / cols) * 100).toFixed(3)}%` });
    button.addEventListener("click", () => glideToCol(c0));
    track.append(button);
    return { c0, c1 };
  });
  track.append(view);
  range.append(back, track, next);
  host.before(range);
  back.addEventListener("click", () => glideToCol(Math.round(scroller.scrollLeft / px) - (shownCols() - 1)));
  next.addEventListener("click", () => glideToCol(Math.round(scroller.scrollLeft / px) + (shownCols() - 1)));

  function syncRange() {
    if (range.hidden) return;
    const total = cols * px;
    const a = scroller.scrollLeft / total;
    const b = (scroller.scrollLeft + scroller.clientWidth) / total;
    setVars(view, { "--l": `${(a * 100).toFixed(2)}%`, "--w": `${((b - a) * 100).toFixed(2)}%` });
    back.disabled = scroller.scrollLeft < 1;
    next.disabled = scroller.scrollLeft + scroller.clientWidth > total - 1;
    const c0 = scroller.scrollLeft / px;
    const c1 = c0 + scroller.clientWidth / px;
    track.querySelectorAll(".range-month").forEach((m, k) => m.classList.toggle("is-in", Math.min(monthSpans[k].c1, c1) - Math.max(monthSpans[k].c0, c0) >= 1.5));
  }

  let px = 16;
  let py = 16;
  let cells = [];
  let cursor = null;
  let active = -1;
  let introDone = false;
  let edgeLabels = [];

  // Where the map scrolls, a label the window would cut in two waits out of sight until it is whole.
  function trimEdges() {
    const a = scroller.scrollLeft - 0.5;
    const b = scroller.scrollLeft + scroller.clientWidth + 0.5;
    for (const l of edgeLabels) l.node.classList.toggle("is-cut", l.x0 < a || l.x1 > b);
  }
  let trimQueued = false;
  scroller.addEventListener("scroll", () => {
    if (trimQueued) return;
    trimQueued = true;
    requestAnimationFrame(() => {
      trimQueued = false;
      trimEdges();
      syncRange();
    });
  }, { passive: true });

  function geometry(width, height) {
    if (isPhone()) {
      px = py = 16;
      return;
    }
    const avail = width - DAY_COL;
    px = clamp(avail / cols, 13, 46);
    const budget = height ? (height - CELLS_TOP - TAG_GAP - tagLane(tagRows(cols * px, px))) / 7 : px;
    // Cells stay close to square: the screen gives up a little of the lower row before a cell turns into a brick.
    py = clamp(Math.max(Math.min(px, budget), px / 1.15), 13, px);
  }

  function draw() {
    const cellsTop = CELLS_TOP;
    const cellsH = py * 7;
    const tagTop = cellsTop + cellsH + TAG_GAP;
    const width = Math.ceil(cols * px);
    const height = Math.ceil(tagTop + tagLane(tagRows(width, px)));
    const gap = Math.max(2, Math.min(px, py) * 0.16);
    const cw = px - gap;
    const ch = py - gap;
    const r = Math.min(cw, ch) * 0.24;

    map.replaceChildren();
    map.setAttribute("width", width);
    map.setAttribute("height", height);
    map.setAttribute("viewBox", `0 0 ${width} ${height}`);
    map.dataset.days = n;
    setVars(inner, { "--w": `${width}px`, "--h": `${height}px`, "--px": `${px}px` });

    // The visible run starts the ripple, so a phone scrolled to the busiest day still sees it from its left edge.
    const visibleFrom = isPhone() ? openingCol() : 0;

    const gCells = svg("g", {}, "cells");
    cells = new Array(n);
    for (let i = 0; i < n; i += 1) {
      const c = colOf(i);
      const rr = rowOf(i);
      const rect = svg("rect", {
        x: (c * px + gap / 2).toFixed(2),
        y: (cellsTop + rr * py + gap / 2).toFixed(2),
        width: cw.toFixed(2),
        height: ch.toFixed(2),
        rx: r.toFixed(2),
      }, `cell lv${level(days[i])}${tagDays.has(i) ? " is-release" : ""}`);
      rect.style.setProperty("--d", `${Math.max(0, c - visibleFrom) * 13 + rr * 24}ms`);
      gCells.append(rect);
      cells[i] = rect;
    }

    // Month names over the first column that holds the 1st.
    const gMonths = svg("g", {}, "months");
    const monthMarks = [];
    for (let i = 0; i < n; i += 1) {
      const d = dayDate(i);
      if (d.getUTCDate() !== 1 && i !== 0) continue;
      const c = i === 0 && d.getUTCDate() > 7 ? colOf(i) + 1 : colOf(i) + (rowOf(i) > 0 && i !== 0 ? 1 : 0);
      if (c >= cols) continue;
      const key = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      const short = monthShort(key);
      const label = d.getUTCMonth() === 0 ? `${short} ${d.getUTCFullYear()}` : short;
      monthMarks.push({ x: c * px + gap / 2, label, short });
    }
    // A January carries its year where there is room, and drops it before it would crowd February.
    const placedMonths = [];
    edgeLabels = [];
    monthMarks.forEach((m, k) => {
      const next = monthMarks[k + 1];
      const room = next ? next.x - m.x - 6 : width - m.x;
      const label = [m.label, m.short].find((text) => monoWidth(text, 11) <= room);
      if (!label) return;
      const w = monoWidth(label, 11);
      const t = svg("text", { x: m.x.toFixed(1), y: CALL_H + 14 }, "month");
      t.textContent = label;
      gMonths.append(t);
      placedMonths.push({ node: t, x0: m.x, x1: m.x + w });
      edgeLabels.push({ node: t, x0: m.x, x1: m.x + w });
    });

    // Releases on the same axis.
    const gTags = svg("g", {}, "tags");
    const axisY = tagTop + 9;
    gTags.append(svg("line", { x1: 0, x2: width, y1: axisY, y2: axisY }, "tag-axis"));
    const ticks = tagLabels(width);
    for (let k = 1; k < ticks.length; k += 1) {
      const a = ticks[k - 1];
      const b = ticks[k];
      const gapDays = b.day - a.day;
      const room = b.x - a.x - 14;
      const longLabel = `${gapDays} days`;
      const shortLabel = `${gapDays}d`;
      const label = monoWidth(longLabel, 10.5) + 10 <= room ? longLabel : monoWidth(shortLabel, 10.5) + 8 <= room ? shortLabel : null;
      if (!label) continue;
      const mid = (a.x + b.x) / 2;
      const w = monoWidth(label, 10.5) + 8;
      const g = svg("g", {}, "tag-gap");
      edgeLabels.push({ node: g, x0: mid - w / 2, x1: mid + w / 2 });
      g.style.setProperty("--d", `${Math.max(0, colOf(b.day) - visibleFrom) * 13 + 420}ms`);
      g.append(svg("rect", { x: (mid - w / 2).toFixed(1), y: axisY - 7, width: w.toFixed(1), height: 14, rx: 7 }, "tag-gap-bg"));
      const t = svg("text", { x: mid.toFixed(1), y: axisY + 3.5 }, "tag-gap-text");
      t.textContent = label;
      g.append(t);
      gTags.append(g);
    }
    // Every release is named, hanging from its own tick like a flag; where names would touch they step down a row.
    for (const t of tagLabels(width)) {
      const g = svg("g", { "data-tag": t.name, "data-day": t.day }, "tag");
      g.style.setProperty("--d", `${Math.max(0, colOf(t.day) - visibleFrom) * 13 + 260}ms`);
      const title = svg("title");
      title.textContent = `${t.name}, ${shortDay(t.day)}`;
      g.append(title);
      g.append(svg("line", { x1: t.x.toFixed(1), x2: t.x.toFixed(1), y1: tagTop - TAG_GAP + 2, y2: axisY }, "tag-stem"));
      const baseline = axisY + TAG_ROW0 + t.row * TAG_ROW;
      g.append(svg("line", { x1: t.x.toFixed(1), x2: t.x.toFixed(1), y1: axisY + 6, y2: baseline + 2 }, "tag-leader"));
      g.append(svg("path", { d: `M${t.x.toFixed(1)},${axisY - 5} l5,5 l-5,5 l-5,-5 z` }, `tag-mark${major(t.name) ? " is-major" : ""}`));
      const text = svg("text", { x: (t.flip ? t.x - TAG_PAD : t.x + TAG_PAD).toFixed(1), y: baseline }, `tag-name${t.flip ? " is-flip" : ""}`);
      text.textContent = t.name;
      g.append(text);
      edgeLabels.push({ node: text, x0: t.x0, x1: t.x1 });
      gTags.append(g);
    }

    // The busiest day: a ring, a stem, and the pill over its column.
    const b = DATA.busiest;
    const bx = colOf(b) * px + gap / 2;
    const by = cellsTop + rowOf(b) * py + gap / 2;
    const gBusy = svg("g", {}, "busy");
    // The stem runs from the pill down to the ring, stepping around a month name that sits in its way.
    const stemX = bx + cw / 2;
    const crossed = placedMonths.some((m) => stemX > m.x0 - 3 && stemX < m.x1 + 3);
    const stemRuns = crossed ? [[CALL_H - 3, CALL_H + 2], [CELLS_TOP - 4, by - 2]] : [[CALL_H - 3, by - 2]];
    for (const [y1, y2] of stemRuns) gBusy.append(svg("line", { x1: stemX.toFixed(1), x2: stemX.toFixed(1), y1, y2 }, "busy-stem"));
    gBusy.append(svg("rect", { x: (bx - 2.5).toFixed(1), y: (by - 2.5).toFixed(1), width: (cw + 5).toFixed(1), height: (ch + 5).toFixed(1), rx: (r + 2).toFixed(1) }, "busy-ring"));
    const pulse = svg("rect", { x: bx.toFixed(1), y: by.toFixed(1), width: cw.toFixed(1), height: ch.toFixed(1), rx: r.toFixed(1) }, "busy-pulse");
    gBusy.append(pulse);

    cursor = svg("rect", { width: (cw + 4).toFixed(2), height: (ch + 4).toFixed(2), rx: (r + 1.5).toFixed(2) }, "cell-cursor");

    map.append(gMonths, gCells, gTags, gBusy, cursor);

    const pillText = isPhone() ? `Busiest day, ${days[b]} commits` : `Busiest day: ${days[b]} commits on ${shortDay(b)}`;
    callout.textContent = pillText;
    const pillW = monoWidth(pillText, 11) + 22;
    const pillX = clamp(bx + cw / 2 - pillW / 2, 0, width - pillW);
    setVars(callout, { "--x": `${pillX.toFixed(1)}px`, "--pw": `${pillW.toFixed(1)}px`, "--stem": `${(bx + cw / 2 - pillX).toFixed(1)}px` });
    edgeLabels.push({ node: callout, x0: pillX, x1: pillX + pillW });

    // Day names in the fixed column.
    daysSvg.replaceChildren();
    daysSvg.setAttribute("width", DAY_COL);
    daysSvg.setAttribute("height", height);
    ["Mon", "", "Wed", "", "Fri", "", ""].forEach((name, k) => {
      if (!name) return;
      const t = svg("text", { x: 0, y: (cellsTop + k * py + py / 2 + 4).toFixed(1) }, "day-name");
      t.textContent = name;
      daysSvg.append(t);
    });
    const tag = svg("g", { transform: `translate(2 ${axisY - 6})` }, "tag-glyph");
    tag.append(svg("path", { d: "M1 1h6l5 5-6 6-5-5z" }));
    tag.append(svg("circle", { cx: 4.2, cy: 4.2, r: 1.1 }));
    daysSvg.append(tag);

    if (active >= 0) placeCursor(active);
  }

  function placeCursor(i) {
    const rect = cells[i];
    if (!rect || !cursor) return;
    cursor.setAttribute("x", (Number(rect.getAttribute("x")) - 2).toFixed(2));
    cursor.setAttribute("y", (Number(rect.getAttribute("y")) - 2).toFixed(2));
    cursor.classList.add("is-on");
  }

  function dayAt(event) {
    const box = map.getBoundingClientRect();
    const x = event.clientX - box.left;
    const y = event.clientY - box.top - CELLS_TOP;
    if (y < 0 || y >= py * 7) return -1;
    const c = Math.floor(x / px);
    const rr = Math.floor(y / py);
    const i = c * 7 + rr - first;
    return i >= 0 && i < n ? i : -1;
  }

  let downAt = null;
  map.addEventListener("pointermove", (event) => {
    if (event.pointerType !== "mouse") return;
    const i = dayAt(event);
    if (i < 0) return;
    if (i !== active) onHover(i, "pointer");
  });
  map.addEventListener("pointerleave", (event) => {
    if (event.pointerType === "mouse") onLeave();
  });
  map.addEventListener("pointerdown", (event) => {
    downAt = { x: event.clientX, y: event.clientY };
  });
  map.addEventListener("pointerup", (event) => {
    if (!downAt || Math.hypot(event.clientX - downAt.x, event.clientY - downAt.y) > 8) return;
    const i = dayAt(event);
    if (i >= 0) onPick(i, "tap");
  });
  map.addEventListener("pointercancel", () => {
    downAt = null;
  });

  scroller.addEventListener("keydown", (event) => {
    const steps = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 };
    if (event.key === "Escape") {
      onLeave();
      return;
    }
    let next = null;
    if (event.key in steps) next = (active < 0 ? DATA.busiest : active) + steps[event.key];
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = n - 1;
    if (next === null) return;
    event.preventDefault();
    next = clamp(next, 0, n - 1);
    onPick(next, "key");
    revealCell(next);
  });

  // A phone shows whole weeks only: the window is a whole number of columns wide and scrolls a column at a time.
  const shownCols = () => Math.max(1, Math.round(scroller.clientWidth / px));
  const scrollToCol = (c) => {
    scroller.scrollLeft = clamp(c, 0, Math.max(0, cols - shownCols())) * px;
  };
  const glideToCol = (c) => {
    scroller.scrollTo({ left: clamp(c, 0, Math.max(0, cols - shownCols())) * px, behavior: calm() ? "auto" : "smooth" });
  };
  // The phone opens on the busiest day, a third of the way in, so the card under the map describes a day in view.
  function openingCol() {
    const fit = Math.max(1, Math.floor((host.clientWidth - DAY_COL) / px));
    return clamp(colOf(DATA.busiest) - Math.floor(fit / 3), 0, Math.max(0, cols - fit));
  }

  function revealCell(i) {
    const c = colOf(i);
    const from = Math.round(scroller.scrollLeft / px);
    if (c < from + 1) scrollToCol(c - 1);
    else if (c > from + shownCols() - 2) scrollToCol(c - shownCols() + 2);
  }

  let lastSize = "";
  function layout(width, height) {
    const key = `${Math.round(width)}:${Math.round(height || 0)}:${isPhone()}`;
    if (key === lastSize) return;
    lastSize = key;
    const wasFrom = Math.round(scroller.scrollLeft / px);
    geometry(width, height);
    const fit = Math.max(1, Math.floor((width - DAY_COL) / px));
    const scrolls = cols * px > width - DAY_COL + 0.5;
    setVars(host, { "--sw": scrolls ? `${fit * px}px` : "1fr" });
    draw();
    snaps.replaceChildren();
    if (scrolls) for (let c = 0; c <= cols - fit; c += 1) snaps.append(el("span", "heat-snap"));
    range.hidden = !scrolls;
    if (!introDone) scrollToCol(isPhone() ? openingCol() : cols);
    else scrollToCol(wasFrom);
    trimEdges();
    syncRange();
    if (introDone) map.classList.add("is-settled");
  }

  function intro() {
    if (calm()) {
      introDone = true;
      map.classList.add("is-settled");
      panel.classList.add("is-settled");
      return;
    }
    // A phone reveals the map behind one moving curtain, which the compositor runs alone.
    const curtain = isPhone();
    if (curtain) {
      const veil = el("div", "heat-curtain");
      veil.setAttribute("aria-hidden", "true");
      host.append(veil);
      window.setTimeout(() => veil.remove(), 1400);
    } else {
      map.classList.add("is-intro");
    }
    panel.classList.add("is-intro");
    window.setTimeout(() => {
      introDone = true;
      map.classList.remove("is-intro");
      map.classList.add("is-settled");
      panel.classList.remove("is-intro");
      panel.classList.add("is-settled");
    }, 1700);
  }

  return {
    layout,
    intro,
    ranges,
    level,
    get pitch() {
      return { px, py };
    },
    setActive(i) {
      active = i;
      placeCursor(i);
      for (const g of map.querySelectorAll(".tag.is-on")) g.classList.remove("is-on");
      const tag = map.querySelector(`.tag[data-day="${i}"]`);
      if (tag) tag.classList.add("is-on");
    },
    clearActive() {
      active = -1;
      cursor?.classList.remove("is-on");
      for (const g of map.querySelectorAll(".tag.is-on")) g.classList.remove("is-on");
    },
    cellRect(i) {
      return cells[i]?.getBoundingClientRect();
    },
    revealCell,
    get scroller() {
      return scroller;
    },
  };
}
