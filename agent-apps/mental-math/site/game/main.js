// Mental Math: Start, Drill, Results, and History on one page. Reads window.__APP_CONFIG__ (players, operations,
// seconds) at load; keeps results in this browser.

import { OPERATIONS, OP_LABELS, MIN_LEVEL, MAX_LEVEL, makeProblem, seeded } from "./problems.js";
import {
  addResult,
  entriesFor,
  exportText,
  importText,
  lastThirty,
  loadPrefs,
  loadResults,
  sampleFor,
  savePrefs,
  today,
} from "./store.js";
import { createCurve, fillRing, fmt } from "./chart.js";
import { burstStreak, confetti, dropStreak, enter, pop, pulseRight, reduced, shakeWrong } from "./motion.js";

const UNTIMED_COUNT = 10;
const WINDOW = 10;
const STEP_UP = 0.9;
const STEP_DOWN = 0.6;

// ---- Config ----------------------------------------------------------------------------------------------------

const config = window.__APP_CONFIG__ || {};
const players = (Array.isArray(config.players) ? config.players : [])
  .filter((p) => p && typeof p.name === "string" && p.name.trim())
  .map((p) => ({ name: p.name.trim(), level: clampLevel(p.level ?? 3), kid: Boolean(p.kid) }));
if (!players.length) players.push({ name: "You", level: 3, kid: false });
const allowedOps = (Array.isArray(config.operations) ? config.operations : OPERATIONS).filter((op) => OPERATIONS.includes(op));
if (!allowedOps.length) allowedOps.push("add", "subtract", "multiply", "divide");
const seconds = Number.isFinite(config.seconds) && config.seconds >= 0 ? Math.round(config.seconds) : 90;

function clampLevel(n) {
  return Math.min(MAX_LEVEL, Math.max(MIN_LEVEL, Math.round(Number(n) || 1)));
}

// ---- Elements ----------------------------------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const app = $("app");
const root = document.documentElement;
const card = $("card");
const problemEl = $("problem");
const answerEl = $("answer");
const hintEl = $("hint");
const announceEl = $("announce");
const badge = $("badge");
const badgeNum = $("badge-num");
const timebarFill = $("timebar");
const confettiLayer = $("confetti");
const streakEl = $("streak");
const streakNum = $("streak-num");
const streakBurst = $("streak-burst");
const fine = matchMedia("(pointer: fine)");

const panelCurve = createCurve($("panel-curve"));
const resultsCurve = createCurve($("results-curve"));
const historyCurve = createCurve($("history-curve"));

// ---- State -------------------------------------------------------------------------------------------------------

const prefs = loadPrefs();
let current = players.find((p) => p.name === prefs.player) || players[0];
let screen = "start";
let drill = null;
let historyPlayer = current;
let streak = 0;

const levelOf = (p) => clampLevel(prefs.levels[p.name] ?? p.level);
const opsOf = (p) => {
  const mine = Array.isArray(prefs.ops[p.name]) ? prefs.ops[p.name].filter((op) => allowedOps.includes(op)) : [];
  return mine.length ? mine : [...allowedOps];
};
const untimedFor = (p) => p.kid || seconds === 0;

function historyOf(p) {
  const real = entriesFor(p.name);
  return { entries: real.length ? real : sampleFor({ ...p, level: levelOf(p) }) };
}

function persist() {
  prefs.player = current.name;
  savePrefs(prefs);
}

// ---- Screens -----------------------------------------------------------------------------------------------------

function setScreen(next) {
  screen = next;
  app.dataset.screen = next;
  $("play").hidden = next === "results" || next === "history";
  $("results").hidden = next !== "results";
  $("history").hidden = next !== "history";
  if (next === "start") startDemo();
  else stopDemo();
  window.scrollTo(0, 0);
}

// ---- Start -------------------------------------------------------------------------------------------------------

