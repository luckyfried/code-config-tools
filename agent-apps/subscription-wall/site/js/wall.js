// The wall: one tile per subscription, its yearly cost the big figure, in three size tiers by that cost (the most
// expensive one the hero), with a renewal bar and a cancel toggle.

import { bright, chargeWindow, daysBetween, everyWord, fmtShort, fmtUntil } from "./format.js";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function initial(name) {
  const ch = Array.from(name.trim())[0] || "?";
  return ch.toLocaleUpperCase();
}

export function createWall({ root, subs, money, today, onToggle }) {
  const tiles = new Map();

  for (const sub of subs) {
    const { next, prev } = chargeWindow(sub, today);
    const span = Math.max(1, daysBetween(prev, next));
    const until = daysBetween(today, next);
    const progress = Math.min(1, Math.max(0.02, 1 - until / span));

    const tile = el("article", `tile hued tier-${sub.tier}${sub.rank === 1 ? " is-hero" : ""}${bright(sub.hue) ? " is-bright" : ""}`);
    tile.dataset.id = sub.id;
    tile.style.setProperty("--hue", String(sub.hue));
    const each = money.cents(Math.round(sub.amount * 100));
    tile.setAttribute("aria-label", `${sub.name}, ${money.cents(sub.yearlyCents)} a year, ${each} ${everyWord(sub.every)}`);

    const letter = el("span", "tile-letter", initial(sub.name));
    letter.setAttribute("aria-hidden", "true");

    const info = el("div", "tile-info");
    const name = el("h3", "tile-name", sub.name);
    const figure = el("p", "tile-figure");
    figure.append(el("span", "tile-amount", money.cents(sub.yearlyCents)), el("span", "tile-unit", "a year"));
    const eachLine = el("p", "tile-each", sub.every === "year" ? "One charge a year" : `${each} ${everyWord(sub.every)}`);
    const saves = el("p", "tile-saves", `You save ${money.cents(sub.yearlyCents)}`);
    saves.hidden = true;
    info.append(name, figure, eachLine, saves);

    const renew = el("div", "tile-renew");
    const bar = el("div", "tile-bar");
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${Math.round(progress * 100)}% of the way to the next charge`);
    const fill = el("span", "tile-bar-fill");
    fill.style.setProperty("--progress", progress.toFixed(4));
    bar.append(fill);
    const nextLine = el("p", "tile-next");
    nextLine.append(el("strong", "", until === 0 ? "Renews today" : `Renews ${fmtShort(next)}`));
    if (until > 0) nextLine.append(el("span", "", fmtUntil(until)));
    renew.append(bar, nextLine);

    const toggle = el("button", "tile-toggle", "What if I cancel?");
    toggle.type = "button";
    toggle.setAttribute("aria-pressed", "false");
    toggle.setAttribute("aria-label", `What if I cancel ${sub.name}?`);
    toggle.addEventListener("click", () => onToggle(sub.id));

    tile.append(letter, info, renew, toggle);
    tiles.set(sub.id, { tile, fill, toggle, saves, eachLine, progress, sub });
  }

  function order(ids) {
    root.replaceChildren(...ids.map((id) => tiles.get(id).tile));
  }

  // Moves tiles to a new order, gliding each from its old place (first, last, invert, play).
  function reorder(ids, animate) {
    const before = new Map();
    if (animate) for (const [id, t] of tiles) before.set(id, t.tile.getBoundingClientRect());
    order(ids);
    if (!animate) return;
    for (const [id, t] of tiles) {
      const a = before.get(id);
      const b = t.tile.getBoundingClientRect();
      const dx = a.left - b.left;
      const dy = a.top - b.top;
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) continue;
      t.tile.animate(
        [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }],
        { duration: 420, easing: "cubic-bezier(0.77, 0, 0.175, 1)" },
      );
    }
  }

  function setOff(id, off) {
    const t = tiles.get(id);
    t.tile.classList.toggle("is-off", off);
    t.toggle.setAttribute("aria-pressed", String(off));
    t.toggle.textContent = off ? "Keep it" : "What if I cancel?";
    t.toggle.setAttribute("aria-label", off ? `Keep ${t.sub.name}` : `What if I cancel ${t.sub.name}?`);
    t.saves.hidden = !off;
    t.eachLine.hidden = off;
  }

  // Fills every renewal bar from empty, staggered across the wall, as the total rolls up.
  function fillBars(reduce) {
    if (reduce) return;
    let i = 0;
    for (const id of Array.from(root.children, (n) => n.dataset.id)) {
      const t = tiles.get(id);
      t.fill.animate(
        [{ transform: "scaleX(0)" }, { transform: `scaleX(${t.progress})` }],
        { duration: 900, delay: 200 + i * 40, easing: "cubic-bezier(0.23, 1, 0.32, 1)", fill: "backwards" },
      );
      i += 1;
    }
  }

  return { order, reorder, setOff, fillBars };
}
