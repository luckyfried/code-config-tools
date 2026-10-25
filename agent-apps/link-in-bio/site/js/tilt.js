// The card tilts toward the pointer on a desktop and with the gyroscope on a phone. Idle on a desktop, it sways slowly;
// on a touch screen it rests level until the phone moves away from the pose it was held in.
// The sheen and the rim light move with the tilt, as a highlight would on glass; on a resting phone they drift alone.
// Link cards lean toward the pointer while it is over them.

const clamp = (v, lo = -1, hi = 1) => Math.min(hi, Math.max(lo, v));

export function startTilt(card, lights) {
  const max = 6;
  const sway = 3.4;
  const level = !matchMedia("(hover: hover) and (pointer: fine)").matches;
  let target = [0, 0];
  let current = [0, 0];
  let lastInput = -Infinity;
  let base = null;
  let drift = [0, 0];
  let written = "";

  if (!level) window.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse" && e.pointerType !== "pen") return;
    const nx = clamp((e.clientX / window.innerWidth) * 2 - 1);
    const ny = clamp((e.clientY / window.innerHeight) * 2 - 1);
    target = [-ny * max, nx * max];
    lastInput = performance.now();
  }, { passive: true });
  document.documentElement.addEventListener("pointerleave", () => { lastInput = -Infinity; });

  const onOrientation = (e) => {
    if (e.beta == null || e.gamma == null) return;
    base = base == null ? [e.beta, e.gamma] : [base[0] + (e.beta - base[0]) * 0.01, base[1] + (e.gamma - base[1]) * 0.01];
    const next = [clamp((base[0] - e.beta) / 25) * max, clamp((e.gamma - base[1]) / 25) * max];
    if (Math.abs(next[0]) + Math.abs(next[1]) < 0.4) return;
    target = next;
    lastInput = performance.now();
  };
  const listen = () => window.addEventListener("deviceorientation", onOrientation, { passive: true });
  const Orientation = window.DeviceOrientationEvent;
  if (Orientation && typeof Orientation.requestPermission === "function") {
    window.addEventListener("pointerdown", () => {
      Orientation.requestPermission().then((state) => { if (state === "granted") listen(); }).catch(() => {});
    }, { once: true });
  } else if (Orientation) {
    listen();
  }

  let last = performance.now();
  const frame = (now) => {
    const dt = Math.min(64, now - last);
    last = now;
    const idle = now - lastInput > 2500;
    if (idle) {
      const wave = [Math.sin(now * 0.00062 + 0.6) * sway, Math.sin(now * 0.00043 + 1.3) * sway * 1.3];
      target = level ? [0, 0] : wave;
      drift = level ? wave : [0, 0];
    } else {
      drift = [0, 0];
    }
    const k = 1 - Math.exp(-dt / (idle ? 520 : 140));
    current = [current[0] + (target[0] - current[0]) * k, current[1] + (target[1] - current[1]) * k];
    const next = `${current[0].toFixed(2)} ${current[1].toFixed(2)} ${drift[0].toFixed(2)} ${drift[1].toFixed(2)}`;
    if (next !== written) {
      written = next;
      card.style.setProperty("--rx", current[0].toFixed(2));
      card.style.setProperty("--ry", current[1].toFixed(2));
      const sx = (((current[1] + drift[1]) / max) * 60).toFixed(2);
      const sy = ((-(current[0] + drift[0]) / max) * 60).toFixed(2);
      lights.forEach((el) => {
        if (!el) return;
        el.style.setProperty("--sx", sx);
        el.style.setProperty("--sy", sy);
      });
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

export function startMagnetic(links) {
  if (!matchMedia("(hover: hover) and (pointer: fine)").matches) return;
  links.forEach((el) => {
    let box = null;
    el.addEventListener("pointerenter", () => { box = el.getBoundingClientRect(); });
    el.addEventListener("pointermove", (e) => {
      if (e.pointerType !== "mouse" || !box) return;
      const mx = ((e.clientX - box.left) / box.width - 0.5) * 8;
      const my = ((e.clientY - box.top) / box.height - 0.5) * 4 - 2;
      el.style.setProperty("--mx", mx.toFixed(2));
      el.style.setProperty("--my", my.toFixed(2));
    });
    el.addEventListener("pointerleave", () => {
      box = null;
      el.style.setProperty("--mx", "0");
      el.style.setProperty("--my", "0");
    });
  });
}
