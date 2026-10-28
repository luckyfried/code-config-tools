// Sky Tonight: boots the catalog and the scene, keeps the clock and the view, and runs the frame.
import * as THREE from "three";
import { loadCatalog, designation, colorWord } from "./catalog.js";
import { createWorld } from "../scene/world.js";
import { buildStarGeometry } from "../scene/stars.js";
import { buildLineGeometry, MAX_CONSTELLATIONS } from "../scene/lines.js";
import { readPalette } from "../scene/palette.js";
import { pickTier, createGovernor } from "../scene/quality.js";
import {
  skyMatrix, viewBasis, apply, project, scaleFor, makeObserver, eqVector, bodies as computeBodies, altAz, compassWord, DEG,
} from "../scene/astro.js";
import { seedFrom } from "../scene/horizon.js";
import { webglAvailable } from "../scene/renderer.js";
import { createHud } from "./hud.js";
import { createLabels, COMPASS_ALT } from "./labels.js";
import { createInput } from "./input.js";
import { createLoop } from "./loop.js";
import { createIntro, HEROES } from "./intro.js";
import { nightOf, lightBands, moonInfo, planetsUp, darkTimeFor } from "./almanac.js";
import { parseLocal, nightStart, validZone, zonedToUtc } from "./time.js";
import { createChart } from "./chart2d.js";

const HOUR = 3600e3;
const DEFAULTS = {
  place: "Flagstaff, Arizona", lat: 35.1983, lon: -111.6513, timezone: "America/Phoenix",
  horizon: "hill", labels: "names", constellations: "lines", theme: "night", when: "now",
};
const cfg = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
let reducedNow = reducedQuery.matches;
reducedQuery.addEventListener("change", (e) => {
  reducedNow = e.matches;
});
const reduced = () => reducedNow;

const smoothstep = (a, b, x) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const easeOutQuint = (t) => 1 - Math.pow(1 - t, 5);
const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const wrap180 = (a) => ((((a + 180) % 360) + 360) % 360) - 180;

const state = {
  place: {
    name: String(cfg.place).split(",")[0].trim() || "Your sky",
    fullName: String(cfg.place),
    lat: Number(cfg.lat),
    lon: Number(cfg.lon),
    timezone: validZone(cfg.timezone) ? cfg.timezone : "UTC",
  },
  settings: { labels: cfg.labels, constellations: cfg.constellations, horizon: cfg.horizon, theme: cfg.theme },
  ms: Date.now(),
  spinning: false,
  glide: null,
  selection: null,
};
let observer = makeObserver(state.place.lat, state.place.lon);

// The view: where the eye looks (yaw is azimuth, pitch altitude) and how wide (degrees across the shorter side).
const view = {
  yaw: 180, pitch: 25, fov: 70,
  flight: null, inertia: null,
  sensor: false, sensorTarget: null, headingOffset: 0,
  clamp() {
    this.pitch = Math.max(-14, Math.min(89.5, this.pitch));
    this.yaw = ((this.yaw % 360) + 360) % 360;
  },
  setFov(f, eased) {
    const next = Math.max(16, Math.min(view.maxFov(), f));
    if (eased && !reduced()) view.flyTo(view.yaw, view.pitch, next, 0.28);
    else view.fov = next;
  },
  maxFov() {
    return innerWidth < innerHeight ? 110 : 120;
  },
  nudge(dyaw, dpitch) {
    const base = view.flight ? view.flight.to : view;
    view.flyTo(base.yaw + dyaw, base.pitch + dpitch, base.fov, 0.32);
  },
  flyTo(yaw, pitch, fov, dur) {
    view.inertia = null;
    if (reduced() || dur <= 0) {
      view.yaw = yaw; view.pitch = pitch; view.fov = fov; view.flight = null; view.clamp();
      return;
    }
    view.flight = { from: { yaw: view.yaw, pitch: view.pitch, fov: view.fov }, to: { yaw, pitch: Math.max(-14, Math.min(89.5, pitch)), fov }, t: 0, dur, ease: dur > 1 ? easeOutQuint : easeOutCubic };
  },
};

const app = document.getElementById("app");
const canvas = document.getElementById("sky");
let W = innerWidth, H = innerHeight;

let insetCache = null;
function safeInsets() {
  if (insetCache) return insetCache;
  const cs = getComputedStyle(document.documentElement);
  const top = parseFloat(cs.getPropertyValue("--chrome-top")) || 0;
  const bottom = parseFloat(cs.getPropertyValue("--chrome-bottom")) || 0;
  insetCache = { top, bottom };
  return insetCache;
}

