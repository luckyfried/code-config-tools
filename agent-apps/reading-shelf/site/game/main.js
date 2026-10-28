// The page: reads config.js, builds the library, and drives the 3D shelf (or the flat shelf where WebGL is missing)
// together with the header, the open book's details, the List, and the Stats.
import { createStore } from "./state.js";
import { createHud } from "./hud.js";
import { createReader, createList, createStats } from "./panels.js";
import { attachInput } from "./input.js";
import { shouldWelcome, runWelcome } from "./tour.js";
import { statusWords, longDate, num } from "./format.js";
import { pickTier, canWebGL, weakDevice } from "../scene/quality.js";

const config = window.__APP_CONFIG__ || { books: [] };
const store = createStore(config);
const app = document.getElementById("app");
const canvas = document.getElementById("scene");
const fine = matchMedia("(hover: hover) and (pointer: fine)");

const fontsReady = Promise.all([
  document.fonts.load('620 40px "Fraunces"'),
  document.fonts.load('italic 400 20px "Fraunces"'),
  document.fonts.load('600 20px "Instrument Sans"'),
]).catch(() => null);

function pageWords(b) {
  const owner = store.owner;
  const facts = [];
  if (b.pages && b.status !== "reading") facts.push(`${num(b.pages)} pages`);
  if (b.started && b.status !== "want") facts.push(`Started ${longDate(b.started)}`);
  return {
    exLibris: owner ? `From the shelf of ${owner}` : "From my shelf",
    status: statusWords(b),
    facts,
    noteHead: owner ? `${owner}’s note` : "My note",
    signature: owner ? `— ${owner}` : "",
    noNote: "No note yet.",
  };
}

let world = null;
let flat = null;
let focused = null;
let welcome = null;
let welcomeOpened = false;
let view = "shelf";
let pendingLayout = false;

function headerBottom() {
  const top = document.querySelector(".top");
  let bottom = 0;
  for (const child of top.children) bottom = Math.max(bottom, child.getBoundingClientRect().bottom);
  return bottom;
}

const narrow = () => innerWidth < 768 || (matchMedia("(pointer: coarse)").matches && innerHeight < 500);
const upright = () => narrow() && innerWidth < innerHeight;
const landscapePhone = () => matchMedia("(pointer: coarse)").matches && innerHeight < 500 && innerWidth >= 600;

function insets() {
  if (landscapePhone()) {
    // The row stepper keeps a clear column at the right.
    return { top: headerBottom() + 6, bottom: 14, right: 84, left: 0 };
  }
  if (upright()) {
    // The bay pager and the now-reading cards keep a clear band at the bottom.
    const dock = document.getElementById("dock");
    const space = innerHeight - dock.offsetTop;
    app.style.setProperty("--dock-space", `${Math.round(space)}px`);
    return { top: headerBottom() + 4, bottom: space + 6, left: 0, right: 0 };
  }
  if (narrow()) return { top: headerBottom() + 4, bottom: 6, left: 0, right: 0 };
  let bottom = 36;
  if (view === "stats") bottom = document.getElementById("stats").getBoundingClientRect().height + 40;
  return { top: headerBottom() + 8, bottom, left: 0, right: 0 };
}

function readRect() {
  const W = innerWidth;
  const H = innerHeight;
  const top = headerBottom();
  if (landscapePhone()) return { x: 12, y: top + 4, w: W - Math.min(380, W * 0.45) - 24, h: H - top - 10 };
  if (narrow()) {
    const el = document.getElementById("reader");
    const sheet = el.hidden ? Math.min(H * 0.45, 380) : el.offsetHeight;
    return { x: 10, y: top + 6, w: W - 20, h: H - sheet - top - 18 };
  }
  const panel = W >= 1600 ? 400 : 360;
  return { x: 32, y: top + 8, w: W - panel - 96, h: H - top - 40 };
}

const reader = createReader(store, {
  close: () => ctl.close(),
});

const thumb = (id, target) => {
  if (world) world.thumb(id, target);
  else if (flat) flat.thumb(id, target);
};

