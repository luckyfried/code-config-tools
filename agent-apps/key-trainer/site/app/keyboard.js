// The on-screen keyboard: an SVG of real keycaps drawn in screen pixels, so the bottom edge is 2 px at every size.
// It lights the next key, flashes the warning color under a wrong key, presses keys, and warms into a heat map.

const NS = "http://www.w3.org/2000/svg";
const EDGE = 2;
let instances = 0;

function el(name, attrs, parent) {
  const node = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, String(v));
  if (parent) parent.appendChild(node);
  return node;
}

const r1 = (n) => Math.round(n * 10) / 10;

/** A closed path through `points` with every corner rounded by `radius`, convex or concave. */
function roundedPath(points, radius) {
  const n = points.length;
  let d = "";
  for (let i = 0; i < n; i += 1) {
    const p = points[i];
    const prev = points[(i - 1 + n) % n];
    const next = points[(i + 1) % n];
    const inLen = Math.hypot(p[0] - prev[0], p[1] - prev[1]);
    const outLen = Math.hypot(next[0] - p[0], next[1] - p[1]);
    const r = Math.min(radius, inLen / 2, outLen / 2);
    const a = [p[0] + ((prev[0] - p[0]) / inLen) * r, p[1] + ((prev[1] - p[1]) / inLen) * r];
    const b = [p[0] + ((next[0] - p[0]) / outLen) * r, p[1] + ((next[1] - p[1]) / outLen) * r];
    d += `${i === 0 ? "M" : "L"}${r1(a[0])},${r1(a[1])} Q${r1(p[0])},${r1(p[1])} ${r1(b[0])},${r1(b[1])} `;
  }
  return d + "Z";
}

function isLetter(key) {
  return key.base && key.base.length === 1 && key.shift === key.base.toUpperCase() && key.base.toUpperCase() !== key.base;
}

export class Keyboard {
  constructor(host, options = {}) {
    this.host = host;
    this.fitHeight = options.fitHeight || (() => Infinity);
    this.maxUnit = options.maxUnit || 118;
    this.id = `kb${(instances += 1)}`;
    this.layout = null;
    this.unit = 0;
    this.keys = new Map();
    this.heat = new Map();
    this.next = [];
    this.heatOn = false;
    this.caseEl = document.createElement("div");
    this.caseEl.className = "kb-case";
    host.appendChild(this.caseEl);
    this.resize = this.resize.bind(this);
    if ("ResizeObserver" in window) {
      this.observer = new ResizeObserver(() => this.resize());
      this.observer.observe(host);
    }
    window.addEventListener("resize", this.resize);
  }

  setLayout(layout) {
    this.layout = layout;
    this.unit = 0;
    this.resize(true);
  }

  resize(force) {
    if (!this.layout) return;
    const width = this.host.clientWidth;
    if (!width) return;
    const fromWidth = width / 15.6;
    const fromHeight = (this.fitHeight(this.host) - EDGE) / 5.6;
    const unit = Math.max(17, Math.min(this.maxUnit, fromWidth, fromHeight));
    if (force !== true && Math.abs(unit - this.unit) < 0.5) return;
    this.unit = unit;
    this.render();
  }

