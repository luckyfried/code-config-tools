// Fish Tank: boots the tank, keeps the day turning, feeds the fish, gathers their pearls, and keeps the save.
import * as THREE from "three";
import { createWorld } from "./scene/world.js";
import { shared } from "./scene/shading.js";
import { readPalette, phaseAt, labelFor, moodAt, createMood } from "./scene/daycycle.js";
import { createFloor } from "./scene/floor.js";
import { createWater } from "./scene/water.js";
import { createPlants } from "./scene/plants.js";
import { createDecor } from "./scene/decor.js";
import { createSchool } from "./scene/school.js";
import { createBubbles } from "./scene/bubbles.js";
import { createItems } from "./scene/items.js";
import { createShowcase } from "./scene/showcase.js";
import { createFlat } from "./render/canvas2d.js";
import { createHud } from "./ui/hud.js";
import { createShop } from "./ui/shop.js";
import { createSettings } from "./ui/settings.js";
import { createAudio } from "./audio.js";
import { eat, isFull, isFed, pearlInterval, creditAway, buy, capacity, PHONE_FISH } from "./sim/economy.js";
import { readSave, writeSave, reconcile, anchorFor } from "./game/state.js";

const DEFAULTS = { title: "Fish Tank", theme: "reef", startingFish: null, cycleMinutes: 60, pearlRate: "normal", sound: true };
const AWAY_MIN_MS = 2 * 60 * 1000;
const IDLE_MS = 5 * 60 * 1000;
const SWEEP_AGE = 5;
const fmt = new Intl.NumberFormat("en-US");

const media = (q) => window.matchMedia(q);
const reducedMotion = media("(prefers-reduced-motion: reduce)").matches;
const phone = media("(pointer: coarse)").matches || window.innerWidth < 768;
const quality = {
  phone,
  dpr: Math.min(window.devicePixelRatio || 1, phone ? 1.5 : 2),
  post: !phone,
  maxFish: phone ? PHONE_FISH : 60,
};

