// The sample run that plays when the page opens: a steady typist working through the line, with a slip or two,
// until the person presses a key and takes over.

import { seeded } from "./text.js";

export class Ghost {
  constructor({ type, done }) {
    this.type = type;
    this.done = done;
    this.timer = 0;
    this.running = false;
  }

  /** Types `chars` for about `ms` milliseconds, slipping at the positions in `slips`. */
  start(chars, { ms = 5200, slips = [12, 43], seed = 1, wrongFor }) {
    this.stop();
    this.running = true;
    const rand = seeded(seed);
    const began = performance.now();
    let i = 0;
    const slipped = new Set();
    const step = () => {
      if (!this.running) return;
      if (performance.now() - began > ms || i >= chars.length) {
        this.running = false;
        this.done();
        return;
      }
      const ch = chars[i];
      if (slips.includes(i) && !slipped.has(i)) {
        slipped.add(i);
        this.type(wrongFor(ch) || "x");
        this.timer = setTimeout(step, 230 + rand() * 60);
        return;
      }
      this.type(ch);
      i += 1;
      const pause = ch === " " ? 150 : ch === "." || ch === "," ? 230 : 112;
      this.timer = setTimeout(step, pause + rand() * 70);
    };
    this.timer = setTimeout(step, 180);
  }

  stop() {
    this.running = false;
    clearTimeout(this.timer);
  }
}
