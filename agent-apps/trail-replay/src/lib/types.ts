export type Sport = "run" | "ride" | "hike"
export type Units = "km" | "mi"
export type ColorBy = "pace" | "heart" | "elevation"

export interface Summary {
  distance: number
  elapsed: number
  moving: number
  climb: number
  descent: number
  maxEle: number | null
  minEle: number | null
  avgHr: number | null
  maxHr: number | null
  avgSpeed: number
}

export interface ActivityMeta {
  id: string
  name: string
  sport: Sport
  start: string | null
  file: string
  summary: Summary
  bbox: [number, number, number, number]
  mini: [number, number][]
  has: { time: boolean; ele: "file" | "terrain" | "none"; hr: boolean; cad: boolean }
}

export interface Split {
  d: number
  t: number
  up: number
  down: number
  hr: number | null
}

export interface Track extends ActivityMeta {
  t: number[]
  lat: number[]
  lon: number[]
  d: number[]
  ele: number[] | null
  v: number[]
  hr: (number | null)[] | null
  cad: (number | null)[] | null
  splits: Split[]
}

export interface ActivityIndex {
  activities: ActivityMeta[]
  sample?: boolean
}
