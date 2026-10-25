// The QR code for the page's own address, drawn with rounded modules that sweep in from one corner.
import qrcode from "../vendor/qrcode-generator/dist/qrcode.mjs";
import { stringToBytes } from "../vendor/qrcode-generator/dist/qrcode_UTF8.mjs";

qrcode.stringToBytes = stringToBytes;

const easeOut = (x) => 1 - Math.pow(1 - x, 3);

function finderAt(r, c, n) {
  return (r < 7 && c < 7) || (r < 7 && c >= n - 7) || (r >= n - 7 && c < 7);
}

function hash(r, c) {
  const x = Math.sin(r * 127.1 + c * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

export function drawQR(canvas, text, { animate = true } = {}) {
  const qr = qrcode(0, "M");
  qr.addData(text, "Byte");
  qr.make();
  const n = qr.getModuleCount();
  canvas.dataset.text = text;

  const modules = [];
  for (let r = 0; r < n; r += 1) {
    for (let c = 0; c < n; c += 1) {
      if (qr.isDark(r, c) && !finderAt(r, c, n)) {
        modules.push({ r, c, at: 160 + ((r + c) / (2 * n)) * 440 + hash(r, c) * 90 });
      }
    }
  }
  const finders = [[0, 0], [0, n - 7], [n - 7, 0]];

  let ink = "#000000";
  let ctx = null;
  let size = 0;
  let cell = 0;

  const setup = () => {
    const css = canvas.getBoundingClientRect().width || 100;
    const ratio = Math.min(window.devicePixelRatio || 1, 3);
    size = Math.round(css * ratio);
    canvas.width = size;
    canvas.height = size;
    ctx = canvas.getContext("2d");
    cell = size / (n + 2);
    ink = getComputedStyle(document.documentElement).getPropertyValue("--qr-ink").trim() || ink;
  };

  const paint = (elapsed) => {
    ctx.clearRect(0, 0, size, size);
    ctx.fillStyle = ink;
    finders.forEach(([r, c], i) => {
      const k = easeOut(Math.min(1, Math.max(0, (elapsed - i * 90) / 420)));
      if (k <= 0) return;
      const x = (c + 1) * cell;
      const y = (r + 1) * cell;
      const mid = 3.5 * cell;
      ctx.save();
      ctx.globalAlpha = k;
      ctx.translate(x + mid, y + mid);
      ctx.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k);
      ctx.beginPath();
      ctx.roundRect(-3.5 * cell, -3.5 * cell, 7 * cell, 7 * cell, 1.2 * cell);
      ctx.roundRect(-2.5 * cell, -2.5 * cell, 5 * cell, 5 * cell, 1 * cell);
      ctx.fill("evenodd");
      ctx.beginPath();
      ctx.roundRect(-1.5 * cell, -1.5 * cell, 3 * cell, 3 * cell, 0.9 * cell);
      ctx.fill();
      ctx.restore();
    });
    let done = true;
    for (const m of modules) {
      const k = easeOut(Math.min(1, Math.max(0, (elapsed - m.at) / 200)));
      if (k < 1) done = false;
      if (k <= 0) continue;
      const s = cell * 0.9 * (0.3 + 0.7 * k);
      const x = (m.c + 1.5) * cell - s / 2;
      const y = (m.r + 1.5) * cell - s / 2;
      ctx.globalAlpha = k;
      ctx.beginPath();
      ctx.roundRect(x, y, s, s, s * 0.42);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    return done;
  };

  setup();
  if (!animate) {
    paint(Infinity);
  } else {
    const start = performance.now();
    const frame = (now) => { if (!paint(now - start)) requestAnimationFrame(frame); };
    requestAnimationFrame(frame);
  }
  const redraw = () => { setup(); paint(Infinity); };
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redraw);
  window.matchMedia(`(resolution: ${window.devicePixelRatio}dppx)`).addEventListener("change", redraw);
}
