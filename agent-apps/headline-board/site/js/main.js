// Headline Board: lays the board out for the screen, fills it with headlines, and runs everything on one
// requestAnimationFrame clock: the flaps, the page cycle, the clock, and the progress bar.

import { Flaps, Tile, fit } from "./flaps.js";
import { PaintedBoard, PaintedTile } from "./canvas.js";
import { Clack } from "./sound.js";
import { fahrenheit, interleave, keepFresh, loadFeed, sky } from "./feed.js";

const config = {
  title: "Headline Board",
  sources: [],
  rows: 6,
  secondsPerFlip: 8,
  location: null,
  ...(window.__APP_CONFIG__ || {}),
};

const KEY = "headline-board:";
const store = {
  get(name, fallback) {
    try {
      const value = localStorage.getItem(KEY + name);
      return value === null ? fallback : value;
    } catch {
      return fallback;
    }
  },
  set(name, value) {
    try {
      localStorage.setItem(KEY + name, String(value));
    } catch {
      // Storage can be off in a private window; the choice lasts until the page closes.
    }
  },
};

const $ = (id) => document.getElementById(id);
const housing = $("housing");
const board = $("board");
const rowsEl = $("rows");
const clockEl = $("clock");
const weatherEl = $("weather");
const statusMain = $("status-main");
const statusMore = $("status-more");
const pageEl = $("page");
const progressEl = $("progress");
const pauseButton = $("pause");
const soundButton = $("sound");
const sheet = $("sheet");