const KID_ICON =
  '<svg class="chip-kid" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5l2.7 6 6.5.6-4.9 4.3 1.5 6.4L12 16.5l-5.8 3.3 1.5-6.4L2.8 9.1l6.5-.6z"/></svg>';

function renderPlayers() {
  const box = $("players");
  box.textContent = "";
  for (const p of players) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.setAttribute("role", "radio");
    chip.setAttribute("aria-checked", String(p === current));
    chip.tabIndex = p === current ? 0 : -1;
    chip.dataset.name = p.name;
    const name = document.createElement("span");
    name.textContent = p.name;
    chip.append(name);
    if (p.kid) chip.insertAdjacentHTML("beforeend", KID_ICON);
    const lv = document.createElement("span");
    lv.className = "chip-level";
    lv.textContent = String(levelOf(p));
    lv.setAttribute("aria-label", `level ${levelOf(p)}`);
    chip.append(lv);
    chip.addEventListener("click", () => selectPlayer(p));
    box.append(chip);
  }
}

function renderOps() {
  const mine = opsOf(current);
  for (const box of document.querySelectorAll("[data-ops]")) {
    box.textContent = "";
    for (const op of allowedOps) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = op === "percent" ? "op op-pct" : "op";
      b.setAttribute("aria-pressed", String(mine.includes(op)));
      b.setAttribute("aria-label", OP_LABELS[op].name);
      b.title = OP_LABELS[op].name;
      if (op === "squares") b.innerHTML = "<span>x<sup>2</sup></span>";
      else b.textContent = OP_LABELS[op].symbol;
      b.addEventListener("click", () => toggleOp(op));
      box.append(b);
    }
  }
}

function toggleOp(op) {
  const mine = opsOf(current);
  const next = mine.includes(op) ? mine.filter((o) => o !== op) : [...mine, op];
  if (!next.length) return;
  prefs.ops[current.name] = allowedOps.filter((o) => next.includes(o));
  persist();
  renderOps();
  startDemo();
}

function renderLevel() {
  const lv = levelOf(current);
  badgeNum.textContent = String(lv);
  $("level-down").disabled = lv <= MIN_LEVEL;
  $("level-up").disabled = lv >= MAX_LEVEL;
}

function stepLevel(delta) {
  const lv = clampLevel(levelOf(current) + delta);
  if (lv === levelOf(current)) return;
  prefs.levels[current.name] = lv;
  persist();
  renderLevel();
  renderPlayers();
  pop(badge);
  startDemo();
}

function lengthWords(p) {
  return untimedFor(p) ? `${UNTIMED_COUNT} problems` : `${seconds} seconds`;
}

function renderStartText() {
  $("length").textContent = lengthWords(current);
  hintEl.textContent = `${lengthWords(current)}. ${fine.matches ? "Press Enter or Go to start." : "Tap Go to start."}`;
  $("go-label").textContent = "Go";
  if (untimedFor(current)) app.dataset.untimed = "";
  else delete app.dataset.untimed;
}

function renderPanel(how = "draw") {
  const { entries } = historyOf(current);
  $("panel-name").textContent = current.name;
  const last = entries[entries.length - 1];
  if (last) {
    const when = document.createElement("span");
    when.className = "panel-last-when";
    when.textContent = "Last drill, ";
    $("panel-score-label").replaceChildren(when, `${last.accuracy}% right`);
    fillRing($("panel-ring"), last.accuracy / 100, $("panel-score"), last.score, { duration: how === "none" ? 0 : 1000 });
  }
  panelCurve.draw(lastThirty(entries), how);
}

function selectPlayer(p, how) {
  if (p === current || screen !== "start") return;
  const from = players.indexOf(current);
  current = p;
  persist();
  if (p.kid) root.setAttribute("data-kid", "");
  else root.removeAttribute("data-kid");
  renderPlayers();
  renderOps();
  renderLevel();
  renderStartText();
  renderPanel(how || (players.indexOf(p) > from ? "slide-left" : "slide-right"));
  startDemo();
  const chip = document.querySelector(`.chip[data-name="${CSS.escape(p.name)}"]`);
  if (chip && document.activeElement && document.activeElement.classList.contains("chip")) chip.focus();
}

