// Repo Pulse: wires the four screens, the theme switch, and the opening, then hands the page to the person.
import { DATA, CONFIG, el, fmt, plural, monthLong, fmtDate, dayDate, onResize, calm, phoneQuery, dockQuery, docked, hideTip, whenSeen } from "./util.js";
import { createHeatmap } from "./heatmap.js";
import { createDayCard } from "./daycard.js";
import { createRiver } from "./river.js";
import { createTreemap, rootOf } from "./treemap.js";
import { createStats, createAuthorTable, createFiles, createTimeline, createCadence } from "./panels.js";

const $ = (sel) => document.querySelector(sel);
const app = $("#app");
const VIEWS = ["overview", "authors", "churn", "timeline"];

/* Header and footer */

document.title = `${DATA.title} — Repo Pulse`;
$("#repo-title").textContent = DATA.title;
const longDate = (i) => fmtDate(dayDate(i), { month: "short", day: "numeric", year: "numeric" });
const monthYear = (i) => fmtDate(dayDate(i), { month: "short", year: "numeric" });
const windowText = () => (window.innerWidth < 1100 ? `${monthYear(0)} to ${monthYear(DATA.days.length - 1)}` : `${longDate(0)} to ${longDate(DATA.days.length - 1)}`);
$("#repo-window").textContent = windowText();
window.addEventListener("resize", () => ($("#repo-window").textContent = windowText()));
app.dataset.commits = DATA.commits;
app.dataset.days = DATA.days.length;
if (DATA.sample) {
  const status = $("#status");
  status.textContent = "Sample year";
  status.hidden = false;
}

(function footer() {
  const totals = DATA.months.map((_, i) => DATA.river.reduce((s, r) => s + r[i], 0) + DATA.rest[i]);
  const best = totals.indexOf(Math.max(...totals));
  $("#foot-left").textContent = `${monthLong(DATA.months[best])} was the busiest month, with ${plural(totals[best], "commit")}.`;
  const { node, path } = rootOf(DATA.tree);
  const top = (node.c || [])[0];
  if (top && DATA.tree.s) {
    const share = Math.round((top.s / DATA.tree.s) * 100);
    const name = `${path}${top.n}${top.d ? "/" : ""}`;
    $("#foot-right").textContent = `${name} took ${share}% of the lines changed.`;
  }
})();

/* Theme switch: only when the page follows the device. */

const toggle = $("#theme-toggle");
if (!CONFIG.theme || CONFIG.theme === "auto") {
  toggle.hidden = false;
  const current = () => document.documentElement.dataset.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const label = () => {
    const next = current() === "dark" ? "light" : "dark";
    toggle.setAttribute("aria-label", `Switch to ${next}`);
    toggle.dataset.mode = current();
  };
  label();
  toggle.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    const swap = () => {
      document.documentElement.dataset.theme = next;
      try {
        localStorage.setItem("repo-pulse:theme", next);
      } catch {
        // Private windows may refuse storage; the switch still holds for this visit.
      }
      label();
    };
    if (document.startViewTransition && !calm()) document.startViewTransition(swap);
    else swap();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", label);
}

/* Overview */

const heatPanel = $(".panel-heat");
let card;
let tourCancel = () => {};
const heat = createHeatmap(heatPanel, {
  onHover: (i) => {
    tourCancel();
    card.show(i);
  },
  onLeave: () => {
    tourCancel();
    card.hide();
  },
  onPick: (i) => {
    tourCancel();
    card.show(i);
  },
});
card = createDayCard(heatPanel, heat);

const legend = $("#heat-legend");
(function heatLegend() {
  legend.replaceChildren();
  legend.append(el("span", "ramp-word", "Fewer"));
  const row = el("span", "ramp");
  const zero = el("span", "ramp-step lv0");
  zero.title = "No commits";
  row.append(zero);
  heat.ranges.forEach(([lo, hi], k) => {
    const step = el("span", `ramp-step lv${k + 1}`);
    step.title = hi === null ? `${lo} or more commits` : lo === hi ? plural(lo, "commit") : `${lo} to ${hi} commits`;
    row.append(step);
  });
  legend.append(row, el("span", "ramp-word", "More"));
})();

const stats = createStats($("#stats"));
const riverOverview = createRiver($("#river-overview"));
const treeOverview = createTreemap($("#tree-overview"));
$("#tree-note").textContent = DATA.ignored
  ? `${fmt(DATA.tree.s)} lines; ${fmt(DATA.ignored)} more left out`
  : `${fmt(DATA.tree.s)} lines in all`;

function oneScreen() {
  return window.matchMedia("(min-width: 1100px) and (min-height: 700px)").matches;
}

function heatHeight() {
  if (!oneScreen()) return 0;
  const view = $("#view-overview");
  const viewStyle = getComputedStyle(view);
  const panelStyle = getComputedStyle(heatPanel);
  const head = heatPanel.querySelector(".panel-head");
  const gap = parseFloat(viewStyle.rowGap) || 16;
  const statsH = $("#stats").offsetHeight;
  const viewH = view.clientHeight - parseFloat(viewStyle.paddingTop) - parseFloat(viewStyle.paddingBottom);
  const bottom = Math.max(260, Math.min(460, window.innerHeight * 0.34));
  const chrome = parseFloat(panelStyle.paddingTop) + parseFloat(panelStyle.paddingBottom) + head.offsetHeight + parseFloat(getComputedStyle(head).marginBottom);
  return viewH - statsH - gap * 2 - bottom - chrome;
}

const heatHost = heatPanel.querySelector(".heat");
let heatReady = false;
onResize(heatHost, (w) => {
  heat.layout(w, heatHeight());
  card.rest();
  heatReady = true;
});
window.addEventListener("resize", () => heat.layout(heatHost.clientWidth, heatHeight()));
for (const query of [phoneQuery, dockQuery]) {
  query.addEventListener("change", () => {
    heat.layout(heatHost.clientWidth, heatHeight());
    card.rest();
  });
}

