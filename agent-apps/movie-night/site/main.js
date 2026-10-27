// Movie Night: the household's watch list as a lit wall of posters, a brass wheel that picks tonight's film, and a
// shelf of what you have watched. The list comes from config.js; what the household does with it stays in this browser.
import { Glide, startLoop, easeOutCubic } from "./game/motion.js";
import { readFilms, createStore } from "./game/state.js";
import { fontsReady, artFor, urlFor, cardUrl, drawCard } from "./game/art.js";
import { Spot } from "./game/spot.js";
import { hasWebGL, pickTier, FrameWatch } from "./scene/quality.js";
import { readTokens, readCss } from "./scene/tokens.js";
import { Wheel } from "./ui/wheel.js";
import { FlatWall } from "./ui/flatwall.js";
import { bindWall } from "./ui/input.js";
import { Confetti } from "./ui/confetti.js";
import { unlockAudio } from "./ui/audio.js";

const config = window.__APP_CONFIG__ || {};
const $ = (id) => document.getElementById(id);
const app = $("app");
const stage = $("stage");
const flatEl = $("flatwall");
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const isPhone = () => innerWidth < 900;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const films = readFilms(config);
const store = createStore(config, films);
const lookup = config.lookupPosters !== false;
const arts = new Map();
const glide = new Glide();
const spot = new Spot();
const wheel = new Wheel($("wheel"), reduced);
const confetti = new Confetti($("confetti"));

let list = [];
let view = null;
let screen = "wall";
let hover = -1;
let dimming = 0;
let autoSpin = 0;
const title = { key: null, t: 1, wght: 0 };
const spotState = { index: -1, on: 0, level: 0, drop: 0, dimming: 0 };
const sceneState = { p: 0, spot: spotState, hover: -1 };

const name = config.title || "Movie Night";
$("brand-name").textContent = name;
document.title = name;

const sourceOf = (film) => arts.get(film.key)?.source || drawCard(film);
const urlOf = (film) => urlFor(film, arts.get(film.key));
const indexOf = (key) => list.findIndex((f) => f.key === key);
const front = () => list[glide.front] || null;

// The film the light belongs to: tonight's pick, otherwise the one with the most hearts.
function lightFilm() {
  const picked = store.tonight();
  if (picked && indexOf(picked.key) >= 0) return picked;
  let best = null;
  for (const f of list) if (!best || store.heartCount(f) > store.heartCount(best)) best = f;
  return best;
}

// Views: the WebGL room, the CSS 3D coverflow, or the reduced-motion grid. All three take the same calls.
async function webglView() {
  const { createWorld } = await import("./scene/world.js");
  const tier = pickTier();
  const world = createWorld({ canvas: stage, tier, tokens: readTokens() });
  const watch = new FrameWatch(tier, (r) => world.setRatio(r), () => {
    world.dispose();
    useView(flatView("css3d"));
  });
  document.addEventListener("visibilitychange", () => watch.resume());
  return {
    el: stage,
    setFilms: (l) => world.setFilms(l, l.map(sourceOf)),
    setSource: (i, f) => world.setSource(i, sourceOf(f)),
    step: (dt) => world.step(dt, sceneState),
    render(t) {
      watch.frame(t);
      world.render(t, sceneState);
    },
    setCover: (r, b, instant, floor) => world.setCover(r, b, instant, floor),
    pick: (x, y) => world.pick(x, y),
    resize: () => world.resize(),
    tokens: () => world.setTokens(readTokens()),
  };
}

function flatView(mode) {
  const wall = new FlatWall(flatEl, mode, (i) => tapPoster(i));
  stage.hidden = true;
  if (mode === "grid") {
    const card = $("card");
    const room = () => app.style.setProperty("--card-room", `${Math.round(innerHeight - card.getBoundingClientRect().top + 12)}px`);
    new ResizeObserver(room).observe(card);
    addEventListener("resize", room);
  }
  return {
    el: flatEl,
    grid: mode === "grid",
    setFilms: (l) => wall.setFilms(l, l.map(urlOf)),
    setSource: (i, f) => wall.setUrl(i, urlOf(f)),
    step: (dt) => wall.update(dt, glide.p, spotState),
    render() {},
    setCover: (r) => wall.setCover(r),
    pick(x, y) {
      const el = document.elementFromPoint(x, y)?.closest(".flat-poster");
      return el ? Number(el.dataset.index) : -1;
    },
    resize: () => wall.resize(),
    tokens() {},
  };
}

