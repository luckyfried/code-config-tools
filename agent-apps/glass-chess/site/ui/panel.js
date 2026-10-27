// The words around the board: who sits at each edge with what they have taken and their clock, the status line,
// the move list, and the result card.
import { formatClock } from "../game/clock.js";

const VALUE = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
const ORDER = "qrbnp";
const $ = (id) => document.getElementById(id);

export class Panel {
  constructor() {
    this.plates = { far: $("plate-far"), near: $("plate-near") };
    this.moves = $("moves");
    this.title = $("status-title");
    this.line = $("status-line");
    this.start = $("start");
    this.result = $("result");
    this.icons = {};
    this.lastClock = {};
  }

  setIcons(icons) { this.icons = icons; }

  // Pieces each side has taken, best first, and the material lead.
  taken(history) {
    const got = { w: [], b: [] };
    for (const m of history) if (m.captured) got[m.color].push(m.captured);
    for (const side of "wb") got[side].sort((a, b) => ORDER.indexOf(a) - ORDER.indexOf(b));
    const score = (side) => got[side].reduce((n, t) => n + VALUE[t], 0);
    return { got, lead: score("w") - score("b") };
  }

  plate(el, side, { name, turn, history, clock }) {
    el.dataset.side = side;
    const img = el.querySelector(".plate-piece");
    const icon = this.icons[side + "k"];
    if (icon && img.getAttribute("src") !== icon) img.src = icon;
    el.querySelector(".plate-name").textContent = name;
    if (turn) el.dataset.turn = ""; else delete el.dataset.turn;
    const { got, lead } = this.taken(history);
    const other = side === "w" ? "b" : "w";
    const box = el.querySelector(".plate-taken");
    const key = got[side].join("") + lead;
    if (box.dataset.key !== key) {
      box.dataset.key = key;
      box.replaceChildren(...got[side].map((t) => {
        const i = document.createElement("img");
        i.alt = t;
        i.width = i.height = 20;
        if (this.icons[other + t]) i.src = this.icons[other + t];
        return i;
      }));
      const mine = side === "w" ? lead : -lead;
      if (mine > 0) { const s = document.createElement("span"); s.textContent = `+${mine}`; box.append(s); }
    }
    const clockEl = el.querySelector(".plate-clock");
    clockEl.hidden = !clock;
  }

  // Draws everything from the current game; `far` is the side across the board from the viewer.
  render({ game, attract, far, demo }) {
    const history = attract ? demo.history : game.history;
    const turn = attract ? demo.turn : game.turn;
    const near = far === "w" ? "b" : "w";
    const nameOf = (side) => (attract ? demo.names[side] : game.nameOf(side));
    const clock = !attract && game.clock.enabled;
    const over = attract ? demo.over : game.over;
    this.plate(this.plates.far, far, { name: nameOf(far), turn: !over && turn === far, history, clock });
    this.plate(this.plates.near, near, { name: nameOf(near), turn: !over && turn === near, history, clock });

    const status = attract ? demo.status : game.status();
    this.title.textContent = status.title;
    if (status.title === "Check" || status.title === "Checkmate") this.title.dataset.check = ""; else delete this.title.dataset.check;
    this.line.textContent = status.line;
    this.start.hidden = !attract;
    if (attract) this.moves.dataset.attract = ""; else delete this.moves.dataset.attract;
    this.renderMoves(history);
  }

  renderMoves(history) {
    const items = [];
    for (let i = 0; i < history.length; i += 2) {
      const li = document.createElement("li");
      const n = document.createElement("span");
      n.className = "move-number";
      n.textContent = `${i / 2 + 1}.`;
      li.append(n);
      for (const m of [history[i], history[i + 1]]) {
        const s = document.createElement("span");
        s.className = "move";
        s.textContent = m ? m.san : "";
        if (m && m === history[history.length - 1]) s.dataset.current = "";
        li.append(s);
      }
      items.push(li);
    }
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "moves-empty";
      li.textContent = "No moves yet. White starts.";
      items.push(li);
    }
    this.moves.replaceChildren(...items);
    const last = this.moves.lastElementChild;
    if (last) {
      this.moves.scrollTo({ top: this.moves.scrollHeight, left: this.moves.scrollWidth, behavior: "smooth" });
    }
  }

  // Updates only the clock faces; called every frame while a clock runs.
  tick(game, now, sound) {
    if (!game?.clock.enabled) return;
    for (const el of Object.values(this.plates)) {
      const side = el.dataset.side;
      const ms = game.clock.remaining(side, now);
      const text = formatClock(ms);
      const face = el.querySelector(".plate-clock");
      if (face.textContent !== text) {
        face.textContent = text;
        if (ms < 20000) face.dataset.low = ""; else delete face.dataset.low;
        const secs = Math.ceil(ms / 1000);
        if (game.clock.running === side && ms < 10000 && secs !== this.lastClock[side]) sound?.("tick");
        this.lastClock[side] = secs;
      }
    }
  }

  showResult(title, line, { actions = true } = {}) {
    $("result-title").textContent = title;
    $("result-line").textContent = line;
    $("result-actions").hidden = !actions;
    this.result.hidden = false;
  }

  hideResult() { this.result.hidden = true; }
}
