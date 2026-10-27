// The brass wheel, drawn with canvas 2D: matte black slices sized by hearts, a brass rim with teeth, and a flapper
// that each tooth knocks aside. A spin eases out, runs a little past its slice, and settles back with a bounce.
// With reduced motion the wheel stays still and a light steps from slice to slice instead.
import { tick, chime } from "./audio.js";
import { spring } from "../game/motion.js";

const TAU = Math.PI * 2;
const TEETH = 36;
const TOOTH = TAU / TEETH;
const POINTER = -Math.PI / 2;
const mod = (a, m) => ((a % m) + m) % m;

function annulus(g, c, outer, inner) {
  g.beginPath();
  g.arc(c, c, outer, 0, TAU);
  g.arc(c, c, inner, 0, TAU, true);
}

export class Wheel {
  constructor(canvas, reduced) {
    this.canvas = canvas;
    this.g = canvas.getContext("2d");
    this.reduced = reduced;
    this.slices = [];
    this.colors = {};
    this.rot = 0;
    this.flap = { x: 0, v: 0 };
    this.anim = null;
    this.win = -1;
    this.glow = 0;
    this.light = -1;
    this.size = 0;
    this.dirty = true;
    this.lastTooth = 0;
    this.needs = true;
  }

  setColors(colors) {
    this.colors = colors;
    this.dirty = true;
    this.needs = true;
  }

  setSlices(list) {
    const total = list.reduce((n, s) => n + s.weight, 0) || 1;
    let a = 0;
    const winKey = this.slices[this.win]?.key;
    this.slices = list.map((s) => {
      const a0 = a;
      a += (s.weight / total) * TAU;
      return { ...s, a0, a1: a };
    });
    this.win = this.slices.findIndex((s) => s.key === winKey);
    this.dirty = true;
    this.needs = true;
  }

  get spinning() {
    return !!this.anim;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const px = Math.round(rect.width * dpr);
    if (px > 0 && px !== this.size) {
      this.size = px;
      this.canvas.width = px;
      this.canvas.height = px;
      this.dirty = true;
      this.needs = true;
    }
  }

  layer() {
    const c = document.createElement("canvas");
    c.width = c.height = this.size;
    return c;
  }

