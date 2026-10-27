// Quick Draw: boots the street, then runs the title, the series, and the poster between rounds. While the title
// sits untouched, the town stages a demo duel of its own.
import * as THREE from "three";
import WebGL from "three/addons/capabilities/WebGL.js";
import { readTokens } from "../scene/tokens.js";
import { pickTier, FrameGovernor } from "../scene/quality.js";
import { createWorld } from "../scene/world.js";
import { easeOut } from "../scene/camera.js";
import { createLoop } from "./loop.js";
import { createInput } from "./input.js";
import { createHud } from "./hud.js";
import { Series } from "./state.js";
import { Round } from "./duel.js";
import { store } from "./store.js";
import { createSound } from "../audio/sound.js";
import { mulberry32 } from "./rng.js";

const DEFAULTS = { title: "Quick Draw", players: ["Rhett", "Cole"], townName: "Dry Gulch", theme: "sunset", bestOf: 5 };
const FIRST_DEMO_MS = 3200;
const NEXT_DEMO_MS = 12000;

function readConfig() {
  const raw = window.__APP_CONFIG__ || {};
  const cfg = { ...DEFAULTS };
  if (typeof raw.title === "string" && raw.title.trim()) cfg.title = raw.title.trim();
  if (typeof raw.townName === "string" && raw.townName.trim()) cfg.townName = raw.townName.trim();
  if (Array.isArray(raw.players)) {
    cfg.players = [0, 1].map((i) => (typeof raw.players[i] === "string" && raw.players[i].trim() ? raw.players[i].trim().slice(0, 14) : DEFAULTS.players[i]));
  }
  if (["sunset", "noon", "midnight"].includes(raw.theme)) cfg.theme = raw.theme;
  if ([3, 5, 7].includes(raw.bestOf)) cfg.bestOf = raw.bestOf;
  return cfg;
}

