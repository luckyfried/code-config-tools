// Builds the sheet from the config and filters it: rows that stop matching fade where they stood, the rest glide into
// place, rows that match again rise in, and the matched text is marked. Caps flip with an arc and sink when pressed.

import { capFor, keysFor, keyWords } from "./keys.js";

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};

function fillMarked(node, text, query) {
  node.replaceChildren();
  if (!query) { node.textContent = text; return; }
  const lower = text.toLowerCase();
  let at = 0;
  for (let hit = lower.indexOf(query); hit !== -1; hit = lower.indexOf(query, at)) {
    if (hit > at) node.append(text.slice(at, hit));
    node.append(el("mark", "hit", text.slice(hit, hit + query.length)));
    at = hit + query.length;
  }
  if (at < text.length) node.append(text.slice(at));
}

function renderKeys(entry, platform) {
  const chords = keysFor(entry, platform);
  if (chords.length === 0) return null;
  const wrap = el("span", "keys");
  let k = 0;
  chords.forEach((chord, i) => {
    if (i > 0) wrap.append(el("span", "then", "then"));
    const group = el("span", "chord");
    for (const name of chord) {
      const cap = capFor(name, platform);
      const outer = el("span", "cap");
      outer.dataset.kind = cap.kind;
      if (cap.word) outer.dataset.word = "";
      outer.style.setProperty("--k", String(k++));
      const face = el("kbd", "cap-face", cap.label);
      const back = el("span", "cap-back");
      back.setAttribute("aria-hidden", "true");
      outer.append(face, back);
      group.append(outer);
    }
    wrap.append(group);
  });
  return wrap;
}

