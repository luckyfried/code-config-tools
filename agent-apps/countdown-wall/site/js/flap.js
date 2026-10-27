// Split-flap digits. Only a digit whose value changes flips: the old digit's top half falls toward the viewer about
// the center hinge and darkens as it folds, uncovering the new top; then the new digit's bottom half lands over the
// old bottom and brightens as it flattens. Each half turns on its own, so nothing depends on a 3D back face.

const FALL = "cubic-bezier(0.55, 0, 0.9, 0.45)";
const LAND = "cubic-bezier(0.15, 0.6, 0.35, 1)";
const BLANK = " ";
// The shade at the fold, as a brightness: 1 is flat, lower is darker.
const FOLD = 0.7;

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function half(classes) {
  const node = el("span", `flap-half ${classes}`);
  const glyph = el("b");
  node.append(glyph);
  return { node, glyph };
}

function flipMs() {
  const value = getComputedStyle(document.documentElement).getPropertyValue("--motion-flip").trim();
  return value.endsWith("ms") ? parseFloat(value) : 300;
}

const turn = (depth, deg) => `perspective(${depth}px) rotateX(${deg}deg)`;

export class FlapDigit {
  constructor(value = BLANK) {
    this.value = value;
    this.node = el("span", "flap");
    this.node.setAttribute("aria-hidden", "true");
    this.upper = half("flap-upper");
    this.lower = half("flap-lower");
    this.fall = half("flap-upper flap-fall");
    this.land = half("flap-lower flap-land");
    this.node.append(this.upper.node, this.lower.node, this.fall.node, this.land.node);
    this.running = [];
    this.show(value);
  }

  show(value) {
    for (const part of [this.upper, this.lower, this.fall, this.land]) part.glyph.textContent = value;
  }

  settle() {
    if (this.running.length === 0) return;
    for (const animation of this.running) animation.cancel();
    this.running = [];
    this.show(this.value);
  }

  set(next, { animate = true, delay = 0 } = {}) {
    if (next === this.value) return;
    this.settle();
    const prev = this.value;
    this.value = next;
    const duration = flipMs();
    if (!animate || reduce.matches || duration === 0 || document.hidden) {
      this.show(next);
      return;
    }
    this.upper.glyph.textContent = next;
    this.land.glyph.textContent = next;
    this.fall.glyph.textContent = prev;
    this.lower.glyph.textContent = prev;
    // A deep perspective centered on each half keeps the fold square to the hinge: no sideways lean at any width.
    const depth = Math.max(240, Math.round(this.node.offsetHeight * 6));
    const half = duration / 2;
    const first = { duration: half, delay, easing: FALL, fill: "both" };
    const second = { duration: half, delay: delay + half, easing: LAND, fill: "both" };
    const dim = `brightness(${FOLD})`;
    this.running = [
      this.fall.node.animate(
        [
          { transform: turn(depth, 0), filter: "brightness(1)" },
          { transform: turn(depth, -90), filter: dim },
        ],
        first,
      ),
      this.upper.node.animate([{ filter: "brightness(0.86)" }, { filter: "brightness(1)" }], first),
      this.lower.node.animate([{ filter: "brightness(1)" }, { filter: "brightness(0.86)" }], first),
      this.land.node.animate(
        [
          { transform: turn(depth, 90), filter: dim },
          { transform: turn(depth, 0), filter: "brightness(1)" },
        ],
        second,
      ),
    ];
    const landing = this.running[3];
    landing.onfinish = () => {
      if (this.running[3] !== landing) return;
      this.settle();
    };
  }
}

const UNITS = [
  ["days", "day", "days"],
  ["hours", "hour", "hours"],
  ["minutes", "minute", "minutes"],
  ["seconds", "second", "seconds"],
];

const pad = (n, width) => String(n).padStart(width, "0");

/** A board of unit groups (days, hours, minutes, seconds, or a leading subset), each digit its own flap. */
export class Clock {
  constructor({ className, units = 4, minDayDigits = 2 }) {
    this.node = el("div", `clock ${className}`);
    this.units = UNITS.slice(0, units).map(([key, one, many]) => {
      const node = el("div", `unit unit-${key}`);
      const digits = el("div", "unit-digits");
      const label = el("span", "unit-label");
      node.append(digits, label);
      this.node.append(node);
      return { key, one, many, node, digits, label, flaps: [] };
    });
    this.minDayDigits = minDayDigits;
    this.text = el("span", "visually-hidden");
    this.node.append(this.text);
  }

  /** Shows `p` ({days, hours, minutes, seconds}); a cascade staggers the flips from `delay`, left to right. */
  update(p, { animate = true, delay = 0, stagger = 0 } = {}) {
    let index = 0;
    let digitCount = 0;
    for (const unit of this.units) {
      const value = p[unit.key];
      const width = unit.key === "days" ? Math.max(this.minDayDigits, String(value).length) : 2;
      const text = pad(value, width);
      const fresh = new Set();
      while (unit.flaps.length < width) {
        const flap = new FlapDigit("0");
        fresh.add(flap);
        unit.flaps.unshift(flap);
        unit.digits.prepend(flap.node);
      }
      while (unit.flaps.length > width) unit.flaps.shift().node.remove();
      unit.flaps.forEach((flap, i) => {
        // A new flap appears already showing its digit, unless this update is the opening cascade, which rolls in from 0.
        const flips = fresh.has(flap) ? animate && stagger > 0 : animate;
        flap.set(text[i], { animate: flips, delay: delay + index * stagger });
        index += 1;
      });
      digitCount += width;
      unit.label.textContent = value === 1 ? unit.one : unit.many;
      if (unit.key === "days") this.node.style.setProperty("--day-digits", String(width));
    }
    this.node.style.setProperty("--digits", String(digitCount));
    this.text.textContent = this.units.map((u) => `${p[u.key]} ${p[u.key] === 1 ? u.one : u.many}`).join(", ");
  }
}
