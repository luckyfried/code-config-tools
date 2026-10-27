// Where a station sits on the scale: stations spread evenly between 88 and 108, like a broadcast band.
export const BAND_LOW = 88
export const BAND_HIGH = 108

export function slot(index: number, count: number) {
  if (count <= 0) return 0.5
  return (index + 0.5) / count
}

export function frequency(position: number) {
  return (BAND_LOW + (BAND_HIGH - BAND_LOW) * position).toFixed(1)
}