  build() {
    const S = this.size;
    const c = S / 2;
    const R = S / 2;
    const k = this.colors;
    this.ring = this.layer();
    let g = this.ring.getContext("2d");
    g.save();
    g.shadowColor = "rgba(0,0,0,0.38)";
    g.shadowBlur = R * 0.07;
    g.shadowOffsetY = R * 0.03;
    g.fillStyle = k["wheel-bezel"];
    g.beginPath();
    g.arc(c, c, R * 0.955, 0, TAU);
    g.fill();
    g.restore();
    const brass = g.createConicGradient(POINTER + 0.5, c, c);
    [
      [0, "wheel-brass-hi"],
      [0.1, "wheel-brass"],
      [0.27, "wheel-brass-lo"],
      [0.42, "wheel-brass"],
      [0.52, "wheel-brass-hi"],
      [0.63, "wheel-brass"],
      [0.8, "wheel-brass-lo"],
      [0.92, "wheel-brass"],
      [1, "wheel-brass-hi"],
    ].forEach(([at, name]) => brass.addColorStop(at, k[name]));
    g.fillStyle = brass;
    annulus(g, c, R * 0.95, R * 0.865);
    g.fill();
    g.lineWidth = Math.max(1, R * 0.006);
    g.strokeStyle = k["wheel-brass-hi"];
    g.beginPath();
    g.arc(c, c, R * 0.947, 0, TAU);
    g.stroke();
    g.strokeStyle = k["wheel-brass-lo"];
    g.beginPath();
    g.arc(c, c, R * 0.868, 0, TAU);
    g.stroke();

    this.face = this.layer();
    g = this.face.getContext("2d");
    const r = R * 0.862;
    const n = this.slices.length;
    this.slices.forEach((s, i) => {
      g.beginPath();
      g.moveTo(c, c);
      g.arc(c, c, r, s.a0, s.a1);
      g.closePath();
      // An odd count closes on a third tone, so no two neighbors match.
      const third = n > 1 && n % 2 === 1 && i === n - 1;
      g.fillStyle = third ? k["wheel-bezel"] : i % 2 === 0 ? k["wheel-face-a"] : k["wheel-face-b"];
      g.fill();
    });
    if (!n) {
      g.fillStyle = k["wheel-face-a"];
      g.beginPath();
      g.arc(c, c, r, 0, TAU);
      g.fill();
    }
    const shade = g.createRadialGradient(c, c, r * 0.2, c, c, r);
    shade.addColorStop(0, "rgba(255,255,255,0.05)");
    shade.addColorStop(0.75, "rgba(0,0,0,0)");
    shade.addColorStop(1, "rgba(0,0,0,0.35)");
    g.fillStyle = shade;
    g.beginPath();
    g.arc(c, c, r, 0, TAU);
    g.fill();

    g.strokeStyle = k["wheel-brass"];
    g.lineWidth = Math.max(1, R * 0.008);
    if (n > 1) {
      for (const s of this.slices) {
        g.beginPath();
        g.moveTo(c + Math.cos(s.a0) * r * 0.18, c + Math.sin(s.a0) * r * 0.18);
        g.lineTo(c + Math.cos(s.a0) * r, c + Math.sin(s.a0) * r);
        g.stroke();
      }
    }

    // Each title reads from the rim inward and stands upright where the wheel rests: slices on the left half turn
    // half a circle. A title is sized so its block, centered on the slice, keeps clear of both spokes all the way to
    // its inner end; a long title breaks onto two lines when that lets it stand larger.
    g.fillStyle = k["wheel-ink"];
    g.textBaseline = "middle";
    g.fontStretch = "condensed";
    const outer = r * 0.88;
    const room = r * 0.64;
    const clear = R * 0.014;
    for (const s of this.slices) {
      const span = s.a1 - s.a0;
      const mid = (s.a0 + s.a1) / 2;
      const top = R * 0.082;
      const t = Math.tan(Math.min(span / 2, 1));
      const fit = (lines) => {
        g.font = `640 100px "Bricolage", sans-serif`;
        const w = Math.max(...lines.map((l) => g.measureText(l).width)) / 100;
        const half = ((lines.length - 1) * 1.05 + 0.8) / 2;
        return Math.min(top, room / w, (outer * t - clear) / (w * t + half));
      };
      let lines = [s.title];
      let fs = fit(lines);
      const words = s.title.split(" ");
      for (let i = 1; i < words.length; i += 1) {
        const pair = [words.slice(0, i).join(" "), words.slice(i).join(" ")];
        const size = fit(pair);
        if (size > fs * 1.08) {
          lines = pair;
          fs = size;
        }
      }
      if (fs < R * 0.026) continue;
      const flip = Math.cos(mid + this.rot) < -0.02;
      g.save();
      g.translate(c, c);
      g.rotate(flip ? mid + Math.PI : mid);
      g.textAlign = flip ? "left" : "right";
      g.font = `640 ${fs}px "Bricolage", sans-serif`;
      const x = flip ? -outer : outer;
      const lead = fs * 1.05;
      lines.forEach((line, i) => g.fillText(line, x, (i - (lines.length - 1) / 2) * lead));
      g.restore();
    }
    g.fontStretch = "normal";

    for (let i = 0; i < TEETH; i += 1) {
      const a = i * TOOTH;
      const x = c + Math.cos(a) * r * 0.955;
      const y = c + Math.sin(a) * r * 0.955;
      const pr = R * 0.019;
      const grad = g.createRadialGradient(x - pr * 0.4, y - pr * 0.4, pr * 0.1, x, y, pr);
      grad.addColorStop(0, k["wheel-brass-hi"]);
      grad.addColorStop(0.6, k["wheel-brass"]);
      grad.addColorStop(1, k["wheel-brass-lo"]);
      g.fillStyle = grad;
      g.beginPath();
      g.arc(x, y, pr, 0, TAU);
      g.fill();
    }

    this.top = this.layer();
    g = this.top.getContext("2d");
    const hr = R * 0.16;
    g.save();
    g.shadowColor = "rgba(0,0,0,0.45)";
    g.shadowBlur = R * 0.04;
    g.shadowOffsetY = R * 0.012;
    const hub = g.createRadialGradient(c - hr * 0.35, c - hr * 0.4, hr * 0.1, c, c, hr);
    hub.addColorStop(0, k["wheel-brass-hi"]);
    hub.addColorStop(0.55, k["wheel-brass"]);
    hub.addColorStop(1, k["wheel-brass-lo"]);
    g.fillStyle = hub;
    g.beginPath();
    g.arc(c, c, hr, 0, TAU);
    g.fill();
    g.restore();
    g.strokeStyle = k["wheel-brass-lo"];
    g.lineWidth = Math.max(1, R * 0.006);
    g.beginPath();
    g.arc(c, c, hr * 0.7, 0, TAU);
    g.stroke();
    g.fillStyle = k["wheel-bezel"];
    g.beginPath();
    g.arc(c, c, hr * 0.24, 0, TAU);
    g.fill();
    this.dirty = false;
  }

  drawFlapper(g, c, R) {
    const k = this.colors;
    const py = c - R * 0.975;
    g.save();
    g.translate(c, py);
    g.rotate(this.flap.x);
    g.shadowColor = "rgba(0,0,0,0.4)";
    g.shadowBlur = R * 0.03;
    g.shadowOffsetY = R * 0.012;
    const grad = g.createLinearGradient(-R * 0.05, 0, R * 0.05, 0);
    grad.addColorStop(0, k["wheel-brass-hi"]);
    grad.addColorStop(0.5, k["wheel-brass"]);
    grad.addColorStop(1, k["wheel-brass-lo"]);
    g.fillStyle = grad;
    g.beginPath();
    g.moveTo(-R * 0.052, 0);
    g.quadraticCurveTo(-R * 0.05, R * 0.08, 0, R * 0.17);
    g.quadraticCurveTo(R * 0.05, R * 0.08, R * 0.052, 0);
    g.arc(0, 0, R * 0.052, 0, Math.PI, true);
    g.fill();
    g.shadowColor = "transparent";
    g.fillStyle = k["wheel-bezel"];
    g.beginPath();
    g.arc(0, 0, R * 0.016, 0, TAU);
    g.fill();
    g.restore();
  }

