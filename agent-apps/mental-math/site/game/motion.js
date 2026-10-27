// The card's answer feedback and the confetti, on the Web Animations API. Reduced motion keeps the color flash
// and drops every movement.

export const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const motionQuery = matchMedia("(prefers-reduced-motion: reduce)");
export const reduced = () => motionQuery.matches;

const flashTimers = new WeakMap();

function flash(card, cls, ms) {
  clearTimeout(flashTimers.get(card));
  card.classList.remove("flash-ok", "flash-miss");
  void card.offsetWidth;
  card.classList.add(cls);
  flashTimers.set(card, setTimeout(() => card.classList.remove(cls), ms));
}

/** A right answer: the card takes the success tint and pulses for 120 ms. */
export function pulseRight(card) {
  flash(card, "flash-ok", 260);
  if (reduced()) return;
  card.animate([{ transform: "scale(1)" }, { transform: "scale(1.035)" }, { transform: "scale(1)" }], {
    duration: 120,
    easing: "ease-out",
  });
}

/** A wrong answer: the card shakes 3 px, twice. */
export function shakeWrong(card) {
  flash(card, "flash-miss", 320);
  if (reduced()) return;
  card.animate(
    [
      { transform: "translateX(0)" },
      { transform: "translateX(-3px)" },
      { transform: "translateX(3px)" },
      { transform: "translateX(-3px)" },
      { transform: "translateX(3px)" },
      { transform: "translateX(0)" },
    ],
    { duration: 280, easing: "ease-in-out" },
  );
}

/** A small pop for a badge whose number just changed. */
export function pop(node) {
  if (reduced()) return;
  node.animate([{ transform: "scale(1)" }, { transform: "scale(1.14)" }, { transform: "scale(1)" }], {
    duration: 260,
    easing: EASE_OUT,
  });
}

/** The next problem arrives from below. */
export function enter(node) {
  if (reduced()) return;
  node.animate([{ opacity: 0, transform: "translateY(14px)" }, { opacity: 1, transform: "none" }], {
    duration: 200,
    easing: EASE_OUT,
  });
}

const NS = "http://www.w3.org/2000/svg";
const SHAPES = ["rect", "circle", "tri"];

/**
 * Fires `count` confetti shapes on arcs from the center of `origin` into the fixed SVG `layer`: each piece leaves
 * at its own angle and speed and falls under gravity, spinning, then fades.
 */
export function confetti(layer, origin, count = 24, { spread = 1, size = 1 } = {}) {
  if (reduced() || !origin) return;
  const box = origin.getBoundingClientRect();
  const ox = box.left + box.width / 2;
  const oy = box.top + box.height / 2;
  const g = 1500;
  for (let i = 0; i < count; i += 1) {
    const kind = SHAPES[i % SHAPES.length];
    const color = `c${(i % 4) + 1}`;
    const s = (8 + ((i * 7) % 6)) * size;
    let node;
    if (kind === "rect") node = make("rect", { x: ox - s / 2, y: oy - s / 4, width: s, height: s / 2, rx: 1.5 });
    else if (kind === "circle") node = make("circle", { cx: ox, cy: oy, r: s / 2.6 });
    else node = make("path", { d: `M${ox},${oy - s / 2} L${ox + s / 2},${oy + s / 2} L${ox - s / 2},${oy + s / 2} Z` });
    node.setAttribute("class", color);
    layer.append(node);

    const angle = (-90 + (i / (count - 1) - 0.5) * 150 * spread + (Math.random() - 0.5) * 14) * (Math.PI / 180);
    const speed = (520 + Math.random() * 380) * Math.sqrt(size);
    const vx = Math.cos(angle) * speed;
    const vy = Math.sin(angle) * speed;
    const spin = (Math.random() < 0.5 ? -1 : 1) * (360 + Math.random() * 540);
    const duration = 1300 + Math.random() * 500;
    const frames = [];
    const steps = 12;
    for (let k = 0; k <= steps; k += 1) {
      const t = ((k / steps) * duration) / 1000;
      const x = vx * t;
      const y = vy * t + 0.5 * g * t * t;
      frames.push({
        transform: `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) rotate(${(spin * (k / steps)).toFixed(0)}deg)`,
        opacity: k < steps * 0.7 ? 1 : 1 - (k - steps * 0.7) / (steps * 0.3),
      });
    }
    const anim = node.animate(frames, { duration, easing: "linear", fill: "forwards" });
    anim.onfinish = () => node.remove();
  }
}

