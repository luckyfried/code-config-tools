// The words around the grid: ages and era labels in the left margin, event words in the right, week numbers on top.
// Each is placed in rows and columns; CSS turns those into lengths with --pitch, on screen and on paper alike.

import { yearOf } from "./life.js";

function el(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Spreads wanted positions apart by at least `gap`, keeping them inside 0..limit and as close to wanted as it can. */
export function spread(wanted, gap, limit) {
  const placed = wanted.map((want, order) => ({ want, order, at: want })).sort((a, b) => a.want - b.want);
  for (let k = 1; k < placed.length; k += 1) placed[k].at = Math.max(placed[k].want, placed[k - 1].at + gap);
  const overflow = placed.length ? placed[placed.length - 1].at - limit : 0;
  if (overflow > 0) {
    placed[placed.length - 1].at = limit;
    for (let k = placed.length - 2; k >= 0; k -= 1) placed[k].at = Math.min(placed[k].at, placed[k + 1].at - gap);
  }
  const out = new Array(wanted.length);
  for (const item of placed) out[item.order] = item.at;
  return out;
}

export function createMargins({ left, right, ticks }, model) {
  const { rows, columns, eras, events } = model;

  const ages = [];
  for (let age = 0; age < rows; age += 5) {
    const node = el("span", age % 10 === 0 ? "age age-ten" : "age", String(age));
    node.style.setProperty("--y", String(age + 0.5));
    ages.push(node);
  }

  const eraLabels = eras.map((era) => {
    const node = el("span", "era-label", era.label);
    node.dataset.era = String(era.index);
    node.style.setProperty("--era-c", era.color);
    return node;
  });

  // Several events in one week share a line.
  const byCell = [];
  for (const event of events) {
    const last = byCell[byCell.length - 1];
    if (last && last.cell === event.cell) last.events.push(event);
    else byCell.push({ cell: event.cell, events: [event] });
  }
  const words = byCell.map(({ cell, events: here }) => {
    const node = el("span", cell < model.lived ? "event-word" : "event-word ahead");
    node.append(el("span", "event-text", here.map((event) => event.label).join(", ")));
    node.append(el("span", "event-year", String(yearOf(here[0].day))));
    return node;
  });

  const tickCols = [0, 9, 19, 29, 39, 51];
  const tickNodes = tickCols.map((col) => {
    const node = el("span", "tick", String(col + 1));
    node.style.setProperty("--x", String(col + 0.5));
    return node;
  });

  left.append(...ages, ...eraLabels);
  right.append(...words);
  ticks.replaceChildren(...tickNodes);

  /** Places era labels `eraRows` apart and event words `wordRows` apart; answers where each word landed, for the leaders. */
  function layout({ eraRows, wordRows }) {
    const eraWanted = eras.map((era) => {
      const top = Math.floor(era.from / columns) + (era.from % columns) / columns;
      return top + eraRows / 2;
    });
    spread(eraWanted, eraRows, rows - eraRows / 2).forEach((y, k) => eraLabels[k].style.setProperty("--y", y.toFixed(3)));

    const wanted = byCell.map(({ cell }) => Math.floor(cell / columns) + 0.5);
    const placed = spread(wanted, wordRows, rows - wordRows / 2);
    placed.forEach((y, k) => words[k].style.setProperty("--y", y.toFixed(3)));
    return byCell.map(({ cell }, k) => ({ cell, row: placed[k] }));
  }

  return { layout };
}
