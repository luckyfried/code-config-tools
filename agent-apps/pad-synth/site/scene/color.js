// Colors from the theme's tokens, and the pitch colors between the field's two colors. Pitch colors are mixed in
// OKLCH so the steps between two hues stay as vivid as the ends.

let probe = null;

/** Any CSS color as [r, g, b, a], each 0 to 1. */
export function parseColor(value) {
  probe = probe || document.createElement("canvas").getContext("2d");
  probe.fillStyle = "#000";
  probe.fillStyle = value.trim();
  const text = probe.fillStyle;
  if (text.startsWith("#")) {
    const n = parseInt(text.slice(1), 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1];
  }
  const parts = text.match(/[\d.]+/g) || ["0", "0", "0", "1"];
  return [parts[0] / 255, parts[1] / 255, parts[2] / 255, parts[3] === undefined ? 1 : Number(parts[3])];
}

/** The theme's tokens the canvases and the shader draw with. */
export function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const get = (name) => style.getPropertyValue(name).trim();
  const voices = {};
  for (const voice of ["pluck", "pad", "bass", "keys"]) voices[voice] = get(`--voice-${voice}`);
  return {
    bg: parseColor(get("--field-bg") || get("--color-bg")),
    a: parseColor(get("--field-a")),
    b: parseColor(get("--field-b")),
    light: Number(get("--field-mode")) === 1,
    text: get("--color-text"),
    muted: get("--color-muted"),
    accent: get("--color-accent"),
    track: get("--ring-track"),
    head: get("--ring-head"),
    core: get("--ring-core") || "#ffffff",
    scopeLine: get("--scope-line"),
    scopeGlow: get("--scope-glow"),
    spectrum: get("--spectrum"),
    spectrumCap: get("--spectrum-cap"),
    blend: get("--canvas-blend") || "source-over",
    voices,
  };
}

const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function toOklch([r, g, b]) {
  const [lr, lg, lb] = [toLinear(r), toLinear(g), toLinear(b)];
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return [L, Math.hypot(A, B), Math.atan2(B, A)];
}

function fromOklch([L, C, h]) {
  const A = C * Math.cos(h);
  const B = C * Math.sin(h);
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
  const rgb = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
  return rgb.map((c) => Math.min(1, Math.max(0, toGamma(Math.min(1, Math.max(0, c))))));
}

/** A color `t` of the way from `from` to `to` (0 to 1), the short way round the hue circle. */
export function mixOklch(from, to, t) {
  const p = toOklch(from);
  const q = toOklch(to);
  let dh = q[2] - p[2];
  if (dh > Math.PI) dh -= 2 * Math.PI;
  if (dh < -Math.PI) dh += 2 * Math.PI;
  return fromOklch([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + dh * t]);
}

/** The color of a note: the key's root is the field's first color, the notes above it walk toward the second. */
export function pitchColor(tokens, midi, rootIndex) {
  const step = (((midi - rootIndex) % 12) + 12) % 12;
  return mixOklch(tokens.a, tokens.b, step / 11);
}

export function cssRgb([r, g, b]) {
  return `rgb(${Math.round(r * 255)} ${Math.round(g * 255)} ${Math.round(b * 255)})`;
}
