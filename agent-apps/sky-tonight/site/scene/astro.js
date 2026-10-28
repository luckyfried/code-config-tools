// Sky geometry: the one rotation from J2000 equatorial to the viewer's horizon, the stereographic projection every
// shader shares, and the Sun, Moon, and planets from astronomy-engine.
import * as A from "astronomy-engine";

export const DEG = Math.PI / 180;

// World frame of every scene module: +x east, +y up (zenith), +z south, so north is -z.
export function eqVector(raDeg, decDeg) {
  const ra = raDeg * DEG;
  const dec = decDeg * DEG;
  const c = Math.cos(dec);
  return [c * Math.cos(ra), c * Math.sin(ra), Math.sin(dec)];
}

// J2000 equatorial to world, as a row-major 3x3 (rows are world x, y, z). astronomy-engine's horizontal frame is
// x north, y west, z zenith, and it stores rotations column-major (v'_i = sum_j rot[j][i] v_j).
export function skyMatrix(date, observer, out = new Float64Array(9)) {
  const r = A.Rotation_EQJ_HOR(date, observer).rot;
  for (let j = 0; j < 3; j += 1) {
    out[0 + j] = -r[j][1];
    out[3 + j] = r[j][2];
    out[6 + j] = -r[j][0];
  }
  return out;
}

export function apply(m, v, out = [0, 0, 0]) {
  const x = v[0], y = v[1], z = v[2];
  out[0] = m[0] * x + m[1] * y + m[2] * z;
  out[1] = m[3] * x + m[4] * y + m[5] * z;
  out[2] = m[6] * x + m[7] * y + m[8] * z;
  return out;
}

export function altAz(w) {
  const alt = Math.asin(Math.max(-1, Math.min(1, w[1]))) / DEG;
  let az = Math.atan2(w[0], -w[2]) / DEG;
  if (az < 0) az += 360;
  return { alt, az };
}

export function worldFromAltAz(altDeg, azDeg) {
  const a = altDeg * DEG, z = azDeg * DEG;
  return [Math.sin(z) * Math.cos(a), Math.sin(a), -Math.cos(z) * Math.cos(a)];
}

// The galactic frame of the ESO panorama, from J2000 equatorial (IAU 1958, J2000 form).
export const EQ_TO_GAL = [
  -0.0548755604, -0.8734370902, -0.4838350155,
  0.4941094279, -0.44482963, 0.7469822445,
  -0.867666149, -0.1980763734, 0.4559837762,
];

// Camera: a view direction from yaw (azimuth) and pitch (altitude), with the horizon kept level.
export function viewBasis(yawDeg, pitchDeg, out = new Float64Array(9)) {
  const f = worldFromAltAz(pitchDeg, yawDeg);
  // right = forward x up, normalized; level horizon
  let rx = -f[2], rz = f[0];
  const rl = Math.hypot(rx, rz) || 1;
  rx /= rl; rz /= rl;
  // up = right x forward
  const ux = 0 * f[2] - rz * f[1];
  const uy = rz * f[0] - rx * f[2];
  const uz = rx * f[1] - 0 * f[0];
  // rows: right, up, back (-forward); world -> view
  out[0] = rx; out[1] = 0; out[2] = rz;
  out[3] = ux; out[4] = uy; out[5] = uz;
  out[6] = -f[0]; out[7] = -f[1]; out[8] = -f[2];
  return out;
}

// Stereographic projection of a view-space direction to pixels from the screen center (y up). `k` is pixels per
// projected unit. Points more than about 150 degrees off the view axis are reported as hidden.
export function project(v, k, out) {
  const f = -v[2];
  if (f < -0.85) { out.visible = false; return out; }
  const s = (2 * k) / (1 + f);
  out.x = v[0] * s;
  out.y = v[1] * s;
  out.f = f;
  out.visible = true;
  return out;
}

export function unproject(px, py, k, out = [0, 0, 0]) {
  const x = px / k, y = py / k;
  const r2 = x * x + y * y;
  const d = 4 + r2;
  out[0] = (4 * x) / d;
  out[1] = (4 * y) / d;
  out[2] = -(4 - r2) / d;
  return out;
}

