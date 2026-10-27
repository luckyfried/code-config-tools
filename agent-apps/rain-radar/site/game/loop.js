// The radar loop: each frame holds, then crossfades into the next; the last frame holds longer, then the loop
// fades back to the first. Under reduced motion it never plays by itself and the frames step.

const DWELL = { slow: 0.9, normal: 0.55, fast: 0.3 };
const END_HOLD = 1.6;

export function createPlayback(count, { speed = "normal", start = 0, playing = true, stepped = false } = {}) {
  let pos = start; // frame index plus the part of the way to the next one
  let wrap = 0; // seconds spent past the last frame
  const pb = {
    playing,
    speed,
    count,
    get position() {
      return pos;
    },
    seek(p) {
      pos = Math.max(0, Math.min(count - 1, p));
      wrap = 0;
    },
    step(by) {
      pb.seek(Math.round(pos) + by);
    },
    update(dt) {
      if (!pb.playing || count < 2) return;
      const dwell = DWELL[pb.speed] ?? DWELL.normal;
      if (pos >= count - 1) {
        wrap += dt;
        if (wrap >= END_HOLD + dwell) {
          pos = 0;
          wrap = 0;
        }
        return;
      }
      pos = Math.min(count - 1, pos + dt / dwell);
    },
    // which two frames show, how far the fade between them has gone, and where the playhead sits (0 to 1)
    view() {
      if (count < 2) return { a: 0, b: 0, mix: 0, head: 1, fade: 1 };
      const dwell = DWELL[pb.speed] ?? DWELL.normal;
      if (pos >= count - 1 && wrap > END_HOLD) {
        const t = Math.min(1, (wrap - END_HOLD) / dwell);
        const m = t * t * (3 - 2 * t);
        return { a: count - 1, b: 0, mix: m, head: 1 - m, fade: Math.abs(1 - 2 * m) };
      }
      const a = Math.floor(pos);
      const f = pos - a;
      const b = Math.min(count - 1, a + 1);
      const x = stepped ? 0 : Math.max(0, Math.min(1, (f - 0.45) / 0.55));
      const m = x * x * (3 - 2 * x);
      return { a, b, mix: m, head: (a + m) / (count - 1), fade: 1 };
    },
  };
  return pb;
}
