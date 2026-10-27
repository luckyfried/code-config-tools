// The day strip, today's list, and the seven-day week, drawn from the saved blocks.
import { DAY, HOUR, addDays, duration, hourLabel, hours, timeOfDay, weekday, windowOf } from "./time.js";

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

const overlap = (a, b, lo, hi) => Math.max(0, Math.min(b, hi) - Math.max(a, lo));
const pct = (n) => (Math.round(n * 1000) / 1000).toString();

// Short blocks keep a pill's minimum width (CSS --block-min), so once laid out a strip is fitted in pixels, in the
// order the blocks began. A pill wider than its time is centred on that time; one that would touch the block before
// it moves along; the block under way keeps its end at the now line and gives up width (down to a round dot) before
// it covers the block before it, which steps back instead, as every finished block does before the now line. Then a tick under a block, or within reach of one or of
// the now line, is hidden.
const GAP = 3;
const TICK_CLEAR = 8;

export function fitStrip(node) {
  const width = node.clientWidth;
  if (!width) return;
  const blocks = [...node.querySelectorAll(".strip__block")].filter((b) => !b.hidden);
  for (const b of blocks) for (const prop of ["left", "width", "margin-left"]) b.style.removeProperty(prop);
  const spans = blocks
    .map((b) => {
      const live = b.classList.contains("is-live");
      let l = b.offsetLeft;
      const w = b.offsetWidth;
      if (!live) {
        const x = (parseFloat(b.style.getPropertyValue("--x")) / 100) * width;
        const real = (parseFloat(b.style.getPropertyValue("--w")) / 100) * width;
        l = Math.max(0, Math.min(width - w, x + real / 2 - w / 2));
      }
      return { b, live, t: Number(b.dataset.start), l, w, h: b.offsetHeight };
    })
    .sort((p, q) => p.t - q.t);

  for (let i = 1; i < spans.length; i++) {
    const s = spans[i];
    const prevR = spans[i - 1].l + spans[i - 1].w;
    if (s.l >= prevR + GAP) continue;
    if (s.live) {
      const r = s.l + s.w;
      s.w = Math.max(s.h, r - prevR - GAP);
      s.l = r - s.w;
    } else {
      s.l = prevR + GAP;
    }
  }
  const now = node.querySelector(".strip__now");
  const nowX = now && !now.hidden ? now.offsetLeft + now.offsetWidth / 2 : null;
  for (let i = spans.length - 1; i >= 0; i--) {
    const s = spans[i];
    if (s.live) continue;
    const bound = i + 1 < spans.length ? spans[i + 1].l : nowX !== null ? nowX - 1 : Infinity;
    const over = s.l + s.w + GAP - bound;
    if (over > 0) s.l -= over;
  }
  for (const s of spans) {
    s.b.style.left = `${s.l}px`;
    s.b.style.width = `${s.w}px`;
    s.b.style.marginLeft = "0px";
  }

  for (const t of node.querySelectorAll(".strip__tick")) {
    const x = t.offsetLeft + t.offsetWidth / 2;
    const covered = spans.some((s) => x > s.l - TICK_CLEAR && x < s.l + s.w + TICK_CLEAR) || (nowX !== null && Math.abs(x - nowX) < TICK_CLEAR);
    t.classList.toggle("is-covered", covered);
  }
}

const fitter = typeof ResizeObserver === "function" ? new ResizeObserver((entries) => entries.forEach((e) => fitStrip(e.target))) : null;

export function dayTotal(blocks, day0) {
  return blocks.reduce((sum, b) => sum + overlap(b.start, b.end, day0, day0 + DAY), 0);
}

