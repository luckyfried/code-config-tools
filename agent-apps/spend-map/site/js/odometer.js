// The month total in large tabular figures that counts to its value: every frame shows one whole amount with only the
// digits it has, so it reads $0, $101, $1,213 on the way up. The first count runs as long as the map draws; later ones
// as long as the map breathes.
export function createOdometer(el, format) {
  let shown = null; // cents on screen now
  let frame = 0;

  function set(value, { duration }) {
    cancelAnimationFrame(frame);
    const from = shown ?? 0;
    el.setAttribute("aria-label", format(value));
    if (duration <= 0 || from === value) {
      shown = value;
      el.textContent = format(value);
      return;
    }
    const t0 = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - t0) / duration);
      shown = Math.round(from + (value - from) * (1 - (1 - t) ** 3));
      el.textContent = format(shown);
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    el.textContent = format(from);
    frame = requestAnimationFrame(tick);
  }

  return { set };
}
