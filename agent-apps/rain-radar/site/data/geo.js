// Web Mercator math. The map is one square extent around the place, measured in tiles at the map's zoom;
// every layer (map, radar frames, wind, clouds) is drawn over that same square, so one uv means one spot on Earth.

export const SPAN = 8; // the extent is SPAN tiles wide at the map zoom
export const ZOOMS = { town: 9, region: 7 };

export function lonToX(lon, z) {
  return ((lon + 180) / 360) * 2 ** z;
}

export function latToY(lat, z) {
  const r = (Math.max(-85, Math.min(85, lat)) * Math.PI) / 180;
  return ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * 2 ** z;
}

export function xToLon(x, z) {
  return (x / 2 ** z) * 360 - 180;
}

export function yToLat(y, z) {
  const n = Math.PI - (2 * Math.PI * y) / 2 ** z;
  return (180 / Math.PI) * Math.atan(Math.sinh(n));
}

export function extentAround(lat, lon, zoomName) {
  const z = ZOOMS[zoomName] ?? ZOOMS.town;
  const cx = lonToX(lon, z);
  const cy = latToY(lat, z);
  return { z, x0: cx - SPAN / 2, y0: cy - SPAN / 2, x1: cx + SPAN / 2, y1: cy + SPAN / 2, lat, lon };
}

// Kilometers across the extent at its middle latitude.
export function extentKm(ext) {
  const circ = 40075 * Math.cos((ext.lat * Math.PI) / 180);
  return (circ * SPAN) / 2 ** ext.z;
}

// The 7 by 7 forecast points, north row first, west to east.
export function gridPoints(ext, n = 7) {
  const pts = [];
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = ext.x0 + ((i + 0.5) / n) * (ext.x1 - ext.x0);
      const y = ext.y0 + ((j + 0.5) / n) * (ext.y1 - ext.y0);
      pts.push({ lat: yToLat(y, ext.z), lon: xToLon(x, ext.z) });
    }
  }
  return pts;
}