  render() {
    const u = this.unit;
    const pad = Math.round(u * 0.3);
    const width = Math.round(15 * u);
    const height = Math.round(5 * u + EDGE);
    this.caseEl.style.setProperty("--case-pad", `${pad}px`);
    const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": `${this.layout.name} keyboard` });
    const defs = el("defs", {}, svg);
    const sheen = el("linearGradient", { id: `${this.id}-sheen`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: 0, class: "sheen-a" }, sheen);
    el("stop", { offset: 1, class: "sheen-b" }, sheen);

    this.keys.clear();
    const gap = Math.max(2, u * 0.065);
    const radius = Math.max(3, u * 0.13);
    const compact = u < 40;
    const fsMain = Math.max(11, u * 0.3);
    const fsSmall = Math.max(9, u * 0.21);
    const fsMod = Math.max(9, u * 0.165);
    const inset = u * 0.14;

    this.layout.rows.forEach((row, ri) => {
      let x = 0;
      row.forEach((key) => {
        const w = (key.w || 1) * u;
        const g = el("g", { class: "key", "data-key": key.code }, svg);
        if (key.code === "KeyF" || key.code === "KeyJ") g.classList.add("is-home");
        if (!key.base || key.base === " ") g.classList.add("is-mod");
        const kx = x + gap / 2;
        const ky = ri * u + gap / 2;
        const kw = w - gap;
        const kh = u - gap - EDGE;
        const tall = key.iso === true;
        const shape = (grow, dy) => {
          if (tall) {
            const lower = 0.25 * u;
            const bottom = ky + u + kh + dy + grow;
            const pts = [
              [kx - grow, ky - grow + dy],
              [kx + kw + grow, ky - grow + dy],
              [kx + kw + grow, bottom],
              [kx + lower - grow, bottom],
              [kx + lower - grow, ky + kh + grow + dy],
              [kx - grow, ky + kh + grow + dy],
            ];
            return { d: roundedPath(pts, radius + grow) };
          }
          return { x: r1(kx - grow), y: r1(ky - grow + dy), width: r1(kw + grow * 2), height: r1(kh + grow * 2), rx: r1(radius + grow) };
        };
        const part = (cls, grow, dy, parent, extra) => {
          const s = shape(grow, dy);
          return el(tall ? "path" : "rect", { class: cls, ...s, ...(extra || {}) }, parent);
        };
        part("flash", Math.max(3, u * 0.07), EDGE / 2, g);
        part("edge", 0, EDGE, g);
        const top = el("g", { class: "top" }, g);
        part("cap", 0, 0, top);
        if (tall) {
          part("face", 0, 0, top, { fill: `url(#${this.id}-sheen)`, opacity: 0.6 });
        } else {
          el("rect", {
            class: "face",
            x: r1(kx + u * 0.08),
            y: r1(ky + u * 0.03),
            width: r1(Math.max(1, kw - u * 0.16)),
            height: r1(Math.max(1, kh * 0.62)),
            rx: r1(Math.max(2, radius * 0.8)),
            fill: `url(#${this.id}-sheen)`,
          }, top);
        }
        part("tint", 0, 0, top);
        part("ring", 2, 0, top);
        this.legends(top, key, { kx, ky, kw, kh, u, compact, fsMain, fsSmall, fsMod, inset });
        if (key.code === "KeyF" || key.code === "KeyJ") {
          // The homing nub: a short raised ridge molded into the cap, lit on top and casting a shadow below.
          const bw = Math.max(7, u * 0.24);
          const bh = Math.max(2.5, u * 0.065);
          const bx = kx + kw / 2 - bw / 2;
          const by = ky + kh * (compact ? 0.8 : 0.74);
          const nub = el("g", { class: "bump" }, top);
          el("rect", { class: "bump-shadow", x: r1(bx - 0.5), y: r1(by + 1), width: r1(bw + 1), height: r1(bh + 0.5), rx: r1(bh / 2 + 0.5) }, nub);
          el("rect", { class: "bump-body", x: r1(bx), y: r1(by), width: r1(bw), height: r1(bh), rx: r1(bh / 2) }, nub);
          el("rect", { class: "bump-shine", x: r1(bx + bh / 2), y: r1(by + 0.5), width: r1(Math.max(1, bw - bh)), height: r1(Math.max(0.8, bh * 0.35)), rx: r1(bh * 0.2) }, nub);
        }
        this.keys.set(key.code, { g, key, x: kx + kw / 2 });
        x += w;
      });
    });

    this.caseEl.replaceChildren(svg);
    this.svg = svg;
    this.applyHeat();
    this.next.forEach((code) => this.keys.get(code)?.g.classList.add("is-next"));
  }

