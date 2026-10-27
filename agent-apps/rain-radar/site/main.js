// Rain Radar: loads the radar frames, the wind and rain forecast, and the map for the place, then plays the loop.
// With ?demo=1, "sample": true in the setup, or no answer from any live feed, it plays the sample loop instead.
import { pickTier, createGovernor } from "./scene/quality.js";
import { createWorld } from "./scene/world.js";
import { extentAround } from "./data/geo.js";
import { radarIndex, radarFrames, basemap, forecast } from "./data/feeds.js";
import { sampleFrames, sampleForecast } from "./data/sample.js";
import { sampleMap } from "./data/samplemap.js";
import { placeSeries, outlook } from "./data/rain.js";
import { loadState, saveState } from "./game/state.js";
import { createPlayback } from "./game/loop.js";
import * as hud from "./game/hud.js";
import { createScrubber } from "./game/scrubber.js";
import { createSettings } from "./game/settings.js";
import { attachInput } from "./game/input.js";
import { createFlat } from "./game/flat.js";

const $ = (id) => document.getElementById(id);
const config = window.__APP_CONFIG__ || {};
const forceSample = config.sample === true || new URLSearchParams(location.search).get("demo") === "1";
// the sample frames start downloading before the scene is built
let firstSample = forceSample ? sampleFrames() : null;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const darkScheme = matchMedia("(prefers-color-scheme: dark)");
const state = loadState(config);
const tier = pickTier();

let world = null;
let flat = null;
try {
  world = createWorld({ canvas: $("scene"), tier });
} catch {
  $("scene").hidden = true;
  $("flat").hidden = false;
  flat = createFlat($("flat"));
}
const governor = world ? createGovernor(tier, (t) => world.setTier(t)) : () => {};

// what is loaded for the current place
const data = { frames: [], series: [], minutely: null, windNow: null, sample: false, liveMap: false };
let playback = createPlayback(0);
let loading = 0;
// the scene draws nothing until the first map and radar loop are in; its opening move starts with them
let mapIn = false;
let opened = false;

const scrubber = createScrubber({
  onSeek(pos, pause, by) {
    if (pause) setPlaying(false);
    if (by) playback.step(by);
    else playback.seek(pos);
  },
  onToggle: () => setPlaying(!playback.playing),
});

function setPlaying(on) {
  playback.playing = on && data.frames.length > 1;
  $("play").setAttribute("aria-label", playback.playing ? "Pause the loop" : "Play the loop");
}
$("play").addEventListener("click", () => setPlaying(!playback.playing));

function applyLayers() {
  world?.setLayers({ radar: state.layers.includes("radar"), wind: state.layers.includes("wind"), clouds: state.layers.includes("clouds") });
}

function layout() {
  const w = innerWidth;
  const h = innerHeight;
  const dockTop = document.querySelector(".dock").getBoundingClientRect().top;
  const top = document.querySelector(".place").getBoundingClientRect().bottom;
  const bottom = Math.max(0, h - dockTop);
  $("app").style.setProperty("--dock-h", `${Math.round(bottom)}px`);
  world?.resize(w, h, top, bottom);
  flat?.resize(w, h, top, bottom);
}
new ResizeObserver(layout).observe(document.querySelector(".dock"));
addEventListener("resize", layout);

function refreshWords() {
  const now = Date.now();
  hud.showClock(now, data.windNow, state.units);
  if (!data.frames.length && !data.minutely) return;
  hud.showBanner(outlook(data.series, data.minutely ?? [], now), now);
}

function showStrip() {
  hud.showStrip(data.minutely ?? [], state.units);
  if (!data.minutely) $("stripPeak").textContent = "No forecast right now";
}

