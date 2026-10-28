// Pointer and keyboard on the shelf. One pointer-event path serves mouse and touch: a mouse points at a spine to
// pull it out and clicks to open; a finger taps once to pull it out and again to open. Dragging scrolls along the
// wall or the row; a vertical swipe on a phone steps between rows. Arrows walk the books; Enter opens; Escape closes.
export function attachInput(canvas, ctl) {
  const drag = { id: null, x: 0, y: 0, sx: 0, sy: 0, t: 0, moved: false, type: "mouse", lastX: 0, lastT: 0, vx: 0 };

  canvas.addEventListener("pointermove", (e) => {
    const w = canvas.clientWidth || 1;
    const h = canvas.clientHeight || 1;
    if (e.pointerType === "mouse") ctl.parallax((e.clientX / w) * 2 - 1, (e.clientY / h) * 2 - 1);
    if (drag.id === e.pointerId) {
      const dx = e.clientX - drag.x;
      const total = Math.hypot(e.clientX - drag.sx, e.clientY - drag.sy);
      if (total > 8) drag.moved = true;
      if (drag.moved && Math.abs(e.clientX - drag.sx) > Math.abs(e.clientY - drag.sy) * 0.8) ctl.dragBy(dx);
      const now = performance.now();
      const dt = Math.max(1, now - drag.lastT);
      drag.vx = drag.vx * 0.6 + (dx / dt) * 0.4;
      drag.lastT = now;
      drag.x = e.clientX;
      drag.y = e.clientY;
      return;
    }
    if (e.pointerType === "mouse") ctl.pointAt(e.clientX, e.clientY);
  });

  canvas.addEventListener("pointerdown", (e) => {
    ctl.interrupt();
    canvas.setPointerCapture(e.pointerId);
    Object.assign(drag, { id: e.pointerId, x: e.clientX, y: e.clientY, sx: e.clientX, sy: e.clientY, t: performance.now(), moved: false, type: e.pointerType, lastT: performance.now(), vx: 0 });
  });

  const end = (e) => {
    if (drag.id !== e.pointerId) return;
    drag.id = null;
    const dx = e.clientX - drag.sx;
    const dy = e.clientY - drag.sy;
    if (!drag.moved) {
      ctl.tap(e.clientX, e.clientY, drag.type);
      return;
    }
    if (Math.abs(dy) > 50 && Math.abs(dy) > Math.abs(dx) * 1.2) ctl.swipeRow(dy < 0 ? 1 : -1);
    else ctl.fling(drag.vx);
  };
  canvas.addEventListener("pointerup", end);
  canvas.addEventListener("pointercancel", (e) => {
    if (drag.id === e.pointerId) drag.id = null;
  });
  canvas.addEventListener("pointerleave", (e) => {
    if (e.pointerType === "mouse" && drag.id === null) ctl.pointAt(null, null);
  });

  let wheelRowLock = 0;
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      ctl.interrupt();
      const now = performance.now();
      const dx = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : 0;
      if (ctl.rowMode() && !dx) {
        if (now > wheelRowLock && Math.abs(e.deltaY) > 12) {
          ctl.swipeRow(e.deltaY > 0 ? 1 : -1);
          wheelRowLock = now + 450;
        }
        return;
      }
      ctl.dragBy(-(dx || e.deltaY) * 0.9);
    },
    { passive: false },
  );

  window.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
      if (e.key === "Escape") e.target.blur();
      return;
    }
    if (e.key === "Escape") {
      ctl.escape();
      return;
    }
    const inPanel = e.target && e.target.closest && e.target.closest(".panel, .reader, .top");
    if (inPanel) return;
    const map = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    if (map[e.key]) {
      e.preventDefault();
      ctl.interrupt();
      ctl.walk(...map[e.key]);
    } else if (e.key === "Enter" || e.key === " ") {
      if (e.target === canvas || e.target === document.body) {
        e.preventDefault();
        ctl.openFocused();
      }
    }
  });
}
