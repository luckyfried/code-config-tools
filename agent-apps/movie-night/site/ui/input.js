// Pointer, wheel, and hover input for the wall. One code path for touch and mouse: a drag moves the wall, a flick
// carries on with inertia, a tap goes to that poster (or picks it when it is already in front).

export function bindWall(el, { glide, pxPerPoster, onTap, onHover }) {
  let id = null;
  let lastX = 0;
  let moved = 0;
  let downAt = 0;
  let samples = [];
  let wheelAcc = 0;
  let wheelAt = 0;

  el.addEventListener("pointerdown", (e) => {
    if (e.button > 0 || id !== null) return;
    id = e.pointerId;
    el.setPointerCapture(id);
    lastX = e.clientX;
    moved = 0;
    downAt = e.timeStamp;
    samples = [{ x: e.clientX, t: e.timeStamp }];
    glide.grab();
    el.classList.add("is-dragging");
  });

  el.addEventListener("pointermove", (e) => {
    if (e.pointerId === id) {
      const dx = e.clientX - lastX;
      lastX = e.clientX;
      moved += Math.abs(dx);
      glide.drag(-dx / pxPerPoster());
      samples.push({ x: e.clientX, t: e.timeStamp });
      while (samples.length > 2 && e.timeStamp - samples[0].t > 90) samples.shift();
    } else if (e.pointerType === "mouse" && id === null) {
      onHover(e.clientX, e.clientY);
    }
  });

  const end = (e, cancelled) => {
    if (e.pointerId !== id) return;
    if (el.hasPointerCapture(id)) el.releasePointerCapture(id);
    id = null;
    el.classList.remove("is-dragging");
    const first = samples[0];
    const span = Math.max(e.timeStamp - first.t, 1);
    const velocity = (-(e.clientX - first.x) / span) * 1000 / pxPerPoster();
    if (!cancelled && moved < 8 && e.timeStamp - downAt < 450) {
      glide.release(0);
      onTap(e.clientX, e.clientY);
    } else {
      glide.release(Math.max(-14, Math.min(14, velocity)));
    }
  };
  el.addEventListener("pointerup", (e) => end(e, false));
  el.addEventListener("pointercancel", (e) => end(e, true));
  el.addEventListener("pointerleave", (e) => {
    if (e.pointerType === "mouse" && id === null) onHover(-1, -1);
  });

  el.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      if (e.timeStamp - wheelAt > 220) wheelAcc = 0;
      wheelAt = e.timeStamp;
      wheelAcc += e.deltaMode === 1 ? delta * 30 : delta;
      if (Math.abs(wheelAcc) >= 60) {
        glide.nudge(Math.sign(wheelAcc));
        wheelAcc = 0;
      }
    },
    { passive: false },
  );
}