const ctl = {
  setView(next) {
    if (next === view && next !== "shelf") next = "shelf";
    if (world && world.reading) ctl.close();
    if (flat && flat.reading) ctl.close();
    view = next;
    hud.showView(view);
    hud.closeMenu();
    if (view === "list") list.open();
    else list.close();
    if (view === "stats") stats.open();
    else stats.close();
    ctl.focus(null);
    syncBays();
    if (world) requestAnimationFrame(() => world.resize());
  },
  setSort(id) {
    store.setSort(id);
  },
  open(id, { fromWelcome = false } = {}) {
    if (!fromWelcome) ctl.interrupt();
    if (view !== "shelf") {
      view = "shelf";
      hud.showView(view);
      list.close();
      stats.close();
    }
    const b = store.byId(id);
    if (!b) return;
    welcomeOpened = fromWelcome;
    hud.showTip(null);
    hud.hideHint();
    app.dataset.open = "true";
    reader.open(id);
    if (world) {
      const book = world.books.get(id);
      if (world.rowMode) world.rig.setRow(book.row);
      world.rig.lookAtX(book.rest.pos.x, true);
      focused = book;
      world.openBook(book);
    } else if (flat) flat.open(id);
  },
  close() {
    welcomeOpened = false;
    app.dataset.open = "false";
    reader.close();
    if (world) {
      world.closeBook();
      focused = null;
      if (pendingLayout) {
        pendingLayout = false;
        world.relayout(store.sorted());
      }
    } else if (flat) flat.close();
  },
  focus(id, { quiet = false } = {}) {
    if (!world) return;
    const book = id ? world.books.get(id) : null;
    if (focused === book) return;
    if (focused && focused !== world.reading) focused.setHover(false);
    focused = book;
    canvas.classList.toggle("is-pointing", Boolean(book));
    if (!book) {
      hud.showTip(null);
      return;
    }
    book.setHover(true);
    if (!quiet || !narrow()) {
      const b = book.data;
      const meta = fine.matches ? `${b.author}\n${statusWords(b)}` : `${b.author}\nTap again to open`;
      hud.showTip(b, meta);
    }
  },
  pointAt(x, y) {
    if (!world || world.reading || welcome?.live) return;
    const hit = x === null ? null : world.pick(x, y);
    ctl.focus(hit ? hit.id : null);
  },
  tap(x, y, type) {
    if (!world) return;
    const hit = world.pick(x, y);
    if (world.reading) {
      if (!hit || hit !== world.reading) ctl.close();
      return;
    }
    if (!hit) {
      ctl.focus(null);
      return;
    }
    if (type === "mouse" || focused === hit) ctl.open(hit.id);
    else ctl.focus(hit.id);
  },
  dragBy(dxPx) {
    if (!world || world.reading) return;
    const perPx = world.rig.visibleWidth() / innerWidth;
    world.rig.scrollBy(-dxPx * perPx);
  },
  fling(vx) {
    if (!world || world.reading) return;
    const perPx = world.rig.visibleWidth() / innerWidth;
    world.rig.scrollBy(-vx * 180 * perPx);
    world.rig.snapToBay();
  },
  swipeRow(dir) {
    if (world && world.rowMode && !world.reading) ctl.stepRow(dir);
  },
  stepRow(dir) {
    if (!world) return;
    ctl.interrupt();
    world.rig.setRow(world.rig.row + dir);
    ctl.focus(null);
    syncRows();
  },
  stepBay(dir) {
    if (!world || world.reading) return;
    ctl.interrupt();
    const windows = world.rig.windows();
    const i = bayIndex(world.rig.xTarget);
    world.rig.xTarget = windows[Math.max(0, Math.min(windows.length - 1, i + dir))];
    ctl.focus(null);
    syncBays();
  },
  walk(dx, dy) {
    if (!world || world.reading) return;
    const order = [...world.books.values()].sort((a, b) => a.row - b.row || a.rest.pos.x - b.rest.pos.x);
    if (!order.length) return;
    let next;
    if (!focused) {
      const x = world.rig.x;
      const pool = world.rowMode ? order.filter((b) => b.row === world.rig.row) : order;
      next = (pool.length ? pool : order).reduce((best, b) => (Math.abs(b.rest.pos.x - x) < Math.abs(best.rest.pos.x - x) ? b : best));
    } else if (dx) {
      const i = order.indexOf(focused);
      next = order[Math.max(0, Math.min(order.length - 1, i + dx))];
    } else {
      const row = focused.row + dy;
      const inRow = order.filter((b) => b.row === row);
      if (!inRow.length) return;
      next = inRow.reduce((best, b) => (Math.abs(b.rest.pos.x - focused.rest.pos.x) < Math.abs(best.rest.pos.x - focused.rest.pos.x) ? b : best));
    }
    if (world.rowMode && next.row !== world.rig.row) {
      world.rig.setRow(next.row);
      syncRows();
    }
    world.rig.lookAtX(next.rest.pos.x, true);
    ctl.focus(next.id);
  },
  openFocused() {
    if (focused && !world?.reading) ctl.open(focused.id);
  },
  escape() {
    if (hud.menuOpen()) hud.closeMenu();
    else if ((world && world.reading) || (flat && flat.reading)) ctl.close();
    else if (view !== "shelf") ctl.setView("shelf");
    else ctl.focus(null);
  },
  parallax(nx, ny) {
    if (world) world.rig.pointer(nx, ny);
  },
  interrupt() {
    if (welcome && welcome.live) {
      welcome.stop();
      if (welcomeOpened) ctl.close();
      ctl.focus(null);
    }
  },
  themeChanged() {
    if (world) world.applyTheme();
    if (flat) flat.applyTheme();
    hud.renderNow(thumb);
    if (list.isOpen) list.render();
  },
  say(text) {
    hud.showHint(text);
  },
  rowMode: () => Boolean(world && world.rowMode),
};

