// A canvas confetti burst in the theme's colors, with gravity, air drag, and a paper flutter. It draws only while
// pieces are in the air.

export function createConfetti(canvas) {
  const ctx = canvas.getContext("2d");
  let pieces = [];
  let frame = 0;
  let last = 0;
  let ratio = 1;
  let width = innerWidth;
  let height = innerHeight;

  // The canvas is resized only when the window's size changes, never per burst, so a burst allocates nothing.
  function size() {
    ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = innerWidth;
    height = innerHeight;
    const w = Math.round(width * ratio);
    const h = Math.round(height * ratio);
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;
  }

  function colors() {
    const css = getComputedStyle(document.documentElement);
    return [1, 2, 3, 4, 5].map((n) => css.getPropertyValue(`--confetti-${n}`).trim()).filter(Boolean);
  }

  /** Fires pieces up and out from the point (x, y), in CSS pixels. */
  function burst(x, y, { count = 150, spread = 1 } = {}) {
    size();
    const palette = colors();
    const scale = Math.min(1.2, Math.max(0.7, innerWidth / 1000));
    for (let i = 0; i < count; i += 1) {
      const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 0.95 * spread;
      const speed = (620 + Math.random() * 760) * scale;
      pieces.push({
        x: x + (Math.random() - 0.5) * 120 * scale,
        y: y + (Math.random() - 0.5) * 20,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        w: 7 + Math.random() * 7,
        h: 4 + Math.random() * 6,
        round: Math.random() < 0.22,
        spin: (Math.random() - 0.5) * 14,
        angle: Math.random() * Math.PI * 2,
        flutter: Math.random() * Math.PI * 2,
        rate: 6 + Math.random() * 8,
        drag: 1.6 + Math.random() * 1.4,
        color: palette[i % palette.length],
        life: 0,
      });
    }
    // Drawn grouped by color, so the fill changes five times a frame, not once a piece.
    pieces.sort((a, b) => (a.color < b.color ? -1 : a.color > b.color ? 1 : 0));
    if (!frame) {
      last = performance.now();
      frame = requestAnimationFrame(tick);
    }
  }

  function tick(now) {
    const dt = Math.min(0.033, (now - last) / 1000);
    last = now;
    const g = 1500;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    pieces = pieces.filter((p) => p.y < height + 40 && p.life < 5);
    let fill = "";
    let alpha = 1;
    ctx.globalAlpha = 1;
    for (const p of pieces) {
      p.life += dt;
      const k = Math.exp(-p.drag * dt);
      p.vx *= k;
      p.vy = p.vy * k + g * dt * (0.35 + 0.65 * Math.min(1, p.life * 2));
      p.vy = Math.min(p.vy, 420 + p.drag * 60);
      p.x += (p.vx + Math.sin(p.flutter) * 40) * dt;
      p.y += p.vy * dt;
      p.angle += p.spin * dt;
      p.flutter += p.rate * dt;
      const fade = p.life > 3.6 ? Math.max(0, 1 - (p.life - 3.6) / 1.4) : 1;
      if (fade !== alpha) ctx.globalAlpha = alpha = fade;
      if (p.color !== fill) ctx.fillStyle = fill = p.color;
      // translate(x, y) · rotate(angle) · scale(1, cos(flutter)) at the device ratio, as one matrix.
      const cos = Math.cos(p.angle) * ratio;
      const sin = Math.sin(p.angle) * ratio;
      const flip = Math.cos(p.flutter);
      ctx.setTransform(cos, sin, -sin * flip, cos * flip, p.x * ratio, p.y * ratio);
      if (p.round) {
        ctx.beginPath();
        ctx.arc(0, 0, p.h * 0.6, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      }
    }
    ctx.globalAlpha = 1;
    if (pieces.length) frame = requestAnimationFrame(tick);
    else stop();
  }

  function stop() {
    cancelAnimationFrame(frame);
    frame = 0;
    pieces = [];
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  addEventListener("resize", () => {
    if (frame) size();
  });

  return { burst, stop };
}
