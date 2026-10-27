// The page around the street: title, plates, tallies, callouts, the flash, and the wanted poster. Game code
// tells it what happened; it sets classes and text, never inline styles.

const $ = (id) => document.getElementById(id);

const SCREENS = ["is-title", "is-duel", "is-card"];
const PHASES = ["is-waiting", "is-drawing", "is-shot", "is-early"];

export function createHud({ config, isTouch }) {
  const body = document.body;
  const title = $("title");
  const poster = $("poster");
  const hud = $("hud");
  const flash = $("flash");
  const names = [$("name-0"), $("name-1")];
  const announce = $("announce");
  const halves = [...document.querySelectorAll(".half")];
  let flashAt = -Infinity;

  body.classList.toggle("is-touch", isTouch);
  $("title-name").textContent = config.title;
  const when = { sunset: "Sundown", noon: "High noon", midnight: "Midnight" }[config.theme] || "Sundown";
  $("title-town").textContent = `${when} in ${config.townName}`;
  names[0].value = config.players[0];
  names[1].value = config.players[1];
  document.querySelectorAll("[data-where]").forEach((el) => {
    const side = Number(el.dataset.where);
    el.textContent = isTouch ? (side === 0 ? "Left thumb" : "Right thumb") : side === 0 ? "Press A to draw" : "Press L to draw";
  });
  $("title-hint").textContent = isTouch ? "Turn the phone sideways, one thumb on each half." : "Space to start. A and L to draw.";

  function setScreen(name) {
    body.classList.remove(...SCREENS);
    body.classList.add(`is-${name}`);
    title.classList.toggle("is-away", name !== "title");
    title.inert = name !== "title";
    poster.inert = name !== "card";
    hud.inert = true;
  }

  function setPhase(name) {
    body.classList.remove(...PHASES);
    if (name) body.classList.add(`is-${name}`);
  }

  function holes(container, need, won) {
    if (container.childElementCount !== need) {
      container.replaceChildren(...Array.from({ length: need }, () => {
        const h = document.createElement("span");
        h.className = "hole";
        return h;
      }));
    }
    [...container.children].forEach((h, i) => h.classList.toggle("is-hit", i < won));
  }

  return {
    names() {
      return names.map((input, i) => input.value.trim() || config.players[i]);
    },

    setMode(mode) {
      body.classList.toggle("is-solo", mode === "solo");
      document.querySelectorAll("#mode button").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.mode === mode)));
      names[1].value = mode === "solo" ? "The Stranger" : config.players[1];
      names[1].readOnly = mode === "solo";
    },

    setBestOf(n) {
      document.querySelectorAll("#best-of button").forEach((b) => b.setAttribute("aria-checked", String(Number(b.dataset.best) === n)));
    },

    setStranger(text) {
      $("stranger").textContent = text;
    },

    ready() {
      body.classList.remove("is-loading");
    },

    title() {
      setScreen("title");
      setPhase(null);
      body.classList.remove("is-demo");
    },

    duel(series, demo = false) {
      setScreen("duel");
      body.classList.toggle("is-demo", demo);
      this.tally(series);
    },

    tally(series) {
      const shown = series.names;
      document.querySelectorAll("[data-name]").forEach((el) => {
        el.textContent = shown[Number(el.dataset.name)];
      });
      document.querySelectorAll("[data-holes]").forEach((el) => holes(el, series.need, series.wins[Number(el.dataset.holes)]));
      $("round-name").textContent = `Round ${series.round || 1}`;
      $("round-need").textContent = `First to ${series.need} of ${series.bestOf}`;
    },

    phase: setPhase,

    early(name) {
      $("callout-early").textContent = `${name} jumped the gun`;
      setPhase("early");
    },

    pressed(side) {
      const half = halves[side];
      half.classList.add("is-pressed");
      setTimeout(() => half.classList.remove("is-pressed"), 140);
    },

    flash(soft = false) {
      // a shot right after DRAW leaves DRAW's white frame to run out
      if (soft && flash.classList.contains("is-on") && performance.now() - flashAt < 400) return;
      flashAt = performance.now();
      flash.classList.remove("is-on", "is-soft");
      void flash.offsetWidth;
      flash.classList.add(soft ? "is-soft" : "is-on");
    },

    say(text) {
      announce.textContent = text;
    },

    /** The wanted poster: kind "round" or "series". */
    poster({ kind, head, forLine, name, digits, unit = "ms", forfeit = false, note, stamp, next, home, portrait }) {
      $("poster-head").textContent = head;
      $("poster-for").textContent = forLine;
      $("poster-name").textContent = name;
      $("poster-digits").textContent = digits;
      $("poster-unit").textContent = unit;
      $("poster-time").classList.toggle("is-forfeit", forfeit);
      $("poster-note").textContent = note;
      $("poster-stamp").textContent = stamp || "";
      $("next-label").textContent = next;
      $("home").hidden = !home;
      if (portrait) {
        const c = $("portrait");
        c.width = portrait.width;
        c.height = portrait.height;
        c.getContext("2d").drawImage(portrait, 0, 0);
      }
      poster.dataset.kind = kind;
      setScreen("card");
      poster.classList.remove("is-open");
      void poster.offsetWidth;
      poster.classList.add("is-open");
      setTimeout(() => {
        if (poster.classList.contains("is-open") && !isTouch) $("next").focus({ preventScroll: true });
      }, 450);
    },

    closePoster() {
      poster.classList.remove("is-open");
      if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    },
  };
}
