// A small clock face per row: the face takes the sky color of that city's current hour, and the seconds hand ticks.
import { wall } from "./zones.js";
import { skyAt } from "./sky.js";

const NS = "http://www.w3.org/2000/svg";

function el(name, attrs) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

export function createDial(zone) {
  const svg = el("svg", { viewBox: "0 0 40 40", class: "dial", "aria-hidden": "true" });
  svg.append(el("circle", { cx: 20, cy: 20, r: 18.5, class: "dial-face" }));
  for (let i = 0; i < 12; i++) {
    const a = (i * Math.PI) / 6;
    const r0 = i % 3 === 0 ? 13.6 : 15;
    svg.append(el("line", {
      x1: 20 + Math.sin(a) * r0, y1: 20 - Math.cos(a) * r0,
      x2: 20 + Math.sin(a) * 16.6, y2: 20 - Math.cos(a) * 16.6, class: "dial-tick",
    }));
  }
  const hour = el("line", { x1: 20, y1: 21.5, x2: 20, y2: 11, class: "hand hand-hour" });
  const minute = el("line", { x1: 20, y1: 22, x2: 20, y2: 6.5, class: "hand hand-minute" });
  const second = el("line", { x1: 20, y1: 24, x2: 20, y2: 4.5, class: "hand hand-second" });
  svg.append(hour, minute, second, el("circle", { cx: 20, cy: 20, r: 2.2, class: "dial-pin" }));

  let base = null; // the seconds count at the first draw, so the hand angle only ever grows and never spins back
  let lastFace = -1;
  let lastPalette = null;
  return {
    svg,
    draw(now, palette) {
      const w = wall(zone, now);
      const total = Math.floor(now / 1000);
      if (base === null) base = total - w.s;
      hour.style.setProperty("--a", `${(w.h % 12) * 30 + w.mi * 0.5}deg`);
      minute.style.setProperty("--a", `${w.mi * 6 + w.s * 0.1}deg`);
      second.style.setProperty("--a", `${(total - base) * 6}deg`);
      const faceMinute = w.h * 60 + w.mi;
      if (faceMinute !== lastFace || palette !== lastPalette) {
        lastFace = faceMinute;
        lastPalette = palette;
        const sky = skyAt(palette, faceMinute);
        svg.style.setProperty("--face", sky.css);
        svg.classList.toggle("on-light", sky.light);
      }
    },
  };
}
