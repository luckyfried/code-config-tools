// The composition donut: assets on the outer ring and debts on the inner one, each account an arc drawn
// with stroke-dasharray. Both rings share one scale, so a ring runs full circle only for the larger side.
// A month change tweens every arc from where it is to where it goes.
const NS = "http://www.w3.org/2000/svg";
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const easeOut = (t) => 1 - (1 - t) ** 3;

export function createDonut({ svg, model, reduced }) {
  const rings = [
    { list: model.assets, r: 82, w: 20 },
    { list: model.debts, r: 56, w: 14 },
  ];
  const arcs = [];
  for (const ring of rings) {
    const track = document.createElementNS(NS, "circle");
    track.setAttribute("class", "donut-track");
    track.setAttribute("cx", "100");
    track.setAttribute("cy", "100");
    track.setAttribute("r", String(ring.r));
    track.setAttribute("stroke-width", String(ring.w));
    svg.appendChild(track);
    const C = 2 * Math.PI * ring.r;
    for (const account of ring.list) {
      const arc = document.createElementNS(NS, "circle");
      arc.setAttribute("class", "donut-arc");
      arc.setAttribute("cx", "100");
      arc.setAttribute("cy", "100");
      arc.setAttribute("r", String(ring.r));
      arc.setAttribute("stroke-width", String(ring.w));
      arc.setAttribute("transform", "rotate(-90 100 100)");
      arc.style.setProperty("--layer", account.color);
      svg.appendChild(arc);
      arcs.push({ node: arc, account, C, start: 0, len: 0, ring });
    }
  }
  let frame = 0;

  function targets(point) {
    const scale = Math.max(point.assets, point.debts, 1);
    const out = [];
    for (const ring of rings) {
      let at = 0;
      for (const account of ring.list) {
        const share = point.balances[account.id] / scale;
        out.push({ start: at, len: share });
        at += share;
      }
    }
    return out;
  }

  function draw() {
    for (const arc of arcs) {
      const gap = arc.len * arc.C > 6 ? 2 : 0;
      const len = Math.max(0, arc.len * arc.C - gap);
      arc.node.setAttribute("stroke-dasharray", `${len.toFixed(2)} ${arc.C.toFixed(2)}`);
      arc.node.setAttribute("stroke-dashoffset", (-(arc.start * arc.C)).toFixed(2));
    }
  }

  return {
    /** Tweens every arc to `point` over `duration` milliseconds. */
    show(point, duration = 420) {
      cancelAnimationFrame(frame);
      const to = targets(point);
      if (reduced() || duration <= 0) {
        arcs.forEach((arc, k) => Object.assign(arc, to[k]));
        draw();
        return;
      }
      const from = arcs.map((arc) => ({ start: arc.start, len: arc.len }));
      const begin = performance.now();
      const step = (now) => {
        const t = easeOut(clamp((now - begin) / duration, 0, 1));
        arcs.forEach((arc, k) => {
          arc.start = from[k].start + (to[k].start - from[k].start) * t;
          arc.len = from[k].len + (to[k].len - from[k].len) * t;
        });
        draw();
        if (t < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    },
  };
}
