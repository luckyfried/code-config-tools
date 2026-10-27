// Turns taps, drags, keys, and typed moves into squares and moves. A tap picks a square; a drag on a desktop turns
// the table a little; arrow keys walk a cursor over the board and Space acts on it; the typed-move box takes SAN.
const FILES = "abcdefgh";

export function bindPointer(canvas, world, { onSquare, canOrbit }) {
  let down = null;
  canvas.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    down = { x: e.clientX, y: e.clientY, drag: 0, dragEl: 0, moved: false, id: e.pointerId };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!down || e.pointerId !== down.id) return;
    const dx = e.clientX - down.x, dy = e.clientY - down.y;
    if (!down.moved && Math.hypot(dx, dy) > 7 && canOrbit()) {
      down.moved = true;
      down.drag = world.view.drag;
      down.dragEl = world.view.dragElevation;
    }
    if (down.moved) {
      world.view.drag = Math.max(-0.6, Math.min(0.6, down.drag - dx * 0.004));
      world.view.dragElevation = Math.max(-0.3, Math.min(0.28, down.dragEl + dy * 0.003));
    }
  });
  const up = (e) => {
    if (!down || e.pointerId !== down.id) return;
    if (!down.moved) {
      const sq = world.pick(e.clientX, e.clientY);
      if (sq) onSquare(sq);
    }
    down = null;
  };
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", () => { down = null; });
}

// Arrow keys move the cursor in the direction they point on screen, whichever side is near.
export function bindKeys(canvas, { getCursor, setCursor, getSide, onSquare, onEscape }) {
  canvas.addEventListener("keydown", (e) => {
    const steps = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
    if (steps[e.key]) {
      e.preventDefault();
      const cur = getCursor() ?? (getSide() === "w" ? "e2" : "e7");
      const flip = getSide() === "b" ? -1 : 1;
      const f = Math.max(0, Math.min(7, FILES.indexOf(cur[0]) + steps[e.key][0] * flip));
      const r = Math.max(1, Math.min(8, Number(cur[1]) + steps[e.key][1] * flip));
      setCursor(FILES[f] + r);
    } else if (e.key === " " || e.key === "Enter") {
      e.preventDefault();
      const cur = getCursor();
      if (cur) onSquare(cur); else setCursor(getSide() === "w" ? "e2" : "e7");
    } else if (e.key === "Escape") {
      onEscape();
    }
  });
}

// Finds the legal move a person typed: SAN with or without check marks, capture marks, or a capital, "0-0" for
// castling, or squares like e2e4.
export function parseTyped(text, legal) {
  const clean = text.trim().replace(/[+#!?]/g, "").replace(/0/g, "O").replace(/\s+/g, "");
  if (!clean) return null;
  const squares = clean.toLowerCase().match(/^([a-h][1-8])-?([a-h][1-8])=?([qrbn])?$/);
  if (squares) return legal.find((m) => m.from === squares[1] && m.to === squares[2] && (!m.promotion || m.promotion === (squares[3] ?? "q"))) ?? null;
  const bare = (s) => s.replace(/[+#x=]/g, "");
  const want = bare(clean);
  return legal.find((m) => bare(m.san) === want)
    ?? legal.find((m) => bare(m.san).toLowerCase() === want.toLowerCase() && !/^[a-h]/.test(want) === !/^[a-h]/.test(m.san))
    ?? null;
}