async function load() {
  const mine = ++loading;
  const ext = extentAround(state.place.lat, state.place.lon, state.zoom);
  const paper = world ? world.tokens.paper === 1 : !darkScheme.matches;
  hud.showPlace(state.place.name);
  hud.showBanner(null);
  hud.showNotice("");

  let frames = [];
  let fc = null;
  let base = null;
  let liveRadar = false;
  let sample = forceSample;
  // the sample frames download while the map is drawn
  const framesWait = sample ? (firstSample ?? sampleFrames()) : null;
  firstSample = null;
  if (!sample) {
    const [idx, f, b] = await Promise.allSettled([radarIndex(), forecast(ext), basemap(ext, paper ? "paper" : "dark", 2048)]);
    if (mine !== loading) return;
    if (idx.status === "fulfilled") {
      frames = await radarFrames(idx.value, ext, 512);
      liveRadar = true;
    }
    if (f.status === "fulfilled") fc = f.value;
    if (b.status === "fulfilled") base = b.value;
    sample = !liveRadar && !fc && !base;
  }
  if (sample) fc = sampleForecast();
  const map = base ? { base } : sampleMap(state.place.name);
  const target = world ?? flat;
  target.setMap(map);
  if (sample) frames = await (framesWait ?? sampleFrames());
  if (mine !== loading) return;

  data.frames = frames;
  data.series = placeSeries(frames);
  data.minutely = fc ? fc.minutely : null;
  data.windNow = fc ? fc.windNow : null;
  data.sample = sample;
  data.liveMap = Boolean(base);

  target.setFrames(frames);
  mapIn = true;
  if (world) {
    world.setWind(fc?.u ?? new Float32Array(49), fc?.v ?? new Float32Array(49));
    world.setWindActive(Boolean(fc));
    world.setClouds(fc?.cloud ?? new Float32Array(49));
    if (fc) world.settleWind(reduced.matches ? 3 : 1);
  }
  opened = true;

  scrubber.setFrames(frames, data.series);
  const nowIndex = scrubber.nowIndex;
  playback = createPlayback(frames.length, {
    speed: state.speed,
    start: reduced.matches ? nowIndex : 0,
    playing: !reduced.matches,
    stepped: reduced.matches,
  });
  setPlaying(!reduced.matches);

  showStrip();
  refreshWords();
  hud.showCredits({ sample, liveRadar, liveForecast: Boolean(fc) && !sample, liveMap: data.liveMap, placeName: state.place.name });
  if (!sample && !liveRadar) hud.showNotice("No radar right now");
  else if (liveRadar && frames.length && frames.every((fr) => !fr.ok)) hud.showNotice("No radar coverage here");
}

createSettings(state, {
  onChange(what) {
    saveState(state);
    if (what === "place" || what === "zoom") {
      if (world) {
        world.rig.target.set(0, 0, 0);
        world.rig.zoom = 1;
        world.rig.update();
      }
      load();
    } else if (what === "layers") applyLayers();
    else if (what === "speed") playback.speed = state.speed;
    else if (what === "units") {
      showStrip();
      refreshWords();
    }
  },
});

if (world) attachInput($("scene"), world.rig, () => {});

darkScheme.addEventListener("change", () => {
  world?.refreshTokens();
  if (data.liveMap || flat) load();
});

let last = performance.now();
document.addEventListener("visibilitychange", () => (last = performance.now()));

function frame(now) {
  const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
  last = now;
  governor(dt * 1000);
  playback.update(dt);
  const view = playback.view();
  scrubber.update(view, playback.playing, playback.speed);
  const animate = !reduced.matches;
  if (!mapIn) {
    requestAnimationFrame(frame);
    return;
  }
  if (world) {
    if (opened && world.rig.intro > 0) {
      world.rig.intro = Math.max(0, world.rig.intro - dt / 1.8);
      world.rig.update();
    }
    world.showFrames(view.a, view.b, view.mix);
    world.render(dt, { animate });
    hud.placePin(world.placeOnScreen(), true);
  } else {
    flat.render(view);
    hud.placePin(flat.placeOnScreen(), true);
  }
  requestAnimationFrame(frame);
}

applyLayers();
layout();
if (world && !reduced.matches) world.rig.intro = 1;
setInterval(refreshWords, 15000);
load();
requestAnimationFrame(frame);