// ---- The attract loop: on Start the card works a few problems by itself ----------------------------------------

const demo = { timers: [], rand: null, previous: "", count: 0 };

function later(fn, ms) {
  demo.timers.push(setTimeout(fn, ms));
}

function stopDemo() {
  demo.timers.forEach(clearTimeout);
  demo.timers = [];
  answerEl.classList.remove("is-demo");
}

function startDemo() {
  stopDemo();
  setStreak(0, false);
  demo.rand = seeded(`demo:${current.name}:${levelOf(current)}:${opsOf(current).join()}`);
  demo.count = 0;
  answerEl.classList.add("is-demo");
  demoProblem(true);
}

function typeOut(text, at) {
  for (let i = 0; i < text.length; i += 1) {
    later(() => {
      answerEl.value = text.slice(0, i + 1);
      flashKey(text[i]);
    }, at + i * 170);
  }
  return at + text.length * 170;
}

function demoProblem(first = false) {
  if (screen !== "start" || document.hidden) return;
  const problem = makeProblem(opsOf(current), levelOf(current), demo.previous, demo.rand);
  demo.previous = problem.text;
  showProblem(problem, !first);
  answerEl.value = "";
  demo.count += 1;
  const right = String(problem.answer);
  let t = first ? 500 : 650;
  const miss = demo.count % 6 === 5;
  if (miss) {
    const wrong = String(problem.answer + (problem.answer > 9 ? 10 : 1));
    t = typeOut(wrong, t) + 260;
    later(() => {
      flashKey("enter");
      shakeWrong(card);
      setStreak(0);
    }, t);
    t += 520;
    later(() => {
      answerEl.value = "";
      flashKey("back");
    }, t);
    t += 200;
  }
  t = typeOut(right, t) + 260;
  later(() => {
    flashKey("enter");
    pulseRight(card);
    if (!miss) setStreak(streak + 1);
  }, t);
  later(() => demoProblem(), t + 820);
}

document.addEventListener("visibilitychange", () => {
  if (screen === "start") {
    if (document.hidden) stopDemo();
    else startDemo();
  }
  if (screen === "drill" && drill) {
    if (document.hidden) pauseClock();
    else resumeClock();
  }
});

// ---- Drill -------------------------------------------------------------------------------------------------------

const OPERATOR = /\s([+−×÷-])\s/;

function showProblem(problem, animate = true) {
  if (problem.html) problemEl.innerHTML = problem.html;
  else {
    const parts = problem.text.split(OPERATOR);
    problemEl.textContent = "";
    parts.forEach((part, i) => {
      if (i % 2) {
        const op = document.createElement("span");
        op.className = "opr";
        op.textContent = part;
        problemEl.append(op);
      } else problemEl.append(part);
    });
  }
  problemEl.setAttribute("aria-label", problem.text);
  fitProblem();
  if (animate) enter(problemEl);
}

// The problem fills the board's width, up to the size cap the layout sets.
function fitProblem() {
  problemEl.style.setProperty("--fit", "1");
  const wrap = problemEl.parentElement;
  const wide = problemEl.scrollWidth;
  const tall = problemEl.offsetHeight;
  if (!wide || !tall || !wrap.clientWidth || !wrap.clientHeight) return;
  const fit = Math.min(1, wrap.clientWidth / wide, wrap.clientHeight / tall);
  problemEl.style.setProperty("--fit", fit.toFixed(3));
}

new ResizeObserver(() => fitProblem()).observe(problemEl.parentElement);
document.fonts.ready.then(fitProblem);

function setStreak(n, animate = true) {
  const climbed = n > streak;
  const broke = n === 0 && streak > 0;
  streak = n;
  streakEl.dataset.count = String(n);
  streakNum.textContent = String(n);
  streakEl.classList.toggle("is-hot", n >= 3);
  streakEl.setAttribute("aria-label", `${n} in a row`);
  if (!animate) return;
  if (climbed) burstStreak(streakEl, streakNum, streakBurst, n);
  else if (broke) dropStreak(streakNum);
}

