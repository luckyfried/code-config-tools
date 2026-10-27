// The loop: fixed 60 Hz updates from an accumulator, one render per animation frame, paused while the page is
// hidden so a run never jumps ahead in a background tab.
import { STEP } from "./rail.js";

export function startLoop({ fixed, frame }) {
  let last = performance.now();
  let acc = 0;
  let running = true;
  let handle = 0;

  const tick = (now) => {
    handle = requestAnimationFrame(tick);
    // The first frame's timestamp can predate `last`; a negative step would throw every easing backward.
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    acc += dt;
    let steps = 0;
    while (acc >= STEP && steps < 6) {
      fixed(STEP);
      acc -= STEP;
      steps += 1;
    }
    if (steps === 6) acc = 0;
    frame(dt, acc / STEP, now);
  };

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      running = false;
      cancelAnimationFrame(handle);
    } else if (!running) {
      running = true;
      last = performance.now();
      acc = 0;
      handle = requestAnimationFrame(tick);
    }
  });

  handle = requestAnimationFrame(tick);
}
