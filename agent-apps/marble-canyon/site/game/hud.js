// The HUD and the two cards, written as DOM so the theme tokens style them. The game tells it what happened;
// it never decides anything itself.
const $ = (id) => document.getElementById(id);

const WORDS = ["no", "one", "two", "three", "four", "five", "six"];
const MINUS = "−";

export function formatTime(seconds) {
  const t = Math.max(0, seconds);
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  const whole = Math.floor(s);
  const hundredths = Math.floor((s - whole) * 100);
  return `${m}:${String(whole).padStart(2, "0")}.${String(hundredths).padStart(2, "0")}`;
}

export function formatDelta(seconds) {
  const sign = seconds < 0 ? MINUS : "+";
  return `${sign}${Math.abs(seconds).toFixed(2)}`;
}

export const medalFor = (time, medals) =>
  time <= medals.gold ? "gold" : time <= medals.silver ? "silver" : time <= medals.bronze ? "bronze" : "none";

const MEDAL_NAMES = { gold: "Gold", silver: "Silver", bronze: "Bronze" };
const capital = (word) => word.charAt(0).toUpperCase() + word.slice(1);
const possessive = (name) => (name.endsWith("s") ? `${name}’` : `${name}’s`);

export function createHud({ track, medals, config, seed, coarse }) {
  const body = document.body;
  const el = {
    timer: $("timer"),
    delta: $("delta"),
    deltaValue: $("delta-value"),
    deltaLabel: $("delta-label"),
    progressFill: $("progress-fill"),
    progressTicks: $("progress-ticks"),
    progressYou: $("progress-you"),
    progressGhost: $("progress-ghost"),
    banner: $("banner"),
    bannerLabel: $("banner-label"),
    bannerTime: $("banner-time"),
    bannerDelta: $("banner-delta"),
    count: $("count"),
    speed: $("speed"),
    speedValue: $("speed-value"),
    speedFill: $("speed-fill"),
    speedMark: $("speed-mark"),
    jumpCue: $("jump-cue"),
    titleCard: $("title-card"),
    resultCard: $("result-card"),
    sound: $("sound"),
    tilt: $("tilt"),
  };

  $("app-title").textContent = config.title;
  document.title = config.title;
  $("canyon-name").textContent = capital(seed);
  const km = (track.length / 1000).toFixed(1);
  const jumps = track.gaps.length;
  $("canyon-facts").textContent = `${capital(track.lengthName)} canyon: ${km} km with ${WORDS[jumps] ?? jumps} jumps and ${track.boosts.length} boost pads.`;
  $("medal-gold").textContent = formatTime(medals.gold);
  $("medal-silver").textContent = formatTime(medals.silver);
  $("medal-bronze").textContent = formatTime(medals.bronze);
  $("hint").textContent = coarse
    ? "Drag left or right anywhere to steer."
    : "Steer with ← → or A and D. R restarts a run.";
  el.deltaLabel.textContent = `${possessive(config.racerName)} ghost`;

  const ticks = [...track.gates.map((g) => g.s / track.length), 1];
  const tickEls = ticks.map((at, i) => {
    const tick = document.createElement("span");
    tick.className = "progress-tick";
    tick.dataset.kind = i === ticks.length - 1 ? "finish" : "gate";
    tick.style.setProperty("--at", at.toFixed(4));
    el.progressTicks.append(tick);
    return tick;
  });

  let bannerTimer = 0;
  let lastTimer = "";
  let lastSpeed = -1;
  let lastJump = "";

  const showBest = (best) => {
    const line = $("best");
    line.replaceChildren();
    for (const medal of ["gold", "silver", "bronze"]) {
      const node = el.titleCard.querySelector(`.medal[data-medal="${medal}"]`);
      if (best && medalFor(best.time, medals) === medal) node.dataset.earned = "";
      else delete node.dataset.earned;
    }
    if (!best) {
      line.textContent = "Your first run sets the ghost you race after it.";
      return;
    }
    const medal = medalFor(best.time, medals);
    const strong = document.createElement("strong");
    strong.textContent = formatTime(best.time);
    const tail = medal === "none" ? "." : `, ${MEDAL_NAMES[medal].toLowerCase()}.`;
    line.append("Best ", strong, `${tail} ${possessive(best.name || config.racerName)} ghost rolls with you.`);
  };

  return {
    el,
    screen(name) {
      body.dataset.screen = name;
      el.resultCard.hidden = name !== "result";
      if (name !== "run" && name !== "countdown") {
        el.banner.removeAttribute("data-on");
        el.speed.removeAttribute("data-jump");
      }
    },
    showBest,
    reset(hasGhost) {
      for (const tick of tickEls) delete tick.dataset.passed;
      el.delta.hidden = true;
      el.progressGhost.hidden = !hasGhost;
      el.banner.removeAttribute("data-on");
      lastTimer = "";
    },
    count(text) {
      el.count.replaceChildren();
      if (text === null) {
        delete el.count.dataset.beat;
        delete el.count.dataset.go;
        return;
      }
      const span = document.createElement("span");
      span.textContent = text;
      el.count.append(span);
      el.count.dataset.beat = text;
      if (text === "Go") el.count.dataset.go = "";
      else delete el.count.dataset.go;
    },
    frame({ time, s, ghostS, delta, speed, topSpeed, jump, jumpMin }) {
      const text = formatTime(time);
      if (text !== lastTimer) {
        el.timer.textContent = text;
        lastTimer = text;
      }
      el.progressFill.style.setProperty("--p", Math.max(0, Math.min(1, s / track.length)).toFixed(4));
      el.progressYou.style.setProperty("--p", Math.max(0, Math.min(1, s / track.length)).toFixed(4));
      if (ghostS !== null) el.progressGhost.style.setProperty("--p", Math.max(0, Math.min(1, ghostS / track.length)).toFixed(4));
      if (delta !== null) {
        el.delta.hidden = false;
        el.deltaValue.textContent = formatDelta(delta);
        el.delta.dataset.sign = delta <= 0 ? "ahead" : "behind";
      }
      const kmh = Math.round(speed * 3.6);
      if (kmh !== lastSpeed) {
        el.speedValue.textContent = String(kmh);
        lastSpeed = kmh;
      }
      el.speedFill.style.setProperty("--v", Math.min(1, speed / topSpeed).toFixed(3));
      el.speedMark.style.setProperty("--mark", (jumpMin / topSpeed).toFixed(3));
      const state = jump ? (speed < jumpMin ? "slow" : "ok") : "";
      if (state !== lastJump) {
        if (state) el.speed.dataset.jump = state;
        else el.speed.removeAttribute("data-jump");
        el.jumpCue.textContent = state === "slow" ? "Too slow for the jump" : "Jump ahead";
        lastJump = state;
      }
    },
    gate(index, time, delta) {
      tickEls[index].dataset.passed = "";
      el.bannerLabel.textContent = `Gate ${index + 1}`;
      el.bannerTime.textContent = formatTime(time);
      if (delta === null) {
        el.bannerDelta.hidden = true;
      } else {
        el.bannerDelta.hidden = false;
        el.bannerDelta.textContent = formatDelta(delta);
        el.bannerDelta.dataset.sign = delta <= 0 ? "ahead" : "behind";
      }
      el.banner.dataset.on = "";
      clearTimeout(bannerTimer);
      bannerTimer = setTimeout(() => el.banner.removeAttribute("data-on"), 2200);
    },
    finishTick() {
      tickEls[tickEls.length - 1].dataset.passed = "";
    },
    result({ time, splits, previous, medal, isBest }) {
      $("result-name").textContent = config.racerName;
      $("result-time").textContent = formatTime(time);
      const medalEl = $("result-medal");
      medalEl.dataset.medal = medal;
      medalEl.textContent = medal === "none" ? `Bronze at ${formatTime(medals.bronze)}` : MEDAL_NAMES[medal];
      const note = $("result-note");
      if (!previous) {
        note.textContent = "First run on this canyon. Your ghost rolls with you next time.";
        note.dataset.sign = "ahead";
      } else if (Math.abs(previous.time - time) < 0.005) {
        note.textContent = `Matched your best of ${formatTime(previous.time)} to the hundredth.`;
        note.dataset.sign = "ahead";
      } else if (isBest) {
        note.textContent = `New best by ${(previous.time - time).toFixed(2)}.`;
        note.dataset.sign = "ahead";
      } else {
        note.textContent = `${(time - previous.time).toFixed(2)} behind your best of ${formatTime(previous.time)}.`;
        delete note.dataset.sign;
      }
      const list = $("splits");
      list.replaceChildren();
      const rows = [...splits.map((t, i) => [`Gate ${i + 1}`, t, previous?.splits?.[i]]), ["Finish", time, previous?.time]];
      for (const [label, t, then] of rows) {
        const li = document.createElement("li");
        const a = document.createElement("span");
        a.className = "split-label";
        a.textContent = label;
        const b = document.createElement("span");
        b.className = "split-time";
        b.textContent = formatTime(t);
        const c = document.createElement("span");
        c.className = "split-delta";
        if (typeof then === "number") {
          c.textContent = formatDelta(t - then);
          c.dataset.sign = t - then <= 0 ? "ahead" : "behind";
        }
        li.append(a, b, c);
        list.append(li);
      }
      el.resultCard.hidden = false;
    },
    sound(on) {
      el.sound.setAttribute("aria-pressed", on ? "true" : "false");
      el.sound.setAttribute("aria-label", on ? "Sound on" : "Sound off");
    },
    offerTilt(show, on) {
      el.tilt.hidden = !show;
      el.tilt.setAttribute("aria-pressed", on ? "true" : "false");
      el.tilt.textContent = on ? "Tilt steering on" : "Tilt to steer";
    },
  };
}
