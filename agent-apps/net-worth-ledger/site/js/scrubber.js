// The scrubber: a thumb that follows the finger, is pulled onto the nearest month tick as it nears it,
// and settles there on release. The chart's plot drags it too, on the same pointer path.
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const easeOut = (t) => 1 - (1 - t) ** 3;
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

export function createScrubber({ root, track, ticksBox, fill, thumb, plot, chart, count, reduced, onMove, onSelect, onGrab }) {
  let shares = [];
  let width = 1;
  let share = null;
  let selected = count - 1;
  let tween = 0;
  let dragging = false;
  const tickNodes = [];

  for (let i = 0; i < count; i += 1) {
    const tick = document.createElement("span");
    tick.className = "scrubber-tick";
    ticksBox.appendChild(tick);
    tickNodes.push(tick);
  }
  thumb.setAttribute("aria-valuemax", String(Math.max(0, count - 1)));

  const nearest = (s) => {
    let best = 0;
    for (let i = 1; i < shares.length; i += 1) if (Math.abs(shares[i] - s) < Math.abs(shares[best] - s)) best = i;
    return best;
  };

  function paint() {
    const tx = `${(share * width).toFixed(2)}px`;
    thumb.style.setProperty("--tx", tx);
    fill.style.setProperty("--p", share.toFixed(4));
    const near = nearest(share);
    tickNodes.forEach((tick, i) => tick.classList.toggle("is-near", i === near));
    onMove(chart.posAtShare(share));
    if (near !== selected) {
      selected = near;
      thumb.setAttribute("aria-valuenow", String(near));
      onSelect(near);
    }
  }

  function layout() {
    const { left, right } = chart.margins();
    root.style.setProperty("--plot-left", `${left}px`);
    root.style.setProperty("--plot-right", `${right}px`);
    shares = count > 0 ? chart.ticks() : [];
    width = track.clientWidth || 1;
    tickNodes.forEach((tick, i) => tick.style.setProperty("--tx", `${(shares[i] * width).toFixed(2)}px`));
    if (share === null) share = shares[count - 1] ?? 1;
    paint();
  }

  /** Magnetic: within a small zone around a tick the thumb lags the finger toward the tick, then lets go. */
  function magnet(raw) {
    const i = nearest(raw);
    const d = (raw - shares[i]) * width;
    const gap = shares.length > 1 ? Math.min(...shares.slice(1).map((s, k) => (s - shares[k]) * width)) : width;
    const zone = Math.min(22, gap * 0.42);
    if (Math.abs(d) >= zone) return raw;
    return shares[i] + ((d * (Math.abs(d) / zone) ** 2) / width);
  }

  function glideTo(target, duration = 240, curve = duration > 400 ? easeInOut : easeOut) {
    cancelAnimationFrame(tween);
    if (reduced() || duration === 0) {
      share = target;
      paint();
      return;
    }
    const from = share;
    const start = performance.now();
    const step = (now) => {
      const t = clamp((now - start) / duration, 0, 1);
      share = from + (target - from) * curve(t);
      paint();
      if (t < 1) tween = requestAnimationFrame(step);
    };
    tween = requestAnimationFrame(step);
  }

  const shareFromTrack = (clientX) => clamp((clientX - track.getBoundingClientRect().left) / width, 0, 1);
  const shareFromPlot = (clientX) => chart.shareAtPos(chart.posAtClientX(clientX));

  function bind(surface, toShare) {
    let id = null;
    surface.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || count === 0) return;
      id = event.pointerId;
      surface.setPointerCapture(id);
      dragging = true;
      root.classList.add("is-dragging");
      cancelAnimationFrame(tween);
      onGrab();
      share = magnet(toShare(event.clientX));
      paint();
    });
    surface.addEventListener("pointermove", (event) => {
      if (!dragging || event.pointerId !== id) return;
      share = magnet(toShare(event.clientX));
      paint();
    });
    const release = (event) => {
      if (!dragging || event.pointerId !== id) return;
      dragging = false;
      id = null;
      root.classList.remove("is-dragging");
      glideTo(shares[nearest(share)]);
    };
    surface.addEventListener("pointerup", release);
    surface.addEventListener("pointercancel", release);
  }
  bind(track, shareFromTrack);
  bind(plot, shareFromPlot);

  thumb.addEventListener("keydown", (event) => {
    const moves = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 3, PageDown: -3 };
    let next = null;
    if (event.key in moves) next = selected + moves[event.key];
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = count - 1;
    if (next === null) return;
    event.preventDefault();
    onGrab();
    glideTo(shares[clamp(next, 0, count - 1)], 180);
  });

  return {
    layout,
    /** Puts the thumb at a fractional point index without easing, for the opening sweep. */
    follow(pos) {
      cancelAnimationFrame(tween);
      share = chart.shareAtPos(pos);
      paint();
    },
    /** Glides the thumb to snapshot `i` over `ms` milliseconds, months changing as it passes them. */
    glide(i, ms) {
      glideTo(shares[clamp(i, 0, count - 1)], ms);
    },
    /** Forgets the shown month, so the next move reports whichever month the thumb is on. */
    resync() {
      selected = -1;
    },
    setText(text) {
      thumb.setAttribute("aria-valuetext", text);
    },
  };
}
