// How the night hardens: every thirty seconds the fog thickens, the ships come faster, and from the second step two
// may come at once.
export function level(seconds) {
  return Math.floor(seconds / 30);
}

export function pace(seconds) {
  const l = level(seconds);
  return {
    level: l,
    speed: 5.2 * Math.pow(1.08, l),
    every: Math.max(3.4, 7.2 - l * 0.45),
    pair: l >= 2 ? Math.min(0.85, 0.35 + (l - 2) * 0.1) : 0,
    fog: 1 + Math.min(0.7, l * 0.07),
    most: Math.min(9, 4 + l),
  };
}
