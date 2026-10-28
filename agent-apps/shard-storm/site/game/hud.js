// The HUD and the screens are HTML styled by the theme; this module only writes text, classes, and live values.
import { easeOutCubic } from "./ease.js";

// Grouped by hand: the HUD formats every frame, and toLocaleString costs a phone a slice of each one.
const fmt = (n) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
export const clock = (s) => {
  const t = Math.max(0, Math.ceil(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
};

/** Fills `el` with one span per letter, kept whole per word, each carrying its order as --i. */
function letters(el, text) {
  el.textContent = "";
  let i = 0;
  text.split(" ").forEach((word, w) => {
    if (w > 0) el.append(" ");
    const span = document.createElement("span");
    span.className = "word";
    for (const ch of word) {
      const c = document.createElement("span");
      c.className = "ch";
      c.textContent = ch;
      c.style.setProperty("--i", String(i++));
      span.append(c);
    }
    el.append(span);
  });
}

// The per-graze pops run on the Web Animations API, so a streak of grazes never forces a layout to restart them.
const still = matchMedia("(prefers-reduced-motion: reduce)");
const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const SQUASH = [
  { transform: "translateY(-0.08em) scale(0.86, 1.28)" },
  { transform: "scale(1.12, 0.92)", offset: 0.45 },
  { transform: "none" },
];
const BUMP = [{ transform: "scale(1.35)" }, { transform: "none" }];
// One animation per element at a time: a new one cancels the last, so each runs on the compositor; two overlapping on
// one element would both fall back to the main thread and cost every frame they run.
const playing = new WeakMap();
function play(el, keyframes, options) {
  playing.get(el)?.cancel();
  playing.set(el, el.animate(keyframes, options));
}
const rise = (x, y) => [
  { opacity: 0, transform: `translate(calc(${x} - 50%), calc(${y} - 8px)) scale(0.6)` },
  { opacity: 1, transform: `translate(calc(${x} - 50%), calc(${y} - 22px)) scale(1.12)`, offset: 0.18 },
  { opacity: 1, offset: 0.5 },
  { opacity: 0, transform: `translate(calc(${x} - 50%), calc(${y} - 46px)) scale(0.96)`, offset: 0.85 },
  { opacity: 0, transform: `translate(calc(${x} - 50%), calc(${y} - 46px)) scale(0.96)` },
];

export function createHud(root) {
  const bound = new Map();
  const $ = (name) => {
    if (!bound.has(name)) bound.set(name, root.querySelector(`[data-bind="${name}"]`));
    return bound.get(name);
  };
  const callout = root.querySelector(".callout");
  const multFill = root.querySelector(".hud-mult-fill");
  const progress = root.querySelector(".hud-progress-fill");
  const clockBox = root.querySelector(".hud-clock");
  const newBest = $("new-best");
  const toastEl = $("toast");
  const streakBox = root.querySelector(".hud-streak");
  const streakN = root.querySelector(".hud-streak-n");
  const multX = root.querySelector(".hud-mult-x");
  const popLayer = root.querySelector(".pops");
  const pops = Array.from({ length: 8 }, () => {
    const el = document.createElement("span");
    el.className = "pop";
    popLayer.append(el);
    return el;
  });
  let popNext = 0;
  let popAt = 0;
  let lastStreak = 0;
  const shown = {};
  let toastTimer = 0;
  let countFrom = 0;
  let countTo = 0;
  let countStart = 0;
  // Each rewrite of the run's numbers costs the page a style, layout, and paint pass, so a slower tier rewrites them
  // every few frames instead of every frame; a graze still shows on its own frame.
  let cadence = 1;
  let beat = 0;

  const write = (name, value) => {
    if (shown[name] === value) return;
    shown[name] = value;
    // The text node is rewritten in place rather than replaced, so a number ticking every frame leaves no garbage.
    const el = $(name);
    if (el.firstChild && el.firstChild.nodeType === 3 && el.childNodes.length === 1) el.firstChild.data = value;
    else el.textContent = value;
  };

  return {
    setScreen(name) {
      root.dataset.screen = name;
    },
    get screen() {
      return root.dataset.screen;
    },
    setTitle(title) {
      letters($("title"), title);
      $("demo-title").textContent = title;
    },
    setPlayer(name, best, streak) {
      $("player").textContent = name;
      write("best", fmt(best));
      write("best-streak", fmt(streak));
    },
    callout(kicker, word) {
      callout.classList.remove("is-on");
      $("callout-kicker").textContent = kicker;
      letters($("callout-word"), word);
      void callout.offsetWidth;
      callout.classList.add("is-on");
    },
    clearCallout() {
      callout.classList.remove("is-on");
    },
    setCadence(every) {
      cadence = every;
    },
    run(g) {
      if (++beat < cadence && g.streak <= lastStreak) return;
      beat = 0;
      const left = g.cleared ? g.runTime - g.runSeconds : g.runSeconds - Math.max(0, g.runTime);
      write("time", clock(left));
      write("time-label", g.cleared ? "overtime" : "left");
      clockBox.classList.toggle("is-overtime", g.cleared);
      write("wave-num", `Wave ${Math.max(1, g.wave + 1)}`);
      write("wave-name", g.waveName || "Incoming");
      write("score", fmt(g.score));
      write("streak", fmt(g.streak));
      // A streak is alive while grazes come within two seconds of each other; it pops on each one.
      streakBox.classList.toggle("is-live", g.streak > 0 && g.sinceGraze < 2);
      if (g.streak > lastStreak && !still.matches) play(streakN, SQUASH, { duration: 260, easing: EASE_OUT });
      lastStreak = g.streak;
      write("mult", `×${g.mult.toFixed(1)}`);
      multFill.style.setProperty("--p", ((g.mult - 1) / 7).toFixed(3));
      const p = g.cleared ? 1 : Math.max(0, g.runTime) / g.runSeconds;
      progress.style.setProperty("--p", Math.min(1, p).toFixed(4));
    },
    /** Floats a graze's points up beside the ship, left and right in turn; at most one every 260 ms. */
    scorePop(points, x, y, field) {
      const now = performance.now();
      if (now - popAt < 260) return;
      popAt = now;
      const el = pops[popNext];
      const side = popNext % 2 ? 1 : -1;
      popNext = (popNext + 1) % pops.length;
      if (still.matches) return;
      el.textContent = `+${points}`;
      const px = `${(field.width / 2 + x * field.pxPerUnit + side * 40).toFixed(1)}px`;
      const py = `${(field.height / 2 - y * field.pxPerUnit).toFixed(1)}px`;
      play(el, rise(px, py), { duration: 620, easing: EASE_OUT });
    },
    multPop() {
      if (!still.matches) play(multX, BUMP, { duration: 220, easing: EASE_OUT });
    },
    result(r, ctx) {
      write("result-kicker", ctx.kicker);
      write("result-title", r.cleared ? "Storm cleared" : `Shattered at ${clock(r.survived)}`);
      write("result-grazes", fmt(r.grazes));
      write("result-streak", fmt(r.longest));
      write("result-best", fmt(ctx.best));
      newBest.classList.toggle("is-on", false);
      countFrom = 0;
      countTo = r.score;
      countStart = performance.now() + 250;
      $("result-score").textContent = "0";
      if (ctx.instant) {
        countStart = 0;
        $("result-score").textContent = fmt(r.score);
        newBest.classList.toggle("is-on", ctx.isBest);
      } else {
        setTimeout(() => newBest.classList.toggle("is-on", ctx.isBest), 1400);
      }
    },
    /** Runs the score count-up on the result card; called every frame. */
    tick(now) {
      if (!countStart || root.dataset.screen !== "result") return;
      const t = Math.min(1, Math.max(0, (now - countStart) / 1100));
      $("result-score").textContent = fmt(countFrom + (countTo - countFrom) * easeOutCubic(t));
      if (t >= 1) countStart = 0;
    },
    setShareLabel(text) {
      $("share-label").textContent = text;
    },
    toast(text) {
      toastEl.textContent = text;
      toastEl.classList.add("is-on");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toastEl.classList.remove("is-on"), 2200);
    },
    /** The rectangle of an element in normalized device coordinates, for the quiet zone behind type. */
    ndcRect(el, padX = 0, padY = 0) {
      const r = el.getBoundingClientRect();
      const w = innerWidth;
      const h = innerHeight;
      return [((r.left - padX) / w) * 2 - 1, 1 - ((r.bottom + padY) / h) * 2, ((r.right + padX) / w) * 2 - 1, 1 - ((r.top - padY) / h) * 2];
    },
  };
}
