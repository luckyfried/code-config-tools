// Piece shapes as data. Each lathe profile is a list of [radius, height] points from the center of the base up to the
// center of the top, in board units (one square is 1). Swap an array to restyle a piece; pieces.js turns these into
// glass. The knight's head is a side silhouette (x forward, y up) extruded with a beveled edge on a lathe base.

// Points on a circular arc, for heads and rounded collars.
export function arc(cx, cy, r, fromDeg, toDeg, steps = 10) {
  const out = [];
  for (let i = 0; i <= steps; i++) {
    const a = ((fromDeg + ((toDeg - fromDeg) * i) / steps) * Math.PI) / 180;
    out.push([Math.max(0, cx + r * Math.cos(a)), cy + r * Math.sin(a)]);
  }
  return out;
}

// The shared foot: a flat base, a rounded plinth, and a fillet into the stem.
function foot(r, h) {
  return [
    [0, 0], [r, 0], [r, h * 0.28], ...arc(r - h * 0.18, h * 0.32, h * 0.18, -10, 80, 5),
    [r * 0.86, h * 0.56], ...arc(r * 0.86, h * 0.72, h * 0.16, -80, 80, 6), [r * 0.74, h * 0.92], [r * 0.66, h],
  ];
}

export const profiles = {
  pawn: [
    ...foot(0.3, 0.17),
    [0.17, 0.21], [0.125, 0.29], [0.1, 0.38], [0.092, 0.45],
    [0.17, 0.47], ...arc(0.17, 0.49, 0.02, -90, 90, 4), [0.1, 0.515],
    ...arc(0, 0.625, 0.135, -55, 90, 12),
  ],
  rook: [
    ...foot(0.34, 0.19),
    [0.25, 0.24], [0.215, 0.32], [0.2, 0.5], [0.205, 0.66], [0.24, 0.72],
    ...arc(0.255, 0.745, 0.025, -90, 90, 4), [0.27, 0.78], [0.275, 0.88], [0.19, 0.88], [0.19, 0.84], [0, 0.84],
  ],
  bishop: [
    ...foot(0.32, 0.18),
    [0.2, 0.23], [0.15, 0.32], [0.115, 0.46], [0.1, 0.6],
    [0.19, 0.625], ...arc(0.19, 0.645, 0.02, -90, 90, 4), [0.12, 0.67], [0.15, 0.695],
    ...arc(0.15, 0.715, 0.02, -90, 90, 4), [0.1, 0.74],
    [0.135, 0.78], [0.16, 0.84], [0.163, 0.9], [0.15, 0.96], [0.12, 1.01], [0.08, 1.05], [0.035, 1.075],
    [0.03, 1.085], ...arc(0, 1.125, 0.045, -45, 90, 8),
  ],
  queen: [
    ...foot(0.35, 0.2),
    [0.23, 0.25], [0.17, 0.35], [0.13, 0.52], [0.11, 0.72], [0.115, 0.84],
    [0.215, 0.865], ...arc(0.215, 0.89, 0.025, -90, 90, 4), [0.14, 0.915], [0.18, 0.94],
    ...arc(0.18, 0.96, 0.02, -90, 90, 4), [0.13, 0.985],
    [0.15, 1.04], [0.19, 1.12], [0.225, 1.2], [0.2, 1.215], [0.15, 1.2], [0.1, 1.215], [0.075, 1.25],
    ...arc(0, 1.315, 0.065, -60, 90, 10),
  ],
  king: [
    ...foot(0.36, 0.21),
    [0.24, 0.26], [0.18, 0.37], [0.135, 0.56], [0.12, 0.78], [0.125, 0.92],
    [0.23, 0.945], ...arc(0.23, 0.97, 0.025, -90, 90, 4), [0.15, 0.995], [0.19, 1.02],
    ...arc(0.19, 1.04, 0.02, -90, 90, 4), [0.14, 1.065],
    [0.16, 1.12], [0.2, 1.22], [0.215, 1.29], [0.18, 1.33], [0.11, 1.36], [0.06, 1.37], [0, 1.372],
  ],
  // The knight's lathe base; its head stands on top of it.
  knight: [
    ...foot(0.33, 0.19),
    [0.25, 0.235], ...arc(0.25, 0.255, 0.02, -90, 90, 4), [0.22, 0.28], [0, 0.28],
  ],
};

// Crenellations on the rook: merlons as annular sectors, in degrees, extruded upward from the rim.
export const rookMerlons = { count: 5, spanDeg: 46, inner: 0.19, outer: 0.275, bottom: 0.86, top: 0.97 };

// Coronet beads on the queen's crown rim.
export const queenBeads = { count: 8, radius: 0.034, ring: 0.212, height: 1.225 };

// The king's cross, as a 2D outline extruded front to back.
export const kingCross = {
  base: 1.35, depth: 0.075,
  outline: [[-0.035, 0], [0.035, 0], [0.035, 0.13], [0.1, 0.13], [0.1, 0.19], [0.035, 0.19], [0.035, 0.27],
    [-0.035, 0.27], [-0.035, 0.19], [-0.1, 0.19], [-0.1, 0.13], [-0.035, 0.13]],
};

// The knight's head: a closed silhouette facing +x, drawn with quadratic curves as [cx, cy, x, y] after the first
// point, then extruded `depth` deep with a rounded bevel.
export const knightHead = {
  depth: 0.24, bevel: 0.045,
  start: [-0.21, 0.26],
  path: [
    [0, 0.25, 0.2, 0.26],
    [0.25, 0.36, 0.2, 0.5],
    [0.15, 0.6, 0.2, 0.66],
    [0.3, 0.7, 0.4, 0.71],
    [0.47, 0.73, 0.46, 0.8],
    [0.45, 0.87, 0.36, 0.91],
    [0.27, 0.97, 0.17, 1.02],
    [0.13, 1.08, 0.08, 1.15],
    [0.04, 1.1, 0.0, 1.07],
    [-0.08, 1.06, -0.15, 1.0],
    [-0.27, 0.86, -0.27, 0.62],
    [-0.27, 0.4, -0.21, 0.26],
  ],
};

// Heights for the camera fit, the shadows, the capture sink, and the king's tip.
export const heights = { pawn: 0.76, rook: 0.97, bishop: 1.17, knight: 1.15, queen: 1.38, king: 1.62 };
export const footRadius = { pawn: 0.3, rook: 0.34, bishop: 0.32, knight: 0.33, queen: 0.35, king: 0.36 };