const bound = new Set();
function useView(v) {
  view = v;
  view.setFilms(list);
  cover(true);
  if (!v.grid && !bound.has(v.el)) {
    bound.add(v.el);
    bindWall(v.el, {
      glide,
      pxPerPoster: () => (isPhone() ? innerWidth * 0.42 : Math.max(180, innerHeight * 0.26)),
      onTap: (x, y) => tapPoster(view.pick(x, y)),
      onHover: (x, y) => {
        hover = x < 0 ? -1 : view.pick(x, y);
      },
    });
  }
}

// The wall's list is every film not yet watched, in the order of the inputs file.
function syncWall() {
  const keys = store.onWall().map((f) => f.key);
  if (keys.join("|") === list.map((f) => f.key).join("|")) return false;
  const keepFront = front()?.key;
  const keepSpot = list[spot.index]?.key;
  list = store.onWall();
  glide.setCount(list.length);
  view?.setFilms(list);
  const fi = indexOf(keepFront);
  if (fi >= 0) glide.jump(fi + (glide.p - Math.round(glide.p)));
  glide.go(fi >= 0 ? fi : glide.front);
  const si = indexOf(keepSpot);
  if (si >= 0) spot.move(si);
  else {
    const lit = lightFilm();
    if (lit) spot.land(indexOf(lit.key), 0.2, true);
  }
  title.key = null;
  return true;
}

// The title card, the hearts, and the buttons follow the poster in front.
const heartSvg = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 7.9 3.6 4.5 7 4.5c2 0 3.6 1.1 5 2.9 1.4-1.8 3-2.9 5-2.9 3.4 0 5.6 3.4 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>';

function paintCard() {
  const f = front();
  const tag = $("card-tag");
  const buttons = [$("btn-heart"), $("btn-pick"), $("btn-watched")];
  if (!f) {
    tag.textContent = "";
    $("card-title").textContent = "Every film is watched";
    $("card-title").classList.add("is-long");
    $("card-year").textContent = "";
    $("card-note").textContent = "Add films to the list and run it again, or put one back from the shelf.";
    $("card-hearts").replaceChildren();
    for (const b of buttons) b.hidden = true;
    return;
  }
  for (const b of buttons) b.hidden = false;
  const tonight = store.tonight()?.key === f.key;
  tag.textContent = tonight ? "Tonight's film" : `${glide.front + 1} of ${list.length} on the list`;
  tag.classList.toggle("is-tonight", tonight);
  $("card-title").textContent = f.title;
  $("card-title").classList.toggle("is-long", f.title.length > 16);
  $("card-year").textContent = f.year ? String(f.year) : "";
  $("card-note").textContent = f.note;
  const hearts = store.hearts(f);
  $("card-hearts").replaceChildren(
    ...store.people.map((p) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "who";
      b.classList.toggle("is-on", hearts.includes(p));
      b.classList.toggle("is-turn", p === store.person && store.people.length > 1);
      b.setAttribute("aria-pressed", String(hearts.includes(p)));
      b.setAttribute("aria-label", `${p}${hearts.includes(p) ? " hearted it" : " has not hearted it"}`);
      b.innerHTML = heartSvg;
      b.append(p);
      b.addEventListener("click", () => {
        unlockAudio();
        store.toggleHeart(f, p);
      });
      return b;
    }),
  );
  const mine = hearts.includes(store.person);
  $("btn-heart").setAttribute("aria-pressed", String(mine));
  $("btn-heart-label").textContent = mine ? "Hearted" : "Heart it";
  $("btn-pick").textContent = tonight ? "Tonight's film" : "Pick for tonight";
  $("btn-pick").disabled = tonight;
  if (isPhone()) cover(false);
}

function paintTurn() {
  const many = store.people.length > 1;
  $("turn-initial").textContent = store.person.slice(0, 1).toUpperCase();
  $("turn-name").textContent = `${store.person}'s turn`;
  $("turn-pass").textContent = many ? `Pass to ${store.nextPerson}` : "";
  $("turn").disabled = !many;
}