const coarse = matchMedia("(pointer: coarse)").matches;
const weak = coarse && ((navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 2);
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const demo = new URLSearchParams(location.search).get("demo") === "1";

const clack = new Clack();
const flaps = new Flaps({ onTurn: (turned, landed) => clack.play(turned, landed), light: coarse });
flaps.still = reduced.matches;
// A touch screen draws the board's flaps on one canvas; a desktop turns each module in the page in 3D.
const painted = coarse ? new PaintedBoard(rowsEl) : null;
housing.classList.toggle("painted", Boolean(painted));

const state = {
  feed: null,
  items: [],
  text: [],
  pages: [],
  page: 0,
  shape: null,
  rows: [],
  clockTiles: [],
  clockText: "",
  weatherTiles: [],
  weatherText: "",
  seconds: Number(store.get("seconds", config.secondsPerFlip)) || config.secondsPerFlip,
  paused: false,
  pageStart: 0,
  pausedAt: 0,
  opened: false,
};

// Text ----------------------------------------------------------------------------------------------------------------

function upper(text) {
  return (text || "")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[‘’‚‛′`´]/g, "'")
    .replace(/[“”„‟″«»]/g, '"')
    .replace(/[–—―−‐]/g, "-")
    .replace(/ß/g, "ss")
    .replace(/[æÆ]/g, "ae")
    .replace(/[øØ]/g, "o")
    .replace(/[œŒ]/g, "oe")
    .toUpperCase()
    .split("")
    .map(fit)
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

// Breaks a headline into lines of `cols` letters at word ends; one that runs past the last line ends in an ellipsis.
function wrap(text, cols, lines) {
  const out = [];
  let line = "";
  for (let word of text.split(" ").filter(Boolean)) {
    while (word.length > cols) {
      if (line) out.push(line);
      line = "";
      out.push(word.slice(0, cols));
      word = word.slice(cols);
    }
    if (!word) continue;
    if (!line) line = word;
    else if (line.length + 1 + word.length <= cols) line += ` ${word}`;
    else {
      out.push(line);
      line = word;
    }
  }
  if (line) out.push(line);
  if (out.length > lines) {
    let last = out[lines - 1];
    if (last.length < cols) last += "…";
    else {
      const cut = last.lastIndexOf(" ", cols - 2);
      last = `${cut > 0 ? last.slice(0, cut) : last.slice(0, cols - 1)}…`;
    }
    out.length = lines;
    out[lines - 1] = last;
  }
  return out;
}

function age(item, now) {
  if (item.label) return item.label.startsWith("TOP") ? `#${item.label.slice(3)}` : item.label;
  let minutes = null;
  if (typeof item.age === "number") minutes = item.age;
  else if (item.time) minutes = (now - Date.parse(item.time)) / 60000;
  if (minutes === null || Number.isNaN(minutes)) return "";
  minutes = Math.max(0, minutes);
  if (minutes < 1) return "NOW";
  if (minutes < 60) return `${Math.floor(minutes)}M`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}H`;
  return `${Math.floor(minutes / 1440)}D`;
}

function list(names) {
  if (names.length < 3) return names.join(" and ");
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

// A steady spread of numbers per module, so the cascade has texture but the same board always moves the same way.
function hash(a, b) {
  let value = (a * 374761393 + b * 668265263) | 0;
  value = (value ^ (value >>> 13)) * 1274126177;
  return ((value ^ (value >>> 16)) >>> 0) / 4294967296;
}

// Layout --------------------------------------------------------------------------------------------------------------
// The board is one fixed grid of lines of modules, sized to the screen. Each headline takes exactly the lines it needs
// (on a narrow board, one more above them for its tag and age), and a page is as many whole headlines as the grid holds.

// The lines a headline needs at `cols` letters across, before its tag line on a narrow board.
function needed(item, cols) {
  return Math.max(1, wrap(upper(item.title), cols, Infinity).length);
}

function readShape() {
  const style = getComputedStyle(rowsEl);
  const side = style.getPropertyValue("--mode").trim() === "side";
  const cols = parseInt(style.getPropertyValue("--cols"), 10) || 18;
  const tagCols = parseInt(style.getPropertyValue("--tag-cols"), 10) || 4;
  const timeCols = parseInt(style.getPropertyValue("--time-cols"), 10) || 4;
  const tgap = parseFloat(style.getPropertyValue("--tgap")) || 2;
  const lgapMin = parseFloat(style.getPropertyValue("--lgap")) || 3;
  const width = rowsEl.clientWidth;
  const height = rowsEl.clientHeight;
  const units = side ? tagCols + 1 + cols + 1 + timeCols : cols;
  const tw = Math.floor(((width - (units - 1) * tgap) / units) * 100) / 100;
  const meta = side ? 0 : 1;
  // The modules are sized so the grid holds about `rows` of today's headlines, each 1.25 to 1.6 times as tall as wide.
  const target = Math.min(12, Math.max(2, weak ? Math.min(4, config.rows) : config.rows));
  const sample = state.items.slice(0, 40);
  const per = meta + (sample.length ? sample.reduce((sum, item) => sum + needed(item, cols), 0) / sample.length : 2);
  const lgap = Math.max(lgapMin, Math.round(tw * 0.24));
  const fill = (height + lgap) / (target * per) - lgap;
  const lines = Math.max(meta + 1, Math.floor((height + lgap) / (Math.min(tw * 1.6, Math.max(tw * 1.25, fill)) + lgap)));
  const th = Math.floor(Math.min(tw * 1.6, (height + lgap) / lines - lgap) * 100) / 100;
  const top = Math.max(0, Math.floor((height - (lines * th + (lines - 1) * lgap)) / 2));
  return { side, cols, tagCols, timeCols, units, tw, th, tgap, lgap, lines, top, meta, width, height };
}

function sameShape(a, b) {
  return a && b && ["side", "cols", "tagCols", "timeCols", "lines", "tw", "th", "top"].every((key) => a[key] === b[key]);
}

// The modules of the grid, made once for a shape and kept: a page turn sends each one from the letter it shows.
const grid = new Map();

function module(line, col) {
  const key = line * 256 + col;
  let tile = grid.get(key);
  if (!tile) {
    tile = painted ? new PaintedTile(painted) : new Tile();
    tile.col = col;
    grid.set(key, tile);
  }
  return tile;
}

function setGrid(shape) {
  for (const tile of grid.values()) flaps.moving.delete(tile);
  grid.clear();
  rowsEl.style.setProperty("--tw", `${shape.tw}px`);
  rowsEl.style.setProperty("--th", `${shape.th}px`);
  rowsEl.style.setProperty("--lgap", `${shape.lgap}px`);
  rowsEl.style.setProperty("--grid-top", `${shape.top}px`);
  rowsEl.style.setProperty("--line-w", `${shape.units * shape.tw + (shape.units - 1) * shape.tgap}px`);
  rowsEl.style.setProperty("--tr", `${Math.max(2, Math.min(5, Math.round(shape.tw * 0.13)))}px`);
  rowsEl.replaceChildren();
  if (painted) painted.mount();
}

// Lays out one page's rows on the grid, each with the lines of its headline.
function buildRows(page, shape) {
  const fragment = document.createDocumentFragment();
  const rows = [];
  const used = new Set();
  // Lines the page leaves over are split above and below it, a whole line at a time, so every module keeps its place.
  let at = Math.floor((shape.lines - page.lines) / 2);
  for (const index of page.items) {
    const item = state.items[index];
    const text = state.text[index];
    const link = document.createElement("a");
    link.className = "row";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    const row = { el: link, tiles: [], item, text };
    const total = text.length + shape.meta;
    for (let line = 0; line < total; line += 1, at += 1) {
      const lineEl = document.createElement("span");
      lineEl.className = "line";
      lineEl.setAttribute("aria-hidden", "true");
      const add = (col, role, slot) => {
        const tile = module(at, col);
        tile.role = role;
        tile.index = slot;
        tile.line = line;
        row.tiles.push(tile);
        used.add(tile);
        if (painted) return;
        tile.el.style.setProperty("--c", col);
        lineEl.append(tile.el);
      };
      if (shape.side) {
        const textAt = shape.tagCols + 1;
        const timeAt = textAt + shape.cols + 1;
        if (line === 0) for (let k = 0; k < shape.tagCols; k += 1) add(k, "tag", k);
        for (let k = 0; k < shape.cols; k += 1) add(textAt + k, "text", k);
        if (line === 0) for (let k = 0; k < shape.timeCols; k += 1) add(timeAt + k, "time", k);
      } else if (line === 0) {
        for (let k = 0; k < shape.tagCols; k += 1) add(k, "tag", k);
        for (let k = 0; k < shape.timeCols; k += 1) add(shape.cols - shape.timeCols + k, "time", k);
      } else {
        for (let k = 0; k < shape.cols; k += 1) add(k, "text", k);
      }
      link.append(lineEl);
    }
    label(row, item);
    rows.push(row);
    fragment.append(link);
  }
  // A module this page leaves out goes blank, so a later page that needs it again turns it from blank.
  for (const tile of grid.values()) {
    if (used.has(tile)) continue;
    flaps.moving.delete(tile);
    tile.snap(" ");
  }
  if (painted) rowsEl.replaceChildren(painted.canvas, painted.probe, fragment);
  else rowsEl.replaceChildren(fragment);
  painted?.layout(rows, shape);
  return rows;
}

// What each module of a row should show.
function compose(row, shape, now) {
  const { item, text } = row;
  const tag = upper(item.tag).slice(0, shape.tagCols);
  const time = age(item, now).slice(0, shape.timeCols).padStart(shape.timeCols, " ");
  return row.tiles.map((tile) => {
    if (tile.role === "tag") return { letter: tag[tile.index] || " ", tone: item.tone };
    if (tile.role === "time") return { letter: time[tile.index] || " ", tone: 0 };
    return { letter: (text[tile.line - shape.meta] || "")[tile.index] || " ", tone: 0 };
  });
}

function label(row, item) {
  row.el.href = item.url;
  row.el.setAttribute("aria-label", `${item.source}: ${item.title}`);
}

// Pages ---------------------------------------------------------------------------------------------------------------
// The headlines go onto pages in order, each page as many whole headlines as fill the grid; when the next one does not
// fit, a shorter one from just behind it takes the space and it leads the next page. The last page is topped up from
// the first headlines, so no page is mostly blank.

const AHEAD = 12;

function paginate(shape) {
  const room = shape.lines;
  state.text = state.items.map((item) => wrap(upper(item.title), shape.cols, room - shape.meta));
  const need = state.text.map((text) => Math.max(1, text.length) + shape.meta);
  const rest = state.items.map((item, index) => index);
  const seen = new Set();
  const pages = [];
  const take = (page, pool, from, used) => {
    for (let k = from, skipped = 0; k < pool.length && skipped < AHEAD; ) {
      if (!page.includes(pool[k]) && used + need[pool[k]] <= room) {
        used += need[pool[k]];
        page.push(pool === rest ? rest.splice(k, 1)[0] : pool[k++]);
      } else {
        k += 1;
        skipped += 1;
      }
    }
    return used;
  };
  while (rest.length) {
    const page = [];
    let used = take(page, rest, 0, 0);
    if (!rest.length && pages.length) used = take(page, state.items.map((item, index) => index), 0, used);
    for (const index of page) seen.add(index);
    pages.push({ items: page, lines: used, seen: seen.size });
  }
  return pages;
}

function showCount() {
  const count = state.items.length;
  const shown = state.pages[state.page]?.seen || 0;
  pageEl.textContent = state.paused ? `Paused on ${shown} of ${count}` : `${shown} of ${count}`;
}

// Sends one row to its headline: the modules that change turn in a cascade across each line.
function turnRow(row, r, { at, opening = false, instant = false, wall = Date.now() }) {
  const targets = compose(row, state.shape, wall);
  if (instant || flaps.still) {
    row.tiles.forEach((tile, index) => tile.snap(targets[index].letter, targets[index].tone));
    return;
  }
  const lineDelay = opening ? 40 : 55;
  const colDelay = opening ? 8 : 13;
  row.tiles.forEach((tile, index) => {
    const spread = hash(r * 97 + tile.line, tile.col);
    flaps.send(tile, targets[index].letter, {
      at: at + tile.line * lineDelay + tile.col * colDelay + spread * 24,
      spins: flaps.light ? 1 + Math.floor(spread * 3) : 2 + Math.floor(spread * 4),
      force: opening && targets[index].letter !== " ",
      tone: targets[index].tone,
    });
  });
}

// Turns the board to page `index`: the rows turn one after another down the board. Reduced motion fades the page.
function showPage(index, { opening = false, instant = false } = {}) {
  const count = state.pages.length;
  if (!count) return;
  state.page = ((index % count) + count) % count;
  const page = state.pages[state.page];
  const change = () => {
    const now = performance.now();
    const wall = Date.now();
    state.rows = buildRows(page, state.shape);
    state.rows.forEach((row, r) => turnRow(row, r, { at: now + 30 + r * (opening ? 80 : 110), opening, instant, wall }));
  };
  if (flaps.still && !instant) fade(rowsEl, change, 0);
  else change();
  state.pageStart = performance.now();
  showCount();
}

// Reduced motion: the page fades out, changes, and fades back in.
function fade(element, change, delay) {
  setTimeout(() => {
    element.classList.add("fading");
    setTimeout(() => {
      change();
      element.classList.remove("fading");
    }, 200);
  }, delay);
}

function step(direction) {
  if (!state.pages.length) return;
  showPage(state.page + direction);
}

function setPaused(paused) {
  const now = performance.now();
  if (paused === state.paused) return;
  state.paused = paused;
  if (paused) state.pausedAt = now;
  else state.pageStart += now - state.pausedAt;
  housing.classList.toggle("paused", paused);
  pauseButton.setAttribute("aria-pressed", String(paused));
  pauseButton.setAttribute("aria-label", paused ? "Start the board" : "Pause the board");
  showCount();
}

// The clock and the weather line ----------------------------------------------------------------------------------

const hour12 = new Intl.DateTimeFormat(undefined, { hour: "numeric" }).resolvedOptions().hourCycle?.startsWith("h1");

function buildClock() {
  const make = (kind = "") => {
    const tile = new Tile(kind);
    state.clockTiles.push(tile);
    return tile.el;
  };
  state.clockTiles = [];
  const fragment = document.createDocumentFragment();
  for (let index = 0; index < 5; index += 1) fragment.append(make());
  const small = document.createElement("span");
  small.className = "cs";
  const seconds = document.createElement("span");
  seconds.className = "cl";
  seconds.append(make("ampm"), make("ampm"));
  small.append(seconds);
  if (hour12) {
    const half = document.createElement("span");
    half.className = "cl";
    half.append(make("ampm"), make("ampm"));
    small.append(half);
  }
  fragment.append(small);
  clockEl.replaceChildren(fragment);
  state.clockText = "";
}

// "HH:MM", then the seconds, then AM or PM where the clock is read in twelve hours.
function clockText(date) {
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  if (!hour12) return `${String(date.getHours()).padStart(2, "0")}:${minutes}${seconds}`;
  const hours = date.getHours() % 12 || 12;
  return `${String(hours).padStart(2, " ")}:${minutes}${seconds}${date.getHours() < 12 ? "AM" : "PM"}`;
}

function tickClock(now, opening = false) {
  const date = new Date();
  const text = clockText(date);
  if (text === state.clockText) return;
  const first = !state.clockText;
  const before = state.clockText;
  state.clockText = text;
  $("date").textContent = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(date);
  clockEl.setAttribute("aria-label", `The time is ${new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date)}`);
  state.clockTiles.forEach((tile, index) => {
    if (first && !opening) tile.snap(text[index]);
    // The opening lands every module of the clock within a second.
    else if (opening) flaps.send(tile, text[index], { at: now + 20 + index * 35, spins: 2 + (index % 3), force: true });
    else if (before[index] !== text[index]) flaps.send(tile, text[index], { at: now + (index === 6 ? 40 : 0), spins: index >= 5 ? 1 : 4 });
  });
}

function weatherLines(lines, width) {
  const weather = state.feed?.weather;
  if (!weather || typeof weather.temp !== "number") return [];
  const toF = fahrenheit();
  const degrees = (value) => `${Math.round(toF ? value * 1.8 + 32 : value)}°`;
  const words = sky(weather.code, weather.day);
  const short = words.replace("PARTLY CLOUDY", "PT CLOUDY").replace("MOSTLY ", "").replace("HEAVY", "HVY");
  const place = upper(weather.place || config.location?.name || "");
  const temp = degrees(weather.temp);
  const range = typeof weather.high === "number" ? `H${degrees(weather.high)} L${degrees(weather.low)}` : "";
  if (lines >= 2) {
    const round = (value) => Math.round(toF ? value * 1.8 + 32 : value);
    const pairs = typeof weather.high === "number"
      ? [`${temp} H${round(weather.high)} L${round(weather.low)}`, `${temp} ${round(weather.high)}/${round(weather.low)}`, temp]
      : [temp];
    const top = pairs.find((line) => line.length <= width) || temp;
    return [words.length <= width ? words : short, top].map((line) => line.slice(0, width));
  }
  const options = [
    [place, temp, words, range],
    [place, temp, short, range],
    [temp, words, range],
    [temp, short, range],
    [temp, short],
  ];
  for (const parts of options) {
    const line = parts.filter(Boolean).join(" ");
    if (line.length <= width) return [line];
  }
  return [temp];
}

function buildWeather(opening = false) {
  const cell = weatherEl.parentElement;
  const style = getComputedStyle(cell);
  const tw = parseFloat(style.getPropertyValue("--tw")) || 14;
  const tgap = parseFloat(style.getPropertyValue("--tgap")) || 2;
  const lines = parseInt(style.getPropertyValue("--wx-lines"), 10) || 1;
  const room = cell.clientWidth - 10;
  const width = Math.max(0, Math.min(30, Math.floor((room + tgap) / (tw + tgap))));
  const text = weatherLines(lines, width);
  const columns = Math.max(0, ...text.map((line) => line.length));
  const key = `${columns}|${text.length}`;
  if (state.weatherKey !== key) {
    const fragment = document.createDocumentFragment();
    state.weatherTiles = [];
    for (let line = 0; line < text.length; line += 1) {
      const lineEl = document.createElement("div");
      lineEl.className = "wl";
      for (let col = 0; col < columns; col += 1) {
        const tile = new Tile();
        tile.line = line;
        tile.col = col;
        state.weatherTiles.push(tile);
        lineEl.append(tile.el);
      }
      fragment.append(lineEl);
    }
    weatherEl.replaceChildren(fragment);
    state.weatherKey = key;
    state.weatherText = "";
  }
  const joined = text.map((line) => line.padEnd(columns, " ")).join("");
  if (joined === state.weatherText) return;
  const animate = state.weatherText !== "" || opening;
  state.weatherText = joined;
  const now = performance.now();
  state.weatherTiles.forEach((tile, index) => {
    if (!animate) tile.snap(joined[index]);
    // The line lands within a second of the opening; a blank slot stays blank rather than spinning round the drum.
    else flaps.send(tile, joined[index], { at: now + 40 + tile.line * 50 + tile.col * 8, spins: 2 + (index % 2), force: opening && joined[index] !== " " });
  });
}

// Status --------------------------------------------------------------------------------------------------------------

function showStatus() {
  const feed = state.feed;
  if (!feed) return;
  if (feed.sample) {
    statusMain.textContent = "Sample headlines";
    statusMore.textContent = "";
    return;
  }
  const updated = new Date(feed.updated?.replace(/Z$/, ":00Z") || Date.now());
  const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(updated);
  const today = new Date().toDateString() === updated.toDateString();
  const day = today ? "" : `${new Intl.DateTimeFormat(undefined, { weekday: "long" }).format(updated)} `;
  statusMain.textContent = `Updated ${day}${time}`;
  const names = (feed.sources || []).filter((source) => source.items?.length).map((source) => source.name);
  statusMore.textContent = names.length ? ` from ${list(names)}` : "";
}

// The clock -------------------------------------------------------------------------------------------------------

let lastClockCheck = 0;

function frame(now) {
  if (state.shape && state.pages.length) {
    const duration = state.seconds * 1000;
    const elapsed = (state.paused ? state.pausedAt : now) - state.pageStart;
    if (!state.paused && !sheet.open && state.pages.length > 1 && elapsed >= duration) showPage(state.page + 1);
    progressEl.style.setProperty("transform", `scaleX(${Math.min(1, Math.max(0, elapsed / duration)).toFixed(4)})`);
  }
  if (now - lastClockCheck > 200) {
    lastClockCheck = now;
    if (state.opened) tickClock(now);
  }
  flaps.frame(now);
  painted?.draw(now);
  requestAnimationFrame(frame);
}

// Fitting the board to the screen -----------------------------------------------------------------------------------

function fitBoard({ opening = false } = {}) {
  const shape = readShape();
  const same = sameShape(shape, state.shape);
  if (same && !opening) {
    painted?.layout(state.rows, shape);
    buildWeather();
    return;
  }
  // The page that shows again on the new grid is the one holding the headline at the top of the board.
  const first = state.pages[state.page]?.items[0] ?? 0;
  state.shape = shape;
  setGrid(shape);
  state.pages = paginate(shape);
  showPage(Math.max(0, state.pages.findIndex((page) => page.items.includes(first))), { opening, instant: !opening });
  buildWeather(opening);
}

let resizeTimer = 0;
const watcher = new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.opened) fitBoard();
  }, 120);
});

// Settings --------------------------------------------------------------------------------------------------------

function fillSlider(input) {
  const share = (Number(input.value) - Number(input.min)) / (Number(input.max) - Number(input.min));
  input.style.setProperty("--fill", `${(share * 100).toFixed(1)}%`);
}

function bindSettings() {
  const speed = $("speed");
  const speedOut = $("speed-out");
  const soundOn = $("sound-on");
  const volume = $("volume");
  const volumeOut = $("volume-out");

  const soundState = () => {
    soundButton.setAttribute("aria-pressed", String(clack.on));
    soundButton.setAttribute("aria-label", clack.on ? "Turn the clack off" : "Turn the clack on");
    soundOn.checked = clack.on;
    volume.disabled = !clack.on;
  };
  const setSound = (on) => {
    clack.on = on;
    store.set("sound", on ? "on" : "off");
    if (on) clack.wake();
    soundState();
  };

  speed.value = String(state.seconds);
  speedOut.textContent = `${state.seconds} seconds`;
  fillSlider(speed);
  speed.addEventListener("input", () => {
    state.seconds = Number(speed.value);
    speedOut.textContent = `${state.seconds} seconds`;
    store.set("seconds", state.seconds);
    fillSlider(speed);
  });

  clack.on = store.get("sound", weak ? "off" : "on") === "on";
  clack.setVolume(Number(store.get("volume", 60)) / 100);
  volume.value = String(Math.round(clack.volume * 100));
  volumeOut.textContent = `${volume.value}%`;
  fillSlider(volume);
  soundState();
  soundOn.addEventListener("change", () => setSound(soundOn.checked));
  volume.addEventListener("input", () => {
    clack.setVolume(Number(volume.value) / 100);
    volumeOut.textContent = `${volume.value}%`;
    store.set("volume", volume.value);
    fillSlider(volume);
  });
  soundButton.addEventListener("click", () => setSound(!clack.on));

  const scheme = store.get("scheme", "auto");
  for (const radio of document.querySelectorAll('input[name="scheme"]')) {
    radio.checked = radio.value === scheme;
    radio.addEventListener("change", () => {
      if (!radio.checked) return;
      store.set("scheme", radio.value);
      if (radio.value === "auto") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", radio.value);
    });
  }

  $("settings-open").addEventListener("click", () => sheet.showModal());
  sheet.addEventListener("click", (event) => {
    if (event.target === sheet) sheet.close();
  });
  pauseButton.addEventListener("click", () => setPaused(!state.paused));
}

function bindKeys() {
  document.addEventListener("keydown", (event) => {
    if (sheet.open || event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target;
    const typing = target instanceof HTMLInputElement || target instanceof HTMLButtonElement;
    if (event.code === "Space" && !typing) {
      event.preventDefault();
      setPaused(!state.paused);
    } else if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      step(1);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      step(-1);
    }
  });
  // A browser lets a page make sound only after a touch or a key.
  const wake = () => {
    if (clack.on) clack.wake();
  };
  document.addEventListener("pointerdown", wake, { passive: true });
  document.addEventListener("keydown", wake);
  document.addEventListener("visibilitychange", () => housing.classList.toggle("hidden", document.hidden));
  // The canvas reads its colors from the theme, so a change of look or of the font draws the flaps again.
  if (painted) {
    const restyle = () => painted.restyle();
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", restyle);
    new MutationObserver(restyle).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    document.fonts.addEventListener("loadingdone", restyle);
  }
  reduced.addEventListener("change", () => {
    flaps.still = reduced.matches;
  });
}

// Start -----------------------------------------------------------------------------------------------------------

async function start() {
  $("title").textContent = config.title;
  document.title = config.title;
  buildClock();
  bindSettings();
  bindKeys();
  painted?.mount();
  requestAnimationFrame(frame);

  // The canvas draws its letters in the board's font, so a touch screen waits for it (it is preloaded) before the opening.
  const font = painted ? document.fonts.load('760 16px "JetBrains Mono"').catch(() => null) : null;
  [state.feed] = await Promise.all([loadFeed({ demo }), font]);
  state.items = interleave(state.feed, config.sources);
  showStatus();
  state.opened = true;
  const now = performance.now();
  tickClock(now, !flaps.still);
  fitBoard({ opening: true });
  watcher.observe(board);
  watcher.observe(weatherEl.parentElement);

  keepFresh(config, state.feed, (feed) => {
    state.feed = feed;
    state.items = interleave(feed, config.sources);
    // The fresh headlines take the next pages; the page up now stays until its turn is over.
    state.pages = paginate(state.shape);
    state.page = Math.max(0, Math.min(state.page, state.pages.length - 1));
    showStatus();
    showCount();
    buildWeather();
  });
}

start();