async function boot() {
  const cfg = readConfig();
  const isTouch = matchMedia("(pointer: coarse)").matches;
  const reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
  let reduced = reducedQuery.matches;
  reducedQuery.addEventListener?.("change", (e) => (reduced = e.matches));
  const hud = createHud({ config: cfg, isTouch });

  if (!WebGL.isWebGL2Available()) {
    document.body.classList.add("is-flat");
    hud.ready();
    return;
  }

  const tier = pickTier();
  const tokens = readTokens();
  const canvas = document.getElementById("scene");
  const world = await createWorld({ canvas, tier, tokens, config: cfg });
  const sound = createSound({ muted: store.muted() });
  const rig = world.rig;
  if (new URLSearchParams(location.search).has("inspect")) window.__quickDraw = { world, get screen() { return screen; } };
  const portraitCanvas = document.createElement("canvas");
  const rnd = mulberry32(Date.now() >>> 0);

  let screen = "title";
  let mode = "duel";
  let bestOf = cfg.bestOf;
  let series = null;
  let round = null;
  let demo = false;
  let lastInput = performance.now();
  let demoAt = Infinity;
  let pendingReload = false;
  let afterFrame = null;

  hud.setMode(mode);
  hud.setBestOf(bestOf);

  // the camera's resting shots
  const drift = () => {
    const f = rig.frame;
    if (reduced) return f.wide;
    const t = performance.now() / 1000;
    return {
      pos: f.wide.pos.clone().add(new THREE.Vector3(Math.sin(t * 0.13) * 0.28, Math.sin(t * 0.21) * 0.05, Math.sin(t * 0.09) * 0.35)),
      target: f.wide.target.clone().add(new THREE.Vector3(Math.sin(t * 0.11) * 0.6, 0, 0)),
      fov: f.wide.fov,
      shift: f.wide.shift,
    };
  };

  function soloLine() {
    const best = store.best();
    hud.setStranger(best ? `Draws at 400 ms, then quicker. Your best: ${best} ms` : "Draws at 400 ms, 20 ms quicker each round");
  }
  soloLine();

  function resetFigures() {
    world.effects.reset();
    for (const f of world.figures) {
      f.restoreHat();
      f.reset();
    }
  }

  function toTitle() {
    if (pendingReload) {
      location.reload();
      return;
    }
    screen = "title";
    demo = false;
    round = null;
    series = null;
    loop.timeScale(1);
    world.setDepthOfField(false);
    resetFigures();
    hud.closePoster();
    hud.title();
    hud.setMode(mode);
    rig.to(drift, 1.4);
    demoAt = performance.now() + NEXT_DEMO_MS;
  }

  function startSeries(isDemo = false) {
    demo = isDemo;
    screen = "duel";
    const names = isDemo ? cfg.players.slice() : hud.names();
    if (!isDemo && mode === "solo") names[1] = "The Stranger";
    series = new Series({ mode: isDemo ? "duel" : mode, bestOf: isDemo ? 3 : bestOf, names, seed: (Date.now() ^ 0x5eed) >>> 0 });
    hud.closePoster();
    hud.duel(series, isDemo);
    if (!isDemo && isTouch && document.fullscreenEnabled && !document.fullscreenElement) {
      document.documentElement.requestFullscreen?.({ navigationUI: "hide" }).then(() => window.screen.orientation?.lock?.("landscape").catch(() => {})).catch(() => {});
    }
    nextRound();
  }

  function nextRound() {
    screen = "duel";
    hud.closePoster();
    hud.duel(series, demo);
    const plan = series.next();
    if (demo) plan.waitMs = 1500;
    hud.tally(series);
    const ai = demo
      ? [Math.round(185 + rnd() * 70), Math.round(200 + rnd() * 80)]
      : mode === "solo"
        ? [null, plan.computerMs]
        : [null, null];
    world.effects.reset();
    round = new Round({ world, hud, sound, loop, reduced, series, plan, ai, onDone: roundDone });
    round.start();
  }

  function posterCopy(result) {
    const w = result.winner;
    const l = 1 - w;
    const names = series.names;
    const solo = series.mode === "solo";
    const you = (side) => solo && side === 0;
    const early = result.early !== null;
    const lateMs = result.times[l];
    let note;
    if (early) note = you(l) ? "You jumped the gun." : `${names[l]} jumped the gun.`;
    else if (lateMs !== null) note = you(l) ? `You drew in ${lateMs} ms.` : `${names[l]} drew in ${lateMs} ms.`;
    else note = you(l) ? "You never cleared leather." : `${names[l]} never cleared leather.`;
    return {
      kind: "round",
      head: "Wanted",
      forLine: early ? `for keeping a cool head in ${cfg.townName}` : `for the fastest draw in ${cfg.townName}`,
      name: names[w],
      digits: early ? "Forfeit" : String(result.times[w]),
      forfeit: early,
      note,
      stamp: `Round ${series.round}`,
      next: series.over ? "Claim the reward" : "Next round",
      home: false,
    };
  }

  function seriesCopy() {
    const c = series.champion;
    const names = series.names;
    const best = series.best[c];
    const solo = series.mode === "solo";
    let note = `Takes the series ${series.wins[c]} to ${series.wins[1 - c]}.`;
    let stamp = `Best of ${series.bestOf}`;
    if (solo) {
      const mine = series.best[0];
      const saved = store.best();
      if (mine !== null && (saved === null || mine < saved)) {
        store.setBest(mine);
        stamp = "New best";
        note += ` Your best draw: ${mine} ms.`;
      } else if (mine !== null) note += ` Your best draw: ${mine} ms.`;
      soloLine();
    }
    return {
      kind: "series",
      head: "Reward",
      forLine: `$500 for the fastest gun in ${cfg.townName}`,
      name: names[c],
      digits: best !== null ? String(best) : `${series.wins[c]} to ${series.wins[1 - c]}`,
      unit: best !== null ? "ms" : "",
      forfeit: best === null,
      note,
      stamp,
      next: "Rematch",
      home: true,
    };
  }

  function roundDone(result) {
    series.record(result);
    hud.tally(series);
    screen = "card";
    const copy = posterCopy(result);
    // the photograph is taken in the same frame, just before the street is drawn again
    afterFrame = () => {
      copy.portrait = world.portrait(result.winner, portraitCanvas);
      hud.poster(copy);
      sound.play("stamp", { gain: 0.7, delay: 0.32 });
    };
    rig.to(drift, 1.8);
    if (demo) {
      const s = series;
      setTimeout(() => {
        if (demo && series === s) toTitle();
      }, 4200);
    }
  }

  function go() {
    if (screen === "title") startSeries(false);
    else if (screen === "card" && demo) toTitle();
    else if (screen === "card" && series) {
      if (document.getElementById("poster").dataset.kind === "series") startSeries(false);
      else if (series.over) {
        const copy = seriesCopy();
        afterFrame = () => {
          copy.portrait = world.portrait(series.champion, portraitCanvas);
          hud.poster(copy);
          sound.play("stamp", { gain: 0.8, delay: 0.32 });
        };
      } else nextRound();
    }
  }

  function back() {
    if (screen !== "title") toTitle();
  }

  // input
  createInput({
    stage: document.getElementById("stage"),
    onShot(side, stamp) {
      if (demo) {
        toTitle();
        return;
      }
      if (screen === "duel" && round) round.press(side, stamp);
    },
    onGo: (event) => {
      if (demo && screen !== "title") {
        toTitle();
        return;
      }
      if (event?.target instanceof HTMLInputElement) event.target.blur();
      go();
    },
    onBack: back,
    onAny() {
      lastInput = performance.now();
      demoAt = Math.max(demoAt, lastInput + NEXT_DEMO_MS);
      sound.unlock();
    },
  });
  document.addEventListener("pointerdown", (event) => {
    if (demo && !(event.target instanceof HTMLButtonElement)) toTitle();
  });

  document.getElementById("go").addEventListener("click", () => {
    sound.unlock();
    if (screen === "title") startSeries(false);
  });
  document.getElementById("next").addEventListener("click", () => {
    sound.unlock();
    go();
  });
  document.getElementById("home").addEventListener("click", () => toTitle());
  document.querySelectorAll("#mode button").forEach((b) =>
    b.addEventListener("click", () => {
      mode = b.dataset.mode;
      hud.setMode(mode);
    }),
  );
  document.querySelectorAll("#best-of button").forEach((b) =>
    b.addEventListener("click", () => {
      bestOf = Number(b.dataset.best);
      hud.setBestOf(bestOf);
    }),
  );
  const soundButton = document.getElementById("sound");
  soundButton.setAttribute("aria-pressed", String(!sound.muted));
  soundButton.addEventListener("click", () => {
    sound.unlock();
    sound.setMuted(!sound.muted);
    store.setMuted(sound.muted);
    soundButton.setAttribute("aria-pressed", String(!sound.muted));
  });
  const fsButton = document.getElementById("fullscreen");
  if (isTouch && document.fullscreenEnabled) {
    fsButton.hidden = false;
    fsButton.addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen?.();
      else document.documentElement.requestFullscreen?.({ navigationUI: "hide" }).catch(() => {});
    });
  }

  world.onEvent((name, n) => {
    if (name === "hat-land") sound.play("hat", { gain: Math.max(0.25, 0.8 / n), rate: 1 + n * 0.06 });
  });

  // screen shape and color scheme
  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      world.resize();
      if (screen === "title") rig.to(drift, 0);
    }, 60);
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (screen === "title") location.reload();
    else pendingReload = true;
  });

  // the loop
  const governor = new FrameGovernor((step) => world.degrade(step));
  const loop = createLoop({
    step() {
      if (round) round.step();
      if (screen === "title" && !demo && performance.now() > demoAt) {
        demoAt = Infinity;
        startSeries(true);
      }
    },
    frame(real, now, gameTime, realTime, gameDt) {
      world.update(gameDt, real, gameTime, realTime);
      if (afterFrame) {
        const fn = afterFrame;
        afterFrame = null;
        fn();
      }
      world.render();
      governor.sample(real * 1000);
    },
  });

  // the opening: a crane down into the street, then the title
  const f = rig.frame;
  const opening = {
    pos: f.wide.pos.clone().add(new THREE.Vector3(0, 2.6, 5)),
    target: f.wide.target.clone().add(new THREE.Vector3(0, 9, 0)),
    fov: f.wide.fov + 4,
    shift: f.wide.shift,
  };
  rig.to(opening, 0);
  rig.update(0);
  if (reduced) rig.to(drift, 0);
  else rig.to(drift, 1.2, easeOut);
  loop.start();
  requestAnimationFrame(() => {
    hud.ready();
    hud.title();
    demoAt = performance.now() + FIRST_DEMO_MS;
  });
}

boot();