function slices() {
  return list.map((f) => ({ key: f.key, title: f.title, weight: 1 + store.heartCount(f) }));
}

const fmt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
const dateOf = (d) => fmt.format(new Date(`${d}T12:00:00`));
const filmOf = (w) => films.find((f) => f.key === w.key) || { key: w.key, title: w.title, year: w.year, note: "" };
const starPath = "M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4-4.7-4.4 6.4-.8z";

function starsRead(n) {
  const s = document.createElement("span");
  s.className = "stars-read";
  s.setAttribute("aria-label", `${n} of 5 stars`);
  s.innerHTML = [1, 2, 3, 4, 5]
    .map((i) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path class="${i <= n ? "star-on" : "star-off"}" d="${starPath}"/></svg>`)
    .join("");
  return s;
}

function posterImg(w, cls) {
  const img = document.createElement("img");
  const f = filmOf(w);
  img.src = arts.has(f.key) ? urlOf(f) : cardUrl(f);
  img.alt = "";
  img.width = 400;
  img.height = 600;
  img.loading = "lazy";
  if (cls) img.className = cls;
  return img;
}

function paintRecent() {
  const items = store.watched().slice(0, 3);
  $("recent").hidden = !items.length;
  $("recent-list").replaceChildren(
    ...items.map((w) => {
      const li = document.createElement("li");
      li.className = "recent-item";
      const text = document.createElement("div");
      const n = document.createElement("span");
      n.className = "recent-name";
      n.textContent = w.title;
      const d = document.createElement("span");
      d.className = "recent-date";
      d.textContent = dateOf(w.date);
      text.append(n, d);
      li.append(posterImg(w), text, starsRead(w.stars));
      return li;
    }),
  );
}

function paintShelf() {
  const items = store.watched();
  $("shelf-count").textContent = `${items.length} ${items.length === 1 ? "film" : "films"} watched`;
  $("shelf-empty").hidden = items.length > 0;
  $("shelf-list").replaceChildren(
    ...items.map((w) => {
      const li = document.createElement("li");
      li.className = "shelf-item";
      const n = document.createElement("p");
      n.className = "shelf-name";
      n.textContent = w.year ? `${w.title} (${w.year})` : w.title;
      const d = document.createElement("p");
      d.className = "shelf-date";
      d.textContent = `Watched ${dateOf(w.date)}`;
      const stars = document.createElement("div");
      stars.className = "stars";
      for (let i = 1; i <= 5; i += 1) {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "star";
        b.classList.toggle("is-on", i <= w.stars);
        b.setAttribute("aria-label", `${i} ${i === 1 ? "star" : "stars"} for ${w.title}`);
        b.setAttribute("aria-pressed", String(i <= w.stars));
        b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${starPath}"/></svg>`;
        b.addEventListener("click", () => store.setStars(w.key, i));
        stars.append(b);
      }
      li.append(posterImg(w, "shelf-poster"), n, d, stars);
      if (films.some((f) => f.key === w.key)) {
        const back = document.createElement("button");
        back.type = "button";
        back.className = "shelf-back";
        back.textContent = "Back on the list";
        back.addEventListener("click", () => store.unwatch(w.key));
        li.append(back);
      }
      return li;
    }),
  );
}

function paintAll() {
  syncWall();
  paintCard();
  paintTurn();
  if (!wheel.spinning) wheel.setSlices(slices());
  paintRecent();
  if (screen === "watched") paintShelf();
}

// Screens. On a wide screen the wheel stands in a column beside the wall; on a phone Tonight is a sheet over the bottom of the room.
const panelOpen = () => (isPhone() ? screen === "tonight" : screen !== "watched");

function cover(instant) {
  if (!view) return;
  let right = 0;
  let bottom = 0;
  let floor = 0;
  if (isPhone()) {
    if (panelOpen()) bottom = $("tonight").offsetHeight + 64;
    floor = innerHeight - $("card").offsetTop + 28;
  } else {
    if (panelOpen()) right = $("tonight").offsetWidth;
    if (screen !== "watched") bottom = innerHeight - $("card").offsetTop + 20;
  }
  view.setCover(right, bottom, instant, floor);
}