function startDrill() {
  stopDemo();
  const untimed = untimedFor(current);
  const level = levelOf(current);
  drill = {
    player: current,
    untimed,
    level,
    startLevel: level,
    window: [],
    answers: 0,
    right: 0,
    score: 0,
    typed: "",
    problem: null,
    locked: false,
    remaining: seconds * 1000,
    endsAt: 0,
    timer: 0,
    lowTimer: 0,
    bar: null,
    ops: opsOf(current),
  };
  setScreen("drill");
  $("drill-player").textContent = current.name;
  $("drill-score").textContent = "0";
  $("length").textContent = untimed ? `1 of ${UNTIMED_COUNT}` : `${seconds} seconds`;
  hintEl.textContent = fine.matches ? "Type the answer, then Enter." : "";
  $("go-label").textContent = "OK";
  $("go-key").setAttribute("aria-label", "Check answer");
  renderStars();
  setStreak(0, false);
  badgeNum.textContent = String(level);
  answerEl.value = "";
  nextProblem();
  if (!untimed) startClock();
}

function renderStars() {
  const box = $("stars");
  box.textContent = "";
  if (!drill || !drill.untimed) return;
  for (let i = 0; i < UNTIMED_COUNT; i += 1) {
    const li = document.createElement("li");
    li.className = "star";
    box.append(li);
  }
}

function startClock() {
  timebarFill.parentElement.classList.remove("is-low");
  drill.bar = timebarFill.animate([{ transform: "scaleX(1)" }, { transform: "scaleX(0)" }], {
    duration: seconds * 1000,
    easing: "linear",
    fill: "forwards",
  });
  resumeClock(true);
}

function resumeClock(fresh = false) {
  if (!drill || drill.untimed) return;
  if (!fresh && drill.bar) drill.bar.play();
  drill.endsAt = performance.now() + drill.remaining;
  clearTimeout(drill.timer);
  clearTimeout(drill.lowTimer);
  drill.timer = setTimeout(endDrill, drill.remaining);
  const lowIn = drill.remaining - 10_000;
  if (lowIn > 0) drill.lowTimer = setTimeout(() => timebarFill.parentElement.classList.add("is-low"), lowIn);
  else timebarFill.parentElement.classList.add("is-low");
}

function pauseClock() {
  if (!drill || drill.untimed) return;
  clearTimeout(drill.timer);
  clearTimeout(drill.lowTimer);
  drill.remaining = Math.max(0, drill.endsAt - performance.now());
  if (drill.bar) drill.bar.pause();
}

function nextProblem() {
  drill.problem = makeProblem(drill.ops, drill.level, drill.problem ? drill.problem.text : "");
  drill.typed = "";
  answerEl.value = "";
  showProblem(drill.problem);
}

function press(key) {
  if (screen === "start") {
    if (key === "enter") startDrill();
    return;
  }
  if (screen !== "drill" || !drill || drill.locked) return;
  if (key === "back") drill.typed = drill.typed.slice(0, -1);
  else if (key === "enter") return submit();
  else if (/^\d$/.test(key) && drill.typed.length < 7) drill.typed = (drill.typed === "0" ? "" : drill.typed) + key;
  answerEl.value = drill.typed;
}

