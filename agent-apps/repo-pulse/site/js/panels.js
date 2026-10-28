// The numbers strip, the authors table, the most-changed files, the weekly timeline, and the release cadence.
import {
  DATA, el, svg, fmt, compact, plural, shortName, authorColor, dayDate, shortDay, fmtDate, tween, ease, calm,
  catmullRom, setVars, showTip, hideTip, escapeHtml, monoWidth, isPhone, clamp,
} from "./util.js";

const DAY_MS = 86400000;
// ease.out (a quartic) as a CSS curve, so what moves beside a number keeps its pace.
const COUNT = "cubic-bezier(0.25, 1, 0.5, 1)";

export function releaseGaps() {
  const gaps = [];
  for (let k = 1; k < DATA.tags.length; k += 1) gaps.push(DATA.tags[k][1] - DATA.tags[k - 1][1]);
  const sorted = [...gaps].sort((a, b) => a - b);
  const median = sorted.length ? sorted[Math.floor(sorted.length / 2)] : 0;
  return { gaps, median, longest: sorted[sorted.length - 1] || 0, shortest: sorted[0] || 0 };
}

/* The numbers */

export function createStats(host) {
  const days = DATA.days.length;
  const lines = DATA.added + DATA.removed;
  const { median } = releaseGaps();
  const lead = DATA.authors[0];
  const items = [
    { value: DATA.commits, label: "commits", sub: `over ${plural(days, "day")}`, viz: sparkline },
    { value: DATA.authors.length, label: DATA.authors.length === 1 ? "author" : "authors", sub: lead ? `${shortName(lead.n)} leads with ${fmt(lead.c)}` : "", viz: shareBar },
    { value: lines, label: "lines changed", sub: null, viz: splitBar },
    { value: DATA.activeDays, label: "days with commits", sub: `Longest run: ${plural(DATA.streak, "day")}`, viz: activeBar },
    { value: DATA.tags.length, label: DATA.tags.length === 1 ? "release" : "releases", sub: DATA.tags.length > 1 ? `About every ${plural(median, "day")}` : DATA.tags.length ? "One in the window" : "No tags in the window", viz: tagTicks },
  ];
  host.replaceChildren();
  // Each card's bar and caption wait for its number, so all three arrive together.
  if (!calm()) host.classList.add("is-waiting");
  const counters = [];
  for (const item of items) {
    const stat = el("div", "stat");
    const value = el("p", "stat-value", calm() ? fmt(item.value) : "0");
    value.dataset.value = item.value;
    const label = el("p", "stat-label", item.label);
    const head = el("div", "stat-head");
    head.append(value, label);
    stat.append(head);
    const viz = item.viz();
    if (viz) stat.append(viz);
    if (item.sub === null) {
      const sub = el("p", "stat-sub stat-split");
      sub.append(el("span", "is-add", `+${fmt(DATA.added)}`), el("span", "is-del", `−${fmt(DATA.removed)}`));
      stat.append(sub);
    } else if (item.sub) {
      stat.append(el("p", "stat-sub", item.sub));
    }
    host.append(stat);
    counters.push({ node: value, viz, sub: stat.querySelector(".stat-sub") });
  }
  return {
    play() {
      host.classList.remove("is-waiting");
      counters.forEach(({ node, viz, sub }, k) => {
        const target = Number(node.dataset.value);
        const delay = 60 + k * 70;
        tween({ duration: 1100, delay, easing: ease.out, update: (t) => (node.textContent = fmt(Math.round(target * t))) });
        if (calm()) return;
        // The bar fills left to right on the count's own curve; the caption settles in as the count lands.
        viz?.animate([{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }], { duration: 1100, delay, easing: COUNT, fill: "backwards" });
        sub?.animate([{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "none" }], { duration: 320, delay: delay + 640, easing: COUNT, fill: "backwards" });
      });
    },
  };
}

function sparkline() {
  const w = 120;
  const h = 28;
  const weeks = DATA.weeks;
  const max = Math.max(...weeks, 1);
  const pts = weeks.map((v, i) => [(i / Math.max(1, weeks.length - 1)) * w, h - 2 - (v / max) * (h - 4)]);
  const node = svg("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none", "aria-hidden": "true" }, "stat-viz spark");
  node.append(svg("path", { d: `${catmullRom(pts)}L${w},${h}L0,${h}Z` }, "spark-fill"));
  node.append(svg("path", { d: catmullRom(pts) }, "spark-line"));
  return node;
}