  legends(parent, key, m) {
    const { kx, ky, kw, kh, u, compact, fsMain, fsSmall, fsMod, inset } = m;
    const text = (value, x, y, size, cls, anchor) => {
      const t = el("text", { x: r1(x), y: r1(y), "font-size": r1(size), class: cls || "", "text-anchor": anchor || "start" }, parent);
      t.textContent = value;
      return t;
    };
    if (key.code === "Space") return;
    if (!key.base || key.base === "\n" || key.base === "\t") {
      const label = compact ? key.glyph : key.label;
      if (!label) return;
      const size = compact && key.glyph && key.glyph.length === 1 ? fsSmall * 1.15 : fsMod;
      if (compact) text(label, kx + kw / 2, ky + kh / 2 + size * 0.36, size, "legend-mod", "middle");
      else text(label, kx + inset, ky + kh - inset * 0.85, size, "legend-mod");
      return;
    }
    if (isLetter(key)) {
      if (compact) text(key.shift, kx + kw / 2, ky + kh / 2 + fsMain * 0.36, fsMain, "", "middle");
      else text(key.shift, kx + inset, ky + inset + fsMain * 0.78, fsMain);
      if (key.alt && !compact) text(key.alt, kx + kw - inset, ky + kh - inset * 0.85, fsSmall, "legend-2", "end");
      return;
    }
    const two = key.shift && key.shift !== key.base;
    if (compact) {
      if (two) {
        text(key.shift, kx + kw / 2, ky + kh * 0.42, fsSmall, "legend-2", "middle");
        text(key.base, kx + kw / 2, ky + kh * 0.86, fsSmall * 1.05, "", "middle");
      } else {
        text(key.base, kx + kw / 2, ky + kh / 2 + fsSmall * 0.4, fsSmall * 1.1, "", "middle");
      }
      return;
    }
    const size = fsSmall * 1.12;
    if (two) {
      text(key.shift, kx + inset, ky + inset + size * 0.8, size);
      text(key.base, kx + inset, ky + kh - inset * 0.85, size);
    } else {
      text(key.base, kx + inset, ky + inset + size * 0.8, size);
    }
    if (key.alt) text(key.alt, kx + kw - inset, ky + kh - inset * 0.85, fsSmall * 0.95, "legend-2", "end");
  }

  /** Lights the key that types `char`, and the shift or alt gr it needs. */
  setNext(char) {
    this.next.forEach((code) => this.keys.get(code)?.g.classList.remove("is-next"));
    this.next = [];
    if (char == null || !this.layout) return;
    const spot = this.locate(char);
    if (!spot) return;
    const codes = [spot.key.code];
    if (spot.level === "shift") {
      const at = this.keys.get(spot.key.code);
      codes.push(at && at.x < 7.5 * this.unit ? "ShiftRight" : "ShiftLeft");
    } else if (spot.level === "alt") {
      codes.push("AltRight");
    }
    this.next = codes;
    codes.forEach((code) => this.keys.get(code)?.g.classList.add("is-next"));
  }

  locate(char) {
    if (!this.layout) return null;
    return this.layout.byChar.get(char) || this.layout.byChar.get(char.normalize("NFD").replace(/[̀-ͯ]/g, "")) || null;
  }

  press(code) {
    const k = this.keys.get(code);
    if (!k) return;
    k.g.classList.add("is-down");
    clearTimeout(k.up);
    k.up = setTimeout(() => k.g.classList.remove("is-down"), 95);
  }

  pressChar(char) {
    const spot = this.locate(char);
    if (spot) this.press(spot.key.code);
  }

  /** The warning flash: the theme's warning color spills out from under the key that was hit by mistake. */
  flash(char) {
    const spot = this.locate(char);
    if (spot) this.flashCode(spot.key.code);
  }

  flashCode(code) {
    const k = this.keys.get(code);
    if (!k) return;
    // Held at full strength long enough to be seen, then let go; is-wrong's transition fades it out.
    k.g.classList.add("is-wrong");
    clearTimeout(k.wrong);
    k.wrong = setTimeout(() => k.g.classList.remove("is-wrong"), 320);
    this.press(code);
  }

  /** Heat per key code, 0 to 1; shown when the heat map is on. */
  setHeat(map) {
    this.heat = map || new Map();
    this.applyHeat();
  }

  applyHeat() {
    const span = 15 * this.unit || 1;
    for (const [code, k] of this.keys) {
      const value = this.heat.get(code) || 0;
      k.g.style.setProperty("--heat", value.toFixed(3));
      k.g.style.setProperty("--delay", `${Math.round((k.x / span) * 220)}ms`);
      k.g.classList.toggle("is-hot", value > 0.55);
    }
  }

  showHeat(on) {
    this.heatOn = on;
    this.host.classList.toggle("is-heat", on);
  }
}
