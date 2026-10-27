// The minimap under the timeline (beside it when time runs down): the whole span, its eras and events, and the
// camera's view as a window that can be dragged.

const NS = "http://www.w3.org/2000/svg";
const el = (name, attrs, parent) => {
  const node = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  parent.appendChild(node);
  return node;
};
const round = (n) => String(Math.round(n * 10) / 10);

export class Minimap {
  constructor(svg, data, { onDrag, onJump, onKey }) {
    this.svg = svg;
    this.data = data;
    this.onDrag = onDrag;
    this.onJump = onJump;
    const span = data.max - data.min;
    this.d0 = data.min - span * 0.03;
    this.d1 = data.max + span * 0.03;
    this.drag = null;
    svg.addEventListener("pointerdown", (e) => this.down(e));
    svg.addEventListener("pointermove", (e) => this.move(e));
    svg.addEventListener("pointerup", (e) => this.up(e));
    svg.addEventListener("pointercancel", (e) => this.up(e));
    svg.addEventListener("keydown", (e) => onKey(e));
  }

  resize(width, height, orient, layers) {
    this.W = width;
    this.H = height;
    this.orient = orient;
    this.length = orient === "h" ? width : height;
    this.thick = orient === "h" ? height : width;
    const svg = this.svg;
    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    const box = (a0, a1, c0, c1) => (orient === "h" ? { x: a0, y: c0, width: a1 - a0, height: c1 - c0 } : { x: c0, y: a0, width: c1 - c0, height: a1 - a0 });
    const fix = (b) => Object.fromEntries(Object.entries(b).map(([k, v]) => [k, round(Math.max(k === "width" || k === "height" ? 0 : -1e6, v))]));
    el("rect", { class: "mm-track", rx: 8, ...fix(box(0, this.length, 0, this.thick)) }, svg);
    const bar = Math.min(6, (this.thick - 14) / Math.max(1, layers));
    for (const era of this.data.eras) {
      const a0 = this.px(era.t);
      const a1 = this.px(era.end);
      const c0 = 4 + era.layer * (bar + 1);
      const rect = el("rect", { class: "mm-era", "data-hue": era.hue, rx: 1.5, ...fix(box(a0, Math.max(a0 + 2, a1), c0, c0 + bar)) }, svg);
      if (era.custom) rect.style.setProperty("--hue", era.custom);
    }
    const c0 = 6 + layers * (bar + 1);
    for (const event of this.data.events) {
      const a = round(this.px(event.t));
      const line = orient === "h" ? { x1: a, x2: a, y1: round(c0), y2: round(this.thick - 4) } : { y1: a, y2: a, x1: round(c0), x2: round(this.thick - 4) };
      el("line", { class: "mm-event", ...line }, svg);
    }
    this.shadeA = el("rect", { class: "mm-shade" }, svg);
    this.shadeB = el("rect", { class: "mm-shade" }, svg);
    this.window = el("rect", { class: "mm-window", rx: 6 }, svg);
    this.grip = el("path", { class: "mm-grip" }, svg);
    this.box = box;
    this.fix = fix;
  }

  px(t) {
    return ((t - this.d0) / (this.d1 - this.d0)) * this.length;
  }

  time(px) {
    return this.d0 + (px / this.length) * (this.d1 - this.d0);
  }

  render(view0, view1) {
    if (!this.window) return;
    let a0 = this.px(view0);
    let a1 = this.px(view1);
    // A view narrower than a few pixels keeps a window wide enough to grab.
    const min = 14;
    if (a1 - a0 < min) {
      const mid = (a0 + a1) / 2;
      a0 = mid - min / 2;
      a1 = mid + min / 2;
    }
    const L = this.length;
    const T = this.thick;
    // The window, its stroke and its corners stay inside the track at every zoom and pan.
    const inset = 1;
    const span = Math.min(L - inset * 2, a1 - a0);
    a0 = Math.min(L - inset - span, Math.max(inset, a0));
    a1 = a0 + span;
    const set = (node, b) => {
      for (const [key, value] of Object.entries(this.fix(b))) if (node.getAttribute(key) !== value) node.setAttribute(key, value);
    };
    set(this.shadeA, this.box(0, Math.max(0, Math.min(L, a0)), 0, T));
    set(this.shadeB, this.box(Math.max(0, Math.min(L, a1)), L, 0, T));
    set(this.window, this.box(a0, a1, 1, T - 1));
    const mid = (a0 + a1) / 2;
    const grip = this.orient === "h" ? `M${round(mid - 4)} ${round(T - 1)}h8` : `M${round(T - 1)} ${round(mid - 4)}v8`;
    if (this.grip.getAttribute("d") !== grip) this.grip.setAttribute("d", grip);
    this.view = [a0, a1];
    const percent = Math.round(Math.min(100, Math.max(0, (mid / L) * 100)));
    this.svg.setAttribute("aria-valuenow", String(percent));
  }

  along(e) {
    const r = this.svg.getBoundingClientRect();
    return this.orient === "h" ? e.clientX - r.left : e.clientY - r.top;
  }

  down(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    e.preventDefault();
    this.svg.setPointerCapture(e.pointerId);
    const at = this.along(e);
    const [a0, a1] = this.view ?? [0, 0];
    const inside = at >= a0 - 6 && at <= a1 + 6;
    this.drag = { id: e.pointerId, offset: inside ? at - (a0 + a1) / 2 : 0 };
    if (!inside) this.onJump(this.time(at));
  }

  move(e) {
    if (!this.drag || e.pointerId !== this.drag.id) return;
    const at = this.along(e) - this.drag.offset;
    this.onDrag(this.time(Math.min(this.length, Math.max(0, at))));
  }

  up(e) {
    if (this.drag && e.pointerId === this.drag.id) this.drag = null;
  }
}
