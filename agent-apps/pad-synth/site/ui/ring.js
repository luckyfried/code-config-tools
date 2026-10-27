// The step ring: one ring per voice, sixteen steps round each. The ring turns slowly while a comet, its head
// bright and its tail fading behind it, sweeps once round per bar; each lit step flares as the comet crosses it.
import { STEPS } from "../music/sequence.js";

const TAU = Math.PI * 2;
const TAIL = 1.15;

export class Ring {
  constructor(canvas, measure, { onToggle }) {
    this.canvas = canvas;
    this.measure = measure;
    this.ctx = canvas.getContext("2d");
    this.onToggle = onToggle;
    this.tokens = null;
    this.lanes = [];
    this.data = null;
    this.flash = new Map();
    this.turn = 0;
    this.geometry = null;
    canvas.addEventListener("pointerdown", (event) => this.tap(event));
  }

  setTokens(tokens) {
    this.tokens = tokens;
  }

  /** `lanes` the voices shown from the outside in; `data` the step data per voice. */
  setLanes(lanes, data) {
    this.lanes = lanes;
    this.data = data;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.ratio = Math.min(window.devicePixelRatio || 1, 2);
    this.width = Math.max(1, Math.round(rect.width));
    this.height = Math.max(1, Math.round(rect.height));
    this.canvas.width = Math.round(this.width * this.ratio);
    this.canvas.height = Math.round(this.height * this.ratio);
    const middle = this.measure().getBoundingClientRect();
    const edge = Math.min(this.width, this.height) / 2;
    // The comet's size follows the ring's, so it reads the same on a phone on its side and on a big screen.
    const comet = Math.min(2, Math.max(0.8, edge / 150));
    const orbit = edge - 7 * comet;
    const outer = orbit - 7 * comet;
    const inner = Math.min(outer * 0.72, Math.max(outer * 0.36, Math.hypot(middle.width, middle.height) / 2 + 8));
    this.geometry = { cx: this.width / 2, cy: this.height / 2, outer, inner, orbit, comet };
  }

  /** Marks a step as just played, so it flares. */
  fire(voice, step) {
    this.flash.set(`${voice}:${step}`, 1);
  }

  laneRadius(index) {
    const { outer, inner } = this.geometry;
    const thick = (outer - inner) / Math.max(1, this.lanes.length);
    return { mid: outer - thick * (index + 0.5), thick };
  }

  tap(event) {
    if (!this.geometry || this.lanes.length === 0 || this.geometry.outer < 24) return;
    const rect = this.canvas.getBoundingClientRect();
    const dx = event.clientX - rect.left - this.geometry.cx;
    const dy = event.clientY - rect.top - this.geometry.cy;
    const r = Math.hypot(dx, dy);
    const { outer, inner } = this.geometry;
    if (r < inner - 4 || r > outer + 10) return;
    const thick = (outer - inner) / this.lanes.length;
    const lane = Math.min(this.lanes.length - 1, Math.max(0, Math.floor((outer - r) / thick)));
    let angle = Math.atan2(dy, dx) + Math.PI / 2 - this.turn;
    angle = ((angle % TAU) + TAU) % TAU;
    const step = Math.floor((angle / TAU) * STEPS) % STEPS;
    event.preventDefault();
    this.onToggle(this.lanes[lane], step);
  }

  /** Draws the ring at `position` steps into the bar; `dt` ages the flares; `motion` false holds it still. */
  draw(position, playing, dt, motion) {
    if (!this.tokens || !this.geometry || !this.data) return;
    if (this.geometry.outer < 24 || this.geometry.outer - this.geometry.inner < 8) return;
    const { ctx, ratio } = this;
    const { cx, cy, outer, inner } = this.geometry;
    const t = this.tokens;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, this.width, this.height);
    if (motion) this.turn = (this.turn - dt * 0.05) % TAU;
    const turn = this.turn;
    const head = motion ? position : Math.floor(position);
    const headAngle = -Math.PI / 2 + turn + (head / STEPS) * TAU;
    const slice = TAU / STEPS;
    const decay = Math.exp(-dt / 0.35);

