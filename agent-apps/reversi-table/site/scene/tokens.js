// The theme's scene tokens, read from the page's CSS so a theme recolors the table as well as the page.
const unquote = (value) => value.replace(/^["']|["']$/g, "");

export function readTokens(root = document.documentElement) {
  const style = getComputedStyle(root);
  const get = (name) => style.getPropertyValue(`--${name}`).trim();
  const num = (name, fallback) => {
    const value = parseFloat(get(name));
    return Number.isFinite(value) ? value : fallback;
  };
  return {
    bg: get("color-bg") || "#888888",
    table: get("scene-table") || "#cccccc",
    tableEdge: get("scene-table-edge") || "#888888",
    tableTexture: get("scene-table-texture") || "stone",
    board: get("scene-board") || "#0e4d37",
    board2: get("scene-board-2") || "#093826",
    boardTexture: get("scene-board-texture") || "lacquer",
    line: get("scene-line") || "#052419",
    lineHi: get("scene-line-hi") || "#2c7356",
    lineGlow: num("scene-line-glow", 0),
    rim: get("scene-rim") || "#141816",
    tray: get("scene-tray") || "#141816",
    trayFloor: get("scene-tray-floor") || "#0b3a29",
    discLight: get("disc-light") || "#efe9db",
    discDark: get("disc-dark") || "#161616",
    discSheen: get("disc-sheen") || "#cfe0ff",
    glow: get("scene-glow") || "#c99a2e",
    glowAdd: get("scene-glow-blend") === "add",
    reflect: num("scene-reflect", 0.2),
    env: num("scene-env", 1),
    key: num("scene-key", 2.4),
    keyColor: get("scene-key-color") || "#ffffff",
    exposure: num("scene-exposure", 1),
    sideDark: unquote(get("side-dark")) || "Black",
    sideLight: unquote(get("side-light")) || "White",
  };
}