async function boot() {
  const tz = state.place.timezone;
  const chosen = cfg.when && cfg.when !== "now" ? parseLocal(cfg.when, tz) : null;
  state.ms = chosen ?? darkTimeFor(Date.now(), observer);
  const introBase = state.ms;

  const hud = createHud({
    spin() {
      intro.cancel();
      state.glide = null;
      state.spinning = !state.spinning;
    },
    now() {
      intro.cancel();
      state.spinning = false;
      glideTo(Date.now());
    },
    glide(ms) {
      intro.cancel();
      state.spinning = false;
      glideTo(ms);
    },
    step(delta) {
      intro.cancel();
      state.spinning = false;
      state.glide = null;
      state.ms += delta;
    },
    scrubStart() {
      intro.cancel();
      state.spinning = false;
      state.glide = null;
    },
    scrub(ms) {
      state.ms = ms;
    },
    scrubEnd() {},
    deselect() {
      select(null);
    },
    openSettings() {
      hud.fillSettings(state);
    },
    setting(name, value) {
      state.settings[name] = value;
      applySettings(name);
    },
    dateTime(d, t) {
      const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d || "");
      if (!m) return;
      const [hh, mm] = (t || "21:00").split(":").map((x) => parseInt(x, 10));
      intro.cancel();
      state.spinning = false;
      glideTo(zonedToUtc(+m[1], +m[2], +m[3], hh || 0, mm || 0, state.place.timezone));
    },
    place(name, lat, lon) {
      if (Number.isFinite(lat) && Math.abs(lat) <= 90) state.place.lat = lat;
      if (Number.isFinite(lon) && Math.abs(lon) <= 180) state.place.lon = lon;
      if (name && name.trim()) state.place.name = name.trim().split(",")[0];
      observer = makeObserver(state.place.lat, state.place.lon);
      hud.setPlace(state.place);
      nightKey = null;
      bodiesMs = -Infinity;
      planetsMs = -Infinity;
      if (world) world.setHorizon(state.settings.horizon, seedFrom(`${state.place.fullName}:${state.settings.horizon}`));
    },
    lookAt(name) {
      if (!bodiesNow) return;
      const w = apply(skyM, bodiesNow[name].dir);
      const { alt, az } = altAz(w);
      view.flyTo(view.yaw + wrap180(az - view.yaw), Math.max(alt - 8, 8), Math.min(view.fov, 60), 1.1);
      selectBody(name);
      document.getElementById("tonight").classList.remove("is-open");
    },
    sensor: toggleSensor,
  });
  hud.setPlace(state.place);
  hud.setSensor(false, "DeviceOrientationEvent" in window && matchMedia("(pointer: coarse)").matches);

  const intro = createIntro(reduced());
  let world = null;
  let chart = null;

  const catalog = await loadCatalog();
  const starData = buildStarGeometry(catalog.features);
  const lineData = buildLineGeometry(catalog.lines, catalog.conIndex);
  const centers = lineData.centers;

  const tier = pickTier();
  const palette = readPalette();
  if (webglAvailable()) {
    try {
      world = createWorld({ canvas, tier, tokens: palette, starGeometry: starData.geometry, lineGeometry: lineData.geometry });
    } catch {
      world = null;
    }
  }
  if (!world) {
    canvas.hidden = true;
    const chartCanvas = document.getElementById("chart");
    chartCanvas.hidden = false;
    document.getElementById("fallback-note").hidden = false;
    chart = createChart(chartCanvas, catalog, lineData, palette);
    document.body.classList.add("is-chart");
  }

  const labels = createLabels(document.getElementById("labels"), catalog, lineData, starData);
  labels.measure();
  document.fonts?.ready.then(() => labels.measure());

  function resize() {
    W = innerWidth;
    H = innerHeight;
    insetCache = null;
    if (world) world.resize(W, H);
    if (chart) chart.resize(W, H);
  }
  addEventListener("resize", resize);
  resize();

  if (world) {
    world.setHorizon(state.settings.horizon, seedFrom(`${state.place.fullName}:${state.settings.horizon}`));
    world.setLineStyle(state.settings.constellations);
    const loader = new THREE.TextureLoader();
    if (tier.milkyWay) {
      const decode = typeof createImageBitmap === "function" ? new THREE.ImageBitmapLoader().setOptions({ imageOrientation: "flipY" }) : null;
      const onMilkyWay = (tex) => {
        tex.colorSpace = THREE.NoColorSpace;
        tex.wrapS = THREE.RepeatWrapping;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.anisotropy = 4;
        world.setMilkyWay(tex);
        mwFadeStart = performance.now();
      };
      const url = "./vendor/eso/eso0932a-4096.jpg";
      if (decode) {
        decode.load(url, (bitmap) => {
          const tex = new THREE.Texture(bitmap);
          tex.flipY = false;
          tex.needsUpdate = true;
          onMilkyWay(tex);
        }, undefined, () => loader.load(url, onMilkyWay));
      } else {
        loader.load(url, onMilkyWay);
      }
    }
    loader.load("./vendor/nasa/lroc_color_poles_1k.jpg", (tex) => {
      tex.colorSpace = THREE.NoColorSpace;
      tex.wrapS = THREE.RepeatWrapping;
      world.setMoonMap(tex);
    });
  }
  let mwFadeStart = 0;

  const input = createInput(canvas, view, {
    scale: () => kNow,
    interact() {
      if (intro.active) intro.cancel();
    },
    tap(x, y) {
      pick(x, y);
    },
    escape() {
      select(null);
    },
    reducedMotion: reduced,
  });

  async function toggleSensor() {
    if (view.sensor) {
      input.disableSensor();
      view.sensor = false;
      hud.setSensor(false, true);
      return;
    }
    const ok = await input.enableSensor();
    view.sensor = ok;
    view.headingOffset = 0;
    hud.setSensor(ok, true);
  }

  function glideTo(ms) {
    const dh = Math.abs(ms - state.ms) / HOUR;
    if (dh > 40 || reduced()) {
      state.glide = null;
      state.ms = ms;
      return;
    }
    state.glide = { from: state.ms, to: ms, t: 0, dur: Math.max(0.6, Math.min(3.2, dh * 0.42)) };
  }

  function applySettings(name) {
    if (name === "theme") {
      const link = document.getElementById("theme-link");
      const next = new URL(`./themes/${state.settings.theme}.css`, location.href).href;
      if (link.href !== next) {
        link.addEventListener("load", () => {
          const p = readPalette();
          if (world) world.setTokens(p);
          if (chart) chart.setPalette(p);
          nightKey = null;
          planetsMs = -Infinity;
        }, { once: true });
        link.href = next;
      }
    } else if (name === "constellations" && world) {
      world.setLineStyle(state.settings.constellations);
    } else if (name === "horizon" && world) {
      world.setHorizon(state.settings.horizon, seedFrom(`${state.place.fullName}:${state.settings.horizon}`));
    }
  }

  // Sky state for this frame.
  const skyM = new Float64Array(9);
  const viewM = new Float64Array(9);
  let kNow = 500;
  let bodiesNow = null;
  let bodiesMs = -Infinity;
  let planetsMs = -Infinity;
  let nightKey = null;
  let nightNow = null;
  let rateSmooth = 0;
  const conAlpha = new Float32Array(MAX_CONSTELLATIONS);
  const conProgress = new Float32Array(MAX_CONSTELLATIONS);
  const conDelay = new Float32Array(MAX_CONSTELLATIONS);
  const conDraw = new Float32Array(MAX_CONSTELLATIONS);
  // How strongly each figure's lines glow: the one nearest the middle of the view leads, the rest sit back.
  const conLead = new Float32Array(MAX_CONSTELLATIONS);
  const conGlow = new Float32Array(MAX_CONSTELLATIONS);
  let leadCi = -1;
  const tmp = [0, 0, 0];
  const tmp2 = [0, 0, 0];
  const proj = { x: 0, y: 0, f: 0, visible: false };

  let lightMs = -Infinity;
  function refreshBodies() {
    const reuse = bodiesNow && Math.abs(state.ms - lightMs) < 3 * HOUR;
    bodiesNow = computeBodies(new Date(state.ms), observer, reuse ? bodiesNow : null);
    if (!reuse) lightMs = state.ms;
    bodiesMs = state.ms;
    if (world) world.updateBodies(bodiesNow);
  }

  let nightFrom = 0;
  function refreshNight() {
    if (nightKey && state.ms >= nightFrom && state.ms < nightFrom + 24 * HOUR) return;
    const start = nightStart(state.ms, state.place.timezone);
    nightFrom = start;
    const key = `${start}:${state.place.lat}:${state.place.lon}`;
    if (key === nightKey) return;
    nightKey = key;
    nightNow = nightOf(start, observer);
    hud.setNight(nightNow, lightBands(start, observer));
    planetsMs = -Infinity;
  }

  function refreshTonight() {
    if (Math.abs(state.ms - planetsMs) < 10 * 60e3) return;
    planetsMs = state.ms;
    hud.setPlanets(planetsUp(state.ms, observer), state.ms, !!(world && world.palette && world.palette.starMono > 0.5));
    const cs = getComputedStyle(document.documentElement);
    hud.setMoon(moonInfo(state.ms, observer), nightNow, {
      lit: cs.getPropertyValue("--band-moon").trim() || "#eee",
      dark: cs.getPropertyValue("--color-border").trim() || "#333",
    });
  }

  // Opening framing: the best-known constellation that stands well up, with the Moon beside it when both fit.
  function frameOpening() {
    skyMatrix(new Date(state.ms), observer, skyM);
    refreshBodies();
    const minSide = Math.min(W, H);
    const portrait = W < H;
    const fov = portrait ? 64 : H < 500 ? 78 : 82;
    const tonightEl = document.querySelector(".tonight");
    // A desktop's almanac column covers the sky's left side; the framing measures where it ends.
    const column = W >= 900 && H > 540 && tonightEl ? Math.ceil(tonightEl.getBoundingClientRect().right) : 0;
    const k = scaleFor(fov, minSide);
    let hero = null;
    for (const id of HEROES) {
      const ci = catalog.conIndex.get(id);
      const c = centers[ci];
      if (!c) continue;
      const w = apply(skyM, c.dir, tmp);
      const { alt, az } = altAz(w);
      if (alt > 16 && alt < 62) {
        hero = { ci, alt, az, spread: c.spread / DEG };
        break;
      }
    }
    if (!hero) hero = { ci: -1, alt: 35, az: 180, spread: 10 };
    if (hero.ci >= 0) {
      leadCi = hero.ci;
      conLead.fill(0);
      conLead[hero.ci] = 1;
    }
    const angAt = (px) => (2 * Math.atan(px / (2 * k))) / DEG;
    const halfW = angAt(W / 2);
    const halfH = angAt(H / 2);
    let yaw = hero.az;
    const moon = altAz(apply(skyM, bodiesNow.Moon.dir, tmp2));
    if (moon.alt > 4) {
      const dm = wrap180(moon.az - hero.az);
      const mid = hero.az + dm * 0.42;
      if (Math.abs(wrap180(moon.az - mid)) < halfW * 0.82 && Math.abs(wrap180(hero.az - mid)) + hero.spread * 0.55 < halfW * 0.9) yaw = mid;
    }
    const horizonAt = portrait ? 0.63 : H < 500 ? 0.8 : 0.83;
    let pitch = angAt((horizonAt - 0.5) * H);
    const reach = H < 500 ? 0.45 : 0.62;
    const room = pitch + halfH * reach;
    if (hero.alt > room) pitch = Math.min(hero.alt - halfH * reach, angAt(H / 2) - (H < 500 ? 3 : 6));
    // The compass points stand on the ground below the horizon, clear of the panels docked at the bottom. A phone
    // on its side has no height to spare under its constellation, so there a point steps up beside the panels
    // instead (labels.js).
    const floor = tonightEl && tonightEl.offsetTop > H / 2 ? tonightEl.offsetTop : H;
    if (portrait || H >= 500) pitch = Math.min(pitch, angAt(floor - 24 - H / 2) + COMPASS_ALT);
    if (column) yaw = clearOfColumn(yaw, pitch, k, column, hero);
    view.yaw = yaw;
    view.pitch = pitch;
    view.fov = fov;
    if (!reduced()) {
      view.flyTo(yaw, pitch, fov, 1.7);
      view.flight.from = { yaw: yaw - 14, pitch: pitch - 6, fov: fov * 1.16 };
      view.yaw = yaw - 14;
      view.pitch = pitch - 6;
      view.fov = fov * 1.16;
    }
  }
  // On a desktop the opening sets the hero, the Moon, and the brightest stars near them right of the column: the
  // yaw nearest the composed one that keeps them all clear, adding the bright stars brightest first while one fits.
  function clearOfColumn(yaw, pitch, k, column, hero) {
    const P = {};
    const v = [0, 0, 0];
    const screenX = (w, y) => {
      viewBasis(y, pitch, viewM);
      apply(viewM, w, v);
      project(v, k, P);
      return P.visible ? { x: W / 2 + P.x, y: H / 2 - P.y } : null;
    };
    const must = [];
    const reach = 40 + hero.spread * 0.6 * k * DEG;
    if (hero.ci >= 0) must.push({ w: apply(skyM, centers[hero.ci].dir, [0, 0, 0]), left: reach, right: reach });
    const moonW = apply(skyM, bodiesNow.Moon.dir, [0, 0, 0]);
    if (altAz(moonW).alt > 4) must.push({ w: moonW, left: 40, right: 70 });
    const bright = [];
    for (const s of catalog.stars) {
      if (!(s.mag < 1.1)) continue;
      const w = apply(skyM, eqVector(s.ra, s.dec), [0, 0, 0]);
      const { alt, az } = altAz(w);
      if (alt < 6 || Math.abs(wrap180(az - yaw)) > 75) continue;
      bright.push({ w, mag: s.mag, left: 90, right: 70 });
    }
    bright.sort((a, b) => a.mag - b.mag);
    const offsets = [];
    for (let d = 0; d <= 40; d += 0.5) offsets.push(d, -d);
    const clear = (y, set) => set.every((p) => {
      const s = screenX(p.w, y);
      return s && s.x > column + p.left && s.x < W - p.right && s.y > 0 && s.y < H;
    });
    // A star that already sits off screen at the composed yaw is not pulled into the frame.
    const shown = bright.filter((p) => {
      const s = screenX(p.w, yaw);
      return s && s.x > 0 && s.x < W && s.y > 0 && s.y < H;
    });
    const base = yaw - (2 * Math.atan(column / 2 / (2 * k))) / DEG;
    let set = must;
    let best = offsets.map((d) => base + d).find((y) => clear(y, set));
    if (best === undefined) return base;
    for (const p of shown) {
      const next = [...set, p];
      const y = offsets.map((d) => base + d).find((yy) => clear(yy, next));
      if (y !== undefined) {
        set = next;
        best = y;
      }
    }
    return best;
  }

  // Tonight is filled before the framing measures it.
  refreshNight();
  refreshTonight();
  frameOpening();

  function updateView(dt) {
    if (view.sensor && view.sensorTarget) {
      const a = 1 - Math.exp(-dt * (reduced() ? 30 : 9));
      view.yaw += wrap180(view.sensorTarget.yaw + view.headingOffset - view.yaw) * a;
      view.pitch += (view.sensorTarget.pitch - view.pitch) * a;
      view.clamp();
      return;
    }
    if (view.flight) {
      const f = view.flight;
      f.t = Math.min(1, f.t + dt / f.dur);
      const e = f.ease(f.t);
      view.yaw = f.from.yaw + wrap180(f.to.yaw - f.from.yaw) * e;
      view.pitch = f.from.pitch + (f.to.pitch - f.from.pitch) * e;
      view.fov = f.from.fov + (f.to.fov - f.from.fov) * e;
      view.clamp();
      if (f.t >= 1) view.flight = null;
    } else if (view.inertia) {
      view.yaw += view.inertia.yaw * dt;
      view.pitch += view.inertia.pitch * dt;
      view.clamp();
      const d = Math.exp(-dt * 4.5);
      view.inertia.yaw *= d;
      view.inertia.pitch *= d;
      if (Math.abs(view.inertia.yaw) + Math.abs(view.inertia.pitch) < 0.3) view.inertia = null;
    }
  }

  function updateClock(dt) {
    const before = state.ms;
    if (intro.active) {
      const off = intro.offset(dt);
      state.ms = introBase + off;
    } else if (state.glide) {
      const g = state.glide;
      g.t = Math.min(1, g.t + dt / g.dur);
      state.ms = g.from + (g.to - g.from) * easeInOutCubic(g.t);
      if (g.t >= 1) state.glide = null;
    } else if (state.spinning) {
      state.ms += dt * HOUR;
    }
    const rate = Math.abs(state.ms - before) / HOUR / Math.max(dt, 1e-3);
    rateSmooth += (rate - rateSmooth) * (1 - Math.exp(-dt * (rate > rateSmooth ? 14 : 6)));
  }

  function magLimitFor(sunAlt, moonLight) {
    const pts = [[-18, 6.4], [-12, 4.7], [-6, 2.4], [-2, 0.6], [3, -1.6]];
    let m = pts[0][1];
    if (sunAlt >= pts[pts.length - 1][0]) m = pts[pts.length - 1][1];
    else {
      for (let i = 0; i < pts.length - 1; i += 1) {
        const [a0, m0] = pts[i];
        const [a1, m1] = pts[i + 1];
        if (sunAlt >= a0 && sunAlt <= a1) m = m0 + ((m1 - m0) * (sunAlt - a0)) / (a1 - a0);
      }
    }
    return m - moonLight * 1.2;
  }

  function updateConstellations(dt, halfDiag, inkMode) {
    const consOn = state.settings.constellations !== "none";
    const spin = smoothstep(0.15, 0.9, rateSmooth);
    let nearCi = -1, nearOff = Infinity, leadOff = Infinity;
    for (let ci = 0; ci < MAX_CONSTELLATIONS; ci += 1) {
      const c = centers[ci];
      if (!c) continue;
      const w = apply(skyM, c.dir, tmp);
      apply(viewM, w, tmp2);
      const f = Math.max(-1, Math.min(1, -tmp2[2]));
      const ang = Math.acos(f) / DEG;
      const spread = c.spread / DEG;
      const off = ang - spread * 0.45;
      const inView = 1 - smoothstep(halfDiag * 0.62, halfDiag * 1.05, off);
      const center = 1 - smoothstep(halfDiag * 0.1, halfDiag * 0.72, off);
      const up = smoothstep(-0.06, 0.12, w[1] + Math.sin(c.spread) * 0.5);
      const target = consOn ? inView * up * (0.3 + 0.7 * center) : 0;
      if (up > 0.5 && inView > 0.5 && ang < nearOff) { nearOff = ang; nearCi = ci; }
      if (ci === leadCi) leadOff = up > 0.5 ? ang : Infinity;
      const rate = reduced() ? 30 : target > conAlpha[ci] ? 3.2 : 2.2;
      conAlpha[ci] += (target - conAlpha[ci]) * (1 - Math.exp(-dt * rate));
      if (target > 0.12) {
        if (conProgress[ci] === 0 && conDelay[ci] <= 0) conDelay[ci] = 0.05 + Math.min(1, ang / halfDiag) * 0.5;
        if (conDelay[ci] > 0) {
          conDelay[ci] -= dt;
          if (conDelay[ci] <= 0) conProgress[ci] = 0.0001;
        } else {
          conProgress[ci] = Math.min(1, conProgress[ci] + dt / 1.05);
        }
      } else if (conAlpha[ci] < 0.04) {
        conProgress[ci] = 0;
        conDelay[ci] = 0;
      }
      conDraw[ci] = reduced() ? (target > 0.12 ? 1 : 0) : easeOutCubic(conProgress[ci]);
    }
    // The opening's figure leads first, and keeps the lead while it stays in the middle of the view; once the view
    // turns away, the figure nearest the middle takes over.
    if (nearCi >= 0 && !view.flight && (leadCi < 0 || leadOff > halfDiag * 0.62)) leadCi = nearCi;
    const leadRate = 1 - Math.exp(-dt * (reduced() ? 30 : 2.4));
    for (let ci = 0; ci < MAX_CONSTELLATIONS; ci += 1) {
      conLead[ci] += ((ci === leadCi ? 1 : 0) - conLead[ci]) * leadRate;
      conGlow[ci] = conAlpha[ci] * (0.3 + 0.85 * conLead[ci]) * (inkMode ? 1.3 : 1);
    }
    return 1 - spin * 0.65;
  }

  function pick(x, y) {
    const px = x - W / 2, py = H / 2 - y;
    let best = null;
    const consider = (score, make) => {
      if (!best || score < best.score) best = { score, make };
    };
    const vecs = starData.vectors;
    for (let i = 0; i < catalog.stars.length; i += 1) {
      tmp[0] = vecs[i * 3]; tmp[1] = vecs[i * 3 + 1]; tmp[2] = vecs[i * 3 + 2];
      const w = apply(skyM, tmp, tmp2);
      if (w[1] < 0) continue;
      const v = apply(viewM, w, tmp);
      project(v, kNow, proj);
      if (!proj.visible || proj.f < 0) continue;
      const d = Math.hypot(proj.x - px, proj.y - py);
      if (d > 26) continue;
      const s = catalog.stars[i];
      consider(d - (6.5 - s.mag) * 2.2, () => ({ type: "star", star: s, dir: [vecs[i * 3], vecs[i * 3 + 1], vecs[i * 3 + 2]] }));
    }
    if (bodiesNow) {
      for (const name of ["Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]) {
        const w = apply(skyM, bodiesNow[name].dir, tmp2);
        if (w[1] < -0.01) continue;
        project(apply(viewM, w, tmp), kNow, proj);
        if (!proj.visible) continue;
        const d = Math.hypot(proj.x - px, proj.y - py);
        const reach = name === "Moon" ? moonRadiusPx + 14 : 26;
        if (d < reach) consider(d - 30, () => ({ type: "body", name }));
      }
    }
    for (const s of catalog.sights) {
      const w = apply(skyM, s.dir, tmp2);
      if (w[1] < 0) continue;
      project(apply(viewM, w, tmp), kNow, proj);
      if (!proj.visible) continue;
      const d = Math.hypot(proj.x - px, proj.y - py);
      if (d < 22) consider(d + 4, () => ({ type: "sight", sight: s }));
    }
    if (!best) {
      select(null);
      return;
    }
    select(best.make(), { x, y });
  }

  function whereText(dir) {
    const { alt, az } = altAz(apply(skyM, dir, tmp2));
    return `${Math.round(alt)}° up in the ${compassWord(az)}`;
  }

  function selectBody(name) {
    select({ type: "body", name });
  }

  function select(sel, at) {
    state.selection = sel;
    if (!sel) {
      hud.hideCard();
      return;
    }
    let info;
    if (sel.type === "star") {
      const s = sel.star;
      const con = catalog.constellations[catalog.conIndex.get(s.con)];
      const desig = designation(s, catalog.constellations, catalog.conIndex);
      const facts = [];
      if (s.ly > 0) facts.push(["Distance", `${s.ly >= 100 ? Math.round(s.ly).toLocaleString("en-US") : s.ly} light-years`]);
      facts.push(["Brightness", `magnitude ${s.mag.toFixed(1)}`]);
      facts.push(["Color", `${colorWord(s.bv)}${s.spect ? `, type ${s.spect.replace(/[^A-Za-z0-9]+$/, "")}` : ""}`]);
      facts.push(["Now", whereText(sel.dir)]);
      info = { kind: con ? `Star in ${con.name}` : "Star", name: s.name || desig, desig: s.name ? desig : "", facts };
      sel.world = apply(skyM, sel.dir).slice();
      sel.radius = 10;
    } else if (sel.type === "sight") {
      const s = sel.sight;
      info = { kind: s.kind, name: s.name, desig: "", facts: [["Distance", s.detail], ["Brightness", `magnitude ${s.mag.toFixed(1)}`], ["Now", whereText(s.dir)]] };
      sel.dir = s.dir;
      sel.radius = 16;
    } else {
      const b = bodiesNow[sel.name];
      const km = b.dist * 149597870.7;
      const facts = [];
      if (sel.name === "Moon") {
        const mi = moonInfo(state.ms, observer);
        facts.push(["Phase", `${mi.lit}% lit`]);
        facts.push(["Distance", `${Math.round(km).toLocaleString("en-US")} km`]);
        facts.push(["Now", whereText(b.dir)]);
        info = { kind: "The Moon", name: mi.name, desig: "", facts };
        sel.radius = moonRadiusPx;
      } else {
        const minutes = (b.dist * 499.005) / 60;
        facts.push(["Distance", `${(km / 1e6).toFixed(km < 1e9 ? 0 : 0).replace(/\B(?=(\d{3})+(?!\d))/g, ",")} million km`]);
        facts.push(["Light time", minutes < 90 ? `${Math.round(minutes)} minutes` : `${(minutes / 60).toFixed(1)} hours`]);
        facts.push(["Brightness", `magnitude ${b.mag.toFixed(1)}`]);
        if (sel.name === "Venus" || sel.name === "Mercury") facts.push(["Phase", `${Math.round(b.phase * 100)}% lit`]);
        facts.push(["Now", whereText(b.dir)]);
        info = { kind: "Planet", name: sel.name, desig: "", facts };
        sel.radius = 12;
      }
      sel.dir = b.dir;
    }
    hud.showCard(info, at);
  }

  let moonRadiusPx = 14;
  let frameCount = 0;
  let blocks = [];
  const blockEls = [".place", ".topbar__actions", ".tonight", ".timebar", ".star-card:not([hidden])", ".code-config-toast:not(.away)"];
  // Where each panel rests, without the few pixels its entrance still has to rise.
  function blockRects() {
    const out = [];
    for (const sel of blockEls) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      const lift = parseFloat((getComputedStyle(el).translate || "").split(" ")[1]) || 0;
      if (r.width > 0) out.push([r.left - 6, r.top - lift - 4, r.width + 12, r.height + 8]);
    }
    return out;
  }
  // The place name and the panels hide the sky's points and lines behind them (scene/shaders.js MASK).
  const range = document.createRange();
  function maskRects() {
    const out = [];
    for (const sel of ["#place-name", "#place-when"]) {
      const el = document.querySelector(sel);
      if (!el) continue;
      range.selectNodeContents(el);
      const r = range.getBoundingClientRect();
      if (r.width > 0) out.push([r.left - 10, r.top - 6, r.right + 10, r.bottom + 6, 1]);
    }
    for (const sel of [".tonight", ".timebar"]) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0) out.push([r.left, r.top, r.right, r.bottom, 1]);
    }
    return out;
  }
  const governor = createGovernor(tier, (t) => {
    if (world) world.setTier(t);
  });

  const loop = createLoop({
    update(dt) {
      updateClock(dt);
      updateView(dt);
    },
    onFrameTime(ms) {
      governor.sample(ms);
    },
    render(dt, tSec) {
      const date = new Date(state.ms);
      skyMatrix(date, observer, skyM);
      viewBasis(view.yaw, view.pitch, viewM);
      const minSide = Math.min(W, H);
      kNow = scaleFor(view.fov, minSide);
      if (Math.abs(state.ms - bodiesMs) > (rateSmooth > 0.15 ? 18 : 4) * 60e3) refreshBodies();
      refreshNight();
      if (rateSmooth < 0.2) refreshTonight();

      const sunW = apply(skyM, bodiesNow.Sun.dir, [0, 0, 0]);
      const moonW = apply(skyM, bodiesNow.Moon.dir, [0, 0, 0]);
      const sunAlt = Math.asin(sunW[1]) / DEG;
      const moonUp = smoothstep(-0.02, 0.12, moonW[1]);
      const moonLight = bodiesNow.Moon.phase * moonUp * 0.65;
      const p = world ? world.palette : null;
      const ink = p ? p.inkMode > 0.5 : false;
      const halfDiag = (2 * Math.atan(Math.hypot(W, H) / 2 / (2 * kNow))) / DEG;
      const lineMaster = updateConstellations(dt, halfDiag, ink);
      const zoom = Math.max(0.85, Math.min(2.4, Math.pow(64 / view.fov, 0.55)));
      const rKm = 1737.4 / (bodiesNow.Moon.dist * 149597870.7);
      moonRadiusPx = Math.max(kNow * rKm, (W < H ? 11 : 13) * Math.max(1, Math.pow(64 / view.fov, 0.6)));
      if (state.selection && state.selection.dir) state.selection.world = apply(skyM, state.selection.dir).slice();

      const magLimit = ink ? 6.4 : magLimitFor(sunAlt, moonLight);
      const trail = ink ? 0 : smoothstep(0.12, 0.55, rateSmooth);
      const mw = p ? p.milkyWay * (mwFadeStart ? smoothstep(0, 700, performance.now() - mwFadeStart) : 0) : 0;

      if (world) {
        world.render({
          sky: skyM,
          view: viewM,
          k: kNow,
          sunAlt,
          sunWorld: sunW,
          moonWorld: moonW,
          moonLight,
          glow: state.settings.horizon === "city" ? 1.15 : 0.5,
          milkyWay: mw,
          time: reduced() ? 0 : tSec,
          magLimit,
          magCut: ink ? 6.5 : magLimit + 0.6,
          zoom,
          twinkle: reduced() || !p ? 0 : p.twinkle,
          conAlpha: conGlow,
          conDraw,
          lineMaster,
          planetFade: ink ? 1 : 1 - 0.75 * smoothstep(-3, 8, sunAlt),
          moonRadius: moonRadiusPx,
          moonHalo: 1 - 0.8 * smoothstep(-6, 6, sunAlt),
          trail,
          trailDecay: Math.pow(0.945, dt * 60),
        });
      } else if (chart) {
        chart.draw({ sky: skyM, view: viewM, k: kNow, width: W, height: H, conAlpha, sunAlt, bodies: bodiesNow });
      }

      if (frameCount++ % 20 === 0) {
        blocks = blockRects();
        if (world) world.setMask(maskRects());
      }
      const insets = safeInsets();
      labels.update({
        sky: skyM, view: viewM, k: kNow, width: W, height: H, now: tSec * 1000, settings: state.settings,
        conAlpha, lineMaster: world ? lineMaster : 1, magLimit, zoom, bodies: bodiesNow, moonRadius: moonRadiusPx, fov: view.fov, selection: state.selection,
        safeTop: insets.top, safeBottom: insets.bottom, blocks, spinning: rateSmooth > 0.35,
      });
      hud.setTime(state.ms, state.spinning || rateSmooth > 0.05);
      app.classList.toggle("is-spinning", rateSmooth > 0.3);
    },
  });
  loop.start();
  document.body.classList.add("is-live");
}

boot().catch((err) => {
  document.body.classList.add("is-failed");
  const note = document.getElementById("fallback-note");
  note.hidden = false;
  note.textContent = "The star catalog didn't load. Reload the page to try again.";
  throw err;
});
