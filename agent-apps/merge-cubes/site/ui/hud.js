// The score strip, the climb to 2048, and the one-line hint. DOM only; the canvas never draws text but the cubes'.
import { textFor } from "../scene/labels.js";

const numbers = new Intl.NumberFormat("en-US");
const fmt = (n) => numbers.format(n);
const easeOut = (u) => 1 - (1 - u) ** 3;

export function createHud(root) {
  const $ = (sel) => root.querySelector(sel);
  const scoreEl = $("[data-score]");
  const bestEl = $("[data-best]");
  const bestBox = bestEl.closest(".score");
  const gainEl = $("[data-gain]");
  const ladder = $("[data-ladder]");
  const ladderTitle = $("[data-ladder-title]");
  const hint = $("[data-hint]");
  const undo = $("[data-undo]");
  const fresh = $("[data-new]");
  const freshLabel = fresh.querySelector("span");
  let shown = 0;
  let target = 0;
  let from = 0;
  let t0 = 0;
  let raf = 0;
  let labels = "numbers";
  // While this game is the best one, Best shows the score as it counts up, never ahead of it.
  let bestLive = false;
  let bestFloor = 0;
  let bestValue = 0;
  const scores = scoreEl.closest(".scores");
  let confirmTimer = 0;
  const rungs = [];

  function buildLadder() {
    ladder.textContent = "";
    rungs.length = 0;
    for (let i = 0; i < 12; i += 1) {
      const value = 2 ** (i + 1);
      const li = document.createElement("li");
      li.className = "rung";
      li.style.setProperty("--rung-color", `var(--cube-${i + 1})`);
      li.style.setProperty("--rung-ink", `var(--cube-ink-${i + 1})`);
      li.classList.toggle("is-goal", value === 2048);
      const cube = document.createElement("span");
      cube.className = "rung-cube";
      cube.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "rung-label";
      label.textContent = textFor(value, labels);
      const note = document.createElement("span");
      note.className = "rung-note";
      li.append(cube, label, note);
      ladder.append(li);
      rungs.push({ li, note, value });
    }
    ladderTitle.textContent = `Toward ${textFor(2048, labels)}`;
  }

  function showBest() {
    bestEl.textContent = fmt(bestLive ? Math.min(bestValue, Math.max(bestFloor, shown)) : bestValue);
  }

  function tick(now) {
    const u = Math.min(1, (now - t0) / 360);
    shown = Math.round(from + (target - from) * easeOut(u));
    scoreEl.textContent = fmt(shown);
    showBest();
    raf = u < 1 ? requestAnimationFrame(tick) : 0;
  }

  return {
    setLabels(next) {
      labels = next;
      buildLadder();
    },
    setScore(score, gained = 0, { instant = false } = {}) {
      target = score;
      scores.classList.remove("is-waiting");
      if (instant || matchMedia("(prefers-reduced-motion: reduce)").matches) {
        cancelAnimationFrame(raf);
        raf = 0;
        shown = score;
        scoreEl.textContent = fmt(score);
        showBest();
      } else {
        from = shown;
        t0 = performance.now();
        if (!raf) raf = requestAnimationFrame(tick);
      }
      if (gained > 0) {
        gainEl.textContent = `+${fmt(gained)}`;
        gainEl.classList.remove("is-up");
        void gainEl.offsetWidth;
        gainEl.classList.add("is-up");
      }
    },
    setBest(best, isNew, { live = false, floor = 0 } = {}) {
      bestValue = best;
      bestLive = live;
      bestFloor = floor;
      showBest();
      bestBox.classList.toggle("is-new", Boolean(isNew));
    },
    setHighest(value) {
      for (const r of rungs) {
        r.li.classList.toggle("is-reached", r.value <= value);
        r.li.classList.toggle("is-top", r.value === value);
        r.note.textContent = r.value === value ? "On the board" : r.value === 2048 && value < 2048 ? "The goal" : "";
      }
    },
    setHint(text) {
      hint.hidden = !text;
      hint.textContent = text || "";
    },
    setUndo(enabled) {
      undo.disabled = !enabled;
    },
    /** New game asks once more when a game is under way; a second tap within three seconds starts over. */
    armNew() {
      clearTimeout(confirmTimer);
      freshLabel.textContent = "Tap again";
      fresh.classList.add("is-armed");
      confirmTimer = setTimeout(() => this.disarmNew(), 3000);
    },
    disarmNew() {
      clearTimeout(confirmTimer);
      freshLabel.textContent = "New game";
      fresh.classList.remove("is-armed");
    },
    get armed() {
      return fresh.classList.contains("is-armed");
    },
  };
}
