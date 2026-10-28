// Tonight at the place: sunset, the end of twilight, the Moon's rise or set and phase, dawn, and the light of the
// whole night as bands for the time ribbon.
import {
  bodyAltitude, compassWord, moonPhaseAngle, moonPhaseName, PLANETS, searchAltitude, searchRiseSet, sunAltitude,
} from "../scene/astro.js";
import * as A from "astronomy-engine";

const DAY = 86400e3;

export function nightOf(startMs, observer) {
  const start = new Date(startMs);
  const sunset = searchRiseSet("Sun", observer, -1, start, 1);
  const dark = searchAltitude("Sun", observer, -1, start, 1, -18);
  const nauticalDark = searchAltitude("Sun", observer, -1, start, 1, -12);
  const from = sunset || start;
  const dawn = searchAltitude("Sun", observer, +1, from, 1, -18);
  const sunrise = searchRiseSet("Sun", observer, +1, from, 1);
  const moonrise = searchRiseSet("Moon", observer, +1, start, 1);
  const moonset = searchRiseSet("Moon", observer, -1, start, 1);
  const end = startMs + DAY;
  const inWindow = (d) => (d && d.getTime() < end ? d : null);
  return {
    start: startMs,
    sunset: inWindow(sunset),
    dark: inWindow(dark),
    nauticalDark: inWindow(nauticalDark),
    dawn: inWindow(dawn),
    sunrise: inWindow(sunrise),
    moonrise: inWindow(moonrise),
    moonset: inWindow(moonset),
  };
}

// The moment the opening view shows for "now" at a place where it is still light: an hour after full dark.
export function darkTimeFor(nowMs, observer) {
  const alt = sunAltitude(new Date(nowMs), observer);
  if (alt < -10) return nowMs;
  const dark = searchAltitude("Sun", observer, -1, new Date(nowMs), 1, -18) || searchAltitude("Sun", observer, -1, new Date(nowMs), 1, -12);
  return dark ? dark.getTime() + 45 * 60e3 : nowMs;
}

// Color stops for the ribbon: the Sun's altitude every 15 minutes across the 24 hours from local noon.
export function lightBands(startMs, observer) {
  const stops = [];
  const moon = [];
  for (let i = 0; i <= 96; i += 1) {
    const t = new Date(startMs + i * 15 * 60e3);
    const a = sunAltitude(t, observer);
    let band;
    if (a > 0) band = "day";
    else if (a > -6) band = "civil";
    else if (a > -12) band = "nautical";
    else if (a > -18) band = "astro";
    else band = "night";
    stops.push(band);
    moon.push(bodyAltitude("Moon", t, observer) > 0);
  }
  const grad = stops.map((b, i) => `var(--band-${b}) ${((i / 96) * 100).toFixed(2)}%`).join(", ");
  const moonGrad = moon.map((up, i) => {
    const p = ((i / 96) * 100).toFixed(2);
    return `${up ? "var(--band-moon)" : "transparent"} ${p}%`;
  }).join(", ");
  return { grad: `linear-gradient(90deg, ${grad})`, moon: `linear-gradient(90deg, ${moonGrad})`, anyMoon: moon.some(Boolean) };
}

export function moonInfo(ms, observer) {
  const date = new Date(ms);
  const ill = A.Illumination("Moon", date);
  return {
    name: moonPhaseName(date),
    angle: moonPhaseAngle(date),
    lit: Math.round(ill.phase_fraction * 100),
    altitude: bodyAltitude("Moon", date, observer),
  };
}

export function planetsUp(ms, observer) {
  const date = new Date(ms);
  const up = [];
  for (const name of PLANETS) {
    if (name === "Neptune") continue;
    const eq = A.Equator(name, date, observer, true, true);
    const hor = A.Horizon(date, observer, eq.ra, eq.dec, "normal");
    if (hor.altitude > 2) {
      const mag = A.Illumination(name, date).mag;
      if (name === "Uranus" && mag > 5.8) continue;
      up.push({ name, alt: hor.altitude, az: hor.azimuth, where: compassWord(hor.azimuth), mag });
    }
  }
  return up.sort((a, b) => a.mag - b.mag);
}