function shareBar() {
  const bar = el("div", "stat-viz share");
  bar.setAttribute("aria-hidden", "true");
  DATA.authors.slice(0, 8).forEach((a, k) => {
    const seg = el("span", "share-seg");
    setVars(seg, { "--c": authorColor(k), "--f": a.c });
    bar.append(seg);
  });
  const rest = DATA.authors.slice(8).reduce((sum, a) => sum + a.c, 0);
  if (rest) {
    const seg = el("span", "share-seg is-rest");
    setVars(seg, { "--c": "var(--cat-rest)", "--f": rest });
    bar.append(seg);
  }
  return bar;
}

function splitBar() {
  const bar = el("div", "stat-viz split");
  bar.setAttribute("aria-hidden", "true");
  const add = el("span", "split-add");
  const del = el("span", "split-del");
  setVars(add, { "--f": DATA.added });
  setVars(del, { "--f": DATA.removed });
  bar.append(add, del);
  return bar;
}

function activeBar() {
  const w = 120;
  const h = 28;
  const node = svg("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none", "aria-hidden": "true" }, "stat-viz active");
  const n = DATA.days.length;
  const step = w / n;
  DATA.days.forEach((c, i) => {
    if (!c) return;
    node.append(svg("rect", { x: (i * step).toFixed(2), y: 6, width: Math.max(0.6, step * 0.7).toFixed(2), height: h - 12 }, "active-day"));
  });
  return node;
}

function tagTicks() {
  const w = 120;
  const h = 28;
  const node = svg("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none", "aria-hidden": "true" }, "stat-viz ticks");
  const n = DATA.days.length;
  node.append(svg("line", { x1: 0, x2: w, y1: h / 2, y2: h / 2 }, "ticks-axis"));
  for (const [, day] of DATA.tags) {
    const x = ((day + 0.5) / n) * w;
    node.append(svg("line", { x1: x.toFixed(2), x2: x.toFixed(2), y1: 5, y2: h - 5 }, "ticks-mark"));
  }
  return node;
}

/* Authors */

export function createAuthorTable(host, { onFocus }) {
  const max = Math.max(...DATA.authors.map((a) => a.c), 1);
  const table = el("table", "authors-table");
  const caption = el("caption", "visually-hidden", "Commits and lines changed per author");
  const thead = el("thead");
  const hr = el("tr");
  for (const [text, cls] of [["Author", "col-who"], ["Commits", "col-commits"], ["Lines added", "col-add"], ["Lines removed", "col-del"], ["Active days", "col-days"]]) {
    const th = el("th", cls, text);
    th.scope = "col";
    hr.append(th);
  }
  thead.append(hr);
  const tbody = el("tbody");
  DATA.authors.forEach((a, k) => {
    const tr = el("tr", k < 8 ? "is-top" : "is-rest");
    tr.dataset.key = k < 8 ? k : "rest";
    const who = el("td", "col-who");
    const dot = el("span", "who-dot");
    dot.style.setProperty("--c", authorColor(k));
    const name = el("span", "who-name", a.n);
    const span = el("span", "who-span", `${shortDay(a.f)} to ${shortDay(a.l)}`);
    const text = el("span", "who-text");
    text.append(name, span);
    who.append(dot, text);
    const commits = el("td", "col-commits");
    const bar = el("span", "c-bar");
    setVars(bar, { "--f": (a.c / max).toFixed(4), "--c": authorColor(k) });
    commits.append(el("span", "c-num", fmt(a.c)), bar);
    tr.append(who, commits, el("td", "col-add", `+${fmt(a.a)}`), el("td", "col-del", `−${fmt(a.r)}`), el("td", "col-days", fmt(a.d)));
    tr.addEventListener("pointerenter", () => onFocus?.(tr.dataset.key));
    tr.addEventListener("pointerleave", () => onFocus?.(null));
    tbody.append(tr);
  });
  table.append(caption, thead, tbody);
  host.replaceChildren(table);
  return {
    focus(key) {
      for (const tr of tbody.children) tr.classList.toggle("is-on", key !== null && tr.dataset.key === String(key));
    },
  };
}

/* Files */

export function createFiles(host) {
  const max = Math.max(...DATA.files.map((f) => f[1]), 1);
  const list = el("ol", "files");
  DATA.files.forEach(([path, lines, commits], k) => {
    const item = el("li", "file");
    item.style.setProperty("--i", k);
    const cut = path.lastIndexOf("/");
    const where = el("p", "file-path");
    // The folder trims from its left end; the marks keep its slashes where they belong.
    if (cut >= 0) where.append(el("span", "file-dir", `\u200e${path.slice(0, cut + 1)}\u200e`));
    where.append(el("span", "file-name", path.slice(cut + 1)));
    where.title = path;
    const bar = el("span", "file-bar");
    bar.style.setProperty("--f", (lines / max).toFixed(4));
    const nums = el("p", "file-nums");
    nums.append(el("span", "file-lines", `${fmt(lines)} lines`), el("span", "file-commits", plural(commits, "commit")));
    item.append(el("span", "file-rank", String(k + 1)), where, bar, nums);
    list.append(item);
  });
  host.replaceChildren(list);
}