    ctx.lineCap = "round";
    this.lanes.forEach((voice, index) => {
      const { mid, thick } = this.laneRadius(index);
      const color = t.voices[voice];
      ctx.strokeStyle = t.track;
      ctx.lineWidth = thick * 0.8;
      ctx.beginPath();
      ctx.arc(cx, cy, mid, 0, TAU);
      ctx.stroke();
      const steps = this.data[voice];
      for (let s = 0; s < STEPS; s += 1) {
        const start = -Math.PI / 2 + turn + s * slice + slice * 0.14;
        const end = start + slice * 0.72;
        const key = `${voice}:${s}`;
        const flare = this.flash.get(key) || 0;
        if (flare > 0.01) this.flash.set(key, flare * decay);
        else this.flash.delete(key);
        if (!steps[s]) {
          ctx.fillStyle = t.track;
          const a = (start + end) / 2;
          ctx.beginPath();
          ctx.arc(cx + Math.cos(a) * mid, cy + Math.sin(a) * mid, Math.max(1.5, thick * 0.09), 0, TAU);
          ctx.fill();
          continue;
        }
        ctx.strokeStyle = color;
        if (flare > 0.02) {
          ctx.globalAlpha = 0.35 * flare;
          ctx.lineWidth = thick * 0.95;
          ctx.beginPath();
          ctx.arc(cx, cy, mid, start - 0.03, end + 0.03);
          ctx.stroke();
        }
        ctx.globalAlpha = 0.62 + 0.38 * flare;
        ctx.lineWidth = thick * (0.5 + 0.16 * flare);
        ctx.beginPath();
        ctx.arc(cx, cy, mid, start, end);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
    });

    if (!playing) return;
    const { orbit, comet } = this.geometry;
    ctx.globalCompositeOperation = t.blend;
    if (motion && typeof ctx.createConicGradient === "function") {
      const fade = ctx.createConicGradient(headAngle - TAIL, cx, cy);
      fade.addColorStop(0, "transparent");
      fade.addColorStop(TAIL / TAU, t.accent);
      fade.addColorStop(Math.min(1, TAIL / TAU + 0.001), "transparent");
      // A faint sweep across the lanes the comet has just crossed.
      ctx.globalAlpha = 0.12;
      ctx.fillStyle = fade;
      ctx.beginPath();
      ctx.arc(cx, cy, outer + 2, headAngle - TAIL, headAngle);
      ctx.arc(cx, cy, inner - 2, headAngle, headAngle - TAIL, true);
      ctx.closePath();
      ctx.fill();
      // The comet's tail follows the arc, thin and faint at its end, thick and bright at the head: eight strokes
      // of the same fade, each shorter and wider than the last, taper it without seams.
      ctx.globalAlpha = 0.95;
      ctx.strokeStyle = fade;
      ctx.lineCap = "butt";
      for (let k = 0; k < 8; k += 1) {
        ctx.lineWidth = (1.5 + k) * comet;
        ctx.beginPath();
        ctx.arc(cx, cy, orbit, headAngle - TAIL * (1 - k / 8.5), headAngle);
        ctx.stroke();
      }
    }
    const hx = cx + Math.cos(headAngle) * orbit;
    const hy = cy + Math.sin(headAngle) * orbit;
    const glow = 16 * comet;
    const halo = ctx.createRadialGradient(hx, hy, 0, hx, hy, glow);
    halo.addColorStop(0, t.accent);
    halo.addColorStop(1, "transparent");
    ctx.globalAlpha = t.blend === "lighter" ? 0.75 : 0.35;
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(hx, hy, glow, 0, TAU);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
    ctx.fillStyle = t.accent;
    ctx.beginPath();
    ctx.arc(hx, hy, 6 * comet, 0, TAU);
    ctx.fill();
    ctx.fillStyle = t.core;
    ctx.beginPath();
    ctx.arc(hx, hy, 3 * comet, 0, TAU);
    ctx.fill();
  }
}
