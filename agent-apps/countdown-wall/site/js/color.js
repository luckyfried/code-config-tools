// Event colors: one hex in, the family of tokens a tile and the hero read out (themes pick which ones they use).

const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => v / 255);
}

function rgbToOklch([r, g, b]) {
  const [lr, lg, lb] = [r, g, b].map(toLinear);
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return [L, Math.hypot(A, B), ((Math.atan2(B, A) * 180) / Math.PI + 360) % 360];
}

function oklchToLinear(L, C, H) {
  const h = (H * Math.PI) / 180;
  const A = C * Math.cos(h);
  const B = C * Math.sin(h);
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const inGamut = (rgb) => rgb.every((v) => v >= -0.0001 && v <= 1.0001);

// The nearest color in sRGB at this lightness and hue: chroma comes down until it fits.
function oklchToHex(L, C, H) {
  let lo = 0;
  let hi = C;
  let rgb = oklchToLinear(L, C, H);
  if (!inGamut(rgb)) {
    for (let i = 0; i < 20; i += 1) {
      const mid = (lo + hi) / 2;
      if (inGamut(oklchToLinear(L, mid, H))) lo = mid;
      else hi = mid;
    }
    rgb = oklchToLinear(L, lo, H);
  }
  return (
    "#" +
    rgb
      .map((v) => Math.round(Math.min(1, Math.max(0, toGamma(Math.min(1, Math.max(0, v))))) * 255))
      .map((v) => v.toString(16).padStart(2, "0"))
      .join("")
  );
}

function luminance(hex) {
  const [r, g, b] = hexToRgb(hex).map(toLinear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

const contrast = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

/** The custom properties one event's color gives the element that shows it. */
export function eventTokens(hex) {
  const [L, C, H] = rgbToOklch(hexToRgb(hex));
  const chroma = Math.max(C, 0.06);
  const lum = luminance(hex);
  const darkInk = contrast(lum, 0.008) >= contrast(lum, 1);
  return {
    "--event": hex,
    "--event-2": oklchToHex(Math.min(0.82, L + 0.06), chroma, H + 38),
    "--event-3": oklchToHex(Math.max(0.42, L - 0.1), chroma, H - 34),
    "--event-deep": oklchToHex(0.42, chroma, H - 28),
    "--event-soft": oklchToHex(0.8, Math.min(chroma, 0.12), H),
    "--event-2-soft": oklchToHex(0.86, Math.min(chroma, 0.1), H + 38),
    "--event-3-soft": oklchToHex(0.76, Math.min(chroma, 0.13), H - 34),
    "--event-pale": oklchToHex(0.93, Math.min(chroma, 0.035), H),
    "--event-bright": oklchToHex(Math.max(L, 0.74), chroma, H),
    "--event-dark": oklchToHex(0.44, Math.min(chroma, 0.14), H),
    "--event-ink": darkInk ? "#0b0a09" : "#ffffff",
    "--event-ink-soft": darkInk ? "rgba(11, 10, 9, 0.7)" : "rgba(255, 255, 255, 0.78)",
    "--event-track": darkInk ? "rgba(11, 10, 9, 0.14)" : "rgba(255, 255, 255, 0.2)",
  };
}

/** Writes an event's color onto an element and marks it so the theme's event tokens apply there. */
export function paint(el, hex) {
  el.setAttribute("data-event", "");
  for (const [name, value] of Object.entries(eventTokens(hex))) el.style.setProperty(name, value);
}