function submit() {
  if (!drill.typed) return;
  const p = drill.problem;
  const ok = Number(drill.typed) === p.answer;
  drill.answers += 1;
  if (ok) {
    drill.right += 1;
    drill.score += 10 * p.level;
    pulseRight(card);
    setStreak(streak + 1);
    announceEl.textContent = streak >= 3 ? `Right. ${streak} in a row.` : "Right.";
    hintEl.textContent = fine.matches ? "Type the answer, then Enter." : "";
    if (drill.player.kid) confetti(confettiLayer, answerEl, 8, { spread: 0.7, size: 0.8 });
  } else {
    shakeWrong(card);
    setStreak(0);
    announceEl.textContent = `Not quite. ${p.text} is ${p.answer}.`;
    hintEl.textContent = `${p.text} = ${fmt.format(p.answer)}`;
  }
  $("drill-score").textContent = fmt.format(drill.score);
  const star = $("stars").children[drill.answers - 1];
  if (star) star.classList.add(ok ? "is-ok" : "is-miss");
  adapt(ok);

  if (drill.untimed && drill.answers >= UNTIMED_COUNT) {
    drill.locked = true;
    setTimeout(endDrill, 420);
    return;
  }
  if (drill.untimed) $("length").textContent = `${drill.answers + 1} of ${UNTIMED_COUNT}`;
  drill.locked = true;
  setTimeout(
    () => {
      if (!drill) return;
      drill.locked = false;
      nextProblem();
    },
    ok ? 160 : 360,
  );
}

// Rolling accuracy over the last ten answers: up a level at 90 %, down at 60 %.
function adapt(ok) {
  drill.window.push(ok);
  if (drill.window.length > WINDOW) drill.window.shift();
  if (drill.window.length < WINDOW) return;
  const acc = drill.window.filter(Boolean).length / WINDOW;
  let next = drill.level;
  if (acc >= STEP_UP) next = clampLevel(drill.level + 1);
  else if (acc <= STEP_DOWN) next = clampLevel(drill.level - 1);
  if (next !== drill.level) {
    drill.level = next;
    drill.window = [];
    badgeNum.textContent = String(next);
    pop(badge);
  }
}

function quitDrill() {
  if (!drill) return;
  clearTimeout(drill.timer);
  clearTimeout(drill.lowTimer);
  if (drill.bar) drill.bar.cancel();
  drill = null;
  backToStart();
}

function endDrill() {
  if (!drill) return;
  clearTimeout(drill.timer);
  clearTimeout(drill.lowTimer);
  const d = drill;
  drill = null;
  if (d.bar) d.bar.cancel();
  timebarFill.parentElement.classList.remove("is-low");
  if (!d.answers) return backToStart();
  const accuracy = Math.round((d.right / d.answers) * 100);
  const entry = { date: today(), score: d.score, level: d.level, accuracy };
  addResult(d.player.name, entry);
  prefs.levels[d.player.name] = d.level;
  persist();
  showResults(d, entry);
}

function backToStart() {
  timebarFill.parentElement.classList.remove("is-low");
  $("go-key").removeAttribute("aria-label");
  renderPlayers();
  renderOps();
  renderLevel();
  renderStartText();
  setScreen("start");
  renderPanel("draw");
}

// ---- Results -----------------------------------------------------------------------------------------------------

function showResults(d, entry) {
  setScreen("results");
  $("results-title").textContent = d.player.name;
  $("results-accuracy").textContent = `${d.right} right of ${d.answers}`;
  $("results-badge-num").textContent = String(d.level);
  $("again").textContent = "Again";
  const next = players.length > 1 ? players[(players.indexOf(d.player) + 1) % players.length] : null;
  const nextBtn = $("next-player");
  nextBtn.hidden = !next;
  if (next) nextBtn.textContent = `Next: ${next.name}`;
  nextBtn.onclick = () => {
    if (!next) return;
    current = d.player;
    selectPlayerFromResults(next);
  };
  $("results-history").classList.toggle("wide-span", !next);

  fillRing($("results-ring"), entry.accuracy / 100, $("results-score"), entry.score, { duration: 1100, delay: 150 });
  resultsCurve.draw(lastThirty(entriesFor(d.player.name)), "draw");
  renderToday(d.player);

  const leveled = d.level > d.startLevel;
  if (leveled || d.player.kid) {
    const at = reduced() ? 0 : 1250;
    setTimeout(() => {
      if (screen !== "results") return;
      pop($("results-badge"));
      confetti(confettiLayer, $("results-badge"), 24);
    }, at);
  }
  $("again").focus({ preventScroll: true });
}