// Draws one strip for the day that starts at midnight `day0` and returns a function that moves the live block
// and the now line to a new time. With `grow` every block grows into place with the spring, its row's turn set by
// `row`; the block whose start is `landed` slides down onto the strip with a bloom, the block that just ended.
export function renderStrip(node, { blocks, day0, cfg, grow = false, row = 0, landed = null, live, labels = false, nowLine = false }) {
  const { from, to } = windowOf(day0, cfg);
  const span = to - from;
  const place = (a, b) => ({ x: ((Math.max(a, from) - from) / span) * 100, w: (overlap(a, b, from, to) / span) * 100 });
  const frag = document.createDocumentFragment();
  const hoursSpan = cfg.dayEnd - cfg.dayStart;
  const step = hoursSpan <= 8 ? 1 : hoursSpan <= 12 ? 2 : 3;

  for (let h = cfg.dayStart; h <= cfg.dayEnd; h += step) {
    const x = ((h - cfg.dayStart) / hoursSpan) * 100;
    if (h > cfg.dayStart && h < cfg.dayEnd) {
      const tick = el("span", "strip__tick");
      tick.style.setProperty("--x", pct(x));
      frag.append(tick);
    }
    if (labels) {
      const at = new Date(day0);
      at.setHours(h, 0, 0, 0);
      const label = el("span", "strip__hour", hourLabel(at));
      if (h === cfg.dayStart) label.classList.add("is-first");
      if (h + step > cfg.dayEnd) label.classList.add("is-last");
      label.style.setProperty("--x", pct(x));
      frag.append(label);
    }
  }

  node.style.setProperty("--row", String(row));
  let order = 0;
  for (const b of blocks) {
    if (overlap(b.start, b.end, from, to) <= 0) continue;
    const { x, w } = place(b.start, b.end);
    const block = el("span", "strip__block");
    block.dataset.start = String(b.start);
    block.style.setProperty("--x", pct(x));
    block.style.setProperty("--w", pct(w));
    block.title = `${b.label || "Focus"}, ${timeOfDay(b.start)} to ${timeOfDay(b.end)}`;
    if (b.start === landed) block.classList.add("is-landed");
    else if (grow) {
      block.classList.add("is-grow");
      block.style.setProperty("--i", String(order++));
    }
    frag.append(block);
  }

  let liveNode = null;
  if (live && live.start < to && live.start + 1 > from - DAY) {
    liveNode = el("span", "strip__block is-live");
    liveNode.dataset.start = String(live.start);
    frag.append(liveNode);
  }
  const nowNode = nowLine ? el("span", "strip__now") : null;
  if (nowNode) frag.append(nowNode);
  node.replaceChildren(frag);
  fitter?.observe(node);

  return (now) => {
    if (liveNode) {
      const { x, w } = place(live.start, Math.max(now, live.start));
      liveNode.style.setProperty("--x", pct(x));
      liveNode.style.setProperty("--w", pct(w));
      liveNode.hidden = w <= 0;
    }
    if (nowNode) {
      nowNode.hidden = now < from || now > to;
      nowNode.style.setProperty("--x", pct(((now - from) / span) * 100));
    }
    fitStrip(node);
  };
}

export function renderList(node, blocks, day0, { grow = false, landed = null } = {}) {
  const today = blocks.filter((b) => overlap(b.start, b.end, day0, day0 + DAY) > 0).reverse();
  if (!today.length) {
    node.replaceChildren(el("li", "blocks__empty", "No blocks yet today. Each one you finish lands on the strip."));
    return;
  }
  node.replaceChildren(
    ...today.map((b, i) => {
      const li = el("li", b.start === landed ? "is-landed" : grow ? "is-grow" : "");
      li.style.setProperty("--i", String(i));
      const what = el("span", "blocks__what");
      what.append(el("span", "blocks__label", b.label || "Focus"), el("span", "blocks__when", `${timeOfDay(b.start)} to ${timeOfDay(b.end)}`));
      li.append(el("span", "blocks__swatch"), what, el("span", "blocks__dur", duration(b.end - b.start)));
      return li;
    }),
  );
}

// Seven rows, six days back to today, each a small strip and its hours. Inside a button (the phone's week card) the
// rows are spans (`tag`); today's row carries the block under way and the now line, as the Today strip does.
export function renderWeek(rowsNode, sumNode, { blocks, day0, cfg, grow = false, landed = null, tag = "li", live = null, nowLine = false }) {
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d0 = addDays(day0, -i);
    days.push({ d0, ms: dayTotal(blocks, d0), today: i === 0 });
  }
  const most = Math.max(HOUR, ...days.map((d) => d.ms));
  const updaters = [];
  if (fitter) for (const old of rowsNode.querySelectorAll(".strip")) fitter.unobserve(old);
  rowsNode.replaceChildren(
    ...days.map((d, i) => {
      const li = el(tag, d.today ? "week__row is-today" : "week__row");
      li.style.setProperty("--row", String(i + 1));
      const strip = el("span", "strip");
      const today = d.today ? { live, nowLine } : {};
      updaters.push(renderStrip(strip, { blocks, day0: d.d0, cfg, grow, row: i + 1, landed, ...today }));
      const hrs = el("span", "week__hours");
      const bar = el("span", grow ? "week__bar is-grow" : "week__bar");
      const fill = el("span");
      fill.style.setProperty("--p", pct(d.ms / most));
      bar.append(fill);
      hrs.append(el("span", "", hours(d.ms)), bar);
      li.append(el("span", "week__day", d.today ? "Today" : weekday(d.d0)), strip, hrs);
      return li;
    }),
  );
  const total = days.reduce((s, d) => s + d.ms, 0);
  const best = days.reduce((a, b) => (b.ms > a.ms ? b : a), days[0]);
  if (!sumNode) return { total, updaters };
  sumNode.replaceChildren();
  if (total > 0) {
    sumNode.append(`Most on ${best.today ? "today" : weekday(best.d0)}, with `, el("strong", "", duration(best.ms)), ".");
  } else {
    sumNode.textContent = "Your week fills in here, one strip a day.";
  }
  return { total, updaters };
}
