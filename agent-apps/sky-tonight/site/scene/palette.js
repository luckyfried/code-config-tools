// The scene's palette, read from the theme's tokens so a theme recolors the sky, the lines, and the ground.

const COLOR_TOKENS = {
  nightZ: "--sky-night-zenith",
  nightH: "--sky-night-horizon",
  astroZ: "--sky-astro-zenith",
  astroH: "--sky-astro-horizon",
  nautZ: "--sky-nautical-zenith",
  nautH: "--sky-nautical-horizon",
  civilRim: "--sky-civil-rim",
  dayZ: "--sky-day-zenith",
  dayH: "--sky-day-horizon",
  glow: "--sky-glow",
  ground: "--sky-ground",
  groundHaze: "--sky-ground-haze",
  light: "--sky-light",
  line: "--sky-line",
  lineArt: "--sky-line-art",
  ink: "--sky-ink",
  starTint: "--sky-star-tint",
};

const NUMBER_TOKENS = {
  inkMode: "--sky-ink-mode",
  starMono: "--sky-star-mono",
  starGain: "--sky-star-gain",
  milkyWay: "--sky-milkyway",
  twinkle: "--sky-twinkle",
};

export function parseColor(text) {
  const s = text.trim();
  if (s.startsWith("#")) {
    let h = s.slice(1);
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    const n = parseInt(h.slice(0, 6), 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }
  const m = s.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const p = m[1].split(",").map((x) => parseFloat(x));
    return [p[0] / 255, p[1] / 255, p[2] / 255];
  }
  return [0, 0, 0];
}

export function readPalette(root = document.documentElement) {
  const cs = getComputedStyle(root);
  const palette = {};
  for (const [key, name] of Object.entries(COLOR_TOKENS)) palette[key] = parseColor(cs.getPropertyValue(name) || "#000");
  for (const [key, name] of Object.entries(NUMBER_TOKENS)) {
    const v = parseFloat(cs.getPropertyValue(name));
    palette[key] = Number.isFinite(v) ? v : 0;
  }
  return palette;
}