function make(name, attrs) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
  return node;
}

/**
 * The streak climbed to `n`: the new number springs in, the plate pops, and sparks and a shock ring burst out of it.
 * The burst grows with the streak, and every fifth in a row raises a callout under the plate.
 */
export function burstStreak(plate, num, layer, n) {
  if (reduced()) return;
  num.animate(
    [
      { transform: "translateY(70%) scale(1.5)", opacity: 0 },
      { transform: "translateY(-8%) scale(1.15)", opacity: 1, offset: 0.55 },
      { transform: "none", opacity: 1 },
    ],
    { duration: 420, easing: EASE_OUT },
  );
  const lift = 1.12 + Math.min(n, 8) * 0.02;
  plate.animate([{ transform: "scale(1)" }, { transform: `scale(${lift})` }, { transform: "scale(1)" }], {
    duration: 380,
    easing: "cubic-bezier(0.34, 1.56, 0.64, 1)",
  });

  const reach = 64 + Math.min(n, 8) * 10;
  const count = 14 + Math.min(n, 7) * 2;
  const shock = make("circle", { cx: 0, cy: 0, r: 24, class: "shock" });
  layer.append(shock);
  shock.animate(
    [
      { transform: "scale(0.6)", opacity: 0.9, strokeWidth: 4 },
      { transform: `scale(${(reach / 24) * 1.1})`, opacity: 0, strokeWidth: 0.5 },
    ],
    { duration: 760, easing: EASE_OUT, fill: "forwards" },
  ).onfinish = () => shock.remove();

  for (let i = 0; i < count; i += 1) {
    const angle = (360 / count) * i + (i % 2 ? 9 : 0);
    const len = 12 + (i % 3) * 6;
    const far = reach * (i % 2 ? 0.78 : 1);
    const spark = make("line", { x1: 0, y1: 0, x2: len, y2: 0, class: i % 3 === 2 ? "spark alt" : "spark" });
    layer.append(spark);
    spark.animate(
      [
        { transform: `rotate(${angle}deg) translateX(20px) scaleX(0.4)`, opacity: 1 },
        { transform: `rotate(${angle}deg) translateX(${far * 0.75}px) scaleX(1)`, opacity: 1, offset: 0.6 },
        { transform: `rotate(${angle}deg) translateX(${far}px) scaleX(0.2)`, opacity: 0 },
      ],
      { duration: 820 + (i % 4) * 60, easing: EASE_OUT, fill: "forwards" },
    ).onfinish = () => spark.remove();
  }

  if (n >= 5 && n % 5 === 0) {
    const call = document.createElement("span");
    call.className = "streak-call";
    call.textContent = `${n} in a row`;
    plate.append(call);
    call.animate(
      [
        { transform: "translateY(-6px) scale(0.7)", opacity: 0 },
        { transform: "translateY(0) scale(1.05)", opacity: 1, offset: 0.2 },
        { transform: "translateY(0) scale(1)", opacity: 1, offset: 0.8 },
        { transform: "translateY(4px)", opacity: 0 },
      ],
      { duration: 1400, easing: EASE_OUT, fill: "forwards" },
    ).onfinish = () => call.remove();
  }
}

/** The streak broke: the number drops out and the zero settles in. */
export function dropStreak(num) {
  if (reduced()) return;
  num.animate(
    [
      { transform: "translateY(-40%)", opacity: 0 },
      { transform: "none", opacity: 1 },
    ],
    { duration: 300, easing: EASE_OUT },
  );
}