function selectPlayerFromResults(p) {
  current = p;
  persist();
  if (p.kid) root.setAttribute("data-kid", "");
  else root.removeAttribute("data-kid");
  backToStart();
}

function renderToday(player) {
  const all = loadResults();
  const day = today();
  const rows = players.map((p) => {
    const list = Array.isArray(all[p.name]) ? all[p.name] : [];
    const best = list.filter((e) => e && e.date === day).reduce((m, e) => Math.max(m, e.score), -1);
    return { p, best };
  });
  const max = Math.max(1, ...rows.map((r) => r.best));
  const box = $("today-list");
  box.textContent = "";
  rows.forEach(({ p, best }, i) => {
    const li = document.createElement("li");
    li.className = p === player ? "today-item is-current" : "today-item";
    const bar = document.createElement("div");
    bar.className = best >= 0 ? "today-bar" : "today-bar is-empty";
    if (best >= 0) bar.style.setProperty("transform", `scaleY(${Math.max(0.06, best / max)})`);
    const score = document.createElement("div");
    score.className = "today-score";
    score.textContent = best >= 0 ? fmt.format(best) : "–";
    const name = document.createElement("div");
    name.className = "today-name";
    name.textContent = p.name;
    li.append(bar, score, name);
    box.append(li);
    if (best >= 0 && !reduced()) {
      bar.animate([{ transform: "scaleY(0)" }, { transform: `scaleY(${Math.max(0.06, best / max)})` }], {
        duration: 700,
        delay: 300 + i * 60,
        easing: "cubic-bezier(0.23, 1, 0.32, 1)",
        fill: "backwards",
      });
    }
  });
}

// ---- History -----------------------------------------------------------------------------------------------------

const dayWords = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric" });

function openHistory(p = current) {
  historyPlayer = p;
  setScreen("history");
  $("history-status").textContent = "";
  renderHistory("draw");
}

function renderHistory(how) {
  const tabs = $("history-tabs");
  tabs.textContent = "";
  for (const p of players) {
    const t = document.createElement("button");
    t.type = "button";
    t.className = "chip";
    t.setAttribute("role", "tab");
    t.setAttribute("aria-selected", String(p === historyPlayer));
    t.setAttribute("aria-checked", String(p === historyPlayer));
    t.textContent = p.name;
    t.addEventListener("click", () => {
      if (p === historyPlayer) return;
      const dir = players.indexOf(p) > players.indexOf(historyPlayer) ? "slide-left" : "slide-right";
      historyPlayer = p;
      $("history-status").textContent = "";
      renderHistory(dir);
    });
    tabs.append(t);
  }
  const { entries } = historyOf(historyPlayer);
  $("history-title").textContent = historyPlayer.name;
  historyCurve.draw(lastThirty(entries), how);
  const body = $("history-rows");
  body.textContent = "";
  const rows = [...entries].reverse();
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.className = "history-empty";
    const td = document.createElement("td");
    td.colSpan = 4;
    td.textContent = "No drills yet.";
    tr.append(td);
    body.append(tr);
  }
  for (const e of rows) {
    const tr = document.createElement("tr");
    const [y, m, d] = e.date.split("-").map(Number);
    for (const text of [dayWords.format(new Date(y, m - 1, d)), fmt.format(e.score), String(e.level), `${e.accuracy}%`]) {
      const td = document.createElement("td");
      td.textContent = text;
      tr.append(td);
    }
    body.append(tr);
  }
}