async function boot() {
  const catalog = await (await fetch("./sim/catalog.json")).json();
  const config = { ...DEFAULTS, ...(window.__APP_CONFIG__ || {}) };
  if (!config.startingFish) config.startingFish = catalog.themes[config.theme].starting;
  document.title = config.title;
  document.getElementById("title").textContent = config.title;

  const now0 = Date.now();
  const prefersDark = media("(prefers-color-scheme: dark)").matches;
  let save = reconcile(readSave(), config, catalog, now0, prefersDark);
  const firstVisit = save.firstVisit;
  save.firstVisit = false;
  const speciesById = Object.fromEntries(catalog.species.map((s) => [s.id, s]));

  applyLook(save.look);
  const hud = createHud({ reducedMotion });
  const audio = createAudio();
  audio.setOn(save.sound);

  // pearls earned while the page was closed land in the save at once; the card shows them
  let awayCredit = null;
  if (!firstVisit && now0 - (save.lastSeen || now0) >= AWAY_MIN_MS) awayCredit = credit(now0 - save.lastSeen);
  hud.setPearls(awayCredit ? save.pearls - awayCredit.pearls : save.pearls);
  save.lastSeen = now0;

  function credit(elapsed) {
    const r = creditAway(save.fish, speciesById, config.pearlRate, catalog.rates, elapsed);
    save.fish = r.fish;
    save.pearls += r.pearls;
    return r.pearls > 0 ? r : null;
  }

  let saveTimer = 0;
  function persist(soon) {
    clearTimeout(saveTimer);
    const write = () => { save.lastSeen = Date.now(); writeSave(save); };
    if (soon) saveTimer = setTimeout(write, 250);
    else write();
  }
  persist();
  setInterval(() => persist(), 60000);
  window.addEventListener("pagehide", () => persist());

  const canvas = document.getElementById("tank");
  let world = null;
  try {
    world = createWorld(canvas, quality);
  } catch {
    world = null;
  }
  if (!world) return bootFlat(canvas, catalog, save, hud, persist);

  const pal = readPalette();
  const mood = createMood();
  const floor = createFloor(pal);
  const water = createWater(quality);
  const plants = createPlants(config.theme, pal, quality);
  const decor = createDecor(catalog, config.theme, pal);
  const school = createSchool(catalog, quality);
  const bubbles = createBubbles(quality);
  const items = createItems(pal, quality);
  world.scene.add(floor.group, water.group, plants.group, decor.group, school.group, bubbles.mesh, items.group);
  const showcase = createShowcase(document.getElementById("showcase"), catalog, Math.min(window.devicePixelRatio || 1, 2));

  let fishById = new Map();
  function indexFish() {
    fishById = new Map(save.fish.map((f) => [f.id, f]));
  }
  indexFish();

  function layout() {
    world.resize(window.innerWidth, window.innerHeight);
    floor.layout(world.frame);
    water.layout(world.frame, quality);
    plants.layout(world.frame);
    decor.layout(world.frame, save.decor);
    school.setBounds(world.bounds);
    bubbles.setSources(decor.sources, world.frame);
    shared.uSurfaceY.value = world.frame.surfaceY;
  }
  layout();
  school.sync(save.fish, { entering: false });
  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(layout, 120);
  });

  // ---- food and pearls -------------------------------------------------------------------------------------------
  const v = new THREE.Vector3();
  const ray = new THREE.Raycaster();
  const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  let fedOnce = false;

  function feedAt(x, fromY, n = 6) {
    const b = world.bounds;
    const fx = THREE.MathUtils.clamp(x, b.x0 + 0.4, b.x1 - 0.4);
    const y = Math.min(fromY, world.frame.surfaceY - 0.25);
    items.dropFood(fx, y, (b.z0 + b.z1) / 2 + 0.4, n);
    bubbles.burst(fx, y - 0.2, 0.4, 6, clock);
    audio.plop();
  }

  function feedRandom() {
    const b = world.bounds;
    feedAt(b.x0 + (b.x1 - b.x0) * (0.3 + Math.random() * 0.4), world.frame.surfaceY);
  }

  function userFed() {
    if (!fedOnce) {
      fedOnce = true;
      hud.hideHint();
    }
  }

  function toScreen(p) {
    v.copy(p).project(world.camera);
    return [(v.x + 1) / 2 * window.innerWidth, (1 - v.y) / 2 * window.innerHeight];
  }

  function gather(i) {
    items.positionOf(i, v);
    const [sx, sy] = toScreen(v);
    const value = items.take(i);
    save.pearls += value;
    persist(true);
    audio.chime(false);
    hud.fly(sx, sy, () => hud.setPearls(save.pearls, true));
  }

  function gatherAll() {
    const list = items.resting();
    list.forEach((i, n) => setTimeout(() => { if (items.pearlState[i] === 2) gather(i); }, n * 70));
    return list.length;
  }

  function pearlNear(px, py) {
    let best = -1, bestD = (phone ? 44 : 30) ** 2;
    for (let i = 0; i < items.pearlState.length; i++) {
      if (!items.pearlState[i]) continue;
      items.positionOf(i, v);
      const [sx, sy] = toScreen(v);
      const d = (sx - px) ** 2 + (sy - py) ** 2;
      if (d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  // a meal: the fish grows a little, turns down food for a while, and drops a pearl soon after
  function onEat(id, attract) {
    const f = fishById.get(id);
    if (!f) return;
    const now = Date.now();
    if (isFull(f, now)) return;
    Object.assign(f, eat(f, now, Math.random()));
    if (attract) f.pin = Math.min(f.pin, 0.4 + Math.random() * 1.6);
    school.regrow([f]);
    persist(true);
  }

  // ---- input ------------------------------------------------------------------------------------------------------
  let lastInput = performance.now();
  let down = null;
  canvas.addEventListener("pointerdown", (ev) => {
    audio.unlock();
    lastInput = performance.now();
    down = { x: ev.clientX, y: ev.clientY, t: performance.now() };
  });
  canvas.addEventListener("pointerup", (ev) => {
    if (!down) return;
    const moved = Math.hypot(ev.clientX - down.x, ev.clientY - down.y);
    down = null;
    if (moved > 14) return;
    const hit = pearlNear(ev.clientX, ev.clientY);
    if (hit >= 0 && items.pearlState[hit] === 2) {
      gather(hit);
      return;
    }
    const ndc = new THREE.Vector2(ev.clientX / window.innerWidth * 2 - 1, -(ev.clientY / window.innerHeight) * 2 + 1);
    ray.setFromCamera(ndc, world.camera);
    if (ray.ray.intersectPlane(plane, v)) {
      feedAt(v.x, Math.max(v.y + 1.2, world.bounds.y1));
      userFed();
    }
  });

  const shop = createShop({
    catalog, theme: config.theme, phone,
    getState: () => save,
    onBuy: (item) => {
      let nid = save.nextId;
      const r = buy(save, catalog, item, phone, Date.now(), () => nid++);
      if (r.state === save) return false;
      save = r.state;
      save.nextId = nid;
      hud.setPearls(save.pearls, true);
      if (item.type === "decor") {
        decor.layout(world.frame, save.decor);
        bubbles.setSources(decor.sources, world.frame);
        hud.toast(`${item.name} is in the tank.`);
      } else if (item.type === "tank") {
        hud.toast(`Your tank holds ${capacity(catalog, save.tank, phone)} fish now.`);
      } else {
        indexFish();
        school.sync(save.fish, { entering: true });
        hud.toast(r.added.length > 1 ? `${r.added.length} ${item.name.toLowerCase()} are swimming in.` : `A ${item.name.toLowerCase()} is swimming in.`);
      }
      audio.chime(true);
      persist();
      return true;
    },
    onOpen: () => { audio.unlock(); hud.hideHint(); settings.hide(); },
    onClose: () => showcase.clear(),
  });

  function applyCycle(minutes) {
    // keep the hour where it is while the day gets longer or shorter
    const phase = phaseAt(Date.now(), save.anchor, save.cycleMinutes);
    save.cycleMinutes = minutes;
    save.anchor = Date.now() - phase * minutes * 60000;
    persist();
  }

  const settings = createSettings({
    getState: () => save,
    onLook: (look) => { save.look = look; applyLook(look); persist(); },
    onCycle: applyCycle,
    onSound: (on) => { save.sound = on; audio.setOn(on); if (on) audio.unlock(); persist(); },
    onOpen: () => { audio.unlock(); shop.hide(); },
    onClose: () => {},
    tankNote: () => {
      const tank = catalog.tanks.find((t) => t.id === save.tank);
      const cap = capacity(catalog, save.tank, phone);
      return `${tank.name}, ${save.fish.length} of ${cap} fish. Your tank is saved in this browser.`;
    },
  });

  document.getElementById("feedBtn").addEventListener("click", () => {
    audio.unlock();
    lastInput = performance.now();
    feedRandom();
    userFed();
  });

  window.addEventListener("keydown", (ev) => {
    lastInput = performance.now();
    if (ev.target.closest && ev.target.closest("input, select, textarea")) return;
    if (ev.key === "Escape") {
      shop.hide();
      settings.hide();
      hideAway();
      return;
    }
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    const k = ev.key.toLowerCase();
    if (k === "f") { audio.unlock(); feedRandom(); userFed(); }
    else if (k === "s") { audio.unlock(); shop.toggle(); }
    else if (ev.key === " " && !ev.target.closest("button")) {
      ev.preventDefault();
      audio.unlock();
      if (!gatherAll()) hud.toast("No pearls on the sand right now.");
    }
  });

  // ---- the away card ---------------------------------------------------------------------------------------------
  const away = document.getElementById("away");
  function showAway(r) {
    const hours = r.hours >= 1 ? `${fmt.format(Math.round(r.hours * 10) / 10)} hours` : `${Math.max(2, Math.round(r.hours * 60))} minutes`;
    document.getElementById("awayText").textContent = r.capped
      ? `Your fish kept earning for the last 48 hours. They made ${fmt.format(r.pearls)} pearls.`
      : `Your fish made ${fmt.format(r.pearls)} pearls in ${hours}.`;
    document.getElementById("awayAmount").textContent = `+${fmt.format(r.pearls)}`;
    away.classList.add("is-open");
    away.removeAttribute("inert");
    away.setAttribute("aria-hidden", "false");
    setTimeout(() => document.getElementById("awayOk").focus({ preventScroll: true }), 80);
  }
  function hideAway() {
    if (!away.classList.contains("is-open")) return;
    away.classList.remove("is-open");
    away.setAttribute("inert", "");
    away.setAttribute("aria-hidden", "true");
    const r = document.getElementById("awayOk").getBoundingClientRect();
    for (let k = 0; k < 7; k++) setTimeout(() => hud.fly(r.left + r.width / 2, r.top, () => {}), k * 60);
    setTimeout(() => hud.setPearls(save.pearls, true), 500);
  }
  document.getElementById("awayOk").addEventListener("click", () => { audio.unlock(); hideAway(); });
  if (awayCredit) setTimeout(() => showAway(awayCredit), 700);

  let hiddenAt = 0;
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      hiddenAt = Date.now();
      persist();
      return;
    }
    const gone = Date.now() - hiddenAt;
    if (hiddenAt && gone >= AWAY_MIN_MS) {
      const r = credit(gone);
      persist();
      if (r) showAway(r);
    }
    last = performance.now();
  });

  // ---- the first visit -------------------------------------------------------------------------------------------
  // a first visit opens mid-meal: food drifts down into the school, and a few pearls already glint on the sand
  let attractUntil = 0;
  if (firstVisit) {
    const b = world.bounds;
    for (let k = 0; k < 4; k++) {
      const x = b.x0 + (b.x1 - b.x0) * (0.18 + k * 0.2 + Math.random() * 0.08);
      const z = -0.9 + Math.random() * 0.9;
      const i = items.dropPearl(x, 0, z, 1);
      if (i >= 0) items.update(0.001, 0, []);
    }
    setTimeout(() => {
      const bb = world.bounds;
      feedAt(bb.x0 + (bb.x1 - bb.x0) * 0.42, bb.y0 + (bb.y1 - bb.y0) * 0.8, 9);
      attractUntil = performance.now() + 8000;
    }, 250);
  } else {
    hud.hideHint();
  }

  // ---- the loop ---------------------------------------------------------------------------------------------------
  let clock = 0;
  let last = performance.now();
  let pending = 0;
  let dayTick = 0;
  const eaten = [];
  const landed = [];
  const camOffset = new THREE.Vector3();
  const lookAt = new THREE.Vector3();
  const hungryOf = (id) => {
    const f = fishById.get(id);
    return !!f && !isFull(f, Date.now());
  };

  function frame(ts) {
    requestAnimationFrame(frame);
    const raw = Math.min(0.1, (ts - last) / 1000);
    last = ts;
    // after five quiet minutes the tank settles to thirty frames a second
    if (ts - lastInput > IDLE_MS && !shop.isOpen()) {
      pending += raw;
      if (pending < 1 / 31) return;
    } else pending = raw;
    const dt = Math.min(0.05, pending);
    pending = 0;
    clock += dt;
    const nowMs = Date.now();

    const phase = phaseAt(nowMs, save.anchor, save.cycleMinutes);
    moodAt(phase, pal, mood);
    shared.uTime.value = clock;
    if (!reducedMotion) shared.uCausticTime.value = clock * 0.9;
    shared.uCaustic.value = mood.caustic;
    shared.uCausticColor.value.copy(mood.key);
    shared.uNight.value = 1 - mood.day;

    const { scene, lights } = world;
    scene.background.copy(mood.deep);
    scene.fog.color.copy(mood.water).lerp(mood.deep, 0.35);
    scene.fog.density = 0.03 + 0.02 * (1 - mood.day);
    lights.hemi.color.copy(mood.key).lerp(mood.water, 0.4);
    lights.hemi.groundColor.copy(pal.sand).multiplyScalar(0.35 + 0.3 * mood.day);
    lights.hemi.intensity = mood.ambient * 1.15;
    scene.environmentIntensity = 0.1 + 0.6 * mood.day;
    lights.key.color.copy(mood.key);
    lights.key.intensity = mood.keyIntensity * 0.85;
    lights.lamp.color.copy(pal.lamp);
    lights.lamp.intensity = mood.lamp * 22;
    if (world.bloom) {
      // daylight sand is bright enough to haze over, so the glow only opens up as the light goes down
      world.bloom.threshold = 0.8 + 1.4 * mood.day;
      world.bloom.strength = 0.12 + 0.5 * (1 - mood.day) + 0.15 * mood.lamp;
    }
    audio.lamp(mood.lamp);

    if (!reducedMotion) {
      const f = world.frame;
      camOffset.set(Math.sin(clock * 0.071) * 0.45, Math.sin(clock * 0.053 + 1) * 0.16, Math.sin(clock * 0.041) * 0.25);
      world.camera.position.copy(f.base).add(camOffset);
      lookAt.copy(f.target).addScaledVector(camOffset, 0.35);
      world.camera.lookAt(lookAt);
    }

    water.update(mood, pal, clock, !reducedMotion);
    bubbles.update(mood, pal);

    eaten.length = 0;
    school.update(dt, clock, mood, items.food, hungryOf, eaten);
    const attract = performance.now() < attractUntil;
    for (let k = 0; k < eaten.length; k += 2) onEat(eaten[k], attract);

    // each fish on screen drops a pearl when its timer runs out
    for (const id of school.ids()) {
      const f = fishById.get(id);
      if (!f) continue;
      f.pin -= dt;
      if (f.pin > 0) continue;
      const spec = speciesById[f.sp];
      f.pin = pearlInterval(spec, config.pearlRate, catalog.rates, isFed(f, nowMs)) * (0.75 + Math.random() * 0.5);
      if (school.positionOf(id, v)) items.dropPearl(v.x, v.y - school.sizeOf(id) * 0.2, v.z, 1);
    }

    landed.length = 0;
    items.update(dt, clock, landed);
    for (const i of landed) {
      audio.chime(true);
      items.positionOf(i, v);
      bubbles.burst(v.x, v.y, v.z, 2, clock);
    }
    for (const i of items.resting(SWEEP_AGE)) gather(i);

    hud.tick(dt);
    dayTick -= dt;
    if (dayTick <= 0) {
      dayTick = 1;
      hud.setDay(labelFor(phase), mood.day < 0.35);
    }

    world.render();
    if (!live) {
      live = true;
      document.body.classList.add("is-live");
    }
    if (shop.isOpen()) showcase.render(shop.views(), shop.clip(), clock, dt);
  }
  let live = false;
  // the water's light is in place before the first frame, so the tank never flashes while it arrives
  world.envReady.then(() => requestAnimationFrame((ts) => { last = ts; frame(ts); }));
}

function applyLook(look) {
  const root = document.documentElement;
  if (look === "light" || look === "dark") root.dataset.theme = look;
  else delete root.dataset.theme;
}

function bootFlat(canvas, catalog, save, hud, persist) {
  const flat = createFlat(canvas, catalog, save.fish);
  const size = () => flat.resize(window.innerWidth, window.innerHeight, Math.min(window.devicePixelRatio || 1, 2));
  size();
  window.addEventListener("resize", size);
  const feed = (x) => {
    flat.feed(x);
    save.pearls += 1;
    hud.setPearls(save.pearls, true);
    hud.hideHint();
    persist(true);
  };
  canvas.addEventListener("pointerup", (ev) => feed(ev.clientX));
  document.getElementById("feedBtn").addEventListener("click", () => feed(window.innerWidth / 2));
  let last = performance.now(), t = 0;
  const loop = (ts) => {
    requestAnimationFrame(loop);
    const dt = Math.min(0.05, (ts - last) / 1000);
    last = ts;
    t += dt;
    flat.frame(dt, t);
    hud.tick(dt);
  };
  requestAnimationFrame(loop);
}

boot();
