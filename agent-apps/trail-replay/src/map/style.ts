import type { ExpressionSpecification, LayerSpecification, StyleSpecification } from "maplibre-gl"
import { token } from "@/lib/tokens"
import type { Track } from "@/lib/types"
import { TERRAIN_ATTRIBUTION } from "./terrain"

export const EXAGGERATION = 1.4
const OPENFREEMAP = "https://tiles.openfreemap.org/planet"
const OPENFREEMAP_ATTRIBUTION =
  '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'

function relief(track: Track | null): ExpressionSpecification {
  const low = (track?.summary.minEle ?? 1500) - 250
  const high = (track?.summary.maxEle ?? 2500) + 450
  const step = (high - low) / 4
  const stops: (number | string)[] = []
  for (let n = 0; n < 5; n++) stops.push(Math.round(low + step * n), token(`relief-${n + 1}`))
  return ["interpolate", ["linear"], ["elevation"], ...stops] as unknown as ExpressionSpecification
}

function labelLayers(): LayerSpecification[] {
  return [
    { id: "water", type: "fill", source: "streets", "source-layer": "water", paint: { "fill-color": token("water"), "fill-opacity": 0.75 } },
    {
      id: "roads",
      type: "line",
      source: "streets",
      "source-layer": "transportation",
      filter: ["in", ["get", "class"], ["literal", ["motorway", "trunk", "primary", "secondary", "tertiary", "minor", "track", "path"]]],
      paint: {
        "line-color": token("road"),
        "line-opacity": 0.55,
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 0.4, 15, ["match", ["get", "class"], ["path", "track"], 1, 2]],
        "line-dasharray": ["match", ["get", "class"], ["path", "track"], ["literal", [2, 1.5]], ["literal", [1, 0]]],
      },
    },
    {
      id: "places",
      type: "symbol",
      source: "streets",
      "source-layer": "place",
      layout: { "text-field": ["get", "name"], "text-font": ["Noto Sans Regular"], "text-size": 12 },
      paint: { "text-color": token("foreground"), "text-halo-color": token("background", 0.85), "text-halo-width": 1.4 },
    },
  ]
}

export interface StyleOptions {
  track: Track | null
  labels: boolean
  terrain: boolean
}

export function buildStyle({ track, labels, terrain }: StyleOptions): StyleSpecification {
  const dem = {
    type: "raster-dem" as const,
    tiles: ["dem://{z}/{x}/{y}"],
    tileSize: 256,
    encoding: "terrarium" as const,
    maxzoom: 13,
    attribution: TERRAIN_ATTRIBUTION,
  }
  const style: StyleSpecification = {
    version: 8,
    sources: {
      "dem-shade": dem,
      "dem-terrain": { type: dem.type, tiles: dem.tiles, tileSize: dem.tileSize, encoding: dem.encoding, maxzoom: dem.maxzoom },
    },
    sky: {
      "sky-color": token("sky"),
      "horizon-color": token("horizon"),
      "fog-color": token("fog"),
      "sky-horizon-blend": 0.7,
      "horizon-fog-blend": 0.8,
      "fog-ground-blend": 0.75,
      "atmosphere-blend": 0,
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": token("map-bg") } },
      { id: "relief", type: "color-relief", source: "dem-shade", paint: { "color-relief-color": relief(track), "color-relief-opacity": 1 } },
      {
        id: "hillshade",
        type: "hillshade",
        source: "dem-shade",
        paint: {
          "hillshade-shadow-color": token("shade-shadow"),
          "hillshade-highlight-color": token("shade-highlight"),
          "hillshade-accent-color": token("shade-accent"),
          "hillshade-exaggeration": 0.62,
          "hillshade-illumination-direction": 315,
        },
      },
      ...(labels ? labelLayers() : []),
    ],
  }
  if (terrain) style.terrain = { source: "dem-terrain", exaggeration: EXAGGERATION }
  if (labels) {
    style.sources.streets = { type: "vector", url: OPENFREEMAP, attribution: OPENFREEMAP_ATTRIBUTION }
    style.glyphs = "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf"
  }
  return style
}
