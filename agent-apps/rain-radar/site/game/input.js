// Moving the map: one finger or the mouse drags it, two fingers or the wheel zoom it, and the keys + and - zoom.

export function attachInput(canvas, rig, onMove) {
  const pointers = new Map();
  let pinch = 0;

  const spread = () => {
    const [a, b] = [...pointers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  };

  canvas.addEventListener("pointerdown", (e) => {
    canvas.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 2) pinch = spread();
  });
  canvas.addEventListener("pointermove", (e) => {
    const p = pointers.get(e.pointerId);
    if (!p) return;
    if (pointers.size === 1) {
      rig.pan(e.clientX - p.x, e.clientY - p.y);
      onMove();
    }
    p.x = e.clientX;
    p.y = e.clientY;
    if (pointers.size === 2) {
      const s = spread();
      if (pinch > 0 && s > 0) rig.zoomBy(pinch / s);
      pinch = s;
      onMove();
    }
  });
  const up = (e) => {
    pointers.delete(e.pointerId);
    pinch = 0;
  };
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      rig.zoomBy(Math.exp(e.deltaY * 0.0015));
      onMove();
    },
    { passive: false },
  );
  addEventListener("keydown", (e) => {
    if (e.target.closest?.("input, dialog")) return;
    if (e.key === "+" || e.key === "=") rig.zoomBy(0.85);
    else if (e.key === "-") rig.zoomBy(1 / 0.85);
    else return;
    onMove();
  });
}
