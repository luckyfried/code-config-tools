// The SVG ring: a stroke that drains with the time left, minute ticks, and a dot that sweeps the seconds.
const R = 186;
const C = 2 * Math.PI * R;
const NS = "http://www.w3.org/2000/svg";

// `scope` carries --heat and --final, so the dial and the live block on the strip warm together.
export function createRing({ fill, sec, ticks, scope }) {
  for (let i = 0; i < 60; i++) {
    const major = i % 5 === 0;
    const a = (i / 60) * 2 * Math.PI;
    const r1 = major ? 158 : 162;
    const r2 = 168;
    const line = document.createElementNS(NS, "line");
    line.setAttribute("x1", (200 + r1 * Math.sin(a)).toFixed(2));
    line.setAttribute("y1", (200 - r1 * Math.cos(a)).toFixed(2));
    line.setAttribute("x2", (200 + r2 * Math.sin(a)).toFixed(2));
    line.setAttribute("y2", (200 - r2 * Math.cos(a)).toFixed(2));
    if (major) line.setAttribute("class", "is-major");
    ticks.append(line);
  }
  let lastHeat = -1;
  let lastFinal = -1;
  return {
    // frac is the share of the block still to go, from 1 (full) to 0 (empty).
    fill(frac) {
      const len = Math.max(0, Math.min(1, frac)) * C;
      fill.setAttribute("stroke-dasharray", `${len.toFixed(2)} ${C.toFixed(2)}`);
      fill.setAttribute("stroke-dashoffset", (-(C - len)).toFixed(2));
      fill.classList.toggle("is-empty", len < 0.5);
    },
    heat(h) {
      const v = Math.round(Math.max(0, Math.min(1, h)) * 1000) / 1000;
      if (v === lastHeat) return;
      lastHeat = v;
      scope.style.setProperty("--heat", String(v));
    },
    // f runs from 0 to 1 over a block's last seconds, when the drained track and the halo burn ember.
    final(f) {
      const v = Math.round(Math.max(0, Math.min(1, f)) * 100) / 100;
      if (v === lastFinal) return;
      lastFinal = v;
      scope.style.setProperty("--final", String(v));
    },
    // ms is the time spent in the block so far, or null to hide the dot.
    seconds(ms) {
      if (ms === null) {
        sec.classList.add("is-off");
        return;
      }
      sec.classList.remove("is-off");
      sec.style.setProperty("--sec", `${(((ms % 60000) / 60000) * 360).toFixed(2)}deg`);
    },
  };
}
