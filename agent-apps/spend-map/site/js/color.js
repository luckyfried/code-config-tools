// Category colors pass through the theme: OKLCH chroma and lightness come from the theme's tokens, so the same input
// color reads as ink on Ledger and as light on Vault.
const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function hexToOklch(hex) {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => toLinear(v / 255));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  return { L, C: Math.hypot(A, B), H: Math.atan2(B, A) };
}

function oklchToHex({ L, C, H }) {
  for (let c = C; c >= 0; c -= 0.005) {
    const A = c * Math.cos(H);
    const B = c * Math.sin(H);
    const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
    const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
    const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
    const rgb = [
      4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ];
    if (rgb.every((v) => v >= -0.0005 && v <= 1.0005)) {
      return `#${rgb.map((v) => Math.round(toGamma(Math.min(1, Math.max(0, v))) * 255).toString(16).padStart(2, "0")).join("")}`;
    }
  }
  return "#808080";
}

export function readTone() {
  const css = getComputedStyle(document.documentElement);
  const num = (name, fallback) => {
    const v = parseFloat(css.getPropertyValue(name));
    return Number.isFinite(v) ? v : fallback;
  };
  return {
    look: css.getPropertyValue("--look").trim() || "ledger",
    chroma: num("--chroma-scale", 1),
    lmin: num("--lightness-min", 0.5),
    lmax: num("--lightness-max", 0.75),
    lift: num("--merchant-lift", 0.1),
    mchroma: num("--merchant-chroma", 0.7),
    income: css.getPropertyValue("--color-income").trim(),
    saved: css.getPropertyValue("--color-saved").trim(),
    other: css.getPropertyValue("--color-other").trim(),
  };
}

export function categoryColor(hex, tone) {
  const c = hexToOklch(hex);
  return oklchToHex({ L: Math.min(tone.lmax, Math.max(tone.lmin, c.L)), C: c.C * tone.chroma, H: c.H });
}

export function merchantColor(hex, tone, rank) {
  const c = hexToOklch(categoryColor(hex, tone));
  const step = Math.min(rank, 6) * 0.012 * Math.sign(tone.lift);
  return oklchToHex({ L: Math.min(0.95, Math.max(0.2, c.L + tone.lift + step)), C: c.C * tone.mchroma, H: c.H });
}