function setScreen(next) {
  if (next === "tonight" && !isPhone()) next = "wall";
  screen = next;
  app.dataset.screen = next;
  app.toggleAttribute("data-panel", panelOpen());
  for (const t of document.querySelectorAll(".tab")) {
    if (t.dataset.go === next) t.setAttribute("aria-current", "page");
    else t.removeAttribute("aria-current");
  }
  $("shelf").hidden = next !== "watched";
  if (next === "watched") paintShelf();
  if (panelOpen()) {
    wheel.resize();
    wheel.needs = true;
  }
  cover(false);
}

// Picking: from the wheel, from the card's button, or by tapping the poster in front.
function lightUp(film) {
  const i = indexOf(film.key);
  if (i < 0) return;
  glide.go(i);
  spot.land(i, 0.25, true);
  title.key = null;
}

function pickFront() {
  const f = front();
  if (!f || store.tonight()?.key === f.key) return;
  unlockAudio();
  store.pick(f, store.person);
  lightUp(f);
  const r = $("card-title").getBoundingClientRect();
  confetti.burst(r.left + Math.min(r.width, 280) / 2, r.top, 70);
}

function tapPoster(i) {
  if (i < 0 || !list[i]) return;
  unlockAudio();
  if (i === glide.front && Math.abs(glide.p - i) < 0.08) pickFront();
  else {
    if (view?.grid) glide.jump(i);
    glide.go(i);
  }
}

async function spin() {
  if (wheel.spinning || list.length === 0) return;
  unlockAudio();
  const s = slices();
  wheel.setSlices(s);
  const total = s.reduce((n, x) => n + x.weight, 0);
  let r = Math.random() * total;
  let at = 0;
  while (at < s.length - 1 && r >= s[at].weight) r -= s[at++].weight;
  const button = $("btn-spin");
  button.setAttribute("aria-busy", "true");
  button.textContent = "Spinning…";
  $("tonight-result").textContent = "";
  const won = await wheel.spin(at);
  button.removeAttribute("aria-busy");
  button.textContent = "Spin again";
  const film = list.find((f) => f.key === s[won]?.key);
  if (!film) return;
  store.pick(film, store.person);
  $("tonight-result").textContent = `Tonight: ${film.title}.`;
  const w = $("wheel").getBoundingClientRect();
  confetti.burst(w.left + w.width / 2, w.top + w.height * 0.3, 160);
  lightUp(film);
  if (isPhone()) setTimeout(() => screen === "tonight" && setScreen("wall"), 1300);
}

// The card's title opens from thin and narrow to heavy and wide; on the lit film it waits for the light to strike.
function stepTitle(dt) {
  const f = front();
  const key = f?.key ?? "";
  const card = $("card");
  if (title.key !== key) {
    title.key = key;
    title.t = reduced ? 1 : 0;
    paintCard();
  }
  const falling = spot.phase === "lifting" || spot.phase === "waiting" || (spot.phase === "landing" && spot.drop < 0.97);
  const waiting = f && glide.front === spot.index && falling;
  if (title.t < 1 && !waiting) title.t = Math.min(1, title.t + dt / 0.85);
  const e = easeOutCubic(title.t);
  const wght = Math.round(300 + 480 * e);
  if (wght !== title.wght) {
    title.wght = wght;
    card.style.setProperty("--title-wght", String(wght));
    card.style.setProperty("--title-wdth", (75 + 25 * e).toFixed(1));
  }
}

function themeColors() {
  wheel.setColors(readCss(["wheel-face-a", "wheel-face-b", "wheel-ink", "wheel-brass-hi", "wheel-brass", "wheel-brass-lo", "wheel-bezel"]));
  const c = readCss(["confetti-1", "confetti-2", "confetti-3", "color-accent", "heart"]);
  confetti.setColors(Object.values(c));
  view?.tokens();
}

