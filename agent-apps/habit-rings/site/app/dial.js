// The dial: up to five concentric rings, one per habit from the outside in, each drawn clockwise from twelve o'clock.
// A tap on a ring closes it; a swipe across the dial moves the day.
import { icon } from "./icons.js";

const NS = "http://www.w3.org/2000/svg";
const C = 120;
const OUTER = 118;
const HOLE = 34;
export const DIAL_MAX = 5;
const DRAW = "cubic-bezier(0.22, 1, 0.36, 1)";

const el = (name, attrs) => {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
};

export function createDial({ root, habits, onTap, onSwipe, reduced }) {
  const svg = root.querySelector(".dial-svg");
  const glow = root.querySelector(".dial-glow");
  const center = root.querySelector(".dial-center");
  const shown = habits.slice(0, DIAL_MAX);
  const step = Math.min(30, (OUTER - HOLE) / shown.length);
  const width = step * 0.8;
  const radii = shown.map((_, i) => OUTER - width / 2 - i * step);

  const turn = el("g", { transform: `rotate(-90 ${C} ${C})` });
  const rings = shown.map((habit, i) => {
    const group = el("g", { class: "ring-g" });
    group.style.setProperty("--hue", `var(--habit-${i + 1})`);
    group.append(
      el("circle", { class: "track", cx: C, cy: C, r: radii[i], "stroke-width": width }),
    );
    const ring = el("circle", { class: "ring is-empty", cx: C, cy: C, r: radii[i], "stroke-width": width, pathLength: 100, "data-habit": habit.id });
    ring.style.setProperty("--offset", "100");
    group.append(ring);
    turn.append(group);
    return { group, ring, value: 0 };
  });
  svg.append(turn);
  svg.setAttribute("aria-label", `Rings for ${shown.map((h) => h.label).join(", ")}`);

  const offset = (p) => String(Math.round((1 - p) * 1000) / 10);

  /** Moves every ring to `values` (0 to 1 each). `draw` plays the opening: each ring sweeps in, 80 ms after the last. */
  function set(values, { draw = false } = {}) {
    rings.forEach((item, i) => {
      const p = values[i] ?? 0;
      item.ring.style.setProperty("--offset", offset(p));
      item.ring.classList.toggle("is-empty", p <= 0);
      if (draw && !reduced() && p > 0) {
        item.ring.animate([{ strokeDashoffset: "100" }, { strokeDashoffset: offset(p) }], {
          duration: 900,
          delay: 120 + i * 80,
          easing: DRAW,
          fill: "backwards",
        });
      }
      item.value = p;
    });
  }

  /** The snap when a ring closes: a 1.08 overshoot and a soft glow behind the dial in the ring's color. */
  function snap(index) {
    if (reduced()) return;
    if (index < rings.length) {
      rings[index].group.animate(
        [{ transform: "scale(1)" }, { transform: "scale(1.08)", offset: 0.42 }, { transform: "scale(1)" }],
        { duration: 560, easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
      );
    }
    bloom(`var(--habit-${index + 1})`);
  }

  function bloom(color, strength = 1) {
    if (reduced()) return;
    glow.style.setProperty("--glow-color", color);
    const peak = parseFloat(getComputedStyle(glow).getPropertyValue("--glow-strength")) || 0.5;
    glow.animate(
      [
        { opacity: 0, transform: "scale(0.82)" },
        { opacity: peak * strength, transform: "scale(1)", offset: 0.3 },
        { opacity: 0, transform: "scale(1.12)" },
      ],
      { duration: 1100, easing: "cubic-bezier(0.22, 1, 0.36, 1)" },
    );
  }

  function setCenter(closed, total) {
    center.replaceChildren();
    if (closed === total && total > 0) center.append(icon("check"));
    else center.textContent = `${closed}/${total}`;
  }

  /** Slides the rings in from the side the day came from. */
  function slide(direction) {
    if (reduced()) return;
    svg.animate([{ transform: `translateX(${direction * 26}px)`, opacity: 0.4 }, { transform: "translateX(0)", opacity: 1 }], {
      duration: 320,
      easing: DRAW,
    });
  }

  // One pointer path for touch and mouse: a short press is a tap on the ring under it, a sideways drag is a swipe.
  let press = null;
  root.addEventListener("pointerdown", (event) => {
    if (event.button > 0) return;
    press = { id: event.pointerId, x: event.clientX, y: event.clientY, dx: 0, dragging: false };
  });
  root.addEventListener("pointermove", (event) => {
    if (!press || event.pointerId !== press.id) return;
    const dx = event.clientX - press.x;
    const dy = event.clientY - press.y;
    if (!press.dragging && Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
      press.dragging = true;
      root.classList.add("is-dragging");
      try {
        root.setPointerCapture(event.pointerId);
      } catch {
        // A pointer that is already gone cannot be captured; the drag still follows it.
      }
    }
    if (press.dragging) {
      press.dx = dx;
      root.style.setProperty("--drag", `${Math.round(dx * 0.4)}px`);
    }
  });
  const release = (event, cancelled) => {
    if (!press || event.pointerId !== press.id) return;
    const { dragging, dx } = press;
    const moved = Math.hypot(event.clientX - press.x, event.clientY - press.y);
    press = null;
    root.classList.remove("is-dragging");
    root.style.setProperty("--drag", "0px");
    if (cancelled) return;
    if (dragging) {
      if (dx > 56) onSwipe(-1);
      else if (dx < -56) onSwipe(1);
      return;
    }
    if (moved > 8) return;
    const box = svg.getBoundingClientRect();
    const scale = 240 / box.width;
    const x = (event.clientX - box.left) * scale - C;
    const y = (event.clientY - box.top) * scale - C;
    const distance = Math.hypot(x, y);
    const hit = radii.findIndex((r) => Math.abs(distance - r) <= step / 2);
    if (hit >= 0) onTap(hit);
  };
  root.addEventListener("pointerup", (event) => release(event, false));
  root.addEventListener("pointercancel", (event) => release(event, true));

  return { set, snap, bloom, setCenter, slide, count: rings.length };
}
