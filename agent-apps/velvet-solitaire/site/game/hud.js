// The page around the felt: the rail's numbers, the phone's bars, the menu, the win card,
// and the one plain status line. HTML styled by the theme's tokens; never canvas text.

const MINUS = "−";

export function money(v) {
  const n = Math.round(v);
  const s = `$${Math.abs(n).toLocaleString("en-US")}`;
  return n < 0 ? `${MINUS}${s}` : s;
}

export function clock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

export function ruleLine(draw, scoring) {
  if (scoring === "vegas") {
    return `The deck costs $52 and pays $5 a card to the foundations. ${draw === 3 ? "Three passes" : "One pass"} through the stock.`;
  }
  return `10 for a card to a foundation, 5 for a card turned up or played from the waste. Unlimited passes.`;
}

export function feltRule(draw, scoring) {
  if (scoring === "vegas") return `Deck $52  •  Pays $5 a card  •  ${draw === 3 ? "Three passes" : "One pass"}`;
  return `Klondike  •  Draw ${draw === 3 ? "three" : "one"}  •  Unlimited passes`;
}

export function createHud({ config, prefs, reduced }) {
  const root = document.getElementById("app");
  const $ = (sel) => root.querySelector(sel);
  const all = (sel) => [...root.querySelectorAll(sel)];
  const bind = (name, text) => {
    for (const el of all(`[data-bind="${name}"]`)) if (el.textContent !== text) el.textContent = text;
  };
  const wide = window.matchMedia("(min-aspect-ratio: 21/20) and (min-width: 640px)");
  // Phone landscape: the rail is too short for the settings, so its Menu button opens them in a sheet.
  const short = window.matchMedia("(min-aspect-ratio: 21/20) and (min-width: 640px) and (max-height: 560px)");
  const status = $("#status");
  const attract = $("#attract");
  const win = $("#win");
  const confirm = $("#confirm");
  const scrim = $("#scrim");
  const rail = $("#rail");
  const more = $("#rail-more");
  let statusTimer = 0;
  let rolling = null;
  let shown = { score: 0, vegas: false };
  let lastFocus = null;
  const handlers = {};

  bind("title", config.title || "Velvet Solitaire");

  // The rail's bottom edge fades while more of it sits below, so a cut-off control reads as scrollable.
  const markMore = () => rail.classList.toggle("has-more", rail.scrollTop + rail.clientHeight < rail.scrollHeight - 2);
  rail.addEventListener("scroll", markMore, { passive: true });
  const railSize = new ResizeObserver(markMore);
  for (const el of [rail, ...rail.children]) railSize.observe(el);

  const hud = {
    on(action, fn) {
      handlers[action] = fn;
    },
    isCompact: () => !wide.matches,
    tableArea() {
      const r = $("#table-area").getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    },
    railRects() {
      const rects = [];
      const push = (el) => {
        if (!el) return;
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) rects.push({ x: r.left, y: r.top, w: r.width, h: r.height });
      };
      if (wide.matches) push(rail);
      else {
        push($(".topbar"));
        push($(".actionbar"));
      }
      return rects;
    },
    paintPrint: () => {},

    setNumbers({ vegas, demo, bank, won, score, seconds, moves }) {
      root.classList.toggle("is-vegas", vegas);
      bind("score-label", vegas ? (demo ? "House bank" : "Bank") : "Score");
      if (!rolling) {
        const value = vegas ? bank : score;
        shown = { score: value, vegas };
        bind("score", vegas ? money(value) : value.toLocaleString("en-US"));
      }
      bind("won-label", "Won");
      bind("won", money(won));
      bind("time", clock(seconds));
      bind("moves", String(moves));
    },

    setControls({ undo, undoOff, finish, hint, demo }) {
      for (const el of all('[data-action="undo"]')) {
        el.disabled = !undo;
        el.title = undoOff ? "Undo is off in Vegas scoring" : "";
      }
      for (const el of all('[data-action="hint"]')) el.disabled = !hint;
      for (const el of all('[data-action="finish"]')) {
        el.disabled = !finish;
        el.classList.toggle("is-ready", !!finish);
      }
      root.classList.toggle("is-demo", !!demo);
    },

    setDemo(on) {
      attract.hidden = !on;
      root.classList.toggle("is-demo", on);
    },

    /** Counts the bank or the score up to a value, as the cards fly. */
    rollBank(to) {
      roll(to, true);
    },
    rollScore(to) {
      roll(to, false);
    },
    setWon(v) {
      bind("won", money(v));
    },

    say(text) {
      status.textContent = text;
      status.classList.add("is-shown");
      clearTimeout(statusTimer);
      statusTimer = setTimeout(() => status.classList.remove("is-shown"), 2800);
    },

    setStats(stats, player) {
      bind("player", player ? `${player}’s table` : "Your table");
      bind("played", String(stats.played));
      bind("wins", stats.played ? `${stats.won} (${Math.round((stats.won / stats.played) * 100)}%)` : String(stats.won));
      bind("streak", String(stats.streak));
      bind("best-time", stats.bestTime ? clock(stats.bestTime) : "None yet");
      bind("best-score", stats.bestScore.toLocaleString("en-US"));
      bind("bank", money(stats.bank));
    },

    setRule(draw, scoring) {
      bind("rule", ruleLine(draw, scoring));
      root.classList.toggle("rule-vegas", scoring === "vegas");
    },

    showWin(summary, stats) {
      const line = `${clock(summary.seconds)} and ${summary.moves} moves.`;
      bind("win-line", line);
      bind(
        "win-money",
        summary.vegas
          ? `Paid ${money(summary.payout)}. Your bank stands at ${money(summary.bank)}.`
          : `Score ${summary.score.toLocaleString("en-US")}${summary.bonus ? `, with a ${summary.bonus.toLocaleString("en-US")} time bonus` : ""}.`,
      );
      hud.setStats(stats, config.playerName);
      openLayer(win);
    },
    hideWin() {
      closeLayer(win);
    },

    confirmNew() {
      const body = prefs.scoring === "vegas" ? "The next deck costs $52. What this deal has won goes to your bank." : "This deal counts as played.";
      bind("confirm-body", body);
      openLayer(confirm);
    },
    closeConfirm() {
      closeLayer(confirm);
    },

    openMenu() {
      if (wide.matches && !short.matches) return;
      const sheet = wide.matches ? more : rail;
      root.classList.add("menu-open");
      scrim.hidden = false;
      lastFocus = document.activeElement;
      sheet.setAttribute("role", "dialog");
      sheet.setAttribute("aria-modal", "true");
      if (sheet === more) sheet.setAttribute("aria-label", "Table settings and stats");
      const first = sheet.querySelector("button, input");
      if (first) first.focus({ preventScroll: true });
    },
    closeMenu() {
      if (!root.classList.contains("menu-open")) return;
      root.classList.remove("menu-open");
      scrim.hidden = true;
      for (const sheet of [rail, more]) {
        sheet.removeAttribute("role");
        sheet.removeAttribute("aria-modal");
      }
      more.removeAttribute("aria-label");
      if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
    },
    menuOpen: () => root.classList.contains("menu-open"),
    layerOpen: () => !win.hidden || !confirm.hidden,

    /** Sets the settings controls to the current choices. */
    showPrefs(p) {
      for (const input of all('input[type="radio"]')) input.checked = String(p[input.name]) === input.value;
      const sound = $('input[name="sound"]');
      if (sound) sound.checked = !!p.sound;
    },
    onWideChange(fn) {
      wide.addEventListener("change", fn);
    },
  };

  function openLayer(el) {
    lastFocus = document.activeElement;
    el.hidden = false;
    scrim.hidden = false;
    requestAnimationFrame(() => el.classList.add("is-open"));
    const btn = el.querySelector(".btn--accent") || el.querySelector("button");
    if (btn) btn.focus({ preventScroll: true });
  }
  function closeLayer(el) {
    if (el.hidden) return;
    el.classList.remove("is-open");
    el.hidden = true;
    if (!root.classList.contains("menu-open")) scrim.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  // The lead number counts toward its target from wherever it stands now, so rolls that
  // arrive faster than they finish still only ever climb toward the last one.
  let rollFrame = 0;
  function roll(to, vegas) {
    const show = (v) => bind("score", vegas ? money(v) : Math.round(v).toLocaleString("en-US"));
    if (reduced || shown.vegas !== vegas) {
      shown = { score: to, vegas };
      rolling = null;
      show(to);
      return;
    }
    rolling = { to, vegas };
    if (rollFrame) return;
    let last = performance.now();
    const step = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const target = rolling ? rolling.to : shown.score;
      const gap = target - shown.score;
      // Close most of the gap every tenth of a second; finish on the last dollar.
      const next = Math.abs(gap) < 1 ? target : shown.score + gap * Math.min(1, dt * 9);
      shown = { score: next, vegas };
      show(next);
      if (next !== target) rollFrame = requestAnimationFrame(step);
      else {
        rollFrame = 0;
        rolling = null;
      }
    };
    rollFrame = requestAnimationFrame(step);
  }

  // Buttons and settings speak through the handlers main.js sets.
  root.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn || btn.disabled) return;
    const fn = handlers[btn.dataset.action];
    if (fn) fn(btn);
  });
  root.addEventListener("change", (e) => {
    const input = e.target;
    if (!input.name) return;
    const fn = handlers[`set:${input.name}`];
    if (fn) fn(input.type === "checkbox" ? input.checked : input.value);
  });
  short.addEventListener("change", () => hud.closeMenu());
  scrim.addEventListener("click", () => {
    if (!confirm.hidden) closeLayer(confirm);
    else hud.closeMenu();
  });

  return hud;
}
