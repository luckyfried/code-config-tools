// What the person picks in Settings, kept in this browser under the one key "rain-radar". The setup's own place
// is the starting point: when the agent writes a new place into the inputs, a place picked earlier gives way to it.

const KEY = "rain-radar";
const LAYERS = ["radar", "wind", "clouds"];

export function loadState(config) {
  const base = {
    place: { name: String(config.place || "Your place"), lat: Number(config.lat) || 0, lon: Number(config.lon) || 0 },
    zoom: config.zoom === "region" ? "region" : "town",
    layers: Array.isArray(config.layers) ? config.layers.filter((l) => LAYERS.includes(l)) : ["radar", "wind"],
    units: config.units === "imperial" ? "imperial" : "metric",
    speed: "normal",
  };
  const origin = `${base.place.lat.toFixed(4)},${base.place.lon.toFixed(4)}`;
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(KEY) || "{}") || {};
  } catch {
    saved = {};
  }
  const state = { ...base, origin };
  if (saved.origin === origin) {
    if (saved.place && Number.isFinite(saved.place.lat) && Number.isFinite(saved.place.lon)) state.place = saved.place;
    if (saved.zoom === "town" || saved.zoom === "region") state.zoom = saved.zoom;
    if (Array.isArray(saved.layers)) state.layers = saved.layers.filter((l) => LAYERS.includes(l));
    if (saved.units === "metric" || saved.units === "imperial") state.units = saved.units;
    if (["slow", "normal", "fast"].includes(saved.speed)) state.speed = saved.speed;
  }
  return state;
}

export function saveState(state) {
  const { place, zoom, layers, units, speed, origin } = state;
  try {
    localStorage.setItem(KEY, JSON.stringify({ origin, place, zoom, layers, units, speed }));
  } catch {
    // a private window without storage keeps the choices for this visit only
  }
}