/* Timeline: commits per week with the releases over them */

export function createTimeline(host) {
  const node = svg("svg", { role: "img", "aria-label": `Commits per week, with ${plural(DATA.tags.length, "release")}` }, "weeks-svg");
  host.replaceChildren(node);
  const [wy, wm, wd] = DATA.weekStart.split("-").map(Number);
  const week0 = Date.UTC(wy, wm - 1, wd);
  const startMs = dayDate(0).getTime();
  let played = false;
  let size = null;

  function render(w, h, animate = false) {
    if (w < 60 || h < 60) return;
    size = { w, h };
    node.setAttribute("width", Math.round(w));
    node.setAttribute("height", Math.round(h));
    node.setAttribute("viewBox", `0 0 ${Math.round(w)} ${Math.round(h)}`);
    const weeks = DATA.weeks;
    const left = 34;
    const flagLane = isPhone() ? 44 : 52;
    const axis = 26;
    const plotW = w - left - 4;
    const plotH = h - flagLane - axis;
    const top = flagLane;
    const max = Math.max(...weeks, 1);
    const stepY = niceStep(max);
    const yMax = Math.ceil(max / stepY) * stepY;
    const step = plotW / weeks.length;
    const bw = Math.max(2, step * 0.68);
    const y = (v) => top + plotH - (v / yMax) * plotH;
    const parts = [];

    const gGrid = svg("g", {}, "weeks-grid");
    for (let v = 0; v <= yMax; v += stepY) {
      gGrid.append(svg("line", { x1: left, x2: w, y1: y(v).toFixed(1), y2: y(v).toFixed(1) }, v === 0 ? "grid-base" : "grid-line"));
      const t = svg("text", { x: left - 8, y: (y(v) + 4).toFixed(1) }, "axis-num");
      t.textContent = compact(v);
      gGrid.append(t);
    }
    // Month names under the bars.
    let lastX = -Infinity;
    weeks.forEach((_, i) => {
      const d = new Date(week0 + i * 7 * DAY_MS);
      const d2 = new Date(week0 + (i + 1) * 7 * DAY_MS);
      if (d.getUTCMonth() === d2.getUTCMonth() && i !== 0) return;
      const x = left + (i + 1) * step;
      const text = fmtDate(d2, d2.getUTCMonth() === 0 ? { month: "short", year: "numeric" } : { month: "short" });
      if (x - lastX < monoWidth(text, 11) + 10 || x > w - 20) return;
      lastX = x;
      const t = svg("text", { x: x.toFixed(1), y: h - 8 }, "axis-label is-start");
      t.textContent = text;
      gGrid.append(t);
    });
    parts.push(gGrid);

    const gBars = svg("g", {}, "weeks-bars");
    weeks.forEach((v, i) => {
      const x = left + i * step + (step - bw) / 2;
      const r = svg("rect", { x: x.toFixed(1), y: y(v).toFixed(1), width: bw.toFixed(1), height: Math.max(0, top + plotH - y(v)).toFixed(1), rx: Math.min(3, bw / 3).toFixed(1) }, "week-bar");
      r.dataset.week = i;
      r.style.setProperty("--d", `${i * 14}ms`);
      gBars.append(r);
    });
    parts.push(gBars);

    // The four-week average as a smooth line.
    const avg = weeks.map((_, i) => {
      const from = Math.max(0, i - 3);
      const slice = weeks.slice(from, i + 1);
      return slice.reduce((a, b) => a + b, 0) / slice.length;
    });
    const pts = avg.map((v, i) => [left + i * step + step / 2, y(v)]);
    const line = svg("path", { d: catmullRom(pts) }, "weeks-avg");
    parts.push(line);

    // Releases as flags, staggered into lanes so no two names touch.
    const gFlags = svg("g", {}, "weeks-flags");
    const lanes = [[], []];
    const flagX = (day) => left + ((startMs + day * DAY_MS - week0) / (7 * DAY_MS)) * step;
    DATA.tags.forEach(([name, day], k) => {
      const x = flagX(day);
      const tw = monoWidth(name, 11) + 14;
      let lane = lanes.findIndex((l) => l.every(([a, b]) => x + tw + 4 < a || x - 4 > b));
      const g = svg("g", { "data-tag": name }, "flag");
      g.style.setProperty("--d", `${(day / DATA.days.length) * weeks.length * 14 + 300}ms`);
      const title = svg("title");
      title.textContent = `${name}, ${shortDay(day)}`;
      g.append(title);
      // A flag near the right edge flies to the left of its pole.
      let x0 = x;
      if (lane < 0 || x + tw > w) {
        x0 = x - tw;
        lane = lanes.findIndex((l) => l.every(([a, b]) => x0 + tw + 4 < a || x0 - 4 > b));
      }
      const fits = lane >= 0 && x0 >= left;
      const fy = lane === 1 ? 26 : 6;
      g.append(svg("line", { x1: x.toFixed(1), x2: x.toFixed(1), y1: fits ? fy : flagLane - 10, y2: top + plotH }, "flag-pole"));
      if (fits) {
        lanes[lane].push([x0, x0 + tw]);
        g.append(svg("rect", { x: x0.toFixed(1), y: fy, width: tw.toFixed(1), height: 18, rx: 4 }, "flag-cloth"));
        const t = svg("text", { x: (x0 + 7).toFixed(1), y: fy + 13 }, "flag-name");
        t.textContent = name;
        g.append(t);
      } else {
        g.append(svg("circle", { cx: x.toFixed(1), cy: flagLane - 10, r: 3 }, "flag-dot"));
      }
      gFlags.append(g);
    });
    parts.push(gFlags);
    node.replaceChildren(...parts);

    node.onpointermove = (event) => {
      const box = node.getBoundingClientRect();
      const i = Math.floor((event.clientX - box.left - left) / step);
      if (i < 0 || i >= weeks.length) {
        hideTip();
        return;
      }
      for (const b of gBars.querySelectorAll(".is-on")) b.classList.remove("is-on");
      gBars.children[i].classList.add("is-on");
      const d = new Date(week0 + i * 7 * DAY_MS);
      showTip(`<strong>Week of ${fmtDate(d, { month: "short", day: "numeric", year: "numeric" })}</strong><span>${plural(weeks[i], "commit")}</span>`, event.clientX, event.clientY);
    };
    node.onpointerleave = () => {
      hideTip();
      for (const b of gBars.querySelectorAll(".is-on")) b.classList.remove("is-on");
    };
    if (animate && !calm()) {
      node.classList.remove("is-grown");
      node.getBoundingClientRect();
      node.classList.add("is-growing");
      const len = line.getTotalLength();
      line.style.setProperty("--len", len.toFixed(0));
    } else {
      node.classList.add("is-grown");
    }
  }

  return {
    render(w, h) {
      render(w, h, false);
    },
    play() {
      if (played || !size) return;
      played = true;
      render(size.w, size.h, true);
    },
  };
}

