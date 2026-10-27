// The week under the pointer or the keyboard cursor: its dates, the age, and the era or event it holds.
// One pointer path for mouse, pen, and touch; arrow keys move the same cursor when the grid has focus.

import { WEEKS, count, rangeWords, ordinal } from "./life.js";

export function describe(model, cell) {
  const { first, last, age, week } = model.life.spanOf(cell);
  const lines = { when: rangeWords(first, last), age: "", tags: [] };
  const where = `Age ${age}, the ${ordinal(week + 1)} week`;
  if (cell === model.now) lines.age = `This week. ${where}`;
  else if (cell < model.lived) lines.age = `${where}. Week ${count.format(cell + 1)} of your life`;
  else lines.age = `${where}. ${count.format(cell - model.lived)} weeks from now`;
  for (const event of model.eventsAt.get(cell) ?? []) lines.tags.push({ kind: "event", text: event.label });
  const era = model.eraOf[cell];
  if (era >= 0) lines.tags.push({ kind: "era", text: model.eras[era].label, color: model.eras[era].color });
  return lines;
}

export function createTip({ wrap, svg, tip, cursor, live }, model) {
  const when = tip.querySelector(".tip-when");
  const age = tip.querySelector(".tip-age");
  const tags = tip.querySelector(".tip-tags");
  let shown = -1;
  let hideTimer = 0;
  let keyCell = model.now ?? Math.max(0, model.lived - 1);

  function fill(cell) {
    if (cell === shown) return;
    shown = cell;
    const lines = describe(model, cell);
    when.textContent = lines.when;
    age.textContent = lines.age;
    tags.replaceChildren(...lines.tags.map((tag) => {
      const item = document.createElement("li");
      item.className = `tip-tag tip-${tag.kind}`;
      const mark = document.createElement("span");
      mark.className = "tip-mark";
      mark.setAttribute("aria-hidden", "true");
      if (tag.color) mark.style.setProperty("--era-c", tag.color);
      item.append(mark, tag.text);
      return item;
    }));
    tags.hidden = lines.tags.length === 0;
    cursor.style.setProperty("--cx", String(cell % WEEKS));
    cursor.style.setProperty("--cy", String(Math.floor(cell / WEEKS)));
  }

  function place(x, y, above) {
    const box = tip.getBoundingClientRect();
    const pad = 12;
    const w = document.documentElement.clientWidth;
    const h = window.innerHeight;
    let left = x + 16;
    let top = above ? y - box.height - 28 : y + 18;
    if (left + box.width > w - pad) left = x - box.width - 16;
    if (left < pad) left = Math.min(Math.max(pad, x - box.width / 2), w - box.width - pad);
    if (top + box.height > h - pad) top = y - box.height - 18;
    if (top < pad) top = Math.min(y + 28, h - box.height - pad);
    tip.style.setProperty("--tx", `${Math.round(left)}px`);
    tip.style.setProperty("--ty", `${Math.round(top)}px`);
  }

  function show() {
    clearTimeout(hideTimer);
    tip.hidden = false;
    cursor.classList.add("is-on");
  }

  function hide() {
    clearTimeout(hideTimer);
    tip.hidden = true;
    cursor.classList.remove("is-on");
    shown = -1;
  }

  function cellAt(clientX, clientY) {
    const box = svg.getBoundingClientRect();
    const pitch = box.width / WEEKS;
    const col = Math.floor((clientX - box.left) / pitch);
    const row = Math.floor((clientY - box.top) / pitch);
    if (col < 0 || col >= WEEKS || row < 0 || row >= model.rows) return -1;
    return row * WEEKS + col;
  }

  function track(event) {
    const cell = cellAt(event.clientX, event.clientY);
    if (cell < 0) {
      if (event.pointerType === "mouse") hide();
      return;
    }
    show();
    fill(cell);
    place(event.clientX, event.clientY, event.pointerType !== "mouse");
  }

  svg.addEventListener("pointermove", (event) => {
    if (event.pointerType === "mouse" || event.buttons) track(event);
  });
  svg.addEventListener("pointerdown", track);
  svg.addEventListener("pointerleave", (event) => {
    if (event.pointerType === "mouse") hide();
  });
  svg.addEventListener("pointerup", (event) => {
    if (event.pointerType !== "mouse") hideTimer = setTimeout(hide, 1800);
  });
  svg.addEventListener("pointercancel", hide);

  function showKey() {
    show();
    fill(keyCell);
    const box = svg.getBoundingClientRect();
    const pitch = box.width / WEEKS;
    place(box.left + ((keyCell % WEEKS) + 1) * pitch, box.top + (Math.floor(keyCell / WEEKS) + 0.5) * pitch, false);
    const lines = describe(model, keyCell);
    live.textContent = [lines.when, lines.age, ...lines.tags.map((tag) => tag.text)].join(". ");
  }

  wrap.addEventListener("keydown", (event) => {
    const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -WEEKS, ArrowDown: WEEKS, Home: -(keyCell % WEEKS), End: WEEKS - 1 - (keyCell % WEEKS) };
    if (event.key === "Escape") {
      hide();
      return;
    }
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = keyCell + moves[event.key];
    if (next >= 0 && next < model.cells) keyCell = next;
    showKey();
  });
  wrap.addEventListener("focus", () => {
    if (wrap.matches(":focus-visible")) showKey();
  });
  wrap.addEventListener("blur", hide);
  window.addEventListener("scroll", () => {
    if (!tip.hidden && document.activeElement !== wrap) hide();
  }, { passive: true });

  return { hide, refresh: () => { if (!tip.hidden && document.activeElement === wrap) showKey(); } };
}
