// The page around the table: status line, player cards, rail, setup, result, the pass note, and settings. It shows
// what the game tells it and hands every choice back; no rules live here.
import { BLACK, WHITE } from "../game/reversi.js";

const $ = (id) => document.getElementById(id);
// A mouse or trackpad clicks; a finger taps.
const pointerVerb = () => (matchMedia("(hover: hover) and (pointer: fine)").matches ? "Click" : "Tap");

export function createHud(handlers) {
  const el = {
    title: $("title"),
    statusDisc: $("status-disc"),
    statusText: $("status-text"),
    rail: $("rail"),
    undo: $("undo"),
    hint: $("hint"),
    newGame: $("new-game"),
    openSettings: $("open-settings"),
    cards: { [BLACK]: $("player-1"), [WHITE]: $("player-2") },
    names: { [BLACK]: $("name-1"), [WHITE]: $("name-2") },
    notes: { [BLACK]: $("note-1"), [WHITE]: $("note-2") },
    counts: { [BLACK]: $("count-1"), [WHITE]: $("count-2") },
    setup: $("setup"),
    setupForm: $("setup-form"),
    setupLede: $("setup-lede"),
    sideField: $("side-field"),
    strengthField: $("strength-field"),
    result: $("result"),
    resultLine: $("result-line"),
    resultScore: $("result-score"),
    resultActions: $("result-actions"),
    toast: $("toast"),
    settings: $("settings"),
  };
  const shownCounts = { [BLACK]: -1, [WHITE]: -1 };
  let toastTimer = 0;

  el.undo.addEventListener("click", () => handlers.onUndo());
  el.hint.addEventListener("click", () => handlers.onHint());
  el.newGame.addEventListener("click", () => handlers.onNew());
  el.openSettings.addEventListener("click", () => handlers.onSettings());
  $("again").addEventListener("click", () => handlers.onAgain());
  $("change").addEventListener("click", () => handlers.onNew());

  const form = el.setupForm;
  const more = $("setup-more");
  const back = $("setup-back");
  back.addEventListener("click", () => handlers.onBack());
  more.addEventListener("toggle", () => handlers.onSetupResize());
  form.addEventListener("change", (event) => {
    if (event.target.name === "theme") handlers.onTheme(event.target.value);
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const submitter = event.submitter;
    handlers.onStart({
      opponent: submitter && submitter.value === "friend" ? "friend" : "computer",
      human: Number(form.elements.side.value),
      strength: Number(form.elements.strength.value),
    });
  });

  const settingsForm = el.settings.querySelector("form");
  settingsForm.addEventListener("change", (event) => {
    const { name, value } = event.target;
    if (name === "s-theme") handlers.onTheme(value);
    else if (name === "s-scheme") handlers.onScheme(value);
    else if (name === "s-sound") handlers.onSound(value === "on");
  });

  function check(container, name, value) {
    const input = container.querySelector(`input[name="${name}"][value="${value}"]`);
    if (input) input.checked = true;
  }

  return {
    setTitle(text) {
      el.title.textContent = text;
      document.title = text;
    },

    setStatus(text, color = null) {
      el.statusText.textContent = text;
      el.statusDisc.className = `status__disc ${color === BLACK ? "is-dark" : color === WHITE ? "is-light" : "is-none"}`;
    },

    setPlayers(players) {
      for (const color of [BLACK, WHITE]) {
        el.names[color].textContent = players[color].name;
        el.notes[color].textContent = players[color].note;
        el.notes[color].hidden = !players[color].note;
      }
    },

    setSideNames(names) {
      for (const b of document.querySelectorAll(".side-name")) b.textContent = names[Number(b.dataset.side)];
      el.cards[BLACK].setAttribute("aria-label", `${names[BLACK]} discs`);
      el.cards[WHITE].setAttribute("aria-label", `${names[WHITE]} discs`);
    },

    setCounts(black, white) {
      if (shownCounts[BLACK] !== black) el.counts[BLACK].textContent = String(black);
      if (shownCounts[WHITE] !== white) el.counts[WHITE].textContent = String(white);
      shownCounts[BLACK] = black;
      shownCounts[WHITE] = white;
    },

    setTurn(color) {
      el.cards[BLACK].classList.toggle("is-turn", color === BLACK);
      el.cards[WHITE].classList.toggle("is-turn", color === WHITE);
    },

    placeCards(anchors) {
      for (const color of [BLACK, WHITE]) {
        const card = el.cards[color];
        card.style.setProperty("--x", `${Math.round(anchors[color].x)}px`);
        card.style.setProperty("--y", `${Math.round(anchors[color].y)}px`);
        card.classList.toggle("is-below", Boolean(anchors.below[color]));
      }
      for (const node of [el.result, el.toast]) {
        node.style.setProperty("--cx", `${Math.round(anchors.center.x)}px`);
        node.style.setProperty("--cy", `${Math.round(anchors.center.y)}px`);
      }
      // The note rides over the board's upper rows, well inside the frame.
      el.toast.style.setProperty("--ty", `${Math.round(anchors.top.y + (anchors.center.y - anchors.top.y) * 0.3)}px`);
    },

    showSetup({ opponent, human, strength, theme, demo, back: canGoBack }) {
      check(form, "side", human);
      check(form, "strength", strength);
      check(form, "theme", theme);
      el.setupLede.textContent = demo
        ? `${pointerVerb()} a glowing square to place a disc. Every line you close flips.`
        : "Starting over clears the board and sets the opening four.";
      more.open = window.innerWidth >= 760 && window.innerHeight >= 600;
      back.hidden = !canGoBack;
      const first = opponent === "friend" ? $("start-friend") : $("start-computer");
      first.classList.add("button--primary");
      first.classList.remove("button--quiet");
      const second = opponent === "friend" ? $("start-computer") : $("start-friend");
      second.classList.add("button--quiet");
      second.classList.remove("button--primary");
      el.setup.classList.remove("is-away");
      el.setup.removeAttribute("inert");
    },

    hideSetup() {
      el.setup.classList.add("is-away");
      el.setup.setAttribute("inert", "");
    },

    setupShown() {
      return !el.setup.classList.contains("is-away");
    },

    setupRect() {
      return el.setup.getBoundingClientRect();
    },

    showRail(shown) {
      el.rail.classList.toggle("is-hidden", !shown);
    },

    railRect() {
      return el.rail.getBoundingClientRect();
    },

    mastheadBottom() {
      const r = el.statusText.parentElement.getBoundingClientRect();
      return r.bottom;
    },

    setRail({ undo, hint }) {
      el.undo.disabled = !undo;
      el.hint.disabled = !hint;
    },

    showResult(line, score, actions) {
      el.resultLine.textContent = line;
      el.resultScore.textContent = score;
      el.resultActions.hidden = !actions;
      el.result.classList.add("is-shown");
    },

    hideResult() {
      el.result.classList.remove("is-shown");
    },

    toast(text, ms = 1800) {
      el.toast.textContent = text;
      el.toast.classList.add("is-shown");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => el.toast.classList.remove("is-shown"), ms);
    },

    openSettings(prefs) {
      check(settingsForm, "s-theme", prefs.theme);
      check(settingsForm, "s-scheme", prefs.scheme);
      check(settingsForm, "s-sound", prefs.sound ? "on" : "off");
      if (!el.settings.open) el.settings.showModal();
    },

    syncThemeChoice(theme) {
      check(form, "theme", theme);
      check(settingsForm, "s-theme", theme);
    },
  };
}
