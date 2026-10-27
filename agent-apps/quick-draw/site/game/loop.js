// The loop: game logic in fixed 60 Hz steps with an accumulator, the scene drawn once per animation frame, a time
// scale for the slow motion of the shot, and a pause while the tab is hidden.
const STEP = 1 / 60;

export function createLoop({ step, frame }) {
  let last = null;
  let acc = 0;
  let running = false;
  let gameTime = 0;
  let realTime = 0;
  const clock = { scale: 1, target: 1, rate: 0 };

  function tick(now) {
    if (!running) return;
    requestAnimationFrame(tick);
    if (last === null) last = now;
    const real = Math.min(0.1, (now - last) / 1000);
    last = now;
    realTime += real;
    acc += real;
    let steps = 0;
    while (acc >= STEP && steps < 5) {
      if (clock.rate > 0) {
        const d = clock.target - clock.scale;
        clock.scale += Math.sign(d) * Math.min(Math.abs(d), clock.rate * STEP);
      } else clock.scale = clock.target;
      const dt = STEP * clock.scale;
      gameTime += dt;
      step(dt, STEP, gameTime);
      acc -= STEP;
      steps += 1;
    }
    if (steps === 5) acc = 0;
    frame(real, now, gameTime, realTime, real * clock.scale);
  }

  function start() {
    if (running) return;
    running = true;
    last = null;
    requestAnimationFrame(tick);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) running = false;
    else start();
  });

  return {
    start,
    clock,
    /** Eases the time scale to `target` at `rate` per second; rate 0 jumps. */
    timeScale(target, rate = 0) {
      clock.target = target;
      clock.rate = rate;
      if (rate === 0) clock.scale = target;
    },
    get gameTime() {
      return gameTime;
    },
    get realTime() {
      return realTime;
    },
  };
}
