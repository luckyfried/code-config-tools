// The color of the sky at each local hour: key colors come from the theme's --sky-* tokens, and the hours between them
// are blended in OKLab so night navy runs through dawn, day, and dusk without muddy middles.
const KEYS = [
  [0, "night"], [4.6, "night"], [5.5, "predawn"], [6.2, "dawn"], [6.9, "sunrise"], [8, "morning"],
  [12.5, "noon"], [15.8, "afternoon"], [17.3, "golden"], [18.2, "sunset"], [19, "dusk"], [19.8, "twilight"],
  [21.4, "evening"], [23, "night"], [24, "night"],
];

function toLinear(c) { return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; }
function toSrgb(c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; }

function hexToLab(hex) {
  const v = hex.trim().replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => toLinear(parseInt(v.slice(i, i + 2), 16) / 255));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

function labToRgb([L, A, B]) {
  const l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3;
  const m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3;
  const s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ].map((c) => Math.round(Math.min(1, Math.max(0, toSrgb(Math.min(1, Math.max(0, c))))) * 255));
}

export function readPalette() {
  const css = getComputedStyle(document.documentElement);
  const keys = KEYS.map(([h, name]) => [h, hexToLab(css.getPropertyValue(`--sky-${name}`) || "#000000")]);
  return { keys };
}

/** The sky at local minute `minute` (0 to 1440): { css, light } where light says dark text reads on it. */
export function skyAt(palette, minute) {
  const h = (((minute / 60) % 24) + 24) % 24;
  const { keys } = palette;
  let i = 0;
  while (i < keys.length - 2 && keys[i + 1][0] <= h) i++;
  const [h0, a] = keys[i];
  const [h1, b] = keys[i + 1];
  const t = h1 === h0 ? 0 : (h - h0) / (h1 - h0);
  const e = t * t * (3 - 2 * t);
  const lab = [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e];
  const [r, g, bl] = labToRgb(lab);
  return { css: `rgb(${r} ${g} ${bl})`, light: lab[0] > 0.72 };
}
