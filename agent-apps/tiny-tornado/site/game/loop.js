// A fixed 60 Hz simulation under a display-rate render.
const STEP = 1 / 60;

export function createLoop({ step, render }) {
  let last = 0;
  let acc = 0;
  let running = false;
  function frame(now) {
    if (!running) return;
    requestAnimationFrame(frame);
    const ms = last ? now - last : STEP * 1000;
    last = now;
    acc += Math.min(ms / 1000, 0.1);
    let steps = 0;
    while (acc >= STEP && steps < 4) {
      step(STEP);
      acc -= STEP;
      steps++;
    }
    if (steps === 4) acc = 0;
    render(Math.min(ms / 1000, 0.1), ms);
  }
  return {
    start() {
      if (running) return;
      running = true;
      last = 0;
      requestAnimationFrame(frame);
    },
    stop() {
      running = false;
    },
  };
}
