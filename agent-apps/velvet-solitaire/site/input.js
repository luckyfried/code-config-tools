// Touch, mouse, and pen on one pointer-event path, and the keyboard. One finger always
// drags a card; two fingers scroll a tall table; a tap that never moved is a tap.

const DRAG_START = 6;

export function bindInput({ surface, session, hud, audio }) {
  const pointers = new Map();
  let primary = null;
  let pan = null;

  const unlock = () => audio.unlock();

  surface.addEventListener("pointerdown", (e) => {
    unlock();
    if (e.button !== undefined && e.button > 0) return;
    session.hideCursor();
    if (session.mode === "demo") {
      session.dealIn();
      return;
    }
    if (hud.menuOpen() || hud.layerOpen()) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) {
      // A second finger: stop any drag and scroll the table instead.
      if (primary && primary.dragging) session.dragCancel();
      primary = null;
      const ys = [...pointers.values()].map((p) => p.y);
      pan = { y: (ys[0] + ys[1]) / 2 };
      return;
    }
    if (pointers.size > 2) return;
    try {
      surface.setPointerCapture(e.pointerId);
    } catch {
      // Capture is a nicety; the drag still works without it.
    }
    primary = { id: e.pointerId, x0: e.clientX, y0: e.clientY, hit: session.hit(e.clientX, e.clientY), dragging: false };
  });

  surface.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pan && pointers.size >= 2) {
      const ys = [...pointers.values()].map((p) => p.y);
      const y = (ys[0] + ys[1]) / 2;
      session.scrollBy(pan.y - y);
      pan.y = y;
      return;
    }
    if (!primary || primary.id !== e.pointerId) return;
    if (!primary.dragging) {
      if (Math.hypot(e.clientX - primary.x0, e.clientY - primary.y0) < DRAG_START) return;
      primary.dragging = session.dragStart(primary.hit, primary.x0, primary.y0);
      if (!primary.dragging) {
        primary = null;
        return;
      }
    }
    session.dragMove(e.clientX, e.clientY);
  });

  const end = (e, cancelled) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pan = null;
    if (!primary || primary.id !== e.pointerId) return;
    if (primary.dragging) {
      if (cancelled) session.dragCancel();
      else session.dragEnd();
    } else if (!cancelled) session.tap(primary.hit);
    primary = null;
  };
  surface.addEventListener("pointerup", (e) => end(e, false));
  surface.addEventListener("pointercancel", (e) => end(e, true));
  surface.addEventListener("lostpointercapture", (e) => {
    if (primary && primary.id === e.pointerId && pointers.has(e.pointerId)) end(e, true);
  });

  surface.addEventListener(
    "wheel",
    (e) => {
      session.scrollBy(e.deltaY);
    },
    { passive: true },
  );

  window.addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "Escape") {
      if (hud.layerOpen()) {
        hud.closeConfirm();
        return;
      }
      if (hud.menuOpen()) {
        hud.closeMenu();
        return;
      }
    }
    if (hud.menuOpen() || hud.layerOpen()) return;
    const target = e.target;
    const inControl = target && target.closest && target.closest("button, input, a, select, textarea");
    // Space and Enter on a focused button press that button; the table takes them otherwise.
    if (inControl && (e.key === " " || e.key === "Enter" || e.key === "Tab")) return;
    if (e.key === "Tab") return;
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    unlock();
    if (session.key(key)) {
      e.preventDefault();
      if (inControl && target.blur) target.blur();
    }
  });
}