function niceStep(max) {
  const raw = max / 4;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / mag;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag;
}

/* Release cadence */

export function createCadence(host) {
  const { gaps, median, longest, shortest } = releaseGaps();
  host.replaceChildren();
  const summary = el("dl", "cadence-sum");
  const pairs = [
    ["Typical gap", DATA.tags.length > 1 ? plural(median, "day") : "None yet"],
    ["Longest", DATA.tags.length > 1 ? plural(longest, "day") : "None yet"],
    ["Shortest", DATA.tags.length > 1 ? plural(shortest, "day") : "None yet"],
  ];
  for (const [term, value] of pairs) {
    const wrap = el("div", "cadence-fact");
    wrap.append(el("dt", "", term), el("dd", "", value));
    summary.append(wrap);
  }
  const list = el("ol", "cadence");
  const max = Math.max(...gaps, 1);
  [...DATA.tags].reverse().forEach(([name, day], idx) => {
    const k = DATA.tags.length - 1 - idx;
    const item = el("li", "rel");
    item.style.setProperty("--i", idx);
    const head = el("p", "rel-head");
    head.append(el("span", "rel-name", name), el("span", "rel-date", fmtDate(dayDate(day), { month: "short", day: "numeric", year: "numeric" })));
    item.append(head);
    if (k > 0) {
      const gap = gaps[k - 1];
      const bar = el("span", `rel-bar${gap === longest ? " is-long" : ""}`);
      bar.style.setProperty("--f", (gap / max).toFixed(4));
      item.append(bar, el("p", "rel-gap", `${plural(gap, "day")} after ${DATA.tags[k - 1][0]}`));
    } else {
      item.append(el("p", "rel-gap", "First release in the window"));
    }
    list.append(item);
  });
  host.append(summary, list);
  if (!DATA.tags.length) host.append(el("p", "empty-note", "No tags fall inside this window."));
}