function bindUi() {
  for (const t of document.querySelectorAll(".tab")) {
    t.addEventListener("click", () => setScreen(screen === t.dataset.go && t.dataset.go !== "wall" ? "wall" : t.dataset.go));
  }
  $("turn").addEventListener("click", () => store.passTurn());
  $("btn-heart").addEventListener("click", () => {
    const f = front();
    if (!f) return;
    unlockAudio();
    store.toggleHeart(f, store.person);
  });
  $("btn-pick").addEventListener("click", pickFront);
  $("btn-watched").addEventListener("click", () => {
    const f = front();
    if (!f) return;
    store.markWatched(f);
    $("shelf-note").textContent = `${f.title} is on the shelf. Give it stars there.`;
  });
  $("btn-spin").addEventListener("click", spin);
  $("btn-export").addEventListener("click", () => {
    const blob = new Blob([store.exportJson()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "movie-night.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    $("shelf-note").textContent = "Saved movie-night.json. Import it in any browser to carry your hearts and shelf there.";
  });
  $("btn-import").addEventListener("click", () => $("import-file").click());
  $("import-file").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const res = store.importJson(await file.text());
    $("shelf-note").textContent = res.message;
    e.target.value = "";
  });
  addEventListener("keydown", (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const onControl = e.target instanceof HTMLElement && e.target.closest("button, input, a");
    if (e.key === "Escape") return setScreen("wall");
    if (screen === "watched") return;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      e.preventDefault();
      glide.nudge(1);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      e.preventDefault();
      glide.nudge(-1);
    } else if (onControl) {
      return;
    } else if (e.key === "Enter") {
      pickFront();
    } else if (e.key === " ") {
      e.preventDefault();
      if (!panelOpen()) setScreen("tonight");
      spin();
    } else if (e.key === "h" || e.key === "H") {
      $("btn-heart").click();
    }
  });
  let resizeTimer = 0;
  addEventListener("resize", () => {
    cancelAnimationFrame(resizeTimer);
    resizeTimer = requestAnimationFrame(() => {
      view?.resize();
      wheel.resize();
      confetti.resize();
      setScreen(screen);
      cover(true);
    });
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", themeColors);
  store.onChange(paintAll);
}

async function boot() {
  const ask = new URLSearchParams(location.search).get("wall");
  const mode = reduced || ask === "grid" ? "grid" : ask === "flat" || !hasWebGL() ? "css3d" : "webgl";
  const making = mode === "webgl" ? webglView().catch(() => null) : Promise.resolve(null);
  await fontsReady();
  const loads = films.map((f) =>
    artFor(f, lookup).then((art) => {
      arts.set(f.key, art);
      const i = indexOf(f.key);
      if (view && i >= 0) view.setSource(i, f);
      return art;
    }),
  );
  await Promise.race([Promise.all(loads), wait(1200)]);

  list = store.onWall();
  glide.setCount(list.length);
  const v = await making;
  setScreen("wall");
  useView(v || flatView(mode === "grid" ? "grid" : "css3d"));
  themeColors();
  bindUi();

  const lit = lightFilm();
  const start = lit ? indexOf(lit.key) : 0;
  glide.jump(reduced ? start : start + 3.2);
  glide.go(start);
  if (lit) spot.land(start, reduced ? 0 : 0.35);
  paintAll();
  wheel.resize();
  if (store.fresh && !isPhone() && list.length > 1) autoSpin = setTimeout(spin, 3200);
  stage.addEventListener("pointerdown", () => clearTimeout(autoSpin), { once: true });

  startLoop(
    (dt) => {
      glide.step(dt);
      spot.step(dt);
      const centered = Math.max(0, 1 - Math.abs(spot.index - glide.p));
      dimming += (spot.level * centered - dimming) * Math.min(1, dt * 8);
      spotState.index = spot.index;
      spotState.on = spot.level;
      spotState.level = spot.level;
      spotState.drop = spot.drop;
      spotState.dimming = dimming;
      sceneState.p = glide.p;
      sceneState.hover = hover;
      view.step(dt);
      wheel.step(dt);
      stepTitle(dt);
    },
    (t) => {
      view.render(t);
      if (wheel.needs && panelOpen()) wheel.draw();
      if (!app.hasAttribute("data-ready")) requestAnimationFrame(() => app.setAttribute("data-ready", ""));
    },
  );
}

boot();