function exportFile() {
  const blob = new Blob([exportText()], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mental-math-${today()}.json`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  sayHistory("Saved every drill to your downloads.");
}

function importFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const added = importText(String(reader.result));
      const names = Object.keys(added);
      const total = names.reduce((n, k) => n + added[k], 0);
      if (!total) sayHistory("Every drill in that file is already here.");
      else sayHistory(`Added ${total} ${total === 1 ? "drill" : "drills"} for ${listWords(names)}.`);
      renderPlayers();
      renderHistory("none");
    } catch {
      sayHistory("That file isn't a Mental Math export.");
    }
  };
  reader.readAsText(file);
}

function sayHistory(text) {
  const s = $("history-status");
  s.textContent = text;
  s.dataset.keep = "1";
  setTimeout(() => delete s.dataset.keep, 0);
}

function listWords(names) {
  if (names.length <= 1) return names.join("");
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

// ---- Input -------------------------------------------------------------------------------------------------------

const pad = $("pad");
const held = new Map();

pad.addEventListener("pointerdown", (e) => {
  const key = e.target.closest(".key");
  if (!key || e.button > 0) return;
  e.preventDefault();
  key.classList.add("is-pressed");
  held.set(e.pointerId, { key, at: performance.now() });
  press(key.dataset.key);
});

// A key stays down while the finger does, and for at least a beat after a quick tap so the press always shows.
function release(e) {
  const hold = held.get(e.pointerId);
  if (!hold) return;
  held.delete(e.pointerId);
  setTimeout(() => hold.key.classList.remove("is-pressed"), Math.max(0, 110 - (performance.now() - hold.at)));
}
for (const type of ["pointerup", "pointercancel", "pointerleave"]) pad.addEventListener(type, release);
pad.addEventListener("click", (e) => {
  const key = e.target.closest(".key");
  if (key && e.detail === 0) press(key.dataset.key);
});

function flashKey(name) {
  const key = pad.querySelector(`[data-key="${name}"]`);
  if (!key) return;
  key.classList.add("is-pressed");
  setTimeout(() => key.classList.remove("is-pressed"), 140);
}

document.addEventListener("keydown", (e) => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const onButton = e.target instanceof HTMLElement && e.target.closest("button, label, input[type=file]");
  if (screen === "drill") {
    if (/^\d$/.test(e.key)) {
      press(e.key);
      flashKey(e.key);
    } else if (e.key === "Backspace") {
      press("back");
      flashKey("back");
    } else if (e.key === "Enter") {
      e.preventDefault();
      press("enter");
      flashKey("enter");
    } else if (e.key === "Escape") quitDrill();
    else return;
    e.preventDefault();
    return;
  }
  if (screen === "start") {
    if (e.key === "Enter" && !onButton) {
      e.preventDefault();
      startDrill();
    } else if ((e.key === "ArrowRight" || e.key === "ArrowLeft") && (!onButton || e.target.classList.contains("chip"))) {
      const i = players.indexOf(current);
      const next = players[(i + (e.key === "ArrowRight" ? 1 : players.length - 1)) % players.length];
      e.preventDefault();
      selectPlayer(next);
    }
    return;
  }
  if (screen === "results") {
    if (e.key === "Escape") backToStart();
    else if (e.key === "Enter" && !onButton) startDrill();
    return;
  }
  if (screen === "history" && e.key === "Escape") backToStart();
});

$("level-down").addEventListener("click", () => stepLevel(-1));
$("level-up").addEventListener("click", () => stepLevel(1));
$("quit").addEventListener("click", quitDrill);
$("again").addEventListener("click", startDrill);
$("open-history").addEventListener("click", () => openHistory(current));
$("results-history").addEventListener("click", () => openHistory(current));
$("history-back").addEventListener("click", backToStart);
$("export").addEventListener("click", exportFile);
$("import").addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  if (file) importFile(file);
  e.target.value = "";
});
fine.addEventListener("change", () => {
  if (screen === "start") renderStartText();
});

// ---- Go ----------------------------------------------------------------------------------------------------------

if (current.kid) root.setAttribute("data-kid", "");
else root.removeAttribute("data-kid");
renderPlayers();
renderOps();
renderLevel();
renderStartText();
setScreen("start");
renderPanel("draw");
