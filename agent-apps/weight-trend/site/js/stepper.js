// The dial: a big number over a scale disc seen through a window, the way an analogue bathroom scale shows it. The
// buttons and the arrow keys step a tenth (Shift steps a whole unit), dragging the disc turns it and a flick lets it
// coast to a stop, scrolling over it turns it, typing the number sets it, and Enter confirms.

const TENTH_PX = 11; // the arc length of a tenth at the disc's rim
const FRICTION_MS = 320; // how fast a flicked disc slows: velocity falls to 1/e in this time

export function createStepper(root, { onConfirm, onChange }) {
  const input = root.querySelector("[data-dial-input]");
  const ruler = root.querySelector("[data-ruler]");
  const canvas = ruler.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  let value = 70;
  let shown = 70;
  let tween = null;
  let colors = null;

  const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v) => Math.min(999.9, Math.max(1, v));
  const round = (v) => Math.round(v * 10) / 10;

  function rgba(hex, a) {
    const h = hex.replace("#", "");
    const n = parseInt(h.length === 3 ? h.replace(/./g, "$&$&") : h.slice(0, 6), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
  }

  function readColors() {
    const css = getComputedStyle(ruler);
    const get = (name) => css.getPropertyValue(name).trim();
    colors = {
      face: get("--dial-face"),
      rim: get("--dial-rim"),
      well: get("--dial-well"),
      tick: get("--dial-tick"),
      minor: get("--dial-tick-minor"),
      needle: get("--dial-needle"),
      glare: get("--dial-glare"),
      font: get("--font-sans"),
    };
  }

  function paint() {
    const w = ruler.clientWidth;
    const h = ruler.clientHeight;
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 3);
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    if (!colors) readColors();
    const c = colors;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // The well behind the disc.
    ctx.fillStyle = c.well;
    ctx.fillRect(0, 0, w, h);

    // The disc: a wide circle whose top arc fills the window, so its rim curves away at both ends.
    const R = Math.max(520, w * 1.55);
    const rimY = 7;
    const cx = w / 2;
    const cy = rimY + R;
    const face = ctx.createRadialGradient(cx, cy, R - h * 1.4, cx, cy, R);
    face.addColorStop(0, rgba(c.face, 1));
    face.addColorStop(0.82, rgba(c.face, 1));
    face.addColorStop(1, rgba(c.rim, 1));
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.fillStyle = face;
    ctx.fill();
    // The rim's lit edge.
    ctx.beginPath();
    ctx.arc(cx, cy, R - 0.75, Math.PI * 1.2, Math.PI * 1.8);
    ctx.strokeStyle = rgba(c.glare, 0.55);
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Ticks and numbers ride the rim; the disc turns so the value sits under the needle.
    const step = TENTH_PX / R;
    const halfAngle = Math.asin(Math.min(1, (w / 2 + 20) / R));
    const span = Math.ceil(halfAngle / step) + 1;
    const base = Math.round(shown * 10);
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    for (let k = base - span; k <= base + span; k += 1) {
      const a = (k - shown * 10) * step;
      if (Math.abs(a) > halfAngle) continue;
      const whole = k % 10 === 0;
      const half = k % 5 === 0;
      const len = whole ? h * 0.36 : half ? h * 0.25 : h * 0.15;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(a);
      ctx.fillStyle = whole || half ? c.tick : c.minor;
      const tw = whole ? 2.4 : half ? 1.6 : 1;
      ctx.fillRect(-tw / 2, -R + 3, tw, len);
      // A number fades out before its foot would drop past the window's floor as the rim curves away.
      const labelY = -R + 3 + len + h * 0.26;
      const foot = cy + labelY * Math.cos(a) + 3;
      const keep = Math.min(1, Math.max(0, (h - 6 - foot) / 10));
      if (whole && keep > 0) {
        ctx.globalAlpha = keep;
        ctx.font = `700 ${Math.round(h * 0.2)}px ${c.font}`;
        ctx.fillStyle = c.tick;
        ctx.fillText(String(k / 10), 0, labelY);
        ctx.globalAlpha = 1;
      }
      ctx.restore();
    }

    // Shade the disc where it turns away, and the window's top edge where the bezel overhangs it.
    const side = ctx.createLinearGradient(0, 0, w, 0);
    side.addColorStop(0, rgba(c.well, 0.62));
    side.addColorStop(0.2, rgba(c.well, 0.1));
    side.addColorStop(0.5, rgba(c.well, 0));
    side.addColorStop(0.8, rgba(c.well, 0.1));
    side.addColorStop(1, rgba(c.well, 0.62));
    ctx.fillStyle = side;
    ctx.fillRect(0, 0, w, h);
    const lip = ctx.createLinearGradient(0, 0, 0, h * 0.3);
    lip.addColorStop(0, rgba(c.well, 0.38));
    lip.addColorStop(1, rgba(c.well, 0));
    ctx.fillStyle = lip;
    ctx.fillRect(0, 0, w, h * 0.3);
    const floor = ctx.createLinearGradient(0, h * 0.7, 0, h);
    floor.addColorStop(0, rgba(c.well, 0));
    floor.addColorStop(1, rgba(c.well, 0.16));
    ctx.fillStyle = floor;
    ctx.fillRect(0, h * 0.7, w, h * 0.3);

    // The needle, fixed over the disc, casts a soft shadow on it.
    const nx = cx;
    const nTop = 1;
    const nBottom = h * 0.74;
    const needle = () => {
      ctx.beginPath();
      ctx.moveTo(nx - 4.5, nTop);
      ctx.lineTo(nx + 4.5, nTop);
      ctx.lineTo(nx + 1.4, nBottom);
      ctx.quadraticCurveTo(nx, nBottom + 3, nx - 1.4, nBottom);
      ctx.closePath();
    };
    ctx.save();
    ctx.shadowColor = rgba(c.well, 0.55);
    ctx.shadowBlur = 5;
    ctx.shadowOffsetX = 2.5;
    ctx.shadowOffsetY = 3;
    needle();
    ctx.fillStyle = c.needle;
    ctx.fill();
    ctx.restore();
    needle();
    const shine = ctx.createLinearGradient(nx - 4.5, 0, nx + 4.5, 0);
    shine.addColorStop(0, rgba(c.glare, 0.45));
    shine.addColorStop(0.45, rgba(c.glare, 0));
    ctx.fillStyle = shine;
    ctx.fill();

    // The glass over it all: a band of glare across the top.
    const glass = ctx.createLinearGradient(0, 0, 0, h);
    glass.addColorStop(0, rgba(c.glare, 0.32));
    glass.addColorStop(0.42, rgba(c.glare, 0.06));
    glass.addColorStop(0.43, rgba(c.glare, 0));
    glass.addColorStop(1, rgba(c.glare, 0));
    ctx.fillStyle = glass;
    ctx.fillRect(0, 0, w, h);
  }

  function stop() {
    if (tween) cancelAnimationFrame(tween.raf);
    tween = null;
  }

  // Eases the disc to a value; a short overshoot gives it the weight of a turning disc.
  function animateTo(target, duration, { settle = true } = {}) {
    stop();
    if (reduced() || duration <= 0) {
      shown = target;
      paint();
      return;
    }
    const from = shown;
    const start = performance.now();
    const k = settle ? 1.25 : 0;
    const frame = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const u = t - 1;
      const e = 1 + (k + 1) * u ** 3 + k * u ** 2;
      shown = from + (target - from) * e;
      paint();
      if (t < 1) tween.raf = requestAnimationFrame(frame);
      else tween = null;
    };
    tween = { raf: requestAnimationFrame(frame) };
  }

  // A flicked disc coasts on its momentum, slowing with friction, then settles on the nearest tenth.
  function coast(velocity) {
    stop();
    let v = velocity; // units per millisecond
    let last = performance.now();
    const frame = (now) => {
      const dt = Math.min(48, now - last);
      last = now;
      v *= Math.exp(-dt / FRICTION_MS);
      shown = clamp(shown + v * dt);
      const snapped = round(shown);
      if (snapped !== value) {
        value = snapped;
        input.value = value.toFixed(1);
        onChange(value);
      }
      paint();
      if (Math.abs(v) > 0.0004 && shown > 1 && shown < 999.9) tween.raf = requestAnimationFrame(frame);
      else animateTo(value, 220, { settle: false });
    };
    tween = { raf: requestAnimationFrame(frame) };
  }

  function set(next, { duration = 220, keepText = false } = {}) {
    value = round(clamp(next));
    if (!keepText) input.value = value.toFixed(1);
    animateTo(value, duration);
    onChange(value);
  }

  function nudge(dir, big) {
    set(value + dir * (big ? 1 : 0.1));
  }

  // The plus and minus buttons step once on a tap and repeat while held.
  for (const button of root.querySelectorAll("[data-step]")) {
    const dir = Number(button.dataset.step);
    let hold = null;
    const stop = () => {
      clearTimeout(hold);
      clearInterval(hold);
      hold = null;
    };
    button.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      nudge(dir, e.shiftKey);
      hold = setTimeout(() => {
        hold = setInterval(() => nudge(dir, false), 70);
      }, 420);
    });
    button.addEventListener("pointerup", stop);
    button.addEventListener("pointerleave", stop);
    button.addEventListener("pointercancel", stop);
    button.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        nudge(dir, e.shiftKey);
      }
    });
  }

  let drag = null;
  ruler.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    ruler.setPointerCapture(e.pointerId);
    stop();
    drag = { x: e.clientX, from: shown, samples: [{ t: e.timeStamp, v: shown }] };
  });
  ruler.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const raw = clamp(drag.from - ((e.clientX - drag.x) / TENTH_PX) * 0.1);
    shown = raw;
    drag.samples.push({ t: e.timeStamp, v: raw });
    if (drag.samples.length > 6) drag.samples.shift();
    paint();
    const snapped = round(raw);
    if (snapped !== value) {
      value = snapped;
      input.value = value.toFixed(1);
      onChange(value);
    }
  });
  const endDrag = (e) => {
    if (!drag) return;
    const recent = drag.samples.filter((s) => e.timeStamp - s.t < 100);
    drag = null;
    const first = recent[0];
    const last = recent[recent.length - 1];
    const velocity = first && last && last.t > first.t ? (last.v - first.v) / (last.t - first.t) : 0;
    if (!reduced() && Math.abs(velocity) > 0.002) coast(velocity);
    else animateTo(value, 180, { settle: false });
  };
  ruler.addEventListener("pointerup", endDrag);
  ruler.addEventListener("pointercancel", endDrag);
  ruler.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
      nudge(delta > 0 ? -1 : 1, e.shiftKey);
    },
    { passive: false },
  );

  input.addEventListener("input", () => {
    const parsed = Number(input.value.replace(",", "."));
    if (Number.isFinite(parsed) && parsed >= 1 && parsed <= 999.9) set(parsed, { keepText: true });
  });
  input.addEventListener("blur", () => {
    input.value = value.toFixed(1);
  });
  input.addEventListener("focus", () => input.select());

  // Arrow keys step from anywhere on the Today screen except inside the note, and Enter confirms.
  document.addEventListener("keydown", (e) => {
    if (root.closest("[hidden]")) return;
    const inNote = e.target instanceof HTMLInputElement && e.target !== input;
    if (e.key === "Enter" && (e.target === input || e.target === document.body)) {
      e.preventDefault();
      input.value = value.toFixed(1);
      onConfirm();
      return;
    }
    if (inNote || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target instanceof HTMLButtonElement && !e.target.matches("[data-step]") && (e.key === "ArrowLeft" || e.key === "ArrowRight")) return;
    const dir = { ArrowUp: 1, ArrowRight: 1, ArrowDown: -1, ArrowLeft: -1 }[e.key];
    if (!dir) return;
    e.preventDefault();
    nudge(dir, e.shiftKey);
  });

  new ResizeObserver(() => paint()).observe(ruler);
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    colors = null;
    paint();
  });

  return {
    get value() {
      return value;
    },
    // Opens on a value with the tape rolling in to it.
    start(v) {
      value = round(clamp(v));
      input.value = value.toFixed(1);
      shown = value - 2.4;
      paint();
      animateTo(value, 1100);
      onChange(value);
    },
    set,
    refresh() {
      colors = null;
      paint();
    },
  };
}