onResize(riverOverview.plot, (w, h) => riverOverview.render(w, h));
let treeSized = false;
onResize($("#tree-overview"), (w, h) => {
  treeOverview.render(w, h);
  treeSized = true;
});

const treeHint = document.querySelector(".panel-tree-lg .panel-note");
const hintText = () => (window.matchMedia("(hover: hover)").matches ? "Hover a folder to open it" : "Tap a folder to open it");
treeHint.textContent = hintText();

/* The other screens, built when first shown */

const built = {};
function buildView(name) {
  if (built[name]) return built[name];
  if (name === "authors") {
    let table;
    const river = createRiver($("#river-authors"), { tall: true, onFocus: (key) => table?.focus(key) });
    table = createAuthorTable($("#authors-table"), { onFocus: (key) => river.highlight(key === null ? null : key) });
    onResize(river.plot, (w, h) => {
      river.render(w, h);
      river.play();
    });
    built[name] = { river };
  }
  if (name === "churn") {
    const tree = createTreemap($("#tree-churn"), { big: true });
    createFiles($("#files"));
    onResize($("#tree-churn"), (w, h) => {
      tree.render(w, h);
      if (!tree.played) tree.play();
    });
    built[name] = { tree };
  }
  if (name === "timeline") {
    const weeks = createTimeline($("#weeks"));
    createCadence($("#cadence"));
    onResize($("#weeks"), (w, h) => {
      weeks.render(w, h);
      weeks.play();
    });
    built[name] = { weeks };
  }
  return built[name];
}

/* Screens by hash */

const tabs = [...document.querySelectorAll(".tab")];
const ink = $(".tab-ink");

function currentView() {
  const name = location.hash.replace("#", "");
  return VIEWS.includes(name) ? name : "overview";
}

function moveInk() {
  const on = tabs.find((t) => t.getAttribute("aria-current") === "page");
  if (!on) return;
  ink.style.setProperty("--ix", `${on.offsetLeft}px`);
  ink.style.setProperty("--iw", `${on.offsetWidth}px`);
}

function show(name, { first = false } = {}) {
  const swap = () => {
    for (const v of VIEWS) {
      const section = $(`#view-${v}`);
      section.hidden = v !== name;
    }
    for (const t of tabs) {
      if (t.dataset.view === name) t.setAttribute("aria-current", "page");
      else t.removeAttribute("aria-current");
    }
    app.dataset.view = name;
    if (name !== "overview") buildView(name);
    moveInk();
    hideTip();
  };
  if (!first && document.startViewTransition && !calm()) document.startViewTransition(swap);
  else swap();
  if (!first) window.scrollTo({ top: 0 });
}

window.addEventListener("hashchange", () => {
  tourCancel();
  show(currentView());
});
onResize($(".tabs"), moveInk);

/* The opening: one orchestrated second, then a short look around that stops the moment the person moves. */

function opening() {
  const start = currentView();
  show(start, { first: true });
  requestAnimationFrame(() => ink.classList.add("is-ready"));
  // What a phone shows further down starts when it scrolls into view; a desktop sees it all at once. A screen
  // opened first by its address plays the overview's when the overview is first shown.
  whenSeen($("#stats"), () => stats.play());
  whenSeen(riverOverview.plot, () => riverOverview.play());
  // The treemap splits once the heat map above it has taken its height, so it splits at its final size.
  whenSeen($("#tree-overview"), function start() {
    if (treeSized && heatReady) requestAnimationFrame(() => treeOverview.play());
    else requestAnimationFrame(start);
  });
  card.rest();
  if (start !== "overview") return;
  heat.intro();
  if (calm()) return;

  const timers = [];
  const at = (ms, fn) => timers.push(window.setTimeout(fn, ms));
  let live = true;
  tourCancel = () => {
    if (!live) return;
    live = false;
    timers.forEach(clearTimeout);
    treeOverview.closePeek();
    riverOverview.highlight(null);
    for (const type of ["pointerdown", "keydown", "wheel", "touchstart"]) window.removeEventListener(type, tourCancel, true);
  };
  for (const type of ["pointerdown", "keydown", "wheel", "touchstart"]) window.addEventListener(type, tourCancel, { capture: true, passive: true });

  const days = DATA.days;
  const n = days.length;
  const lastMonthStart = n - dayDate(n - 1).getUTCDate();
  let recent = -1;
  for (let i = Math.max(0, lastMonthStart); i < n; i += 1) if (recent < 0 || days[i] > days[recent]) recent = i;
  const lastTag = DATA.tags.length ? DATA.tags[DATA.tags.length - 1][1] : -1;
  const stops = [recent, lastTag].filter((i) => i >= 0 && i !== DATA.busiest);

  at(1150, () => card.show(DATA.busiest));
  if (stops[0] !== undefined) at(3000, () => {
    card.show(stops[0]);
    heat.revealCell(stops[0]);
  });
  if (stops[1] !== undefined && stops[1] !== stops[0]) at(4300, () => card.show(stops[1]));
  at(5150, () => {
    if (!docked()) card.hide();
  });
  at(5500, () => {
    if (treeOverview.played) treeOverview.peekBiggest();
  });
  at(6900, () => {
    treeOverview.closePeek();
    riverOverview.highlight(0);
  });
  at(8100, () => {
    riverOverview.highlight(null);
    if (docked()) {
      card.show(DATA.busiest);
      heat.revealCell(DATA.busiest);
    } else {
      card.show(DATA.busiest);
    }
    live = false;
  });
}

opening();