export function createSheet({ root, config }) {
  const sections = [];
  let platform = config.platform;
  let query = "";
  let rowIndex = 0;

  for (const section of config.sections) {
    const node = el("section", "section");
    const head = el("h2", "section-head");
    head.append(el("span", "section-label", section.label), el("span", "section-count", String(section.entries.length)));
    const list = el("ul", "rows");
    const rows = section.entries.map((entry) => {
      const row = el("li", "row");
      row.style.setProperty("--d-in", `${Math.min(rowIndex++ * 28, 900)}ms`);
      const action = el("span", "action");
      const actionText = el("span", "action-text", entry.action);
      action.append(actionText);
      if (entry.note) action.append(el("span", "note", entry.note));
      row.append(action);
      let cmdNode = null;
      if (entry.command) {
        const wrap = el("span", "cmd-wrap");
        cmdNode = el("code", "cmd", entry.command);
        wrap.append(cmdNode);
        row.classList.add("has-cmd");
        row.append(wrap);
      }
      const item = { entry, row, actionText, cmdNode, keysNode: null, section: section.label.toLowerCase(), visible: true };
      placeKeys(item);
      list.append(row);
      return item;
    });
    node.append(head, list);
    root.append(node);
    sections.push({ node, rows, visible: true });
  }

  function placeKeys(item) {
    const fresh = renderKeys(item.entry, platform);
    if (item.keysNode) item.keysNode.remove();
    item.keysNode = fresh;
    if (fresh) item.row.insertBefore(fresh, item.cmdNode ? item.cmdNode.parentNode : null);
  }

  function matches(item, q) {
    if (!q) return true;
    const e = item.entry;
    return [e.action, e.command || "", e.note || "", item.section, keyWords(e, platform)].some((s) => s.toLowerCase().includes(q));
  }

  // A search narrows in three beats: what stops matching fades where it stood, what still matches glides to its new
  // place, and what matches again rises in after them. Each keystroke starts from wherever the last one left things.
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const moving = new Set();
  let ghosts = null;

  function ghost(node, box, opacity) {
    if (!ghosts) {
      ghosts = el("div", "ghosts");
      ghosts.setAttribute("aria-hidden", "true");
      document.body.append(ghosts);
    }
    ghosts.classList.toggle("is-learning", root.classList.contains("is-learning"));
    const copy = node.cloneNode(true);
    if (node.classList.contains("section") && node === root.firstElementChild) copy.classList.add("is-first");
    copy.style.setProperty("--gx", `${box.left + scrollX}px`);
    copy.style.setProperty("--gy", `${box.top + scrollY}px`);
    copy.style.setProperty("--gw", `${box.width}px`);
    ghosts.append(copy);
    copy.animate(
      [{ opacity, transform: "none", filter: "blur(0)" }, { opacity: 0, transform: "translateY(-4px) scale(0.98)", filter: "blur(2px)" }],
      { duration: 100, easing: "cubic-bezier(0.4, 0, 1, 1)", fill: "forwards" },
    ).finished.then(() => copy.remove(), () => copy.remove());
  }

  function glide(node, dy, opacity, delay) {
    if (Math.abs(dy) < 0.5 && opacity > 0.99) return;
    moving.add(node.animate(
      [{ transform: `translateY(${dy}px)`, opacity }, { transform: "none", opacity: 1 }],
      { duration: 420, delay, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "backwards" },
    ));
  }

  function arrive(node, delay) {
    moving.add(node.animate(
      [{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "none" }],
      { duration: 340, delay, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "backwards" },
    ));
  }

  function filter(raw) {
    query = raw.trim().toLowerCase();
    const plan = sections.map((s) => {
      const on = s.rows.map((item) => matches(item, query));
      return { s, on, any: on.some(Boolean) };
    });
    const animate = !reduced.matches && root.isConnected && root.getClientRects().length > 0;

    // First: where everything on screen stands now and how far it has faded in, mid-glide included. A fresh search
    // holds still for one beat while what stops matching clears, so nothing slides through a fading row; a keystroke
    // mid-glide starts again from wherever things are.
    const first = new Map();
    const seen = (node) => ({ box: node.getBoundingClientRect(), opacity: Number(getComputedStyle(node).opacity) });
    const beat = 100;
    if (animate) {
      for (const { s, on, any } of plan) {
        if (s.node.hidden) continue;
        const was = seen(s.node);
        first.set(s.node, was);
        if (!any) { ghost(s.node, was.box, was.opacity); continue; }
        s.rows.forEach((item, i) => {
          if (item.row.hidden) return;
          const rwas = seen(item.row);
          first.set(item.row, rwas);
          if (!on[i]) ghost(item.row, rwas.box, rwas.opacity);
        });
      }
      for (const a of moving) a.cancel();
      moving.clear();
    }

    let shown = 0;
    for (const { s, on, any } of plan) {
      s.rows.forEach((item, i) => {
        item.visible = on[i];
        if (on[i]) shown++;
        fillMarked(item.actionText, item.entry.action, query);
        if (item.cmdNode) fillMarked(item.cmdNode, item.entry.command, query);
        item.row.hidden = !on[i];
      });
      s.visible = any;
      s.node.hidden = !any;
    }
    if (!animate) return shown;

    // Last, then invert. Nothing flies across the sheet: within its column a section slides up or down as one and its
    // rows close up inside it, all in step so nothing in a column passes over its neighbor; a section that lands in
    // another column fades where it stood and rises where it lands, and new matches rise in one after another.
    const last = new Map();
    for (const { s, any } of plan) {
      if (!any) continue;
      last.set(s.node, s.node.getBoundingClientRect());
      for (const item of s.rows) if (!item.row.hidden) last.set(item.row, item.row.getBoundingClientRect());
    }
    let arrivals = 0;
    const rise = (node, step) => arrive(node, beat + 330 + Math.min(arrivals++ * step, 240));
    for (const { s, any } of plan) {
      if (!any) continue;
      const was = first.get(s.node);
      const now = last.get(s.node);
      if (!was || was.opacity < 0.5) { rise(s.node, 40); continue; }
      if (Math.abs(was.box.left - now.left) > 24) {
        ghost(s.node, was.box, was.opacity);
        rise(s.node, 40);
        continue;
      }
      glide(s.node, was.box.top - now.top, was.opacity, beat);
      for (const item of s.rows) {
        if (item.row.hidden) continue;
        const rwas = first.get(item.row);
        if (!rwas || rwas.opacity < 0.5) { rise(item.row, 30); continue; }
        const rnow = last.get(item.row);
        glide(item.row, (rwas.box.top - was.box.top) - (rnow.top - now.top), rwas.opacity, beat);
      }
    }
    return shown;
  }

  // The flip's arc: each cap lifts off the sheet as it turns, lands on its edge, and the landing sinks it once.
  function hop(caps, delayOf) {
    if (reduced.matches) return;
    caps.forEach((cap, i) => {
      const delay = delayOf(cap, i);
      cap.animate(
        [
          { translate: "0 0", scale: "1", easing: "cubic-bezier(0.3, 0.7, 0.4, 1)" },
          { translate: "0 -9px", scale: "1.08", offset: 0.45, easing: "cubic-bezier(0.5, 0, 0.75, 0.3)" },
          { translate: "0 0", scale: "1", offset: 0.82 },
          { translate: "0 0", scale: "1" },
        ],
        { duration: 600, delay },
      );
      for (const side of cap.children) {
        side.animate(
          [{ "--edge": "var(--depth)" }, { "--edge": "1px", offset: 0.4 }, { "--edge": "var(--depth)" }],
          { duration: 240, delay: delay + 470, easing: "ease-out" },
        );
      }
    });
  }

  const capsOf = (row) => [...row.querySelectorAll(".cap")];
  const byKey = (cap) => Number(cap.style.getPropertyValue("--k") || 0) * 45;

  // Tapping a row plays its chord: each cap goes down in the order it is pressed.
  function play(row) {
    if (reduced.matches) return;
    row.classList.remove("is-playing");
    void row.offsetWidth;
    row.classList.add("is-playing");
    clearTimeout(row.playTimer);
    row.playTimer = setTimeout(() => row.classList.remove("is-playing"), capsOf(row).length * 110 + 400);
  }

  function setPlatform(next) {
    platform = next;
    root.classList.add("is-swapping");
    for (const s of sections) for (const item of s.rows) placeKeys(item);
    setTimeout(() => root.classList.remove("is-swapping"), 600);
    return filter(query);
  }

  // Each cap's delay in a Learn wave follows its place on the sheet: down the columns, then across. The caps that are
  // on screen lift as they turn; the rest turn unseen.
  function stampWave() {
    const caps = [...root.querySelectorAll(".row:not([hidden]) .cap")];
    const boxes = caps.map((c) => c.getBoundingClientRect());
    const top = Math.min(...boxes.map((b) => b.top));
    const left = Math.min(...boxes.map((b) => b.left));
    caps.forEach((cap, i) => {
      const b = boxes[i];
      const d = (b.top - top) * 0.55 + (b.left - left) * 0.32;
      cap.style.setProperty("--d", `${Math.round(Math.min(d, 900))}ms`);
    });
    const onScreen = caps.filter((_, i) => boxes[i].bottom > 0 && boxes[i].top < innerHeight);
    hop(onScreen, (cap) => parseFloat(cap.style.getPropertyValue("--d")) || 0);
  }

  const total = sections.reduce((n, s) => n + s.rows.length, 0);
  return {
    filter,
    setPlatform,
    stampWave,
    play,
    turn: (row) => hop(capsOf(row), byKey),
    total,
    rows: () => sections.flatMap((s) => s.rows),
  };
}
