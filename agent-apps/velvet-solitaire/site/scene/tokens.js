// Reads the theme's tokens off the page, so the scene takes its palette and light from the
// same CSS custom properties that color the rail. Swap the theme file and the world recolors.

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const raw = (name) => css.getPropertyValue(name).trim();
  return {
    raw,
    color(name, fallback = "#808080") {
      return raw(name) || fallback;
    },
    number(name, fallback = 0) {
      const v = parseFloat(raw(name));
      return Number.isFinite(v) ? v : fallback;
    },
  };
}