const hud = createHud(store, ctl);
const list = createList(store, ctl, thumb);
const stats = createStats(store, ctl);

function bayIndex(x) {
  const windows = world.rig.windows();
  return windows.indexOf(world.rig.nearestWindow(x));
}

let shownBay = -1;
function syncBays() {
  if (!world) {
    hud.renderBays(0, 0, 0, false);
    return;
  }
  const count = world.rig.windows().length;
  const current = bayIndex(world.rig.xTarget);
  const elsewhere = [...world.books.values()].filter((b) => bayIndex(b.rest.pos.x) !== current).length;
  shownBay = current;
  hud.renderBays(count, current, elsewhere, world.columnMode && view === "shelf");
}

function syncRows() {
  if (!world) return;
  hud.renderRows(3, world.rig.row, world.rowMode && view === "shelf");
}

store.on((type, detail) => {
  if (type === "sort") {
    hud.renderMenu();
    if (world) world.relayout(store.sorted());
    if (flat) flat.layout();
    if (list.isOpen) list.render();
    syncBays();
    return;
  }
  hud.tally();
  hud.renderNow(thumb);
  reader.refresh();
  if (list.isOpen) list.render();
  if (stats.isOpen) stats.render();
  if (world) {
    const book = detail.id ? world.books.get(detail.id) : null;
    if (book) world.refreshPages(book);
    else for (const b of world.books.values()) world.refreshPages(b);
    if (detail.statusChanged) {
      if (world.reading) pendingLayout = true;
      else world.relayout(store.sorted());
    }
  }
  if (flat && detail.statusChanged) flat.layout();
});

function chooseWelcomeBook() {
  const half = world.rig.visibleWidth() / 2 - 0.06;
  const visible = (b) => {
    const o = world.books.get(b.id);
    return Math.abs(o.rest.pos.x - world.rig.xTarget) < half && (!world.rowMode || o.row === world.rig.row);
  };
  const pool = store.books.filter((b) => b.status !== "reading" && visible(b));
  const score = (b) => (b.note ? 4 : 0) + (world.books.get(b.id).image ? 3 : 0) + b.rating * 0.5 + (world.books.get(b.id).kind === "stand" ? 1 : 0);
  return pool.sort((a, b) => score(b) - score(a))[0] || null;
}

async function startShelf() {
  const tier = pickTier();
  const { createWorld } = await import("../scene/world.js");
  world = await createWorld({
    canvas,
    tier,
    shelf: config.shelf,
    books: store.books,
    openLibrary: config.openLibrary === true,
    readRect,
    insets,
    text: pageWords,
  });
  await fontsReady;
  world.paintAll();
  world.relayout(store.sorted(), { entrance: true });
  hud.renderNow(thumb);
  hud.renderBays(2, 0, 0, upright());
  world.resize();
  const [lo] = world.rig.range();
  world.rig.xTarget = world.rowMode ? lo : 0;
  world.rig.clampTargets();
  world.rig.snapToBay();
  world.rig.snap();
  world.rig.startIntro(performance.now() / 1000);
  world.onCover = () => {
    hud.renderNow(thumb);
    if (list.isOpen) list.render();
  };
  world.onFrame = () => {
    if (bayIndex(world.rig.xTarget) !== shownBay) syncBays();
    if (focused && !world.reading && !narrow()) {
      const p = world.screenOf(focused);
      hud.placeTip(p.x, p.y);
    }
  };
  world.start();
  app.dataset.ready = "true";
  attachInput(canvas, ctl);
  syncRows();
  syncBays();
  addEventListener("resize", () => {
    hud.renderBays(2, 0, 0, upright());
    world.resize();
    syncRows();
    syncBays();
  });

  const hintText = fine.matches ? "Point at a spine to pull it out. Click to open it." : "Swipe along the shelf. Tap a book to pull it out.";
  const pick = shouldWelcome() ? chooseWelcomeBook() : null;
  if (pick) {
    welcome = runWelcome(ctl, pick.id, {
      onEnd: (interrupted) => {
        if (!interrupted) hud.showHint(hintText);
      },
    });
  } else {
    setTimeout(() => hud.showHint(hintText), 1600);
  }
}

async function startFlat() {
  app.classList.add("is-flat");
  canvas.hidden = true;
  const { createFlat } = await import("./flat.js");
  await fontsReady;
  flat = createFlat(store, ctl);
  hud.renderNow(thumb);
}

const wantFlat = !canWebGL() || weakDevice();
(wantFlat ? startFlat() : startShelf()).catch((err) => {
  console.warn("The 3D shelf could not start; showing the flat shelf.", err);
  if (world) world.stop();
  world = null;
  startFlat();
});
