// Sets the table: reads the config and this device's choices, picks the WebGL table or the
// CSS 3D one, deals (or brings back the saved game, or lets the house play a hand), and
// runs the frame loop: a fixed step for the springs, a draw only when something moved.

import { createSession } from "./game/session.js";
import { step } from "./game/motion.js";
import { createHud, feltRule } from "./game/hud.js";
import { bindInput } from "./input.js";
import { createAudio } from "./audio.js";
import { cardLook, initialsOf } from "./faces.js";
import { readTokens } from "./scene/tokens.js";

const SLUG = "velvet-solitaire";
const KEY_PREFS = `${SLUG}:prefs`;
const THEMES = ["velvet-green", "midnight-blue", "ivory-club"];

const config = Object.assign(
  { title: "Velvet Solitaire", playerName: "", draw: 1, scoring: "standard", theme: "velvet-green", cardBack: "classic", sound: true },
  window.__APP_CONFIG__ || {},
);

function loadPrefs() {
  let saved = {};
  try {
    saved = JSON.parse(localStorage.getItem(KEY_PREFS) || "{}") || {};
  } catch {
    saved = {};
  }
  return {
    draw: Number(saved.draw ?? config.draw) === 3 ? 3 : 1,
    scoring: (saved.scoring ?? config.scoring) === "vegas" ? "vegas" : "standard",
    theme: THEMES.includes(saved.theme) ? saved.theme : config.theme,
    lighting: ["light", "dark"].includes(saved.lighting) ? saved.lighting : "auto",
    sound: saved.sound ?? config.sound !== false,
  };
}
function savePrefs(p) {
  try {
    localStorage.setItem(KEY_PREFS, JSON.stringify(p));
  } catch {
    // Choices still apply for this visit.
  }
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

async function fontsReady() {
  if (!document.fonts) return;
  const wait = Promise.all([
    document.fonts.load('700 40px "Velvet Serif"'),
    document.fonts.load('italic 400 40px "Velvet Serif"'),
    document.fonts.load('400 40px "Velvet Serif"'),
  ]);
  await Promise.race([wait, new Promise((r) => setTimeout(r, 900))]);
}

async function start() {
  const prefs = loadPrefs();
  const reducedQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const reduced = reducedQuery.matches;
  const hud = createHud({ config, prefs, reduced });
  const host = document.getElementById("stage");
  const area = hud.tableArea();
  const compact = hud.isCompact();
  const roughCard = compact ? area.w / 8 : Math.min(140, area.w / 8.6);
  const tier = window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 768 ? "phone" : "desktop";

  const [, backImage] = await Promise.all([
    fontsReady(),
    ["classic", "lattice", "monogram"].includes(config.cardBack) ? Promise.resolve(null) : loadImage(config.cardBack),
  ]);
  const back = {
    style: backImage ? "image" : ["classic", "lattice", "monogram"].includes(config.cardBack) ? config.cardBack : "classic",
    initials: initialsOf(config.playerName) || initialsOf(config.title),
    image: backImage,
  };

  let renderer = null;
  const webgl = await import("./render/webgl.js");
  if (webgl.supportsWebGL()) {
    try {
      renderer = await webgl.createWebGLRenderer({ host, tier, reduced, envUrl: "./vendor/env/studio.hdr", cardCssWidth: roughCard });
    } catch {
      renderer = null;
      host.textContent = "";
    }
  }
  if (!renderer) {
    const css3d = await import("./render/css3d.js");
    renderer = css3d.createCss3dRenderer({ host, reduced, cardCssWidth: roughCard });
    document.documentElement.classList.add("no-webgl");
  }

  const audio = createAudio({ enabled: prefs.sound });
  const session = createSession({ renderer, audio, hud, prefs, reduced, player: config.playerName });

  const paint = () => {
    const tok = readTokens();
    renderer.applyTheme(tok, cardLook(tok.raw), back);
    paintPrint();
  };
  const paintPrint = (info = {}) => {
    const st = session.state;
    const draw = info.draw ?? (st ? st.draw : prefs.draw);
    const scoring = info.scoring ?? (st ? st.scoring : prefs.scoring);
    renderer.paintPrint(readTokens(), { title: config.title, rule: feltRule(draw, scoring), stockState: info.stockState || "ok" });
  };
  hud.paintPrint = paintPrint;

  // ---- Settings and buttons --------------------------------------------------------------
  hud.showPrefs(prefs);
  hud.setRule(prefs.draw, prefs.scoring);
  hud.setStats(session.stats, config.playerName);
  const themeLink = document.getElementById("theme-link");
  const setTheme = (name) => {
    if (!THEMES.includes(name)) return;
    prefs.theme = name;
    savePrefs(prefs);
    const href = name === config.theme ? "./theme.css" : `./themes/${name}.css`;
    if (themeLink.getAttribute("href") === href) return;
    themeLink.addEventListener("load", paint, { once: true });
    themeLink.setAttribute("href", href);
  };
  const setLighting = (v) => {
    prefs.lighting = v;
    savePrefs(prefs);
    if (v === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", v);
    paint();
  };
  hud.on("set:theme", setTheme);
  hud.on("set:lighting", setLighting);
  hud.on("set:draw", (v) => {
    prefs.draw = Number(v) === 3 ? 3 : 1;
    savePrefs(prefs);
    hud.setRule(prefs.draw, prefs.scoring);
    hud.say(`Draw ${prefs.draw === 3 ? "three" : "one"} starts with the next deal.`);
  });
  hud.on("set:scoring", (v) => {
    prefs.scoring = v === "vegas" ? "vegas" : "standard";
    savePrefs(prefs);
    hud.setRule(prefs.draw, prefs.scoring);
    hud.say(`${prefs.scoring === "vegas" ? "Vegas" : "Standard"} scoring starts with the next deal.`);
  });
  hud.on("set:sound", (on) => {
    prefs.sound = !!on;
    audio.enabled = prefs.sound;
    savePrefs(prefs);
    if (on) audio.unlock().then(() => audio.play("snap"));
  });
  hud.on("menu", () => hud.openMenu());
  hud.on("close-menu", () => hud.closeMenu());
  hud.on("new", () => {
    hud.closeMenu();
    if (session.mode === "demo") session.dealIn();
    else if (session.mode === "play" && session.state && session.state.moves > 0) hud.confirmNew();
    else session.newGame();
    afterDeal();
  });
  hud.on("confirm-new", () => {
    hud.closeConfirm();
    session.newGame();
    afterDeal();
  });
  hud.on("keep", () => hud.closeConfirm());
  hud.on("again", () => {
    hud.hideWin();
    session.newGame();
    afterDeal();
  });
  hud.on("deal-in", () => {
    audio.unlock();
    session.dealIn();
    afterDeal();
  });
  hud.on("undo", () => session.undo());
  hud.on("hint", () => {
    hud.closeMenu();
    session.showHint();
  });
  hud.on("finish", () => {
    hud.closeMenu();
    session.autoFinish();
  });
  const afterDeal = () => {
    hud.setStats(session.stats, config.playerName);
    session.updateHud();
  };

  // ---- First frame -----------------------------------------------------------------------
  session.relayout();
  paint();
  if (!session.restore()) {
    if (reduced) session.newGame();
    else session.startDemo();
  }
  session.updateHud();
  bindInput({ surface: host, session, hud, audio });

  let resizeTimer = 0;
  const onResize = () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      session.relayout();
      paintPrint();
    }, 60);
  };
  window.addEventListener("resize", onResize);
  hud.onWideChange(() => {
    hud.closeMenu();
    onResize();
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (prefs.lighting === "auto") paint();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) session.persist();
    last = performance.now();
  });
  window.addEventListener("pagehide", () => session.persist());

  // ---- The loop --------------------------------------------------------------------------
  let last = performance.now();
  let frames = 0;
  let slow = 0;
  const STEP = 1 / 120;
  const loop = (now) => {
    const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
    last = now;
    session.tick(dt);
    let left = dt;
    let moving = false;
    while (left > 1e-6) {
      const h = Math.min(STEP, left);
      moving = step(session.motion, h) || moving;
      left -= h;
    }
    const cascading = renderer.stepCascade(session.motion, dt);
    if (moving || cascading || renderer.dirty || session.isBusy()) {
      renderer.draw(session.motion, dt);
      // After the first 120 drawn frames, long frames lower the pixel ratio a step.
      frames += 1;
      if (frames > 120) {
        slow = slow * 0.95 + (dt > 0.02 ? 1 : 0) * 0.05;
        if (slow > 0.5 && renderer.lowerQuality) {
          renderer.lowerQuality();
          slow = 0;
          frames = 0;
        }
      }
    }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  document.documentElement.classList.add("is-ready");
}

start();