// Pixels per projected unit so that `fovDeg` spans the smaller side of the screen.
export function scaleFor(fovDeg, minSidePx) {
  return minSidePx / 2 / (2 * Math.tan((fovDeg * DEG) / 4));
}

export function makeObserver(lat, lon) {
  return new A.Observer(lat, lon, 0);
}

export const PLANETS = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"];

// J2000 topocentric unit vectors and brightness of the Sun, Moon, and planets at `date`.
export function bodies(date, observer, previous = null) {
  const out = {};
  const unit = (v) => {
    const l = Math.hypot(v.x, v.y, v.z);
    return [v.x / l, v.y / l, v.z / l];
  };
  for (const name of ["Sun", "Moon", ...PLANETS]) {
    const eq = A.Equator(name, date, observer, false, true);
    const entry = { name, dir: unit(eq.vec), dist: eq.dist };
    if (name !== "Sun" && previous && previous[name]) {
      entry.mag = previous[name].mag;
      entry.phase = previous[name].phase;
      entry.phaseAngle = previous[name].phaseAngle;
    } else if (name !== "Sun") {
      try {
        const ill = A.Illumination(name, date);
        entry.mag = ill.mag;
        entry.phase = ill.phase_fraction;
        entry.phaseAngle = ill.phase_angle;
      } catch {
        entry.mag = 6;
        entry.phase = 1;
      }
    }
    out[name] = entry;
  }
  return out;
}

export function moonPhaseName(date) {
  const deg = A.MoonPhase(date);
  if (deg < 6 || deg >= 354) return "New moon";
  if (deg < 84) return "Waxing crescent";
  if (deg < 96) return "First quarter";
  if (deg < 174) return "Waxing gibbous";
  if (deg < 186) return "Full moon";
  if (deg < 264) return "Waning gibbous";
  if (deg < 276) return "Last quarter";
  return "Waning crescent";
}

export function moonPhaseAngle(date) {
  return A.MoonPhase(date);
}

export function sunAltitude(date, observer) {
  const eq = A.Equator("Sun", date, observer, true, true);
  return A.Horizon(date, observer, eq.ra, eq.dec, "").altitude;
}

export function bodyAltitude(name, date, observer) {
  const eq = A.Equator(name, date, observer, true, true);
  return A.Horizon(date, observer, eq.ra, eq.dec, "").altitude;
}

export function searchRiseSet(name, observer, direction, start, days) {
  try {
    const t = A.SearchRiseSet(name, observer, direction, start, days);
    return t ? t.date : null;
  } catch {
    return null;
  }
}

export function searchAltitude(name, observer, direction, start, days, alt) {
  try {
    const t = A.SearchAltitude(name, observer, direction, start, days, alt);
    return t ? t.date : null;
  } catch {
    return null;
  }
}

const POINTS = ["north", "north-northeast", "northeast", "east-northeast", "east", "east-southeast", "southeast",
  "south-southeast", "south", "south-southwest", "southwest", "west-southwest", "west", "west-northwest",
  "northwest", "north-northwest"];

export function compassWord(az) {
  return POINTS[Math.round(((az % 360) + 360) % 360 / 22.5) % 16];
}

// Star color from the B-V index: Ballesteros' temperature, then a blackbody fit, softened toward white the way a
// dark-adapted eye sees it.
export function bvToRgb(bv) {
  const b = Math.max(-0.4, Math.min(2.0, bv));
  const t = 4600 * (1 / (0.92 * b + 1.7) + 1 / (0.92 * b + 0.62));
  const k = t / 100;
  let r, g, bl;
  if (k <= 66) {
    r = 255;
    g = 99.4708025861 * Math.log(k) - 161.1195681661;
    bl = k <= 19 ? 0 : 138.5177312231 * Math.log(k - 10) - 305.0447927307;
  } else {
    r = 329.698727446 * Math.pow(k - 60, -0.1332047592);
    g = 288.1221695283 * Math.pow(k - 60, -0.0755148492);
    bl = 255;
  }
  const c = (x) => Math.max(0, Math.min(255, x)) / 255;
  const rgb = [c(r), c(g), c(bl)];
  const soft = 0.22;
  return rgb.map((x) => x * (1 - soft) + soft);
}
