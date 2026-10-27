// The radial picker: five swatches on an arc around the tapped day, roughest to best, turned to whichever side has room.
const R = 80;
const SPREAD = 160;
const SWATCH = 22;
const LABEL_GAP = 5;
const NOTE_GAP = 50;
const EDGE = 8;
const DIRECTIONS = { up: -90, down: 90, right: 0, left: 180 };

const rad = (deg) => (deg * Math.PI) / 180;

export function createPicker(root, ring, moods, { onPick, onNote, onDismiss }) {
  let day = null;
  let cell = null;

  const swatches = moods.map((mood, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "swatch";
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", "false");
    b.setAttribute("aria-label", mood.label);
    b.style.setProperty("--sw", `var(--mood-${i + 1})`);
    b.style.setProperty("--i", String(i));
    b.addEventListener("click", () => onPick(day, i + 1));
    return b;
  });
  // Labels sit above every swatch, each pushed out along its own radius until it clears its circle.
  const labels = moods.map((mood, i) => {
    const label = document.createElement("span");
    label.className = "swatch-label";
    label.textContent = mood.label;
    label.setAttribute("aria-hidden", "true");
    label.style.setProperty("--i", String(i));
    return label;
  });
  const note = document.createElement("button");
  note.type = "button";
  note.className = "picker-note";
  note.addEventListener("click", () => onNote(day));
  ring.setAttribute("role", "radiogroup");
  ring.replaceChildren(...swatches, ...labels, note);

  // Arc points for one direction, ordered so the roughest mood is on the left (or on top for a side arc),
  // each with its label's center and half size.
  function arc(dir, sizes) {
    const center = DIRECTIONS[dir];
    const pts = moods.map((_, i) => {
      const a = rad(center - SPREAD / 2 + (SPREAD / (moods.length - 1)) * i);
      return { x: Math.cos(a) * R, y: Math.sin(a) * R, ux: Math.cos(a), uy: Math.sin(a) };
    });
    const sideways = dir === "left" || dir === "right";
    pts.sort((p, q) => (sideways ? p.y - q.y : p.x - q.x));
    pts.forEach((p, i) => {
      const { hw, hh } = sizes[i];
      const d = SWATCH + LABEL_GAP + Math.abs(p.ux) * hw + Math.abs(p.uy) * hh;
      Object.assign(p, { lx: p.x + p.ux * d, ly: p.y + p.uy * d, hw, hh });
    });
    const back = rad(DIRECTIONS[dir] + 180);
    return { pts, nx: Math.cos(back) * NOTE_GAP, ny: Math.sin(back) * NOTE_GAP };
  }

  // How far, in pixels, an arc around (cx, cy) spills past the viewport, and the shift that brings it back.
  function spill(cx, cy, layout) {
    const W = window.innerWidth;
    const H = window.innerHeight;
    let minX = cx, maxX = cx, minY = cy, maxY = cy;
    for (const p of layout.pts) {
      const lx = cx + p.lx;
      const ly = cy + p.ly;
      minX = Math.min(minX, cx + p.x - SWATCH, lx - p.hw);
      maxX = Math.max(maxX, cx + p.x + SWATCH, lx + p.hw);
      minY = Math.min(minY, cy + p.y - SWATCH, ly - p.hh);
      maxY = Math.max(maxY, cy + p.y + SWATCH, ly + p.hh);
    }
    const dx = minX < EDGE ? EDGE - minX : maxX > W - EDGE ? W - EDGE - maxX : 0;
    const dy = minY < EDGE ? EDGE - minY : maxY > H - EDGE ? H - EDGE - maxY : 0;
    return { cost: Math.abs(dx) + Math.abs(dy), dx, dy };
  }

  function place() {
    if (!cell) return;
    const r = cell.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const sizes = labels.map((l) => ({ hw: l.offsetWidth / 2, hh: l.offsetHeight / 2 }));
    let best = null;
    for (const dir of Object.keys(DIRECTIONS)) {
      const layout = arc(dir, sizes);
      const s = spill(cx, cy, layout);
      if (!best || s.cost < best.s.cost) best = { layout, s };
      if (s.cost === 0) break;
    }
    const { layout, s } = best;
    ring.style.setProperty("--cx", `${cx + s.dx}px`);
    ring.style.setProperty("--cy", `${cy + s.dy}px`);
    layout.pts.forEach((p, i) => {
      const b = swatches[i];
      b.style.setProperty("--x", `${p.x.toFixed(1)}px`);
      b.style.setProperty("--y", `${p.y.toFixed(1)}px`);
      labels[i].style.setProperty("--x", `${p.lx.toFixed(1)}px`);
      labels[i].style.setProperty("--y", `${p.ly.toFixed(1)}px`);
    });
    placeNote(cx + s.dx, cy + s.dy, r, layout);
  }

  // The note pill takes the first spot that stays on screen and clears the swatches, their labels, and the day.
  function placeNote(ox, oy, cellRect, layout) {
    const W = window.innerWidth;
    const H = window.innerHeight;
    const w = note.offsetWidth || 120;
    const h = note.offsetHeight || 40;
    const lift = { x: (cell.offsetWidth * 1.6) / 2 + 6, y: (cell.offsetHeight * 1.6) / 2 + 6 };
    const cx = cellRect.left + cellRect.width / 2 - ox;
    const cy = cellRect.top + cellRect.height / 2 - oy;
    const blocks = [{ x: cx, y: cy, hw: lift.x, hh: lift.y }];
    for (const p of layout.pts) {
      blocks.push({ x: p.x, y: p.y, hw: SWATCH + 4, hh: SWATCH + 4 });
      blocks.push({ x: p.lx, y: p.ly, hw: p.hw + 4, hh: p.hh + 4 });
    }
    const spots = [{ x: layout.nx, y: layout.ny }];
    for (let d = lift.y + h / 2; d < 220; d += 12) spots.push({ x: cx, y: cy + d }, { x: cx, y: cy - d });
    for (let d = lift.x + w / 2; d < 260; d += 12) spots.push({ x: cx + d, y: cy }, { x: cx - d, y: cy });
    const fit = (p) => ({
      x: Math.min(Math.max(ox + p.x, w / 2 + EDGE), W - w / 2 - EDGE) - ox,
      y: Math.min(Math.max(oy + p.y, h / 2 + EDGE), H - h / 2 - EDGE) - oy,
    });
    const clear = (p) => blocks.every((b) => Math.abs(p.x - b.x) >= w / 2 + b.hw || Math.abs(p.y - b.y) >= h / 2 + b.hh);
    const spot = spots.map(fit).find(clear) || fit(spots[0]);
    note.style.setProperty("--nx", `${spot.x.toFixed(1)}px`);
    note.style.setProperty("--ny", `${spot.y.toFixed(1)}px`);
  }

  function open(target, entry, { focus = false } = {}) {
    if (cell && cell !== target) cell.classList.remove("is-lifted");
    cell = target;
    day = target.dataset.day;
    cell.classList.add("is-lifted");
    swatches.forEach((b, i) => b.setAttribute("aria-checked", String(entry ? entry.mood === i + 1 : false)));
    note.textContent = entry && entry.note ? "Edit the note" : "Add a note";
    ring.setAttribute("aria-label", `Pick a mood for ${target.getAttribute("aria-label").split(",").slice(0, 2).join(",")}`);
    const wasOpen = root.classList.contains("is-open");
    root.hidden = false;
    place();
    if (!wasOpen) {
      root.getBoundingClientRect();
      root.classList.add("is-open");
    }
    if (focus) (swatches[(entry ? entry.mood : 3) - 1] || swatches[2]).focus({ preventScroll: true });
  }

  function close({ refocus = false } = {}) {
    if (!cell) return;
    const was = cell;
    cell.classList.remove("is-lifted");
    root.classList.remove("is-open");
    root.hidden = true;
    cell = null;
    day = null;
    if (refocus) was.focus({ preventScroll: true });
  }

  ring.addEventListener("keydown", (e) => {
    const i = swatches.indexOf(document.activeElement);
    if (e.key === "Escape") {
      e.preventDefault();
      close({ refocus: true });
      onDismiss();
    } else if (/^[1-5]$/.test(e.key)) {
      e.preventDefault();
      onPick(day, Number(e.key));
    } else if (e.key === "n" || e.key === "N") {
      e.preventDefault();
      onNote(day);
    } else if (i >= 0 && ["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"].includes(e.key)) {
      e.preventDefault();
      const step = e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 1;
      swatches[(i + step + swatches.length) % swatches.length].focus();
    }
  });

  document.addEventListener(
    "pointerdown",
    (e) => {
      if (!cell) return;
      if (ring.contains(e.target) || e.target.closest(".cell")) return;
      close();
      onDismiss();
    },
    true,
  );

  return { open, close, place, day: () => day, cell: () => cell };
}