  draw() {
    if (!this.size) return;
    if (this.dirty) this.build();
    const g = this.g;
    const S = this.size;
    const c = S / 2;
    const R = S / 2;
    g.clearRect(0, 0, S, S);
    g.drawImage(this.ring, 0, 0);
    g.save();
    g.translate(c, c);
    g.rotate(this.rot);
    g.drawImage(this.face, -c, -c);
    const lit = this.anim?.kind === "step" ? this.light : this.win;
    const s = this.slices[lit];
    if (s && (this.glow > 0.01 || this.anim?.kind === "step")) {
      const a = this.anim?.kind === "step" ? 0.32 : 0.3 * this.glow;
      g.globalAlpha = a;
      g.fillStyle = this.colors["wheel-brass-hi"];
      g.beginPath();
      g.moveTo(0, 0);
      g.arc(0, 0, R * 0.862, s.a0, s.a1);
      g.closePath();
      g.fill();
      g.globalAlpha = 1;
    }
    g.restore();
    g.drawImage(this.top, 0, 0);
    this.drawFlapper(g, c, R);
    this.needs = false;
  }

  sliceUnderPointer() {
    const a = mod(POINTER - this.rot, TAU);
    return this.slices.findIndex((s) => a >= s.a0 && a < s.a1);
  }

  spin(index) {
    return new Promise((resolve) => {
      const s = this.slices[index];
      if (!s) return resolve(-1);
      this.win = -1;
      this.glow = 0;
      if (this.reduced) {
        const start = Math.max(0, this.sliceUnderPointer());
        const n = this.slices.length;
        const count = n * 2 + mod(index - start, n);
        const times = [];
        let t = 0;
        for (let i = 0; i < count; i += 1) {
          t += 0.07 + 0.32 * Math.pow(i / count, 2);
          times.push(t);
        }
        this.light = start;
        this.anim = { kind: "step", t: 0, times, done: 0, index, resolve };
        return;
      }
      const aim = s.a0 + (s.a1 - s.a0) * (0.25 + Math.random() * 0.5);
      const delta = mod(POINTER - aim - this.rot, TAU);
      const D = (5 + Math.floor(Math.random() * 2)) * TAU + delta;
      const over = TOOTH * 0.55;
      this.lastTooth = Math.floor(this.rot / TOOTH);
      this.anim = { kind: "spin", phase: "run", t: 0, T: 4.4, r0: this.rot, D, over, rf: this.rot + D, index, resolve };
    });
  }

  step(dt) {
    const a = this.anim;
    if (a?.kind === "step") {
      a.t += dt;
      while (a.done < a.times.length && a.t >= a.times[a.done]) {
        a.done += 1;
        this.light = (this.light + 1) % this.slices.length;
        tick(0.8);
      }
      if (a.done >= a.times.length && a.t > a.times[a.times.length - 1] + 0.25) {
        this.anim = null;
        this.win = a.index;
        this.glow = 1;
        chime();
        a.resolve(a.index);
      }
      this.needs = true;
    } else if (a?.kind === "spin") {
      a.t += dt;
      if (a.phase === "run") {
        const u = Math.min(a.t / a.T, 1);
        this.rot = a.r0 + (a.D + a.over) * (1 - Math.pow(1 - u, 3));
        if (u >= 1) {
          a.phase = "settle";
          a.t = 0;
        }
      } else {
        this.rot = a.rf + a.over * Math.exp(-5.5 * a.t) * Math.cos(11 * a.t);
        if (a.t > 1.1) {
          this.rot = mod(a.rf, TAU);
          this.lastTooth = Math.floor(this.rot / TOOTH);
          this.dirty = true;
          this.anim = null;
          this.win = a.index;
          this.glow = 1;
          chime();
          a.resolve(a.index);
        }
      }
      if (this.anim) {
        const tooth = Math.floor(this.rot / TOOTH);
        if (tooth !== this.lastTooth) {
          const dir = Math.sign(tooth - this.lastTooth);
          this.lastTooth = tooth;
          this.flap.v -= dir * 9;
          tick(1);
        }
      }
      this.needs = true;
    }
    if (Math.abs(this.flap.x) > 0.0005 || Math.abs(this.flap.v) > 0.0005) {
      spring(this.flap, 0, 700, 0.3, dt);
      this.flap.x = Math.max(-0.55, Math.min(0.55, this.flap.x));
      this.needs = true;
    }
  }
}
