// The live feeds: RainViewer's frame list and radar tiles, Open-Meteo's forecast for the 7 by 7 grid, and the map tiles.
import { mosaic } from "./tiles.js";
import { gridPoints } from "./geo.js";

const RADAR_INDEX = "https://api.rainviewer.com/public/weather-maps.json";
const FORECAST = "https://api.open-meteo.com/v1/forecast";
const GEOCODE = "https://geocoding-api.open-meteo.com/v1/search";
const BASEMAPS = {
  dark: "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
  paper: "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
};
const RADAR_MAX_ZOOM = 7;

export async function fetchJSON(url, ms = 9000) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);
  try {
    const res = await fetch(url, { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

// The frame list: the past two hours and, when the feed carries it, the nowcast, ten minutes apart.
export async function radarIndex() {
  const data = await fetchJSON(RADAR_INDEX);
  const past = (data.radar?.past ?? []).map((f) => ({ ...f, nowcast: false }));
  const next = (data.radar?.nowcast ?? []).map((f) => ({ ...f, nowcast: true }));
  const frames = [...past, ...next].filter((f) => f.path && f.time);
  if (!frames.length) throw new Error("no frames");
  return { host: data.host || "https://tilecache.rainviewer.com", frames };
}

export async function radarFrames(index, ext, size, onFrame) {
  const zoom = Math.min(ext.z, RADAR_MAX_ZOOM);
  const out = [];
  await Promise.all(
    index.frames.map(async (f, i) => {
      const template = `${index.host}${f.path}/256/{z}/{x}/{y}/2/1_1.png`;
      const { canvas, loaded } = await mosaic(template, zoom, ext, size);
      out[i] = { time: f.time * 1000, nowcast: f.nowcast, image: canvas, ok: loaded > 0 };
      onFrame?.();
    }),
  );
  return out;
}

export async function basemap(ext, look, size) {
  const zoom = ext.z;
  const { canvas, loaded, failed } = await mosaic(BASEMAPS[look] ?? BASEMAPS.dark, zoom, ext, size);
  if (loaded === 0 || failed > loaded) throw new Error("map tiles");
  return canvas;
}

// One call for 49 points: hourly wind and cloud cover, and the precipitation every 15 minutes.
export async function forecast(ext) {
  const pts = gridPoints(ext);
  const q = new URLSearchParams({
    latitude: pts.map((p) => p.lat.toFixed(3)).join(","),
    longitude: pts.map((p) => p.lon.toFixed(3)).join(","),
    hourly: "wind_speed_10m,wind_direction_10m,cloud_cover",
    minutely_15: "precipitation",
    forecast_hours: "3",
    forecast_minutely_15: "10",
    wind_speed_unit: "ms",
    timeformat: "unixtime",
    timezone: "auto",
  });
  const data = await fetchJSON(`${FORECAST}?${q}`, 12000);
  const list = Array.isArray(data) ? data : [data];
  if (list.length !== pts.length) throw new Error("forecast size");
  const now = Date.now() / 1000;
  const u = new Float32Array(49);
  const v = new Float32Array(49);
  const cloud = new Float32Array(49);
  list.forEach((loc, k) => {
    const h = loc.hourly;
    let idx = 0;
    for (let i = 0; i < h.time.length; i++) if (h.time[i] <= now) idx = i;
    const s = h.wind_speed_10m[idx] ?? 0;
    const d = ((h.wind_direction_10m[idx] ?? 0) * Math.PI) / 180;
    u[k] = -s * Math.sin(d);
    v[k] = -s * Math.cos(d);
    cloud[k] = (h.cloud_cover[idx] ?? 0) / 100;
  });
  const mid = list[24];
  const m = mid.minutely_15;
  const minutely = [];
  for (let i = 0; i < m.time.length; i++) {
    if (m.time[i] <= now) continue; // each value is the sum of the 15 minutes before its time
    minutely.push({ time: (m.time[i] - 900) * 1000, rate: (m.precipitation[i] ?? 0) * 4 });
  }
  const speed = Math.hypot(u[24], v[24]);
  const from = (Math.atan2(-u[24], -v[24]) * 180) / Math.PI;
  return { u, v, cloud, minutely: minutely.slice(0, 8), windNow: { speed, from: (from + 360) % 360 } };
}

export async function searchPlaces(name) {
  const q = new URLSearchParams({ name, count: "6", language: "en", format: "json" });
  const data = await fetchJSON(`${GEOCODE}?${q}`, 8000);
  return (data.results ?? []).map((r) => ({
    name: r.name,
    lat: r.latitude,
    lon: r.longitude,
    where: [r.admin1, r.country].filter(Boolean).join(", "),
  }));
}
